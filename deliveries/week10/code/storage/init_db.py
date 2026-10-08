from __future__ import annotations

from storage import db


def main() -> None:
    db.ensure_database()
    conn = db.connect()
    try:
        db.init_schema(conn)
    finally:
        conn.close()
    print("[init_db] esquema aplicado correctamente.")


if __name__ == "__main__":
    main()
