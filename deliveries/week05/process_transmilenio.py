#!/usr/bin/env python3
"""
Procesa los archivos diarios de Validación Troncal de TransMilenio (CSV/ZIP)
y genera un dataset agregado compacto, con coordenadas y capacidad de estaciones.

Cada ZIP diario contiene un CSV con una fila por transacción de validación
(~600 MB/día). Este script lee por streaming (sin cargar todo en memoria) y
agrega el conteo de validaciones por (estación, fecha, hora, línea, tipo de día).

Uso:
    # Agregación por hora (recomendado para el modelo de aforo)
    python3 process_transmilenio.py -i data/transmilenio/diario/troncal \
        -o data/transmilenio/dataset.csv --geo data/transmilenio/geo/estaciones_troncales.geojson \
        --trazados data/transmilenio/geo/trazados_troncales.geojson

    # Otras granularidades
    python3 process_transmilenio.py --intervalo 15min ...
    python3 process_transmilenio.py --intervalo minuto ...
"""

import argparse
import csv
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

CAMPOS = ["Estacion", "Fecha", "Hora", "Linea", "Tipo_Dia", "Validaciones"]
CAMPOS_GEO = ["Latitud", "Longitud", "Ubicacion", "Troncal", "Fase", "Cap_ART", "Cap_BIART"]


def extraer_hora(fecha_hora: str, ancho: int) -> str:
    """'2025-12-01 03:50:39' -> '03' si ancho=2, '03:50' si ancho=5, '03:50:39' si ancho=8."""
    return fecha_hora[11:11 + ancho]


def procesar_csv(fileobj, agregado: defaultdict, ancho: int) -> None:
    """Procesa CSV de Validación Troncal (streaming) y acumula conteos."""
    reader = csv.DictReader(fileobj)
    for fila in reader:
        estacion = fila.get("Estacion_Parada") or ""
        fecha_hora = fila.get("Fecha_Transaccion") or ""
        linea = fila.get("Linea") or ""
        tipo_dia = fila.get("Day_Group_Type") or ""
        sistema = fila.get("Sistema") or ""
        if sistema and sistema.strip().upper() != "TRONCAL":
            continue
        if not estacion.strip():
            continue
        fecha = fecha_hora[:10]
        hora = extraer_hora(fecha_hora, ancho)
        if not fecha or not hora:
            continue
        clave = (estacion, fecha, hora, linea, tipo_dia)
        agregado[clave] += 1


def procesar_zip(ruta_zip: Path, agregado: defaultdict, ancho: int) -> None:
    """Lee un ZIP de Validación Troncal y procesa su CSV."""
    with zipfile.ZipFile(ruta_zip) as z:
        for nombre in z.namelist():
            if nombre.lower().endswith((".csv", ".txt")):
                print(f"    procesando {nombre} ...")
                with z.open(nombre) as f:
                    texto = __import__("io").TextIOWrapper(f, encoding="utf-8")
                    procesar_csv(texto, agregado, ancho)
                return


def cargar_estaciones(ruta_geojson: Path, ruta_trazados: Path = None) -> dict:
    """Carga el GeoJSON de estaciones y devuelve {clave: {atributos}}.

    El cruce con los datos es frágil porque los nombres varían en formato:
      - Validaciones: "(02000) Portal Norte" (con espacio)
      - GeoJSON:      num_est "02000", nom_est "Portal Norte"
    Por eso se indexa por el código numérico de la estación (num_est),
    que es la clave estable en ambos lados.

    Si se pasa también el GeoJSON de trazados, se completa la troncal y fase
    de cada estación cruzando por id_trazado.
    """
    trazados = {}
    if ruta_trazados and ruta_trazados.exists():
        with open(ruta_trazados, encoding="utf-8") as f:
            gjt = json.load(f)
        for feat in gjt.get("features", []):
            props = feat.get("properties", {})
            tz = props.get("id_trazado")
            if tz:
                trazados[tz] = {
                    "nom_troncal": props.get("nom_tronc"),
                    "fase": props.get("fase_tronc"),
                    "long_traz": props.get("long_traz"),
                }

    with open(ruta_geojson, encoding="utf-8") as f:
        gj = json.load(f)
    estaciones = {}
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        nombre = props.get("nom_est") or props.get("name") or ""
        if not nombre:
            continue
        geom = feat.get("geometry", {})
        datos = {
            "lat": geom["coordinates"][1] if geom.get("type") == "Point" else "",
            "lon": geom["coordinates"][0] if geom.get("type") == "Point" else "",
            "num_est": props.get("num_est"),
            "cod_nodo": props.get("cod_nodo"),
            "id_trazado": props.get("id_trazado"),
            "ub_est": props.get("ub_est"),
            "nom_troncal": props.get("nom_tronc"),
            "fase": props.get("fase_tronc"),
            "cap_art": props.get("cap_art"),
            "cap_biart": props.get("cap_biart"),
        }
        # Completar troncal/fase desde los trazados
        tz = props.get("id_trazado")
        if tz and tz in trazados:
            datos["nom_troncal"] = datos["nom_troncal"] or trazados[tz]["nom_troncal"]
            datos["fase"] = datos["fase"] or trazados[tz]["fase"]
        estaciones[nombre] = datos
        if props.get("num_est"):
            estaciones[f"({props.get('num_est')}) {nombre}"] = datos
            # Clave numérica: int(num_est) tolera ceros a la izquierda
            try:
                estaciones[int(props["num_est"])] = datos
            except (TypeError, ValueError):
                pass
    return estaciones


def _codigo_estacion(nombre: str):
    """Extrae el código numérico de un nombre de estación "(02000) Nombre"."""
    m = re.match(r"\s*\((\d+)\)", nombre)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _info_estacion(estaciones: dict, estacion: str) -> dict:
    """Busca la info de una estación probando varias claves de forma robusta."""
    if not estaciones:
        return {}
    for clave in (estacion, estacion.replace(" ", ""), estacion.strip()):
        info = estaciones.get(clave)
        if info:
            return info
    cod = _codigo_estacion(estacion)
    if cod is not None and cod in estaciones:
        return estaciones[cod]
    return {}


def _en_rango(fecha8: str, desde: str, hasta: str) -> bool:
    if not fecha8:
        return True
    if desde and fecha8 < desde.replace("-", ""):
        return False
    if hasta and fecha8 > hasta.replace("-", ""):
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", "-i", type=Path,
        default=Path("data/transmilenio/diario/troncal"),
        help="Carpeta con los ZIP diarios de Validación Troncal",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        default=Path("data/transmilenio/dataset.csv"),
        help="CSV de salida (default: data/transmilenio/dataset.csv)",
    )
    parser.add_argument(
        "--geo", type=Path, default=None,
        help="GeoJSON de estaciones troncales para enriquecer con lat/lon y capacidad",
    )
    parser.add_argument(
        "--trazados", type=Path, default=None,
        help="GeoJSON de trazados troncales para completar troncal/fase de cada estación",
    )
    parser.add_argument(
        "--desde", type=str, default=None,
        help="Solo procesar días >= esta fecha (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--hasta", type=str, default=None,
        help="Solo procesar días <= esta fecha (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--intervalo", choices=["hora", "15min", "minuto"], default="hora",
        help="Granularidad temporal de la agregación (default: hora)",
    )
    args = parser.parse_args()

    ancho = {"hora": 2, "15min": 5, "minuto": 8}[args.intervalo]

    zips = sorted(args.input.glob("validacionTroncal*.zip"))
    if not zips:
        print(f"No se encontraron archivos validacionTroncal*.zip en {args.input}")
        print("Ejecuta primero:")
        print("  python3 download_transmilenio.py --diarios --desde ... --hasta ...")
        return

    def fecha_de_nombre(p: Path) -> str:
        m = re.search(r"(\d{8})", p.name)
        return m.group(1) if m else ""

    zips = [p for p in zips if _en_rango(fecha_de_nombre(p), args.desde, args.hasta)]

    print(f"Procesando {len(zips)} archivos desde {args.input} "
          f"(intervalo: {args.intervalo})")

    estaciones = {}
    campos_out = list(CAMPOS)
    if args.geo:
        if not args.geo.exists():
            print(f"AVISO: no existe {args.geo}; continúo sin coordenadas")
        else:
            estaciones = cargar_estaciones(args.geo, args.trazados)
            print(f"  {len(estaciones)} claves de estación cargadas")
            idx_estacion = campos_out.index("Estacion")
            for i, c in enumerate(CAMPOS_GEO):
                campos_out.insert(idx_estacion + 1 + i, c)

    def geo_de(estacion: str) -> list:
        info = _info_estacion(estaciones, estacion)
        return [
            info.get("lat", ""),
            info.get("lon", ""),
            info.get("ub_est", ""),
            info.get("nom_troncal", ""),
            info.get("fase", ""),
            info.get("cap_art", ""),
            info.get("cap_biart", ""),
        ]

    agregado: defaultdict = defaultdict(int)
    for ruta in zips:
        print(f"  {ruta.name} ...")
        procesar_zip(ruta, agregado, ancho)

    filas = []
    for (estacion, fecha, hora, linea, tipo_dia), n in sorted(agregado.items()):
        filas.append([estacion, *geo_de(estacion), fecha, hora, linea, tipo_dia, n])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nEscribiendo {len(filas):,} filas a {args.output}")
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(campos_out)
        writer.writerows(filas)

    print(f"TOTAL registros agregados: {len(filas):,}")
    print(f"TOTAL validaciones procesadas: {sum(agregado.values()):,}")
    print("¡Listo!")


if __name__ == "__main__":
    main()