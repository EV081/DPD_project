"""Trayecto a pie del transbordo: interpretación de la respuesta y caché (sin red)."""
import pytest
from services import caminata as C

RESP = {"code": "Ok", "routes": [{"distance": 312.4, "duration": 240.0,
        "geometry": {"type": "LineString", "coordinates": [[-77.0235, -12.0893], [-77.0240, -12.0900], [-77.0254, -12.0910]]}}]}


def test_interpretar_respuesta():
    out = C.interpretar(RESP)
    assert out["distancia_m"] == 312.4 and out["minutos"] == 4.0
    assert len(out["geojson"]["geometry"]["coordinates"]) == 3


@pytest.mark.parametrize("resp", [{}, {"code": "NoRoute", "routes": []}, {"code": "Ok", "routes": [{"distance": 1, "duration": 1, "geometry": {"coordinates": [[0, 0]]}}]}])
def test_sin_ruta_falla(resp):
    with pytest.raises(C.CaminataError):
        C.interpretar(resp)


def test_cache_pide_una_sola_vez():
    C._cache.clear()
    llamadas = []
    def falso(*a):
        llamadas.append(a)
        return RESP
    a = C.ruta_a_pie(-12.0893, -77.0235, -12.0910, -77.0254, pedir=falso)
    b = C.ruta_a_pie(-12.0893, -77.0235, -12.0910, -77.0254, pedir=falso)
    assert a == b and len(llamadas) == 1
