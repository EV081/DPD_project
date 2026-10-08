# Guía · `export/`

Genera el paquete de salida representativo de la semana: muestra CSV, reportes,
JSON de tráfico y copia de los outputs de modelado, con un manifiesto que sella
todo (sha256 + conteos de la base).

## Contenido

| Archivo | Rol |
| :--- | :--- |
| `export_data.py` | Módulo `run()` que consulta la vista y escribe `EXPORT_DIR` |
| `Guia.md` | Este documento |

## Cómo ejecutar

```bash
# local
cd deliveries/week10/code && python -m export.export_data

# docker
docker compose run --rm pipeline export
# (o incluido en) docker compose run --rm pipeline full
```

Requiere la base cargada (si no, la vista está vacía): corre antes
`pipeline.run init-db` y `pipeline.run demand`.

## Qué produce (en `EXPORT_DIR`, default `deliveries/week10/export/`)

| Archivo | Contenido |
| :--- | :--- |
| `muestra_demanda_fiable.csv` | Muestra determinista de `MUESTRA_LIMITE` (100.000) filas de `demanda_fiable`, ordenada por fecha/hora/sistema/unidad/sentido |
| `resumen_por_sistema.csv` | `sistema, grano, filas, unidades, validaciones, fecha_min, fecha_max` |
| `perfil_horario.csv` | `sistema, hora, promedio, total` — 90 filas (metro L1 opera 5–22 h; el resto 24 h) |
| `trafico_tomtom.json` | Snapshot de `trafico_en_vivo` (`generado_en` + `segmentos[]` con velocidad, ratio y `fuente`) |
| `modelo/` | Copia de los outputs de week08: `manifiesto_modelamiento.json`, `metricas_modelos.csv`, `bakeoff_wmape_todos.csv`, `eval_walkforward_modelos.csv` |
| `manifiesto_export.json` | Inventario: `generado_en`, `fuente`, `limite_muestra`, `conteos_bd` y `archivos` (bytes + sha256) |

## Configuración

| Constante / variable | Default | Uso |
| :--- | :--- | :--- |
| `MUESTRA_LIMITE` (`export_data.py`) | `100_000` | Filas de la muestra |
| `ARCHIVOS_MODELO` (`export_data.py`) | lista de 4 | Archivos copiados de `MODELO_OUTPUTS_DIR` |
| `EXPORT_DIR` | `week10/export` | Destino (en contenedor `/app/out`) |
| `MODELO_OUTPUTS_DIR` | `code/model/outputs` | Origen de los outputs de modelo (en contenedor `/app/model_outputs`) |

Si `MODELO_OUTPUTS_DIR` no existe, el export avisa y sigue (no falla); el resto
de archivos se generan igual.

## Cómo verificar la integridad

```bash
# recomputar un sha y compararlo con el manifiesto
python - <<'PY'
import hashlib, json, pathlib
out = pathlib.Path("deliveries/week10/export")
man = json.loads((out / "manifiesto_export.json").read_text())
for nombre, meta in man["archivos"].items():
    sha = hashlib.sha256((out / nombre).read_bytes()).hexdigest()
    print(nombre, sha == meta["sha256"])
PY
```

El manifiesto se excluye a sí mismo del inventario y registra `conteos_bd` de
las 7 tablas + `trafico_en_vivo` + `demanda_fiable`, de modo que un export se
puede contrastar contra la base con la que se generó.

## Uso programático

```python
from export import export_data

export_data.run()                 # escribe en config.EXPORT_DIR y devuelve el Path
```
