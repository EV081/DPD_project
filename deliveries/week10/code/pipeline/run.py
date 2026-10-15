
from __future__ import annotations

import argparse
import os
import time

from pipeline import config


def _cmd_init_db() -> None:
    from storage import db

    db.ensure_database()
    conn = db.connect()
    try:
        db.init_schema(conn)
    finally:
        conn.close()
    print("[run] init-db OK")


def _cmd_demand(argv: list[str]) -> None:
    from pipeline import ingest_demand

    ingest_demand.main(argv)


def _cmd_live() -> None:
    from pipeline import ingest_tomtom

    ingest_tomtom.main()


def _cmd_loop(cada: float) -> None:
    from pipeline import ingest_tomtom
    from storage import db

    conn = db.connect()
    try:
        while True:
            ingest_tomtom.snapshot(conn)
            time.sleep(cada)
    except KeyboardInterrupt:
        print("[run] loop interrumpido")
    finally:
        conn.close()


def _cmd_predict(dia: str | None, modo: str, sistemas: list[str] | None) -> None:
    import datetime as dt

    from pipeline import predict

    predict.main(dt.date.fromisoformat(dia) if dia else None, modo, sistemas)


def _cmd_paraderos(opcional: bool = False) -> None:
    from pipeline import config, ingest_paraderos

    if opcional and not config.GEO_DIR.exists():
        print(f"[paraderos] omitido: no existe {config.GEO_DIR}")
        return
    ingest_paraderos.main()


def _cmd_export() -> None:
    from export.export_data import run

    run()


def _cmd_check() -> None:
    from storage import db

    conn = db.connect()
    try:
        tablas = [
            t["tabla"]
            for t in conn.execute(
                "SELECT tablename AS tabla FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            ).fetchall()
        ]
        print("[check] tablas:")
        for tabla in tablas:
            if tabla.startswith(("pg_", "sql_")):
                continue
            print(f"[check]   {tabla:<24} {db.table_count(conn, tabla):>10,}")
        existe = conn.execute(
            "SELECT count(*) AS n FROM information_schema.views "
            "WHERE table_name = 'demanda_fiable'"
        ).fetchone()["n"]
        print(
            "[check] vista demanda_fiable:",
            f"{db.table_count(conn, 'demanda_fiable'):,}" if existe else "AUSENTE",
        )
    finally:
        conn.close()
    export_dir = config.EXPORT_DIR
    if export_dir.exists():
        archivos = sorted(p for p in export_dir.rglob("*") if p.is_file())
        print(f"[check] export/ ({len(archivos)} archivos):")
        for p in archivos[:20]:
            print(f"[check]   {p.relative_to(export_dir)} ({p.stat().st_size:,} B)")
    else:
        print(f"[check] export/ aun no existe ({export_dir})")


def _cmd_predict_opcional() -> None:
    """Pronostico del dia siguiente dentro de ``full``: un fallo avisa pero no corta el arranque."""
    try:
        _cmd_predict(None, "ligero", None)
    except Exception as exc:  # noqa: BLE001
        print(f"[predict] omitido: {type(exc).__name__}: {exc}")


def _cmd_full(argv: list[str]) -> None:
    _cmd_init_db()
    _cmd_demand(argv)
    _cmd_paraderos(opcional=True)
    _cmd_predict_opcional()
    _cmd_live()
    _cmd_export()
    _cmd_check()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.run", description=__doc__
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("init-db", help="crea BD + esquema")

    p_demand = sub.add_parser("demand", help="ingesta de demanda")
    p_demand.add_argument("--solo-verify", action="store_true")

    sub.add_parser("live", help="snapshot de trafico")

    p_loop = sub.add_parser("loop", help="snapshots periodicos")
    p_loop.add_argument(
        "--cada",
        type=float,
        default=float(os.getenv("LOOP_SECONDS", "300")),
        help="segundos entre snapshots (default LOOP_SECONDS o 300 = 5 min)",
    )

    p_pred = sub.add_parser("predict", help="batch diario: llena prediccion")
    p_pred.add_argument("--dia", help="YYYY-MM-DD (default: dia siguiente al ultimo dato)")
    p_pred.add_argument("--modo", choices=["ligero", "principal"], default="ligero")
    p_pred.add_argument("--sistemas", nargs="+")

    sub.add_parser("paraderos", help="carga paraderos/rutas/trazados (GeoJSON) a la BD")

    sub.add_parser("export", help="exporta archivos a EXPORT_DIR")
    sub.add_parser("check", help="reporte de conteos")
    sub.add_parser("full", help="init-db + demand + paraderos + predict + live + export")

    args = parser.parse_args(argv)
    rest: list[str] = []

    if args.comando == "init-db":
        _cmd_init_db()
    elif args.comando == "demand":
        rest = ["--solo-verify"] if args.solo_verify else []
        _cmd_demand(rest)
    elif args.comando == "live":
        _cmd_live()
    elif args.comando == "loop":
        _cmd_loop(args.cada)
    elif args.comando == "predict":
        _cmd_predict(args.dia, args.modo, args.sistemas)
    elif args.comando == "paraderos":
        _cmd_paraderos()
    elif args.comando == "export":
        _cmd_export()
    elif args.comando == "check":
        _cmd_check()
    elif args.comando == "full":
        _cmd_full([])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
