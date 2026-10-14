"""Revisión humana y completado por calle (sin BD ni archivos reales)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
pytest.importorskip("pandas")
import geocodificar_alimentadores as G  # noqa: E402


def test_clave_calle_ignora_tipo_de_via():
    assert G.clave_calle("Jirón Las Crucetas") == G.clave_calle("Calle Las Crucetas") == "las crucetas"
    assert G.clave_calle("Av. Alcides Vigo") == "alcides vigo"


def test_variantes_alias_y_notas():
    assert G._variantes_nombre("Cáceres (Jamaica)") == ["Cáceres", "Jamaica"]
    assert G._variantes_nombre("Cementerio (domingos) (*)") == ["Cementerio"]


def test_correcciones_csv(tmp_path, monkeypatch):
    f = tmp_path / "c.csv"
    f.write_text("servicio,bloque,orden,estado,lat,lon,comentario\n"
                 "Belaunde,1,1,mover,-11.95,-77.06,x\nBelaunde,1,2,otro,,,\n", encoding="utf-8")
    monkeypatch.setattr(G, "CORRECCIONES", f)
    c = G.cargar_correcciones()
    assert list(c) == [("Belaunde", "1", 1)] and c[("Belaunde", "1", 1)]["estado"] == "mover"
    monkeypatch.setattr(G, "CORRECCIONES", tmp_path / "no_existe.csv")
    assert G.cargar_correcciones() == {}


def test_completar_por_calle_elige_el_punto_cercano_al_tramo():
    # calle homonima con dos tramos: uno junto a la ruta y otro a ~5 km
    calle = np.array([[-12.0500, -77.0400], [-12.0501, -77.0401], [-12.1000, -77.0000]])
    res = [(-12.0480, -77.0405), None, (-12.0520, -77.0395)]
    out, met = G.completar_por_calle(["A", "Alcides Vigo", "C"], res, {"alcides vigo": calle})
    assert met[1] == "osm_calle_cercania"
    assert abs(out[1][0] - (-12.0500)) < 0.001
    # sin vecinas resueltas no se inventa nada
    out2, met2 = G.completar_por_calle(["Alcides Vigo"], [None], {"alcides vigo": calle})
    assert out2 == [None] and met2 == [""]


def test_confianza_por_metodo():
    assert G.confianza("revision_humana", 5) == "verificada"
    assert G.confianza("osm_calle_cercania", 1) == "baja"
    assert G.confianza("osm_exacto_unico", 1) == "alta"
    assert G.confianza("osm_exacto_secuencia", 4) == "baja"


def test_coord_de_texto_enlaces_de_google_maps():
    url = ("https://www.google.com/maps/place/METROPOLITANO+estaci%C3%B3n+Estadio+Uni%C3%B3n/"
           "@-12.153076,-77.0199522,20z/data=!4m10!3m6!8m2!3d-12.1529242!4d-77.0196905!15sChx?entry=ttu")
    assert G.coord_de_texto(url) == (-12.1529242, -77.0196905)          # lugar (!3d!4d), no la vista
    assert G.coord_de_texto("https://www.google.com/maps?q=-12.05,-77.04") == (-12.05, -77.04)
    assert G.coord_de_texto("https://x/@-12.1,-77.0,17z") == (-12.1, -77.0)
    assert G.coord_de_texto("https://maps.app.goo.gl/abc123") is None   # corto: no se resuelve
    assert G.coord_de_texto("") is None


def test_correccion_con_enlace_en_comentario(tmp_path, monkeypatch):
    f = tmp_path / "c.csv"
    f.write_text('servicio,bloque,orden,estado,lat,lon,comentario,grupo\n'
                 'Norte/Belaunde,1,1,ok,,,"https://www.google.com/maps/place/X/@-12.2,-77.1,17z/data=!3d-12.15!4d-77.02",prioritaria\n',
                 encoding="utf-8")
    monkeypatch.setattr(G, "CORRECCIONES", f)
    c = G.cargar_correcciones()[("Norte/Belaunde", "1", 1)]
    assert c["estado"] == "mover" and (float(c["lat"]), float(c["lon"])) == (-12.15, -77.02)
