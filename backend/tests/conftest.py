"""Configuración común de las pruebas.

Por defecto las pruebas usan Postgres dedicado (`db-test`, puerto 5433). También se puede definir
TEST_DATABASE_URL con un archivo SQLite terminado en `_test.db`: las pruebas de particiones y
concurrencia se omiten. Nunca elijas una base que quieras conservar:

    docker compose --profile test up -d db-test
    cd backend && pytest

Guardas de seguridad:
  1. el nombre de la base debe terminar en ``_test`` o las pruebas abortan antes de conectarse;
  2. se ignora ``DATABASE_URL`` (solo se lee ``TEST_DATABASE_URL``);
  3. el esquema se reinicia únicamente dentro de esa base.

Las pruebas que usan la base se marcan con ``pytestmark = pytest.mark.bd``; las puras (ruteo, recalibración,
DDL…) no la necesitan. Cada módulo marcado empieza con las tablas vacías.
"""
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5433/urbansafe_test")

TEST_DIALECT = make_url(TEST_URL).get_backend_name()
_nombre_bd = make_url(TEST_URL).database or ""
_nombre_seguro = Path(_nombre_bd).stem if TEST_DIALECT == "sqlite" else _nombre_bd
if not _nombre_seguro.endswith("_test"):
    raise RuntimeError(
        f"TEST_DATABASE_URL apunta a '{_nombre_bd}': por seguridad la base de pruebas debe terminar en '_test'.")

# los tests no tocan la base real ni TomTom
os.environ["DATABASE_URL"] = TEST_URL           # sobrescribe cualquier DATABASE_URL del entorno o del .env
os.environ["API_TOMTOM"] = ""
os.environ["TOMMTOM_KEY"] = ""
os.environ["LOCATIONIQ_TOKEN"] = ""
os.environ["JWT_SECRET_KEY"] = "urbansafe-test-key-not-for-production-0000000000000000000000000000"

RAIZ = Path(__file__).resolve().parents[1]
for p in (RAIZ, RAIZ / "model"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

MENSAJE_SIN_BD = (
    "No hay Postgres de pruebas en {url}.\n"
    "  Levántalo con:  docker compose --profile test up -d db-test\n"
    "  (o define TEST_DATABASE_URL hacia una base cuyo nombre termine en _test).")


def pytest_configure(config):
    config.addinivalue_line("markers", "bd: la prueba usa la base de datos Postgres de pruebas")
    config.addinivalue_line("markers", "postgres: requiere Postgres real (particiones nativas)")
    config.addinivalue_line("markers", "lento: prueba lenta (carga de modelos o simulaciones largas)")


def pytest_sessionstart(session):
    """Comprueba la base de pruebas y reinicia el esquema de Postgres antes de importar la app."""
    session.config._bd_ok = False
    try:
        engine = create_engine(TEST_URL, pool_pre_ping=True)
        with engine.begin() as con:
            if TEST_DIALECT == "postgresql":
                con.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                con.execute(text("CREATE SCHEMA public"))
        engine.dispose()
        session.config._bd_ok = True
    except Exception as exc:                                    # sin Docker: las pruebas puras siguen funcionando
        session.config._bd_error = str(exc).splitlines()[0]


def pytest_collection_modifyitems(items):
    if TEST_DIALECT != "postgresql":
        for item in items:
            if item.get_closest_marker("postgres"):
                item.add_marker(pytest.mark.skip(reason="Esta prueba necesita Postgres y sus particiones nativas"))


@pytest.fixture(scope="module", autouse=True)
def _bd_limpia_por_modulo(request):
    """Los módulos marcados con `bd` arrancan con todas las tablas vacías."""
    if request.node.get_closest_marker("bd") is None:
        yield
        return
    if not request.config._bd_ok:
        pytest.fail(MENSAJE_SIN_BD.format(url=TEST_URL) + f"\n  Detalle: {getattr(request.config, '_bd_error', '')}")
    from app import app
    from db.connection import db
    with app.app_context():
        if TEST_DIALECT == "sqlite":
            for tabla in reversed(db.metadata.sorted_tables):
                db.session.execute(tabla.delete())
            db.session.commit()
        else:
            tablas = ", ".join(f'"{t.name}"' for t in db.metadata.sorted_tables)
            if tablas:
                db.session.execute(text(f"TRUNCATE TABLE {tablas} RESTART IDENTITY CASCADE"))
                db.session.commit()
    yield
