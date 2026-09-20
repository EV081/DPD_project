# UrbanSafe AI: Ecosistema de Movilidad Predictiva y Segura

---

## 1. Equipo de Trabajo y Responsabilidades

| Integrante | Rol |
| :--- | :--- |
| **Elmer Jose Manuel Villegas Suarez** | *Data Engineer* — ingesta, pipelines y diccionarios de datos. |
| **Alessandro Facundo Freed Monzón Gallegos** | *Data Product Manager & AI/ML Developer* — requerimientos, backend y frontend. |
| **Juan David Velo Poma** (*Líder de Proyecto*) | *Data Scientist & Leader* — modelado, explicabilidad y evaluación. |

---

## 2. Problema y Propuesta de Valor

En el Sistema Integrado de Transporte (Metropolitano y Corredores Complementarios de Lima) los
usuarios enfrentan alta incertidumbre sobre **tiempos de llegada** y **nivel de aforo** (asientos
disponibles / de pie / saturado) de las unidades. **UrbanSafe AI reduce esos tiempos de espera**
mostrando el aforo proyectado y el ETA de las próximas unidades, y **recomendando** abordar, esperar
la siguiente o cambiar de paradero. Como segundo plus, integra un **enrutamiento peatonal seguro**
(primera y última milla) que prioriza calles iluminadas y vigiladas sobre la distancia más corta.

El proyecto evoluciona de la **Hackathon ATU 2026** y el concepto de **Urbyte**, combinando datos
abiertos (Open Data/APIs) con una capa sintética.

**Fuentes de datos:**

| Fuente | Rol |
| :--- | :--- |
| **Validaciones ATU (ProTransporte)** | Demanda base prevista — **solicitud pendiente**. Mientras tanto se usa como *proxy* el **dataset de Validaciones Troncales de TransMilenio (Bogotá)** (misma naturaleza BRT). |
| **TomTom Traffic API** | Telemetría de congestión en tiempo real (key `TOMMTOM_KEY`). |
| **OpenStreetMap (OSM)** | Infraestructura urbana (luminarias, comisarías, comercios) -> índice de seguridad peatonal. |
| **Meteostat** | Clima horario de Bogotá — **solo para el EDA**; no entra a los predictores. |
| **Dataset sintético** | Capa de congestión (`congestion_sintetica.csv`) y simulación de aforo. |

---

## 3. Estructura del Repositorio

```
DPD_project/
├── README.md                     ← este archivo
├── requirements.txt              ← dependencias (pandas, sklearn, geopandas, torch, chronos…) 
├── .env(.example)                ← única variable: API key TomTom (TOMMTOM_KEY)
├── .venv/                        ← entorno virtual
└── deliveries/
    ├── week04/                   ← ideación/data product canvas inicial
    ├── week05/                   ← definición, canvas y primeros datasets
    ├── week06/                   ← EDA(TransMilenio+clima+OSM) y selección de modelos (teórica)
    └── week07/                   ← Integrated Project Definition
        ├── Requirements.md                    ← especificación de requerimientos (RF/RNF, AC)
        ├── docs/
        │   ├── DataAnalysis.md                ← EDA (datos, preprocesamiento, hallazgos)
        │   ├── ModelSelection.md              ← selección/justificación de modelos + resultados
        │   ├── images/                        ← figuras del EDA (14 PNG)
        │   └── data_dictionary/
        │       ├── Data_Dictionary_Transmilenio.md/Clima.md/OSM.md   ← fuentes crudas
        │       ├── Data_Dictionary_Procesados.md                         ← datasets procesados
        │       └── DatasetDescriptions.md                                ← descripción de datasets
        ├── code/
        │   ├── download/         ← ingesta (Guia.md explica cada script)
        │   ├── scripts/congestion.py           ← generador de la capa de congestión sintética
        │   ├── eda/              ← notebooks EDA (TransMilenio, clima, OSM)
        │   └── model/            ← Modelamiento_Preeliminar.ipynb + outputs/ (comparativas)
        ├── data/                               ← datos crudos descargados (gitignored)
        │   ├── transmilenio/     ← diario/, geo/, gtfs/, dataset.csv (17 cols)
        │   ├── clima/            ← clima_hora/dia/semana_*.csv
        │   └── OSM/              ← bogota.osm.pbf, pois.csv, red_vial.geojson
        └── data_processed/       ← dataset_limpio.csv (modelo) + salidas del notebook
```

---

## 4. Instrucciones de Ejecución

### 4.1 Entorno

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # y completar la API key de TomTom si se dispone de ella
```

> **TomTom (opcional):** la única variable de entorno es la API key. **Sin key, el sistema opera en
> *Modo Histórico*** (RF-05) — configuración por defecto de la S07; la capa de congestión sintética
> no la requiere.

### 4.2 Descarga e ingesta de datos crudos (`deliveries/week07/code/download/Guia.md`)

Todos los scripts son **idempotentes** y se ejecutan desde la raíz del repositorio:

```bash
.venv/bin/python deliveries/week07/code/download/download_transmilenio.py   # ZIP de validaciones diarias
.venv/bin/python deliveries/week07/code/download/download_geo.py            # estaciones + trazados (GeoJSON)
.venv/bin/python deliveries/week07/code/download/download_gtfs.py           # oferta GTFS semanal
.venv/bin/python deliveries/week07/code/download/download_clima.py          # clima Meteostat (solo EDA)
.venv/bin/python deliveries/week07/code/download/download_osm.py            # calles y POIs (OSM, pyrosm)

# Agrega todo al dataset principal (dataset.csv, 17 columnas):
.venv/bin/python deliveries/week07/code/download/process_transmilenio.py
```

### 4.3 EDA y construcción del dataset de modelado (notebooks)

| Notebook | Produce |
| :--- | :--- |
| `deliveries/week06/code/eda/eda_transmilenio.ipynb` | `dataset_limpio.csv` — **base del modelado** (176,783 × 28). |
| `deliveries/week06/code/eda/eda_transmilenio_clima.ipynb` | Cruce clima (solo análisis). |
| `deliveries/week06/code/eda/EDA_OSM.ipynb` | `dataset_osm_estaciones_limpio.csv`, `pois_limpio.csv`, `red_vial_limpia.geojson` (requiere Colab para el PBF de 20 MB). |

```bash
jupyter notebook deliverables/week06/code/eda/eda_transmilenio.ipynb
```

### 4.4 Modelado preliminary (week07)

```bash
# Capa de congestión sintética (si no existe en data_processed/):
.venv/bin/python deliveries/week07/code/scripts/congestion.py

# Notebook principal - pronóstico Chronos, ETA, aforo, módulo prescriptivo y anomalías:
jupyter notebook deliveries/week07/code/model/Modelamiento_Preeliminar.ipynb
```

El notebook descarga `amazon/chronos-bolt-small` desde Hugging Face (requiere internet) y escribe en
`deliveries/week07/data_processed/` y `code/model/outputs/`:

| Salida | Contenido |
| :--- | :--- |
| `pronostico_24h_estaciones.csv` | Pronóstico 24 h × 145 estaciones (banda q10–q90, ocupación, ETA, recomendación). |
| `eval_walkforward_modelos.csv` | Walk-forward 5 días × 11 modelos (MAE/RMSE/WMAPE). |
| `metricas_modelos.csv` | Métricas globales `chronos` vs `naive_24`. |
| `outputs/eta_comparativa_modelos.csv` | Comparativa ETA (A/B/C/D). |
| `outputs/comparativa_aforo_modelos.csv` | 8 clasificadores de aforo. |
| `outputs/comparativa_modulo3_modelos.csv` | Fidelidad AC-03 / F1 / FP-«Abordar». |


---

## 5. Documentación

| Documento | Alcance |
| :--- | :--- |
| [`deliveries/week07/docs/Requirements.md`](deliveries/week07/docs/Requirements.md) | Requerimientos funcionales/no funcionales, casos de uso, contratos de datos, criterios de aceptación. |
| [`docs/DataAnalysis.md`](deliveries/week07/docs/DataAnalysis.md) | EDA: fuentes, preprocesamiento, hallazgos e implicaciones para el modelado. |
| [`docs/ModelSelection.md`](deliveries/week07/docs/ModelSelection.md) | Selección/justificación de modelos, baselines y resultados de la S07. |
| [`docs/data_dictionary/`](deliveries/week07/docs/data_dictionary/) | Diccionarios de datos (crudos y procesados) + descripciones de dataset. |
| [`code/download/Guia.md`](deliveries/week07/code/download/Guia.md) | Guía técnica de descarga/ingesta. |

---

## 6. Cronograma de Entregables del Curso

| Semana | Entregable | Responsable principal |
| :---: | :--- | :--- |
| **S07** | **Integrated Project Definition** (Requirement spec, EDA, model selection, datasets) | Elmer (datos), Juan David (modelo), Alessandro (requerimientos/arquitectura). |
| **S08** | *Examen Parcial* (sin entrega) — ajustar TomTom real y calibrar modelos. | Elmer (ingesta), Juan David (modelos). |
| **S09** | Desarrollo del Prototipo Base (API REST, pipeline en vivo, Módulos 3 y 4). | Alessandro (backend), Elmer (pipeline). |
| **S10** | **Prototipo Funcional** (frontend, persistencia, métricas vs baselines, video). | Alessandro (frontend), Juan David (validación). |
| **S11** | Eje 2: Módulo Peatonal (grafo OSM + costo por riesgo). | Elmer (datos), Juan David (algoritmo), Alessandro (mapa). |
| **S12** | **Prototipo Refinado y Casos de Estudio** (latencia P95≤2 s, usabilidad, `EvaluationReport.md`). | Elmer (rendimiento), Juan David (evaluación). |
| **S13** | Despliegue Cloud & Docker (URL pública). | Elmer (Docker), Alessandro (cloud). |
| **S14** | Video Demo Final (5–7 min) y Project Page. | Alessandro (video), Juan David (informe final). |
| **S15** | **Entrega Final & Presentación Pública** + README definitivo. | Todo el equipo. |

**Fases:**

* **Fase 1 — Definición e Integración de Requerimientos (S07).** Definición del problema, canvas,
  especificación de requerimientos, EDA, diccionarios, selección de modelos y prototipo de baja
  fidelidad. -> `deliveries/week07/`.
* **Fase 2 — Prototipo Funcional MVP (S08–S10).** Pipeline automatizado, modelos afinados y
  serializados, API REST con latencia < 2.0 s y primer frontend. -> `deliveries/week10/`.
* **Fase 3 — Prototipo Refinado y Módulo Peatonal (S11–S12).** Eje 2 (grafo peatonal OSM),
  evaluación con métricas avanzadas, latencia/usabilidad y casos de estudio. -> `deliveries/week12/`.
* **Fase 4 — Despliegue, Demo y Entrega Final (S13–S15).** Docker + cloud, Video Demo Final,
  Project Page y presentación ante el jurado. -> `deliveries/week15/`.

### Matriz de responsabilidades por rol (S07–S15)

| Semana | **Elmer** *(Data Engineer)* | **Juan David** *(Data Scientist & Leader)* | **Alessandro** *(DPM & AI/ML Dev)* |
| :---: | :--- | :--- | :--- |
| **S07** | Descripción del dataset, diccionarios, preprocesamiento, EDA y baseline. | Definición del problema, Data Product Canvas y wireframes. | Target users, stakeholders, requerimientos y arquitectura inicial. |
| **S08** | Ajustar scripts a APIs externas (TomTom). | Calibrar y serializar modelos ETA/Aforo. | Diseñar esquema OpenAPI/Swagger del backend. |
| **S09** | Pipeline de ingesta en vivo. | Implementar Módulo 3 y Módulo 4. | API REST (FastAPI/Flask) con inferencia en cascada < 2.0 s. |
| **S10** | Persistencia (PostgreSQL/DuckDB). | Validar métricas vs baselines. | Frontend funcional + video demostrativo + `PrototypeReport.md`. |
| **S11** | Subgrafo vial OSM de Lima. | Algoritmo de enrutamiento por riesgo. | Mapa interactivo (Leaflet/Mapbox) de 1.ª/última milla. |
| **S12** | Pruebas de latencia P95 ≤ 2 s. | Casos de estudio + `EvaluationReport.md`. | Usabilidad (CSAT) + presentación S12. |
| **S13** | Contenerización Docker. | Congelar artefactos ML + robustez. | Despliegue cloud con URL pública. |
| **S14** | Auditoría de reproducibilidad. | Secciones técnicas del `FinalReport.pdf`. | Video demo final + Project Page. |
| **S15** | README definitivo + instalación. | Defensa técnica + contribuciones. | Demo en vivo + reflexión de equipo. |

---

## 7. Referencias

* INEI (2025). *Percepción de la Inseguridad Ciudadana y Victimización en Áreas Urbanas de Lima
  Metropolitana*. <https://www.inei.gob.pe/estadisticas/indice-tematico/seguridad-ciudadana/>
* ATU (2026). *Hackathon 2026*. <https://www.gob.pe/institucion/atu/noticias/atu-lanza-la-hackathon-2026>
* ProTransporte & ATU. *Portal de Datos Abiertos del Sistema Integrado de Transporte*.
  <https://sistemas.protransporte.gob.pe/DatosAbiertos/>
* TransMilenio (Bogotá) — *datos abiertos del operador*.
  <https://www.transmilenio.gov.co/datosAbiertos/>
* TomTom Traffic API. <https://docs.tomtom.com/traffic-api/>
* Amazon Science — *Chronos-Bolt* (pronóstico de series). <https://github.com/amazon-science/chronos-forecasting>