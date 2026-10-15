"""Distancia entre paradas consecutivas de cada ruta y sentido -> ``geo/tramos_osrm.csv``.

Offline (como ``build_trazados.py``): lee ``paradero_ruta`` de la BD ya cargada
(``run paraderos``), consulta OSRM público para la distancia por calles y escribe un CSV con
claves estables (sistema, ruta, direccion, orden). ``ingest_paraderos`` lo carga a la tabla
``tramo`` y calcula ahí la duración, de modo que ajustar velocidades no requiere volver a OSRM.

  python scripts/04_geo_build/build_tramos.py   # desde week10/code, con PG* del entorno
Escribe en GEO_DIR (week10/data_processed/geo); export/tramos.csv es la copia versionada.
Reanuda: los tramos ya presentes en el CSV no se vuelven a consultar.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.request
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE))

from pipeline import config  # noqa: E402
from storage import db  # noqa: E402

OSRM = "https://router.project-osrm.org/route/v1/driving"
UA = "UrbanSafeAI-week10/1.0 (UTEC academic)"
CIRCUITO = 1.3        # factor calle/recta cuando OSRM no responde
SIN_OSRM = {"metro_l1"}   # via ferrea: distancia recta entre estaciones
CAMPOS = ["sistema", "ruta", "direccion", "orden_desde", "orden_hasta", "dist_m",
          "duracion_osrm_s", "fuente"]
SALIDA = config.GEO_DIR / "tramos_osrm.csv"


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(h))


def osrm(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float] | None:
    url = f"{OSRM}/{a[1]},{a[0]};{b[1]},{b[0]}?overview=false"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if d.get("code") != "Ok" or not d.get("routes"):
        return None
    return float(d["routes"][0]["distance"]), float(d["routes"][0]["duration"])


def guardar(filas: list[dict]) -> None:
    """Escribe el CSV completo (se llama a intervalos para que una corrida cortada se pueda reanudar)."""
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tmp = SALIDA.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    tmp.replace(SALIDA)


def _clave(r: dict) -> tuple:
    return (r["sistema"], r["ruta"], int(r["direccion"]), int(r["orden_desde"]))


def _unir(out: list[dict], hechos: dict) -> list[dict]:
    """Lo calculado en esta corrida + lo previo que aun no se alcanzo (no se pierde si se corta antes)."""
    vistos = {_clave(r) for r in out}
    return out + [r for k, r in hechos.items() if k not in vistos]


def main() -> None:
    conn = db.connect()
    filas = conn.execute(
        """
        SELECT r.sistema, r.codigo AS ruta, pr.direccion, pr.orden, p.lat, p.lon
        FROM paradero_ruta pr JOIN ruta r ON r.id = pr.ruta_id JOIN paradero p ON p.id = pr.paradero_id
        WHERE pr.orden IS NOT NULL ORDER BY r.sistema, r.codigo, pr.direccion, pr.orden
        """
    ).fetchall()
    conn.close()

    hechos: dict[tuple, dict] = {}
    if SALIDA.exists():
        with SALIDA.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                hechos[(r["sistema"], r["ruta"], int(r["direccion"]), int(r["orden_desde"]))] = r

    pares = []
    for ant, act in zip(filas, filas[1:]):
        if (ant["sistema"], ant["ruta"], ant["direccion"]) == (act["sistema"], act["ruta"], act["direccion"]):
            pares.append((ant, act))
    print(f"[tramos] {len(pares)} tramos, {len(hechos)} ya calculados", flush=True)

    out: list[dict] = []
    try:
        _calcular(pares, hechos, out)
    finally:
        # incluso con Ctrl+C o un error: lo calculado hasta aqui queda en el CSV y la proxima corrida sigue
        guardar(_unir(out, hechos))
    print(f"[tramos] {SALIDA}: {len(out)} filas")


def _calcular(pares: list, hechos: dict, out: list[dict]) -> None:
    n_osrm = n_recta = nuevos = 0
    for i, (a, b) in enumerate(pares, 1):
        k = (a["sistema"], a["ruta"], a["direccion"], a["orden"])
        if k in hechos:
            out.append(hechos[k])
            continue
        pa, pb = (a["lat"], a["lon"]), (b["lat"], b["lon"])
        res = None if a["sistema"] in SIN_OSRM else osrm(pa, pb)
        if a["sistema"] not in SIN_OSRM:
            time.sleep(0.15)
        if res:
            dist, dur, fuente = res[0], res[1], "osrm"
            n_osrm += 1
        else:
            fac = 1.0 if a["sistema"] in SIN_OSRM else CIRCUITO
            dist, dur, fuente = haversine_m(pa, pb) * fac, "", "haversine"
            n_recta += 1
        out.append({"sistema": a["sistema"], "ruta": a["ruta"], "direccion": a["direccion"],
                    "orden_desde": a["orden"], "orden_hasta": b["orden"], "dist_m": round(dist, 1),
                    "duracion_osrm_s": round(dur, 1) if dur != "" else "", "fuente": fuente})
        nuevos += 1
        if nuevos % 100 == 0:
            guardar(_unir(out, hechos))
        if i % 200 == 0:
            print(f"[tramos] {i}/{len(pares)} (osrm nuevos={n_osrm}, haversine nuevos={n_recta})", flush=True)
    print(f"[tramos] osrm nuevos={n_osrm}, haversine nuevos={n_recta}")


if __name__ == "__main__":
    main()
