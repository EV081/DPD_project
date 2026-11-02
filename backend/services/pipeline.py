"""Bitácora de los jobs (tabla ``pipeline_ejecucion``): cada corrida deja inicio, fin, estado y un detalle legible."""
from __future__ import annotations

import datetime as dt
import json
from contextlib import contextmanager

from db.connection import db
from db.tablas import PipelineEjecucion, ahora_utc


def _serializable(obj):
    """Convierte a tipos JSON (tuplas, fechas, numpy) para guardar el detalle."""
    return json.loads(json.dumps(obj, default=lambda o: o.isoformat() if isinstance(o, (dt.date, dt.datetime)) else
                                 (o.item() if hasattr(o, "item") else str(o))))


@contextmanager
def ejecucion(nombre: str):
    """Registra una corrida: ``with ejecucion('eje2-recalibrar') as r: r['ajustes'] = 3`` (estado ok; ``r['estado']='sin_datos'`` opcional)."""
    fila = PipelineEjecucion(nombre=nombre, inicio=ahora_utc(), estado="en_curso")
    db.session.add(fila)
    db.session.commit()
    fila_id, resultado = fila.id, {}
    try:
        yield resultado
    except Exception as exc:
        db.session.rollback()
        f = db.session.get(PipelineEjecucion, fila_id)
        f.estado, f.fin, f.detalle = "error", ahora_utc(), {"error": f"{type(exc).__name__}: {exc}"}
        db.session.commit()
        raise
    f = db.session.get(PipelineEjecucion, fila_id)
    f.estado = resultado.pop("estado", "ok")
    f.fin, f.detalle = ahora_utc(), _serializable(resultado)
    db.session.commit()
