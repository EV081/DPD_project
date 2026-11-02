"""Particionado mensual de Postgres: lógica pura (DDL) y comportamiento real contra el Postgres de pruebas."""
import datetime as dt

import pytest
from sqlalchemy import text

from db import particiones as P
from db import tablas as T

HOY = dt.datetime.now(dt.timezone.utc).date()


# --------------------------------------------------------------------------- puras (sin base)
def test_sumar_meses_cruza_anios():
    assert P.sumar_meses(2026, 12, 1) == (2027, 1)
    assert P.sumar_meses(2026, 1, -1) == (2025, 12)
    assert P.sumar_meses(2026, 11, 14) == (2028, 1)


def test_meses_entre_incluye_ambos_extremos():
    assert P.meses_entre((2026, 11), (2027, 2)) == [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]
    assert P.meses_entre((2026, 5), (2026, 5)) == [(2026, 5)]


def test_rango_y_nombre_de_particion():
    assert P.rango_mes(2026, 12) == ("2026-12-01", "2027-01-01")
    assert P.nombre_particion("reporte_seguridad", 2026, 3) == "reporte_seguridad_2026_03"
    assert P.mes_de_particion("reporte_seguridad", "reporte_seguridad_2026_03") == (2026, 3)
    assert P.mes_de_particion("reporte_seguridad", "reporte_seguridad_default") is None
    assert P.mes_de_particion("validacion_hora", "reporte_seguridad_2026_03") is None


def test_ddl_de_particion_y_default():
    ddl = P.ddl_particion("validacion_hora", 2026, 12)
    assert "PARTITION OF validacion_hora" in ddl and "FROM ('2026-12-01') TO ('2027-01-01')" in ddl and "IF NOT EXISTS" in ddl
    assert P.ddl_particion_default("validacion_hora").endswith("PARTITION OF validacion_hora DEFAULT")


def test_ddl_de_tabla_padre_usa_el_esquema_del_modelo():
    sentencias = P.ddl_tabla_particionada(T.ReporteSeguridad.__table__, "creado_en")
    assert sentencias[0].startswith("CREATE TABLE IF NOT EXISTS reporte_seguridad") and sentencias[0].endswith("PARTITION BY RANGE (creado_en)")
    assert "PRIMARY KEY (id, creado_en)" in sentencias[0]                      # la PK incluye la clave de partición
    assert any("ix_reporte_seg_creado" in s for s in sentencias[1:])


def test_las_tablas_particionadas_tienen_la_clave_en_la_pk():
    for tabla, columna in T.PARTICIONADAS.items():
        pk = [c.name for c in db_tabla(tabla).primary_key.columns]
        assert columna in pk, f"{tabla}: la PK debe incluir {columna}"


def db_tabla(nombre):
    return {"reporte_seguridad": T.ReporteSeguridad.__table__, "validacion_hora": T.ValidacionHora.__table__}[nombre]


# --------------------------------------------------------------------------- Postgres real
pytestmark = [pytest.mark.bd, pytest.mark.postgres]


@pytest.fixture(scope="module")
def ctx():
    from app import app
    from db.connection import db
    with app.app_context():
        yield db
        db.session.rollback()


@pytest.fixture(autouse=True)
def _sin_transacciones_abiertas(ctx):
    """El DDL de particiones necesita bloqueos exclusivos: ninguna prueba deja una transacción abierta."""
    yield
    ctx.session.rollback()


def _particion_de(db, tabla, **filtro):
    cond = " AND ".join(f"{k} = :{k}" for k in filtro)
    r = db.session.execute(text(f"SELECT tableoid::regclass::text FROM {tabla} WHERE {cond}"), filtro).scalar()
    db.session.rollback()                      # cierra la transacción: una lectura abierta bloquearía el DDL de las particiones
    return r


def test_las_tablas_quedan_particionadas(ctx):
    r = ctx.session.execute(text(
        "SELECT relname, relkind FROM pg_class WHERE relname IN ('reporte_seguridad', 'validacion_hora') ORDER BY relname")).all()
    ctx.session.rollback()
    assert [(n, k) for n, k in r] == [("reporte_seguridad", "p"), ("validacion_hora", "p")]


def test_particiones_iniciales_y_default(ctx):
    for tabla in T.PARTICIONADAS:
        esperadas = {P.nombre_particion(tabla, *ym) for ym in P.meses_entre(P.sumar_meses(HOY.year, HOY.month, -1),
                                                                             P.sumar_meses(HOY.year, HOY.month, 3))}
        assert set(P.listar_particiones(ctx.engine, tabla)) >= esperadas | {f"{tabla}_default"}


def test_ensure_particiones_es_idempotente_y_crea_lo_que_falta(ctx):
    assert P.ensure_todas(ctx.engine, T.PARTICIONADAS) == {t: [] for t in T.PARTICIONADAS}
    lejos = HOY.replace(day=1) + dt.timedelta(days=200)
    creadas = P.ensure_particiones(ctx.engine, "reporte_seguridad", "creado_en", adelante=2, atras=0, hoy=lejos)
    assert creadas and all(n.startswith("reporte_seguridad_") for n in creadas)
    assert P.ensure_particiones(ctx.engine, "reporte_seguridad", "creado_en", adelante=2, atras=0, hoy=lejos) == []


def test_cada_reporte_cae_en_la_particion_de_su_mes(ctx):
    a, m = P.sumar_meses(HOY.year, HOY.month, 1)
    fechas = {"actual": dt.datetime(HOY.year, HOY.month, 15, 12, tzinfo=dt.timezone.utc),
              "proximo": dt.datetime(a, m, 3, 8, tzinfo=dt.timezone.utc)}
    ids = {}
    for nombre, f in fechas.items():
        ids[nombre] = f"rep-{nombre}-{HOY.isoformat()}"
        ctx.session.add(T.ReporteSeguridad(id=ids[nombre], creado_en=f, tipo="robo", ocurrido_en=f, lat=-12.05, lon=-77.03,
                                           seg_id=f"s_{nombre}", franja="dia"))
    ctx.session.commit()
    assert _particion_de(ctx, "reporte_seguridad", id=ids["actual"]) == P.nombre_particion("reporte_seguridad", HOY.year, HOY.month)
    assert _particion_de(ctx, "reporte_seguridad", id=ids["proximo"]) == P.nombre_particion("reporte_seguridad", a, m)


def test_validacion_hora_particionada_por_fecha_hora(ctx):
    f = dt.datetime(HOY.year, HOY.month, 10, 7)
    ctx.session.add(T.ValidacionHora(fuente="app", sistema="metro_l1", serie="Gamarra", fecha_hora=f, n=1))
    ctx.session.commit()
    assert _particion_de(ctx, "validacion_hora", serie="Gamarra") == P.nombre_particion("validacion_hora", HOY.year, HOY.month)


def test_las_consultas_por_mes_solo_leen_esa_particion(ctx):
    mes = P.nombre_particion("reporte_seguridad", HOY.year, HOY.month)
    desde, hasta = P.rango_mes(HOY.year, HOY.month)
    plan = "\n".join(r[0] for r in ctx.session.execute(text(
        f"EXPLAIN SELECT * FROM reporte_seguridad WHERE creado_en >= '{desde}' AND creado_en < '{hasta}'")).all())
    assert mes in plan
    otras = [p for p in P.listar_particiones(ctx.engine, "reporte_seguridad") if p != mes and not p.endswith("_default")]
    assert all(o not in plan for o in otras), plan                    # poda de particiones: solo se lee el mes pedido


def test_una_fila_fuera_de_rango_cae_en_default_y_se_rescata_al_crear_su_particion(ctx):
    f = dt.datetime(2031, 5, 20, 10, tzinfo=dt.timezone.utc)
    ctx.session.add(T.ReporteSeguridad(id="rep-fuera", creado_en=f, tipo="acoso", ocurrido_en=f, lat=-12.05, lon=-77.03,
                                       seg_id="fuera", franja="noche"))
    ctx.session.commit()
    assert _particion_de(ctx, "reporte_seguridad", id="rep-fuera") == "reporte_seguridad_default"
    creadas = P.ensure_particiones(ctx.engine, "reporte_seguridad", "creado_en", adelante=0, atras=0, hoy=dt.date(2031, 5, 10))
    assert creadas == ["reporte_seguridad_2031_05"]
    assert _particion_de(ctx, "reporte_seguridad", id="rep-fuera") == "reporte_seguridad_2031_05"    # no se perdió ni se duplicó
    assert ctx.session.execute(text("SELECT count(*) FROM reporte_seguridad WHERE seg_id = 'fuera'")).scalar() == 1


def test_retener_quita_los_meses_viejos_y_no_toca_la_default(ctx):
    vieja = dt.date(2022, 1, 15)
    creadas = P.ensure_particiones(ctx.engine, "validacion_hora", "fecha_hora", adelante=1, atras=0, hoy=vieja)
    assert creadas == ["validacion_hora_2022_01", "validacion_hora_2022_02"]
    ctx.session.add(T.ValidacionHora(fuente="app", sistema="troncal", serie="Naranjal", fecha_hora=dt.datetime(2022, 1, 20, 9), n=3))
    ctx.session.commit()
    ctx.session.rollback()
    borradas = P.retener(ctx.engine, "validacion_hora", meses=24, hoy=HOY)
    assert set(borradas) >= {"validacion_hora_2022_01", "validacion_hora_2022_02"}
    restantes = P.listar_particiones(ctx.engine, "validacion_hora")
    assert "validacion_hora_default" in restantes and P.nombre_particion("validacion_hora", HOY.year, HOY.month) in restantes
    assert ctx.session.execute(text("SELECT count(*) FROM validacion_hora WHERE serie = 'Naranjal'")).scalar() == 0


def test_retener_conserva_lo_reciente(ctx):
    antes = P.listar_particiones(ctx.engine, "reporte_seguridad")
    P.retener(ctx.engine, "reporte_seguridad", meses=24, hoy=HOY)
    assert P.nombre_particion("reporte_seguridad", HOY.year, HOY.month) in P.listar_particiones(ctx.engine, "reporte_seguridad")
    assert set(P.listar_particiones(ctx.engine, "reporte_seguridad")) <= set(antes)


def test_el_reporte_rechaza_valores_invalidos(ctx):
    from sqlalchemy.exc import IntegrityError
    f = dt.datetime.now(dt.timezone.utc)
    ctx.session.add(T.ReporteSeguridad(creado_en=f, tipo="otro", ocurrido_en=f, lat=0, lon=0, seg_id="x", franja="dia"))
    with pytest.raises(IntegrityError):
        ctx.session.commit()
    ctx.session.rollback()
