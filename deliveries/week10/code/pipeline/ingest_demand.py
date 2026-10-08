from __future__ import annotations

import argparse
import time

import pandas as pd

from pipeline import config
from storage import db

TABLAS: dict[str, tuple[str, str]] = {
    # tabla -> (archivo en clean/, formato)
    "troncal_hora": ("troncal_hora.parquet", "parquet"),
    "metro_l1_hora": ("metro_l1_hora.parquet", "parquet"),
    "metro_l1_total_hora": ("metro_l1_total_hora.parquet", "parquet"),
    "corredores_hora": ("corredores_hora.parquet", "parquet"),
    "alimentador_hora": ("alimentador_hora.parquet", "parquet"),
    "alimentador_tarifa": ("alimentador_tarifa.parquet", "parquet"),
    "cobertura_unidad": ("calidad_cobertura.csv", "csv"),
}


def _leer(nombre: str, formato: str) -> pd.DataFrame:
    ruta = config.CLEAN_DIR / nombre
    if not ruta.exists():
        raise SystemExit(
            f"[ingest] falta {ruta}. Ejecuta la Fase 0 de week08 primero "
            "(prepare_parquet + EDA) o revisa DATA_DIR={config.DATA_DIR}."
        )
    if formato == "csv":
        return pd.read_csv(ruta)
    return pd.read_parquet(ruta)


def load_table(conn, table: str) -> int:
    archivo, formato = TABLAS[table]
    df = _leer(archivo, formato)
    esperado = config.FILAS_ESPERADAS[table]
    if len(df) != esperado:
        raise SystemExit(
            f"[ingest] {table}: el parquet tiene {len(df):,} filas y se "
            f"esperaban {esperado:,}. Fuente inconsistente — no se carga."
        )
    t0 = time.perf_counter()
    db.copy_df(conn, df, table, truncate=True)
    real = db.table_count(conn, table)
    if real != esperado:
        raise SystemExit(
            f"[ingest] {table}: quedaron {real:,} filas en la BD y se "
            f"esperaban {esperado:,}."
        )
    print(
        f"[ingest] {table:<22} {real:>10,} filas  "
        f"({time.perf_counter() - t0:5.1f}s)"
    )
    return real


def load_all(conn) -> dict[str, int]:
    return {tabla: load_table(conn, tabla) for tabla in TABLAS}


def verify_vista(conn) -> None:
    filas = conn.execute(
        "SELECT sistema, count(*) AS n FROM demanda_fiable "
        "GROUP BY sistema ORDER BY sistema"
    ).fetchall()
    visto = {r["sistema"]: r["n"] for r in filas}
    total = sum(visto.values())
    errores = []
    for sistema, esperado in config.FIABLE_ESPERADO.items():
        real = visto.get(sistema, 0)
        if real != esperado:
            errores.append(f"{sistema}: {real:,} != {esperado:,}")
    if total != config.FIABLE_TOTAL_ESPERADO:
        errores.append(f"total: {total:,} != {config.FIABLE_TOTAL_ESPERADO:,}")
    if errores:
        raise SystemExit(
            "[ingest] vista demanda_fiable fuera de contrato -> "
            + "; ".join(errores)
        )
    print(
        f"[ingest] vista demanda_fiable OK: {total:,} filas "
        + ", ".join(f"{s}={n:,}" for s, n in visto.items())
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--solo-verify",
        action="store_true",
        help="solo valida la vista (sin recargar tablas)",
    )
    args = parser.parse_args(argv)
    conn = db.connect()
    try:
        if not args.solo_verify:
            load_all(conn)
        verify_vista(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
