"""Carga paraderos, rutas y trazados (GeoJSON de ``scripts/build_trazados.py``) a PostgreSQL.

Idempotente: recarga las tres tablas en una transaccion. El enlace con el modelo
(``paradero_ruta.unidad_modelo``) sale de ``demanda_fiable``, la misma fuente que usa el
batch ``predict``, de modo que el backend puede unir paraderos con ``prediccion``.

Calidad de las coordenadas (campo ``calidad_coord``):
  gps_atu     corredores: coordenada oficial del catalogo ATU
  osm_nombre  troncal y embarques de alimentador en estacion: ubicadas por nombre exacto
              en OSM (aproximadas). Los paraderos de alimentador que no son embarques en
              estacion NO tienen coordenada oficial y no se cargan
  shapefile   metro L1
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from psycopg.types.json import Jsonb

from pipeline import config

SISTEMAS = ("metro_l1", "troncal", "corredor", "alimentador")


def norm(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "").strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


# Variantes de escritura de ATU en las paginas de servicio (mismas que build_trazados.py)
ALIAS_SERVICIO = {
    "canavaly moreyra": "canaval y moreyra", "plaza flores": "plaza de flores",
    "dos mayo": "2 de mayo", "28julio": "28 de julio",
}


def norm_estacion(texto) -> str:
    n = norm(texto)
    return ALIAS_SERVICIO.get(n, n)


def _features(geo_dir: Path, nombre: str) -> list[dict]:
    ruta = geo_dir / f"{nombre}.geojson"
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8")).get("features", [])


def _punto(f: dict) -> tuple[float, float] | None:
    c = (f.get("geometry") or {}).get("coordinates")
    if not c or len(c) < 2:
        return None
    lon, lat = float(c[0]), float(c[1])
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None


def _multilinea(features: list[dict]) -> dict | None:
    lineas = []
    for f in features:
        g = f.get("geometry") or {}
        if g.get("type") == "LineString":
            lineas.append(g["coordinates"])
        elif g.get("type") == "MultiLineString":
            lineas.extend(g["coordinates"])
    if not lineas:
        return None
    if len(lineas) == 1:
        return {"type": "LineString", "coordinates": lineas[0]}
    return {"type": "MultiLineString", "coordinates": lineas}


FUSION_M = 40.0  # mismo nombre a menos de esto = mismo paradero fisico


def _dist_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import cos, hypot, radians

    dy = (a[0] - b[0]) * 111_320.0
    dx = (a[1] - b[1]) * 111_320.0 * cos(radians((a[0] + b[0]) / 2))
    return hypot(dx, dy)


def construir(geo_dir: Path, unidades: dict[str, dict[str, str]]) -> dict:
    """Arma paraderos/rutas/enlaces en memoria. ``unidades``: sistema -> {norm: unidad real}."""
    paraderos: dict[tuple[str, str], dict] = {}
    rutas: dict[tuple[str, str], dict] = {}
    enlaces: dict[tuple, dict] = {}
    sin_enlace = {"servicio_sin_estacion": 0}

    def unidad_de(sistema: str, valor: str) -> str | None:
        # "LosAlisos" / "AntunezDeMayolo" (carpetas del portal) -> palabras separadas
        tab, n = unidades.get(sistema, {}), norm(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(valor)))
        if n in tab:
            return tab[n]
        n2 = re.sub(r"^(los|las|el|la)\s+", "", n)
        # "LosAlisos" (carpeta del portal) -> "alisos"; tambien sin espacios
        return tab.get(n2) or next((v for k, v in tab.items() if k.replace(" ", "") in
                                    (n.replace(" ", ""), n2.replace(" ", ""))), None)

    fusion: dict[tuple[str, str], list[tuple[tuple[float, float], tuple[str, str]]]] = {}

    def add_paradero(sistema, codigo, nombre, pt, precision, fusionar=False, confianza=None,
                     precision_coord=None, evidencia=None):
        nombre = " ".join(str(nombre).split())
        if fusionar and pt:
            # el catalogo ATU repite el paradero fisico por ruta/sentido: se unifican
            for otro, k_otro in fusion.get((sistema, norm(nombre)), []):
                if _dist_m(pt, otro) <= FUSION_M:
                    if precision_coord == "exacta":       # un sentido confirmado confirma el paradero
                        paraderos[k_otro]["precision_coord"] = "exacta"
                        paraderos[k_otro]["evidencia"] = evidencia
                    return k_otro
        k = (sistema, str(codigo))
        if fusionar and pt and k not in paraderos:
            fusion.setdefault((sistema, norm(nombre)), []).append((pt, k))
        if k not in paraderos and pt:
            paraderos[k] = {"sistema": sistema, "codigo": str(codigo), "nombre": nombre,
                            "lat": pt[0], "lon": pt[1], "calidad_coord": precision,
                            "confianza": confianza, "precision_coord": precision_coord,
                            "evidencia": evidencia}
        return k

    def add_ruta(sistema, codigo, nombre, color=None, nota=None):
        k = (sistema, str(codigo))
        rutas.setdefault(k, {"sistema": sistema, "codigo": str(codigo), "nombre": nombre,
                             "color_hex": color, "trazado": None, "nota": nota,
                             "origen_trazado": None})
        return k

    def enlazar(pk, rk, orden, unidad, direccion=0):
        if pk in paraderos:
            enlaces.setdefault((pk, rk, direccion), {"orden": orden, "unidad_modelo": unidad})

    # metro L1 y troncal: una estacion = un paradero, todas sobre una ruta unica
    for sistema, archivo, ruta_cod, ruta_nom in (
        ("metro_l1", "puntos_metro_l1", "metro_l1", "Metro de Lima - Linea 1"),
        ("troncal", "puntos_troncal", "troncal", "Metropolitano - Troncal"),
    ):
        rk = add_ruta(sistema, ruta_cod, ruta_nom)
        for i, f in enumerate(_features(geo_dir, archivo), 1):
            p = f["properties"]
            nombre = p.get("estacion") or p.get("unidad")
            calidad = ("shapefile" if sistema == "metro_l1" else
                       "revision_humana" if p.get("match") == "manual" else
                       "google_places" if p.get("match") == "google" else "osm_nombre")
            pk = add_paradero(sistema, norm(nombre), nombre, _punto(f), calidad,
                              confianza={"google_places": "media", "revision_humana": "verificada"}.get(calidad))
            enlazar(pk, rk, i, unidad_de(sistema, p.get("unidad") or nombre))

    # corredores: paradero por cod_paradero, ruta por codigo de servicio
    for f in _features(geo_dir, "puntos_corredores"):
        p = f["properties"]
        rk = add_ruta("corredor", p["ruta"], f"Corredor {p['ruta']}")
        pk = add_paradero("corredor", p["cod_paradero"], p["paradero"], _punto(f), "gps_atu",
                          fusionar=True)
        enlazar(pk, rk, None, unidad_de("corredor", p["ruta"]))

    # orden real por ruta y sentido (ATU) con la coordenada resuelta por build_trazados
    for f in _features(geo_dir, "paradas_corredores"):
        p, pt = f["properties"], _punto(f)
        if not pt:
            continue
        rk = add_ruta("corredor", p["ruta"], f"Corredor {p['ruta']}")
        pk = add_paradero("corredor", f"{p['ruta']}-{p['direccion']}-{p['orden']}", p["paradero"],
                          pt, "gps_atu", fusionar=True)
        enlazar(pk, rk, p["orden"], unidad_de("corredor", p["ruta"]), int(p["direccion"]))

    # alimentadores: nombre y orden ATU (portal QR) + coordenada OSM por secuencia
    for f in _features(geo_dir, "paradas_alimentadores"):
        p, pt = f["properties"], _punto(f)
        if not pt:
            continue
        titulo = p.get("codigo") or p["servicio"]
        rk = add_ruta("alimentador", p["servicio"], f"Alimentador {p['servicio']} ({titulo})")
        pk = add_paradero("alimentador", f"{p['servicio']}-{p['bloque']}-{p['orden']}", p["paradero"],
                          pt, "osm_secuencia", fusionar=True, confianza=p.get("confianza"),
                          precision_coord=p.get("precision"), evidencia=p.get("evidencia"))
        enlazar(pk, rk, p["orden"], unidad_de("alimentador", p["servicio"].split("/")[-1]), int(p["bloque"]))

    # servicios del Metropolitano (rutas expreso/regular) sobre las estaciones troncales
    por_norm = {norm(v["nombre"]): k for k, v in paraderos.items() if k[0] == "troncal"}
    for f in _features(geo_dir, "puntos_metropolitano_servicios"):
        p = f["properties"]
        rk = add_ruta("troncal", p["servicio_slug"], p.get("servicio_nombre") or p["servicio_slug"])
        pk = por_norm.get(norm_estacion(p.get("estacion")))
        if pk is None:
            sin_enlace["servicio_sin_estacion"] += 1
            continue
        enlazar(pk, rk, p.get("orden"), unidad_de("troncal", paraderos[pk]["nombre"]))

    # trazados -> ruta.trazado (MultiLineString si hay varias direcciones)
    def agrupar(archivo, sistema, clave, origen):
        grupos: dict[str, list[dict]] = {}
        for f in _features(geo_dir, archivo):
            p = f["properties"]
            cod = str(p.get(clave) or p.get("sistema") or "").strip()
            grupos.setdefault(cod, []).append(f)
        for cod, fs in grupos.items():
            k = (sistema, cod)
            if k not in rutas:
                continue  # trazado sin paraderos: no se publica
            p0 = fs[0]["properties"]
            rutas[k]["trazado"] = _multilinea(fs)
            rutas[k]["color_hex"] = rutas[k]["color_hex"] or p0.get("color_hex")
            rutas[k]["nota"] = p0.get("nota") or None
            rutas[k]["origen_trazado"] = origen

    agrupar("trazado_metro_l1", "metro_l1", "sistema", "shapefile_atu")
    agrupar("trazado_troncal", "troncal", "sistema", "osm_relation")
    agrupar("trazados_corredores", "corredor", "ruta", "derivado_osrm")
    agrupar("trazados_alimentadores_atu", "alimentador", "ruta", "derivado_osrm")
    agrupar("trazados_metropolitano_servicios", "troncal", "servicio_slug", "osm_relation")

    con_sentido = {(pk, rk) for (pk, rk, d) in enlaces if d}
    enlaces = {k: v for k, v in enlaces.items() if k[2] or (k[0], k[1]) not in con_sentido}
    return {"paraderos": paraderos, "rutas": rutas, "enlaces": enlaces, "avisos": sin_enlace}


def _unidades_modelo(conn) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {s: {} for s in SISTEMAS}
    try:
        filas = conn.execute("SELECT DISTINCT sistema, unidad FROM demanda_fiable").fetchall()
    except Exception:  # vista aun no creada
        return out
    for f in filas:
        out.setdefault(f["sistema"], {})[norm(f["unidad"])] = f["unidad"]
    return out


def cargar(conn, geo_dir: Path | None = None) -> dict:
    geo_dir = Path(geo_dir or config.GEO_DIR)
    if not geo_dir.exists():
        raise FileNotFoundError(
            f"no existe {geo_dir}: genera los GeoJSON con scripts/build_trazados.py "
            "o define GEO_DIR"
        )
    datos = construir(geo_dir, _unidades_modelo(conn))
    with conn.transaction():
        conn.execute("TRUNCATE paradero_ruta, paradero, ruta RESTART IDENTITY CASCADE")
        ids_p, ids_r = {}, {}
        for k, p in datos["paraderos"].items():
            ids_p[k] = conn.execute(
                "INSERT INTO paradero (sistema, codigo, nombre, lat, lon, calidad_coord, confianza, "
                "precision_coord, evidencia) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (p["sistema"], p["codigo"], p["nombre"], p["lat"], p["lon"], p["calidad_coord"],
                 p.get("confianza"), p.get("precision_coord"), p.get("evidencia")),
            ).fetchone()["id"]
        for k, r in datos["rutas"].items():
            ids_r[k] = conn.execute(
                "INSERT INTO ruta (sistema, codigo, nombre, color_hex, trazado, nota, "
                "origen_trazado) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (r["sistema"], r["codigo"], r["nombre"], r["color_hex"],
                 Jsonb(r["trazado"]) if r["trazado"] else None, r["nota"],
                 r["origen_trazado"] if r["trazado"] else None),
            ).fetchone()["id"]
        # porcentaje de paradas con precision 'exacta' por ruta (solo donde se evalua: alimentadores)
        tot_r: dict = {}
        for (pk, rk, _d), _e in datos["enlaces"].items():
            pc = datos["paraderos"][pk].get("precision_coord")
            if pc:
                t = tot_r.setdefault(rk, [0, 0])
                t[1] += 1
                t[0] += pc == "exacta"
        for rk, (ex, n) in tot_r.items():
            conn.execute("UPDATE ruta SET n_paradas = %s, pct_exactas = %s WHERE id = %s",
                         (n, round(100 * ex / n), ids_r[rk]))
        for (pk, rk, direccion), e in datos["enlaces"].items():
            conn.execute(
                "INSERT INTO paradero_ruta (paradero_id, ruta_id, direccion, orden, unidad_modelo) "
                "VALUES (%s,%s,%s,%s,%s)",
                (ids_p[pk], ids_r[rk], direccion, e["orden"], e["unidad_modelo"]),
            )
    resumen = {
        "paraderos": len(datos["paraderos"]), "rutas": len(datos["rutas"]),
        "enlaces": len(datos["enlaces"]),
        "con_unidad_modelo": sum(1 for e in datos["enlaces"].values() if e["unidad_modelo"]),
        "rutas_con_trazado": sum(1 for r in datos["rutas"].values() if r["trazado"]),
        **datos["avisos"],
    }
    return resumen


def main() -> None:
    from storage import db

    conn = db.connect()
    try:
        r = cargar(conn)
    finally:
        conn.close()
    print("[paraderos] " + ", ".join(f"{k}={v}" for k, v in r.items()))


if __name__ == "__main__":
    main()
