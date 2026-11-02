"""Latencia y memoria del Eje 2 (mismo espíritu que `test_api.py::test_latencia_p95_en_caliente` del Eje 1, AC-04).

Objetivos: /ruta p95 <= 1,0 s en caliente · /reportes p95 <= 0,3 s · /accesos/cercanos p95 <= 0,2 s · carga en frío <= 5 s.
Para ver los números:  pytest tests/test_latencia_eje2.py -s
"""
import os
import time

import numpy as np
import pytest

from eje2_real import origen_destino, punto_de_segmento, registrar_y_entrar, segmentos_distintos
from services import eje2_service as E

pytestmark = pytest.mark.bd


@pytest.fixture(scope="module")
def client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(scope="module")
def g():
    return E.grafo()


def medir(llamadas):
    t = []
    for f in llamadas:
        t0 = time.perf_counter()
        f()
        t.append(time.perf_counter() - t0)
    return np.array(t)


def informe(nombre, t):
    print(f"\n[latencia] {nombre}: mediana {np.median(t) * 1000:.1f} ms · p95 {np.percentile(t, 95) * 1000:.1f} ms · máx {t.max() * 1000:.1f} ms (n={len(t)})")


def rss_mb() -> float:
    return int(open("/proc/self/statm").read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1e6


def test_carga_en_frio_del_grafo():
    t0 = time.perf_counter()
    E.GrafoEje2(E.DATA_EJE2)
    cargado = time.perf_counter() - t0
    print(f"\n[latencia] carga en frío del grafo: {cargado:.2f} s")
    assert cargado <= 5.0


@pytest.mark.skipif(not os.path.exists("/proc/self/statm"), reason="medición de memoria solo en Linux")
def test_el_grafo_cabe_en_memoria():
    antes = rss_mb()
    otro = E.GrafoEje2(E.DATA_EJE2)
    otro.matriz(otro.largo)
    delta = rss_mb() - antes
    print(f"\n[memoria] el grafo en memoria ocupa ~{delta:.0f} MB por proceso (sin los índices de reportes)")
    assert delta < 200            # cada worker de gunicorn carga su propia copia: 2 workers ~ 2x


def test_latencia_p95_de_la_ruta_en_caliente(client, g):
    pares = []
    for acceso in range(0, 60, 3):
        a, (o,) = origen_destino(g, acceso=acceso, seed=acceso)
        pares.append({"origen": o, "destino": {"acceso_id": a}, "franja": "noche" if acceso % 2 else "dia"})
    client.post("/api/eje2/ruta", json=pares[0])                           # calienta
    t = medir([lambda c=c: client.post("/api/eje2/ruta", json=c) for c in pares])
    informe("POST /api/eje2/ruta", t)
    assert np.percentile(t, 95) <= 1.0


def test_latencia_p95_de_los_accesos_cercanos(client, g):
    pts = [g.accesos.iloc[i] for i in range(0, 1500, 75)]
    t = medir([lambda a=a: client.get(f"/api/eje2/accesos/cercanos?lat={a['lat']}&lon={a['lon']}&radius=800") for a in pts])
    informe("GET /api/eje2/accesos/cercanos", t)
    assert np.percentile(t, 95) <= 0.2


def test_latencia_p95_de_crear_un_reporte(client, g, monkeypatch):
    monkeypatch.setenv("EJE2_REPORTES_POR_HORA", "100")
    monkeypatch.setenv("EJE2_REPORTES_POR_DIA", "1000")
    h = registrar_y_entrar(client, "Veloz", "veloz@latencia.test")
    segs = segmentos_distintos(g, 25, seed=77)
    client.post("/api/eje2/reportes", json={"tipo": "robo", **punto_de_segmento(g, 1)}, headers=h)        # calienta (índice de calles)
    t = medir([lambda s=s: client.post("/api/eje2/reportes", json={"tipo": "robo", **punto_de_segmento(g, s)}, headers=h) for s in segs])
    informe("POST /api/eje2/reportes", t)
    assert np.percentile(t, 95) <= 0.3
