"""Feedback mínimo de usuario: "Ya abordé" (espera real) + aforo percibido muestreado.

Espera real = ``t_aborde - t_consulta``; se usa para MEDIR el error del ETA, no para
reentrenar. El aforo percibido es opcional (NULL si el usuario omite) y se pregunta con
probabilidad ``config.FEEDBACK_AFORO_PROB`` (demo 1.0, prod 0.2-0.33).
"""
from __future__ import annotations

import datetime as dt
import random

from pipeline import config

CLASES_AFORO = ("Asientos", "De_pie", "Saturado")


def debe_preguntar_aforo(prob: float | None = None, rng: random.Random | None = None) -> bool:
    prob = config.FEEDBACK_AFORO_PROB if prob is None else prob
    return (rng or random).random() < prob


def registrar_consulta(conn, sistema: str, unidad: str, eta_mostrado_min: float,
                       eta2_mostrado_min: float, aforo_mostrado: str, modo_datos: str,
                       edad_snapshot_s: float | None, t_consulta: dt.datetime | None = None,
                       entorno: str | None = None) -> int:
    t = t_consulta or dt.datetime.now(dt.timezone.utc)
    return conn.execute(
        """
        INSERT INTO feedback_usuario
            (sistema, unidad, fecha, hora, t_consulta, eta_mostrado_min, eta2_mostrado_min,
             aforo_mostrado, modo_datos, edad_snapshot_s, entorno)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """,
        (sistema, unidad, t.date(), t.hour, t, eta_mostrado_min, eta2_mostrado_min,
         aforo_mostrado, modo_datos, edad_snapshot_s, entorno or config.ENTORNO),
    ).fetchone()["id"]


def registrar_aborde(conn, feedback_id: int, aforo_percibido: str | None = None,
                     t_aborde: dt.datetime | None = None) -> float | None:
    """Cierra la consulta; devuelve la espera real en minutos."""
    if aforo_percibido is not None and aforo_percibido not in CLASES_AFORO:
        raise ValueError(f"aforo_percibido invalido: {aforo_percibido!r}")
    t = t_aborde or dt.datetime.now(dt.timezone.utc)
    row = conn.execute(
        """
        UPDATE feedback_usuario SET t_aborde = %s, aforo_percibido = %s
        WHERE id = %s RETURNING t_consulta
        """,
        (t, aforo_percibido, feedback_id),
    ).fetchone()
    if row is None:
        raise KeyError(f"feedback {feedback_id} inexistente")
    return (t - row["t_consulta"]).total_seconds() / 60.0
