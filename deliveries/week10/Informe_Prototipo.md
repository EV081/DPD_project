# Informe del Prototipo Funcional - UrbanSafe

**Entregable :  Semana 11**  
**Producto de Datos:** UrbanSafe - Sistema Móvil e Inteligente de Navegación y Evaluación de Riesgo Urbano en Transporte Público


## 1. Resumen Ejecutivo

UrbanSafe es un Producto de Datos móvil e interactivo desarrollado para optimizar la toma de decisiones de los usuarios del transporte público en Lima Metropolitana. A través de la integración de datos geoespaciales, información de validaciones del sistema de transporte y un pipeline de Machine Learning especializado, la plataforma permite consultar paraderos urbanos, explorar el trazado de sus rutas y predecir el nivel de afluencia y ocupación en tiempo real.

> [!NOTE]
> En esta fase funcional, el sistema se enfoca en la navegación de paraderos, la búsqueda geoespacial y la estimación de demanda, sentando las bases analíticas para la posterior integración de algoritmos de caminabilidad y riesgo peatona

El presente informe describe el estado del **Prototipo Funcional (semana 11)**. Se presenta una solución *end-to-end* completamente integrada que conecta una aplicación nativa Android (APK) con un backend analítico desplegado en la nube en Render, capaz de ejecutar inferencias de modelos predictivos sobre escenarios reales.


## 2. Fuentes y Procesamiento de Datos (*Data Sources & Pipeline*)

El producto de datos integra y procesa de manera coordinada múltiples fuentes heterogéneas de datos urbanos:

| Fuente de Datos | Descripción / Formato | Aplicación en el Producto de Datos |
| :--- | :--- | :--- |
| **ATU** | Estructura de rutas, horarios y paraderos del transporte formal de Lima. | Construcción de la topología base de paraderos y red de transporte. |
| **Validaciones Metropolitano** | Registros de transacciones y flujo de pasajeros en torniquetes. | Matriz base para el entrenamiento de predicción de afluencia y congestión. |
| **TomTom Traffic API** | Datos de velocidad, congestión y tiempo de recorrido en vías. | Factor dinámico para el cálculo de riesgo y demoras en ruta. |
| **OpenStreetMap (OSM)** | Red vial, nodos peatonales y geometría urbana. | Generación del trazado de los paraderos y calculo de distancias. |


## 3. Funcionalidades Implementadas (*Implemented Features*)

### 3.1 Aplicación Móvil (React Native / Expo)
- **Sistema de Autenticación Segura (JWT):** Módulo completo de gestión de usuarios que incluye registro de cuentas, inicio de sesión mediante tokens JWT, actualización de datos de perfil, cambio de contraseña y eliminación de cuenta.
- **Búsqueda y Recomendación de Destinos:** Interfaz de autocompletado conectada al proxy de geocodificación para la selección de orígenes, destinos y sugerencias inteligentes de puntos de llegada en la ciudad.
- **Predicción en Tiempo Real y Análisis de Paraderos:** Visualización del estado actual de los paraderos incluyendo estimación de aforo, tiempo estimado de llegada (ETA), detección de anomalías operativas y un sistema de recomendación accionable (*abordar vehículo, esperar al siguiente o cambiar de paradero*).
- **Módulo de Pronóstico (*Forecast*):** Curvas de proyección de afluencia temporal para la planificación anticipada de viajes.
- **Exploración de Trazados y Filtrado Multimodal:** Visualización de las rutas asociadas a cada paradero y filtros avanzados por tipo de servicio de transporte público en Lima (Metropolitano, Corredores Complementarios, Líneas de Metro y buses Alimentadores).
- **Branding y Empaquetado Standalone (APK):** Configuración de identidad visual, iconos, esquema de colores y package nativo (`com.urbansafe.mobile`) compilado mediante **EAS Build (Expo Application Services)** para pruebas físicas en Android.

### 3.2 Backend y Pipeline Analítico (Flask/FastAPI en Render)
- **Proxy Geoespacial y Rate Limiting:** Endpoint centralizado `/geo/autocomplete` que gestiona de manera segura las peticiones hacia la API de OpenStreetMap (Nominatim), incorporando manejo de cabeceras y control de tráfico.
- **Inferencia Predictiva con Modelos ML:** Servidor de modelos basado en algoritmos de Gradient Boosting (**LightGBM / XGBoost**) encargados de procesar la matriz de validaciones históricas y calcular métricas de ocupación, ETA y alertas.
- **Gestión de Lags y Mapeo Temporal:** Pipeline de transformación en tiempo real que homologa las peticiones del año actual hacia la ventana de 28 días de entrenamiento histórico respetando el día de la semana y contexto temporal.


## 4. Arquitectura del Sistema (*System Architecture*)

El prototipo se despliega sobre una arquitectura modular orientada a Productos de Datos:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Móvil (APK)                         │
│               (React Native / Expo Standalone)                  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 │ HTTPS (JSON / REST API)
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Analítico                            │
│                 (Flask / FastAPI en Render)                     │
│                                                                 │
│  ┌──────────────────────────┐     ┌──────────────────────────┐  │
│  │ Módulo de Geocodificación│     │ Algoritmo de Mapeo       │  │
│  │ (Proxy OSM / Nominatim)  │     │ Temporal (2026 -> 2025)  │  │
│  └─────────────┬────────────┘     └────────────┬─────────────┘  │
└────────────────┼───────────────────────────────┼────────────────┘
                 │                               │
     HTTP GET    │                               │ Matriz Lag 28 días
   (User-Agent)  ▼                               ▼
┌─────────────────────────────┐   ┌──────────────────────────────┐
│  OpenStreetMap (Nominatim)  │   │     Pipeline ML Inferencia   │
│  - Grafos de Caminabilidad  │   │  - LightGBM / XGBoost        │
└─────────────────────────────┘   │  - TomTom / ATU              │
                                  └──────────────────────────────┘
```



## 5. Retos Técnicos y Soluciones de Ingeniería (*Technical Challenges*)

### 5.1 Requisito de Lag Temporal (28 Días) y Mapeo Sintético 2026 -> 2025
* **El Problema:** El modelo predictivo (LightGBM/XGBoost) fue diseñado para capturar la estacionalidad de afluencia y riesgo mediante características de retardo (*lags*) que exigen una **ventana histórica continua de 28 días previos** a la fecha consultada. Dado que el prototipo se ejecuta en tiempo real en **2026** y los datasets históricos validados cubren hasta **2025**, las consultas en vivo no encontraban registros previos en la matriz de datos, provocando fallos en la matriz de entrada o inferencias nulas.
* **La Solución:** Se desarrolló un **módulo de mapeo y alineación temporal** en el backend. Cuando el cliente envía una petición con la fecha y hora actual de 2026, el servidor transforma sintéticamente la fecha al año 2025 **preservando exactamente el mismo día de la semana, la franja horaria y las características de festivos/calendario**. De este modo, se reconstruye dinámicamente la ventana de 28 días de lag que requiere el modelo para realizar la inferencia sin alterar la estructura del pipeline de ML.

### 5.2 Escasez de Datos Etiquetados y Focalización en Estación Naranjal
* **El Problema:** : La información oficial de validaciones y flujos proporcionada por la Autoridad de Transporte Urbano para Lima y Callao (**ATU**) presenta una alta concentración en estaciones troncales, dejando a gran parte de los paraderos secundarios e intermedios con una marcada escasez de datos (*data sparsity*) o sin registros históricos etiquetados. Para evitar que la aplicación devuelva valores nulos (`NULL`) o interfiera con la experiencia de usuario en paraderos sin cobertura directa de entrenamiento, se diseñó e implementó una **estrategia de inferencia por nodo representativo**.

* **La Solución:** Bajo este enfoque, los paraderos que cuentan con registros históricos continuos de la ATU ejecutan sus predicciones de afluencia de forma directa. Por su parte, aquellos paraderos sin matriz de datos asignan dinámicamente como *proxy* o patrón de referencia las estimaciones calculadas para la **Estación Naranjal**. La elección de Naranjal como nodo maestro se justifica técnicamente por su condición de terminal macro-urbano de alta demanda: sus curvas de afluencia temporal (picos de hora punta, valles de mediodía y comportamiento de fines de semana) reflejan con alta correlación el ritmo de movilidad y saturación del transporte público en los ejes conectados de Lima. Esta solución garantiza que el Producto de Datos mantenga una estimación continua, coherente y funcional a lo largo de toda la red geoespacial del prototipo.

### 5.3 Control de Tasa (*Rate Limiting 429*) en OpenStreetMap (Nominatim)
* **El Problema:** Durante el testing en dispositivos móviles, las ráfagas rápidas de tipeo en el campo de búsqueda enviaban peticiones consecutivas por cada carácter ingresado. Esto superó la política de uso de Nominatim (máximo 1 req/seg), provocando un bloqueo de la IP de Render con el error `HTTP Error 429: Too many requests`.
* **La Solución:** Se diagnosticó la causa raíz mediante peticiones directas al endpoint y se definió la estrategia de mitigación:
  1. Implementación de **Debounce (~500 ms)** en el frontend para suspender el envío de peticiones hasta que el usuario termine de tipear.
  2. Inclusión obligatoria del encabezado personalizado `User-Agent: UrbanSafeApp/1.0` en las peticiones del backend hacia la API de Nominatim.

### 5.4 Latencia de Latencia por Arranque en Frío (*Cold Start*) en Render
* **El Problema:** Al operar sobre la infraestructura gratuita de Render, la instancia del backend entra en modo de suspensión tras 15 minutos de inactividad, generando tiempos de espera de 30 a 60 segundos en la primera petición enviada desde el móvil.
* **La Solución:** Documentación del comportamiento para las pruebas de usuario y activación previa del servicio mediante una petición GET inicial desde el navegador antes de iniciar las pruebas en la aplicación instalada.


## 6. Limitaciones Conocidas (*Known Limitations*)

### 6.1 Cobertura Heterogénea de Datos y Dependencia del Nodo Proxy (Naranjal)
* **Inferencia Asimétrica:** La precisión cuantitativa de los modelos de *Machine Learning* (LightGBM/XGBoost) se encuentra óptimamente calibrada para la **Estación Naranjal y su cuenca de paraderos afluentes**, debido a la concentración de datos oficiales de validación de la ATU.
* **Aproximación por Nodo Representativo:** Para paraderos secundarios o informales que carecen de registros históricos directos, la plataforma recurre a una estimación por *proxy* basada en el patrón temporal de Naranjal. Aunque esta solución mantiene la operatividad continua de la aplicación, constituye una aproximación cualitativa que no refleja micro-fluctuaciones específicas de cada punto.

### 6.2 Estrategia de Mapeo Temporal Sintético (Ventana de Lags 2026 $\rightarrow$ 2025)
* **Dependencia de Homologación:** La conversión en tiempo de ejecución de las fechas solicitadas en 2026 hacia su equivalente homólogo en 2025 (respetando día de la semana, franja horaria y festivos) es un mecanismo de contingencia para cumplir con la ventana de *lag* de 28 días exigida por los modelos.
* **Ausencia de Eventos Ocurridos en Tiempo Real:** Este enfoque asume que el patrón de demanda se comporta de manera similar al año previo, por lo que no puede capturar disrupciones imprevistas en tiempo real ocurridas en 2026 (como protestas, desvíos por obras o accidentes de tránsito de último minuto).

### 6.3 Dependencia de APIs Externas y Tasa de Peticiones (*Rate Limiting*)
* **Sensibilidad de Geocodificación y Autocompletado:** El servicio de geocodificación depende de la API pública de **OpenStreetMap (Nominatim)**, la cual aplica restricciones estrictas de tasa de peticiones (máximo 1 req/seg y requerimiento obligatorio de `User-Agent`). Ante ráfagas de escritura rápida en el cliente móvil sin protección de *debounce*, el servicio backend puede experimentar bloqueos temporales (error `429 Too Many Requests`).

### 6.4 Latencia de Infraestructura Cloud y Conectividad
* **Arranque en Frío (*Cold Start*) en Render:** El despliegue de la API en la capa gratuita de Render provoca latencias iniciales de entre 30 y 50 segundos cuando la aplicación realiza la primera petición tras un periodo de inactividad.
* **Requisito Estricto de Conectividad en Línea:** El prototipo requiere acceso ininterrumpido a internet para resolver el trazado de paraderos, la geocodificación y la predicción de afluencia; actualmente no cuenta con una capa de almacenamiento/persistencia *offline* ni mapa vectorial local.

## 7. Trabajo Restante y Hoja de Ruta (*Remaining Work*)

De cara a las fases finales del desarrollo y el escalamiento del Producto de Datos, se han establecido las siguientes prioridades estratégicas organizadas por componentes técnicos:

### 7.1 Implementación del Segundo Eje: Módulo de Rutas Seguras y Caminabilidad
- **Desarrollo del Algoritmo de Ruteo Peatonal Seguro:** Construir el motor de cálculo de rutas que combine la red geoespacial de OpenStreetMap con capas de riesgo, iluminación y datos del entorno para sugerir trayectos peatonales óptimos hacia los paraderos.
- **Visualización Interactiva en Mapa:** Integrar en el cliente móvil la representación gráfica del trazado peatonal sugerido junto con sus indicadores cualitativos de seguridad.

### 7.2 Cobertura Geoespacial Completa y Trazado de Rutas
- **Completitud del Catálogo de Trazados:** Finalizar el pipeline de extracción y renderizado para asegurar que el 100% de los paraderos de la red cuente con la geometría y el trazado de sus líneas asociadas (cubriendo paraderos secundarios que actualmente carecen de trazado).
- **Optimización del Algoritmo de Recomendación de Paraderos:** Rediseñar la lógica de recomendación de origen/destino para que priorice dinámicamente paraderos que cuenten con trazado verificado y predicción de afluencia activa, evitando sugerir nodos sin cobertura analítica completa.

### 7.3 Infraestructura y Despliegue Cloud-Native
- **Migración Integral a la Nube (AWS / Cloud-Native Architecture):** Transicionar la infraestructura actual a un entorno Cloud escalable y de alta disponibilidad, orquestando el backend, el almacenamiento de grafos y los modelos ML mediante servicios *serverless* o contenedores administrados (evitando latencias por *cold start* y limitaciones de capacidad).
- **Capa de Caching y Middleware de Alta Eficiencia (Redis):** Implementar un sistema de almacenamiento en memoria para caching de autocompletado y consultas recurrentes, garantizando tiempos de respuesta por debajo de los 100 ms y aislando el sistema de bloqueos por *rate limiting* de APIs externas.

### 7.4 Escalabilidad del Pipeline de Machine Learning
- **Entrenamiento Masivo y Descentralizado:** Expandir el entrenamiento de los modelos LightGBM/XGBoost para abarcar de forma nativa la totalidad de paraderos de la red, reduciendo progresivamente la dependencia del nodo patrón de Naranjal a medida que se integren nuevas fuentes de datos.
- **Pipeline de Ingesta Continua y Reentrenamiento Autónomo:** Reemplazar la transformación sintética de fechas por un pipeline ETL automatizado que reentrene los modelos periódicamente con la llegada de nuevas validaciones de la ATU y fuentes meteorológicas/tráfico en tiempo real.

### 7.5 Optimización de Cliente Móvil (UX / Frontend)
- **Integración Definitiva de Debounce y Gestión de Peticiones:** Incorporar de forma nativa el control de peticiones (temporizador de 500 ms) en las entradas de texto para proteger los *endpoints* del backend.
- **Gestión de Estados de Carga y Retroalimentación:** Implementar indicadores visuales (*skeletons*, loaders y alertas) para informarle al usuario el estado de procesamiento del backend durante la carga inicial.
- **Validación de Campo con Usuarios Reales:** Ejecutar pruebas de usabilidad e itinerario en escenarios reales de movilidad con la APK instalada, recolectando métricas directas de experiencia de usuario (*UX*).

## 8. Despliegue y Repositorios (*Deployment & Repository Links*)

Para la evaluación técnica y pruebas del prototipo funcional (semana 11), se ponen a disposición los enlaces de acceso a la infraestructura desplegada, el instalador del cliente móvil y los repositorios de código fuente del proyecto:

### 8.1 Servicios Desplegados en Producción
* **Servidor Backend (API REST & Inferencia ML):**  
  [https://backend-urbansafe.onrender.com](https://backend-urbansafe.onrender.com)  
  *(Alojado en Render. Gestiona la autenticación JWT, el proxy de geocodificación y los endpoints de inferencia predictiva).*

* **Descarga de Aplicación Móvil (APK Android):**  
  [https://expo.dev/accounts/alessandro1821/projects/urbansafe-mobile/builds/4214e546-5181-4c2d-a740-f6d754b46aa6](https://expo.dev/accounts/alessandro1821/projects/urbansafe-mobile/builds/4214e546-5181-4c2d-a740-f6d754b46aa6)  
  *(Compilación ejecutable lista para instalación e inspección en dispositivos físicos Android).*



### 8.2 Repositorios de Código Fuente
* **Repositorio Frontend (React Native / Expo):**  
  [https://github.com/Alessandromg18/Frontend_UrbanSafe.git](https://github.com/Alessandromg18/Frontend_UrbanSafe.git)

* **Repositorio Backend & Machine Learning (Python / API REST):**  
  [https://github.com/Alessandromg18/Backend_UrbanSafe.git](https://github.com/Alessandromg18/Backend_UrbanSafe.git)
