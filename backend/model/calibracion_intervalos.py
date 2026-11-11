"""Cobertura temporal: cada día se calibra exclusivamente con días anteriores."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _cuantil(values, level):
    n = len(values)
    adjusted = min(np.ceil((n + 1) * level) / n, 1.0)
    return float(np.quantile(values, adjusted, method="higher"))


def cobertura_causal(observed, predicted, scale, days, window=14, coverage=.8) -> dict:
    """Arreglos día × serie × hora; los primeros `window` días solo calibran.

    Las predicciones deben haberse obtenido fuera de muestra. Esta función no
    entrena modelos ni convierte predicciones de entrenamiento en una prueba.
    """
    observed, predicted, scale = (np.asarray(x, dtype=float) for x in (observed, predicted, scale))
    dates = pd.DatetimeIndex(days)
    if observed.shape != predicted.shape or observed.shape != scale.shape or observed.ndim != 3:
        raise ValueError("Se necesitan tres arreglos iguales de día × serie × hora.")
    if len(dates) != len(observed) or not dates.is_monotonic_increasing or dates.has_duplicates:
        raise ValueError("Las fechas deben estar ordenadas, sin repetirse.")
    if window < 1 or len(dates) <= window or not 0 < coverage < 1:
        raise ValueError("No hay suficientes días o la cobertura no es válida.")
    if not all(np.isfinite(x).all() for x in (observed, predicted, scale)) or (scale <= 0).any():
        raise ValueError("Los datos deben ser finitos y la escala positiva.")
    alpha = 1 - coverage
    covered, total = 0, 0
    for i in range(window, len(dates)):
        residual = (observed[i - window:i] - predicted[i - window:i]) / scale[i - window:i]
        low = np.empty_like(predicted[i])
        high = np.empty_like(predicted[i])
        for hour in range(predicted.shape[2]):
            errors = residual[:, :, hour].ravel()
            low[:, hour] = np.maximum(0, predicted[i, :, hour] - _cuantil(-errors, 1 - alpha / 2) * scale[i, :, hour])
            high[:, hour] = np.maximum(0, predicted[i, :, hour] + _cuantil(errors, 1 - alpha / 2) * scale[i, :, hour])
        covered += int(((observed[i] >= low) & (observed[i] <= high)).sum())
        total += observed[i].size
    return {"coverage": covered / total, "target": coverage, "evaluated_cells": total,
            "evaluated_days": len(dates) - window, "first_evaluation": dates[window].date().isoformat(),
            "last_evaluation": dates[-1].date().isoformat(), "calibration_window_days": window,
            "protocol": "cada día usa solamente los residuos de los 14 días anteriores" if window == 14 else
                        f"cada día usa solamente los residuos de los {window} días anteriores"}
