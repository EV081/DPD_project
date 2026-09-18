# UrbanSafe AI: Ecosistema de Movilidad Predictiva

## 1. Equipo de Trabajo

* **Integrante 1:** Elmer Jose Manuel Villegas Suarez
* **Integrante 2:** Alessandro Facundo Freed Monzón Gallegos
* **Integrante 3:** Juan David Velo Poma (Líder del grupo)


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
| **S08** | *Examen Parcial* (Sin entrega) | Ajuste de los scripts de extracción y preprocesamiento de APIs externas (TomTom, Meteostat) incorporando las observaciones de la Semana 07. | Calibración inicial de hiperparámetros y serialización preliminar de los artefactos de modelado para tiempo de espera (ETA) y aforo. | Diseño del esquema OpenAPI/Swagger para los endpoints del backend y reestructuración del repositorio Git para las fases de código. |
| **S09** | Desarrollo del Prototipo Base | Automatización del pipeline de ingesta de datos que suministra en tiempo real los predictores meteorológicos y de oferta vehicular. | Implementación en código de la lógica del motor prescriptivo (Módulo 3) y la detección no supervisada de anomalías (Módulo 4). | Construcción de la API REST en FastAPI/Flask para orquestar la inferencia en cascada de los 4 módulos con latencia objetivo $< 2.0\text{s}$. |
| **S10** | **Delivery:** Prototipo Funcional | Configuración del esquema de persistencia (PostgreSQL/DuckDB) para almacenar datos procesados e historial de inferencias para `deliveries/week10/`. | Evaluación y validación de las métricas de desempeño (MAE, F1-Weighted) comparando los modelos frente a los baselines en el prototipo. | Desarrollo de la primera versión del Frontend web funcional, grabación del video demostrativo de la S10 y redacción de `PrototypeReport.md`. |
| **S11** | Eje 2: Módulo Peatonal | Extracción, limpieza y carga del subgrafo vial de Lima desde OpenStreetMap (OSM) enriquecido con atributos de luminaria pública y zonas transitadas. | Desarrollo e implementación del algoritmo de costo para el enrutamiento peatonal prescriptivo nocturno sobre la red en grafo. | Integración del mapa interactivo (Leaflet/Mapbox) en la interfaz gráfica para la visualización de rutas de primera y última milla. |
| **S12** | **Delivery:** Prototipo Refinado y Casos de Estudio | Pruebas de estrés y latencia sobre el pipeline de ingesta ($P_{95} \le 2.0\text{s}$) y optimización de consultas espaciales en el grafo. | Formulación de casos de estudio reales con usuarios, matriz de confusión de reglas, validación de anomalías y redacción de `EvaluationReport.md`. | Pruebas de usabilidad (CSAT), optimización de la interfaz en modo nocturno, actualización de diagramas y elaboración de la presentación de la S12. |
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
* **S11 - S12:** Diseño de la función de costos para el grafo de navegación peatonal nocturna, evaluación con métricas analíticas ($F1\text{-Weighted}$, $PR\text{-AUC}$) y redacción del `EvaluationReport.md` con casos de estudio.
* **S13 - S15:** Consolidación del informe final (`FinalReport.pdf`), declaración de contribuciones del equipo, evaluación de impacto/limitaciones y liderazgo en la presentación pública ante el jurado.

#### 3. Alessandro Facundo Freed Monzón Gallegos — *Data Product Manager & AI/ML Developer*
* **S07:** Identificación y caracterización de Target Users, mapa de stakeholders, elicitación de requerimientos funcionales/no funcionales, diseño de la arquitectura del sistema/diagramas de flujo y elaboración del plan de implementación S07-S15.
* **S08 - S10:** Desarrollo del backend en FastAPI/Flask para la inferencia en cascada de los modelos ($< 2.0\text{s}$), construcción de la primera interfaz de usuario y grabación del video del prototipo.
* **S11 - S12:** Integración del mapa interactivo con conmutación dual (día/noche) para la navegación de primera y última milla, ejecución de pruebas de usabilidad y preparación de la presentación ejecutiva.
* **S13 - S15:** Despliegue en la nube para obtención de la URL pública, producción del Video Demo Final (5–7 min), diseño de la Project Page y preparación de las diapositivas finales.