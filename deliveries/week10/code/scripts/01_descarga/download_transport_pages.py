import argparse
import csv
import hashlib
import html as htmllib
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

CODEDIR = Path(__file__).resolve().parent
RAIZ = Path(__file__).resolve().parents[2]        
SALIDA = RAIZ / "data" / "fuentes"
CACHE = RAIZ / "data" / "_cache_html"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# URLs
QR = "https://portal.atu.gob.pe/QR/"
URL_ESTACION = QR + "Metropolitano/{slug}/"
URL_SERVICIO = QR + "Metropolitano/Servicios/{slug}.php"
URL_L1 = QR + "MetroLima/L1/"
URL_CORREDOR = QR + "Corredor{color}/{ruta}.php"
URL_METROLIMA = "https://metrolima.info/metropolitano/rutas/"

# Rutas por corredor. Se recorren todas y se descarta la que devuelva la pagina de
# error del SRA: esas devuelven HTTP 200 con un cuerpo identico y sin paraderos.
RUTAS_CORREDOR = {
    "Azul": ["301", "302", "303", "305", "306", "336", "370", "371"],
    "Rojo": ["201", "204", "206", "209", "257", "409"],
    "Morado": ["401", "404", "405", "406", "412", "601"],
}

# Comunicados verificados de la ATU en gob.pe.
URL_FREC_L1 = ("https://www.gob.pe/institucion/atu/noticias/1281919-atu-linea-1-incrementa-"
               "el-numero-de-viajes-para-reducir-el-tiempo-de-espera-de-los-usuarios-en-las-estaciones")
URL_CAP_BUS = ("https://www.gob.pe/institucion/atu/noticias/895166-atu-nuevo-bus-articulado-"
               "del-metropolitano-podra-transportar-a-164-pasajeros")
URL_AFORO_L1 = ("https://www.gob.pe/institucion/atu/noticias/320083-desde-el-lunes-14-de-"
                "diciembre-la-linea-1-del-metro-de-lima-y-callao-trasladara-el-doble-de-pasajeros-por-tren")
GOB_FUENTES = [URL_FREC_L1, URL_CAP_BUS, URL_AFORO_L1]

# Prensa reciente (2025) con frecuencia numerica de corredores. Criterio: RPP/La Republica/Radio Nacional
URL_RPP_SE08_MARCHA = (
    "https://rpp.pe/lima/actualidad/corredor-azul-inicia-este-domingo-marcha-blanca-"
    "de-nueva-ruta-que-unira-san-martin-de-porres-y-el-cercado-de-lima-noticia-1652874"
)
URL_RPP_SE08_OPERA = (
    "https://rpp.pe/lima/actualidad/comenzo-a-operar-nueva-ruta-del-corredor-azul-que-"
    "une-el-cercado-de-lima-y-smp-conoce-su-recorrido-y-paraderos-noticia-1653463"
)
URL_RN_SE08 = (
    "https://www.radionacional.gob.pe/noticias/locales/"
    "corredor-azul-inauguran-nueva-ruta-que-une-smp-con-el-cercado-de-lima"
)
URL_INFOBAE_SE08 = (
    "https://www.infobae.com/peru/2025/08/29/nueva-ruta-del-corredor-azul-este-domingo-"
    "se-inicia-la-marcha-blanca-hasta-el-3-de-septiembre-cuanto-costara-el-pasaje/"
)
URL_UPC_404 = "https://upc.aws.openrepository.com/handle/10757/670217"

_cache_mem: dict[str, str] = {}


def _decodificar(crudo: bytes) -> str:
    texto = crudo.decode("utf-8", errors="surrogateescape")
    if not any(0xDC80 <= ord(c) <= 0xDCFF for c in texto):
        return texto
    return "".join(chr(ord(c) - 0xDC00) if 0xDC80 <= ord(c) <= 0xDCFF else c for c in texto)


def _cache_path(url: str) -> Path:
    return CACHE / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".html")


def descargar(url: str, force: bool = False, intentos: int = 3) -> str | None:
    if not force and url in _cache_mem:
        return _cache_mem[url]

    cp = _cache_path(url)
    if cp.exists() and cp.stat().st_size > 0 and not force:
        texto = cp.read_text(encoding="utf-8", errors="replace")
        _cache_mem[url] = texto
        return texto

    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "es-PE,es;q=0.9"})
    for intento in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                crudo = r.read()
            texto = _decodificar(crudo)
            CACHE.mkdir(parents=True, exist_ok=True)
            cp.write_text(texto, encoding="utf-8")
            _cache_mem[url] = texto
            time.sleep(0.3)                      # cortesia con el servidor
            return texto
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  [aviso] {url.rsplit('/', 1)[-1][:50]} -> {e} "
                  f"(intento {intento + 1}/{intentos})")
            if intento < intentos - 1:
                time.sleep(1.5 * (intento + 1))
    return None


def a_texto(html: str) -> list[str]:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</(?:p|div|li|tr|h\d|td|th)>", "\n", t, flags=re.I)
    t = htmllib.unescape(re.sub(r"<[^>]+>", "\n", t))
    return [l.strip() for l in t.split("\n")]


def lineas_utiles(html: str) -> list[str]:
    return [l for l in a_texto(html) if l and l != "\xad"]


# Horarios
def _hora(suf: str = "") -> str:
    return (rf"(?P<h{suf}>\d{{1,2}}):(?P<mm{suf}>\d{{2}})\s*"
            rf"(?P<ap{suf}>[ap])\.?\s*m\.?")


RE_DIA = (r"Lunes\s+a\s+Viernes|Lunes\s+a\s+s[áa]bado|"   # los compuestos van primero
          r"Lunes|Martes|Miércoles|Jueves|Viernes|"
          r"S[áa]bado|Domingos?|Lun|Mar|Mi[ée]|Jue|Vie|S[áa]b|Dom")
RE_TIPO_DIA = re.compile(rf"\b(?P<dia>{RE_DIA})\b\s*:", re.IGNORECASE)
SEP = r"(?:-{1,2}|–|—|\s+a\s|\s+hasta\s+[^ ]+\s+)"
RE_RANGO = re.compile(rf"\s*{_hora()}\s*(?:{SEP})\s*{_hora('2')}", re.IGNORECASE)


def _minutos(match: re.Match, sufijo: str = "") -> int:
    h = int(match.group(f"h{sufijo}"))
    m = int(match.group(f"mm{sufijo}"))
    ap = match.group(f"ap{sufijo}").lower()
    if ap == "p" and h != 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    return h * 60 + m


def parse_bloque_horario(lineas: list[str], inicio: int, max_lineas: int = 8) -> list[dict]:
    ventana = [l for l in lineas[inicio:inicio + max_lineas] if l]
    if not ventana:
        return []
    # no pasar de un nuevo encabezado de horario
    for k, l in enumerate(ventana):
        if k and re.match(r"^(Horario\s+(?:Corredor|L[ií]nea)|HORARIO)", l, re.IGNORECASE):
            ventana = ventana[:k]
            break

    texto = re.sub(r"\s+", " ", " ".join(ventana))
    m_tipo = RE_TIPO_DIA.search(texto)
    trayecto = texto[:m_tipo.start()].strip(" .:-") if m_tipo else ""

    out = []
    for m in RE_TIPO_DIA.finditer(texto):
        r = RE_RANGO.match(texto, m.end())
        if r and r.group("h2") and r.group("ap2"):
            out.append({
                "trayecto": trayecto,
                "tipo_dia": m.group("dia").strip().title(),
                "hora_ini": f"{int(r.group('h')):02d}:{r.group('mm')} {r.group('ap').upper()}M",
                "hora_fin": f"{int(r.group('h2')):02d}:{r.group('mm2')} {r.group('ap2').upper()}M",
                "min_ini": _minutos(r, ""),
                "min_fin": _minutos(r, "2"),
            })
    return out


# Capa 1: portal ATU
def _descubrir_slugs(html_idx: str) -> tuple[list[str], list[str]]:
    enlaces = re.findall(r'href="([^"]+)"', html_idx)
    estaciones, servicios = set(), set()
    for e in enlaces:
        if (m := re.fullmatch(r"Metropolitano/([A-Za-z0-9\-_]+)/(?:index\.php)?", e)):
            estaciones.add(m.group(1))
        elif (m := re.fullmatch(r"Metropolitano/Servicios/([A-Za-z0-9\-_]+)\.php", e)):
            servicios.add(m.group(1))
    return sorted(estaciones), sorted(servicios)


def _servicios_de_estacion(html: str) -> list[str]:
    nombres = []
    for c in re.findall(r"<!--(.*?)-->", html, flags=re.S):
        m = re.search(r"Pesta(?:ñ|n|\u0303)a\s*\d*\s*:?\s*([^\-<]+)", c, re.IGNORECASE)
        if m:
            v = re.sub(r"\s+", " ", m.group(1)).strip(" -")
            if v:
                nombres.append(v)
    return list(dict.fromkeys(nombres))


def capa1_portal_atu(force: bool) -> dict[str, list[dict]]:
    print("\n== CAPA 1: portal.atu.gob.pe (oficial) ==")
    claves = ["servicios_por_estacion", "horarios_servicios", "paraderos_corredores",
              "horarios_corredores", "horario_linea1"]

    html_idx = descargar(QR, force)
    if not html_idx:
        print("  [error] no se pudo descargar el indice; se omite la capa 1")
        return {k: [] for k in claves}

    estaciones, servicios = _descubrir_slugs(html_idx)
    print(f"  indice: {len(estaciones)} estaciones, {len(servicios)} servicios")

    # Servicios por estacion + horarios (ambas cosas salen de la pagina de la estacion)
    filas_est, filas_hor, estaciones_sin_servicios = [], [], []
    for slug in estaciones:
        url = URL_ESTACION.format(slug=slug)
        html = descargar(url, force)
        if not html:
            print(f"  [aviso] estacion {slug}: no se pudo descargar")
            continue
        servs = _servicios_de_estacion(html)
        if not servs:
            estaciones_sin_servicios.append(slug)
        filas_est.append({
            "estacion_slug": slug,
            "estacion": slug.replace("-", " "),
            "n_servicios": len(servs),
            "servicios": " | ".join(servs),
            "url": url,
            "confianza": "alta",
        })
        lineas = lineas_utiles(html)
        for j, l in enumerate(lineas):
            if re.match(r"^HORARIO\s+\S", l, re.IGNORECASE):
                nombre = l.split(None, 1)[1].strip() if " " in l else l
                for h in parse_bloque_horario(lineas, j + 1):
                    filas_hor.append({"estacion_slug": slug, "servicio": nombre,
                                      "url": url, "confianza": "alta", **h})
    print(f"  servicios_por_estacion: {len(filas_est)} filas "
          f"({len(estaciones_sin_servicios)} sin pestanas de servicio: "
          f"{', '.join(estaciones_sin_servicios) or '-'})")
    print(f"  horarios_servicios:      {len(filas_hor)} filas")

    # Corredores
    filas_par, filas_cor = [], []
    for color, rutas in RUTAS_CORREDOR.items():
        for ruta in rutas:
            url = URL_CORREDOR.format(color=color, ruta=ruta)
            html = descargar(url, force)
            if not html:
                continue
            lineas = lineas_utiles(html)
            num = [l for l in lineas if re.match(r"^\d{1,3}\.\s+\S", l)]
            if len(num) < 5:
                print(f"  [skip] {color}/{ruta}: pagina de error SRA (sin paraderos)")
                continue

            # la numeracion reinicia en cada direccion -> cada reinicio es una direccion
            dirs, actual = [], []
            for l in num:
                if l.split(".", 1)[0].strip() == "1" and actual:
                    dirs.append(actual)
                    actual = []
                actual.append(l.split(".", 1)[1].strip())
            if actual:
                dirs.append(actual)

            for d, paradas in enumerate(dirs, start=1):
                origen, destino = paradas[0], paradas[-1]
                for k, nombre in enumerate(paradas, start=1):
                    filas_par.append({
                        "corredor": color, "ruta": ruta, "direccion": d,
                        "origen": origen, "destino": destino, "orden": k,
                        "paradero": nombre, "n_paraderos_direccion": len(paradas),
                        "url": url, "confianza": "alta",
                    })

            for j, l in enumerate(lineas):
                if re.match(r"^Horario\s+Corredor", l, re.IGNORECASE):
                    for h in parse_bloque_horario(lineas, j + 1):
                        filas_cor.append({"corredor": color, "ruta": ruta, "url": url,
                                          "confianza": "alta", **h})
            print(f"  corredor {color}/{ruta}: {len(num)} paradas, {len(dirs)} direccion(es)")
    print(f"  paraderos_corredores:    {len(filas_par)} filas")
    print(f"  horarios_corredores:     {len(filas_cor)} filas")

    # Linea 1
    filas_l1 = []
    html_l1 = descargar(URL_L1, force)
    if html_l1:
        lineas = lineas_utiles(html_l1)
        for j, l in enumerate(lineas):
            if re.match(r"^HORARIO\s+L[IÍ]NEA", l, re.IGNORECASE):
                for h in parse_bloque_horario(lineas, j + 1):
                    filas_l1.append({"linea": "L1", "url": URL_L1, "confianza": "alta", **h})
    print(f"  horario_linea1:          {len(filas_l1)} filas")

    return {"servicios_por_estacion": filas_est, "horarios_servicios": filas_hor,
            "paraderos_corredores": filas_par, "horarios_corredores": filas_cor,
            "horario_linea1": filas_l1}


# Capa 2: gob.pe
def capa2_gob(force: bool) -> dict[str, list[dict]]:
    print("\n== CAPA 2: gob.pe / comunicados ATU (oficial) ==")
    for u in GOB_FUENTES:
        print(f"  {'ok    ' if descargar(u, force) else 'FALLO '} {u.rsplit('/', 1)[-1][:64]}")

    metodo = "manual_verificado"

    frecuencias_l1 = [
        {"linea": "L1", "tipo_dia": "Lunes a Sabado", "viajes_dia": 510,
         "min_pico": 3, "max_pico": 4,
         "descripcion": "510 viajes diarios; 3 a 4 minutos en horas punta de manana y tarde",
         "url": URL_FREC_L1, "confianza": "alta", "metodo": metodo},
        {"linea": "L1", "tipo_dia": "Sabado", "viajes_dia": 510,
         "min_pico": 3, "max_pico": 10,
         "descripcion": "510 salidas diarias; frecuencia 3 a 10 minutos segun horario",
         "url": URL_FREC_L1, "confianza": "alta", "metodo": metodo},
        {"linea": "L1", "tipo_dia": "Domingo", "viajes_dia": 292,
         "min_pico": 6, "max_pico": 12,
         "descripcion": "292 salidas en la jornada; frecuencia 6 a 12 minutos",
         "url": URL_FREC_L1, "confianza": "alta", "metodo": metodo},
    ]

    capacidad = [
        {"tipo": "bus troncal articulado", "pasajeros": 164, "sentados": 47, "de_pie": 117,
         "longitud_m": 18.5,
         "descripcion": "Bus articulado de 18.5 m; 78 unidades para Lima Bus Internacional",
         "url": URL_CAP_BUS, "confianza": "alta", "metodo": metodo},
        {"tipo": "tren Linea 1", "pasajeros": 1200, "sentados": None, "de_pie": None,
         "longitud_m": None,
         "descripcion": "Capacidad nominal estimada del comunicado (428-512 usuarios = 36-43%)",
         "url": URL_AFORO_L1, "confianza": "media", "metodo": "derivado_del_comunicado"},
    ]

    nota = "Unico aforo oficial publicado por la ATU; dato puntual de 2020, no es serie historica"
    aforos = [
        {"sistema": "Metro Linea 1", "indicador": "ocupacion_actual", "valor": 17,
         "unidad": "%", "fecha_ref": "2020-12", "descripcion": "Ocupacion actual de los trenes",
         "url": URL_AFORO_L1, "confianza": "alta", "metodo": metodo, "nota": nota},
        {"sistema": "Metro Linea 1", "indicador": "ocupacion_proyectada_alstom", "valor": 36,
         "unidad": "%", "fecha_ref": "2020-12", "descripcion": "Con flota Alstom",
         "url": URL_AFORO_L1, "confianza": "alta", "metodo": metodo, "nota": nota},
        {"sistema": "Metro Linea 1", "indicador": "ocupacion_proyectada_ansaldo", "valor": 43,
         "unidad": "%", "fecha_ref": "2020-12", "descripcion": "Con flota Ansaldo",
         "url": URL_AFORO_L1, "confianza": "alta", "metodo": metodo, "nota": nota},
        {"sistema": "Metro Linea 1", "indicador": "pasajeros_por_tren", "valor": "428-512",
         "unidad": "pasajeros", "fecha_ref": "2020-12", "descripcion": "Rango de pasajeros por tren",
         "url": URL_AFORO_L1, "confianza": "alta", "metodo": metodo, "nota": nota},
    ]

    return {"frecuencias_l1_oficial": frecuencias_l1,
            "capacidad_vehiculos": capacidad,
            "aforos_publicados": aforos}


# Capa 3: metrolima.info
RE_CADA = re.compile(r"Cada\s+(\d+)(?:\s*[–\-—]\s*(\d+))?\s*min", re.IGNORECASE)
RE_COD = re.compile(r"^(?:[ABCD]|EX\d{1,2}|SX|SXN|L)$")


def capa3_metrolima(force: bool) -> list[dict]:
    print("\n== CAPA 3: metrolima.info (terceros, no oficial) ==")
    html = descargar(URL_METROLIMA, force)
    if not html:
        print("  [error] no se pudo descargar metrolima.info")
        return []

    lineas = lineas_utiles(html)
    filas = []
    vistos: set[str] = set()
    for i, l in enumerate(lineas):
        if not RE_COD.match(l) or l in vistos:
            continue
        vistos.add(l)
        frec = min_pico = max_pico = n_par = None
        nombre = ""
        for j in range(i + 1, min(i + 12, len(lineas))):
            # no cruzarse al bloque del siguiente servicio
            if j > i + 1 and RE_COD.match(lineas[j]):
                break
            if m := RE_CADA.search(lineas[j]):
                frec = lineas[j].strip()
                min_pico = int(m.group(1))
                max_pico = int(m.group(2)) if m.group(2) else int(m.group(1))
            if m2 := re.match(r"^(\d+)\s+paraderos$", lineas[j]):
                n_par = int(m2.group(1))
            if not nombre and re.match(r"^(L[ií]nea|Expreso|S[úu]per|SX|L)\b", lineas[j]):
                nombre = lineas[j]
            if n_par and frec:
                break
        filas.append({
            "servicio": l, "nombre": nombre, "frecuencia_texto": frec,
            "min_pico": min_pico, "max_pico": max_pico, "n_paraderos": n_par,
            "url": URL_METROLIMA, "no_oficial": True, "confianza": "baja",
        })

    con_num = sum(1 for r in filas if r["min_pico"] is not None)
    sin_num = [r["servicio"] for r in filas if r["min_pico"] is None]
    print(f"  servicios detectados: {len(filas)}")
    print(f"  con frecuencia numerica: {con_num} | sin frecuencia: "
          f"{', '.join(sin_num) or '-'}")
    return filas


# Capa 4: prensa corredores
def capa4_prensa_corredores() -> list[dict]:
    print("\n== CAPA 4: prensa/tesis corredores (2023-2025) ==")
    metodo_p = "manual_verificado_prensa"
    metodo_a = "manual_verificado_academico"
    nota_se08 = (
        "Servicio nuevo (ago-set 2025); no esta entre las 12 rutas del dataset "
        "de validaciones (301/303/...)."
    )
    filas = [
        {
            "corredor": "Azul", "servicio": "SE08",
            "nombre": "Servicio alimentador extraordinario 08",
            "frecuencia_texto": "frecuencia de paso de cinco minutos aproximadamente",
            "min_pico": 5, "max_pico": 5,
            "hora_ini": "05:00", "hora_fin": "00:00",
            "n_paraderos_ida": 22, "n_paraderos_vuelta": 26,
            "anio": 2025, "mes": 8, "medio": "RPP",
            "url": URL_RPP_SE08_MARCHA, "confianza": "media", "metodo": metodo_p,
            "nota": "Marcha blanca 31-ago-2025. " + nota_se08,
        },
        {
            "corredor": "Azul", "servicio": "SE08",
            "nombre": "Servicio alimentador extraordinario 08",
            "frecuencia_texto": "frecuencia de paso de cinco minutos aproximadamente",
            "min_pico": 5, "max_pico": 5,
            "hora_ini": "05:00", "hora_fin": "00:00",
            "n_paraderos_ida": 22, "n_paraderos_vuelta": 26,
            "anio": 2025, "mes": 9, "medio": "RPP",
            "url": URL_RPP_SE08_OPERA, "confianza": "media", "metodo": metodo_p,
            "nota": "Inicio de operacion 3-set-2025. Corrobora ~5 min. " + nota_se08,
        },
        {
            "corredor": "Azul", "servicio": "SE08",
            "nombre": "Servicio alimentador extraordinario 08",
            "frecuencia_texto": "frecuencia de los buses sera cada cinco minutos",
            "min_pico": 5, "max_pico": 5,
            "hora_ini": "05:00", "hora_fin": "00:00",
            "n_paraderos_ida": 22, "n_paraderos_vuelta": 26,
            "anio": 2025, "mes": 9, "medio": "Radio Nacional",
            "url": URL_RN_SE08, "confianza": "media", "metodo": metodo_p,
            "nota": "Ministro Sandoval (MTC) declara cada 5 min. " + nota_se08,
        },
        {
            "corredor": "Azul", "servicio": "SE08",
            "nombre": "Servicio alimentador extraordinario 08",
            "frecuencia_texto": "frecuencia aproximada de cinco minutos entre buses",
            "min_pico": 5, "max_pico": 5,
            "hora_ini": "05:00", "hora_fin": "00:00",
            "n_paraderos_ida": 22, "n_paraderos_vuelta": 26,
            "anio": 2025, "mes": 8, "medio": "Infobae",
            "url": URL_INFOBAE_SE08, "confianza": "media", "metodo": metodo_p,
            "nota": "Infobae cita ATU; corroboracion adicional. " + nota_se08,
        },
        {
            "corredor": "Morado", "servicio": "404",
            "nombre": "Servicio 404 Corredor Morado",
            "frecuencia_texto": "frecuencia de autobuses cada 15 minutos",
            "min_pico": 15, "max_pico": 15,
            "hora_ini": "", "hora_fin": "",
            "n_paraderos_ida": "", "n_paraderos_vuelta": "",
            "anio": 2023, "mes": 11, "medio": "UPC tesis",
            "url": URL_UPC_404, "confianza": "baja", "metodo": metodo_a,
            "nota": (
                "Tesis UPC 15-nov-2023 (Gonzales/Tinco). Promedio del 404; "
                "no es comunicado ATU. 404 si esta en el dataset."
            ),
        },
    ]
    print(f"  filas: {len(filas)} (SE08~5min prensa 2025; 404~15min tesis 2023)")
    return filas



def escribir(nombre: str, filas: list[dict]) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / nombre

    # el HTML tiene pestanas repetidas: se eliminan filas identicas
    vistas, unicas = set(), []
    for r in filas:
        clave = tuple(sorted((k, str(v)) for k, v in r.items()))
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(r)
    filas = unicas

    if not filas:
        destino.write_text("", encoding="utf-8")
        print(f"  [vacio] {nombre}")
        return
    campos: list[str] = []
    for r in filas:
        for k in r:
            if k not in campos:
                campos.append(k)
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    print(f"  OK {nombre} ({len(filas)} filas, {len(campos)} columnas)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="redescarga ignorando la cache HTML")
    args = ap.parse_args()

    print(f"Salida: {SALIDA}")
    c1 = capa1_portal_atu(args.force)
    for nombre, filas in c1.items():
        escribir(nombre + ".csv", filas)

    c2 = capa2_gob(args.force)
    for nombre, filas in c2.items():
        escribir(nombre + ".csv", filas)

    escribir("frecuencias_referencia.csv", capa3_metrolima(args.force))
    escribir("frecuencias_corredores_prensa.csv", capa4_prensa_corredores())

    n_oficial = sum(len(f) for f in list(c1.values()) + list(c2.values()))
    print(f"\nListo: {n_oficial:,} filas oficiales (capas 1-2) + 1 CSV de referencia "
          f"no oficial (capa 3) + 1 CSV de prensa corredores (capa 4).")


if __name__ == "__main__":
    main()
