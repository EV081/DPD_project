"""Exporta paraderos, rutas y trazados de la BD a archivos listos para compartir.

  paraderos.csv          una fila por parada de cada ruta y sentido (la entrega para el equipo)
  rutas.csv              una fila por ruta, con % de paradas exactas y origen del trazado
  rutas_trazados.geojson trazado de cada ruta (derivado u oficial segun `origen_trazado`)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SQL_PARADAS = """
SELECT r.sistema, r.codigo AS ruta, r.nombre AS ruta_nombre,
       pr.direccion AS sentido, pr.orden, p.nombre AS paradero,
       p.lat, p.lon, p.calidad_coord, p.confianza, p.precision_coord AS precision,
       p.evidencia, pr.unidad_modelo, r.origen_trazado
FROM paradero_ruta pr
JOIN ruta r ON r.id = pr.ruta_id
JOIN paradero p ON p.id = pr.paradero_id
ORDER BY r.sistema, r.codigo, pr.direccion, pr.orden NULLS LAST, p.nombre
"""
SQL_RUTAS = """
SELECT r.sistema, r.codigo AS ruta, r.nombre AS ruta_nombre, r.origen_trazado,
       (r.trazado IS NOT NULL) AS tiene_trazado, r.n_paradas, r.pct_exactas,
       count(pr.paradero_id) AS enlaces
FROM ruta r LEFT JOIN paradero_ruta pr ON pr.ruta_id = r.id
GROUP BY r.id ORDER BY r.sistema, r.codigo
"""


def _df(conn, sql: str) -> pd.DataFrame:
    cur = conn.cursor()
    try:
        cur.execute(sql)
        filas, cols = cur.fetchall(), [d[0] for d in cur.description]
    finally:
        cur.close()
    return pd.DataFrame(filas, columns=cols)


def exportar(conn, out: Path) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    paradas = _df(conn, SQL_PARADAS)
    paradas["sentido"] = paradas["sentido"].replace(0, pd.NA).astype("Int64")   # 0 = sin sentido
    paradas["orden"] = paradas["orden"].astype("Int64")
    paradas.to_csv(out / "paraderos.csv", index=False, encoding="utf-8")
    rutas = _df(conn, SQL_RUTAS)
    for c in ("n_paradas", "pct_exactas"):
        rutas[c] = rutas[c].astype("Int64")
    rutas.to_csv(out / "rutas.csv", index=False, encoding="utf-8")

    cur = conn.cursor()
    try:
        cur.execute("SELECT sistema, codigo, nombre, origen_trazado, trazado FROM ruta "
                    "WHERE trazado IS NOT NULL ORDER BY sistema, codigo")
        feats = [{"type": "Feature",
                  "properties": {"sistema": r["sistema"], "ruta": r["codigo"], "nombre": r["nombre"],
                                 "origen_trazado": r["origen_trazado"]},
                  "geometry": r["trazado"] if isinstance(r["trazado"], dict) else json.loads(r["trazado"])}
                 for r in cur.fetchall()]
    finally:
        cur.close()
    (out / "rutas_trazados.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    return {"paraderos_csv": len(paradas), "rutas_csv": len(rutas), "trazados": len(feats)}
