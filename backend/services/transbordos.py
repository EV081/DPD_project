"""Viajes con un transbordo: "toma el servicio A hasta el paradero X, camina hasta Y y toma el servicio B".

Se usa cuando no hay ruta directa (o como alternativa). Es una búsqueda sobre las paradas de cada servicio:

* Corredores: cada (ruta, sentido) es una secuencia ORDENADA de paradas (`paradas_corredores.geojson`, orden de ATU).
  Solo se puede viajar hacia delante en esa secuencia.
* Metropolitano y Metro L1: son troncales que van en los dos sentidos. Del Metropolitano solo se sabe qué estaciones
  sirve cada servicio (el campo `orden` de ese archivo es alfabético, no geográfico), así que se puede ir de cualquiera
  de sus estaciones a otra. Los alimentadores quedan fuera: sus datos no traen el orden de las paradas.

Los tiempos son estimaciones simples (velocidades y esperas típicas por sistema); no usan el pronóstico de aforo.
"""
from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np

GEO_DIR = Path(__file__).resolve().parent.parent / "data" / "geo"

# Estimaciones por sistema (km/h de recorrido incluyendo paradas, y espera media en el paradero)
VEL_KMH = {"corredores": 15.0, "metropolitano": 22.0, "metro_l1": 30.0}
ESPERA_MIN = {"corredores": 6.0, "metropolitano": 4.0, "metro_l1": 5.0}
CAMINATA_M_MIN = 80.0                 # ~4,8 km/h
PENALIZACION_TRANSBORDO_MIN = 4.0     # incomodidad de cambiar de bus
SINUOSIDAD = 1.25                     # recorrido real / línea recta, para servicios sin orden de paradas
TRONCALES = {"metropolitano", "metro_l1"}
MAX_PARADA_A_ESTACION_M = 150.0       # una parada de corredor se asocia a la estación más cercana de su ruta


def normalizar(texto: str) -> str:
    s = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def _dist(lat0: float, lon0: float, lats, lons):
    """Metros desde un punto a uno o varios (aproximación plana, suficiente a escala de ciudad)."""
    dx = (np.asarray(lons) - lon0) * 111320.0 * math.cos(math.radians(lat0))
    dy = (np.asarray(lats) - lat0) * 110540.0
    return np.hypot(dx, dy)


@dataclass
class Servicio:
    id: str
    sistema: str
    codigo: str            # "301", "Expreso 5", "Metro L1"…
    bidireccional: bool
    ids: list[str]         # id de estación/paradero de cada parada
    nombres: list[str]
    lat: np.ndarray
    lon: np.ndarray
    acum: np.ndarray       # metros acumulados a lo largo de la secuencia (solo útil si está ordenado)

    def siguientes(self, i: int) -> np.ndarray:
        """Índices donde se puede bajar si se sube en i."""
        n = len(self.ids)
        if self.bidireccional:
            return np.array([k for k in range(n) if k != i], dtype=int)
        return np.arange(i + 1, n, dtype=int)

    def anteriores(self, n: int) -> np.ndarray:
        """Índices donde se puede subir si se quiere bajar en n."""
        total = len(self.ids)
        if self.bidireccional:
            return np.array([k for k in range(total) if k != n], dtype=int)
        return np.arange(0, n, dtype=int)

    def viaje_min(self, i: int, j: int) -> float:
        if self.bidireccional:
            metros = float(_dist(self.lat[i], self.lon[i], self.lat[j], self.lon[j])) * SINUOSIDAD
        else:
            metros = float(abs(self.acum[j] - self.acum[i]))
        return metros / 1000.0 / VEL_KMH[self.sistema] * 60.0


def _servicio(id_, sistema, codigo, bidireccional, paradas) -> Servicio | None:
    """paradas: lista de (id, nombre, lat, lon). Quita repetidas consecutivas."""
    limpias = []
    for p in paradas:
        if limpias and limpias[-1][0] == p[0]:
            continue
        limpias.append(p)
    if len(limpias) < 2:
        return None
    lat = np.array([p[2] for p in limpias], dtype=float)
    lon = np.array([p[3] for p in limpias], dtype=float)
    acum = np.zeros(len(limpias))
    for k in range(1, len(limpias)):
        acum[k] = acum[k - 1] + float(_dist(lat[k - 1], lon[k - 1], lat[k], lon[k]))
    return Servicio(id_, sistema, str(codigo), bidireccional, [p[0] for p in limpias], [p[1] for p in limpias], lat, lon, acum)


def construir_servicios(estaciones: list[dict], paradas_corredores: list[dict], servicios_metro: list[dict]) -> list[Servicio]:
    """Arma los servicios a partir de las estaciones de la app y de los archivos de paradas (GeoJSON features)."""
    out: list[Servicio] = []

    # --- Corredores: secuencias ordenadas por (ruta, sentido), cada parada asociada a una estación de esa ruta
    por_ruta: dict[str, list[dict]] = {}
    for e in estaciones:
        if e.get("system") == "corredores":
            por_ruta.setdefault(str((e.get("raw_properties") or {}).get("ruta")), []).append(e)
    grupos: dict[tuple[str, int], list[tuple[int, dict]]] = {}
    for f in paradas_corredores:
        p = f.get("properties", {})
        grupos.setdefault((str(p.get("ruta")), int(p.get("direccion") or 1)), []).append((int(p.get("orden") or 0), f))
    for (ruta, sentido), items in grupos.items():
        candidatas = por_ruta.get(ruta, [])
        if not candidatas:
            continue
        clat = np.array([c["latitude"] for c in candidatas])
        clon = np.array([c["longitude"] for c in candidatas])
        paradas = []
        for _, f in sorted(items, key=lambda t: t[0]):
            lon, lat = f["geometry"]["coordinates"][:2]
            d = _dist(lat, lon, clat, clon)
            k = int(np.argmin(d))
            if d[k] <= MAX_PARADA_A_ESTACION_M:
                e = candidatas[k]
                paradas.append((e["id"], e["name"], e["latitude"], e["longitude"]))
        s = _servicio(f"corredores:{ruta}:{sentido}", "corredores", ruta, False, paradas)
        if s:
            out.append(s)

    # --- Metropolitano: por servicio, las estaciones que sirve (sin orden fiable → bidireccional)
    metro = [e for e in estaciones if e.get("system") == "metropolitano"]
    por_nombre = {normalizar(e["name"]): e for e in metro}
    servicios: dict[str, list[tuple]] = {}
    for f in servicios_metro:
        p = f.get("properties", {})
        e = por_nombre.get(normalizar(p.get("estacion")))
        if e is None and metro:   # sin coincidencia por nombre: la estación más cercana si está a menos de 300 m
            lon, lat = f["geometry"]["coordinates"][:2]
            d = _dist(lat, lon, [m["latitude"] for m in metro], [m["longitude"] for m in metro])
            k = int(np.argmin(d))
            e = metro[k] if d[k] <= 300 else None
        if e is not None:
            servicios.setdefault(str(p.get("servicio_nombre")), []).append((e["id"], e["name"], e["latitude"], e["longitude"]))
    for nombre, paradas in servicios.items():
        s = _servicio(f"metropolitano:{nombre}", "metropolitano", nombre, True, list(dict.fromkeys(paradas)))
        if s:
            out.append(s)

    # --- Metro L1: todas sus estaciones, en los dos sentidos
    l1 = [(e["id"], e["name"], e["latitude"], e["longitude"]) for e in estaciones if e.get("system") == "metro_l1"]
    s = _servicio("metro_l1:L1", "metro_l1", "Metro L1", True, l1)
    if s:
        out.append(s)
    return out


def cargar_servicios(estaciones: list[dict]) -> list[Servicio]:
    def leer(nombre):
        try:
            return json.loads((GEO_DIR / nombre).read_text(encoding="utf-8")).get("features", [])
        except (OSError, ValueError):
            return []
    return construir_servicios(estaciones, leer("paradas_corredores.geojson"), leer("puntos_metropolitano_servicios.geojson"))


def _mas_cercanas(s: Servicio, lat: float, lon: float, radio_m: float, cuantas: int = 2):
    d = _dist(lat, lon, s.lat, s.lon)
    return [(int(i), float(d[i])) for i in np.argsort(d)[:cuantas] if d[i] <= radio_m]


def buscar_transbordos(servicios: list[Servicio], origen: tuple[float, float], destino: tuple[float, float],
                       radio_m: float = 1000.0, caminata_max_m: float = 300.0, limite: int = 5) -> list[dict]:
    """Viajes de dos tramos, ordenados por tiempo total estimado. Cada uno trae el primer tramo en los campos de una
    ruta normal y el segundo en `transbordo`."""
    subidas = [(s, i, d) for s in servicios for i, d in _mas_cercanas(s, origen[0], origen[1], radio_m)]
    bajadas = [(s, n, d) for s in servicios for n, d in _mas_cercanas(s, destino[0], destino[1], radio_m)]
    mejores: dict[tuple[str, str], dict] = {}

    for s1, i, d_origen in subidas:
        idx1 = s1.siguientes(i)
        if not len(idx1):
            continue
        for s2, n, d_destino in bajadas:
            if s1.id == s2.id or (s1.sistema == s2.sistema and s1.codigo == s2.codigo):
                continue
            if s1.sistema == s2.sistema and s1.sistema in TRONCALES:
                continue   # dos servicios de la misma troncal ya son un viaje directo por sistema
            idx2 = s2.anteriores(n)
            if not len(idx2):
                continue
            # distancia a pie entre cada parada donde se puede bajar del 1.º y cada parada donde se puede subir al 2.º
            D = np.hypot(
                (s1.lon[idx1][:, None] - s2.lon[idx2][None, :]) * 111320.0 * math.cos(math.radians(origen[0])),
                (s1.lat[idx1][:, None] - s2.lat[idx2][None, :]) * 110540.0,
            )
            for k, m in zip(*np.nonzero(D <= caminata_max_m)):
                j, mm = int(idx1[k]), int(idx2[m])
                if mm == n or j == i:
                    continue
                caminata_m = d_origen + float(D[k, m]) + d_destino
                viaje1, viaje2 = s1.viaje_min(i, j), s2.viaje_min(mm, n)
                espera = ESPERA_MIN[s1.sistema] + ESPERA_MIN[s2.sistema]
                costo = caminata_m / CAMINATA_M_MIN + viaje1 + viaje2 + espera + PENALIZACION_TRANSBORDO_MIN
                clave = (s1.id, s2.id)
                if clave in mejores and mejores[clave]["costo_generalizado_min"] <= costo:
                    continue
                mejores[clave] = {
                    "type": "TRANSBORDO",
                    "route_code": s1.codigo, "system": s1.sistema,
                    "boarding_station": s1.nombres[i], "boarding_id": s1.ids[i], "origin_walk_m": round(d_origen, 1),
                    "leaving_station": s1.nombres[j], "leaving_id": s1.ids[j],
                    "dest_walk_m": round(d_destino, 1),
                    "transbordo": {
                        "route_code": s2.codigo, "system": s2.sistema,
                        "caminata_m": round(float(D[k, m]), 1),
                        "boarding_station": s2.nombres[mm], "boarding_id": s2.ids[mm],
                        "leaving_station": s2.nombres[n], "leaving_id": s2.ids[n],
                    },
                    "caminata_min": round(caminata_m / CAMINATA_M_MIN, 1),
                    "espera_min": round(espera, 1),
                    "viaje_min": round(viaje1 + viaje2, 1),
                    "costo_generalizado_min": round(costo, 1),
                }
    return _agrupar(sorted(mejores.values(), key=lambda r: r["costo_generalizado_min"]))[:limite]


def _agrupar(viajes: list[dict]) -> list[dict]:
    """Une los viajes que usan los mismos paraderos y solo cambian de número de ruta ("Ruta 201 / 204 / 206"): son el
    mismo viaje para quien espera el bus. Conserva el orden por costo (queda el de menor costo de cada grupo)."""
    grupos: dict[tuple, dict] = {}
    for v in viajes:
        t = v["transbordo"]
        # Por nombre de paradero: dos rutas que paran en "Javier Prado" tienen códigos de paradero distintos
        clave = (v["system"], normalizar(v["boarding_station"]), normalizar(v["leaving_station"]),
                 t["system"], normalizar(t["boarding_station"]), normalizar(t["leaving_station"]))
        g = grupos.get(clave)
        if g is None:
            grupos[clave] = {**v, "transbordo": dict(t), "_a": [v["route_code"]], "_b": [t["route_code"]]}
        else:
            if v["route_code"] not in g["_a"]:
                g["_a"].append(v["route_code"])
            if t["route_code"] not in g["_b"]:
                g["_b"].append(t["route_code"])
    out = []
    for g in grupos.values():
        g["route_code"] = " / ".join(g.pop("_a"))
        g["transbordo"]["route_code"] = " / ".join(g.pop("_b"))
        out.append(g)
    return out


# Servicios en memoria (se arman una vez; las estaciones ya están en caché)
_SERVICIOS: list[Servicio] | None = None


def servicios_en_memoria(estaciones: list[dict]) -> list[Servicio]:
    global _SERVICIOS
    if _SERVICIOS is None:
        _SERVICIOS = cargar_servicios(estaciones)
    return _SERVICIOS
