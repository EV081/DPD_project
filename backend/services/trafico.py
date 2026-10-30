"""Ajuste del ETA con la congestión en vivo de TomTom (capa C del diseño de week10).

El ETA base sale del modelo (intervalo x factor de aforo). Aquí se multiplica por
``factor = clip(velocidad_libre / velocidad_actual, 1, tope)`` promediado sobre los ejes
arteriales asociados al sistema. Solo aplica a sistemas en vía mixta (corredores y alimentadores);
metro y troncal tienen vía exclusiva.

Es una hipótesis acotada, **no entrenada**: se valida con el feedback de usuarios
(``routes/feedback.py``, ``GET /api/feedback/resumen``). La API nunca espera a TomTom más de
``TIMEOUT_S``: si falla o no hay clave, queda el ETA base (modo ``historico``).
"""
from __future__ import annotations

import datetime as dt
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import requests

# Puntos de muestreo en ejes principales de Lima (los mismos de deliveries/week10 ingest_tomtom)
SEGMENTOS = {
    "javier_prado_salaverry": (-12.0949, -77.0320),
    "via_expresa_pardo": (-12.0795, -77.0385),
    "argentina_mexico": (-12.0589, -77.0406),
    "brasil_28julio": (-12.1064, -77.0246),
    "evitamiento_norte": (-12.0050, -77.0750),
    "panamericana_norte": (-11.9900, -77.0550),
}

# Asociación manual y aproximada sistema -> ejes (supuesto a validar con ATU/ProTransporte)
SEGMENTOS_POR_SISTEMA = {
    "corredor": ["javier_prado_salaverry", "argentina_mexico", "brasil_28julio"],
    "alimentador": ["evitamiento_norte", "panamericana_norte"],
}

TOPE_FACTOR = 1.5
UMBRAL_EN_VIVO_S = 600        # snapshot <= 10 min: factor completo
UMBRAL_RECIENTE_S = 1800      # 10-30 min: factor atenuado; más viejo: sin ajuste
PESO_RECIENTE = 0.5
TTL_S = 300                   # no se consulta TomTom más de una vez cada 5 min por eje
TIMEOUT_S = float(os.getenv("TOMTOM_TIMEOUT", "2.5"))
TOMTOM_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative/10/json"

_cache: dict[str, dict] = {}
_lock = threading.Lock()


def _api_key() -> str | None:
    return os.getenv("API_TOMTOM") or os.getenv("TOMMTOM_KEY") or None


def factor_trafico(ratio: float | None, tope: float = TOPE_FACTOR) -> float:
    """clip(libre/actual, 1.0, tope); un dato inválido no ajusta."""
    if ratio is None or not math.isfinite(ratio):
        return 1.0
    return float(min(max(ratio, 1.0), tope))


def modo_por_edad(edad_s: float | None) -> str:
    if edad_s is None or edad_s < 0 or edad_s > UMBRAL_RECIENTE_S:
        return "historico"
    return "en_vivo" if edad_s <= UMBRAL_EN_VIVO_S else "reciente"


def _consultar(segmento: str) -> float | None:
    """Ratio libre/actual de un eje, o None si TomTom no responde."""
    lat, lon = SEGMENTOS[segmento]
    try:
        r = requests.get(TOMTOM_URL, params={"point": f"{lat},{lon}", "key": _api_key(), "unit": "KMPH"},
                         timeout=TIMEOUT_S)
        r.raise_for_status()
        d = r.json()["flowSegmentData"]
        actual, libre = float(d["currentSpeed"]), float(d["freeFlowSpeed"])
        return libre / actual if actual > 0 else 1.0
    except Exception:  # noqa: BLE001 - cualquier fallo deja el dato anterior (que envejece solo)
        return None


def _refrescar(segmentos: list[str], ahora: dt.datetime) -> None:
    viejos = [s for s in segmentos
              if s not in _cache or (ahora - _cache[s]["capturado_en"]).total_seconds() > TTL_S]
    if not viejos or not _api_key():
        return
    with _lock:   # un solo refresco a la vez; los demás pedidos esperan y reutilizan el resultado
        viejos = [s for s in viejos
                  if s not in _cache or (ahora - _cache[s]["capturado_en"]).total_seconds() > TTL_S]
        if not viejos:
            return
        with ThreadPoolExecutor(max_workers=len(viejos)) as ex:
            for seg, ratio in zip(viejos, ex.map(_consultar, viejos)):
                if ratio is not None:
                    _cache[seg] = {"ratio": ratio, "capturado_en": ahora}


def estado(sistema: str, ahora: dt.datetime | None = None) -> dict:
    """{factor, modo_datos, edad_snapshot_s} de un sistema. Sin ajuste => factor 1.0 e historico."""
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    segmentos = SEGMENTOS_POR_SISTEMA.get(sistema)
    if not segmentos:
        return {"factor": 1.0, "modo_datos": "historico", "edad_snapshot_s": None}
    _refrescar(segmentos, ahora)
    datos = [_cache[s] for s in segmentos if s in _cache]
    if not datos:
        return {"factor": 1.0, "modo_datos": "historico", "edad_snapshot_s": None}
    ratio = sum(d["ratio"] for d in datos) / len(datos)
    edad = max((ahora - d["capturado_en"]).total_seconds() for d in datos)
    modo = modo_por_edad(edad)
    pleno = factor_trafico(ratio)
    factor = pleno if modo == "en_vivo" else 1.0 + PESO_RECIENTE * (pleno - 1.0) if modo == "reciente" else 1.0
    return {"factor": factor, "modo_datos": modo, "edad_snapshot_s": round(edad)}


def ajustar_item(item: dict, sistema: str, ahora: dt.datetime | None = None) -> dict:
    """Aplica el factor de tráfico al ETA de un ítem de predicción (solo la hora actual)."""
    est = estado(sistema, ahora)
    item["modo_datos"] = est["modo_datos"]
    item["factor_trafico"] = round(est["factor"], 3)
    item["edad_snapshot_s"] = est["edad_snapshot_s"]
    if est["factor"] <= 1.0 or item.get("eta_min") is None:
        return item
    item["eta_base_min"] = item["eta_min"]
    item["eta_min"] = round(item["eta_min"] * est["factor"], 1)
    if item.get("eta2_min") is not None:
        item["eta2_min"] = round(item["eta2_min"] * est["factor"], 1)
    # regla U: con aforo saturado, esperar más de 10 min deja de ser razonable
    if item.get("recommendation") == "esperar_siguiente" and item["eta_min"] > 10.0:
        item["recommendation"] = "cambiar_paradero"
    return item
