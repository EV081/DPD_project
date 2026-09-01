# Adquisición de Datos

El proceso de obtención de datos para este proyecto proviene de diferentes fuentes de datos abiertos (Open Data), consultas a APIs de terceros y la generación de datos sintético para resolver el problema de arranque en frío.

## 1. ATU Open Data
* **Fuente:** Portal de Datos Abiertos de Protransporte/ATU.
* **URL:** https://sistemas.protransporte.gob.pe/DatosAbiertos/
* **Método de Adquisición:** Descarga manual de los archivos CSV históricos que contienen el número de validaciones por estación, ruta y por hora.

## 2. Tráfico en Tiempo Real e Histórico (TomTom)
* **Fuente:** TomTom Traffic Flow API.
* **URL:** https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/introduction 
* **Método de Adquisición:**
  1. Registro en el portal de desarrolladores de TomTom y obtención de una API Key.
  2. Ejecución de peticiones al endpoint de flujo de tráfico utilizando las coordenadas de las principales rutas del Metropolitano y Corredores.
  3. Extracción de variables clave:...

## 3. Infraestructura y Seguridad Ciudadana (OpenStreetMap)
* **Fuente:** OpenStreetMap (OSM).
* **URL:** https://www.openstreetmap.org/
* **Método de Adquisición:** Utilización de la API de Overpass para descargar la red de calles de Lima. Se extraerán puntos de interés relacionados con iluminación, comisarías, paraderos autorizados y zonas comerciales para construir el índice de seguridad del algoritmo.

## 4. Clima Histórico (SENAMHI)
* **Fuente:** Datos meteorológicos históricos de Lima.
* **URL:** https://www.senamhi.gob.pe/site/descarga-datos/
* **Método de Adquisición:** Descarga manual del portal del SENAMHI para obtener datos de precipitación y temperatura. Estos datos se cruzarán temporalmente con la demanda de ATU, ya que el clima afecta el uso del transporte.

## 5. Dataset Sintético
Los datos sintéticos serían los registros generados que van imitir las condiciones del trafico para solventar la falta de información o problemas de arranque en frío (Cold Start). Para el proyecto, la generación se realizará mediante un script de Python. Este código tomará las distribuciones probabilísticas base de la demanda de la ATU y heurísticas lógicas por franjas horarias, construyendo un histórico simulado de 6 meses al que se le inyectará ruido estadístico. Este proceso permitirá simular escenarios variados de ocupación vehicular, clasificándolos en niveles de "Asientos", "De pie" y "Lleno", lo que proporcionará el volumen de información necesario para entrenar el modelo predictivo inicial sin caer en el sobreajuste (overfitting).