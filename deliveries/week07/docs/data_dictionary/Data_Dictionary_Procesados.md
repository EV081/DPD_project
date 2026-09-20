# Diccionario de Datos — Datasets Procesados (UrbanSafe AI)

**Entrega:** Semana 07 · **Rutas:** `deliveries/week07/data_processed/` y `deliveries/week07/code/model/outputs/`

Diccionario por columna de los **datasets procesados** y **artefactos de modelado**. Para una
descripción narrativa (qué es, cómo se genera, para qué se usa) ver
[`DatasetDescriptions.md`](DatasetDescriptions.md). Fuentes crudas en
`Data_Dictionary_Transmilenio.md`, `Data_Dictionary_Clima.md` y `Data_Dictionary_OSM.md`.

Los conteos de nulos y cardinalidad corresponden a **la última corrida** (2026-09-19).

---

## 1. `dataset_limpio.csv` — dataset de modelado (176,783 × 28)

Base del EDA y del pipeline de modelado. Producción: `code/eda/eda_transmilenio.ipynb`.
Una fila = validaciones de una **línea** en una **estación**, en una **hora** de un **día**.

| Campo | Tipo | Nulos | Descripción |
|-------|------|-------|-------------|
| `num_est` | int | 0 | Código Tullave de 5 dígitos de la estación (153 únicos). Clave de unión con GTFS y con OSM. |
| `Fecha` | date (str) | 0 | Día de la transacción, `YYYY-MM-DD` (62 únicos). |
| `Hora` | int | 0 | Hora 0–23 (22 únicos: madrugadas sin servicio). |
| `Linea` | str | 0 | Línea (agrupación operativa de rutas), ej. `(33) Zona B AutoNorte` (13 únicos). |
| `Tipo_Dia` | str | 0 | Clasificación oficial cruda: `Dia 1` (hábil lun–sáb) / `Dia 2` (domingo). No corrige festivos (ver `Tipo_Dia_ok`). |
| `Estacion` | str | 0 | Nombre de la estación con código, ej. `(02000) Portal Norte - Unicervantes` (156 únicos). |
| `Latitud` | float | 0 | Latitud WGS84 (EPSG:4326). |
| `Longitud` | float | 0 | Longitud WGS84 (EPSG:4326). |
| `Ubicacion` | str | 13,256 | Referencia a vías principales de la estación, ej. `CL 173`. |
| `Troncal` | str | 13,256 | Nombre de la troncal (12 únicos). |
| `Fase` | str | 13,256 | Fase constructiva: `FASE I/II/III` (3 únicos). |
| `Cap_ART` | float | 13,256 | Capacidad de la estación (pasajeros) para buses **articulados**. |
| `Cap_BIART` | float | 13,256 | Capacidad de la estación para buses **biarticulados**. |
| `Frecuencia` | float | 0 | Llegadas de buses por hora según GTFS (463 únicos). `0` = sin servicio programado (flag `Sin_Oferta`). |
| `Headway_Min` | float | 14,279 | Intervalo promedio entre buses = `60/Frecuencia` (min). `NaN` si no hay oferta. |
| `N_Rutas` | float | 8,727 | N° de rutas distintas que atienden la estación esa hora (38 únicos). |
| `Validaciones` | int | 0 | N° de tarjetas validadas en la celda (pasajeros que **entran**). Target de demanda. |
| `Es_Festivo` | bool | 0 | `True` si el día es festivo según el calendario colombiano de la ventana (4 festivos). |
| `Tipo_Dia_ok` | str | 0 | Clasificación **corregida**: `Dia 2` = domingo **o** festivo. Usar siempre esta en features. |
| `Sin_Oferta` | bool | 0 | `True` si la estación no tiene parada en GTFS (corrales/patios/cables). |
| `Cap_total` | float | 0 | `Cap_ART + Cap_BIART` cuando existen; `NaN` si no hay capacidad reportada (43 únicos). |
| `sin_capacidad` | bool | 0 | `True` si la estación no reportó capacidad oficial (no se imputa). |
| `DiaSemana` | str | 0 | Lunes … Domingo (7 únicos). |
| `Franja` | str | 0 | Ventana de demanda: `madrugada`, `pico am`, `valle`, `pico pm`, `noche` (5 únicos). |
| `Es_Habil` | bool | 0 | `Tipo_Dia_ok == "Dia 1"`. |
| `Pax_bus` | float | 14,279 | `Validaciones / Frecuencia` — pasajeros por bus que llega (saturación de oferta). |
| `Ocupacion_pk` | float | 14,670 | `Validaciones / Cap_total` — proxy de ocupación de infraestructura; base de la etiqueta de aforo. |
| `log_val` | float | 0 | `log1p(Validaciones)` — estabiliza la cola larga para gráficos y modelos. |

---

## 2. `congestion_sintetica.csv` — congestión sintética (232,128 × 7)

Capas de congestión para ajustar el ETA (Módulo 1). Producción:
`code/scripts/congestion.py` (determinista, seed 42). El `ratio` modela
`freeFlowSpeed / currentSpeed` ∈ [1.0, 3.0]; simula picos 06–09 h y 17–20 h, «pico y placa» y lluvia
de fin de mes. En S08 se reemplaza por TomTom Traffic (key `TOMMTOM_KEY`).

| Campo | Tipo | Nulos | Descripción |
|-------|------|-------|-------------|
| `Fecha_Hora` | datetime | 0 | Timestamp horario `-05:00` (1,488 únicos = 62 d × 24 h). |
| `Estacion` | str | 0 | Estación TransMilenio (156 únicos). |
| `Latitud` / `Longitud` | float | 0 | Coordenadas de la estación (EPSG:4326). |
| `freeFlowSpeed_kph` | float | 0 | Velocidad en flujo libre, **constante 50.0** (corredor troncal). |
| `currentSpeed_kph` | float | 0 | Velocidad simulada = `50 / ratio` (84 únicos). |
| `ratio_congestion` | float | 0 | `freeFlow / current` (85 únicos). 1.0 = flujo libre; ~2.0–2.5 = tráfico pesado. |

---

## 3. `dataset_osm_estaciones_limpio.csv` — entorno urbano por estación (156 × 12)

Producción: `code/eda/eda_OSM.ipynb`. Una fila por estación TransMilenio (cuenta POIs en buffer
peatonal de **500 m**, `EPSG:3116`). Clave de unión: `num_est`.

| Campo | Tipo | Nulos | Descripción |
|-------|------|-------|-------------|
| `num_est` | int | 0 | Código Tullave (153 únicos). |
| `Estacion` | str | 0 | Nombre con código (156 únicos). |
| `Latitud` / `Longitud` | float | 0 | Coordenadas (EPSG:4326). |
| `Troncal` | str | 0 | Troncal de la estación (13 únicos). |
| `poi_500m_comercio` | int | 0 | Locales comerciales (`shop=*`) en 500 m. |
| `poi_500m_comisaria` | int | 0 | Estaciones de policía (`amenity=police`). |
| `poi_500m_hospital` | int | 0 | Hospitales/clínicas (`amenity=hospital\|clinic`). |
| `poi_500m_luminaria` | int | 0 | Luminarias (`highway=street_lamp`). |
| `poi_500m_negocio` | int | 0 | Negocios/amenities de servicio (banco, restaurante, farmacia…). |
| `total_pois_500m` | int | 0 | Suma de los 5 conteos (indicador de actividad urbana). |
| `ratio_seguridad_comercio` | float | 0 | `(poi_500m_comisaria + 1) / (poi_500m_comercio + 1)` (suavizado de Laplace). |

---

## 4. `pois_limpio.csv` — POIs depurados (35,123 × 7)

Producción: `code/eda/eda_OSM.ipynb` (elimina 6 duplicados espaciales del crudo de 35,129).

| Campo | Tipo | Nulos | Descripción |
|-------|------|-------|-------------|
| `osm_type` | str | 0 | `node` / `way` / `relation` (3 únicos). |
| `id` | int | 0 | ID OSM (35,020 únicos). |
| `categoria` | str | 0 | `luminaria`, `hospital`, `comisaria`, `comercio`, `negocio` (5 únicos). |
| `lat` / `lon` | float | 0 | Coordenadas (EPSG:4326). |
| `name` | str | 0 | Nombre en OSM; `"Sin registro"` si no tiene (23,970 únicos). |
| `sin_nombre` | bool | 0 | Flag de nombre ausente en OSM. |

---

## 5. `red_vial_limpia.geojson` — red vial limpia (123,508 × 16)

Producción: `code/eda/eda_OSM.ipynb`. Una fila = tramo vial (arista del grafo peatonal).

| Campo | Tipo | Nulos | Descripción |
|-------|------|-------|-------------|
| `id` | int | 0 | ID OSM del tramo. |
| `osm_type` | str | 0 | `way` / `relation`. |
| `highway` | str | 0 | Clasificación OSM (`residential`, `footway`, `service`, …). |
| `oneway` | str | 0 | Valor crudo OSM (`yes`/`no`/`-1`/vacío). |
| `lanes` | str | 74.9 % | Carriles crudos (cadena, ej. `"2;3"`). |
| `maxspeed` | str | 90.4 % | Límite crudo (cadena con unidades textuales). |
| `length_meters` | float | 0 | Longitud del tramo **recalculada en EPSG:3116** (metros reales). |
| `es_unidireccional` | bool | 0 | `True` si `oneway ∈ {yes, 1, -1}`. |
| `lanes_num` | float | 74.9 % | `lanes` parseado a numérico (primer valor si lista). |
| `sin_carril_reportado` | bool | 0 | Flag: el valor en `lanes_imputados` es imputación, no dato observado. |
| `lanes_imputados` | float | 0 | Imputación jerárquica (mediana por `highway`, fallback 1.0). |
| `maxspeed_kmh` | float | 90.4 % | `maxspeed` parseado a km/h; `NaN` si no se reporta. |
| `sin_maxspeed` | bool | 0 | Flag de límite ausente. |
| `jerarquia_vial` | str | 0 | Macro-categoría: `Arterial`, `Intermedia`, `Local`, `No motorizada`, `Otro`. |
| `log_length_m` | float | 0 | `log1p(length_meters)` — estabiliza la cola larga. |
| `geometry` | LineString | 0 | Trazado (EPSG:4326). |

---

## 6. `pronostico_24h_estaciones.csv` — pronóstico 24 h por estación (3,480 × 12)

Salida del `Modelamiento_Preeliminar.ipynb` (§4). Una fila por (estación, hora) del
**2026-08-31**, para las **145 estaciones con señal suficiente**. Pronóstico Chronos (mediana +
banda q10–q90), ocupación estimada, ETA en Modo Histórico (RF-05) y recomendación operativa.

| Campo | Tipo | Nulos | Descripción |
|-------|------|-------|-------------|
| `Fecha_Hora` | datetime | 0 | Timestamp horario del día pronosticado (24 únicos). |
| `Estacion` | str | 0 | Estación (145 únicos). |
| `Validaciones_pron` | float | 0 | Pronóstico (mediana) de validaciones a esa hora. |
| `Val_q10` / `Val_q90` | float | 0 | Banda de incertidumbre (cuantiles 10/90 del pronóstico). |
| `Cap_Total` | float | 0 | Capacidad combinada de la estación (43 únicos); `NaN`→`Ocupacion_pron` normalizada. |
| `Ocupacion_pron` | float | 264 | Ocupación pronosticada = `Validaciones_pron / Cap_Total`, o normalizada por el máximo histórico si falta `Cap_Total`. |
| `Hora_n` | int | 0 | Hora 0–23 (24 únicos). |
| `Validaciones` | float | 468 | Validaciones **reales** (ground truth) de la hora, cuando están disponibles. |
| `oc_level` | str | 0 | Nivel de ocupación pronosticado: `Bajo` / `Medio` / `Alto`. |
| `ETA_pron` | float | 690 | Headway histórico medio por (estación, hora) ajustado ×1.1 (med.) / ×1.3 (alto) según `oc_level` (min). |
| `recomendacion` | str | 0 | Recomendación operativa de refuerzo: `Normal` (1,761 h), `ALTO: considerar refuerzo` (158), `CRITICO: refuerzo inmediato` (1,561). |

---

## 7. `eval_walkforward_modelos.csv` — evaluación walk-forward (55 × 5)

Una fila por (día, modelo) en los 5 días de evaluación (2026-08-14, 15, 16, 21, 29).
11 modelos: `chronos`, `naive_24` y 9 cuantiles `pinball_q10`…`q90`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `dia` | date | Día evaluado (5 únicos). |
| `modelo` | str | Id del modelo (11 únicos). |
| `MAE` | float | Error absoluto medio de validaciones pronosticadas. |
| `RMSE` | float | Raíz del error cuadrático medio. |
| `WMAPE` | float | Error porcentual absoluto ponderado (`Σ\|err\|/Σ\|obs\|`). |

---

## 8. `metricas_modelos.csv` — métricas globales del pronóstico (2 × 4)

Promedio de los 5 días walk-forward: `chronos` (MAE 56.32, RMSE 147.32, WMAPE 0.165) vs `naive_24`
(MAE 104.12, RMSE 244.92, WMAPE 0.237).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `modelo` | str | `chronos` / `naive_24`. |
| `MAE` / `RMSE` / `WMAPE` | float | Métricas globales (promedio walk-forward). |

---

## 9. `code/model/outputs/` — comparativas de módulos

### 9.1 `eta_comparativa_modelos.csv` — comparativa ETA (20 × 6)

Una fila por (día, opción). Opciones: `A_chronos` (Chronos sobre Headway), `B_hist` (tabla
histórica ajustada por ocupación), `C_blend` (`w·A + (1−w)·B`, `w` del walk-forward sin fuga),
`D_ratio` (C × `ratio_congestion` sintético — ablación TomTom).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `dia` | date | Día evaluado (5 únicos). |
| `opcion` | str | `A_chronos` / `B_hist` / `C_blend` / `D_ratio`. |
| `pares` | int | N° de pares estación–hora evaluados (≈2,700). |
| `MAE` / `RMSE` | float | Error del headway en minutos. |
| `w` | float | Peso del blend usado ese día (0.5 / 0.75, de días anteriores). |

### 9.2 `comparativa_aforo_modelos.csv` — comparativa Aforo (8 × 5)

Clasificadores multiclase (`Logistic`, `Tree`, `RF`, `ExtraTrees`, `GB`, `HistGB`, `LightGBM`,
`XGBoost`) sobre **split cronológico** train 07-01→08-13 / test 08-14→08-31.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `modelo` | str | Id del clasificador (8 únicos). |
| `accuracy` | float | Exactitud en test. |
| `balanced_acc` | float | Exactitud balanceada (clases desbalanceadas). |
| `f1_macro` | float | F1 macro. Criterio de selección. |
| `roc_auc_ovr` | float | ROC-AUC one-vs-rest, independiente del umbral de decisión. |

### 9.3 `comparativa_modulo3_modelos.csv` — comparativa Módulo 3 (8 × 4)

Clasificadores que **preservan la matriz de decisión** U(ETA, Aforo) (umbral 10 min + chequeo del
siguiente bus). Métricas sobre el test.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `modelo` | str | Id del clasificador (8 únicos). |
| `fidelidad_AC03` | float | Fracción de decisiones iguales a la matriz → criterio AC-03 (≥ 0.80). |
| `f1_macro` | float | F1 macro de las 3 clases (`abordar`, `cambiar_paradero`, `esperar_siguiente`). |
| `fp_abordar` | float | Tasa de **falsos positivos de «Abordar»** (recomendar abordar un bus colapsado) — error de mayor costo. |

---

## Notas transversales

- **Modo Histórico vs telemetría:** `ETA_pron` y `recomendacion` no dependen de datos en vivo
  (RF-05). La capa de congestión sintética es para ablación (opción D); en producción se reemplaza
  por TomTom real.
- **Determinismo:** `congestion_sintetica.csv` es reproducible (seed 42); el resto de los archivos
  son reproducibles ejecutando los notebooks/scripts citados en [`DatasetDescriptions.md`](DatasetDescriptions.md).
- **Zona horaria:** todos los timestamps son `-05:00` (Colombia, sin horario de verano).