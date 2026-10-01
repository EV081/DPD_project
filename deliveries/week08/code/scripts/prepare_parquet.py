"""Convierte Excel de validaciones ATU a Parquet crudo (sin limpieza).

Solo hace reshape (wide→long), renombra columnas y filtra el año pedido.
La limpieza + EDA viven en los notebooks:

    deliveries/week08/code/eda/eda_troncales_metropolitano.ipynb
    deliveries/week08/code/eda/eda_alimentadores.ipynb
    deliveries/week08/code/eda/eda_corredores.ipynb
    deliveries/week08/code/eda/eda_metro_l1.ipynb

Uso:
    .venv/bin/python deliveries/week08/code/scripts/prepare_parquet.py --anio 2025
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd

CODEDIR = Path(__file__).resolve().parent
RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"
SALIDA = RAIZ / "data_processed" / "raw"
SALIDA.mkdir(parents=True, exist_ok=True)

XLSX_COSAC = DATA / "4950-2026-02-0012640.xlsx"
BASE_L1 = DATA / "AIP -E- 0302-2026-02-0060693" / "Validaciones_01.2024-01.2026"
MESES_L1 = [
    "01_Enero", "02_Febrero", "03_Marzo", "04_Abril", "05_Mayo", "06_Junio",
    "07_Julio", "08_Agosto", "09_Septiembre", "10_Octubre", "11_Noviembre",
    "12_Diciembre",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def _limpiar_col(c) -> str:
    return str(c).strip().replace("\n", " ")


def _es_hora(v) -> bool:
    s = str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s.isdigit() and 0 <= int(s) <= 23


def re_hora(v) -> bool:
    return bool(re.match(r"^\d{1,2}\s*-\s*\d{1,2}\s*h$", str(v).strip(), re.IGNORECASE))


def guardar(df: pd.DataFrame, nombre: str) -> None:
    ruta = SALIDA / nombre
    df.to_parquet(ruta, index=False, compression="snappy")
    log(f"  {nombre:<32} {len(df):>12,} filas  {ruta.stat().st_size / 1e6:>7.1f} MB")


def _leer(sheet: str, header, usecols=None):
    t = time.time()
    log(f"    leyendo '{sheet}' ...")
    df = pd.read_excel(XLSX_COSAC, sheet_name=sheet, header=header, usecols=usecols)
    log(f"    -> {len(df):,} filas x {len(df.columns)} columnas ({time.time() - t:.0f}s)")
    return df


def _wide_a_long(df: pd.DataFrame, id_cols: list[str], cols_hora: dict) -> pd.DataFrame:
    largo = df.melt(
        id_vars=id_cols,
        value_vars=list(cols_hora),
        var_name="_col",
        value_name="validaciones",
    )
    largo["hora"] = largo["_col"].map(lambda c: cols_hora[c][0])
    if any(v[1] for v in cols_hora.values()):
        largo["tipo_tarifa"] = largo["_col"].map(lambda c: cols_hora[c][1])
    largo = largo.drop(columns=["_col"])
    largo["validaciones"] = pd.to_numeric(largo["validaciones"], errors="coerce")
    return largo


def _normalizar_tarifa(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.replace(r"\s*\(S/[\d.]+\)", "", regex=True)
    s = s.str.replace("Intervalos en tarifa", "", regex=False).str.strip()
    s = s.str.replace(r"\s*/\s*Medio$", "", regex=True)
    return s.str.strip()


def preparar_troncal(anio: int) -> None:
    log("\n[1/5] COSAC - TRONCAL (crudo: fecha/estación/hora)")
    df = _leer("COSAC - TRONCAL", header=3)
    df.columns = [_limpiar_col(c) for c in df.columns]
    cols_hora = {c: (int(float(c)), None) for c in df.columns if _es_hora(c)}
    log(f"    {len(df):,} filas crudas | {len(cols_hora)} columnas horarias")

    largo = _wide_a_long(df, ["Fecha", "Estacion"], cols_hora)
    largo = largo.rename(columns={"Fecha": "fecha", "Estacion": "estacion"})
    largo["fecha"] = pd.to_datetime(largo["fecha"], errors="coerce")
    largo = largo[largo["fecha"].dt.year == anio]
    largo = largo[["fecha", "estacion", "hora", "validaciones"]]
    guardar(largo.sort_values(["fecha", "estacion", "hora"]), "troncal_hora.parquet")


def preparar_alimentador(anio: int) -> None:
    log("\n[2/5] COSAC - ALIMENTADOR (crudo: con desglose tarifario)")
    df = _leer("COSAC - ALIMENTADOR", header=[3, 4])
    TAREAS = ("General", "Universitario", "Escolar", "Libre")
    planas = []
    for a, b in zip(df.columns.get_level_values(0), df.columns.get_level_values(1)):
        a, b = _limpiar_col(a), _limpiar_col(b)
        if a.startswith("Hora:") and b in TAREAS:
            planas.append(f"{a.split(':', 1)[1].strip()}|{b}")
        else:
            planas.append(b if b and b != "Unnamed" else a)
    df.columns = planas
    log(f"    {len(df):,} filas x {len(df.columns)} columnas")

    metas = [c for c in df.columns if c in (
        "Fecha", "Num. Linea", "Ruta", "Sentido", "No. Paradero", "Paradero"
    )]
    if not metas:
        raise RuntimeError(
            f"No se encontraron columnas de dimensiones en ALIMENTADOR "
            f"(columnas: {list(df.columns[:10])})"
        )

    mapa_hora = {}
    for col in df.columns:
        if "|" in str(col):
            h, tarifa = str(col).split("|", 1)
            if _es_hora(h):
                mapa_hora[col] = (int(float(h)), tarifa)

    largo = _wide_a_long(df, metas, mapa_hora)
    largo = largo.rename(columns={
        "Fecha": "fecha", "Num. Linea": "linea", "Ruta": "ruta",
        "Sentido": "sentido", "No. Paradero": "n_paradero", "Paradero": "paradero",
    })
    largo["fecha"] = pd.to_datetime(largo["fecha"], errors="coerce")
    largo = largo[largo["fecha"].dt.year == anio]
    largo = largo[[
        "fecha", "linea", "ruta", "sentido", "n_paradero", "paradero",
        "hora", "tipo_tarifa", "validaciones",
    ]]
    guardar(
        largo.sort_values(["fecha", "ruta", "sentido", "n_paradero", "hora", "tipo_tarifa"]),
        "alimentador_hora.parquet",
    )


def preparar_corredores(anio: int) -> None:
    log("\n[3/5] CORREDORES COMPLEMENTARIOS (crudo)")
    df = _leer("CORREDORES COMPLEMENTARIOS", header=1)
    df.columns = [_limpiar_col(c) for c in df.columns]
    cols_hora = {c: (int(float(c)), None) for c in df.columns if _es_hora(c)}
    log(f"    {len(df):,} filas crudas | {len(cols_hora)} columnas horarias")

    largo = _wide_a_long(
        df,
        ["Fecha", "TIPO DE DÍA", "RUTA", "CODIGO PARADERO", "PARADERO", "SENTIDO"],
        cols_hora,
    )
    largo = largo.rename(columns={
        "Fecha": "fecha", "TIPO DE DÍA": "tipo_dia_archivo", "RUTA": "ruta",
        "CODIGO PARADERO": "cod_paradero", "PARADERO": "paradero", "SENTIDO": "sentido",
    })
    largo["fecha"] = pd.to_datetime(largo["fecha"], errors="coerce")
    largo = largo[largo["fecha"].dt.year == anio]
    largo = largo[[
        "fecha", "tipo_dia_archivo", "ruta", "cod_paradero", "paradero",
        "sentido", "hora", "validaciones",
    ]]
    guardar(
        largo.sort_values(["fecha", "ruta", "sentido", "cod_paradero", "hora"]),
        "corredores_hora.parquet",
    )


def preparar_metro_l1(anio: int) -> None:
    log("\n[4/5] Metro Línea 1 (crudo: con desglose tarifario)")
    largos = []
    for mes in MESES_L1:
        ruta = BASE_L1 / str(anio) / f"{mes}.xlsx"
        if not ruta.exists():
            log(f"    [aviso] falta {ruta.name}")
            continue
        t = time.time()
        df = pd.read_excel(ruta, sheet_name=0, header=[4, 5])
        niv0 = [_limpiar_col(c) for c in df.columns.get_level_values(0)]
        niv1 = [_limpiar_col(c) for c in df.columns.get_level_values(1)]
        pos_fecha = next((i for i, c in enumerate(niv1) if c.lower() == "fecha"), None)
        pos_est = next((i for i, c in enumerate(niv1) if "estaci" in c.lower()), None)
        if pos_fecha is None or pos_est is None:
            raise RuntimeError(f"{ruta.name}: no se hallaron Fecha/Estación en {niv1[:6]}")

        idxs_hora = [i for i, c in enumerate(niv1) if re_hora(c)]
        df = df.iloc[:, [pos_fecha, pos_est] + idxs_hora]

        for k, i in enumerate(idxs_hora):
            sub = df.iloc[:, [0, 1, 2 + k]].copy()
            sub.columns = ["fecha", "estacion", "validaciones"]
            tarifa = niv0[i]
            sub["tipo_tarifa"] = _normalizar_tarifa(
                pd.Series([
                    tarifa if tarifa and not tarifa.startswith("Unnamed") else "Adulto"
                ])
            ).iloc[0]
            sub["intervalo"] = niv1[i]
            largos.append(sub)
        log(f"    {mes:<14} {len(df):>5,} filas  ({time.time() - t:.0f}s)")

    if not largos:
        raise RuntimeError("No se leyó ningún mes de la Línea 1")

    cat = pd.concat(largos, ignore_index=True)
    cat["fecha"] = pd.to_datetime(cat["fecha"], errors="coerce")
    cat = cat[cat["fecha"].dt.year == anio]
    cat["hora"] = pd.to_numeric(
        cat["intervalo"].str.extract(r"^(\d{1,2})")[0], errors="coerce"
    ).astype("Int16")
    cat = cat[cat["hora"].notna()]
    cat["validaciones"] = pd.to_numeric(cat["validaciones"], errors="coerce")
    cat["tipo_tarifa"] = _normalizar_tarifa(cat["tipo_tarifa"].astype("string"))
    cat = cat[["fecha", "estacion", "hora", "intervalo", "tipo_tarifa", "validaciones"]]
    guardar(
        cat.sort_values(["fecha", "estacion", "hora", "tipo_tarifa"]),
        "metro_l1_hora.parquet",
    )


def preparar_catalogos() -> None:
    log("\n[5/5] Catálogos de paraderos (crudo)")
    for sheet, nombre, header, ren in [
        (
            "LISTA DE PARADEROS - COSAC ",
            "paraderos_cosac.parquet",
            3,
            {
                "Ruta": "ruta", "Nombre Ruta": "nombre_ruta", "Sentido": "sentido",
                "Paradero": "n_paradero", "Nombre estación": "paradero",
            },
        ),
        (
            "LISTA DE PARADEROS - CC",
            "paraderos_cc.parquet",
            1,
            {
                "Ruta": "ruta", "Nro de Paradero": "n_paradero",
                "Codigo Parada": "cod_paradero", "Nombre Parada": "paradero",
                "Sentido": "sentido", "Latitude": "lat", "Longitude": "lon",
                "Radio": "radio",
            },
        ),
    ]:
        df = _leer(sheet, header=header)
        df.columns = [_limpiar_col(c) for c in df.columns]
        df = df.rename(columns=ren)
        antes = len(df.columns)
        df = df.loc[:, ~df.columns.str.match(r"^Unnamed:\s*\d+$")]
        if len(df.columns) < antes:
            log(f"    (se descartaron {antes - len(df.columns)} columnas 'Unnamed')")
        if "lat" in df.columns:
            for c in ("lat", "lon", "radio"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
        guardar(df, nombre)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--anio", type=int, default=2025, help="año a extraer (default 2025)")
    args = ap.parse_args()

    if not XLSX_COSAC.exists():
        raise SystemExit(f"No existe {XLSX_COSAC}. Ejecuta antes extract_zip_data.py")

    log(f"Año: {args.anio}")
    log(f"Salida cruda: {SALIDA}")
    log("Nota: la limpieza NO se hace aquí → corre los EDA por sistema después.")

    t0 = time.time()
    preparar_troncal(args.anio)
    preparar_alimentador(args.anio)
    preparar_corredores(args.anio)
    preparar_metro_l1(args.anio)
    preparar_catalogos()

    log(f"\nCrudos listos en {time.time() - t0:.0f}s: {SALIDA}")
    log("Siguiente paso: EDA troncal / alimentadores / corredores / metro_l1")


if __name__ == "__main__":
    main()
