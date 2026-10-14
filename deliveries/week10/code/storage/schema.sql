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
    origen_trazado TEXT CHECK (origen_trazado IN ('shapefile_atu', 'osm_relation', 'derivado_osrm')),
    UNIQUE (sistema, codigo)
);
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS origen_trazado TEXT;
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS n_paradas INTEGER;
ALTER TABLE ruta ADD COLUMN IF NOT EXISTS pct_exactas SMALLINT;

CREATE TABLE IF NOT EXISTS paradero_ruta (
    paradero_id    BIGINT NOT NULL REFERENCES paradero (id) ON DELETE CASCADE,
    ruta_id        BIGINT NOT NULL REFERENCES ruta (id) ON DELETE CASCADE,
    direccion      SMALLINT NOT NULL DEFAULT 0,   -- 0 = sin sentido publicado
    orden          INTEGER,                        -- posicion en la ruta/direccion (ATU)
    unidad_modelo  TEXT,       -- unidad con prediccion (NULL si no hay demanda)
    PRIMARY KEY (paradero_id, ruta_id, direccion)
);
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

-- Paradas de cada ruta en orden, con coordenadas (paradero a paradero).
DROP VIEW IF EXISTS ruta_paradas;
CREATE VIEW ruta_paradas AS
SELECT r.id AS ruta_id, r.sistema, r.codigo AS ruta, pr.direccion, pr.orden,
       p.id AS paradero_id, p.nombre, p.lat, p.lon, p.calidad_coord, pr.unidad_modelo
FROM paradero_ruta pr
JOIN ruta r ON r.id = pr.ruta_id
JOIN paradero p ON p.id = pr.paradero_id;

