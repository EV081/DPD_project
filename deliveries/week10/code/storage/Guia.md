# Guía · `storage/`

Capa de persistencia: esquema, conexión y carga COPY. El esquema completo y
comentado vive en `schema.sql`; el README de la semana explica el porqué de
cada tabla.

## Contenido

| Archivo | Rol |
| :--- | :--- |
| `schema.sql` | DDL idempotente: 6 tablas granulares, `cobertura_unidad`, vista `demanda_fiable`, tablas de modelo y `trafico_en_vivo` |
| `db.py` | Conexión (`PG*`), `ensure_database`, `init_schema`, `table_count`, `copy_df` |
| `init_db.py` | Punto de entrada: crea la base y aplica el esquema |

## Inicializar la base

```bash
# local (requiere PostgreSQL arriba)
cd deliveries/week10/code && python -m storage.init_db

# docker
docker compose run --rm pipeline init-db
```

`init_db` es idempotente: crea `PGDATABASE` si no existe y aplica el esquema con
`IF NOT EXISTS` / `CREATE OR REPLACE`. Se puede correr las veces que haga falta.

## Conexión manual

```bash
docker compose exec db psql -U urbansafe -d urbansafe
# \dt  -> tablas      \dv -> vistas      \d+ demanda_fiable -> columnas
```

## API de `db.py`

```python
from storage import db

db.dsn()                       # "host=... port=... dbname=... user=... password=..."
conn = db.connect()            # autocommit=True, filas tipo dict (row_factory=dict_row)

db.ensure_database()           # crea PGDATABASE si falta (conecta a `postgres`)
db.init_schema(conn)           # aplica schema.sql (en una transacción)
db.table_count(conn, "corredores_hora")   # -> int
db.copy_df(conn, df, "corredores_hora", truncate=True)  # -> filas cargadas
```

Detalles de `copy_df`:

- Usa `COPY ... FROM STDIN WITH (FORMAT csv)` en streaming por chunks
  (`chunksize=100_000`), sin header.
- `truncate=True` hace `TRUNCATE` + `COPY` dentro de **una sola transacción**
  (carga atómica e idempotente).
- Formatea `fecha` como `%Y-%m-%d`; celdas vacías → `NULL`.
- Los `bool` de pandas (`True`/`False`) y los `pd.NA` se adaptan solos
  (PostgreSQL acepta `True`/`False` como booleanos; vacío = `NULL`).

```python
import pandas as pd
from storage import db

conn = db.connect()
try:
    df = pd.read_parquet("data_processed/clean/troncal_hora.parquet")
    db.copy_df(conn, df, "troncal_hora", truncate=True)
finally:
    conn.close()
```

Convención: `connect()` deja la conexión en **autocommit**; las operaciones
multi-sentencia se agrupan con `with conn.transaction():`, y el llamador cierra
la conexión (`try/finally` o un fixture de test).

## Cambiar el esquema

1. Editar `schema.sql` manteniéndolo idempotente (`IF NOT EXISTS` / `OR REPLACE`).
2. Re-aplicar: `python -m storage.init_db` (o `pipeline.run init-db`).
3. Si cambia el grano o los conteos, actualizar `config.FILAS_ESPERADAS` y
   `config.FIABLE_ESPERADO` y correr `tests/`.
