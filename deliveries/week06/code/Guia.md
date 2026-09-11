# Guía de descarga de datasets

Todos los scripts se ejecutan con el venv (antes instalar los requirements.txt) del proyecto desde `deliveries/week06/`:

```bash
cd deliveries/week06
../../.venv/bin/python code/<script>.py
```

Cada script es idempotente (si el archivo ya existe, lo salta).

---

## 1. TransMilenio — Validaciones diarias (`download_transmilenio.py`)

- **Fuente:** `https://storage.googleapis.com/validaciones_tmsa/ValidacionTroncal/validacionTroncal{YYYYMMDD}.zip`
- **Qué guarda:** `data/transmilenio/diario/validacionTroncal{YYYYMMDD}.zip`
- **Variables (editar en el script):**
  - `DESDE = date(2026, 7, 1)` — primer día.
  - `HASTA = date(2026, 8, 31)` — último día.
- **Ejecución:**
  ```bash
  ../../.venv/bin/python code/download_transmilenio.py
  ```

---

## 2. TransMilenio — GeoJSON de estaciones y trazados (`download_geo.py`)

- **Fuente:** Portal de Datos Abiertos TransMilenio (Hub ArcGIS).
- **Qué guarda:** `data/transmilenio/geo/estaciones_troncales.geojson` (153 estaciones)
  y `data/transmilenio/geo/trazados_troncales.geojson` (22 trazados).
- **Variables:** `GEODATA` (URLs de items ArcGIS; no requiere cambios salvo nuevas capas).
- **Ejecución:**
  ```bash
  ../../.venv/bin/python code/download_geo.py
  ```

---

## 3. TransMilenio — GTFS estático semanal (`download_gtfs.py`)

- **Fuente:** `https://storage.googleapis.com/gtfs-estaticos/GTFS_{YYYYMMDD}.zip`
- **Qué guarda:** `data/transmilenio/gtfs/GTFS_{YYYYMMDD}.zip` (una por semana;
  `stops`, `routes`, `trips`, `stop_times`, `calendar`, `calendar_dates`, `frequencies`).
- **Variables:**
  - `DESDE` / `HASTA` — rango de semanas.
  - `PASO_DIAS = 7` — **7 = semanal** (recomendado). `1` = diario.
  - `FALLBACK_MAX_DIAS = 7` — si un día falla (404), busca el más cercano en los siguientes
    días para no dejar la semana sin cobertura.
  - `BUSCAR_SUSTITUTO = PASO_DIAS > 1` — en modo semanal busca el reemplazo; en diario no.
- **Ejecución:**
  ```bash
  ../../.venv/bin/python code/download_gtfs.py
  ```
- **Nota:** el `stop_times.txt` de algunos snapshots viene incompleto
  (ej. `GTFS_20260807` 5.4M filas vs ~9.4M del resto); al procesar, revisar el conteo.

---

## 4. Clima — Meteostat Bogotá (`download_clima.py`)

- **Fuente:** Meteostat (estación `80222` Bogotá / El Dorado), vía libreria `meteostat`.
- **Qué guarda:** `data/clima/clima_hora_*.csv` (1,488 filas), `clima_dia_*.csv` (62),
  `clima_semana_*.csv` (10). Diario/semanal se derivan de la hora (el `daily()` de Meteostat
  llega con `prcp` vacío).
- **Variables:**
  - `DESDE` / `HASTA` — rango.
  - `ESTACION_ID = "80222"` — estación Meteostat.
  - `ZONA_HORARIA = "America/Bogota"`.
  - `GRANULARIDAD = "todas"` — `"hora" | "diario" | "semana" | "todas"`.
- **Ejecución:**
  ```bash
  ../../.venv/bin/python code/download_clima.py
  ```
- **Dependencia:** `meteostat` ≥ 2.1 (usa la API v2: `meteostat.daily()` / `meteostat.hourly()`).

---

## 5. OSM — Calles y POIs de Bogotá (`download_osm.py`)

- **Fuente:** extracto BBBike `https://download.bbbike.org/osm/bbbike/Bogota/Bogota.osm.pbf`
  (contiene todas las calles y todos los POI de la ciudad en un solo archivo).
- **Qué guarda:**
  - `data/OSM/bogota.osm.pbf` — PBF crudo.
  - `data/OSM/pois.csv` — 34,853 POIs (`luminaria`, `hospital`, `comisaria`, `comercio`, `negocio`).
  - `data/OSM/red_vial.geojson` — 123,390 tramos de vías (para `build_graph.py`).
- **Variables:**
  - `URL_OSM` / `NOMBRE_PBF` — origen del extracto.
  - `RECUPERAR_DATOS = False` — `True` para reprocesar POIs/red aunque ya existan.
  - `CATEGORIAS` — filtros `custom_filter` para pyrosm.
- **Ejecución:**
  ```bash
  ../../.venv/bin/python code/download_osm.py
  ```
- **Dependencias:** `pyrosm` 0.13.1 y módulo `osmium` (python; no se requiere CLI `osmium`).

---

## Procesamiento: `process_transmilenio.py`

No descarga, agrega todo lo anterior al dataset principal:

```bash
../../.venv/bin/python code/process_transmilenio.py \
  --input data/transmilenio/diario \
  --geo data/transmilenio/geo/estaciones_troncales.geojson \
  --trazados data/transmilenio/geo/trazados_troncales.geojson \
  --gtfs data/transmilenio/gtfs \
  --desde 2026-07-01 --hasta 2026-08-31 \
  --output data/transmilenio/dataset.csv
```

Produce `data/transmilenio/dataset.csv` (177,944 filas × 17 columnas) con las
validaciones diarias por (estación, fecha, hora, línea, tipo día) + coordenadas +
capacidades + oferta GTFS (Frecuencia, Headway, N_Rutas).