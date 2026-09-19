import urllib.request
from pathlib import Path

import pandas as pd
from pyrosm import OSM

URL_OSM = "https://download.bbbike.org/osm/bbbike/Bogota/Bogota.osm.pbf"
NOMBRE_PBF = "bogota.osm.pbf"
RECUPERAR_DATOS = False  # True = reprocesar POIs/red aunque ya existan

CODEDIR = Path(__file__).resolve().parent
SALIDA = Path(__file__).resolve().parents[2] /"data"/ "OSM"

# Categorías de POIs y sus etiquetas OSM
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


def extraer_pois(osm: OSM) -> pd.DataFrame:
    frames = []
    for categoria, filtro in CATEGORIAS:
        try:
            gdf = osm.get_pois(custom_filter=filtro)
        except Exception as e:
            print(f"  [aviso] {categoria} falló: {e}")
            continue
        if gdf is None or len(gdf) == 0:
            print(f"  {categoria:<10} 0")
            continue
        gdf = gdf.copy()
        gdf["categoria"] = categoria
        gdf["lon"], gdf["lat"] = zip(*gdf["geometry"].apply(_punto))
        frames.append(gdf)
        print(f"  {categoria:<10} {len(gdf):,}")

    if not frames:
        return pd.DataFrame(columns=["categoria", "lon", "lat", "name"])
    df = pd.concat(frames, ignore_index=True)
    cols = ["categoria", "lon", "lat"]
    if "name" in df.columns:
        cols.append("name")
    return df[cols]


def extraer_red_vial(osm: OSM):
    gdf = osm.get_network(network_type="all")
    if gdf is None or len(gdf) == 0:
        raise RuntimeError("No se obtuvo red vial del PBF")
    cols = [c for c in ["highway", "oneway", "lanes", "maxspeed", "geometry"]
            if c in gdf.columns]
    return gdf[cols]


def main() -> None:
    print(f"Directorio de salida: {SALIDA}")
    SALIDA.mkdir(parents=True, exist_ok=True)

    pbf = SALIDA / NOMBRE_PBF
    descargar(URL_OSM, pbf)

    pois_csv = SALIDA / "pois.csv"
    red_geo = SALIDA / "red_vial.geojson"
    if (pois_csv.exists() or red_geo.exists()) and not RECUPERAR_DATOS:
        print("Ya hay salidas procesadas (RECUPERAR_DATOS=False); "
              "no se reprocesa.")

    print("\nLeyendo PBF ...")
    osm = OSM(pbf)

    print("\n[1/2] POIs:")
    pois = extraer_pois(osm)
    pois.to_csv(pois_csv, index=False, encoding="utf-8")
    print(f"  guardado: {len(pois):,} POIs -> {pois_csv}")

    print("\n[2/2] Red vial:")
    red = extraer_red_vial(osm)
    if "highway" in red.columns:
        top = red["highway"].value_counts().head(6)
        print("  tipos de vía más frecuentes:")
        for k, v in top.items():
            print(f"    {k:<25} {v:>8,}")
    red.to_file(red_geo, driver="GeoJSON")
    print(f"  guardado: {len(red):,} tramos -> {red_geo}")

    print("\nListo! Revisa:", SALIDA)


if __name__ == "__main__":
    main()