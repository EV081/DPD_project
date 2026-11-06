"""Búsqueda de destinos en Lima: zona permitida, alias de lugares conocidos y normalización del texto.

Los geocodificadores (LocationIQ/Nominatim) no conocen siglas como "UTEC" (devuelven una calle de Ayacucho),
así que los lugares frecuentes se resuelven aquí, con coordenadas verificadas contra el propio geocodificador.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

# Lima Metropolitana y Callao, en el orden que piden LocationIQ y Nominatim:
# (lon_oeste, lat_norte, lon_este, lat_sur)
VIEWBOX_LIMA = (-77.20, -11.75, -76.75, -12.30)


def viewbox_param() -> str:
    return ",".join(str(v) for v in VIEWBOX_LIMA)


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos, con espacios simples: 'Ingeniería, y  Tecnología' -> 'ingenieria y tecnologia'."""
    s = unicodedata.normalize("NFD", texto or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


# Lugares conocidos de Lima (backend/data/lugares_lima.json). Cada uno: nombre, distrito, formas de escribirlo y
# coordenadas. Las coordenadas salen del propio geocodificador y se revisaron una por una; los que no se pudieron
# confirmar se dejaron fuera a propósito (mejor omitir un lugar que mandar a alguien al sitio equivocado).
ARCHIVO = Path(__file__).resolve().parent.parent / "data" / "lugares_lima.json"
MAX_FAVORITOS = 4   # para que los favoritos no tapen los resultados del geocodificador


def _cargar() -> list[dict]:
    try:
        crudos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [{
        "claves": [normalizar(c) for c in l["claves"]],
        "display_name": f"{l['nombre']}, {l['distrito']}, Lima",
        "lat": float(l["lat"]), "lon": float(l["lon"]),
    } for l in crudos]


LUGARES: list[dict] = _cargar()


def buscar_alias(consulta: str) -> list[dict]:
    """Lugares conocidos que coinciden con lo escrito: primero los que coinciden exacto y luego los que empiezan así."""
    q = normalizar(consulta)
    if len(q) < 3:
        return []
    exactos, parciales = [], []
    for lugar in LUGARES:
        res = {"display_name": lugar["display_name"], "lat": lugar["lat"], "lon": lugar["lon"]}
        if q in lugar["claves"]:
            exactos.append(res)
        elif any(c.startswith(q) for c in lugar["claves"]):
            parciales.append(res)
    return (exactos + parciales)[:MAX_FAVORITOS]
