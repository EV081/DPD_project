"""Casos que impedían continuar la demo: perfil, entradas inválidas y servicios opcionales."""
import uuid

import pytest

pytestmark = pytest.mark.bd


@pytest.fixture(scope="module")
def client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def account(client):
    email = f"qa-{uuid.uuid4().hex}@example.test"
    assert client.post("/api/auth/register", json={"name": "Prueba", "email": email, "password": "prueba123"}).status_code == 201
    response = client.post("/api/auth/login", json={"email": email, "password": "prueba123"}).get_json()
    return email, {"Authorization": "Bearer " + response["access_token"]}, response["user"]["id"]


@pytest.mark.parametrize("body", [None, [], [1], "texto", 7, True])
@pytest.mark.parametrize("url", ["/api/auth/register", "/api/auth/login", "/api/eje2/ruta"])
def test_json_debe_ser_objeto(client, body, url):
    import json
    response = client.post(url, data=json.dumps(body), content_type="application/json")
    assert response.status_code == 400 and response.get_json()["error"]


@pytest.mark.parametrize("change", [{"name": []}, {"email": 123}, {"password": {}}, {"password": "á" * 40}])
def test_registro_valida_tipos_y_limite_bcrypt(client, change):
    response = client.post("/api/auth/register", json={"name": "Prueba", "email": "qa@example.test", "password": "prueba123", **change})
    assert response.status_code == 400


def test_actualizar_correo_no_impide_volver_a_entrar(client, account):
    _, headers, _ = account
    email = f"NUEVO-{uuid.uuid4().hex}@EXAMPLE.TEST"
    response = client.put("/api/auth/me", json={"email": f"  {email}  "}, headers=headers)
    assert response.status_code == 200 and response.get_json()["user"]["email"] == email.lower()
    assert client.post("/api/auth/login", json={"email": email.lower(), "password": "prueba123"}).status_code == 200


def test_perfil_no_duplica_correo_cambiando_mayusculas(client, account):
    email, _, _ = account
    other = f"otra-{uuid.uuid4().hex}@example.test"
    client.post("/api/auth/register", json={"name": "Otra", "email": other, "password": "prueba123"})
    token = client.post("/api/auth/login", json={"email": other, "password": "prueba123"}).get_json()["access_token"]
    assert client.put("/api/auth/me", json={"email": email.upper()}, headers={"Authorization": "Bearer " + token}).status_code == 409


@pytest.mark.parametrize("field,value", [("eta_mostrado_min", "nan"), ("eta_base_min", "inf"), ("factor_trafico", -1), ("station_id", "no-existe"), ("sistema", "inventado")])
def test_feedback_no_contamina_metricas(client, account, field, value):
    _, headers, _ = account
    data = {"station_id": "Naranjal", "sistema": "troncal", "espera_real_min": 5, field: value}
    assert client.post("/api/feedback", json=data, headers=headers).status_code == 400


def test_borrar_cuenta_desvincula_feedback_y_rechaza_token(client, account):
    from app import app
    from db.connection import db
    from routes.feedback import FeedbackViaje
    _, headers, _ = account
    response = client.post("/api/feedback", json={"station_id": "Naranjal", "sistema": "troncal", "espera_real_min": 5}, headers=headers)
    assert response.status_code == 201
    feedback_id = response.get_json()["id"]
    assert client.delete("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/feedback", json={}, headers=headers).status_code == 401
    with app.app_context():
        assert db.session.get(FeedbackViaje, feedback_id).user_id is None


@pytest.mark.parametrize("url", [
    "/api/eje2/accesos/cercanos?lat=nan&lon=-77",
    "/api/eje2/accesos/cercanos?lat=-12&lon=-77&limit=1.5",
    "/api/geo/match-trip?origin_lat=inf&origin_lon=-77&dest_lat=-12&dest_lon=-77",
    "/api/geo/match-trip?origin_lat=-12&origin_lon=-77&dest_lat=-12&dest_lon=-77&radius=nan",
    "/api/geo/caminata?lat1=nan&lon1=-77&lat2=-12&lon2=-77",
    "/api/stations/nearby?latitude=-12&longitude=-77&radius=inf",
    "/api/predictions/metro_l1/Gamarra?hour=abc",
    "/api/predictions/metro_l1/Gamarra/forecast?hours=abc",
])
def test_consultas_invalidas_responden_400(client, url):
    assert client.get(url).status_code == 400


@pytest.mark.parametrize("change", [{"lambda": "no"}, {"origen": {"lat": "nan", "lon": -77}}, {"destino": {"lat": [], "lon": -77}}, {"franja": {}}])
def test_ruta_valida_coordenadas_y_parametros(client, change):
    data = {"origen": {"lat": -12.05, "lon": -77.03}, "destino": {"acceso_id": "metro_l1_0000"}, **change}
    assert client.post("/api/eje2/ruta", json=data).status_code == 400


def test_autocomplete_local_no_necesita_token_ni_red(client, monkeypatch):
    from routes import geo
    monkeypatch.setenv("LOCATIONIQ_TOKEN", "")
    def no_network(*args, **kwargs):
        raise AssertionError("No debe llamar a la red sin token")
    monkeypatch.setattr(geo.urllib.request, "urlopen", no_network)
    response = client.get("/api/geo/autocomplete?q=UTEC")
    assert response.status_code == 200 and response.get_json()
    assert client.get("/api/geo/autocomplete?q=sin-coincidencias").get_json() == []


def test_autocomplete_timeout_tiene_respuesta_controlada(client, monkeypatch):
    from routes import geo
    monkeypatch.setenv("LOCATIONIQ_TOKEN", "clave-de-prueba")
    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == geo.GEOCODING_TIMEOUT_S
        raise TimeoutError()
    monkeypatch.setattr(geo.urllib.request, "urlopen", timeout)
    response = client.get("/api/geo/autocomplete?q=lugar-no-catalogado-qa")
    assert response.status_code == 502 and "clave-de-prueba" not in response.get_data(as_text=True)


def test_jwt_vacio_local_genera_clave_estable(tmp_path, monkeypatch):
    from settings import jwt_secret
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    monkeypatch.setenv("DATABASE_URL", "")
    first = jwt_secret(tmp_path)
    assert len(first) >= 64 and jwt_secret(tmp_path) == first
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/ejemplo")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        jwt_secret(tmp_path)
