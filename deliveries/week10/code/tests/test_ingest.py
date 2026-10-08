from __future__ import annotations

import pandas as pd
import pytest

from pipeline import config
from storage import db as storagedb

KEYS_UNICAS = {
    "troncal_hora": "(estacion, fecha, hora)",
    "metro_l1_hora": "(estacion, fecha, hora, tipo_tarifa)",
    "metro_l1_total_hora": "(estacion, fecha, hora)",
    "alimentador_hora": "(linea, ruta, n_paradero, fecha, hora, sentido_norm)",
    "alimentador_tarifa": "(fecha, ruta, hora, tipo_tarifa)",
}


def test_conteos_tablas_espejo(db_cargado):
    for tabla, esperado in config.FILAS_ESPERADAS.items():
        real = storagedb.table_count(db_cargado, tabla)
        assert real == esperado, f"{tabla}: {real:,} != {esperado:,}"


def test_regresion_corredores_cero_duplicados_exactos(db_cargado):
    ruta = config.CLEAN_DIR / "corredores_hora.parquet"
    df = pd.read_parquet(ruta)
    dups = int(df.duplicated(list(df.columns)).sum())
    assert len(df) == 8_253_635, f"corredores: {len(df):,} filas"
    assert dups == 0, f"corredores: {dups} duplicados exactos (regresion Fase 0)"


def test_claves_unicas_declaradas(db_cargado):
    for tabla, keys in KEYS_UNICAS.items():
        row = db_cargado.execute(
            f"SELECT count(*) AS conflictos FROM ("
            f"  SELECT {keys} FROM {tabla} GROUP BY {keys} HAVING count(*) > 1"
            f") conflictos"
        ).fetchone()
        assert row["conflictos"] == 0, f"{tabla}: {row['conflictos']} claves repetidas en {keys}"


def test_vista_por_sistema(db_cargado):
    filas = db_cargado.execute(
        "SELECT sistema, count(*) AS n FROM demanda_fiable "
        "GROUP BY sistema ORDER BY sistema"
    ).fetchall()
    visto = {r["sistema"]: r["n"] for r in filas}
    assert visto == config.FIABLE_ESPERADO
    assert sum(visto.values()) == config.FIABLE_TOTAL_ESPERADO


def test_vista_espejo_consolidada_por_grupo(db_cargado):
    consolidada = pd.read_parquet(
        config.CLEAN_DIR / "demanda_consolidada_fiable.parquet"
    )
    keys = ["sistema", "unidad", "fecha", "hora", "sentido"]
    esperado = (
        consolidada.groupby(keys, observed=True, dropna=False)
        .agg(
            filas=("validaciones", "size"),
            validaciones=("validaciones", "sum"),
        )
        .reset_index()
    )
    esperado["sentido"] = esperado["sentido"].fillna("__NULL__")
    esperado["fecha"] = pd.to_datetime(esperado["fecha"])
    esperado["hora"] = esperado["hora"].astype("int64")

    cur = db_cargado.execute(
        "SELECT sistema, unidad, fecha, hora, "
        "coalesce(sentido, '__NULL__') AS sentido, "
        "count(*) AS filas, sum(validaciones) AS validaciones "
        "FROM demanda_fiable "
        "GROUP BY sistema, unidad, fecha, hora, coalesce(sentido, '__NULL__')"
    )
    real = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    real["fecha"] = pd.to_datetime(real["fecha"])
    real["hora"] = real["hora"].astype("int64")

    assert len(real) == len(esperado), (
        f"grupos: vista={len(real):,} vs consolidada={len(esperado):,}"
    )
    merged = esperado.merge(
        real,
        on=keys,
        how="outer",
        suffixes=("_esperado", "_real"),
        indicator=True,
    )
    solo_esperado = int((merged["_merge"] == "left_only").sum())
    solo_real = int((merged["_merge"] == "right_only").sum())
    assert solo_esperado == 0 and solo_real == 0, (
        f"grupos sin contraparte: consolidada={solo_esperado}, vista={solo_real}"
    )
    dif_filas = merged[merged["filas_esperado"] != merged["filas_real"]]
    assert dif_filas.empty, f"{len(dif_filas)} grupos con conteo distinto"

    dif_sum = merged[
        merged["validaciones_esperado"].astype("float64")
        != merged["validaciones_real"].astype("float64")
    ]
    assert dif_sum.empty, (
        f"{len(dif_sum)} grupos con suma de validaciones distinta; "
        f"ejemplo: {dif_sum.head(3).to_dict(orient='records')}"
    )


def test_cobertura_unidad(db_cargado):
    row = db_cargado.execute(
        "SELECT count(*) AS total, "
        "count(*) FILTER (WHERE fiable) AS fiables, "
        "count(DISTINCT (sistema, unidad)) AS claves "
        "FROM cobertura_unidad"
    ).fetchone()
    assert row["total"] == 125
    assert row["fiables"] == 106
    assert row["claves"] == 125
