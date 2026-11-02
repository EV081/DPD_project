"""Eje 1 · calibración semanal del ETA con los "Ya abordé" de los usuarios (campeón vs retador).

NO reentrena el modelo de demanda (LightGBM, entrenado con ~600 mil subidas ATU por día). Ajusta una capa pequeña:

    espera_real ≈ k × (ETA del modelo × factor de tráfico)

- con contracción hacia 1: ``k = 1 + (k_obs − 1) · n / (n + 100)`` y tope [0,8; 1,4];
- solo si hay ≥ 100 respuestas para ajustar y el factor cambia ≥ 3 %; el retador se evalúa con las 2 últimas semanas, **que no se usaron para ajustarlo**,
  y se promueve únicamente si mejora el error medio ≥ 5 % frente al campeón actual (por omisión, k = 1);
- cada versión queda guardada (``calibracion_modelo``): la anterior pasa a ``archivado`` y se puede volver atrás;
- interruptor ``ETA_CALIBRACION_ACTIVA``. Es una hipótesis acotada, no un modelo entrenado.
"""
from __future__ import annotations

import datetime as dt
import os
import statistics
import threading
import time

from db.connection import db
from db.tablas import CalibracionModelo
from routes.feedback import FeedbackViaje
from services import calendario
from services.mapeo_estaciones import sistema_modelo

NOMBRE = "eta_factor"
PARAMS = {"min_ajuste": 100, "min_validacion": 20, "contraccion_n0": 100, "tope_inf": 0.8, "tope_sup": 1.4,
          "mejora_min": 0.05, "cambio_min": 0.03, "dias_ventana": 56, "dias_validacion": 14, "eta_min": 1.0}


def activa() -> bool:
    return os.getenv("ETA_CALIBRACION_ACTIVA", "1").strip().lower() not in ("0", "false", "no", "off")


# --------------------------------------------------------------------------- funciones puras
def eta_previo(f: dict) -> float | None:
    """ETA del modelo antes de calibrar: eta_base × factor de tráfico (sin base, el mostrado ya es el del modelo)."""
    base = f.get("eta_base_min") if f.get("eta_base_min") is not None else f.get("eta_mostrado_min")
    if base is None:
        return None
    return float(base) * float(f.get("factor_trafico") or 1.0)


def factor_estimado(filas: list[dict], p: dict | None = None) -> tuple[float | None, int]:
    """(k contraído hacia 1, n usado) a partir de filas con espera_real_min y su ETA previo; None si no hay datos."""
    p = p or PARAMS
    r = []
    for f in filas:
        pre = eta_previo(f)
        if pre is not None and pre >= p["eta_min"] and f.get("espera_real_min") is not None:
            r.append(f["espera_real_min"] / pre)
    if not r:
        return None, 0
    k_obs, n = statistics.median(r), len(r)
    k = 1.0 + (k_obs - 1.0) * n / (n + p["contraccion_n0"])
    return min(max(k, p["tope_inf"]), p["tope_sup"]), n


def mae(filas: list[dict], k: float, p: dict | None = None) -> float | None:
    p = p or PARAMS
    e = [abs(f["espera_real_min"] - k * eta_previo(f)) for f in filas
         if eta_previo(f) is not None and eta_previo(f) >= p["eta_min"] and f.get("espera_real_min") is not None]
    return sum(e) / len(e) if e else None


def decidir(fit: list[dict], valid: list[dict], k_campeon: float, p: dict | None = None) -> dict:
    """Decisión campeón/retador (pura). Devuelve {estado, k, n_ajuste, n_validacion, mae_campeon, mae_retador, mejora, motivo}."""
    p = p or PARAMS
    k, n_fit = factor_estimado(fit, p)
    base = {"estado": "sin_datos", "k": k_campeon, "n_ajuste": n_fit, "n_validacion": len(valid)}
    if k is None or n_fit < p["min_ajuste"]:
        return {**base, "motivo": f"se necesitan ≥ {p['min_ajuste']} respuestas para ajustar (hay {n_fit})"}
    m_camp, m_chal = mae(valid, k_campeon, p), mae(valid, k, p)
    n_val = sum(1 for f in valid if eta_previo(f) is not None and eta_previo(f) >= p["eta_min"])
    info = {**base, "k": k, "mae_campeon": m_camp, "mae_retador": m_chal, "n_validacion": n_val}
    if n_val < p["min_validacion"] or m_camp is None or m_chal is None:
        return {**info, "estado": "retador", "mejora": None, "motivo": f"faltan respuestas de validación (≥ {p['min_validacion']})"}
    mejora = (m_camp - m_chal) / max(m_camp, 1e-6)
    if abs(k - k_campeon) < 1e-3:
        return {**info, "estado": "retador", "mejora": mejora, "motivo": "igual al campeón actual"}
    if abs(k - k_campeon) < p["cambio_min"]:
        return {**info, "estado": "retador", "mejora": mejora,
                "motivo": f"cambio del factor menor a {p['cambio_min']:.0%}: es ruido, no vale la pena cambiar el ETA"}
    if mejora >= p["mejora_min"]:
        return {**info, "estado": "campeon", "mejora": mejora, "motivo": f"mejora {mejora:.1%} ≥ {p['mejora_min']:.0%} en datos no usados para ajustar"}
    return {**info, "estado": "retador", "mejora": mejora, "motivo": f"mejora {mejora:.1%} < {p['mejora_min']:.0%}: se mantiene el campeón"}


# --------------------------------------------------------------------------- factor vigente (caché por proceso)
_cache: dict[str, tuple[float, float]] = {}
_lock = threading.Lock()
TTL_S = float(os.getenv("ETA_CALIBRACION_TTL_S", "60"))


def invalidar() -> None:
    with _lock:
        _cache.clear()


def campeon(sistema: str):
    fila = (CalibracionModelo.query.filter_by(sistema=sistema, nombre=NOMBRE, estado="campeon")
            .order_by(CalibracionModelo.version.desc()).first())
    db.session.rollback()
    return fila


def factor_eta(sistema: str) -> float:
    """Factor del campeón vigente (1.0 si no hay, está apagado o no hay base de datos disponible)."""
    if not activa():
        return 1.0
    s = sistema_modelo(sistema) or sistema
    with _lock:
        hit = _cache.get(s)
        if hit and time.monotonic() - hit[1] < TTL_S:
            return hit[0]
    try:
        fila = campeon(s)
        k = float(fila.parametros["factor"]) if fila else 1.0
    except Exception:                                                                    # noqa: BLE001 - sin contexto de app o sin tabla
        k = 1.0
    with _lock:
        _cache[s] = (k, time.monotonic())
    return k


# --------------------------------------------------------------------------- job semanal
def _filas(sistema: str, desde: dt.datetime, hasta: dt.datetime) -> list[dict]:
    q = FeedbackViaje.query.filter(FeedbackViaje.creado_en >= desde, FeedbackViaje.creado_en < hasta).all()
    db.session.rollback()
    return [{"espera_real_min": f.espera_real_min, "eta_mostrado_min": f.eta_mostrado_min, "eta_base_min": f.eta_base_min,
             "factor_trafico": f.factor_trafico} for f in q if (sistema_modelo(f.sistema) or "otro") == sistema]


def calibrar_eta(sistema: str, ahora: dt.datetime | None = None, p: dict | None = None) -> dict:
    """Ajusta el retador de un sistema, lo compara con el campeón y guarda el resultado versionado."""
    p = p or PARAMS
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    corte = ahora - dt.timedelta(days=p["dias_validacion"])
    fit = _filas(sistema, ahora - dt.timedelta(days=p["dias_ventana"]), corte)
    valid = _filas(sistema, corte, ahora + dt.timedelta(minutes=1))
    actual = campeon(sistema)
    k_camp = float(actual.parametros["factor"]) if actual else 1.0
    d = decidir(fit, valid, k_camp, p)
    if d["estado"] == "sin_datos" or d.get("motivo", "").startswith(("igual al campeón", "cambio del factor menor")):
        return {"sistema": sistema, "guardado": False, **d}              # nada que registrar: sin datos suficientes o cambio irrelevante
    ultima = db.session.query(db.func.max(CalibracionModelo.version)).filter_by(sistema=sistema, nombre=NOMBRE).scalar() or 0
    if d["estado"] == "campeon":
        CalibracionModelo.query.filter_by(sistema=sistema, nombre=NOMBRE, estado="campeon").update({"estado": "archivado"})
    db.session.add(CalibracionModelo(
        sistema=sistema, nombre=NOMBRE, version=ultima + 1, estado=d["estado"], creado_en=ahora,
        parametros={"factor": round(d["k"], 4), "n_ajuste": d["n_ajuste"], "n_validacion": d["n_validacion"]},
        metricas={k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items() if k in ("mae_campeon", "mae_retador", "mejora", "motivo")}))
    db.session.commit()
    invalidar()
    return {"sistema": sistema, "version": ultima + 1, "guardado": True, **d}


def calibrar_todos(ahora: dt.datetime | None = None) -> dict:
    sistemas = ("metro_l1", "troncal", "corredor", "alimentador")
    res = {s: calibrar_eta(s, ahora) for s in sistemas}
    return {"estado": "ok" if any(r["estado"] != "sin_datos" for r in res.values()) else "sin_datos", "sistemas": res}
