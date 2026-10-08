from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from pipeline import config
from storage import db

MUESTRA_LIMITE = 100_000

ARCHIVOS_MODELO = [
    "manifiesto_modelamiento.json",
    "metricas_modelos.csv",
    "bakeoff_wmape_todos.csv",
    "eval_walkforward_modelos.csv",
]


def _query(conn, sql: str) -> pd.DataFrame:
    cur = conn.cursor()
    try:
        cur.execute(sql)
        filas = cur.fetchall()
        columnas = [d[0] for d in cur.description]
    finally:
        cur.close()
    return pd.DataFrame(filas, columns=columnas)


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def run() -> Path:
    out = config.EXPORT_DIR
    out.mkdir(parents=True, exist_ok=True)

    conteos: dict[str, int] = {}
    conn = db.connect()
    try:
        resumen = _query(
            conn,
            "SELECT sistema, grano, count(*) AS filas, "
            "count(DISTINCT unidad) AS unidades, "
            "sum(validaciones) AS validaciones, "
            "min(fecha) AS fecha_min, max(fecha) AS fecha_max "
            "FROM demanda_fiable GROUP BY sistema, grano ORDER BY sistema",
        )
        resumen.to_csv(out / "resumen_por_sistema.csv", index=False)

        perfil = _query(
            conn,
            "SELECT sistema, hora, "
            "round(avg(validaciones)::numeric, 3) AS promedio, "
            "round(sum(validaciones)::numeric, 1) AS total "
            "FROM demanda_fiable GROUP BY sistema, hora "
            "ORDER BY sistema, hora",
        )
        perfil.to_csv(out / "perfil_horario.csv", index=False)

        muestra = _query(
            conn,
            "SELECT * FROM demanda_fiable "
            "ORDER BY fecha, hora, sistema, unidad, sentido, validaciones "
            f"LIMIT {MUESTRA_LIMITE}",
        )
        muestra.to_csv(
            out / "muestra_demanda_fiable.csv", index=False, date_format="%Y-%m-%d"
        )

        trafico = _query(
            conn,
            "SELECT segmento, lat, lon, actual_speed_kph, free_flow_speed_kph, "
            "ratio_congestion, fuente, actualizado_en "
            "FROM trafico_en_vivo ORDER BY segmento",
        )
        (out / "trafico_tomtom.json").write_text(
            json.dumps(
                {
                    "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
                    "segmentos": trafico.to_dict(orient="records"),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        for tabla in list(config.FILAS_ESPERADAS) + ["trafico_en_vivo"]:
            conteos[tabla] = db.table_count(conn, tabla)
        conteos["demanda_fiable"] = db.table_count(conn, "demanda_fiable")
    finally:
        conn.close()

    copiados: list[str] = []
    src = config.MODELO_OUTPUTS_DIR
    if src.exists():
        dst = out / "modelo"
        dst.mkdir(exist_ok=True)
        for nombre in ARCHIVOS_MODELO:
            origen = src / nombre
            if origen.exists():
                shutil.copy2(origen, dst / nombre)
                copiados.append(f"modelo/{nombre}")
    else:
        print(f"[export] aviso: no se encontró {src} (outputs de modelo)")

    archivos: dict[str, dict] = {}
    for ruta in sorted(out.rglob("*")):
        if ruta.is_file() and ruta.name != "manifiesto_export.json":
            archivos[str(ruta.relative_to(out))] = {
                "bytes": ruta.stat().st_size,
                "sha256": _sha256(ruta),
            }

    manifiesto = {
        "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
        "fuente": str(config.CLEAN_DIR),
        "limite_muestra": MUESTRA_LIMITE,
        "conteos_bd": conteos,
        "archivos": archivos,
    }
    (out / "manifiesto_export.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"[export] OK -> {out}: {len(archivos) + 1} archivos, "
        f"muestra={len(muestra):,} filas, "
        f"modelo/copiados={len(copiados)}, "
        f"demanda_fiable={conteos.get('demanda_fiable', 0):,}"
    )
    return out


if __name__ == "__main__":
    run()
