"""Tablas nuevas del Eje 1 y Eje 2 (SQLAlchemy). Se registran al importar este módulo, antes de ``db.create_all()``.

Las tablas que crecen con el uso (``reporte_seguridad`` y ``validacion_hora``) son **particionadas por mes** en Postgres
(ver ``db/particiones.py``): consultas por periodo, borrado de meses viejos sin ``DELETE`` y mantenimiento barato.
"""
from __future__ import annotations

import datetime as dt
import uuid

from db.connection import db

# tabla -> columna de partición (RANGE mensual). La PK de estas tablas incluye esa columna.
PARTICIONADAS = {"reporte_seguridad": "creado_en", "validacion_hora": "fecha_hora"}

TIPOS_REPORTE = ("acoso", "seguimiento", "robo")
FRANJAS = ("dia", "noche")


def ahora_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class ReporteSeguridad(db.Model):
    """Reporte de un usuario sobre una calle cercana a una estación o paradero. Nunca se expone individualmente."""

    __tablename__ = "reporte_seguridad"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creado_en = db.Column(db.DateTime(timezone=True), primary_key=True, nullable=False, default=ahora_utc)   # clave de partición
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)
    ocurrido_en = db.Column(db.DateTime(timezone=True), nullable=False)
    lat = db.Column(db.Float, nullable=False)                       # 5 decimales (~1 m)
    lon = db.Column(db.Float, nullable=False)
    seg_id = db.Column(db.String(40), nullable=False)               # calle del grafo a la que se ajustó el punto
    acceso_id = db.Column(db.String(40))                            # estación/paradero más cercano (opcional)
    franja = db.Column(db.String(6), nullable=False)
    estado = db.Column(db.String(10), nullable=False, default="activo")

    __table_args__ = (
        db.CheckConstraint("tipo IN ('acoso', 'seguimiento', 'robo')", name="ck_reporte_tipo"),
        db.CheckConstraint("franja IN ('dia', 'noche')", name="ck_reporte_franja"),
        db.CheckConstraint("estado IN ('activo', 'retirado')", name="ck_reporte_estado"),
        db.Index("ix_reporte_seg_creado", "seg_id", "creado_en"),
        db.Index("ix_reporte_user_creado", "user_id", "creado_en"),
    )


class ValidacionHora(db.Model):
    """Conteo por hora de validaciones. ``fuente='app'`` = cada "Ya abordé" de la app; ``'atu'`` queda reservado para datos de la ATU."""

    __tablename__ = "validacion_hora"

    fuente = db.Column(db.String(10), primary_key=True)
    sistema = db.Column(db.String(30), primary_key=True)
    serie = db.Column(db.String(100), primary_key=True)
    fecha_hora = db.Column(db.DateTime, primary_key=True)           # hora local de Lima, truncada a la hora; clave de partición
    n = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (db.Index("ix_validacion_sistema_hora", "sistema", "fecha_hora"),)


class AjusteRiesgoSegmento(db.Model):
    """Ajuste del riesgo de una calle por reportes recientes (lo calcula ``eje2-recalibrar``; vuelve a 0 sin reportes)."""

    __tablename__ = "ajuste_riesgo_segmento"

    seg_id = db.Column(db.String(40), primary_key=True)
    franja = db.Column(db.String(6), primary_key=True)
    delta = db.Column(db.Float, nullable=False)
    n_reportes = db.Column(db.Integer, nullable=False)
    n_usuarios = db.Column(db.Integer, nullable=False)
    actualizado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=ahora_utc)


class MonitoreoModelo(db.Model):
    """Métricas semanales del Eje 1 con el feedback de la app (ETA y aforo)."""

    __tablename__ = "monitoreo_modelo"

    id = db.Column(db.Integer, primary_key=True)
    sistema = db.Column(db.String(30), nullable=False)
    semana = db.Column(db.Date, nullable=False)                     # lunes de la semana
    n_abordajes = db.Column(db.Integer, nullable=False)
    eta_n = db.Column(db.Integer, nullable=False)
    eta_mae_min = db.Column(db.Float)
    eta_sesgo_min = db.Column(db.Float)
    aforo_n = db.Column(db.Integer, nullable=False)
    aforo_acierto = db.Column(db.Float)
    alerta = db.Column(db.Boolean, nullable=False, default=False)
    motivo_alerta = db.Column(db.String(200))
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=ahora_utc)

    __table_args__ = (db.UniqueConstraint("sistema", "semana", name="uq_monitoreo_sistema_semana"),)


class CalibracionModelo(db.Model):
    """Capa de calibración versionada (hoy: factor del ETA). Un campeón por (sistema, nombre); las versiones viejas quedan archivadas."""

    __tablename__ = "calibracion_modelo"

    sistema = db.Column(db.String(30), primary_key=True)
    nombre = db.Column(db.String(30), primary_key=True)
    version = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.String(10), nullable=False)               # campeon | retador | archivado
    parametros = db.Column(db.JSON, nullable=False)
    metricas = db.Column(db.JSON)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=ahora_utc)


class PipelineEjecucion(db.Model):
    """Bitácora de los jobs (particiones, recalibración, monitoreo…)."""

    __tablename__ = "pipeline_ejecucion"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(40), nullable=False)
    inicio = db.Column(db.DateTime(timezone=True), nullable=False, default=ahora_utc)
    fin = db.Column(db.DateTime(timezone=True))
    estado = db.Column(db.String(12), nullable=False, default="en_curso")      # en_curso | ok | sin_datos | error
    detalle = db.Column(db.JSON)

    __table_args__ = (db.Index("ix_pipeline_nombre_inicio", "nombre", "inicio"),)
