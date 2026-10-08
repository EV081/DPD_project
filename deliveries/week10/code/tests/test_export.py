from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from export import export_data
from pipeline import config


@pytest.fixture()
def export_tmp(db_cargado, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EXPORT_DIR", tmp_path / "export")

    modelo_src = tmp_path / "modelo_src"
    modelo_src.mkdir()
    for nombre in export_data.ARCHIVOS_MODELO:
        (modelo_src / nombre).write_text(f"dummy {nombre}\n", encoding="utf-8")
    monkeypatch.setattr(config, "MODELO_OUTPUTS_DIR", modelo_src)

    with db_cargado.transaction():
        db_cargado.execute("TRUNCATE trafico_en_vivo, log_inferencia")
        db_cargado.execute(
            "INSERT INTO trafico_en_vivo (segmento, lat, lon, "
            "actual_speed_kph, free_flow_speed_kph, ratio_congestion, fuente) "
            "VALUES ('test', -12.1, -77.0, 30.0, 50.0, 1.667, 'fallback')"
        )
    return export_data.run()


def test_export_genera_archivos(export_tmp):
    for nombre in [
        "muestra_demanda_fiable.csv",
        "resumen_por_sistema.csv",
        "perfil_horario.csv",
        "trafico_tomtom.json",
        "manifiesto_export.json",
    ]:
        assert (export_tmp / nombre).exists(), f"falta {nombre}"


def test_export_muestra_100k(export_tmp):
    muestra = pd.read_csv(
        export_tmp / "muestra_demanda_fiable.csv", low_memory=False
    )
    assert len(muestra) == 100_000
    assert set(muestra["sistema"]) == {
        "corredor",
        "alimentador",
        "troncal",
        "metro_l1",
    }


def test_export_resumen_por_sistema(export_tmp):
    resumen = pd.read_csv(export_tmp / "resumen_por_sistema.csv")
    assert len(resumen) == 4
    assert int(resumen["filas"].sum()) == config.FIABLE_TOTAL_ESPERADO
    assert set(resumen["sistema"]) == set(config.FIABLE_ESPERADO)


def test_export_perfil_horario(export_tmp):
    perfil = pd.read_csv(export_tmp / "perfil_horario.csv")
    # metro_l1 opera 5-22 (18 h); el resto cubre las 24 h -> 3*24 + 18 = 90
    assert len(perfil) == 90
    horas = perfil.groupby("sistema")["hora"].apply(lambda s: set(s))
    assert horas["corredor"] == set(range(24))
    assert horas["alimentador"] == set(range(24))
    assert horas["troncal"] == set(range(24))
    assert horas["metro_l1"] == set(range(5, 23))


def test_export_trafico_json(export_tmp):
    data = json.loads(
        (export_tmp / "trafico_tomtom.json").read_text(encoding="utf-8")
    )
    assert len(data["segmentos"]) == 1
    assert data["segmentos"][0]["segmento"] == "test"
    assert data["segmentos"][0]["ratio_congestion"] == 1.667


def test_export_copia_outputs_modelo(export_tmp):
    for nombre in export_data.ARCHIVOS_MODELO:
        assert (export_tmp / "modelo" / nombre).exists(), f"falta modelo/{nombre}"


def test_export_manifiesto_sha256_y_conteos(export_tmp):
    manifiesto = json.loads(
        (export_tmp / "manifiesto_export.json").read_text(encoding="utf-8")
    )
    assert manifiesto["conteos_bd"]["demanda_fiable"] == (
        config.FIABLE_TOTAL_ESPERADO
    )
    assert manifiesto["conteos_bd"]["corredores_hora"] == 8_253_635

    archivos = manifiesto["archivos"]
    assert "muestra_demanda_fiable.csv" in archivos
    ruta = export_tmp / "muestra_demanda_fiable.csv"
    sha = hashlib.sha256(ruta.read_bytes()).hexdigest()
    assert archivos["muestra_demanda_fiable.csv"]["sha256"] == sha
