"""Control de acceso por rol. ``current_user`` lo resuelve ``user_lookup_loader`` de app.py (consulta la base en cada petición)."""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import current_user, verify_jwt_in_request


def admin_required(fn):
    """Solo administradores. 401 sin sesión válida (o cuenta eliminada); 403 si la cuenta no es admin."""
    @wraps(fn)
    def envoltura(*args, **kwargs):
        verify_jwt_in_request()
        if current_user is None or getattr(current_user, "role", None) != "admin":
            return jsonify({"error": "Se requiere una cuenta de administrador"}), 403
        return fn(*args, **kwargs)
    return envoltura
