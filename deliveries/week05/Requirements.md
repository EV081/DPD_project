# Requerimientos del Sistema: UrbanSafe AI
**Ecosistema de Movilidad Predictiva y Segura en Lima Metropolitana**

* **Curso:** Desarrollo de Productos de Datos (DS-3022) — UTEC
* **Ciclo:** 2026-II
* **Semana de Entrega:** Semana 05 (9 de septiembre de 2026)
* **Ubicación en Repositorio:** `deliveries/week05/Requirements.md`
* **Equipo de Trabajo:**
  * Elmer Jose Manuel Villegas Suarez
  * Alessandro Facundo Freed Monzón Gallegos
  * Juan David Velo Poma (*Líder de Proyecto*)

---

## 1. Introducción y Propósito del Documento
El presente documento consolida la actividad de elicitación, análisis y especificación de requerimientos para el desarrollo de **UrbanSafe AI**. Siguiendo las directrices metodológicas de ingeniería de software orientada a productos de datos (*Data Products*), este artefacto formaliza las necesidades de los usuarios y stakeholders, define los comportamientos predictivos y prescriptivos del sistema, y fija las restricciones operativas y criterios de aceptación para el MVP (*Minimum Viable Product*).

---

## 2. Mapa de Stakeholders y Actores

| Stakeholder / Actor | Categoría | Interés / Responsabilidad en el Producto de Datos | Impacto / Poder |
| :--- | :--- | :--- | :--- |
| **Pasajeros / Peatones Urbanos** | Actor Primario | Usuarios cotidianos del Metropolitano y Corredores (estudiantes y trabajadores en turnos nocturnos). Requieren visibilidad del aforo del bus y caminos peatonales protegidos contra el delito patrimonial. | Alto / Alto |
| **Familiares y Red de Apoyo** | Beneficiario Indirecto | Personas del entorno de los usuarios que valoran la reducción del riesgo e incertidumbre durante los tramos a pie hacia o desde las estaciones. | Medio / Bajo |
| **Autoridad de Transporte Urbano (ATU)** | Aliado Estratégico / Regulador | Proveedor de la data base (*Open Data*). Se beneficia del análisis consolidado de demanda y la visibilidad de cuellos de botella en la red del SIT. | Alto / Medio |
| **Municipalidades Distritales y Serenazgo** | Stakeholder Operativo | Gobiernos locales interesados en identificar segmentos viales con déficit de alumbrado público, zonas de baja densidad comercial y puntos ciegos para patrullaje. | Medio / Medio |
| **Conductores y Operadores de Bus** | Stakeholder Indirecto | Personal de operación que experimenta demoras en estaciones con aglomeraciones desbordadas y abordajes caóticos. | Medio / Bajo |
| **Equipo Docente y Evaluadores Académicos** | Sponsor / Evaluador | Cuerpo académico de la UTEC responsable de validar el rigor técnico, viabilidad analítica, gobernanza de datos y reproducibilidad del MVP. | Alto / Alto |

---

## 3. Necesidades del Usuario (User Needs)

1. **Reducción de la Incertidumbre en Tiempo Real:** El usuario necesita saber el nivel de ocupación futuro de la unidad antes de llegar al andén, eliminando el estrés de esperar buses saturados o perder tiempo innecesario en paraderos inseguros.
2. **Priorización de la Integridad Física sobre la Distancia Geométrica:** El peatón necesita alternativas de navegación que prioricen vías con iluminación pública funcional, vigilancia y flujo comercial activo durante la primera y última milla, descartando el criterio ciego de "distancia más corta".
3. **Baja Carga Cognitiva en Entornos Críticos:** El usuario requiere interfaces simples y legibles con una sola mano en pantallas móviles, diseñadas para ser interpretadas en menos de 5 segundos sin exponer su teléfono de forma prolongada en la vía pública.
4. **Capacidad de Ajuste Personalizado:** El sistema debe permitir balancear la aversión al riesgo del usuario (minutos o metros adicionales tolerables para caminar por calles seguras frente al trayecto habitual).

---

## 4. Historias de Usuario (User Stories & Job Stories)

### User Stories (Formato INVEST)

* **US-01: Estimación Anticipada de Aforo**
  * **Como** estudiante o trabajador que sale en hora punta de la universidad o trabajo,
  * **quiero** consultar la categoría pronosticada de ocupación (*Asientos disponibles*, *De pie* o *Saturado*) del bus antes de que arribe al paradero,
  * **para** decidir oportunamente si abordo esa unidad, aguardo el siguiente servicio o cambio de andén.

* **US-02: Enrutamiento Peatonal Seguro (Última Milla)**
  * **Como** peatón que transita tarde en la noche desde la estación hasta mi hogar,
  * **quiero** que la plataforma me trace la ruta a pie calculada en función de vías iluminadas y transitadas,
  * **para** mitigar mi exposición a asaltos o zonas desoladas en el trayecto final.

* **US-03: Retroalimentación y Confirmación de Estado**
  * **Como** usuario que acaba de abordar una unidad o finalizar su caminata,
  * **quiero** validar con un único toque si la predicción de aforo y la sensación de seguridad fueron correctas,
  * **para** contribuir a la retroalimentación y calibración continua del modelo de machine learning.

### Job Stories (Enfoque en Contexto y Resultado)

* **JS-01: Planificación Proactiva en Horario Nocturno**
  * **Cuando** salgo del Metropolitano pasadas las 9:00 PM y debo caminar hacia mi destino,
  * **quiero** acceder a una ruta de navegación guiada por índice de riesgo urbano,
  * **para** caminar con tranquilidad y evitar arterias reportadas como peligrosas o desoladas.

---

## 5. Casos de Uso del Producto de Datos

### UC-01: Inferencia de Aforo Predictivo Multiclase

| Campo | Detalle |
| :--- | :--- |
| **Actores** | Pasajero / Peatón (Principal), TomTom API, Data ATU, Meteostat API, Modelo ML (Secundarios). |
| **Propósito** | Pronosticar el nivel de ocupación de las unidades próximas. |
| **Precondiciones** | Modelo entrenado disponible; APIs de telemetría y meteorología activas. |
| **Disparador** | El usuario selecciona una estación de origen y ruta del SIT. |
| **Flujo Principal** | 1. El usuario consulta el servicio de transporte y paradero de abordaje.<br>2. El pipeline ingesta la velocidad de flujo y congestión de TomTom Traffic API.<br>3. El sistema extrae las métricas meteorológicas horarias (temperatura y precipitación) mediante la librería/API de Meteostat para las coordenadas de la estación.<br>4. El pipeline cruza estas features con el histórico de validaciones horarias de ATU.<br>5. El modelo LightGBM/XGBoost genera las probabilidades para cada categoría de aforo: *Asientos Disponibles*, *De Pie*, *Saturado*.<br>6. La interfaz renderiza el nivel de aforo resultante y su intervalo de confianza. |
| **Flujo Alternativo** | **4a. Falla de Telemetría Externa o Clima:** Si alguna API supera el timeout (2.0s), el backend conmuta a inferencia basada exclusivamente en el histórico horario de validaciones ATU con imputación de valores climáticos medios históricos.<br>**5a.** La interfaz notifica al usuario que la estimación opera en *Modo Histórico*. |
| **Postcondiciones** | Inferencia despachada al frontend y persistida en el log de telemetría interna para monitoreo de drift. |

### UC-02: Optimización Prescriptiva de Ruta Peatonal Segura

| Campo | Detalle |
| :--- | :--- |
| **Actores** | Peatón Urbano (Principal), Motor de Grafos OSMnx (Secundario). |
| **Propósito** | Recomendar el camino a pie con menor índice de riesgo urbano. |
| **Precondiciones** | Grafo vial de Lima Metropolitana cargado con atributos de OSM. |
| **Disparador** | El usuario solicita la ruta a pie hacia o desde una estación. |
| **Flujo Principal** | 1. El sistema toma las coordenadas geográficas de origen y destino del usuario.<br>2. El motor de optimización carga el subgrafo local peatonal.<br>3. Se asigna a cada tramo vial un costo ponderado:<br>$$\text{Costo} = \text{Distancia} \times \text{Penalización}(\text{FaltaLuz}, \text{FaltaComercios}, \text{DistanciaComisaria})$$<br>4. Se calcula la trayectoria de costo mínimo mediante algoritmo de Dijkstra/A*.<br>5. La aplicación presenta la ruta sugerida, destacando los tramos protegidos y el tiempo estimado frente a la ruta geométrica tradicional. |
| **Postcondiciones** | Ruta segura visualizada en el mapa interactivo del usuario. |

---

## 6. Requerimientos Funcionales (Functional Requirements)

* **RF-01 (Inferencia de Aforo Multiclase):** El motor predictivo debe clasificar el aforo futuro del bus en tres clases discretas (*Asientos disponibles*, *Viaje de pie*, *Bus saturado*) utilizando variables proxy de tráfico, clima (Meteostat), estacionalidad y datos históricos.
* **RF-02 (Cálculo del Índice de Riesgo Peatonal):** El servicio analítico debe computar un score de riesgo por arista en el grafo vial a partir de atributos geoespaciales (presencia y distancia a luminarias, comisarías, paraderos y comercios activos según OpenStreetMap).
* **RF-03 (Generación de Rutas Prescriptivas):** El sistema debe proporcionar la ruta peatonal óptima en términos de seguridad urbana, permitiendo la comparación directa con la ruta de distancia mínima geométrica.
* **RF-04 (Configuración de Tolerancia de Caminata):** La solución debe ofrecer un selector de parámetros para que el usuario determine la distancia adicional máxima que está dispuesto a recorrer a cambio de menor exposición al riesgo.
* **RF-05 (Captura de Etiquetas Reales / Feedback):** La interfaz debe incluir un módulo liviano para registrar la validación del aforo observado por el pasajero al subir al bus y reportar tramos con luminarias averiadas.
* **RF-06 (Modo Degradado / Fallback):** Ante cortes de servicio o cuotas agotadas de APIs externas (TomTom, Meteostat), el sistema debe responder degradando automáticamente a la estimación basada en la matriz histórica de validaciones ATU con imputación estacional.

---

## 7. Requerimientos No Funcionales (Non-Functional Requirements)

* **RNF-01 (Rendimiento Analítico del Modelo):** El modelo predictivo de aforo debe alcanzar un desempeño mínimo de **$F_1\text{-score Macro} \ge 0.72$** y un **Accuracy $\ge 75\%$** evaluado sobre particiones temporales retenidas (*hold-out split*).
* **RNF-02 (Latencia de Consulta en Extremo a Extremo):** El tiempo de cómputo para la inferencia de aforo y el cálculo de la ruta peatonal no debe exceder **2.0 segundos** en el percentil 95 ($P_{95}$) bajo condiciones estándar de red móvil (4G/5G).
* **RNF-03 (Disponibilidad y Resiliencia del Servicio):** La API y la interfaz deben garantizar una tasa de disponibilidad (*uptime*) de al menos **99.0%** durante el horario operativo del transporte público (05:00 a 23:30 horas).
* **RNF-04 (Usabilidad y Ergonomía Móvil):** El diseño de la interfaz móvil debe contemplar uso a una mano, contar con paletas de alto contraste para visibilidad nocturna y requerir no más de dos toques para consultar el estado del viaje.
* **RNF-05 (Privacidad y Anonimización de Datos):** La solución no almacenará datos de geolocalización continua ni identidades personales en sus bases operativas. Las coordenadas de navegación se procesarán de manera efímera, cumpliendo con los estándares de privacidad y la Ley N° 29733 (Ley de Protección de Datos Personales del Perú).

---

## 8. Contratos de Datos e Ingesta (Data Contracts)

| Variable / Flujo | Fuente de Origen | Frecuencia de Ingesta | Criterio de Calidad Aceptable | Uso Analítico en UrbanSafe AI |
| :--- | :--- | :--- | :--- | :--- |
| **Validaciones por Estación** | Portal de Datos Abiertos ATU / ProTransporte | Batch (Diario / Semanal) | Valores nulos $< 1\%$; marcas temporales consistentes en formato ISO 8601. | Demanda base e histórica para predicción de aforo. |
| **Flujo y Congestión Vial** | TomTom Traffic Flow API | Tiempo Real (Streaming/Polling por evento) | Latencia de API $< 800\text{ ms}$; completitud de coordenadas $\ge 98\%$. | Feature dinámica proxy del retraso y acumulación de pasajeros. |
| **Infraestructura Geoespacial** | OpenStreetMap (API Overpass) | Batch (Quincenal / Mensual) | Geometrías de calles cerradas y validadas; sin nodos huérfanos. | Construcción de grafos peatonales y cálculo de riesgo. |
| **Condiciones Meteorológicas** | Meteostat API / Python Library (Estaciones Lima / SPIM) | Batch horario / Inferencia Near Real-Time | Latencia de consulta $< 500\text{ ms}$; nulos $< 2\%$ en temperatura y precipitación horaria. | Feature estacional correlacionada con variaciones repentinas de demanda y caminabilidad. |
| **Aforo Calibrado (Dataset Sintético)** | Generador Estadístico Python | Proceso de Entrenamiento | Distribuciones bimodales consistentes con las horas punta de Lima. | Ground truth inicial para entrenamiento supervisado. |

---

## 9. Supuestos y Restricciones del Proyecto

### Supuestos (Assumptions)
1. **Validez del Proxy de Tráfico:** Se asume una correlación estadística alta y positiva entre los cuellos de botella de velocidad vehicular reportados por telemetría y el retraso en la frecuencia de buses, impactando directamente en la acumulación de usuarios en las estaciones.
2. **Cobertura Suficiente de OpenStreetMap:** Se asume que las principales zonas de cobertura del Metropolitano y Corredores en Lima Metropolitana cuentan con etiquetas vigentes sobre alumbrado público y comercios en OSM.
3. **Representatividad Meteorológica Local:** Se asume que las observaciones horarias agregadas por Meteostat (estaciones meteorológicas formales e interpolaciones puntuales para Lima) reflejan adecuadamente las condiciones climáticas que alteran los patrones de viaje de los peatones.
4. **Consistencia Estacional de la Demanda:** Se asume que los patrones de movilidad post-pandemia presentan regularidad cíclica por franjas horarias y días laborales.

### Restricciones (Constraints)
1. **Ausencia de Sensores IoT Físicos:** El proyecto no dispone de presupuesto ni autorizaciones para instalar cámaras de visión artificial ni sensores de peso en los buses; el sistema depende íntegramente de datos abiertos, APIs públicas y datos sintéticos.
2. **Límites de Cuota de APIs:** El pipeline debe ceñirse a las restricciones de consumo de la API de TomTom Traffic, a la política de consultas razonables de Meteostat y respetar las directrices de uso del servidor Overpass de OpenStreetMap.
3. **Dependencia de Conectividad Móvil:** La entrega de valor en tiempo real está sujeta a la cobertura de red móvil del operador del usuario en el punto de consulta.
4. **Horizonte Temporal Académico:** El desarrollo del producto de datos está acotado al calendario semestral del curso DS-3022, priorizando un MVP funcional centrado en rutas y estaciones clave.

---

## 10. Criterios de Aceptación y Definición de Terminado (DoD)

| Código | Requisito Relacionado | Criterio de Aceptación (Acceptance Criteria) | Método de Validación |
| :--- | :--- | :--- | :--- |
| **AC-01** | Pipeline de Datos | Integración automatizada de las fuentes ATU, TomTom, OSM y Meteostat dentro del flujo de preprocesamiento sin quiebre de esquema. | Ejecución exitosa de scripts en CI/CD y logs de validación de datos. |
| **AC-02** | Precisión de Aforo | El clasificador multiclase supera $F_1\text{-score} \ge 0.72$ en las tres categorías sobre el set de prueba independiente. | Reporte automatizado de métricas y matriz de confusión en el pipeline. |
| **AC-03** | Algoritmo de Grafo | El motor de enrutamiento genera caminos peatonales con menor score de riesgo que el camino más corto en al menos un 80% de los casos evaluados. | Batería de pruebas unitarias geoespaciales con pares origen-destino conocidos. |
| **AC-04** | Tiempo de Respuesta | La consulta integral de ruta y aforo responde en $\le 2.0\text{ s}$ en percentil 95. | Monitoreo sintético de latencia mediante llamadas a los endpoints de la API. |
| **AC-05** | Usabilidad de Campo | Al menos el 60% de los usuarios participantes en pruebas controladas de campo optan por la ruta prescriptiva sobre el camino mínimo. | Encuesta de usabilidad posterior a la prueba y registro de telemetría de interacción. |