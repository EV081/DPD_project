"""Ubica paradas de alimentadores por interpolacion a lo largo de la ruta usando el mapa de ATU.

Los mapas PNG traen los paraderos numerados (azul = sentido 1, gris = sentido 2) sobre la linea de
ruta. La geometria del dibujo es estilizada, pero el ORDEN y la proporcion de distancia entre paradas
consecutivas se conservan. Donde ya tenemos paradas bien ubicadas (anclas), una parada intermedia se
coloca en la fraccion de distancia que ocupa en la imagen entre sus dos anclas vecinas.

No se asume escala ni rotacion del dibujo; solo monotonia local. Se valida con leave-one-out
sobre las propias anclas (--validar) antes de usar nada.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

CODEDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODEDIR))
import georef_mapas as G  # noqa: E402
import geocodificar_alimentadores as GA  # noqa: E402

FUENTES = GA.FUENTES
GEO = FUENTES / "geo"
COLOR_BLOQUE = {"claro": 1, "gris": 2}


def mapa_principal(grupo: str, servicio: str) -> list[Path]:
    """PNG(s) grandes del servicio (mapa de ruta)."""
    d = GEO / "mapas_alimentadores" / grupo / servicio
    return sorted([p for p in d.glob("*.png") if p.stat().st_size > 300_000], key=lambda p: -p.stat().st_size)


def leer_marcadores(png: Path) -> dict[tuple[int, int], tuple[float, float]]:
    """(bloque, numero) -> (x, y); descarta numeros repetidos dentro de un color."""
    cnt: dict[tuple[str, int], list] = {}
    for m in G.detectar_discos_alimentador(png):
        if m.numero:
            cnt.setdefault((m.color, m.numero), []).append(m)
    return {(COLOR_BLOQUE[c], n): (v[0].x, v[0].y) for (c, n), v in cnt.items() if len(v) == 1}


def _es_ancla(r: dict) -> bool:
    if not r["lat"]:
        return False
    if r["confianza"] in ("verificada", "alta"):
        return True
    return r["confianza"] == "media" and r.get("corroborado_google") == "1"


def interpolar(px: dict[int, tuple[float, float]], anclas: dict[int, tuple[float, float]], n: int):
    """Posicion mundial de la parada `n` entre sus anclas vecinas (por orden)."""
    if n not in px:
        return None
    previos = [k for k in anclas if k < n and k in px]
    siguientes = [k for k in anclas if k > n and k in px]
    if not previos or not siguientes:
        return None
    a, b = max(previos), min(siguientes)
    pa, pb, pn = np.array(px[a]), np.array(px[b]), np.array(px[n])
    # fraccion de la distancia de la imagen recorrida entre las dos anclas, pasando por la parada
    d1, d2 = np.linalg.norm(pn - pa), np.linalg.norm(pb - pn)
    if d1 + d2 < 1e-6:
        return None
    f = d1 / (d1 + d2)
    (la, oa), (lb, ob) = anclas[a], anclas[b]
    return (la + f * (lb - la), oa + f * (ob - oa), a, b)


def cargar_estado() -> list[dict]:
    return list(csv.DictReader((FUENTES / "alimentadores_paradas_geo.csv").open(encoding="utf-8")))


def por_servicio(filas: list[dict]) -> dict[tuple[str, str], dict[int, list[dict]]]:
    out: dict = {}
    for r in filas:
        out.setdefault((r["grupo"], r["servicio"].split("/")[-1]), {}).setdefault(int(r["bloque"]), []).append(r)
    return out


def validar() -> None:
    filas = cargar_estado()
    errs, por_serv, sin_mapa = [], {}, []
    for (grupo, serv), bl in por_servicio(filas).items():
        pngs = mapa_principal(grupo, serv)
        if not pngs:
            sin_mapa.append(serv)
            continue
        px_all = leer_marcadores(pngs[0])
        for b, L in bl.items():
            px = {n: xy for (bb, n), xy in px_all.items() if bb == b}
            anclas = {int(r["orden"]): (float(r["lat"]), float(r["lon"])) for r in L if _es_ancla(r)}
            for n, (lat, lon) in anclas.items():
                res = interpolar(px, {k: v for k, v in anclas.items() if k != n}, n)   # leave-one-out
                if res is None:
                    continue
                e = GA.dist_m((res[0], res[1]), (lat, lon))
                errs.append(e)
                por_serv.setdefault(serv, []).append(e)
    e = np.array(errs)
    print(f"leave-one-out sobre anclas: n={len(e)} | mediana {np.median(e):.0f} m | p75 {np.percentile(e, 75):.0f} m | "
          f"p90 {np.percentile(e, 90):.0f} m | <=50 m: {(e <= 50).mean():.0%} | <=150 m: {(e <= 150).mean():.0%} | "
          f">300 m: {(e > 300).mean():.0%}")
    print("servicios sin mapa PNG:", sin_mapa)
    peores = sorted(((np.median(v), s, len(v)) for s, v in por_serv.items()), reverse=True)[:5]
    print("peores servicios (mediana m):", [(s, round(m), n) for m, s, n in peores])


if __name__ == "__main__":
    validar()
