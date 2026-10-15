# Backend: flujo de recomendación de paraderos

Diseño del flujo "estoy en un lugar y quiero ir a otro". La parte de datos **ya está implementada** (tablas y
funciones SQL en la BD, ver abajo); este documento define qué debe hacer la aplicación backend, que **aún no
existe**, con esos datos y con el modelo.

> **Fuente de datos.** El backend consulta **PostgreSQL** (funciones SQL, `prediccion`, `trafico_en_vivo`) y
> escribe `log_inferencia` y `feedback_usuario`. Los CSV de `export/` son un snapshot entregable para el
> equipo y la evaluación (verificable con `manifiesto_export.json`); no son el canal de la app. El frontend
> habla solo con el backend.

## Qué debe hacer el backend (resumen)

| # | Responsabilidad | Detalle |
|---|---|---|
| 1 | Geocodificar el destino | Texto → `lat, lon`; zonas amplias se resuelven con un pin |
| 2 | Tipo de día | La BD lo deduce de `p_ahora`: sábado `SAB`, domingo y **feriados** (tabla `feriado`, 2025-2026) `DOM`. Solo pasar `p_bucket` para forzarlo (p. ej. un feriado extraordinario) |
| 3 | Llamar a `rutas_directas()` y `rutas_transbordo()` | Con la hora de Lima en `p_ahora` |
| 4 | Ajustar el ETA con tráfico | `ajustar_en_vivo()` sobre `eta_min`/`eta2_min` de cada opción |
| 5 | Caminata real | OSRM `foot` para los mejores candidatos |
| 6 | Ranking final y respuesta | Penalizar aforo y transbordo, ordenar y construir el JSON |
| 7 | Degradar con claridad | Rutas sin predicción, tráfico caído, sin opciones |
| 8 | Registrar uso | `log_inferencia` y `feedback_usuario` (ya existen las tablas) |

## Objetivo

Dado el origen del usuario (su ubicación) y un destino (zona o dirección exacta), devolver los paraderos
cercanos ordenados por conveniencia. Cada opción indica la ruta, el sentido, el aforo estimado y el tiempo
hasta el próximo bus.

Ejemplo: el paradero 1 tiene un bus próximo pero lleno y el siguiente llega en 20 min. El paradero 2 está
5 min más lejos a pie, pero tiene un bus en 8 min con asientos libres. La app recomienda el paradero 2.

## Flujo

```
Frontend → Backend  GET /recomendar?lat_o&lon_o&destino
                      │
                      ├─ 1. Geocodifica el destino (si es texto) → lat_d, lon_d
                      ├─ 2. SQL: rutas_directas(...) y rutas_transbordo(...)
                      ├─ 3. Une con prediccion (aforo, eta_min, eta2_min) y trafico_en_vivo
                      ├─ 4. OSRM perfil foot: caminata real a los mejores candidatos
                      └─ 5. Ranking → JSON
```

### 1. Geocodificación del destino

- Dirección exacta: se convierte a `lat, lon` con TomTom Search, Google Geocoding o Nominatim (OSM).
- Zona (por ejemplo "San Miguel"): se geocodifica al centro del distrito y se pide al usuario precisar o
  soltar un pin. Un radio de 800 m sobre el centro de un distrito entero no es representativo.
- Origen: ubicación del dispositivo (geolocalización del navegador o del móvil).

### 2. Rutas que conectan origen y destino

**Implementado en la BD** ([schema.sql](../code/storage/schema.sql), sección 7). El backend solo las llama:

```sql
-- una sola ruta
SELECT * FROM rutas_directas(lat_o, lon_o, lat_d, lon_d,
       p_radio_m := 800, p_ahora := now_lima, p_bucket := NULL, p_solo_fiables := true,
       p_vel_mps := 1.33, p_limite := 10);
-- dos rutas con un transbordo a pie
SELECT * FROM rutas_transbordo(lat_o, lon_o, lat_d, lon_d,
       p_radio_m := 800, p_transbordo_m := 300, p_ahora := now_lima, p_bucket := NULL,
       p_solo_fiables := true, p_vel_mps := 1.33, p_penal_s := 300, p_limite := 10);
```

| Parámetro | Significado |
|---|---|
| `p_ahora` | Hora de Lima (`timestamp`); decide la hora de `prediccion` y el tipo de día |
| `p_bucket` | `LAB`/`SAB`/`DOM`. Si es NULL se deduce del día y de la tabla `feriado`: sábado `SAB`, domingo o feriado `DOM` |
| `p_solo_fiables` | Excluye opciones con algún tramo `fiable = false` (ver `tramo`); con `false` las devuelve y marca `tramos_no_fiables` |
| `p_vel_mps` | Velocidad de caminata en línea recta (1.33 m/s ≈ 80 m/min); el backend la afina con OSRM `foot` |
| `p_penal_s` | Penalización fija por transbordar |

`rutas_directas` devuelve, por ruta y sentido, la mejor pareja subida/bajada: `ruta`, `sistema`, `direccion`,
`paradero_subida`, `paradero_bajada`, `orden_*`, `dist_origen_m`, `dist_destino_m`, `viaje_s`, `aforo`, `eta_min`,
`eta2_min`, `recomendacion`, `espera_s`, `espera_fuente` (`prediccion` o `headway`) y `tiempo_total_s`.
`rutas_transbordo` devuelve lo mismo por tramo (`*1`, `*2`) más `dist_transbordo_m`, `espera1_s`, `espera2_s`
y `tiempo_total_s`. El aforo del segundo tramo usa la hora estimada de llegada al transbordo.

Reglas que aplican las funciones:

1. Paraderos de subida y bajada a ≤ `p_radio_m` del origen y del destino.
2. Misma ruta y `direccion`; el sentido se valida con `sentido_valido()` (tabla de abajo).
3. Los tiempos de viaje suman los `tramo` entre ambos órdenes.
4. Transbordo entre paraderos a ≤ `p_transbordo_m` (≤ 300 m, tabla `transbordo_cercano`) y rutas distintas.
5. Si una ruta no tiene predicción para esa hora, la espera es `headway / 2` del sistema.

`tiempo_total_s` es un orden de magnitud para ordenar: usa velocidades supuestas y la caminata es en línea
recta. El ranking final con la penalización por aforo queda en el backend.

Cómo leer `direccion` y `orden` (ver `orden_origen` en `paradero_ruta`):

| Caso | Regla para validar el sentido |
|---|---|
| `direccion` 1 o 2 (`atu_secuencia`) | `orden_subida < orden_bajada` en la misma `direccion` |
| `metro_l1` (`atu_secuencia`) y `troncal` (`latitud_troncal`), `direccion = 0` | Línea bidireccional: vale cualquier par de estaciones; el sentido es el signo de `orden_bajada − orden_subida` |
| corredores con `direccion = 0` (`catalogo_n_paradero`) | El orden recorre ida y vuelta: exigir `orden_subida < orden_bajada` y compararlo solo con enlaces `direccion = 0` de la misma ruta |

Ningún enlace tiene `orden` NULL. Los enlaces `catalogo_n_paradero` y `latitud_troncal` son menos fiables que los
de ATU: conviene mostrarlos con menor prioridad en el ranking.

Espera en un transbordo: `headway_sistema.headway_min / 2` del sistema de la segunda ruta, según el tipo de día
(`LAB`/`SAB`/`DOM`; feriado = `DOM`). Son los mismos valores con que el modelo calcula `eta_min`, así que no hay
que recalcular nada. En el primer tramo se usa `eta_min` de `prediccion`, que ya incluye el factor de aforo.
No hay headway por ruta ni por hora; solo Metro L1 tiene fuente oficial (ver el README de la semana).

El tiempo de un tramo sale de la tabla `tramo` (`duracion_s`, estimada; ver el README de la semana) o, sin BD,
de `export/tramos.csv`. Las funciones SQL ya los suman y excluyen los `fiable = false` por defecto.

Limitaciones: máximo **un** transbordo, siempre a pie y a ≤ 300 m; no considera horarios reales de los
servicios (solo headway) ni transbordos dentro de la misma ruta. Una ruta sin tramos calculados no se ofrece.

### 3. Aforo, ETA y tráfico

Las funciones SQL ya unen cada opción con `prediccion` (aforo, `eta_min`, `eta2_min`, `recomendacion`) y con
`headway_sistema`; el backend no consulta `prediccion` por su cuenta. Lo que le falta es el tráfico en vivo:

| Dato | Fuente | Notas |
|---|---|---|
| `aforo`, `eta_min`, `eta2_min`, `recomendacion` | Columnas de `rutas_directas` / `rutas_transbordo` | Por ruta, sentido y hora |
| Congestión en vivo | `trafico_en_vivo` | El backend ajusta el ETA con `ajustar_en_vivo()` (ver abajo) |

#### Ajuste del ETA con tráfico (responsabilidad del backend)

El `eta_min` guardado en `prediccion` corresponde a un día normal: el modelo lo calcula en batch y no sabe
cómo está el tráfico ahora. Al responder cada consulta, el backend lo corrige llamando a
`ajustar_en_vivo()` de `code/model/ajuste_vivo.py`. La función ya está escrita: es solo aritmética sobre
una fila de `prediccion` y el último snapshot de tráfico, sin llamar a TomTom, de modo que la API nunca
depende de la latencia de TomTom.

| Entrada | Fuente |
|---|---|
| `fila` (`aforo`, `eta_min`, `eta2_min`, opcional `aforo_siguiente`) | tabla `prediccion`, por ruta y hora |
| `snapshots` (`{segmento: {ratio, fuente, capturado_en}}`) | tabla `trafico_en_vivo` |
| `ahora`, `sistema` | hora de la consulta y sistema de la ruta |

Cálculo:

1. `factor = clip(ratio, 1.0, 1.5)`, donde `ratio` es velocidad libre ÷ velocidad actual del segmento.
   El factor nunca acelera el ETA y lo infla como máximo 50 %.
2. `eta_ajustado = eta_min × factor` (igual para `eta2_min`), y se recalcula la `recomendacion`.

Ejemplo: `eta_min = 8` y ratio 1.4 → ETA ajustado ≈ 11 min.

| `modo_datos` | Edad del snapshot | Efecto |
|---|---|---|
| `en_vivo` | ≤ 10 min | Aplica el factor completo |
| `reciente` | 10–30 min | Aplica solo una fracción (`peso_reciente`) |
| `historico` | > 30 min o sin dato TomTom | No ajusta (factor 1.0) |

Notas:

- Solo ajusta los sistemas con `aplica_trafico` en `models/mapeo_segmentos.json`; el Metro, por ejemplo,
  no depende del tráfico vial.
- Ajusta el **ETA**, no el aforo: el tráfico no cambia cuánta gente viaja, solo cuánto tarda el bus.
- El factor es una **hipótesis acotada, no entrenada**. Debe presentarse así, no como un modelo validado.
- La captura de snapshots (`run live` / `run loop`) corre aparte; el backend solo lee de la BD.
- La respuesta puede incluir `modo_datos`, `edad_snapshot_s` y `factor_trafico` para que el frontend
  indique qué tan fresco es el dato.

Reglas:

- Si `unidad_modelo` es NULL (20 rutas: 3 alimentadores y 17 corredores sin demanda fiable), mostrar
  "sin estimación" y bajarla en el ranking; no ocultarla.
- `eta_min` es una **estimación** a partir de headway y aforo, no la posición real del bus (ATU no la
  publica). TomTom corrige por tráfico, pero no localiza buses. Mostrar "bus estimado en ~X min".
- El aforo es por ruta, sentido y hora, **no por paradero**: dos paraderos de la misma ruta muestran el
  mismo aforo. La diferencia entre ellos viene de la caminata y de las rutas distintas.

### 4. Caminata real

La caminata de las funciones SQL es en línea recta a 1.33 m/s y subestima. Para las 3-5 mejores opciones se
consulta OSRM con perfil `foot` (origen → paradero de subida, bajada → destino y, en transbordos, paradero de
bajada → paradero de subida). Si OSRM no responde se conserva la estimación en línea recta.

### 5. Ranking

`tiempo_total_s` de la BD ordena las opciones de forma preliminar. El backend lo recalcula con lo que la BD no
sabe y ordena por el resultado (menor es mejor):

```
puntaje = caminata_real + espera_ajustada + viaje + (caminata_transbordo + penalización_transbordo)
          + penalización_aforo
espera_ajustada = ajustar_en_vivo(eta_min)      (o eta2_min si el aforo de la primera unidad es "Saturado")
```

- La penalización por aforo debe calibrarse; el modelo ya produce una `recomendacion` por clase de aforo
  (ver `V.recomendaciones` en `code/model`).
- Un viaje directo razonable debe quedar por encima de uno con transbordo, salvo que el transbordo ahorre
  tiempo claramente.
- Las rutas sin predicción (`espera_fuente = 'headway'`) se muestran como "sin estimación de aforo" y no se
  ocultan.

### 6. Fallos y degradación

| Situación | Comportamiento |
|---|---|
| Sin predicción para la hora o la ruta | `espera_fuente = 'headway'`; sin aforo |
| TomTom caído o snapshot viejo | `ajustar_en_vivo` devuelve `modo_datos = 'historico'` y no ajusta |
| OSRM no responde | Caminata en línea recta, marcada como estimada |
| Ninguna opción en el radio | Ampliar a 1.5 km una vez; si sigue vacío, informar que no hay transporte cercano |
| `tramos_no_fiables > 0` | Solo con `p_solo_fiables = false`; mostrar como menos confiable |

### 7. Registro

Cada recomendación puede registrarse en `log_inferencia` (fuente `tomtom` o `fallback`, latencia, estado) y el
botón "Ya abordé" escribe en `feedback_usuario` (`t_consulta`, `t_aborde`, `eta_mostrado_min`). Ver
`code/pipeline/feedback.py`.

## Respuesta esperada (borrador)

```json
{
  "origen": {"lat": -12.135, "lon": -77.0225},
  "destino": {"lat": -12.0773, "lon": -77.0825, "texto": "San Miguel"},
  "generado_en": "2026-10-15T08:00:00-05:00",
  "opciones": [
    {
      "tipo": "transbordo",
      "tiempo_total_min": 82,
      "tramos": [
        {"sistema": "corredor", "ruta": "304", "sentido": 1,
         "sube": "LAS ACACIAS", "baja": "OLAVIDE",
         "caminata_min": 5, "espera_min": 8, "viaje_min": 23,
         "aforo": null, "recomendacion": null, "espera_fuente": "headway"},
        {"sistema": "corredor", "ruta": "206", "sentido": 1,
         "sube": "ARENALES", "baja": "UNIVERSITARIA",
         "caminata_min": 3, "espera_min": 10, "viaje_min": 32,
         "aforo": "Asientos", "recomendacion": "...", "espera_fuente": "prediccion"}
      ],
      "caminata_final_min": 2,
      "modo_datos": "en_vivo",
      "confianza_coord": "alta",
      "advertencias": ["sin estimación de aforo en el primer tramo"]
    }
  ]
}
```

Un viaje directo es el mismo objeto con `tipo = "directo"` y un solo elemento en `tramos`.

## Fuera de alcance por ahora

- **Aforo por paradero**: requiere bajadas por paradero, que no existen (solo hay validaciones de subida).
  Se podría aproximar con trip-chaining (Barry et al. 2002; Munizaga y Palma 2012) o simetría de sentidos,
  pero no tendría ground truth para validarlo.
- **Más de un transbordo** y transbordos con trayectos largos a pie: requieren un grafo de la red.
- **Posición real de buses**: no hay fuente.

## Datos de referencia

| Tabla / vista / función | Uso |
|---|---|
| `paradero` | Coordenadas, `calidad_coord`, `confianza`, `precision_coord` |
| `ruta` | `codigo` (el servicio), `sistema`, `tiene_trazado`, `origen_trazado` |
| `paradero_ruta` | `direccion`, `orden`, `unidad_modelo` |
| `prediccion` | Aforo y ETA del modelo |
| `trafico_en_vivo` | Congestión en tiempo real (TomTom o fallback) |
| `paraderos_cercanos()` | Paraderos por radio con sus rutas |
| `tramo` | Distancia y tiempo estimado entre paradas consecutivas (`fiable`) |
| `headway_sistema` | Intervalo entre buses por sistema y tipo de día |
| `feriado` | Feriados nacionales 2025-2026 (tipo de día `DOM`) |
| `transbordo_cercano` | Pares de paraderos a ≤ 300 m |
| `rutas_directas()`, `rutas_transbordo()` | Opciones de viaje origen → destino |
| `log_inferencia`, `feedback_usuario` | Registro de uso y de feedback |
