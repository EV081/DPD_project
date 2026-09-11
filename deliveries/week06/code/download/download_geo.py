import urllib.request
from pathlib import Path

CODEDIR = Path(__file__).resolve().parent          
SALIDA = CODEDIR.parent / "data" / "transmilenio" / "geo" 

ARC_BASE = "https://datosabiertos-transmilenio.hub.arcgis.com/api/download/v1/items"
GEODATA = {
    "estaciones_troncales.geojson": f"{ARC_BASE}/5365d814bbdd4062a59234eea7d70db7/geojson?layers=2",
    "trazados_troncales.geojson":   f"{ARC_BASE}/4f5282678c72406bb19f7fbf22886bbf/geojson?layers=5",
}


def descargar(url: str, destino: Path) -> bool:
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  [skip] ya existe: {destino.name}")
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [descargando] {destino.name}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (project-data-download)"})
        with urllib.request.urlopen(req) as resp, open(destino, "wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  ERROR: no se pudo descargar {destino.name}: {e}")
        if destino.exists():
            destino.unlink()
        return False


def main() -> None:
    print(f"Directorio de salida: {SALIDA}")
    for nombre, url in GEODATA.items():
        descargar(url, SALIDA / nombre)

    import json
    for nombre in GEODATA:
        p = SALIDA / nombre
        if not p.exists():
            continue
        try:
            with open(p, encoding="utf-8") as f:
                n = len(json.load(f)["features"])
            print(f"  Ok: {nombre}: {n} features")
        except Exception as e:
            print(f"  Ok: {nombre}: JSON válido, no se pudo contar ({e})")

    print("\nDescarga completada! Revisa:", SALIDA)


if __name__ == "__main__":
    main()