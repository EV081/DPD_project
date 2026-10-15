# Backend: flujo de recomendación de paraderos

Diseño del flujo "estoy en un lugar y quiero ir a otro". **Aún no está implementado**: este documento
define qué debe hacer el backend con los datos y el modelo que ya existen.

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
                      ├─ 2. SQL: rutas_origen_destino(lat_o, lon_o, lat_d, lon_d)
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

Función SQL pendiente: `rutas_origen_destino(lat_o, lon_o, lat_d, lon_d, radio_m DEFAULT 800)`.

Para cada ruta devuelve una fila si cumple:

1. Tiene un paradero a ≤ `radio_m` del origen y otro a ≤ `radio_m` del destino.
2. En `paradero_ruta`, ambos paraderos tienen la misma `direccion` y `orden` del origen < `orden` del
   destino (garantiza el sentido correcto).

Columnas esperadas: `ruta_id`, `sistema`, `codigo`, `direccion`, `paradero_subida`, `paradero_bajada`,
`orden_subida`, `orden_bajada`, `dist_origen_m`, `dist_destino_m`, `unidad_modelo`.

Se apoya en lo que ya existe: `paraderos_cercanos()`, `paradero_ruta`, `ruta` y la vista `ruta_paradas`.

Cómo leer `direccion` y `orden` (ver `orden_origen` en `paradero_ruta`):

| Caso | Regla para validar el sentido |
|---|---|
| `direccion` 1 o 2 (`atu_secuencia`) | `orden_subida < orden_bajada` en la misma `direccion` |
| `metro_l1` (`atu_secuencia`) y `troncal` (`latitud_troncal`), `direccion = 0` | Línea bidireccional: vale cualquier par de estaciones; el sentido es el signo de `orden_bajada − orden_subida` |
| corredores con `direccion = 0` (`catalogo_n_paradero`) | El orden recorre ida y vuelta: exigir `orden_subida < orden_bajada` y compararlo solo con enlaces `direccion = 0` de la misma ruta |

Ningún enlace tiene `orden` NULL. Los enlaces `catalogo_n_paradero` y `latitud_troncal` son menos fiables que los
de ATU: conviene mostrarlos con menor prioridad en el ranking.

El tiempo de un tramo sale de la tabla `tramo` (`duracion_s`, estimada; ver el README de la semana) o, sin BD,
de `export/tramos.csv`. Al sumar tramos entre dos paradas hay que excluir los `fiable = false`.

Limitación: solo viajes **directos**, sin transbordos. Barranco → San Miguel probablemente requiera
combinar Metropolitano o Metro con un alimentador; eso queda como mejora futura.

### 3. Aforo, ETA y tráfico

| Dato | Fuente | Notas |
|---|---|---|
| `aforo`, `eta_min`, `eta2_min`, `recomendacion` | tabla `prediccion` (unida por `unidad_modelo`) | Por ruta, sentido y hora |
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

La distancia de `paraderos_cercanos()` es en línea recta y subestima. Para los 3-5 mejores candidatos se
consulta OSRM con perfil `foot`. Aproximación si OSRM no responde: 80 m/min sobre la distancia en línea recta.

### 5. Ranking

Puntaje propuesto (menor es mejor), por opción:

```
puntaje = t_caminata_origen + t_espera + penalización_aforo + t_caminata_destino
t_espera = eta_min              (o eta2_min si el aforo es "Saturado")
```

La penalización por aforo debe calibrarse; el modelo ya produce una `recomendacion` por clase de aforo
(ver `V.recomendaciones` en `code/model`).

## Respuesta esperada (borrador)

```json
{
  "origen": {"lat": -12.140, "lon": -77.021},
  "destino": {"lat": -12.077, "lon": -77.083, "texto": "San Miguel"},
  "opciones": [
    {
      "paradero": "Nombre del paradero",
      "sistema": "corredor",
      "ruta": "201",
      "sentido": 1,
      "caminata_min": 9,
      "eta_min": 8,
      "aforo": "Asientos",
      "recomendacion": "...",
      "fuente_trafico": "tomtom",
      "confianza_coord": "alta"
    }
  ]
}
```

## Fuera de alcance por ahora

- **Aforo por paradero**: requiere bajadas por paradero, que no existen (solo hay validaciones de subida).
  Se podría aproximar con trip-chaining (Barry et al. 2002; Munizaga y Palma 2012) o simetría de sentidos,
  pero no tendría ground truth para validarlo.
- **Transbordos**: requiere un grafo de la red, no solo `paradero_ruta`.
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
