"""Ajuste en vivo del ETA y la recomendación con congestión TomTom (capa C del diseño).

El pronóstico de demanda corre en batch (``inferencia.ModeloSistema.pronosticar``); esta capa
solo hace aritmética sobre una fila de ``prediccion`` y el último snapshot de tráfico, de modo
que la API nunca depende de la latencia de TomTom. El factor de tráfico es una **hipótesis
acotada, no entrenada** (ver ``models/ajuste_vivo_config.json``).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Mapping

import numpy as np

MODEL_DIR = Path(__file__).resolve().parent
MODELS_DIR = MODEL_DIR.parents[1] / "models"
sys.path.insert(0, str(MODEL_DIR))

import model_atu_v2 as V  # noqa: E402

MODOS = ("en_vivo", "reciente", "historico")


def _leer(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def cargar_config(models_dir: Path = MODELS_DIR) -> tuple[dict, dict]:
    return _leer(models_dir / "ajuste_vivo_config.json"), _leer(models_dir / "mapeo_segmentos.json")


def factor_trafico(ratio: float, tope: float = 1.5) -> float:
    """clip(libre/actual, 1.0, tope); un dato inválido no ajusta."""
    if ratio is None or not np.isfinite(ratio):
        return 1.0
    return float(min(max(ratio, 1.0), tope))


def modo_por_edad(edad_s: float | None, umbrales: Mapping[str, float] | None = None) -> str:
    umbrales = umbrales or {"en_vivo": 600, "reciente": 1800}
    if edad_s is None or edad_s < 0 or edad_s > umbrales["reciente"]:
        return "historico"
    return "en_vivo" if edad_s <= umbrales["en_vivo"] else "reciente"


def _snapshot_agregado(snapshots: Mapping[str, Mapping], segmentos: list[str], ahora: dt.datetime):
    """(ratio medio, edad en s del más viejo) de los segmentos TomTom disponibles; None si no hay."""
    ratios, edades = [], []
    for seg in segmentos:
        s = snapshots.get(seg)
        if not s or s.get("fuente") != "tomtom":
            continue
        ratios.append(float(s["ratio"]))
        edades.append((ahora - s["capturado_en"]).total_seconds())
    if not ratios:
        return None, None
    return float(np.mean(ratios)), float(max(edades))


def ajustar_en_vivo(fila: Mapping, snapshots: Mapping[str, Mapping], ahora: dt.datetime,
                    sistema: str, config: dict | None = None, mapeo: dict | None = None) -> dict:
    """Devuelve eta, eta2, recomendación, modo y edad del snapshot para una fila de predicción.

    ``fila`` requiere ``aforo``, ``eta_min``, ``eta2_min`` y opcionalmente ``aforo_siguiente``
    (clase de la hora h+1; si falta se asume igual a la actual). ``snapshots`` es
    ``{segmento: {ratio, fuente, capturado_en}}``.
    """
    if config is None or mapeo is None:
        config, mapeo = cargar_config()
    eta, eta2 = float(fila["eta_min"]), float(fila["eta2_min"])
    cfg_sis = mapeo["sistemas"].get(sistema, {"aplica_trafico": False, "segmentos": []})

    modo, edad, factor = "historico", None, 1.0
    if cfg_sis["aplica_trafico"]:
        ratio, edad = _snapshot_agregado(snapshots, cfg_sis["segmentos"], ahora)
        modo = modo_por_edad(edad, config["umbrales_edad_s"]) if ratio is not None else "historico"
        pleno = factor_trafico(ratio, config["tope_factor"]) if ratio is not None else 1.0
        if modo == "en_vivo":
            factor = pleno
        elif modo == "reciente":
            factor = 1.0 + config["peso_reciente"] * (pleno - 1.0)

    eta_adj, eta2_adj = eta * factor, eta2 * factor
    clase = fila["aforo"]
    clases = np.array([clase, fila.get("aforo_siguiente", clase)])
    rec = V.recomendaciones(clases, np.array([eta_adj, eta_adj]))[0]
    return {
        "eta_min": eta_adj, "eta2_min": eta2_adj, "recomendacion": str(rec),
        "modo_datos": modo, "edad_snapshot_s": edad, "factor_trafico": factor,
    }
