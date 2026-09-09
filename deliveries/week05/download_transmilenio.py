#!/usr/bin/env python3
"""
Descarga datos históricos de validaciones TransMilenio (SITP - Bogotá).

Fuentes:
- Validaciones Troncales mensuales (2024-2025): XLSX ~13 MB/mes
- Validaciones Troncales diarias (Oct 2025 en adelante): ZIP ~100 MB/día
- Salidas diarias: ZIP ~1.5 MB/día

Uso:
    python3 download_transmilenio.py --mensuales 2025
    python3 download_transmilenio.py --mensuales 2024 2025
    python3 download_transmilenio.py --diarios --desde 2025-09-01 --hasta 2025-09-30
"""

import argparse
import os
import sys
import zipfile
import urllib.request
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

BASE_URL = "https://storage.googleapis.com/validaciones_tmsa"

# Los archivos mensuales tienen nombres largos con acentos y espacios.
MESES_ES = {
    1: ("Enero", "2025"), 2: ("Febrero", "2025"), 3: ("Marzo", "2025"),
    4: ("Abril", "2025"), 5: ("Mayo", "2025"), 6: ("Junio", "2025"),
    7: ("Julio", "2025"), 8: ("Agosto", "del 2025"), 9: ("Septiembre", "del 2025"),
    10: ("Octubre", "del 2025"), 11: ("Noveimbre", "del 2025"), 12: ("Diciembre", "del 2025"),
}
MESES_ES_CORTO = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def ultimo_dia_mes(anio: int, mes: int) -> int:
    """Devuelve el último día del mes (maneja febrero bisiesto)."""
    if mes == 12:
        return 31
    return (date(anio, mes + 1, 1) - timedelta(days=1)).day


def nom_mensual(anio: int, mes: int) -> str:
    """Devuelve el nombre de archivo mensual (2024) o la URL (2025).

    El portal usa dos formatos distintos:
    - 2024: "12 TM Resumen de Validaciones Troncales al 31 Dic 2024 Intervalo 15 Mint.xlsx"
    - 2025: "01 TM Resumen de Validaciones Troncales al 31 de Enero 2025 Intervalo 15 Mint.xlsx"
            (con "del 2025" de agosto a diciembre, y el typo "Noveimbre")
    """
    if anio == 2024:
        return f"{mes:02d} TM Resumen de Validaciones Troncales al {ultimo_dia_mes(anio, mes)} {MESES_ES_CORTO[mes]} {anio} Intervalo 15 Mint.xlsx"
    mes_es, anio_sufijo = MESES_ES[mes]
    return f"{mes:02d} TM Resumen de Validaciones Troncales al {ultimo_dia_mes(anio, mes)} de {mes_es} {anio_sufijo} Intervalo 15 Mint.xlsx"


def descargar(url: str, destino: Path) -> bool:
    """Descarga `url` a `destino`, saltando si ya existe. Devuelve True si descargó."""
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  [skip] ya existe: {destino.name}")
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [descargando] {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (project-data-download)"},
        )
        with urllib.request.urlopen(req) as resp, open(destino, "wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  [ERROR] no se pudo descargar {url}: {e}")
        if destino.exists():
            destino.unlink()
        return False


def descargar_mensuales(anios, salida: Path) -> None:
    """Descarga los resúmenes mensuales de Validación Troncal para los años dados."""
    for anio in anios:
        print(f"\n=== Validaciones Troncales mensuales {anio} ===")
        for mes in range(1, 13):
            nombre = nom_mensual(anio, mes)
            url = (BASE_URL + "/ValidacionTroncal/" + str(anio) + "/"
                   + urllib.parse.quote(nombre))
            destino = salida / "mensual" / str(anio) / nombre
            descargar(url, destino)
        # Para 2024 hay además un consolidado anual
        if anio == 2024:
            url = f"{BASE_URL}/ValidacionTroncal/2024/consolidado_2024.zip"
            descargar(url, salida / "mensual" / "2024" / "consolidado_2024.zip")


def descargar_diarios(desde: date, hasta: date, salida: Path) -> None:
    """Descarga archivos diarios de Validación Troncal entre fechas dadas."""
    for day in range((hasta - desde).days + 1):
        d = desde + timedelta(days=day)
        fecha = d.strftime("%Y%m%d")
        url = f"{BASE_URL}/ValidacionTroncal/validacionTroncal{fecha}.zip"
        destino = salida / "diario" / "troncal" / f"validacionTroncal{fecha}.zip"
        descargar(url, destino)


def descargar_geodata(salida: Path) -> None:
    """Descarga las capas geoespaciales de estaciones y trazados (CSV/GeoJSON)."""
    print("\n=== Datos geoespaciales (estaciones y trazados) ===")
    geodata = {
        "estaciones_troncales.geojson": (
            "https://datosabiertos-transmilenio.hub.arcgis.com/api/download/v1/"
            "items/5365d814bbdd4062a59234eea7d70db7/geojson?layers=2"),
        "trazados_troncales.geojson": (
            "https://datosabiertos-transmilenio.hub.arcgis.com/api/download/v1/"
            "items/4f5282678c72406bb19f7fbf22886bbf/geojson?layers=5"),
    }
    for nombre, url in geodata.items():
        destino = salida / "geo" / nombre
        descargar(url, destino)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga datos de validaciones TransMilenio (SITP Bogotá)."
    )
    parser.add_argument(
        "--mensuales", nargs="+", type=int, default=None,
        help="Años de resúmenes mensuales a descargar (ej: --mensuales 2025 o 2024 2025)",
    )
    parser.add_argument(
        "--diarios", action="store_true",
        help="Descargar archivos diarios de Validación Troncal",
    )
    parser.add_argument(
        "--desde", type=lambda s: date.fromisoformat(s),
        help="Fecha inicio para diarios (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--hasta", type=lambda s: date.fromisoformat(s),
        help="Fecha fin para diarios (YYYY-MM-DD). Default: hoy",
    )
    parser.add_argument(
        "--geo", action="store_true",
        help="Descargar capas geoespaciales (estaciones y trazados)",
    )
    parser.add_argument(
        "--salida", type=Path, default=Path("data/transmilenio"),
        help="Directorio de salida (default: data/transmilenio)",
    )
    args = parser.parse_args()

    salida = args.salida
    print(f"Directorio de salida: {salida}")

    if not (args.diarios or args.mensuales or args.geo):
        parser.print_help()
        sys.exit(0)

    if args.diarios:
        if not args.desde:
            print("Para --diarios usa también --desde YYYY-MM-DD")
            sys.exit(1)
        hasta = args.hasta or date.today()
        print(f"\nDescargando diarios desde {args.desde} hasta {hasta}")
        descargar_diarios(args.desde, hasta, salida)

    if args.mensuales:
        descargar_mensuales(args.mensuales, salida)

    if args.geo:
        descargar_geodata(salida)

    print("\n¡Descarga completada! Revisa la estructura en:", salida)


if __name__ == "__main__":
    main()
