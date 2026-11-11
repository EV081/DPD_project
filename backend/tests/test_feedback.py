import pytest


pytestmark = pytest.mark.bd


@pytest.fixture(scope="module")
def auth():
    from app import app
    app.config["TESTING"] = True
    c = app.test_client()
    c.post("/api/auth/register", json={"name": "Fb", "email": "fb@test.com", "password": "123456"})
    token = c.post("/api/auth/login", json={"email": "fb@test.com", "password": "123456"}).get_json()["access_token"]
    return c, {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin(monkeypatch_module=None):
    import os
    from app import app
    from services import usuarios
    os.environ.update(SEED_ADMIN_EMAIL="fbadmin@test.com", SEED_ADMIN_PASSWORD="clave-admin-1")
    with app.app_context():
        usuarios.sembrar_admin()
    c = app.test_client()
    token = c.post("/api/auth/login", json={"email": "fbadmin@test.com", "password": "clave-admin-1"}).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


BASE = {"station_id": "Naranjal", "sistema": "troncal", "espera_real_min": 5.0,
        "eta_mostrado_min": 4.0, "aforo_mostrado": "De_pie", "modo_datos": "historico"}


def test_requiere_sesion(auth):
    c, _ = auth
    assert c.post("/api/feedback", json=BASE).status_code == 401


def test_guarda_y_resume(auth, admin):
    c, h = auth
    r = c.post("/api/feedback", json={**BASE, "aforo_percibido": "De_pie"}, headers=h)
    assert r.status_code == 201
    r = c.post("/api/feedback", json={**BASE, "espera_real_min": 8.0, "aforo_percibido": "Saturado"}, headers=h)
    assert r.status_code == 201
    assert c.get("/api/feedback/resumen", headers=h).status_code == 403      # el resumen global es solo de administradores
    res = c.get("/api/feedback/resumen", headers=admin).get_json()
    assert res["n"] == 2 and res["eta"]["mae_min"] == 2.5 and res["eta"]["sesgo_min"] == 2.5
    assert res["aforo"]["acierto"] == 0.5
    assert res["por_modo_datos"]["historico"]["n"] == 2 and res["por_modo_datos"]["en_vivo"]["n"] == 0


@pytest.mark.parametrize("cambio", [{"espera_real_min": -1}, {"espera_real_min": 9999},
                                    {"espera_real_min": None}, {"aforo_percibido": "Lleno"}, {"station_id": ""}])
def test_valida_entrada(auth, cambio):
    c, h = auth
    assert c.post("/api/feedback", json={**BASE, **cambio}, headers=h).status_code == 400
