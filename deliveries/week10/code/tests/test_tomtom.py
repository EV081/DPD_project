from __future__ import annotations

import datetime as dt

import pytest

from pipeline import config, ingest_tomtom


@pytest.fixture()
def trafico_limpio(db):
    with db.transaction():
        db.execute("TRUNCATE log_inferencia, trafico_en_vivo")
    yield db


def test_ratio_sintetico_determinista_y_en_rango():
    habil = dt.datetime(2026, 1, 6, 8, 0)  # martes
    assert habil.weekday() < 5
    r1 = ingest_tomtom.ratio_sintetico(habil)
    r2 = ingest_tomtom.ratio_sintetico(habil)
    assert r1 == r2, "el fallback debe ser determinista"
    assert 1.0 <= r1 <= 3.0

    horas = {
        h: ingest_tomtom.ratio_sintetico(habil.replace(hour=h))
        for h in range(24)
    }
    assert all(1.0 <= v <= 3.0 for v in horas.values())
    assert horas[8] > horas[3], "pico manana > madrugada"
    assert horas[18] > horas[3], "pico tarde > madrugada"

    sabado = dt.datetime(2026, 1, 10, 8, 0)
    assert sabado.weekday() == 5
    assert 1.0 <= ingest_tomtom.ratio_sintetico(sabado) <= 3.0


def test_snapshot_sin_api_cae_a_fallback(trafico_limpio, monkeypatch):
    monkeypatch.setattr(config, "TOMTOM_API_KEY", "")
    resumen = ingest_tomtom.snapshot(trafico_limpio)
    assert resumen == {"tomtom": 0, "fallback": 6, "segmentos": 6}

    filas = trafico_limpio.execute(
        "SELECT segmento, fuente, ratio_congestion FROM trafico_en_vivo "
        "ORDER BY segmento"
    ).fetchall()
    assert len(filas) == 6
    assert all(f["fuente"] == "fallback" for f in filas)
    assert all(1.0 <= f["ratio_congestion"] <= 3.0 for f in filas)

    logs = trafico_limpio.execute(
        "SELECT fuente, status FROM log_inferencia ORDER BY id"
    ).fetchall()
    assert len(logs) == 6
    assert all(l["fuente"] == "fallback" for l in logs)
    assert all(l["status"].startswith("fallback:") for l in logs)


def test_snapshot_tomtom_ok_mockeado(trafico_limpio, monkeypatch):
    def _fake(client, seg):
        return {
            "actual": 25.0,
            "libre": 50.0,
            "ratio": 2.0,
            "detalle": {"currentSpeed": 25, "freeFlowSpeed": 50},
        }

    monkeypatch.setattr(ingest_tomtom, "_obtener", _fake)
    resumen = ingest_tomtom.snapshot(trafico_limpio)
    assert resumen == {"tomtom": 6, "fallback": 0, "segmentos": 6}

    fila = trafico_limpio.execute(
        "SELECT fuente, ratio_congestion, actual_speed_kph "
        "FROM trafico_en_vivo WHERE segmento = 'javier_prado_salaverry'"
    ).fetchone()
    assert fila["fuente"] == "tomtom"
    assert fila["ratio_congestion"] == 2.0
    assert fila["actual_speed_kph"] == 25.0

    log = trafico_limpio.execute(
        "SELECT fuente, status, latencia_ms FROM log_inferencia "
        "ORDER BY id LIMIT 1"
    ).fetchone()
    assert log["fuente"] == "tomtom"
    assert log["status"] == "ok"
    assert log["latencia_ms"] >= 0


def test_snapshot_excepcion_cae_a_fallback(trafico_limpio, monkeypatch):
    def _boom(client, seg):
        raise TimeoutError("timeout simulado")

    monkeypatch.setattr(ingest_tomtom, "_obtener", _boom)
    resumen = ingest_tomtom.snapshot(trafico_limpio)
    assert resumen["fallback"] == 6 and resumen["tomtom"] == 0

    log = trafico_limpio.execute(
        "SELECT status, detalle FROM log_inferencia ORDER BY id LIMIT 1"
    ).fetchone()
    assert log["status"] == "fallback:TimeoutError"
    assert "timeout simulado" in log["detalle"]["motivo"]
