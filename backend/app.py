import datetime
import os

from dotenv import load_dotenv

load_dotenv()  # lee backend/.env (en Render las variables vienen del panel)

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flasgger import Swagger
from werkzeug.exceptions import BadRequest
from settings import jwt_secret

from db.connection import init_db

from routes.auth import auth_bp
from routes.systems import systems_bp
from routes.stations import stations_bp
from routes.predictions import predictions_bp
from routes.feedback import feedback_bp
from routes.geo import geo_bp  # <-- NUEVO: Blueprint para los GeoJSON de rutas y mapas
from routes.eje2 import eje2_bp  # Eje 2: ruta peatonal segura y reportes de usuarios
from routes.admin import admin_bp  # panel operacional (solo admin)


app = Flask(__name__)

CORS(app)

app.config["JWT_SECRET_KEY"] = jwt_secret(app.instance_path)

# Sin esto flask-jwt-extended usa 15 min y la app no tiene refresh token: el usuario quedaba fuera a los 15 minutos.
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=float(os.getenv("JWT_EXPIRA_HORAS", "168")))

jwt = JWTManager(app)


@app.errorhandler(BadRequest)
def invalid_input(error):
    return jsonify({"error": error.description}), 400


@jwt.invalid_token_loader
def invalid_token(reason):
    # Un token firmado con otra clave (p. ej. tras cambiar JWT_SECRET_KEY) llegaba como 422: el frontend lo tomaba por
    # un fallo de red y no cerraba la sesión. Como 401, la web descarta el token y pide iniciar sesión.
    return jsonify({"error": "Sesión no válida. Inicia sesión de nuevo."}), 401


@jwt.user_lookup_loader
def current_user(_header, token):
    from routes.auth import User
    from db.connection import db
    try:
        return db.session.get(User, int(token["sub"]))
    except (KeyError, TypeError, ValueError):
        return None

# Base de datos (si la usas para usuarios u otras entidades)
init_db(app)

# Swagger
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "UrbanSafe API",
        "description": "API backend del proyecto UrbanSafe AI",
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": [
        "http"
    ],
    "securityDefinitions": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header",
                   "description": "JWT: escribe 'Bearer <token>' (el token sale de /api/auth/login)"}
    }
})

# Routes / Blueprints
app.register_blueprint(
    auth_bp,
    url_prefix="/api/auth"
)

app.register_blueprint(
    systems_bp,
    url_prefix="/api/systems"
)

app.register_blueprint(
    stations_bp,
    url_prefix="/api/stations"
)

app.register_blueprint(
    predictions_bp,
    url_prefix="/api/predictions"
)

app.register_blueprint(
    geo_bp,
    url_prefix="/api/geo"  # <-- NUEVO: Ruta base para los trazados geoespaciales
)


app.register_blueprint(
    feedback_bp,
    url_prefix="/api/feedback"
)

app.register_blueprint(
    eje2_bp,
    url_prefix="/api/eje2"
)

app.register_blueprint(
    admin_bp,
    url_prefix="/api/admin"
)

# Administrador desde backend/.env (SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD): se crea o actualiza al arrancar.
# Desactivar con SEED_ADMIN_ON_START=0; también se puede correr a mano: flask --app app seed-admin
from services.usuarios import sembrar_al_arrancar  # noqa: E402

with app.app_context():
    sembrar_al_arrancar()

# Eje 2: carga el grafo al arrancar (≈0,2 s y ~100 MB por proceso) para que la primera ruta no pague la carga.
# Desactivar con EJE2_PRECALENTAR=0 si el servidor tiene muy poca memoria (ver backend/docs/EJE2_RUTA_SEGURA.md).
if os.getenv("EJE2_PRECALENTAR", "1") == "1":
    try:
        from services import eje2_service
        eje2_service.precalentar()
    except Exception as exc:  # noqa: BLE001 - sin artefactos del Eje 2 el resto de la API sigue funcionando
        print(f"[eje2] no se pudo precargar el grafo: {exc}")

# Comandos de mantenimiento y pipelines: `flask --app app db-particiones | eje2-recalibrar | pipeline-diario ...`
from cli import registrar_comandos  # noqa: E402

registrar_comandos(app)


@app.route("/api/health", methods=["GET"])
def health():
    """
    Verifica que la API esté funcionando.
    ---
    tags:
      - Health
    responses:
      200:
        description: API funcionando correctamente
    """
    return jsonify({
        "status": "ok",
        "message": "UrbanSafe API funcionando"
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
