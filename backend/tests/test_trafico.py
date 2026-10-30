import datetime as dt

import pytest

from services import trafico

AHORA = dt.datetime(2026, 10, 30, 12, 0, tzinfo=dt.timezone.utc)


@pytest.fixture(autouse=True)
def cache_limpio():
    trafico._cache.clear()
    yield
    trafico._cache.clear()


def _snapshot(segmentos, ratio, edad_s):
    for s in segmentos:
        trafico._cache[s] = {"ratio": ratio, "capturado_en": AHORA - dt.timedelta(seconds=edad_s)}


def test_factor_acotado():
    assert trafico.factor_trafico(0.8) == 1.0            # más rápido que el flujo libre: no acorta
    assert trafico.factor_trafico(1.3) == 1.3
    assert trafico.factor_trafico(3.0) == trafico.TOPE_FACTOR
    assert trafico.factor_trafico(None) == 1.0
    assert trafico.factor_trafico(float("nan")) == 1.0


def test_modos_por_edad():
    assert trafico.modo_por_edad(60) == "en_vivo"
    assert trafico.modo_por_edad(900) == "reciente"
    assert trafico.modo_por_edad(3600) == "historico"
    assert trafico.modo_por_edad(None) == "historico"


def test_sin_dato_no_ajusta():
    it = trafico.ajustar_item({"eta_min": 4.0, "eta2_min": 8.0, "recommendation": "abordar"}, "corredor", AHORA)
    assert it["eta_min"] == 4.0 and it["modo_datos"] == "historico" and "eta_base_min" not in it


def test_en_vivo_alarga_eta_y_conserva_la_base():
    _snapshot(trafico.SEGMENTOS_POR_SISTEMA["corredor"], 1.5, 60)
    it = trafico.ajustar_item({"eta_min": 4.0, "eta2_min": 8.0, "recommendation": "abordar"}, "corredor", AHORA)
    assert it["eta_min"] == 6.0 and it["eta2_min"] == 12.0 and it["eta_base_min"] == 4.0
    assert it["modo_datos"] == "en_vivo" and it["factor_trafico"] == 1.5


def test_reciente_atenua_el_factor():
    _snapshot(trafico.SEGMENTOS_POR_SISTEMA["alimentador"], 1.5, 1000)
    it = trafico.ajustar_item({"eta_min": 4.0, "eta2_min": 8.0, "recommendation": "abordar"}, "alimentador", AHORA)
    assert it["modo_datos"] == "reciente" and it["factor_trafico"] == 1.25 and it["eta_min"] == 5.0


def test_sistemas_de_via_exclusiva_no_se_ajustan():
    _snapshot(list(trafico.SEGMENTOS), 1.5, 60)
    for sis in ("metro_l1", "troncal"):
        it = trafico.ajustar_item({"eta_min": 4.0, "eta2_min": 8.0, "recommendation": "abordar"}, sis, AHORA)
        assert it["eta_min"] == 4.0 and it["modo_datos"] == "historico"


def test_esperar_pasa_a_cambiar_paradero_si_el_eta_supera_10():
    _snapshot(trafico.SEGMENTOS_POR_SISTEMA["corredor"], 1.5, 60)
    it = trafico.ajustar_item({"eta_min": 8.0, "eta2_min": 16.0, "recommendation": "esperar_siguiente"}, "corredor", AHORA)
    assert it["eta_min"] == 12.0 and it["recommendation"] == "cambiar_paradero"
