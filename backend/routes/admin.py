"""Panel operacional (solo administradores): salud, pipelines, calidad del modelo, uso y reportes agregados.

Privacidad: nunca se devuelven reportes individuales, coordenadas, correos ni identificadores de usuarios.
Del Eje 2 solo salen conteos agregados.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from flask import Blueprint, jsonify
from sqlalchemy import extract, func

from db.connection import db
from db.tablas import (AjusteRiesgoSegmento, CalibracionModelo, EventoUso, MonitoreoModelo, PipelineEjecucion, ReporteSeguridad,
                       ValidacionHora, ahora_utc)
from routes.auth import User
from routes.feedback import FeedbackViaje, _resumen_desde_bd
from routes.permisos import admin_required
from services.calendario import TZ_LIMA

admin_bp = Blueprint("admin", __name__)

MODELOS_DIR = Path(__file__).resolve().parents[1] / "models"
SISTEMAS = ("metro_l1", "troncal", "corredor", "alimentador")
JOBS = ("pipeline-diario", "pipeline-semanal", "eje2-recalibrar", "monitoreo-semanal", "calibrar-eta", "db-particiones")


def _iso(valor) -> str | None:
    return valor.isoformat() if valor is not None else None


def _aware(valor: dt.datetime | None) -> dt.datetime | None:
    """SQLite devuelve fechas sin zona; todo se guarda en UTC."""
    if valor is not None and valor.tzinfo is None:
        return valor.replace(tzinfo=dt.timezone.utc)
    return valor


def _salud() -> dict:
    try:
        db.session.execute(db.text("SELECT 1"))
        bd = {"ok": True, "motor": db.engine.dialect.name}
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        bd = {"ok": False, "motor": db.engine.dialect.name, "error": type(exc).__name__}
    try:
        from services import eje2_service as E
        m = E.grafo().manifest
        eje2 = {"cargado": True, "version": m["version"], "datos_hasta": m["datos_hasta"],
                "n_segmentos": m["n_segmentos"], "n_accesos": m["n_accesos"]}
    except Exception as exc:  # noqa: BLE001
        eje2 = {"cargado": False, "error": type(exc).__name__}
    return {
        "api": "ok",
        "base_datos": bd,
        "eje2": eje2,
        # solo se informa si hay clave, jamás su valor
        "tomtom_configurado": bool(os.getenv("API_TOMTOM") or os.getenv("TOMMTOM_KEY")),
        "locationiq_configurado": bool(os.getenv("LOCATIONIQ_TOKEN", "").strip()),
    }


def _modelos() -> dict:
    try:
        man = json.loads((MODELOS_DIR / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"manifest": None, "sistemas": []}
    artefactos = man.get("artefactos", {})
    sistemas = []
    for s in SISTEMAS:
        propios = {k: v for k, v in artefactos.items() if k.startswith(f"{s}/")}
        sistemas.append({"sistema": s, "artefactos": len(propios), "bytes": sum(v.get("bytes", 0) for v in propios.values()),
                         "disponible": (MODELOS_DIR / s).is_dir() and bool(propios)})
    return {"manifest": {"version": man.get("version"), "fecha": man.get("fecha"), "cambios": man.get("cambios"),
                         "entorno": man.get("entorno"), "dia_referencia_verificacion": man.get("dia_referencia_verificacion")},
            "sistemas": sistemas}


def _pipelines() -> dict:
    filas = PipelineEjecucion.query.order_by(PipelineEjecucion.inicio.desc()).limit(25).all()
    ultimas = []
    for f in filas:
        ini, fin = _aware(f.inicio), _aware(f.fin)
        error = (f.detalle or {}).get("error") if isinstance(f.detalle, dict) else None
        ultimas.append({"id": f.id, "nombre": f.nombre, "estado": f.estado, "inicio": _iso(ini), "fin": _iso(fin),
                        "duracion_s": round((fin - ini).total_seconds(), 1) if ini and fin else None,
                        "error": error[:200] if error else None})
    por_job = {}
    for nombre in JOBS:
        u = next((x for x in ultimas if x["nombre"] == nombre), None)
        if u is None:
            u = PipelineEjecucion.query.filter_by(nombre=nombre).order_by(PipelineEjecucion.inicio.desc()).first()
            u = None if u is None else {"nombre": u.nombre, "estado": u.estado, "inicio": _iso(_aware(u.inicio)), "fin": _iso(_aware(u.fin))}
        por_job[nombre] = u
    return {"ultimas": ultimas, "por_job": por_job,
            "con_error": sum(1 for x in ultimas if x["estado"] == "error")}


def _monitoreo() -> dict:
    filas = MonitoreoModelo.query.order_by(MonitoreoModelo.semana.desc(), MonitoreoModelo.sistema).limit(8 * 4).all()
    semanal = [{"semana": f.semana.isoformat(), "sistema": f.sistema, "abordajes": f.n_abordajes, "eta_n": f.eta_n,
                "eta_mae_min": f.eta_mae_min, "eta_sesgo_min": f.eta_sesgo_min, "aforo_n": f.aforo_n,
                "aforo_acierto": f.aforo_acierto, "alerta": f.alerta, "motivo": f.motivo_alerta} for f in filas]
    campeones = CalibracionModelo.query.filter_by(estado="campeon").order_by(CalibracionModelo.sistema).all()
    return {"semanal": semanal,
            "alertas_activas": [f for f in semanal if f["alerta"] and f["semana"] == (semanal[0]["semana"] if semanal else None)],
            "calibracion": [{"sistema": c.sistema, "nombre": c.nombre, "version": c.version, "parametros": c.parametros,
                             "metricas": c.metricas, "creado_en": _iso(_aware(c.creado_en))} for c in campeones]}


def _serie_diaria(consulta_fecha, consulta_valor, desde: dt.datetime, filtros=()) -> dict[str, int]:
    q = db.session.query(func.date(consulta_fecha), consulta_valor).filter(consulta_fecha >= desde, *filtros).group_by(func.date(consulta_fecha))
    return {str(d): int(n or 0) for d, n in q.all()}


def _rellenar_dias(valores: dict[str, int], dias: int, hoy: dt.date) -> list[dict]:
    return [{"fecha": (d := (hoy - dt.timedelta(days=dias - 1 - i))).isoformat(), "n": valores.get(d.isoformat(), 0)} for i in range(dias)]


def _uso(ahora: dt.datetime) -> dict:
    # ValidacionHora.fecha_hora contiene hora local de Lima sin zona. Las fechas
    # de usuarios y feedback, en cambio, se siguen comparando con UTC.
    lima = ahora.astimezone(TZ_LIMA)
    hoy_lima = lima.date()
    inicio_14d_lima = hoy_lima - dt.timedelta(days=13)
    corte_14d_lima = dt.datetime.combine(inicio_14d_lima, dt.time.min)
    corte_30d_lima = (lima - dt.timedelta(days=30)).replace(tzinfo=None)
    hace7_utc = (ahora - dt.timedelta(days=7)).replace(tzinfo=None)

    por_dia = _serie_diaria(ValidacionHora.fecha_hora, func.sum(ValidacionHora.n), corte_14d_lima, (ValidacionHora.fuente == "app",))
    por_sistema = (db.session.query(ValidacionHora.sistema, func.sum(ValidacionHora.n))
                   .filter(ValidacionHora.fuente == "app", ValidacionHora.fecha_hora >= corte_30d_lima)
                   .group_by(ValidacionHora.sistema).order_by(func.sum(ValidacionHora.n).desc()).all())
    por_hora = dict(db.session.query(extract("hour", ValidacionHora.fecha_hora), func.sum(ValidacionHora.n))
                    .filter(ValidacionHora.fuente == "app", ValidacionHora.fecha_hora >= corte_30d_lima)
                    .group_by(extract("hour", ValidacionHora.fecha_hora)).all())
    eventos = (db.session.query(EventoUso.dia_lima, EventoUso.tipo, func.count(EventoUso.id))
               .filter(EventoUso.dia_lima >= inicio_14d_lima, EventoUso.dia_lima <= hoy_lima)
               .group_by(EventoUso.dia_lima, EventoUso.tipo).all())
    consultas = {dia.isoformat(): int(n) for dia, tipo, n in eventos if tipo == "consulta"}
    recomendaciones = {dia.isoformat(): int(n) for dia, tipo, n in eventos if tipo == "recomendacion_vista"}
    return {
        "usuarios_total": User.query.count(),
        "usuarios_nuevos_7d": User.query.filter(User.created_at >= hace7_utc).count(),
        "feedback_total": FeedbackViaje.query.count(),
        "feedback_7d": FeedbackViaje.query.filter(FeedbackViaje.creado_en >= hace7_utc).count(),
        "abordajes_por_dia": _rellenar_dias(por_dia, 14, hoy_lima),
        "abordajes_por_sistema": [{"sistema": s, "n": int(n or 0)} for s, n in por_sistema],
        "abordajes_por_hora": [{"hora": h, "n": int(por_hora.get(h, por_hora.get(float(h), 0)) or 0)} for h in range(24)],
        "consultas_14d": sum(consultas.values()),
        "recomendaciones_14d": sum(recomendaciones.values()),
        "consultas_por_dia": _rellenar_dias(consultas, 14, hoy_lima),
        "recomendaciones_por_dia": _rellenar_dias(recomendaciones, 14, hoy_lima),
    }


def _feedback() -> dict:
    return _resumen_desde_bd()


def _eje2(ahora: dt.datetime) -> dict:
    """Solo conteos. Sin coordenadas, calles individuales ni autores."""
    activos = ReporteSeguridad.query.filter_by(estado="activo")
    por_tipo = dict(db.session.query(ReporteSeguridad.tipo, func.count()).filter(ReporteSeguridad.estado == "activo").group_by(ReporteSeguridad.tipo).all())
    por_franja = dict(db.session.query(ReporteSeguridad.franja, func.count()).filter(ReporteSeguridad.estado == "activo").group_by(ReporteSeguridad.franja).all())
    hace14 = ahora - dt.timedelta(days=14)
    por_dia = _serie_diaria(ReporteSeguridad.creado_en, func.count(), hace14.replace(tzinfo=None), (ReporteSeguridad.estado == "activo",))
    n_aj, ult = db.session.query(func.count(), func.max(AjusteRiesgoSegmento.actualizado_en)).one()
    return {"activos": activos.count(), "retirados": ReporteSeguridad.query.filter_by(estado="retirado").count(),
            "por_tipo": {t: int(por_tipo.get(t, 0)) for t in ("acoso", "seguimiento", "robo")},
            "por_franja": {f: int(por_franja.get(f, 0)) for f in ("dia", "noche")},
            "por_dia": _rellenar_dias(por_dia, 14, ahora.date()),
            "segmentos_ajustados": int(n_aj or 0), "ajuste_actualizado_en": _iso(_aware(ult)),
            "subregistro": "Los reportes subestiman lo ocurrido y reflejan quién usa la app; no son una tasa de delitos."}


@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():
    """Resumen operacional del sistema (solo administradores).
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    responses:
      200: {description: Salud, modelos, pipelines, monitoreo, uso y reportes agregados}
      401: {description: Sin sesión}
      403: {description: La cuenta no es administradora}
    """
    ahora = ahora_utc()
    try:
        cuerpo = {"generado_en": ahora.isoformat(), "salud": _salud(), "modelos": _modelos(), "pipelines": _pipelines(),
                  "monitoreo": _monitoreo(), "uso": _uso(ahora), "feedback": _feedback(), "eje2": _eje2(ahora)}
    finally:
        db.session.rollback()          # solo lectura: no dejar la transacción abierta
    return jsonify(cuerpo), 200
