"""Exporta los datos procesados de week09 a CSV versionable (``data_csv/``).

Lee ``data_processed/clean/`` (salida de los EDA) y escribe:

* ``panel_horario_<sistema>.csv``: validaciones por unidad × fecha × hora (cobertura ≥ 90 %),
  el mismo panel que consumen los modelos (paraderos y sentidos sumados a nivel de ruta);
* ``calidad_cobertura.csv``: cobertura por unidad (tabla de control de fiabilidad);
* ``calendario_eventos_2025.csv``: 16 feriados, paros de transportistas verificados y vísperas.

Uso:
    .venv/Scripts/python deliveries/week09/code/scripts/exportar_csv.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CLEAN = RAIZ / "data_processed" / "clean"
SALIDA = RAIZ / "data_csv"
sys.path.insert(0, str(RAIZ / "code" / "model"))

import model_atu_v2 as V  # noqa: E402


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    cols = ["sistema", "unidad", "fecha", "hora", "dia_semana", "tipo_dia", "es_feriado", "validaciones"]
    df = pd.read_parquet(CLEAN / "demanda_consolidada_fiable.parquet", columns=cols)
    df["fecha"] = pd.to_datetime(df["fecha"])
    for sistema, g in df.groupby("sistema"):
        panel = (g.groupby(["unidad", "fecha", "hora"], as_index=False)
                 .agg(validaciones=("validaciones", "sum"), dia_semana=("dia_semana", "first"),
                      tipo_dia=("tipo_dia", "first"), es_feriado=("es_feriado", "first")))
        panel["tipo_evento"] = panel["fecha"].map(V.tipo_evento)
        panel.insert(0, "sistema", sistema)
        panel = panel.sort_values(["unidad", "fecha", "hora"])
        panel["validaciones"] = panel["validaciones"].round().astype("int64")
        ruta = SALIDA / f"panel_horario_{sistema}.csv"
        panel.to_csv(ruta, index=False, date_format="%Y-%m-%d")
        print(f"  {ruta.name:<34} {len(panel):>9,} filas  {ruta.stat().st_size / 1e6:6.1f} MB  "
              f"unidades={panel['unidad'].nunique()}")
    shutil.copy2(CLEAN / "calidad_cobertura.csv", SALIDA / "calidad_cobertura.csv")
    V.calendario_eventos(2025).to_csv(SALIDA / "calendario_eventos_2025.csv", index=False)
    print(f"  calidad_cobertura.csv + calendario_eventos_2025.csv → {SALIDA}")


if __name__ == "__main__":
    main()
