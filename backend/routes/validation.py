"""Validaciones pequeñas compartidas por los formularios y las consultas del mapa."""
import math

from flask import request
from werkzeug.exceptions import BadRequest


def json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("El cuerpo debe ser un objeto JSON")
    return data


def text_field(data, name, maximum, *, strip=True):
    value = data.get(name)
    if not isinstance(value, str):
        raise BadRequest(f"{name} debe ser texto")
    value = value.strip() if strip else value
    if not value or len(value) > maximum:
        raise BadRequest(f"{name} debe tener entre 1 y {maximum} caracteres")
    return value


def number(value, name, minimum=None, maximum=None):
    if isinstance(value, bool):
        raise BadRequest(f"{name} debe ser numérico")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise BadRequest(f"{name} debe ser numérico") from None
    if not math.isfinite(result):
        raise BadRequest(f"{name} debe ser un número finito")
    if minimum is not None and result < minimum or maximum is not None and result > maximum:
        raise BadRequest(f"{name} está fuera del rango permitido")
    return result


def coordinates(lat, lon):
    return number(lat, "latitud", -90, 90), number(lon, "longitud", -180, 180)
