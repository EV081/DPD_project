"""Viajes con transbordo (sin red ni Flask): escenario sintético con dos corredores que se cruzan."""
from services import transbordos as T

DEG = 0.001   # ~110 m


def _linea(id_, sistema, codigo, bidi, puntos):
    return T._servicio(id_, sistema, codigo, bidi, [(f"{codigo}-{k}", f"parada {k}", lat, lon) for k, (lat, lon) in enumerate(puntos)])


def escenario(ultimo_k_de_A=20):
    # A va de oeste a este por lat=-12.00 y termina en la parada `ultimo_k_de_A`; B va de sur a norte por lon=-77.00
    A = _linea("c:A:1", "corredores", "A", False, [(-12.000, -77.010 + k * DEG) for k in range(0, ultimo_k_de_A + 1)])
    B = _linea("c:B:1", "corredores", "B", False, [(-12.010 + k * DEG, -77.000) for k in range(0, 21)])
    return [A, B]


ORIGEN = (-12.000, -77.0095)     # junto al comienzo de A
DESTINO = (-11.9905, -77.000)    # junto al final de B


def test_encuentra_transbordo_en_el_sentido_correcto():
    r = T.buscar_transbordos(escenario(), ORIGEN, DESTINO)
    assert r, "debería haber un viaje A → B"
    v = r[0]
    assert (v["route_code"], v["transbordo"]["route_code"]) == ("A", "B")
    assert v["transbordo"]["caminata_m"] < 20            # se cruzan en la misma parada
    assert v["costo_generalizado_min"] > 0 and v["viaje_min"] > 0


def test_sentido_contrario_no_existe_en_corredores():
    # de B (final) hacia A (comienzo) habría que ir contra el sentido de ambas secuencias
    assert T.buscar_transbordos(escenario(), DESTINO, ORIGEN) == []


def test_limite_de_caminata_entre_paraderos():
    # A termina en lon=-77.003 (~326 m de B) o en -77.002 (~218 m de B); el tope es 300 m
    assert T.buscar_transbordos(escenario(ultimo_k_de_A=7), ORIGEN, DESTINO, caminata_max_m=300) == []
    r = T.buscar_transbordos(escenario(ultimo_k_de_A=8), ORIGEN, DESTINO, caminata_max_m=300)
    assert r and 150 < r[0]["transbordo"]["caminata_m"] <= 300


def test_dos_servicios_de_la_misma_troncal_no_son_transbordo():
    X = _linea("m:X", "metropolitano", "Ruta A", True, [(-12.0, -77.01 + k * DEG) for k in range(10)])
    Y = _linea("m:Y", "metropolitano", "Ruta B", True, [(-12.0, -77.01 + k * DEG) for k in range(10)])
    assert T.buscar_transbordos([X, Y], (-12.0, -77.0099), (-12.0, -77.0015)) == []


def test_troncal_bidireccional_permite_ir_y_volver():
    L1 = _linea("l1", "metro_l1", "Metro L1", True, [(-12.0, -77.02 + k * DEG) for k in range(10)])
    B = _linea("c:B:1", "corredores", "B", False, [(-12.0 + k * DEG, -77.0115) for k in range(8)])
    # origen cerca del extremo ESTE de L1, el cruce con B está al OESTE: hay que ir "hacia atrás" en la lista
    r = T.buscar_transbordos([L1, B], (-12.0, -77.0105), (-11.9945, -77.0115))
    assert r and r[0]["system"] == "metro_l1"


def test_orden_por_costo_y_limite():
    r = T.buscar_transbordos(escenario(), ORIGEN, DESTINO, limite=3)
    costos = [x["costo_generalizado_min"] for x in r]
    assert costos == sorted(costos) and len(r) <= 3


def test_construir_servicios_asocia_paradas_a_estaciones_y_ordena():
    est = [
        {"id": "E2", "name": "Dos", "system": "corredores", "latitude": -12.001, "longitude": -77.0, "raw_properties": {"ruta": "9"}},
        {"id": "E1", "name": "Uno", "system": "corredores", "latitude": -12.000, "longitude": -77.0, "raw_properties": {"ruta": "9"}},
        {"id": "E3", "name": "Tres", "system": "corredores", "latitude": -12.002, "longitude": -77.0, "raw_properties": {"ruta": "9"}},
    ]
    paradas = [  # llegan desordenadas: el campo `orden` manda
        {"properties": {"ruta": "9", "direccion": 1, "orden": 3}, "geometry": {"coordinates": [-77.0, -12.002]}},
        {"properties": {"ruta": "9", "direccion": 1, "orden": 1}, "geometry": {"coordinates": [-77.0, -12.000]}},
        {"properties": {"ruta": "9", "direccion": 1, "orden": 2}, "geometry": {"coordinates": [-77.0, -12.001]}},
    ]
    s = T.construir_servicios(est, paradas, [])
    assert len(s) == 1 and s[0].ids == ["E1", "E2", "E3"] and not s[0].bidireccional
    assert s[0].acum[-1] > 200   # ~220 m acumulados


def test_misma_pareja_de_paraderos_con_distintas_rutas_se_agrupa():
    A = _linea("c:A:1", "corredores", "A", False, [(-12.000, -77.010 + k * DEG) for k in range(0, 21)])
    A2 = _linea("c:A2:1", "corredores", "A2", False, [(-12.000, -77.010 + k * DEG) for k in range(0, 21)])
    B = _linea("c:B:1", "corredores", "B", False, [(-12.010 + k * DEG, -77.000) for k in range(0, 21)])
    r = T.buscar_transbordos([A, A2, B], ORIGEN, DESTINO)
    pares = {(x["boarding_station"], x["leaving_station"], x["transbordo"]["boarding_station"], x["transbordo"]["leaving_station"]) for x in r}
    assert len(pares) == len(r), "no debe haber dos viajes con los mismos paraderos"
    assert any("A" in x["route_code"] and "A2" in x["route_code"] for x in r)


def test_parada_sin_coordenada_no_se_inventa_y_se_respetan_sentidos_atu():
    est = [
        {'id':'A','name':'A','system':'metropolitano','latitude':-12.,'longitude':-77.},
        {'id':'B','name':'B','system':'metropolitano','latitude':-12.01,'longitude':-77.},
    ]
    features = [
        {'properties':{'estacion':e['name'],'servicio_nombre':'Expreso de prueba','sentido':'desc','bidireccional':False,'orden_completo':True},
         'geometry':{'coordinates':[e['longitude'],e['latitude']]}}
        for e in est
    ]
    features.append({'properties':{'estacion':'Pendiente','servicio_nombre':'Expreso de prueba'},'geometry':None})
    unknown_corridor = [{'properties':{'ruta':'9','direccion':1,'orden':1},'geometry':None}]
    services = T.construir_servicios(est, unknown_corridor, features)
    assert len(services) == 1
    assert services[0].ids == ['A','B']
    assert services[0].siguientes(1).tolist() == []
    assert services[0].siguientes(0).tolist() == [1]
