import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path

# Fecha de descarga
DESDE = date(2026, 7, 1)   # (YYYY, M, D)
HASTA = date(2026, 8, 31)  # (YYYY, M, D)

CODEDIR = Path(__file__).resolve().parent          
SALIDA = Path(__file__).resolve().parents[2] /"data"/ "transmilenio" 

BASE_URL = "https://storage.googleapis.com/validaciones_tmsa"


def descargar(url: str, destino: Path) -> bool:
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  Ya existe: {destino.name}")
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Descargando: {url}")
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
        print(f"  Error: no se pudo descargar {url}: {e}")
        if destino.exists():
            destino.unlink()
        return False


def descargar_diarios(desde: date, hasta: date, salida: Path) -> None:
    for day in range((hasta - desde).days + 1):
        d = desde + timedelta(days=day)
        fecha = d.strftime("%Y%m%d")
        url = f"{BASE_URL}/ValidacionTroncal/validacionTroncal{fecha}.zip"
        destino = salida / "diario" / f"validacionTroncal{fecha}.zip"
        descargar(url, destino)


def main() -> None:
    print(f"Directorio de salida: {SALIDA}")
    print(f"Descargando diarios desde {DESDE.isoformat()} hasta {HASTA.isoformat()} "
          f"({(HASTA - DESDE).days + 1} días)")
    descargar_diarios(DESDE, HASTA, SALIDA)
    print(f"\nDescarga completada! Revisa: {SALIDA / 'diario'}")


if __name__ == "__main__":
    main()