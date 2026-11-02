"""Polilíneas codificadas (algoritmo de Google, sin dependencias) para guardar y devolver geometrías compactas."""
from __future__ import annotations


def _codificar(valor: int) -> str:
    valor = ~(valor << 1) if valor < 0 else valor << 1
    salida = []
    while valor >= 0x20:
        salida.append(chr((0x20 | (valor & 0x1F)) + 63))
        valor >>= 5
    salida.append(chr(valor + 63))
    return "".join(salida)


def codificar(coords: list[tuple[float, float]], precision: int = 5) -> str:
    """Lista de (lon, lat) -> texto. Con precisión 5 el error máximo es ~1 m."""
    f = 10 ** precision
    ult_lat = ult_lon = 0
    out = []
    for lon, lat in coords:
        la, lo = round(lat * f), round(lon * f)
        out.append(_codificar(la - ult_lat) + _codificar(lo - ult_lon))
        ult_lat, ult_lon = la, lo
    return "".join(out)


def decodificar(texto: str, precision: int = 5) -> list[tuple[float, float]]:
    """Texto -> lista de (lon, lat)."""
    f = 10 ** precision
    i, lat, lon, out = 0, 0, 0, []
    while i < len(texto):
        for eje in (0, 1):
            desplaz = resultado = 0
            while True:
                b = ord(texto[i]) - 63
                i += 1
                resultado |= (b & 0x1F) << desplaz
                desplaz += 5
                if b < 0x20:
                    break
            delta = ~(resultado >> 1) if resultado & 1 else resultado >> 1
            if eje == 0:
                lat += delta
            else:
                lon += delta
        out.append((lon / f, lat / f))
    return out
