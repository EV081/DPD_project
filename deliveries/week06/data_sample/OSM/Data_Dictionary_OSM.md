# Diccionario de Datos — OpenStreetMap (Bogotá)

Fuente: OSM vía BBBike — `https://download.bbbike.org/osm/bbbike/Bogota/Bogota.osm.pbf`
(Fragmento de la ciudad, incluye todas las calles y todos los Puntos de Interés).
Generado por `code/download_osm.py` con la librería **pyrosm**.

Se producen 3 archivos en `data/OSM/`:

| Archivo | Contenido | Volumen |
|---------|-----------|---------|
| `bogota.osm.pbf` | Extracto OSM crudo | 20,297,152 B |
| `pois.csv` | Puntos de interés (categorizados) | 34,853 POIs |
| `red_vial.geojson` | Red vial completa (segmentos por calle) | 123,390 tramos |

---

## `pois.csv` — Puntos de interés (34,853 filas)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `categoria` | str | Categoría del POI (ver dominios abajo). |
| `lon` | float | Longitud (EPSG:4326, grados decimales). |
| `lat` | float | Latitud (EPSG:4326). |
| `name` | str | Nombre en OSM (puede estar vacío, ej. luminarias sueltas). |

### Dominio `categoria`

| Categoría | Cantidad | ¿Qué es? (tags OSM) |
|-----------|----------|----------------------|
| `luminaria` | 606 | `highway=street_lamp` — postes de alumbrado público. |
| `hospital` | 162 | `amenity=hospital`, `amenity=clinic`, centros médicos. |
| `comisaria` | 206 | `amenity=police` — estaciones de policía/comisarías. |
| `comercio` | 22,452 | `shop=*` — locales comerciales. |
| `negocio` | 11,427 | `amenity` de servicios: banco, restaurante, hotel, farmacia, etc. |

> Uso típico: indicadores de **seguridad/iluminación** (luminarias, comisarías) y de
> **actividad/comercio** alrededor de las estaciones de TransMilenio.

---

## `red_vial.geojson` — Red vial (123,390 features LineString)

Cada feature es un **segmento** de calle (arista). Para construir el grafo vial,
los nodos serán las intersecciones y las aristas estos segmentos (`build_graph.py`).

| Campo | Tipo | Dominio / descripción |
|-------|------|------------------------|
| `highway` | str | Clasificación OSM (ver tabla abajo). |
| `oneway` | str | `yes` (24,651) / `no` (2,463) / `-1` (sentido inverso) / vacío (bidireccional implícito). |
| `lanes` | int | N° de carriles (23,254 tramos con 2; 3,518 con 1; 3,372 con 3; resto vacío = sin dato). |
| `maxspeed` | float | Límite de velocidad (km/h); mayormente vacío en OSM primeras coberturas. |
| `geometry` | LineString | Trazado del segmento (EPSG:4326). |

### Dominio `highway` (top 10 de 123,390)

| Valor | Tramos | Descripción |
|-------|--------|-------------|
| `footway` | 35,907 | Sendas peatonales. |
| `residential` | 34,784 | Calles residenciales. |
| `service` | 27,107 | Vías de servicio / acceso a predios. |
| `tertiary` | 7,479 | Vías terciarias. |
| `secondary` | 4,339 | Vías secundarias. |
| `primary` | 3,557 | Vías primarias. |
| `cycleway` | 2,321 | Ciclorrutas dedicadas. |
| `steps` | 1,845 | Escaleras. |
| `trunk` | 1,471 | Vías principales (tipo autopista urbana). |
| `corridor` | 828 | Pasillos interiores. |

> La red incluye TODAS las calles de la ciudad, no solo corredores de TransMilenio.
> Para el proyecto conviene filtrar `highway` en
> `residential, footway, tertiary, secondary, primary, residential` y decidir si se
> excluyen `motorway`, `steps` o `cycleway` según el caso.

---

## Reproducibilidad

- Descarga: `python code/download_osm.py`
  (variable `RECUPERAR_DATOS` para reprocesar el PBF ya descargado).
- Procesamiento: pyrosm 0.13.1 (`get_network(network_type="all")`,
  `get_pois(custom_filter=…)`). Requiere módulo `osmium` (python, no CLI).