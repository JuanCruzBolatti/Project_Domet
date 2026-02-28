import sqlite3
from .config import DATA_DIR, DB_PATH

def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with connect() as con: 
        cur = con.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listings_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                url TEXT,
                fetched_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listings_clean (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_id INTEGER,
                cleaned_at TEXT NOT NULL,
                price REAL,
                area_m2 REAL,
                rooms INTEGER,
                bathrooms INTEGER,
                lat REAL,
                lon REAL,
                neighborhood TEXT,
                city TEXT,
                features_json TEXT,
                FOREIGN KEY(raw_id) REFERENCES listings_raw(id)
            )
            """
        )

        con.commit()