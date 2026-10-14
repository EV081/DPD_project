"""Georreferenciacion aproximada de los mapas de ruta de ATU (PNG con paradas numeradas).

Pasos: (1) detectar los discos numerados por color + transformada de distancia,
(2) leer el numero con tesseract, (3) ajustar una similitud pixel->metros con puntos de
control y (4) proyectar cada parada a lat/lon.

Son mapas **estilizados** (calles simplificadas, no a escala): el resultado es
aproximado y debe validarse contra coordenadas conocidas (ver validar_georef.py).
"""
from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


@dataclass
class Marcador:
    x: float
    y: float
    r: float
    color: str          # "claro" | "oscuro"
    numero: int | None


def _mascara_azul(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    mx, mn = rgb.max(-1).astype(int), rgb.min(-1).astype(int)
    sat = (mx - mn) / np.maximum(mx, 1)
    return (b - r > 70) & (b > 110) & (sat > 0.55)


def _ocr_digitos(recorte: np.ndarray, r: float) -> int | None:
    """recorte: RGB centrado en el disco; los digitos son blancos sobre fondo azul.
    Solo se consideran pixeles dentro del disco (los vecinos se solapan)."""
    h, w = recorte.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    dentro = (yy - h // 2) ** 2 + (xx - w // 2) ** 2 <= (0.92 * r) ** 2
    blanco = (recorte.min(-1) > 185) & dentro
    if blanco.sum() < 6:
        return None
    img = Image.fromarray(np.where(blanco, 0, 255).astype("uint8"))
    img = img.resize((img.width * 4, img.height * 4), Image.LANCZOS)
    img = Image.fromarray(np.pad(np.asarray(img), 24, constant_values=255))
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        img.save(f.name)
        out = subprocess.run(
            ["tesseract", f.name, "stdout", "--psm", "7", "-c", "tessedit_char_whitelist=0123456789"],
            capture_output=True, text=True, timeout=30).stdout.strip()
    return int(out) if out.isdigit() and 1 <= int(out) <= 99 else None


def detectar_marcadores(ruta: str | Path, r_rel: float | None = None) -> list[Marcador]:
    rgb = np.asarray(Image.open(ruta).convert("RGB"))
    mask = ndi.binary_fill_holes(ndi.binary_closing(_mascara_azul(rgb), iterations=2))
    dt = ndi.distance_transform_edt(mask)
    mx = ndi.maximum_filter(dt, size=9)
    picos = np.argwhere((dt == mx) & (dt > 4))
    if len(picos) == 0:
        return []
    W = rgb.shape[1]
    vals = dt[picos[:, 0], picos[:, 1]]
    # el disco mide ~1-2 % del ancho; banner, titulos y la linea quedan fuera de rango
    lo, hi = 0.007 * W, 0.024 * W
    en_rango = (vals >= lo) & (vals <= hi)
    if not en_rango.any():
        return []
    h, edges = np.histogram(vals[en_rango], bins=np.arange(lo, hi + 1.0, 1.0))
    r_star = float(edges[int(np.argmax(h))] + 0.5) if r_rel is None else r_rel
    ok = (vals >= 0.8 * r_star) & (vals <= 1.35 * r_star)
    keep = picos[ok]
    if len(keep) == 0:
        return []
    # NMS: un disco por zona
    keep = keep[np.argsort(-dt[keep[:, 0], keep[:, 1]])]
    sel: list[tuple[int, int]] = []
    for y, x in keep:
        if all((y - sy) ** 2 + (x - sx) ** 2 > (1.2 * r_star) ** 2 for sy, sx in sel):
            sel.append((y, x))
    out = []
    for y, x in sel:
        r = float(dt[y, x])
        a = int(max(r * 1.1, 6))
        if y - a < 0 or x - a < 0 or y + a >= rgb.shape[0] or x + a >= rgb.shape[1]:
            continue
        rec = rgb[y - a: y + a + 1, x - a: x + a + 1]
        centro = rec.reshape(-1, 3)
        azul = centro[(centro[:, 2].astype(int) - centro[:, 0] > 70)]
        claro = bool(len(azul) and azul[:, 0].mean() < 40 and azul[:, 1].mean() > 120)
        out.append(Marcador(float(x), float(y), r, "claro" if claro else "oscuro", _ocr_digitos(rec, r)))
    return out


def detectar_discos_alimentador(ruta: str | Path) -> list[Marcador]:
    """Discos numerados de un mapa de alimentador: azul claro (sentido 1) y gris (sentido 2).

    La linea de ruta es amarilla/naranja y los textos son negros finos, asi que ambos colores se
    distinguen del fondo por transformada de distancia (el disco es mucho mas ancho que un trazo)."""
    rgb = np.asarray(Image.open(ruta).convert("RGB"))
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    azul = _mascara_azul(rgb)
    gris = (np.abs(r - g) < 14) & (np.abs(g - b) < 14) & (r > 85) & (r < 150)
    W = rgb.shape[1]
    out: list[Marcador] = []
    for color, mask in (("claro", azul), ("gris", gris)):
        m = ndi.binary_fill_holes(ndi.binary_closing(mask, iterations=2))
        dt = ndi.distance_transform_edt(m)
        lo, hi = 0.012 * W, 0.03 * W
        picos = np.argwhere((dt == ndi.maximum_filter(dt, size=9)) & (dt >= lo) & (dt <= hi))
        if len(picos) == 0:
            continue
        vals = dt[picos[:, 0], picos[:, 1]]
        h, edges = np.histogram(vals, bins=np.arange(lo, hi + 1.0, 1.0))
        r_star = float(edges[int(np.argmax(h))] + 0.5)
        picos = picos[(vals >= 0.8 * r_star) & (vals <= 1.3 * r_star)]
        picos = picos[np.argsort(-dt[picos[:, 0], picos[:, 1]])]
        sel: list[tuple[int, int]] = []
        for y, x in picos:
            if all((y - sy) ** 2 + (x - sx) ** 2 > (1.3 * r_star) ** 2 for sy, sx in sel):
                sel.append((y, x))
        for y, x in sel:
            rr = float(dt[y, x]); a = int(max(rr * 1.1, 6))
            if y - a < 0 or x - a < 0 or y + a >= rgb.shape[0] or x + a >= rgb.shape[1]:
                continue
            out.append(Marcador(float(x), float(y), rr, color, _ocr_digitos(rgb[y - a: y + a + 1, x - a: x + a + 1], rr)))
    return out


def ajustar_similitud(px: np.ndarray, mm: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Umeyama: mm ~ s * R @ px + t  (R puede incluir reflexion: eje y de imagen invertido)."""
    mu_p, mu_m = px.mean(0), mm.mean(0)
    P, M = px - mu_p, mm - mu_m
    U, S, Vt = np.linalg.svd(M.T @ P / len(px))
    d = np.sign(np.linalg.det(U) * np.linalg.det(Vt))
    D = np.diag([1, d])
    R = U @ D @ Vt
    s = (S * np.diag(D)).sum() / (P ** 2).sum() * len(px)
    t = mu_m - s * R @ mu_p
    return float(s), R, t


def aplicar(s: float, R: np.ndarray, t: np.ndarray, px: np.ndarray) -> np.ndarray:
    return (s * (R @ px.T)).T + t
