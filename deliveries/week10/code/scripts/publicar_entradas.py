"""Copia a ``week10/datos_entrada`` (versionado) las entradas que consume el pipeline.

``data_processed/`` y ``data/`` están en .gitignore (crudos y fuentes pesados). Esta carpeta guarda solo
lo mínimo para que un clon levante todo con ``docker compose up``: los parquets limpios de demanda y los
GeoJSON de paraderos/rutas. Ejecutar tras regenerarlos (EDA, ``build_trazados.py``):

  python -m scripts.publicar_entradas            # desde week10/code
"""
from __future__ import annotations

import shutil
from pathlib import Path

WEEK10 = Path(__file__).resolve().parents[2]
CLEAN_ORIGEN = WEEK10 / "data_processed" / "clean"
GEO_ORIGEN = WEEK10 / "data" / "fuentes" / "geo"
DESTINO = WEEK10 / "datos_entrada"

CLEAN = [
    "alimentador_hora.parquet", "alimentador_tarifa.parquet", "corredores_hora.parquet",
    "metro_l1_hora.parquet", "metro_l1_total_hora.parquet", "troncal_hora.parquet",
    "calidad_cobertura.csv",
    "demanda_consolidada_fiable.parquet",   # paridad en tests/test_ingest.py
]
GEO = [
    "puntos_metro_l1", "puntos_troncal", "puntos_corredores", "paradas_corredores",
    "paradas_alimentadores", "puntos_metropolitano_servicios", "trazado_metro_l1", "trazado_troncal",
    "trazados_corredores", "trazados_alimentadores_atu", "trazados_metropolitano_servicios",
]


def main() -> None:
    n = 0
    for origen, destino, nombres in (
        (CLEAN_ORIGEN, DESTINO / "clean", CLEAN),
        (GEO_ORIGEN, DESTINO / "geo", [f"{g}.geojson" for g in GEO]),
    ):
        destino.mkdir(parents=True, exist_ok=True)
        for nombre in nombres:
            src = origen / nombre
            if not src.exists():
                raise SystemExit(f"[publicar] falta {src}")
            shutil.copy2(src, destino / nombre)
            n += 1
    print(f"[publicar] {n} archivos copiados a {DESTINO}")


if __name__ == "__main__":
    main()
