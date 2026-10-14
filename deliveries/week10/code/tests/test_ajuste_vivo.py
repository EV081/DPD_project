"""Ajuste en vivo del ETA (sin BD ni modelos entrenados)."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
import ajuste_vivo as A  # noqa: E402

AHORA = dt.datetime(2026, 1, 1, 8, 0)
FILA = {"aforo": "Saturado", "aforo_siguiente": "De_pie", "eta_min": 7.8, "eta2_min": 13.8}


def _snap(ratio, minutos, fuente="tomtom", seg="javier_prado_salaverry"):
    return {seg: {"ratio": ratio, "fuente": fuente, "capturado_en": AHORA - dt.timedelta(minutes=minutos)}}


def test_factor_acotado():
    assert A.factor_trafico(0.8) == 1.0
    assert A.factor_trafico(1.2) == 1.2
    assert A.factor_trafico(3.0) == 1.5
    assert A.factor_trafico(float("nan")) == 1.0


@pytest.mark.parametrize("edad,modo", [(60, "en_vivo"), (600, "en_vivo"), (601, "reciente"),
                                       (1800, "reciente"), (1801, "historico"), (None, "historico")])
def test_modo_por_edad(edad, modo):
    assert A.modo_por_edad(edad) == modo


def test_en_vivo_escala_eta_y_aplica_regla_u():
    r = A.ajustar_en_vivo(FILA, _snap(1.5, 2), AHORA, "corredor")
    assert r["modo_datos"] == "en_vivo"
    assert r["eta_min"] == pytest.approx(7.8 * 1.5)
    assert r["eta2_min"] == pytest.approx(13.8 * 1.5)
    assert r["recomendacion"] == "cambiar_paradero"  # eta ajustado > 10 y Saturado


def test_reciente_pesa_la_mitad():
    r = A.ajustar_en_vivo(FILA, _snap(1.4, 20), AHORA, "corredor")
    assert r["modo_datos"] == "reciente"
    assert r["factor_trafico"] == pytest.approx(1.2)


@pytest.mark.parametrize("snaps", [{}, _snap(1.5, 60), _snap(1.5, 2, fuente="fallback")])
def test_sin_dato_vigente_cae_a_historico(snaps):
    r = A.ajustar_en_vivo(FILA, snaps, AHORA, "corredor")
    assert r["modo_datos"] == "historico"
    assert r["eta_min"] == FILA["eta_min"]
    assert r["recomendacion"] == "esperar_siguiente"  # regla U con ETA base <= 10


@pytest.mark.parametrize("sistema", ["metro_l1", "troncal"])
def test_via_exclusiva_no_se_ajusta(sistema):
    seg = {"via_expresa_pardo": {"ratio": 2.0, "fuente": "tomtom", "capturado_en": AHORA}}
    r = A.ajustar_en_vivo(FILA, seg, AHORA, sistema)
    assert r["factor_trafico"] == 1.0 and r["eta_min"] == FILA["eta_min"]


def test_misma_regla_u_que_el_modelo():
    import numpy as np
    import model_atu_v2 as V

    for aforo in ("Asientos", "De_pie", "Saturado"):
        for sig in ("Asientos", "Saturado"):
            for eta in (4.0, 9.0, 12.0):
                fila = {"aforo": aforo, "aforo_siguiente": sig, "eta_min": eta, "eta2_min": eta + 6}
                esperado = V.recomendaciones(np.array([aforo, sig]), np.array([eta, eta]))[0]
                assert A.ajustar_en_vivo(fila, {}, AHORA, "metro_l1")["recomendacion"] == esperado
