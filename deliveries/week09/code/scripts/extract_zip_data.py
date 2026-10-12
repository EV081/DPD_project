import argparse
import shutil
import zipfile
from pathlib import Path, PurePosixPath

CODEDIR = Path(__file__).resolve().parent
RAIZ = Path(__file__).resolve().parents[2]
ENTRADA = RAIZ / "zip"
SALIDA = RAIZ / "data"

PREFIJOS_PERMITIDOS = {".xlsx", ".xls", ".csv", ".shp", ".shx", ".dbf", ".prj",
                       ".cpg", ".qmd", ".txt", ".xml", ".json", ".geojson", ".pbf",
                       ".zip"}   # .zip: los shapefiles de la L1 vienen anidados en un .zip

MAX_PROFUNDIDAD = 3   # nivel 1 = zip de entrega, nivel 2 = zip anidado, nivel 3 = tope de seguridad


def _es_seguro(destino: Path, raiz: Path) -> bool:
    try:
        destino.resolve().relative_to(raiz.resolve())
    except ValueError:
        return False
    return True


def _nombre_valido(entrada: str) -> bool:
    p = PurePosixPath(entrada)
    if p.is_absolute():
        return False
    return ".." not in p.parts


def extraer_zip(ruta_zip: Path, destino_raiz: Path, overwrite: bool = False,
                profundidad: int = 1) -> list[Path]:
    escritos: list[Path] = []
    destino_raiz.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(ruta_zip) as zf:
        roto = zf.testzip()
        if roto is not None:
            raise RuntimeError(f"{ruta_zip.name}: archivo corrupto en {roto}")

        for info in zf.infolist():
            if info.is_dir():
                continue
            if not _nombre_valido(info.filename):
                print(f"  [descartado] ruta insegura: {info.filename}")
                continue

            destino = destino_raiz / info.filename
            if not _es_seguro(destino, destino_raiz):
                print(f"  [descartado] escapa del directorio destino: {info.filename}")
                continue

            if destino.suffix.lower() not in PREFIJOS_PERMITIDOS:
                print(f"  [descartado] extensión no permitida: {info.filename}")
                continue

            if destino.exists() and not overwrite and destino.stat().st_size == info.file_size:
                continue

            destino.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as origen, open(destino, "wb") as f:
                shutil.copyfileobj(origen, f, length=1024 * 1024)
            escritos.append(destino)

    return escritos


def _es_zip(ruta: Path) -> bool:
    return zipfile.is_zipfile(ruta)


def procesar_zip(ruta_zip: Path, overwrite: bool, profundidad: int = 1,
                 indent: str = "  ") -> int:
    total = 0
    nombre = ruta_zip.relative_to(RAIZ)
    print(f"{indent}[{ruta_zip.name}] {ruta_zip.stat().st_size / 1e6:.1f} MB")

    escritos = extraer_zip(ruta_zip, SALIDA, overwrite, profundidad)
    total += len(escritos)
    for w in escritos:
        print(f"{indent}  + {w.relative_to(SALIDA)} ({w.stat().st_size / 1e6:.2f} MB)")

    if profundidad >= MAX_PROFUNDIDAD:
        return total

    anidados = [w for w in escritos if w.suffix.lower() == ".zip"]
    for sub in anidados:
        total += procesar_zip(sub, overwrite, profundidad + 1, indent + "    ")

    return total


def resumen() -> None:
    print("\n" + "=" * 72)
    print("RESUMEN DE ARCHIVOS EXTRAIDOS")
    print("=" * 72)

    archivos = sorted(p for p in SALIDA.rglob("*") if p.is_file())
    total_bytes = sum(p.stat().st_size for p in archivos)
    print(f"Total archivos: {len(archivos):,}   Tamano total: {total_bytes / 1e6:,.1f} MB\n")

    por_ext: dict[str, list[Path]] = {}
    for p in archivos:
        por_ext.setdefault(p.suffix.lower() or "(sin ext)", []).append(p)

    for ext, items in sorted(por_ext.items()):
        size = sum(p.stat().st_size for p in items)
        print(f"  {ext:<10} {len(items):>6,} archivos   {size / 1e6:>10,.1f} MB")

    print("\nHojas de Excel:")
    for p in sorted(por_ext.get(".xlsx", [])):
        print(f"  {p.relative_to(SALIDA)}")

    shp = por_ext.get(".shp", [])
    if shp:
        print("\nShapefiles (shp + dbf + prj):")
        for p in sorted(shp):
            print(f"  {p.relative_to(SALIDA)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="Sobrescribe archivos existentes (por defecto se saltan).")
    args = ap.parse_args()

    if not ENTRADA.exists():
        raise SystemExit(f"No existe el directorio de entrada: {ENTRADA}")

    zips = sorted(ENTRADA.glob("*.zip"))
    if not zips:
        raise SystemExit(f"No hay archivos .zip en {ENTRADA}")

    print(f"Entrada: {ENTRADA}")
    print(f"Salida:  {SALIDA}")
    print(f"Zips encontrados: {len(zips)}\n")

    total = 0
    for z in zips:
        total += procesar_zip(z, args.force)

    print(f"\nArchivos escritos en esta ejecucion: {total:,}")
    if total == 0:
        print("(todo ya existia; usa --force para reextraer)")

    resumen()


if __name__ == "__main__":
    main()
