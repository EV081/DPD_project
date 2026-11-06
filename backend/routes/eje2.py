"""Eje 2 · ruta peatonal segura, índice de seguridad de estaciones/paraderos y reportes de usuarios (/api/eje2)."""
from __future__ import annotations

import datetime as dt

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from db.connection import db
from db.tablas import AjusteRiesgoSegmento, PipelineEjecucion, ReporteSeguridad
from services import calendario
from services import eje2_reportes as R
from services import eje2_service as E

eje2_bp = Blueprint("eje2", __name__)


def _error(e: E.Eje2Error):
    return jsonify({"error": str(e)}), e.status


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _flotante(nombre: str, defecto: float, minimo: float, maximo: float) -> float:
    try:
        v = float(request.args.get(nombre, defecto))
    except ValueError:
        raise E.Eje2Error(f"{nombre} debe ser numérico") from None
    if not minimo <= v <= maximo:
        raise E.Eje2Error(f"{nombre} debe estar entre {minimo:g} y {maximo:g}")
    return v


# --------------------------------------------------------------------------- ruta
@eje2_bp.route("/ruta", methods=["POST"])
def ruta():
    """Ruta normal y ruta más segura hasta una estación o paradero, con la recomendada y su explicación.
    ---
    tags:
      - Eje 2
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [origen, destino]
          properties:
            origen: {type: object, properties: {lat: {type: number}, lon: {type: number}}}
            destino:
              type: object
              description: acceso_id, o station_id (+ sistema), o lat/lon
            preferencia: {type: string, enum: [segura, normal], default: segura}
            franja: {type: string, enum: [dia, noche], description: "por defecto la de la hora de salida en Lima"}
            salida: {type: string, description: "ISO 8601; por defecto ahora"}
            lambda: {type: number, description: "0 a 50; por defecto el valor validado"}
    responses:
      200:
        description: Ambas rutas (GeoJSON), comparación, recomendación y explicación
      404:
        description: Destino inexistente
      422:
        description: Origen fuera de la cobertura o demasiado lejos del destino
    """
    d = _json()
    salida = None
    if d.get("salida"):
        try:
            salida = dt.datetime.fromisoformat(str(d["salida"]).replace("Z", "+00:00"))
            if salida.tzinfo is None:
                salida = salida.replace(tzinfo=calendario.TZ_LIMA)
            salida = salida.astimezone(calendario.TZ_LIMA)
        except ValueError:
            return jsonify({"error": "salida debe ser una fecha ISO 8601"}), 400
    try:
        g = E.grafo()
        out = E.rutas(d.get("origen") or {}, d.get("destino") or {}, preferencia=d.get("preferencia") or "segura",
                      franja=d.get("franja"), salida=salida, lam=d.get("lambda"), deltas=R.ajustes.obtener(g), g=g)
    except E.Eje2Error as e:
        return _error(e)
    return jsonify(out), 200


# --------------------------------------------------------------------------- accesos
@eje2_bp.route("/accesos/cercanos", methods=["GET"])
def accesos_cercanos():
    """Estaciones y paraderos cercanos con su índice de seguridad (con base, intervalo y confianza).
    ---
    tags:
      - Eje 2
    parameters:
      - {in: query, name: lat, type: number, required: true}
      - {in: query, name: lon, type: number, required: true}
      - {in: query, name: radius, type: number, description: "metros (por defecto 800)"}
      - {in: query, name: limit, type: integer}
    """
    try:
        lat, lon = float(request.args["lat"]), float(request.args["lon"])
        radio = _flotante("radius", 800, 50, 3000)
        limite = int(_flotante("limit", 20, 1, 100))
    except (KeyError, ValueError):
        return jsonify({"error": "lat y lon son obligatorios y numéricos"}), 400
    except E.Eje2Error as e:
        return _error(e)
    return jsonify({"accesos": E.grafo().accesos_cercanos(lat, lon, radio, limite),
                    "aviso": E.AVISO.format(datos_hasta=E.grafo().manifest["datos_hasta"])}), 200


@eje2_bp.route("/accesos/por-estacion", methods=["GET"], defaults={"station_id": None})   # ?id=...: ids con espacios no pasan por API Gateway en la ruta
@eje2_bp.route("/accesos/por-estacion/<path:station_id>", methods=["GET"])
def acceso_por_estacion(station_id):
    """Índice de seguridad del punto de acceso que corresponde a una estación/paradero de /api/stations.
    ---
    tags:
      - Eje 2
    parameters:
      - {in: path, name: station_id, type: string, required: true}
      - {in: query, name: sistema, type: string, description: "metropolitano | corredores | metro_l1 | alimentadores"}
    """
    station_id = station_id or request.args.get("id", "")
    try:
        fila = E.acceso_de_estacion(E.grafo(), station_id, request.args.get("sistema"))
    except E.Eje2Error as e:
        return _error(e)
    return jsonify(E.indice_de_acceso(fila)), 200


@eje2_bp.route("/accesos/<acceso_id>", methods=["GET"])
def acceso(acceso_id):
    """Índice de seguridad de un punto de acceso.
    ---
    tags:
      - Eje 2
    parameters:
      - {in: path, name: acceso_id, type: string, required: true}
    """
    try:
        return jsonify(E.indice_de_acceso(E.grafo().acceso_por_id(acceso_id))), 200
    except E.Eje2Error as e:
        return _error(e)


# --------------------------------------------------------------------------- reportes
def _uid() -> int:
    return int(get_jwt_identity())


@eje2_bp.route("/reportes", methods=["POST"])
@jwt_required()
def crear_reporte():
    """Reporta acoso, seguimiento o robo cerca de una estación o paradero. Solo se usa de forma agregada.
    ---
    tags:
      - Eje 2
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [tipo, lat, lon]
          properties:
            tipo: {type: string, enum: [acoso, seguimiento, robo]}
            lat: {type: number}
            lon: {type: number}
            ocurrido_en: {type: string, description: "ISO 8601, hasta 24 h atrás; por defecto ahora"}
    responses:
      201:
        description: Reporte registrado (incluye el aviso de llamar al 105)
      422:
        description: El punto no está cerca de una calle cubierta
      429:
        description: Límite de reportes por usuario
    """
    try:
        return jsonify(R.crear_reporte(_uid(), _json())), 201
    except E.Eje2Error as e:
        return _error(e)


@eje2_bp.route("/reportes/mios", methods=["GET"])
@jwt_required()
def mis_reportes():
    """Tus reportes (solo los propios).
    ---
    tags:
      - Eje 2
    security:
      - Bearer: []
    """
    filas = (ReporteSeguridad.query.filter_by(user_id=_uid()).order_by(ReporteSeguridad.creado_en.desc()).limit(50).all())
    return jsonify({"reportes": [{"id": f.id, "tipo": f.tipo, "franja": f.franja, "estado": f.estado,
                                  "creado_en": f.creado_en.isoformat(), "ocurrido_en": f.ocurrido_en.isoformat(),
                                  "lat": f.lat, "lon": f.lon} for f in filas]}), 200


@eje2_bp.route("/reportes/<reporte_id>", methods=["DELETE"])
@jwt_required()
def retirar_reporte(reporte_id):
    """Retira un reporte propio (deja de contar en la recalibración).
    ---
    tags:
      - Eje 2
    security:
      - Bearer: []
    parameters:
      - {in: path, name: reporte_id, type: string, required: true}
    """
    n = (ReporteSeguridad.query.filter_by(id=reporte_id, user_id=_uid(), estado="activo").update({"estado": "retirado"}))
    db.session.commit()
    if not n:
        return jsonify({"error": "Reporte no encontrado"}), 404         # igual respuesta si es de otra persona: no se revela
    return jsonify({"message": "Reporte retirado"}), 200


# --------------------------------------------------------------------------- estado
@eje2_bp.route("/estado", methods=["GET"])
def estado():
    """Versión y antigüedad del riesgo base, ajuste por reportes y último pipeline.
    ---
    tags:
      - Eje 2
    """
    m = E.grafo().manifest
    n_aj, ult = db.session.query(func.count(), func.max(AjusteRiesgoSegmento.actualizado_en)).one()
    pipe = (PipelineEjecucion.query.filter(PipelineEjecucion.nombre.in_(("pipeline-diario", "eje2-recalibrar")))
            .order_by(PipelineEjecucion.inicio.desc()).first())
    db.session.rollback()
    datos_hasta = dt.date.fromisoformat(m["datos_hasta"])
    return jsonify({
        "version": m["version"], "datos_hasta": m["datos_hasta"],
        "antiguedad_meses": round((calendario.ahora_lima().date() - datos_hasta).days / 30.4, 1),
        "lambda": m["lambda"], "forma_costo": m["forma_costo"], "n_segmentos": m["n_segmentos"], "n_accesos": m["n_accesos"],
        "ajuste_por_reportes": {"activo": R.ajuste_activo(), "segmentos_ajustados": int(n_aj),
                                "actualizado_en": ult.isoformat() if ult else None, "parametros": R.parametros()},
        "ultimo_pipeline": ({"nombre": pipe.nombre, "estado": pipe.estado, "inicio": pipe.inicio.isoformat()} if pipe else None),
        "aviso": E.AVISO.format(datos_hasta=m["datos_hasta"]),
    }), 200
