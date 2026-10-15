"""Coordenadas de paradas de alimentadores: nombre ATU limpio -> OSM, desambiguado por secuencia.

ATU no publica coordenadas de los alimentadores, pero si el nombre y el orden de cada parada
(`alimentadores_paraderos_atu.csv`). Para cada servicio:
  1. candidatos OSM con nombre exacto (o con prefijo "Estacion"/"Paradero"/"Terminal");
  2. se elige, para toda la secuencia, un candidato por parada (o ninguno) que minimice la
     suma de saltos entre consecutivas (Viterbi); un homonimo lejano se descarta.
Una parada sin candidato plausible queda SIN coordenada (no se inventa).

El mismo algoritmo se valida sobre corredores, donde se conoce el GPS de ATU (--validar).
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

CODEDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODEDIR))
FUENTES = CODEDIR.parents[2] / "data" / "fuentes"
GEO = FUENTES / "geo"
GEOJSON = CODEDIR.parents[2] / "data_processed" / "geo"
OSM = CODEDIR.parents[2] / "data" / "OSM" / "transporte.csv"

MAX_HOP_M = 2000.0   # distancia maxima entre paradas consecutivas de un alimentador
VENTANA = 6          # vecinas consideradas a cada lado


def norm(s) -> str:
    t = unicodedata.normalize("NFKD", str(s or "").strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def dist_m(a, b) -> float:
    la1, lo1, la2, lo2 = map(np.radians, [a[0], a[1], b[0], b[1]])
    x = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return float(6371000 * 2 * np.arcsin(np.sqrt(x)))


def cargar_osm() -> dict[str, list[tuple[float, float]]]:
    o = pd.read_csv(OSM, usecols=["name", "lat", "lon"]).dropna()
    por: dict[str, list[tuple[float, float]]] = {}
    for n, la, lo in zip(o["name"].map(norm), o["lat"], o["lon"]):
        por.setdefault(n, []).append((float(la), float(lo)))
    return por


def _variantes_nombre(nombre: str) -> list[str]:
    """"Caceres (Jamaica)" -> ["Caceres", "Jamaica"]; quita notas como "(domingos) (*)"."""
    base = re.sub(r"\([^)]*\)", " ", str(nombre))
    alias = [a for a in re.findall(r"\(([^)]*)\)", str(nombre))
             if a.strip() and a.strip() != "*" and not re.search(r"domingo|sabado|s[aá]bado|\*", a, re.I)]
    return [b for b in [" ".join(base.split())] + alias if b]


def candidatos(nombre: str, osm: dict, extra: list | None = None) -> list[tuple[float, float]]:
    """Candidatos OSM por nombre exacto; `extra` anade coordenadas de otra fuente (Google)."""
    out: list[tuple[float, float]] = []
    for v in _variantes_nombre(nombre):
        for c in _candidatos_exactos(v, osm):
            if all(dist_m(c, o) > 8 for o in out):
                out.append(c)
    for c in extra or []:
        if all(dist_m(c, o) > FUSION_EXTRA_M for o in out):   # < 25 m de un nodo OSM = mismo lugar
            out.append(c)
    return out


def _candidatos_exactos(nombre: str, osm: dict) -> list[tuple[float, float]]:
    n = norm(nombre)
    sin = re.sub(r"^(terminal|estacion|paradero)\s+", "", n)
    nombres = dict.fromkeys([n, f"estacion {n}", f"paradero {n}", sin, f"estacion {sin}",
                             f"terminal {sin}"])
    out: list[tuple[float, float]] = []
    for k in nombres:
        for c in osm.get(k, []):
            if all(dist_m(c, o) > 8 for o in out):    # nodos duplicados; ida/vuelta quedan separados
                out.append(c)
    return out


FUSION_EXTRA_M = 25.0   # un candidato de otra fuente a menos de esto de uno OSM es el mismo lugar
HOP_POR_PARADA_M = 1500.0   # salto maximo por posicion entre paradas resueltas (con huecos)
HOP_TOPE_M = 3500.0
SALTO_NULO_M = 1500.0   # costo de dejar una parada sin coordenada (frente a un salto grande)
LADO_PENALTY_M = 60.0   # costo de elegir el nodo del lado contrario al del sentido de marcha
PAR_MAX_M = 90.0        # dos nodos del mismo nombre a menos de esto = paradas de cada sentido


def _penalidad_lado(cands: list[list[tuple[float, float]]]) -> list[list[float]]:
    """Se circula por la derecha: el paradero del sentido de marcha esta a la derecha del eje.
    Solo penaliza cuando una parada tiene un nodo hermano en el lado opuesto (par ida/vuelta)."""
    n = len(cands)
    cen = [np.median(np.array(c), axis=0) if c else None for c in cands]
    pen = [[0.0] * len(c) for c in cands]
    for i in range(n):
        c = cands[i]
        if len(c) < 2:
            continue
        a = next((cen[j] for j in range(i - 1, -1, -1) if cen[j] is not None and j != i), None)
        b = next((cen[j] for j in range(i + 1, n) if cen[j] is not None), None)
        if a is None or b is None:
            continue
        lat0 = float(cen[i][0])
        kx = 111320.0 * np.cos(np.radians(lat0))
        v = np.array([(b[1] - a[1]) * kx, (b[0] - a[0]) * 111320.0])
        if np.linalg.norm(v) < 1:
            continue
        for k, q in enumerate(c):
            d = np.array([(q[1] - cen[i][1]) * kx, (q[0] - cen[i][0]) * 111320.0])
            hermano = any(dist_m(q, o) <= PAR_MAX_M for m, o in enumerate(c) if m != k)
            cruz = v[0] * d[1] - v[1] * d[0]       # < 0: a la derecha del sentido de marcha
            if hermano and cruz > 0:
                pen[i][k] = LADO_PENALTY_M
    return pen


def resolver_secuencia(cands: list[list[tuple[float, float]]], max_hop: float = MAX_HOP_M):
    """Viterbi: un candidato (o ninguno) por parada que minimiza la suma de saltos consecutivos.

    Un homonimo lejano cuesta mas que dejar la parada sin coordenada, asi que se descarta.
    Devuelve (coords, metodo, n_candidatos) por posicion; coords None si no se resuelve.
    """
    n = len(cands)
    estados = [list(c) + [None] for c in cands]
    INF = float("inf")
    lado = _penalidad_lado(cands)
    costo = [[(lado[i][k] if k < len(lado[i]) else 0.0) for k in range(len(e))]
             for i, e in enumerate(estados)]
    prev = [[-1] * len(e) for e in estados]
    for i in range(1, n):
        for k, c in enumerate(estados[i]):
            mejor, arg = INF, -1
            for kk, cc in enumerate(estados[i - 1]):
                if c is None or cc is None:
                    t = SALTO_NULO_M
                else:
                    d = dist_m(cc, c)
                    t = d if d <= max_hop else INF
                v = costo[i - 1][kk] + t
                if v < mejor:
                    mejor, arg = v, kk
            costo[i][k], prev[i][k] = mejor + costo[i][k], arg
    k = int(np.argmin(costo[-1])) if n else 0
    res: list = [None] * n
    for i in range(n - 1, -1, -1):
        res[i] = estados[i][k]
        k = prev[i][k] if i > 0 else k
    # el Viterbi no mide distancia a traves de huecos sin coordenada: podar las paradas que quedan
    # lejos de sus vecinas resueltas (homonimo lejano, p. ej. "Calle 22" a 6 km)
    for _ in range(3):
        cambio = False
        for i in range(n):
            if res[i] is None:
                continue
            izq = next((j for j in range(i - 1, -1, -1) if res[j] is not None), None)
            der = next((j for j in range(i + 1, n) if res[j] is not None), None)
            vec = [j for j in (izq, der) if j is not None]
            if vec and not any(dist_m(res[i], res[j]) <= min(HOP_POR_PARADA_M * abs(j - i), HOP_TOPE_M)
                               for j in vec):
                res[i], cambio = None, True
        if not cambio:
            break
    metodo = ["" if r is None else ("osm_exacto_unico" if len(cands[i]) == 1 else "osm_exacto_secuencia")
              for i, r in enumerate(res)]
    return res, metodo, [len(c) for c in cands]


CALLES = CODEDIR.parents[2] / "data" / "OSM" / "calles_nombradas.parquet"
TIPOS_VIA = {"avenida", "av", "jiron", "jr", "calle", "ca", "pasaje", "psje", "pje", "carretera",
             "paseo", "alameda", "malecon", "prolongacion", "prol", "camino", "autopista", "via"}
MAX_A_TRAMO_M = 350.0     # distancia maxima de la calle al tramo entre vecinas resueltas
MAX_A_PUNTO_M = 600.0     # idem con una sola vecina


def clave_calle(nombre: str) -> str:
    t = norm(nombre).split()
    while t and t[0] in TIPOS_VIA:
        t = t[1:]
    return " ".join(t)


def cargar_calles() -> dict[str, np.ndarray]:
    """clave de calle -> vertices (lat, lon) de todos sus tramos OSM."""
    import geopandas as gpd

    if not CALLES.exists():
        return {}
    gdf = gpd.read_parquet(CALLES)
    por: dict[str, list] = {}
    for nombre, geom in zip(gdf["name"], gdf.geometry):
        k = clave_calle(nombre)
        if not k or geom is None:
            continue
        partes = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
        for parte in partes:
            por.setdefault(k, []).extend((y, x) for x, y in parte.coords)
    return {k: np.array(v) for k, v in por.items()}


def _a_metros(pts: np.ndarray, lat0: float) -> np.ndarray:
    return np.column_stack([(pts[:, 1]) * 111320.0 * np.cos(np.radians(lat0)), pts[:, 0] * 111320.0])


def completar_por_calle(nombres: list[str], res: list, calles: dict[str, np.ndarray]):
    """Para paradas sin coordenada: punto de la calle homonima mas cercano al tramo entre las
    vecinas resueltas. Devuelve (res, metodo) con las paradas completadas."""
    res = list(res)
    metodo = [""] * len(res)
    n = len(res)
    for i in range(n):
        if res[i] is not None:
            continue
        V = None
        for v in _variantes_nombre(nombres[i]):
            k = clave_calle(v)
            V = calles.get(k)
            if V is None and len(k) >= 8:       # erratas de OCR: una sola coincidencia muy cercana
                import difflib
                cerca = difflib.get_close_matches(k, calles.keys(), n=2, cutoff=0.92)
                if len(cerca) == 1:
                    V = calles[cerca[0]]
            if V is not None:
                break
        if V is None or len(V) == 0:
            continue
        izq = next((j for j in range(i - 1, max(i - 5, -1), -1) if res[j] is not None), None)
        der = next((j for j in range(i + 1, min(i + 5, n)) if res[j] is not None), None)
        ref = [res[j] for j in (izq, der) if j is not None]
        if not ref:
            continue
        lat0 = float(np.mean([r[0] for r in ref]))
        Vm = _a_metros(V, lat0)
        if len(ref) == 2:
            a, b = (_a_metros(np.array([r]), lat0)[0] for r in ref)
            ab = b - a
            t = np.clip(((Vm - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
            d = np.linalg.norm(Vm - (a + t[:, None] * ab), axis=1)
            limite = MAX_A_TRAMO_M
        else:
            a = _a_metros(np.array(ref), lat0)[0]
            d = np.linalg.norm(Vm - a, axis=1)
            limite = MAX_A_PUNTO_M
        k = int(np.argmin(d))
        if d[k] <= limite and all(dist_m(tuple(V[k]), r) <= MAX_HOP_M * 2 for r in ref):
            res[i], metodo[i] = (float(V[k][0]), float(V[k][1])), "osm_calle_cercania"
    return res, metodo


def validar() -> None:
    """Mismo algoritmo sobre corredores: se oculta el GPS de ATU y se compara."""
    osm = cargar_osm()
    fc = json.loads((GEOJSON / "paradas_corredores.geojson").read_text(encoding="utf-8"))["features"]
    seqs: dict[tuple, list] = {}
    for f in fc:
        p = f["properties"]
        seqs.setdefault((p["ruta"], p["direccion"]), []).append(
            (p["orden"], p["paradero"], f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]))
    tot, errs, sin_c = 0, [], 0
    for (_r, _d), L in seqs.items():
        L.sort()
        cands = [candidatos(x[1], osm) for x in L]
        res, _, _ = resolver_secuencia(cands)
        for x, c, r in zip(L, cands, res):
            tot += 1
            if not c:
                sin_c += 1
            if r is not None:
                errs.append(dist_m(r, (x[2], x[3])))
    e = np.array(errs)
    # --- completado por calle sobre las no resueltas por nombre de parada ---
    calles = cargar_calles()
    if calles:
        e2, intentos, total_sin = [], 0, 0
        for (_r, _d), L in seqs.items():
            L.sort()
            cands = [candidatos(x[1], osm) for x in L]
            res, _, _ = resolver_secuencia(cands)
            sin = [i for i, r in enumerate(res) if r is None]
            total_sin += len(sin)
            res2, met2 = completar_por_calle([x[1] for x in L], res, calles)
            for i in sin:
                if res2[i] is not None:
                    intentos += 1
                    e2.append(dist_m(res2[i], (L[i][2], L[i][3])))
        e2 = np.array(e2) if e2 else np.array([0.0])
        print(f"Completado por calle: sin coordenada={total_sin} | completadas={intentos} "
              f"({intentos / max(total_sin, 1):.0%}) | error mediana={np.median(e2):.0f} m "
              f"p90={np.percentile(e2, 90):.0f} m | <=150 m: {(e2 <= 150).mean():.0%} "
              f"| >500 m: {(e2 > 500).mean():.0%}")
    # --- separacion de sentidos (mismo nodo OSM para ida y vuelta) ---
    antes, despues, n_mov = [], [], 0
    por_ruta: dict[str, dict] = {}
    for (ruta, d), L in seqs.items():
        L.sort()
        res, _, _ = resolver_secuencia([candidatos(x[1], osm) for x in L])
        por_ruta.setdefault(ruta, {})[d] = (L, res)
    for ruta, ds in por_ruta.items():
        bl = {d: ([x[1] for x in L], list(res)) for d, (L, res) in ds.items()}
        orig = {d: list(res) for d, (_, res) in bl.items()}
        mov = separar_sentidos(bl)
        for d, idxs in mov.items():
            L = ds[d][0]
            for i in idxs:
                tr = (L[i][2], L[i][3])
                antes.append(dist_m(orig[d][i], tr))
                despues.append(dist_m(bl[d][1][i], tr))
                n_mov += 1
    if n_mov:
        a, b = np.array(antes), np.array(despues)
        print(f"Separacion de sentidos: paradas desplazadas={n_mov} | error mediana {np.median(a):.0f} m -> "
              f"{np.median(b):.0f} m | p90 {np.percentile(a, 90):.0f} -> {np.percentile(b, 90):.0f} m")
    print(f"Validacion en corredores: paradas={tot} | sin candidato OSM={sin_c} ({sin_c / tot:.0%}) | "
          f"resueltas={len(e)} ({len(e) / tot:.0%})")
    print(f"  error vs GPS ATU: mediana={np.median(e):.0f} m | p90={np.percentile(e, 90):.0f} m | "
          f"<=50 m: {(e <= 50).mean():.0%} | <=150 m: {(e <= 150).mean():.0%} | >500 m: {(e > 500).mean():.1%}")


DESPLAZAMIENTO_M = 12.0   # separacion de cada sentido respecto al eje (acera derecha)


def separar_sentidos(bloques: dict) -> dict[int, set[int]]:
    """Si ida y vuelta de un mismo nombre cayeron en el mismo punto (OSM tiene un solo nodo),
    cada una se desplaza DESPLAZAMIENTO_M a la derecha de su sentido de marcha.
    ``bloques``: {bloque: (nombres, res)} se modifica in situ. Devuelve indices movidos."""
    movidos: dict[int, set[int]] = {b: set() for b in bloques}
    bs = sorted(bloques)
    if len(bs) < 2 or DESPLAZAMIENTO_M <= 0:
        return movidos
    claves = {b: {} for b in bs}
    for b, (nombres, res) in bloques.items():
        for i, r in enumerate(res):
            if r is not None:
                claves[b].setdefault(norm(nombres[i]), []).append(i)
    original = {b: list(res) for b, (_, res) in bloques.items()}
    # 1) detectar coincidencias con las coordenadas ORIGINALES (antes de mover nada)
    for b in bs:
        nombres, res = bloques[b]
        for i, r in enumerate(original[b]):
            if r is None:
                continue
            k = norm(nombres[i])
            if any(any(dist_m(r, original[o][j]) < 1.0 for j in claves[o].get(k, []))
                   for o in bs if o != b):
                movidos[b].add(i)
    # 2) desplazar a la derecha del sentido de marcha de cada sentido
    for b in bs:
        res, orig = bloques[b][1], original[b]
        for i in sorted(movidos[b]):
            r = orig[i]
            ant = next((orig[j] for j in range(i - 1, -1, -1) if orig[j] is not None), None)
            sig = next((orig[j] for j in range(i + 1, len(orig)) if orig[j] is not None), None)
            a, c = (ant or r), (sig or r)
            kx = 111320.0 * np.cos(np.radians(r[0]))
            vx, vy = (c[1] - a[1]) * kx, (c[0] - a[0]) * 111320.0
            nv = float(np.hypot(vx, vy))
            if nv < 1.0:
                movidos[b].discard(i)
                continue
            ex, ny = vy / nv, -vx / nv                    # normal a la derecha del sentido de marcha
            res[i] = (r[0] + ny * DESPLAZAMIENTO_M / 111320.0, r[1] + ex * DESPLAZAMIENTO_M / kx)
    return movidos


CORRECCIONES = FUENTES / "correcciones_paradas.csv"
_RE_LUGAR = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
_RE_VISTA = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
_RE_Q = re.compile(r"[?&](?:q|query|ll)=(-?\d+\.\d+),(-?\d+\.\d+)")


def coord_de_texto(texto: str) -> tuple[float, float] | None:
    """Coordenada de un enlace de Google Maps: primero el lugar (!3d!4d, exacto), luego `q=lat,lon`,
    y al final el centro de la vista (@lat,lon), que es aproximado. Enlaces cortos no se resuelven."""
    for rx in (_RE_LUGAR, _RE_Q, _RE_VISTA):
        m = rx.search(texto or "")
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
    return None


def cargar_correcciones() -> dict[tuple[str, str, int], dict]:
    """Revision humana: (servicio, bloque, orden) -> {estado: ok|mover|sin_parada, lat, lon}."""
    if not CORRECCIONES.exists():
        return {}
    out = {}
    for r in csv.DictReader(CORRECCIONES.open(encoding="utf-8")):
        est = r.get("estado")
        if est in ("mover", "ok", "") and not r.get("lat"):
            c = coord_de_texto(r.get("comentario", ""))          # enlace de Google Maps en el comentario
            if c:
                r["estado"], r["lat"], r["lon"] = "mover", c[0], c[1]
                est = "mover"
        if est in ("ok", "mover", "sin_parada"):
            out[(r["servicio"], str(r["bloque"]), int(r["orden"]))] = r
    return out


UMBRAL_EXACTA_M = 50.0


def cargar_cercanos() -> list[tuple[str, tuple[float, float], float]]:
    """(servicio, (lat, lon) de una parada de Google, distancia al centro consultado)."""
    p = FUENTES / "google_cercanos.csv"
    out = []
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            if r.get("lat") and (set(r["tipos"].split("|")) & {"bus_stop", "transit_stop", "bus_station",
                                                                "transit_station"}):
                out.append((r["servicio"], (float(r["lat"]), float(r["lon"])), float(r["dist_m"] or 0)))
    return out


def precision_parada(c, nombre_cands: list, cercanos_serv: list) -> tuple[str, str, int | None]:
    """('exacta'|'aproximada'|'sin_coordenada', evidencia, distancia_m).

    exacta    = Google tiene una parada con ese NOMBRE a <= UMBRAL_EXACTA_M de nuestra coordenada.
    aproximada = hay coordenada pero Google no la confirma por nombre; 'parada_cercana' indica que
                 Google tiene otra parada a <= UMBRAL_EXACTA_M (misma esquina), 'sin_parada_google' que no.
    """
    if c is None:
        return "sin_coordenada", "", None
    if nombre_cands:
        d = min(dist_m(c, x) for x in nombre_cands)
        if d <= UMBRAL_EXACTA_M:
            return "exacta", "nombre_google", round(d)
    cerca = [dist_m(c, x) for x in cercanos_serv]
    if cerca and min(cerca) <= UMBRAL_EXACTA_M:
        return "aproximada", "parada_cercana_google", round(min(cerca))
    return "aproximada", "sin_parada_google", None


def subir(conf: str) -> str:
    return {"baja": "media", "media": "alta"}.get(conf, conf)


def confianza(metodo: str, n_cand: int) -> str:
    """Segun la validacion en corredores: unico ~11 m de mediana; secuencia con >=3 candidatos
    tiene ~5 % de errores > 500 m."""
    if metodo == "revision_humana":
        return "verificada"
    if metodo == "google_places":
        return "media"         # sin medir aun: `consultar_google_paraderos.py --validar` da el error
    if metodo == "osm_calle_cercania":
        return "baja"          # ubicada sobre la calle homonima, cerca de sus vecinas
    if metodo == "osm_exacto_unico":
        return "alta"
    return "media" if n_cand <= 2 else "baja"


CALLES_IDX: dict[str, np.ndarray] = {}


def geocodificar() -> None:
    global CALLES_IDX
    osm = cargar_osm()
    CALLES_IDX = cargar_calles()
    filas = list(csv.DictReader((FUENTES / "alimentadores_paraderos_atu.csv").open(encoding="utf-8")))
    ocr = FUENTES / "alimentadores_paraderos_ocr.csv"      # servicios que solo publican la lista en imagen
    if ocr.exists():
        filas += list(csv.DictReader(ocr.open(encoding="utf-8")))
    grupos: dict[tuple, list[dict]] = {}
    for r in filas:
        grupos.setdefault((r["grupo"], r["servicio"], r["bloque"]), []).append(r)
    corr = cargar_correcciones()
    try:                                   # coordenadas de Google Places (ingesta unica, opcional)
        from consultar_google_paraderos import cargar_google
        google = cargar_google()
    except Exception:  # noqa: BLE001
        google = {}
    g_pts = {(round(c[0], 6), round(c[1], 6)) for v in google.values() for c in v}
    cercanos = cargar_cercanos()
    cerca_por_serv: dict[str, list] = {}
    for sv, pt, _d in cercanos:
        cerca_por_serv.setdefault(sv, []).append(pt)
    feats, salida, resumen = [], [], []
    # fase 1: resolver cada (servicio, sentido)
    fase1: dict[str, dict[int, dict]] = {}
    for (g, s0, b), L in grupos.items():
        sid = f"{g.replace('Alimentadores', '')}/{s0}"      # "Norte/Collique" != "LosIncas/Collique"
        L.sort(key=lambda r: int(r["orden"]))
        cands = [candidatos(r["paradero"], osm,
                            google.get((sid, norm(_variantes_nombre(r["paradero"])[0])), []))
                 for r in L]
        res, met, nc = resolver_secuencia(cands)
        # lo elegido que solo existe en Google queda marcado como tal
        for k, c in enumerate(res):
            if c is not None and (round(c[0], 6), round(c[1], 6)) in g_pts:
                if all(dist_m(c, o) > 8 for o in candidatos(L[k]["paradero"], osm)):
                    met[k] = "google_places"
        res, met_calle = completar_por_calle([r["paradero"] for r in L], res, CALLES_IDX)
        met = [m or mc for m, mc in zip(met, met_calle)]
        fase1.setdefault(sid, {})[int(b)] = {"g": g, "L": L, "res": res, "met": met, "nc": nc}
    # fase 2: ida y vuelta en el mismo nodo OSM -> acera derecha de cada sentido
    for sid, bl in fase1.items():
        mov = separar_sentidos({b: ([r["paradero"] for r in d["L"]], d["res"]) for b, d in bl.items()})
        for b, idxs in mov.items():
            for i in idxs:
                bl[b]["met"][i] = bl[b]["met"][i] + "+lado"
    # fase 3: correcciones humanas y salida
    for sid, bl in fase1.items():
        for b, d in sorted(bl.items()):
            L, res, met, nc, g = d["L"], d["res"], d["met"], d["nc"], d["g"]
            for k, r in enumerate(L):
                c = corr.get((sid, str(b), int(r["orden"])))
                if not c:
                    continue
                if c["estado"] == "sin_parada":
                    res[k], met[k] = None, ""
                elif c["estado"] == "mover" and c.get("lat") and c.get("lon"):
                    res[k], met[k] = (float(c["lat"]), float(c["lon"])), "revision_humana"
                elif c["estado"] == "ok" and res[k] is not None:
                    met[k] = "revision_humana"
            ok = sum(r is not None for r in res)
            resumen.append((g.replace("Alimentadores", ""), sid, b, len(L), ok))
            for r, c, m, k in zip(L, res, met, nc):
                base = m.replace("+lado", "")
                conf = confianza(base, k) if c else ""
                corro = 0
                if c is not None and base not in ("revision_humana",):
                    g_loc = google.get((sid, norm(_variantes_nombre(r["paradero"])[0])), [])
                    o_loc = candidatos(r["paradero"], osm)
                    # dos fuentes independientes (nodo OSM por nombre y Google) en el mismo lugar
                    if any(dist_m(c, x) <= 40 for x in g_loc) and any(dist_m(c, x) <= 40 for x in o_loc):
                        corro, conf = 1, subir(conf)
                nom_c = google.get((sid, norm(_variantes_nombre(r["paradero"])[0])), [])
                if m.startswith("revision_humana"):
                    prec, evid, dprec = "exacta", "revision_humana", 0
                else:
                    prec, evid, dprec = precision_parada(c, nom_c, cerca_por_serv.get(sid, []))
                salida.append({"grupo": g, "servicio": sid, "codigo": r["codigo"], "bloque": b,
                               "orden": r["orden"], "paradero": r["paradero"],
                               "precision": prec, "evidencia": evid,
                               "lat": "" if c is None else round(c[0], 6),
                               "lon": "" if c is None else round(c[1], 6),
                               "metodo": m if c else "sin_coordenada", "n_candidatos": k,
                               "corroborado_google": corro, "confianza": conf})
                if c is not None:
                    feats.append({"type": "Feature", "properties": {
                        "grupo": g, "servicio": sid, "codigo": r["codigo"], "bloque": int(b),
                        "orden": int(r["orden"]), "paradero": r["paradero"], "metodo": m,
                        "confianza": conf, "n_candidatos": k, "precision": prec, "evidencia": evid,
                        "fuente": "ATU (nombre, orden) + OSM/Google (coordenada)"},
                        "geometry": {"type": "Point", "coordinates": [c[1], c[0]]}})
    (GEOJSON / "paradas_alimentadores.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "name": "paradas_alimentadores", "features": feats},
                   ensure_ascii=False), encoding="utf-8")
    with (FUENTES / "alimentadores_paradas_geo.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(salida[0]))
        w.writeheader()
        w.writerows(salida)
    tot = sum(x[3] for x in resumen)
    ok = sum(x[4] for x in resumen)
    print(f"Alimentadores: {ok}/{tot} paradas con coordenada ({ok / tot:.0%})")
    for g, s, b, n, k in resumen:
        print(f"  {g[:14]:<14}{s:<18} bloque {b}: {k:>2}/{n:<2}")


def trazar() -> None:
    """Trazado derivado: OSRM entre paradas consecutivas geocodificadas (NO es el oficial)."""
    from osrm_snap import snap_waypoints

    fc = json.loads((GEOJSON / "paradas_alimentadores.geojson").read_text(encoding="utf-8"))["features"]
    por: dict[tuple, list] = {}
    for f in fc:
        p = f["properties"]
        por.setdefault((p["servicio"], p["bloque"]), []).append(
            (p["orden"], f["geometry"]["coordinates"], p["codigo"]))
    lineas = []
    for (serv, bloque), L in sorted(por.items()):
        L.sort(key=lambda t: t[0])
        coords = [c for _, c, _ in L]
        if len(coords) < 3:
            continue
        coords, meta = snap_waypoints(coords, max_direct_km=MAX_HOP_M / 1000, sleep_s=0.05)
        print(f"  trazado {serv}/{bloque}: {meta['n_waypoints']} paradas, {meta['n_osrm_ok']} tramos OSRM")
        lineas.append({"type": "Feature", "properties": {
            "ruta": serv, "direccion": bloque, "codigo": L[0][2], "sistema": "alimentador",
            "nota": f"derivado: OSRM entre paradas geocodificadas por nombre OSM "
                    f"({meta['n_osrm_ok']} tramos ok, {meta['n_skipped']} en recta); no es el trazado oficial"},
            "geometry": {"type": "LineString", "coordinates": coords}})
    (GEOJSON / "trazados_alimentadores_atu.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "name": "trazados_alimentadores_atu",
                    "features": lineas}, ensure_ascii=False), encoding="utf-8")
    print(f"trazados_alimentadores_atu.geojson: {len(lineas)} lineas")


if __name__ == "__main__":
    if "--validar" in sys.argv:
        validar()
    else:
        validar()
        geocodificar()
        trazar()
