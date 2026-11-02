"""Eje 1 · validaciones de la app y monitoreo semanal con el feedback de los usuarios.

- Cada "Ya abordé" suma 1 a ``validacion_hora`` (``fuente='app'``, serie del modelo, hora de Lima). Son validaciones **de la app**:
  un subconjunto pequeño y sesgado de los viajeros. **No se mezclan con las validaciones ATU** con que se entrenó el modelo.
- Cada semana se calculan, por sistema, el error del ETA (MAE y sesgo), el acierto del aforo (percibido vs mostrado) y el número de
  abordajes, y se marca una **alerta** si hay suficientes respuestas y el error es grande. No cambia ningún modelo: sirve para decidir.
"""
from __future__ import annotations

import datetime as dt
import os

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.connection import db
from db.tablas import MonitoreoModelo, ValidacionHora
from routes.feedback import FeedbackViaje
from services import calendario
from services.mapeo_estaciones import resolver_serie, sistema_modelo


def _env_float(nombre: str, defecto: float) -> float:
    try:
        return float(os.getenv(nombre, defecto))
    except ValueError:
        return defecto


def umbrales() -> dict:
    return {"min_respuestas": int(_env_float("MONITOREO_MIN_N", 30)), "sesgo_max_min": _env_float("MONITOREO_SESGO_MIN", 3.0),
            "mae_max_min": _env_float("MONITOREO_MAE_MIN", 5.0), "acierto_min": _env_float("MONITOREO_ACIERTO_MIN", 0.5)}


# --------------------------------------------------------------------------- validaciones de la app
def registrar_validacion_app(sistema: str, estacion: str, momento: dt.datetime | None = None) -> bool:
    """Suma un abordaje a la hora correspondiente. Nunca lanza: registrar la validación no debe romper el feedback."""
    try:
        s = sistema_modelo(sistema) or str(sistema).strip().lower()
        serie = (resolver_serie(s, estacion) if sistema_modelo(sistema) else None) or str(estacion).strip()
        momento = (momento or calendario.ahora_lima()).astimezone(calendario.TZ_LIMA)
        hora = momento.replace(minute=0, second=0, microsecond=0, tzinfo=None)          # hora local de Lima, sin zona
        if db.engine.dialect.name == "postgresql":
            ins = pg_insert(ValidacionHora).values(fuente="app", sistema=s, serie=serie[:100], fecha_hora=hora, n=1)
            db.session.execute(ins.on_conflict_do_update(index_elements=["fuente", "sistema", "serie", "fecha_hora"],
                                                         set_={"n": ValidacionHora.n + 1}))
        else:                                                                           # otros motores (no soportados oficialmente)
            fila = db.session.get(ValidacionHora, ("app", s, serie[:100], hora))
            if fila:
                fila.n += 1
            else:
                db.session.add(ValidacionHora(fuente="app", sistema=s, serie=serie[:100], fecha_hora=hora, n=1))
        db.session.commit()
        return True
    except Exception:                                                                    # noqa: BLE001
        db.session.rollback()
        return False


# --------------------------------------------------------------------------- métricas semanales
def lunes_de(fecha: dt.date) -> dt.date:
    return fecha - dt.timedelta(days=fecha.weekday())


def rango_semana_utc(lunes: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """[lunes 00:00, lunes siguiente 00:00) en hora de Lima, convertido a UTC."""
    ini = dt.datetime.combine(lunes, dt.time(0, 0), tzinfo=calendario.TZ_LIMA)
    return ini.astimezone(dt.timezone.utc), (ini + dt.timedelta(days=7)).astimezone(dt.timezone.utc)


def calcular_metricas(filas: list[dict]) -> dict:
    """Métricas de un conjunto de feedbacks: {n, eta:{n, mae_min, sesgo_min}, aforo:{n, acierto}} (función pura)."""
    con_eta = [f for f in filas if f.get("eta_mostrado_min") is not None]
    err = [f["espera_real_min"] - f["eta_mostrado_min"] for f in con_eta]              # >0: esperó más de lo que decía el ETA
    con_aforo = [f for f in filas if f.get("aforo_percibido") and f.get("aforo_mostrado")]
    return {
        "n": len(filas),
        "eta": {"n": len(con_eta), "mae_min": sum(abs(e) for e in err) / len(err) if err else None,
                "sesgo_min": sum(err) / len(err) if err else None},
        "aforo": {"n": len(con_aforo),
                  "acierto": sum(f["aforo_percibido"] == f["aforo_mostrado"] for f in con_aforo) / len(con_aforo) if con_aforo else None},
    }


def evaluar_alerta(m: dict, u: dict | None = None) -> str | None:
    """Motivo de la alerta o None. Solo alerta con suficientes respuestas (evita falsas alarmas por pocos datos)."""
    u = u or umbrales()
    motivos = []
    if m["eta"]["n"] >= u["min_respuestas"]:
        if abs(m["eta"]["sesgo_min"]) > u["sesgo_max_min"]:
            motivos.append(f"sesgo del ETA {m['eta']['sesgo_min']:+.1f} min (> {u['sesgo_max_min']:g})")
        if m["eta"]["mae_min"] > u["mae_max_min"]:
            motivos.append(f"error medio del ETA {m['eta']['mae_min']:.1f} min (> {u['mae_max_min']:g})")
    if m["aforo"]["n"] >= u["min_respuestas"] and m["aforo"]["acierto"] < u["acierto_min"]:
        motivos.append(f"acierto del aforo {m['aforo']['acierto']:.0%} (< {u['acierto_min']:.0%})")
    return "; ".join(motivos) or None


def _feedback_de(inicio: dt.datetime, fin: dt.datetime) -> dict[str, list[dict]]:
    filas = FeedbackViaje.query.filter(FeedbackViaje.creado_en >= inicio, FeedbackViaje.creado_en < fin).all()
    por_sistema: dict[str, list[dict]] = {}
    for f in filas:
        s = sistema_modelo(f.sistema) or "otro"
        por_sistema.setdefault(s, []).append({"espera_real_min": f.espera_real_min, "eta_mostrado_min": f.eta_mostrado_min,
                                              "aforo_percibido": f.aforo_percibido, "aforo_mostrado": f.aforo_mostrado})
    db.session.rollback()
    return por_sistema


def monitoreo_semanal(hoy: dt.date | None = None, semana: dt.date | None = None) -> dict:
    """Calcula y guarda las métricas de la semana (por defecto, la última semana completa respecto de ``hoy``)."""
    hoy = hoy or calendario.ahora_lima().date()
    lunes = lunes_de(semana) if semana else lunes_de(hoy) - dt.timedelta(days=7)
    ini, fin = rango_semana_utc(lunes)
    por_sistema = _feedback_de(ini, fin)
    if not por_sistema:
        return {"estado": "sin_datos", "semana": lunes.isoformat(), "sistemas": {}}
    u, salida = umbrales(), {}
    for sistema, filas in sorted(por_sistema.items()):
        m = calcular_metricas(filas)
        motivo = evaluar_alerta(m, u)
        abordajes = db.session.query(func.coalesce(func.sum(ValidacionHora.n), 0)).filter(
            ValidacionHora.fuente == "app", ValidacionHora.sistema == sistema,
            ValidacionHora.fecha_hora >= dt.datetime.combine(lunes, dt.time(0, 0)),
            ValidacionHora.fecha_hora < dt.datetime.combine(lunes + dt.timedelta(days=7), dt.time(0, 0))).scalar()
        MonitoreoModelo.query.filter_by(sistema=sistema, semana=lunes).delete()
        db.session.add(MonitoreoModelo(
            sistema=sistema, semana=lunes, n_abordajes=int(abordajes or 0), eta_n=m["eta"]["n"], eta_mae_min=m["eta"]["mae_min"],
            eta_sesgo_min=m["eta"]["sesgo_min"], aforo_n=m["aforo"]["n"], aforo_acierto=m["aforo"]["acierto"],
            alerta=motivo is not None, motivo_alerta=motivo))
        salida[sistema] = {**m, "n_abordajes": int(abordajes or 0), "alerta": motivo}
    db.session.commit()
    return {"estado": "ok", "semana": lunes.isoformat(), "sistemas": salida, "alertas": sum(1 for v in salida.values() if v["alerta"])}


def resumen(ultimas: int = 8) -> list[dict]:
    filas = MonitoreoModelo.query.order_by(MonitoreoModelo.semana.desc(), MonitoreoModelo.sistema).limit(ultimas * 4).all()
    db.session.rollback()
    return [{"semana": f.semana.isoformat(), "sistema": f.sistema, "abordajes": f.n_abordajes, "eta_mae_min": f.eta_mae_min,
             "eta_sesgo_min": f.eta_sesgo_min, "aforo_acierto": f.aforo_acierto, "alerta": f.alerta, "motivo": f.motivo_alerta} for f in filas]
