from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

import pandas as pd
import psycopg
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def dsn() -> str:
    import os

    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER", "urbansafe")
    password = os.getenv("PGPASSWORD", "urbansafe_dev")
    dbname = os.getenv("PGDATABASE", "urbansafe")
    return (
        f"host={host} port={port} dbname={dbname} "
        f"user={user} password={password}"
    )


def connect() -> psycopg.Connection:
    conn = psycopg.connect(dsn(), row_factory=dict_row)
    conn.autocommit = True  # cada operacion explicita se confirma sola;
    return conn


def ensure_database() -> None:
    import os

    dbname = os.getenv("PGDATABASE", "urbansafe")
    with psycopg.connect(
        f"host={os.getenv('PGHOST', 'localhost')} port={os.getenv('PGPORT', '5432')} "
        f"dbname=postgres user={os.getenv('PGUSER', 'urbansafe')} "
        f"password={os.getenv('PGPASSWORD', 'urbansafe_dev')}",
        autocommit=True,
    ) as admin:
        row = admin.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if row is None:
            admin.execute(f'CREATE DATABASE "{dbname}"')


def init_schema(conn: psycopg.Connection) -> None:
    with conn.transaction():
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def table_count(conn: psycopg.Connection, table: str) -> int:
    row = conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()
    return int(row["n"])


def copy_df(
    conn: psycopg.Connection,
    df: pd.DataFrame,
    table: str,
    columns: Iterable[str] | None = None,
    chunksize: int = 100_000,
    truncate: bool = False,
) -> int:
    cols = list(columns) if columns is not None else list(df.columns)
    with conn.transaction():
        if truncate:
            conn.execute(f"TRUNCATE TABLE {table}")
        with conn.cursor() as cur:
            with cur.copy(
                f"COPY {table} ({', '.join(cols)}) FROM STDIN WITH (FORMAT csv)"
            ) as copy:
                for start in range(0, len(df), chunksize):
                    buf = io.StringIO()
                    df.iloc[start : start + chunksize][cols].to_csv(
                        buf, index=False, header=False, date_format="%Y-%m-%d"
                    )
                    copy.write(buf.getvalue().encode("utf-8"))
    return len(df)
