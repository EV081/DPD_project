# Probar los scripts desde cero

Guía para comprobar que los scripts de `01_descarga` → `04_geo_build` reproducen los datos **sin tocar** los
que ya tienes. Para qué sirve cada uno y en qué orden se usan, ver [Guia.md](Guia.md).

## 0. No borres `data/` ni `data_processed/`

Parte de lo que hay ahí no se recupera barato:

| Archivo | Por qué no borrarlo |
|---|---|
| `data/fuentes/google_paraderos.csv`, `google_cercanos.csv` | ~1 350 consultas de Google Places (con costo y cupo) |
| `data/fuentes/correcciones_troncal.csv`, `correcciones_paradas.csv` | decisiones tomadas a mano |
| `data/fuentes/alimentadores_paraderos_ocr.csv` | OCR de imágenes, revisado |
| `data_processed/geo/tramos_osrm.csv` | ~35 min contra el OSRM público |
| `data_processed/clean/` | salida de los EDA (notebooks), no de los scripts |

En su lugar, prueba en una **copia** (sandbox). Parte de cero porque no incluye `data/` ni `data_processed/`.

```bash
# desde la raíz del repo
SB=/tmp/week10_prueba
mkdir -p $SB
cp -r deliveries/week10/code $SB/code
ln -s "$PWD/deliveries/week10/zip" $SB/zip          # los ZIP son pesados: se enlazan, no se copian
cd $SB/code
```

Los scripts calculan sus rutas a partir de su propia ubicación, así que dentro del sandbox escriben en
`/tmp/week10_prueba/data` y `/tmp/week10_prueba/data_processed`, no en tu repo.
Para limpiar al terminar: `rm -rf /tmp/week10_prueba` (el enlace a `zip` no borra los ZIP).

Todos los comandos siguientes se ejecutan desde `$SB/code`.

## 1. Pasos sin internet ni claves (rápidos)

| # | Comando | Tarda | Debe producir |
|---|---|---|---|
| 1 | `python scripts/01_descarga/extract_zip_data.py` | ~3 s | `$SB/data/` (Excel de validaciones + shapefiles L1) |
| 2 | `python scripts/02_procesado/prepare_parquet.py --anio 2025` | ~6 min | `$SB/data_processed/raw/*.parquet` (troncal, alimentador, corredores, metro_l1, `paraderos_*`) |

Comprobación:

```bash
ls $SB/data/AIP*/Validaciones_01.2024-01.2026/2025 | wc -l       # 12 libros mensuales
python - <<'PY'
import pandas as pd, pathlib
for f in sorted(pathlib.Path("/tmp/week10_prueba/data_processed/raw").glob("*.parquet")):
    print(f.name, len(pd.read_parquet(f)))
PY
```

## 2. Pasos con internet (sin clave)

Escriben en `$SB/data/fuentes/` y `$SB/data/OSM/`. Son los más lentos; la caché HTML evita repetir descargas.

| # | Comando | Notas |
|---|---|---|
| 3 | `python scripts/01_descarga/download_transport_pages.py` | scraper de ATU, gob.pe y metrolima; `--force` ignora la caché |
| 4 | `python scripts/01_descarga/download_osm_lima.py` | PBF de OSM Lima (~150 MB) y tablas; requiere `pyrosm` |
| 5 | `python scripts/01_descarga/download_alimentadores.py` | paraderos, horarios e imágenes de alimentadores |
| 6 | `python scripts/01_descarga/download_atu_mapas.py` | mapas oficiales ATU (corredores y Metropolitano) |

## 3. Georreferenciación y construcción de GeoJSON

Necesitan lo anterior. Los pasos 8 y 9 dependen de `tesseract` (instalado en tu equipo) y de la API de Google.

| # | Comando | Requiere | Debe producir |
|---|---|---|---|
| 7 | `python scripts/04_geo_build/build_trazados.py` | pasos 2–6 (usa OSRM/Overpass) | `$SB/data_processed/geo/*.geojson` |
| 8 | `python scripts/03_georef/ocr_listas_alimentadores.py --guardar` | paso 5, `tesseract` | CSV de paradas leídas de imagen |
| 9 | `python scripts/03_georef/consultar_google_paraderos.py --dry-run` | `GOOGLE_MAPS_API_KEY` en `.env` | cuenta cuántas consultas haría, sin gastar |
| 9b | `python scripts/03_georef/consultar_google_paraderos.py --contrastar-oficiales` | paso 7, `GOOGLE_MAPS_API_KEY` | `contraste_google_oficiales.csv` (~70 consultas) |
| 10 | `python scripts/03_georef/corregir_troncal_con_google.py` | paso 7, `contraste_google_oficiales.csv` (paso 9b) y `correcciones_troncal.csv` (manual, en `data/fuentes/`) | estaciones de troncal corregidas |
| 11 | `python scripts/03_georef/geocodificar_alimentadores.py` | pasos 5, 7, 8 | `paradas_alimentadores.geojson`, `trazados_alimentadores_atu.geojson` |
| 12 | `python scripts/03_georef/generar_revision.py` | pasos 7 y 11 | `deliveries/week10/docs/visor/mapa_revision.html` |

**Cuidado con el paso 9:** sin `--dry-run` ejecuta consultas reales (hasta `--max-llamadas`, 800 por defecto).
En el sandbox pruébalo siempre con `--dry-run`, o copia antes tu `google_paraderos.csv` al sandbox para que
use la caché y no gaste cupo:

```bash
mkdir -p $SB/data/fuentes && cp deliveries/week10/data/fuentes/google_*.csv $SB/data/fuentes/
```

El paso 12 escribe en `RAIZ/docs/visor`; en el sandbox eso es `$SB/docs/visor`, no tu repo.

## 4. Tramos (necesita PostgreSQL)

`build_tramos.py` lee `paradero_ruta` de la base, así que primero hay que cargarla con el pipeline. Eso se hace
desde el repo real (Docker), no desde el sandbox:

```bash
docker compose up -d db
cd deliveries/week10/code
PGHOST=localhost python -m pipeline.run init-db
PGHOST=localhost python -m pipeline.run paraderos
PGHOST=localhost python scripts/04_geo_build/build_tramos.py     # ~35 min con el OSRM público; reanuda
```

Si se corta (Ctrl+C o error) guarda lo calculado y la siguiente corrida sigue desde ahí (guarda cada 100 tramos).

`.env` define `PGHOST=db` (válido solo dentro de Docker); por eso se sobrescribe con `PGHOST=localhost` al
correr desde tu máquina.

## Resultado de la prueba del 15-oct-2026

Corrida completa en un sandbox sin `data/` ni `data_processed/`: los pasos 1–12 y `build_tramos` funcionan. Los
parquets de `raw/` coinciden fila a fila con los del repo. Los GeoJSON que dependen de OSRM/Overpass/portales
(`trazados_corredores`, `trazado_troncal`, `trazados_metropolitano_servicios`) difieren algo entre ejecuciones, y
`paradas_alimentadores` queda 2 paradas por debajo si faltan las correcciones manuales de `correcciones_paradas.csv`.

## 5. Qué considerar una prueba exitosa

- Los pasos 1 y 2 generan los mismos parquets que `data_processed/raw` del repo (mismo número de filas por archivo).
- Los pasos 7 y 11 generan en conjunto los 13 GeoJSON (11 el paso 7, 2 el paso 11); compara contra los versionados:
  ```bash
  for f in $SB/data_processed/geo/*.geojson; do
    cmp -s "$f" deliveries/week10/data_processed/geo/$(basename "$f") && echo "= $(basename $f)" || echo "≠ $(basename $f)"
  done
  ```
  Las fuentes online (OSRM, Overpass, portales ATU) pueden cambiar entre ejecuciones; una diferencia pequeña
  en coordenadas no implica un error del script.
- Ningún script falla por rutas (`FileNotFoundError` al buscar `data/fuentes`, `data_processed/geo` o
  `plantilla_revision.html`). Eso es lo que cambió con la reorganización en subcarpetas.
- Suite de regresión (necesita `docker compose up -d db`):
  ```bash
  cd deliveries/week10/code && PGHOST=localhost python -m pytest tests -q
  ```
