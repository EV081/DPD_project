"""Corrige estaciones del Metropolitano cuya coordenada OSM por nombre cae lejos de la linea troncal.

Arbitro objetivo: una estacion debe estar sobre la linea del Metropolitano (relaciones OSM
`network=Metropolitano`, `trazados_metropolitano_servicios.geojson`). Si la coordenada actual esta a mas
de UMBRAL_M de la linea y el resultado de Google (`contraste_google_oficiales.csv`) esta a <= UMBRAL_M,
se usa el de Google. Las que ninguna fuente deja sobre la linea quedan marcadas para revision manual.

Idempotente: guarda la coordenada original en la propiedad `coord_osm`. Reejecutar tras build_trazados.py.
    python scripts/03_georef/corregir_troncal_con_google.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

CODEDIR = Path(__file__).resolve().parent
FUENTES = CODEDIR.parents[2] / "data" / "fuentes"
GEO = FUENTES / "geo"
GEOJSON = CODEDIR.parents[2] / "data_processed" / "geo"
UMBRAL_M = 150.0


def _norm(s: str) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", str(s or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


_RUIDO = {"estacion", "metropolitano", "terminal", "embarque", "de", "la", "del", "los", "las", "el", "y",
          "norte", "sur", "hacia"}


def _nucleo(nombre: str) -> frozenset[str]:
    """Nombre sin palabras de relleno: 'Estacion Jiron De La Union' != 'Union'."""
    return frozenset(t for t in _norm(nombre).split() if t not in _RUIDO)


def _a_metros(lat, lon, lat0):
    return np.column_stack([np.asarray(lon) * 111320.0 * np.cos(np.radians(lat0)), np.asarray(lat) * 111320.0])


def dist_a_lineas(lat: float, lon: float, lineas: list[np.ndarray]) -> float:
    p = _a_metros([lat], [lon], lat)[0]
    mejor = float("inf")
    for ln in lineas:                       # ln: (n, 2) = lat, lon
        q = _a_metros(ln[:, 0], ln[:, 1], lat)
        a, b = q[:-1], q[1:]
        ab = b - a
        t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-9), 0, 1)
        d = np.linalg.norm(a + t[:, None] * ab - p, axis=1)
        mejor = min(mejor, float(d.min()))
    return mejor


def main() -> None:
    lineas = []
    for f in json.loads((GEOJSON / "trazados_metropolitano_servicios.geojson").read_text(encoding="utf-8"))["features"]:
        c = np.array(f["geometry"]["coordinates"])
        lineas.append(np.column_stack([c[:, 1], c[:, 0]]))
    contraste = {_norm(r["nombre"]): r for r in csv.DictReader(
        (FUENTES / "contraste_google_oficiales.csv").open(encoding="utf-8")) if r["sistema"] == "troncal"}

    # correcciones hechas a mano (prioridad sobre OSM y Google)
    manual: dict[str, tuple[float, float]] = {}
    mc = FUENTES / "correcciones_troncal.csv"
    if mc.exists():
        for r in csv.DictReader(mc.open(encoding="utf-8")):
            manual[_norm(r["estacion"])] = (float(r["lat"]), float(r["lon"]))

    arch = GEOJSON / "puntos_troncal.geojson"
    fc = json.loads(arch.read_text(encoding="utf-8"))
    cambios, pendientes = [], []
    nuevas: dict[str, tuple[float, float]] = {}
    for f in fc["features"]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        if "coord_osm" in p:                              # reejecucion: partir de la original
            lon, lat = p["coord_osm"]
            f["geometry"]["coordinates"] = [lon, lat]
            p["match"] = "osm"
            p.pop("coord_osm")
        d_nuestra = dist_a_lineas(lat, lon, lineas)
        p["dist_a_troncal_m"] = round(d_nuestra)
        if _norm(p["estacion"]) in manual:                # revision manual: manda
            mlat, mlon = manual[_norm(p["estacion"])]
            p["coord_osm"] = [lon, lat]
            p["match"] = "manual"
            p["dist_a_troncal_m"] = round(dist_a_lineas(mlat, mlon, lineas))
            f["geometry"]["coordinates"] = [mlon, mlat]
            nuevas[_norm(p["estacion"])] = (mlat, mlon)
            cambios.append((p["estacion"] + " (manual)", d_nuestra))
            continue
        r = contraste.get(_norm(p["estacion"]))
        if d_nuestra > UMBRAL_M:
            mismo_nombre = bool(r) and _nucleo(r["google_nombre"]) == _nucleo(p["estacion"])
            if r and r["google_lat"] and mismo_nombre and \
                    dist_a_lineas(float(r["google_lat"]), float(r["google_lon"]), lineas) <= UMBRAL_M:
                p["coord_osm"] = [lon, lat]
                p["match"] = "google"
                f["geometry"]["coordinates"] = [float(r["google_lon"]), float(r["google_lat"])]
                nuevas[_norm(p["estacion"])] = (float(r["google_lat"]), float(r["google_lon"]))
                cambios.append((p["estacion"], d_nuestra))
            else:
                motivo = "" if (r and mismo_nombre) or not r or not r["google_nombre"] else \
                    f" (Google devolvio otra estacion: {r['google_nombre']!r})"
                pendientes.append((p["estacion"], d_nuestra, motivo))
    arch.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")

    # los puntos por servicio heredan la coordenada de la estacion
    arch2 = GEOJSON / "puntos_metropolitano_servicios.geojson"
    if arch2.exists():
        sv = json.loads(arch2.read_text(encoding="utf-8"))
        n = 0
        for f in sv["features"]:
            k = _norm(f["properties"].get("estacion"))
            for alias, canon in (("canavaly moreyra", "canaval y moreyra"), ("plaza flores", "plaza de flores"),
                                 ("dos mayo", "2 de mayo"), ("28julio", "28 de julio")):
                if k == alias:
                    k = canon
            if k in nuevas:
                f["geometry"]["coordinates"] = [nuevas[k][1], nuevas[k][0]]
                n += 1
        arch2.write_text(json.dumps(sv, ensure_ascii=False), encoding="utf-8")

    print(f"corregidas con Google: {len(cambios)}")
    for nom, d in cambios:
        print(f"   {nom}: estaba a {d:.0f} m de la linea")
    print(f"sin resolver (revision manual): {len(pendientes)}")
    for nom, d, motivo in pendientes:
        print(f"   {nom}: a {d:.0f} m de la linea{motivo}")


if __name__ == "__main__":
    main()
