"""Coordenadas de paradas de alimentadores desde Google Places (Text Search, API nueva).

UNA sola ingesta: cada consulta queda en `data/fuentes/google_paraderos.csv` (que sirve de cache y
de entrega para el resto del equipo). Una consulta ya registrada NO se vuelve a pagar.

Requiere GOOGLE_MAPS_API_KEY en el .env y facturacion activa en Google Cloud (el cupo gratuito
es por SKU y mensual; revisarlo en la consola). Fija un tope de llamadas con --max-llamadas.

    python scripts/consultar_google_paraderos.py --dry-run          # cuantas consultas serian
    python scripts/consultar_google_paraderos.py --max-llamadas 800  # ejecuta
    python scripts/consultar_google_paraderos.py --validar 100       # error vs GPS oficial de ATU

AVISO: los terminos de Google Maps Platform limitan cuanto tiempo se pueden conservar las
coordenadas obtenidas y su uso fuera de un mapa de Google. Esta salida es para el prototipo del
curso; antes de producir hay que reemplazarla (datos oficiales de ATU) o cumplir esos terminos.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

CODEDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODEDIR))
import geocodificar_alimentadores as GA  # noqa: E402

FUENTES = GA.FUENTES
SALIDA = FUENTES / "google_paraderos.csv"
URL = "https://places.googleapis.com/v1/places:searchText"
CAMPOS = "places.id,places.displayName,places.location,places.types,places.formattedAddress"
TIPOS_PARADA = {"bus_stop", "transit_stop", "bus_station", "transit_station", "light_rail_station", "subway_station"}
LIMA = (-12.0464, -77.0428)
COLUMNAS = ["servicio", "consulta", "rank", "place_id", "nombre_google", "lat", "lon", "tipos",
            "direccion", "fuente", "fecha_consulta"]


def _env(clave: str) -> str | None:
    if os.getenv(clave):
        return os.getenv(clave)
    p = CODEDIR.parents[3] / ".env"
    if p.exists():
        for linea in p.read_text(encoding="utf-8").splitlines():
            if linea.startswith(clave + "="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def buscar(texto: str, centro: tuple[float, float], key: str, radio_m: float = 6000.0) -> list[dict]:
    cuerpo = {"textQuery": f"{texto} paradero, Lima, Perú", "languageCode": "es", "regionCode": "PE",
              "maxResultCount": 5,
              "locationBias": {"circle": {"center": {"latitude": centro[0], "longitude": centro[1]},
                                          "radius": radio_m}}}
    req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode(), method="POST", headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": CAMPOS})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("places", [])
    except urllib.error.HTTPError as e:      # mostrar el motivo que da Google (sin la clave)
        try:
            err = json.loads(e.read().decode()).get("error", {})
        except Exception:  # noqa: BLE001
            err = {}
        motivos = [d.get("reason") for d in err.get("details", []) if d.get("reason")]
        raise RuntimeError(f"HTTP {e.code} {err.get('status', '')}: {err.get('message', '')} "
                           f"{motivos}") from None


def consultas_pendientes() -> list[tuple[str, str, tuple[float, float]]]:
    """(servicio, nombre, centro): centro = mediana de las paradas ya resueltas del servicio."""
    filas = list(csv.DictReader((FUENTES / "alimentadores_paraderos_atu.csv").open(encoding="utf-8")))
    ocr = FUENTES / "alimentadores_paraderos_ocr.csv"
    if ocr.exists():
        filas += list(csv.DictReader(ocr.open(encoding="utf-8")))
    centros: dict[str, tuple[float, float]] = {}
    geo = FUENTES / "alimentadores_paradas_geo.csv"
    if geo.exists():
        por: dict[str, list] = {}
        for r in csv.DictReader(geo.open(encoding="utf-8")):
            if r["lat"]:
                por.setdefault(r["servicio"], []).append((float(r["lat"]), float(r["lon"])))
        centros = {s: (float(np.median([p[0] for p in v])), float(np.median([p[1] for p in v])))
                   for s, v in por.items()}
    hechas = set()
    if SALIDA.exists():
        hechas = {(r["servicio"], r["consulta"]) for r in csv.DictReader(SALIDA.open(encoding="utf-8"))}
    out, vistos = [], set()
    for r in filas:
        sid = f"{r['grupo'].replace('Alimentadores', '')}/{r['servicio']}"
        for v in GA._variantes_nombre(r["paradero"])[:1]:
            k = (sid, GA.norm(v))
            if not k[1] or k in vistos or k in hechas:
                continue
            vistos.add(k)
            out.append((sid, v, centros.get(sid, LIMA)))
    return out


def ejecutar(max_llamadas: int, pausa: float = 0.1) -> None:
    key = _env("GOOGLE_MAPS_API_KEY")
    if not key:
        raise SystemExit("Falta GOOGLE_MAPS_API_KEY en el .env")
    pend = consultas_pendientes()
    print(f"consultas pendientes: {len(pend)} | tope: {max_llamadas}")
    nuevo = not SALIDA.exists()
    with SALIDA.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        if nuevo:
            w.writeheader()
        for n, (sid, nombre, centro) in enumerate(pend[:max_llamadas], 1):
            try:
                lugares = buscar(nombre, centro, key)
            except Exception as e:  # noqa: BLE001 - se registra y se sigue
                print(f"  [aviso] {sid} / {nombre}: {type(e).__name__}: {e}")
                continue
            fecha = dt.date.today().isoformat()
            if not lugares:
                w.writerow({"servicio": sid, "consulta": GA.norm(nombre), "rank": 0, "fuente": "google_places",
                            "fecha_consulta": fecha})
            for rk, p in enumerate(lugares, 1):
                loc = p.get("location", {})
                w.writerow({"servicio": sid, "consulta": GA.norm(nombre), "rank": rk, "place_id": p.get("id", ""),
                            "nombre_google": p.get("displayName", {}).get("text", ""),
                            "lat": loc.get("latitude", ""), "lon": loc.get("longitude", ""),
                            "tipos": "|".join(p.get("types", [])), "direccion": p.get("formattedAddress", ""),
                            "fuente": "google_places", "fecha_consulta": fecha})
            fh.flush()
            if n % 50 == 0:
                print(f"  {n}/{min(len(pend), max_llamadas)}")
            time.sleep(pausa)
    print(f"listo: {SALIDA}")


CERCANOS = FUENTES / "google_cercanos.csv"
URL_CERCA = "https://places.googleapis.com/v1/places:searchNearby"
COLS_CERCA = ["servicio", "centro_lat", "centro_lon", "rank", "place_id", "nombre_google", "lat", "lon",
              "tipos", "dist_m", "fecha_consulta"]
RADIO_CERCA_M = 100.0


def _post(url: str, cuerpo: dict, key: str) -> dict:
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode(), method="POST", headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": CAMPOS})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
        except Exception:  # noqa: BLE001
            err = {}
        raise RuntimeError(f"HTTP {e.code} {err.get('status', '')}: {err.get('message', '')}") from None


def buscar_variante(texto: str, centro: tuple[float, float], key: str, radio_m: float = 6000.0) -> list[dict]:
    """Variante B: sin la palabra 'paradero' y con filtro estricto de tipo parada de bus."""
    cuerpo = {"textQuery": f"{texto}, Lima", "languageCode": "es", "regionCode": "PE", "maxResultCount": 5,
              "includedType": "bus_stop", "strictTypeFiltering": True,
              "locationBias": {"circle": {"center": {"latitude": centro[0], "longitude": centro[1]},
                                          "radius": radio_m}}}
    return _post(URL, cuerpo, key).get("places", [])


def buscar_cercanos(centro: tuple[float, float], key: str, radio_m: float = RADIO_CERCA_M) -> list[dict]:
    cuerpo = {"includedTypes": ["bus_stop", "transit_station", "bus_station"], "maxResultCount": 5,
              "rankPreference": "DISTANCE", "languageCode": "es",
              "locationRestriction": {"circle": {"center": {"latitude": centro[0], "longitude": centro[1]},
                                                 "radius": radio_m}}}
    return _post(URL_CERCA, cuerpo, key).get("places", [])


def _estado_actual() -> list[dict]:
    return list(csv.DictReader((FUENTES / "alimentadores_paradas_geo.csv").open(encoding="utf-8")))


def pendientes_completar() -> tuple[list, list]:
    """(texto_variante_B, cercanos): paradas sin coincidencia de nombre a <= 50 m en Google."""
    g = cargar_google()
    hechas_b = set()
    if SALIDA.exists():
        hechas_b = {(r["servicio"], r["consulta"]) for r in csv.DictReader(SALIDA.open(encoding="utf-8"))
                    if r.get("fuente") == "google_places_b"}
    hechas_c = set()
    if CERCANOS.exists():
        hechas_c = {(round(float(r["centro_lat"]), 5), round(float(r["centro_lon"]), 5))
                    for r in csv.DictReader(CERCANOS.open(encoding="utf-8"))}
    centros: dict[str, tuple[float, float]] = {}
    por: dict[str, list] = {}
    for r in _estado_actual():
        if r["lat"]:
            por.setdefault(r["servicio"], []).append((float(r["lat"]), float(r["lon"])))
    centros = {k: (float(np.median([p[0] for p in v])), float(np.median([p[1] for p in v]))) for k, v in por.items()}
    textos, cerca, vistos_t, vistos_c = [], [], set(), set()
    for r in _estado_actual():
        sid = r["servicio"]
        nombre = GA._variantes_nombre(r["paradero"])[0]
        k = (sid, GA.norm(nombre))
        ours = (float(r["lat"]), float(r["lon"])) if r["lat"] else None
        if ours and any(GA.dist_m(c, ours) <= 50 for c in g.get(k, [])):
            continue                                       # ya coincide por nombre
        if k not in hechas_b and k not in vistos_t and k[1]:
            vistos_t.add(k)
            textos.append((sid, nombre, centros.get(sid, LIMA)))
        if ours:
            kc = (round(ours[0], 5), round(ours[1], 5))
            if kc not in hechas_c and kc not in vistos_c:
                vistos_c.add(kc)
                cerca.append((sid, ours))
    return textos, cerca


def completar(max_llamadas: int, pausa: float = 0.1) -> None:
    key = _env("GOOGLE_MAPS_API_KEY")
    if not key:
        raise SystemExit("Falta GOOGLE_MAPS_API_KEY en el .env")
    textos, cerca = pendientes_completar()
    print(f"texto (variante B): {len(textos)} | cercanos: {len(cerca)} | tope: {max_llamadas}")
    usadas = 0
    fecha = dt.date.today().isoformat()
    nuevo = not SALIDA.exists()
    with SALIDA.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        if nuevo:
            w.writeheader()
        for sid, nombre, centro in textos:
            if usadas >= max_llamadas:
                break
            usadas += 1
            try:
                lugares = buscar_variante(nombre, centro, key)
            except Exception as e:  # noqa: BLE001
                print(f"  [aviso] {sid}/{nombre}: {e}")
                continue
            if not lugares:
                w.writerow({"servicio": sid, "consulta": GA.norm(nombre), "rank": 0, "fuente": "google_places_b",
                            "fecha_consulta": fecha})
            for rk, p in enumerate(lugares, 1):
                loc = p.get("location", {})
                w.writerow({"servicio": sid, "consulta": GA.norm(nombre), "rank": rk, "place_id": p.get("id", ""),
                            "nombre_google": p.get("displayName", {}).get("text", ""),
                            "lat": loc.get("latitude", ""), "lon": loc.get("longitude", ""),
                            "tipos": "|".join(p.get("types", [])), "direccion": p.get("formattedAddress", ""),
                            "fuente": "google_places_b", "fecha_consulta": fecha})
            fh.flush()
            time.sleep(pausa)
    nuevo = not CERCANOS.exists()
    with CERCANOS.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS_CERCA)
        if nuevo:
            w.writeheader()
        for sid, c in cerca:
            if usadas >= max_llamadas:
                break
            usadas += 1
            try:
                lugares = buscar_cercanos(c, key)
            except Exception as e:  # noqa: BLE001
                print(f"  [aviso] cercanos {c}: {e}")
                continue
            base = {"servicio": sid, "centro_lat": c[0], "centro_lon": c[1], "fecha_consulta": fecha}
            if not lugares:
                w.writerow({**base, "rank": 0})
            for rk, p in enumerate(lugares, 1):
                loc = p.get("location", {})
                d = GA.dist_m((loc.get("latitude"), loc.get("longitude")), c) if loc else ""
                w.writerow({**base, "rank": rk, "place_id": p.get("id", ""),
                            "nombre_google": p.get("displayName", {}).get("text", ""),
                            "lat": loc.get("latitude", ""), "lon": loc.get("longitude", ""),
                            "tipos": "|".join(p.get("types", [])), "dist_m": round(d) if d != "" else ""})
            fh.flush()
            time.sleep(pausa)
            if usadas % 50 == 0:
                print(f"  llamadas: {usadas}")
    print(f"listo: {usadas} llamadas")


def cargar_google() -> dict[tuple[str, str], list[tuple[float, float]]]:
    """(servicio, nombre normalizado) -> coordenadas de resultados que son paradas."""
    out: dict = {}
    if not SALIDA.exists():
        return out
    for r in csv.DictReader(SALIDA.open(encoding="utf-8")):
        if not r["lat"] or not (set(r["tipos"].split("|")) & TIPOS_PARADA):
            continue
        out.setdefault((r["servicio"], r["consulta"]), []).append((float(r["lat"]), float(r["lon"])))
    return out


def validar(n: int) -> None:
    """Mismos nombres de corredores que ya tienen GPS de ATU: error del primer resultado de Google."""
    key = _env("GOOGLE_MAPS_API_KEY")
    if not key:
        raise SystemExit("Falta GOOGLE_MAPS_API_KEY en el .env")
    fc = json.loads((GA.GEO / "paradas_corredores.geojson").read_text(encoding="utf-8"))["features"]
    rng = np.random.default_rng(0)
    idx = rng.choice(len(fc), size=min(n, len(fc)), replace=False)
    errs, sin, fallos = [], 0, 0
    for i in idx:
        f = fc[int(i)]
        lon, lat = f["geometry"]["coordinates"]
        try:
            lugares = [p for p in buscar(f["properties"]["paradero"], (lat, lon), key, 3000.0)
                       if set(p.get("types", [])) & TIPOS_PARADA]
        except RuntimeError as e:
            fallos += 1
            print(f"  [error {fallos}] {e}")
            if fallos >= 3:
                print("  demasiados errores seguidos: se detiene")
                break
            continue
        if not lugares:
            sin += 1
            continue
        errs.append(min(GA.dist_m((p["location"]["latitude"], p["location"]["longitude"]), (lat, lon))
                        for p in lugares))
        time.sleep(0.1)
    if not errs:
        print("sin resultados validos")
        return
    e = np.array(errs)
    print(f"validacion: {len(idx)} consultas | sin resultado de parada: {sin} | "
          f"error (mejor resultado) mediana={np.median(e):.0f} m p90={np.percentile(e, 90):.0f} m")


def contrastar_oficiales(umbral_m: float = 50.0) -> None:
    """Estaciones del Metropolitano (OSM por nombre) y del Metro L1 (shapefile ATU): se busca cada una
    en Google SIN sesgo hacia nuestra coordenada y se compara. No modifica ninguna coordenada."""
    key = _env("GOOGLE_MAPS_API_KEY")
    if not key:
        raise SystemExit("Falta GOOGLE_MAPS_API_KEY en el .env")
    casos = []
    for sis, arch, plantilla in (("troncal", "puntos_troncal", "Estación {} Metropolitano"),
                                 ("metro_l1", "puntos_metro_l1", "Estación {} Metro de Lima Línea 1")):
        for f in json.loads((GA.GEO / f"{arch}.geojson").read_text(encoding="utf-8"))["features"]:
            nombre = f["properties"].get("estacion") or f["properties"].get("unidad")
            casos.append((sis, nombre, f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0],
                          plantilla.format(nombre)))
    filas = []
    for sis, nombre, lat, lon, consulta in casos:
        try:
            lugares = [p for p in buscar(consulta.replace("Estación Estación", "Estación"), LIMA, key, 30000.0)
                       if set(p.get("types", [])) & TIPOS_PARADA]
        except RuntimeError as e:
            lugares = []
            print(f"  [error] {nombre}: {e}")
        fila = {"sistema": sis, "nombre": nombre, "lat": lat, "lon": lon, "google_nombre": "",
                "google_lat": "", "google_lon": "", "dist_m": "", "tipos": "", "estado": "sin_resultado"}
        if lugares:
            # el primero que da Google (sin sesgo a nuestra coordenada); se informa tambien el mas cercano
            top = lugares[0]
            loc = top["location"]
            d = GA.dist_m((loc["latitude"], loc["longitude"]), (lat, lon))
            cerca = min(GA.dist_m((p["location"]["latitude"], p["location"]["longitude"]), (lat, lon))
                        for p in lugares)
            fila.update({"google_nombre": top.get("displayName", {}).get("text", ""),
                         "google_lat": loc["latitude"], "google_lon": loc["longitude"],
                         "dist_m": round(d), "tipos": "|".join(top.get("types", [])),
                         "estado": "ok" if d <= umbral_m else ("ok_otro_resultado" if cerca <= umbral_m
                                                                  else "revisar")})
        filas.append(fila)
        time.sleep(0.1)
    out = FUENTES / "contraste_google_oficiales.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    for sis in ("troncal", "metro_l1"):
        L = [f for f in filas if f["sistema"] == sis]
        c = {k: sum(1 for f in L if f["estado"] == k) for k in ("ok", "ok_otro_resultado", "revisar", "sin_resultado")}
        d = np.array([f["dist_m"] for f in L if f["dist_m"] != ""], float)
        print(f"{sis}: {len(L)} estaciones | {c} | distancia mediana {np.median(d):.0f} m" if len(d) else f"{sis}: {c}")
    print("A revisar:")
    for f in filas:
        if f["estado"] in ("revisar", "sin_resultado"):
            print(f"  [{f['sistema']}] {f['nombre']}: {f['estado']} | Google: {f['google_nombre']!r} a {f['dist_m']} m")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-llamadas", type=int, default=800)
    ap.add_argument("--validar", type=int, metavar="N")
    ap.add_argument("--completar", action="store_true",
                    help="busqueda adicional para paradas sin coincidencia: variante B + cercanos")
    ap.add_argument("--contrastar-oficiales", action="store_true",
                    help="compara estaciones de troncal y L1 con Google (~70 consultas)")
    a = ap.parse_args()
    if a.completar and a.dry_run:
        t, c = pendientes_completar()
        print(f"completar: texto variante B = {len(t)} | cercanos = {len(c)} | total {len(t) + len(c)}")
    elif a.completar:
        completar(a.max_llamadas)
    elif a.contrastar_oficiales:
        contrastar_oficiales()
    elif a.validar:
        validar(a.validar)
    elif a.dry_run:
        p = consultas_pendientes()
        print(f"consultas que se harian: {len(p)} (tope {a.max_llamadas}); "
              f"ya registradas se omiten. Servicios: {len({x[0] for x in p})}")
    else:
        ejecutar(a.max_llamadas)


if __name__ == "__main__":
    main()
