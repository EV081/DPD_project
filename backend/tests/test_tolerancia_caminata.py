"""Límite de minutos adicionales usando el grafo controlado que ya existe en las pruebas."""
import pytest

from eje2_sintetico import NODOS, crear_grafo
from services import eje2_service as E

ORIGEN = {"lat": NODOS[1][1], "lon": NODOS[1][0]}
DESTINO = {"acceso_id": "metro_l1_0000"}


@pytest.fixture
def grafo(tmp_path):
    return E.GrafoEje2(crear_grafo(tmp_path))


def consultar(grafo, **kwargs):
    return E.rutas(ORIGEN, DESTINO, franja="noche", g=grafo, **kwargs)


def test_sin_limite_conserva_la_respuesta_anterior(grafo):
    sin_campo = consultar(grafo)
    nulo = consultar(grafo, max_minutos_extra=None)
    assert sin_campo == nulo
    assert "tolerancia_caminata" not in sin_campo
    assert sin_campo["seleccionada"] == sin_campo["recomendada"] == "segura"


def test_cero_minutos_selecciona_normal_sin_borrar_alternativa(grafo):
    original = consultar(grafo)
    limitado = consultar(grafo, max_minutos_extra=0)
    assert limitado["seleccionada"] == limitado["recomendada"] == "normal"
    assert limitado["rutas"] == original["rutas"]
    assert limitado["comparacion"] == original["comparacion"]
    assert limitado["tolerancia_caminata"]["cumple_segura"] is False
    assert "supera tu límite" in limitado["explicacion"]["resumen"]


def test_limite_exacto_usa_distancia_y_velocidad_existentes(grafo):
    # La ruta normal mide 250 m y la alternativa 310 m; el manifiesto indica 80 m/min.
    exacto = 60 / grafo.manifest["velocidad_caminata_m_min"]
    permitido = consultar(grafo, max_minutos_extra=exacto)
    no_permitido = consultar(grafo, max_minutos_extra=exacto - 0.001)
    assert permitido["tolerancia_caminata"]["minutos_extra_segura"] == exacto
    assert permitido["tolerancia_caminata"]["cumple_segura"] is True
    assert permitido["seleccionada"] == "segura"
    assert no_permitido["seleccionada"] == "normal"


def test_limite_explicito_reemplaza_tope_predeterminado(tmp_path):
    grafo = E.GrafoEje2(crear_grafo(tmp_path, largo_b=400.0))
    predeterminado = consultar(grafo)
    aceptado = consultar(grafo, max_minutos_extra=7.5)
    assert predeterminado["recomendada"] == "normal"
    assert aceptado["recomendada"] == "segura"
    assert aceptado["rutas"] == predeterminado["rutas"]
    assert aceptado["tolerancia_caminata"]["minutos_extra_segura"] == 7.5


def test_preferencia_normal_se_respeta_aunque_segura_cumpla(grafo):
    resultado = consultar(grafo, preferencia="normal", max_minutos_extra=1)
    assert resultado["seleccionada"] == "normal"
    assert resultado["recomendada"] == "segura"


def test_cumplir_limite_no_elimina_umbral_de_mejora(tmp_path):
    grafo = E.GrafoEje2(crear_grafo(tmp_path, largo_b=102.5, riesgo_a=0.30, riesgo_b=0.29))
    resultado = consultar(grafo, max_minutos_extra=10)
    assert resultado["tolerancia_caminata"]["cumple_segura"] is True
    assert resultado["comparacion"]["reduccion_riesgo_pct"] < 0.10
    assert resultado["recomendada"] == "normal"


def test_rutas_iguales_cumplen_limite_cero(grafo):
    resultado = consultar(grafo, lam=0, max_minutos_extra=0)
    assert resultado["recomendada"] == "misma" and resultado["seleccionada"] == "normal"
    assert resultado["tolerancia_caminata"]["cumple_segura"] is True
    assert resultado["tolerancia_caminata"]["minutos_extra_segura"] == 0


def test_explicacion_declara_comparacion_de_dos_candidatas(grafo):
    resultado = consultar(grafo, max_minutos_extra=1)
    tolerancia = resultado["tolerancia_caminata"]
    assert tolerancia["metodo"] == "comparacion_de_dos_rutas"
    assert "No se buscan todas las rutas" in tolerancia["aviso"]
    assert resultado["explicacion"]["condiciones"]["max_minutos_extra"] == 1
    assert "1 min" in resultado["explicacion"]["condiciones"]["recomendacion_si"]


@pytest.mark.parametrize("valor", [-1, float("nan"), float("inf"), True, [], {}, "ayer"])
def test_servicio_rechaza_limites_invalidos(grafo, valor):
    with pytest.raises(E.Eje2Error, match="max_minutos_extra"):
        consultar(grafo, max_minutos_extra=valor)


@pytest.mark.bd
class TestApiTolerancia:
    @pytest.fixture
    def client(self, monkeypatch, grafo):
        from app import app
        from services import eje2_reportes as R
        app.config["TESTING"] = True
        monkeypatch.setattr(E, "grafo", lambda: grafo)
        monkeypatch.setattr(R.ajustes, "obtener", lambda _grafo: None)
        return app.test_client()

    def test_endpoint_transmite_limite_y_mantiene_compatibilidad(self, client):
        body = {"origen": ORIGEN, "destino": DESTINO, "franja": "noche"}
        normal = client.post("/api/eje2/ruta", json=body)
        nulo = client.post("/api/eje2/ruta", json={**body, "max_minutos_extra": None})
        limitado = client.post("/api/eje2/ruta", json={**body, "max_minutos_extra": 0})
        assert normal.status_code == nulo.status_code == limitado.status_code == 200
        assert normal.get_json() == nulo.get_json()
        data = limitado.get_json()
        assert data["seleccionada"] == "normal"
        assert data["tolerancia_caminata"]["cumple_segura"] is False
        assert data["tolerancia_caminata"]["max_minutos_extra"] == 0

    @pytest.mark.parametrize("valor", [-1, "nan", "inf", True, [], {}, "ayer"])
    def test_endpoint_devuelve_400_para_limite_invalido(self, client, valor):
        response = client.post("/api/eje2/ruta", json={"origen": ORIGEN, "destino": DESTINO, "max_minutos_extra": valor})
        assert response.status_code == 400
        assert "max_minutos_extra" in response.get_json()["error"]
