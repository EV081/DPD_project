"""Ingesta de Google Places: cache en CSV, filtrado por tipo y candidatos (sin red ni clave)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "03_georef"))
pytest.importorskip("pandas")
import consultar_google_paraderos as CG  # noqa: E402
import geocodificar_alimentadores as GA  # noqa: E402


def _csv(path: Path, filas: list[dict], cols: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)


@pytest.fixture()
def fuentes(tmp_path, monkeypatch):
    cols = ["grupo", "servicio", "codigo", "bloque", "orden", "paradero"]
    _csv(tmp_path / "alimentadores_paraderos_atu.csv", [
        {"grupo": "AlimentadoresNorte", "servicio": "Naranjal", "codigo": "", "bloque": 1, "orden": 1,
         "paradero": "Las Palmeras"},
        {"grupo": "AlimentadoresNorte", "servicio": "Naranjal", "codigo": "", "bloque": 2, "orden": 5,
         "paradero": "Las Palmeras"},                                    # duplicado: una sola consulta
        {"grupo": "AlimentadoresNorte", "servicio": "Naranjal", "codigo": "", "bloque": 1, "orden": 2,
         "paradero": "Huandoy"}], cols)
    monkeypatch.setattr(CG, "FUENTES", tmp_path)
    monkeypatch.setattr(CG, "SALIDA", tmp_path / "google_paraderos.csv")
    return tmp_path


def test_consultas_se_deduplican_y_no_se_repiten(fuentes):
    pend = CG.consultas_pendientes()
    assert [(s, n) for s, n, _ in pend] == [("Norte/Naranjal", "Las Palmeras"), ("Norte/Naranjal", "Huandoy")]
    _csv(CG.SALIDA, [{"servicio": "Norte/Naranjal", "consulta": "huandoy", "rank": 1, "lat": "-12.0",
                      "lon": "-77.0", "tipos": "bus_stop"}], CG.COLUMNAS)
    assert [n for _, n, _ in CG.consultas_pendientes()] == ["Las Palmeras"]   # ya registrada: no se paga


def test_cargar_google_solo_paradas(fuentes):
    _csv(CG.SALIDA, [
        {"servicio": "S", "consulta": "a", "rank": 1, "lat": "-12.0", "lon": "-77.0", "tipos": "bus_stop|point_of_interest"},
        {"servicio": "S", "consulta": "a", "rank": 2, "lat": "-12.5", "lon": "-77.5", "tipos": "restaurant"},
        {"servicio": "S", "consulta": "b", "rank": 0, "lat": "", "lon": "", "tipos": ""}], CG.COLUMNAS)
    assert CG.cargar_google() == {("S", "a"): [(-12.0, -77.0)]}


def test_candidatos_con_extra_no_duplica():
    c = GA.candidatos("Zzz inexistente", {}, extra=[(-12.0, -77.0), (-12.00001, -77.00001), (-12.1, -77.1)])
    assert len(c) == 2          # el segundo cae a < 8 m del primero


def test_confianza_google_es_media():
    assert GA.confianza("google_places", 1) == "media"
