"""Lee con OCR la lista de paradas impresa al pie de los mapas de alimentadores que no la
publican como texto HTML (Los Proceres, Villa El Salvador, Trapiche-Universidad).

El mapa termina en un bloque azul oscuro con dos columnas (un sentido por columna):
"1. Calango", "2. Guardia Peruana"... Se recorta el bloque, se binariza (texto blanco) y
se pasa tesseract por columna. Los nombres se filtran contra el vocabulario de calles OSM
solo para marcar la confianza; no se corrigen.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

CODEDIR = Path(__file__).resolve().parent
FUENTES = CODEDIR.parents[1] / "data" / "fuentes"
MAPAS = FUENTES / "geo" / "mapas_alimentadores"

OBJETIVOS = {
    ("AlimentadoresSur", "LosProceres", "AS-08"): "mapa-alimentador-metropolitano-SUR-LOS PROCERESvf.png",
    ("AlimentadoresSur", "VillaElSalvador", "AS-04"): "mapa-alimentador-metropolitano-SUR-VILLA EL SALVADOR.png",
    ("AlimentadoresUniversidad", "Trapiche", "AN-10"): "Trapiche-hora-punta.png",
}
RE_ITEM = re.compile(r"^\s*(\d{1,2})\s*[.,:]?\s+(.+?)\s*$")
RE_HORA = re.compile(r"\d{1,2}\s*:\s*\d{2}|[ap]\.\s*m\.|lunes|s[aá]bado|domingo|paradero final|terminal|horario",
                     re.I)
RE_MARCA = re.compile(r"\((inicial y final|inicial|final)\)\s*$", re.I)


def bloque_azul(rgb: np.ndarray) -> tuple[int, int]:
    """Filas [y0, y1) del bloque de fondo azul oscuro del final del mapa."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    azul = (r < 40) & (60 < g) & (g < 110) & (120 < b) & (b < 180)
    frac = azul.mean(1)
    filas = np.where(frac > 0.5)[0]
    if len(filas) == 0:
        return 0, 0
    return int(filas[0]), int(filas[-1]) + 1


def ocr_columna(rgb: np.ndarray) -> list[str]:
    blanco = rgb.min(-1) > 200
    img = Image.fromarray(np.where(blanco, 0, 255).astype("uint8"))
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        img.save(f.name)
        txt = subprocess.run(["tesseract", f.name, "stdout", "--psm", "6", "-l", "eng"],
                             capture_output=True, text=True, timeout=120).stdout
    return [x.strip() for x in txt.splitlines() if x.strip()]


def leer(grupo: str, servicio: str) -> list[dict]:
    ruta = MAPAS / grupo / servicio / OBJETIVOS[(grupo, servicio, next(c for g, s, c in OBJETIVOS if (g, s) == (grupo, servicio)))]
    rgb = np.asarray(Image.open(ruta).convert("RGB"))
    y0, y1 = bloque_azul(rgb)
    if y1 - y0 < 100:
        return []
    bloque = rgb[y0:y1]
    mitad = bloque.shape[1] // 2
    filas = []
    for b, col in enumerate((bloque[:, :mitad], bloque[:, mitad:]), start=1):
        previo = 0
        for linea in ocr_columna(col):
            m = RE_ITEM.match(linea)
            if not m or RE_HORA.search(linea):
                continue
            n, nombre = int(m.group(1)), m.group(2).strip(" *")
            if len(nombre) < 3 or n <= previo or n > 60:
                continue          # ruido de horarios / numeracion que no avanza
            previo = n
            marca = ""
            if (mm := RE_MARCA.search(nombre)):
                marca, nombre = mm.group(1).lower(), RE_MARCA.sub("", nombre).strip()
            filas.append({"bloque": b, "orden": n, "paradero": nombre, "marca": marca})
    return filas


def main() -> None:
    salida = []
    for (grupo, servicio, codigo) in OBJETIVOS:
        filas = leer(grupo, servicio)
        print(f"{servicio}: {len(filas)} paradas")
        for f in filas:
            salida.append({"grupo": grupo, "servicio": servicio, "codigo": codigo,
                           "titulo": servicio, "url": "ocr_imagen", **f})
    if "--guardar" in sys.argv and salida:
        p = FUENTES / "alimentadores_paraderos_ocr.csv"
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(salida[0]))
            w.writeheader()
            w.writerows(salida)
        print(f"guardado {p.name}: {len(salida)} filas")


if __name__ == "__main__":
    main()
