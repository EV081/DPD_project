# Selección y Justificación de Modelos: UrbanSafe AI

* **Curso:** Desarrollo de Productos de Datos (DS-3022) — UTEC
* **Ciclo:** 2026-II
* **Entrega:** Semana 06 — Exploratory Data Analysis and Model Selection
* **Ubicación en Repositorio:** `deliveries/week06/ModelSelection.md`


## 1. Visión General y Continuidad del Producto de Datos

El presente documento formaliza la selección, justificación y estrategia de evaluación de los modelos analíticos que componen el núcleo operante de **UrbanSafe AI**. Esta selección mantiene una continuidad directa y estricta con los requerimientos definidos en la Semana 05 (`Requirements.md`) y el *Data Product Canvas*:

1. **Núcleo Primario:** Reducir la incertidumbre y los tiempos de espera del pasajero en las estaciones y paraderos del Sistema Integrado de Transporte (SIT) mediante la predicción de aforo y recomendación de abordaje (RF-01, RF-02, RF-03).

2. **Segundo Plus:** Garantizar un enrutamiento peatonal seguro para desplazamientos nocturnos en la primera y última milla, incorporando por primera vez la **Percepción de Urbanización** (*Streetscape Perception*) junto a variables geoespaciales de infraestructura (RF-06, RF-07, RF-08).

Siguiendo las recomendaciones académicas del curso, la arquitectura prioriza modelos analíticos altamente explicables, eficientes en términos computacionales y de baja latencia, garantizando que el producto no dependa de "cajas negras" complejas o infraestructura costosa sin justificación operativa.


## 2. Definición, Justificación y Comparación de Modelos

En esta sección se detalla la construcción teórica, la fundamentación de las características seleccionadas y el diseño analítico de los cuatro módulos del Eje 1, definiendo para cada uno su modelo baseline, el modelo analítico elegido, la estrategia de mantenimiento continuo y el pipeline de uso en producción.

### Módulo 1: Estimador Continuo del Tiempo de Espera (ETA)

* **Propósito del Módulo:** Predecir de manera continua el tiempo en minutos que tardará en arribar la siguiente unidad vehicular a una estación o paradero determinado, reduciendo la incertidumbre del usuario en la plataforma.

* **Construcción Analítica del Target ($y_{ETA}$):**
  El target continuo $\text{Target\_ETA\_Min}$ se formula analíticamente a partir de la frecuencia de despacho observada y se valida contra el intervalo entre buses ($Headway$):
  $$\text{Target\_ETA\_Min} = \begin{cases} \frac{60.0}{\text{Frecuencia}} & \text{si Frecuencia} > 0 \\ \text{Headway\_Min} & \text{en otro caso} \end{cases}$$

* **Variables de Entrada Evaluadas ($X$):**
  * *Espacio-Temporales:* `Hora`, `Es_Habil`, `Troncal_code`, `Franja_code`, `DiaSemana_code`.
  * *Oferta Operativa:* `Cap_total`, `Frecuencia`, `N_Rutas`, `Sin_Oferta`, `sin_capacidad`.
  * *Inercia de Demanda:* Lags históricos de validaciones (`val_lag_1h`, `val_lag_24h`) y promedio móvil (`val_roll_mean_3h`).

* **Justificación de Selección de Features:**
  Estas variables se evaluaron y seleccionaron debido a la alta correlación directa entre el volumen reciente de pasajeros (`val_roll_mean_3h`) y las desviaciones sobre la oferta programada (`Frecuencia`). La inclusión de la franja horaria y la troncal permite al modelo ajustar los tiempos teóricos según la congestión histórica observada en cada corredor.

* **Modelo Baseline de Referencia:** **Regresión Ridge**.
  * *Justificación del Baseline:* Representa el enfoque tradicional de los sistemas de transporte, calculando el ETA a partir de la división estática entre la hora del día y la oferta teórica programada.

* **Modelo Seleccionado:** **Decision Tree Regressor**.
  * *Justificación Técnica y Explicabilidad:* Se elige un Árbol de Regresión sobre arquitecturas complejas debido a la exigencia de alta explicabilidad y baja latencia de la asignatura. El modelo segmenta el espacio multidimensional mediante reglas condicionales transparentes ($IF\dots THEN$). Permite mapear de forma no lineal cómo la interacción entre la hora y la troncal afecta el tiempo de llegada, garantizando una inferencia ultrarrápida en producción.

* **Métricas Principales de Evaluación:** **MAE** (*Mean Absolute Error*), **RMSE** (*Root Mean Squared Error*) y **$R^2$ Score**.
  * *Justificación de Métricas:* El MAE mide la desviación promedio en minutos reales que experimentará el usuario en la estación (fácilmente interpretable). El RMSE penaliza con mayor severidad los errores grandes (p. ej., predecir 3 minutos cuando el bus tarda 25), lo cual es crítico para evitar la pérdida de confianza del usuario. El $R^2$ permite evaluar qué proporción de la varianza del tiempo de llegada está siendo capturada por las variables espacio-temporales.

---

### Módulo 2: Predictor Multiclase de Aforo Vehicular

* **Propósito del Módulo:** Clasificar el nivel de ocupación con el que llegará el bus a la estación, permitiendo al usuario anticipar si viajará sentado, de pie o si la unidad vendrá saturada.

* **Construcción Analítica del Target ($y_{Aforo}$):**
  Se construye a partir del Índice de Ocupación Físico ($\text{Indice\_Ocupacion} = \frac{\text{Validaciones}}{\text{Cap\_total}}$), discretizado en tres clases ordinales de confort:
  $$\text{Target\_Aforo} = \begin{cases} 0 \text{ (Bajo / Asientos Disponibles)} & \text{si } \text{Indice\_Ocupacion} \le 0.40 \\ 1 \text{ (Medio / Viaje de Pie)} & \text{si } 0.40 < \text{Indice\_Ocupacion} \le 0.85 \\ 2 \text{ (Alto / Bus Saturado)} & \text{si } \text{Indice\_Ocupacion} > 0.85 \end{cases}$$

* **Variables de Entrada Evaluadas ($X$):**
  Predictores del Módulo 1 enriquecidos con factores ambientales:
  * *Demanda e Inercia:* `val_roll_mean_3h`, `val_lag_1h`, `val_lag_24h`.
  * *Infraestructura y Oferta:* `Cap_total`, `Frecuencia`, `N_Rutas`, `Troncal_code`.
  * *Factores Contextuales y Clima:* `Hora`, `DiaSemana_code`, `clima_temp_cat`, `clima_lluvia_cat`.

* **Justificación de Selección de Features:**
  Las variables fueron probadas observando la correlación entre la acumulación de validaciones y las condiciones extremas del entorno. Las precipitaciones (`clima_lluvia_cat`) generan aumentos abruptos en la demanda del transporte masivo frente a alternativas abiertas, alterando significativamente los patrones normales de aforo.

* **Modelo Baseline de Referencia:** **Clasificador Zero-R (Clase Mayoritaria)** o **Decision Tree Classifier de profundidad baja**.
  * *Justificación del Baseline:* Zero-R establece el umbral mínimo de desempeño predeterminado al asignar siempre la clase de aforo más frecuente del histórico.

* **Modelo Seleccionado:** **Random Forest Classifier**.
  * *Justificación Técnica y Explicabilidad:* La relación entre la hora, la lluvia y la demanda presenta fronteras de decisión no lineales. Random Forest combina múltiples árboles de decisión (*bagging*), lo que reduce la varianza y evita el sobreajuste. Permite evaluar la importancia de cada característica mediante la Impureza de Gini (*Feature Importance*), garantizando la auditabilidad exigida.

* **Métricas Principales de Evaluación:** **ROC-AUC Multiclase** (*One-vs-Rest*), **F1-Score Weighted** y **Balanced Accuracy**.
  * *Justificación de Métricas:* La distribución de ocupación en el transporte público presenta un fuerte desbalance de clases (los buses pasan saturados en horas pico y vacíos en horas valle). El área bajo la curva ROC (ROC-AUC) evalúa la capacidad de discriminación global del modelo entre los niveles de aforo independientemente del umbral de decisión. El F1-Weighted y la precisión balanceada aseguran que el modelo clasifique con la misma eficacia las situaciones de baja, media y alta ocupación sin sesgarse hacia la clase mayoritaria.

---

### Módulo 3: Motor Prescriptivo de Recomendación (*Decision Engine*)

* **Propósito del Módulo:** Generar una sugerencia de acción para la toma de decisiones del usuario en tiempo real (abordar inmediatamente, esperar la siguiente unidad o evaluar transporte alternativo).

* **Construcción Analítica del Target ($y_{Rec}$):**
  Este target prescriptivo se genera mapeando la matriz de decisión de la función de utilidad del producto $U(Aforo, ETA)$:
  $$\text{Regla}(A, ETA) = \begin{cases} 
  0 \text{ (Abordar Ahora)} & \text{si } A = 0 \text{ o } (A = 1 \text{ y } ETA \le 5.0\text{ min}) \\
  1 \text{ (Esperar Siguiente)} & \text{si } (A = 1 \text{ y } ETA > 5.0\text{ min}) \text{ o } (A = 2 \text{ y } ETA \le 3.0\text{ min}) \\
  2 \text{ (Evaluar Alternativa)} & \text{si } A = 2 \text{ y } ETA > 3.0\text{ min}
  \end{cases}$$

* **Variables de Entrada Evaluadas ($X$):**
  Salidas estimadas de los Módulos 1 y 2 (`ETA_predicho`, `Aforo_predicho`) junto con la variable contextual `Franja_code`.

* **Justificación de Selección de Features:**
  Se probaron y seleccionaron únicamente estas características compuestas porque la decisión del usuario se fundamenta exclusivamente en la relación entre el tiempo de espera y el nivel de confort, sin requerir la complejidad de las variables crudas de infraestructura.

* **Modelo Baseline de Referencia:** **Reglas Condicionales Estáticas**.
  * *Justificación del Baseline:* Estructura lógica rígida integrada directamente en el software que carece de flexibilidad ante cambios en las preferencias de los usuarios.

* **Modelo Seleccionado:** **Utility Decision Tree Classifier**.
  * *Justificación Técnica y Explicabilidad:* Encapsular la regla de utilidad dentro de un Árbol de Decisión simplifica el software backend. Permite auditar visualmente las recomendaciones emitidas y garantiza un tiempo de ejecución prácticamente nulo en producción.

* **Métricas Principales de Evaluación:** **Matriz de Confusión de Reglas**, **Matched Decision Accuracy** y **ROC-AUC Macro**.
  * *Justificación de Métricas:* Al ser un modelo prescriptivo basado en la función de utilidad $U(Aforo, ETA)$, el ROC-AUC Macro y la exactitud de decisión miden la fidelidad con la que el árbol de decisión preserva la lógica de recomendación óptima frente a escenarios límite. Se prioriza minimizar los Falsos Positivos de Abordaje (recomendar abordar cuando el bus viene colapsado), pues representa el error con mayor costo de experiencia para el usuario.

---

### Módulo 4: Detector de Anomalías Espacio-Temporales

* **Propósito del Módulo:** Identificar eventos atípicos en la red de transporte (colapsos de ruta, bloqueos o sobredemanda extemporánea) sin depender de etiquetas históricas de incidentes.

* **Variables de Entrada Evaluadas ($X$):**
  `Pax_bus` (pasajeros por unidad), `Ocupacion_pk` (pico de ocupación) y `Headway_Min` (intervalo de paso real).

* **Justificación de Selección de Features:**
  Se seleccionaron estas tres variables debido a su correlación directa con fallas operativas: una anomalía se manifiesta en el desacoplamiento entre el intervalo de paso y la carga de pasajeros (p. ej., un `Headway_Min` alto acoplado a un disparo en `Pax_bus`).

* **Modelo Baseline de Referencia:** **Umbral Móvil basado en Z-Score / Rango Intercuartílico (IQR)**.
  * *Justificación del Baseline:* Aplica límites estadísticos estándar sobre ventanas móviles para detectar valores fuera de rango de manera univariable.

* **Modelo Seleccionado:** **Isolation Forest**.
  * *Justificación Técnica y Explicabilidad:* Algoritmo no supervisado que aisla datos atípicos mediante particiones aleatorias en el espacio de características. Produce un *Anomaly Score* continuo entre $[-1, 1]$, permitiendo detectar desviaciones multivariables complejas con una baja carga computacional.

* **Métricas Principales de Evaluación:** **PR-AUC** (*Precision-Recall AUC*), **ROC-AUC en Datos Sintéticos/Inyectados** y **Precision@K**.
  * *Justificación de Métricas:* Al tratarse de un algoritmo no supervisado (*Isolation Forest*) donde las anomalías son eventos extremadamente raros (clase minoritaria severa), el área bajo la curva Precision-Recall (**PR-AUC**) es significativamente más informativa que la precisión global para medir la especificidad de las alertas. Adicionalmente, se utiliza el ROC-AUC sobre un conjunto de validación con anomalías inyectadas sintéticamente (p. ej., saltos abruptos de *Headway*) y la inspección del $top-K$ ($K=5\%$) de las desviaciones más extremas contra registros históricos de colapsos de ruta.


> [!WARNING]
> **Nota Operativa sobre los Target Definidos**
> Las fórmulas analíticas utilizadas para la construcción de los targets (`Target_ETA_Min`, `Target_Aforo` y `Regla_Recomendacion`) se encuentran sujetas a calibraciones durante las fases avanzadas de desarrollo y pruebas con usuarios. Dichos umbrales y transformaciones podrán ajustarse para reflejar de forma más precisa la dinámica real del servicio de transporte masivo o cambios en las políticas operativas del sistema.

> [!NOTE]
> **Variables de Entrada (Features) y Validación de Modelos**
> Las variables de entrada presentadas en este documento corresponden a un conjunto evaluado y seleccionado preliminarmente durante la fase de exploración de datos. Si bien este grupo de características ha demostrado un excelente desempeño analítico y consistencia teórica en las pruebas iniciales, el *feature store* definitivo permanecerá dinámico y podrá incorporar nuevas covariables o descartar predictores redundantes conforme se avance en la etapa de despliegue y refinamiento continuo en producción.

## 4. Uso Operativo en Producción de los modelos

Para asegurar la viabilidad del Eje 1 en un entorno de producción continuo, se define el flujo de ejecución y el plan de mantenimiento analítico.

### Flujo de Uso en Producción (Inferencia en Tiempo Real)
1. **Ingesta e Inferencia en Cascada:**
   Al realizar una consulta, el sistema ingiere las variables meteorológicas y operativas en tiempo real. Los Módulos 1 (ETA) y 2 (Aforo) procesan la información en paralelo.
2. **Evaluación de Anomalías y Prescripción:**
   El Módulo 4 evalúa si el estado del corredor presenta un comportamiento anómalo. Si las condiciones son normales, los resultados de ETA y Aforo alimentan el Módulo 3 (Recomendador Prescriptivo) para responder al usuario en menos de $2.0\text{ segundos}$.