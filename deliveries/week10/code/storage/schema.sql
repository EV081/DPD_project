-- 1. Tablas granulares

CREATE TABLE IF NOT EXISTS troncal_hora (
    id              BIGSERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    anio            SMALLINT,
    mes             SMALLINT,
    dia_semana      TEXT,
    tipo_dia        TEXT,
    semana_iso      SMALLINT,
    feriado         TEXT,
    es_feriado      BOOLEAN,
    estacion        TEXT NOT NULL,
    hora            SMALLINT NOT NULL,
    franja          TEXT,
    validaciones    DOUBLE PRECISION,
    log_val         DOUBLE PRECISION,
    es_outlier_iqr  BOOLEAN,
    era_celda_vacia BOOLEAN
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_troncal_hora
    ON troncal_hora (estacion, fecha, hora);

CREATE TABLE IF NOT EXISTS metro_l1_hora (
    id              BIGSERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    anio            SMALLINT,
    mes             SMALLINT,
    dia_semana      TEXT,
    tipo_dia        TEXT,
    semana_iso      SMALLINT,
    feriado         TEXT,
    es_feriado      BOOLEAN,
    estacion        TEXT NOT NULL,
    hora            SMALLINT NOT NULL,
    intervalo       TEXT,
    tipo_tarifa     TEXT NOT NULL,
    franja          TEXT,
    validaciones    DOUBLE PRECISION,
    log_val         DOUBLE PRECISION,
    es_outlier_iqr  BOOLEAN,
    era_celda_vacia BOOLEAN
);
-- Grano verificado sin colisiones: (estacion, fecha, hora, tipo_tarifa).
CREATE UNIQUE INDEX IF NOT EXISTS ux_metro_l1_hora
    ON metro_l1_hora (estacion, fecha, hora, tipo_tarifa);

CREATE TABLE IF NOT EXISTS metro_l1_total_hora (
    id              BIGSERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    anio            SMALLINT,
    mes             SMALLINT,
    dia_semana      TEXT,
    tipo_dia        TEXT,
    semana_iso      SMALLINT,
    feriado         TEXT,
    es_feriado      BOOLEAN,
    estacion        TEXT NOT NULL,
    hora            SMALLINT NOT NULL,
    franja          TEXT,
    validaciones    DOUBLE PRECISION,
    log_val         DOUBLE PRECISION,
    es_outlier_iqr  BOOLEAN,
    era_celda_vacia BOOLEAN
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_metro_l1_total_hora
    ON metro_l1_total_hora (estacion, fecha, hora);

CREATE TABLE IF NOT EXISTS corredores_hora (
    id                BIGSERIAL PRIMARY KEY,
    fecha             DATE NOT NULL,
    anio              SMALLINT,
    mes               SMALLINT,
    dia_semana        TEXT,
    tipo_dia          TEXT,
    semana_iso        SMALLINT,
    feriado           TEXT,
    es_feriado        BOOLEAN,
    ruta              TEXT NOT NULL,
    cod_paradero      TEXT,
    paradero          TEXT,
    sentido           TEXT,
    sentido_crudo     TEXT,
    sentido_norm      TEXT,
    eje               TEXT,
    hora              SMALLINT NOT NULL,
    franja            TEXT,
    validaciones      DOUBLE PRECISION,
    log_val           DOUBLE PRECISION,
    es_outlier_iqr    BOOLEAN,
    era_celda_vacia   BOOLEAN,
    tipo_dia_archivo  TEXT,
    tipo_dia_coincide BOOLEAN
);
-- Sin constraint de unicidad por diseño: se exige únicamente ausencia de
-- duplicados exactos (regresion cubierta por tests: 0 dups en la fuente parquet).

CREATE TABLE IF NOT EXISTS alimentador_hora (
    id              BIGSERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    anio            SMALLINT,
    mes             SMALLINT,
    dia_semana      TEXT,
    tipo_dia        TEXT,
    semana_iso      SMALLINT,
    feriado         TEXT,
    es_feriado      BOOLEAN,
    linea           TEXT NOT NULL,
    ruta            TEXT NOT NULL,
    sentido         TEXT,
    sentido_crudo   TEXT,
    sentido_norm    TEXT NOT NULL,
    eje             TEXT,
    n_paradero      TEXT NOT NULL,
    paradero        TEXT,
    hora            SMALLINT NOT NULL,
    franja          TEXT,
    validaciones    DOUBLE PRECISION,
    log_val         DOUBLE PRECISION,
    es_outlier_iqr  BOOLEAN,
    era_celda_vacia BOOLEAN
);
-- Grano verificado sin colisiones: (linea, ruta, n_paradero, fecha, hora,
-- sentido_norm). Los pares que colisionaban sin `linea` difieren en linea
-- (mismo paradero atendido por dos lineas en la misma hora).
CREATE UNIQUE INDEX IF NOT EXISTS ux_alimentador_hora
    ON alimentador_hora (linea, ruta, n_paradero, fecha, hora, sentido_norm);

CREATE TABLE IF NOT EXISTS alimentador_tarifa (
    id              BIGSERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    ruta            TEXT NOT NULL,
    hora            SMALLINT NOT NULL,
    tipo_tarifa     TEXT NOT NULL,
    validaciones    DOUBLE PRECISION
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_alimentador_tarifa
    ON alimentador_tarifa (fecha, ruta, hora, tipo_tarifa);


-- 2. Cobertura / fiabilidad por unidad
CREATE TABLE IF NOT EXISTS cobertura_unidad (
    sistema          TEXT NOT NULL,
    grano            TEXT NOT NULL,
    unidad           TEXT NOT NULL,
    dias_con_datos   SMALLINT,
    dias_esperados   SMALLINT,
    pct_cobertura    DOUBLE PRECISION,
    fiable           BOOLEAN,
    PRIMARY KEY (sistema, unidad)
);

-- 3. Vista de paridad: demanda fiable (réplica de demanda_consolidada_fiable)
--    Filas = grano de modelado:
--      corredor/alimentador -> por (ruta, sentido_norm)
--      troncal/metro_l1     -> por estacion (ruta y sentido = NULL)
CREATE OR REPLACE VIEW demanda_fiable AS
SELECT 'corredor'::text            AS sistema,
       'ruta'::text                AS grano,
       c.ruta                      AS unidad,
       c.ruta                      AS ruta,
       c.sentido_norm::text        AS sentido,
       c.fecha, c.anio, c.mes, c.dia_semana, c.tipo_dia, c.semana_iso,
       c.feriado, c.es_feriado, c.hora,
       c.validaciones::double precision AS validaciones,
       true                        AS _ok
FROM corredores_hora c
JOIN cobertura_unidad u
  ON u.sistema = 'corredor' AND u.unidad = c.ruta AND u.fiable

UNION ALL

SELECT 'alimentador'::text, 'ruta'::text,
       a.ruta, a.ruta, a.sentido_norm::text,
       a.fecha, a.anio, a.mes, a.dia_semana, a.tipo_dia, a.semana_iso,
       a.feriado, a.es_feriado, a.hora,
       a.validaciones::double precision, true
FROM alimentador_hora a
JOIN cobertura_unidad u
  ON u.sistema = 'alimentador' AND u.unidad = a.ruta AND u.fiable

UNION ALL

SELECT 'troncal'::text, 'estacion'::text,
       t.estacion, NULL::text, NULL::text,
       t.fecha, t.anio, t.mes, t.dia_semana, t.tipo_dia, t.semana_iso,
       t.feriado, t.es_feriado, t.hora,
       t.validaciones::double precision, true
FROM troncal_hora t
JOIN cobertura_unidad u
  ON u.sistema = 'troncal' AND u.unidad = t.estacion AND u.fiable

UNION ALL

SELECT 'metro_l1'::text, 'estacion'::text,
       m.estacion, NULL::text, NULL::text,
       m.fecha, m.anio, m.mes, m.dia_semana, m.tipo_dia, m.semana_iso,
       m.feriado, m.es_feriado, m.hora,
       m.validaciones::double precision, true
FROM metro_l1_total_hora m
JOIN cobertura_unidad u
  ON u.sistema = 'metro_l1' AND u.unidad = m.estacion AND u.fiable;


-- 4. Tablas de modelo
CREATE TABLE IF NOT EXISTS registro_modelo (
    id            BIGSERIAL PRIMARY KEY,
    nombre        TEXT NOT NULL,
    sistema       TEXT NOT NULL,
    version       TEXT,
    mejor_modelo  TEXT,
    wmape         DOUBLE PRECISION,
    mae           DOUBLE PRECISION,
    entrenado_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ruta_archivo  TEXT,
    notas         TEXT
);

CREATE TABLE IF NOT EXISTS prediccion (
    id                  BIGSERIAL PRIMARY KEY,
    registro_modelo_id  BIGINT NOT NULL REFERENCES registro_modelo (id),
    sistema             TEXT NOT NULL,
    unidad              TEXT NOT NULL,
    fecha               DATE NOT NULL,
    hora                SMALLINT NOT NULL,
    predicho            DOUBLE PRECISION NOT NULL,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_prediccion
    ON prediccion (sistema, unidad, fecha, hora);
ALTER TABLE prediccion
    ADD COLUMN IF NOT EXISTS aforo TEXT,
    ADD COLUMN IF NOT EXISTS eta_min DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS eta2_min DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS recomendacion TEXT,
    ADD COLUMN IF NOT EXISTS banda80_lo DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS banda80_hi DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS modelo TEXT;

CREATE TABLE IF NOT EXISTS log_inferencia (
    id              BIGSERIAL PRIMARY KEY,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    fuente          TEXT NOT NULL CHECK (fuente IN ('tomtom', 'fallback')),
    segmento        TEXT,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    latencia_ms     DOUBLE PRECISION,
    status          TEXT,
    ratio_congestion DOUBLE PRECISION,
    detalle         JSONB
);
CREATE INDEX IF NOT EXISTS ix_log_inferencia_creado
    ON log_inferencia (creado_en DESC);

CREATE TABLE IF NOT EXISTS feedback_usuario (
    id          BIGSERIAL PRIMARY KEY,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
    sistema     TEXT NOT NULL,
    unidad      TEXT NOT NULL,
    fecha       DATE,
    hora        SMALLINT,
    utilidad    SMALLINT CHECK (utilidad BETWEEN 1 AND 5),
    comentario  TEXT
);
-- Feedback mínimo (boton "Ya abordé"): espera real = t_aborde - t_consulta.
ALTER TABLE feedback_usuario ALTER COLUMN utilidad DROP NOT NULL;
ALTER TABLE feedback_usuario
    ADD COLUMN IF NOT EXISTS t_consulta TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS t_aborde TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS eta_mostrado_min DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS eta2_mostrado_min DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS aforo_mostrado TEXT,
    ADD COLUMN IF NOT EXISTS aforo_percibido TEXT,
    ADD COLUMN IF NOT EXISTS modo_datos TEXT,
    ADD COLUMN IF NOT EXISTS edad_snapshot_s DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS entorno TEXT NOT NULL DEFAULT 'prod';
DO $$ BEGIN
    ALTER TABLE feedback_usuario ADD CONSTRAINT ck_feedback_aforo_percibido
        CHECK (aforo_percibido IN ('Asientos', 'De_pie', 'Saturado'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE feedback_usuario ADD CONSTRAINT ck_feedback_entorno
        CHECK (entorno IN ('demo', 'prod'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 5. Trafico en vivo 
CREATE TABLE IF NOT EXISTS trafico_en_vivo (
    segmento            TEXT PRIMARY KEY,
    lat                 DOUBLE PRECISION,
    lon                 DOUBLE PRECISION,
    actual_speed_kph    DOUBLE PRECISION,
    free_flow_speed_kph DOUBLE PRECISION,
    ratio_congestion    DOUBLE PRECISION,
    fuente              TEXT NOT NULL CHECK (fuente IN ('tomtom', 'fallback')),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Historico de snapshots (trafico_en_vivo solo guarda el ultimo por segmento).
CREATE TABLE IF NOT EXISTS trafico_historico (
    id            BIGSERIAL PRIMARY KEY,
    segmento      TEXT NOT NULL,
    actual_kph    DOUBLE PRECISION,
    libre_kph     DOUBLE PRECISION,
    ratio         DOUBLE PRECISION,
    fuente        TEXT NOT NULL CHECK (fuente IN ('tomtom', 'fallback')),
    capturado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_trafico_historico
    ON trafico_historico (segmento, capturado_en DESC);

-- 6. Geografia de la red: paraderos, rutas y consulta de cercanos (sin PostGIS).
-- `unidad_modelo` enlaza con `prediccion.unidad` / demanda_fiable.unidad.
CREATE TABLE IF NOT EXISTS paradero (
    id         BIGSERIAL PRIMARY KEY,
    sistema    TEXT NOT NULL
               CHECK (sistema IN ('metro_l1', 'troncal', 'corredor', 'alimentador')),
    codigo     TEXT NOT NULL,
    nombre     TEXT NOT NULL,
    lat        DOUBLE PRECISION NOT NULL,
    lon        DOUBLE PRECISION NOT NULL,
    -- gps_atu: coordenada oficial; osm_nombre: aproximada por nombre en OSM;
    -- shapefile: estaciones del shapefile ATU (L1)
    calidad_coord TEXT NOT NULL,
    confianza  TEXT,
    UNIQUE (sistema, codigo)
);
-- gps_atu: coordenada oficial; osm_nombre: aproximada por nombre en OSM;
-- osm_secuencia: nombre ATU exacto + candidato OSM elegido por secuencia (validado: mediana ~20 m
-- sobre corredores); shapefile: estaciones del shapefile ATU (L1)
ALTER TABLE paradero ADD COLUMN IF NOT EXISTS confianza TEXT;
ALTER TABLE paradero ADD COLUMN IF NOT EXISTS precision_coord TEXT;
ALTER TABLE paradero ADD COLUMN IF NOT EXISTS evidencia TEXT;
ALTER TABLE paradero DROP CONSTRAINT IF EXISTS paradero_precision_check;
ALTER TABLE paradero ADD CONSTRAINT paradero_precision_check
    CHECK (precision_coord IN ('exacta', 'aproximada'));
ALTER TABLE paradero DROP CONSTRAINT IF EXISTS paradero_confianza_check;
ALTER TABLE paradero ADD CONSTRAINT paradero_confianza_check
    CHECK (confianza IN ('alta', 'media', 'baja', 'verificada'));
ALTER TABLE paradero DROP CONSTRAINT IF EXISTS paradero_sistema_check;
ALTER TABLE paradero ADD CONSTRAINT paradero_sistema_check
    CHECK (sistema IN ('metro_l1', 'troncal', 'corredor', 'alimentador'));
ALTER TABLE paradero DROP CONSTRAINT IF EXISTS paradero_calidad_coord_check;
ALTER TABLE paradero ADD CONSTRAINT paradero_calidad_coord_check
    CHECK (calidad_coord IN ('gps_atu', 'osm_nombre', 'osm_secuencia', 'shapefile', 'google_places', 'revision_humana'));
-- Sin NULLs: se completa por fuente de la coordenada y se exige NOT NULL (ver ingest_paraderos).
UPDATE paradero SET
    confianza = coalesce(confianza, CASE calidad_coord
        WHEN 'gps_atu' THEN 'alta' WHEN 'shapefile' THEN 'alta'
        WHEN 'revision_humana' THEN 'verificada' ELSE 'media' END),
    precision_coord = coalesce(precision_coord, CASE
        WHEN calidad_coord IN ('gps_atu', 'shapefile', 'revision_humana') THEN 'exacta'
        ELSE 'aproximada' END),
    evidencia = coalesce(evidencia, 'Completado por fuente: ' || calidad_coord)
WHERE confianza IS NULL OR precision_coord IS NULL OR evidencia IS NULL;
ALTER TABLE paradero ALTER COLUMN confianza SET NOT NULL;
ALTER TABLE paradero ALTER COLUMN precision_coord SET NOT NULL;
ALTER TABLE paradero ALTER COLUMN evidencia SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_paradero_geo ON paradero (lat, lon);

CREATE TABLE IF NOT EXISTS ruta (
    id         BIGSERIAL PRIMARY KEY,
    sistema    TEXT NOT NULL
               CHECK (sistema IN ('metro_l1', 'troncal', 'corredor', 'alimentador')),
    codigo     TEXT NOT NULL,
    nombre     TEXT NOT NULL,
    color_hex  TEXT,
    trazado    JSONB,          -- GeoJSON geometry (LineString / MultiLineString)
    nota       TEXT,
    -- shapefile_atu: eje oficial L1; osm_relation: relacion OSM route=bus;
    -- derivado_osrm: calculado por calles entre paraderos (NO es el trazado oficial)
    origen_trazado TEXT,
    UNIQUE (sistema, codigo)
);
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS origen_trazado TEXT;
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS n_paradas INTEGER;
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS pct_exactas SMALLINT;
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS tiene_trazado BOOLEAN NOT NULL DEFAULT false;
-- 'sin_trazado': ATU no publica geometria para la ruta (trazado queda NULL; solo paradas)
ALTER TABLE ruta DROP CONSTRAINT IF EXISTS ruta_origen_trazado_check;
ALTER TABLE ruta ADD CONSTRAINT ruta_origen_trazado_check
    CHECK (origen_trazado IN ('shapefile_atu', 'osm_relation', 'derivado_osrm', 'sin_trazado'));

CREATE TABLE IF NOT EXISTS paradero_ruta (
    paradero_id    BIGINT NOT NULL REFERENCES paradero (id) ON DELETE CASCADE,
    ruta_id        BIGINT NOT NULL REFERENCES ruta (id) ON DELETE CASCADE,
    direccion      SMALLINT NOT NULL DEFAULT 0,   -- 0 = sin sentido publicado
    orden          INTEGER,                        -- posicion en la ruta/direccion (ATU)
    unidad_modelo  TEXT,       -- unidad con prediccion (NULL si no hay demanda)
    PRIMARY KEY (paradero_id, ruta_id, direccion)
);
-- atu_secuencia: orden publicado por ATU (por sentido); catalogo_n_paradero: ranking del correlativo
-- n_paradero del catalogo de la ruta (ida y vuelta, direccion 0): solo comparable con direccion 0;
-- latitud_troncal: estaciones de la troncal ordenadas de sur a norte (aproximacion geografica).
ALTER TABLE paradero_ruta ADD COLUMN IF NOT EXISTS orden_origen TEXT NOT NULL DEFAULT 'atu_secuencia';
ALTER TABLE paradero_ruta DROP CONSTRAINT IF EXISTS paradero_ruta_orden_origen_check;
ALTER TABLE paradero_ruta ADD CONSTRAINT paradero_ruta_orden_origen_check
    CHECK (orden_origen IN ('atu_secuencia', 'catalogo_n_paradero', 'latitud_troncal'));
ALTER TABLE ruta DROP CONSTRAINT IF EXISTS ruta_sistema_check;
ALTER TABLE ruta ADD CONSTRAINT ruta_sistema_check
    CHECK (sistema IN ('metro_l1', 'troncal', 'corredor', 'alimentador'));
-- migracion de cargas anteriores (tabla derivada: se recarga con `run paraderos`)
ALTER TABLE paradero_ruta ADD COLUMN IF NOT EXISTS direccion SMALLINT NOT NULL DEFAULT 0;
DO $$ BEGIN
    IF (SELECT count(*) FROM information_schema.key_column_usage
        WHERE table_name = 'paradero_ruta' AND constraint_name = 'paradero_ruta_pkey') <> 3 THEN
        ALTER TABLE paradero_ruta DROP CONSTRAINT IF EXISTS paradero_ruta_pkey;
        ALTER TABLE paradero_ruta ADD PRIMARY KEY (paradero_id, ruta_id, direccion);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS ix_paradero_ruta_ruta ON paradero_ruta (ruta_id);

-- Tiempo de viaje entre paradas consecutivas de cada ruta y sentido (base del costo de un tramo).
-- dist_m sale de OSRM por calles (fuente 'osrm') o de la distancia recta x 1.3 si no respondio
-- ('haversine'; Metro L1 siempre recta). duracion_s es una ESTIMACION: dist_m / velocidad comercial
-- del sistema + parada, con velocidades supuestas (ver VELOCIDAD_KMH en ingest_paraderos.py);
-- duracion_osrm_s es la de OSRM en auto y solo se guarda como referencia.
CREATE TABLE IF NOT EXISTS tramo (
    ruta_id         BIGINT NOT NULL REFERENCES ruta (id) ON DELETE CASCADE,
    direccion       SMALLINT NOT NULL,
    orden_desde     INTEGER NOT NULL,
    orden_hasta     INTEGER NOT NULL,
    paradero_desde  BIGINT NOT NULL REFERENCES paradero (id) ON DELETE CASCADE,
    paradero_hasta  BIGINT NOT NULL REFERENCES paradero (id) ON DELETE CASCADE,
    dist_m          DOUBLE PRECISION NOT NULL,
    duracion_osrm_s DOUBLE PRECISION,
    duracion_s      DOUBLE PRECISION NOT NULL,
    fuente          TEXT NOT NULL CHECK (fuente IN ('osrm', 'haversine')),
    -- false: salto > 3 km entre paradas consecutivas (corredor/alimentador): casi siempre una parada del
    -- catalogo fuera de la secuencia ATU, no un tramo real. En troncal los expresos saltan estaciones.
    fiable          BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (ruta_id, direccion, orden_desde)
);
ALTER TABLE tramo ADD COLUMN IF NOT EXISTS fiable BOOLEAN NOT NULL DEFAULT true;
CREATE INDEX IF NOT EXISTS ix_tramo_paradero ON tramo (paradero_desde);

-- Intervalo entre buses (headway) que usa el modelo para el ETA y el aforo, por sistema y tipo de dia.
-- Es la espera esperada en un transbordo (headway_min / 2). Se carga desde models/<sistema>/
-- crowding_config.json para que backend y modelo usen EXACTAMENTE los mismos valores.
-- fuente: atu_punto_medio = punto medio del rango oficial ATU (Metro L1); supuesto_modelo = valor
-- fijado por el modelo sin fuente publicada. No hay headway por ruta ni por hora.
CREATE TABLE IF NOT EXISTS headway_sistema (
    sistema      TEXT NOT NULL CHECK (sistema IN ('metro_l1', 'troncal', 'corredor', 'alimentador')),
    bucket       TEXT NOT NULL CHECK (bucket IN ('LAB', 'SAB', 'DOM')),   -- feriado = DOM
    headway_min  DOUBLE PRECISION NOT NULL,
    cap_vehiculo DOUBLE PRECISION NOT NULL,
    fuente       TEXT NOT NULL CHECK (fuente IN ('atu_punto_medio', 'supuesto_modelo')),
    PRIMARY KEY (sistema, bucket)
);

CREATE OR REPLACE FUNCTION paraderos_cercanos(
    p_lat DOUBLE PRECISION, p_lon DOUBLE PRECISION,
    p_radio_m DOUBLE PRECISION DEFAULT 800, p_limite INTEGER DEFAULT 10)
RETURNS TABLE (paradero_id BIGINT, sistema TEXT, nombre TEXT, lat DOUBLE PRECISION,
               lon DOUBLE PRECISION, calidad_coord TEXT, distancia_m DOUBLE PRECISION,
               rutas JSONB)
LANGUAGE sql STABLE AS $$
    WITH cand AS (
        SELECT p.*,
               2 * 6371000 * asin(sqrt(
                   sin(radians(p.lat - p_lat) / 2) ^ 2
                   + cos(radians(p_lat)) * cos(radians(p.lat))
                     * sin(radians(p.lon - p_lon) / 2) ^ 2)) AS d
        FROM paradero p
        WHERE p.lat BETWEEN p_lat - p_radio_m / 111320.0 AND p_lat + p_radio_m / 111320.0
          AND p.lon BETWEEN p_lon - p_radio_m / (111320.0 * greatest(cos(radians(p_lat)), 0.01))
                        AND p_lon + p_radio_m / (111320.0 * greatest(cos(radians(p_lat)), 0.01))
    )
    SELECT c.id, c.sistema, c.nombre, c.lat, c.lon, c.calidad_coord, c.d,
           coalesce((
               SELECT jsonb_agg(t.x ORDER BY t.x ->> 'codigo')
               FROM (SELECT DISTINCT ON (r.id) jsonb_build_object(
                          'ruta_id', r.id, 'codigo', r.codigo, 'nombre', r.nombre,
                          'color_hex', r.color_hex, 'orden', pr.orden,
                          'unidad_modelo', pr.unidad_modelo) AS x
                     FROM paradero_ruta pr JOIN ruta r ON r.id = pr.ruta_id
                     WHERE pr.paradero_id = c.id
                     ORDER BY r.id, pr.direccion) t), '[]'::jsonb)
    FROM cand c
    WHERE c.d <= p_radio_m
    ORDER BY c.d
    LIMIT p_limite
$$;

-- 7. Opciones de viaje origen -> destino (directo y con un transbordo).
-- Contrato para el backend: devuelve opciones con tiempos estimados; el ranking final, la caminata
-- real (OSRM foot) y la geocodificacion quedan en la aplicacion. Ver backend/README.md.

CREATE OR REPLACE FUNCTION distancia_m(lat1 DOUBLE PRECISION, lon1 DOUBLE PRECISION,
                                       lat2 DOUBLE PRECISION, lon2 DOUBLE PRECISION)
RETURNS DOUBLE PRECISION LANGUAGE sql IMMUTABLE AS $$
    SELECT 2 * 6371000 * asin(sqrt(
        sin(radians(lat2 - lat1) / 2) ^ 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ^ 2))
$$;

-- Feriados nacionales (models/calendario_eventos.json, 2025-2026): el tipo de dia es DOM.
CREATE TABLE IF NOT EXISTS feriado (
    fecha  DATE PRIMARY KEY,
    nombre TEXT NOT NULL
);

-- Se puede viajar de `o_from` a `o_to` en una ruta/sentido? metro_l1 y troncal con direccion 0 son
-- lineas bidireccionales; en el resto el orden debe crecer (ver backend/README.md).
CREATE OR REPLACE FUNCTION sentido_valido(p_sistema TEXT, p_direccion SMALLINT, o_from INTEGER, o_to INTEGER)
RETURNS BOOLEAN LANGUAGE sql IMMUTABLE AS $$
    SELECT o_from IS NOT NULL AND o_to IS NOT NULL AND (
        o_from < o_to
        OR (p_direccion = 0 AND p_sistema IN ('metro_l1', 'troncal') AND o_from <> o_to))
$$;

-- Paraderos a <= 300 m entre si (incluye cada paradero consigo mismo, dist 0): candidatos a transbordo.
CREATE TABLE IF NOT EXISTS transbordo_cercano (
    paradero_a BIGINT NOT NULL REFERENCES paradero (id) ON DELETE CASCADE,
    paradero_b BIGINT NOT NULL REFERENCES paradero (id) ON DELETE CASCADE,
    dist_m     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (paradero_a, paradero_b)
);

-- Duracion y distancia de recorrer una ruta/sentido entre dos ordenes (suma de `tramo`).
CREATE OR REPLACE FUNCTION viaje_tramos(p_ruta BIGINT, p_dir SMALLINT, p_o1 INTEGER, p_o2 INTEGER)
RETURNS TABLE (duracion_s DOUBLE PRECISION, dist_m DOUBLE PRECISION, n_tramos INTEGER, n_no_fiables INTEGER)
LANGUAGE sql STABLE AS $$
    SELECT coalesce(sum(t.duracion_s), 0)::double precision,
           coalesce(sum(t.dist_m), 0)::double precision,
           count(*)::int,
           (count(*) FILTER (WHERE NOT t.fiable))::int
    FROM tramo t
    WHERE t.ruta_id = p_ruta AND t.direccion = p_dir
      AND t.orden_desde >= least(p_o1, p_o2) AND t.orden_hasta <= greatest(p_o1, p_o2)
$$;

-- Una sola ruta. p_ahora en hora de Lima; p_bucket (LAB/SAB/DOM) se deduce del dia si es NULL
-- (feriado -> DOM segun la tabla `feriado`). Espera = eta_min de `prediccion` en esa hora; si no hay
-- prediccion, headway / 2 del sistema. Caminata en linea recta a p_vel_mps (el backend la afina).
CREATE OR REPLACE FUNCTION rutas_directas(
    p_lat_o DOUBLE PRECISION, p_lon_o DOUBLE PRECISION,
    p_lat_d DOUBLE PRECISION, p_lon_d DOUBLE PRECISION,
    p_radio_m DOUBLE PRECISION DEFAULT 800,
    p_ahora TIMESTAMP DEFAULT (now() AT TIME ZONE 'America/Lima'),
    p_bucket TEXT DEFAULT NULL,
    p_solo_fiables BOOLEAN DEFAULT true,
    p_vel_mps DOUBLE PRECISION DEFAULT 1.33,
    p_limite INTEGER DEFAULT 10)
RETURNS TABLE (
    ruta_id BIGINT, sistema TEXT, ruta TEXT, direccion SMALLINT,
    paradero_subida_id BIGINT, paradero_subida TEXT, orden_subida INTEGER,
    paradero_bajada_id BIGINT, paradero_bajada TEXT, orden_bajada INTEGER,
    dist_origen_m DOUBLE PRECISION, dist_destino_m DOUBLE PRECISION,
    viaje_s DOUBLE PRECISION, n_tramos INTEGER, tramos_no_fiables INTEGER,
    unidad_modelo TEXT, aforo TEXT, eta_min DOUBLE PRECISION, eta2_min DOUBLE PRECISION,
    recomendacion TEXT, espera_s DOUBLE PRECISION, espera_fuente TEXT, tiempo_total_s DOUBLE PRECISION)
LANGUAGE sql STABLE AS $$
    WITH par AS (
        SELECT coalesce(p_bucket, CASE
                   WHEN EXISTS (SELECT 1 FROM feriado f WHERE f.fecha = p_ahora::date) THEN 'DOM'
                   ELSE CASE extract(dow FROM p_ahora)
                        WHEN 0 THEN 'DOM' WHEN 6 THEN 'SAB' ELSE 'LAB' END END) AS bucket
    ),
    org AS (
        SELECT p.id, p.nombre, distancia_m(p.lat, p.lon, p_lat_o, p_lon_o) AS d
        FROM paradero p
        WHERE p.lat BETWEEN p_lat_o - p_radio_m / 111320.0 AND p_lat_o + p_radio_m / 111320.0
          AND p.lon BETWEEN p_lon_o - p_radio_m / (111320.0 * greatest(cos(radians(p_lat_o)), 0.01))
                        AND p_lon_o + p_radio_m / (111320.0 * greatest(cos(radians(p_lat_o)), 0.01))
    ),
    dst AS (
        SELECT p.id, p.nombre, distancia_m(p.lat, p.lon, p_lat_d, p_lon_d) AS d
        FROM paradero p
        WHERE p.lat BETWEEN p_lat_d - p_radio_m / 111320.0 AND p_lat_d + p_radio_m / 111320.0
          AND p.lon BETWEEN p_lon_d - p_radio_m / (111320.0 * greatest(cos(radians(p_lat_d)), 0.01))
                        AND p_lon_d + p_radio_m / (111320.0 * greatest(cos(radians(p_lat_d)), 0.01))
    ),
    cand AS (
        SELECT DISTINCT ON (a.ruta_id, a.direccion)
               r.id AS rid, r.sistema AS sis, r.codigo AS cod, a.direccion AS dir,
               o.id AS sub_id, o.nombre AS sub_n, a.orden AS o1, a.unidad_modelo AS um,
               q.id AS baj_id, q.nombre AS baj_n, b.orden AS o2, o.d AS d_o, q.d AS d_d
        FROM org o
        JOIN paradero_ruta a ON a.paradero_id = o.id
        JOIN paradero_ruta b ON b.ruta_id = a.ruta_id AND b.direccion = a.direccion
        JOIN dst q ON q.id = b.paradero_id
        JOIN ruta r ON r.id = a.ruta_id
        WHERE a.paradero_id <> b.paradero_id
          AND sentido_valido(r.sistema, a.direccion, a.orden, b.orden)
          AND o.d <= p_radio_m AND q.d <= p_radio_m
        ORDER BY a.ruta_id, a.direccion, o.d + q.d
    )
    SELECT c.rid, c.sis, c.cod, c.dir, c.sub_id, c.sub_n, c.o1, c.baj_id, c.baj_n, c.o2,
           c.d_o, c.d_d, v.duracion_s, v.n_tramos, v.n_no_fiables,
           c.um, pr.aforo, pr.eta_min, pr.eta2_min, pr.recomendacion,
           coalesce(pr.eta_min * 60, h.headway_min * 30) AS espera_s,
           CASE WHEN pr.eta_min IS NOT NULL THEN 'prediccion' ELSE 'headway' END AS espera_fuente,
           c.d_o / p_vel_mps + coalesce(pr.eta_min * 60, h.headway_min * 30) + v.duracion_s
               + c.d_d / p_vel_mps AS tiempo_total_s
    FROM cand c
    CROSS JOIN par
    CROSS JOIN LATERAL viaje_tramos(c.rid, c.dir, c.o1, c.o2) v
    LEFT JOIN headway_sistema h ON h.sistema = c.sis AND h.bucket = par.bucket
    LEFT JOIN prediccion pr ON pr.sistema = c.sis AND pr.unidad = c.um
                           AND pr.fecha = p_ahora::date AND pr.hora = extract(hour FROM p_ahora)::int
    WHERE v.n_tramos > 0 AND (NOT p_solo_fiables OR v.n_no_fiables = 0)
    ORDER BY tiempo_total_s
    LIMIT p_limite
$$;

-- Dos rutas con un transbordo a pie (<= p_transbordo_m entre paraderos). Espera en el transbordo =
-- headway / 2 de la segunda ruta + p_penal_s. El tramo 2 usa la prediccion de la hora estimada de
-- llegada al transbordo. Los candidatos se preseleccionan con un proxy (caminata + 60 s por parada)
-- y solo los mejores por par de rutas calculan el tiempo exacto con `tramo`.
CREATE OR REPLACE FUNCTION rutas_transbordo(
    p_lat_o DOUBLE PRECISION, p_lon_o DOUBLE PRECISION,
    p_lat_d DOUBLE PRECISION, p_lon_d DOUBLE PRECISION,
    p_radio_m DOUBLE PRECISION DEFAULT 800,
    p_transbordo_m DOUBLE PRECISION DEFAULT 300,
    p_ahora TIMESTAMP DEFAULT (now() AT TIME ZONE 'America/Lima'),
    p_bucket TEXT DEFAULT NULL,
    p_solo_fiables BOOLEAN DEFAULT true,
    p_vel_mps DOUBLE PRECISION DEFAULT 1.33,
    p_penal_s DOUBLE PRECISION DEFAULT 300,
    p_limite INTEGER DEFAULT 10)
RETURNS TABLE (
    ruta1_id BIGINT, sistema1 TEXT, ruta1 TEXT, direccion1 SMALLINT,
    paradero_subida1 TEXT, orden_subida1 INTEGER, paradero_bajada1 TEXT, orden_bajada1 INTEGER,
    ruta2_id BIGINT, sistema2 TEXT, ruta2 TEXT, direccion2 SMALLINT,
    paradero_subida2 TEXT, orden_subida2 INTEGER, paradero_bajada2 TEXT, orden_bajada2 INTEGER,
    dist_origen_m DOUBLE PRECISION, dist_transbordo_m DOUBLE PRECISION, dist_destino_m DOUBLE PRECISION,
    viaje1_s DOUBLE PRECISION, viaje2_s DOUBLE PRECISION,
    aforo1 TEXT, eta1_min DOUBLE PRECISION, aforo2 TEXT, eta2_ruta2_min DOUBLE PRECISION,
    espera1_s DOUBLE PRECISION, espera2_s DOUBLE PRECISION, espera_fuente TEXT,
    tramos_no_fiables INTEGER, tiempo_total_s DOUBLE PRECISION)
LANGUAGE sql STABLE AS $$
    WITH par AS (
        SELECT coalesce(p_bucket, CASE
                   WHEN EXISTS (SELECT 1 FROM feriado f WHERE f.fecha = p_ahora::date) THEN 'DOM'
                   ELSE CASE extract(dow FROM p_ahora)
                        WHEN 0 THEN 'DOM' WHEN 6 THEN 'SAB' ELSE 'LAB' END END) AS bucket
    ),
    org AS (
        SELECT p.id, distancia_m(p.lat, p.lon, p_lat_o, p_lon_o) AS d
        FROM paradero p
        WHERE p.lat BETWEEN p_lat_o - p_radio_m / 111320.0 AND p_lat_o + p_radio_m / 111320.0
          AND p.lon BETWEEN p_lon_o - p_radio_m / (111320.0 * greatest(cos(radians(p_lat_o)), 0.01))
                        AND p_lon_o + p_radio_m / (111320.0 * greatest(cos(radians(p_lat_o)), 0.01))
    ),
    dst AS (
        SELECT p.id, distancia_m(p.lat, p.lon, p_lat_d, p_lon_d) AS d
        FROM paradero p
        WHERE p.lat BETWEEN p_lat_d - p_radio_m / 111320.0 AND p_lat_d + p_radio_m / 111320.0
          AND p.lon BETWEEN p_lon_d - p_radio_m / (111320.0 * greatest(cos(radians(p_lat_d)), 0.01))
                        AND p_lon_d + p_radio_m / (111320.0 * greatest(cos(radians(p_lat_d)), 0.01))
    ),
    leg1 AS (   -- subir cerca del origen y bajar en cualquier parada posterior
        SELECT a.ruta_id AS r1, r.sistema AS s1, r.codigo AS c1, a.direccion AS d1,
               a.paradero_id AS sub1, a.orden AS o_sub1, a.unidad_modelo AS u1, o.d AS d_o,
               x.paradero_id AS x_id, x.orden AS o_x
        FROM org o
        JOIN paradero_ruta a ON a.paradero_id = o.id AND o.d <= p_radio_m
        JOIN ruta r ON r.id = a.ruta_id
        JOIN paradero_ruta x ON x.ruta_id = a.ruta_id AND x.direccion = a.direccion
                            AND x.paradero_id <> a.paradero_id
        WHERE sentido_valido(r.sistema, a.direccion, a.orden, x.orden)
    ),
    leg2 AS (   -- subir en cualquier parada anterior y bajar cerca del destino
        SELECT b.ruta_id AS r2, r.sistema AS s2, r.codigo AS c2, b.direccion AS d2,
               y.paradero_id AS y_id, y.orden AS o_y,
               b.paradero_id AS baj2, b.orden AS o_baj2, q.d AS d_d
        FROM dst q
        JOIN paradero_ruta b ON b.paradero_id = q.id AND q.d <= p_radio_m
        JOIN ruta r ON r.id = b.ruta_id
        JOIN paradero_ruta y ON y.ruta_id = b.ruta_id AND y.direccion = b.direccion
                            AND y.paradero_id <> b.paradero_id
        WHERE sentido_valido(r.sistema, b.direccion, y.orden, b.orden)
    ),
    pre AS (    -- mejor punto de transbordo por par (ruta1/sentido, ruta2/sentido), con un proxy barato
        SELECT DISTINCT ON (l1.r1, l1.d1, l2.r2, l2.d2)
               l1.*, l2.*, tc.dist_m AS d_t
        FROM leg1 l1
        JOIN transbordo_cercano tc ON tc.paradero_a = l1.x_id AND tc.dist_m <= p_transbordo_m
        JOIN leg2 l2 ON l2.y_id = tc.paradero_b AND l2.r2 <> l1.r1
        ORDER BY l1.r1, l1.d1, l2.r2, l2.d2,
                 (l1.d_o + tc.dist_m + l2.d_d) / p_vel_mps
                 + 60 * (abs(l1.o_x - l1.o_sub1) + abs(l2.o_baj2 - l2.o_y))
    ),
    top AS (
        SELECT * FROM pre
        ORDER BY (d_o + d_t + d_d) / p_vel_mps + 60 * (abs(o_x - o_sub1) + abs(o_baj2 - o_y))
        LIMIT greatest(p_limite * 10, 50)
    ),
    calc AS (
        SELECT t.*, v1.duracion_s AS viaje1, v1.n_tramos AS n1, v1.n_no_fiables AS nf1,
               v2.duracion_s AS viaje2, v2.n_tramos AS n2, v2.n_no_fiables AS nf2,
               pr1.aforo AS aforo1, pr1.eta_min AS eta1,
               coalesce(pr1.eta_min * 60, h1.headway_min * 30) AS esp1,
               h2.headway_min * 30 + p_penal_s AS esp2,
               (pr1.eta_min IS NOT NULL) AS tiene_pred1
        FROM top t
        CROSS JOIN par
        CROSS JOIN LATERAL viaje_tramos(t.r1, t.d1, t.o_sub1, t.o_x) v1
        CROSS JOIN LATERAL viaje_tramos(t.r2, t.d2, t.o_y, t.o_baj2) v2
        LEFT JOIN headway_sistema h1 ON h1.sistema = t.s1 AND h1.bucket = par.bucket
        LEFT JOIN headway_sistema h2 ON h2.sistema = t.s2 AND h2.bucket = par.bucket
        LEFT JOIN prediccion pr1 ON pr1.sistema = t.s1 AND pr1.unidad = t.u1
                                AND pr1.fecha = p_ahora::date AND pr1.hora = extract(hour FROM p_ahora)::int
    )
    SELECT c.r1, c.s1, c.c1, c.d1, ps1.nombre, c.o_sub1, px.nombre, c.o_x,
           c.r2, c.s2, c.c2, c.d2, py.nombre, c.o_y, pb2.nombre, c.o_baj2,
           c.d_o, c.d_t, c.d_d, c.viaje1, c.viaje2,
           c.aforo1, c.eta1, pr2.aforo, pr2.eta_min,
           c.esp1, c.esp2,
           CASE WHEN c.tiene_pred1 THEN 'prediccion' ELSE 'headway' END,
           c.nf1 + c.nf2,
           c.d_o / p_vel_mps + c.esp1 + c.viaje1 + c.d_t / p_vel_mps + c.esp2 + c.viaje2
               + c.d_d / p_vel_mps AS tiempo_total_s
    FROM calc c
    JOIN paradero ps1 ON ps1.id = c.sub1
    JOIN paradero px ON px.id = c.x_id
    JOIN paradero py ON py.id = c.y_id
    JOIN paradero pb2 ON pb2.id = c.baj2
    LEFT JOIN paradero_ruta e2 ON e2.paradero_id = c.y_id AND e2.ruta_id = c.r2 AND e2.direccion = c.d2
    LEFT JOIN prediccion pr2 ON pr2.sistema = c.s2 AND pr2.unidad = e2.unidad_modelo
         AND pr2.fecha = (p_ahora + make_interval(secs => c.d_o / p_vel_mps + c.esp1 + c.viaje1
                                                          + c.d_t / p_vel_mps))::date
         AND pr2.hora = extract(hour FROM p_ahora + make_interval(secs => c.d_o / p_vel_mps + c.esp1
                                                          + c.viaje1 + c.d_t / p_vel_mps))::int
    WHERE c.n1 > 0 AND c.n2 > 0 AND (NOT p_solo_fiables OR c.nf1 + c.nf2 = 0)
    ORDER BY tiempo_total_s
    LIMIT p_limite
$$;

-- Paradas de cada ruta en orden, con coordenadas (paradero a paradero).
DROP VIEW IF EXISTS ruta_paradas;
CREATE VIEW ruta_paradas AS
SELECT r.id AS ruta_id, r.sistema, r.codigo AS ruta, pr.direccion, pr.orden,
       p.id AS paradero_id, p.nombre, p.lat, p.lon, p.calidad_coord, pr.unidad_modelo,
       pr.orden_origen
FROM paradero_ruta pr
JOIN ruta r ON r.id = pr.ruta_id
JOIN paradero p ON p.id = pr.paradero_id;

