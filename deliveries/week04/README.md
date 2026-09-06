# UrbanSafe AI: Ecosistema de Movilidad Predictiva y Segura

## 1. Equipo de Trabajo (Team Members)

* **Integrante 1:** Elmer Jose Manuel Villegas Suarez
* **Integrante 2:** Alessandro Facundo Freed Monzón Gallegos
* **Integrante 3:** Juan David Velo Poma (Líder del grupo)


## 2. Nombre Tentativo del Producto (Tentative Product Name)

**UrbanSafe AI**

> [!NOTE]
> El nombre del equipo se encuentra sujeto a modificaciones.

## 3. Problema u Oportunidad Inicial (Initial Problem or Opportunity)

### Contexto y Problemática
En el Sistema Integrado de Transporte de Lima (Metropolitano y Corredores Complementarios), los usuarios enfrentan una alta incertidumbre respecto a los tiempos de llegada y el nivel de aforo (asientos disponibles, viaje de pie o bus saturado) de las unidades. Esta carencia de información genera tiempos de espera ineficientes, viajes incómodos y aglomeraciones severas en los paraderos.

A esta ineficiencia en la movilidad se suma una problemática crítica de seguridad ciudadana durante la denominada "primera y última milla" (los tramos a pie que realizan los usuarios desde su origen hacia el paradero y desde la estación hasta su destino final). Según el informe técnico del Instituto Nacional de Estadística e Informática (INEI, 2025), la percepción de inseguridad ciudadana en las principales áreas urbanas supera el 85%, registrándose la mayor incidencia de victimización por robos y hurtos en vías públicas desoladas o mal iluminadas durante horarios de alta vulnerabilidad. Las herramientas de navegación convencionales vigentes en el mercado optimizan los trayectos basándose únicamente en la distancia mínima o el menor tiempo hipotético, ignorando el nivel de riesgo peatonal y el estado de ocupación de las unidades de transporte.

### Origen de la Iniciativa y Oportunidad
Evolucionando a partir de los aprendizajes y propuestas de la **Hackathon ATU 2026** y el concepto desarrollado por **Urbyte**, surge **UrbanSafe AI**. El proyecto capitaliza la disponibilidad de portales de datos abiertos (*Open Data*) y servicios de APIs públicas para transformar la gestión tradicional del transporte hacia un **Producto de Datos**.

### Propuesta de Valor del Producto de Datos
UrbanSafe AI aborda estas problemáticas mediante el modelado predictivo del aforo a través de datos proxy (tráfico en tiempo real y registros históricos de la ATU) e integra un algoritmo de enrutamiento por riesgo que prioriza vías iluminadas y seguras sobre la distancia más corta, reduciendo la exposición al peligro de los peatones.

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
El proyecto se enmarca analíticamente en la convergencia de tres áreas clave: **Transporte Urbano**, **Ciudades Inteligentes (*Smart Cities*)** y **Seguridad Ciudadana**.

### Enfoque de la Solución
La solución adopta un enfoque predictivo y prescriptivo mediante el uso de algoritmos de Machine Learning. En lugar de ofrecer un diagnóstico puramente descriptivo sobre la ubicación actual de los buses, el sistema infiere el nivel de aforo futuro de las unidades y sugiere rutas peatonales seguras en función del entorno y la hora del desplazamiento.

### Usuarios Objetivo
La solución ha sido estructurada considerando dos perfiles de usuarios claramente identificados:

* **Usuarios del Transporte Público (Pasajeros y Peatones):** Ciudadanos que realizan desplazamientos cotidianos en el sistema integrado de Lima y requieren planificar sus viajes reduciendo la incertidumbre del aforo de los buses, optimizando sus tiempos de espera y transitando por caminos peatonales con menor exposición a la delincuencia.
* **Planificadores Urbanos y Entidades Reguladoras (ATU y Municipios):** Organismos de gestión del transporte que pueden aprovechar el análisis agregado de la demanda e identificar zonas críticas en la infraestructura de la primera y última milla para la toma de decisiones basada en datos.

## 5. Fuente del Dataset (Dataset Source)

Para demostrar que los datos son accesibles, ricos y útiles para el desarrollo de un Producto de Datos, el proyecto combina cuatro fuentes de datos abiertos (Open Data / APIs) con un conjunto de datos sintéticos :

* **ATU Open Data (ProTransporte):** Fuente primaria para la demanda base.  
Corresponde al portal de datos abiertos que provee el conteo de validaciones por hora, ruta y estación. Se obtiene mediante descarga manual en formato CSV desde el [Portal Oficial de ProTransporte](https://sistemas.protransporte.gob.pe/DatosAbiertos/).
* **TomTom Traffic Flow API:** Telemetría de velocidad y congestión en tiempo real obtenida mediante peticiones HTTP a la [TomTom Traffic API](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/introduction) utilizando una API Key sobre las coordenadas de las rutas del transporte público.
* **OpenStreetMap (OSM):** Información geoespacial de infraestructura (luminarias, comisarías, zonas comerciales y paraderos) extraída mediante la API de Overpass para calcular el índice de seguridad peatonal.
* **SENAMHI (Clima Histórico):** Registros de precipitación y temperatura descargados del portal del [SENAMHI](https://www.senamhi.gob.pe/site/descarga-datos/) para cruzar el impacto meteorológico con la demanda de transporte.
* **Dataset Sintético (Python Script):** Muestra simulada de 6 meses generada mediante un script en Python que inyecta ruido estadístico sobre las distribuciones de la ATU para simular niveles de aforo (*Asientos*, *De pie*, *Lleno*), garantizando volumen suficiente para el entrenamiento inicial del modelo.

Para revisar los scripts de extracción, el flujo de ingesta y los detalles del script de datos sintéticos, consulte la [Guía Técnica de Adquisición de Datos](./acquisition.md). La estructura detallada de las variables se encuentra en el [Diccionario de Datos](./data_dictionary.csv) y la muestra de trabajo en [`data/sample.csv`](./data/sample.csv).
