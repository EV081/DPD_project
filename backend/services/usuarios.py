"""Roles de usuario y creación del administrador desde variables de entorno.

El único camino para ser administrador es este: ``flask --app app seed-admin`` (o el arranque automático de la API)
lee ``SEED_ADMIN_EMAIL`` / ``SEED_ADMIN_PASSWORD`` / ``SEED_ADMIN_NAME``. El registro público siempre crea rol ``user``.
"""
from __future__ import annotations

import os

import bcrypt
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from db.connection import db

PASSWORD_MIN = 8
# valores de ejemplo que nunca deben quedar como credencial real
_PLACEHOLDERS = {"cambia_esto", "changeme", "password", "admin", "12345678", "tu_clave_aqui"}


class SeedError(ValueError):
    """Configuración del administrador inválida (mensaje apto para mostrar en consola)."""


def asegurar_columna_role(engine=None) -> bool:
    """Agrega ``users.role`` en bases creadas antes de existir los roles (``create_all`` no altera tablas existentes).

    Devuelve True si hubo que crearla. Es seguro llamarla en cada arranque y desde varios procesos a la vez.
    """
    engine = engine or db.engine
    columnas = {c["name"] for c in inspect(engine).get_columns("users")}
    if "role" in columnas:
        return False
    try:
        with engine.begin() as con:
            con.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(10) NOT NULL DEFAULT 'user'"))
    except (OperationalError, ProgrammingError):
        # otro worker la creó entre la lectura y el ALTER
        if "role" not in {c["name"] for c in inspect(engine).get_columns("users")}:
            raise
        return False
    return True


def credenciales_admin() -> tuple[str, str, str] | None:
    """(nombre, correo, clave) del .env, o None si no se configuraron. Lanza SeedError si están a medias o son débiles."""
    email = os.getenv("SEED_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("SEED_ADMIN_PASSWORD", "")
    nombre = os.getenv("SEED_ADMIN_NAME", "").strip() or "Administrador"
    if not email and not password:
        return None
    if not email or not password:
        raise SeedError("Define SEED_ADMIN_EMAIL y SEED_ADMIN_PASSWORD juntos en backend/.env.")
    if email.count("@") != 1 or any(c.isspace() for c in email) or not all(email.split("@")):
        raise SeedError("SEED_ADMIN_EMAIL no tiene un formato de correo válido.")
    if len(password) < PASSWORD_MIN or password.lower() in _PLACEHOLDERS:
        raise SeedError(f"SEED_ADMIN_PASSWORD debe tener al menos {PASSWORD_MIN} caracteres y no ser un valor de ejemplo.")
    if len(password.encode("utf-8")) > 72:
        raise SeedError("SEED_ADMIN_PASSWORD admite como máximo 72 bytes (límite de bcrypt).")
    return nombre[:100], email, password


def sembrar_admin() -> dict:
    """Crea o actualiza al administrador. Idempotente: el .env manda sobre nombre, rol y contraseña.

    Retorna ``{"estado": "creado" | "actualizado" | "sin_cambios" | "omitido", "email": ...}``.
    """
    from routes.auth import User, _by_email

    creds = credenciales_admin()
    if creds is None:
        return {"estado": "omitido", "motivo": "SEED_ADMIN_EMAIL y SEED_ADMIN_PASSWORD no están definidos"}
    nombre, email, password = creds

    def _aplicar() -> str:
        user = _by_email(email)
        if user is None:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            db.session.add(User(name=nombre, email=email, password_hash=hashed, role="admin"))
            db.session.commit()
            return "creado"
        cambios = []
        if user.role != "admin":
            user.role = "admin"
            cambios.append("rol")
        if user.name != nombre:
            user.name = nombre
            cambios.append("nombre")
        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            user.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cambios.append("contraseña")
        if not cambios:
            return "sin_cambios"
        db.session.commit()
        return "actualizado"

    try:
        estado = _aplicar()
    except IntegrityError:
        # dos workers de gunicorn sembrando a la vez: el segundo ya encuentra al usuario
        db.session.rollback()
        estado = _aplicar()
    return {"estado": estado, "email": email}


def sembrar_al_arrancar(log=print) -> None:
    """Llamada desde ``app.py``. Nunca impide arrancar: un error de configuración solo se avisa."""
    if os.getenv("SEED_ADMIN_ON_START", "1").strip() in ("0", "false", "no"):
        return
    try:
        r = sembrar_admin()
    except SeedError as exc:
        log(f"[seed-admin] omitido: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - la API debe poder arrancar sin el administrador
        db.session.rollback()
        log(f"[seed-admin] no se pudo crear el administrador: {exc}")
        return
    if r["estado"] != "omitido":
        log(f"[seed-admin] {r['estado']}: {r['email']}")
