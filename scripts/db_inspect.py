import json
import sqlite3

from domet.config import DB_PATH


def list_tables(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def count_rows(con: sqlite3.Connection, table: str) -> int:
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def raw_breakdown(con: sqlite3.Connection):
    rows = con.execute(
        "SELECT payload_type, COUNT(*) FROM listings_raw GROUP BY payload_type ORDER BY COUNT(*) DESC"
    ).fetchall()
    return rows


def show_sample_raw(con: sqlite3.Connection, n: int = 1):
    rows = con.execute(
        """
        SELECT id, source, item_id, url, fetched_at, payload_type, payload_json
        FROM listings_raw
        ORDER BY id DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()

    for r in rows:
        id_, source, item_id, url, fetched_at, payload_type, payload_json = r
        print("\n--- RAW ROW ---")
        print("id:", id_)
        print("source:", source)
        print("item_id:", item_id)
        print("url:", url)
        print("fetched_at:", fetched_at)
        print("payload_type:", payload_type)
        try:
            obj = json.loads(payload_json)
            print("payload keys:", list(obj.keys()) if isinstance(obj, dict) else type(obj))
        except Exception as e:
            print("payload_json not valid json:", e)


def main():
    con = sqlite3.connect(DB_PATH)

    print("DB:", DB_PATH)
    tables = list_tables(con)
    print("Tables:", tables)

    if "listings_raw" in tables:
        print("listings_raw rows:", count_rows(con, "listings_raw"))
        print("listings_raw by payload_type:", raw_breakdown(con))

    if "listings_clean" in tables:
        print("listings_clean rows:", count_rows(con, "listings_clean"))

    if "listings_raw" in tables and count_rows(con, "listings_raw") > 0:
        show_sample_raw(con, n=1)

    con.close()


if __name__ == "__main__":
    main()