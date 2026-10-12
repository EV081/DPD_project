"""Verificación de recarga de los modelos serializados (Issue #19).

1. sha256 de cada artefacto contra ``models/manifest.json``.
2. Recarga LightGBM, HistGB e IsolationForest y compara con las predicciones guardadas al serializar.
3. Re-ejecuta el pronóstico completo del día de referencia (``inferencia.ModeloSistema``) y lo compara
   con ``referencia_salida.csv`` (valores numéricos con tolerancia, clases y recomendaciones exactas).

Uso (desde la raíz del repo):
    .venv/Scripts/python deliveries/week10/code/model/verificar_modelos.py
Escribe ``models/verify_report.json`` y ``models/verify_report.md``; sale con código 1 si algo falla.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODEL_DIR))

from inferencia import MODELS_DIR, ModeloSistema, leer_json, sha256  # noqa: E402

NUMERICAS = ["validaciones_pron", "banda80_lo", "banda80_hi", "crowding_index", "eta_min", "eta2_min"]
CATEGORICAS = ["aforo", "recomendacion", "modelo"]


def _check(nombre: str, ok: bool, detalle: str = "") -> dict:
    print(f"  [{'PASS' if ok else 'FAIL'}] {nombre}{(' — ' + detalle) if detalle else ''}", flush=True)
    return {"check": nombre, "ok": bool(ok), "detalle": detalle}


def verificar_hashes(models_dir: Path, manifiesto: dict) -> list[dict]:
    out = []
    for rel, meta in manifiesto["artefactos"].items():
        ruta = models_dir / rel
        if not ruta.exists():
            out.append(_check(f"sha256 {rel}", False, "no existe"))
            continue
        out.append(_check(f"sha256 {rel}", sha256(ruta) == meta["sha256"]))
    return out


def verificar_sistema(models_dir: Path, sistema: str, dia_ref: str, rtol: float) -> list[dict]:
    import joblib
    import lightgbm as lgb

    print(f"\n[{sistema}]", flush=True)
    carpeta = models_dir / sistema
    ref = np.load(carpeta / "referencia_artefactos.npz", allow_pickle=False)
    out = []

    booster = lgb.Booster(model_file=str(carpeta / "lightgbm.txt"))
    pred = booster.predict(ref["lgb_X"])
    out.append(_check(f"{sistema} LightGBM recarga", np.allclose(pred, ref["lgb_pred"], rtol=1e-9, atol=1e-9),
                      f"max |Δ| = {np.max(np.abs(pred - ref['lgb_pred'])):.2e}"))

    clf = joblib.load(carpeta / "aforo_histgb.joblib")
    feats_clf = leer_json(carpeta / "aforo_histgb_meta.json")["features"]
    proba = clf.predict_proba(pd.DataFrame(ref["clf_X"], columns=feats_clf))
    out.append(_check(f"{sistema} HistGB recarga", np.allclose(proba, ref["clf_proba"], rtol=1e-9, atol=1e-12),
                      f"max |Δ| = {np.max(np.abs(proba - ref['clf_proba'])):.2e}"))

    ifo = joblib.load(carpeta / "isolation_forest.joblib")
    feats_if = leer_json(carpeta / "anomalias.json")["isolation_forest"]["features"]
    score = ifo.score_samples(pd.DataFrame(ref["if_X"], columns=feats_if))
    out.append(_check(f"{sistema} IsolationForest recarga", np.allclose(score, ref["if_score"], rtol=1e-9),
                      f"max |Δ| = {np.max(np.abs(score - ref['if_score'])):.2e}"))

    modelo = ModeloSistema.cargar(sistema, models_dir, verificar_hash=True)
    ctx = pd.read_csv(carpeta / "referencia_contexto.csv", index_col="Fecha_Hora", parse_dates=True)
    ctx.columns = [str(c) for c in ctx.columns]
    # Chronos en CPU puede variar en el último decimal entre equipos: tolerancia relativa configurable
    tol = rtol if modelo.principal in ("chronos2", "chronos_bolt", "ensemble") else 1e-9
    for modo, archivo, tol_modo in [("principal", "referencia_salida.csv", tol),
                                    ("ligero", "referencia_salida_ligero.csv", 1e-9)]:
        t = time.time()
        nueva = modelo.pronosticar(ctx, dia_ref, modo=modo)
        seg = time.time() - t
        esperada = pd.read_csv(carpeta / archivo)
        etiqueta = f"{sistema} pronóstico {modo}"
        ok_forma = list(nueva.columns) == list(esperada.columns) and len(nueva) == len(esperada)
        out.append(_check(f"{etiqueta}: columnas y filas", ok_forma, f"{len(nueva)} filas"))
        if ok_forma:
            for c in NUMERICAS:
                a, b = nueva[c].to_numpy(float), esperada[c].to_numpy(float)
                out.append(_check(f"{etiqueta} {c}", np.allclose(a, b, rtol=tol_modo, atol=1e-6),
                                  f"max |Δ| = {np.max(np.abs(a - b)):.2e}"))
            for c in CATEGORICAS:
                igual = (nueva[c].astype(str).to_numpy() == esperada[c].astype(str).to_numpy()).mean()
                out.append(_check(f"{etiqueta} {c}", igual == 1.0, f"{igual:.2%} idénticas"))
        usado = modelo.principal if modo == "principal" else "lightgbm"
        out.append(_check(f"{etiqueta}: latencia (informativa)", True, f"{seg:.2f} s con {usado}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", type=Path, default=MODELS_DIR)
    ap.add_argument("--rtol", type=float, default=1e-4, help="tolerancia relativa para modelos fundacionales")
    args = ap.parse_args()
    models_dir = args.models.resolve()
    manifiesto = leer_json(models_dir / "manifest.json")
    print(f"Manifiesto {manifiesto['nombre']} v{manifiesto['version']} ({len(manifiesto['artefactos'])} artefactos)")

    print("\n[sha256]")
    checks = verificar_hashes(models_dir, manifiesto)
    for r in manifiesto["resumen"]:
        checks += verificar_sistema(models_dir, r["sistema"], manifiesto["dia_referencia"], args.rtol)

    ok = all(c["ok"] for c in checks)
    reporte = {"verificado_en": dt.datetime.now().isoformat(timespec="seconds"),
               "version": manifiesto["version"], "ok": ok,
               "n_checks": len(checks), "n_fail": sum(not c["ok"] for c in checks), "checks": checks}
    (models_dir / "verify_report.json").write_text(json.dumps(reporte, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")
    filas = "\n".join(f"| {c['check']} | {'✅' if c['ok'] else '❌'} | {c['detalle']} |" for c in checks)
    (models_dir / "verify_report.md").write_text(
        f"# Verificación de recarga — modelos v{manifiesto['version']}\n\n"
        f"Fecha: {reporte['verificado_en']} · Resultado: **{'OK' if ok else 'FALLA'}** "
        f"({reporte['n_checks'] - reporte['n_fail']}/{reporte['n_checks']} checks)\n\n"
        f"| Check | Estado | Detalle |\n|---|:---:|---|\n{filas}\n", encoding="utf-8")
    print(f"\nRESULTADO: {'OK' if ok else 'FALLA'} ({reporte['n_checks'] - reporte['n_fail']}/{reporte['n_checks']})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
