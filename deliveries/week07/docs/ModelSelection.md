# Selección y Justificación de Modelos: UrbanSafe AI

* **Curso:** Desarrollo de Productos de Datos (DS-3022) — UTEC
* **Ciclo:** 2026-II
* **Entrega:** Semana 07 — Model Selection y Modelado Preliminar
* **Ubicación en Repositorio:** `deliveries/week07/ModelSelection.md`
* **Implementación de referencia:** `deliveries/week07/code/model/Modelamiento_Preeliminar.ipynb`

---

## 1. Visión General y Continuidad del Producto de Datos

Este documento formaliza la selección, justificación y resultados de los modelos analíticos que
componen el núcleo operante de **UrbanSafe AI**: **reducir la incertidumbre y el tiempo de espera
del pasajero** en el Sistema Integrado de Transporte (RF-01, RF-02, RF-03), con la predicción de
aforo como funcionalidad principal y la recomendación prescriptiva de abordaje como segundo
componente.

A diferencia de la entrega de la Semana 06 (diseño teórico), aquí se describen **los modelos que
realmente se entrenaron y evaluaron** en el `Modelamiento_Preeliminar.ipynb` mediante *walk-forward*:
un **pronóstico de validaciones** con Chronos (modelo fundacional, cero-tuning) con baselines
clásicos, del cual se derivan el **ETA**, el **aforo** y la **recomendación prescriptiva**. La
arquitectura conserva la prioridad del curso: modelos explicables, eficientes y de baja latencia,
con los *baselines* académicos documentados para cada módulo. Los hallazgos del EDA (Semana 06) se
mantienen: **el clima queda excluido del *feature store*** (ver `DataAnalysis.md`).

---

## 2. Dataset de Entrada, Targets y Particiones

### 2.1 Dataset base

* **Fuente:** `data_processed/dataset_limpio.csv` — 176,783 filas × 28 columnas, producido por
  `code/eda/eda_transmilenio.ipynb`.
* **Granularidad:** una fila = validaciones de una **línea** en una **estación**, en una **hora**
  de un **día**.
* **Cobertura:** 2026-07-01 a 2026-08-31 (62 días), 153 códigos de estación, 13 líneas, 12 troncales.
* **Claves:** `num_est` une con el contexto urbano (`dataset_osm_estaciones_limpio.csv`); la
  capa de congestión (`congestion_sintetica.csv`) se une por `(Estacion, Fecha_Hora)`.
* Diccionario por columna: [`Data_Dictionary_Procesados.md`](data_dictionary/Data_Dictionary_Procesados.md).

### 2.2 Panel de series y relleno de ausencias

Se construye un **grid** de **1,488 horas (62 días × 24 h) × 156 estaciones** de `Validaciones`.
Las ausencias (horas sin validaciones) se rellenan con **ceros**, y se filtran las estaciones con
insuficiente señal -> la tabla de pronóstico final cubre **145 estaciones** (3,480 = 145 × 24 h en
`pronostico_24h_estaciones.csv`). Este grid es la entrada del pronóstico walk-forward.

### 2.3 Targets

| Target | Definición | Módulo |
|---|---|---|
| `Validaciones` ($y_{val}$) | Serie horaria de validaciones por estación (objetivo del pronóstico). | Pronóstico (Sección 3) |
| `Headway_Min` ($y_{ETA}$) | `60 / Frecuencia`, intervalo real observado entre buses. Objetivo del Módulo 1. | ETA |
| `Ocupacion_real` ($y_{occ}$) | `Validaciones / Cap_total` (o normalizada). Se discretiza en **Asientos / De pie / Saturado** con cuantiles calibrados en train. | Aforo (Módulo 2) |
| `Regla_Rec` ($y_{rec}$) | Clase derivada de la matriz de decisión `U(ETA, Aforo)`. | Prescriptivo (Módulo 3) |

### 2.4 Partición temporal

No se baraja: **`train` = 2026/07/01 - 2026/08/13**, **`test` = 2026/08/14 - 2026/08/31**. El
*walk-forward* evalúa los días 14, 15, 16, 21 y 29 de agosto; el test del comparativo de
clasificadores usa todo el rango posterior a la partición. El orden temporal se preserva en todo
el pipeline (no hay *leakage* de días singulares; festivos quedan aislados por `Es_Festivo`).

---

## 3. Pronóstico de Validaciones (base de los módulos)

### 3.1 Modelos comparados

| Modelo | Tipo | Rol |
|---|---|---|
| **Chronos** (`amazon/chronos-bolt-small`) | Modelo fundacional de series (probabilístico, 9 cuantiles) | **Modelo seleccionado** — pronostica la panel-serie con *mínimo de señal* por estación. |
| `baseline_hora_media` | Promedio histórico de la misma hora | Baseline académico. |
| `baseline_naive_24` | La validación de "la semana pasada" (misma ventana) | Baseline académico. |
| `pinball_q10…q90` | Cuantiles cronquísticos evaluados en walk-forward | Validación de la calibración probabilística. |

### 3.2 ¿Qué es Chronos-Bolt-Small?

**Chronos** es una familia de **modelos preentrenados para pronóstico de series de tiempo**,
desarrollada por Amazon Science (de acceso público en Hugging Face). La idea central: las series
numéricas se **tokensizan** (las observaciones se escalan y discretizan en *tokens*) y se alimentan
a un **encoder-decoder estilo T5** entrenado como un modelo de lenguaje sobre esos tokens; en
inferencia, el modelo genera tokens futuros que se decodifican de vuelta a valores numéricos. Por
ese diseño puede entregar **pronósticos probabilísticos**: en lugar de un solo valor, genera una
distribución (en el notebook se usan los cuantiles q10–q90 para la banda de incertidumbre).

**Bolt** es la generación optimizada de esa familia (más rápida y eficiente en memoria). La variante
**Small** es la más liviana (~46 M parámetros), pensada para correr en CPU con baja latencia.
El modelo exacto cargado en el notebook es `amazon/chronos-bolt-small`.

#### ¿Por qué es el mejor para nuestro caso?

* **Cero riesgo de sobreajuste.** Tenemos solo **62 días** por estación (una sola
  ventana, sin estacionalidad anual). Entrenar un modelo propio con 62 puntos por serie es casi
  garantía de *overfitting*; Chronos llega **preentrenado sobre millones de series diversas** y
  traslada esos patrones generales (ciclos, festivos, picos) a nuestra serie **sin tocar un
  parámetro** (zero-shot). El ahorro no es solo de tiempo: es de **validez estadística**.
* **Series dispersas y con ausencias.** El grid rellena con ceros las horas sin servicio y filtra
  estaciones con poca señal. Chronos maneja ese contexto con un **mínimo de señal** por estación
  (`pronostica_dia`), algo que un modelo tabular basado en lags trataría como ruido.
* **Cero esfuerzo de despliegue.** Al ser cero-shot, no hay artefactos de entrenamiento que
  versionar ni *checkpoints* propios: en producción se descarga el modelo y se llama la misma
  función que en desarrollo — misma lógica, mismas salidas.
* **Baja latencia (RNF-02).** La variante *Small* corre en CPU y pronostica el grid de estaciones
  en tiempos compatibles con el objetivo de < 2.0 s en P95, sin GPU.
* **Auditable contra baselines.** Como no se "aprende" nada local, su mérito se mide de forma
  limpia contra `naive_24` y `hora_media` en el walk-forward: si algún día se degrada, se ve al
  instante. Esto respeta el lineamiento del curso de no depender de cajas negras sin justificar.
* **Resulta el mejor empiricamente.** En la evaluación walk-forward (5 días) supera a `naive_24`
  en MAE (56.32 vs 104.12), RMSE (147.32 vs 244.92) y WMAPE (0.165 vs 0.237) — el mejor de los
  modelos evaluados, no solo una elección teórica.

**Los modelos que "compiten" y por qué no ganan aquí:**

| Alternativa típica | Por qué no es la mejor para nuestro caso |
|---|---|
| `naive_24` / `hora_media` (baselines) | No capturan la forma del doble pico ni el cambio de régimen festivo/domingo; son el piso que Chronos ya supera. |
| ARIMA / SARIMA | Requiere estimar parámetros por estación y asume estacionariedad; con 62 días y ausencias se degrada rápido y no da banda probabilística calibrada sin trabajo extra. |
| LightGBM/XGBoost con lags | Son **clasificadores/regresores tabulares**: para un horizonte de 24 h necesitan lag-stacking y *roll-forward* por celda, con alto riesgo de **fuga temporal** y sin incertidumbre nativa. En este proyecto se usan donde corresponden: aforo (Módulo 2) y Módulo 3. |
| Modelo propio de deep learning (LSTM/Transformer) | Exige muchos datos (no los tenemos por estación) y entrenamiento/afinamiento costoso; sobreajusta a 62 días. |

#### El beneficio clave: probabilidad en vez de un solo valor

Para un producto que le dice al usuario **"aborda" / "espera" / "cambia de paradero"**, la
incertidumbre no es un defecto del modelo: es **información de decisión**. Un pronóstico puntual
(un solo número) solo puede acertar o fallar; un pronóstico probabilístico (banda q10–q90) dice
**cuán seguros estamos**, y eso se usa en tres lugares:

1. **La recomendación (Módulo 3) se vuelve más segura.** Si la banda es angosta y la hora
   pronosticada respalda "Abordar", la decisión es firme. Si la banda es **ancha** (alta
   incertidumbre), el motor puede degradar la recomendación a un tono prudente o esperar la
   siguiente unidad — exactamente la situación en la que un punto único engañaría al usuario.
2. **Se puede verificar la calibración.** La evaluación evalúa los cuantiles `pinball_q10…q90`
   además del punto medio: que la banda capture la realidad ~80 % de las veces (`Val_q10/Val_q90`
   en `pronostico_24h_estaciones.csv`). Con un solo valor no hay forma de auditar si el modelo
   "sabe cuándo no sabe".
3. **El ETA hereda lo mismo.** La banda q10–q90 del pronóstico de validaciones se propaga a la
   ocupación y al ETA (x1.1/x1.3), de modo que el usuario ve un rango de espera ("llegará en
   ~2–5 min") en vez de una cifra falsamente exacta, alineado con reducir la incertidumbre (RF-02).

**En resumen:** la probabilidad convierte una predicción puntual en una **decisión con nivel de
confianza**, y eso es lo que necesita un sistema prescriptivo cuya falla más cara es recomendar
"Abordar" un bus que viene colapsado.

### 3.3 Resultados (evaluación walk-forward, 5 días)

Métricas globales (`data_processed/metricas_modelos.csv`):

| Modelo | MAE | RMSE | WMAPE |
|---|---|---|---|
| **chronos** | **56.32** | **147.32** | **0.165** |
| naive_24 | 104.12 | 244.92 | 0.237 |

**Interpretación:** Chronos supera a `naive_24` en las 3 métricas y por un margen amplio
(≈46% menos MAE y ≈40% menos RMSE), incluso siendo un modelo *zero-shot* (sin entrenamiento
adicional sobre estos datos). En horas valle/madrugada el WMAPE es alto por construcción
(denominador pequeño), no por error absoluto. Detalle por día: `eval_walkforward_modelos.csv`.

**Por qué no se use regresión clásica aquí:** este paso entrega el **horizonte del producto**
(próximos 24 h); capturar el ciclo temporal (doble pico, festivos) con modelos tabulares requeriría
lag-stacking con riesgo de fuga temporal. Chronos abstrae esa complejidad con calibración incluida
(banda q10–q90).

---

## 4. Módulo 1 — Estimador Continuo del Tiempo de Espera (ETA)

### 4.1 Construcción del target

`Target_ETA_Min = Headway_Min = 60 / Frecuencia` cuando hay oferta GTFS (ver §2.3). Se estima el
headway **del día siguiente** a partir del pronóstico.

### 4.2 Opciones evaluadas (walk-forward)

| Opción | Construcción | Nota |
|---|---|---|
| **A** — `A_chronos` | Chronos pronostica la serie de `Headway_Min` (panel 24 h × estación). | Pronóstico puro. |
| **B** — `B_hist` | Tabla histórica de headway por (estación, hora) ajustada ×1.1/×1.3 según ocupación pronosticada. | **Baseline** (enfoque tradicional del operador). |
| **C** — `C_blend` | `w·A + (1−w)·B`, con `w` elegido en walk-forward **solo con días anteriores** (sin fuga). | **Modelo seleccionado**. |
| **D** — `D_ratio` | La mejor de A/B/C multiplicada por `ratio_congestion` de la capa sintética TomTom (ablación). | Descartada en S07; re-evaluar en S08 con telemetría real. |

### 4.3 Resultados globales (promedio 5 días, `eta_comparativa_modelos.csv`)

| Opción | MAE (min) | RMSE (min) |
|---|---|---|
| **C_blend** | **0.2426** | 1.0854 |
| A_chronos | 0.2451 | 1.2972 |
| B_hist | 0.2968 | **0.8859** |
| D_ratio | 0.4128 | 1.1314 |

**Lectura:** el **blend C** gana en MAE (0.243 vs 0.245 de Chronos solo) y mejora el RMSE frente a
A. La **ablación D** (factor de congestión sintético) **empeora** el MAE a 0.413: el ratio
`freeFlow/current` simulado no aporta señal real. **Conclusión operativa:** el ajuste por congestión
solo se justifica con datos **reales** de producción (TomTom Traffic) y queda **desactivado**
en esta iteración. El peso `w` por día (0.5/0.75) está en el CSV.

### 4.4 En producción (pronóstico 24 h, RF-05)

`ETA_pron = headway histórico por (estación, hora) × 1.1 (ocupación media) / 1.3 (alta)`, derivado
del pronóstico de validaciones. Es **Modo Histórico** (RF-05): no depende de telemetría en vivo,
pero captura el comportamiento típico de cada estación-hora.

---

## 5. Módulo 2 — Predictor Multiclase de Aforo

### 5.1 Construcción del target

La ocupación real `Ocupacion_real = Validaciones / Cap_total` se discretiza en tres clases de
confort usando **cuantiles calibrados solo en train en los cuantiles 0.6/0.9**, supliendo
{Asientos / De pie / Saturado}:

* `lo = Q60(Ocupacion_real | train) = 1.479` -> limite Asientos|De pie.
* `hi = Q90(Ocupacion_real | train) = 9.013` -> limite De pie|Saturado.

> A diferencia del EDA (qcut global de `Ocupacion_pk`), calibrar en train evita confundir "Bajo"
> con "Alto" y hace la etiqueta coherente con los Módulos 2/3.

### 5.2 Features

Las **excluyentes de clima** (EDA). Features: ciclo horario (`sin_h`/`cos_h`, `dia`),
`Es_Habil` y **`Estacion_cod`** (identity de estación — la saturación depende en gran parte de que
la estación sea de alta demanda).

### 5.3 Baselines y modelo comparado

* **Baseline Zero-R (clase mayoritaria):** umbral mínimo de desempeño.
* **Baseline lineal:** `Logistic` — mide cuánto añade la no-linealidad.

Comparativo completo (`comparativa_aforo_modelos.csv`):

| Modelo | accuracy | balanced_acc | f1_macro | roc_auc_ovr |
|---|---|---|---|---|
| **HistGB** | **0.9447** | **0.9336** | **0.9408** | 0.9852 |
| LightGBM | 0.9422 | 0.9296 | 0.9373 | 0.9847 |
| XGBoost | 0.9422 | 0.9288 | 0.9372 | **0.9856** |
| Tree | 0.9361 | 0.9234 | 0.9302 | 0.9398 |
| GB | 0.9230 | 0.9030 | 0.9153 | 0.9809 |
| RF | 0.9159 | 0.8813 | 0.9014 | 0.9789 |
| ExtraTrees | 0.8969 | 0.8251 | 0.8578 | 0.9726 |
| Logistic | 0.8120 | 0.6324 | 0.6550 | 0.8851 |

**Modelo seleccionado: HistGB**, por F1-macro y Balanced Accuracy (criterio del desbalanceo).

### 5.4 Resultado en test (14,178 casos)

| Clase | precision | recall | f1 | support |
|---|---|---|---|---|
| Asientos | 0.949 | 0.974 | 0.961 | 8,721 |
| De pie | 0.926 | 0.883 | 0.904 | 4,102 |
| Saturado | 0.970 | 0.944 | 0.957 | 1,355 |
| **accuracy** | | | **0.945** | 14,178 |

### 5.5 Nowcasting honesto (misma etiqueta, features calendario + estación)

Se evaluó además un clasificador **nowcasting** (usa la ocupación real en test, no pronosticada)
con las mismas etiquetas: se usa como **techo de información** del sistema.

| Clase | precision | recall | f1 | support |
|---|---|---|---|---|
| Asientos | 0.904 | 0.935 | 0.919 | 30,274 |
| De pie | 0.809 | 0.797 | 0.803 | 15,567 |
| Saturado | 0.941 | 0.820 | 0.876 | 6,074 |
| **accuracy** | | | **0.880** | 51,915 |

La brecha Saturado (f1 0.957 vs 0.876) entre ambas versiones es la pérdida esperada al pasar de
ocupación real a pronosticada, y es el margen de mejora de la siguiente iteración.

---

## 6. Módulo 3 — Motor Prescriptivo de Recomendación (*Decision Engine*)

### 6.1 Matriz de decisión `U(ETA, Aforo)` recalibrada

La lógica de decisión del usuario se formaliza como la etiqueta que preservan los clasificadores:
* **`ETA ≥ 10.0 min`** -> **Cambiar de paradero** (esperar más de 10 min no vale la pena).
* **`ETA < 10 min` y la unidad viene saturada** -> **Esperar siguiente** *solo si* el siguiente bus
  **no** viene saturado (se verifica su ocupación pronosticada para la próxima hora); **si el
  siguiente también viene lleno -> Cambiar de paradero**.
* **`ETA < 10 min` y no saturada** -> **Abordar ahora**.

> La regla de la Semana 06 (5/3 min) se **recalibró a 10 min** (según la matriz de utilidad y el
> límite tolerado de espera)

### 6.2 Baselines y modelo comparado

* **Baseline:** las **reglas condicionales estáticas** aplicadas directamente (fidelidad 1.0 por
  construcción). Un clasificador solo tiene sentido si lo **preserva** en el test.

Comparativo (`comparativa_modulo3_modelos.csv`), test = 12,358 decisiones:

| Modelo | fidelidad_AC03 | f1_macro | fp_abordar |
|---|---|---|---|
| **Tree** | **0.9997** | **0.9977** | **0.0000** |
| RF | 0.9997 | 0.9977 | 0.0000 |
| GB | 0.9997 | 0.9977 | 0.0000 |
| HistGB | 0.9992 | 0.9817 | 0.0005 |
| XGBoost | 0.9987 | 0.9611 | 0.0006 |
| LightGBM | 0.9975 | 0.9364 | 0.0005 |
| Logistic | 0.9961 | 0.8819 | 0.0016 |
| ExtraTrees | 0.9960 | 0.8886 | 0.0013 |

**Modelo seleccionado: Tree (Decision Tree).** Por ser la lógica que **mejor atraviesa** (no
"aprende") la matriz, con **fidelidad AC-03 = 0.9997** (≥ 0.80 exigido), **F1-macro 0.998** y
**cero falsos positivos de «Abordar»** (recomendar abordar un bus colapsado, el error de mayor
costo de experiencia). Un árbol es además auditável visualmente y de latencia nula.

### 6.3 Distribución del test y matriz

| Clase | count | precision | recall | f1 |
|---|---|---|---|---|
| abordar | **11,999** | 1.000 | 1.000 | 1.000 |
| cambiar_paradero | 293 | 0.987 | 1.000 | 0.993 |
| esperar_siguiente | 66 | 1.000 | 1.000 | 1.000 |

**Lectura:** la saturación generalizada del sistema (133/153 estaciones sobre capacidad en pico)
hace que "abordar" domine; "esperar siguiente" es rara porque exige que la unidad actual venga
llena **y** la siguiente venga libre — raro en hora pico, exactamente el caso que la regla nueva
protege.

---

## 7. Módulo 4 — Detector de Anomalías Espacio-Temporales

### 7.1 Planteamiento

* **Entrada:** registros del **test** (contexto): serie de validaciones y su pronóstico.
* **Baseline:** umbral móvil Z-Score / IQR (univariable, revisado en el EDA).
* **Modelo seleccionado:** **Isolation Forest**, entrenado **solo sobre el contexto ≤ `split`**
  (sin etiquetas), aplicado al test.

### 7.2 Resultados

* `anomaly_score` continuo por registro; umbrales por percentiles:
  **p0.5 -> −0.686, p3.0 -> −0.605** (fracción esperada bajo umbral ≈ 0.005 / 0.03).
* Columna `outlier` flaggea los registros anómalos; la agregación diaria revela qué días se desvían
  del patrón histórico (demanda anómala). El día más anómalo del test es 2026-08-31 (0.095 de
  fracción de outliers), consistente con el cierre de señal del periodo.

---

## 8. Uso Operativo en Producción

### 8.1 Flujo de inferencia (cascada)

1. **Pronóstico:** Chronos entrega `Validaciones_pron` + banda q10–q90 para las próximas 24h.
2. **ETA (Módulo 1):** `C_blend = w·chronos + (1−w)·histórico` — ETA en minutos.
3. **Aforo (Módulo 2):** HistGB clasifica Asientos / De pie / Saturado.
4. **Anomalías (Módulo 4):** IsolationForest sobre el contexto vigila el corredor.
5. **Recomendación (Módulo 3):** Tree aplica la matriz `U(ETA, Aforo)` -> abordar / esperar
   siguiente / cambiar de paradero, en < 2.0 s (RNF-02).

### 8.2 Modo Resiliente (RF-05)

Sin telemetría real (arranque del producto), el sistema opera en **Modo Histórico**:
`ETA_pron` usa la tabla histórica ajustada por ocupación y **no** se aplica el `ratio_congestion`
(la ablación D mostró que el ratio sintético no aporta). Con **TomTom Traffic real** (S08, key
`TOMMTOM_KEY`) se recalibraría sin reentrenar: `eta_efectivo = eta_base × ratio`.

---

## 9. Artefactos y Métricas

| Artefacto | Contenido |
|---|---|
| `data_processed/metricas_modelos.csv` | Métricas globales del pronóstico (chronos vs naive_24). |
| `data_processed/eval_walkforward_modelos.csv` | Walk-forward 5 días × 11 modelos. |
| `code/model/outputs/eta_comparativa_modelos.csv` | Comparativa ETA (4 opciones × 5 días, con `w`). |
| `code/model/outputs/comparativa_aforo_modelos.csv` | Comparativa Aforo (8 clasificadores). |
| `code/model/outputs/comparativa_modulo3_modelos.csv` | Comparativa Módulo 3 (fidelidad AC-03, F1, FP-«Abordar»). |
| `data_processed/pronostico_24h_estaciones.csv` | Pronóstico 24 h por estación + ETA + recomendación operativa. |

Diccionarios de datos: [`data_dictionary/`](data_dictionary/) (incluye `Data_Dictionary_Procesados.md` y
`DatasetDescriptions.md`). El notebook completo (`Modelamiento_Preeliminar.ipynb`) reproduce todos
los archivos anteriores.

---

## Notas operativas

* **Targets calibrables:** las fórmulas de `Target_ETA_Min`, la discretización de `Ocupacion_real`
  (quantiles 0.6/0.9) y la matriz `U(ETA, Aforo)` (umbral 10 min + chequeo del siguiente bus) son
  **calibraciones actuales**, sujetas a ajuste con pruebas de usuario y datos reales de producción.
* **Feature store dinámico:** el conjunto de variables es preliminar y podrá incorporar o descartar
  predictores (p. ej. el ratio de congestión TomTom real, features de contexto urbano OSM) conforme
  el despliegue lo justifique.