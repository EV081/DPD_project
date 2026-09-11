import argparse
import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

CAMPOS_GEO = ["Latitud", "Longitud", "Ubicacion", "Troncal", "Fase", "Cap_ART", "Cap_BIART"]
CAMPOS_OFERTA = ["Frecuencia", "Headway_Min", "N_Rutas"]

# Estaciones sin coordenadas en el geojson -> estacion GTFS mas representativa.
# Corrales = depositos de buses -> se usa la estacion asociada como proxy.
MAPA_GTFS = {
    "02305": "2000",   # Bicicletero Portal Norte -> Portal Norte
    "04004": "4004",   # La Granja
    "08100": "8000",   # Portal Tunal Cable -> Portal Tunal
    "09125": "9119",   # Temporal Calle 57
    "09126": "9118",   # Temporal Marly
    "09127": "9121",   # Temporal Flores
    "09128": "9110",   # Temporal AV Jimenez - Inter Electricas
    "09129": "9113",   # Temporal Calle 22
    "09130": "9116",   # Temporal Avenida 39
    "15001": "90009",  # Tibanica - Primavera
    "15002": "90010",  # Los Laureles
    "15003": "90011",  # Islandia
    "50003": "9001",   # Corral Molinos -> Molinos
    "50006": "4004",   # Corral Carrera 77 -> Granja Cra 77
    "50008": "6000",   # Corral Portal Dorado -> Portal El Dorado
    "57503": "57503",  # Embajada de Paz de Colombia (codigo exacto)
}


def extraer_hora(fecha_hora: str, ancho: int) -> str:
    return fecha_hora[11:11 + ancho]


def procesar_csv(fileobj, agregado: defaultdict, ancho: int) -> None:
    reader = csv.DictReader(fileobj)
    for fila in reader:
        estacion = fila.get("Estacion_Parada") or ""
        fecha_hora = fila.get("Fecha_Transaccion") or ""
        linea = fila.get("Linea") or ""
        tipo_dia = fila.get("Day_Group_Type") or ""
        sistema = fila.get("Sistema") or ""
        if sistema and sistema.strip().upper() != "TRONCAL":
            continue
        if not estacion.strip():
            continue
        fecha = fecha_hora[:10]
        hora = extraer_hora(fecha_hora, ancho)
        if not fecha or not hora:
            continue
        clave = (estacion, fecha, hora, linea, tipo_dia)
        agregado[clave] += 1


def procesar_zip(ruta_zip: Path, agregado: defaultdict, ancho: int) -> None:
    with zipfile.ZipFile(ruta_zip) as z:
        for nombre in z.namelist():
            if nombre.lower().endswith((".csv", ".txt")):
                print(f"    procesando {nombre} ...")
                with z.open(nombre) as f:
                    texto = io.TextIOWrapper(f, encoding="utf-8")
                    procesar_csv(texto, agregado, ancho)
                return


def cargar_estaciones(ruta_geojson: Path, ruta_trazados: Path = None) -> dict:
    trazados = {}
    if ruta_trazados and ruta_trazados.exists():
        with open(ruta_trazados, encoding="utf-8") as f:
            gjt = json.load(f)
        for feat in gjt.get("features", []):
            props = feat.get("properties", {})
            tz = props.get("id_trazado")
            if tz:
                trazados[tz] = {
                    "nom_troncal": props.get("nom_tronc"),
                    "fase": props.get("fase_tronc"),
                    "long_traz": props.get("long_traz"),
                }

    with open(ruta_geojson, encoding="utf-8") as f:
        gj = json.load(f)
    estaciones = {}
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        nombre = props.get("nom_est") or props.get("name") or ""
        if not nombre:
            continue
        geom = feat.get("geometry", {})
        datos = {
            "lat": geom["coordinates"][1] if geom.get("type") == "Point" else "",
            "lon": geom["coordinates"][0] if geom.get("type") == "Point" else "",
            "num_est": props.get("num_est"),
            "cod_nodo": props.get("cod_nodo"),
            "id_trazado": props.get("id_trazado"),
            "ub_est": props.get("ub_est"),
            "nom_troncal": props.get("nom_tronc"),
            "fase": props.get("fase_tronc"),
            "cap_art": props.get("cap_art"),
            "cap_biart": props.get("cap_biart"),
        }
        # Completar troncal/fase desde los trazados
        tz = props.get("id_trazado")
        if tz and tz in trazados:
            datos["nom_troncal"] = datos["nom_troncal"] or trazados[tz]["nom_troncal"]
            datos["fase"] = datos["fase"] or trazados[tz]["fase"]
        estaciones[nombre] = datos
        if props.get("num_est"):
            estaciones[f"({props.get('num_est')}) {nombre}"] = datos
            try:
                estaciones[int(props["num_est"])] = datos
            except (TypeError, ValueError):
                pass
    return estaciones


def _codigo_estacion(nombre: str):
    m = re.match(r"\s*\((\d+)\)", nombre)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _info_estacion(estaciones: dict, estacion: str) -> dict:
    if not estaciones:
        return {}
    for clave in (estacion, estacion.replace(" ", ""), estacion.strip()):
        info = estaciones.get(clave)
        if info:
            return info
    cod = _codigo_estacion(estacion)
    if cod is not None and cod in estaciones:
        return estaciones[cod]
    return {}


def _en_rango(fecha8: str, desde: str, hasta: str) -> bool:
    if not fecha8:
        return True
    if desde and fecha8 < desde.replace("-", ""):
        return False
    if hasta and fecha8 > hasta.replace("-", ""):
        return False
    return True


# GTFS (oferta + coordenadas por codigo/andén)
def _leer_gtfs(ruta: Path) -> dict:
    print(f"  leyendo GTFS {ruta.name} ...")
    with zipfile.ZipFile(ruta) as z:
        nombres = set(z.namelist())

        stops = {}
        if "stops.txt" in nombres:
            with z.open("stops.txt") as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                    stops[row["stop_id"]] = {
                        "name": row.get("stop_name", ""),
                        "lat": float(row.get("stop_lat", "") or 0),
                        "lon": float(row.get("stop_lon", "") or 0),
                        "type": row.get("location_type", "0"),
                        "parent": row.get("parent_station", ""),
                    }

        # estaciones GTFS (location_type == 1)
        estaciones_gtfs = {sid: v for sid, v in stops.items() if v["type"] == "1"}

        # andenes (type 0) cuyo parent es una estacion GTFS
        andenes = {
            sid: v for sid, v in stops.items()
            if v["type"] == "0" and v["parent"] in estaciones_gtfs
        }
        anden_a_estacion = {sid: v["parent"] for sid, v in andenes.items()}

        # servicios activos por fecha (calendar.txt + calendar_dates.txt)
        servicios = {}
        if "calendar.txt" in nombres:
            with z.open("calendar.txt") as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                    dias = {d for d, campo in zip(
                        range(7), ["monday", "tuesday", "wednesday", "thursday",
                                   "friday", "saturday", "sunday"]
                    ) if row.get(campo) == "1"}
                    servicios[row["service_id"]] = {
                        "dias": dias,
                        "inicio": row.get("start_date", ""),
                        "fin": row.get("end_date", ""),
                    }
        excepciones = defaultdict(lambda: {"anade": set(), "quita": set()})
        if "calendar_dates.txt" in nombres:
            with z.open("calendar_dates.txt") as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                    if row.get("exception_type") == "1":
                        excepciones[row["date"]]["anade"].add(row["service_id"])
                    else:
                        excepciones[row["date"]]["quita"].add(row["service_id"])

        # trips -> (ruta, servicio)
        trips = {}
        if "trips.txt" in nombres:
            with z.open("trips.txt") as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                    trips[row["trip_id"]] = (row.get("route_id", ""), row.get("service_id", ""))

        # stop_times: por estacion, hora, servicio, trips, rutas
        por_estacion = defaultdict(lambda: defaultdict(
            lambda: defaultdict(lambda: [set(), set()])))
        if "stop_times.txt" in nombres:
            archivo = z.open("stop_times.txt")
            titulos = {}
            fichero_lector = io.TextIOWrapper(archivo, encoding="utf-8")
            primera = fichero_lector.readline()
            titulos = {
                nombre: i for i, nombre in enumerate(
                    primera.strip().split(","))
            }
            i_trip = titulos["trip_id"]
            i_hora = titulos["arrival_time"]
            i_stop = titulos["stop_id"]
            for linea in fichero_lector:
                partes = linea.split(",")
                stop_id = partes[i_stop]
                estacion_gid = anden_a_estacion.get(stop_id)
                if estacion_gid is None:
                    continue
                trip_id = partes[i_trip]
                tr = trips.get(trip_id)
                if tr is None:
                    continue
                ruta, servicio = tr
                if servicio not in servicios:
                    continue
                hora = partes[i_hora][:2]
                celdas = por_estacion[estacion_gid][hora]
                celdas[servicio][0].add(trip_id)
                celdas[servicio][1].add(ruta)

    todas = dict(stops)
    return {
        "estaciones": estaciones_gtfs,
        "andenes": andenes,
        "anden_a_estacion": anden_a_estacion,
        "todas": todas,  # todos los stops (estaciones + andenes + sueltos)
        "referencia": {sid: v for sid, v in estaciones_gtfs.items()}
                     | {sid: v for sid, v in andenes.items()},
        "servicios": servicios,
        "excepciones": excepciones,
        "por_estacion": por_estacion,
    }


def _servicios_activos_fecha(fecha8: str, gtfs: dict) -> set:
    servicios = gtfs["servicios"]
    activos = set()
    try:
        registro = date(int(fecha8[:4]), int(fecha8[4:6]), int(fecha8[6:8]))
    except ValueError:
        return activos
    wd = registro.weekday()
    for sid, sv in servicios.items():
        if sv["inicio"] and sv["inicio"] > fecha8:
            continue
        if sv["fin"] and sv["fin"] < fecha8:
            continue
        if wd in sv["dias"]:
            activos.add(sid)
    exc = gtfs["excepciones"].get(fecha8)
    if exc:
        activos |= exc["anade"]
        activos -= exc["quita"]
    return activos


def _mapear_num_est(gtfs: dict, estaciones: dict) -> dict:
    mapa = {}
    est_gtfs = gtfs["estaciones"]
    todo = gtfs["todas"]

    # 1) coincidencia por codigo contra todos los stops GTFS
    for stop_id in todo:
        cod5 = stop_id.zfill(5)
        mapa.setdefault(cod5, stop_id)

    # 2) nombre de la estacion GTFS -> num_est conocido (estaciones sin codigo directo)
    nombres_especiales = {
        "islandia": "15003",
        "laureles": "15002",
        "tibanica": "15001",
        "danubio": "09005",
        "portal usme": "09000",
    }
    # num_est que existen en el geojson (para no pisar el match por codigo)
    nums_geojson = set()
    for v in estaciones.values():
        ne = v.get("num_est")
        if ne:
            nums_geojson.add(str(ne).zfill(5))
    for gid, v in est_gtfs.items():
        nombre = re.sub(r"[^a-zA-Z0-9 ]", "", v["name"].lower())
        nombre = re.sub(r"\s+", " ", nombre).strip()
        for clave, num in nombres_especiales.items():
            if clave in nombre and num not in nums_geojson:
                mapa.setdefault(num, gid)

    # 3) mapeo manual (temporales, corrales, etc.)
    for num, gid in MAPA_GTFS.items():
        mapa[num] = gid
    return mapa


def _completar_geo_gtfs(gtfs: dict, estaciones: dict) -> int:
    todo = gtfs["todas"]
    n = 0
    nums_geo = set()
    for v in estaciones.values():
        if str(v.get("lat", "") or "").strip():
            ne = v.get("num_est")
            if ne:
                nums_geo.add(str(ne).zfill(5))
    completadas = {}
    for num, gid in MAPA_GTFS.items():
        st = todo.get(gid)
        if st is None:
            continue
        completadas[num] = st
    for stop_id, st in todo.items():
        cod5 = stop_id.zfill(5)
        if cod5 not in nums_geo and cod5 not in completadas:
            completadas[cod5] = st
    for num, st in completadas.items():
        try:
            clave_int = int(num)
        except ValueError:
            continue
        estaciones[clave_int] = {
            "lat": st["lat"], "lon": st["lon"], "num_est": num,
            "ub_est": "", "nom_troncal": "", "fase": "",
            "cap_art": "", "cap_biart": "",
        }
        n += 1
    return n


def _oferta_fecha(gtfs: dict, fecha8: str, mapa: dict) -> dict:
    activos = _servicios_activos_fecha(fecha8, gtfs)
    oferta = {}
    for num, gid in mapa.items():
        celdas = gtfs["por_estacion"].get(gid)
        if celdas is None:
            continue
        for hora, por_servicio in celdas.items():
            trips = set()
            rutas = set()
            for sid in activos:
                if sid in por_servicio:
                    trips |= por_servicio[sid][0]
                    rutas |= por_servicio[sid][1]
            frecuencia = len(trips)
            if frecuencia:
                oferta[(num, hora)] = (
                    frecuencia,
                    round(60.0 / frecuencia, 2),
                    len(rutas),
                )
            else:
                oferta[(num, hora)] = (0, "", 0)
    return oferta


def procesar_gtfs(ruta_dir: Path, estaciones: dict, desde: str, hasta: str) -> dict:
    snapshots = sorted(ruta_dir.glob("GTFS_20*.zip"))
    if not snapshots:
        print("  no hay snapshots GTFS")
        return {}

    fechas_fn = lambda p: p.name.split("_")[1].split(".")[0]

    # todas las fechas del rango
    rango_fechas = []
    if desde and hasta:
        d0 = date(*[int(x) for x in desde.split("-")])
        d1 = date(*[int(x) for x in hasta.split("-")])
        import datetime
        d = d0
        while d <= d1:
            rango_fechas.append(d.strftime("%Y%m%d"))
            d += datetime.timedelta(days=1)

    oferta = {}
    mapeo_global = {}
    n_geo = 0
    for sn in snapshots:
        gtfs = _leer_gtfs(sn)
        n_geo += _completar_geo_gtfs(gtfs, estaciones)
        mapa = _mapear_num_est(gtfs, estaciones)
        for k, v in mapa.items():
            mapeo_global.setdefault(k, v)
        for f8 in rango_fechas:
            # snapshot mas reciente <= fecha
            snap = None
            for s in snapshots:
                if fechas_fn(s) <= f8:
                    snap = s
            if snap != sn:
                continue
            fecha_iso = "-".join([f8[:4], f8[4:6], f8[6:8]])
            for (num, hora), vals in _oferta_fecha(gtfs, f8, mapeo_global).items():
                oferta[(num, fecha_iso, hora)] = vals
    if n_geo:
        print(f"  coordenadas completadas desde GTFS: {n_geo} claves (num_est)")
    print(f"  oferta GTFS calculada para {len(oferta)} (estacion, fecha, hora)")
    return oferta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", "-i", type=Path,
        default=Path("data/transmilenio/diario/troncal"),
        help="Carpeta con los ZIP diarios de Validación Troncal",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        default=Path("data/transmilenio/dataset.csv"),
        help="CSV de salida (default: data/transmilenio/dataset.csv)",
    )
    parser.add_argument(
        "--geo", type=Path, default=None,
        help="GeoJSON de estaciones troncales para enriquecer con lat/lon y capacidad",
    )
    parser.add_argument(
        "--trazados", type=Path, default=None,
        help="GeoJSON de trazados troncales para completar troncal/fase de cada estación",
    )
    parser.add_argument(
        "--gtfs", type=Path, default=None,
        help="Carpeta con snapshots GTFS (GTFS_YYYYMMDD.zip) para oferta/frecuencia",
    )
    parser.add_argument(
        "--desde", type=str, default=None,
        help="Solo procesar días >= esta fecha (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--hasta", type=str, default=None,
        help="Solo procesar días <= esta fecha (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--intervalo", choices=["hora", "15min", "minuto"], default="hora",
        help="Granularidad temporal de la agregación (default: hora)",
    )
    args = parser.parse_args()

    ancho = {"hora": 2, "15min": 5, "minuto": 8}[args.intervalo]

    zips = sorted(args.input.glob("validacionTroncal*.zip"))
    if not zips:
        print(f"No se encontraron archivos validacionTroncal*.zip en {args.input}")
        print("Ejecuta primero:")
        print("  python3 download_transmilenio.py --diarios --desde ... --hasta ...")
        return

    def fecha_de_nombre(p: Path) -> str:
        m = re.search(r"(\d{8})", p.name)
        return m.group(1) if m else ""

    zips = [p for p in zips if _en_rango(fecha_de_nombre(p), args.desde, args.hasta)]

    print(f"Procesando {len(zips)} archivos desde {args.input} "
          f"(intervalo: {args.intervalo})")

    estaciones = {}
    campos_out = ["Estacion"]
    if args.geo:
        if not args.geo.exists():
            print(f"AVISO: no existe {args.geo}; continúo sin coordenadas")
        else:
            estaciones = cargar_estaciones(args.geo, args.trazados)
            print(f"  {len(estaciones)} claves de estación cargadas")
        campos_out += CAMPOS_GEO
    campos_out += ["num_est"]

    def geo_de(estacion: str) -> list:
        info = _info_estacion(estaciones, estacion)
        return [
            info.get("lat", ""),
            info.get("lon", ""),
            info.get("ub_est", ""),
            info.get("nom_troncal", ""),
            info.get("fase", ""),
            info.get("cap_art", ""),
            info.get("cap_biart", ""),
        ]

    oferta = {}
    if args.gtfs and args.gtfs.exists():
        oferta = procesar_gtfs(args.gtfs, estaciones, args.desde, args.hasta)
        campos_out += CAMPOS_OFERTA
    campos_out += ["Fecha", "Hora", "Linea", "Tipo_Dia", "Validaciones"]

    agregado: defaultdict = defaultdict(int)
    for ruta in zips:
        print(f"  {ruta.name} ...")
        procesar_zip(ruta, agregado, ancho)

    filas = []
    for (estacion, fecha, hora, linea, tipo_dia), n in sorted(agregado.items()):
        cod = _codigo_estacion(estacion)
        num = f"{cod:05d}" if cod is not None else ""
        hora_base = hora[:2] if ancho > 2 else hora
        if oferta:
            frec, headway, n_rutas = oferta.get((num, fecha, hora_base), ("", "", ""))
        else:
            frec, headway, n_rutas = "", "", ""
        fila = [estacion]
        if args.geo:
            fila.extend(geo_de(estacion))
        fila.append(num)
        if oferta:
            fila.extend([frec, headway, n_rutas])
        fila.extend([fecha, hora, linea, tipo_dia, n])
        filas.append(fila)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nEscribiendo {len(filas):,} filas a {args.output}")
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(campos_out)
        writer.writerows(filas)

    print(f"TOTAL registros agregados: {len(filas):,}")
    print(f"TOTAL validaciones procesadas: {sum(agregado.values()):,}")
    print("¡Listo!")


if __name__ == "__main__":
    main()