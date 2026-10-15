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
docker compose run pipeline loop       # snapshots cada LOOP_SECONDS (300 por defecto)
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
| `loop [--cada SEG]` | Snapshots periódicos cada `LOOP_SECONDS` (300 s por defecto) |
| `predict [--dia] [--modo] [--sistemas]` | Batch diario: pronostica 24 h y llena `prediccion` (aforo, ETA, regla U) |
| `paraderos` | Carga paraderos, rutas y trazados (GeoJSON de `scripts/build_trazados.py`) y habilita `paraderos_cercanos()` |
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
│   ├── export/                ← export_data.py (CSV/JSON + manifiesto), export_paraderos.py + Guia.md
│   ├── scripts/               ← paraderos, rutas, OCR, Google Places y validaciones (ver §10)
│   ├── tests/                 ← pytest (paridad, regresión, tomtom mock, export) + Guia.md
│   └── entrypoint.sh
├── export/                    ← salidas del pipeline (commiteables)
├── revision/                  ← visor de paradas (mapa_revision.html) y su guía
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
| `paraderos.csv`, `rutas.csv`, `rutas_trazados.geojson` | paradas por ruta y sentido, rutas y trazados (ver §10) |
| `modelo/` | manifiesto + métricas de los modelos de week08 |
| `manifiesto_export.json` | inventario con sha256 de cada archivo + conteos de la BD |

## 9. Modelos serializados (Issue #19 — Juan David Velo)

`models/` contiene un modelo operativo por sistema (Metro L1, troncal, corredores, alimentadores)
entrenado con todo 2025 y elegido en la evaluación v2 de week09 (validación 15–31 oct, test
1 nov – 31 dic): pronosticador principal, configuración de aforo (crowding), bandas conformal 80 %,
clasificador de aforo de respaldo, detector de anomalías, `model_card.json` por sistema y un
`manifest.json` con versión, hiperparámetros, métricas contra baselines y sha256 de cada artefacto.

```bash
pip install -r requirements-models.txt                      # (sin torch si solo se usa LightGBM)
python code/model/serializar_modelos.py                      # re-entrena y re-serializa
python code/model/verificar_modelos.py                       # sha256 + recarga + re-inferencia → models/verify_report.md
cd code && python -m pytest tests/test_models.py -q          # no requiere PostgreSQL
```

Inferencia (backend / batch diario → tabla `prediccion`): `code/model/inferencia.py`
(`ModeloSistema.cargar(sistema).pronosticar(contexto, dia)`). Detalle en `models/README.md`.
`data_processed/` de esta carpeta es una copia del de week09 (mismos conteos que `FILAS_ESPERADAS`,
con el calendario de 16 feriados).

## 10. Paraderos, rutas y trazados (para el mapa)

### Dónde están los datos

| Qué | Dónde |
| :--- | :--- |
| **Entrega para el equipo** | `export/paraderos.csv` (una fila por parada, ruta y sentido), `export/rutas.csv`, `export/rutas_trazados.geojson` |
| Base de datos | tablas `paradero`, `ruta`, `paradero_ruta` y vista `ruta_paradas` |
| Insumos intermedios | `data/fuentes/` (gitignored): `alimentadores_paradas_geo.csv`, `google_paraderos.csv`, `google_cercanos.csv`, `geo/*.geojson` |

`python -m pipeline.run paraderos` carga los GeoJSON a PostgreSQL (`GEO_DIR`; en Docker `/data/geo`) y
`python -m pipeline.run export` regenera los tres archivos de `export/`. Un compañero que solo necesite las
paradas **no tiene que repetir nada**: le basta `export/paraderos.csv`.

Columnas de `paraderos.csv`: `sistema, ruta, ruta_nombre, sentido, orden, paradero, lat, lon, calidad_coord,
confianza, precision, evidencia, unidad_modelo, origen_trazado`.

### Consulta para el backend

```sql
SELECT * FROM paraderos_cercanos(-12.0519, -77.0364, 600, 10);  -- lat, lon, radio_m, limite
-- paradero_id, sistema, nombre, lat, lon, calidad_coord, distancia_m, rutas (JSONB)

SELECT sentido, orden, nombre, lat, lon FROM ruta_paradas   -- paradero a paradero
WHERE sistema = 'corredor' AND ruta = '301' ORDER BY direccion, orden;
```

El backend debe **geocodificar la dirección** del usuario a `lat/lon` antes de llamarla (no está en este pipeline).

### Origen de las coordenadas

| Sistema | Paradas | Coordenada | Trazado |
| :--- | :--- | :--- | :--- |
| Metro L1 | 26 | Shapefile oficial de ATU | Eje oficial (`shapefile_atu`) |
| Corredores | 701 | `Latitude/Longitude` del Excel de ATU (`gps_atu`) | Calculado con OSRM entre paraderos (`derivado_osrm`), **no es el oficial** |
| Troncal (Metropolitano) | 44 estaciones | 34 OSM por nombre, 6 Google, 4 manuales; todas verificadas sobre la línea troncal | Relaciones OSM `network=Metropolitano` |
| Alimentadores | 757 paradas (por sentido) | **Inferidas**: nombre y orden de ATU + coordenada OSM/Google | `derivado_osrm` sobre esas paradas |

ATU **no publica coordenadas de los alimentadores**, solo nombre y orden por sentido (portal QR, o impresos en
imagen en 3 servicios, que se leen con OCR). Cada parada se ubica así: candidatos OSM por nombre exacto y
resultados de Google Places; se elige uno por parada minimizando los saltos entre consecutivas (Viterbi); ida
y vuelta caen a la derecha de su sentido de marcha; y, sin candidato, el punto de la calle homónima más
cercano a sus vecinas. Si nada aplica, la parada queda **sin coordenada**.

### Atributos de calidad (alimentadores)

| Atributo | Valores | Significado |
| :--- | :--- | :--- |
| `precision` | `exacta` | Google tiene una parada **con ese nombre** a ≤ 50 m de la coordenada |
| | `aproximada` | Hay coordenada pero Google no la confirma por nombre |
| `evidencia` | `nombre_google` | respalda `exacta` |
| | `parada_cercana_google` | `aproximada`, pero Google tiene **otra** parada a ≤ 50 m (la esquina sí tiene paradero) |
| | `sin_parada_google` | `aproximada` y Google no tiene ninguna parada ahí |
| | `revision_humana` | corregida a mano |
| `confianza` | `alta` / `media` / `baja` / `verificada` | método de ubicación (ver tabla de validación) |
| `ruta.pct_exactas` | 0–100 | porcentaje de paradas exactas de la ruta |
| `ruta.tiene_trazado` | `true` / `false` | `false` = ATU no publica geometría; `trazado` queda NULL y solo se muestran las paradas |
| `ruta.origen_trazado` | `shapefile_atu` / `osm_relation` / `derivado_osrm` / `sin_trazado` | procedencia de la línea dibujada |

Los campos de `paradero` (`confianza`, `precision`, `evidencia`) no tienen NULL: fuera de los alimentadores se
asignan según la fuente de la coordenada (`gps_atu` y `shapefile` → `alta`/`exacta`; `osm_nombre` y
`google_places` → `media`/`aproximada`; `revision_humana` → `verificada`/`exacta`). `unidad_modelo` sí es NULL
cuando la ruta no tiene demanda fiable para predecir (20 rutas: 3 alimentadores y 17 corredores).

Resultado actual (757 paradas por sentido): **308 exactas (41 %)**, 404 aproximadas (267 con parada de Google
cerca, 137 sin parada en Google) y **45 sin coordenada**. Por ruta: 2 con ≥ 75 % exactas, 10 con 50–74 %,
14 con 25–49 % y 1 con < 25 %.

> «Aproximada» **no significa que la parada no exista**: Google no tiene todas las paradas de Lima. Significa
> que la coordenada no está confirmada. Su error va desde decenas de metros hasta varios kilómetros; las de
> confianza `baja` tienen mediana de ~2 km frente a Google. Quien consuma los datos debe filtrar por `precision`.

### Validación (medida, no supuesta)

| Método | Dónde se validó | Resultado |
| :--- | :--- | :--- |
| Nombre OSM exacto + secuencia | 993 paradas de corredor (GPS de ATU como verdad) | resueltas 78 %; error mediano **17 m**, p90 148 m, ≤ 150 m el 92 % |
| Consulta a Google Places | 100 paradas de corredor | 83 % con parada encontrada; mediana 13 m, **p90 760 m** (homónimos): se usa como candidato, no como verdad |
| Alta / media / baja vs Google | alimentadores | mediana a Google 11 m / 12 m / 1 992 m |
| Estaciones del Metropolitano vs línea troncal | 44 estaciones | detectó 10 mal ubicadas (hasta 4.3 km) que se corrigieron |
| Georreferenciar los **mapas PNG** de ATU | Metro L1 y 5 mapas de corredor | mediana 280 m (L1) a varios km: **no se usan para coordenadas** |
| Interpolación por imagen entre paradas ancla | 88 paradas | mediana 172 m (reparto uniforme: 213 m) |

### Scripts (`code/scripts/`)

| Script | Qué hace |
| :--- | :--- |
| `build_trazados.py` | puntos y trazados de L1, corredores, troncal y servicios (shapefiles, Excel, OSM/Overpass, OSRM) |
| `download_alimentadores.py` | nombre, orden, sentido, horarios e imágenes de los alimentadores (portal QR) |
| `ocr_listas_alimentadores.py` | lista de paradas impresa en imagen (Los Próceres, Villa El Salvador, Trapiche-Universidad) |
| `geocodificar_alimentadores.py` | coordenadas de alimentadores y su `precision`; `--validar` mide el método sobre corredores |
| `consultar_google_paraderos.py` | Google Places: consultas guardadas en CSV (`--completar`, `--validar N`, `--contrastar-oficiales`) |
| `corregir_troncal_con_google.py` | corrige estaciones de troncal fuera de la línea; aplica `correcciones_troncal.csv` |
| `validar_georef.py`, `interpolar_por_imagen.py` | validación de los mapas PNG |
| `generar_revision.py` | genera el visor `revision/mapa_revision.html` |

Orden de reproducción: `build_trazados.py` → `corregir_troncal_con_google.py` → `download_alimentadores.py` →
`ocr_listas_alimentadores.py` → `consultar_google_paraderos.py` → `geocodificar_alimentadores.py` →
`pipeline.run paraderos` → `pipeline.run export`.

### Limitaciones y condiciones

- **Términos de Google**: los resultados de Google Places se usan en un CSV compartido para el prototipo del
  curso; los términos de Google Maps Platform limitan cuánto tiempo se pueden conservar las coordenadas y su
  uso fuera de un mapa de Google. **Antes de producción** hay que reemplazarlas por datos oficiales de ATU o
  cumplir esos términos. Requiere `GOOGLE_MAPS_API_KEY` y facturación activa; se hicieron ~1 350 consultas.
- 13 de 29 rutas de corredor tienen GPS pero **no orden de paradas ni trazado**.
- Solo 12 de 29 rutas de corredor y 19 de 23 alimentadores modelados tienen demanda enlazada (`unidad_modelo`).
- Sin horarios de paso reales: la consulta devuelve *qué rutas pasan*, no cuándo llega el bus.
- El visor [`revision/mapa_revision.html`](revision/mapa_revision.html) permite ver y, opcionalmente,
  corregir paradas; ver [`revision/LEEME.md`](revision/LEEME.md).
