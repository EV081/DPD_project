# Guía de ejecución

Guía de ejecución manual para reproducir los datos. Los scripts son
independientes y se pueden correr en cualquier orden **menos** donde se indica la
dependencia.

Todos los comandos usan el entorno virtual del proyecto:

```bash
.venv/bin/python deliveries/week08/code/scripts/<script>.py
```

---

## 0. Orden recomendado

| # | Script | Qué hace | Depende de |
|---|--------|----------|------------|
| 1 | `extract_zip_data.py` | Descomprime los 2 ZIP de `zip/` (y los ZIP internos de shapefiles) | `zip/` |
| 2 | `download_transport_pages.py` | Scraper de `portal.atu.gob.pe`, `gob.pe` y `metrolima.info` a CSV | internet |
| 3 | `download_osm_lima.py` | Descarga OSM Lima (PBF) y extrae POIs, transporte y red vial | internet |
| 4 | `prepare_parquet.py` | Excel → Parquet **crudo** (`data_processed/raw/`) | paso 1 |
| 5 | EDA por sistema (4 notebooks) | Limpieza + EDA completo -> `clean/` | paso 4 |
| 6 | `eda_comparativo_sistemas.ipynb` | Consolida + compara los 4 sistemas | paso 5 |
| 7 | `code/model/modelamiento_atu.py` (+ `Modelamiento_ATU.ipynb`) | Pronóstico Chronos / aforo proxy / recomendación ATU | paso 6 |

Los pasos 2 y 3 son independientes del 1 y entre sí: se pueden hacer en paralelo o
saltarlos si los CSV ya existen.

---

## 1. `extract_zip_data.py`

Los ZIP **no** van en el repo (son pesados; `zip/` y `*.zip` están en `.gitignore`).
Hay que crear la carpeta y bajarlos a mano:

```bash
mkdir -p deliveries/week08/zip
```

Descargar desde Drive y dejarlos en `deliveries/week08/zip/`:

[ZIP de datos ATU (Drive)](https://drive.google.com/drive/folders/1qktczst2lUi7BqOt3Lr5ffcip9wqOSSw?usp=sharing)

Archivos esperados:

- `OneDrive_2026-09-22.zip`: datos del Metro L1 (12 xlsx mensuales) + 2 shapefiles
  que vienen **dentro de otro ZIP**.
- `4950-2026-02-0012640.zip`: sistema del Metropolitano (troncal, alimentadores,
  corredores, catálogos de paraderos).

```bash
.venv/bin/python deliveries/week08/code/scripts/extract_zip_data.py
```

**Salida:** `deliveries/week08/data/`

---

## 2. `download_transport_pages.py`

Descarga y parsea tres fuentes web:

| Fuente | Qué se extrae |
|--------|---------------|
| `portal.atu.gob.pe/QR/` | 44 páginas de estación, servicios, horarios, paraderos de corredores |
| `gob.pe` (notas ATU) | Frecuencias L1, capacidad de bus troncal, único aforo oficial |
| `metrolima.info` | Frecuencias de referencia de terceros (**no oficial**) |
| Prensa (RPP / Radio Nacional, 2025) | Frecuencias puntuales de corredores (`frecuencias_corredores_prensa.csv`) |

```bash
.venv/bin/python deliveries/week08/code/scripts/download_transport_pages.py
```

**Salida:** CSV en `deliveries/week08/data/fuentes/` (oficiales + referencia + prensa/apps):

**Advertencia importante:** el scraper **distingue fuentes oficiales de fuentes de
terceros**. `metrolima.info` no es un sitio de la ATU; sus frecuencias se marcan con
`no_oficial=True` y `confianza="baja"` en el CSV. No usarlas para dimensionar flota.
`frecuencias_corredores_prensa.csv` mezcla prensa (`confianza=media`, SE08≈5 min) y
tesis UPC (`confianza=baja`, 404≈15 min). `auditoria_apps_frecuencia.csv` documenta
que TuRuta/Moovit no exportan headways estáticos.


---

## 3. `download_osm_lima.py`

```bash
.venv/bin/python deliveries/week08/code/scripts/download_osm_lima.py
```

**Salida:** `deliveries/week08/data/OSM/`


---

## 4. `prepare_parquet.py` (solo conversión)

Convierte Excel (~294 MB) a Parquet **crudo**. **No** limpia ni hace EDA: eso va
en los notebooks del paso 5.

```bash
.venv/bin/python deliveries/week08/code/scripts/prepare_parquet.py --anio 2025
```

Tarda ~**6 minutos** (leer 17 libros de Excel es lento).

**Qué sí hace:** reshape wide→long, renombrar columnas, filtrar `--anio`, parsear
hora/tarifa de encabezados.

**Salida** en `deliveries/week08/data_processed/raw/`:

| Archivo | Contenido (crudo) |
|---------|-------------------|
| `troncal_hora.parquet` | `fecha`, `estacion`, `hora`, `validaciones` |
| `alimentador_hora.parquet` | + `linea`, `ruta`, `sentido`, `paradero`, **`tipo_tarifa`** |
| `corredores_hora.parquet` | + `tipo_dia_archivo`, `ruta`, `paradero`, `sentido` |
| `metro_l1_hora.parquet` | + `intervalo`, **`tipo_tarifa`** |
| `paraderos_*.parquet` | Catálogos con columnas renombradas |

---

## 5. EDA por sistema

Cada notebook lee su `raw/`, aplica **NA→0 + `era_celda_vacia`** (ceros conservados),
IQR (marcados, no borrados), EDA y mapa Folium, y escribe en `clean/`.

Estilo guía: `deliveries/week07/code/eda/eda_transmilenio.ipynb`.
Reporte unificado (como week07): `docs/DataAnalysis.md`.

Antes (una vez): `python code/scripts/build_trazados.py`  
(Trazados de **corredores** van por **OSRM** entre paraderos. **Metropolitano** usa
geometría OSM `route=bus`/`network=Metropolitano` vía Overpass — **no** OSRM car.
Metro L1 usa shapefiles MTC–AATE. Alimentadores: solo centroides; Moovit no se usa.)
Mapas oficiales ATU (corredores por ruta + Metropolitano por servicio):  
`python code/scripts/download_atu_mapas.py`

Mapas Folium **inline** en cada notebook (estilo week07 TransMilenio: zoom/pan en el
**output** de la celda; no se guardan HTML en `docs/`).
En `eda_corredores` / `eda_troncales_metropolitano`: variables `ruta_mapa` / `servicio_mapa`
(+ comentarios con alternativas), imagen ATU opcional + Folium (burbujas = validaciones;
línea = trazado).

| Notebook | Sistema |
|----------|---------|
| `eda_troncales_metropolitano.ipynb` | Troncal (pista exclusiva) |
| `eda_alimentadores.ipynb` | Alimentadores |
| `eda_corredores.ipynb` | Corredores complementarios |
| `eda_metro_l1.ipynb` | Metro Línea 1 |

**Salida:** `data_processed/clean/` + `calidad_cobertura_*.csv` + figuras en
`docs/images/` + mapas Folium solo en el output del notebook.

### Cómo leer cobertura

Solo unidades con cobertura alta (≥90%) son fiables para promedios anuales.
Metro L1 y troncal están casi completos; alimentadores y varios corredores no.

---

## 6. `eda_comparativo_sistemas.ipynb`

Corre **después** de los 4 EDA. Une coberturas, arma `demanda_consolidada.parquet`
(todas las unidades) y `demanda_consolidada_fiable.parquet` (cobertura ≥ 90%; **usar este**).
Marca `grano` (`estacion` vs `ruta`) para no mezclar métricas por unidad, y compara
escala / perfiles / calendario entre sistemas.

---

## 7. Modelamiento ATU (`code/model/`) — **un modelo por sistema**

No mezclar modos en un solo fit. Notebooks:

| Sistema | Notebook |
|---------|----------|
| Metro L1 | `Modelamiento_metro_l1.ipynb` |
| Troncal | `Modelamiento_troncal.ipynb` |
| Corredores | `Modelamiento_corredores.ipynb` |
| Alimentadores | `Modelamiento_alimentadores.ipynb` |

Índice / comparativa WMAPE: `Modelamiento_ATU.ipynb`.  
Helpers: `model_atu_common.py`.  
Outputs: `code/model/outputs/<sistema>/` · figuras `docs/images/model/<sistema>/`.

```bash
# abrir y Run All cada notebook, o desde code/model/
# (cada uno carga Chronos y hace walk-forward propio)
```

