from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # week10/code

from pipeline import ingest_demand  # noqa: E402
from storage import db as storagedb  # noqa: E402


def _servidor_arriba() -> bool:
    import os

    import psycopg

    try:
        with psycopg.connect(
            f"host={os.getenv('PGHOST', 'localhost')} "
            f"port={os.getenv('PGPORT', '5432')} "
            f"dbname=postgres user={os.getenv('PGUSER', 'urbansafe')} "
            f"password={os.getenv('PGPASSWORD', 'urbansafe_dev')}",
            connect_timeout=3,
        ):
            return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def db():
    if not _servidor_arriba():
        pytest.fail(
            "PostgreSQL no disponible. Levanta el server: "
            "`docker compose up -d db` (y espera el healthcheck)."
        )
    storagedb.ensure_database()
    conn = storagedb.connect()
    try:
        storagedb.init_schema(conn)
    except Exception:
        conn.close()
        raise
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def db_cargado(db):
    ingest_demand.load_all(db)
    ingest_demand.verify_vista(db)
    return db
