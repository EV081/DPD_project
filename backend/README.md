# UrbanSafe Backend API

API REST y motor de inferencia analítica desarrollado para **UrbanSafe**, responsable de gestionar la autenticación de usuarios (JWT), procesar el proxy geoespacial de OpenStreetMap y ejecutar los modelos predictivos de Machine Learning (LightGBM) para la afluencia en el transporte público de Lima Metropolitana.

## Modelo de predicción (v2)

- **Demanda:** LightGBM por sistema, pronóstico horario de subidas (validaciones ATU); en alimentadores, por ruta × sentido (v1.2.0). Es el modelo de producción: en el test retenido iguala o supera al ensemble con Chronos y corre en milisegundos. Las métricas de test son fuera de muestra (reentrenado solo con días previos).
- **Ocupación a bordo (los 4 sistemas):** matriz origen-destino estimada solo con subidas, con bajadas por viaje de retorno. Metro L1 y troncal: línea doblemente acotada (Furness). Corredores: por ruta y sentido a nivel de paradero (acotada a orígenes). Alimentadores: carga crítica junto a la estación de integración. Los pasajeros por vehículo salen del horario oficial (Metro) o de la flota publicada (buses). Clases por densidad de pie: Asientos, De pie, Saturado. Detalle, evaluación en test y fuentes en [docs/MODELO_OCUPACION.md](docs/MODELO_OCUPACION.md).
- **Tráfico en vivo:** en corredores y alimentadores el ETA de la hora actual se multiplica por la congestión TomTom (`services/trafico.py`, factor 1–1.5, caché de 5 min, requiere `API_TOMTOM`). La respuesta trae `eta_base_min`, `factor_trafico` y `modo_datos` (`en_vivo`, `reciente`, `historico`). Es una hipótesis no entrenada: se valida con `/api/feedback/resumen`.
- **Fechas:** hora de Lima. Para fechas posteriores a 2025 se usa el día homólogo de 2025 con datos ATU (mismo día de la semana y tipo de día), declarado en `referencia`.
- **Endpoints:**

| Endpoint | Uso |
|---|---|
| `GET /api/predictions/estacion/<station_id>?dia&hour&hacia_id` | Estado actual + 24 h de un paradero en una sola llamada (recomendado) |
| `GET /api/predictions/<sistema>/<serie>?dia&hour&sentido\|hacia` | Una hora |
| `GET /api/predictions/<sistema>/<serie>/forecast?dia&hours&desde_hora&sentido\|hacia` | Horas del día |
| `POST /api/feedback` (JWT) | "Ya abordé": espera real vs ETA mostrado y aforo percibido (opcional) |
| `GET /api/feedback/resumen` (JWT) | Error del ETA (MAE y sesgo) y acierto del aforo, global y por modo de tráfico |
| `GET /api/stations` | Cada estación trae `model_system` y `model_series` (`null` = sin datos ATU, no se inventa la predicción) |

- **Integración con el frontend:** [docs/INTEGRACION_FRONTEND.md](docs/INTEGRACION_FRONTEND.md) (implementada en la rama `feat/aforo-v2-integracion` del frontend).

## Eje 2: ruta peatonal segura y reportes

`/api/eje2` responde "si estoy a ~10 min de una estación o paradero, ¿qué camino es más seguro?" (ruta normal y segura con la recomendada y su explicación), muestra el índice de seguridad de
estaciones/paraderos y recibe **reportes de usuarios** (acoso, seguimiento, robo) que recalibran el riesgo de forma acotada. Las tablas que crecen (`reporte_seguridad`, `validacion_hora`) son
**particionadas por mes en Postgres**, y hay pipelines diario y semanal (`flask --app app pipeline-diario | pipeline-semanal`, pensados para Cron Jobs). Todo está en
[`docs/EJE2_RUTA_SEGURA.md`](docs/EJE2_RUTA_SEGURA.md); el contrato para el frontend, en [`docs/INTEGRACION_FRONTEND.md`](docs/INTEGRACION_FRONTEND.md).

## Arquitectura

Esta API (Flask, desplegada en Render) es **la arquitectura del producto**. No hay base de datos de
demanda: los modelos y su contexto viajan como archivos versionados.

```
App (Expo) ──HTTP──► Flask API
                      ├─ routes/        auth (SQLite, solo usuarios), stations, geo, predictions
                      ├─ services/      model_service (caché de modelos y pronósticos), calendario
                      │                 (hora de Lima, feriados, día homólogo), mapeo_estaciones
                      ├─ model/         inferencia (LightGBM), od_matrix (Furness/gravedad),
                      │                 ocupacion (capas por sistema)
                      ├─ models/        artefactos versionados + manifest.json (sha256)
                      └─ data/          context/<sistema>_2025.parquet (validaciones ATU), geo/
```

El repositorio del curso (`EV081/DPD_project`, carpeta `deliveries/week10`) contiene además un
flujo con PostgreSQL (`rutas_directas()`, tabla `prediccion`, ajuste con TomTom, `feedback_usuario`)
y el pipeline de ingesta y entrenamiento. **La app no usa ese flujo de base de datos**: lo reemplaza
esta API con archivos versionados. El pipeline de entrenamiento y los datos limpios del repo del
curso sí son la fuente de los artefactos de `models/` y de `data/context/`.
- **Tests:** 196 pruebas (algoritmo de Furness contra la Tabla 5.7 de Ortúzar y Willumsen, calendario, API, latencia P95, Eje 2). Usan un **Postgres de pruebas aparte** (nunca la base de desarrollo):
  `docker compose --profile test up -d db-test` y luego `cd backend && pip install pytest && python -m pytest`. Ver `docs/EJE2_RUTA_SEGURA.md` (sección 8).
- **Versión de modelos: 1.3.0** (`models/manifest.json`; la API verifica los sha256 al cargar).
- **Regenerar o evaluar:** `python scripts/construir_linea_metro_l1.py`, `python scripts/construir_linea_troncal.py`, `python scripts/construir_rutas_bus.py --datos <DPD_project>/deliveries/week10/data_processed/clean`, `python scripts/entrenar_alimentador_sentido.py --datos <...>/clean`, `python scripts/evaluar_od_metro_l1.py`, `python scripts/evaluar_ocupacion.py` y `python scripts/serializar_modelos.py <versión> "<cambios>"`.


## Stack Tecnológico
* **Lenguaje:** Python 3.10+
* **Framework Web:** Flask
* **Machine Learning:** LightGBM, Scikit-Learn, NumPy (matriz O-D)
* **Control de Tráfico / Geo:** Requests, OpenStreetMap Nominatim API Integration


## Configuración y Ejecución Local

### 1. Requisitos Previos
* Tener instalado **Python 3.10 o superior** y `pip`.

### 2. Clonar el Repositorio e Instalar Dependencias
Abre tu terminal en la carpeta del backend y ejecuta los siguientes comandos:

```bash
# Instalar las librerías y dependencias necesarias
pip install -r requirements.txt
```
### 3. Configurar Variables de Entorno
Copia la plantilla y completa los valores (`backend/.env` está ignorado por git):

```bash
cp .env.example .env
```

| Variable | Uso |
|---|---|
| `JWT_SECRET_KEY` | Firma de los tokens de sesión (obligatoria en producción) |
| `LOCATIONIQ_TOKEN` | Autocompletado de destinos |
| `DATABASE_URL` | Base de usuarios. Vacía = SQLite local; en producción, Postgres |
| `PORT` | Solo local; Render lo define |
| `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, `SEED_ADMIN_NAME` | Cuenta de **administrador** (acceso a Simulación y al Panel operacional). Clave: mínimo 8 caracteres |
| `SEED_ADMIN_ON_START` | `1` (por defecto) crea/actualiza al administrador al arrancar; `0` lo desactiva |

### 3.1 Administrador y roles
- Roles: `user` (por defecto) y `admin`. El registro público **siempre** crea `user`; el rol nunca se acepta desde el cliente.
- Al arrancar la API (o con `flask --app app seed-admin`) se crea o actualiza al administrador con las variables `SEED_ADMIN_*` del `.env`.
  Es idempotente: si el correo ya existe se promueve a `admin`, y el `.env` manda sobre el nombre y la contraseña.
  Sin las variables no se crea nada (la API arranca igual).
- Solo `admin` puede usar `GET /api/admin/dashboard` (panel operacional) y `GET /api/feedback/resumen`. El rol se lee de la base en cada petición:
  degradar a alguien le quita el acceso aunque conserve un token vigente.
- Bases anteriores a los roles: al arrancar se agrega la columna `users.role` automáticamente.
- El panel solo devuelve agregados: nunca reportes individuales, ubicaciones, correos ni identificadores de usuarios.
- Privacidad: existen cuentas (nombre y correo) y los reportes del Eje 2 guardan `user_id`; esto debe reflejarse en la descripción del RNF-05 de los requisitos.

### 4. Ejecutar la aplicacióm
Inicia el servidor local ejecutando el archivo principal:

```bash
python app.py
```
El servidor se levantará por defecto en `http://localhost:5000` o el puerto configurado).

---

## Instrucciones de Despliegue (Deployment en Render)

El backend está configurado para desplegarse de manera automatizada en la plataforma en la nube **Render**:

### 1. Conectar el Repositorio

Conecta el repositorio de GitHub (https://github.com/Alessandromg18/Backend_UrbanSafe.git) a un nuevo **Web Service** en Render.

### 2. Configurar el Comando de Inicio (`Procfile`)

El repositorio incluye un archivo `Procfile` en la raíz que indica a Render cómo arrancar la aplicación de Python de forma automática.

### 3. Variables de Entorno en Producción

En el panel de Render (**Environment**) define `JWT_SECRET_KEY`, `LOCATIONIQ_TOKEN` y `DATABASE_URL`
(la URL de tu Postgres). Sin `DATABASE_URL` se usa SQLite, que se borra en cada redeploy y **no soporta** las tablas particionadas ni el pipeline del Eje 2: usa Postgres.
Cada worker carga su copia de los modelos y del grafo del Eje 2 (~100 MB): en servidores de 512 MB usa `WEB_CONCURRENCY=1`.

### 3.2. Jobs programados (Render → Cron Jobs)

Crea dos Cron Jobs con el mismo repositorio, `DATABASE_URL` y variables que el servicio web:

| Job | Comando | Programación (UTC) |
|---|---|---|
| Diario | `flask --app app pipeline-diario` | `0 8 * * *` (03:00 Lima) |
| Semanal | `flask --app app pipeline-semanal` | `0 7 * * 1` (lunes 02:00 Lima) |

Cada corrida queda registrada en la tabla `pipeline_ejecucion` (`ok`, `sin_datos` o `error`) y `GET /api/eje2/estado` muestra el último job.

### 4. Despliegue Automático

Cada vez que realices un `git push` a la rama principal, Render recompilará las dependencias a partir de `requirements.txt` y actualizará el servicio en línea.
