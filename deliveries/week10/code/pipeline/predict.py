"""Batch diario (capa A): pronostica 24 h por sistema y llena ``registro_modelo`` + ``prediccion``.

El contexto sale de la vista ``demanda_fiable`` (28 días hasta el día previo). Degrada
``principal`` -> ``ligero`` si el modelo principal falla (p. ej. sin torch/Chronos).
"""
from __future__ import annotations

import datetime as dt
import sys

import pandas as pd

from pipeline import config
from storage import db

sys.path.insert(0, str(config._CODE_DIR / "model"))
from inferencia import DIAS_CONTEXTO, MODELS_DIR, ModeloSistema, leer_json  # noqa: E402

SISTEMAS = ["metro_l1", "troncal", "corredor", "alimentador"]


def contexto_desde_bd(conn, sistema: str, dia: dt.date, dias: int = DIAS_CONTEXTO) -> pd.DataFrame:
    """DataFrame hora x unidad con las validaciones de [dia-dias, dia) (huecos = 0)."""
    desde = dia - dt.timedelta(days=dias)
    filas = conn.execute(
        """
        SELECT fecha, hora, unidad, sum(validaciones) AS v
        FROM demanda_fiable
        WHERE sistema = %s AND fecha >= %s AND fecha < %s
        GROUP BY fecha, hora, unidad
        """,
        (sistema, desde, dia),
    ).fetchall()
    if not filas:
        raise RuntimeError(f"sin demanda para {sistema} en [{desde}, {dia})")
    df = pd.DataFrame(filas)
    df["Fecha_Hora"] = pd.to_datetime(df["fecha"]) + pd.to_timedelta(df["hora"], unit="h")
    ancho = df.pivot_table(index="Fecha_Hora", columns="unidad", values="v", aggfunc="sum")
    idx = pd.date_range(pd.Timestamp(desde), pd.Timestamp(dia) - pd.Timedelta(hours=1), freq="h")
    return ancho.reindex(idx).fillna(0.0).rename_axis("Fecha_Hora")


def _pronosticar_con_degradacion(modelo: ModeloSistema, contexto, dia, modo: str):
    orden = [modo] + (["ligero"] if modo == "principal" else [])
    ultimo = None
    for m in orden:
        try:
            return modelo.pronosticar(contexto, dia, modo=m), m
        except Exception as exc:  # noqa: BLE001 - se reporta y se degrada
            ultimo = exc
            print(f"[predict] {modelo.sistema}: modo {m} fallo ({type(exc).__name__}: {exc})")
    raise RuntimeError(f"{modelo.sistema}: sin modo disponible") from ultimo


def predecir_sistema(conn, sistema: str, dia: dt.date, modo: str = "ligero") -> int:
    modelo = ModeloSistema.cargar(sistema)
    contexto = contexto_desde_bd(conn, sistema, dia)
    salida, modo_usado = _pronosticar_con_degradacion(modelo, contexto, dia, modo)
    card = leer_json(MODELS_DIR / sistema / "model_card.json")
    wmape = card["metricas_test"]["principal"]["todos"]["WMAPE"]
    with conn.transaction():
        reg = conn.execute(
            """
            INSERT INTO registro_modelo
                (nombre, sistema, version, mejor_modelo, wmape, ruta_archivo, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (card["nombre"], sistema, card["version"], str(salida["modelo"].iloc[0]),
             wmape, f"models/{sistema}", f"batch {dia} modo={modo_usado}"),
        ).fetchone()["id"]
        conn.execute("DELETE FROM prediccion WHERE sistema = %s AND fecha = %s", (sistema, dia))
        filas = [
            (reg, sistema, r.unidad, r.fecha_hora.date(), int(r.fecha_hora.hour),
             float(r.validaciones_pron), r.aforo, float(r.eta_min), float(r.eta2_min),
             r.recomendacion, float(r.banda80_lo), float(r.banda80_hi), r.modelo)
            for r in salida.itertuples()
        ]
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO prediccion
                    (registro_modelo_id, sistema, unidad, fecha, hora, predicho, aforo,
                     eta_min, eta2_min, recomendacion, banda80_lo, banda80_hi, modelo)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                filas,
            )
    return len(filas)


def main(dia: dt.date | None = None, modo: str = "ligero", sistemas: list[str] | None = None) -> None:
    conn = db.connect()
    try:
        if dia is None:
            ultimo = conn.execute("SELECT max(fecha) AS f FROM demanda_fiable").fetchone()["f"]
            dia = ultimo + dt.timedelta(days=1)
        for s in sistemas or SISTEMAS:
            n = predecir_sistema(conn, s, dia, modo)
            print(f"[predict] {s}: {n} filas para {dia}")
    finally:
        conn.close()
