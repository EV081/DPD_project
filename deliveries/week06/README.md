# UrbanSafe AI: Ecosistema de Movilidad Predictiva

## 1. Equipo de Trabajo

| Rol | Integrante |
|---|---|
| **Data Engineer** | Elmer Jose Manuel Villegas Suarez |
| **ML Engineer** | Alessandro Facundo Freed Monzón Gallegos |
| **Líder del grupo y Data Scientist** | Juan David Velo Poma |


## 2. Nombre Tentativo del Producto

**UrbanSafe AI**

## 3. Problema u Oportunidad Inicial

### Contexto y Problemática
En el Sistema Integrado de Transporte de Lima (Metropolitano y Corredores Complementarios), los usuarios enfrentan una alta incertidumbre respecto a los tiempos de llegada y el nivel de aforo (asientos disponibles, viaje de pie o bus saturado) de las unidades. Esta carencia de información genera **tiempos de espera ineficientes** en las estaciones y paraderos, viajes incómodos y aglomeraciones severas. **El objetivo general del producto es minimizar esos tiempos de espera**, permitiendo al pasajero decidir oportunamente si aborda, espera el siguiente servicio o cambia de paradero.

A esta ineficiencia en los tiempos de espera se suma una problemática de seguridad ciudadana durante la denominada "primera y última milla" (los tramos a pie que realizan los usuarios desde su origen hacia el paradero y desde la estación hasta su destino final, en horario nocturno). Según el informe técnico del Instituto Nacional de Estadística e Informática (INEI, 2025), la percepción de inseguridad ciudadana en las principales áreas urbanas supera el 85%, registrándose la mayor incidencia de victimización por robos y hurtos en vías públicas desoladas o mal iluminadas durante horarios de alta vulnerabilidad. Las herramientas de navegación convencionales vigentes en el mercado optimizan los trayectos basándose únicamente en la distancia mínima o el menor tiempo hipotético, ignorando el nivel de riesgo peatonal y el estado de ocupación de las unidades de transporte.

### Origen de la Iniciativa y Oportunidad
Evolucionando a partir de los aprendizajes y propuestas de la **Hackathon ATU 2026** y el concepto desarrollado por **Urbyte**, surge **UrbanSafe AI**. El proyecto capitaliza la disponibilidad de portales de datos abiertos (*Open Data*) y servicios de APIs públicas para transformar la gestión tradicional del transporte hacia un **Producto de Datos**.

### Propuesta de Valor del Producto de Datos
UrbanSafe AI aborda estas problemáticas mediante el modelado predictivo del aforo a través de datos proxy (tráfico en tiempo real y registros históricos de la ATU), **estimando también el tiempo de espera de las próximas unidades para reducir la permanencia del usuario en la estación o paradero**. Integra además un algoritmo de enrutamiento por riesgo que prioriza vías iluminadas y seguras sobre la distancia más corta para los desplazamientos a pie en horario nocturno.

### Referencias y Fuentes Consultadas:
> 
> * **Instituto Nacional de Estadística e Informática (INEI).** (2025). *Percepción de la Inseguridad Ciudadana y Victimización en Áreas Urbanas de Lima Metropolitana*. Informe Técnico de Seguridad Ciudadana.  
>   [https://www.inei.gob.pe/estadisticas/indice-tematico/seguridad-ciudadana/](https://www.inei.gob.pe/estadisticas/indice-tematico/seguridad-ciudadana/)
> 
> * **Autoridad de Transporte Urbano para Lima y Callao (ATU).** (2026). *ATU lanza la Hackathon 2026 para impulsar soluciones innovadoras en el transporte público: inscripciones ya están habilitadas*. Noticias - Plataforma Única del Estado Peruano.  
>   [https://www.gob.pe/institucion/atu/noticias/atu-lanza-la-hackathon-2026](https://www.gob.pe/institucion/atu/noticias/atu-lanza-la-hackathon-2026)
> 
> * **ProTransporte & Autoridad de Transporte Urbano para Lima y Callao (ATU).** (2026). *Portal Oficial de Datos Abiertos del Sistema Integrado de Transporte*.  
>   [https://sistemas.protransporte.gob.pe/DatosAbiertos/](https://sistemas.protransporte.gob.pe/DatosAbiertos/)

## 4. Dominio Objetivo (Target Domain) y Enfoque de la Solución

### Dominio Objetivo
El proyecto se enmarca analíticamente en la convergencia de dos áreas clave: **Transporte Urbano** y **Ciudades Inteligentes (*Smart Cities*)**, con la **Seguridad Ciudadana** como capa complementaria del modo nocturno.

### Enfoque de la Solución
La solución adopta un enfoque predictivo y prescriptivo mediante el uso de algoritmos de Machine Learning. En lugar de ofrecer un diagnóstico puramente descriptivo sobre la ubicación actual de los buses, el sistema infiere el nivel de aforo futuro de las unidades y el tiempo de espera estimado, y, para desplazamientos nocturnos, sugiere rutas peatonales seguras en función del entorno y la hora del desplazamiento.

### Usuarios Objetivo
La solución ha sido estructurada considerando dos perfiles de usuarios claramente identificados:

* **Usuarios del Transporte Público (Pasajeros y Peatones):** Ciudadanos que realizan desplazamientos cotidianos en el sistema integrado de Lima y requieren planificar sus viajes reduciendo la incertidumbre del aforo de los buses y **optimizando sus tiempos de espera en las estaciones y paraderos**; en horario nocturno, también transitando por caminos peatonales con menor exposición a la delincuencia.
* **Planificadores Urbanos y Entidades Reguladoras (ATU y Municipios):** Organismos de gestión del transporte que pueden aprovechar el análisis agregado de la demanda e identificar zonas críticas en la infraestructura de la primera y última milla para la toma de decisiones basada en datos.

## 5. Fuente del Dataset (Dataset Source)

> **Nota sobre los datos de demanda (importante).** En esta semana aún no se cuenta con el dataset de validaciones de la **ATU**: la solicitud de datos ya fue cursada y se encuentra **pendiente de respuesta**. Para no bloquear el avance del proyecto, mientras tanto se está utilizando como fuente equivalente un **dataset de Validaciones Troncales del TransMilenio de Bogotá** (sistema troncal de buses de la misma naturaleza), descargado del Portal de Datos Abiertos de TransMilenio:  
> [https://www.transmilenio.gov.co/datosAbiertos/](https://www.transmilenio.gov.co/datosAbiertos/)

Para demostrar que los datos son accesibles, ricos y útiles para el desarrollo de un Producto de Datos, el proyecto combina fuentes de datos abiertos (Open Data / APIs) con un conjunto de datos sintéticos:

* **Validaciones ATU (ProTransporte):** Fuente primaria prevista para la demanda base, ya solicitada y pendiente de respuesta. Corresponde al portal de datos abiertos que provee el conteo de validaciones por hora, ruta y estación del Metropolitano de Lima. Mientras se obtiene, se usa el [dataset de TransMilenio Bogotá](https://www.transmilenio.gov.co/datosAbiertos/) (validaciones troncales por estación, día y hora) y los archivos geoespaciales de estaciones y trazados.
* **TomTom Traffic Flow API:** Telemetría de velocidad y congestión en tiempo real obtenida mediante peticiones HTTP a la [TomTom Traffic API](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/introduction) utilizando una API Key sobre las coordenadas de las rutas del transporte público. Alimenta tanto la predicción de aforo como la estimación del tiempo de espera.
* **OpenStreetMap (OSM):** Información geoespacial de infraestructura (luminarias, comisarías, zonas comerciales y paraderos) extraída mediante la API de Overpass; base del índice de seguridad peatonal del **modo noche**.
* **Meteostat (Clima Histórico y en Tiempo Real):** Datos meteorológicos de temperatura y precipitación a través de [Meteostat](https://meteostat.net/en/) (API pública y librería Python), reemplazando pendiente el conjunto SENAMHI previamente considerado. Se usan para cruzar el impacto meteorológico con la demanda de transporte y las esperas.
* **Dataset Sintético (Python Script):** Muestra simulada de 6 meses generada mediante un script en Python que inyecta ruido estadístico sobre las distribuciones de referencia para simular niveles de aforo (*Asientos*, *De pie*, *Lleno*), garantizando volumen suficiente para el entrenamiento inicial del modelo.

Para revisar los scripts de extracción, el flujo de ingesta y los detalles del script de datos sintéticos, consulte la [Guía Técnica de Adquisición de Datos](./acquisition.md). La estructura detallada de las variables se encuentra en el [Diccionario de Datos](./data_dictionary.csv) y la muestra de trabajo en [`data/sample.csv`](./data/sample.csv).

## 6. Avances de la Semana

Durante la **semana 06** del curso se realizó el análisis exploratorio de los datos seleccionados y se propuso la componente analítica/modelamiento del Data Product:

* **Análisis Exploratorio de Datos (EDA):** reporte [`docs/DataAnalysis.md`](./docs/DataAnalysis.md) con la comprensión de los datos (estructura, granularidad y perfiles de nulos de las 3 fuentes: validaciones TransMilenio, clima Meteostat y OpenStreetMap), decisiones de preprocesamiento (tipado, consolidación de celdas duplicadas, corrección de festivos con `Tipo_Dia_ok`, política de nulos y feature engineering: `Pax_bus`, `Ocupacion_pk`, `Franja`, buffers de 500 m sobre OSM), distribuciones y relaciones relevantes (estacionalidad semanal/horaria, concentración geográfica, saturación estructural: 133/153 estaciones sobre capacidad en pico), hallazgos iniciales (el clima es un efecto despreciable, la temperatura actúa como proxy de la hora, la oferta sigue a la demanda, etc.), sesgos potenciales y limitaciones (proxy TransMilenio->Lima, lluvia solo ligera, una sola estación climática, OSM colaborativo).
* **Selección de Modelos:** reporte [`docs/ModelSelection.md`](./docs/ModelSelection.md) con 4 módulos del Eje 1; para cada uno se identifican entradas y salidas esperadas, se justifica el método seleccionado y se define al menos un baseline alternativo:
  * **Módulo 1 — ETA (tiempo de espera):** *Decision Tree Regressor* (baseline: Ridge) -> MAE, RMSE, R².
  * **Módulo 2 — Aforo multiclase (Asientos/De pie/Saturado):** *Random Forest Classifier* (baseline: Zero-R) -> ROC-AUC One-vs-Rest, F1-weighted, Balanced Accuracy.
  * **Módulo 3 — Recomendador prescriptivo:** *Utility Decision Tree* (baseline: reglas condicionales estáticas) -> Matched Decision Accuracy, ROC-AUC macro.
  * **Módulo 4 — Detección de anomalías espacio-temporales:** *Isolation Forest* (baseline: umbral Z-Score/IQR) → PR-AUC, ROC-AUC sintético, Precision@K.
* **Modelamiento preliminar:** notebook [`code/model/Modelamiento_Preeliminar.ipynb`](./code/model/Modelamiento_Preeliminar.ipynb) que define los targets (`Target_ETA_Min`, `Target_Aforo`), implementa el feature engineering, divide en train/test y entrena/evalúa los modelos seleccionados.
* **Datos procesados:** se generaron los CSV utilizados en el análisis: `data/transmilenio/dataset.csv`, `data/transmilenio/dataset_limpio.csv`, `data/transmilenio/dataset_final_clima_transmilenio.csv`, series de clima en `data/clima/` y features de entorno urbano OSM (`dataset_osm_estaciones_limpio.csv`), con sus diccionarios de datos en `data_sample/`.
* **Reproducibilidad:** notebooks de análisis en `code/eda/`, scripts de ingesta en `code/download/` (con guía en `code/download/Guia.md`) y figuras del reporte en `docs/images/`.
