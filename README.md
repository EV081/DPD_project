# UrbanSafe AI: Ecosistema de Movilidad Predictiva y Segura

## 1. Equipo de Trabajo (Team Members)

* **Integrante 1:** Elmer Jose Manuel Villegas Suarez
* **Integrante 2:** Alessandro Facundo Freed Monzón Gallegos
* **Integrante 3:** Juan Velo Poma


## 2. Nombre Tentativo del Producto (Tentative Product Name)

**UrbanSafe AI**

> [!NOTE]
> El nombre del equipo se encuentra sujeto a modificaciones.

## 3. Problema u Oportunidad Inicial (Initial Problem or Opportunity)

En el Sistema Integrado de Transporte de Lima (Metropolitano y Corredores Complementarios), los usuarios enfrentan una alta incertidumbre respecto a los tiempos de llegada y el nivel de aforo de las unidades. Esta situación genera colas ineficientes, viajes incómodos y exposición a riesgos de seguridad ciudadana durante los desplazamientos a pie en la primera y última milla. 

UrbanSafe AI aborda esta problemática mediante el modelado predictivo del aforo a través de datos proxy (tráfico en tiempo real y registros históricos de la ATU) e integra un algoritmo de enrutamiento por riesgo que prioriza vías iluminadas y seguras sobre la distancia más corta, reduciendo la exposición al peligro de los peatones.

## 4. Dominio Objetivo (Target Domain) y Enfoque de la Solución

El proyecto se enmarca en el sector de **Transporte Urbano, Ciudades Inteligentes (Smart Cities) y Seguridad Ciudadana**.

La solución adopta un enfoque predictivo y prescriptivo mediante el uso de algoritmos de Machine Learning. En lugar de ofrecer un diagnóstico puramente descriptivo sobre la ubicación actual de los buses, el sistema infiere el nivel de aforo futuro de las unidades y sugiere rutas peatonales seguras en función del entorno y la hora del desplazamiento.


## 5. Fuente del Dataset (Dataset Source)

Para demostrar que los datos son accesibles, ricos y útiles para el desarrollo de un Producto de Datos, el proyecto combina cuatro fuentes de datos abiertos (Open Data / APIs) con un conjunto de datos sintéticos :

* **ATU Open Data (ProTransporte):** Fuente primaria para la demanda base.  
Corresponde al portal de datos abiertos que provee el conteo de validaciones por hora, ruta y estación. Se obtiene mediante descarga manual en formato CSV desde el [Portal Oficial de ProTransporte](https://sistemas.protransporte.gob.pe/DatosAbiertos/).
* **TomTom Traffic Flow API:** Telemetría de velocidad y congestión en tiempo real obtenida mediante peticiones HTTP a la [TomTom Traffic API](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/introduction) utilizando una API Key sobre las coordenadas de las rutas del transporte público.
* **OpenStreetMap (OSM):** Información geoespacial de infraestructura (luminarias, comisarías, zonas comerciales y paraderos) extraída mediante la API de Overpass para calcular el índice de seguridad peatonal.
* **SENAMHI (Clima Histórico):** Registros de precipitación y temperatura descargados del portal del [SENAMHI](https://www.senamhi.gob.pe/site/descarga-datos/) para cruzar el impacto meteorológico con la demanda de transporte.
* **Dataset Sintético (Python Script):** Muestra simulada de 6 meses generada mediante un script en Python que inyecta ruido estadístico sobre las distribuciones de la ATU para simular niveles de aforo (*Asientos*, *De pie*, *Lleno*), garantizando volumen suficiente para el entrenamiento inicial del modelo.

Para revisar los scripts de extracción, el flujo de ingesta y los detalles del script de datos sintéticos, consulte la [Guía Técnica de Adquisición de Datos](./acquisition.md). La estructura detallada de las variables se encuentra en el [Diccionario de Datos](./data_dictionary.csv) y la muestra de trabajo en [`data/sample.csv`](./data/sample.csv).
