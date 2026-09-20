"""Capas de congestion para ajustar el ETA (Modulo 1).

Diseno (S08):
  - Ahora: backend SINTETICO. Genera `congestion_sintetica.csv` en data_processed con un
    patron de Bogota (picos 6-9 y 17-20, pico y placa, lluvia), determinista (sin API).
  - Futuro (produccion): backend REAL con TomTom Traffic `flowSegmentData`
    (currentSpeed / freeFlowSpeed) leyendo la key de la variable de entorno `TOMMTOM_KEY`.
    El ETA en vivo se recalibraria sin reentrenar: eta_efectivo = eta_base * ratio.

El ratio de congestion se define como  freeFlowSpeed / currentSpeed  (>= 1.0):
    1.0 = flujo libre, ~2.0-2.5 = trafico pesado.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


def _ratio_por_hora(hora: int, es_habil: bool = True, seed: int = 0) -> float:
    """Ratio base deterministico segun hora del dia y tipo de dia."""
    rng = np.random.default_rng(seed + hora)
    jitter = 1.0 + rng.uniform(-0.03, 0.03)
    if es_habil:
        if 6 <= hora <= 9:      # pico manana
            return 1.75 * jitter
        if 17 <= hora <= 20:    # pico tarde
            return 1.85 * jitter
        if 12 <= hora <= 16:    # mediodia
            return 1.35 * jitter
        if hora <= 5 or hora >= 22:
            return 1.08 * jitter
        return 1.25 * jitter    # resto (10-11, 21)
    # fin de semana
    if 10 <= hora <= 19:
        return 1.30 * jitter
    return 1.10 * jitter


def _aplica_eventos(ts: pd.Timestamp, es_habil: bool, seed: int) -> float:
    """Multiplicadores por eventos: pico y placa (habil) y lluvia (determinista)."""
    mult = 1.0
    rng = np.random.default_rng(seed + ts.dayofyear * 7 + ts.hour)
    if es_habil and (ts.hour in (7, 8, 17, 18)):
        mult *= 1.15  # dias laborales de alta carga
    if 30 <= ts.day <= 31 and ts.hour in (14, 15, 16, 17):
        mult *= 1.30  # evento de lluvia de fin de mes (determinista)
    day = ts.dayofyear + ts.hour
    if day % 6 == 0 and 8 <= ts.hour <= 20:
        mult *= 1.20  # episodio disperso pero reproducible
    return mult


def build_congestion_sintetica(
    out_csv: Path,
    dataset_csv: Path,
    rango_inicio: str = "2026-07-01 00:00:00",
    rango_fin: str = "2026-08-31 23:00:00",
    seed: int = 42,
) -> pd.DataFrame:
    """Genera el CSV sintetico (estacion, hora) -> ratio_congestion.

    Velocidades simuladas a partir del patron: se asume free_flow ~ 50 km/h en corredor.
    """
    df = pd.read_csv(dataset_csv)
    est = df.groupby("Estacion")[["Latitud", "Longitud"]].first().reset_index()

    idx = pd.date_range(rango_inicio, rango_fin, freq="h")
    filas = []
    for _, r in est.iterrows():
        for ts in idx:
            es_habil = ts.weekday() < 5
            ratio = _ratio_por_hora(ts.hour, es_habil, seed) * _aplica_eventos(ts, es_habil, seed)
            ratio = min(max(ratio, 1.0), 3.0)
            free = 50.0
            cur = free / ratio
            filas.append({
                "Fecha_Hora": ts,
                "Estacion": r["Estacion"],
                "Latitud": r["Latitud"],
                "Longitud": r["Longitud"],
                "freeFlowSpeed_kph": round(free, 2),
                "currentSpeed_kph": round(cur, 2),
                "ratio_congestion": round(ratio, 4),
            })

    out = pd.DataFrame(filas)
    out.to_csv(out_csv, index=False)
    return out


def get_ratio(estacion: str, ts: pd.Timestamp, cache_csv: Path) -> float:
    """Devuelve el ratio de congestion para (estacion, timestamp) desde el cache sintetico.

    En produccion este metodo se reemplaza por la consulta a TomTom Traffic real
    (`flowSegmentData`) con la key de la variable de entorno `TOMMTOM_KEY`.
    """
    cache = pd.read_csv(cache_csv, parse_dates=["Fecha_Hora"])
    hit = cache[(cache["Estacion"] == estacion) & (cache["Fecha_Hora"] == ts)]
    if len(hit):
        return float(hit["ratio_congestion"].iloc[0])
    # fallback: ratio promedio de la hora (si la estacion no esta en el cache)
    if ts in cache["Fecha_Hora"].values:
        return float(cache.loc[cache["Fecha_Hora"] == ts, "ratio_congestion"].mean())
    return 1.15


if __name__ == "__main__":
    import sys

    def repo_root():
        p = Path(__file__).resolve()
        for up in [p] + list(p.parents):
            if (up / "deliveries").is_dir():
                return up
        raise FileNotFoundError("No se encontro 'deliveries'")

    root = repo_root()
    dataset = root / "deliveries" / "week07" / "data_processed" / "dataset_limpio.csv"
    salida = root / "deliveries" / "week07" / "data_processed" / "congestion_sintetica.csv"
    tabla = build_congestion_sintetica(salida, dataset)
    print("Filas:", tabla.shape)
    print(tabla.head())
    print("\nGuardado en:", salida)