# Especificación de Requerimientos del Sistema: UrbanSafe AI
**Ecosistema de Movilidad Predictiva en Lima Metropolitana.**

* **Curso:** Desarrollo de Productos de Datos (DS-3022) — UTEC
* **Ciclo:** 2026-II
* **Semana de Entrega:** Semana 07 (23 de septiembre de 2026)
* **Ubicación en Repositorio:** `deliveries/week07/Requirements.md`
* **Equipo de Trabajo:**
  * Elmer Jose Manuel Villegas Suarez
  * Alessandro Facundo Freed Monzón Gallegos
  * Juan David Velo Poma (*Líder de Proyecto*)

## 1. Introducción y Propósito del Documento
El presente documento consolida y actualiza la especificación formal de requerimientos para **UrbanSafe AI**, tomando como base el trabajo presentado en la Semana 05 y refinándolo a partir de la retroalimentación recibida por el equipo docente. Bajo la metodología de ingeniería de productos de datos (*Data Products*), este artefacto formaliza el entendimiento de las necesidades de los usuarios, la caracterización de los actores, la definición funcional del sistema, la calidad de la data de entrada y las restricciones técnicas que delimitan el Producto Mínimo Viable (MVP).

El propósito central de **UrbanSafe AI** es **reducir los tiempos de espera e incertidumbre de los usuarios en estaciones y paraderos** del Sistema Integrado de Transporte de Lima (Metropolitano y Corredores Complementarios), mostrándoles la estimación del nivel de ocupación futuro de los buses para facilitar decisiones rápidas de abordaje o cambio de ruta. Como **funcionalidad secundaria (segundo plus)**, el producto incorpora un módulo de navegación peatonal enfocado en la "primera y última milla", sugiriendo rutas a pie por vías mejor iluminadas y transitadas durante horarios nocturnos.

## 2. Usuarios Objetivo (Target Users)

La solución ha sido estructurada considerando dos perfiles de usuarios claramente identificados:

* **Usuarios del Transporte Público (Pasajeros y Peatones):** Ciudadanos que realizan desplazamientos cotidianos en el sistema integrado de Lima y requieren planificar sus viajes reduciendo la incertidumbre del aforo de los buses y **optimizando sus tiempos de espera en las estaciones y paraderos**; en horario nocturno, también transitando por caminos peatonales con menor exposición a la delincuencia.
* **Planificadores Urbanos y Entidades Reguladoras (ATU y Municipios):** Organismos de gestión del transporte que pueden aprovechar el análisis agregado de la demanda e identificar zonas críticas en la infraestructura de la primera y última milla para la toma de decisiones basada en datos.


## 3. Mapa de Stakeholders y Actores

| Stakeholder / Actor | Categoría | Interés / Responsabilidad en el Producto | Impacto / Poder |
| :--- | :--- | :--- | :--- |
| **Pasajeros y Peatones Urbanos** | Actor Primario | Usuarios finales. Requieren conocer el aforo futuro del bus para reducir tiempos de espera y rutas nocturnas más seguras. | Alto / Alto |
| **Familiares y Red de Apoyo** | Beneficiario Indirecto | Entorno cercano que busca tranquilidad sobre el desplazamiento seguro de sus familiares en tramos peatonales nocturnos. | Medio / Bajo |
| **Autoridad de Transporte Urbano (ATU)** | Aliado Estratégico | Proveedor de datos abiertos de validaciones. Se beneficia de la visibilidad sobre la saturación de unidades y cuellos de botella en la red. | Alto / Medio |
| **Municipalidades Distritales / Serenazgo** | Stakeholder Operativo | Interesados en identificar tramos viales con déficit de alumbrado público, zonas desoladas y puntos ciegos para patrullaje. | Medio / Medio |
| **Conductores y Operadores de Bus** | Stakeholder Indirecto | Se benefician indirectamente por la disminución de aglomeraciones caóticas en estaciones de alta demanda. | Medio / Bajo |
| **Equipo Docente y Evaluadores Académicos** | Sponsor / Evaluador | Cuerpo académico de UTEC (DS-3022) responsable de validar el rigor técnico, arquitectura de datos y desempeño de los modelos. | Alto / Alto |


## 4. Necesidades del Usuario (User Needs)

1. **Saber el nivel de ocupación del bus antes de su llegada:** El usuario necesita conocer con anticipación si la unidad próxima viene con *asientos disponibles*, *para ir de pie* o *saturada*, para decidir oportunamente si aguarda en el andén, busca otro bus o cambia de paradero sin perder tiempo.
2. **Comparar opciones de viaje para minimizar el tiempo de espera:** El usuario necesita visualizar el tiempo estimado de llegada y la ocupación proyectada de la unidad actual frente a las siguientes, permitiéndole tomar la opción que reduzca su tiempo efectivo de espera.
3. **Baja carga cognitiva en consulta móvil:** El usuario requiere una interfaz ligera y legible, diseñada para interactuar con una sola mano en la vía pública y ser interpretada en menos de 5 segundos.
4. **Integridad Física en Horario Nocturno:**  El peatón necesita alternativas de navegación que prioricen vías con iluminación pública funcional, vigilancia y flujo comercial activo durante la primera y última milla de noche, descartando el criterio ciego de "distancia más corta" para reducir el riesgo de la exposición nocturna al delito patrimonial.
5. **Configuración de tolerancia de caminata:** El usuario requiere ajustar qué tanto tiempo o distancia adicional está dispuesto a caminar de noche a cambio de transitar por vías con menor índice de riesgo urbano.


## 5. Historias de Usuario (User Stories & Job Stories)

### User Stories

* **US-01: Estimación Anticipada de Aforo (Núcleo)**
  * **Como** pasajero que se encuentra en un paradero o estación en hora punta,
  * **quiero** consultar la categoría de ocupación proyectada del próximo bus antes de que llegue,
  * **para** decidir si me preparo para subir, espero la siguiente unidad o camino a otro paradero, reduciendo mi tiempo de espera.

* **US-02: Comparativa de Unidades y Tiempos de Llegada**
  * **Como** usuario esperando en el andén,
  * **quiero** comparar el tiempo de llegada y nivel de aforo del bus actual frente al siguiente,
  * **para** elegir la alternativa que me brinde un viaje más cómodo y rápido.

* **US-03: Validar la Predicción (Feedback en Tiempo Real)**
  * **Como** usuario que acaba de abordar el bus,
  * **quiero** confirmar con un toque si la estimación de aforo fue acertada,
  * **para** retroalimentar el sistema y mejorar la precisión del modelo predictivo.

* **US-04: Ruta Peatonal Segura Nocturna (Modo Noche)**
  * **Como** peatón que camina a casa pasadas las 9:00 PM desde la estación,
  * **quiero** recibir la sugerencia de una ruta guiada por calles iluminadas y transitadas,
  * **para** reducir mi exposición a zonas desoladas o con riesgo delictivo.

### Job Stories

* **JS-01: Toma de Decisiones en Andén**
  * **Cuando** estoy en la estación en hora punta y la cola está congestionada,
  * **quiero** ver de inmediato el aforo estimado y la frecuencia de los próximos buses,
  * **para** decidir en menos de 5 segundos la mejor estrategia de abordaje.

* **JS-02: Retorno Seguro a Casa**
  * **Cuando** salgo del transporte público durante la noche y debo caminar hacia mi destino,
  * **quiero** que la aplicación active la ruta con menor índice de riesgo urbano,
  * **para** transitar con tranquilidad por tramos vigilados e iluminados.



## 6. Casos de Uso del Producto de Datos

### UC-01 (Núcleo): Inferencia de Aforo Predictivo Multiclase

| Campo | Detalle |
| :--- | :--- |
| **Actores** | Pasajero / Peatón (Principal), TomTom API, Data ATU, Meteostat API, Modelo ML (Secundarios). |
| **Propósito** | Pronosticar el nivel de ocupación de las unidades próximas para reducir los tiempos de espera del pasajero. |
| **Precondiciones** | Modelo entrenado disponible; APIs de telemetría y meteorología activas. |
| **Disparador** | El usuario selecciona una estación de origen y ruta del SIT. |
| **Flujo Principal** | 1. El usuario consulta el servicio de transporte y paradero de abordaje.<br>2. El pipeline ingesta la velocidad de flujo y congestión de TomTom Traffic API.<br>3. El sistema extrae las métricas meteorológicas horarias (temperatura y precipitación) mediante la librería/API de Meteostat para las coordenadas de la estación.<br>4. El pipeline cruza estas features con el histórico de validaciones horarias de ATU.<br>5. El modelo LightGBM/XGBoost genera las probabilidades para cada categoría de aforo: *Asientos Disponibles*, *De Pie*, *Saturado*.<br>6. La interfaz renderiza el nivel de aforo resultante, su intervalo de confianza y el tiempo de espera estimado. |
| **Flujo Alternativo** | **4a. Falla de Telemetría Externa o Clima:** Si alguna API supera el timeout (2.0s), el backend conmuta a inferencia basada exclusivamente en el histórico horario de validaciones ATU con imputación de valores climáticos medios históricos.<br>**5a.** La interfaz notifica al usuario que la estimación opera en *Modo Histórico*. |
| **Postcondiciones** | Inferencia despachada al frontend y persistida en el log de telemetría interna para monitoreo de drift. |

### UC-02 (Segundo Plus): Optimización Prescriptiva de Ruta Peatonal Segura Nocturna

| Campo | Detalle |
| :--- | :--- |
| **Actores** | Peatón Urbano (Principal), Motor de Grafos OSMnx (Secundario). |
| **Propósito** | Recomendar el camino a pie con menor índice de riesgo urbano durante horarios nocturnos. |
| **Precondiciones** | Grafo vial de Lima Metropolitana cargado con atributos de OSM. |
| **Disparador** | El usuario solicita la ruta a pie hacia o desde una estación en un horario nocturno predeterminado. |
| **Flujo Principal** | 1. El sistema toma las coordenadas geográficas de origen y destino del usuario y valida que el modo noche esté activo.<br>2. El motor de optimización carga el subgrafo local peatonal.<br>3. Se asigna a cada tramo vial un costo ponderado:<br>$$\text{Costo} = \text{Distancia} \times \text{Penalización}(\text{FaltaLuz}, \text{FaltaComercios}, \text{DistanciaComisaria})$$<br>4. Se calcula la trayectoria de costo mínimo mediante algoritmo de Dijkstra/A*.<br>5. La aplicación presenta la ruta sugerida, destacando los tramos protegidos y el tiempo estimado frente a la ruta geométrica tradicional. |
| **Postcondiciones** | Ruta segura visualizada en el mapa interactivo del usuario. |

## 7. Requerimientos Funcionales (RF)

### Módulo Principal: Predicción de Aforo y Tiempos de Espera
* **RF-01 (Inferencia de Aforo Multiclase):** El sistema debe mostrar al usuario el nivel de ocupación esperado para la próxima unidad de transporte, categorizado de forma sencilla en tres estados: Asientos disponibles, Viaje de pie o Bus saturado.
* **RF-02 (Estimación de Tiempo de Llegada):** El sistema debe calcular y mostrar el tiempo estimado de espera (en minutos) para las dos próximas unidades en la estación seleccionada.
* **RF-03 (Sugerencia de Abordaje/Espera):** El sistema debe indicarle expresamente al usuario si la opción más eficiente es abordar la unidad que viene, esperar la siguiente o acudir a un paradero cercano.
* **RF-04 (Módulo de Retroalimentación/Feedback):** La interfaz debe incluir una opción de un solo toque para que el usuario confirme si la estimación de aforo coincidió con la realidad al abordar.
* **RF-05 (Modo Resiliente / Fallback):** Ante la caída de APIs de terceros (TomTom, Meteostat), el sistema debe responder degradando automáticamente a la estimación basada en la matriz histórica de la ATU.

### Módulo Secundario: Enrutamiento Peatonal Nocturno
* **RF-06 (Cálculo del Índice de Riesgo Peatonal):** El sistema debe computar un score de riesgo por tramo vial considerando la presencia de postes de alumbrado, comisarías, comercios abiertos y paraderos según OpenStreetMap.
* **RF-07 (Generación de Ruta Segura):** El sistema debe proporcionar la ruta peatonal prescriptiva permitiendo la comparación directa con la ruta más corta geométrica.
* **RF-08 (Selector de Tolerancia a Caminata):** La aplicación debe permitir al usuario ajustar la distancia o tiempo adicional máximo que acepta caminar a cambio de mayor seguridad y tránsito.


## 8. Requerimientos No Funcionales (RNF)

* **RNF-01 (Precisión Analítica del Modelo):** El modelo de clasificación de aforo debe alcanzar un **Accuracy $\ge 75\%$** y un **$F_1\text{-score Macro} \ge 0.72$** sobre las particiones de prueba.
* **RNF-02 (Latencia Global):** El tiempo de consulta de aforo y generación de rutas no debe superar los **2.0 segundos** en el percentil 95 ($P_{95}$) sobre conexiones móviles 4G/5G.
* **RNF-03 (Disponibilidad del Servicio):** El backend del producto debe mantener una tasa de disponibilidad de al menos **99.0%** dentro del horario operativo del transporte público (05:00 a 23:30 hrs).
* **RNF-04 (Ergonomía y Usabilidad Móvil):** La interfaz gráfica debe diseñarse para operación con una sola mano, contar con paleta visual de alto contraste nocturno y requerir no más de **2 toques** para mostrar el resultado.
* **RNF-05 (Gobernanza y Privacidad de Datos):** La solución no almacenará datos de geolocalización continua ni información identificable del usuario. Las coordenadas de consulta se procesarán de forma efímera cumpliendo la Ley N° 29733 (Ley de Protección de Datos Personales del Perú).


## 9. Contratos de Datos e Ingesta (Data Contracts)

| Fuente de Datos | Tipo / Frecuencia | Criterio de Calidad Aceptable | Uso en UrbanSafe AI |
| :--- | :--- | :--- | :--- |
| **Validaciones ATU** | Batch (Diario/Semanal) | Nulos $< 1\%$, marcas ISO 8601. | Demanda histórica base por estación y hora. |
| **TomTom Traffic API** | Tiempo Real (Streaming/Polling) | Latencia de API $< 800\text{ ms}$, completitud $\ge 98\%$. | Feature de congestión y velocidad proxy de retraso del bus. |
| **OpenStreetMap (OSM)** | Batch (Quincenal) | Geometrías de calles validadas sin nodos huérfanos. | Grafo vial peatonal, luminarias, comisarías y comercios. |
| **API Meteostat / SENAMHI** | Horario / Near Real-Time | Latencia $< 500\text{ ms}$, nulos $< 2\%$. | Variable estacional climática (lluvia/temperatura). |
| **Dataset Sintético Aforo** | Generación por Código | Distribución bimodal de hora punta. | Ground truth inicial para entrenamiento supervisado. |


## 10. Restricciones y Criterios de Aceptación

### Restricciones
1. **Ausencia de Sensores IoT Físicos:** El proyecto no dispone de presupuesto ni autorizaciones para instalar cámaras de visión artificial ni sensores de peso en los buses; el sistema depende íntegramente de datos abiertos, APIs públicas y datos sintéticos.
2. **Límites de Cuota de APIs:** El pipeline debe ceñirse a las restricciones de consumo de la API de TomTom Traffic, a la política de consultas razonables de Meteostat y respetar las directrices de uso del servidor Overpass de OpenStreetMap.
3. **Dependencia de Conectividad Móvil:** La entrega de valor en tiempo real está sujeta a la cobertura de red móvil del operador del usuario en el punto de consulta.
4. **Alcance Priorizado del MVP:** El desarrollo del producto de datos está acotado al calendario semestral del curso DS-3022. **El núcleo (aforo predictivo y reducción del tiempo de espera) tiene prioridad absoluta; el enrutamiento peatonal seguro se implementa únicamente si el núcleo cumple sus criterios de aceptación y queda tiempo de semestre.**


### Criterios de Aceptación y Definición de Terminado (DoD)
| Código | Requisito Relacionado | Criterio de Aceptación (Acceptance Criteria) | Método de Validación |
| :--- | :--- | :--- | :--- |
| **AC-01** | Pipeline de Datos | Integración automatizada de las fuentes ATU, TomTom, OSM y Meteostat dentro del flujo de preprocesamiento sin quiebre de esquema. | Ejecución exitosa de scripts en CI/CD y logs de validación de datos. |
| **AC-02** | Precisión de Aforo | El clasificador multiclase supera $F_1\text{-score} \ge 0.72$ en las tres categorías sobre el set de prueba independiente. | Reporte automatizado de métricas y matriz de confusión en el pipeline. |
| **AC-03** | Estimación de Espera | El sistema entrega el aforo y el tiempo de espera estimado de las próximas unidades en el endpoint de consulta, con exactitud suficiente para recomendar abordar/esperar/cambiar en al menos el 80% de los casos evaluados. | Batería de pruebas unitarias con conjuntos de datos de estaciones y franjas horarias conocidas. |
| **AC-04** | Tiempo de Respuesta | La consulta integral de aforo y tiempo de espera responde en $\le 2.0\text{ s}$ en percentil 95. | Monitoreo sintético de latencia mediante llamadas a los endpoints de la API. |
| **AC-05** | Algoritmo de Grafo  | El motor de enrutamiento genera caminos peatonales con menor score de riesgo que el camino más corto en al menos un 80% de los casos evaluados. | Batería de pruebas unitarias geoespaciales con pares origen-destino conocidos. |
| **AC-06** | Usabilidad de Campo | Al menos el 60% de los usuarios participantes en pruebas controladas declaran que la estimación de aforo les permitió reducir su tiempo de espera percibido. | Encuesta de usabilidad posterior a la prueba y registro de telemetría de interacción. |
