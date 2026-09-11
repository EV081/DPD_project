import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path


DESDE = date(2026, 7, 1)    
HASTA = date(2026, 8, 31)   
PASO_DIAS = 7              

CODEDIR = Path(__file__).resolve().parent
SALIDA = CODEDIR.parent / "data" / "transmilenio" / "gtfs"

BASE_URL = "https://storage.googleapis.com/gtfs-estaticos"
FALLBACK_MAX_DIAS = 7   # si GTFS_YYYYMMDD.zip da error, se busca en d+1..d+7, o sea un dia q si tenga datos para cubrir esa semana

BUSCAR_SUSTITUTO = PASO_DIAS > 1


def descargar(url: str, destino: Path) -> bool:
    if destino.exists() and destino.stat().st_size > 0:
        print(f" Ya existe: {destino.name}")
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Descargando: {destino.name}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (project-data-download)"})
        with urllib.request.urlopen(req) as resp, open(destino, "wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        return True
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return False
    except Exception as e:
        print(f"  Error: no se pudo descargar {destino.name}: {e}")
        if destino.exists():
            destino.unlink()
        return False


def descargar_con_fallback(d: date) -> str:
    fecha = d.strftime("%Y%m%d")
    destino = SALIDA / f"GTFS_{fecha}.zip"

    if destino.exists() and destino.stat().st_size > 0:
        print(f" Ya existe: {destino.name}")
        return "ok"

    if not BUSCAR_SUSTITUTO:
        # Modo diario
        url = f"{BASE_URL}/GTFS_{fecha}.zip"
        if descargar(url, destino):
            return "ok"
        print(f"  No existe] {destino.name}: skip.")
        return "no-existe"

    # Modo semanal
    for desfase in range(FALLBACK_MAX_DIAS + 1):
        fecha_c = (d + timedelta(days=desfase)).strftime("%Y%m%d")
        cand = SALIDA / f"GTFS_{fecha_c}.zip"
        if cand.exists() and cand.stat().st_size > 0:
            print(f"  Ya existe: {cand.name}")
            return "ok"

    for desfase in range(FALLBACK_MAX_DIAS + 1):
        dia = d + timedelta(days=desfase)
        fecha_c = dia.strftime("%Y%m%d")
        url = f"{BASE_URL}/GTFS_{fecha_c}.zip"
        destino_c = SALIDA / f"GTFS_{fecha_c}.zip"
        if descargar(url, destino_c):
            if desfase:
                print(f"    (No existía el de {d.isoformat()}; se usó {dia.isoformat()})")
            return "sust"
    print(f"  No existe ningún snapshot para la semana de {d.isoformat()}.")
    return "no-existe"


def main() -> None:
    dias = []
    d = DESDE
    while d <= HASTA:
        dias.append(d)
        d += timedelta(days=PASO_DIAS)

    print(f"Directorio de salida: {SALIDA}")
    print(f"Snapshots a descargar ({len(dias)}): "
          f"{[x.isoformat() for x in dias]}\n")

    descargados = 0
    faltantes = []
    for d in dias:
        estado = descargar_con_fallback(d)
        if estado == "no-existe":
            faltantes.append(d.isoformat())
        elif estado in ("ok", "sust"):
            descargados += 1

    total = (sum(1 for x in SALIDA.glob("*.zip"))
             if SALIDA.exists() else 0)
    print(f"\nResultado: {descargados} fechas cubiertas | "
          f"{len(faltantes)} sin snapshot | {total} archivos en carpeta")
    if faltantes:
        print("Días sin snapshot (se continuó; revisar si importan): "
              f"{', '.join(faltantes)}")


if __name__ == "__main__":
    main()