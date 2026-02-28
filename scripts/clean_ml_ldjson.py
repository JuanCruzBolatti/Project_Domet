import json
from datetime import datetime, timezone
from typing import Any

from domet.db import connect, init_db


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_price_currency(ld_list: list[dict[str, Any]]) -> tuple[float | None, str | None]:
    # Busca el objeto que tenga offers (tipo Product)
    for obj in ld_list:
        offers = obj.get("offers")
        if isinstance(offers, dict):
            price = offers.get("price")
            currency = offers.get("priceCurrency")

            try:
                price_f = float(price) if price is not None else None
            except (TypeError, ValueError):
                price_f = None

            currency_s = currency if isinstance(currency, str) else None
            return price_f, currency_s
    return None, None


def extract_city_from_breadcrumb(ld_list: list[dict[str, Any]]) -> str | None:
    # Busca el objeto BreadcrumbList y toma el último "name" (en tu ejemplo es Caseros)
    for obj in ld_list:
        if obj.get("@type") != "BreadcrumbList":
            continue
        items = obj.get("itemListElement")
        if not isinstance(items, list) or not items:
            continue
        last = items[-1]
        if isinstance(last, dict):
            item = last.get("item")
            if isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str) and name:
                    return name
    return None


def main():
    init_db()

    with connect() as con:
        cur = con.cursor()

        # Traemos raws no limpiados todavía
        rows = cur.execute(
            """
            SELECT r.id, r.payload_json
            FROM listings_raw r
            LEFT JOIN listings_clean c ON c.raw_id = r.id
            WHERE r.payload_type = 'item_ldjson'
              AND c.id IS NULL
            ORDER BY r.id
            """
        ).fetchall()

        print(f"raw pendientes de limpiar: {len(rows)}")

        inserted = 0
        skipped = 0

        for raw_id, payload_json in rows:
            try:
                payload = json.loads(payload_json)
            except json.JSONDecodeError:
                skipped += 1
                continue

            ld_list = payload.get("ld_json")
            if not isinstance(ld_list, list):
                skipped += 1
                continue

            price, currency = extract_price_currency(ld_list)
            city = extract_city_from_breadcrumb(ld_list) or "Caseros"

            if price is None:
                skipped += 1
                continue

            cur.execute(
                """
                INSERT INTO listings_clean (
                    raw_id, cleaned_at, currency, price,
                    area_m2, rooms, bathrooms,
                    lat, lon,
                    neighborhood, city,
                    features_json
                )
                VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, ?, NULL)
                """,
                (raw_id, now_utc_iso(), currency, price, city),
            )
            inserted += 1

        con.commit()

        print("inserted:", inserted)
        print("skipped:", skipped)
        print("listings_clean total:", cur.execute("SELECT COUNT(*) FROM listings_clean").fetchone()[0])


if __name__ == "__main__":
    main()