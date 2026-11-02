"""Recalibración del riesgo con reportes (función pura): umbrales, decaimiento, tope, zona y reversibilidad."""
import datetime as dt
import math

import pytest

from eje2_sintetico import crear_grafo
from services import eje2_reportes as R
from services import eje2_service as E

AHORA = dt.datetime(2026, 11, 2, 15, 0, tzinfo=dt.timezone.utc)
P = dict(R.PARAMS)


@pytest.fixture(scope="module")
def g(tmp_path_factory):
    return E.GrafoEje2(crear_grafo(tmp_path_factory.mktemp("grafo")))


def rep(seg="1_2_0", user=1, hace_dias=0.0, franja="noche"):
    return {"seg_id": seg, "franja": franja, "user_id": user, "ocurrido_en": AHORA - dt.timedelta(days=hace_dias)}


def delta(res, seg, franja="noche"):
    return next((a["delta"] for a in res if a["seg_id"] == seg and a["franja"] == franja), 0.0)


def test_sin_reportes_no_hay_ajustes(g):
    assert R.calcular_ajustes([], g, AHORA, P) == []


def test_dos_reportes_no_alcanzan(g):
    assert R.calcular_ajustes([rep(user=1), rep(user=2)], g, AHORA, P) == []


def test_tres_reportes_de_una_sola_persona_no_alcanzan(g):
    res = R.calcular_ajustes([rep(user=1, hace_dias=d) for d in (0, 1, 2)], g, AHORA, P)
    assert res == []                                                                       # hace falta al menos 2 personas distintas


def test_la_misma_persona_cuenta_una_vez_por_segmento_y_dia(g):
    res = R.calcular_ajustes([rep(user=1), rep(user=1), rep(user=1), rep(user=2), rep(user=2)], g, AHORA, P)
    assert res == []                                                                       # 5 reportes pero solo 2 (persona, día) distintos


def test_tres_personas_distintas_activan_el_ajuste(g):
    res = R.calcular_ajustes([rep(user=u) for u in (1, 2, 3)], g, AHORA, P)
    esperado = P["tope"] * (1 - math.exp(-3 / P["n0"]))
    assert delta(res, "1_2_0") == pytest.approx(esperado, abs=1e-4)
    fila = next(a for a in res if a["seg_id"] == "1_2_0")
    assert fila["n_reportes"] == 3 and fila["n_usuarios"] == 3


def test_la_zona_incluye_vecinos_con_menos_efecto(g):
    res = R.calcular_ajustes([rep(user=u) for u in (1, 2, 3)], g, AHORA, P)
    pleno = delta(res, "1_2_0")
    assert delta(res, "2_4_0") == pytest.approx(pleno * 0.5, abs=1e-4)                       # 1 salto (comparte el nodo 2)
    assert delta(res, "1_3_0") == pytest.approx(pleno * 0.5, abs=1e-4)                       # 1 salto (comparte el nodo 1)
    assert delta(res, "4_5_0") == pytest.approx(pleno * 0.25, abs=1e-4)                      # 2 saltos
    assert delta(res, "1_2_0") > delta(res, "2_4_0") > delta(res, "4_5_0")


def test_reportes_repartidos_en_la_zona_suman_para_el_umbral(g):
    res = R.calcular_ajustes([rep("1_2_0", 1), rep("2_4_0", 2), rep("1_3_0", 3)], g, AHORA, P)
    assert delta(res, "1_2_0") > 0


def test_el_peso_baja_con_la_edad_a_la_mitad_cada_vida_media(g):
    frescos = delta(R.calcular_ajustes([rep(user=u) for u in (1, 2, 3)], g, AHORA, P), "1_2_0")
    viejos = delta(R.calcular_ajustes([rep(user=u, hace_dias=30) for u in (1, 2, 3)], g, AHORA, P), "1_2_0")
    assert viejos == pytest.approx(P["tope"] * (1 - math.exp(-1.5 / P["n0"])), abs=1e-4) and viejos < frescos


def test_reportes_fuera_de_la_ventana_se_ignoran(g):
    assert R.calcular_ajustes([rep(user=u, hace_dias=P["ventana_dias"] + 1) for u in (1, 2, 3)], g, AHORA, P) == []


def test_reportes_del_futuro_se_ignoran(g):
    assert R.calcular_ajustes([rep(user=u, hace_dias=-3) for u in (1, 2, 3)], g, AHORA, P) == []


def test_el_ajuste_tiene_tope_aunque_lleguen_muchos_reportes(g):
    res = R.calcular_ajustes([rep(user=u, hace_dias=d % 20) for u in range(60) for d in range(5)], g, AHORA, P)
    assert max(a["delta"] for a in res) <= P["tope"] + 1e-9 and delta(res, "1_2_0") > 0.28


def test_el_ajuste_crece_con_mas_reportes(g):
    d = [delta(R.calcular_ajustes([rep(user=u) for u in range(n)], g, AHORA, P), "1_2_0") for n in (3, 5, 8, 15)]
    assert d == sorted(d) and len(set(d)) == 4


def test_las_franjas_son_independientes(g):
    res = R.calcular_ajustes([rep(user=u, franja="noche") for u in (1, 2, 3)] + [rep(user=9, franja="dia")], g, AHORA, P)
    assert delta(res, "1_2_0", "noche") > 0 and delta(res, "1_2_0", "dia") == 0


def test_vuelve_a_cero_cuando_dejan_de_llegar_reportes(g):
    reportes = [rep(user=u) for u in (1, 2, 3)]
    assert R.calcular_ajustes(reportes, g, AHORA, P)
    despues = AHORA + dt.timedelta(days=P["ventana_dias"] + 5)
    assert R.calcular_ajustes(reportes, g, despues, P) == []


def test_segmentos_desconocidos_y_franjas_raras_se_ignoran(g):
    assert R.calcular_ajustes([rep("no_existe", u) for u in (1, 2, 3)] + [rep(franja="tarde", user=u) for u in (1, 2, 3)], g, AHORA, P) == []


def test_los_parametros_se_pueden_cambiar_por_entorno(monkeypatch):
    monkeypatch.setenv("EJE2_MIN_REPORTES", "5")
    monkeypatch.setenv("EJE2_AJUSTE_TOPE", "0.1")
    p = R.parametros()
    assert p["min_reportes"] == 5 and p["tope"] == 0.1 and p["min_usuarios"] == 2


def test_el_interruptor_apaga_el_ajuste(monkeypatch):
    assert R.ajuste_activo() is True
    for v in ("0", "false", "off", "NO"):
        monkeypatch.setenv("EJE2_AJUSTE_ACTIVO", v)
        assert R.ajuste_activo() is False
