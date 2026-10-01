from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from osrm_snap import snap_waypoints
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from osrm_snap import snap_waypoints

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"
RAW = RAIZ / "data_processed" / "raw"
FUENTES = DATA / "fuentes"
GEO = FUENTES / "geo"
GEO.mkdir(parents=True, exist_ok=True)

LIMA_CENTER = [-12.0464, -77.0428]
USE_OSRM = True  # geometría por calles (no rectas que cruzan manzanas)


def log(msg: str) -> None:
    print(msg, flush=True)


def norm_name(s: str) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    t = str(s).strip().lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # alias frecuentes Metropolitano / L1
    aliases = {
        "estacion central": "central",
        "estacio n central": "central",
        "jiron de la union": "jiron de la union",
        "villa el salvador": "villa el salvador",
        "22 de agosto": "22 de agosto",
        "2 de mayo": "2 de mayo",
        "28 de julio": "28 de julio",
    }
    return aliases.get(t, t)


def write_geojson(path: Path, features: list[dict], name: str) -> None:
    fc = {"type": "FeatureCollection", "name": name, "features": features}
    path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    log(f"  {path.name}: {len(features)} features")


def build_metro_l1() -> None:
    log("\n[1/4] Metro L1 — shapefiles del zip ATU")
    try:
        import geopandas as gpd
    except ImportError as e:
        raise SystemExit(f"geopandas requerido: {e}")

    shp_est = DATA / "Estaciones_de_la_Linea1_del_Metro" / "estaciones_linea_1.shp"
    shp_eje = DATA / "01_linea1" / "eje_de_la_linea_1_del_metro.shp"
    if not shp_est.exists():
        log(f"  [aviso] falta {shp_est}")
        return

    g = gpd.read_file(shp_est)
    if g.crs is None:
        g = g.set_crs(32718)  # UTM 18S típico Lima
    g = g.to_crs(4326)
    g["lon"] = g.geometry.x
    g["lat"] = g.geometry.y
    g["nombre_norm"] = g["nombre"].map(norm_name)

    feats = []
    for _, r in g.iterrows():
        feats.append({
            "type": "Feature",
            "properties": {
                "estacion": str(r["nombre"]).title() if pd.notna(r["nombre"]) else None,
                "estacion_norm": r["nombre_norm"],
                "unidad": str(r["nombre"]).title() if pd.notna(r["nombre"]) else None,
            },
            "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]},
        })
    write_geojson(GEO / "puntos_metro_l1.geojson", feats, "puntos_metro_l1")

    if shp_eje.exists():
        eje = gpd.read_file(shp_eje)
        if eje.crs is None:
            eje = eje.set_crs(32718)
        eje = eje.to_crs(4326)
        feats_l = []
        for _, r in eje.iterrows():
            geom = r.geometry
            if geom is None:
                continue
            # MultiLineString / LineString
            if geom.geom_type == "LineString":
                coords = [list(c[:2]) for c in geom.coords]
                feats_l.append({
                    "type": "Feature",
                    "properties": {"sistema": "metro_l1"},
                    "geometry": {"type": "LineString", "coordinates": coords},
                })
            elif geom.geom_type == "MultiLineString":
                for part in geom.geoms:
                    coords = [list(c[:2]) for c in part.coords]
                    feats_l.append({
                        "type": "Feature",
                        "properties": {"sistema": "metro_l1"},
                        "geometry": {"type": "LineString", "coordinates": coords},
                    })
        write_geojson(GEO / "trazado_metro_l1.geojson", feats_l, "trazado_metro_l1")
    else:
        log(f"  [aviso] falta eje {shp_eje}")


def build_corredores() -> None:
    log("\n[2/4] Corredores — paraderos_cc + orden ATU/QR")
    cc = pd.read_parquet(RAW / "paraderos_cc.parquet")
    cc["cod_paradero"] = cc["cod_paradero"].astype("string").str.strip()
    cc["ruta"] = cc["ruta"].astype("string").str.strip()
    cc["n_paradero"] = pd.to_numeric(cc["n_paradero"], errors="coerce")
    COLOR = {"Rojo": "#c0392b", "Azul": "#2471a3", "Morado": "#7d3c98"}

    pts = []
    for _, r in cc.dropna(subset=["lat", "lon"]).iterrows():
        pts.append({
            "type": "Feature",
            "properties": {
                "cod_paradero": str(r["cod_paradero"]),
                "paradero": str(r.get("paradero", "")),
                "ruta": str(r["ruta"]),
                "n_paradero": int(r["n_paradero"]) if pd.notna(r["n_paradero"]) else None,
                "unidad": str(r["cod_paradero"]),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [float(r["lon"]), float(r["lat"])],
            },
        })
    write_geojson(GEO / "puntos_corredores.geojson", pts, "puntos_corredores")

    orden_p = FUENTES / "paraderos_corredores.csv"
    if not orden_p.exists():
        log("  [aviso] falta paraderos_corredores.csv — sin LineString ordenado")
        return

    orden = pd.read_csv(orden_p)
    orden["ruta"] = orden["ruta"].astype("string").str.strip()
    orden["orden"] = pd.to_numeric(orden["orden"], errors="coerce")
    orden["paradero_norm"] = orden["paradero"].map(norm_name)

    cc2 = cc.copy()
    cc2["paradero_norm"] = cc2["paradero"].map(norm_name)

    # Prefer name within ruta (n_paradero ≠ orden ATU en varios casos)
    m_name = orden.merge(
        cc2[["ruta", "paradero_norm", "lat", "lon", "cod_paradero"]],
        on=["ruta", "paradero_norm"],
        how="left",
    )
    m_ord = orden.merge(
        cc2[["ruta", "n_paradero", "lat", "lon", "cod_paradero"]].rename(
            columns={"n_paradero": "orden"}
        ),
        on=["ruta", "orden"],
        how="left",
    )
    merged = orden.copy()
    merged["lat"] = m_name["lat"].combine_first(m_ord["lat"])
    merged["lon"] = m_name["lon"].combine_first(m_ord["lon"])
    merged["cod_paradero"] = m_name["cod_paradero"].combine_first(m_ord["cod_paradero"])
    merged = merged.drop_duplicates(subset=["ruta", "direccion", "orden"], keep="first")
    # corredor color from orden CSV
    corr_map = (
        orden.drop_duplicates("ruta")
        .set_index("ruta")["corredor"]
        .astype(str)
        .to_dict()
    )

    def _hav_km(a, b):
        lon1, lat1 = np.radians(a)
        lon2, lat2 = np.radians(b)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        x = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        return float(2 * 6371 * np.arcsin(np.sqrt(x)))

    lines = []
    for (ruta, direccion), g in merged.groupby(["ruta", "direccion"], dropna=False):
        g = g.sort_values("orden").dropna(subset=["lat", "lon"])
        if len(g) < 2:
            continue
        coords = [[float(lon), float(lat)] for lat, lon in zip(g["lat"], g["lon"])]
        jumps = []
        for i in range(1, len(coords)):
            a = (coords[i - 1][1], coords[i - 1][0])  # lat, lon
            b = (coords[i][1], coords[i][0])
            jumps.append(_hav_km(a, b))
        max_j = max(jumps) if jumps else 0.0
        corredor = corr_map.get(str(ruta), "")
        if max_j > 3:
            log(f"  [aviso] ruta {ruta} dir {direccion}: max_jump={max_j:.1f} km (pre-OSRM)")
        nota = "paraderos orden ATU"
        if USE_OSRM and len(coords) >= 2:
            coords, meta = snap_waypoints(coords, max_direct_km=2.5, sleep_s=0.08)
            nota = f"OSRM driving entre paraderos ({meta['n_osrm_ok']} tramos ok)"
            log(f"  OSRM {ruta}/{direccion}: {meta}")
        lines.append({
            "type": "Feature",
            "properties": {
                "ruta": str(ruta),
                "direccion": str(direccion),
                "corredor": corredor,
                "color_hex": COLOR.get(corredor, "#4f81bd"),
                "n_puntos": len(coords),
                "max_jump_km": round(max_j, 2),
                "sistema": "corredor",
                "nota": nota,
            },
            "geometry": {"type": "LineString", "coordinates": coords},
        })
    write_geojson(GEO / "trazados_corredores.geojson", lines, "trazados_corredores")
    log(f"  match orden→coords: {merged['lat'].notna().mean():.1%} filas con lat | {len(lines)} LineStrings")


def _load_osm_named() -> pd.DataFrame:
    osm = pd.read_csv(DATA / "OSM" / "transporte.csv", usecols=["categoria", "name", "lat", "lon"])
    osm = osm.dropna(subset=["name", "lat", "lon"]).copy()
    osm["name_norm"] = osm["name"].map(norm_name)
    osm = osm[osm["name_norm"] != ""]
    # prefer unique names: take median coord
    return (
        osm.groupby("name_norm", as_index=False)
        .agg(lat=("lat", "median"), lon=("lon", "median"), name=("name", "first"),
             categoria=("categoria", "first"))
    )


# ATU portal slug → OSM Metropolitano route=bus ref
ATU_TO_OSM_REF = {
    "RegularA": "A",
    "RegularB": "B",
    "RegularC": "C",
    "RegularD": "D",
    "EX11-NS": "EX11",
    "EX13-NS": "EX13",
    "EX9-NS": "EX9",
    "Lechucero": "L",
    "SX-M": "SX",
    "SXN-NS-M": "SXN",
    "X1-M": "EX1",
    "X10": "EX10",
    "X12": "EX12",
    "X3-N": "EX3",
    "X5": "EX5",
    "X6": "EX6",
    "X7": "EX7",
    "X8": "EX8",
}

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _overpass(query: str) -> dict:
    import time
    import urllib.parse
    import urllib.request

    data = urllib.parse.urlencode({"data": query}).encode()
    last_err: Exception | None = None
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data,
                method="POST",
                headers={
                    "User-Agent": "UrbanSafeAI-week08/1.0 (academic)",
                    "Accept": "*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last_err = e
            log(f"  [aviso] Overpass falló ({url}): {e}")
            time.sleep(2)
    raise RuntimeError(f"Overpass no disponible: {last_err}")


def _relation_to_coords(rel: dict) -> list[list[float]]:
    """Une ways de una relation OSM (out geom) en un LineString lon/lat."""
    coords: list[list[float]] = []
    for m in rel.get("members", []):
        if m.get("type") != "way" or "geometry" not in m:
            continue
        pts = [[float(p["lon"]), float(p["lat"])] for p in m["geometry"]]
        if len(pts) < 2:
            continue
        if not coords:
            coords.extend(pts)
            continue
        # alinear orientación con el extremo actual
        if pts[0] == coords[-1]:
            coords.extend(pts[1:])
        elif pts[-1] == coords[-1]:
            coords.extend(reversed(pts[:-1]))
        elif pts[0] == coords[0]:
            coords = list(reversed(pts[1:])) + coords
        elif pts[-1] == coords[0]:
            coords = pts[:-1] + coords
        else:
            # salto: pegar sin invertir (corredor BRT suele ser continuo)
            coords.extend(pts)
    return coords


def _path_length_deg(coords: list[list[float]]) -> float:
    if len(coords) < 2:
        return 0.0
    arr = np.asarray(coords, dtype=float)
    d = np.sqrt(((arr[1:] - arr[:-1]) ** 2).sum(axis=1)).sum()
    return float(d)


def fetch_osm_metropolitano_routes(force: bool = False) -> dict[str, dict]:
    """Descarga route=bus network=Metropolitano (sin alimentadoras) vía Overpass.

    Cache: data/fuentes/geo/osm_metropolitano_routes.geojson
    Retorna ref → {coords, name, osm_id, n_coords}
    """
    cache = GEO / "osm_metropolitano_routes.geojson"
    if cache.exists() and not force:
        fc = json.loads(cache.read_text(encoding="utf-8"))
        out: dict[str, dict] = {}
        for f in fc.get("features", []):
            ref = str(f["properties"].get("ref") or "")
            coords = f["geometry"]["coordinates"]
            if f["geometry"]["type"] == "MultiLineString":
                # aplanar
                flat: list[list[float]] = []
                for part in coords:
                    flat.extend(part)
                coords = flat
            if ref and len(coords) >= 2:
                # quedarse con la variante más larga por ref
                prev = out.get(ref)
                if prev is None or _path_length_deg(coords) > _path_length_deg(prev["coords"]):
                    out[ref] = {
                        "coords": coords,
                        "name": f["properties"].get("name"),
                        "osm_id": f["properties"].get("osm_id"),
                        "n_coords": len(coords),
                    }
        log(f"  cache OSM Metropolitano: {cache.name} ({len(out)} refs)")
        return out

    log("  Overpass: relaciones Metropolitano (route=bus, sin alimentadoras)…")
    query = """
[out:json][timeout:180];
(
  relation["route"="bus"]["network"="Metropolitano"]["ref"~"^(A|B|C|D|L|SX|SXN|EX[0-9]+)$"](-12.35,-77.15,-11.85,-76.85);
);
out geom;
"""
    payload = _overpass(query)
    feats = []
    by_ref: dict[str, dict] = {}
    for el in payload.get("elements", []):
        if el.get("type") != "relation":
            continue
        tags = el.get("tags") or {}
        ref = str(tags.get("ref") or "")
        name = str(tags.get("name") or "")
        if not ref or "Aliment" in name:
            continue
        coords = _relation_to_coords(el)
        if len(coords) < 10:
            continue
        feat = {
            "type": "Feature",
            "properties": {
                "ref": ref,
                "name": name,
                "osm_id": el.get("id"),
                "from": tags.get("from"),
                "to": tags.get("to"),
                "n_coords": len(coords),
                "fuente": "OpenStreetMap Overpass (network=Metropolitano)",
            },
            "geometry": {"type": "LineString", "coordinates": coords},
        }
        feats.append(feat)
        prev = by_ref.get(ref)
        if prev is None or _path_length_deg(coords) > _path_length_deg(prev["coords"]):
            by_ref[ref] = {
                "coords": coords,
                "name": name,
                "osm_id": el.get("id"),
                "n_coords": len(coords),
            }
    write_geojson(cache, feats, "osm_metropolitano_routes")
    log(f"  refs OSM descargadas: {sorted(by_ref)}")
    return by_ref


def build_troncal() -> None:
    log("\n[3/5] Troncal Metropolitano — estaciones OSM + eje Regular C (Overpass)")
    if not (RAW / "troncal_hora.parquet").exists():
        log("  [aviso] falta troncal raw")
        return
    est = (
        pd.read_parquet(RAW / "troncal_hora.parquet", columns=["estacion"])
        ["estacion"].astype("string").str.strip().dropna().unique()
    )
    osm = _load_osm_named()
    pts = []
    matched = 0
    for e in est:
        n = norm_name(e)
        hit = osm[osm["name_norm"] == n]
        if hit.empty and n:
            hit = osm[osm["name_norm"].apply(lambda x: n in x or x in n)]
        if not hit.empty:
            r = hit.iloc[0]
            matched += 1
            pts.append({
                "type": "Feature",
                "properties": {
                    "estacion": str(e),
                    "unidad": str(e),
                    "osm_name": str(r["name"]),
                    "match": "osm",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r["lon"]), float(r["lat"])],
                },
            })
    write_geojson(GEO / "puntos_troncal.geojson", pts, "puntos_troncal")
    log(f"  estaciones matched OSM: {matched}/{len(est)}")

    # Eje troncal = relación OSM Regular C (Matellini ↔ Castilla), no OSRM car
    routes = fetch_osm_metropolitano_routes()
    trunk = routes.get("C")
    if trunk and len(trunk["coords"]) >= 2:
        write_geojson(
            GEO / "trazado_troncal.geojson",
            [{
                "type": "Feature",
                "properties": {
                    "sistema": "troncal",
                    "osm_ref": "C",
                    "osm_id": trunk.get("osm_id"),
                    "osm_name": trunk.get("name"),
                    "nota": "OSM relation route=bus network=Metropolitano ref=C (corredor BRT)",
                    "fuente": "https://www.openstreetmap.org + Overpass API",
                },
                "geometry": {"type": "LineString", "coordinates": trunk["coords"]},
            }],
            "trazado_troncal",
        )
        log(f"  trazado_troncal: OSM Regular C ({trunk['n_coords']} verts)")
    else:
        log("  [aviso] sin geometría OSM ref=C; no se escribe trazado_troncal")


def build_alimentadores() -> None:
    log("\n[4/5] Alimentadores — OSM por nombre de paradero (parcial)")
    if not (RAW / "alimentador_hora.parquet").exists():
        log("  [aviso] falta alimentador raw")
        return
    # distinct paraderos with names
    cols = ["ruta", "n_paradero", "paradero"]
    df = pd.read_parquet(RAW / "alimentador_hora.parquet", columns=cols)
    df = df.dropna(subset=["n_paradero"]).drop_duplicates(subset=["ruta", "n_paradero"])
    df["paradero"] = df["paradero"].astype("string")
    df["paradero_norm"] = df["paradero"].map(norm_name)
    osm = _load_osm_named()

    pts = []
    for _, r in df.iterrows():
        n = r["paradero_norm"]
        if not n:
            continue
        hit = osm[osm["name_norm"] == n]
        if hit.empty and n:
            hit = osm[osm["name_norm"].apply(lambda x: n in x or x in n)]
        if hit.empty:
            continue
        o = hit.iloc[0]
        pts.append({
            "type": "Feature",
            "properties": {
                "ruta": str(r["ruta"]),
                "n_paradero": str(r["n_paradero"]),
                "paradero": str(r["paradero"]),
                "unidad": f"{r['ruta']}|{r['n_paradero']}",
                "osm_name": str(o["name"]),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [float(o["lon"]), float(o["lat"])],
            },
        })
    write_geojson(GEO / "puntos_alimentadores.geojson", pts, "puntos_alimentadores")
    log(f"  paraderos matched: {len(pts)}/{len(df)}")

    # Sin LineString por defecto: geocoding OSM-por-nombre es ruidoso y OSRM
    # sobre waypoints malos sigue cruzando la ciudad. El EDA usa centroides.
    # Para intentar OSRM parcial: USE_OSRM_ALIM=1 en el entorno.
    import os
    if os.environ.get("USE_OSRM_ALIM") != "1":
        write_geojson(GEO / "trazados_alimentadores.geojson", [], "trazados_alimentadores")
        log("  trazados_alimentadores: vacío (pon USE_OSRM_ALIM=1 para intentar OSRM)")
        return

    by_ruta: dict[str, list] = {}
    for f in pts:
        by_ruta.setdefault(f["properties"]["ruta"], []).append(f)
    lines = []
    for ruta, flist in by_ruta.items():
        flist = sorted(
            flist,
            key=lambda f: int(float(f["properties"]["n_paradero"]))
            if str(f["properties"]["n_paradero"]).replace(".", "", 1).isdigit()
            else 0,
        )
        if len(flist) < 2:
            continue
        coords = [f["geometry"]["coordinates"] for f in flist]
        if len(coords) > 15:
            idx = np.linspace(0, len(coords) - 1, 15).astype(int)
            coords = [coords[i] for i in idx]
        coords, meta = snap_waypoints(coords, max_direct_km=1.2, sleep_s=0.05)
        if meta["n_osrm_ok"] < 3:
            continue
        lines.append({
            "type": "Feature",
            "properties": {
                "ruta": str(ruta).strip(),
                "sistema": "alimentador",
                "n_puntos": len(coords),
                "nota": f"OSRM parcial ({meta['n_osrm_ok']} ok)",
                "color_hex": "#c0504d",
            },
            "geometry": {"type": "LineString", "coordinates": coords},
        })
    write_geojson(GEO / "trazados_alimentadores.geojson", lines, "trazados_alimentadores")
    log(f"  trazados_alimentadores: {len(lines)} rutas OSRM")


def build_metro_servicios() -> None:
    """Puntos ATU por servicio + trazado OSM relation (ref A/B/C/EX…), sin OSRM car."""
    log("\n[5/5] Metropolitano por servicio — estaciones ATU + geometría OSM route=bus")
    est_p = FUENTES / "estaciones_por_servicio_atu.csv"
    pts_p = GEO / "puntos_troncal.geojson"
    if not est_p.exists():
        log("  [aviso] falta estaciones_por_servicio_atu.csv (corre download_atu_mapas.py)")
        return
    if not pts_p.exists():
        log("  [aviso] falta puntos_troncal.geojson (corre build_troncal antes)")
        return

    est = pd.read_csv(est_p)
    if est.empty:
        log("  [aviso] CSV de estaciones por servicio vacío")
        return
    est["estacion_norm"] = est["estacion"].map(norm_name)

    pts_fc = json.loads(pts_p.read_text(encoding="utf-8"))
    rows = []
    for f in pts_fc["features"]:
        props = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2]
        rows.append({
            "estacion": props.get("estacion"),
            "estacion_norm": norm_name(props.get("estacion")),
            "lat": lat,
            "lon": lon,
        })
    pts = pd.DataFrame(rows).drop_duplicates("estacion_norm")

    inv = (
        est.groupby("estacion_norm")["servicio_slug"]
        .apply(lambda s: sorted(set(s.astype(str))))
        .to_dict()
    )

    routes = fetch_osm_metropolitano_routes()
    lines, all_pts = [], []
    for slug, g in est.groupby("servicio_slug"):
        g = g.copy()
        g = g.merge(pts, on="estacion_norm", how="left", suffixes=("", "_geo"))
        miss = g["lat"].isna()
        if miss.any():
            for idx in g.index[miss]:
                n = g.at[idx, "estacion_norm"]
                hit = pts[pts["estacion_norm"].apply(
                    lambda x: n in x or x in n if n and x else False
                )]
                if not hit.empty:
                    g.at[idx, "lat"] = hit.iloc[0]["lat"]
                    g.at[idx, "lon"] = hit.iloc[0]["lon"]
                    if pd.isna(g.at[idx, "estacion"]) or not g.at[idx, "estacion"]:
                        g.at[idx, "estacion"] = hit.iloc[0]["estacion"]
        matched = g.dropna(subset=["lat", "lon"]).copy()
        matched = matched.sort_values("lat", ascending=False)
        servs_lbl = str(g["servicio_nombre"].iloc[0]) if len(g) else slug
        log(f"  {slug}: {len(matched)}/{len(g)} estaciones geocodificadas")
        for orden_i, (_, r) in enumerate(matched.iterrows(), start=1):
            name = str(r.get("estacion") or r.get("estacion_x") or "")
            otros = [x for x in inv.get(r["estacion_norm"], []) if x != str(slug)]
            all_pts.append({
                "type": "Feature",
                "properties": {
                    "servicio_slug": str(slug),
                    "servicio_nombre": servs_lbl,
                    "estacion": name,
                    "unidad": name,
                    "orden": orden_i,
                    "otros_servicios": " | ".join(otros),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r["lon"]), float(r["lat"])],
                },
            })

        osm_ref = ATU_TO_OSM_REF.get(str(slug))
        trunk = routes.get(osm_ref) if osm_ref else None
        if trunk and len(trunk["coords"]) >= 2:
            coords = trunk["coords"]
            nota = (
                f"OSM relation route=bus network=Metropolitano ref={osm_ref} "
                f"(id={trunk.get('osm_id')})"
            )
            log(f"  {slug} ← OSM ref={osm_ref} ({trunk['n_coords']} verts)")
            lines.append({
                "type": "Feature",
                "properties": {
                    "servicio_slug": str(slug),
                    "servicio_nombre": servs_lbl,
                    "osm_ref": osm_ref,
                    "osm_id": trunk.get("osm_id"),
                    "n_puntos": len(coords),
                    "sistema": "metropolitano_servicio",
                    "color_hex": "#1f4e79",
                    "nota": nota,
                    "fuente": "OpenStreetMap Overpass",
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            })
        else:
            log(f"  [aviso] {slug}: sin geometría OSM (ref={osm_ref})")

    write_geojson(GEO / "puntos_metropolitano_servicios.geojson", all_pts, "puntos_metropolitano_servicios")
    write_geojson(GEO / "trazados_metropolitano_servicios.geojson", lines, "trazados_metropolitano_servicios")
    log(f"  servicios con trazado OSM: {len(lines)}/{est['servicio_slug'].nunique()}")


def main() -> None:
    log(f"Salida: {GEO}")
    build_metro_l1()
    build_corredores()
    build_troncal()
    build_alimentadores()
    build_metro_servicios()
    log("\nListo. Los EDA leen estos GeoJSON para Folium.")


if __name__ == "__main__":
    main()
