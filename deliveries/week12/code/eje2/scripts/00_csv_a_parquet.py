from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

RAIZ = Path(__file__).resolve().parents[3]          # deliveries/week12
CSV = RAIZ / "data" / "denuncias_unificado.csv"
OUT = RAIZ / "data_processed" / "eje2" / "raw"
CHUNK = 250_000

COLS_FECHA_MS = ["fecha_hora_registro_hecho", "fecha_hora_hecho", "fecha_actualizacion"]
COLS_ENTERO = ["objectid", "id_dgc", "año_hecho", "mes_hecho", "dia_hecho", "solo_denuncia", "estado",
               "id_comisaria_registro", "cuadra_hecho"]
COLS_FLOAT = ["lat_hecho", "long_hecho", "indice_priorizacion"]


def tipar(df: pd.DataFrame) -> pd.DataFrame:
    for c in COLS_FECHA_MS:
        df[c] = pd.to_datetime(pd.to_numeric(df[c], errors="coerce"), unit="ms")
    for c in COLS_ENTERO:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in COLS_FLOAT:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype("string")
    return df


def grupo(anio: pd.Series) -> pd.Series:
    """Etiqueta del archivo de salida: el año, o 'antes_2018' para años anteriores."""
    return anio.where(anio >= 2018).astype("Int64").astype("string").fillna("antes_2018")


def main() -> None:
    if not CSV.exists():
        raise FileNotFoundError(f"Falta {CSV}")
    OUT.mkdir(parents=True, exist_ok=True)
    for viejo in OUT.glob("denuncias*.parquet"):
        viejo.unlink()
    escritores, esquema, n = {}, None, 0
    for chunk in pd.read_csv(CSV, dtype=str, chunksize=CHUNK, keep_default_na=False, na_values=[""]):
        chunk = tipar(chunk)
        chunk["_fila"] = pd.array(range(n, n + len(chunk)), dtype="Int64")
        n += len(chunk)
        etiqueta = grupo(chunk["fecha_hora_hecho"].dt.year)
        for et, parte in chunk.groupby(etiqueta, sort=False):
            tabla = pa.Table.from_pandas(parte, preserve_index=False)
            if esquema is None:
                esquema = tabla.schema
            else:
                tabla = tabla.cast(esquema)
            if et not in escritores:
                escritores[et] = pq.ParquetWriter(OUT / f"denuncias_{et}.parquet", esquema, compression="zstd")
            escritores[et].write_table(tabla)
        print(f"{n:>10,} filas", flush=True)
    for w in escritores.values():
        w.close()
    for f in sorted(OUT.glob("denuncias_*.parquet")):
        print(f"{f.name:<30} {f.stat().st_size / 1e6:6.1f} MB")
    print(f"OK {OUT} ({n:,} filas en {len(escritores)} archivos)")


if __name__ == "__main__":
    main()
