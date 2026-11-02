"""Arranque simultáneo de varios procesos (p. ej. 2+ workers de gunicorn) sobre una base VACÍA.

Antes de serializar la creación del esquema con un bloqueo asesor de Postgres, dos procesos hacían `CREATE TABLE` a la vez
y uno fallaba con `duplicate key value violates unique constraint "pg_type_typname_nsp_index"` (se vio al levantar el backend en Docker).
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

import conftest

pytestmark = [pytest.mark.postgres]

RAIZ = Path(__file__).resolve().parents[1]
NOMBRE = "urbansafe_arranque_test"


@pytest.fixture()
def base_vacia():
    admin_url = make_url(conftest.TEST_URL).set(database="postgres")
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE IF EXISTS {NOMBRE} WITH (FORCE)"))
            c.execute(text(f"CREATE DATABASE {NOMBRE}"))
    except Exception as exc:
        pytest.fail(conftest.MENSAJE_SIN_BD.format(url=conftest.TEST_URL) + f"\n  Detalle: {str(exc).splitlines()[0]}")
    url = make_url(conftest.TEST_URL).set(database=NOMBRE).render_as_string(hide_password=False)
    yield url
    with admin.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {NOMBRE} WITH (FORCE)"))
    admin.dispose()


def test_varios_procesos_arrancando_a_la_vez_crean_el_esquema_sin_errores(base_vacia):
    env = {**os.environ, "DATABASE_URL": base_vacia, "EJE2_PRECALENTAR": "0", "PYTHONPATH": f"{RAIZ}:{RAIZ / 'model'}"}
    procesos = [subprocess.Popen([sys.executable, "-c", "import app"], cwd=RAIZ, env=env, stderr=subprocess.PIPE, text=True) for _ in range(8)]
    resultados = [(p.wait(timeout=120), p.stderr.read()) for p in procesos]
    errores = [e[-400:] for code, e in resultados if code != 0]
    assert not errores, errores
    motor = create_engine(base_vacia)
    with motor.connect() as c:
        tablas = {r[0] for r in c.execute(text("SELECT relname FROM pg_class WHERE relkind IN ('r', 'p') AND relnamespace = 'public'::regnamespace"))}
        kinds = dict(c.execute(text("SELECT relname, relkind FROM pg_class WHERE relname IN ('reporte_seguridad', 'validacion_hora')")).all())
    motor.dispose()
    assert {"users", "feedback_viaje", "reporte_seguridad", "validacion_hora", "ajuste_riesgo_segmento", "pipeline_ejecucion"} <= tablas
    assert kinds == {"reporte_seguridad": "p", "validacion_hora": "p"}
