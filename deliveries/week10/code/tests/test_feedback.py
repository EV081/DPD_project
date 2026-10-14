from __future__ import annotations

import datetime as dt
import random

import pytest

from pipeline import feedback


def test_probabilidad_extremos():
    rng = random.Random(0)
    assert all(feedback.debe_preguntar_aforo(1.0, rng) for _ in range(100))
    assert not any(feedback.debe_preguntar_aforo(0.0, rng) for _ in range(100))


def test_probabilidad_intermedia_cercana():
    rng = random.Random(1)
    n = sum(feedback.debe_preguntar_aforo(0.25, rng) for _ in range(4000))
    assert 0.20 < n / 4000 < 0.30


@pytest.fixture()
def fb_limpio(db):
    with db.transaction():
        db.execute("TRUNCATE feedback_usuario")
    return db


def test_espera_real_y_aforo_opcional(fb_limpio):
    t0 = dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc)
    fid = feedback.registrar_consulta(fb_limpio, "corredor", "Ruta A", 8.0, 14.0, "De_pie",
                                      "en_vivo", 90.0, t_consulta=t0, entorno="demo")
    espera = feedback.registrar_aborde(fb_limpio, fid, None, t0 + dt.timedelta(minutes=9, seconds=30))
    assert espera == pytest.approx(9.5)
    fila = fb_limpio.execute("SELECT * FROM feedback_usuario WHERE id = %s", (fid,)).fetchone()
    assert fila["aforo_percibido"] is None and fila["entorno"] == "demo"
    assert fila["modo_datos"] == "en_vivo"


def test_aforo_percibido_invalido(fb_limpio):
    fid = feedback.registrar_consulta(fb_limpio, "corredor", "Ruta A", 8.0, 14.0, "De_pie", "historico", None)
    with pytest.raises(ValueError):
        feedback.registrar_aborde(fb_limpio, fid, "Vacio")
