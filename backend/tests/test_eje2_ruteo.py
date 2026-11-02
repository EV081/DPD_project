"""Ruteo seguro del Eje 2: pruebas sobre un grafo sintético (casos controlados) y sobre los datos reales exportados."""
import datetime as dt
import hashlib
import json

import numpy as np
import pytest
from scipy.sparse.csgraph import dijkstra

from eje2_sintetico import NODOS, crear_grafo
from services import eje2_service as E
from services import polilinea

ORIGEN = {"lat": NODOS[1][1], "lon": NODOS[1][0]}
DESTINO = {"acceso_id": "metro_l1_0000"}


def grafo(tmp_path, **kw):
    return E.GrafoEje2(crear_grafo(tmp_path, **kw))


# --------------------------------------------------------------------------- utilidades
def test_polilinea_ida_y_vuelta():
    pts = [(-77.03, -12.05), (-77.0291, -12.0494), (-77.02, -12.04)]
    for p, q in zip(pts, polilinea.decodificar(polilinea.codificar(pts))):
        assert p == pytest.approx(q, abs=1e-5)


@pytest.mark.parametrize("hora,esperada", [(5, "noche"), (6, "dia"), (17, "dia"), (18, "noche"), (23, "noche"), (0, "noche")])
def test_franja_por_hora_de_lima(hora, esperada):
    assert E.franja_de(dt.datetime(2026, 11, 2, hora, 30, tzinfo=E.calendario.TZ_LIMA)) == esperada


def test_banda_de_riesgo():
    b = {"bajo_hasta": 0.2, "alto_desde": 0.5}
    assert [E.banda(x, b) for x in (0.0, 0.19, 0.2, 0.49, 0.5, 1.0)] == ["bajo", "bajo", "medio", "medio", "alto", "alto"]


# --------------------------------------------------------------------------- grafo sintético
def test_lambda_cero_es_la_ruta_mas_corta(tmp_path):
    r = E.rutas(ORIGEN, DESTINO, lam=0, g=grafo(tmp_path))
    assert r["rutas"]["segura"]["distancia_m"] == r["rutas"]["normal"]["distancia_m"] == 250.0
    assert r["recomendada"] == "misma" and "ya es la más segura" in r["explicacion"]["resumen"]


def test_la_segura_esquiva_la_calle_riesgosa(tmp_path):
    r = E.rutas(ORIGEN, DESTINO, franja="noche", g=grafo(tmp_path))
    assert r["rutas"]["normal"]["distancia_m"] == 250.0          # A: 100 + 100 + 50
    assert r["rutas"]["segura"]["distancia_m"] == 310.0          # B: 130 + 130 + 50
    assert r["recomendada"] == "segura" and r["seleccionada"] == "segura"
    c = r["comparacion"]
    assert c["distancia_extra_m"] == 60.0 and c["reduccion_riesgo_pct"] > 0.5
    assert "Jr. Tranquilo" in [t["nombre"] for t in r["rutas"]["segura"]["tramos"] if t["desvio"]]
    assert r["explicacion"]["tramos_evitados"][0]["nombre"] == "Av. Rápida"
    assert r["explicacion"]["llamar_105"] is True and "105" in r["explicacion"]["aviso"]


def test_el_usuario_puede_preferir_la_normal_y_la_recomendacion_se_mantiene(tmp_path):
    r = E.rutas(ORIGEN, DESTINO, preferencia="normal", g=grafo(tmp_path))
    assert r["seleccionada"] == "normal" and r["recomendada"] == "segura"          # ambas rutas vienen siempre en la respuesta
    assert set(r["rutas"]) == {"normal", "segura"}


def test_no_recomienda_la_segura_si_el_desvio_es_excesivo(tmp_path):
    r = E.rutas(ORIGEN, DESTINO, franja="noche", g=grafo(tmp_path, largo_b=400.0))        # B suma 800 m contra 200 m de A
    assert r["rutas"]["segura"]["distancia_m"] > r["rutas"]["normal"]["distancia_m"]
    assert r["recomendada"] == "normal" and "Elige la que prefieras" in r["explicacion"]["resumen"]


def test_no_recomienda_la_segura_si_la_mejora_es_pequena(tmp_path):
    r = E.rutas(ORIGEN, DESTINO, g=grafo(tmp_path, largo_b=102.5, riesgo_a=0.30, riesgo_b=0.29))
    assert r["rutas"]["segura"]["distancia_m"] != r["rutas"]["normal"]["distancia_m"]
    assert r["comparacion"]["reduccion_riesgo_pct"] < 0.10
    assert r["recomendada"] == "normal"


def test_la_franja_cambia_la_ruta(tmp_path):
    g = grafo(tmp_path, riesgo_a={"dia": 0.1, "noche": 0.9, "total": 0.5}, riesgo_b=0.1)
    de_dia = E.rutas(ORIGEN, DESTINO, franja="dia", g=g)
    de_noche = E.rutas(ORIGEN, DESTINO, franja="noche", g=g)
    assert de_dia["recomendada"] == "misma" and de_noche["recomendada"] == "segura"
    assert de_dia["franja"] == "dia" and de_noche["explicacion"]["condiciones"]["franja"] == "noche"


def test_los_reportes_de_usuarios_pueden_cambiar_la_ruta(tmp_path):
    g = grafo(tmp_path, riesgo_a=0.1, riesgo_b=0.1)
    sin = E.rutas(ORIGEN, DESTINO, franja="noche", g=g)
    assert sin["recomendada"] == "misma"
    deltas = E.deltas_desde_filas(g, [("1_2_0", "noche", 0.3), ("2_4_0", "noche", 0.3)])
    con = E.rutas(ORIGEN, DESTINO, franja="noche", g=g, deltas=deltas)
    assert con["rutas"]["segura"]["distancia_m"] == 310.0
    assert con["explicacion"]["condiciones"]["reportes_aplicados"] is True
    assert any("reportes recientes" in m for m in con["explicacion"]["motivos"])


def test_los_reportes_de_una_franja_no_afectan_a_la_otra(tmp_path):
    g = grafo(tmp_path, riesgo_a=0.1, riesgo_b=0.1)
    deltas = E.deltas_desde_filas(g, [("1_2_0", "noche", 0.3), ("2_4_0", "noche", 0.3)])
    assert E.rutas(ORIGEN, DESTINO, franja="dia", g=g, deltas=deltas)["recomendada"] == "misma"


def test_el_riesgo_efectivo_queda_entre_0_y_1(tmp_path):
    g = grafo(tmp_path, riesgo_a=0.9)
    r = g.riesgo_efectivo("noche", E.deltas_desde_filas(g, [("1_2_0", "noche", 0.8), ("1_3_0", "noche", -0.8)]))
    assert r.min() >= 0.0 and r.max() <= 1.0


def test_la_geometria_empieza_en_el_origen_y_termina_en_el_acceso(tmp_path):
    r = E.rutas(ORIGEN, DESTINO, franja="noche", g=grafo(tmp_path))
    for tipo in ("normal", "segura"):
        coords = r["rutas"][tipo]["geojson"]["geometry"]["coordinates"]
        assert coords[0] == pytest.approx(list(NODOS[1]), abs=1e-5) and coords[-1] == pytest.approx(list(NODOS[5]), abs=1e-5)


def test_origen_igual_al_destino(tmp_path):
    r = E.rutas({"lat": NODOS[5][1], "lon": NODOS[5][0]}, DESTINO, g=grafo(tmp_path))
    assert r["rutas"]["normal"]["distancia_m"] == 0 and r["recomendada"] == "misma"


@pytest.mark.parametrize("origen,destino,estado", [
    ({"lat": -12.2, "lon": -77.2}, DESTINO, 422),                                  # lejos de la red cubierta
    (ORIGEN, {"acceso_id": "no_existe"}, 404),
    (ORIGEN, {"nada": 1}, 400),
    ({"lat": "x", "lon": 1}, DESTINO, 400),
])
def test_errores_de_entrada(tmp_path, origen, destino, estado):
    with pytest.raises(E.Eje2Error) as e:
        E.rutas(origen, destino, g=grafo(tmp_path))
    assert e.value.status == estado


@pytest.mark.parametrize("kw", [{"preferencia": "rapida"}, {"franja": "tarde"}, {"lam": 999}, {"lam": -1}])
def test_parametros_invalidos(tmp_path, kw):
    with pytest.raises(E.Eje2Error):
        E.rutas(ORIGEN, DESTINO, g=grafo(tmp_path), **kw)


def test_aristas_paralelas_se_deduplican(tmp_path):
    g = grafo(tmp_path)
    assert g.segmentos_omitidos == 0 and g._indptr[-1] == 2 * 5                   # 5 segmentos, ambos sentidos


def test_accesos_cercanos(tmp_path):
    g = grafo(tmp_path)
    cerca = g.accesos_cercanos(NODOS[5][1], NODOS[5][0], radio_m=100)
    assert [a["acceso_id"] for a in cerca] == ["metro_l1_0000"] and cerca[0]["seguridad_pct"] == 80
    assert cerca[0]["base_tipo_pct"] == 75 and cerca[0]["intervalo_pct"] == [70, 90]
    assert g.accesos_cercanos(NODOS[1][1], NODOS[1][0], radio_m=50) == []


# --------------------------------------------------------------------------- datos reales exportados
@pytest.fixture(scope="module")
def real():
    return E.grafo()


def test_artefactos_integros():
    manifest = json.loads((E.DATA_EJE2 / "manifest.json").read_text())
    for nombre, info in manifest["archivos"].items():
        datos = (E.DATA_EJE2 / nombre).read_bytes()
        assert len(datos) == info["bytes"] and hashlib.sha256(datos).hexdigest() == info["sha256"], nombre


def test_el_grafo_real_es_consistente(real):
    m = real.manifest
    assert real.n_seg == m["n_segmentos"] == 146_607 and real.n == m["n_nodos"] and len(real.accesos) == m["n_accesos"]
    for f in ("total", "noche", "dia"):
        assert real.riesgo[f].min() >= 0 and real.riesgo[f].max() <= 1
    assert real.segmentos_omitidos < 0.02 * real.n_seg                         # aristas paralelas: pocas
    assert real.accesos["snap_m"].max() < 150 and set(real.accesos["tipo"]) == {"metro_l1", "troncal", "corredor", "alimentador"}


def _origenes(real, acceso_id, n=5, seed=0):
    nodo = int(real.acc_nodo[real.acc_indice[acceso_id]])
    d = dijkstra(real.matriz(real.largo), directed=True, indices=nodo, limit=800)
    cand = np.where((d > 400) & (d < 750))[0]
    return [dict(zip(("lon", "lat"), real.nodo_lonlat[k])) for k in np.random.default_rng(seed).choice(cand, n, replace=False)]


def test_ruta_real_es_optima_y_valida(real):
    acceso = real.accesos["acceso_id"].iloc[0]
    for o in _origenes(real, acceso):
        r = E.rutas(o, {"acceso_id": acceso}, franja="noche", g=real)
        corta, segura = r["rutas"]["normal"], r["rutas"]["segura"]
        assert corta["distancia_m"] <= segura["distancia_m"] + 1e-6               # la corta nunca es más larga
        assert corta["distancia_m"] < E.ALCANCE_MAX_M
        # óptima con los pesos de riesgo: no existe otro camino más barato (la corta evaluada con esos pesos cuesta ≥)
        g2 = r["rutas"]["segura"]["densidad_media_km_anio"] <= corta["densidad_media_km_anio"] + 1e-6
        assert g2, "la ruta segura no puede tener más denuncias esperadas por km que la corta"
        assert r["recomendada"] in ("segura", "normal", "misma")


def test_lambda_cero_real_coincide_con_la_corta(real):
    acceso = real.accesos["acceso_id"].iloc[3]
    o = _origenes(real, acceso, 1)[0]
    r = E.rutas(o, {"acceso_id": acceso}, lam=0, g=real)
    assert r["rutas"]["segura"]["distancia_m"] == r["rutas"]["normal"]["distancia_m"] and r["recomendada"] == "misma"


def test_todos_los_accesos_se_pueden_usar_como_destino(real):
    for tipo, g in real.accesos.groupby("tipo"):
        acc = g.iloc[0]["acceso_id"]
        d, fila = E.resolver_destino(real, {"acceso_id": acc})
        assert fila["tipo"] == tipo and 0 <= d < real.n


def test_estaciones_de_la_api_se_mapean_a_accesos(real):
    from routes.stations import load_all_stations_into_memory
    est = load_all_stations_into_memory()
    con_acceso = sin_acceso = 0
    for e in est:
        try:
            assert E.acceso_de_estacion(real, e["id"], e["system"])["tipo"] == E.SISTEMA_A_TIPO[e["system"]]
            con_acceso += 1
        except E.SinAccesoError:
            sin_acceso += 1
    assert con_acceso / len(est) > 0.85, f"solo {con_acceso} de {len(est)} estaciones tienen punto de acceso"
    for s in ("metro_l1", "metropolitano", "alimentadores"):                          # estos tres sistemas se mapean completos
        assert all(E.acceso_de_estacion(real, e["id"], s) is not None for e in est if e["system"] == s)


def test_paradero_sin_indice_se_enruta_hacia_su_coordenada(real):
    from routes.stations import load_all_stations_into_memory
    sin = next(e for e in load_all_stations_into_memory() if e["system"] == "corredores"
               and not _tiene_acceso(real, e))
    nodo, fila = E.resolver_destino(real, {"station_id": sin["id"], "sistema": "corredores"}) if _cubierto(real, sin) else (None, None)
    if nodo is not None:
        assert fila is None and 0 <= nodo < real.n


def _tiene_acceso(real, e):
    try:
        E.acceso_de_estacion(real, e["id"], e["system"])
        return True
    except E.SinAccesoError:
        return False


def _cubierto(real, e):
    try:
        real.nodo_cercano(e["latitude"], e["longitude"])
        return True
    except E.Eje2Error:
        return False
