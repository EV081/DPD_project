"""Horarios por servicio, aforo dentro de la hora y hora de salida para llegar a tiempo (sin base de datos)."""
import datetime as dt

import pytest
from flask import Flask

from routes.predictions import predictions_bp
from routes.stations import load_all_stations_into_memory
from services import horarios as H
from services import model_service as MS
from services import planificador_salida as P

LUNES, SABADO, DOMINGO = "2025-11-17", "2025-11-15", "2025-11-16"


def momento(dia: str, hhmm: str) -> dt.datetime:
    return dt.datetime.fromisoformat(f"{dia}T{hhmm}")


def estacion(nombre: str, sistema: str = "metropolitano") -> dict:
    return next(s for s in load_all_stations_into_memory() if s["system"] == sistema and s["name"] == nombre)


@pytest.fixture(scope="module")
def client():
    app = Flask(__name__)
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")
    return app.test_client()


# --------------------------------------------------------------------------- horarios
def test_tipo_dia_trata_el_feriado_como_domingo():
    assert H.tipo_dia(dt.date(2025, 11, 17)) == "LAB"
    assert H.tipo_dia(dt.date(2025, 11, 15)) == "SAB"
    assert H.tipo_dia(dt.date(2025, 11, 16)) == "DOM"
    assert H.tipo_dia(dt.date(2025, 12, 8)) == "DOM"      # Inmaculada Concepción cae lunes


def test_cada_sistema_del_modelo_tiene_horarios():
    assert set(MS.series_modelo("alimentador")) == set(H.servicios("alimentador"))
    assert set(MS.series_modelo("corredor")) == set(H.servicios("corredor"))
    assert H.servicio("metro_l1", "Gamarra") is H.servicios("metro_l1")["Línea 1"]
    assert H.servicio("troncal", "Expreso 5") is H.servicios("metropolitano")["Expreso 5"]


def test_las_paradas_del_metropolitano_son_estaciones_del_modelo_en_orden():
    estaciones = MS.modelo("troncal").linea.estaciones
    for nombre, reg in H.servicios("metropolitano").items():
        for sentido, paradas in reg["paradas"].items():
            assert set(paradas) <= set(estaciones), nombre
            indices = [estaciones.index(p) for p in paradas]
            assert indices == sorted(indices, reverse=sentido == "desc"), (nombre, sentido)


def test_expreso_de_la_manana_no_opera_en_la_tarde_ni_el_sabado():
    exp6 = H.servicio("troncal", "Expreso 6")
    assert H.opera(exp6, "desc", momento(LUNES, "07:00")) is True
    assert H.opera(exp6, "desc", momento(LUNES, "15:00")) is False
    assert H.opera(exp6, "desc", momento(SABADO, "07:00")) is False
    assert H.opera(exp6, "asc", momento(LUNES, "07:00")) is False       # solo circula hacia el sur


def test_el_limite_del_horario_es_abierto_al_cierre():
    exp5 = H.servicio("troncal", "Expreso 5")
    assert H.opera(exp5, "desc", momento(LUNES, "09:00")) is True
    assert H.opera(exp5, "desc", momento(LUNES, "16:59")) is True
    assert H.opera(exp5, "desc", momento(LUNES, "17:00")) is False


def test_servicio_que_cruza_la_medianoche():
    lechucero = H.servicio("troncal", "Lechucero")
    jueves, viernes, miercoles = "2025-11-20", "2025-11-21", "2025-11-19"
    assert H.opera(lechucero, "asc", momento(jueves, "23:45")) is True
    assert H.opera(lechucero, "asc", momento(viernes, "02:00")) is True   # turno que empezó el jueves
    assert H.opera(lechucero, "asc", momento(viernes, "05:00")) is False
    assert H.opera(lechucero, "asc", momento(miercoles, "23:45")) is False
    ruta301 = H.servicio("corredor", "301")                               # cierra a las 00:00
    assert H.opera(ruta301, None, momento(LUNES, "23:30")) is True
    assert H.opera(ruta301, None, momento(LUNES, "03:00")) is False


def test_ruta_sin_horario_publicado_devuelve_none():
    assert H.opera(H.servicio("corredor", "206"), None, momento(LUNES, "10:00")) is None
    assert H.texto_horario(H.servicio("corredor", "206"), None, dt.date(2025, 11, 17)) is None


def test_intervalo_distingue_punta_y_valle():
    alisos = H.servicio("alimentador", "Alisos")
    assert H.intervalo_min(alisos, momento(LUNES, "07:10")) == 7.5
    assert H.intervalo_min(alisos, momento(LUNES, "11:00")) == 16.0
    exp1 = H.servicio("troncal", "Expreso 1")
    assert H.intervalo_min(exp1, momento(LUNES, "18:00")) == 5.0
    assert H.intervalo_min(exp1, momento(LUNES, "11:00")) == 5.0           # valle calibrado (fuente solo punta)
    assert H.intervalo_min(H.servicio("troncal", "Ruta C"), momento(LUNES, "18:00")) == 5.0
    assert H.intervalo_min(H.servicio("troncal", "Ruta A"), momento(LUNES, "18:00")) == 5.0
    assert H.intervalo_min(H.servicio("troncal", "Expreso 5"), momento(LUNES, "12:00")) == 5.0


# --------------------------------------------------------------------------- aforo dentro de la hora
def test_interpolar_ancla_cada_hora_en_su_minuto_30():
    v = [None] * 24
    v[15], v[16] = 0.2, 0.8
    assert P.interpolar(v, 15 * 60 + 30) == pytest.approx(0.2)
    assert P.interpolar(v, 16 * 60 + 30) == pytest.approx(0.8)
    assert P.interpolar(v, 16 * 60) == pytest.approx(0.5)                  # a medio camino entre las dos anclas
    assert P.interpolar(v, 15 * 60 + 50) == pytest.approx(0.4)             # 1/3 del camino


def test_interpolar_no_inventa_donde_no_hay_servicio():
    v = [None] * 24
    v[5] = 0.3
    assert P.interpolar(v, 4 * 60 + 50) is None                            # la hora 4 no tiene servicio
    assert P.interpolar(v, 5 * 60 + 10) == pytest.approx(0.3)              # la vecina sin dato no arrastra el valor
    assert P.interpolar([0.1] * 24, 5) == pytest.approx(0.1)               # antes de las 00:30
    assert P.interpolar([0.1] * 24, 23 * 60 + 55) == pytest.approx(0.1)


def test_clase_usa_los_umbrales_del_vehiculo():
    veh = MS.modelo("troncal").linea.veh                                   # 164 de capacidad, 47 asientos
    assert veh.capacidad == 164 and veh.asientos == 47
    assert P.clase_de(47 / 164, veh) == "Asientos"
    assert P.clase_de(48 / 164, veh) == "De_pie"
    assert P.clase_de(0.9, veh) == "Saturado"


# --------------------------------------------------------------------------- tiempo por servicio
def test_el_expreso_tarda_menos_que_el_regular_pero_no_mas_rapido_que_el_crucero():
    linea = MS.modelo("troncal").linea
    regular = H.servicio("troncal", "Ruta C")["paradas"]["asc"]
    expreso = H.servicio("troncal", "Expreso 1")["paradas"]["asc"]
    t_regular, n_regular = P._viaje_servicio(linea, "Matellini", "Javier Prado", regular)
    t_expreso, n_expreso = P._viaje_servicio(linea, "Matellini", "Javier Prado", expreso)
    km = dict(zip(linea.estaciones, linea.cfg["km"]))
    dist = abs(km["Matellini"] - km["Javier Prado"])
    assert n_expreso < n_regular and t_expreso < t_regular
    sin_tope = t_regular - P.AHORRO_PARADA_MIN * (n_regular - n_expreso)
    assert t_expreso == pytest.approx(max(sin_tope, dist / P.VEL_CRUCERO_KMH * 60))
    assert t_expreso >= dist / P.VEL_CRUCERO_KMH * 60
    assert t_regular <= dist / linea.cfg["velocidad_comercial_kmh"] * 60 + 1e-9


def test_el_regular_no_gana_tiempo_por_el_ramal_del_centro_que_no_recorre():
    linea = MS.modelo("troncal").linea
    paradas = H.servicio("troncal", "Ruta C")["paradas"]["asc"]
    km = dict(zip(linea.estaciones, linea.cfg["km"]))
    t, _ = P._viaje_servicio(linea, "Estacion Central", "Ramon Castilla", paradas)
    assert t == pytest.approx(abs(km["Estacion Central"] - km["Ramon Castilla"]) / linea.cfg["velocidad_comercial_kmh"] * 60)


# --------------------------------------------------------------------------- planificador
def minutos(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


def test_la_recomendada_llega_a_tiempo_con_margen_para_perder_un_vehiculo():
    plan = P.planificar(estacion("Naranjal"), estacion("Angamos"), LUNES, "16:00")
    rec = next(o for o in plan["opciones"] if o["salida"] == plan["recomendada"])
    assert rec["estado"] == "con_margen" and rec["margen_min"] >= rec["intervalo_min"]
    assert minutos(rec["llegada"]) <= 16 * 60
    assert rec["tramos"][0]["servicio"] == "Expreso 5"                    # único directo que opera a esa hora
    assert plan["tipo_dia"] == "LAB" and plan["sentido"].startswith("hacia el sur")
    assert plan["fuente_horarios"]["nombre"] == "metrolima.info"


def test_las_opciones_son_coherentes():
    plan = P.planificar(estacion("Naranjal"), estacion("Angamos"), LUNES, "16:00")
    salidas = [minutos(o["salida"]) for o in plan["opciones"]]
    assert salidas == sorted(salidas) and all(s % P.PASO_MIN == 0 for s in salidas)
    for o in plan["opciones"]:
        assert o["margen_min"] == pytest.approx(16 * 60 - (minutos(o["salida"]) + o["espera_min"] + o["viaje_min"]), abs=0.25)
        assert (o["estado"] == "tarde") == (o["margen_min"] < 0)
        assert o["clase"] in ("Asientos", "De_pie", "Saturado") and o["ocupacion"] >= 0
    assert sum(o["estado"] == "tarde" for o in plan["opciones"]) <= 2
    assert minutos(plan["recomendada"]) <= minutos(plan["ultima_puntual"])


def test_sin_servicio_directo_arma_un_transbordo():
    plan = P.planificar(estacion("Naranjal"), estacion("Angamos"), DOMINGO, "11:00")
    rec = next(o for o in plan["opciones"] if o["salida"] == plan["recomendada"])
    assert len(rec["tramos"]) == 2 and rec["tramos"][0]["baja"] == rec["tramos"][1]["sube"]
    assert rec["espera_min"] == pytest.approx(sum(t["espera_min"] for t in rec["tramos"]), abs=0.11)
    assert all(not s["opera"] for s in plan["servicios"])                  # los directos no operan el domingo


def test_antes_del_primer_servicio_no_hay_recomendacion():
    plan = P.planificar(estacion("Naranjal"), estacion("Angamos"), LUNES, "04:30")
    assert plan["recomendada"] is None and plan["opciones"] == []
    assert "No hay servicio" in plan["motivo"]


def test_metro_l1_y_dia_futuro_usan_el_dia_homologo():
    plan = P.planificar(estacion("Villa El Salvador", "metro_l1"), estacion("Gamarra", "metro_l1"), "2026-11-12", "08:00")
    assert plan["recomendada"] and plan["referencia"]["fecha_referencia_datos"].startswith("2025-")
    assert plan["servicios"][0]["nombre"] == "Línea 1" and plan["servicios"][0]["opera"] is True
    assert plan["opciones"][0]["tramos"] is None


@pytest.mark.parametrize("origen, destino, mensaje", [
    (("Naranjal", "metropolitano"), ("Naranjal", "metropolitano"), "coincide"),
    (("Naranjal", "metropolitano"), ("Gamarra", "metro_l1"), "mismo sistema"),
])
def test_pares_invalidos(origen, destino, mensaje):
    with pytest.raises(MS.PrediccionError, match=mensaje) as e:
        P.planificar(estacion(*origen), estacion(*destino), LUNES, "16:00")
    assert e.value.status == 422


def test_corredor_rechaza_el_paradero_del_sentido_contrario():
    sentido = next(iter(MS.modelo("corredor").linea.rutas["301"]["sentidos"].values()))
    por_codigo = {s["raw_properties"].get("cod_paradero"): s for s in load_all_stations_into_memory()
                  if s["system"] == "corredores" and str(s["raw_properties"].get("ruta")) == "301"}
    a, b = por_codigo[sentido["paradas"][3]], por_codigo[sentido["paradas"][20]]
    assert P.planificar(a, b, LUNES, "18:30")["recomendada"]
    with pytest.raises(MS.PrediccionError, match="sentido contrario"):
        P.planificar(b, a, LUNES, "18:30")


# --------------------------------------------------------------------------- API
def test_api_viaje(client):
    r = client.get("/api/predictions/viaje", query_string={
        "origen_id": "Naranjal", "destino_id": "Angamos", "dia": LUNES, "llegada": "16:00"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["recomendada"] and d["llegada_limite"] == "16:00" and d["supuestos"] and d["seguridad"]["franja_salida"] == "dia"


def test_api_viaje_alimentador_elige_el_paradero_por_nombre(client):
    r = client.get("/api/predictions/viaje", query_string={
        "origen_id": "AN-15", "origen_nombre": "Maracuyá", "destino_id": "AN-15", "destino_nombre": "Huandoy",
        "dia": LUNES, "llegada": "07:30"})
    assert r.status_code == 200
    d = r.get_json()
    assert d["origen"]["name"] == "Maracuyá" and d["destino"]["name"] == "Huandoy" and d["recomendada"]


@pytest.mark.parametrize("params, status", [
    ({"origen_id": "Naranjal"}, 400),
    ({"origen_id": "Naranjal", "destino_id": "Angamos", "llegada": "25:00"}, 400),
    ({"origen_id": "Naranjal", "destino_id": "Angamos", "llegada": "las cuatro"}, 400),
    ({"origen_id": "Naranjal", "destino_id": "Angamos", "llegada": "16:00", "dia": "ayer"}, 400),
    ({"origen_id": "no-existe", "destino_id": "Angamos", "llegada": "16:00"}, 404),
    ({"origen_id": "Naranjal", "destino_id": "Naranjal", "llegada": "16:00"}, 422),
])
def test_api_viaje_errores(client, params, status):
    r = client.get("/api/predictions/viaje", query_string=params)
    assert r.status_code == status and r.get_json()["error"]


# --------------------------------------------------------------------------- próximas salidas (mapa)
def test_proximas_salidas_empiezan_en_el_siguiente_multiplo_de_10():
    ahora = momento(LUNES, "15:25")
    d = P.proximas_salidas(estacion("Naranjal"), estacion("Angamos"), ahora)
    assert [o["salida"] for o in d["proximas_salidas"]] == ["15:30", "15:40", "15:50", "16:00", "16:10", "16:20"]
    assert d["ahora"]["hora"] == "15:25" and d["ahora"]["class"] in ("Asientos", "De_pie", "Saturado")
    for o in d["proximas_salidas"]:
        assert minutos(o["llegada"]) == pytest.approx(minutos(o["salida"]) + o["espera_min"] + o["viaje_min"], abs=1)
        assert o["tramos"] and "_exacto" not in o and "margen_min" not in o


def test_el_aforo_de_ahora_queda_entre_las_dos_horas_vecinas():
    horas = MS.prediccion_serie("troncal", "Naranjal", LUNES, hacia="Angamos")["filas"]
    a, b = horas[15]["ocupacion_desc"], horas[16]["ocupacion_desc"]
    d = P.proximas_salidas(estacion("Naranjal"), estacion("Angamos"), momento(LUNES, "15:50"))
    assert min(a, b) - 1e-3 <= d["ahora"]["crowding"] <= max(a, b) + 1e-3
    assert d["ahora"]["crowding"] == pytest.approx(a + (b - a) / 3, abs=1e-3)


def test_proximas_salidas_sin_destino_no_inventan_llegada():
    d = P.proximas_salidas(estacion("Naranjal"), None, momento(LUNES, "15:25"))
    assert len(d["proximas_salidas"]) == 6
    assert all(o["llegada"] is None and o["viaje_min"] is None and o["tramos"] is None for o in d["proximas_salidas"])


def test_proximas_salidas_saltan_las_horas_sin_servicio_y_no_pasan_de_medianoche():
    d = P.proximas_salidas(estacion("Naranjal"), estacion("Angamos"), momento(LUNES, "03:00"))
    assert d["ahora"] is None                                              # de madrugada no hay servicio
    assert d["proximas_salidas"] and minutos(d["proximas_salidas"][0]["salida"]) >= 5 * 60
    tarde = P.proximas_salidas(estacion("Naranjal"), None, momento(LUNES, "23:45"))
    assert all(minutos(o["salida"]) >= 23 * 60 + 50 for o in tarde["proximas_salidas"]) and len(tarde["proximas_salidas"]) <= 1


def test_la_espera_de_la_hora_actual_se_puede_corregir_con_trafico():
    est = estacion("Villa El Salvador", "metro_l1")
    d = P.proximas_salidas(est, estacion("Gamarra", "metro_l1"), momento(LUNES, "07:35"), esperas={7: 9.0})
    por_hora = {o["salida"]: o["espera_min"] for o in d["proximas_salidas"]}
    assert por_hora["07:40"] == 9.0 and por_hora["07:50"] == 9.0 and por_hora["08:00"] != 9.0


def test_super_expreso_circula_en_sus_dos_turnos():
    sx = H.servicio("troncal", "Super Expreso")
    for sentido in ("asc", "desc"):
        assert H.opera(sx, sentido, momento(LUNES, "07:00")) is True
        assert H.opera(sx, sentido, momento(LUNES, "18:00")) is True
        assert H.opera(sx, sentido, momento(LUNES, "12:00")) is False
        assert H.opera(sx, sentido, momento(SABADO, "18:00")) is False
    assert H.texto_horario(sx, "desc", dt.date(2025, 11, 17)) == "05:30–09:00 y 17:00–21:00"


def test_api_estacion_incluye_proximas_salidas_solo_para_ahora(client):
    r = client.get("/api/predictions/estacion", query_string={"id": "Naranjal", "hacia_id": "Angamos"})
    d = r.get_json()
    assert r.status_code == 200 and "proximas_salidas" in d and "ahora" in d
    assert all(o["llegada"] for o in d["proximas_salidas"])
    pasado = client.get("/api/predictions/estacion", query_string={"id": "Naranjal", "dia": LUNES, "hour": 8}).get_json()
    assert "proximas_salidas" not in pasado and "ahora" not in pasado
