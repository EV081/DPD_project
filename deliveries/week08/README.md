# UrbanSafe AI: Ecosistema de Movilidad Predictiva

## 1. Equipo de Trabajo

* **Integrante 1:** Elmer Jose Manuel Villegas Suarez
* **Integrante 2:** Alessandro Facundo Freed Monzón Gallegos
* **Integrante 3:** Juan David Velo Poma (Líder del grupo)


## 2. Nombre del Producto

**UrbanSafe AI**

## 3. Problema u Oportunidad Inicial

### Contexto y Problemática
En el Sistema Integrado de Transporte de Lima (Metropolitano), los usuarios enfrentan una alta incertidumbre respecto a los tiempos de llegada y el nivel de aforo (asientos disponibles, viaje de pie o bus saturado) de las unidades. Esta carencia de información genera **tiempos de espera ineficientes** en las estaciones y paraderos, viajes incómodos y aglomeraciones severas. **El objetivo general del producto es minimizar esos tiempos de espera**, permitiendo al pasajero decidir oportunamente si aborda, espera el siguiente servicio o cambia de paradero.

A esta ineficiencia en los tiempos de espera se suma una problemática de seguridad ciudadana durante la denominada "primera y última milla" (los tramos a pie que realizan los usuarios desde su origen hacia el paradero y desde la estación hasta su destino final, en horario nocturno). Según el informe técnico del Instituto Nacional de Estadística e Informática (INEI, 2025), la percepción de inseguridad ciudadana en las principales áreas urbanas supera el 85%, registrándose la mayor incidencia de victimización por robos y hurtos en vías públicas desoladas o mal iluminadas durante horarios de alta vulnerabilidad. Las herramientas de navegación convencionales vigentes en el mercado optimizan los trayectos basándose únicamente en la distancia mínima o el menor tiempo hipotético, ignorando el nivel de riesgo peatonal y el estado de ocupación de las unidades de transporte.

### Origen de la Iniciativa y Oportunidad
Evolucionando a partir de los aprendizajes y propuestas de la **Hackathon ATU 2026** y el concepto desarrollado por **Urbyte**, surge **UrbanSafe AI**. El proyecto capitaliza la disponibilidad de portales de datos abiertos (*Open Data*) y servicios de APIs públicas para transformar la gestión tradicional del transporte hacia un **Producto de Datos**.

### Propuesta de Valor del Producto de Datos
UrbanSafe AI aborda estas problemáticas mediante el modelado predictivo del aforo a través de datos proxy (tráfico en tiempo real y registros históricos de la ATU), **estimando también el tiempo de espera de las próximas unidades para reducir la permanencia del usuario en la estación o paradero**. Integra además un algoritmo de enrutamiento por riesgo que prioriza vías iluminadas y seguras sobre la distancia más corta para los desplazamientos a pie.

### Referencias y Fuentes Consultadas:
> 
> * **Instituto Nacional de Estadística e Informática (INEI).** (2025). *Percepción de la Inseguridad Ciudadana y Victimización en Áreas Urbanas de Lima Metropolitana*. Informe Técnico de Seguridad Ciudadana.  
>   [https://www.inei.gob.pe/estadisticas/indice-tematico/seguridad-ciudadana/](https://www.inei.gob.pe/estadisticas/indice-tematico/seguridad-ciudadana/)
> 
> * **Autoridad de Transporte Urbano para Lima y Callao (ATU).** (2026). *ATU lanza la Hackathon 2026 para impulsar soluciones innovadoras en el transporte público: inscripciones ya están habilitadas*. Noticias - Plataforma Única del Estado Peruano.  
>   [https://www.gob.pe/institucion/atu/noticias/1389820-atu-lanza-la-hackathon-2026-para-impulsar-soluciones-innovadoras-en-el-transporte-publico-inscripciones-ya-estan-habilitadas](https://www.gob.pe/institucion/atu/noticias/1389820-atu-lanza-la-hackathon-2026-para-impulsar-soluciones-innovadoras-en-el-transporte-publico-inscripciones-ya-estan-habilitadas)
> 
> * **ProTransporte & Autoridad de Transporte Urbano para Lima y Callao (ATU).** (2026). *Portal Oficial de Datos Abiertos del Sistema Integrado de Transporte*.  
>   [https://sistemas.protransporte.gob.pe/DatosAbiertos/](https://sistemas.protransporte.gob.pe/DatosAbiertos/)

## 4. Dominio Objetivo (Target Domain) y Enfoque de la Solución

### Dominio Objetivo
El proyecto se enmarca analíticamente en la convergencia de dos áreas clave: **Transporte Urbano** y **Ciudades Inteligentes (*Smart Cities*)**, con la **Seguridad Ciudadana** como capa complementaria de la navegación peatonal.

### Enfoque de la Solución
La solución adopta un enfoque predictivo y prescriptivo mediante el uso de algoritmos de Machine Learning. En lugar de ofrecer un diagnóstico puramente descriptivo sobre la ubicación actual de los buses, el sistema infiere el nivel de aforo futuro de las unidades y el tiempo de espera estimado, y sugiere rutas peatonales seguras en función del entorno y la hora del desplazamiento.

### Usuarios Objetivo
La solución ha sido estructurada considerando dos perfiles de usuarios claramente identificados:

* **Usuarios del Transporte Público (Pasajeros y Peatones):** Ciudadanos que realizan desplazamientos cotidianos en el sistema integrado de Lima y requieren planificar sus viajes reduciendo la incertidumbre del aforo de los buses y **optimizando sus tiempos de espera en las estaciones y paraderos**; transitando también por caminos peatonales con menor exposición a la delincuencia.
* **Planificadores Urbanos y Entidades Reguladoras (ATU y Municipios):** Organismos de gestión del transporte que pueden aprovechar el análisis agregado de la demanda e identificar zonas críticas en la infraestructura de la primera y última milla para la toma de decisiones basada en datos.

## 5. Fuente del Dataset (Dataset Source)

> ### Actualización S08: los datos de la ATU ya se recibieron
>
> En S07 se había indicado que los datos de validaciones de la ATU estaban
> "pendientes de respuesta" y se usaba TransMilenio Bogotá como sustituto.
> **En la semana 08 se recibieron y procesaron los datos reales de la ATU.**
> Esta sección describe la fuente definitiva.

### 5.1 Dataset principal — Validaciones ATU 2025

El dataset es el **conjunto de validaciones del Sistema Integrado de Transporte de
Lima correspondiente a 2025 completo**, provisto por la ATU. Cubre **cuatro
subsistemas**:

| Subsistema | Unidad de registro | Filas | Cobertura 2025 |
|------------|-------------------|-------|----------------|
| **Metro Línea 1** | estación | 169,921 | **100%** (26/26 estaciones, 365 días) |
| **Troncales** | estación | 342,703 | **99%** (45/46 estaciones) |
| **Corredores Complementarios** | ruta numerada | 4,532,529 | 63% (12/26 rutas sobre 90%) |
| **Alimentadores (COSAC)** | ruta con nombre | 1,640,842 | 85% (ninguna ruta completa) |

**Total consolidado: 6,685,995 filas** en formato Parquet (~9.8 MB comprimido).

**Grano de registro:** validaciones por *fecha × unidad (estación o ruta) × hora*, con
sentido y tarifado cuando la fuente lo provee.

Fuentes de origen (archivos entregados por la ATU, almacenados en `zip/` y
versionados por ser pesados):

* `OneDrive_2026-09-22.zip` → Metro L1, 12 libros Excel mensuales de 2025 + 2
  shapefiles (que vienen anidados en otro ZIP).
* `4950-2026-02-0012640.xlsx` → troncales, alimentadores, corredores y catálogos de
  paraderos del Metropolitano.

### 5.2 Por qué los datos van en Parquet y no en CSV

El volumen raw son **~294 MB de Excel**. Convertido a Parquet (columnar, comprimido con
Snappy) el consolidado baja a **9.8 MB** y se lee **decenas de veces más rápido**, lo
que hace que los notebooks sean ejecutables de principio a fin. El pipeline es en dos
pasos: `prepare_parquet.py` convierte Excel → Parquet **crudo** (`data_processed/raw/`)
y los notebooks EDA por sistema (troncal / alimentadores / corredores / L1),
modelados tras `week07/.../eda_transmilenio.ipynb`, limpian y analizan escribiendo en `data_processed/clean/`.

### 5.3 Fuentes web complementarias (`data/fuentes/`)

Además de las validaciones, se scrapean fuentes públicas para **contextualizar** la
demanda (horarios, frecuencias, capacidades). Se distingue explícitamente entre fuente
oficial y de terceros:

* **Portal oficial ATU** (`portal.atu.gob.pe/QR/`) — 44 páginas de estación, 19
  servicios, horarios de corredores y paraderos. Nota: el patrón de URL de estación es
  `Metropolitano/<slug>/` (**en singular**) y no existe un índice general navegable.
* **Comunicados oficiales** (`gob.pe`) — frecuencias de la L1 (510 viajes/día L–Sáb,
  292 domingo), capacidad del bus troncal articulado (164 pasajeros: 47 sentados +
  117 de pie), y el **único aforo oficial publicado** por la ATU (L1, dic 2020).
* **OpenStreetMap (OSM, vía BBBike)** — 29,658 POIs, 5,706 elementos de transporte y
  221,410 tramos de red vial. Base del índice de seguridad peatonal.
* **Fuente de terceros `metrolima.info`** — frecuencias de referencia de servicios.
  **Marcada como no oficial (`confianza="baja"`)**; no se usa para dimensionar flota.
* **Prensa/tesis 2023–2025** — `frecuencias_corredores_prensa.csv`: SE08 ≈ 5 min
  (RPP/Infobae/Radio Nacional) y 404 ≈ 15 min (tesis UPC, confianza baja).
* **Auditoría de apps** — `auditoria_apps_frecuencia.csv`: TuRuta/Moovit/Maps no
  entregan headway estático exportable. Detalle en `docs/analisis.md`.

Los endpoints de flota de la ATU (`Total de Flota`, `Flota VS Oferta`) se intentaron
pero agotan el tiempo de conexión; queda como limitación documentada.

### 5.3.1 Fuentes geográficas de recorridos (`data/fuentes/geo/`)

Las validaciones ATU **no traen geometría**. Los mapas Folium del EDA usan estas
fuentes (generadas con `code/scripts/build_trazados.py` y
`download_atu_mapas.py`):

| Sistema | Nodos (estaciones/paraderos) | Trazado (línea) | Origen |
|---------|------------------------------|-----------------|--------|
| **Metro Línea 1** | Shapefile estaciones | Shapefile eje L1 | **MTC–AATE** en Datos Abiertos Perú ([estaciones L1](https://datosabiertos.gob.pe/dataset/mtc-aate-estaciones-de-metro-de-lima-linea-1)); copia local en `data/Estaciones_de_la_Linea1_del_Metro/` y `data/01_linea1/`. Licencia Open Data Commons Attribution. |
| **Metropolitano (troncal + por servicio)** | Match de nombres ATU ↔ OSM (`data/OSM/transporte.csv`) | Relaciones OSM `type=route` + `route=bus` + `network=Metropolitano` (refs `A/B/C/D`, `EX*`, `L`, `SX`, `SXN`) | **OpenStreetMap** vía **Overpass API** ([overpass-turbo.eu](https://overpass-turbo.eu), esquema [`route=bus`](https://wiki.openstreetmap.org/wiki/Tag:route%3Dbus)). Cache: `geo/osm_metropolitano_routes.geojson`. El eje troncal usa Regular **C**; cada servicio ATU se mapea a su `ref` OSM (p. ej. `RegularA`→`A`, `X5`→`EX5`). **No** se usa OSRM “driving” (desvía por calles normales fuera del BRT). Inventario estación↔servicio: portal ATU (`estaciones_por_servicio_atu.csv`). |
| **Corredores complementarios** | `paraderos_cc` (ATU) + orden portal QR | Paraderos ordenados + snap **OSRM** entre paradas consecutivas | ATU (paraderos/orden) + [OSRM](https://project-osrm.org/) para seguir la red vial. Mapas imagen oficiales: portal ATU QR (Rojo/Azul/Morado). |
| **Alimentadores** | Match OSM por nombre (parcial) | Sin LineString por defecto (match por nombre es ruidoso) | OSM + ATU; centroides en el EDA. |

Archivos de salida relevantes: `puntos_*.geojson`, `trazado_troncal.geojson`,
`trazados_metropolitano_servicios.geojson`, `trazados_corredores.geojson`,
`trazado_metro_l1.geojson`, más JPGs oficiales en `geo/mapas_corredores/` y
`geo/mapas_metropolitano/`.

### 5.4 Advertencia metodológica: aforo vs. demanda

Un hallazgo central de esta semana es que **las validaciones NO son un aforo**. Son
**abordajes registrados**: cuando el bus va lleno, el usuario que no logra subir
**no valida**. Esto trunca el conteo exactamente en la punta, que es donde más importa,
y por lo tanto:

* **No se estima ocupación/aforo de buses.** No se generó `estimate_occupancy.py`.
* Tampoco es posible reconstruir pasajeros-por-bus: los datos **no traen `bus_id`, ni
  headway, ni hora individual de abordaje**.
* La ATU no publica una serie de aforo de buses; su único aforo oficial es un dato
  puntual de la L1 de diciembre de 2020.

Lo que **sí** es modelable es la **demanda de abordajes** (validaciones por fecha,
unidad, hora y sentido), y es lo que analizan los notebooks de esta semana.

### 5.5 Calidad y criterios de uso

El EDA detectó heterogeneidad real que condiciona el modelado (detalle en los
notebooks y en `docs/data_dictionary/`):

* **Cobertura desigual:** solo L1 y troncales están esencialmente completos. Alimentadores
  y corredores tienen rutas con 1–5 días sueltos, por lo que los notebooks aplican un
  **umbral de cobertura del 90%** antes de promediar.
* **Sábado ≠ domingo:** la L1 mantiene el nivel del lunes el sábado (ratio 1.01) pero cae
  a 0.55 el domingo; los buses caen a ~0.75 el sábado. Agrupar "fin de semana" como
  sábado+domingo es incorrecto.
* **`TIPO DE DÍA` es redundante** en corredores (coincide 100% con el día de la semana)
  y **no detecta feriados**: el calendario se agrega aparte.
* **La L1 no reporta domingos universitarios**, por lo que las comparaciones entre
  tipos de día se hacen sobre el agregado sin tarifado.

Documentación detallada: guía de ejecución en
[`code/scripts/Guia.md`](./code/scripts/Guia.md), y diccionarios campo por campo en
[`docs/data_dictionary/`](./docs/data_dictionary/) (un archivo por subsistema más un
`DatasetDescriptions.md` de panorama). Los 5 notebooks de EDA están en
[`code/eda/`](./code/eda/), con figuras en [`docs/images/`](./docs/images/). Reporte EDA unificado: [`docs/DataAnalysis.md`](./docs/DataAnalysis.md) (mapas Folium interactivos en el output de las celdas del notebook).



## 6. Plan de Implementación Priorizado y División de Responsabilidades (Semanas 07 - 15)

El desarrollo del producto de datos **UrbanSafe AI** se estructura en cuatro fases estratégicas alineadas estrictamente con las entregas oficiales del curso:

* **Fase 1 — Definición e Integración de Requerimientos (Semana 07):** Formalización de la definición del problema, arquitectura técnica, Data Product Canvas, especificación de requerimientos, análisis exploratorio, prototipo de baja fidelidad y ordenamiento de la entrega en `deliveries/week07/`.
* **Fase 2 — Prototipo Funcional MVP (Semanas 08 a 10):** Perfeccionamiento de los modelos analíticos tras la evaluación parcial, construcción del pipeline de ingesta automatizado, desarrollo del backend con API REST (inferencia en cascada con respuesta $< 2.0\text{s}$) y primer frontend funcional (`deliveries/week10/`).
* **Fase 3 — Prototipo Refinado y Módulo Peatonal (Semanas 11 y 12):** Integración del Eje 2 (Grafo Peatonal de OpenStreetMap), evaluación analítica con métricas avanzadas, pruebas de latencia, usabilidad y documentación de casos de estudio (`deliveries/week12/`).
* **Fase 4 — Despliegue, Demo y Entrega Final (Semanas 13 a 15):** Contenerización en Docker, despliegue en servidor Cloud con URL pública, producción del Video Demo Final (5–7 min), Project Page y presentación pública ante el jurado (`deliveries/week15/`).

> [!NOTE]
> Las definiciones analíticas, arquitecturas (Módulos 1 al 4) y selecciones preliminares de modelos presentadas representan la estrategia base evaluada durante la fase exploratoria. El Feature Store y los algoritmos definitivos permanecerán dinámicos y se someterán a calibraciones, ajuste de hiperparámetros y re-entrenamiento continuo durante la fase de prototipado y pruebas con usuarios.



### Matriz de Planificación y Responsabilidades por Semana

| Semana | Hito / Entregable Oficial | **Elmer Villegas**<br>*(Data Engineer)* | **Juan David Velo**<br>*(Data Scientist & Leader)* | **Alessandro Monzón**<br>*(Data Product Manager & AI/ML Dev)* |
| :---: | :--- | :--- | :--- | :--- |
| **S07** | **Delivery 1:** Integrated Project Definition | Descripción detallada del dataset, diccionario de datos, script de preprocesamiento, análisis exploratorio (EDA) y definición del modelo analítico y baseline. | Revisión de la definición del problema, contexto y propuesta de valor, versión final del Data Product Canvas y bosquejo de wireframes/prototipo de baja fidelidad. | Caracterización de Target Users, stakeholders, necesidades y requerimientos, arquitectura inicial del sistema/diagrama de flujo y plan de implementación priorizado a S15. |
| **S08** | *Examen Parcial* (Sin entrega) | Ajuste de los scripts de extracción y preprocesamiento de APIs externas (TomTom) incorporando las observaciones de la Semana 07. | Calibración inicial de hiperparámetros y serialización preliminar de los artefactos de modelado para tiempo de espera (ETA) y aforo. | Diseño del esquema OpenAPI/Swagger para los endpoints del backend y reestructuración del repositorio Git para las fases de código. |
| **S09** | Desarrollo del Prototipo Base | Automatización del pipeline de ingesta de datos que suministra en tiempo real los predictores meteorológicos y de oferta vehicular. | Implementación en código de la lógica del motor prescriptivo (Módulo 3) y la detección no supervisada de anomalías (Módulo 4). | Construcción de la API REST en FastAPI/Flask para orquestar la inferencia en cascada de los 4 módulos con latencia objetivo $< 2.0\text{s}$. |
| **S10** | **Delivery:** Prototipo Funcional | Configuración del esquema de persistencia (PostgreSQL/DuckDB) para almacenar datos procesados e historial de inferencias para `deliveries/week10/`. | Evaluación y validación de las métricas de desempeño (MAE, F1-Weighted) comparando los modelos frente a los baselines en el prototipo. | Desarrollo de la primera versión del Frontend web funcional, grabación del video demostrativo de la S10 y redacción de `PrototypeReport.md`. |
| **S11** | Eje 2: Módulo Peatonal | Extracción, limpieza y carga del subgrafo vial de Lima desde OpenStreetMap (OSM) enriquecido con atributos de luminaria pública y zonas transitadas. | Desarrollo e implementación del algoritmo de costo para el enrutamiento peatonal prescriptivo sobre la red en grafo. | Integración del mapa interactivo (Leaflet/Mapbox) en la interfaz gráfica para la visualización de rutas de primera y última milla. |
| **S12** | **Delivery:** Prototipo Refinado y Casos de Estudio | Pruebas de estrés y latencia sobre el pipeline de ingesta ($P_{95} \le 2.0\text{s}$) y optimización de consultas espaciales en el grafo. | Formulación de casos de estudio reales con usuarios, matriz de confusión de reglas, validación de anomalías y redacción de `EvaluationReport.md`. | Pruebas de usabilidad (CSAT), optimización de la interfaz de navegación peatonal, actualización de diagramas y elaboración de la presentación de la S12. |
| **S13** | Despliegue Cloud & Docker | Empaquetado y contenerización de la solución completa mediante Docker (Pipeline, Base de Datos, API y Frontend) para asegurar la reproducibilidad. | Congelamiento de artefactos de Machine Learning y ejecución de pruebas de robustez ante caídas o falta de datos en APIs externas. | Despliegue del producto de datos en infraestructura Cloud (AWS/Render/GCP) obteniendo la URL pública operativa de la plataforma. |
| **S14** | Video Demo Final y Project Page | Verificación y auditoría de scripts de reproducibilidad del pipeline y entrenamiento en el repositorio de GitHub. | Redacción de las secciones técnicas finales del informe consolidado (`FinalReport.pdf`), evaluación de sesgos, ética y limitaciones. | Producción, grabación y edición del Video Demo Final (5–7 minutos), construcción de la Project Page (sitio web del proyecto) y diapositivas finales. |
| **S15** | **Delivery 2 Final & Presentación Pública** | Revisión y documentación final del archivo `README.md` principal con instrucciones completas de instalación, configuración y ejecución. | Liderazgo de la defensa técnica del producto ante el jurado, coordinación del documento de contribución del equipo y entrega final en Canvas. | Ensayo de la demostración en vivo del producto interactivo y redacción de la reflexión de trabajo en equipo. |



### Detalle de Responsabilidades Específicas por Rol

#### 1. Elmer Jose Manuel Villegas Suarez — *Data Engineer*
* **S07:** Responsable directo de la descripción técnica del dataset, construcción del diccionario de datos, codificación de scripts de limpieza/preprocesamiento, ejecución del EDA y propuesta de la estrategia analítica de ingeniería de datos.
* **S08 - S10:** Implementación del pipeline de ingesta en vivo para variables de transporte y clima, y estructuración de la base de datos de persistencia en `deliveries/week10/`.
* **S11 - S12:** Procesamiento del subgrafo vial de OpenStreetMap (OSM) y optimización del rendimiento del pipeline ($P_{95} \le 2.0\text{s}$).
* **S13 - S15:** Contenerización integral con Docker, garantía de reproducibilidad total del código/datos y documentación de la infraestructura en el `README.md` principal.

#### 2. Juan David Velo Poma — *Data Scientist & Líder de Proyecto*
* **S07:** Responsable de la redefinición del problema, contexto y propuesta de valor, diseño final del Data Product Canvas (Fase 1) y creación de las maquetas de interfaz/wireframes iniciales.
* **S08 - S10:** Calibración, serialización y validación de los modelos predictivos (ETA, Aforo Multiclase, Decision Engine y Detector de Anomalías), verificando su desempeño frente a los baselines en el prototipo funcional.
* **S11 - S12:** Diseño de la función de costos para el grafo de navegación peatonal, evaluación con métricas analíticas ($F1\text{-Weighted}$, $PR\text{-AUC}$) y redacción del `EvaluationReport.md` con casos de estudio.
* **S13 - S15:** Consolidación del informe final (`FinalReport.pdf`), declaración de contribuciones del equipo, evaluación de impacto/limitaciones y liderazgo en la presentación pública ante el jurado.

#### 3. Alessandro Facundo Freed Monzón Gallegos — *Data Product Manager & AI/ML Developer*
* **S07:** Identificación y caracterización de Target Users, mapa de stakeholders, elicitación de requerimientos funcionales/no funcionales, diseño de la arquitectura del sistema/diagramas de flujo y elaboración del plan de implementación S07-S15.
* **S08 - S10:** Desarrollo del backend en FastAPI/Flask para la inferencia en cascada de los modelos ($< 2.0\text{s}$), construcción de la primera interfaz de usuario y grabación del video del prototipo.
* **S11 - S12:** Integración del mapa interactivo con conmutación dual (día/noche) para la navegación de primera y última milla, ejecución de pruebas de usabilidad y preparación de la presentación ejecutiva.
* **S13 - S15:** Despliegue en la nube para obtención de la URL pública, producción del Video Demo Final (5–7 min), diseño de la Project Page y preparación de las diapositivas finales.
