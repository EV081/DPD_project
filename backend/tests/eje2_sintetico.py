"""Grafo sintético mínimo para probar el ruteo del Eje 2 sin depender de los datos reales.

        n2 ----(A)---- n4
       /                 \\
    n1                    n5   (n5 = punto de acceso)
       \\                 /
        n3 ----(B)---- n4        A = camino corto, B = camino alternativo

Segmentos: s1 n1-n2, s2 n2-n4 (camino A) · s3 n1-n3, s4 n3-n4 (camino B) · s5 n4-n5 (compartido).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from services import polilinea

NODOS = {1: (-77.0300, -12.0500), 2: (-77.0290, -12.0490), 3: (-77.0290, -12.0510), 4: (-77.0280, -12.0500), 5: (-77.0272, -12.0500)}
SEGMENTOS = {"1_2_0": (1, 2), "2_4_0": (2, 4), "1_3_0": (1, 3), "3_4_0": (3, 4), "4_5_0": (4, 5)}
MANIFEST = {
    "version": "eje2-test", "datos_hasta": "2024-08-31", "forma_costo": "lineal", "lambda": 12.0,
    "topes_recomendacion": {"reduccion_min": 0.10, "desvio_pct_max": 0.30, "desvio_m_max": 250},
    "bandas_riesgo": {"bajo_hasta": 0.2, "alto_desde": 0.5},
    "ref_p99_densidad": {"total": 50.0, "noche": 50.0, "dia": 50.0}, "velocidad_caminata_m_min": 80,
}


def crear_grafo(directorio: Path, largo_a: float = 100.0, largo_b: float = 130.0, riesgo_a=0.9, riesgo_b=0.1,
                riesgo_compartido: float = 0.1, nombres: dict | None = None) -> Path:
    """Escribe un directorio con el mismo formato que backend/data/eje2.

    largo_a / largo_b: largo de CADA segmento de los caminos A y B. riesgo_a / riesgo_b: número (mismo en las tres franjas)
    o dict {'dia':…, 'noche':…, 'total':…}.
    """
    def r(valor, franja):
        return valor[franja] if isinstance(valor, dict) else valor

    nombres = nombres or {"1_2_0": "Av. Rápida", "2_4_0": "Av. Rápida", "1_3_0": "Jr. Tranquilo", "3_4_0": "Jr. Tranquilo", "4_5_0": "Jr. Estación"}
    filas = []
    for seg, (u, v) in SEGMENTOS.items():
        en_a, en_b = seg in ("1_2_0", "2_4_0"), seg in ("1_3_0", "3_4_0")
        largo = largo_a if en_a else (largo_b if en_b else 50.0)
        base = riesgo_a if en_a else (riesgo_b if en_b else riesgo_compartido)
        filas.append({"seg_id": seg, "u": u, "v": v, "largo_m": largo, "via": "arterial" if en_a else "residencial",
                      "nombre": nombres.get(seg), "riesgo_total": r(base, "total"), "riesgo_noche": r(base, "noche"), "riesgo_dia": r(base, "dia")})
    grafo = pd.DataFrame(filas)
    nodos = pd.DataFrame({"nodo": list(NODOS), "lon": [p[0] for p in NODOS.values()], "lat": [p[1] for p in NODOS.values()]})
    geo = pd.DataFrame({"seg_id": list(SEGMENTOS), "geom": [polilinea.codificar([NODOS[u], NODOS[v]]) for u, v in SEGMENTOS.values()]})
    acc = pd.DataFrame([{
        "acceso_id": "metro_l1_0000", "tipo": "metro_l1", "nombre": "Estación Prueba", "ruta": None, "lon": NODOS[5][0], "lat": NODOS[5][1],
        "nodo": 5, "snap_m": 0.0, "precision_coord": "exacta", "seguridad_pct": 80.0, "seg_lo": 70.0, "seg_hi": 90.0,
        "base_tipo_pct": 75.0, "vs_base": 5.0, "confianza": "alta", "n_seg": 5}])
    directorio.mkdir(parents=True, exist_ok=True)
    for nombre, df in {"grafo.parquet": grafo, "nodos.parquet": nodos, "geometrias.parquet": geo, "accesos.parquet": acc}.items():
        df.to_parquet(directorio / nombre, index=False)
    (directorio / "manifest.json").write_text(json.dumps(MANIFEST))
    return directorio
