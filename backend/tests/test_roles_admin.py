"""Roles: administrador sembrado desde el .env, permisos del panel operacional y registro público sin escalada."""
import pytest

pytestmark = pytest.mark.bd

ADMIN = {"SEED_ADMIN_EMAIL": "Admin@Test.com", "SEED_ADMIN_PASSWORD": "clave-segura-1", "SEED_ADMIN_NAME": "Admin Prueba"}


@pytest.fixture(scope="module")
def app_():
    from app import app
    app.config["TESTING"] = True
    return app


@pytest.fixture(autouse=True)
def _entorno(monkeypatch):
    for k, v in ADMIN.items():
        monkeypatch.setenv(k, v)


def _login(c, email, password):
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    return r, {"Authorization": f"Bearer {r.get_json().get('access_token', '')}"}


@pytest.fixture(scope="module")
def sesiones(app_):
    import os
    from services import usuarios
    for k, v in ADMIN.items():
        os.environ[k] = v
    with app_.app_context():
        usuarios.sembrar_admin()
    c = app_.test_client()
    c.post("/api/auth/register", json={"name": "Normal", "email": "normal@test.com", "password": "123456"})
    _, h_admin = _login(c, "admin@test.com", ADMIN["SEED_ADMIN_PASSWORD"])
    _, h_user = _login(c, "normal@test.com", "123456")
    return c, h_admin, h_user


def test_seed_crea_admin_con_correo_normalizado(app_, sesiones):
    c, h_admin, _ = sesiones
    me = c.get("/api/auth/me", headers=h_admin).get_json()
    assert me["role"] == "admin" and me["email"] == "admin@test.com" and me["name"] == "Admin Prueba"


def test_seed_es_idempotente_y_el_env_manda(app_, sesiones, monkeypatch):
    from services import usuarios
    from routes.auth import User
    with app_.app_context():
        assert usuarios.sembrar_admin()["estado"] == "sin_cambios"
        antes = User.query.count()
        monkeypatch.setenv("SEED_ADMIN_PASSWORD", "otra-clave-nueva-2")
        assert usuarios.sembrar_admin()["estado"] == "actualizado"
        assert User.query.count() == antes
    c = app_.test_client()
    assert _login(c, "admin@test.com", "otra-clave-nueva-2")[0].status_code == 200
    assert _login(c, "admin@test.com", ADMIN["SEED_ADMIN_PASSWORD"])[0].status_code == 401
    with app_.app_context():
        monkeypatch.setenv("SEED_ADMIN_PASSWORD", ADMIN["SEED_ADMIN_PASSWORD"])
        usuarios.sembrar_admin()


def test_seed_promueve_cuenta_existente(app_, sesiones):
    from services import usuarios
    from routes.auth import User
    from db.connection import db
    import os
    c, _, _ = sesiones
    c.post("/api/auth/register", json={"name": "Otro", "email": "otro@test.com", "password": "123456"})
    os.environ["SEED_ADMIN_EMAIL"] = "otro@test.com"
    try:
        with app_.app_context():
            assert usuarios.sembrar_admin()["estado"] == "actualizado"
            assert User.query.filter_by(email="otro@test.com").one().role == "admin"
            User.query.filter_by(email="otro@test.com").delete()
            db.session.commit()
    finally:
        os.environ["SEED_ADMIN_EMAIL"] = ADMIN["SEED_ADMIN_EMAIL"]


def test_seed_sin_variables_se_omite(app_, monkeypatch):
    from services import usuarios
    monkeypatch.delenv("SEED_ADMIN_EMAIL")
    monkeypatch.delenv("SEED_ADMIN_PASSWORD")
    with app_.app_context():
        assert usuarios.sembrar_admin()["estado"] == "omitido"


@pytest.mark.parametrize("env", [{"SEED_ADMIN_PASSWORD": "corta"}, {"SEED_ADMIN_PASSWORD": "changeme"},
                                 {"SEED_ADMIN_EMAIL": "no-es-correo"}, {"SEED_ADMIN_EMAIL": ""},
                                 {"SEED_ADMIN_PASSWORD": "é" * 40}])
def test_seed_rechaza_configuracion_invalida(app_, monkeypatch, env):
    from services import usuarios
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with app_.app_context(), pytest.raises(usuarios.SeedError):
        usuarios.sembrar_admin()


def test_arranque_no_falla_con_configuracion_invalida(app_, monkeypatch):
    from services import usuarios
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "corta")
    mensajes = []
    with app_.app_context():
        usuarios.sembrar_al_arrancar(log=mensajes.append)       # no lanza
    assert mensajes and "omitido" in mensajes[0]


def test_registro_publico_nunca_crea_admin(app_, sesiones):
    c, _, _ = sesiones
    r = c.post("/api/auth/register", json={"name": "Listo", "email": "listo@test.com", "password": "123456", "role": "admin"})
    assert r.status_code == 201 and r.get_json()["user"]["role"] == "user"
    c.put("/api/auth/me", json={"name": "Listo", "role": "admin"}, headers=_login(c, "listo@test.com", "123456")[1])
    assert c.get("/api/auth/me", headers=_login(c, "listo@test.com", "123456")[1]).get_json()["role"] == "user"


def test_login_devuelve_rol(app_, sesiones):
    c, _, _ = sesiones
    assert _login(c, "normal@test.com", "123456")[0].get_json()["user"]["role"] == "user"


RUTAS_ADMIN = ["/api/admin/dashboard", "/api/feedback/resumen"]


@pytest.mark.parametrize("ruta", RUTAS_ADMIN)
def test_admin_exige_sesion_y_rol(sesiones, ruta):
    c, h_admin, h_user = sesiones
    assert c.get(ruta).status_code == 401
    assert c.get(ruta, headers=h_user).status_code == 403
    assert c.get(ruta, headers=h_admin).status_code == 200


def test_dashboard_forma_y_privacidad(sesiones):
    c, h_admin, _ = sesiones
    d = c.get("/api/admin/dashboard", headers=h_admin).get_json()
    assert set(d) >= {"generado_en", "salud", "modelos", "pipelines", "monitoreo", "uso", "feedback", "eje2"}
    assert d["salud"]["api"] == "ok" and d["salud"]["base_datos"]["ok"] is True
    assert len(d["uso"]["abordajes_por_dia"]) == 14 and len(d["uso"]["abordajes_por_hora"]) == 24
    assert d["uso"]["usuarios_total"] >= 2
    assert set(d["eje2"]["por_tipo"]) == {"acoso", "seguimiento", "robo"}
    assert {s["sistema"] for s in d["modelos"]["sistemas"]} == {"metro_l1", "troncal", "corredor", "alimentador"}
    texto = c.get("/api/admin/dashboard", headers=h_admin).get_data(as_text=True)
    for clave in ("lat", "lon", "user_id", "seg_id", "password_hash", "email"):
        assert f'"{clave}"' not in texto                         # sin coordenadas, calles, autores ni correos
    assert "admin@test.com" not in texto and "normal@test.com" not in texto


def test_rol_se_lee_de_la_base_en_cada_peticion(app_, sesiones):
    """Degradar a un admin le quita el acceso aunque conserve un token vigente."""
    from routes.auth import User
    from db.connection import db
    c, _, _ = sesiones
    c.post("/api/auth/register", json={"name": "Temp", "email": "temp@test.com", "password": "123456"})
    with app_.app_context():
        User.query.filter_by(email="temp@test.com").update({"role": "admin"})
        db.session.commit()
    h = _login(c, "temp@test.com", "123456")[1]
    assert c.get("/api/admin/dashboard", headers=h).status_code == 200
    with app_.app_context():
        User.query.filter_by(email="temp@test.com").update({"role": "user"})
        db.session.commit()
    assert c.get("/api/admin/dashboard", headers=h).status_code == 403


def test_migra_columna_role_en_bases_antiguas(tmp_path):
    """Una base anterior a los roles (sin users.role) se actualiza sin perder cuentas. Usa un motor aparte."""
    from sqlalchemy import create_engine, inspect, text
    from services import usuarios
    engine = create_engine(f"sqlite:///{tmp_path / 'antigua_test.db'}")
    with engine.begin() as con:
        con.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100), email VARCHAR(150), password_hash VARCHAR(255))"))
        con.execute(text("INSERT INTO users (name, email, password_hash) VALUES ('Vieja', 'vieja@test.com', 'x')"))
    assert usuarios.asegurar_columna_role(engine) is True
    assert usuarios.asegurar_columna_role(engine) is False
    assert "role" in {c["name"] for c in inspect(engine).get_columns("users")}
    with engine.connect() as con:
        assert con.execute(text("SELECT role FROM users WHERE email='vieja@test.com'")).scalar() == "user"
    engine.dispose()


def test_token_con_otra_clave_responde_401_no_422(sesiones):
    """Tras cambiar JWT_SECRET_KEY, un token viejo debe cerrar la sesión (401) y no parecer un error del servidor."""
    c, _, _ = sesiones
    ajeno = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjo5OTk5OTk5OTk5fQ."
             "firma-que-no-corresponde-a-esta-clave-0000000000000")
    r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {ajeno}"})
    assert r.status_code == 401
