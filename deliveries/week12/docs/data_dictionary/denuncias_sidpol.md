# Diccionario de datos — denuncias SIDPOL (Eje 2)

Fuente: Denuncias policiales registradas a nivel nacional, MININTER (datos abiertos). Aquí: Lima y Callao.
Tabla cruda: `data_processed/eje2/raw/denuncias_<año>.parquet` (2 594 332 filas en total; un archivo por año del hecho, y `denuncias_antes_2018.parquet` para los años anteriores). Cada fila lleva `_fila`, su posición en el CSV unificado. Tabla limpia del EDA:
`data_processed/eje2/clean/denuncias_eje2_clean.parquet`.

## 1. Tabla cruda (columnas que se usan)
| Columna | Tipo | Descripción | Nulos | Uso |
|---|---|---|---:|---|
| `id_dgc` | Int64 | identificador único de la denuncia | 0 % | llave |
| `fecha_hora_hecho` | datetime | fecha y hora del hecho | 0 % | partición temporal, turno |
| `fecha_hora_registro_hecho` | datetime | fecha y hora del registro | 0 % | calidad (registro < hecho) |
| `turno_hecho` | texto | madrugada / mañana / tarde / noche (derivado de la hora) | 0 % | feature |
| `lat_hecho`, `long_hecho` | float | coordenada WGS84 del hecho. **Nunca nula, pero puede ser el centroide de la comisaría** | 0 % | ubicación |
| `estado_coord` | texto | `CON COORDENADA` / `SIN COORDENADA`. **No confiable**: ver `observacion` | 0 % | no usar |
| `observacion` | texto | calidad de la coordenada (ver sección 3) | 0 % | define `coord_real` |
| `distrito_hecho`, `provincia_hecho` | texto | ubicación declarada | 0 % | filtro Lima/Callao, cobertura |
| `comisaria_hecho` | texto | comisaría de jurisdicción | 0 % | cobertura, ponderación |
| `tipo_hecho`, `subtipo_hecho`, `modalidad_hecho` | texto | clasificación del hecho | 0 % | grupo del Eje 2 |
| `direccion_hecho`, `tipo_via_hecho` | texto | dirección escrita y tipo de vía (87 % "Otros") | 0 % / 3,7 % | prueba de geocodificación |
| `es_delito_x`, `materia_hecho`, `solo_denuncia` | texto/entero | clasificación general | 0 % | referencia |

**Columnas descartadas** (≥ 95 % nulos): `tipologias_ia`, `cuadra_hecho`, `barrio`, `comisaria`, `departamento`, `provincia`,
`distrito`, `fecha_inaguracion`, `indice_priorizacion`. `origen` indica el archivo del que salió la fila.

## 2. Columnas derivadas (`eje2_common.marcar_calidad`)
| Columna | Descripción |
|---|---|
| `coord_real` | `observacion` ≠ `GEO FORZADA AL CENTROIDE DE COMISARIA` |
| `coord_apilada` | coordenada real repetida ≥ 500 veces (punto por defecto del geocodificador); lista calculada con train |
| `verificar_ubigeo` | `observacion` contiene `VERIFICAR` o `CORREGIR` |
| `hora_00_exacta` | la hora es exactamente 00:00 (valor por defecto) |
| `anio` | año del hecho |
| `grupo` | robo_persona, hurto, acoso, agresion_sexual, violencia_fisica (útiles) · vehiculo, domicilio, fraude_extorsion, violencia_familiar, intervencion_policial, otros (no útiles) |
| `sirve_eje2` | el `grupo` es útil para el peatón |

## 3. Valores de `observacion`
| Valor | Filas (train+valid) | Significado | ¿Coordenada real? |
|---|---:|---|:-:|
| COORDENADA OK | 1 466 725 | geocodificada correctamente | Sí |
| COORDENADA ADECUADA MANUALMENTE | 1 667 | corregida a mano | Sí |
| COORDENADA ADECUADA MANUALMENTE_A CORREGIR UBIGEO | 368 | corregida a mano, ubigeo dudoso | Sí (con bandera) |
| COORDENADA OK_VERIFICAR UBIGEO | 226 | OK, ubigeo dudoso | Sí (con bandera) |
| VERIFICAR UBIGEO | 7 | ubigeo dudoso | Sí (con bandera) |
| GEO FORZADA AL CENTROIDE DE COMISARIA | 581 057 | **sin ubicación; se puso el centroide de la comisaría** | **No** |

## 4. Tablas de apoyo (`data_processed/eje2/clean/`)
| Archivo | Contenido |
|---|---|
| `denuncias_eje2_clean.parquet` | 495 374 denuncias útiles (train + valid) |
| `puntos_apilados.parquet` | 115 puntos por defecto a excluir (`lat`, `long`) |
| `meses_baja_cobertura.csv` | 3 meses con < 50 % de eventos relevantes con coordenada **utilizable** (real y no apilada): 2019-09, 2019-10 y 2019-11. Se excluyen del objetivo |
| `cobertura_comisaria_anio.csv` | `cobertura` = % de eventos relevantes con coordenada utilizable, por comisaría y año, solo en meses válidos (803 celdas, mediana 0,93); sirve de peso y de exposición |
| `embudo_filtros.csv` | conteo tras cada filtro |
| `resumen_calidad_anio_grupo.csv` | filas y % de coordenada real por año y grupo |
| `geocode_muestra.parquet` | prueba de geocodificación (200 direcciones) |

## 5. Particiones (`data_processed/eje2/splits/`)
| Partición | Filas | Rango |
|---|---:|---|
| `train.parquet` | 1 603 871 | hasta 2022-12-31 |
| `valid.parquet` | 446 179 | 2023 |
| `test.parquet` | 283 138 | 2024-01-01 a 2024-08-31 (**sellado**) |
| `reserva.parquet` | 261 144 | 2024-09-01 a 2025-06-30 (**no se usa**: coordenadas utilizables insuficientes) |

## 6. Tablas del feature engineering (`data_processed/eje2/features/`)
| Archivo | Grano | Contenido |
|---|---|---|
| `puntos_acceso.parquet` | punto de acceso | `acceso_id`, `tipo` (metro_l1, troncal, corredor, alimentador), `nombre`, `ruta`, `lon`, `lat`, `precision_coord` y `confianza_coord` (solo alimentadores) |
| `segmentos_zona.parquet` | segmento de calle | `seg_id` (`u_v_key`, único), `u`, `v` (nodos OSM), `highway`, `via` (residencial, peatonal, arterial, servicio, otra), `length_m`, `dist_acceso_m`, `n_accesos`, `tipo_acceso_cercano`, `geometry` (UTM 18S) |
| `acceso_segmentos.parquet` | acceso × segmento | `acceso_id`, `seg_id`, `dist_m` (caminando por la red, ≤ 800 m) |
| `acceso_snap.parquet` | punto de acceso | `snap_m`: distancia al nodo de la red más cercano |
| `eventos_segmento.parquet` | evento | denuncias limpias asignadas a un segmento a ≤ 40 m (`seg_id`, `dist_evento_m`) |
| `segmento_comisaria.parquet` | segmento | comisaría del evento asignado más cercano |
| `poi_segmento.parquet` | segmento | conteo de POIs de OSM a ≤ 50 m por categoría (`poi_*`) |
| `panel_train.parquet`, `panel_valid.parquet` | segmento × año objetivo | features y objetivos (ver abajo): train 2019–2022, valid 2023 |
| `diccionario_features.csv` | columna | tipo y % de nulos del panel |

### Columnas del panel
| Columna | Descripción |
|---|---|
| `anio_obj` | año objetivo (2019–2022 en train, 2023 en valid) |
| `tasa_all`, `tasa_prev`, `decay` | eventos ponderados por cobertura por mes válido: todo el pasado, año anterior, con decaimiento (vida media 1,5 años) |
| `tasa_pat`, `tasa_per`, `frac_noche` | tasa de robo+hurto, tasa de acoso+agresión sexual+violencia física, fracción nocturna (nula si no hay historial) |
| `vec1`, `vec2`, `n_vec1`, `prior_vec` | tasa de calles contiguas a 1 y 2 saltos, nº de vecinos y su promedio |
| `n_eventos_pasado` | eventos del pasado en el segmento |
| `y_total`, `y_noche`, `y_dia`, `y_pat`, `y_per` | **objetivos**: conteos observados del año objetivo (meses válidos) |
| `cobertura`, `expo` | cobertura de la comisaría en el año objetivo y exposición del Poisson (`meses válidos/12 × cobertura`) |
| `via`, `length_m`, `poi_*` | tipo de vía, largo en metros, POIs cercanos |

Las features de un año objetivo usan **solo eventos de años anteriores**.

## 7. Grafo y salidas del modelo
| Archivo | Contenido |
|---|---|
| `graph/aristas.parquet`, `nodos.parquet`, `pois.parquet` | grafo peatonal de OSM (377 078 aristas dirigidas, 131 835 nodos) y 32 100 POIs de la zona, descargados offline. `graph/_teselas/` es caché de descarga |
| `outputs/riesgo_segmentos.parquet` | por segmento: `r_{total,noche,dia,persona}` (eventos/año), `dens_*` (por km), `riesgo01_*` (escala 0–1); modelos de producción con eventos hasta agosto de 2024 |
| `outputs/riesgo_valid2023.parquet` | igual, con modelos entrenados hasta 2022 y los eventos reales de 2023 (`y_*`, `expo`): sirve para elegir λ |
| `outputs/riesgo_test2024.parquet` | igual, con modelos entrenados hasta 2023 y los eventos reales de enero–agosto de 2024: confirma λ en el test |
| `outputs/indice_puntos_acceso.parquet` | por acceso: `seguridad_pct`, `seg_lo`, `seg_hi`, `base_tipo_pct`, `vs_base`, `confianza`, `ER`, `n_seg`, `snap_m`, … |
| `export/grafo_ruteo.parquet` | para el backend: `seg_id`, `u`, `v`, `largo_m`, `via`, `riesgo_total`, `riesgo_noche`, `riesgo_dia` |
