import pickle
import sys
import time
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import box

RAIZ = Path(__file__).resolve().parents[3]          # deliveries/week12
GEO = RAIZ.parents[1] / "backend" / "data" / "geo"
OUT = RAIZ / "data_processed" / "eje2" / "graph"
TES = OUT / "_teselas"
RADIO_M = 800
TESELA_GRADOS = 0.05                                 # ~5,5 km
CRS_M = 32718                                        # UTM 18S (Lima)

FUENTES = {"metro_l1": "puntos_metro_l1.geojson", "troncal": "puntos_troncal.geojson",
           "corredor": "paradas_corredores.geojson", "alimentador": "paradas_alimentadores.geojson"}
TAGS = {"amenity": True, "shop": True, "leisure": ["park"], "highway": ["bus_stop"], "public_transport": True}
CAT_AMENITY = {
    "bar_ocio": {"bar", "pub", "nightclub", "casino", "biergarten"},
    "banco": {"bank", "atm"},
    "educacion": {"school", "college", "university", "kindergarten"},
    "salud": {"hospital", "clinic", "doctors", "pharmacy"},
    "mercado": {"marketplace"},
    "restaurante": {"restaurant", "cafe", "fast_food", "food_court"},
}


def cargar_accesos() -> gpd.GeoDataFrame:
    fr = []
    for tipo, f in FUENTES.items():
        g = gpd.read_file(GEO / f)
        fr.append(gpd.GeoDataFrame({"tipo": [tipo] * len(g)}, geometry=g.geometry.values, crs=g.crs))
    return pd.concat(fr, ignore_index=True).to_crs(CRS_M)


def categoria_poi(r) -> str | None:
    a = r.get("amenity")
    for cat, s in CAT_AMENITY.items():
        if a in s:
            return cat
    if isinstance(r.get("shop"), str):
        return "comercio"
    if r.get("leisure") == "park":
        return "parque"
    if r.get("highway") == "bus_stop" or isinstance(r.get("public_transport"), str):
        return "paradero_bus"
    return None


def descargar_tesela(i, t):
    f = TES / f"tesela_{i:03d}.pkl"
    if f.exists():
        n, e, p = pickle.loads(f.read_bytes())
        if len(p) == 0 and len(e) > 1000:      # la consulta de POIs falló en silencio: se reintenta solo esa parte
            for intento in range(3):
                try:
                    p = ox.features_from_polygon(t, TAGS)
                    break
                except Exception as ex:
                    print(f"  POIs tesela {i} intento {intento}: {ex}"); time.sleep(20)
            p = p.reset_index() if len(p) else p
            tmp = f.with_suffix(".tmp"); tmp.write_bytes(pickle.dumps((n, e, p))); tmp.rename(f)
            print(f"tesela {i} reparada: {len(p):,} POIs", flush=True)
        return n, e, p
    for intento in range(4):
        try:
            G = ox.graph_from_polygon(t, network_type="walk", simplify=True, retain_all=True)
            n, e = ox.graph_to_gdfs(G)
            try:
                p = ox.features_from_polygon(t, TAGS)
            except Exception:
                p = gpd.GeoDataFrame()
            break
        except Exception as ex:
            print(f"  tesela {i} intento {intento}: {ex}"); time.sleep(20)
    else:
        raise RuntimeError(f"tesela {i} falló")
    r = (n.reset_index(), e.reset_index(), p.reset_index() if len(p) else p)
    tmp = f.with_suffix(".tmp"); tmp.write_bytes(pickle.dumps(r)); tmp.rename(f)
    print(f"tesela {i}: {len(e):,} aristas · {len(p):,} POIs", flush=True)
    return r


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); TES.mkdir(exist_ok=True)
    ox.settings.requests_timeout = 300
    ox.settings.cache_folder = str(TES / "_cache")
    acc = cargar_accesos()
    area = gpd.GeoSeries([acc.buffer(RADIO_M).union_all()], crs=CRS_M).to_crs(4326).iloc[0]
    minx, miny, maxx, maxy = area.bounds
    tiles = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            t = box(x, y, x + TESELA_GRADOS, y + TESELA_GRADOS).intersection(area)
            if not t.is_empty and t.area > 1e-6:
                tiles.append(t)
            y += TESELA_GRADOS
        x += TESELA_GRADOS
    print(f"{len(tiles)} teselas")
    aristas, nodos, pois = [], [], []
    if "--reverso" in sys.argv:        # segundo trabajador: baja teselas desde el final hasta cruzarse con el primero
        for i in reversed(range(len(tiles))):
            if (TES / f"tesela_{i:03d}.pkl").exists():
                print("cruce con el otro trabajador en", i); return
            descargar_tesela(i, tiles[i])
        return
    for i, t in enumerate(tiles):
        r = descargar_tesela(i, t)
        n, e, p = r
        aristas.append(e); nodos.append(n); pois.append(p)
        print(f"tesela {i + 1}/{len(tiles)}: {len(e):,} aristas · {len(p):,} POIs", flush=True)

    e = pd.concat(aristas, ignore_index=True)
    for c in ("highway", "osmid", "name", "oneway", "lanes", "bridge", "tunnel", "service", "access"):
        if c in e:
            e[c] = e[c].apply(lambda v: ";".join(map(str, v)) if isinstance(v, list) else (None if pd.isna(v) else str(v)))
    e = e.drop_duplicates(subset=["u", "v", "key"])
    cols = [c for c in ("u", "v", "key", "osmid", "highway", "name", "oneway", "length", "geometry") if c in e]
    gpd.GeoDataFrame(e[cols], crs=4326).to_parquet(OUT / "aristas.parquet")
    n = pd.concat(nodos, ignore_index=True).drop_duplicates(subset=["osmid"])
    gpd.GeoDataFrame(n[["osmid", "y", "x", "geometry"]], crs=4326).to_parquet(OUT / "nodos.parquet")

    pp = [p for p in pois if len(p)]
    if pp:
        p = pd.concat(pp, ignore_index=True)
        p["cat"] = p.apply(categoria_poi, axis=1)
        p = gpd.GeoDataFrame(p[p.cat.notna()][["cat", "geometry"]], crs=4326)
        c = p.to_crs(CRS_M).geometry.centroid.to_crs(4326)
        p = gpd.GeoDataFrame({"cat": p.cat.values}, geometry=c.values, crs=4326)
        p.to_parquet(OUT / "pois.parquet")
        print(p.cat.value_counts().to_dict())
    print(f"OK: {len(e):,} aristas, {len(n):,} nodos")


if __name__ == "__main__":
    main()
