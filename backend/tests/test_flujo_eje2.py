"""Flujo completo del Eje 2 (de punta a punta, con Postgres y datos reales):

   usuarios reportan -> `flask eje2-recalibrar` -> el riesgo de la zona sube y la ruta lo refleja ->
   pasa el tiempo -> el ajuste desaparece solo y todo vuelve a lo que dice el modelo.
"""
import datetime as dt

import pytest
from sqlalchemy import text

from eje2_real import origen_destino, punto_de_segmento, registrar_y_entrar
from services import eje2_reportes as R
from services import eje2_service as E

pytestmark = pytest.mark.bd


@pytest.fixture(scope="module")
def app_ctx():
    from app import app
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def client(app_ctx):
    return app_ctx.test_client()


@pytest.fixture(scope="module")
def g():
    return E.grafo()


def anoche_a_las_22() -> str:
    """Una hora de la noche que cae dentro de las últimas 24 h (para que el reporte sea de la franja 'noche')."""
    ahora = dt.datetime.now(E.calendario.TZ_LIMA)
    f = ahora.replace(hour=22, minute=0, second=0, microsecond=0)
    if f > ahora:
        f -= dt.timedelta(days=1)
    return f.isoformat()


def ruta(client, o, acc, franja):
    r = client.post("/api/eje2/ruta", json={"origen": o, "destino": {"acceso_id": acc}, "franja": franja})
    assert r.status_code == 200
    return r.get_json()


def test_los_reportes_recalibran_la_zona_y_el_tiempo_la_devuelve_a_su_valor(client, app_ctx, g):
    from db.connection import db
    acc, (origen,) = origen_destino(g, acceso=4, seed=2)

    # 1) estado inicial: sin reportes, sin ajustes
    R.ajustes.invalidar()
    antes_noche, antes_dia = ruta(client, origen, acc, "noche"), ruta(client, origen, acc, "dia")
    assert antes_noche["explicacion"]["condiciones"]["reportes_aplicados"] is False
    assert client.get("/api/eje2/estado").get_json()["ajuste_por_reportes"]["segmentos_ajustados"] == 0

    # 2) tres personas distintas reportan en la misma calle de la ruta normal (de noche)
    o, _ = g.nodo_cercano(origen["lat"], origen["lon"])
    d = int(g.acc_nodo[g.acc_indice[acc]])
    segs, _nodos = g.camino(o, d, g.largo, E.ALCANCE_MAX_M)
    punto = punto_de_segmento(g, int(segs[len(segs) // 2]))
    for i in range(3):
        h = registrar_y_entrar(client, f"Vecina {i}", f"vecina{i}@flujo.test")
        r = client.post("/api/eje2/reportes", json={"tipo": "acoso", "ocurrido_en": anoche_a_las_22(), **punto}, headers=h)
        assert r.status_code == 201, r.get_json()
        assert r.get_json()["franja"] == "noche" and r.get_json()["llamar_105"] is True

    # 3) el job de recalibración (el mismo comando que corre el cron)
    res = app_ctx.test_cli_runner().invoke(args=["eje2-recalibrar"])
    assert res.exit_code == 0 and "ajustes" in res.output and "ajustes: 0" not in res.output

    # 4) la ruta lo refleja: más riesgo en la ruta normal, solo en la franja de los reportes, y la explicación lo dice
    despues_noche, despues_dia = ruta(client, origen, acc, "noche"), ruta(client, origen, acc, "dia")
    assert despues_noche["explicacion"]["condiciones"]["reportes_aplicados"] is True
    assert despues_noche["rutas"]["normal"]["riesgo_medio"] > antes_noche["rutas"]["normal"]["riesgo_medio"]
    assert despues_dia["rutas"]["normal"]["riesgo_medio"] == antes_dia["rutas"]["normal"]["riesgo_medio"]
    est = client.get("/api/eje2/estado").get_json()["ajuste_por_reportes"]
    assert est["segmentos_ajustados"] > 0 and est["actualizado_en"]

    # la bitácora del job quedó registrada
    with app_ctx.app_context():
        filas = db.session.execute(text("SELECT nombre, estado FROM pipeline_ejecucion WHERE nombre = 'eje2-recalibrar'")).all()
        db.session.rollback()
    assert filas and filas[-1].estado == "ok"

    # 5) pasan 120 días sin nuevos reportes: el ajuste desaparece solo y vuelve el valor del modelo
    with app_ctx.app_context():
        R.recalibrar(ahora=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=120))
    final = ruta(client, origen, acc, "noche")
    assert final["rutas"]["normal"]["riesgo_medio"] == antes_noche["rutas"]["normal"]["riesgo_medio"]
    assert final["explicacion"]["condiciones"]["reportes_aplicados"] is False
    assert client.get("/api/eje2/estado").get_json()["ajuste_por_reportes"]["segmentos_ajustados"] == 0


def test_el_interruptor_apaga_el_efecto_de_los_reportes_sin_perderlos(client, app_ctx, g, monkeypatch):
    acc, (origen,) = origen_destino(g, acceso=6, seed=4)
    o, _ = g.nodo_cercano(origen["lat"], origen["lon"])
    segs, _ = g.camino(o, int(g.acc_nodo[g.acc_indice[acc]]), g.largo, E.ALCANCE_MAX_M)
    punto = punto_de_segmento(g, int(segs[len(segs) // 2]))
    for i in range(3):
        h = registrar_y_entrar(client, f"Otra {i}", f"otra{i}@flujo.test")
        assert client.post("/api/eje2/reportes", json={"tipo": "robo", "ocurrido_en": anoche_a_las_22(), **punto}, headers=h).status_code == 201
    R.ajustes.invalidar()
    base = ruta(client, origen, acc, "noche")["rutas"]["normal"]["riesgo_medio"]
    with app_ctx.app_context():
        assert R.recalibrar()["ajustes"] > 0
    con = ruta(client, origen, acc, "noche")["rutas"]["normal"]["riesgo_medio"]
    assert con > base
    monkeypatch.setenv("EJE2_AJUSTE_ACTIVO", "0")
    R.ajustes.invalidar()
    assert ruta(client, origen, acc, "noche")["rutas"]["normal"]["riesgo_medio"] == base               # apagado: usa solo el modelo
    monkeypatch.setenv("EJE2_AJUSTE_ACTIVO", "1")
    R.ajustes.invalidar()
    assert ruta(client, origen, acc, "noche")["rutas"]["normal"]["riesgo_medio"] == con                 # los ajustes no se perdieron


def test_pipeline_diario_deja_particiones_y_bitacora(app_ctx):
    from db.connection import db
    res = app_ctx.test_cli_runner().invoke(args=["pipeline-diario"])
    assert res.exit_code == 0 and "pipeline-diario ok" in res.output
    res = app_ctx.test_cli_runner().invoke(args=["db-particiones", "--adelante", "4"])
    assert res.exit_code == 0 and '"creadas"' in res.output
    with app_ctx.app_context():
        nombres = {r[0] for r in db.session.execute(text("SELECT DISTINCT nombre FROM pipeline_ejecucion")).all()}
        db.session.rollback()
    assert {"pipeline-diario", "db-particiones"} <= nombres
