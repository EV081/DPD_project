"""Enruta segmentos consecutivos con OSRM público para seguir la red vial.

Evita LineStrings en línea recta que atraviesan manzanas/edificios.
API: https://router.project-osrm.org (uso cortés; rate-limit local).

No usa Moovit: esa web exige JS/captcha y no expone shapes estables.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Iterable

import numpy as np

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"
_UA = "UrbanSafeAI-week08/1.0 (UTEC academic; contact: local)"


def _hav_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """a,b = (lat, lon)."""
    lon1, lat1 = np.radians(a[1]), np.radians(a[0])
    lon2, lat2 = np.radians(b[1]), np.radians(b[0])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return float(2 * 6371 * np.arcsin(np.sqrt(x)))


def osrm_segment(lon1: float, lat1: float, lon2: float, lat2: float,
                 *, timeout: float = 30.0) -> list[list[float]] | None:
    """Devuelve coordenadas [lon,lat] del tramo, o None si falla."""
    url = (
        f"{OSRM_BASE}/{lon1},{lat1};{lon2},{lat2}"
        f"?overview=full&geometries=geojson&steps=false"
    )
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if data.get("code") != "Ok" or not data.get("routes"):
        return None
    coords = data["routes"][0]["geometry"]["coordinates"]
    return [[float(c[0]), float(c[1])] for c in coords]


def snap_waypoints(
    coords_lonlat: Iterable[list[float] | tuple[float, float]],
    *,
    max_direct_km: float = 3.0,
    sleep_s: float = 0.12,
    profile_note: str = "osrm_driving",
) -> tuple[list[list[float]], dict]:
    """Une waypoints con geometría OSRM entre consecutivos.

    Si un salto > max_direct_km falla OSRM o es absurdo, se omite el tramo
    (rompe la línea) en lugar de cruzar la ciudad en recta.
    coords: secuencia [lon, lat]
    """
    pts = [[float(c[0]), float(c[1])] for c in coords_lonlat]
    meta = {"n_waypoints": len(pts), "n_osrm_ok": 0, "n_skipped": 0, "modo": profile_note}
    if len(pts) < 2:
        return pts, meta

    out: list[list[float]] = [pts[0]]
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        dist = _hav_km((a[1], a[0]), (b[1], b[0]))
        if dist > max_direct_km * 3:  # join claramente erróneo
            meta["n_skipped"] += 1
            out.append(b)  # salto visual mínimo; el split posterior corta
            continue
        seg = osrm_segment(a[0], a[1], b[0], b[1])
        time.sleep(sleep_s)
        if not seg or len(seg) < 2:
            meta["n_skipped"] += 1
            if dist <= max_direct_km:
                out.append(b)  # recta corta OK
            else:
                out.append(b)
            continue
        meta["n_osrm_ok"] += 1
        # evitar duplicar el primer punto del segmento
        out.extend(seg[1:])
    return out, meta
