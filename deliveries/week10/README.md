# Semana 10 · Pipeline de ingesta + PostgreSQL

**Autor:** Elmer José Manuel Villegas Suarez — Data Engineer
**Alcance:** pipeline de datos contenerizado: ingesta de la demanda consolidada
(week08) → PostgreSQL 17 → export representativo, con telemetría de tráfico en
vivo (TomTom + fallback RF-05) y suite de regresión en pytest.

> Los EDA y el modelado viven en `deliveries/week08/` (Alessandro/Juan David).
> Esta semana solo consume sus salidas (`data_processed/clean/`) y las persiste
> en una base relacional con contratos de integridad verificables.

---

## 1. Qué hace el pipeline

```
data_processed/clean/*.parquet (week08, post-Fase 0)
        │  ingest_demand.py  (COPY masivo + conteos esperados)
        ▼
PostgreSQL 17 (contenedor docker `db`)
  · 6 tablas granulares (espejo 1:1 de los parquets)
  · cobertura_unidad (125 unidades, flag `fiable`)
  · vista demanda_fiable  = réplica exacta de demanda_consolidada_fiable.parquet
  · tablas de modelo: registro_modelo, prediccion, log_inferencia, feedback_usuario
  · trafico_en_vivo + log_inferencia (trazabilidad de cada llamada)
        │  export_data.py
        ▼
deliveries/week10/export/   (CSV + JSON + manifiesto con sha256)

TomTom Flow Segment Data ──► ingest_tomtom.py ──► trafico_en_vivo
        (si falla / no hay key)  fallback RF-05  (patrón horario determinista,
                                                  réplica de week07 congestion.py)
```

## 2. Requisitos

- Docker + Docker Compose (recomendado), **o** Python 3.14 + PostgreSQL en local
- `requirements-pipeline.txt` (pandas, pyarrow, httpx, psycopg[binary], dotenv,
  pytest) — **sin torch**: el modelado no corre aquí.

## 3. Cómo ejecutar

### Opción A — Docker (recomendada)

```bash
# 1) levanta todo: init-db + ingesta de demanda + snapshot de tráfico + export
docker compose up --build

# comandos sueltos del contenedor
docker compose run pipeline demand     # solo ingesta de demanda
docker compose run pipeline live       # 1 snapshot de tráfico
docker compose run pipeline loop       # snapshots cada LOOP_SECONDS (60 por defecto)
docker compose run pipeline export     # re-exporta a export/
docker compose run pipeline check      # reporte de conteos
docker compose run pipeline pytest     # suite de regresión/paridad

docker compose down        # detiene (pgdata persiste)
docker compose down -v     # detiene y borra la base
```

### Opción B — local

```bash
docker compose up -d db                     # solo el servidor PostgreSQL
cd deliveries/week10/code
python -m pipeline.run full                 # init-db + demand + live + export
python -m pytest tests -q                   # requiere el server arriba
```

### Subcomandos de `pipeline.run`

| Subcomando | Qué hace |
| :--- | :--- |
| `init-db` | Crea la base (si falta) y aplica `storage/schema.sql` |
| `demand [--solo-verify]` | Carga las 7 tablas granulares y verifica la vista `demanda_fiable` |
| `live` | Un snapshot de tráfico (6 segmentos, TomTom o fallback RF-05) |
| `loop [--cada SEG]` | Snapshots periódicos cada `LOOP_SECONDS` (60 s por defecto) |
| `export` | Escribe la muestra, reportes y JSON en `export/` |
| `check` | Reporte de conteos de tablas, vista y archivos exportados |
| `full` | `init-db` + `demand` + `live` + `export` + `check` (es el `CMD` por defecto) |

Variables (`.env` en la raíz, ver `.env.example`):

| Variable | Uso |
| :--- | :--- |
| `API_TOMTOM` / `TOMMTOM_KEY` | key TomTom (basta con una; se aceptan ambas) |
| `PGUSER` `PGPASSWORD` `PGDATABASE` `PGPORT` | credenciales del server |
| `PGHOST` | `localhost` en local; `db` lo fija docker-compose |
| `DATA_DIR` `EXPORT_DIR` `MODELO_OUTPUTS_DIR` | rutas (en contenedor ya vienen fijas) |

## 4. Estructura

```
deliveries/week10/
├── README.md                  ← este archivo
├── Dockerfile                 ← python:3.14-slim
├── requirements-pipeline.txt
├── code/
│   ├── pipeline/              ← config.py, ingest_demand.py, ingest_tomtom.py, run.py + Guia.md
│   ├── storage/               ← schema.sql, db.py (COPY), init_db.py + Guia.md
│   ├── export/export_data.py  ← CSV/JSON + manifiesto_export.json + Guia.md
│   ├── tests/                 ← pytest (paridad, regresión, tomtom mock, export) + Guia.md
│   └── entrypoint.sh
├── export/                    ← salidas del pipeline (commiteables)
└── data_processed/            ← espejo post-Fase 0 de week08 (gitignored)
```

> Cada carpeta de `code/` incluye una `Guia.md` con su uso detallado (comandos,
> API, variables y ejemplos).

## 5. Esquema (PostgreSQL 17)

| Tabla / vista | Grano | Clave |
| :--- | :--- | :--- |
| `troncal_hora` (398.928) | estación × fecha × hora | única (estacion, fecha, hora) |
| `metro_l1_hora` (341.640) | estación × fecha × hora × tipo_tarifa | única (estacion, fecha, hora, tipo_tarifa) |
| `metro_l1_total_hora` (170.820) | estación × fecha × hora | única (estacion, fecha, hora) |
| `corredores_hora` (8.253.635) | paradero × sentido × fecha × hora | `id` bigserial (**0 dups exactos**, sin unique por diseño) |
| `alimentador_hora` (4.670.304) | línea × ruta × paradero × sentido × fecha × hora | única (linea, ruta, n_paradero, fecha, hora, sentido_norm) |
| `alimentador_tarifa` (804.864) | ruta × fecha × hora × tipo_tarifa | única (fecha, ruta, hora, tipo_tarifa) |
| `cobertura_unidad` (125) | sistema × unidad | PK (sistema, unidad) — 106 `fiable` |
| **vista `demanda_fiable` (12.344.159)** | = `demanda_consolidada_fiable.parquet` | contrato de paridad |
| `registro_modelo`, `prediccion`, `log_inferencia`, `feedback_usuario` | modelo MLOps | ver `storage/schema.sql` |
| `trafico_en_vivo` | último snapshot por segmento | PK `segmento` |

## 6. Garantías verificadas por la suite

- **Conteo exacto por tabla** contra los valores de la Fase 0 (falla la ingesta
  si la fuente cambia).
- **Regresión de duplicados:** `corredores_hora` con **0 duplicados exactos**
  (las 517 filas duplicadas del Excel COSAC fueron eliminadas en la Fase 0 de
  week08; ver `DataAnalysis.md`).
- **Paridad exacta** vista `demanda_fiable` ↔ `demanda_consolidada_fiable.parquet`
  agrupada por (sistema, unidad, fecha, hora, sentido): conteos **y** sumas de
  validaciones idénticos (1.149.528 filas descartadas por cobertura = diferencia
  exacta entre consolidada y fiable).
- **Claves únicas** declaradas sin colisiones en las 5 tablas con natural key.
- **Trafico:** camino TomTom mockeado, caída a fallback RF-05 determinista
  (ratio ∈ [1, 3]) y traza completa en `log_inferencia`.

## 7. Decisiones y limitaciones

- **PostgreSQL 17 en Docker** (no DuckDB): consulta relacional, vistas y
  concurrencia para el consumo aguas abajo.
- **Carga granular por sistema** (no una tabla plana): cada parquet espeja una
  tabla; la vista `demanda_fiable` reconstruye el grano de modelado.
- **Duplicados Fase 0:** la causa raíz fue el Excel COSAC
  (`4950-2026-02-0012640.xlsx`); el fix vive en `prepare_parquet.py`
  (`drop_duplicates` exacto) y la regresión queda blindada en `tests/test_ingest.py`.
- **Clima omitido** de la capa de modelos (correlación r ≤ 0.10 con las
  validaciones; decisión documentada en `week08/docs/Model.md`).
- **ATU sigue siendo proxy:** troncal/metro usan datos ATU reales; corredores y
  alimentadores usan el dataset de TransMilenio (Bogotá) hasta que ATU entregue
  datos, más el complemento COSAC.
- **Fallback RF-05:** sin key o con error de red, el ratio de congestión sale
  del patrón horario determinista (picos 6–9 / 17–20, eventos fijos,
  clamp [1, 3]) — réplica de `week07/code/scripts/congestion.py`.
- `validaciones` se almacena como `double precision` en todas las tablas para
  que la vista unifique sin coerciones (los valores son conteos enteros).

## 8. Export (`deliveries/week10/export/`)

| Archivo | Contenido |
| :--- | :--- |
| `muestra_demanda_fiable.csv` | muestra determinista de 100.000 filas de la vista |
| `resumen_por_sistema.csv` | filas, unidades y suma de validaciones por sistema |
| `perfil_horario.csv` | promedio/total por sistema × hora (90 filas: metro L1 opera 5–22 h) |
| `trafico_tomtom.json` | snapshot de `trafico_en_vivo` |
| `modelo/` | manifiesto + métricas de los modelos de week08 |
| `manifiesto_export.json` | inventario con sha256 de cada archivo + conteos de la BD |
