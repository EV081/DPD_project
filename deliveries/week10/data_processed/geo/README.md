# `data_processed/geo/`

Entrada del pipeline (`GEO_DIR`): GeoJSON de paraderos, rutas y trazados, y `tramos_osrm.csv`.
Los generan `scripts/04_geo_build/build_trazados.py`, `scripts/03_georef/geocodificar_alimentadores.py` y
`scripts/04_geo_build/build_tramos.py`.

## Aviso: contiene coordenadas derivadas de Google Places

- `paradas_alimentadores.geojson`: 134 de 712 paradas ubicadas con Google (`metodo` = `google_places` o
  `google_places+lado`); el resto, con OSM.
- `puntos_troncal.geojson`: 6 de 44 estaciones ubicadas con Google (32 filas por sentido en `export/paraderos.csv`,
  columna `evidencia`).

Uso: prototipo académico. No redistribuir ni usar en producción sin sustituirlas por datos oficiales de ATU
(ver `../../README.md`, sección "Coordenadas derivadas de Google Places").
