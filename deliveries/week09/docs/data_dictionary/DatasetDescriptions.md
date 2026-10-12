# Descripción de datasets — Semana 08

Resumen de todo lo que produce el pipeline de la semana 08, con grano, cobertura y
advertencias. Para el detalle campo por campo, ver los archivos hermanos:

- `Data_Dictionary_Troncales.md`
- `Data_Dictionary_Alimentadores.md`
- `Data_Dictionary_Corredores.md`
- `Data_Dictionary_MetroL1.md`
- `Data_Dictionary_Fuentes_Web.md`

---

## Panorama de la semana

| Sistema | Unidad | Grano | Filas | Cobertura 2025 | Role |
|---------|--------|-------|-------|----------------|------|
| Metro L1 | estación | fecha×estación×hora | 169,921 | **100%** (26/26) | Referencia |
| Troncales | estación | fecha×estación×hora | 342,703 | **99%** (45/46) | Alta calidad |
| Corredores | ruta (n°) | fecha×ruta×paradero×sentido×hora | 4,532,528 | **63%** (12/26 sobre 90%) | Cobertura irregular |
| Alimentadores | ruta (nombre) | fecha×ruta×sentido×paradero×hora | 1,640,842 | **85%** (0/27 completos) | La más irregular |

Total consolidado (todas las unidades, grano fino de buses = paradero): ver
`demanda_consolidada.parquet`. Para análisis usar **`demanda_consolidada_fiable.parquet`**
(cobertura ≥ 90%).

---

## Archivos de `data_processed/clean/`

### `demanda_consolidada.parquet` / `demanda_consolidada_fiable.parquet`
Esquema común de los **cuatro** sistemas. El notebook comparativo **analiza el fiable**.

| Columna | Descripción |
|---------|-------------|
| `sistema` | `troncal`, `alimentador`, `corredor`, `metro_l1` |
| `grano` | `estacion` (troncal/L1) o `ruta` (corredor/alimentador) — no mezclar métricas “por unidad” entre granos |
| `unidad` | Estación o ruta (según `grano`) |
| `ruta` | Ruta, o nulo si no aplica (troncal, L1) |
| `sentido` | Sentido normalizado, o nulo si no aplica |
| `fecha`, `anio`, `mes`, `dia_semana`, `tipo_dia`, `semana_iso`, `feriado`, `es_feriado` | Calendario |
| `hora` | Hora de la validación |
| `validaciones` | Recuento (float64) |

**Nota:** en corredor/alimentador el Excel es por **paradero**; `unidad=ruta` y al
agregar por `(sistema, unidad, fecha, …)` se suman los paraderos de esa ruta.

**Consistencia:** la L1 en el consolidado suma igual que `metro_l1_total_hora.parquet`
(201,512,887).

### Archivos por sistema
`troncal_hora`, `alimentador_hora`, `corredores_hora`, `metro_l1_hora`,
`metro_l1_total_hora`, `alimentador_tarifa` — ver los diccionarios específicos.

### `calidad_cobertura.csv` — 125 unidades
Una fila por (sistema, unidad) con días con datos, cobertura, primera y última fecha,
filas y validaciones. **Es la tabla de control**: define qué unidades son usables.

```python
FIABLES = calidad[calidad.pct_cobertura >= 90]
```

### Catálogos
- `paraderos_cosac.parquet` — 792 filas (paraderos de alimentadores)
- `paraderos_cc.parquet` — 1,531 filas (paraderos de corredores, **con lat/lon**)

---

## Hallazgos que condicionan el modelado

Estos no son conclusiones del EDA para publicar, sino restricciones que la data impone:

1. **La identidad de la unidad lo es todo.** Un árbol de decisión con solo
   calendario (hora, día, mes, sistema) alcanza R²≈0.30. Al añadir la unidad, sube a
   **R²≈0.82**. Sin `unidad` no hay modelo.

2. **Sábado ≠ domingo.** En la L1 el sábado mueve 1.01× el lunes y el domingo 0.55×.
   En los tres sistemas de buses el sábado ya cae a 0.75–0.78. La fuente de la L1
   además codifica `SAB` aparte de `LAB`. Cualquier codificación de "fin de semana"
   que agrupe sábado y domingo se equivoca.

3. **`TIPO DE DÍA` no sirve para detectar feriados.** Coincide el 100% con el día de la
   semana. Los feriados hay que derivarlos del calendario.

4. **La L1 no reporta domingos universitarios.** Mezcla real (excluyendo domingos):
   Adulto 94.6%, Universitario 5.4%. Los domingos tienen **1 sola** fila de tarifa
   universitaria en todo el año. Si comparas días promediando filas, el domingo parece
   más mover de lo que mueve, y el volumen real del domingo queda subestimado ~5%.

5. **La cobertura manda.** Alimentadores y corredores tienen rutas con 1–5 días de
   datos. Promediar sin filtrar produce cifras inventadas. La troncales y la L1 se
   pueden usar casi sin filtro.

---

## Lo que este dataset NO permite

- **Aforo u ocupación de buses.** No hay `bus_id` ni headway, y las validaciones se
  truncan por saturación en punta. No se generó `estimate_occupancy.py` por esto.
- **Frecuencia completa de corredores.** Portal/apps no entregan headways de las
  12 rutas. Fuentes puntuales 2023–2025: SE08 ≈ 5 min (prensa) y 404 ≈ 15 min
  (tesis UPC, confianza baja). Ver `frecuencias_corredores_prensa.csv`,
  `auditoria_apps_frecuencia.csv` y `docs/analisis.md`.
- **Capacidad de alimentadores.** No se halló fuente oficial verificable; se dejó fuera
  en vez de estimarla.
- **Serie histórica de aforo.** El único aforo oficial de la ATU es un dato puntual
  de diciembre de 2020.

---

## Cómo reproducir

```bash
.venv/bin/python deliveries/week08/code/scripts/extract_zip_data.py
.venv/bin/python deliveries/week08/code/scripts/download_transport_pages.py
.venv/bin/python deliveries/week08/code/scripts/download_osm_lima.py
.venv/bin/python deliveries/week08/code/scripts/prepare_parquet.py --anio 2025
# luego: notebooks EDA por sistema → data_processed/clean/
.venv/bin/python deliveries/week08/code/eda/_build_notebooks.py
.venv/bin/python deliveries/week08/code/eda/_run_notebooks.py
```

Detalle paso a paso en `code/scripts/Guia.md`.
