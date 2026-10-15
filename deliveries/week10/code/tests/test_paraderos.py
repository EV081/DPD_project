"""Carga de paraderos/rutas y consulta de cercanos, con GeoJSON sintéticos (sin datos reales)."""
from __future__ import annotations

import json

import pytest

from pipeline import ingest_paraderos as IP


def _pts(nombre, feats):
    return {"type": "FeatureCollection", "name": nombre, "features": feats}


def _pt(lon, lat, **props):
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "Point", "coordinates": [lon, lat]}}


def _ln(coords, **props):
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "LineString", "coordinates": coords}}


@pytest.fixture()
def geo(tmp_path):
    d = tmp_path / "geo"
    d.mkdir()
    w = lambda n, f: (d / f"{n}.geojson").write_text(json.dumps(_pts(n, f)), encoding="utf-8")  # noqa: E731
    w("puntos_metro_l1", [_pt(-77.0, -12.0, estacion="Bayóvar", unidad="Bayóvar")])
    w("puntos_troncal", [_pt(-77.03, -12.05, estacion="Quilca", unidad="Quilca", match="osm")])
    w("puntos_corredores", [
        # mismo paradero fisico repetido por ruta/sentido (a ~4 m): debe fusionarse
        _pt(-77.0400, -12.0600, cod_paradero="3QUI", paradero="QUILCA ", ruta="301", n_paradero=1, unidad="3QUI"),
        _pt(-77.04004, -12.0600, cod_paradero="3QUI2", paradero="Quilca", ruta="302", n_paradero=4, unidad="3QUI2"),
        _pt(-77.0600, -12.0600, cod_paradero="3LEJ", paradero="LEJOS", ruta="301", n_paradero=9, unidad="3LEJ"),
    ])
    w("paradas_alimentadores", [
        _pt(-77.1, -12.1, grupo="AlimentadoresNorte", servicio="Norte/LosAlisos", codigo="AN-15", bloque=1,
            orden=3, paradero="Las Palmeras", metodo="osm_exacto_unico", confianza="alta")])
    w("puntos_metropolitano_servicios", [
        _pt(-77.03, -12.05, servicio_slug="EX11-NS", servicio_nombre="Expreso 11", estacion="Quilca", orden=2)])
    w("trazados_corredores", [_ln([[-77.04, -12.06], [-77.06, -12.06]], ruta="301", color_hex="#00f"),
                              _ln([[-77.06, -12.06], [-77.04, -12.06]], ruta="301")])
    w("trazado_troncal", [_ln([[-77.03, -12.05], [-77.02, -12.04]], sistema="troncal")])
    return d


UNIDADES = {"corredor": {"301": "301"}, "alimentador": {"alisos": "Alisos"}, "metro_l1": {}, "troncal": {}}


def test_norm_quita_acentos_y_espacios():
    assert IP.norm("  Bayóvar ") == IP.norm("BAYOVAR") == "bayovar"


def test_fusiona_paradero_duplicado_y_une_rutas(geo):
    d = IP.construir(geo, UNIDADES)
    quilca = [p for p in d["paraderos"].values() if p["sistema"] == "corredor" and IP.norm(p["nombre"]) == "quilca"]
    assert len(quilca) == 1 and quilca[0]["nombre"] == "QUILCA"
    rutas = {rk[1] for (pk, rk, _d) in d["enlaces"] if d["paraderos"][pk]["nombre"] == "QUILCA"}
    assert rutas == {"301", "302"}


def test_unidad_modelo_y_calidad(geo):
    d = IP.construir(geo, UNIDADES)
    ali = next(e for (pk, rk, _d), e in d["enlaces"].items() if pk[0] == "alimentador")
    assert ali["unidad_modelo"] == "Alisos"  # "LosAlisos" (portal) -> unidad "Alisos"
    cor = {rk[1]: e["unidad_modelo"] for (pk, rk, _d), e in d["enlaces"].items() if pk[0] == "corredor"}
    assert cor["301"] == "301" and cor["302"] is None  # 302 no tiene demanda en el modelo
    cal = {p["sistema"]: p["calidad_coord"] for p in d["paraderos"].values()}
    assert cal == {"metro_l1": "shapefile", "troncal": "osm_nombre",
                   "corredor": "gps_atu", "alimentador": "osm_secuencia"}
    ali_p = next(p for p in d["paraderos"].values() if p["sistema"] == "alimentador")
    assert ali_p["confianza"] == "alta"


def test_trazado_multilinea_y_servicio_enlazado(geo):
    d = IP.construir(geo, UNIDADES)
    assert d["rutas"][("corredor", "301")]["trazado"]["type"] == "MultiLineString"
    assert d["rutas"][("corredor", "302")]["trazado"] is None
    assert ("troncal", "EX11-NS") in d["rutas"]
    assert d["avisos"]["servicio_sin_estacion"] == 0


def test_cercanos_orden_radio_y_rutas(db, geo):
    IP.cargar(db, geo)
    filas = db.execute("SELECT * FROM paraderos_cercanos(%s, %s, 500, 10)", (-12.0600, -77.0400)).fetchall()
    assert [f["nombre"] for f in filas] == ["QUILCA"]  # LEJOS (~2 km) queda fuera
    assert filas[0]["distancia_m"] < 5
    assert {r["codigo"] for r in filas[0]["rutas"]} == {"301", "302"}
    assert filas[0]["calidad_coord"] == "gps_atu"

    todas = db.execute("SELECT nombre FROM paraderos_cercanos(%s, %s, 5000, 3)", (-12.0600, -77.0400)).fetchall()
    assert len(todas) == 3  # respeta el limite


def test_carga_idempotente(db, geo):
    a = IP.cargar(db, geo)
    b = IP.cargar(db, geo)
    assert a == b
    assert db.execute("SELECT count(*) AS n FROM paradero").fetchone()["n"] == a["paraderos"]


def test_ningun_enlace_queda_sin_orden(geo):
    d = IP.construir(geo, UNIDADES)
    assert d["avisos"]["enlaces_sin_orden"] == 0
    assert all(e["orden"] is not None for e in d["enlaces"].values())


def test_corredor_sin_secuencia_usa_n_paradero_del_catalogo(geo):
    d = IP.construir(geo, UNIDADES)
    cor = {(rk[1], d["paraderos"][pk]["nombre"]): e for (pk, rk, dire), e in d["enlaces"].items()
           if pk[0] == "corredor"}
    # ruta 301: n_paradero 1 (QUILCA) y 9 (LEJOS) -> ranking 1 y 2 dentro de la ruta
    assert cor[("301", "QUILCA")]["orden"] == 1 and cor[("301", "LEJOS")]["orden"] == 2
    assert {e["orden_origen"] for e in cor.values()} == {"catalogo_n_paradero"}
    # el resto conserva la secuencia publicada; la troncal se ordena geograficamente
    otros = {pk[0]: e["orden_origen"] for (pk, _rk, _d), e in d["enlaces"].items() if pk[0] != "corredor"}
    assert otros == {"metro_l1": "atu_secuencia", "troncal": "latitud_troncal",
                     "alimentador": "atu_secuencia"}


def test_paradero_fuera_de_la_secuencia_atu_queda_en_direccion_0_con_orden_de_catalogo(tmp_path):
    g = tmp_path / "geo"
    g.mkdir()
    w = lambda n, f: (g / f"{n}.geojson").write_text(json.dumps(_pts(n, f)), encoding="utf-8")  # noqa: E731
    w("puntos_corredores", [
        _pt(-77.00, -12.00, cod_paradero="A", paradero="UNO", ruta="201", n_paradero=10),
        _pt(-77.01, -12.00, cod_paradero="B", paradero="DOS", ruta="201", n_paradero=11),
        _pt(-77.02, -12.00, cod_paradero="C", paradero="TRES", ruta="201", n_paradero=12),  # no esta en ATU
    ])
    w("paradas_corredores", [
        _pt(-77.00, -12.00, ruta="201", direccion=1, orden=1, paradero="UNO"),
        _pt(-77.01, -12.00, ruta="201", direccion=1, orden=2, paradero="DOS"),
    ])
    d = IP.construir(g, {"corredor": {}})
    por_nombre = {d["paraderos"][pk]["nombre"]: (dire, e["orden"], e["orden_origen"])
                  for (pk, _rk, dire), e in d["enlaces"].items()}
    assert por_nombre["UNO"] == (1, 1, "atu_secuencia")
    assert por_nombre["DOS"] == (1, 2, "atu_secuencia")
    assert por_nombre["TRES"] == (0, 3, "catalogo_n_paradero")  # rank de n_paradero 12 entre 10, 11, 12


def test_troncal_se_ordena_de_sur_a_norte_no_alfabeticamente(tmp_path):
    g = tmp_path / "geo"
    g.mkdir()
    w = lambda n, f: (g / f"{n}.geojson").write_text(json.dumps(_pts(n, f)), encoding="utf-8")  # noqa: E731
    w("puntos_troncal", [  # orden alfabetico en el archivo, latitudes N -> S distintas
        _pt(-77.03, -12.00, estacion="Aaa Norte", unidad="Aaa Norte"),
        _pt(-77.03, -12.10, estacion="Zzz Sur", unidad="Zzz Sur"),
        _pt(-77.03, -12.05, estacion="Mmm Centro", unidad="Mmm Centro"),
    ])
    d = IP.construir(g, {"troncal": {}})
    orden = {d["paraderos"][pk]["nombre"]: (e["orden"], e["orden_origen"]) for (pk, _rk, _d), e in d["enlaces"].items()}
    assert orden == {"Zzz Sur": (1, "latitud_troncal"), "Mmm Centro": (2, "latitud_troncal"),
                     "Aaa Norte": (3, "latitud_troncal")}


def test_tramos_sentido_vacio_es_cero_y_acepta_ambos_encabezados():
    assert IP._direccion_tramo({"direccion": "2"}) == 2          # geo/tramos_osrm.csv
    assert IP._direccion_tramo({"sentido": "1"}) == 1            # export/tramos.csv
    assert IP._direccion_tramo({"sentido": ""}) == 0             # sin sentido (como paraderos.csv)
    assert IP._direccion_tramo({"direccion": "0"}) == 0
