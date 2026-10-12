# UrbanSafe AI — Semana 09: estado del producto de datos

**Curso:** DS3022 Desarrollo de Producto de Datos (UTEC, 2026-2) · **Fecha:** octubre 2026

| Integrante | Rol |
| :--- | :--- |
| Elmer José Manuel Villegas Suarez | Data Engineer — ingesta, pipelines, EDA y diccionarios |
| Alessandro Facundo Freed Monzón Gallegos | Data Product Manager — requerimientos, backend y frontend |
| Juan David Velo Poma (líder) | Data Scientist — modelado, evaluación y explicabilidad |

Esta carpeta consolida **lo que tenemos hasta ahora**: la copia de week08 (EDA, scripts, modelado y
documentación) más una **evaluación v2** de todos los componentes analíticos, los datos procesados en
CSV y la presentación actualizada. El prototipo funcional (API, frontend y despliegue) se entrega en
`deliveries/week10/`.

## Índice — checklist de la semana 9

| # | Pedido del profesor | Dónde está |
| :---: | :--- | :--- |
| 1 | Presentación actualizada del proyecto | [`PresentationWeek09.pptx`](PresentationWeek09.pptx) · [`PresentationWeek09.pdf`](PresentationWeek09.pdf) |
| 2 | Notebook de Jupyter y código utilizado | [§7](#7-instrucciones-de-ejecución) · `code/eda/`, `code/model/`, `code/scripts/` |
| 3 | Datos originales y procesados, o instrucciones de acceso | [§2](#2-datos-originales-y-procesados) · `data_csv/` |
| 4 | Qué funciona actualmente y qué falta desarrollar | [§5](#5-qué-funciona-y-qué-falta-desarrollar) |
| 5 | Resultado a demostrar en la presentación final (beneficios por usuario) | [§6](#6-resultado-a-demostrar-en-la-presentación-final) |
| 6 | Variable que se busca predecir, clasificar, recomendar o explicar | [§3](#3-variable-objetivo) |
| 7 | Modelos probados, métricas obtenidas y conclusiones | [§4](#4-modelos-probados-métricas-y-conclusiones) · `docs/Model.md` |
| 8 | Instrucciones para ejecutar el notebook o aplicativo | [§7](#7-instrucciones-de-ejecución) |
| 9 | Limitaciones conocidas y próximos pasos | [§8](#8-limitaciones-conocidas-y-próximos-pasos) |
| 10 | Descripción del problema, usuario objetivo y solución propuesta | [§1](#1-problema-usuarios-y-solución) |

---

## 1. Problema, usuarios y solución

**Problema.** En el Sistema Integrado de Transporte de Lima (Metropolitano, corredores
complementarios y Metro Línea 1) el pasajero no sabe cuándo llega la próxima unidad ni qué tan llena
viene. Eso produce esperas ineficientes, viajes en buses saturados y aglomeraciones. A esto se suma la
inseguridad de los tramos a pie de primera y última milla: según el INEI (2025), más del 85 % de los
limeños percibe inseguridad en la vía pública.

**Usuarios objetivo.**

| Usuario | Necesidad | Qué le da UrbanSafe AI |
| :--- | :--- | :--- |
| **Pasajero** del sistema integrado | Decidir si abordar, esperar la siguiente unidad o cambiar de paradero | Aforo esperado (Asientos / De pie / Saturado), ETA de las 2 próximas unidades y recomendación |
| **Planificador** (ATU, municipios) | Anticipar la demanda y reaccionar ante eventos | Pronóstico 24 h por estación o ruta con banda de confianza, alertas de días atípicos (paros, feriados) y focos de presión |

**Solución propuesta.** Un producto de datos predictivo y prescriptivo que funciona en cascada:

1. **Pronóstico de demanda** (validaciones por unidad y hora, 24 h adelante, con banda del 80 %).
2. **Aforo** derivado del pronóstico: índice de presión de abordaje (`crowding_index`) → 3 clases.
3. **ETA** (headway oficial × factor de aforo) y **recomendación** con la regla U
   (abordar / esperar / cambiar de paradero).
4. **Alertas**: detección de días anómalos a partir de los residuos del pronóstico.
5. *(Semana 11)* **Ruta peatonal segura** sobre OpenStreetMap (luminarias, comisarías, comercios).

Detalle de requerimientos, canvas y arquitectura: `deliveries/week07/` (Requirements.md, canvas,
diagramas) y `deliveries/week08/README.md`.

## 2. Datos originales y procesados

**Fuente principal:** validaciones horarias 2025 entregadas por la **ATU** vía solicitud de acceso a la
información pública. Son dos archivos ZIP que no se versionan por su tamaño:

| Archivo | Contenido |
| :--- | :--- |
| `4950-2026-02-0012640.zip` (246 MB) | Excel COSAC: troncal, alimentadores, corredores complementarios y catálogos de paraderos |
| `OneDrive_*.zip` (5.5 MB) | Metro Línea 1: libros mensuales (2024-01 a 2026-01) + shapefiles de estaciones y eje |

**Cómo obtenerlos:** descargarlos del [Drive del equipo](https://drive.google.com/drive/folders/1qktczst2lUi7BqOt3Lr5ffcip9wqOSSw?usp=sharing)
y copiarlos en `deliveries/week09/zip/` (el script toma cualquier `*.zip` de esa carpeta). Las
fuentes web complementarias (portal ATU, gob.pe, OpenStreetMap vía BBBike/Overpass y OSRM) se
descargan con los scripts de `code/scripts/` (ver [§7](#7-instrucciones-de-ejecución)).

**Datos procesados:**

| Ubicación | Formato | Contenido |
| :--- | :--- | :--- |
| `data_processed/raw/` | Parquet (gitignored) | Excel → formato largo, sin limpieza (`prepare_parquet.py`) |
| `data_processed/clean/` | Parquet (gitignored) | Paneles limpios por sistema + `demanda_consolidada_fiable.parquet` (12,344,159 filas) |
| **`data_csv/`** | **CSV (versionado)** | `panel_horario_<sistema>.csv`: unidad × fecha × hora, cobertura ≥ 90 % (870,708 filas en total) · `calidad_cobertura.csv` · `calendario_eventos_2025.csv` |

Diccionarios campo por campo: `docs/data_dictionary/` (un archivo por sistema + fuentes web). Las
columnas de `data_csv/panel_horario_*.csv` son `sistema, unidad, fecha, hora, validaciones,
dia_semana, tipo_dia, es_feriado, tipo_evento` (`tipo_evento` ∈ normal / feriado / paro / vispera).

**Reproducibilidad verificada.** Re-ejecutamos todo el pipeline desde los ZIP en una máquina distinta
(Windows, Python 3.14). Los conteos coinciden **exactamente** con el contrato del pipeline de week10:

| Tabla | Filas esperadas | Filas obtenidas |
| :--- | ---: | ---: |
| troncal_hora | 398,928 | 398,928 |
| metro_l1_hora | 341,640 | 341,640 |
| corredores_hora | 8,253,635 | 8,253,635 |
| alimentador_hora | 4,670,304 | 4,670,304 |
| demanda fiable (vista) | 12,344,159 | 12,344,159 |

## 3. Variable objetivo

| Tarea | Variable | Tipo | Cómo se mide |
| :--- | :--- | :--- | :--- |
| **Predecir** | `validaciones` por unidad (estación o ruta) y hora, horizonte 24 h, contexto hasta el día previo 23:00 | Pronóstico de series de tiempo (regresión) | WMAPE (criterio), MAE, RMSE, MASE, WQL, cobertura 80 % |
| **Clasificar** | `aforo` ∈ {Asientos, De_pie, Saturado} a partir del `crowding_index` = val/Cap_hora + 0.3 · upstream | Multiclase (cascada desde el pronóstico) | F1-weighted, F1-macro, accuracy (RNF-01, AC-02) |
| **Recomendar** | `recomendacion` ∈ {abordar, esperar_siguiente, cambiar_paradero} | Regla U sobre aforo + ETA | Acuerdo con la regla aplicada a datos reales (AC-03) y balanced accuracy |
| **Explicar / detectar** | Día anómalo (feriado, paro, evento) por sistema | Detección no supervisada | PR-AUC, ROC-AUC, precisión, recall contra un calendario de eventos |
| Estimar | `eta_min` de las 2 próximas unidades | Estimador determinista (headway × factor) | Error inducido por el modelo (sin GPS no hay llegadas reales) |

> Las validaciones son **abordajes registrados**, no ocupación a bordo: cuando el bus va lleno, quien
> no sube no valida. Por eso el aforo es un **proxy de presión de abordaje** y no un conteo de
> pasajeros (detalle en `docs/Model.md` §2.1).

## 4. Modelos probados, métricas y conclusiones

### 4.1 Qué cambió en la evaluación (week08 → week09)

Al cruzar los días de evaluación de week08 con el calendario oficial encontramos dos problemas:

1. **2 de los 5 días de test eran atípicos.** El **04-nov-2025** hubo paro de transportistas y el
   **09-dic-2025** fue feriado (Batalla de Ayacucho). El ganador además se elegía sobre esos mismos días.
2. **El calendario tenía 11 feriados**, pero el oficial 2025 tiene 16: faltaban 07-06, 23-07, 28-07,
   06-08 y 09-12. Se corrigió en los 4 notebooks EDA; los conteos no cambian.

La **evaluación v2** (`code/model/model_atu_v2.py`, `evaluar_v2.py`, `Evaluacion_Modelos_v2.ipynb`)
corrige ambos problemas:

- *Rolling-origin* diario; la **validación** (15–31 oct) elige el modelo y el **test** (1 nov – 31 dic,
  **61 días**) solo reporta.
- Estratos: días normales, atípicos, laborables y fin de semana.
- Modelos nuevos: `media_4sem`, MSTL, LightGBM directo, **Chronos-2** con covariable de feriado, y un
  ensemble del top-3 de validación.
- Bandas **conformal** en lugar del ±15 % fijo.
- Se evalúa la **cascada real del producto** (aforo, ETA y regla U) y el detector de anomalías contra
  feriados y 8 paros verificados en prensa.

Literatura que respalda las decisiones:

- **Chronos-2** ([Ansari et al., 2025](https://arxiv.org/abs/2510.15821)): resulta top-3 en los
  benchmarks independientes de 2026 ([It's TIME](https://arxiv.org/abs/2602.12147),
  [LiveHouse-TS](https://arxiv.org/abs/2608.17299)), es de los mejor calibrados
  ([arXiv 2609.25788](https://arxiv.org/abs/2609.25788)) y es un baseline fuerte en transporte
  ([Yanes-Pulido & Rodrigues, 2026](https://arxiv.org/abs/2602.24238)).
- **Conformal para series de tiempo** ([Stocker et al., 2025](https://arxiv.org/abs/2511.13608);
  [Sabashvili, 2026](https://arxiv.org/abs/2601.18509)): base de las bandas calibradas.
- **Anomalías por residuos de pronóstico:** la literatura con datos de tarjeta reporta que funciona
  mejor que usar los datos crudos.

### 4.2 Pronóstico de demanda (test, 61 días)

| Sistema | Ganador (validación) | WMAPE test | WMAPE normales | WMAPE atípicos | MASE | Mejor baseline (WMAPE) | Mejora | DM p-valor vs baseline | Cobertura 80 % (conformal) |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- | ---: | ---: | ---: |
| Metro L1 | **Ensemble** (LightGBM + Chronos-2 + MSTL) | **0.102** | 0.076 | 0.354 | 0.95 | Media 4 sem. (0.126) | 18.7 % | 0.0003 | 77.1 % |
| Troncal | **Ensemble** (LightGBM + Chronos-2 + MSTL) | **0.123** | 0.084 | 0.604 | 0.95 | Media 4 sem. (0.160) | 23.0 % | 0.0031 | 77.9 % |
| Corredores | **Ensemble** (LightGBM + Chronos-2 + Chronos-Bolt) | **0.120** | 0.092 | 0.465 | 0.81 | Media 4 sem. (0.167) | 28.4 % | 0.0024 | 80.4 % |
| Alimentadores | **LightGBM** | **0.405** | 0.393 | 0.548 | 0.71 | Media 4 sem. (0.472) | 14.4 % | 0.0002 | 81.1 % |

### 4.3 Aforo, ETA y recomendación (test)

| Sistema | Modelo | Accuracy | F1-weighted | F1-macro | F1 Saturado | RNF-01 | AC-02 | Error ETA (min) | Acuerdo regla U (AC-03) | Balanced acc. regla U |
| :--- | :--- | ---: | ---: | ---: | ---: | :---: | :---: | ---: | ---: | ---: |
| Metro L1 | Cascada Ensemble | 0.919 | 0.919 | 0.904 | 0.883 | ✅ | ✅ | 0.07 | 96.9 % | 0.846 |
| Metro L1 | HistGB directo (w08) | 0.881 | 0.879 | 0.856 | 0.826 | ✅ | ✅ | 0.10 | 96.2 % | 0.730 |
| Metro L1 | Moda histórica | 0.881 | 0.879 | 0.853 | 0.815 | ✅ | ✅ | 0.10 | 95.8 % | 0.713 |
| Metro L1 | Clase mayoritaria | 0.551 | 0.391 | 0.237 | 0.000 | ❌ | ❌ | 0.42 | 93.1 % | 0.333 |
| Metro L1 | «Siempre abordar» | – | – | – | – | – | – | – | 93.1 % | 0.333 |
| Troncal | Cascada Ensemble | 0.905 | 0.907 | 0.899 | 0.905 | ✅ | ✅ | 0.07 | 97.8 % | 0.904 |
| Troncal | HistGB directo (w08) | 0.921 | 0.920 | 0.903 | 0.884 | ✅ | ✅ | 0.06 | 97.6 % | 0.791 |
| Troncal | Moda histórica | 0.920 | 0.920 | 0.904 | 0.892 | ✅ | ✅ | 0.06 | 97.7 % | 0.793 |
| Troncal | Clase mayoritaria | 0.582 | 0.428 | 0.245 | 0.000 | ❌ | ❌ | 0.31 | 94.7 % | 0.333 |
| Troncal | «Siempre abordar» | – | – | – | – | – | – | – | 94.7 % | 0.333 |
| Corredores | Cascada Ensemble | 0.927 | 0.927 | 0.906 | 0.883 | ✅ | ✅ | 0.10 | 97.6 % | 0.935 |
| Corredores | HistGB directo (w08) | 0.921 | 0.922 | 0.890 | 0.844 | ✅ | ✅ | 0.12 | 96.5 % | 0.946 |
| Corredores | Moda histórica | 0.924 | 0.924 | 0.891 | 0.842 | ✅ | ✅ | 0.11 | 96.8 % | 0.903 |
| Corredores | Clase mayoritaria | 0.611 | 0.464 | 0.253 | 0.000 | ❌ | ❌ | 0.62 | 89.7 % | 0.500 |
| Corredores | «Siempre abordar» | – | – | – | – | – | – | – | 89.7 % | 0.500 |
| Alimentadores | Cascada LightGBM | 0.839 | 0.842 | 0.766 | 0.708 | ✅ | ❌ | 0.14 | 97.0 % | 0.636 |
| Alimentadores | HistGB directo (w08) | 0.827 | 0.831 | 0.743 | 0.659 | ✅ | ❌ | 0.15 | 96.5 % | 0.613 |
| Alimentadores | Moda histórica | 0.789 | 0.801 | 0.697 | 0.584 | ❌ | ❌ | 0.20 | 95.4 % | 0.654 |
| Alimentadores | Clase mayoritaria | 0.703 | 0.581 | 0.275 | 0.000 | ❌ | ❌ | 0.29 | 96.4 % | 0.333 |
| Alimentadores | «Siempre abordar» | – | – | – | – | – | – | – | 96.4 % | 0.333 |

### 4.4 Anomalías (feb–dic 2025, etiquetas: 16 feriados + 8 paros)

| Sistema | Detector | PR-AUC | ROC-AUC | Precisión@k | Precisión | Recall |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| Metro L1 | Residuo vs media 4 sem. + z robusto (v2) | 0.595 | 0.921 | 0.591 | 0.320 | 0.727 |
| Metro L1 | z del total vs mismo día de la semana | 0.590 | 0.922 | 0.565 | 0.588 | 0.435 |
| Metro L1 | IsolationForest (week08) | 0.408 | 0.630 | 0.391 | 0.529 | 0.391 |
| Troncal | Residuo vs media 4 sem. + z robusto (v2) | 0.691 | 0.896 | 0.591 | 0.304 | 0.773 |
| Troncal | z del total vs mismo día de la semana | 0.725 | 0.926 | 0.652 | 0.700 | 0.609 |
| Troncal | IsolationForest (week08) | 0.461 | 0.640 | 0.435 | 0.588 | 0.435 |
| Corredores | Residuo vs media 4 sem. + z robusto (v2) | 0.717 | 0.918 | 0.636 | 0.333 | 0.773 |
| Corredores | z del total vs mismo día de la semana | 0.717 | 0.900 | 0.652 | 0.778 | 0.609 |
| Corredores | IsolationForest (week08) | 0.226 | 0.500 | 0.174 | 0.222 | 0.174 |
| Alimentadores | Residuo vs media 4 sem. + z robusto (v2) | 0.395 | 0.830 | 0.409 | 0.286 | 0.636 |
| Alimentadores | z del total vs mismo día de la semana | 0.480 | 0.831 | 0.478 | 0.500 | 0.391 |
| Alimentadores | IsolationForest (week08) | 0.435 | 0.660 | 0.391 | 0.471 | 0.348 |

### 4.5 Conclusiones

1. **La evaluación de week08 sobreestimaba a AutoETS y a Chronos-Bolt.**
   - En 61 días con todos los días de la semana, AutoETS(24 h) es el peor modelo (WMAPE 0.25–0.58). Era
     el ganador de week08 en troncal, corredores y alimentadores. Sin estacionalidad semanal, colapsa en
     fines de semana (0.42–0.83). Con la historia completa mejora en martes (0.137 frente a 0.183 en L1),
     pero no en sábado (0.267 con ambas ventanas).
   - Chronos-Bolt, el ganador de week08 en L1, queda detrás de los modelos v2 en los 4 sistemas.
2. **Los modelos elegidos en validación superan a la mejor baseline** (`media_4sem`) en los 4 sistemas,
   con diferencias significativas (Diebold-Mariano p < 0.01). La reducción de WMAPE es de 19 % en Metro
   L1, 23 % en troncal, 28 % en corredores y 14 % en alimentadores.
3. **LightGBM directo es el mejor modelo individual.**
   - WMAPE de test: 0.100 en L1, 0.115 en troncal, 0.113 en corredores y 0.405 en alimentadores.
   - También es el más barato: 0.4–6 min por sistema para los 78 días, frente a 12–41 min de Chronos-2
     en CPU.
   - El ensemble elegido en validación no es significativamente distinto (p = 0.28–0.63).
4. **Chronos-2 zero-shot queda a 1–10 % de LightGBM sin entrenar nada.** Es consistente con la literatura
   de 2026 (los modelos fundacionales son un baseline fuerte en transporte).
   - Su covariable de feriado reduce el error en feriados frente a las baselines (L1: 0.46 frente a 0.67).
   - Aun así, LightGBM con banderas de calendario es mejor en feriados (0.25–0.48).
5. **Los días atípicos siguen siendo el punto débil.**
   - En L1, troncal y corredores el WMAPE es 0.35–0.60 en feriados, paros y vísperas, frente a 0.08–0.09
     en días normales.
   - Alimentadores es el sistema más difícil (0.39 incluso en días normales) por su cobertura irregular.
6. **Las bandas conformal cumplen lo prometido:** cubren entre 76.5 y 83.9 % con todos los modelos
   (objetivo: 80 %). En cambio, la banda fija de ±15 % de week08 cubre entre 16.7 y 79.6 %, y los
   cuantiles nativos de Chronos-2 se quedan en 69.5–75.7 %.
7. **Aforo:** la cascada del producto cumple RNF-01 en los 4 sistemas y AC-02 en 3.
   - F1-weighted: 0.91–0.93 en L1, troncal y corredores; 0.84 en alimentadores.
   - Alimentadores falla AC-02 en "Saturado" (F1 0.71).
   - La cascada supera al clasificador HistGB de week08 en L1 y alimentadores, y empata en corredores.
     En troncal, la moda histórica (0.920) iguala o supera a la cascada (0.907): el régimen
     hora × estación explica casi todo.
8. **AC-03 se cumple, pero no discrimina:** «siempre abordar» ya acierta entre 90 y 96 %. Con balanced
   accuracy, la regla aplicada al pronóstico obtiene 0.85, 0.90, 0.93 y 0.64, frente a 0.33–0.50 de la
   baseline. **Proponemos medir AC-03 con balanced accuracy.**
9. **Alertas:** el detector causal por residuos mejora claramente al IsolationForest de week08.
   - PR-AUC: 0.59, 0.69, 0.72 y 0.39, frente a 0.41, 0.46, 0.23 y 0.44 del IsolationForest. Gana en 3
     de 4 sistemas.
   - Detecta 12–14 de los 15 feriados evaluables, pero solo 2–4 de los 7 paros.
   - En general, los paros **reducen** la demanda formal: hasta −21 % en L1, −26 % en troncal y −30 % en
     corredores. En alimentadores, en cambio, la subieron: +15 % y +21 % los días 7 y 10 de abril.
   - Parte de los "falsos positivos" son eventos reales no etiquetados (por ejemplo, el 15-jun en L1,
     con −67 %).
10. **Decisión para el prototipo (week10).**
    - Modelo principal: el ganador de validación. Es el ensemble en L1, troncal y corredores, y LightGBM
      en alimentadores. Se ejecuta en batch diario (≈ 46 s por sistema con Chronos-2).
    - **Modo ligero:** LightGBM, que responde en milisegundos y no requiere torch. Sirve para despliegues
      con poca memoria y tiene precisión estadísticamente equivalente.

Tablas completas: `code/model/results_v2/<sistema>/` · Notebook: `code/model/Evaluacion_Modelos_v2.ipynb`
· Narrativa de week08 + sección v2: `docs/Model.md`.

## 5. Qué funciona y qué falta desarrollar

| Componente | Estado | Dónde |
| :--- | :---: | :--- |
| Pipeline de datos ATU (ZIP → Parquet → EDA → CSV), reproducible y verificado | ✅ | `code/scripts/`, `code/eda/`, `data_csv/` |
| EDA por sistema + comparativo, con calendario corregido | ✅ | `code/eda/`, `docs/DataAnalysis.md` |
| Modelado por sistema (week08) y evaluación v2 de 9 modelos | ✅ | `code/model/` |
| Aforo en cascada, ETA, regla U y detector de anomalías evaluados | ✅ | `results_v2/`, notebook v2 |
| Ingesta a PostgreSQL + Docker con pruebas de paridad (Elmer) | ✅ | `deliveries/week10/` |
| Modelos serializados con manifiesto, sha256 y verificación de recarga | ✅ | `deliveries/week10/models/` |
| Módulo de inferencia (pronóstico + banda + aforo + ETA + recomendación) | ✅ | `deliveries/week10/code/model/inferencia.py` |
| API REST con inferencia en < 2 s (P95) | ⏳ S10 | Alessandro |
| Frontend web, video y despliegue con URL pública | ⏳ S10 | Alessandro |
| Batch diario que llene la tabla `prediccion` | ⏳ S10 | Elmer + Juan |
| TomTom en vivo como entrada del pronóstico (hoy alimenta el modo resiliente) | ⏳ S12 | Elmer |
| Módulo peatonal seguro sobre OSM | ⏳ S11 | equipo |
| Validación con usuarios (feedback de aforo, CSAT) | ⏳ S12 | equipo |

## 6. Resultado a demostrar en la presentación final

**Para el pasajero.** En 2 toques ve el aforo esperado y el ETA de las dos próximas unidades en su
estación, con una recomendación explícita (abordar, esperar o cambiar de paradero). Beneficio: menos
tiempo de espera e incertidumbre y menos viajes en unidades saturadas. De noche, además, una ruta a
pie más segura (semana 11).

**Para el planificador (ATU).** Pronóstico de 24 h por estación o ruta con banda de confianza
calibrada, alertas de días atípicos con su magnitud (por ejemplo, la sobredemanda del Metro en un paro
de transportistas) y un mapa de las horas y estaciones con mayor presión de abordaje. Beneficio:
anticipar refuerzos de flota y reaccionar a eventos con datos.

**Qué mostraremos como evidencia:** el flujo completo en vivo sobre datos reales y los indicadores de
test comparados contra baselines simples:

| Indicador (test 1 nov – 31 dic 2025) | Valor actual | Comparado contra |
| :--- | :--- | :--- |
| Error del pronóstico 24 h (WMAPE) | −19 % a −28 % en L1, troncal y corredores; −14 % en alimentadores | mejor baseline (media de 4 semanas) |
| Aforo: F1-weighted de la cascada | 0.91–0.93 (L1, troncal, corredores); 0.84 (alimentadores) | 0.39–0.58 (clase mayoritaria) |
| Recomendación: balanced accuracy | 0.85–0.93 (L1, troncal, corredores) | 0.33–0.50 («siempre abordar») |
| Cobertura de la banda del 80 % | 77–81 % (modelo principal) | 17–80 % (banda fija ±15 %) |
| Alertas: PR-AUC de días atípicos | 0.59–0.72 (L1, troncal, corredores) | 0.23–0.46 (IsolationForest) |

## 7. Instrucciones de ejecución

### 7.1 Entorno

```bash
python -m venv .venv                       # Python 3.14 (igual que el equipo)
.venv\Scripts\activate                     # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt            # raíz del repo: pandas, sklearn, lightgbm, statsforecast, torch, chronos…
pip install ipykernel nbconvert            # para ejecutar los notebooks
```

> `pyrosm` (solo para `download_osm_lima.py`) no tiene wheels para Windows: compila `cykhash` y pide
> MSVC. Alternativa probada: un entorno de conda-forge
> (`micromamba create -p osm_env -c conda-forge python=3.12 pyrosm pandas`) y correr ese script con
> ese intérprete. En Linux, `pip install pyrosm` funciona directamente.

### 7.2 Datos (desde la raíz del repo; ver `code/scripts/Guia.md`)

```bash
mkdir deliveries/week09/zip                # copiar aquí los 2 ZIP de la ATU
.venv/Scripts/python deliveries/week09/code/scripts/extract_zip_data.py
.venv/Scripts/python deliveries/week09/code/scripts/download_transport_pages.py   # ~30 s
<python con pyrosm> deliveries/week09/code/scripts/download_osm_lima.py           # ~3 min
.venv/Scripts/python deliveries/week09/code/scripts/build_trazados.py             # ~12 min (OSRM)
.venv/Scripts/python deliveries/week09/code/scripts/download_atu_mapas.py         # ~1 min
.venv/Scripts/python deliveries/week09/code/scripts/prepare_parquet.py --anio 2025  # ~6–15 min
```

### 7.3 Notebooks

| Orden | Notebook | Produce | Tiempo |
| :---: | :--- | :--- | :--- |
| 1 | `code/eda/eda_troncales_metropolitano.ipynb`, `eda_alimentadores`, `eda_corredores`, `eda_metro_l1` | `data_processed/clean/` + figuras | ~6 min |
| 2 | `code/eda/eda_comparativo_sistemas.ipynb` | `demanda_consolidada_fiable.parquet` | ~2 min |
| 3 | `code/model/Modelamiento_<sistema>.ipynb` (week08) | bakeoff por sistema | ~5 min c/u |
| 4 | `code/model/Evaluacion_Modelos_v2.ipynb` | tablas y figuras v2 (lee `results_v2/`) | segundos |

```bash
cd deliveries/week09/code/eda
jupyter nbconvert --to notebook --execute --inplace eda_metro_l1.ipynb   # o abrir con Jupyter / VS Code
```

### 7.4 Evaluación v2 y exportes

```bash
# Cómputo completo (≈ 1 h en CPU, 2 procesos en paralelo): predicciones + métricas en results_v2/
.venv/Scripts/python deliveries/week09/code/model/evaluar_v2.py --sistemas metro_l1 alimentador --hilos 5
.venv/Scripts/python deliveries/week09/code/model/evaluar_v2.py --sistemas troncal corredor --hilos 5
# Re-analizar sin volver a predecir
.venv/Scripts/python deliveries/week09/code/model/evaluar_v2.py --solo-analisis
# CSV de datos procesados
.venv/Scripts/python deliveries/week09/code/scripts/exportar_csv.py
```

Chronos-Bolt y Chronos-2 se descargan de Hugging Face la primera vez (191 MB y 478 MB, con revisión
fija en `model_atu_v2.py`).

### 7.5 Aplicativo (semana 10)

- Pipeline de ingesta + PostgreSQL: `deliveries/week10/README.md` (`docker compose up --build`).
- Modelos e inferencia: `deliveries/week10/models/README.md`.

## 8. Limitaciones conocidas y próximos pasos

**Limitaciones**

- **Aforo:** las validaciones son abordajes, no ocupación a bordo; el aforo es un proxy de presión.
  Además, con umbrales p60/p90 **por franja**, "Saturado" es relativo a cada franja horaria: de noche,
  entre 6.5 y 13.2 % de las horas operativas quedan como "Saturado", frente a 0.7–3.8 % con umbrales
  globales (`aforo_sensibilidad_umbrales.csv`). En alimentadores no se cumple AC-02: el F1 de
  "Saturado" es 0.71.
- **Regla U:** el corte de 10 min no está calibrado por sistema. En L1, los domingos y feriados
  (headway de 9 min) todo tren "Saturado" genera "cambiar de paradero", algo poco accionable en un metro.
- **ETA:** sin GPS/AVL no hay llegadas reales; solo medimos el error inducido por el modelo.
- **Historia y cobertura:** un solo año de historia en el panel (2025). Corredores (12/26 rutas) y
  alimentadores (23 rutas) tienen cobertura parcial; los huecos se rellenan con 0.
- **Paros:** el detector los marca después de ocurrir (2–4 de 7), pero no se anticipan.
- **AC-03:** tal como está escrito es débil, porque "siempre abordar" ya lo cumple. Proponemos medirlo
  con balanced accuracy.
- **Coste de Chronos-2 en CPU:** 12–41 min por sistema para los 78 días evaluados. En producción hay
  que elegir entre batch diario y el modo ligero (LightGBM, 0.01 s, con precisión equivalente).

**Próximos pasos**

| Semana | Paso |
| :---: | :--- |
| S10 | API + frontend + despliegue; batch diario → tabla `prediccion`; PrototypeReport |
| S11 | Módulo peatonal seguro (grafo OSM + costo por riesgo) |
| S12 | EvaluationReport con casos de estudio; calibrar α del crowding y reemplazar el umbral por franja si la ATU entrega conteos a bordo; incorporar 2024 de la L1 |
| S13–S15 | Docker completo y cloud, video demo, project page y presentación final |

## 9. Cambios respecto a week08

- `code/eda/*.ipynb` y `model_atu_common.feriados_peru_2025()`: calendario de 16 feriados.
  Re-ejecutados con salidas nuevas.
- Nuevos: `code/model/model_atu_v2.py`, `evaluar_v2.py`, `Evaluacion_Modelos_v2.ipynb`,
  `results_v2/`, `code/scripts/exportar_csv.py`, `data_csv/`, `docs/images/model_v2/` y
  `PresentationWeek09.*`.
- `docs/DataAnalysis.md` (nota de actualización) y `docs/Model.md` (§8 evaluación v2).
- Los notebooks `Modelamiento_<sistema>.ipynb` se conservan tal como se ejecutaron en week08: son la
  evidencia de los modelos probados entonces.

## 10. Estructura

```
week09/
├── README.md                      ← este archivo (checklist de la semana 9)
├── PresentationWeek09.pptx / .pdf
├── code/
│   ├── scripts/                   ← descarga, conversión y exportes (+ Guia.md)
│   ├── eda/                       ← 5 notebooks EDA (calendario corregido)
│   └── model/                     ← notebooks week08 + model_atu_v2.py, evaluar_v2.py,
│                                    Evaluacion_Modelos_v2.ipynb, results_v2/ (métricas)
├── data_csv/                      ← datos procesados en CSV (versionados)
├── docs/                          ← DataAnalysis.md, Model.md, data_dictionary/, images/
├── zip/  data/  data_processed/   ← datos crudos y Parquet (gitignored)
```
