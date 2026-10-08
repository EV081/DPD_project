
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


def _cmd_full(argv: list[str]) -> None:
    _cmd_init_db()
    _cmd_demand(argv)
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
        default=float(os.getenv("LOOP_SECONDS", "60")),
        help="segundos entre snapshots (default LOOP_SECONDS o 60)",
    )

    sub.add_parser("export", help="exporta archivos a EXPORT_DIR")
    sub.add_parser("check", help="reporte de conteos")
    sub.add_parser("full", help="init-db + demand + live + export")

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
    elif args.comando == "export":
        _cmd_export()
    elif args.comando == "check":
        _cmd_check()
    elif args.comando == "full":
        _cmd_full([])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
