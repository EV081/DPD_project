# Eje 2 en el backend — ruta peatonal segura, reportes de usuarios y pipelines

Pregunta que responde: **si estoy a ~10 minutos caminando de una estación o paradero y quiero llegar a ella, ¿qué camino es más seguro?**
(Metro L1, Metropolitano, corredores y alimentadores). El modelo, su evaluación y las decisiones están en
`deliveries/week12/docs/Model_Eje2.md`; este documento describe cómo funciona **dentro del servidor**.

> El riesgo es de **denuncias registradas** (hay subregistro y sesgo social): no es la probabilidad de ser víctima.
> En una emergencia se llama al **105**.

## 1. Piezas

| Pieza | Archivo | Qué hace |
|---|---|---|
| Artefactos | `data/eje2/` (7,5 MB, versionados) | `grafo.parquet` (146 607 calles con riesgo 0-1 de día/noche/total), `nodos.parquet`, `geometrias.parquet`, `accesos.parquet` (1 775 estaciones/paraderos con su índice de seguridad), `manifest.json` (versión, λ, `datos_hasta`, sha256) |
| Exportación | `scripts/exportar_eje2.py` | Copia y reduce los resultados de `deliveries/week12` a `data/eje2/`. `geopandas` solo se usa aquí; el servidor no lo necesita |
| Ruteo | `services/eje2_service.py` | Grafo en memoria, Dijkstra (scipy), explicación de la ruta, índice por acceso |
| Reportes | `services/eje2_reportes.py` | Validación, límites por usuario, recalibración del riesgo, caché de ajustes |
| API | `routes/eje2.py` (`/api/eje2`) | Endpoints de la sección 2 |
| Base de datos | `db/tablas.py`, `db/particiones.py` | Tablas nuevas y particionado mensual de Postgres |
| Jobs | `cli.py` (`flask --app app ...`) | Particiones, recalibración, monitoreo y calibración semanal |

## 2. API (`/api/eje2`; documentada también en Swagger, `/apidocs`)

| Método y ruta | Auth | Qué hace |
|---|---|---|
| `POST /ruta` | pública | Ruta normal y segura hasta una estación/paradero, con la recomendada y su explicación |
| `GET /accesos/cercanos?lat&lon&radius&limit` | pública | Estaciones/paraderos cercanos con Seguridad %, base del tipo, intervalo y confianza |
| `GET /accesos/<acceso_id>` · `GET /accesos/por-estacion/<station_id>?sistema=` | pública | Índice de un acceso (el `station_id` de `/api/stations` se une por sistema + coordenada ≤ 50 m) |
| `POST /reportes` | JWT | Reporta `acoso`, `seguimiento` o `robo` en una calle |
| `GET /reportes/mios` · `DELETE /reportes/<id>` | JWT | Solo los propios; borrar marca el reporte como `retirado` |
| `GET /estado` | pública | Versión y antigüedad del riesgo base, λ, ajuste por reportes y último job |

### `POST /api/eje2/ruta`

```json
{ "origen": {"lat": -12.0486, "lon": -77.0305},
  "destino": {"acceso_id": "metro_l1_0003"},              // o {"station_id": "...", "sistema": "metro_l1"}  o {"lat": ..., "lon": ...}
  "preferencia": "segura",                                 // "segura" (por defecto) | "normal"
  "franja": "noche",                                       // opcional; por defecto la de la hora de salida en Lima
  "salida": "2026-11-02T21:30:00-05:00",                   // opcional
  "lambda": 12 }                                           // opcional, 0 a 50 (valor validado: 12)
```

Siempre devuelve **las dos rutas**; `preferencia` solo marca cuál queda `seleccionada`:

```json
{ "seleccionada": "segura", "recomendada": "segura",       // "segura" | "normal" | "misma"
  "franja": "noche",
  "destino": {"acceso_id": "metro_l1_0003", "nombre": "...", "seguridad_pct": 62, "intervalo_pct": [48, 75], "base_tipo_pct": 68, "confianza": "alta"},
  "comparacion": {"distancia_extra_m": 87.0, "distancia_extra_pct": 0.13, "minutos_extra": 1.1, "reduccion_riesgo_pct": 0.68},
  "rutas": {
    "normal": {"distancia_m": 660.1, "minutos": 8.3, "banda_riesgo": "alto",  "densidad_media_km_anio": 41.2, "geojson": {...LineString...}, "tramos": [...]},
    "segura": {"distancia_m": 747.3, "minutos": 9.3, "banda_riesgo": "medio", "densidad_media_km_anio": 13.1, "geojson": {...LineString...},
               "tramos": [{"nombre": "Jr. X", "largo_m": 120, "riesgo": "bajo", "desvio": true}, ...]}},
  "explicacion": {
    "resumen": "La ruta segura es 87 m más larga (+13%, +1.1 min) y reduce 68% las denuncias registradas esperadas por metro (franja noche).",
    "motivos": ["El tramo evitado (180 m, por Av. Y) tiene riesgo alto en la franja noche: ~210 % más denuncias registradas por km que el tramo alternativo."],
    "tramos_evitados": [{"nombre": "Av. Y", "largo_m": 180}],
    "condiciones": {"franja": "noche", "franja_regla": "noche de 18:00 a 05:59 (hora de Lima); día el resto", "lambda": 12.0,
                    "forma_costo": "lineal", "datos_hasta": "2024-08-31", "version": "eje2-ruta-v1.0",
                    "recomendacion_si": "la ruta segura reduce el riesgo por metro ≥ 10% y el camino extra es ≤ max(30%, 250 m)",
                    "reportes_aplicados": false},
    "aviso": "Basado en denuncias registradas ... En una emergencia llama al 105.", "llamar_105": true } }
```

**Cuándo se recomienda la segura:** si reduce el riesgo por metro ≥ 10 % **y** el camino extra es ≤ max(30 %, 250 m). Si no, se recomienda la normal y
`explicacion.resumen` dice por qué ("No recomendamos la ruta segura: exigiría 520 m más de camino (+80%) para una mejora de riesgo de solo 6%"). Si ambas rutas coinciden,
`recomendada = "misma"` ("la ruta más corta ya es la más segura").

Errores: `400` entrada inválida · `404` destino inexistente · `422` origen fuera de la cobertura (a más de 150 m de una calle del grafo) o a más de 2,5 km caminando del destino.

### `POST /api/eje2/reportes` (requiere `Authorization: Bearer <token>`)

```json
{ "tipo": "acoso", "lat": -12.0486, "lon": -77.0305, "ocurrido_en": "2026-11-02T21:30:00-05:00" }   // ocurrido_en opcional (hasta 24 h atrás)
```

→ `201` con `{"id", "calle", "franja", "llamar_105": true, "numero_emergencia": "105", "aviso", "mensaje", "nota"}`.
**Sin texto libre** (no se guardan nombres ni acusaciones). `422` si el punto no está a ≤ 40 m de una calle cubierta.
`429` por límite: 5 reportes por hora, 20 por día, y no se repite la misma calle en una hora (`EJE2_REPORTES_POR_HORA`, `EJE2_REPORTES_POR_DIA`).

## 3. Cómo se calcula la ruta

Costo por calle `largo × (1 + λ · riesgo)`; λ = 0 es la ruta más corta y λ = 12 el valor validado (reduce 43,8 % el riesgo realizado en el test con 8,7 % de desvío medio).
`riesgo = clip(riesgo_modelo + ajuste_por_reportes, 0, 1)`. Se resuelve con `scipy.sparse.csgraph.dijkstra`: la estructura CSR del grafo se arma una vez por proceso y por consulta
solo cambia el vector de costos. La franja sale de la hora de salida en Lima (noche 18:00–05:59). El riesgo base no depende de la fecha, solo de la franja; la respuesta siempre declara `datos_hasta`.

## 4. Reportes de usuarios y recalibración

Los reportes **no reentrenan el modelo**: corrigen el riesgo de una zona de forma acotada (hipótesis, no entrenada). Reglas de `calcular_ajustes` (`services/eje2_reportes.py`):

- cuentan los reportes de los últimos **90 días**, con peso `0,5^(edad/30 días)`;
- una persona cuenta **una vez por segmento y día**;
- la **zona** es la calle y sus vecinas hasta 2 saltos (~150–250 m); solo hay ajuste con **≥ 3 reportes de ≥ 2 personas distintas** en la zona;
- `delta = 0,30 × (1 − exp(−n_efectivo / 5))`, con efecto pleno en la calle reportada y 0,5× y 0,25× en las vecinas; nunca pasa de +0,30;
- sin nuevos reportes el ajuste **desaparece solo** (vuelve al valor del modelo);
- `EJE2_AJUSTE_ACTIVO=0` apaga el efecto sin perder los reportes. Parámetros: `EJE2_VENTANA_DIAS`, `EJE2_VIDA_MEDIA_DIAS`, `EJE2_MIN_REPORTES`, `EJE2_MIN_USUARIOS`, `EJE2_AJUSTE_TOPE`, `EJE2_AJUSTE_N0`.

Con poco uso (por ejemplo 2 reportes por semana en toda Lima) rara vez se cumplirán los umbrales: es lo esperado y evita que un reporte aislado o malicioso cambie una ruta.

**Privacidad:** nunca se exponen reportes individuales ni usuarios (las respuestas públicas solo traen datos agregados); el usuario puede ver y retirar los suyos; las coordenadas se guardan con 5 decimales;
al borrar la cuenta, `user_id` queda en `NULL` (`ON DELETE SET NULL`).

## 5. Base de datos y particionado

| Tabla | Particionado | Para qué |
|---|---|---|
| `reporte_seguridad` | **mensual** por `creado_en` | reportes (PK `(id uuid, creado_en)`) |
| `validacion_hora` | **mensual** por `fecha_hora` | conteo por hora de validaciones; `fuente='app'` = cada "Ya abordé" (`'atu'` queda reservado) |
| `ajuste_riesgo_segmento` | no | ajuste por calle y franja (lo escribe `eje2-recalibrar`) |
| `monitoreo_modelo` | no | métricas semanales del feedback (ETA, aforo, abordajes) y alertas |
| `calibracion_modelo` | no | factor del ETA versionado (campeón / retador / archivado) |
| `pipeline_ejecucion` | no | bitácora de los jobs |

En **Postgres** las tablas grandes se crean con `PARTITION BY RANGE` (una partición por mes, `<tabla>_AAAA_MM`, más una `DEFAULT` de seguridad); `init_db` crea el mes anterior y los 3 siguientes al arrancar.
`flask --app app db-particiones` crea lo que falte y retira las particiones de más de 24 meses (reportes) o 36 (validaciones): `RETENCION_MESES_REPORTES`, `RETENCION_MESES_VALIDACIONES`.
Si algún registro cae en la partición `DEFAULT`, al crear su mes se mueve solo. Los límites de mes son en UTC para `reporte_seguridad` (timestamptz) y en hora de Lima para `validacion_hora`.
El servidor **no soporta SQLite para estas tablas** (no hay particionado ni `ON CONFLICT` equivalente): usa Postgres en desarrollo y producción.

## 6. Pipelines (`flask --app app <comando>`)

| Comando | Qué hace | Cuándo |
|---|---|---|
| `db-particiones [--adelante 3]` | crea particiones futuras y retira las viejas | diario |
| `eje2-recalibrar` | reportes → `ajuste_riesgo_segmento` | diario |
| `pipeline-diario` | `db-particiones` + `eje2-recalibrar` | **diario** (p. ej. 03:00 Lima = `0 8 * * *` UTC) |
| `monitoreo-semanal [--hoy AAAA-MM-DD]` | métricas de la última semana completa y alertas | semanal |
| `calibrar-eta` | re-ajusta el factor del ETA (campeón vs retador) | semanal |
| `pipeline-semanal` | particiones + monitoreo + calibración | **lunes 02:00 Lima = `0 7 * * 1` UTC** |
| `monitoreo-resumen` | imprime las últimas métricas | a demanda |

Cada corrida queda en `pipeline_ejecucion` (`ok`, `sin_datos` o `error`). En Render se programan como **Cron Jobs** con el mismo `DATABASE_URL` y el comando
`flask --app app pipeline-diario` (o `pipeline-semanal`); en Docker: `docker compose --profile backend-pipeline run --rm backend-pipeline pipeline-diario`.
Los jobs **no se exponen por HTTP**. El servidor web recarga los ajustes por reportes revisando `max(actualizado_en)` cada 60 s (`EJE2_AJUSTES_TTL_S`).

### Eje 1: validaciones de la app, monitoreo y calibración del ETA

- Cada `POST /api/feedback` ("Ya abordé") suma 1 a `validacion_hora` (`fuente='app'`). Son validaciones **de la app**, un subconjunto pequeño y sesgado de los viajeros:
  **no se mezclan con las validaciones ATU** con que se entrenó LightGBM y no lo reentrenan.
- `monitoreo-semanal` calcula por sistema el error del ETA (MAE y sesgo), el acierto del aforo y los abordajes, y marca **alerta** con ≥ 30 respuestas si |sesgo| > 3 min, MAE > 5 min o acierto < 50 %
  (`MONITOREO_MIN_N`, `MONITOREO_SESGO_MIN`, `MONITOREO_MAE_MIN`, `MONITOREO_ACIERTO_MIN`).
- `calibrar-eta` ajusta `espera_real ≈ k × (ETA del modelo × factor de tráfico)` con los últimos 56 días, con **contracción hacia 1** (`k = 1 + (k_obs − 1)·n/(n + 100)`) y tope [0,8; 1,4]; requiere ≥ 100 respuestas para ajustar y ≥ 20 para validar,
  evalúa con las 2 últimas semanas (que no se usaron para ajustar) y **solo promueve** si el error baja ≥ 5 % y el factor cambia ≥ 3 %. La versión anterior queda `archivado` (se puede volver atrás).
  `services/trafico.ajustar_item` aplica el campeón al ETA de la hora actual y lo declara en la respuesta (`factor_calibracion`; `eta_base_min` conserva el ETA del modelo). Interruptor: `ETA_CALIBRACION_ACTIVA=0`.
- **No se reentrena LightGBM del aforo** (ni el riesgo del Eje 2) con datos de la app: son miles de veces menos datos, de un subconjunto sesgado y de otra naturaleza. El calendario del Eje 1 sigue usando el día homólogo de 2025
  para cualquier fecha (p. ej. el 1-nov-2026 responde con el 1-nov-2025 y lo declara).

## 7. Rendimiento medido (`pytest tests/test_latencia_eje2.py -s`, datos reales)

| Operación | Mediana | p95 | Objetivo |
|---|---:|---:|---:|
| `POST /ruta` (400–750 m y hasta ~2 km caminando) | 2 ms | 3 ms | ≤ 1,0 s |
| `GET /accesos/cercanos` | 0,9 ms | 1,0 ms | ≤ 0,2 s |
| `POST /reportes` (con validación y escritura en Postgres) | 5,7 ms | 9,2 ms | ≤ 0,3 s |
| Carga del grafo (una vez por proceso) | 0,2 s | – | ≤ 5 s |

**Memoria:** el grafo ocupa ~95 MB por proceso (~140 MB con el índice de calles para reportes, que se arma al recibir el primer reporte). Cada worker de gunicorn carga su propia copia
(`WEB_CONCURRENCY`, 2 por defecto en el `Dockerfile`; usa 1 en servidores de 512 MB). `EJE2_PRECALENTAR=0` evita cargarlo al arrancar.

## 8. Pruebas

```bash
docker compose --profile test up -d db-test            # Postgres de pruebas: puerto 5433, en memoria, distinto del de desarrollo
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest                              # 196 pruebas
```

Las pruebas **nunca tocan la base de desarrollo ni la de producción**: solo leen `TEST_DATABASE_URL` (se ignora `DATABASE_URL`), el nombre de la base debe terminar en `_test` y el esquema se reinicia únicamente ahí.
Cobertura del Eje 2: ruteo sobre un grafo sintético y sobre los datos reales (`test_eje2_ruteo.py`), recalibración pura (`test_eje2_recalibracion.py`), API y privacidad (`test_eje2_api.py`),
particionado en Postgres real (`test_particiones.py`), flujos de punta a punta (`test_flujo_eje2.py`, `test_flujo_eje1.py`), calibración y monitoreo (`test_eje1_calibracion.py`) y latencia/memoria (`test_latencia_eje2.py`).

## 9. Actualizar el riesgo base

No llegarán más archivos SIDPOL (no hay API y la extracción fue manual): el riesgo base queda con datos hasta `datos_hasta` (agosto de 2024). Si algún día se reentrena en `deliveries/week12`,
`python backend/scripts/exportar_eje2.py` regenera `data/eje2/` (con un entorno que tenga `geopandas`) y el despliegue lo recoge sin más cambios.

## 10. Variables de entorno del Eje 2

| Variable | Defecto | Efecto |
|---|---|---|
| `EJE2_PRECALENTAR` | `1` | carga el grafo al arrancar |
| `EJE2_AJUSTE_ACTIVO` | `1` | `0` apaga el efecto de los reportes en las rutas |
| `EJE2_REPORTES_POR_HORA` / `EJE2_REPORTES_POR_DIA` | 5 / 20 | límites por usuario |
| `EJE2_VENTANA_DIAS`, `EJE2_VIDA_MEDIA_DIAS`, `EJE2_MIN_REPORTES`, `EJE2_MIN_USUARIOS`, `EJE2_AJUSTE_TOPE`, `EJE2_AJUSTE_N0` | 90, 30, 3, 2, 0,30, 5 | parámetros de la recalibración |
| `EJE2_AJUSTES_TTL_S` | 60 | cada cuánto el servidor revisa si hay ajustes nuevos |
| `ETA_CALIBRACION_ACTIVA` | `1` | `0` desactiva el factor de calibración del ETA |
| `MONITOREO_MIN_N`, `MONITOREO_SESGO_MIN`, `MONITOREO_MAE_MIN`, `MONITOREO_ACIERTO_MIN` | 30, 3, 5, 0,5 | umbrales de alerta |
| `RETENCION_MESES_REPORTES` / `RETENCION_MESES_VALIDACIONES` | 24 / 36 | meses que se conservan |
| `WEB_CONCURRENCY` | 2 | workers de gunicorn (Docker) |

## 11. Limitaciones

- Denuncias ≠ delito: subregistro (muy alto en acoso y violencia sexual), sesgo de quién denuncia y de dónde se registra. El índice de los alimentadores sale "muy seguro" sobre todo por menos registro en zonas periféricas.
- El ordenamiento de calles es una tendencia (Spearman ≈ 0,41), no una garantía por calle; la mejora medida es sobre denuncias registradas.
- Solo hay riesgo dentro de los ~10 min de una estación o paradero; el grafo no tiene calles fuera de esas zonas. El punto del usuario se ajusta a la calle más cercana (≤ 150 m).
- El riesgo base refleja hasta agosto de 2024. Con poco uso, los reportes casi nunca cambiarán una ruta.
- La recalibración por reportes y la calibración del ETA son hipótesis acotadas (tope, umbrales, decaimiento, interruptor), no modelos entrenados.
- 201 paraderos de `puntos_corredores` no tienen punto de acceso a ≤ 50 m: se enrutan hacia su coordenada, sin índice de seguridad.
