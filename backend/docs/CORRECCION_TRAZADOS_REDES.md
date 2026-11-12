# Corrección de trazados del mapa

Se contrastaron las secuencias con los mapas ATU descargados y revisados en `data/atu/paradas_mapas_revisadas.json` y el catálogo de paradas revisado. El portal no respondió durante el intento de consulta de esta revisión; se usaron sus originales descargados previamente, no una nueva publicación comprobada.

- Línea 1: los dos archivos eran tramos consecutivos. Se unieron en la misma coordenada compartida, sin introducir segmentos. Las 26 estaciones corresponden al esquema ATU.
- Metropolitano: 28 fichas/sentidos reconstruidos sobre un grafo de segmentos OSM existentes, pasando por las estaciones en el orden revisado. Se descartaron conexiones de más de 1200 metros que originaban diagonales falsas. Ruta C también actualiza la vista general troncal. En Expresos 5 y 9, España/Central se conservan separados cuando el orden de ese ramal no está confirmado; no se inventa su conexión.
- Alimentadores: 110 lazos redundantes eliminados con el mismo criterio conservador de corredores: mantener segmentos existentes y no alejar el trazado más de 35 metros adicionales de los paraderos localizados. Los giros necesarios se conservan. Quedan 46 trazados activos (23 servicios con dos sentidos).
- Ocho trazados antiguos (Norte/Carabayllo, Norte/Collique, Norte/SantoDomingo y Norte/Tungasuca, dos sentidos cada uno) están archivados en `data/atu/trazados_alimentadores_sin_ficha.json`. No corresponden a claves del catálogo ATU vigente revisado; Carabayllo y Collique sí conservan las variantes actuales LosIncas.

Las imágenes ATU confirman estaciones y recorrido esquemático; no certifican los vértices calle por calle. Las geometrías del mapa siguen siendo aproximadas, basadas en segmentos OSM/OSRM existentes. No se deben rotular como trazados geográficos oficiales ATU.

Reproducir: `python scripts/corregir_trazados_redes.py` desde backend. El informe está en `data/atu/correccion_trazados_redes.json`. Verificaciones: `pytest tests/test_trazados_redes.py tests/test_limpieza_trazados.py`.
