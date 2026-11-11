"""Configuración mínima para conservar las sesiones al reiniciar la demo local."""
import os
import secrets
from pathlib import Path


def jwt_secret(instance_path):
    configured = os.getenv("JWT_SECRET_KEY", "").strip()
    if configured:
        return configured
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url and not database_url.startswith("sqlite:"):
        raise RuntimeError("Configura JWT_SECRET_KEY en el entorno antes de iniciar con Postgres.")

    # Este archivo se crea en el equipo del alumno; nunca forma parte de la entrega.
    directory = Path(instance_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".jwt-secret"
    try:
        with path.open("x", encoding="utf-8") as file:
            os.chmod(path, 0o600)
            file.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("La clave local está vacía. Define JWT_SECRET_KEY en backend/.env.")
    return value
