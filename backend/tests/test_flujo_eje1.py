"""Flujo del Eje 1 con el uso de la app (de punta a punta, con Postgres):

   los usuarios hacen "Ya abordé" -> se acumulan validaciones de la app por hora -> `pipeline-semanal` calcula las métricas y alertas
   y calibra el ETA (campeón vs retador) -> el ETA que ve el usuario cambia y lo declara -> sin respuestas nuevas no cambia nada.
"""
import datetime as dt

import pytest
from sqlalchemy import text

from eje2_real import registrar_y_entrar
from services import calendario, calibracion, monitoreo

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
def usuario(client):
    return registrar_y_entrar(client, "Elena", "elena@eje1.test")


def sql(app_ctx, consulta, **p):
    from db.connection import db
    with app_ctx.app_context():
        filas = db.session.execute(text(consulta), p).all()
        db.session.rollback()
    return filas


def agregar_feedback(app_ctx, sistema, n, real, mostrado=4.0, base=4.0, hace_dias=0.0, creado_en=None, percibido=None, aforo=None):
    """Inserta n 'Ya abordé' (con fecha controlada) sin pasar por la API, para simular semanas de uso."""
    from db.connection import db
    from routes.feedback import FeedbackViaje
    momento = creado_en or (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=hace_dias))
    with app_ctx.app_context():
        db.session.add_all(FeedbackViaje(station_id="Naranjal", sistema=sistema, espera_real_min=real, eta_mostrado_min=mostrado,
                                         eta_base_min=base, factor_trafico=1.0, modo_datos="historico", creado_en=momento,
                                         aforo_percibido=percibido, aforo_mostrado=aforo) for _ in range(n))
        db.session.commit()


def test_cada_ya_aborde_suma_una_validacion_de_la_app_en_su_hora(client, app_ctx, usuario):
    cuerpo = {"station_id": "Naranjal", "sistema": "troncal", "espera_real_min": 5.0, "eta_mostrado_min": 4.0}
    for _ in range(3):
        assert client.post("/api/feedback", json=cuerpo, headers=usuario).status_code == 201
    assert client.post("/api/feedback", json={**cuerpo, "station_id": "Gamarra", "sistema": "metro_l1"}, headers=usuario).status_code == 201
    hora = calendario.ahora_lima().replace(minute=0, second=0, microsecond=0, tzinfo=None)
    filas = sql(app_ctx, "SELECT sistema, serie, fecha_hora, n FROM validacion_hora WHERE fuente = 'app' ORDER BY serie")
    assert [(f.sistema, f.serie, f.fecha_hora, f.n) for f in filas] == [("metro_l1", "Gamarra", hora, 1), ("troncal", "Naranjal", hora, 3)]


def test_un_feedback_invalido_no_suma_validaciones(client, app_ctx, usuario):
    antes = sql(app_ctx, "SELECT coalesce(sum(n), 0) FROM validacion_hora")[0][0]
    assert client.post("/api/feedback", json={"station_id": "", "sistema": "troncal", "espera_real_min": 5}, headers=usuario).status_code == 400
    assert sql(app_ctx, "SELECT coalesce(sum(n), 0) FROM validacion_hora")[0][0] == antes


def test_pipeline_semanal_mide_alerta_y_calibra(client, app_ctx):
    hoy = calendario.ahora_lima().date()
    lunes_pasado = monitoreo.lunes_de(hoy) - dt.timedelta(days=7)
    miercoles = dt.datetime.combine(lunes_pasado + dt.timedelta(days=2), dt.time(12, 0), tzinfo=calendario.TZ_LIMA).astimezone(dt.timezone.utc)

    # corredores: la semana pasada esperaron 10 min con ETA de 4 (sesgo +6) y el aforo percibido casi nunca coincidió
    agregar_feedback(app_ctx, "corredores", 40, real=10.0, mostrado=4.0, creado_en=miercoles, percibido="Saturado", aforo="Asientos")
    # troncal: 150 respuestas antiguas (para ajustar) + 40 recientes (para validar) con esperas 40 % mayores que el ETA del modelo
    agregar_feedback(app_ctx, "troncal", 150, real=5.6, hace_dias=30)
    agregar_feedback(app_ctx, "troncal", 40, real=5.6, hace_dias=5)
    # Metro: muy pocas respuestas -> no se calibra ni alerta
    agregar_feedback(app_ctx, "metro_l1", 10, real=9.0, hace_dias=5)

    res = app_ctx.test_cli_runner().invoke(args=["pipeline-semanal"])
    assert res.exit_code == 0 and "pipeline-semanal: ok" in res.output, res.output

    mon = {f.sistema: f for f in sql(app_ctx, "SELECT sistema, alerta, motivo_alerta, eta_n, eta_sesgo_min FROM monitoreo_modelo")}
    assert mon["corredor"].alerta is True and "sesgo del ETA +6.0" in mon["corredor"].motivo_alerta and "acierto del aforo 0%" in mon["corredor"].motivo_alerta
    assert mon["corredor"].eta_n == 40

    cal = {f.sistema: f for f in sql(app_ctx, "SELECT sistema, estado, parametros, version FROM calibracion_modelo WHERE estado = 'campeon'")}
    assert set(cal) == {"troncal"}                                         # solo el sistema con ≥ 100 respuestas se calibra
    k = cal["troncal"].parametros["factor"]
    assert 1.15 < k <= 1.4                                                  # contraído hacia 1: 1 + 0,4·150/250 ≈ 1,24

    bit = sql(app_ctx, "SELECT estado FROM pipeline_ejecucion WHERE nombre = 'pipeline-semanal'")
    assert [b.estado for b in bit] == ["ok"]
    resumen = app_ctx.test_cli_runner().invoke(args=["monitoreo-resumen"]).output
    assert "corredor" in resumen and "ALERTA" in resumen


def test_el_eta_que_ve_el_usuario_incluye_la_calibracion_y_lo_declara(client, app_ctx, monkeypatch):
    from services import trafico
    with app_ctx.app_context():
        calibracion.invalidar()
        k = calibracion.factor_eta("troncal")
        assert k > 1.15
        item = trafico.ajustar_item({"eta_min": 4.0, "eta2_min": 8.0, "recommendation": "abordar"}, "troncal")
    assert item["factor_calibracion"] == pytest.approx(k, abs=1e-3)
    assert item["eta_min"] == pytest.approx(round(4.0 * k, 1)) and item["eta2_min"] == pytest.approx(round(8.0 * k, 1))
    assert item["eta_base_min"] == 4.0                                      # el ETA del modelo queda aparte (el cliente lo reenvía en el feedback)

    estacion = client.get("/api/stations?system=metropolitano").get_json()[0]
    d = client.get(f"/api/predictions/estacion/{estacion['id']}").get_json()
    assert d["current"]["factor_calibracion"] == pytest.approx(k, abs=1e-3)

    monkeypatch.setenv("ETA_CALIBRACION_ACTIVA", "0")                       # interruptor: vuelve el ETA puro del modelo
    calibracion.invalidar()
    with app_ctx.app_context():
        sin = trafico.ajustar_item({"eta_min": 4.0}, "troncal")
    assert sin["factor_calibracion"] == 1.0 and sin["eta_min"] == 4.0
    monkeypatch.undo()
    calibracion.invalidar()


def test_otros_sistemas_no_se_ven_afectados(app_ctx):
    from services import trafico
    with app_ctx.app_context():
        calibracion.invalidar()
        assert calibracion.factor_eta("metro_l1") == 1.0 and calibracion.factor_eta("corredor") == 1.0
        assert trafico.ajustar_item({"eta_min": 4.0}, "metro_l1")["eta_min"] == 4.0


def test_si_cambia_el_comportamiento_se_promueve_una_nueva_version_y_la_anterior_queda_archivada(app_ctx):
    from db.connection import db
    futuro = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=100)         # las respuestas anteriores ya salieron de la ventana
    agregar_feedback(app_ctx, "troncal", 150, real=3.4, creado_en=futuro - dt.timedelta(days=30))     # ahora esperan menos que el ETA
    agregar_feedback(app_ctx, "troncal", 40, real=3.4, creado_en=futuro - dt.timedelta(days=5))
    with app_ctx.app_context():
        r = calibracion.calibrar_eta("troncal", ahora=futuro)
        db.session.rollback()
    assert r["estado"] == "campeon" and r["k"] < 1.0 and r["mejora"] >= 0.05
    versiones = {f.version: f.estado for f in sql(app_ctx, "SELECT version, estado FROM calibracion_modelo WHERE sistema = 'troncal' ORDER BY version")}
    assert versiones[1] == "archivado" and versiones[r["version"]] == "campeon"          # se puede volver a la versión anterior
    assert list(versiones.values()).count("campeon") == 1


def test_repetir_el_pipeline_con_los_mismos_datos_no_cambia_nada(app_ctx):
    app_ctx.test_cli_runner().invoke(args=["pipeline-semanal"])                 # estabiliza: el campeón ya refleja los datos vigentes
    antes = sql(app_ctx, "SELECT version, estado FROM calibracion_modelo ORDER BY sistema, version")
    res = app_ctx.test_cli_runner().invoke(args=["pipeline-semanal"])
    assert res.exit_code == 0
    assert sql(app_ctx, "SELECT version, estado FROM calibracion_modelo ORDER BY sistema, version") == antes    # no se acumulan filas ni versiones


def test_sin_respuestas_nuevas_no_cambia_nada(app_ctx):
    from db.connection import db
    with app_ctx.app_context():
        db.session.execute(text("TRUNCATE TABLE feedback_viaje, monitoreo_modelo"))
        db.session.commit()
    antes = sql(app_ctx, "SELECT sistema, version, estado FROM calibracion_modelo ORDER BY sistema, version")
    res = app_ctx.test_cli_runner().invoke(args=["pipeline-semanal"])
    assert res.exit_code == 0 and "pipeline-semanal: sin_datos" in res.output
    assert sql(app_ctx, "SELECT sistema, version, estado FROM calibracion_modelo ORDER BY sistema, version") == antes
    assert sql(app_ctx, "SELECT count(*) FROM monitoreo_modelo")[0][0] == 0
    ultima = sql(app_ctx, "SELECT estado FROM pipeline_ejecucion WHERE nombre = 'pipeline-semanal' ORDER BY inicio DESC LIMIT 1")[0]
    assert ultima.estado == "sin_datos"


def test_el_pronostico_del_1_de_noviembre_sigue_respondiendo_con_el_homologo(client):
    r = client.get("/api/predictions/metro_l1/Gamarra?dia=2026-11-01&hour=8")
    assert r.status_code == 200
    d = r.get_json()
    assert d["datetime"] == "2026-11-01 08:00" and d["referencia"]["tipo_dia"] == "feriado"
    assert d["referencia"]["fecha_referencia_datos"] == "2025-11-01"                       # Todos los Santos: el mismo feriado de 2025
