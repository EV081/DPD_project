import bcrypt
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest

from flask import Blueprint, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)

from db.connection import db
from routes.validation import json_object, text_field


auth_bp = Blueprint("auth", __name__)


def _email(data):
    email = text_field(data, "email", 150).lower()
    if email.count("@") != 1 or any(c.isspace() for c in email) or not all(email.split("@")):
        raise BadRequest("El correo no tiene un formato válido")
    return email


def _password(data, field="password", minimum=1):
    value = text_field(data, field, 72, strip=False)
    # bcrypt trabaja con un máximo de 72 bytes, no de 72 letras.
    if len(value) < minimum or len(value.encode("utf-8")) > 72:
        raise BadRequest(f"{field} debe tener al menos {minimum} caracteres y como máximo 72 bytes")
    return value


def _by_email(email):
    return User.query.filter(func.lower(func.trim(User.email)) == email).first()


def _save():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "El correo ya está registrado"}), 409
    return None


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    # 'user' (por defecto) o 'admin'. El rol nunca se recibe del cliente: solo lo asigna `flask seed-admin`.
    role = db.Column(
        db.String(10),
        nullable=False,
        default="user",
        server_default="user"
    )

    @property
    def is_admin(self):
        return self.role == "admin"

    def to_dict(self, *, with_created=False):
        data = {"id": self.id, "name": self.name, "email": self.email, "role": self.role}
        if with_created:
            data["created_at"] = self.created_at
        return data


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Registra un nuevo usuario.
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - email
            - password
          properties:
            name:
              type: string
              example: Alessandro
            email:
              type: string
              example: alessandro@gmail.com
            password:
              type: string
              example: 123456
    responses:
      201:
        description: Usuario registrado correctamente
      400:
        description: Datos incompletos
      409:
        description: El correo ya está registrado
    """

    data = json_object()
    name = text_field(data, "name", 100)
    email = _email(data)
    password = _password(data, minimum=6)
    existing_user = _by_email(email)

    if existing_user:
        return jsonify({
            "error": "El correo ya está registrado"
        }), 409

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    user = User(
        name=name,
        email=email,
        password_hash=password_hash
    )

    db.session.add(user)
    error = _save()
    if error:
        return error

    return jsonify({
        "message": "Usuario registrado correctamente",
        "user": user.to_dict()
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Inicia sesión y obtiene un JWT.
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: alessandro@gmail.com
            password:
              type: string
              example: 123456
    responses:
      200:
        description: Login exitoso
      400:
        description: Datos incompletos
      401:
        description: Credenciales incorrectas
    """

    data = json_object()
    email = _email(data)
    password = _password(data)
    user = _by_email(email)

    if not user:
        return jsonify({
            "error": "Credenciales incorrectas"
        }), 401

    valid_password = bcrypt.checkpw(
        password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    )

    if not valid_password:
        return jsonify({
            "error": "Credenciales incorrectas"
        }), 401

    access_token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "message": "Login exitoso",
        "access_token": access_token,
        "user": user.to_dict()
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    Obtiene los datos del usuario autenticado.
    ---
    tags:
      - Auth
    securityDefinitions:
      - Bearer:
          type: apiKey
          name: Authorization
          in: header
    security:
      - Bearer: []
    responses:
      200:
        description: Usuario actual
      401:
        description: Token inválido o ausente
      404:
        description: Usuario no encontrado
    """

    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    return jsonify(user.to_dict(with_created=True)), 200

@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_profile():
    """
    Actualiza el perfil del usuario autenticado.
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: Alessandro Matius
            email:
              type: string
              example: alessandro@example.com
    responses:
      200:
        description: Perfil actualizado correctamente
      400:
        description: Datos inválidos
      409:
        description: El email ya está registrado
      404:
        description: Usuario no encontrado
    """

    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    data = json_object()
    if "name" not in data and "email" not in data:
        return jsonify({
            "error": "Debe enviar al menos name o email"
        }), 400

    name = text_field(data, "name", 100) if "name" in data else user.name
    email = _email(data) if "email" in data else user.email
    if email != user.email:
        existing_user = _by_email(email)
        if existing_user and existing_user.id != user.id:
            return jsonify({
                "error": "El email ya está registrado"
            }), 409

    user.name, user.email = name, email
    error = _save()
    if error:
        return error

    return jsonify({
        "message": "Perfil actualizado correctamente",
        "user": user.to_dict(with_created=True)
    }), 200

@auth_bp.route("/me/password", methods=["PUT"])
@jwt_required()
def update_password():
    """
    Cambia la contraseña del usuario autenticado.
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - current_password
            - new_password
          properties:
            current_password:
              type: string
              example: password123
            new_password:
              type: string
              example: nuevaPassword456
    responses:
      200:
        description: Contraseña actualizada correctamente
      400:
        description: Datos incompletos
      401:
        description: Contraseña actual incorrecta
      404:
        description: Usuario no encontrado
    """

    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    data = json_object()
    current_password = _password(data, "current_password")
    new_password = _password(data, "new_password", minimum=6)

    if not bcrypt.checkpw(
        current_password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    ):
        return jsonify({
            "error": "La contraseña actual es incorrecta"
        }), 401

    hashed_password = bcrypt.hashpw(
        new_password.encode("utf-8"),
        bcrypt.gensalt()
    )

    user.password_hash = hashed_password.decode("utf-8")

    db.session.commit()

    return jsonify({
        "message": "Contraseña actualizada correctamente"
    }), 200


@auth_bp.route("/me", methods=["DELETE"])
@jwt_required()
def delete_account():
    """
    Elimina la cuenta del usuario autenticado.
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: Cuenta eliminada correctamente
      404:
        description: Usuario no encontrado
    """

    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({
        "message": "Cuenta eliminada correctamente"
    }), 200

