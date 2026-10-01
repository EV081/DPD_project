import argparse
import urllib.request
from pathlib import Path

import pandas as pd
from pyrosm import OSM

URL_OSM = "https://download.bbbike.org/osm/bbbike/Lima/Lima.osm.pbf"
NOMBRE_PBF = "lima.osm.pbf"
RECUPERAR_DATOS = False   # True = reprocesar POIs/transporte/red aunque ya existan

CODEDIR = Path(__file__).resolve().parent
RAIZ = Path(__file__).resolve().parents[2]   
SALIDA = RAIZ / "data" / "OSM"

# Categorias de POIs de ciudad y sus etiquetas OSM.
CATEGORIAS = [
    ("luminaria", {"highway": ["street_lamp"]}),
    ("hospital",  {"amenity": ["hospital"]}),
    ("comisaria", {"amenity": ["police"]}),
    ("comercio",  {"shop": True}),
    ("negocio",   {"amenity": [
        "bank", "atm", "fuel", "pharmacy", "restaurant", "fast_food",
        "cafe", "bar", "pub", "marketplace", "financial", "money_transfer",
        "laundry", "beauty", "barber",
    ]}),
]

# Capa de transporte publico: paradas, estaciones y accesos.
CATEGORIAS_TRANSPORTE = [
    ("paradero_bus",   {"highway": ["bus_stop"]}),
    ("estacion_metro", {"station": ["subway", "light_rail", "train"], "railway": ["station"]}),
    ("entrada_metro",  {"railway": ["subway_entrance", "station"]}),
    ("paradero_micro", {"highway": ["bus_stop"], "bus": ["yes"]}),
]


def descargar(url: str, destino: Path) -> bool:
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  Ya existe: {destino.name} ({destino.stat().st_size:,} bytes)")
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Descargando: {destino.name} de BBBike ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (project-data-download)"})
    with urllib.request.urlopen(req) as resp, open(destino, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return True


def _punto(g) -> tuple:
    if g is None:
        return None, None
    if g.geom_type == "Point":
        return g.x, g.y
    return g.centroid.x, g.centroid.y


def _construir(osm: OSM, categorias: list[tuple], etiqueta: str) -> pd.DataFrame:
    frames = []
    for categoria, filtro in categorias:
        try:
            gdf = osm.get_pois(custom_filter=filtro)
        except Exception as e:
            print(f"  [aviso] {categoria} fallo: {e}")
            continue
        if gdf is None or len(gdf) == 0:
            print(f"  {categoria:<16} 0")
            continue
        gdf = gdf.copy()
        gdf["categoria"] = categoria
        gdf["lon"], gdf["lat"] = zip(*gdf["geometry"].apply(_punto))
        frames.append(gdf)
        print(f"  {categoria:<16} {len(gdf):,}")

    if not frames:
        return pd.DataFrame(columns=["categoria", "lon", "lat", "name", "ref"])
    df = pd.concat(frames, ignore_index=True)
    cols = [c for c in ["categoria", "lon", "lat", "name", "ref"] if c in df.columns]
    return df[cols + [c for c in df.columns if c not in cols and c != "geometry"]]


def extraer_red_vial(osm: OSM):
    gdf = osm.get_network(network_type="all")
    if gdf is None or len(gdf) == 0:
        raise RuntimeError("No se obtuvo red vial del PBF")
    cols = [c for c in ["highway", "oneway", "lanes", "maxspeed", "geometry"] if c in gdf.columns]
    return gdf[cols]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recuperar", action="store_true",
                    help="Reprocesa POIs/transporte/red aunque ya existan")
    args = ap.parse_args()
    recuperar = args.recuperar or RECUPERAR_DATOS

    print(f"Directorio de salida: {SALIDA}")
    SALIDA.mkdir(parents=True, exist_ok=True)

    pbf = SALIDA / NOMBRE_PBF
    descargar(URL_OSM, pbf)

    pois_csv = SALIDA / "pois.csv"
    trans_csv = SALIDA / "transporte.csv"
    red_geo = SALIDA / "red_vial.geojson"
    if (pois_csv.exists() or trans_csv.exists() or red_geo.exists()) and not recuperar:
        print("Ya hay salidas procesadas (usa --recuperar para reprocesar). Nada que hacer.")
        return

    print("\nLeyendo PBF (puede tardar) ...")
    osm = OSM(pbf)

    print("\n[1/3] POIs de ciudad:")
    pois = _construir(osm, CATEGORIAS, "ciudad")
    pois.to_csv(pois_csv, index=False, encoding="utf-8")
    print(f"  guardado: {len(pois):,} POIs -> {pois_csv}")

    print("\n[2/3] Transporte publico:")
    trans = _construir(osm, CATEGORIAS_TRANSPORTE, "transporte")
    trans.to_csv(trans_csv, index=False, encoding="utf-8")
    print(f"  guardado: {len(trans):,} elementos -> {trans_csv}")

    print("\n[3/3] Red vial:")
    red = extraer_red_vial(osm)
    if "highway" in red.columns:
        print("  tipos de via mas frecuentes:")
        for k, v in red["highway"].value_counts().head(6).items():
            print(f"    {k:<25} {v:>8,}")
    red.to_file(red_geo, driver="GeoJSON")
    print(f"  guardado: {len(red):,} tramos -> {red_geo}")

    print("\nListo! Revisa:", SALIDA)


if __name__ == "__main__":
    main()
