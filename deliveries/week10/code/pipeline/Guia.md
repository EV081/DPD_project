# Guía · `pipeline/`

Orquestación del pipeline: ingesta de demanda, telemetría de
tráfico y export. Para el panorama general ver `deliveries/week10/README.md`.

## Contenido

| Archivo | Rol |
| :--- | :--- |
| `config.py` | Configuración y constantes de regresión (`FILAS_ESPERADAS`, `FIABLE_ESPERADO`) |
| `ingest_demand.py` | Carga granular de los parquets de `data_processed/clean/` a PostgreSQL |
| `ingest_tomtom.py` | Snapshot de tráfico (TomTom) con fallback RF-05 sintético |
| `run.py` | Orquestador con subcomandos (entrypoint del contenedor) |

## Cómo ejecutar

Los módulos se invocan como paquete; el directorio de trabajo debe ser
`deliveries/week10/code` (en Docker ya es `/app`).

```bash
# local (desde deliveries/week10/code)
python -m pipeline.run full          # init-db + demand + live + export + check
python -m pipeline.run demand        # ingesta granular + verificación de la vista
python -m pipeline.run live          # un snapshot de tráfico
python -m pipeline.run check         # reporte de conteos y exports

# docker (desde la raíz del repo)
docker compose run --rm pipeline full
docker compose run --rm pipeline demand
docker compose run --rm pipeline live
docker compose run --rm pipeline check
```

Los subcomandos disponibles son: **`init-db`, `demand`, `live`, `loop`,
`export`, `check`, `full`** (los mismos que `CMD` del contenedor, por eso
`docker compose up --build` ejecuta `full` por defecto).

| Subcomando | Qué hace |
| :--- | :--- |
| `init-db` | Crea la base (si falta) y aplica `storage/schema.sql` |
| `demand [--solo-verify]` | Ingresa las 7 tablas y verifica la vista `demanda_fiable` |
| `live` | Un snapshot de tráfico (6 segmentos) |
| `loop [--cada SEG]` | Snapshots periódicos (`LOOP_SECONDS`, default 60 s) |
| `export` | Escribe los archivos en `EXPORT_DIR` |
| `check` | Reporte de conteos de tablas, vista y archivos exportados |
| `full` | `init-db` + `demand` + `live` + `export` + `check` |

Ejemplos:

```bash
python -m pipeline.run demand --solo-verify   # re-valida la vista sin recargar
python -m pipeline.run loop --cada 30          # snapshots cada 30 segundos
docker compose run --rm pipeline check         # inventario rápido
```

## Variables de entorno (`config.py`)

| Variable | Default | Uso |
| :--- | :--- | :--- |
| `DATA_DIR` | `week10/data_processed` | Raíz de datos (los parquets van en `DATA_DIR/clean/`) |
| `EXPORT_DIR` | `week10/export` | Destino de `export_data` |
| `MODELO_OUTPUTS_DIR` | `code/model/outputs` | Outputs de week08 que se copian al export |
| `API_TOMTOM` / `TOMMTOM_KEY` | — | Key TomTom (basta con una; se aceptan ambas) |
| `TOMTOM_TIMEOUT` | `4.0` | Timeout por llamada (segundos) |
| `TOMTOM_SEGMENT` | `10` | Tamaño del segmento relativo de `flowSegmentData` |
| `LOOP_SECONDS` | `60` | Intervalo por defecto de `loop` |
| `PGHOST` `PGPORT` `PGUSER` `PGPASSWORD` `PGDATABASE` | `localhost:5432` | Conexión (ver `storage/Guia.md`) |

## Regresión de datos

`config.FILAS_ESPERADAS` fija el contrato de la Fase 0 (p. ej. corredores =
8.253.635). Si un parquet no coincide, `ingest_demand` **aborta antes de cargar**
en vez de persistir datos inconsistentes. Si cambian los datos de week08 hay que
actualizar esos valores a conciencia (y re-correr `tests/`).

## Fallback RF-05

`ingest_tomtom` replica el patrón horario determinista de
`week07/code/scripts/congestion.py` (picos 6–9 / 17–20, eventos fijos,
clamp `[1, 3]`). Se activa si falta la key o si la llamada falla, y deja la
traza en `log_inferencia` (`fuente='fallback'`, `status='fallback:<error>'`).
La función `ratio_sintetico(ts)` es pura y testeable sin red.

## Tráfico: `trafico_en_vivo` vs `log_inferencia`

- **`trafico_en_vivo`** = estado **actual** (última lectura). Una fila por
  `segmento` (6), con `UPSERT` (`ON CONFLICT DO UPDATE`): se **reescribe** cada
  ciclo y por eso **siempre son 6 filas**.
- **`log_inferencia`** = **historial** append-only. Una fila por segmento y por
  ciclo: **crece +6** cada vez (6, 12, 18…) y nunca se borra.

Un **ciclo** = una pasada de `live`/`loop`: 6 llamadas (una por segmento) +
escritura, y luego `LOOP_SECONDS` de espera. Ej.: `loop --cada 30`.

Cómo distinguir un dato real de un fallback:

| Columna | Dato real | Fallback RF-05 |
| :--- | :--- | :--- |
| `fuente` | `tomtom` | `fallback` |
| `log_inferencia.status` | `ok` | `fallback:TimeoutError`, `fallback:HTTPStatusError`, etc. |
| `detalle.motivo` | — | mensaje de la excepción |

### Cuidado con `pytest` (datos de prueba)

`tests/test_tomtom.py` usa el fixture `trafico_limpio`, que hace
`TRUNCATE log_inferencia, trafico_en_vivo` al inicio de cada test de tráfico
(`test_tomtom.py:12-13`). El último test *simula* un timeout
(`raise TimeoutError("timeout simulado")`) para comprobar el fallback.

Consecuencia: **después de correr `pytest`, esas dos tablas quedan con datos de
prueba** (`fuente=fallback`, `status=fallback:TimeoutError`), no con tu lectura
real de TomTom. Por eso:

```bash
docker compose run --rm pipeline pytest     # corre los tests
docker compose run --rm pipeline live       # RESTAURA las 6 filas reales
# ...y, si vas a exportar, recién ahora:
docker compose run --rm pipeline export     # trafico_tomtom.json ya con datos reales
```

Reglas prácticas:

- Tras `pytest`, corre `live` (o `full`) para restaurar datos reales; si no, el
  siguiente `export` copiará el snapshot del test.
- No corras `pytest` en paralelo con un `loop` (el `TRUNCATE` borra lo que el
  ciclo acaba de escribir; hay carrera).
- Para ver un snapshot real en vivo, `docker compose run --rm pipeline live`
  escribe **de inmediato** (no hay que esperar los 60 s).

## Uso programático

```python
from pipeline import ingest_demand
from storage import db

conn = db.connect()
try:
    ingest_demand.load_all(conn)      # 7 tablas
    ingest_demand.verify_vista(conn)  # valida demanda_fiable
finally:
    conn.close()
```
