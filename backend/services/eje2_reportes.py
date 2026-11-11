"""Eje 2 · reportes de usuarios: validación, límites por usuario, recalibración del riesgo y caché de los ajustes.

Reglas del proyecto (nunca se rompen):
- un reporte individual **no se expone** ni se muestra su autor; solo cuentan los agregados por zona;
- la respuesta de un reporte siempre recuerda que en una emergencia se llama al 105;
- sin texto libre: solo tipo + ubicación + hora (no hay datos personales ni acusaciones sobre personas).

La recalibración (``calcular_ajustes``) es una **hipótesis acotada, no entrenada**: con poca evidencia no cambia nada, el cambio
tiene un tope y desaparece solo cuando dejan de llegar reportes. Ver docs/EJE2_RUTA_SEGURA.md.
"""
from __future__ import annotations

import datetime as dt
import math
import os
import threading
import time
from collections import defaultdict

from sqlalchemy import func

from db.connection import db
from db.tablas import AjusteRiesgoSegmento, ReporteSeguridad, TIPOS_REPORTE
from services import calendario
from services import eje2_service as E


def _env_int(nombre: str, defecto: int) -> int:
    try:
        return int(os.getenv(nombre, defecto))
    except ValueError:
        return defecto


def _env_float(nombre: str, defecto: float) -> float:
    try:
        return float(os.getenv(nombre, defecto))
    except ValueError:
        return defecto


# --- límites por usuario ---
def limite_por_hora() -> int:
    return _env_int("EJE2_REPORTES_POR_HORA", 5)


def limite_por_dia() -> int:
    return _env_int("EJE2_REPORTES_POR_DIA", 20)


VENTANA_PASADO = dt.timedelta(hours=24)         # un reporte puede ser de hasta 24 h atrás
TOLERANCIA_FUTURO = dt.timedelta(minutes=5)
SNAP_REPORTE_M = 40.0                           # el punto reportado debe estar a ≤ 40 m de una calle del grafo
MENSAJE_105 = "Si estás en peligro o presencias una emergencia, llama al 105."


class ReporteError(E.Eje2Error):
    pass


def ajuste_activo() -> bool:
    return os.getenv("EJE2_AJUSTE_ACTIVO", "1").strip().lower() not in ("0", "false", "no", "off")


# --------------------------------------------------------------------------- crear un reporte
def _parsear_ocurrido(valor, ahora: dt.datetime) -> dt.datetime:
    if valor in (None, ""):
        return ahora
    try:
        f = dt.datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        raise ReporteError("ocurrido_en debe ser una fecha ISO 8601, por ejemplo 2026-11-02T21:30:00-05:00") from None
    if f.tzinfo is None:
        f = f.replace(tzinfo=calendario.TZ_LIMA)             # sin zona: se asume la hora de Lima
    f = f.astimezone(dt.timezone.utc)
    if f > ahora + TOLERANCIA_FUTURO:
        raise ReporteError("ocurrido_en no puede estar en el futuro")
    if f < ahora - VENTANA_PASADO:
        raise ReporteError("Solo se aceptan reportes de las últimas 24 horas")
    return f


def crear_reporte(user_id: int, datos: dict, ahora: dt.datetime | None = None, g: E.GrafoEje2 | None = None) -> dict:
    """Valida y guarda un reporte. Lanza ``ReporteError`` (400/422/429) o devuelve el dato de confirmación."""
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    g = g or E.grafo()
    if not isinstance(datos, dict):
        raise ReporteError("El cuerpo debe ser un objeto JSON")
    tipo = str(datos.get("tipo") or "").strip().lower()
    if tipo not in TIPOS_REPORTE:
        raise ReporteError(f"tipo debe ser uno de: {', '.join(TIPOS_REPORTE)}")
    try:
        lat, lon = float(datos["lat"]), float(datos["lon"])
    except (KeyError, TypeError, ValueError):
        raise ReporteError("lat y lon son obligatorios y numéricos") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ReporteError("lat/lon fuera de rango")
    ocurrido = _parsear_ocurrido(datos.get("ocurrido_en"), ahora)
    seg, _dist = g.segmento_cercano(lat, lon, SNAP_REPORTE_M)                      # 422 si no hay calle cubierta cerca

    # límites por usuario (contando también los retirados, para que borrar no sirva para esquivarlos)
    base = db.session.query(func.count()).select_from(ReporteSeguridad).filter(ReporteSeguridad.user_id == user_id)
    if base.filter(ReporteSeguridad.creado_en >= ahora - dt.timedelta(hours=1)).scalar() >= limite_por_hora():
        raise ReporteError(f"Alcanzaste el límite de {limite_por_hora()} reportes por hora. Intenta más tarde.", 429)
    if base.filter(ReporteSeguridad.creado_en >= ahora - dt.timedelta(days=1)).scalar() >= limite_por_dia():
        raise ReporteError(f"Alcanzaste el límite de {limite_por_dia()} reportes por día.", 429)
    seg_id = g.seg_id_de(seg)
    if base.filter(ReporteSeguridad.seg_id == seg_id, ReporteSeguridad.creado_en >= ahora - dt.timedelta(hours=1)).scalar() > 0:
        raise ReporteError("Ya reportaste esta calle hace poco. Gracias: no hace falta repetirlo.", 429)

    d_acc, i_acc = g.acc_tree.query(E._xy([lat], [lon])[0])
    franja = E.franja_de(ocurrido.astimezone(calendario.TZ_LIMA))
    fila = ReporteSeguridad(user_id=user_id, tipo=tipo, ocurrido_en=ocurrido, lat=round(lat, 5), lon=round(lon, 5), seg_id=seg_id,
                            acceso_id=str(g.accesos["acceso_id"].iloc[int(i_acc)]) if d_acc <= 1500 else None, franja=franja,
                            creado_en=ahora)
    db.session.add(fila)
    db.session.commit()
    return {"id": fila.id, "mensaje": "Gracias por tu reporte. Ayuda a mejorar las rutas de otras personas.",
            "calle": g.nombre_de(seg) or E.ETIQUETA_VIA.get(g.via_de(seg), "vía"), "franja": franja,
            "llamar_105": True, "numero_emergencia": "105", "aviso": MENSAJE_105,
            "nota": "Tu reporte solo se usa de forma agregada y anónima; nunca se muestra a otros usuarios."}


# --------------------------------------------------------------------------- caché de los ajustes por reportes
class CacheAjustes:
    """Mantiene en memoria los ajustes de riesgo (tabla ``ajuste_riesgo_segmento``) y los recarga cuando cambian.

    El job que recalibra corre en otro proceso: el servidor web se entera revisando ``max(actualizado_en)`` cada ``ttl`` s.
    """

    def __init__(self, ttl: float | None = None):
        self.ttl = _env_float("EJE2_AJUSTES_TTL_S", 60.0) if ttl is None else ttl
        self._deltas, self._version, self._t = None, None, 0.0
        self._lock = threading.Lock()

    def invalidar(self) -> None:
        with self._lock:
            self._deltas, self._version, self._t = None, None, 0.0

    def obtener(self, g: E.GrafoEje2) -> dict | None:
        if not ajuste_activo():
            return None
        with self._lock:
            ahora = time.monotonic()
            if self._t and ahora - self._t < self.ttl:
                return self._deltas
            version = db.session.query(func.max(AjusteRiesgoSegmento.actualizado_en), func.count()).one()
            db.session.rollback()                                          # no dejar la transacción de lectura abierta
            version = tuple(version)
            if version != self._version:
                filas = db.session.query(AjusteRiesgoSegmento.seg_id, AjusteRiesgoSegmento.franja, AjusteRiesgoSegmento.delta).all()
                db.session.rollback()
                self._deltas = E.deltas_desde_filas(g, filas) if filas else None
                self._version = version
            self._t = ahora
            return self._deltas


ajustes = CacheAjustes()


# --------------------------------------------------------------------------- recalibración (función pura, sin base de datos)
PARAMS = {
    "ventana_dias": 90,            # solo cuentan los reportes de los últimos 90 días
    "vida_media_dias": 30,         # el peso de un reporte se reduce a la mitad cada 30 días
    "min_reportes": 3,             # evidencia mínima en la zona...
    "min_usuarios": 2,             # ...de al menos 2 personas distintas
    "tope": 0.30,                  # el ajuste nunca pasa de +0,30 de riesgo (escala 0-1)
    "n0": 5.0,                     # saturación: delta = tope · (1 − exp(−n_efectivo / n0))
    "saltos": 2,                   # la zona es el segmento y sus vecinos hasta 2 saltos (~150-250 m)
    "peso_vecinos": (1.0, 0.5, 0.25),   # efecto en el propio segmento y a 1 y 2 saltos
}


def parametros() -> dict:
    p = dict(PARAMS)
    for k, env in (("ventana_dias", "EJE2_VENTANA_DIAS"), ("min_reportes", "EJE2_MIN_REPORTES"), ("min_usuarios", "EJE2_MIN_USUARIOS")):
        p[k] = _env_int(env, p[k])
    for k, env in (("vida_media_dias", "EJE2_VIDA_MEDIA_DIAS"), ("tope", "EJE2_AJUSTE_TOPE"), ("n0", "EJE2_AJUSTE_N0")):
        p[k] = _env_float(env, p[k])
    return p


def vecinos_por_saltos(g: E.GrafoEje2, seg: int, saltos: int) -> list[set[int]]:
    """[segmentos a 0 saltos, a 1 salto, a 2 saltos...] usando la adyacencia del grafo (segmentos que comparten un nodo)."""
    niveles = [{int(seg)}]
    visto = {int(seg)}
    for _ in range(saltos):
        sig = set()
        for s in niveles[-1]:
            for nodo in (int(g.seg_u[s]), int(g.seg_v[s])):
                sig.update(g.segmentos_de_nodo(nodo).tolist())
        sig -= visto
        visto |= sig
        niveles.append(sig)
    return niveles


def calcular_ajustes(reportes: list[dict], g: E.GrafoEje2, ahora: dt.datetime, params: dict | None = None) -> list[dict]:
    """Ajuste de riesgo por segmento y franja a partir de reportes activos.

    reportes: dicts con ``seg_id``, ``franja``, ``user_id``, ``ocurrido_en`` (datetime con zona).
    Devuelve [{seg_id, franja, delta, n_reportes, n_usuarios}] solo para los segmentos con delta > 0.

    1) cada reporte pesa ``0,5 ** (edad / vida_media)`` y solo cuenta si tiene ≤ ventana días;
    2) una persona cuenta una vez por segmento y día (evita que una sola cuenta "infle" un lugar);
    3) la **zona** de un segmento es él y sus vecinos hasta 2 saltos; solo hay ajuste si la zona reúne ≥ min_reportes
       reportes de ≥ min_usuarios personas distintas;
    4) ``delta = tope · (1 − exp(−n_efectivo / n0))``, con efecto pleno en el segmento reportado y menor en los vecinos.
    """
    p = params or parametros()
    por_franja: dict[str, dict[int, dict]] = {"dia": defaultdict(dict), "noche": defaultdict(dict)}
    for r, i in zip(reportes, g.indices_de([x["seg_id"] for x in reportes])):
        i = int(i)
        edad = (ahora - r["ocurrido_en"]).total_seconds() / 86400.0
        if i < 0 or edad > p["ventana_dias"] or edad < -0.01 or r["franja"] not in por_franja:
            continue
        clave = (r["user_id"], r["ocurrido_en"].astimezone(calendario.TZ_LIMA).date())      # una persona, un segmento, un día
        w = 0.5 ** (max(edad, 0.0) / p["vida_media_dias"])
        previo = por_franja[r["franja"]][i].get(clave)
        if previo is None or w > previo:
            por_franja[r["franja"]][i][clave] = w

    salida = []
    for franja, segmentos in por_franja.items():
        delta_seg: dict[int, tuple[float, int, int]] = {}
        for centro in segmentos:
            niveles = vecinos_por_saltos(g, centro, p["saltos"])
            zona = set().union(*niveles)
            claves = [(c, w) for s in zona for c, w in segmentos.get(s, {}).items()]
            usuarios = {c[0] for c, _ in claves}
            if len(claves) < p["min_reportes"] or len(usuarios) < p["min_usuarios"]:
                continue
            n_ef = sum(w for _, w in claves)
            delta_zona = p["tope"] * (1.0 - math.exp(-n_ef / p["n0"]))
            for nivel, segs in enumerate(niveles):
                peso = p["peso_vecinos"][min(nivel, len(p["peso_vecinos"]) - 1)]
                for s in segs:
                    d = delta_zona * peso
                    if d > delta_seg.get(s, (0.0, 0, 0))[0]:
                        delta_seg[s] = (d, len(claves), len(usuarios))
        for s, (d, n_rep, n_usr) in delta_seg.items():
            salida.append({"seg_id": g.seg_id_de(s), "franja": franja, "delta": round(min(d, p["tope"]), 4),
                           "n_reportes": n_rep, "n_usuarios": n_usr})
    return salida


# --------------------------------------------------------------------------- recalibración contra la base de datos
def recalibrar(ahora: dt.datetime | None = None, g: E.GrafoEje2 | None = None) -> dict:
    """Lee los reportes activos de la ventana, calcula los ajustes y reemplaza ``ajuste_riesgo_segmento`` en una transacción."""
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    g = g or E.grafo()
    p = parametros()
    desde = ahora - dt.timedelta(days=p["ventana_dias"] + 1)
    filas = (db.session.query(ReporteSeguridad.seg_id, ReporteSeguridad.franja, ReporteSeguridad.user_id, ReporteSeguridad.ocurrido_en)
             .filter(ReporteSeguridad.creado_en >= desde, ReporteSeguridad.estado == "activo").all())
    # SQLite devuelve fechas sin zona; estos instantes siempre se guardan en UTC.
    reportes = [{"seg_id": f.seg_id, "franja": f.franja, "user_id": f.user_id,
                 "ocurrido_en": f.ocurrido_en if f.ocurrido_en.tzinfo else f.ocurrido_en.replace(tzinfo=dt.timezone.utc)}
                for f in filas]
    ajustes_nuevos = calcular_ajustes(reportes, g, ahora, p)
    db.session.query(AjusteRiesgoSegmento).delete()
    db.session.add_all(AjusteRiesgoSegmento(seg_id=a["seg_id"], franja=a["franja"], delta=a["delta"], n_reportes=a["n_reportes"],
                                            n_usuarios=a["n_usuarios"], actualizado_en=ahora) for a in ajustes_nuevos)
    db.session.commit()
    ajustes.invalidar()
    return {"reportes_considerados": len(reportes), "ajustes": len(ajustes_nuevos),
            "segmentos_distintos": len({a["seg_id"] for a in ajustes_nuevos}), "activo": ajuste_activo(), "parametros": p}
