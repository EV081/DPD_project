"""Comandos de mantenimiento y pipelines:  ``flask --app app <comando>``.

Pensados para correr desde un Cron Job (Render) o el servicio `pipeline` de docker-compose; ninguno se expone por HTTP.

    db-particiones     crea las particiones de los próximos meses y retira las muy viejas
    eje2-recalibrar    reportes de usuarios -> ajuste del riesgo de las calles (tabla ajuste_riesgo_segmento)
    pipeline-diario    db-particiones + eje2-recalibrar
    seed-admin         crea/actualiza el administrador con las variables SEED_ADMIN_* del .env
    monitoreo-semanal  métricas de la semana con el feedback de la app (ETA, aforo, abordajes) y alertas
    calibrar-eta       calibración semanal del ETA con los "Ya abordé" (campeón vs retador)
    monitoreo-resumen  imprime las últimas métricas guardadas
    pipeline-semanal   particiones + monitoreo + calibración del ETA (lunes 02:00 hora de Lima = 07:00 UTC)
"""
from __future__ import annotations

import datetime as dt
import json
import os

import click

from services.pipeline import ejecucion


def _retencion(nombre: str, defecto: int) -> int:
    try:
        return int(os.getenv(nombre, defecto))
    except ValueError:
        return defecto


def particiones_job(adelante: int = 3) -> dict:
    from db import particiones, tablas
    from db.connection import db
    creadas = particiones.ensure_todas(db.engine, tablas.PARTICIONADAS, adelante=adelante)
    retenciones = {"reporte_seguridad": _retencion("RETENCION_MESES_REPORTES", 24),
                   "validacion_hora": _retencion("RETENCION_MESES_VALIDACIONES", 36)}
    borradas = {t: particiones.retener(db.engine, t, retenciones[t]) for t in tablas.PARTICIONADAS}
    return {"creadas": creadas, "retiradas": borradas, "retencion_meses": retenciones}


def recalibrar_job() -> dict:
    from services import eje2_reportes
    return eje2_reportes.recalibrar()


def registrar_comandos(app) -> None:
    @app.cli.command("db-particiones")
    @click.option("--adelante", default=3, show_default=True, help="meses futuros que deben tener partición")
    def db_particiones(adelante):
        """Crea las particiones mensuales que falten y retira las que superan la retención."""
        with ejecucion("db-particiones") as r:
            r.update(particiones_job(adelante))
        click.echo(json.dumps(r, ensure_ascii=False, default=str))

    @app.cli.command("eje2-recalibrar")
    def eje2_recalibrar():
        """Recalcula el ajuste de riesgo de las calles con los reportes de usuarios de los últimos 90 días."""
        with ejecucion("eje2-recalibrar") as r:
            r.update(recalibrar_job())
            if not r["ajustes"]:
                r["estado"] = "sin_datos"
        click.echo(f"reportes considerados: {r['reportes_considerados']} · ajustes: {r['ajustes']} en {r['segmentos_distintos']} calles")

    @app.cli.command("seed-admin")
    def seed_admin():
        """Crea o actualiza al administrador con SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD / SEED_ADMIN_NAME del .env."""
        from services import usuarios
        try:
            r = usuarios.sembrar_admin()
        except usuarios.SeedError as exc:
            raise click.ClickException(str(exc))
        if r["estado"] == "omitido":
            raise click.ClickException(r["motivo"])
        click.echo(f"seed-admin: {r['estado']} ({r['email']})")

    @app.cli.command("pipeline-diario")
    def pipeline_diario():
        """Mantenimiento diario: particiones y recalibración del Eje 2."""
        with ejecucion("pipeline-diario") as r:
            r["particiones"] = particiones_job()
            r["recalibracion"] = recalibrar_job()
        click.echo("pipeline-diario ok")

    @app.cli.command("monitoreo-semanal")
    @click.option("--hoy", default=None, help="fecha de referencia AAAA-MM-DD (por defecto hoy en Lima)")
    def monitoreo_semanal(hoy):
        """Calcula y guarda las métricas de la última semana completa."""
        from services import monitoreo
        with ejecucion("monitoreo-semanal") as r:
            r.update(monitoreo.monitoreo_semanal(hoy=dt.date.fromisoformat(hoy) if hoy else None))
        click.echo(json.dumps(r, ensure_ascii=False, default=str))

    @app.cli.command("calibrar-eta")
    @click.option("--ahora", default=None, help="momento de referencia ISO 8601 (por defecto ahora)")
    def calibrar_eta(ahora):
        """Re-ajusta el factor del ETA con el feedback de las últimas 8 semanas (solo se promueve si mejora)."""
        from services import calibracion
        with ejecucion("calibrar-eta") as r:
            r.update(calibracion.calibrar_todos(dt.datetime.fromisoformat(ahora) if ahora else None))
        click.echo(json.dumps(r, ensure_ascii=False, default=str))

    @app.cli.command("monitoreo-resumen")
    def monitoreo_resumen():
        """Imprime las últimas métricas semanales y sus alertas."""
        from services import monitoreo
        filas = monitoreo.resumen()
        if not filas:
            click.echo("Todavía no hay métricas guardadas.")
        for f in filas:
            click.echo(f"{f['semana']} {f['sistema']:<12} abordajes={f['abordajes']:<4} ETA MAE={f['eta_mae_min']} sesgo={f['eta_sesgo_min']} "
                       f"aforo={f['aforo_acierto']} {'ALERTA: ' + f['motivo'] if f['alerta'] else ''}")

    @app.cli.command("pipeline-semanal")
    @click.option("--hoy", default=None, help="fecha de referencia AAAA-MM-DD (por defecto hoy en Lima)")
    def pipeline_semanal(hoy):
        """Lunes de madrugada: particiones, métricas de la semana y calibración del ETA."""
        from services import calibracion, monitoreo
        with ejecucion("pipeline-semanal") as r:
            r["particiones"] = particiones_job()
            r["monitoreo"] = monitoreo.monitoreo_semanal(hoy=dt.date.fromisoformat(hoy) if hoy else None)
            r["calibracion"] = calibracion.calibrar_todos()
            if r["monitoreo"]["estado"] == "sin_datos" and r["calibracion"]["estado"] == "sin_datos":
                r["estado"] = "sin_datos"                          # sin respuestas nuevas: no se cambió nada
            estado = r.get("estado", "ok")
        click.echo(f"pipeline-semanal: {estado}")
