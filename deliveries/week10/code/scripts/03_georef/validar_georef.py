"""Mide el error de georreferenciar los mapas ATU contra coordenadas oficiales conocidas.

Metro L1: estaciones del shapefile ATU (anillos verdes, orden norte->sur).
Corredores: paradas con GPS de ATU (discos numerados; numero = orden ATU).

Para cada mapa se reportan, en metros sobre las paradas NO usadas como control:
  piso   leave-one-out con todos los puntos (distorsion propia del dibujo)
  K=2    control solo en los 2 extremos (lo disponible para un alimentador: terminal + otro)
  K=3/4  extremos + puntos intermedios
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import Transformer
from scipy import ndimage as ndi

CODEDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODEDIR))
import georef_mapas as G  # noqa: E402

FUENTES = CODEDIR.parents[1] / "data" / "fuentes"
GEO = FUENTES / "geo"
TO_M = Transformer.from_crs(4326, 32718, always_xy=True)


def a_metros(lon, lat) -> np.ndarray:
    x, y = TO_M.transform(np.asarray(lon), np.asarray(lat))
    return np.column_stack([x, y])


def _fps(px: np.ndarray, k: int) -> list[int]:
    """Muestreo de punto mas lejano en el plano de la imagen."""
    i = int(np.argmax(np.linalg.norm(px - px.mean(0), axis=1)))
    j = int(np.argmax(np.linalg.norm(px - px[i], axis=1)))
    idx = [i, j]
    while len(idx) < k:
        d = np.min([np.linalg.norm(px - px[t], axis=1) for t in idx], axis=0)
        idx.append(int(np.argmax(d)))
    return idx


def _ajuste(modelo: str, px: np.ndarray, mm: np.ndarray):
    """Devuelve f(px)->metros. 'sim' = similitud (4 gl), 'afin' = afin completa (6 gl)."""
    if modelo == "sim":
        s, R, t = G.ajustar_similitud(px, mm)
        return lambda q: G.aplicar(s, R, t, q)
    A = np.column_stack([px, np.ones(len(px))])
    coef, *_ = np.linalg.lstsq(A, mm, rcond=None)
    return lambda q: np.column_stack([q, np.ones(len(q))]) @ coef


def error_con_control(px, mm, k: int, modelo: str) -> np.ndarray:
    idx = _fps(px, k)
    f = _ajuste(modelo, px[idx], mm[idx])
    rest = [i for i in range(len(px)) if i not in idx]
    return np.linalg.norm(f(px) - mm, axis=1)[rest]


def error_piso(px, mm, modelo: str) -> np.ndarray:
    e = []
    for i in range(len(px)):
        m = np.arange(len(px)) != i
        e.append(np.linalg.norm(_ajuste(modelo, px[m], mm[m])(px[i:i + 1]) - mm[i]))
    return np.asarray(e)


def resumen(nombre: str, px: np.ndarray, mm: np.ndarray, extra: dict | None = None) -> dict:
    fila = {"mapa": nombre, "n_puntos": len(px), **(extra or {})}
    casos = [("sim_piso", error_piso(px, mm, "sim")), ("afin_piso", error_piso(px, mm, "afin")),
             ("sim_K2", error_con_control(px, mm, 2, "sim")),
             ("sim_K4", error_con_control(px, mm, 4, "sim")),
             ("afin_K4", error_con_control(px, mm, 4, "afin")),
             ("afin_K6", error_con_control(px, mm, 6, "afin"))]
    for etiqueta, e in casos:
        fila[f"{etiqueta}_mediana_m"] = round(float(np.median(e)), 1)
        fila[f"{etiqueta}_p90_m"] = round(float(np.percentile(e, 90)), 1)
    return fila


# ── Metro L1 ───────────────────────────────────────────────────────────────
def detectar_anillos_verdes(ruta: Path) -> np.ndarray:
    rgb = np.asarray(Image.open(ruta).convert("RGB")).astype(int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    verde = (g > 110) & (r < 90) & (b < 120) & (g - r > 60)
    mask = ndi.binary_fill_holes(ndi.binary_closing(verde, iterations=2))
    dt = ndi.distance_transform_edt(mask)
    W = rgb.shape[1]
    lo, hi = 0.0095 * W, 0.022 * W
    picos = np.argwhere((dt == ndi.maximum_filter(dt, size=9)) & (dt >= lo) & (dt <= hi))
    # el banner "LINEA 1" es verde y grande: fuera de rango; descartar zona superior
    picos = picos[picos[:, 0] > 0.17 * rgb.shape[0]]
    picos = picos[np.argsort(-dt[picos[:, 0], picos[:, 1]])]
    sel: list[np.ndarray] = []
    for p in picos:
        if all(np.linalg.norm(p - q) > 2.2 * lo for q in sel):
            sel.append(p)
    xy = np.array([[p[1], p[0]] for p in sel], float)
    return xy[np.argsort(xy[:, 1])]  # norte -> sur


def validar_l1() -> dict | None:
    img = GEO / "mapas_metro_l1" / "Mapa-Linea-1.png"
    shp = json.loads((GEO / "puntos_metro_l1.geojson").read_text(encoding="utf-8"))["features"]
    est = sorted(((f["geometry"]["coordinates"], f["properties"]["estacion"]) for f in shp),
                 key=lambda t: -t[0][1])  # norte -> sur (L1 es monotona en latitud)
    px = detectar_anillos_verdes(img)
    print(f"  L1: anillos detectados={len(px)} estaciones shapefile={len(est)}")
    if len(px) == len(est) - 2:     # los terminales son capsulas, no anillos
        est = est[1:-1]
    if len(px) != len(est):
        return {"mapa": "metro_l1", "n_puntos": len(px), "nota": f"deteccion {len(px)} != {len(est)}"}
    mm = a_metros([c[0][0] for c in est], [c[0][1] for c in est])
    return resumen("metro_l1", px, mm, {"sistema": "metro_l1"})


# ── Corredores ──────────────────────────────────────────────────────────────
def _truth_corredores() -> dict[tuple[str, int, int], tuple[float, float]]:
    fc = json.loads((GEO / "paradas_corredores.geojson").read_text(encoding="utf-8"))["features"]
    return {(f["properties"]["ruta"], int(f["properties"]["direccion"]), int(f["properties"]["orden"])):
            tuple(f["geometry"]["coordinates"]) for f in fc}


def mapa_principal(carpeta: Path) -> Path | None:
    best, area = None, 0
    for p in carpeta.glob("*.[pj][np]*g"):
        try:
            w, h = Image.open(p).size
        except Exception:  # noqa: BLE001
            continue
        if h >= 1.8 * w and w * h > area:
            best, area = p, w * h
    return best


def validar_corredores() -> list[dict]:
    truth = _truth_corredores()
    filas = []
    for carpeta in sorted(GEO.glob("mapas_corredores/*/[0-9]*")):
        ruta = carpeta.name
        img = mapa_principal(carpeta)
        if img is None or not any(k[0] == ruta for k in truth):
            continue
        marc = [m for m in G.detectar_marcadores(img) if m.numero]
        cnt: dict[tuple[str, int], list] = {}
        for m in marc:
            cnt.setdefault((m.color, m.numero), []).append(m)
        unicos = {k: v[0] for k, v in cnt.items() if len(v) == 1}
        mejor = None
        for mapeo in ({"claro": 1, "oscuro": 2}, {"claro": 2, "oscuro": 1}):
            pares = [(m, truth[(ruta, mapeo[c], n)]) for (c, n), m in unicos.items()
                     if (ruta, mapeo[c], n) in truth]
            if len(pares) < 6:
                continue
            px = np.array([[m.x, m.y] for m, _ in pares])
            mm = a_metros([t[0] for _, t in pares], [t[1] for _, t in pares])
            s, R, t = G.ajustar_similitud(px, mm)
            rms = float(np.sqrt(np.mean(np.sum((G.aplicar(s, R, t, px) - mm) ** 2, axis=1))))
            if mejor is None or rms < mejor[0]:
                mejor = (rms, px, mm, len(pares))
        if mejor is None:
            filas.append({"mapa": f"corredor_{ruta}", "n_puntos": len(unicos),
                          "nota": "pocos marcadores identificables", "sistema": "corredor"})
            print(f"  {ruta}: marcadores utiles insuficientes ({len(unicos)})")
            continue
        _, px, mm, n = mejor
        # atipicos del OCR: descartar los que superan 3x la mediana del residuo global
        res = np.linalg.norm(_ajuste("afin", px, mm)(px) - mm, axis=1)
        ok = res <= max(4 * np.median(res), 250)
        px, mm = px[ok], mm[ok]
        f = resumen(f"corredor_{ruta}", px, mm, {"sistema": "corredor", "n_descartados": int((~ok).sum())})
        print(f"  {ruta}: n={f['n_puntos']:>3} (-{f['n_descartados']}) "
              + " ".join(f"{k}={f[k + '_mediana_m']:>6}" for k in
                         ("sim_piso", "afin_piso", "sim_K2", "sim_K4", "afin_K4", "afin_K6")))
        filas.append(f)
    return filas


def main() -> None:
    print("Validacion de georreferenciacion (error en metros sobre paradas no usadas como control)")
    filas = []
    l1 = validar_l1()
    if l1:
        filas.append(l1)
        if "sim_K2_mediana_m" in l1:
            print("  metro_l1: n=%d " % l1["n_puntos"] + " ".join(
                f"{k}={l1[k + '_mediana_m']:>6}" for k in
                ("sim_piso", "afin_piso", "sim_K2", "sim_K4", "afin_K4", "afin_K6")))
    filas += validar_corredores()
    campos = sorted({k for f in filas for k in f}, key=lambda k: (k not in ("mapa", "sistema", "n_puntos"), k))
    with (FUENTES / "validacion_georef.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)
    ok = [f for f in filas if "sim_K2_mediana_m" in f]
    print(f"\nResumen ({len(ok)} mapas validados) - mediana de las medianas / peor mapa, en metros:")
    for k in ("sim_piso", "afin_piso", "sim_K2", "sim_K4", "afin_K4", "afin_K6"):
        v = [f[f"{k}_mediana_m"] for f in ok]
        print(f"  {k:>9}: {np.median(v):6.0f} / {max(v):6.0f}")


if __name__ == "__main__":
    main()
