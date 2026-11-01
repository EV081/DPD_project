import hashlib
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]          # deliveries/week12
BASE = RAIZ / "data_processed" / "eje2"
RAW = BASE / "raw"
SPL = BASE / "splits"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    archivos = sorted(RAW.glob("denuncias_*.parquet"))
    if not archivos:
        raise FileNotFoundError(f"Faltan los parquet por año en {RAW}; corre 00_csv_a_parquet.py")
    SPL.mkdir(parents=True, exist_ok=True)
    # se juntan todos los años y se recupera el orden original del CSV unificado
    d = pd.concat([pd.read_parquet(f) for f in archivos], ignore_index=True).sort_values("_fila").drop(columns="_fila").reset_index(drop=True)
    print(f"{len(archivos)} archivos -> {len(d):,} filas")
    f = d["fecha_hora_hecho"]
    partes = {
        "train": d[f < "2023-01-01"],
        "valid": d[(f >= "2023-01-01") & (f < "2024-01-01")],
        "test": d[(f >= "2024-01-01") & (f < "2024-09-01")],
        "reserva": d[f >= "2024-09-01"],
    }
    assert sum(len(p) for p in partes.values()) == len(d), "la partición debe cubrir todas las filas"
    manifest = {"criterio": "fecha_hora_hecho", "total": len(d), "splits": {}}
    for nombre, p in partes.items():
        ruta = SPL / f"{nombre}.parquet"
        p.to_parquet(ruta, index=False, compression="zstd")
        manifest["splits"][nombre] = {
            "filas": len(p),
            "desde": str(p["fecha_hora_hecho"].min()),
            "hasta": str(p["fecha_hora_hecho"].max()),
            "sha256": sha256(ruta),
        }
        print(f"{nombre}: {len(p):,} filas  {manifest['splits'][nombre]['desde']} -> {manifest['splits'][nombre]['hasta']}")
    (SPL / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print("OK", SPL / "manifest.json")


if __name__ == "__main__":
    main()
