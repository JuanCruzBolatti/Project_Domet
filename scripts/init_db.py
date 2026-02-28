from domet.db import init_db
from domet.config import DB_PATH

def main():
    init_db()
    print(f"DB creada/ok en: {DB_PATH}")

if __name__ == "__main__":
    main()