"""Conteos reales de uso y límites de fecha del panel."""
import datetime as dt
import uuid

import pytest

pytestmark = pytest.mark.bd


@pytest.fixture(scope="module")
def app_():
    from app import app
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def sesiones(app_):
    from db.connection import db
    from routes.auth import User

    cliente = app_.test_client()
    for correo in ("uso-admin@test.com", "uso-estudiante@test.com"):
        respuesta = cliente.post("/api/auth/register", json={
            "name": "Prueba uso", "email": correo, "password": "TestUserPass_01",
        })
        assert respuesta.status_code == 201
    with app_.app_context():
        User.query.filter_by(email="uso-admin@test.com").update({"role": "admin"})
        db.session.commit()

    def acceso(correo):
        respuesta = cliente.post("/api/auth/login", json={"email": correo, "password": "TestUserPass_01"})
        assert respuesta.status_code == 200
        return {"Authorization": f"Bearer {respuesta.get_json()['access_token']}"}

    return cliente, acceso("uso-admin@test.com"), acceso("uso-estudiante@test.com")


def test_eventos_requieren_sesion_y_no_guardan_datos_personales(app_, sesiones):
    from db.tablas import EventoUso

    cliente, admin, estudiante = sesiones
    evento_id = str(uuid.uuid4())
    datos = {"tipo": "consulta", "sistema": "metro_l1", "evento_id": evento_id}
    assert cliente.post("/api/uso/eventos", json=datos).status_code == 401
    respuesta = cliente.post("/api/uso/eventos", json=datos, headers=estudiante)
    assert respuesta.status_code == 201 and respuesta.get_json() == {"registrado": True}
    repetido = cliente.post("/api/uso/eventos", json=datos, headers=estudiante)
    assert repetido.status_code == 200 and repetido.get_json() == {"registrado": False}
    with app_.app_context():
        fila = EventoUso.query.filter_by(id=evento_id).one()
        assert fila.tipo == "consulta" and fila.sistema == "metro_l1"
        assert all(c not in EventoUso.__table__.columns for c in ("user_id", "station_id", "lat", "lon"))
        assert EventoUso.query.count() == 1

    datos["evento_id"] = str(uuid.uuid4())
    datos["tipo"] = "recomendacion_vista"
    assert cliente.post("/api/uso/eventos", json=datos, headers=estudiante).status_code == 201
    panel = cliente.get("/api/admin/dashboard", headers=admin)
    assert panel.status_code == 200
    uso = panel.get_json()["uso"]
    assert uso["consultas_14d"] == 1 and uso["recomendaciones_14d"] == 1
    assert len(uso["consultas_por_dia"]) == len(uso["recomendaciones_por_dia"]) == 14
    assert sum(f["n"] for f in uso["consultas_por_dia"]) == 1


@pytest.mark.parametrize("cambio", [
    {"tipo": "compra"}, {"sistema": "taxi"}, {"evento_id": "no-es-uuid"},
    {"evento_id": str(uuid.uuid1())},
])
def test_evento_rechaza_valores_ajenos_al_catalogo(sesiones, cambio):
    cliente, _, estudiante = sesiones
    datos = {"tipo": "consulta", "sistema": "metro_l1", "evento_id": str(uuid.uuid4())}
    datos.update(cambio)
    assert cliente.post("/api/uso/eventos", json=datos, headers=estudiante).status_code == 400


def test_limite_por_cuenta_no_bloquea_un_reintento(sesiones, monkeypatch):
    from routes import uso

    cliente, _, estudiante = sesiones
    monkeypatch.setattr(uso, "MAX_EVENTOS_POR_VENTANA", 1)
    uso._ventanas.clear()
    datos = {"tipo": "consulta", "sistema": "metro_l1", "evento_id": str(uuid.uuid4())}
    try:
        assert cliente.post("/api/uso/eventos", json=datos, headers=estudiante).status_code == 201
        assert cliente.post("/api/uso/eventos", json=datos, headers=estudiante).status_code == 200
        datos["evento_id"] = str(uuid.uuid4())
        assert cliente.post("/api/uso/eventos", json=datos, headers=estudiante).status_code == 429
    finally:
        uso._ventanas.clear()


def test_ventana_diaria_usa_lima_entre_19_y_24_utc(app_):
    from db.connection import db
    from db.tablas import ValidacionHora
    from routes.admin import _uso

    with app_.app_context():
        db.session.add_all([
            ValidacionHora(fuente="app", sistema="metro_l1", serie="fuera", fecha_hora=dt.datetime(2026, 10, 29, 23), n=9),
            ValidacionHora(fuente="app", sistema="metro_l1", serie="inicio", fecha_hora=dt.datetime(2026, 10, 30, 0), n=2),
            ValidacionHora(fuente="app", sistema="metro_l1", serie="hoy", fecha_hora=dt.datetime(2026, 11, 12, 20), n=3),
        ])
        db.session.commit()
        # 01:00 UTC del 13 de noviembre sigue siendo 20:00 del 12 en Lima.
        uso = _uso(dt.datetime(2026, 11, 13, 1, tzinfo=dt.timezone.utc))
        assert uso["abordajes_por_dia"][0] == {"fecha": "2026-10-30", "n": 2}
        assert uso["abordajes_por_dia"][-1] == {"fecha": "2026-11-12", "n": 3}
        assert sum(f["n"] for f in uso["abordajes_por_dia"]) == 5
        antes = _uso(dt.datetime(2026, 11, 13, 4, 59, tzinfo=dt.timezone.utc))
        despues = _uso(dt.datetime(2026, 11, 13, 5, tzinfo=dt.timezone.utc))
        assert antes["abordajes_por_dia"][-1]["fecha"] == "2026-11-12"  # 23:59 en Lima
        assert despues["abordajes_por_dia"][-1]["fecha"] == "2026-11-13"  # 00:00 en Lima


def test_resumen_feedback_agrupado_conserva_el_contrato(app_):
    from db.connection import db
    from routes.feedback import FeedbackViaje, MODOS, _resumen, _resumen_desde_bd

    with app_.app_context():
        db.session.add_all([
            FeedbackViaje(station_id="A", sistema="metro_l1", espera_real_min=7, eta_mostrado_min=5,
                          modo_datos="en_vivo", aforo_mostrado="Asientos", aforo_percibido="Asientos"),
            FeedbackViaje(station_id="B", sistema="metro_l1", espera_real_min=4, eta_mostrado_min=5,
                          modo_datos="reciente", aforo_mostrado="Asientos", aforo_percibido="De_pie"),
            FeedbackViaje(station_id="C", sistema="metro_l1", espera_real_min=6),
        ])
        db.session.commit()
        filas = FeedbackViaje.query.all()
        esperado = {**_resumen(filas), "por_modo_datos": {m: _resumen([f for f in filas if f.modo_datos == m]) for m in MODOS}}
        assert _resumen_desde_bd() == esperado
