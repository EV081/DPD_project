"""Trayecto a pie entre dos puntos por las calles (LocationIQ Directions), con caché en memoria.

Lo usa el transbordo: la red peatonal del Eje 2 son islas alrededor de las estaciones y no conecta paraderos
lejanos entre sí. El mismo par de paraderos se pide una sola vez: el resultado queda en caché.
"""
import json
import os
import urllib.error
import urllib.request
from collections import OrderedDict
from threading import Lock

URL = "https://us1.locationiq.com/v1/directions/walking/{lon1},{lat1};{lon2},{lat2}"
MAX_CACHE = 2000
TIMEOUT_S = 8

_cache: "OrderedDict[tuple, dict]" = OrderedDict()
_lock = Lock()


class CaminataError(Exception):
    pass


def _clave(lat1, lon1, lat2, lon2) -> tuple:
    return tuple(round(float(v), 5) for v in (lat1, lon1, lat2, lon2))   # ~1 m: mismo paradero, misma clave


def _pedir(lat1, lon1, lat2, lon2) -> dict:
    token = os.getenv("LOCATIONIQ_TOKEN")
    if not token:
        raise CaminataError("Falta LOCATIONIQ_TOKEN")
    url = URL.format(lat1=lat1, lon1=lon1, lat2=lat2, lon2=lon2) + f"?key={token}&overview=full&geometries=geojson"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise CaminataError(f"LocationIQ respondió {e.code}") from None   # sin la URL: lleva la clave
    except Exception as e:
        raise CaminataError(type(e).__name__) from None


def interpretar(resp: dict) -> dict:
    rutas = resp.get("routes") or []
    if resp.get("code") != "Ok" or not rutas:
        raise CaminataError("Sin ruta a pie entre esos puntos")
    r = rutas[0]
    coords = (r.get("geometry") or {}).get("coordinates") or []
    if len(coords) < 2:
        raise CaminataError("Trazado vacío")
    return {
        "distancia_m": round(float(r["distance"]), 1),
        "minutos": round(float(r["duration"]) / 60, 1),
        "geojson": {"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": coords}},
    }


def ruta_a_pie(lat1: float, lon1: float, lat2: float, lon2: float, pedir=_pedir) -> dict:
    clave = _clave(lat1, lon1, lat2, lon2)
    with _lock:
        if clave in _cache:
            _cache.move_to_end(clave)
            return _cache[clave]
    out = interpretar(pedir(lat1, lon1, lat2, lon2))
    with _lock:
        _cache[clave] = out
        while len(_cache) > MAX_CACHE:
            _cache.popitem(last=False)
    return out
