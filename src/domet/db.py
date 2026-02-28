import sqlite3
from .config import DATA_DIR, DB_PATH

def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON") 
    return con

def init_db(drop_existing=False):
    with connect() as con: 
        cur = con.cursor()

        if drop_existing:
            cur.execute("DROP TABLE IF EXISTS listings_clean")
            cur.execute("DROP TABLE IF EXISTS listings_raw")


        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listings_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,              -- 'mercadolibre', 'zonaprop', etc.
                item_id TEXT,                      -- ej: 'MLA1682911893' (si existe)
                url TEXT NOT NULL,
                fetched_at TEXT NOT NULL,          -- ISO 8601 UTC
                payload_type TEXT NOT NULL,        -- 'item_json', 'item_html', 'search_json', etc.
                payload_json TEXT NOT NULL         -- JSON string (o HTML string si payload_type es 'item_html')
            )
            """
        )

        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_listings_raw_source_item
            ON listings_raw(source, item_id)
            """
        )

        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_listings_raw_source_url
            ON listings_raw(source, url)
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listings_clean (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_id INTEGER NOT NULL,
                cleaned_at TEXT NOT NULL,          -- ISO 8601 UTC

                currency TEXT,                     -- 'USD', 'ARS', etc.
                price REAL,                        -- precio total (número)
                area_m2 REAL,                      -- m2 (preferentemente cubiertos o totales; definimos en clean.py)
                rooms INTEGER,
                bathrooms INTEGER,

                lat REAL,
                lon REAL,

                neighborhood TEXT,
                city TEXT,

                features_json TEXT,                -- JSON string con extras (garage, patio, pileta, etc.)
                FOREIGN KEY(raw_id) REFERENCES listings_raw(id) ON DELETE CASCADE
            )
            """
        )

        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_listings_clean_raw_id
            ON listings_clean(raw_id)
            """
        )
        

        con.commit()