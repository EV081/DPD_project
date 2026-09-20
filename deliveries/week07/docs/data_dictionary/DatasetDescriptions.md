# Descripción de Datasets — UrbanSafe AI

**Entrega:** Semana 07 · **Ubicación:** `deliveries/week07`

Este documento describe los **datasets procesados** (`data_processed/`) y los **artefactos de
modelado** (`code/model/outputs/`) que alimentan el pipeline analítico de UrbanSafe AI. El
diccionario por columna de cada archivo está en
[`Data_Dictionary_Procesados.md`](Data_Dictionary_Procesados.md). La documentación de las fuentes
crudas y los datasets de entrada vive en `Data_Dictionary_Transmilenio.md`,
`Data_Dictionary_Clima.md` y `Data_Dictionary_OSM.md`.

---

## 1. Flujo general del pipeline

```
data cruda (TransMilenio / Clima / OSM)            deliveries/week07/data/
        │  process_transmilenio.py · download_*.py
        ▼
dataset_base.csv (177,944 × 17)                    data/transmilenio/dataset.csv
        │  code/eda/eda_transmilenio.ipynb (limpieza + FE)
        ▼
dataset_limpio.csv (176,783 × 28)                  data_processed/            ◄── base de modelado
        │  code/eda/eda_OSM.ipynb
        ├─► dataset_osm_estaciones_limpio.csv (156 × 12)   (contexto urbano por estación)
        │  code/scripts/congestion.py (S08: TomTom real)
        ├─► congestion_sintetica.csv (232,128 × 7)          (capa sintética de congestión)
        │  code/model/Modelamiento_Preeliminar.ipynb
        ├─► pronostico_24h_estaciones.csv (3,480 × 12)      ◄── pronóstico 24 h por estación
        ├─► eval_walkforward_modelos.csv (55 × 5)           (walk-forward Chronos vs baselines)
        ├─► metricas_modelos.csv (2 × 4)
        └─► code/model/outputs/  (comparativas M1/M2/M3)
```

---

## 2. Resumen de los datasets

| Archivo | Tamaño | Granularidad | Cobertura | Productor | Uso principal |
|---|---|---|---|---|---|
| `data_processed/dataset_limpio.csv` | 176,783 × 28 | (estación, fecha, hora, línea, tipo de día) | 62 días · 153 estaciones · 13 líneas | `code/eda/eda_transmilenio.ipynb` | Base del EDA y de la construcción de series horarias y del pronóstico. |
| `data_processed/congestion_sintetica.csv` | 232,128 × 7 | (estación, hora) | 1,488 h × 156 estaciones | `code/scripts/congestion.py` | Capa de congestión para ajustar el ETA (Módulo 1). En S08 se reemplaza por TomTom Traffic real. |
| `data_processed/dataset_osm_estaciones_limpio.csv` | 156 × 12 | estación (`num_est`) | 156 estaciones | `code/eda/eda_OSM.ipynb` | Features de entorno urbano por estación (buffer 500 m); se unen por `num_est`. |
| `data_processed/pois_limpio.csv` | 35,123 × 7 | punto de interés | Bogotá (bbox del extracto) | `code/eda/eda_OSM.ipynb` | POIs depurados para el segundo plus (seguridad peatonal). |
| `data_processed/red_vial_limpia.geojson` | 123,508 × 16 | tramo vial | Bogotá | `code/eda/eda_OSM.ipynb` | Grafo vial base del enrutamiento peatonal seguro. |
| `data_processed/pronostico_24h_estaciones.csv` | 3,480 × 12 | (estación, hora) | 145 estaciones × 24 h (2026-08-31) | `Modelamiento_Preeliminar.ipynb` | Pronóstico de validaciones con banda q10–q90, ocupación, ETA y recomendación operativa. |
| `data_processed/eval_walkforward_modelos.csv` | 55 × 5 | (día, modelo) | 11 modelos × 5 días (14/15/16/21/29 ago) | `Modelamiento_Preeliminar.ipynb` | Evaluación walk-forward del pronóstico de validaciones. |
| `data_processed/metricas_modelos.csv` | 2 × 4 | modelo | 2 modelos | `Modelamiento_Preeliminar.ipynb` | Métricas globales del pronóstico (promedio walk-forward). |
| `code/model/outputs/eta_comparativa_modelos.csv` | 20 × 6 | (día, opción ETA) | 4 opciones × 5 días | `Modelamiento_Preeliminar.ipynb` | Comparativa del Módulo 1 (ETA). |
| `code/model/outputs/comparativa_aforo_modelos.csv` | 8 × 5 | modelo | 8 clasificadores | `Modelamiento_Preeliminar.ipynb` | Comparativa del Módulo 2 (Aforo). |
| `code/model/outputs/comparativa_modulo3_modelos.csv` | 8 × 4 | modelo | 8 clasificadores | `Modelamiento_Preeliminar.ipynb` | Comparativa del Módulo 3 (Recomendación). |

> `eval_walkforward_modelos.csv`, `metricas_modelos.csv` y `pronostico_24h_estaciones.csv` se
> persisten en `data_processed/` por el notebook; `code/model/outputs/` mantiene una **copia** con
> la hora de la última corrida para que el entregable de modelado sea autocontenido.

---

## 3. Descripción por dataset

### 3.1 `dataset_limpio.csv` — dataset de modelado (TransMilenio)

Producido por `code/eda/eda_transmilenio.ipynb` a partir de `data/transmilenio/dataset.csv`.
Contiene las **validaciones** (demanda) agregadas por **(estación, fecha, hora, línea, tipo de
día)**, enriquecidas con atributos de infraestructura (`Troncal`, `Fase`, `Cap_ART/BIART`),
**oferta GTFS** (`Frecuencia`, `Headway_Min`, `N_Rutas`) y los **features derivados** usados por el
modelo (`Es_Festivo`, `Tipo_Dia_ok`, `Sin_Oferta`, `Cap_total`, `sin_capacidad`, `DiaSemana`,
`Franja`, `Es_Habil`, `Pax_bus`, `Ocupacion_pk`, `log_val`).

- **Cobertura:** 2026-07-01 a 2026-08-31 (62 días), 176,783 filas, 153 códigos de estación
  (`num_est`, 156 nombres), 13 líneas, 12 troncales, 3 fases.
- **Claves de unión:** `num_est` <-> `dataset_osm_estaciones_limpio.csv`; `(Fecha, Hora)` <-> clima
  horario (cruce documentado en `DataAnalysis.md`).
- **Nota:** esta tabla **no** incorpora el clima; el EDA determinó que las variables meteorológicas
  no aportan señal en el periodo ver en `DataAnalysis.md`.

### 3.2 `congestion_sintetica.csv` — capa de congestión para el ETA

Producida por `code/scripts/congestion.py`. Replica a nivel **(estación, hora)** un patrón de
congestión tipo Bogotá (picos 06–09 y 17–20, «pico y placa»)
mediante un ratio `freeFlowSpeed / currentSpeed` ∈ [1.0, 3.0]. Es **determinista** (seed 42): misma
ejecución → mismos valores, y no requiere API.

En producción esta capa se reemplaza por la telemetría real de **TomTom Traffic**
(`flowSegmentData`) con la key de la variable de entorno `TOMMTOM_KEY`. El producto debe operar en
**Modo Histórico** (RF-05) mientras no haya telemetría real.

### 3.3 `dataset_osm_estaciones_limpio.csv` — entorno urbano por estación

Producido por `code/eda/eda_OSM.ipynb`. Para cada una de las 156 estaciones de TransMilenio
computa conteos de POIs por categoría (`poi_500m_<categoria>`) dentro de un **buffer peatonal de
500 m** (proyección `EPSG:3116`), más `total_pois_500m` y `ratio_seguridad_comercio`. Se unen al
dataset principal por `num_est`.

### 3.4 `pois_limpio.csv` y `red_vial_limpia.geojson` — insumos geográficos

- `pois_limpio.csv`: los 35,123 POIs únicos (tras eliminar 6 duplicados espaciales exactos), con
  categoría funcional (`luminaria`, `hospital`, `comisaria`, `comercio`, `negocio`).
- `red_vial_limpia.geojson`: 123,508 tramos viales con `length_meters` en metros (EPSG:3116),
  `jerarquia_vial`, imputación jerárquica de carriles y flags de auditoría (`sin_carril_reportado`,
  `sin_maxspeed`). Base del grafo peatonal del segundo plus.

### 3.5 `pronostico_24h_estaciones.csv` — pronóstico 24 h por estación

Salida del `Modelamiento_Preeliminar.ipynb`. Para cada estación (145 con señal suficiente) y
hora del **2026-08-31** entrega:
- `Validaciones_pron` (mediana del pronóstico Chronos) con banda `Val_q10`/`Val_q90`;
- `Ocupacion_pron` (validaciones / `Cap_Total`, o normalizada por el máximo histórico);
- `oc_level`: `Bajo` / `Medio` / `Alto`;
- `ETA_pron`: headway histórico por (estación, hora) ajustado ×1.1/×1.3 según la ocupación
  pronosticada (**Modo Histórico**, RF-05);
- `recomendacion` operativa de refuerzo: `Normal` (1,761 h), `ALTO: considerar refuerzo` (158) y
  `CRITICO: refuerzo inmediato` (1,561).

### 3.6 `eval_walkforward_modelos.csv` y `metricas_modelos.csv` — evaluación del pronóstico

`eval_walkforward_modelos.csv` guarda **MAE / RMSE / WMAPE por día y por modelo** en el walk-forward
de 5 días (14, 15, 16, 21 y 29 de agosto de 2026). `metricas_modelos.csv` guarda las métricas
**globales** (promedio de los 5 días) de `chronos` y `naive_24`. En S07 se evalúan 11 variantes
(`chronos`, `naive_24` y 9 cuantiles pinball q10–q90).

### 3.7 `code/model/outputs/` — comparativas de los módulos

- `eta_comparativa_modelos.csv` (20 × 6): 4 opciones de ETA (`A_chronos`, `B_hist`, `C_blend`,
  `D_ratio`) en 5 días, con el peso `w` de cada día usado en el blend (walk-forward sin fuga).
- `comparativa_aforo_modelos.csv` (8 × 5): 8 clasificadores (`Logistic`, `Tree`, `RF`, `ExtraTrees`,
  `GB`, `HistGB`, `LightGBM`, `XGBoost`) con `accuracy`, `balanced_acc`, `f1_macro`, `roc_auc_ovr`.
- `comparativa_modulo3_modelos.csv` (8 × 4): 8 clasificadores con `fidelidad_AC03`, `f1_macro` y
  `fp_abordar` (falsos positivos de «Abordar», el error de mayor costo).

---

## 4. Relaciones y claves de unión

| Desde | Hacia | Clave | Uso |
|---|---|---|---|
| `dataset_limpio` | `dataset_osm_estaciones_limpio` | `num_est` | Enriquecer con contexto urbano. |
| `dataset_limpio` | `clima_hora_*.csv` | `(Fecha, Hora)` | Cruce clima (EDA §2.7); no entra al modelo. |
| `dataset_limpio` | grid del notebook | `(Estacion, Fecha, Hora)` | Construir la panel-serie de validaciones (88,551 celdas no nulas de 232,128). |
| `congestion_sintetica` | pronóstico/ETA | `(Estacion, Fecha_Hora)` | Ratio de congestión para la opción D del Módulo 1. |
| `pronostico_24h_estaciones` | `dataset_limpio` | `(Estacion, Hora_n)` | Validar/contextualizar el pronóstico. |

---

## 5. Privacidad y trazabilidad

- Ningún dataset procesado contiene PII: `Numero_Tarjeta` (crudo) es un hash SHA-256 y no se
  persiste en `data_processed/`.
- Todos los archivos son **reproducibles** desde los scripts/notebooks citados; la semilla de
  `congestion_sintetica.csv` es fija (42) para permitir comparaciones byte a byte.