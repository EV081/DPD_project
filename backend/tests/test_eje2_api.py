"""API del Eje 2: accesos, ruta y reportes (con la base Postgres de pruebas y los datos reales exportados)."""
import datetime as dt

import pytest
from sqlalchemy import text

from eje2_real import origen_destino, punto_de_segmento, registrar_y_entrar, segmentos_distintos
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


@pytest.fixture(scope="module")
def ana(client):
    return registrar_y_entrar(client, "Ana", "ana@eje2.test")


@pytest.fixture(scope="module")
def beto(client):
    return registrar_y_entrar(client, "Beto", "beto@eje2.test")


@pytest.fixture(autouse=True)
def _limites_amplios(monkeypatch):
    """Por defecto los límites por usuario no estorban; las pruebas de límites los bajan."""
    monkeypatch.setenv("EJE2_REPORTES_POR_HORA", "50")
    monkeypatch.setenv("EJE2_REPORTES_POR_DIA", "200")


# --------------------------------------------------------------------------- estado y accesos
def test_estado_publico(client):
    d = client.get("/api/eje2/estado").get_json()
    assert d["datos_hasta"] == "2024-08-31" and d["lambda"] == 12.0 and d["n_segmentos"] == 146_607
    assert d["ajuste_por_reportes"]["parametros"]["min_usuarios"] == 2 and "105" in d["aviso"]
    assert "user" not in str(d).lower()                                 # nada de usuarios ni reportes individuales


def test_accesos_cercanos(client, g):
    a = g.accesos.iloc[10]
    d = client.get(f"/api/eje2/accesos/cercanos?lat={a['lat']}&lon={a['lon']}&radius=200").get_json()
    ids = [x["acceso_id"] for x in d["accesos"]]
    assert a["acceso_id"] in ids and all(x["distancia_m"] <= 200 for x in d["accesos"])
    uno = d["accesos"][0]
    assert {"seguridad_pct", "intervalo_pct", "base_tipo_pct", "confianza", "aviso"} <= set(uno) and 0 <= uno["seguridad_pct"] <= 100
    assert client.get("/api/eje2/accesos/cercanos?lat=x&lon=1").status_code == 400


def test_acceso_por_id_y_por_estacion(client):
    est = client.get("/api/stations?system=metro_l1").get_json()
    por_estacion = client.get(f"/api/eje2/accesos/por-estacion/{est[0]['id']}?sistema=metro_l1")
    assert por_estacion.status_code == 200 and por_estacion.get_json()["tipo"] == "metro_l1"
    acc = por_estacion.get_json()["acceso_id"]
    assert client.get(f"/api/eje2/accesos/{acc}").get_json()["acceso_id"] == acc
    assert client.get("/api/eje2/accesos/no_existe").status_code == 404
    assert client.get("/api/eje2/accesos/por-estacion/NOEXISTE").status_code == 404


# --------------------------------------------------------------------------- ruta
def test_ruta_es_publica_y_devuelve_ambas_rutas_y_la_explicacion(client, g):
    acc, (o,) = origen_destino(g, acceso=5)
    r = client.post("/api/eje2/ruta", json={"origen": o, "destino": {"acceso_id": acc}, "franja": "noche"})
    assert r.status_code == 200
    d = r.get_json()
    assert set(d["rutas"]) == {"normal", "segura"} and d["recomendada"] in ("segura", "normal", "misma") and d["seleccionada"] in ("segura", "normal")
    assert d["rutas"]["segura"]["geojson"]["geometry"]["type"] == "LineString"
    assert d["explicacion"]["llamar_105"] is True and d["explicacion"]["condiciones"]["datos_hasta"] == "2024-08-31"
    assert d["destino"]["acceso_id"] == acc and d["comparacion"]["distancia_extra_m"] >= 0


def test_ruta_la_preferencia_normal_no_cambia_lo_recomendado(client, g):
    acc, (o,) = origen_destino(g, acceso=5)
    seg = client.post("/api/eje2/ruta", json={"origen": o, "destino": {"acceso_id": acc}, "franja": "noche"}).get_json()
    nor = client.post("/api/eje2/ruta", json={"origen": o, "destino": {"acceso_id": acc}, "franja": "noche", "preferencia": "normal"}).get_json()
    assert seg["recomendada"] == nor["recomendada"] and nor["seleccionada"] in ("normal",) and seg["rutas"] == nor["rutas"]


def test_ruta_por_station_id(client, g):
    est = client.get("/api/stations?system=metro_l1").get_json()[3]
    a = client.get(f"/api/eje2/accesos/por-estacion/{est['id']}?sistema=metro_l1").get_json()
    _, (o,) = origen_destino(g, acceso=g.acc_indice[a["acceso_id"]])
    r = client.post("/api/eje2/ruta", json={"origen": o, "destino": {"station_id": est["id"], "sistema": "metro_l1"}})
    assert r.status_code == 200 and r.get_json()["destino"]["acceso_id"] == a["acceso_id"]


@pytest.mark.parametrize("cuerpo,estado", [
    ({"origen": {"lat": -12.2, "lon": -77.2}, "destino": {"acceso_id": "metro_l1_0000"}}, 422),
    ({"origen": {"lat": -12.05, "lon": -77.03}, "destino": {"acceso_id": "nada"}}, 404),
    ({"origen": {"lat": -12.05, "lon": -77.03}, "destino": {}}, 400),
    ({"origen": {}, "destino": {"acceso_id": "metro_l1_0000"}}, 400),
    ({"origen": {"lat": -12.05, "lon": -77.03}, "destino": {"acceso_id": "metro_l1_0000"}, "preferencia": "rapida"}, 400),
    ({"origen": {"lat": -12.05, "lon": -77.03}, "destino": {"acceso_id": "metro_l1_0000"}, "salida": "ayer"}, 400),
])
def test_ruta_errores(client, cuerpo, estado):
    assert client.post("/api/eje2/ruta", json=cuerpo).status_code == estado


# --------------------------------------------------------------------------- reportes
def test_reportar_exige_sesion(client, g):
    p = punto_de_segmento(g, segmentos_distintos(g, 1)[0])
    assert client.post("/api/eje2/reportes", json={"tipo": "robo", **p}).status_code == 401
    assert client.get("/api/eje2/reportes/mios").status_code == 401
    assert client.delete("/api/eje2/reportes/x").status_code == 401


@pytest.mark.parametrize("cambio,estado", [
    ({"tipo": "otro"}, 400), ({"tipo": ""}, 400), ({"lat": None}, 400), ({"lat": "x"}, 400),
    ({"lat": -12.2, "lon": -77.2}, 422),                                                   # lejos de cualquier calle cubierta
    ({"ocurrido_en": "mañana"}, 400),
    ({"ocurrido_en": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)).isoformat()}, 400),
    ({"ocurrido_en": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=30)).isoformat()}, 400),
])
def test_reporte_valida_la_entrada(client, g, ana, cambio, estado):
    base = {"tipo": "robo", **punto_de_segmento(g, segmentos_distintos(g, 1, seed=11)[0])}
    assert client.post("/api/eje2/reportes", json={**base, **cambio}, headers=ana).status_code == estado


def test_reporte_valido_responde_201_con_el_aviso_del_105(client, g, ana):
    s = segmentos_distintos(g, 1, seed=3)[0]
    r = client.post("/api/eje2/reportes", json={"tipo": "acoso", **punto_de_segmento(g, s)}, headers=ana)
    assert r.status_code == 201
    d = r.get_json()
    assert d["llamar_105"] is True and d["numero_emergencia"] == "105" and "105" in d["aviso"] and d["id"]
    assert d["franja"] in ("dia", "noche") and "agregada" in d["nota"]


@pytest.mark.parametrize("hora,franja", [("12:00:00-05:00", "dia"), ("22:30:00-05:00", "noche")])
def test_la_franja_sale_de_la_hora_en_que_ocurrio(client, g, beto, hora, franja):
    s = segmentos_distintos(g, 4, seed=5)[0 if franja == "dia" else 1]
    hoy = dt.datetime.now(E.calendario.TZ_LIMA).date()
    ocurrido = f"{hoy.isoformat()}T{hora}"
    if dt.datetime.fromisoformat(ocurrido) > dt.datetime.now(E.calendario.TZ_LIMA):         # si aún no llega esa hora, usar ayer
        ocurrido = f"{(hoy - dt.timedelta(days=1)).isoformat()}T{hora}"
    r = client.post("/api/eje2/reportes", json={"tipo": "robo", "ocurrido_en": ocurrido, **punto_de_segmento(g, s)}, headers=beto)
    assert r.status_code == 201 and r.get_json()["franja"] == franja


def test_no_se_puede_repetir_la_misma_calle_en_una_hora(client, g, ana):
    s = segmentos_distintos(g, 1, seed=21)[0]
    cuerpo = {"tipo": "seguimiento", **punto_de_segmento(g, s)}
    assert client.post("/api/eje2/reportes", json=cuerpo, headers=ana).status_code == 201
    r = client.post("/api/eje2/reportes", json=cuerpo, headers=ana)
    assert r.status_code == 429 and "Ya reportaste" in r.get_json()["error"]


def test_limite_de_reportes_por_hora(client, g, monkeypatch):
    monkeypatch.setenv("EJE2_REPORTES_POR_HORA", "3")
    h = registrar_y_entrar(client, "Carla", "carla@eje2.test")
    segs = segmentos_distintos(g, 5, seed=31)
    estados = [client.post("/api/eje2/reportes", json={"tipo": "robo", **punto_de_segmento(g, s)}, headers=h).status_code for s in segs]
    assert estados == [201, 201, 201, 429, 429]


def test_limite_de_reportes_por_dia(client, g, monkeypatch):
    monkeypatch.setenv("EJE2_REPORTES_POR_DIA", "2")
    h = registrar_y_entrar(client, "Dani", "dani@eje2.test")
    segs = segmentos_distintos(g, 3, seed=41)
    estados = [client.post("/api/eje2/reportes", json={"tipo": "robo", **punto_de_segmento(g, s)}, headers=h).status_code for s in segs]
    assert estados == [201, 201, 429]


def test_mis_reportes_son_solo_mios_y_se_pueden_retirar(client, g, ana, beto):
    s = segmentos_distintos(g, 1, seed=51)[0]
    rid = client.post("/api/eje2/reportes", json={"tipo": "robo", **punto_de_segmento(g, s)}, headers=ana).get_json()["id"]
    mios_ana = {r["id"] for r in client.get("/api/eje2/reportes/mios", headers=ana).get_json()["reportes"]}
    mios_beto = {r["id"] for r in client.get("/api/eje2/reportes/mios", headers=beto).get_json()["reportes"]}
    assert rid in mios_ana and rid not in mios_beto                                         # nadie ve reportes ajenos
    assert client.delete(f"/api/eje2/reportes/{rid}", headers=beto).status_code == 404       # Beto no puede retirar el de Ana
    assert client.delete(f"/api/eje2/reportes/{rid}", headers=ana).status_code == 200
    estado = {r["id"]: r["estado"] for r in client.get("/api/eje2/reportes/mios", headers=ana).get_json()["reportes"]}
    assert estado[rid] == "retirado"
    assert client.delete(f"/api/eje2/reportes/{rid}", headers=ana).status_code == 404         # ya retirado


def test_el_reporte_se_guarda_sin_texto_libre_y_con_coordenadas_redondeadas(client, g, ana, app_ctx):
    from db.connection import db
    s = segmentos_distintos(g, 1, seed=61)[0]
    p = punto_de_segmento(g, s)
    rid = client.post("/api/eje2/reportes", json={"tipo": "robo", "comentario": "Juan Pérez me robó", **p}, headers=ana).get_json()["id"]
    with app_ctx.app_context():
        fila = db.session.execute(text("SELECT lat, lon, tipo, seg_id FROM reporte_seguridad WHERE id = :i"), {"i": rid}).one()
        columnas = {r[0] for r in db.session.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'reporte_seguridad'")).all()}
        db.session.rollback()
    assert fila.lat == round(p["lat"], 5) and fila.lon == round(p["lon"], 5) and fila.seg_id and fila.tipo == "robo"
    assert not columnas & {"comentario", "descripcion", "texto", "nombre"}              # no hay dónde guardar texto libre ni nombres


def test_ninguna_respuesta_publica_expone_reportes_ni_usuarios(client, g, ana):
    acc, (o,) = origen_destino(g, acceso=7)
    textos = [client.get("/api/eje2/estado").get_data(as_text=True),
              client.post("/api/eje2/ruta", json={"origen": o, "destino": {"acceso_id": acc}}).get_data(as_text=True),
              client.get(f"/api/eje2/accesos/{acc}").get_data(as_text=True)]
    for t in textos:
        for prohibido in ("ana@eje2.test", "user_id", "reporte_id", '"email"'):
            assert prohibido not in t
