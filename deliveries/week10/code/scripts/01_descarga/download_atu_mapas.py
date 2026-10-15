from __future__ import annotations

import argparse
import csv
import hashlib
import html as htmllib
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

CODEDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODEDIR))

from download_transport_pages import (  # noqa: E402
    CACHE,
    QR,
    RUTAS_CORREDOR,
    SALIDA,
    UA,
    URL_CORREDOR,
    URL_SERVICIO,
    _descubrir_slugs,
    descargar,
    lineas_utiles,
)

GEO = SALIDA / "geo"
MAPAS_C = GEO / "mapas_corredores"
MAPAS_M = GEO / "mapas_metropolitano"

SKIP_IMG = re.compile(
    r"(icono|footer|banda|logo|nuevoimg|modificado|actulizado|redes|"
    r"faces|tuiter|horario-|landing|nombre-home|FOOTER|Logo)",
    re.I,
)
MAPA_HINT = re.compile(
    r"(mapa|map|regular|expreso|corredor|_A_|arriba|abajo|paraderos|"
    r"\d{3}_|\d{3}-|nuevo-|QR|PACHA|MOLINA|ATE|SJL|RIMAC|MIRAFLORES|"
    r"MAGDALENA|LIMA_A|SM_A)",
    re.I,
)


def _get_bytes(url: str, force: bool = False) -> bytes | None:
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    cp = CACHE / f"{key}.bin"
    if cp.exists() and cp.stat().st_size > 0 and not force:
        return cp.read_bytes()
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "es-PE,es;q=0.9"}
    )
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            CACHE.mkdir(parents=True, exist_ok=True)
            cp.write_bytes(data)
            time.sleep(0.25)
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  [aviso] bin {url.rsplit('/', 1)[-1][:40]} -> {e}")
            if intento < 2:
                time.sleep(1.2 * (intento + 1))
    return None


def _img_srcs(html: str, page_url: str) -> list[str]:
    raw = re.findall(r'\bsrc=["\']([^"\']+)["\']', html, re.I)
    out = []
    for s in raw:
        s = htmllib.unescape(s.split("?")[0])
        if not re.search(r"\.(png|jpe?g|webp|gif)$", s, re.I):
            continue
        if SKIP_IMG.search(s):
            continue
        if "imagenes/" not in s.lower() and not MAPA_HINT.search(Path(s).name):
            continue
        if not MAPA_HINT.search(s) and re.search(r"(png|jpg)$", Path(s).name, re.I):
            # keep if under imagenes/ of corredor/metro
            if "imagenes/" not in s.lower():
                continue
        abs_u = urljoin(page_url, s)
        out.append(abs_u)
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def _save_img(url: str, dest_dir: Path, force: bool) -> Path | None:
    from urllib.parse import quote
    # encode spaces / weird chars in path while keeping scheme/host
    parsed = urlparse(url)
    path_enc = quote(parsed.path, safe="/:%")
    url_ok = parsed._replace(path=path_enc).geturl()
    data = _get_bytes(url_ok, force=force)
    if not data:
        return None
    name = unquote(Path(parsed.path).name)
    name = re.sub(r"[^\w.\-]+", "_", name)
    if not name:
        name = hashlib.sha256(url.encode()).hexdigest()[:12] + ".png"
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / name
    path.write_bytes(data)
    return path


def _tipo_img(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ("arriba", "abajo", "_a_", "paraderos", "sentido", "pacha", "molina")):
        return "esquema_sentido"
    if "horario" in n:
        return "horario"
    return "mapa_ruta"


def descargar_corredores(force: bool) -> list[dict]:
    print("\n== Mapas corredores (por número de ruta) ==")
    filas = []
    for color in ("Rojo", "Azul", "Morado"):
        idx = f"{QR}Corredor{color}/index.php"
        html_idx = descargar(idx, force)
        if html_idx:
            dest = MAPAS_C / color / "_index"
            for u in _img_srcs(html_idx, idx)[:5]:
                p = _save_img(u, dest, force)
                if p:
                    filas.append({
                        "corredor": color, "ruta": "",
                        "archivo_local": str(p.relative_to(SALIDA)),
                        "url": u, "tipo": "index", "ok": True,
                    })
            print(f"  index {color}: ok")
        else:
            print(f"  index {color}: FALLO")

        for ruta in RUTAS_CORREDOR[color]:
            url = URL_CORREDOR.format(color=color, ruta=ruta)
            html = descargar(url, force)
            dest = MAPAS_C / color / str(ruta)
            if not html:
                filas.append({
                    "corredor": color, "ruta": ruta, "archivo_local": "",
                    "url": url, "tipo": "mapa_ruta", "ok": False,
                })
                print(f"  {color}/{ruta}: sin HTML")
                continue
            imgs = _img_srcs(html, url)
            saved = 0
            for u in imgs:
                p = _save_img(u, dest, force)
                if not p:
                    continue
                saved += 1
                filas.append({
                    "corredor": color, "ruta": ruta,
                    "archivo_local": str(p.relative_to(SALIDA)),
                    "url": u, "tipo": _tipo_img(p.name), "ok": True,
                })
            if saved == 0:
                filas.append({
                    "corredor": color, "ruta": ruta, "archivo_local": "",
                    "url": url, "tipo": "mapa_ruta", "ok": False,
                })
            print(f"  {color}/{ruta}: {saved} imagen(es)")
    return filas


def _parse_estaciones_servicio(html: str) -> list[str]:
    """Bloque entre 'Estaciones' y 'Servicios' del menú ATU (todas las del sistema).

    Ojo: en muchas páginas de servicio ese bloque es el menú global, no el
    recorrido del servicio. Preferir estaciones_desde_servicios_por_estacion().
    """
    lineas = lineas_utiles(html)
    try:
        i0 = next(i for i, l in enumerate(lineas) if l.strip().lower() == "estaciones")
    except StopIteration:
        return []
    out = []
    for l in lineas[i0 + 1 :]:
        if l.strip().lower() == "servicios":
            break
        if len(l) < 2 or len(l) > 80:
            continue
        if re.search(r"\d{1,2}:\d{2}", l):
            continue
        out.append(l.strip())
    return out


def _humanize_estacion(s: str) -> str:
    t = str(s).replace("-", " ").replace("_", " ").strip()
    # EstacionCentral -> Estacion Central
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # aliases frecuentes Excel troncal
    aliases = {
        "estacion central": "Estacion Central",
        "jiron union": "Jiron de la Union",
        "parque trabajo": "Parque del Trabajo",
        "ramon castilla": "Ramon Castilla",
        "tomas valle": "Tomas Valle",
        "el milagro": "El Milagro",
        "los jazmines": "Los Jazmines",
        "honorio delgado": "Honorio Delgado",
        "andres belaunde": "Andres Belaunde",
        "22 agosto": "22 De Agosto",
        "28 julio": "28 de Julio",
        "2 mayo": "2 de Mayo",
    }
    key = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    return aliases.get(key, t)
SLUG_A_SERVICIO = {
    "RegularA": ["Ruta A", "REGULAR A"],
    "RegularB": ["Ruta B", "REGULAR B"],
    "RegularC": ["Ruta C", "REGULAR C"],
    "RegularD": ["Ruta D", "REGULAR D"],
    "Lechucero": ["Lechucero"],
    "X1-M": ["Expreso 1", "Expreso 1 NS", "Expreso 1 SN", "Super Expreso M"],
    "X3-N": ["Expreso 3", "Expreso 3 N"],
    "X4": ["Expreso 4"],
    "X5": ["Expreso 5"],
    "X6": ["Expreso 6"],
    "X7": ["Expreso 7"],
    "X8": ["Expreso 8", "Expreso8"],
    "X10": ["Expreso 10"],
    "X12": ["Expreso 12"],
    "EX9-NS": ["Expreso 9", "Expreso 9 NS", "Expreso 9 SN"],
    "EX11-NS": ["Expreso 11", "Expreso 11 NS", "Expreso 11 SN"],
    "EX13-NS": ["Expreso 13"],
    "SX-M": ["Super Expreso M", "Super Expreso Mañana", "SXN"],
    "SXN-NS-M": ["Super Expreso Norte", "Super Expreso Norte NS", "Super Expreso Norte SN", "SXN"],
    "SX": ["Super Expreso M", "Super Expreso Mañana"],
    "SZ": ["Super Expreso Noche", "Super Expreso N"],
    "SuperExpreso": ["Super Expreso M", "Super Expreso Mañana"],
    "SuperExpresoNorte": ["Super Expreso Norte"],
}


def estaciones_desde_servicios_por_estacion(servicios_descubiertos: list[str]) -> list[dict]:
    """Invierte servicios_por_estacion.csv → filas por servicio_slug."""
    path = SALIDA / "servicios_por_estacion.csv"
    if not path.exists():
        print("  [aviso] falta servicios_por_estacion.csv")
        return []
    import csv as _csv
    rows_in = list(_csv.DictReader(path.open(encoding="utf-8")))
    # servicio_nombre -> estaciones
    by_serv: dict[str, list[dict]] = {}
    for r in rows_in:
        for s in str(r.get("servicios", "")).split("|"):
            s = s.strip()
            if not s:
                continue
            by_serv.setdefault(s, []).append({
                "estacion_slug": r["estacion_slug"],
                "estacion": _humanize_estacion(
                    r.get("estacion") or r["estacion_slug"]
                ),
            })

    filas = []
    for slug in servicios_descubiertos:
        aliases = SLUG_A_SERVICIO.get(slug)
        if not aliases:
            # heuristic: RegularA already covered; Expreso5 -> try X5 style
            aliases = [slug, slug.replace("Expreso", "Expreso ")]
        matched_names = []
        estaciones = []
        seen = set()
        for alias in aliases:
            if alias in by_serv:
                matched_names.append(alias)
                for e in by_serv[alias]:
                    key = e["estacion_slug"]
                    if key not in seen:
                        seen.add(key)
                        estaciones.append(e)
        nombre = matched_names[0] if matched_names else slug
        for i, e in enumerate(estaciones, start=1):
            filas.append({
                "servicio_slug": slug,
                "servicio_nombre": nombre,
                "orden": i,
                "estacion": e["estacion"],
                "estacion_slug": e["estacion_slug"],
                "url": URL_SERVICIO.format(slug=slug),
                "confianza": "alta" if matched_names else "baja",
            })
        print(f"  invert {slug} ← {matched_names or ['?']}: {len(estaciones)} estaciones")
    return filas


def descargar_metropolitano_servicios(force: bool) -> tuple[list[dict], list[dict]]:
    print("\n== Mapas Metropolitano (por servicio) ==")
    html_idx = descargar(QR, force)
    servicios: list[str] = []
    if html_idx:
        _, servicios = _descubrir_slugs(html_idx)
    # solo slugs vivos del índice + regulares conocidos
    for s in ["RegularA", "RegularB", "RegularC", "RegularD", "Lechucero"]:
        if s not in servicios:
            servicios.append(s)
    print(f"  servicios a intentar: {len(servicios)} → {servicios}")

    filas_img = []
    for slug in servicios:
        url = URL_SERVICIO.format(slug=slug)
        html = descargar(url, force)
        dest = MAPAS_M / slug
        if not html or len(html) < 500:
            filas_img.append({
                "servicio_slug": slug, "servicio_nombre": slug,
                "archivo_local": "", "url": url, "tipo": "mapa_ruta", "ok": False,
            })
            print(f"  {slug}: sin página útil")
            continue
        title = re.search(r"<title>([^<]+)", html, re.I)
        nombre = title.group(1).strip() if title else slug
        imgs = _img_srcs(html, url)
        saved = 0
        for u in imgs:
            p = _save_img(u, dest, force)
            if not p:
                continue
            saved += 1
            filas_img.append({
                "servicio_slug": slug, "servicio_nombre": nombre,
                "archivo_local": str(p.relative_to(SALIDA)),
                "url": u, "tipo": _tipo_img(p.name), "ok": True,
            })
        if saved == 0:
            filas_img.append({
                "servicio_slug": slug, "servicio_nombre": nombre,
                "archivo_local": "", "url": url, "tipo": "mapa_ruta", "ok": False,
            })
        print(f"  {slug}: {saved} img")

    print("\n== Estaciones por servicio (invertir portal estaciones) ==")
    filas_est = estaciones_desde_servicios_por_estacion(servicios)
    return filas_img, filas_est


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  -> {path} ({len(rows)} filas)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    GEO.mkdir(parents=True, exist_ok=True)

    corr = descargar_corredores(args.force)
    _write_csv(
        SALIDA / "mapas_corredores_atu.csv",
        corr,
        ["corredor", "ruta", "archivo_local", "url", "tipo", "ok"],
    )

    imgs, ests = descargar_metropolitano_servicios(args.force)
    _write_csv(
        SALIDA / "mapas_metropolitano_servicios_atu.csv",
        imgs,
        ["servicio_slug", "servicio_nombre", "archivo_local", "url", "tipo", "ok"],
    )
    _write_csv(
        SALIDA / "estaciones_por_servicio_atu.csv",
        ests,
        ["servicio_slug", "servicio_nombre", "orden", "estacion", "estacion_slug", "url", "confianza"],
    )
    print("\nListo.")


if __name__ == "__main__":
    main()
