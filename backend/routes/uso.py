"""Registro mínimo de acciones para comprobar el uso del producto.

Cada evento cuenta una acción de una sesión iniciada, no una persona ni un viaje real.
Los datos sintéticos del laboratorio nunca se envían a este endpoint.
"""
from __future__ import annotations

import collections
import datetime as dt
import threading
import time
import uuid

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from db.connection import db
from db.tablas import EventoUso
from routes.validation import json_object, text_field
from services.calendario import TZ_LIMA

uso_bp = Blueprint("uso", __name__)
TIPOS = frozenset(("consulta", "recomendacion_vista"))
SISTEMAS = frozenset(("metro_l1", "metropolitano", "corredores", "alimentadores"))

# Límite liviano para errores o automatizaciones accidentales. Es por proceso;
# para un despliegue con varios workers se necesita un limitador compartido.
VENTANA_S = 60
MAX_EVENTOS_POR_VENTANA = 60
_ventanas: dict[str, collections.deque[float]] = {}
_candado = threading.Lock()


def _permite_evento(cuenta: str, ahora: float) -> bool:
    with _candado:
        if len(_ventanas) > 2048:
            for clave in list(_ventanas):
                if not _ventanas[clave] or _ventanas[clave][-1] <= ahora - VENTANA_S:
                    del _ventanas[clave]
        ventana = _ventanas.setdefault(cuenta, collections.deque())
        while ventana and ventana[0] <= ahora - VENTANA_S:
            ventana.popleft()
        if len(ventana) >= MAX_EVENTOS_POR_VENTANA:
            return False
        ventana.append(ahora)
        return True


@uso_bp.route("/eventos", methods=["POST"])
@jwt_required()
def registrar_evento():
    """Registra una consulta exitosa o la visualización de una recomendación.
    ---
    tags:
      - Uso
    security:
      - Bearer: []
    consumes:
      - application/json
    responses:
      201: {description: Acción registrada}
      200: {description: UUID repetido; no se contó dos veces}
      400: {description: Acción o sistema no admitidos}
      429: {description: Demasiadas acciones en un minuto}
    """
    datos = json_object()
    tipo = text_field(datos, "tipo", 24)
    sistema = text_field(datos, "sistema", 20)
    evento_id = text_field(datos, "evento_id", 36)
    if tipo not in TIPOS or sistema not in SISTEMAS:
        return jsonify({"error": "El tipo o el sistema no pertenece al catálogo"}), 400
    try:
        identificador = uuid.UUID(evento_id)
    except (ValueError, AttributeError):
        return jsonify({"error": "evento_id debe ser un UUID v4"}), 400
    if identificador.version != 4 or str(identificador) != evento_id.lower():
        return jsonify({"error": "evento_id debe ser un UUID v4"}), 400
    evento_id = str(identificador)

    # La idempotencia se comprueba antes del límite para que un reintento no consuma cupo.
    if db.session.get(EventoUso, evento_id) is not None:
        return jsonify({"registrado": False}), 200
    if not _permite_evento(str(get_jwt_identity()), time.monotonic()):
        return jsonify({"error": "Demasiadas acciones en un minuto"}), 429

    ahora = dt.datetime.now(dt.timezone.utc)
    db.session.add(EventoUso(id=evento_id, tipo=tipo, sistema=sistema,
                            creado_en=ahora, dia_lima=ahora.astimezone(TZ_LIMA).date()))
    try:
        db.session.commit()
    except IntegrityError:  # el mismo UUID pudo llegar en otro worker al mismo tiempo
        db.session.rollback()
        return jsonify({"registrado": False}), 200
    return jsonify({"registrado": True}), 201
