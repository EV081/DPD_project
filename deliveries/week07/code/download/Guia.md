# Guía de descarga de datasets

Todos los scripts se ejecutan con el venv del proyecto (antes instalar `requirements.txt`) y **desde la raíz del repositorio**. Los scripts calculan sus rutas de salida de forma absoluta según su propia ubicación, así que no importa desde qué carpeta los corras:

```bash
python3 deliveries/week07/code/download/<script>.py
```

Si tu `python3` no tiene las dependencias (`pandas`, `meteostat`, `pyrosm`, …), usa el venv:

```bash
.venv/bin/python deliveries/week07/code/download/<script>.py
```

Cada script es idempotente (si el archivo ya existe, lo salta).

Toda la data descargada queda en `deliveries/week07/data/`:

```
deliveries/week07/data/
├── transmilenio/
│   ├── diario/    validacionTroncal{YYYYMMDD}.zip
│   ├── geo/       estaciones_troncales.geojson + trazados_troncales.geojson
│   └── gtfs/      GTFS_{YYYYMMDD}.zip
├── clima/         clima_hora_*.csv, clima_dia_*.csv, clima_semana_*.csv
└── OSM/           bogota.osm.pbf, pois.csv, red_vial.geojson
```

---

## 1. TransMilenio — Validaciones diarias (`download_transmilenio.py`)

- **Fuente:** `https://storage.googleapis.com/validaciones_tmsa/ValidacionTroncal/validacionTroncal{YYYYMMDD}.zip`
- **Qué guarda:** `deliveries/week07/data/transmilenio/diario/validacionTroncal{YYYYMMDD}.zip`
- **Variables (editar en el script):**
  - `DESDE = date(2026, 7, 1)` — primer día.
  - `HASTA = date(2026, 8, 31)` — último día.
- **Ejecución:**
  ```bash
  .venv/bin/python deliveries/week07/code/download/download_transmilenio.py
  ```

---

## 2. TransMilenio — GeoJSON de estaciones y trazados (`download_geo.py`)

- **Fuente:** Portal de Datos Abiertos TransMilenio (Hub ArcGIS).
- **Qué guarda:** `deliveries/week07/data/transmilenio/geo/estaciones_troncales.geojson` (153 estaciones)
  y `deliveries/week07/data/transmilenio/geo/trazados_troncales.geojson` (22 trazados).
- **Variables:** `GEODATA` (URLs de items ArcGIS; no requiere cambios salvo nuevas capas).
- **Ejecución:**
  ```bash
  .venv/bin/python deliveries/week07/code/download/download_geo.py
  ```

---

## 3. TransMilenio — GTFS estático semanal (`download_gtfs.py`)

- **Fuente:** `https://storage.googleapis.com/gtfs-estaticos/GTFS_{YYYYMMDD}.zip`
- **Qué guarda:** `deliveries/week07/data/transmilenio/gtfs/GTFS_{YYYYMMDD}.zip` (una por semana;
  `stops`, `routes`, `trips`, `stop_times`, `calendar`, `calendar_dates`, `frequencies`).
- **Variables:**
  - `DESDE` / `HASTA` — rango de semanas.
  - `PASO_DIAS = 7` — **7 = semanal** (recomendado). `1` = diario.
  - `FALLBACK_MAX_DIAS = 7` — si un día falla (404), busca el más cercano en los siguientes
    días para no dejar la semana sin cobertura.
  - `BUSCAR_SUSTITUTO = PASO_DIAS > 1` — en modo semanal busca el reemplazo; en diario no.
- **Ejecución:**
  ```bash
  .venv/bin/python deliveries/week07/code/download/download_gtfs.py
  ```
- **Nota:** el `stop_times.txt` de algunos snapshots viene incompleto
  (ej. `GTFS_20260807` 5.4M filas vs ~9.4M del resto); al procesar, revisar el conteo.

---

## 4. Clima — Meteostat Bogotá (`download_clima.py`)

- **Fuente:** Meteostat (estación `80222` Bogotá / El Dorado), vía libreria `meteostat`.
- **Qué guarda:** `deliveries/week07/data/clima/clima_hora_*.csv` (1,488 filas), `clima_dia_*.csv` (62),
  `clima_semana_*.csv` (10). Diario/semanal se derivan de la hora (el `daily()` de Meteostat
  llega con `prcp` vacío).
- **Variables:**
  - `DESDE` / `HASTA` — rango.
  - `ESTACION_ID = "80222"` — estación Meteostat.
  - `ZONA_HORARIA = "America/Bogota"`.
  - `GRANULARIDAD = "todas"` — `"hora" | "diario" | "semana" | "todas"`.
- **Ejecución:**
  ```bash
  .venv/bin/python deliveries/week07/code/download/download_clima.py
  ```
- **Dependencia:** `meteostat` ≥ 2.1 (usa la API v2: `meteostat.daily()` / `meteostat.hourly()`).

---

## 5. OSM — Calles y POIs de Bogotá (`download_osm.py`)

- **Fuente:** extracto BBBike `https://download.bbbike.org/osm/bbbike/Bogota/Bogota.osm.pbf`
  (contiene todas las calles y todos los POI de la ciudad en un solo archivo).
- **Qué guarda:**
  - `deliveries/week07/data/OSM/bogota.osm.pbf` — PBF crudo.
  - `deliveries/week07/data/OSM/pois.csv` — 34,853 POIs (`luminaria`, `hospital`, `comisaria`, `comercio`, `negocio`).
  - `deliveries/week07/data/OSM/red_vial.geojson` — 123,390 tramos de vías (para `build_graph.py`).
- **Variables:**
  - `URL_OSM` / `NOMBRE_PBF` — origen del extracto.
  - `RECUPERAR_DATOS = False` — `True` para reprocesar POIs/red aunque ya existan.
  - `CATEGORIAS` — filtros `custom_filter` para pyrosm.
- **Ejecución:**
  ```bash
  .venv/bin/python deliveries/week07/code/download/download_osm.py
  ```
- **Dependencias:** `pyrosm` 0.13.1 y módulo `osmium` (python; no se requiere CLI `osmium`).

---

## Procesamiento: `process_transmilenio.py`

No descarga; agrega todo lo anterior al dataset principal **con las 17 columnas**:
validaciones diarias por (estación, fecha, hora, línea, tipo día) + coordenadas
+ capacidades + oferta GTFS (Frecuencia, Headway, N_Rutas).

```bash
.venv/bin/python deliveries/week07/code/download/process_transmilenio.py
```

Por defecto el script ya apunta a los datos descargados:
`deliveries/week07/data/transmilenio/{diario,geo,gtfs}` y escribe `dataset.csv` ahí mismo.
`--desde`/`--hasta` son opcionales: si no se pasan, se deducen del rango de fechas de los
ZIPs en `diario/`. Solo tienes que pasar flags si quieres cambiar algo:

```bash
.venv/bin/python deliveries/week07/code/download/process_transmilenio.py \
  --input   deliveries/week07/data/transmilenio/diario \
  --geo     deliveries/week07/data/transmilenio/geo/estaciones_troncales.geojson \
  --trazados deliveries/week07/data/transmilenio/geo/trazados_troncales.geojson \
  --gtfs    deliveries/week07/data/transmilenio/gtfs \
  --desde   2026-07-01 --hasta 2026-08-31 \
  --output  deliveries/week07/data/transmilenio/dataset.csv
```

Produce `deliveries/week07/data/transmilenio/dataset.csv`
(177,944 filas × 17 columnas) con:

| Columna | Descripción |
| :--- | :--- |
| `Estacion` | Nombre de la estación / paradero |
| `Latitud`, `Longitud` | Coordenadas (GeoJSON estaciones, completadas con GTFS) |
| `Ubicacion`, `Troncal`, `Fase` | Ubicación, troncal y fase de la estación |
| `Cap_ART`, `Cap_BIART` | Capacidad operativa (ART y/o BI-ART) |
| `num_est` | Código numérico de la estación (5 dígitos) |
| `Frecuencia`, `Headway_Min`, `N_Rutas` | Oferta GTFS por hora (buses/hora, headway, nº de rutas) |
| `Fecha`, `Hora` | Día y franja horaria de la validación |
| `Linea`, `Tipo_Dia` | Línea de servicio y tipo de día (Dia 1/2/3… o Día 1) |
| `Validaciones` | Nº de validaciones (pasajeros) en esa celda |