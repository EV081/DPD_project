"""Feedback de usuarios ("Ya abordé"): mide el error real del ETA y del aforo mostrados.

No reentrena el modelo de demanda (aprende de validaciones ATU): sirve para medir el error
del ETA, validar el ajuste por tráfico (``modo_datos``) y calibrar el aforo percibido.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from db.connection import db

feedback_bp = Blueprint("feedback", __name__)

CLASES_AFORO = ("Asientos", "De_pie", "Saturado")
MODOS = ("en_vivo", "reciente", "historico")
ESPERA_MAX_MIN = 180.0


class FeedbackViaje(db.Model):
    # nombre distinto de `feedback_usuario` (tabla del pipeline de week10, esquema propio)
    __tablename__ = "feedback_viaje"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    creado_en = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    station_id = db.Column(db.String(150), nullable=False)
    sistema = db.Column(db.String(30), nullable=False)
    espera_real_min = db.Column(db.Float, nullable=False)     # consulta -> "Ya abordé", medida en el cliente
    eta_mostrado_min = db.Column(db.Float)
    eta_base_min = db.Column(db.Float)                        # antes del ajuste por tráfico
    factor_trafico = db.Column(db.Float)
    modo_datos = db.Column(db.String(12))
    aforo_mostrado = db.Column(db.String(12))
    aforo_percibido = db.Column(db.String(12))                # opcional


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


@feedback_bp.route("", methods=["POST"])
@jwt_required()
def crear_feedback():
    """Registra que el usuario abordó: espera real vs ETA mostrado y aforo percibido (opcional).
    ---
    tags:
      - Feedback
    security:
      - Bearer: []
    """
    d = request.get_json(silent=True) or {}
    station_id, sistema = str(d.get("station_id") or "").strip(), str(d.get("sistema") or "").strip()
    espera = _num(d.get("espera_real_min"))
    if not station_id or not sistema or espera is None:
        return jsonify({"error": "station_id, sistema y espera_real_min son obligatorios"}), 400
    if not 0 <= espera <= ESPERA_MAX_MIN:
        return jsonify({"error": f"espera_real_min debe estar entre 0 y {ESPERA_MAX_MIN:g}"}), 400
    percibido = d.get("aforo_percibido") or None
    if percibido is not None and percibido not in CLASES_AFORO:
        return jsonify({"error": f"aforo_percibido debe ser uno de {', '.join(CLASES_AFORO)}"}), 400
    modo = d.get("modo_datos") if d.get("modo_datos") in MODOS else None
    fila = FeedbackViaje(
        user_id=get_jwt_identity() and int(get_jwt_identity()),
        station_id=station_id, sistema=sistema, espera_real_min=round(espera, 2),
        eta_mostrado_min=_num(d.get("eta_mostrado_min")), eta_base_min=_num(d.get("eta_base_min")),
        factor_trafico=_num(d.get("factor_trafico")), modo_datos=modo,
        aforo_mostrado=d.get("aforo_mostrado") if d.get("aforo_mostrado") in CLASES_AFORO else None,
        aforo_percibido=percibido,
    )
    db.session.add(fila)
    db.session.commit()
    return jsonify({"message": "Gracias por tu feedback", "id": fila.id}), 201


def _resumen(filas: list[FeedbackViaje]) -> dict:
    con_eta = [f for f in filas if f.eta_mostrado_min is not None]
    errores = [f.espera_real_min - f.eta_mostrado_min for f in con_eta]      # >0: esperó más de lo dicho
    con_aforo = [f for f in filas if f.aforo_percibido and f.aforo_mostrado]
    return {
        "n": len(filas),
        "eta": {
            "n": len(con_eta),
            "mae_min": round(sum(abs(e) for e in errores) / len(errores), 2) if errores else None,
            "sesgo_min": round(sum(errores) / len(errores), 2) if errores else None,
        },
        "aforo": {
            "n": len(con_aforo),
            "acierto": round(sum(f.aforo_percibido == f.aforo_mostrado for f in con_aforo) / len(con_aforo), 3)
            if con_aforo else None,
        },
    }


@feedback_bp.route("/resumen", methods=["GET"])
@jwt_required()
def resumen_feedback():
    """Métricas agregadas: error del ETA (MAE y sesgo) y acierto del aforo, global y por modo de
    tráfico (en_vivo / reciente / historico) para validar el ajuste con TomTom.
    ---
    tags:
      - Feedback
    security:
      - Bearer: []
    """
    filas = FeedbackViaje.query.all()
    por_modo = {m: _resumen([f for f in filas if f.modo_datos == m]) for m in MODOS}
    return jsonify({**_resumen(filas), "por_modo_datos": por_modo}), 200
