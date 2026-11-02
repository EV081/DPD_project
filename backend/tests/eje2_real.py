"""Ayudas para probar el Eje 2 con los datos reales exportados (puntos sobre calles, orígenes y destinos válidos)."""
from __future__ import annotations

import numpy as np
from scipy.sparse.csgraph import dijkstra

from services import eje2_service as E


def punto_de_segmento(g: E.GrafoEje2, s: int) -> dict:
    """lat/lon del punto medio (en línea recta) de un segmento."""
    lon, lat = (g.nodo_lonlat[g.seg_u[s]] + g.nodo_lonlat[g.seg_v[s]]) / 2
    return {"lat": float(lat), "lon": float(lon)}


def segmentos_distintos(g: E.GrafoEje2, n: int, seed: int = 0, largo_max: float = 110.0) -> list[int]:
    """n segmentos cortos y rectos cuyo punto medio cae sobre ellos mismos (útil para que cada reporte vaya a una calle distinta)."""
    rng = np.random.default_rng(seed)
    candidatos = np.where(g.largo < largo_max)[0]
    elegidos: list[int] = []
    for s in rng.permutation(candidatos):
        p = punto_de_segmento(g, int(s))
        try:
            vecino, _ = g.segmento_cercano(p["lat"], p["lon"], 40.0)
        except E.Eje2Error:
            continue
        if vecino == s and all(abs(g.nodo_lonlat[g.seg_u[s]][0] - g.nodo_lonlat[g.seg_u[o]][0]) > 5e-4 for o in elegidos):
            elegidos.append(int(s))
        if len(elegidos) == n:
            return elegidos
    raise AssertionError("no se encontraron suficientes segmentos de prueba")


def origen_destino(g: E.GrafoEje2, acceso: int = 0, minimo: float = 450.0, maximo: float = 750.0, n: int = 1, seed: int = 0):
    """(acceso_id, [orígenes {lat, lon} a minimo..maximo m caminando del acceso])."""
    fila = g.accesos.iloc[acceso]
    nodo = int(g.acc_nodo[g.acc_indice[fila["acceso_id"]]])
    d = dijkstra(g.matriz(g.largo), directed=True, indices=nodo, limit=maximo)
    cand = np.where((d > minimo) & (d < maximo))[0]
    pts = [dict(lat=float(g.nodo_lonlat[k][1]), lon=float(g.nodo_lonlat[k][0])) for k in np.random.default_rng(seed).choice(cand, n, replace=False)]
    return fila["acceso_id"], pts


def registrar_y_entrar(client, nombre: str, email: str) -> dict:
    """Crea un usuario y devuelve su cabecera Authorization."""
    client.post("/api/auth/register", json={"name": nombre, "email": email, "password": "123456"})
    token = client.post("/api/auth/login", json={"email": email, "password": "123456"}).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
