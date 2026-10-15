"""Genera el material de revision humana de paradas y rutas.

Salida en deliveries/week10/docs/visor/:
  mapa_revision.html      visor interactivo (Leaflet): ver paradas, rutas y su precision; correccion opcional
  revision_paradas.csv    solo con --csv (la entrega de datos es export/paraderos.csv)
Las correcciones se exportan desde el mapa a `correcciones_paradas.csv`, se guardan en
data/fuentes/ y se aplican con `geocodificar_alimentadores.py`.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from urllib.parse import quote

CODEDIR = Path(__file__).resolve().parent
RAIZ = CODEDIR.parents[2]
FUENTES = RAIZ / "data" / "fuentes"
GEO = FUENTES / "geo"
GEOJSON = RAIZ / "data_processed" / "geo"
OUT = RAIZ / "docs" / "visor"
PRIO = {"": 0, "baja": 1, "media": 2, "alta": 3, "verificada": 4, None: 0}


def _fc(nombre: str) -> list[dict]:
    p = GEOJSON / f"{nombre}.geojson"
    return json.loads(p.read_text(encoding="utf-8"))["features"] if p.exists() else []


def _lineas(feats: list[dict], clave: str) -> dict[str, list]:
    out: dict[str, list] = {}
    for f in feats:
        k = str(f["properties"].get(clave) or f["properties"].get("sistema") or "")
        g = f["geometry"]
        partes = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        out.setdefault(k, []).extend([[[c[1], c[0]] for c in parte] for parte in partes])
    return out


def _nombre_norm(x: str) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", str(x or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()
    return {"canavaly moreyra": "canaval y moreyra", "plaza flores": "plaza de flores",
            "dos mayo": "2 de mayo", "28julio": "28 de julio", "estacion central": "central"}.get(t, t)


def construir() -> dict:
    datos: dict = {}

    # alimentadores (coordenada inferida: editables)
    tr = _lineas(_fc("trazados_alimentadores_atu"), "ruta")
    alim: dict = {}
    for r in csv.DictReader((FUENTES / "alimentadores_paradas_geo.csv").open(encoding="utf-8")):
        d = alim.setdefault(r["servicio"], {"codigo": r["codigo"], "grupo": r["grupo"],
                                            "trazado": tr.get(r["servicio"], []), "paradas": []})
        d["paradas"].append({
            "bloque": int(r["bloque"]), "orden": int(r["orden"]), "nombre": r["paradero"],
            "lat": float(r["lat"]) if r["lat"] else None, "lon": float(r["lon"]) if r["lon"] else None,
            "confianza": r["confianza"] or "sin", "metodo": r["metodo"],
            "n_cand": int(r["n_candidatos"] or 0), "precision": r.get("precision", ""),
            "evidencia": r.get("evidencia", "")})
    # nombre de cada sentido: "tramo" de los horarios de la pagina (ida primero, luego vuelta)
    tramos: dict[tuple, list[str]] = {}
    h = FUENTES / "alimentadores_horarios_atu.csv"
    if h.exists():
        for r in csv.DictReader(h.open(encoding="utf-8")):
            t = tramos.setdefault((r["grupo"], r["servicio"]), [])
            if r["tramo"] and r["tramo"] not in t:
                t.append(r["tramo"])
    for sid, d in alim.items():
        ts = tramos.get((d["grupo"], sid.split("/")[-1]), [])
        nb = len({p["bloque"] for p in d["paradas"]})
        d["sentidos"] = {str(i + 1): ts[i] for i in range(nb)} if len(ts) == nb else {}
    # contraste con Google (consultas ya guardadas, sin costo): candidato mas cercano a nuestra coordenada
    try:
        import geocodificar_alimentadores as GA
        from consultar_google_paraderos import cargar_google
        google = cargar_google()
        for sid, d in alim.items():
            for p in d["paradas"]:
                cand = google.get((sid, GA.norm(GA._variantes_nombre(p["nombre"])[0])), [])
                p["g_lat"] = p["g_lon"] = p["g_dist"] = None
                if not cand:
                    continue
                if p["lat"] is not None:
                    c = min(cand, key=lambda x: GA.dist_m(x, (p["lat"], p["lon"])))
                    p["g_dist"] = round(GA.dist_m(c, (p["lat"], p["lon"])))
                else:
                    c = cand[0]
                p["g_lat"], p["g_lon"] = c
    except Exception as e:  # noqa: BLE001 - la revision funciona sin el contraste
        print(f"  [aviso] sin contraste con Google: {e}")
    # tercera opinion: interpolacion por imagen entre anclas (error esperado ~170 m, ver interpolar_por_imagen.py)
    try:
        import interpolar_por_imagen as I
        import numpy as np
        interp = {}
        for (grupo, serv), bl in I.por_servicio(I.cargar_estado()).items():
            pngs = I.mapa_principal(grupo, serv)
            if not pngs:
                continue
            pxa = I.leer_marcadores(pngs[0])
            for b, L in bl.items():
                px = {n: xy for (bb, n), xy in pxa.items() if bb == b}
                anclas = {int(r["orden"]): (float(r["lat"]), float(r["lon"])) for r in L if I._es_ancla(r)}
                for r in L:
                    o = int(r["orden"])
                    res = I.interpolar(px, {k: v for k, v in anclas.items() if k != o}, o)
                    if res:
                        interp[(r["servicio"], b, o)] = (res[0], res[1])
        for sid, d in alim.items():
            for p in d["paradas"]:
                i = interp.get((sid, p["bloque"], p["orden"]))
                p["i_lat"], p["i_lon"] = (i if i else (None, None))
                p["i_dist"] = (round(GA.dist_m(i, (p["lat"], p["lon"]))) if i and p["lat"] is not None else None)
                # consenso entre nuestro punto (N), Google (G) e imagen (I)
                n_ = (p["lat"], p["lon"]) if p["lat"] is not None else None
                g_ = (p["g_lat"], p["g_lon"]) if p.get("g_lat") is not None else None
                v = "sin_consenso"
                if n_ and g_ and GA.dist_m(n_, g_) <= 100:
                    v = "nuestro_y_google"
                elif g_ and i and GA.dist_m(g_, i) <= 150:
                    v = "google_e_imagen"
                elif n_ and i and GA.dist_m(n_, i) <= 150:
                    v = "nuestro_e_imagen"
                elif not n_ and not g_ and not i:
                    v = "sin_datos"
                p["consenso"] = v
        print(f"  interpolacion por imagen: {len(interp)} paradas")
    except Exception as e:  # noqa: BLE001
        print(f"  [aviso] sin interpolacion por imagen: {e}")
    datos["alimentador"] = {"editable": True, "servicios": alim}

    # corredores: GPS oficial de ATU (solo lectura)
    tr = _lineas(_fc("trazados_corredores"), "ruta")
    cor: dict = {}
    for f in _fc("paradas_corredores"):
        p = f["properties"]
        d = cor.setdefault(p["ruta"], {"codigo": p["ruta"], "grupo": "Corredor",
                                       "trazado": tr.get(p["ruta"], []), "paradas": []})
        d["paradas"].append({"bloque": int(p["direccion"]), "orden": int(p["orden"]),
                             "nombre": p["paradero"], "lat": f["geometry"]["coordinates"][1],
                             "lon": f["geometry"]["coordinates"][0], "confianza": "oficial",
                             "metodo": "gps_atu", "n_cand": 1})
    datos["corredor"] = {"editable": False, "servicios": cor}

    # servicios del Metropolitano (estaciones OSM por nombre) y L1 (shapefile)
    tr = _lineas(_fc("trazados_metropolitano_servicios"), "servicio_slug")
    tro: dict = {}
    estado_est: dict[str, dict] = {}
    for f in _fc("puntos_troncal"):
        estado_est[_nombre_norm(f["properties"]["estacion"])] = f["properties"]
    for f in _fc("puntos_metropolitano_servicios"):
        p = f["properties"]
        est = estado_est.get(_nombre_norm(p["estacion"]), {})
        lejos = est.get("dist_a_troncal_m", 0) > 150 and est.get("match") not in ("google", "manual")
        origen = {"google": "google_places (corregida)", "manual": "revision_humana"}.get(
            est.get("match"), "osm_nombre")
        d = tro.setdefault(p["servicio_slug"], {"codigo": p["servicio_slug"], "grupo": "Metropolitano",
                                                "trazado": tr.get(p["servicio_slug"], []), "paradas": []})
        d["paradas"].append({"bloque": 1, "orden": int(p["orden"]), "nombre": p["estacion"],
                             "lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0],
                             "confianza": "baja" if lejos else ("verificada" if est.get("match") == "manual" else "media"),
                             "metodo": (f"osm_nombre: a {est.get('dist_a_troncal_m')} m de la linea troncal"
                                        if lejos else origen), "n_cand": 1})
    datos["troncal"] = {"editable": False, "servicios": tro}
    l1 = {"metro_l1": {"codigo": "L1", "grupo": "Metro", "paradas": [], "trazado": []}}
    for i, f in enumerate(_fc("puntos_metro_l1"), 1):
        l1["metro_l1"]["paradas"].append({"bloque": 1, "orden": i, "nombre": f["properties"]["estacion"],
                                          "lat": f["geometry"]["coordinates"][1],
                                          "lon": f["geometry"]["coordinates"][0], "confianza": "oficial",
                                          "metodo": "shapefile_atu", "n_cand": 1})
    for ls in _lineas(_fc("trazado_metro_l1"), "sistema").values():
        l1["metro_l1"]["trazado"].extend(ls)
    datos["metro_l1"] = {"editable": False, "servicios": l1}
    return datos


def enlaces(lat, lon) -> tuple[str, str]:
    if lat is None:
        return "", ""
    return (f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
            f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    datos = construir()
    filas = []
    for sis, bloque in datos.items():
        for serv, d in bloque["servicios"].items():
            if sis not in ("alimentador", "troncal"):
                continue                      # corredor/L1 son oficiales: solo visual
            for p in d["paradas"]:
                g, o = enlaces(p["lat"], p["lon"])
                filas.append({"prioridad": PRIO.get(p["confianza"], 0) if p["confianza"] != "sin" else -1,
                              "sistema": sis, "servicio": serv, "codigo": d["codigo"], "bloque": p["bloque"],
                              "orden": p["orden"], "paradero": p["nombre"], "lat": p["lat"] or "",
                              "lon": p["lon"] or "", "confianza": p["confianza"], "metodo": p["metodo"],
                              "n_candidatos": p["n_cand"], "google_dist_m": p.get("g_dist") if p.get("g_dist") is not None else "",
                              "precision": p.get("precision", ""), "evidencia": p.get("evidencia", ""),
                              "interp_dist_m": p.get("i_dist") if p.get("i_dist") is not None else "",
                              "consenso": p.get("consenso", ""),
                              "google_maps": g, "osm": o,
                              "estado": "", "lat_corregida": "", "lon_corregida": "", "comentario": ""})
    filas.sort(key=lambda r: (r["prioridad"], r["sistema"], r["servicio"], r["bloque"], r["orden"]))
    if "--csv" in sys.argv:                  # el CSV consolidado vive en export/paraderos.csv
        with (OUT / "revision_paradas.csv").open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
    plantilla = (CODEDIR / "plantilla_revision.html").read_text(encoding="utf-8")
    html = plantilla.replace("/*__DATOS__*/null", json.dumps(datos, ensure_ascii=False))
    (OUT / "mapa_revision.html").write_text(html, encoding="utf-8")
    sin = sum(1 for f in filas if f["confianza"] == "sin")
    print(f"paradas revisables: {len(filas)} ({sin} sin coordenada)")
    print(f"mapa_revision.html: {sum(len(v['servicios']) for v in datos.values())} servicios")


if __name__ == "__main__":
    main()
