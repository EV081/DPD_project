"""Alias y zona de búsqueda de destinos (sin red ni Flask)."""
from services import lugares


def test_utec_se_resuelve_por_sigla_y_por_nombre():
    for q in ["UTEC", "utec", "Utec Barranco", "universidad de ingeniería y tecnología", "UTE"]:
        r = lugares.buscar_alias(q)
        assert r and "Barranco" in r[0]["display_name"], q


def test_texto_corto_o_ajeno_no_da_alias():
    assert lugares.buscar_alias("ut") == []
    assert lugares.buscar_alias("Miraflores") == []


def test_coordenadas_de_utec_estan_en_barranco_y_dentro_de_lima():
    r = lugares.buscar_alias("utec")[0]
    oeste, norte, este, sur = lugares.VIEWBOX_LIMA
    assert oeste < r["lon"] < este and sur < r["lat"] < norte


def test_normalizar_quita_tildes_y_signos():
    assert lugares.normalizar("  Ingeniería, y  Tecnología ") == "ingenieria y tecnologia"


def test_viewbox_tiene_formato_lon_lat_lon_lat():
    oeste, norte, este, sur = (float(x) for x in lugares.viewbox_param().split(","))
    assert oeste < este and sur < norte


def test_kennedy_sale_el_de_miraflores_y_no_solo_el_de_pueblo_libre():
    for q in ["Kennedy", "parque kennedy", "John F. Kennedy Park"]:
        r = lugares.buscar_alias(q)
        assert r and "Miraflores" in r[0]["display_name"], q


def test_los_favoritos_estan_dentro_de_lima_y_sin_claves_repetidas_entre_lugares():
    oeste, norte, este, sur = lugares.VIEWBOX_LIMA
    vistas = {}
    assert len(lugares.LUGARES) >= 60
    for l in lugares.LUGARES:
        assert oeste < l["lon"] < este and sur < l["lat"] < norte, l["display_name"]
        for c in l["claves"]:
            assert vistas.setdefault(c, l["display_name"]) == l["display_name"], f"clave repetida: {c}"


def test_exactos_primero_y_tope_de_favoritos():
    r = lugares.buscar_alias("uni")
    assert "Universidad Nacional de Ingeniería" in r[0]["display_name"]
    assert len(lugares.buscar_alias("par")) <= lugares.MAX_FAVORITOS


def test_lugares_conocidos_de_distintos_distritos():
    casos = {"larcomar": "Miraflores", "jockey plaza": "Santiago de Surco", "aeropuerto": "Callao",
             "plaza de armas": "Cercado de Lima", "gamarra": "La Victoria", "pucp": "San Miguel"}
    for q, distrito in casos.items():
        r = lugares.buscar_alias(q)
        assert r and distrito in r[0]["display_name"], q
