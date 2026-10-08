# Guía · `tests/`

Suite de regresión y paridad del pipeline (pytest). Es el contrato que garantiza
que la ingesta no se desvía de la fuente.

## Contenido

| Archivo | Cubre |
| :--- | :--- |
| `conftest.py` | Fixtures `db` (esquema) y `db_cargado` (ingesta + verificación de la vista) |
| `test_ingest.py` | Conteos exactos, 0 duplicados en corredores, claves únicas, paridad vista ↔ parquet |
| `test_tomtom.py` | Fallback RF-05 determinista y caminos TomTom mockeados |
| `test_export.py` | Archivos generados, límite de muestra y manifiesto con sha256 |

## Requisitos

- PostgreSQL arriba: `docker compose up -d db` (el default local es
  `localhost:5432`, usuario/clave `urbansafe`).
- `requirements-pipeline.txt` instalado (pytest incluido).

## Cómo correr

```bash
# docker (recomendado; es el entorno de la entrega)
docker compose run --rm pipeline pytest

# local
cd deliveries/week10/code
python -m pytest tests -q

# un solo archivo o test
python -m pytest tests/test_tomtom.py -q
python -m pytest tests/test_ingest.py -k paridad -q
```

## Fixtures (`conftest.py`)

- `db`: verifica que el server responde (si no, falla con el comando a correr),
  crea la base y aplica el esquema una vez por sesión.
- `db_cargado`: sobre `db`, ejecuta `load_all` + `verify_vista`. **Es costoso
  (~2–4 min por los 14,6 M de filas)** y solo corre si algún test que lo pide se
  ejecuta; queda cacheado para toda la sesión.

Consejo: `test_tomtom.py` depende solo de `db` (rápido); si solo tocas el
tráfico, `python -m pytest tests/test_tomtom.py` no dispara la carga completa.

## Qué garantiza (lo importante)

- **Conteos exactos** de las 7 tablas contra `config.FILAS_ESPERADAS`.
- **Regresión Fase 0**: `corredores_hora.parquet` con 0 duplicados exactos
  (las 517 filas del Excel COSAC ya no están).
- **Paridad exacta** de `demanda_fiable` con `demanda_consolidada_fiable.parquet`
  agrupadas por (sistema, unidad, fecha, hora, sentido): mismo número de grupos,
  mismos conteos y mismas sumas de validaciones.
- **Claves únicas** sin colisiones (alimentador, troncal, metro, tarifa).
- **TomTom**: éxito mockeado, y caída a fallback determinista (ratio ∈ `[1, 3]`)
  cuando falta la key o la llamada falla; traza correcta en `log_inferencia`.
- **Export**: 100.000 filas de muestra, 4 sistemas, 90 filas de perfil, JSON de
  tráfico parseable y sha256 del manifiesto reproducible.

## Costo y duración

La suite completa tarda ~4–5 min (dominado por la carga inicial y el test de
paridad, que lee 12,3 M de filas del parquet y agrupa en SQL). Los tests de
tráfico y export son rápidos una vez cargada la base.

## Extender la suite

- Nuevos chequeos de datos → `test_ingest.py` usando `db_cargado`.
- Nuevos proveedores de tráfico → mockear `ingest_tomtom._obtener` (como en
  `test_tomtom.py`) para no salir a red.
- Mantener los tests como **regresión**: si cambia la fuente de week08, los
  conteos de `config.py` y esta suite son la red de seguridad.
