"""Alimentadores del Metropolitano desde portal.atu.gob.pe/QR (fuente oficial ATU).

Cada pagina publica, **como texto**: codigo del servicio, paraderos numerados por sentido
(nombres cortos y limpios, no los cruces truncados del Excel), horarios, y los mapas
(PNG de ruta + tiras por sentido). El scraper previo no cubria esta seccion.

Salida en data/fuentes/:
  alimentadores_paraderos_atu.csv   grupo, servicio, codigo, bloque, orden, paradero, marca
  alimentadores_horarios_atu.csv    grupo, servicio, tramo, tipo_dia, inicio, fin
  mapas_alimentadores_atu.csv       grupo, servicio, archivo_local, url, tipo
  geo/mapas_alimentadores/<Grupo>/<Servicio>/*.png|jpg
Tambien registra horarios de X2 y X4 (paginas sin lista de estaciones ni mapa).
"""
from __future__ import annotations

import csv
import html as htmllib
import re
import sys
import time
import urllib.request
from urllib.parse import quote
from pathlib import Path

CODEDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODEDIR))

from download_transport_pages import QR, SALIDA, UA, descargar  # noqa: E402

GEO = SALIDA / "geo" / "mapas_alimentadores"
RE_ITEM = re.compile(r"^(\d{1,3})\.\s*(.+?)\s*$")
RE_MARCA = re.compile(r"\((inicial y final|inicial|final)\)\s*$", re.I)
RE_TITULO = re.compile(r"^(.+?)\s*\(([A-Z]{2}-\d{2})\)\s*$")
RE_HORA = re.compile(r"(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?", re.I)
RE_RANGO = re.compile(
    r"(\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?)\s*[-–—]\s*(\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?)", re.I)
RE_DIA = re.compile(r"^(lunes a (?:s[áa]bado|viernes)|s[áa]bado|domingo)s?\s*:?\s*$", re.I)


def lineas(html: str) -> list[str]:
    t = re.sub(r"(?s)<(style|script).*?</\1>", "", html)
    t = re.sub(r"(?s)<!--.*?-->", "", t)
    t = re.sub(r"<[^>]+>", "\n", t)
    out = [htmllib.unescape(x).replace("\xad", "").replace("\xa0", " ").strip()
           for x in t.split("\n")]
    return [x for x in out if x]


def _hhmm(txt: str) -> str:
    h, m, ap = RE_HORA.search(txt).groups()
    h = int(h) % 12 + (12 if ap.lower() == "p" else 0)
    return f"{h:02d}:{m}"


def _paradas_por_columna(html: str) -> list[list[dict]]:
    """La pagina pone cada sentido en una columna (`<th width="50%">`): ida | vuelta.
    Devuelve una lista por columna que contenga paradas numeradas."""
    cols = re.split(r"<th\b[^>]*width=\"50%\"", html)
    out = []
    for c in cols[1:]:
        items = []
        for x in lineas(c):
            if (m := RE_ITEM.match(x)) and not RE_HORA.search(x):
                nombre = m.group(2)
                marca = ""
                if (mm := RE_MARCA.search(nombre)):
                    marca, nombre = mm.group(1).lower(), RE_MARCA.sub("", nombre).strip()
                items.append({"orden": int(m.group(1)), "paradero": nombre, "marca": marca})
        if len(items) >= 2:
            out.append(items)
    return out


def parse_pagina(html: str) -> dict:
    L = lineas(html)
    titulo = codigo = None
    for x in L:
        if (m := RE_TITULO.match(x)):
            titulo, codigo = m.group(1).strip(), m.group(2)
            break
    paradas, bloque, previo = [], 0, None
    for x in L:
        if (m := RE_ITEM.match(x)) and not RE_HORA.search(x):
            n, nombre = int(m.group(1)), m.group(2)
            if previo is not None and n <= previo:
                bloque += 1       # la numeracion reinicia o repite el terminal -> nuevo bloque
            elif previo is None:
                bloque = 1
            previo = n
            marca = ""
            if (mm := RE_MARCA.search(nombre)):
                marca = mm.group(1).lower()
                nombre = RE_MARCA.sub("", nombre).strip()
            paradas.append({"bloque": bloque, "orden": n, "paradero": nombre, "marca": marca})
    # sentido = columna de la pagina cuando hay >= 2 columnas con paradas (cubre la numeracion
    # continua 1..24); si no, se mantiene la separacion por reinicio de numeracion
    cols = _paradas_por_columna(html)
    if len(cols) >= 2 and sum(len(c) for c in cols) == len(paradas):
        paradas = [{"bloque": b, **it} for b, c in enumerate(cols, 1) for it in c]
    horarios, tramo, dia = [], "", ""
    activo = False
    for x in L:
        if re.match(r"^horario\b", x, re.I):
            activo, tramo, dia = True, "", ""
            continue
        if not activo or x.startswith("+511"):
            if x.startswith("+511"):
                activo = False
            continue
        if RE_DIA.match(x):
            dia = x.rstrip(":").strip()
        elif (r := RE_RANGO.search(x)) and dia:
            horarios.append({"tramo": tramo, "tipo_dia": dia,
                             "inicio": _hhmm(r.group(1)), "fin": _hhmm(r.group(2))})
        elif not RE_RANGO.search(x):
            tramo, dia = x.rstrip(":").strip(), ""
    return {"titulo": titulo, "codigo": codigo, "paradas": paradas, "horarios": horarios}


def _bajar(url: str, destino: Path) -> bool:
    if destino.exists() and destino.stat().st_size > 0:
        return True
    req = urllib.request.Request(quote(url, safe="/:%"), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(r.read())
        time.sleep(0.3)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  [aviso] imagen {url}: {e}")
        return False


def main() -> None:
    idx = descargar(QR)
    if not idx:
        raise SystemExit("no se pudo descargar el indice del portal QR")
    paginas = sorted({h for h in re.findall(r'href="([^"#]+)"', idx)
                      if re.fullmatch(r"Alimentadores/[^/]+/[^/]+/", h)})
    print(f"portal: {len(paginas)} paginas de alimentadores")

    f_par, f_hor, f_img = [], [], []
    for p in paginas:
        _, grupo, servicio, _ = p.split("/")
        url = QR + p
        h = descargar(url)
        if not h:
            print(f"  [aviso] {p}: no descargada")
            continue
        d = parse_pagina(h)
        for s in d["paradas"]:
            f_par.append({"grupo": grupo, "servicio": servicio, "codigo": d["codigo"] or "",
                          "titulo": d["titulo"] or "", "url": url, **s})
        for r in d["horarios"]:
            f_hor.append({"grupo": grupo, "servicio": servicio, "codigo": d["codigo"] or "",
                          "url": url, **r})
        imgs = [i for i in re.findall(r'src="([^"]+\.(?:png|jpe?g))"', h)
                if "/" not in i and not re.search(r"icono|Img\.png|banda", i)]
        for i in dict.fromkeys(imgs):
            dest = GEO / grupo / servicio / i
            ok = _bajar(url + i, dest)
            tipo = "mapa_ruta" if (dest.exists() and dest.stat().st_size > 400_000) else "esquema_sentido"
            f_img.append({"grupo": grupo, "servicio": servicio, "tipo": tipo, "ok": ok,
                          "archivo_local": str(dest.relative_to(SALIDA)), "url": url + i})
        print(f"  {grupo}/{servicio}: {d['codigo'] or '-':>6} | {len(d['paradas']):>3} paradas "
              f"| {len(d['horarios'])} horarios | {len(imgs)} imagenes")

    # servicios X2 / X4: solo horario
    for slug in ("X2-NS-M", "X4"):
        url = f"{QR}Metropolitano/Servicios/{slug}.php"
        h = descargar(url)
        if h:
            for r in parse_pagina(h)["horarios"]:
                f_hor.append({"grupo": "Servicios", "servicio": slug, "codigo": "", "url": url, **r})

    def escribir(nombre: str, filas: list[dict]) -> None:
        if not filas:
            return
        with (SALIDA / nombre).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        print(f"{nombre}: {len(filas)} filas")

    escribir("alimentadores_paraderos_atu.csv", f_par)
    escribir("alimentadores_horarios_atu.csv", f_hor)
    escribir("mapas_alimentadores_atu.csv", f_img)


if __name__ == "__main__":
    main()
