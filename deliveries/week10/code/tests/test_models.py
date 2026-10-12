"""Modelos serializados (Issue #19): integridad, manifiesto y verificación de recarga.

No requiere PostgreSQL. Se salta si faltan las dependencias de modelado (la imagen del
pipeline no instala lightgbm/scikit-learn); ver ``requirements-models.txt``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("lightgbm")
pytest.importorskip("sklearn")
pytest.importorskip("statsforecast")

MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
sys.path.insert(0, str(MODEL_DIR))

import verificar_modelos as VM  # noqa: E402
from inferencia import MODELS_DIR, leer_json  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (MODELS_DIR / "manifest.json").exists(),
    reason="no existe models/manifest.json (correr serializar_modelos.py)",
)
SISTEMAS = ["metro_l1", "troncal", "corredor", "alimentador"]


@pytest.fixture(scope="module")
def manifiesto() -> dict:
    return leer_json(MODELS_DIR / "manifest.json")


def test_hashes_coinciden_con_manifiesto(manifiesto):
    checks = VM.verificar_hashes(MODELS_DIR, manifiesto)
    assert checks
    assert all(c["ok"] for c in checks), [c for c in checks if not c["ok"]]


def test_model_cards_consistentes(manifiesto):
    assert [r["sistema"] for r in manifiesto["resumen"]] == SISTEMAS
    for r in manifiesto["resumen"]:
        card = leer_json(MODELS_DIR / r["sistema"] / "model_card.json")
        assert card["version"] == manifiesto["version"]
        assert card["pronostico"]["modelo_principal"] == r["modelo_principal"]
        assert card["metricas_test"]["principal"]["todos"]["WMAPE"] > 0
        assert set(card["criterios_aceptacion"]) == {
            "RNF-01 (accuracy >= 0.75 y F1-macro >= 0.72)",
            "AC-02 (F1 >= 0.72 en las 3 clases)",
            "AC-03 (recomendación correcta >= 80 %)",
        }


@pytest.mark.parametrize("sistema", SISTEMAS)
def test_recarga_reproduce_referencia(manifiesto, sistema):
    card = leer_json(MODELS_DIR / sistema / "model_card.json")
    principal = card["pronostico"]["modelo_principal"]
    miembros = (card["pronostico"].get("ensemble") or {}).get("miembros", [])
    if {"chronos2", "chronos_bolt"} & ({principal} | set(miembros)):
        pytest.importorskip("chronos")
    checks = VM.verificar_sistema(MODELS_DIR, sistema, manifiesto["dia_referencia"], rtol=1e-4)
    fallas = [c for c in checks if not c["ok"]]
    assert not fallas, fallas
