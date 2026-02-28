import json
import random
import re
import time
from datetime import datetime, timezone 
from typing import Any

import requests
from bs4 import BeautifulSoup 

from domet.db import connect, init_db 

SOURCE = "mercadolibre" 

SEARCH_BASE = "https://inmuebles.mercadolibre.com.ar/venta-casa-caseros_NoIndex_True"
PAGE_SIZE = 48

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)

HEADERS = {"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9,en;q=0.8"}

MLA_RE = re.compile(r"(MLA[-]?\d+)", re.IGNORECASE)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch(url: str, session: requests.Session) -> str:
    r = session.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def search_url_from_offset(offset: int) -> str:
    # 1 = primera página (sin _Desde_)
    # 49 = segunda (1 + 48)
    if offset == 1:
        return SEARCH_BASE
    return SEARCH_BASE.replace("_NoIndex_True", f"_Desde_{offset}_NoIndex_True")


def parse_listing_urls(search_html: str) -> list[str]:
    soup = BeautifulSoup(search_html, "lxml")
    urls: list[str] = []

    for a in soup.select("a.poly-component__title"):
        href = str(a.get("href", ""))
        if not href:
            continue
        urls.append(href.split("#", 1)[0])

    # dedupe preservando orden
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out


def extract_ld_json(item_html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(item_html, "lxml")
    out: list[dict[str, Any]] = []
    for s in soup.select('script[type="application/ld+json"]'):
        txt = s.string or s.get_text(strip=True)
        if not txt:
            continue
        try:
            obj = json.loads(txt)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def extract_item_id(url: str, ld_list: list[dict[str, Any]]) -> str | None:
    # 1) Preferimos sku/productID desde JSON-LD
    for obj in ld_list:
        sku = obj.get("sku") or obj.get("productID")
        if isinstance(sku, str) and sku:
            return sku.strip().upper()

    # 2) fallback: regex en URL (MLA-168... o MLA168...)
    m = MLA_RE.search(url)
    if not m:
        return None
    return m.group(1).replace("-", "").upper()


def already_have(con, item_id: str | None, url: str) -> bool:
    cur = con.cursor()
    if item_id:
        cur.execute(
            "SELECT 1 FROM listings_raw WHERE source=? AND item_id=? LIMIT 1",
            (SOURCE, item_id),
        )
        if cur.fetchone() is not None:
            return True

    cur.execute(
        "SELECT 1 FROM listings_raw WHERE source=? AND url=? LIMIT 1",
        (SOURCE, url),
    )
    return cur.fetchone() is not None


def insert_raw(con, *, item_id: str | None, url: str, payload_type: str, payload: dict[str, Any]):
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO listings_raw (source, item_id, url, fetched_at, payload_type, payload_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (SOURCE, item_id, url, now_utc_iso(), payload_type, json.dumps(payload, ensure_ascii=False)),
    )
    con.commit()


def main(max_pages: int = 3, sleep_range: tuple[float, float] = (1.0, 2.3)):
    """
    max_pages: cuántas páginas de búsqueda recorre (cada una ~48 items).
    """
    init_db()

    session = requests.Session()

    offset = 1
    pages_done = 0

    with connect() as con:
        while pages_done < max_pages:
            s_url = search_url_from_offset(offset)
            print(f"[search] {s_url}")

            s_html = fetch(s_url, session)
            item_urls = parse_listing_urls(s_html)

            if not item_urls:
                print("No encontré URLs; corto.")
                break

            print(f"  encontrados: {len(item_urls)}")

            for item_url in item_urls:
                # Para no refetchear cosas ya guardadas, intentamos dedupe por URL antes de bajar el item.
                if already_have(con, None, item_url):
                    continue

                print(f"    [item] {item_url}")
                item_html = fetch(item_url, session)

                ld_list = extract_ld_json(item_html)
                item_id = extract_item_id(item_url, ld_list)

                if already_have(con, item_id, item_url):
                    continue

                if ld_list:
                    payload_type = "item_ldjson"
                    payload = {
                        "url": item_url,
                        "item_id": item_id,
                        "ld_json": ld_list,
                    }
                else:
                    # fallback (no debería pasar mucho en ML, pero por las dudas)
                    payload_type = "item_html"
                    payload = {"url": item_url, "item_id": item_id, "html": item_html}

                insert_raw(
                    con,
                    item_id=item_id,
                    url=item_url,
                    payload_type=payload_type,
                    payload=payload,
                )

                time.sleep(random.uniform(*sleep_range))

            pages_done += 1
            offset += PAGE_SIZE
            time.sleep(random.uniform(*sleep_range))

    print("Listo.")


if __name__ == "__main__":
    main(max_pages=2)