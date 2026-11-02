"""Particionado nativo de Postgres por mes (PARTITION BY RANGE) para las tablas que crecen con el uso.

- La tabla "padre" se crea con el mismo esquema del modelo SQLAlchemy (no se repiten las columnas) más
  ``PARTITION BY RANGE (<columna>)``; hay una partición por mes (``<tabla>_AAAA_MM``) y una ``DEFAULT`` de seguridad,
  para que un registro fuera de rango nunca falle.
- ``ensure_particiones`` crea los meses que faltan (idempotente) y rescata filas que hubieran caído en la partición DEFAULT.
- ``retener`` quita (DETACH + DROP) los meses más viejos que N meses: borrar un mes no cuesta un ``DELETE``.
- Solo Postgres: en otros motores la tabla queda normal y estas funciones no hacen nada.
"""
from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

PREFIJO_DEFAULT = "_default"


# --------------------------------------------------------------------------- funciones puras (DDL)
def sumar_meses(anio: int, mes: int, k: int) -> tuple[int, int]:
    total = anio * 12 + (mes - 1) + k
    return total // 12, total % 12 + 1


def meses_entre(desde: tuple[int, int], hasta: tuple[int, int]) -> list[tuple[int, int]]:
    """Lista de (año, mes) desde `desde` hasta `hasta`, ambos incluidos."""
    out, (a, m) = [], desde
    while (a, m) <= hasta:
        out.append((a, m))
        a, m = sumar_meses(a, m, 1)
    return out


def nombre_particion(tabla: str, anio: int, mes: int) -> str:
    return f"{tabla}_{anio}_{mes:02d}"


def mes_de_particion(tabla: str, nombre: str) -> tuple[int, int] | None:
    """(año, mes) de una partición mensual, o None si no lo es (p. ej. la DEFAULT)."""
    m = re.fullmatch(rf"{re.escape(tabla)}_(\d{{4}})_(\d{{2}})", nombre)
    return (int(m.group(1)), int(m.group(2))) if m else None


def rango_mes(anio: int, mes: int) -> tuple[str, str]:
    a2, m2 = sumar_meses(anio, mes, 1)
    return f"{anio}-{mes:02d}-01", f"{a2}-{m2:02d}-01"


def ddl_particion(tabla: str, anio: int, mes: int) -> str:
    desde, hasta = rango_mes(anio, mes)
    return (f"CREATE TABLE IF NOT EXISTS {nombre_particion(tabla, anio, mes)} PARTITION OF {tabla} "
            f"FOR VALUES FROM ('{desde}') TO ('{hasta}')")


def ddl_particion_default(tabla: str) -> str:
    return f"CREATE TABLE IF NOT EXISTS {tabla}{PREFIJO_DEFAULT} PARTITION OF {tabla} DEFAULT"


def ddl_tabla_particionada(table, columna: str) -> list[str]:
    """Sentencias que crean la tabla padre particionada (y sus índices) a partir de un ``sqlalchemy.Table``."""
    dialecto = postgresql.dialect()
    crear = str(CreateTable(table, if_not_exists=True).compile(dialect=dialecto)).strip()
    crear = f"{crear} PARTITION BY RANGE ({columna})"
    indices = [str(CreateIndex(ix, if_not_exists=True).compile(dialect=dialecto)).strip() for ix in table.indexes]
    return [crear, *indices]


# --------------------------------------------------------------------------- operaciones sobre la base
def es_postgres(engine) -> bool:
    return engine.dialect.name == "postgresql"


def listar_particiones(engine, tabla: str) -> list[str]:
    with engine.connect() as con:
        filas = con.execute(text(
            "SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid "
            "JOIN pg_class p ON p.oid = i.inhparent WHERE p.relname = :t ORDER BY c.relname"), {"t": tabla}).all()
    return [f[0] for f in filas]


def _hoy(hoy: dt.date | None) -> dt.date:
    return hoy or dt.datetime.now(dt.timezone.utc).date()


def ensure_particiones(engine, tabla: str, columna: str, adelante: int = 3, atras: int = 1, hoy: dt.date | None = None) -> list[str]:
    """Crea las particiones de [mes actual − atrás, mes actual + adelante] que falten y devuelve los nombres creados."""
    if not es_postgres(engine):
        return []
    hoy = _hoy(hoy)
    desde = sumar_meses(hoy.year, hoy.month, -atras)
    hasta = sumar_meses(hoy.year, hoy.month, adelante)
    existentes = set(listar_particiones(engine, tabla))
    creadas = []
    with engine.begin() as con:
        con.execute(text(ddl_particion_default(tabla)))
        for a, m in meses_entre(desde, hasta):
            nombre = nombre_particion(tabla, a, m)
            if nombre in existentes:
                continue
            _mover_desde_default(con, tabla, columna, a, m)
            con.execute(text(ddl_particion(tabla, a, m)))
            _devolver_movidas(con, tabla)
            creadas.append(nombre)
    return creadas


def _mover_desde_default(con, tabla: str, columna: str, anio: int, mes: int) -> None:
    """Si la partición DEFAULT ya tiene filas de ese mes, las aparta (Postgres no deja crear la partición con ellas ahí)."""
    desde, hasta = rango_mes(anio, mes)
    con.execute(text(f"CREATE TEMP TABLE IF NOT EXISTS _mover_{tabla} (LIKE {tabla} INCLUDING DEFAULTS) ON COMMIT DROP"))
    con.execute(text(
        f"WITH m AS (DELETE FROM {tabla}{PREFIJO_DEFAULT} WHERE {columna} >= '{desde}' AND {columna} < '{hasta}' RETURNING *) "
        f"INSERT INTO _mover_{tabla} SELECT * FROM m"))


def _devolver_movidas(con, tabla: str) -> None:
    con.execute(text(f"INSERT INTO {tabla} SELECT * FROM _mover_{tabla}"))
    con.execute(text(f"DELETE FROM _mover_{tabla}"))


def retener(engine, tabla: str, meses: int, hoy: dt.date | None = None) -> list[str]:
    """Elimina las particiones mensuales anteriores a (mes actual − meses). Nunca toca la partición DEFAULT."""
    if not es_postgres(engine):
        return []
    hoy = _hoy(hoy)
    limite = sumar_meses(hoy.year, hoy.month, -meses)
    borradas = []
    with engine.begin() as con:
        for nombre in listar_particiones(engine, tabla):
            ym = mes_de_particion(tabla, nombre)
            if ym is not None and ym < limite:
                con.execute(text(f"ALTER TABLE {tabla} DETACH PARTITION {nombre}"))
                con.execute(text(f"DROP TABLE {nombre}"))
                borradas.append(nombre)
    return borradas


def crear_tablas_particionadas(engine, tablas: list, columnas: dict[str, str], adelante: int = 3, hoy: dt.date | None = None) -> None:
    """Crea (si no existen) las tablas padre particionadas con sus índices y las particiones iniciales."""
    if not es_postgres(engine):
        return
    with engine.begin() as con:
        for t in tablas:
            for sentencia in ddl_tabla_particionada(t, columnas[t.name]):
                con.execute(text(sentencia))
    for t in tablas:
        ensure_particiones(engine, t.name, columnas[t.name], adelante=adelante, hoy=hoy)


def ensure_todas(engine, columnas: dict[str, str], adelante: int = 3, hoy: dt.date | None = None) -> dict[str, list[str]]:
    return {t: ensure_particiones(engine, t, c, adelante=adelante, hoy=hoy) for t, c in columnas.items()}


def retener_todas(engine, columnas: dict[str, str], meses: int, hoy: dt.date | None = None) -> dict[str, list[str]]:
    return {t: retener(engine, t, meses, hoy=hoy) for t in columnas}
