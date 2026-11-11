"""Construye ``data/horarios_servicios.json``: horario, frecuencia y paradas por servicio.

Fuente: https://metrolima.info/ (sitio no oficial; su ``robots.txt`` permite el rastreo). Se leen:

- Metropolitano: paradas ordenadas por sentido de cada servicio (JSON-LD ``BusTrip``), la tabla por
  sentido de ``/metropolitano/horario/`` y la frecuencia del texto de la página de cada servicio.
- Alimentadores, corredores y Metro L1: la tabla o el bloque "Horarios" de cada página.

La fuente se contradice en algunos servicios (tabla contra texto). ``CORRECCIONES`` reúne esos
casos con su motivo y el JSON los declara en ``notas``. Los horarios son referenciales.

Uso:  python scripts/construir_horarios_servicios.py [--cache DIR]
      (``--cache`` guarda o reutiliza las páginas descargadas)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tempfile
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from services.mapeo_estaciones import norm, series_modelo  # noqa: E402

SITIO = "https://metrolima.info"
SALIDA = BASE / "data" / "horarios_servicios.json"

# slug de la página -> nombre del servicio en la app
METROPOLITANO = {
    "ruta-a": "Ruta A", "ruta-b": "Ruta B", "ruta-c": "Ruta C", "ruta-d": "Ruta D",
    **{f"expreso-{n}": f"Expreso {n}" for n in (1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13)},
    "super-expreso": "Super Expreso", "super-expreso-norte": "Super Expreso Norte", "lechucero": "Lechucero",
}
# título en /metropolitano/horario/ -> nombre del servicio
TITULOS_HORARIO = {
    **{f"Regular {x}": f"Ruta {x}" for x in "ABCD"},
    **{f"Expreso {n}": f"Expreso {n}" for n in (1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13)},
    "Súper Expreso SX": "Super Expreso", "Súper Expreso Norte SXN": "Super Expreso Norte",
}
# nombre de estación en la fuente -> estación del modelo troncal (cuando no basta quitar tildes)
ALIAS_ESTACION = {
    "terminal naranjal": "Naranjal", "terminal matellini": "Matellini", "central": "Estacion Central",
    "terminal chimpu ocllo": "Chimpu Ocllo", "dos de mayo": "2 de Mayo", "plaza flores": "Plaza de Flores",
    "estadio union": "Union", "terminal los incas": "Los Incas",
}
ALIMENTADORES = {   # slug -> serie del modelo
    "america": "Las Américas", "antunez-de-mayolo": "Antúnez de Mayolo", "belaunde": "Belaunde",
    "bertello": "Bertello", "carabayllo": "Carabayllo", "cedros-de-villa": "Cedros de Villa",
    "collique": "Collique", "izaguirre": "Izaguirre", "la-ensenada": "Ensenada", "los-alisos": "Alisos",
    "los-olivos": "Los Olivos", "los-proceres": "Los Próceres", "milagro-de-jesus": "Milagro de Jesús",
    "naranjal": "Naranjal", "payet": "Payet", "puente-piedra": "Puente Piedra", "puno": "Puno",
    "san-juan-de-dios": "San Juan de Dios", "tahuantinsuyo": "Tahuantinsuyo", "torre-blanca": "Torre Blanca",
    "trapiche": "Trapiche", "universitaria": "Universitaria", "villa-el-salvador": "Villa El Salvador",
}
CORREDORES = {"corredor-rojo": ("201", "204", "206", "209"), "corredor-azul": ("301", "305", "370", "371"),
              "corredor-morado": ("404", "405", "406", "412")}

# Casos en que la tabla por sentido de la fuente no coincide con el texto de la página del servicio.
CORRECCIONES = {
    "Super Expreso": {
        "horario": {s: {"LAB": [["05:30", "09:00"], ["17:00", "21:00"]], "SAB": [["06:00", "09:00"]]} for s in ("asc", "desc")},
        "nota": "Dos turnos (05:30-09:00 y 17:00-21:00; sábados 06:00-09:00) según la página del servicio, que no "
                "indica el sentido de cada turno: se aplican a los dos. La tabla general solo lista 05:30-09:00.",
    },
    "Super Expreso Norte": {
        "horario": {s: {"LAB": [["05:00", "10:00"], ["16:30", "21:00"]]} for s in ("asc", "desc")},
        "nota": "Dos turnos (05:00-10:00 y 16:30-21:00) según la página del servicio, que no indica el sentido de "
                "cada turno: se aplican a los dos. La tabla general lista 16:00-22:00.",
    },
    "Lechucero": {
        "horario": {s: {"LAB": [["23:30", "04:00"]], "SAB": [["23:30", "04:00"]]} for s in ("asc", "desc")},
        "dias_semana": [3, 4, 5],
        "nota": "Servicio nocturno de jueves, viernes y sábado (23:30-04:00) según la página del servicio; la "
                "tabla general dice 22:00-05:00.",
    },
}
DIAS = {"lunes a viernes": ("LAB",), "sabados": ("SAB",), "sabado": ("SAB",), "domingos": ("DOM",),
        "domingo": ("DOM",), "domingos y feriados": ("DOM",), "domingo y feriados": ("DOM",),
        "lunes a sabado": ("LAB", "SAB"), "lunes a domingo": ("LAB", "SAB", "DOM")}


class _Texto(HTMLParser):
    """HTML -> texto: una línea por bloque y `` | `` entre celdas de tabla."""
    OCULTAS = {"script", "style", "svg", "nav", "footer", "header"}
    BLOQUES = {"tr", "p", "h1", "h2", "h3", "h4", "li", "br", "div", "table"}

    def __init__(self):
        super().__init__()
        self.partes, self.oculto = [], 0

    def handle_starttag(self, tag, attrs):
        self.oculto += tag in self.OCULTAS
        if tag in self.BLOQUES:
            self.partes.append("\n")
        if tag in ("td", "th"):
            self.partes.append(" | ")

    def handle_endtag(self, tag):
        if tag in self.OCULTAS:
            self.oculto = max(0, self.oculto - 1)

    def handle_data(self, data):
        if not self.oculto:
            self.partes.append(data)


def lineas(html: str) -> list[str]:
    p = _Texto()
    p.feed(html)
    texto = re.sub(r"[ \t\xa0]+", " ", "".join(p.partes))
    return [x.strip() for x in texto.split("\n") if x.strip()]


def grafo(html: str) -> list[dict]:
    out = []
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S):
        try:
            datos = json.loads(bloque)
        except json.JSONDecodeError:
            continue
        for x in datos if isinstance(datos, list) else [datos]:
            out += x.get("@graph", [x])
    return out


def hora(texto: str) -> str | None:
    """'4:30 a. m.' | '05:00' | '12:00 a. m.' -> 'HH:MM' (None si no hay hora)."""
    m = re.search(r"(\d{1,2}):(\d{2})\s*(a\.?\s*m\.?|p\.?\s*m\.?)?", texto.lower())
    if not m:
        return None
    h, minuto, sufijo = int(m.group(1)), m.group(2), (m.group(3) or "").replace(" ", "").replace(".", "")
    if sufijo == "pm" and h < 12:
        h += 12
    if sufijo == "am" and h == 12:
        h = 0
    return f"{h:02d}:{minuto}"


def dias(texto: str) -> tuple[str, ...]:
    return DIAS.get(norm(texto), ())


def medio(texto: str) -> float | None:
    """'5–10 min' -> 7.5; '3 a 5 minutos' -> 4.0; '10 minutos' -> 10.0."""
    n = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", texto)]
    return round(sum(n[:2]) / len(n[:2]), 1) if n else None


def pagina(ruta: str, cache: Path) -> str:
    archivo = cache / (ruta.strip("/").replace("/", "__") + ".html")
    if not archivo.exists():
        peticion = urllib.request.Request(f"{SITIO}/{ruta.strip('/')}/", headers={"User-Agent": "UrbanSafe-curso/1.0"})
        with urllib.request.urlopen(peticion, timeout=30) as r:   # noqa: S310 - URL fija del sitio fuente
            archivo.write_bytes(r.read())
        time.sleep(0.4)
    return archivo.read_text(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------- Metropolitano
def _estacion_modelo(nombre: str, indice: dict[str, str]) -> str | None:
    n = norm(re.sub(r"^estaci[oó]n\s+", "", nombre.strip(), flags=re.I))
    for clave in (norm(nombre), n):
        if clave in ALIAS_ESTACION:
            return ALIAS_ESTACION[clave]
        if clave in indice:
            return indice[clave]
    return None


def paradas_metropolitano(html: str, estaciones: list[str], sin_mapa: set[str]) -> dict[str, list[str]]:
    """{'asc': [...], 'desc': [...]} con estaciones del modelo, en orden de recorrido."""
    indice = {norm(e): e for e in estaciones}
    g = grafo(html)
    nombres = {x["@id"]: x["name"] for x in g if x.get("@type") == "BusStop"}
    out: dict[str, list[str]] = {}
    for viaje in (x for x in g if x.get("@type") == "BusTrip"):
        paradas = []
        for p in viaje.get("itinerary", []):
            est = _estacion_modelo(nombres.get(p["@id"], ""), indice)
            if est is None:
                sin_mapa.add(nombres.get(p["@id"], p["@id"]))
            elif est not in paradas:
                paradas.append(est)
        if len(paradas) < 2:
            continue
        sube = estaciones.index(paradas[-1]) > estaciones.index(paradas[0])   # el modelo ordena de sur a norte
        out["asc" if sube else "desc"] = paradas
    return out


def horarios_metropolitano(html: str) -> dict[str, dict]:
    """Tabla por sentido de /metropolitano/horario/: {servicio: {'asc'|'desc': {tipo_dia: [[ini, fin]]}}}."""
    out: dict[str, dict] = {}
    servicio = sentido = None
    for linea in lineas(html):
        if linea.startswith("Guía de Horarios"):
            break                                  # la tabla resumen repite (y a veces contradice) las anteriores
        if linea in TITULOS_HORARIO:
            servicio, sentido = TITULOS_HORARIO[linea], None
        elif linea in ("Sentido Norte", "Sentido Sur"):
            sentido = "asc" if linea.endswith("Norte") else "desc"
        elif linea.startswith("|") and servicio and sentido:
            celdas = [c.strip() for c in linea.strip("| ").split("|")]
            ini, fin = (hora(celdas[1]), hora(celdas[2])) if len(celdas) >= 3 else (None, None)
            for d in dias(celdas[0]):
                if ini and fin:
                    out.setdefault(servicio, {}).setdefault(sentido, {})[d] = [[ini, fin]]
    return out


def frecuencia_metropolitano(html: str) -> tuple[dict, str | None]:
    """Frecuencia (min) por tipo de día a partir del texto de la página del servicio."""
    frases = [x for x in lineas(html) if re.search(r"frecuencia de \d|cada \d+ minutos|\d+ a \d+ minutos en hora punta", x)]
    if not frases:
        return {}, None
    frase = min(frases, key=len)
    valores = re.findall(r"(?:frecuencia de|cada) (\d+(?: a \d+)?) minutos", frase) or re.findall(r"(\d+ a \d+) minutos", frase)
    if not valores:
        return {}, frase
    lab = medio(valores[0])
    finde = medio(valores[-1]) if len(valores) > 1 and re.search(r"s[áa]bados y domingos", frase) else None
    # "en hora punta": la fuente solo publica la frecuencia de punta de los días laborables
    valle = None if "hora punta" in frase else lab
    return {"LAB": {"punta": lab, "valle": valle},
            **{d: {"punta": finde or lab, "valle": finde or valle} for d in ("SAB", "DOM")}}, frase


def metropolitano(cache: Path, avisos: list[str]) -> dict:
    estaciones = json.loads((BASE / "models" / "troncal" / "linea_config.json").read_text(encoding="utf-8"))["estaciones"]
    tabla = horarios_metropolitano(pagina("metropolitano/horario", cache))
    out, sin_mapa = {}, set()
    for slug, nombre in METROPOLITANO.items():
        html = pagina(f"metropolitano/{slug}", cache)
        frecuencia, frase = frecuencia_metropolitano(html)
        servicio = {"url": f"{SITIO}/metropolitano/{slug}/", "paradas": paradas_metropolitano(html, estaciones, sin_mapa),
                    "horario": tabla.get(nombre, {}), "intervalo_min": frecuencia, "frecuencia_texto": frase, "notas": []}
        if nombre in CORRECCIONES:
            c = CORRECCIONES[nombre]
            servicio["horario"] = c["horario"]
            servicio["notas"].append(c["nota"])
            if "dias_semana" in c:
                servicio["dias_semana"] = c["dias_semana"]
        if not frecuencia:
            servicio["notas"].append("La fuente no publica la frecuencia: la espera usa el intervalo típico del modelo.")
        # un sentido con horario pero sin lista de paradas recorre la del otro sentido al revés
        for s, otro in (("asc", "desc"), ("desc", "asc")):
            if s in servicio["horario"] and s not in servicio["paradas"] and otro in servicio["paradas"]:
                servicio["paradas"][s] = servicio["paradas"][otro][::-1]
        if not servicio["horario"]:
            avisos.append(f"Metropolitano {nombre}: sin horario")
        out[nombre] = servicio
    if sin_mapa:
        avisos.append(f"Estaciones de la fuente sin equivalente en el modelo: {sorted(sin_mapa)}")
    return out


# --------------------------------------------------------------------------- otros sistemas
def _tabla_dias(filas: list[str]) -> tuple[dict, dict]:
    """Filas ' | días | inicio | cierre | (frecuencia)' -> (horario por tipo de día, intervalo por tipo de día)."""
    horario, intervalo = {}, {}
    for fila in filas:
        celdas = [c.strip() for c in fila.strip("| ").split("|")]
        if len(celdas) < 3 or not dias(celdas[0]):
            continue
        ini, fin = hora(celdas[1]), hora(celdas[2])
        for d in dias(celdas[0]):
            if ini:
                horario[d] = [[ini, fin]]          # fin None: la fuente no publica el cierre
            if len(celdas) > 3 and "min" in celdas[3]:
                rango = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", celdas[3])]
                intervalo[d] = {"punta": rango[0], "valle": rango[-1]}
    return horario, intervalo


def metro_l1(cache: Path) -> dict:
    filas = [x for x in lineas(pagina("metro/linea-1", cache)) if x.startswith("|")]
    horario, intervalo = _tabla_dias(filas)
    return {"Línea 1": {"url": f"{SITIO}/metro/linea-1/", "horario": {"asc": horario, "desc": horario},
                        "intervalo_min": intervalo, "notas": []}}


def corredores(cache: Path, avisos: list[str]) -> dict:
    out = {}
    for corredor, rutas in CORREDORES.items():
        for ruta in rutas:
            texto = lineas(pagina(f"{corredor}/ruta-{ruta}", cache))
            horario, _ = _tabla_dias([x for x in texto if x.startswith("|")])
            notas = [] if horario else ["La fuente no publica el horario de esta ruta."]
            if any(fin is None for tramos in horario.values() for _, fin in tramos):
                notas.append("La fuente no publica la hora de cierre de algún día.")
            if not horario:
                avisos.append(f"Corredor {ruta}: sin horario en la fuente")
            out[ruta] = {"url": f"{SITIO}/{corredor}/ruta-{ruta}/",
                         "horario": {"asc": horario, "desc": horario} if horario else {},
                         "intervalo_min": {}, "notas": notas}
    return out


def alimentadores(cache: Path, avisos: list[str]) -> dict:
    out = {}
    for slug, serie in ALIMENTADORES.items():
        texto = lineas(pagina(f"metropolitano/alimentador-{slug}", cache))
        ini = next((i for i, x in enumerate(texto) if x == "Horarios"), None)
        if ini is None:
            avisos.append(f"Alimentador {serie}: sin bloque de horarios")
            continue
        bloque = []
        for x in texto[ini + 1:]:
            if x.startswith("ℹ") or x.startswith("En esta página"):
                break
            bloque.append(x)
        horario: dict[str, dict] = {}
        intervalo: dict[str, dict] = {}
        sentido, tipos = None, ()
        for x in bloque:
            if "→" in x:                            # "Terminal X → barrio": sale de la estación de integración (asc)
                sentido = "asc" if re.match(r"(terminal|estaci[oó]n)\b", x, flags=re.I) else "desc"
            elif dias(x):
                tipos = dias(x)
            elif re.match(r"\d{1,2}:\d{2}\s*[–-]", x) and tipos:
                a, b = (hora(p) for p in re.split(r"[–-]", x, maxsplit=1))
                for s in ((sentido,) if sentido else ("asc", "desc")):
                    for d in tipos:
                        horario.setdefault(s, {})[d] = [[a, b]]
            elif "min" in x and tipos:
                pico = re.search(r"Pico:\s*([\d–\-. ]+)min", x)
                valle = re.search(r"Valle:\s*([\d–\-. ]+)min", x)
                for d in tipos:
                    intervalo[d] = ({"punta": medio(pico.group(1)), "valle": medio(valle.group(1))} if pico and valle
                                    else {"punta": medio(x), "valle": medio(x)})
        out[serie] = {"url": f"{SITIO}/metropolitano/alimentador-{slug}/", "horario": horario,
                      "intervalo_min": intervalo, "notas": []}
    faltan = sorted(set(series_modelo("alimentador")) - set(out))
    if faltan:
        avisos.append(f"Alimentadores del modelo sin página en la fuente: {faltan}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, help="carpeta donde guardar o reutilizar las páginas descargadas")
    args = ap.parse_args()
    cache = args.cache or Path(tempfile.mkdtemp(prefix="metrolima_"))
    cache.mkdir(parents=True, exist_ok=True)
    avisos: list[str] = []
    datos = {
        "fuente": {
            "nombre": "metrolima.info", "url": f"{SITIO}/", "consultado": dt.date.today().isoformat(),
            "aviso": "Horarios y frecuencias referenciales de un sitio no oficial; pueden cambiar por disposición "
                     "de la ATU. En feriados nacionales rige el horario de domingo.",
        },
        "tipos_dia": {"LAB": "lunes a viernes", "SAB": "sábado", "DOM": "domingo y feriados"},
        "sentidos": "asc/desc son los sentidos del modelo de cada sistema (troncal: asc = hacia el norte)",
        "servicios": {
            "metropolitano": metropolitano(cache, avisos),
            "metro_l1": metro_l1(cache),
            "corredor": corredores(cache, avisos),
            "alimentador": alimentadores(cache, avisos),
        },
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{SALIDA.relative_to(BASE)}: " + ", ".join(f"{k} {len(v)}" for k, v in datos["servicios"].items()))
    for a in avisos:
        print("AVISO:", a)


if __name__ == "__main__":
    main()
