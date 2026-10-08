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
    utilidad    SMALLINT NOT NULL CHECK (utilidad BETWEEN 1 AND 5),
    comentario  TEXT
);

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
