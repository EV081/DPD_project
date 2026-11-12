"""Horario y frecuencia publicados de cada servicio (``data/horarios_servicios.json``).

Los horarios ATU revisados en ``horarios_atu_oficial.json`` prevalecen sobre el catálogo
secundario de metrolima.info. Las frecuencias y paradas conservan su procedencia secundaria.
Son referenciales; no reemplazan la oferta del modelo de ocupación.

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
from services.mapeo_estaciones import norm

ARCHIVO = Path(__file__).resolve().parent.parent / "data" / "horarios_servicios.json"
HORAS_PUNTA = frozenset({6, 7, 8, 17, 18, 19})   # las del perfil de oferta del modelo troncal
SISTEMA_HORARIO = {"troncal": "metropolitano", "metro_l1": "metro_l1", "corredor": "corredor",
                   "alimentador": "alimentador"}


@lru_cache(maxsize=1)
def datos() -> dict:
    base = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    oficial = json.loads(ARCHIVO.with_name("horarios_atu_oficial.json").read_text(encoding="utf-8"))
    for sistema in ("metropolitano", "metro_l1", "corredor"):
        for nombre, reg in base["servicios"][sistema].items():
            ficha = oficial["servicios"][sistema].get(nombre)
            if ficha:
                _aplicar_oficial(reg, ficha, sistema)
    base["fuente"] = {**oficial["fuente"], "nombre": "ATU y fuentes complementarias",
        "aviso": "Horarios de Metro L1, corredores y Metropolitano: portal oficial ATU. "
                 "Frecuencias, paradas y horarios de alimentadores: catálogo secundario metrolima.info; "
                 "algunas frecuencias son calibradas, no publicadas por ATU. Feriados sin confirmación oficial."}
    return base


def _aplicar_oficial(reg: dict, ficha: dict, sistema: str) -> None:
    anteriores = {k: reg.get(k) for k in ("url", "notas", "intervalo_min", "paradas")}
    semanal, etiquetas = {}, {}
    for i, direccion in enumerate(ficha["direcciones"]):
        label = direccion["sentido_publicado"]
        if sistema == "corredor":
            keys = [f"sentido_{i + 1}"]  # La ficha usa terminales, no los asc/desc del modelo.
        elif norm(label) == "ambos sentidos":
            keys = ["asc", "desc"]
        else:
            origen, destino = norm(label).split(" a ", 1)
            orden = ("chimpu ocllo", "22 de agosto", "los incas", "naranjal", "izaguirre", "tomas valle",
                     "uni", "ramon castilla", "central", "aramburu", "angamos", "ricardo palma", "benavides",
                     "28 de julio", "plaza de flores", "matellini")
            def posicion(extremo):
                coincidencias = [i for i, nombre in enumerate(orden) if nombre in extremo]
                if len(coincidencias) != 1:
                    raise ValueError(f"Terminal ATU sin correspondencia inequívoca: {extremo}")
                return coincidencias[0]
            keys = ["desc" if posicion(origen) < posicion(destino) else "asc"]
        for key in keys:
            por_dia = semanal.setdefault(key, {})
            etiquetas[key] = label
            for regla in direccion["reglas"]:
                for dia in regla["dias_semana"]:
                    por_dia[str(dia)] = regla["tramos"]
    reg.pop("dias_semana", None)
    reg.update({"url": ficha["url"], "fuente_horario": "ATU", "horario_semanal": semanal,
                "sentidos_publicados": etiquetas, "evidencias_horario": ficha["direcciones"],
                "procedencia_complementaria": anteriores,
                "notas": ficha["notas"] + ["Horario ATU por sentido y día. Frecuencia y paradas de fuente complementaria; no verificadas como oficiales en esta extracción."]})
    # Compatibilidad con los consumidores que consultan las claves de sentido/tipo de día.
    reg["horario"] = {key: {tipo: days[str(d)] for tipo, d in (("LAB", 0), ("SAB", 5), ("DOM", 6)) if str(d) in days}
                      for key, days in semanal.items()}


def fuente() -> dict:
    return datos()["fuente"]


def tipo_dia(fecha: dt.date) -> str:
    """'LAB' | 'SAB' | 'DOM'. Los feriados nacionales usan el tipo DOM; las fichas ATU requieren confirmación específica."""
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
    if reg.get("fuente_horario") == "ATU":
        key = sentido if sentido is not None else next(iter(reg["horario_semanal"]), None)
        tramos = reg["horario_semanal"].get(key, {}).get(str(fecha.weekday()), [])
        if calendario.tipo_dia(fecha)[0] == "feriado":
            tramos = []  # La ficha no declara una regla para feriados.
    else:
        tramos = (por_dia or {}).get(tipo_dia(fecha), [])
    for ini, fin in tramos:
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
    if reg.get("fuente_horario") == "ATU" and sentido is None and len(reg["horario"]) > 1:
        estados = [opera(reg, key, momento) for key in reg["horario"]]
        return estados[0] if all(e is estados[0] for e in estados) else None
    t = momento.hour * 60 + momento.minute
    hoy, ayer = momento.date(), momento.date() - dt.timedelta(days=1)
    if any(a <= t and (b is None or t < b) for a, b in _tramos(reg, sentido, hoy)):
        return True
    if any(b is not None and a <= t + 1440 < b for a, b in _tramos(reg, sentido, ayer)):
        return True
    if reg.get("fuente_horario") == "ATU":
        if calendario.tipo_dia(hoy)[0] == "feriado": return None
        key = sentido if sentido is not None else next(iter(reg["horario_semanal"]), None)
        if str(hoy.weekday()) not in reg["horario_semanal"].get(key, {}): return None
    return False


def intervalo_min(reg: dict | None, momento: dt.datetime) -> float | None:
    """Intervalo de referencia secundario/calibrado; no es una frecuencia verificada de ATU."""
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
    if reg.get("fuente_horario") == "ATU" and sentido is None and len(reg["horario"]) > 1:
        textos = {key: texto_horario(reg, key, fecha) for key in reg["horario"]}
        if len(set(textos.values())) == 1: return next(iter(textos.values()))
        return "; ".join(f"{reg['sentidos_publicados'][key]}: {texto}" for key, texto in textos.items())
    if reg.get("fuente_horario") == "ATU":
        key = sentido if sentido is not None else next(iter(reg["horario_semanal"]), None)
        if calendario.tipo_dia(fecha)[0] == "feriado" or str(fecha.weekday()) not in reg["horario_semanal"].get(key, {}):
            return "Horario no publicado para este día"
    tramos = _tramos(reg, sentido, fecha)
    if not tramos:
        return "No opera este día"

    def fmt(m: int | None) -> str:
        return "cierre no publicado" if m is None else f"{(m // 60) % 24:02d}:{m % 60:02d}"
    return " y ".join(f"{fmt(a)}–{fmt(b)}" for a, b in tramos)
