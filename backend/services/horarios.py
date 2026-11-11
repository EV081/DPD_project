"""Horario y frecuencia publicados de cada servicio (``data/horarios_servicios.json``).

Los datos vienen de metrolima.info (sitio no oficial) y se generan con
``scripts/construir_horarios_servicios.py``. Son referenciales: sirven para saber si un servicio
circula a una hora y cada cuánto pasa, no para reemplazar la oferta del modelo de ocupación.

Sistemas: ``metropolitano`` (un registro por servicio: Ruta A, Expreso 5…), ``metro_l1``
(``Línea 1``), ``corredor`` (por ruta) y ``alimentador`` (por serie del modelo). Los sentidos
``asc``/``desc`` son los del modelo de cada sistema.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

from services import calendario

ARCHIVO = Path(__file__).resolve().parent.parent / "data" / "horarios_servicios.json"
HORAS_PUNTA = frozenset({6, 7, 8, 17, 18, 19})   # las del perfil de oferta del modelo troncal
SISTEMA_HORARIO = {"troncal": "metropolitano", "metro_l1": "metro_l1", "corredor": "corredor",
                   "alimentador": "alimentador"}


@lru_cache(maxsize=1)
def datos() -> dict:
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def fuente() -> dict:
    return datos()["fuente"]


def tipo_dia(fecha: dt.date) -> str:
    """'LAB' | 'SAB' | 'DOM'. Los feriados nacionales usan el horario de domingo."""
    if calendario.tipo_dia(fecha)[0] == "feriado" or fecha.weekday() == 6:
        return "DOM"
    return "SAB" if fecha.weekday() == 5 else "LAB"


def servicios(sistema: str) -> dict:
    return datos()["servicios"].get(sistema, {})


def servicio(sistema: str, nombre: str) -> dict | None:
    """Registro del servicio. Para sistemas del modelo: troncal -> metropolitano; Metro L1 -> 'Línea 1'."""
    sistema = SISTEMA_HORARIO.get(sistema, sistema)
    return servicios(sistema).get("Línea 1" if sistema == "metro_l1" else nombre)


def _minutos(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _tramos(reg: dict, sentido: str | None, fecha: dt.date) -> list[tuple[int, int | None]]:
    """Tramos (inicio, fin) en minutos del día; el fin pasa de 1440 si cruza la medianoche."""
    if reg.get("dias_semana") and fecha.weekday() not in reg["dias_semana"]:
        return []
    horario = reg.get("horario") or {}
    por_dia = horario.get(sentido) if sentido in horario else None
    if por_dia is None and sentido is None:
        por_dia = next(iter(horario.values()), None)
    out = []
    for ini, fin in (por_dia or {}).get(tipo_dia(fecha), []):
        a = _minutos(ini)
        b = None if fin is None else _minutos(fin)
        out.append((a, b + 1440 if b is not None and b <= a else b))
    return out


def _publicado(reg: dict | None) -> bool:
    return bool(reg) and any((reg.get("horario") or {}).values())


def opera(reg: dict | None, sentido: str | None, momento: dt.datetime) -> bool | None:
    """¿Circula el servicio en ``momento``? None si la fuente no publica su horario."""
    if not _publicado(reg):
        return None
    if sentido is not None and sentido not in reg["horario"]:
        return False                              # el servicio no circula en ese sentido
    t = momento.hour * 60 + momento.minute
    hoy, ayer = momento.date(), momento.date() - dt.timedelta(days=1)
    if any(a <= t and (b is None or t < b) for a, b in _tramos(reg, sentido, hoy)):
        return True
    return any(b is not None and a <= t + 1440 < b for a, b in _tramos(reg, sentido, ayer))


def intervalo_min(reg: dict | None, momento: dt.datetime) -> float | None:
    """Minutos entre vehículos publicados para ese tipo de día y hora (None si no se publica)."""
    f = ((reg or {}).get("intervalo_min") or {}).get(tipo_dia(momento.date()))
    if not f:
        return None
    return f.get("punta") if momento.hour in HORAS_PUNTA else f.get("valle")


def texto_horario(reg: dict | None, sentido: str | None, fecha: dt.date) -> str | None:
    """'05:00–23:00' (o varios tramos) del día; 'No opera este día' si no hay tramos; None si no se publica."""
    if not _publicado(reg):
        return None
    if sentido is not None and sentido not in reg["horario"]:
        return "No circula en este sentido"
    tramos = _tramos(reg, sentido, fecha)
    if not tramos:
        return "No opera este día"

    def fmt(m: int | None) -> str:
        return "cierre no publicado" if m is None else f"{(m // 60) % 24:02d}:{m % 60:02d}"
    return " y ".join(f"{fmt(a)}–{fmt(b)}" for a, b in tramos)
