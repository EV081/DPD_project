"""Exporta los artefactos del Eje 2 desde deliveries/week12 a backend/data/eje2 (lo único que necesita el servidor).

    python backend/scripts/exportar_eje2.py            # desde la raíz del repo, con un entorno que tenga geopandas

geopandas/shapely se usan SOLO aquí; el backend en producción lee parquet con pandas/pyarrow y no depende de ellos.

Salida (backend/data/eje2/):
    grafo.parquet       seg_id,u,v,largo_m,via,nombre,riesgo_total,riesgo_noche,riesgo_dia  (un segmento = una calle)
    nodos.parquet       nodo,lon,lat                                                      (solo los nodos del grafo)
    geometrias.parquet  seg_id,geom   polilínea codificada y simplificada (~2 m), orientada de u a v
    accesos.parquet     acceso_id,tipo,nombre,ruta,lon,lat,nodo,snap_m + índice de seguridad (seguridad %, intervalo, base, confianza)
    manifest.json       versión, λ, forma de costo, p99 de densidad, datos_hasta, tamaños y sha256
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))
from services import polilinea  # noqa: E402

W12 = RAIZ / "deliveries" / "week12"
EJE2 = W12 / "data_processed" / "eje2"
SALIDA = RAIZ / "backend" / "data" / "eje2"
TOLERANCIA_GRADOS = 2e-5                       # ~2 m al simplificar geometrías
LAT0 = -12.05
M_LAT, M_LON = 111_132.0, 111_320.0 * np.cos(np.radians(LAT0))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def primer_nombre(v) -> str | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).split(";")[0].strip()
    return s or None


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    grafo = pd.read_parquet(EJE2 / "export" / "grafo_ruteo.parquet")
    print(f"grafo: {len(grafo):,} segmentos")

    # --- nombres y geometrías: se reconstruye el mismo seg_id que usó el feature engineering ---
    ar = gpd.read_parquet(EJE2 / "graph" / "aristas.parquet").to_crs(4326)
    a, b = np.minimum(ar["u"], ar["v"]), np.maximum(ar["u"], ar["v"])
    ar["seg_id"] = a.astype(str) + "_" + b.astype(str) + "_" + ar["key"].astype(str)
    ar["u_min"] = a.values
    ar = ar[ar["seg_id"].isin(set(grafo["seg_id"]))].drop_duplicates("seg_id")
    nombres = ar.set_index("seg_id")["name"].map(primer_nombre)

    simp = ar.geometry.simplify(TOLERANCIA_GRADOS, preserve_topology=False)
    geoms = []
    for g, u_orig, u_min in zip(simp, ar["u"].values, ar["u_min"].values):
        coords = list(g.coords)
        if u_orig != u_min:                      # orientar siempre de u (nodo menor) a v
            coords = coords[::-1]
        geoms.append(polilinea.codificar(coords))
    geo = pd.DataFrame({"seg_id": ar["seg_id"].values, "geom": geoms})
    faltan = set(grafo["seg_id"]) - set(geo["seg_id"])
    print(f"geometrías: {len(geo):,} · segmentos sin geometría: {len(faltan)}")

    grafo_out = grafo.assign(nombre=grafo["seg_id"].map(nombres)).astype(
        {"largo_m": "float32", "riesgo_total": "float32", "riesgo_noche": "float32", "riesgo_dia": "float32"})
    grafo_out["via"] = grafo_out["via"].astype("category")
    grafo_out = grafo_out[["seg_id", "u", "v", "largo_m", "via", "nombre", "riesgo_total", "riesgo_noche", "riesgo_dia"]]

    # --- nodos del grafo ---
    nodos = gpd.read_parquet(EJE2 / "graph" / "nodos.parquet")
    usados = set(grafo["u"]).union(set(grafo["v"]))
    nodos = nodos[nodos["osmid"].isin(usados)]
    nodos_out = pd.DataFrame({"nodo": nodos["osmid"].astype("int64").values, "lon": nodos["x"].values, "lat": nodos["y"].values})
    print(f"nodos: {len(nodos_out):,}")

    # --- accesos con su índice de seguridad ---
    acc = pd.read_parquet(EJE2 / "outputs" / "indice_puntos_acceso.parquet")
    xy_n = np.c_[nodos_out["lon"] * M_LON, nodos_out["lat"] * M_LAT]
    d, i = cKDTree(xy_n).query(np.c_[acc["lon"] * M_LON, acc["lat"] * M_LAT])
    acc = acc.assign(nodo=nodos_out["nodo"].values[i], snap_m=d)
    cols = ["acceso_id", "tipo", "nombre", "ruta", "lon", "lat", "nodo", "snap_m", "precision_coord", "seguridad_pct",
            "seg_lo", "seg_hi", "base_tipo_pct", "vs_base", "confianza", "n_seg"]
    acc_out = acc[cols].copy()
    acc_out["ruta"] = acc_out["ruta"].astype("string")
    print(f"accesos: {len(acc_out):,} · snap máx {acc_out['snap_m'].max():.0f} m")

    escribir = {"grafo.parquet": grafo_out, "nodos.parquet": nodos_out, "geometrias.parquet": geo, "accesos.parquet": acc_out}
    for nombre, df in escribir.items():
        df.to_parquet(SALIDA / nombre, index=False, compression="zstd")

    lam = json.loads((EJE2 / "outputs" / "lambda_elegido.json").read_text())
    mod = json.loads((W12 / "models" / "eje2" / "manifest.json").read_text())
    manifest = {
        "version": "eje2-ruta-v1.0",
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "modelo_riesgo": mod.get("version"),
        "datos_hasta": "2024-08-31",
        "entrenado_con": mod.get("entrenado_con"),
        "forma_costo": lam["forma"],
        "lambda": lam["lambda"],
        "topes_recomendacion": {"reduccion_min": 0.10, "desvio_pct_max": 0.30, "desvio_m_max": 250},
        "bandas_riesgo": {"bajo_hasta": 0.2, "alto_desde": 0.5},
        "ref_p99_densidad": mod["ref_p99_densidad"],
        "velocidad_caminata_m_min": 80,
        "n_segmentos": int(len(grafo_out)), "n_nodos": int(len(nodos_out)), "n_accesos": int(len(acc_out)),
        "archivos": {n: {"bytes": (SALIDA / n).stat().st_size, "sha256": sha256(SALIDA / n)} for n in escribir},
    }
    (SALIDA / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(json.dumps({k: manifest[k] for k in ("version", "lambda", "n_segmentos", "n_nodos", "n_accesos")}))
    print({n: f"{v['bytes'] / 1e6:.1f} MB" for n, v in manifest["archivos"].items()})


if __name__ == "__main__":
    main()
