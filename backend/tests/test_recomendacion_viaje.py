"""Orden de las rutas de /api/geo/match-trip por costo generalizado y servicio del Metropolitano a tomar
(datos reales, sin base de datos).

Antes, las rutas del Metropolitano, el Metro L1 y los alimentadores no encontraban su estación (se
buscaba con el código de ruta, que solo tienen los corredores), quedaban sin costo y cualquier corredor
les ganaba aunque estuviera a cinco cuadras.
"""
import datetime as dt

import pytest
from flask import Flask

from routes.geo import geo_bp
from services import calendario
from services import horarios as H
from services import recomendacion_viaje as RV

CANAVAL = (-12.09635, -77.02520)          # Estación Canaval y Moreyra (Metropolitano)
UTEC = (-12.1351351, -77.0221296)
JUNTO_A_ESPANA = (-12.0578, -77.0390)     # Cercado, a ~90 m de la Estación España
JUNTO_AL_301 = (-12.0905, -77.0335)       # Av. Arequipa, junto a un paradero del 301 y lejos del Metropolitano
LUNES_7AM = dt.datetime(2025, 11, 17, 7, 0, tzinfo=calendario.TZ_LIMA)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(calendario, "ahora_lima", lambda: LUNES_7AM)   # día hábil: los expresos operan
    app = Flask(__name__)
    app.register_blueprint(geo_bp, url_prefix="/api/geo")
    return app.test_client()


def viaje(client, origen, destino, hora=8):
    r = client.get("/api/geo/match-trip", query_string={
        "origin_lat": origen[0], "origin_lon": origen[1], "dest_lat": destino[0], "dest_lon": destino[1],
        "radius": 1000, "hour": hora})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def test_desde_una_estacion_del_metropolitano_no_recomienda_un_corredor_a_cinco_cuadras(client):
    res = viaje(client, CANAVAL, UTEC)
    mejor = res["found_routes"][0]
    assert mejor["system"] == "metropolitano" and mejor["boarding_station"] == "Canaval y Moreyra"
    assert mejor["costo_generalizado_min"] is not None
    assert mejor["servicio_troncal"]["texto"]
    assert res["recomendacion_viaje"]["mejor"]["servicio"].startswith("Metropolitano · ")


def test_hacia_cercado_recomienda_el_expreso_que_para_en_espana(client):
    mejor = viaje(client, CANAVAL, JUNTO_A_ESPANA)["found_routes"][0]
    assert (mejor["system"], mejor["boarding_station"], mejor["leaving_station"]) == (
        "metropolitano", "Canaval y Moreyra", "España")
    # cada servicio nombrado para en ambas estaciones, en ese orden, y opera a esa hora
    momento = dt.datetime(2025, 11, 17, 8, 30)
    sentido = mejor["servicio_troncal"]["sentido"]
    for tramo in mejor["servicio_troncal"]["tramos"]:
        for s in tramo["servicios"]:
            paradas = H.servicio("troncal", s["nombre"])["paradas"][sentido]
            assert paradas.index(tramo["sube"]) < paradas.index(tramo["baja"])
            assert H.opera(H.servicio("troncal", s["nombre"]), sentido, momento)


def test_el_metropolitano_y_el_metro_evaluados_siempre_encuentran_su_estacion(client):
    for destino in (UTEC, JUNTO_A_ESPANA):
        for r in viaje(client, CANAVAL, destino)["found_routes"]:
            if "caminata_min" in r and r["system"] in ("metropolitano", "metro_l1"):
                assert not r.get("sin_prediccion"), r


def test_junto_a_un_paradero_del_corredor_gana_el_corredor(client):
    # el arreglo no invierte el sesgo: si el corredor está al lado y el Metropolitano lejos, gana el corredor
    mejor = viaje(client, JUNTO_AL_301, JUNTO_A_ESPANA)["found_routes"][0]
    assert mejor["system"] == "corredores" and mejor["costo_generalizado_min"] is not None


@pytest.mark.parametrize("hora", [8, 18, 22, 23])
def test_solo_ofrece_servicios_que_operan_a_esa_hora(client, hora):
    for r in viaje(client, CANAVAL, JUNTO_A_ESPANA, hora=hora)["found_routes"]:
        troncal = r.get("servicio_troncal")
        for tramo in (troncal or {}).get("tramos", []):
            for s in tramo["servicios"]:
                assert H.opera(H.servicio("troncal", s["nombre"]), troncal["sentido"],
                               dt.datetime(2025, 11, 17, hora, 30)), (hora, s)


def test_las_candidatas_incluyen_cada_sistema_aunque_otro_tenga_muchos_pares_cercanos():
    corredor = [{"system": "corredores", "route_code": "301", "origin_walk_m": 10 + i, "dest_walk_m": 10}
                for i in range(20)]
    metro = {"system": "metropolitano", "route_code": "METROPOLITANO", "origin_walk_m": 900, "dest_walk_m": 50}
    elegidas = list(RV._candidatas(corredor + [metro]))
    assert metro in elegidas and len(elegidas) == RV.MAX_CANDIDATAS


def test_un_sentido_contrario_no_cubre_su_ruta():
    # la primera del 301 va en el sentido contrario: se evalúa la siguiente del 301 antes de rellenar
    rutas = [{"system": "corredores", "route_code": "301", "origin_walk_m": 1, "dest_walk_m": 1},
             {"system": "corredores", "route_code": "305", "origin_walk_m": 2, "dest_walk_m": 1},
             {"system": "corredores", "route_code": "301", "origin_walk_m": 3, "dest_walk_m": 1}]
    gen, vistas = RV._candidatas(rutas), []
    for r in gen:
        if not vistas:
            r["sentido_contrario"] = True
        vistas.append(r)
    assert vistas == rutas


def test_texto_del_servicio_con_cambio_de_servicio():
    tramos = [{"servicio": "Expreso 1", "baja": "Estacion Central"}, {"servicio": "Ruta B", "baja": "España"}]
    assert RV._texto_servicio(tramos) == "Expreso 1 hasta Estacion Central, luego Ruta B"
    assert RV._texto_servicio(tramos[:1]) == "Expreso 1"
