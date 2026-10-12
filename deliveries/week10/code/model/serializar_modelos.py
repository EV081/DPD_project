"""Serializa los modelos del prototipo en ``deliveries/week10/models/`` (Issue #19).

Entrena con todo 2025 los modelos seleccionados en la evaluación v2 (validación 15–31 oct,
test 1 nov–31 dic) y escribe artefactos, model cards, manifiesto con sha256 y referencias
de entrada/salida para la verificación de recarga (``verificar_modelos.py``).

Uso (desde la raíz del repo):
    .venv/Scripts/python deliveries/week10/code/model/serializar_modelos.py
    .venv/Scripts/python deliveries/week10/code/model/serializar_modelos.py --evaluacion deliveries/week09/code/model/results_v2
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent
RAIZ = MODEL_DIR.parents[1]                       # deliveries/week10
REPO = RAIZ.parents[1]
sys.path.insert(0, str(MODEL_DIR))

import model_atu_common as M  # noqa: E402
import model_atu_v2 as V  # noqa: E402
from inferencia import ModeloSistema, leer_json, panel_desde_contexto, sha256  # noqa: E402

VERSION = "1.0.0"
SISTEMAS = ["metro_l1", "troncal", "corredor", "alimentador"]
FUENTES = RAIZ / "data" / "fuentes"
MODELS = RAIZ / "models"
DIA_REFERENCIA = pd.Timestamp("2026-01-01")       # día siguiente al último dato (feriado: Año Nuevo)
DIAS_CTX_REFERENCIA = 35
EVAL_DEFECTO = [MODEL_DIR / "results_v2", REPO / "deliveries" / "week09" / "code" / "model" / "results_v2"]
ARCHIVOS_EVAL = [
    "metricas_test.csv", "seleccion_validacion.csv", "diebold_mariano.csv", "intervalos_test.csv",
    "aforo_test.csv", "aforo_sensibilidad_umbrales.csv", "regla_u_test.csv", "anomalias_eval.csv",
    "resumen.json",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def escribir_json(ruta: Path, obj) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(V.a_json(obj), encoding="utf-8")


def ver(pkg: str) -> str | None:
    try:
        return version(pkg)
    except PackageNotFoundError:
        return None


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def git_codigo_modificado() -> bool | None:
    """True si el código de modelado tiene cambios sin commitear (el commit no basta para reproducir)."""
    rutas = [str(MODEL_DIR), str(REPO / "deliveries" / "week09" / "code" / "model")]
    try:
        out = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", *rutas],
                             capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except Exception:
        return None


def fila(df: pd.DataFrame, **filtros) -> dict:
    sub = df
    for k, v in filtros.items():
        sub = sub[sub[k] == v]
    return {} if sub.empty else sub.iloc[0].to_dict()


# ── Artefactos por sistema ────────────────────────────────────────────────

def specs_pronostico(n_est: int) -> dict:
    return {
        "lightgbm": {"tipo": "lightgbm", "archivo": "lightgbm.txt", "n_estimators": n_est,
                     "parametros": V.LGB_PARAMS, "features": V.LGB_FEATS,
                     "entrenamiento": "global por sistema, objetivo Tweedie, lags >= 24 h (sin recursión)"},
        "chronos2": {"tipo": "foundation_zero_shot", "repo": V.CHRONOS2_ID, "revision": V.CHRONOS2_REV,
                     "contexto_horas": V.CHRONOS2_CTX, "covariables": {"feriado": "pasada y futura"},
                     "pesos": "no versionados en git (478 MB); se descargan de Hugging Face con la revisión fija"},
        "chronos_bolt": {"tipo": "foundation_zero_shot", "repo": V.BOLT_ID, "revision": V.BOLT_REV,
                         "contexto_dias": 60, "pesos": "Hugging Face, revisión fija (191 MB)"},
        "autoets": {"tipo": "statsforecast", "modelo": "AutoETS(season_length=24)", "ventana_dias": 56,
                    "nota": "se reajusta en cada pronóstico con la ventana indicada"},
        "mstl": {"tipo": "statsforecast", "modelo": "MSTL([24, 168], trend=AutoETS(ZZN))", "ventana_dias": 56,
                 "nota": "se reajusta en cada pronóstico con la ventana indicada"},
        "media_4sem": {"tipo": "baseline", "definicion": "media de la misma hora en los 4 mismos días previos"},
    }


def serializar_sistema(sistema: str, eval_dir: Path) -> dict:
    dst = MODELS / sistema
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    ev = eval_dir / sistema
    resumen = leer_json(ev / "resumen.json")
    principal = resumen["ganador_validacion"]
    n_est = int(resumen["lgb_n_estimators"])
    P = V.cargar_panel(sistema, RAIZ)
    log(f"[{sistema}] panel {P.Y.shape} | principal={principal} | LightGBM {n_est} árboles")

    # copia de la evaluación (métricas vs baselines) para que week10 sea autocontenida
    (MODELS / "evaluacion" / sistema).mkdir(parents=True, exist_ok=True)
    for f in ARCHIVOS_EVAL:
        if (ev / f).exists():
            shutil.copy2(ev / f, MODELS / "evaluacion" / sistema / f)

    # 1) LightGBM final (todo 2025)
    lgbm = V.LGBMDirecto(n_estimators=n_est).fit(P, len(P.index))
    lgbm.model.booster_.save_model(str(dst / "lightgbm.txt"))
    escribir_json(dst / "lightgbm_meta.json", {
        "features": V.LGB_FEATS, "series": P.series, "n_estimators": n_est, "parametros": V.LGB_PARAMS,
        "entrenado_hasta": str(P.index[-1]), "filas_entrenamiento": (len(P.index) - V.MIN_P_LGB) // 24 * P.S * 24,
    })

    # 2) Aforo: configuración de crowding + clasificador directo (respaldo sin pronóstico)
    cfg, df_ops = V.config_aforo(P, FUENTES)
    escribir_json(dst / "crowding_config.json", cfg.to_dict())
    import joblib
    from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest

    d = df_ops.copy()
    d["hora_sin"] = np.sin(2 * np.pi * d["hora_n"] / 24)
    d["hora_cos"] = np.cos(2 * np.pi * d["hora_n"] / 24)
    d["es_feriado_i"] = d["es_feriado"].astype(int)
    cod = {s: i for i, s in enumerate(sorted(d["serie_id"].unique()))}
    d["est_cod"] = d["serie_id"].map(cod)
    feats_clf = ["hora_n", "hora_sin", "hora_cos", "mes", "dow", "es_feriado_i", "est_cod"]
    tr = d.sample(min(200_000, len(d)), random_state=0)
    clf = HistGradientBoostingClassifier(max_depth=8, random_state=0).fit(tr[feats_clf], tr["aforo"])
    joblib.dump(clf, dst / "aforo_histgb.joblib")
    escribir_json(dst / "aforo_histgb_meta.json", {
        "features": feats_clf, "codigos_unidad": cod, "clases": list(clf.classes_),
        "parametros": {"max_depth": 8, "random_state": 0}, "filas_entrenamiento": len(tr),
        "uso": "respaldo cuando no hay pronóstico; el producto usa la cascada pronóstico → crowding → clase",
    })

    # 3) Anomalías: detector por residuos (principal) + IsolationForest de week08 (comparación)
    det = V.residuo_diario_baseline(P, pd.Timestamp("2025-02-01"))
    ult = det["residuo_rel"].to_numpy()[-56:]
    med = float(np.median(ult))
    mad = float(np.median(np.abs(ult - med)) * 1.4826)
    cols_if = ["Validaciones", "hora_n", "dow", "mes", "Headway_Min", "Ocupacion_proxy"]
    tr_if = df_ops[cols_if].fillna(0).sample(min(150_000, len(df_ops)), random_state=0)
    ifo = IsolationForest(contamination=0.05, random_state=0, n_jobs=-1).fit(tr_if)
    joblib.dump(ifo, dst / "isolation_forest.joblib")
    ev_an = pd.read_csv(ev / "anomalias_eval.csv")
    escribir_json(dst / "anomalias.json", {
        "detector": "residuo diario del sistema vs media de las 4 semanas previas, z robusto (mediana/MAD)",
        "ventana_dias": 56, "umbral_z": 3.0,
        "referencia": {"mediana": med, "mad": mad, "desde": str(det["dia"].iloc[-56].date()),
                       "hasta": str(det["dia"].iloc[-1].date())},
        "isolation_forest": {"archivo": "isolation_forest.joblib", "features": cols_if,
                             "umbral_score": float(np.quantile(-ifo.score_samples(tr_if), 0.95))},
        "evaluacion_2025": ev_an.to_dict(orient="records"),
    })

    # 4) Intervalos conformal del modelo principal (últimos 14 días de test)
    conf_all = leer_json(ev / "conformal_produccion.json")
    escribir_json(dst / "conformal.json", conf_all[principal])
    escribir_json(dst / "conformal_ligero.json", conf_all["lightgbm"])

    # 5) Model card
    specs = specs_pronostico(n_est)
    tab = pd.read_csv(ev / "metricas_test.csv")
    af = pd.read_csv(ev / "aforo_test.csv")
    ru = pd.read_csv(ev / "regla_u_test.csv")
    inter = pd.read_csv(ev / "intervalos_test.csv")
    dm = pd.read_csv(ev / "diebold_mariano.csv")
    base_mejor = (tab[(tab["estrato"] == "todos") & tab["modelo"].isin(V.BASELINES)]
                  .sort_values("WMAPE").iloc[0].to_dict())
    met_p = {e: fila(tab, modelo=principal, estrato=e) for e in ("todos", "normales", "atipicos")}
    af_p = fila(af, modelo=f"cascada_{principal}")
    ru_p = fila(ru, modelo=f"cascada_{principal}")
    criterios = {
        "RNF-01 (accuracy >= 0.75 y F1-macro >= 0.72)":
            bool(af_p.get("accuracy", 0) >= 0.75 and af_p.get("f1_macro", 0) >= 0.72),
        "AC-02 (F1 >= 0.72 en las 3 clases)":
            bool(min(af_p.get("f1_Asientos", 0), af_p.get("f1_De_pie", 0), af_p.get("f1_Saturado", 0)) >= 0.72),
        "AC-03 (recomendación correcta >= 80 %)": bool(ru_p.get("acuerdo", 0) >= 0.80),
    }
    miembros = resumen.get("top3_validacion", []) if principal == "ensemble" else []
    met_lgb = fila(tab, modelo="lightgbm", estrato="todos")
    dm_lgb = dm[dm["vs"] == "lightgbm"]["p_valor"]
    ligero = {
        "modelo": "lightgbm", "wmape_test": met_lgb.get("WMAPE"), "mae_test": met_lgb.get("MAE"),
        "dm_p_vs_principal": None if dm_lgb.empty else float(dm_lgb.iloc[0]),
        "uso": "sin torch/Chronos; inferencia en milisegundos; para servidores con poca memoria o latencia estricta",
    }
    card = {
        "nombre": f"urbansafe-demanda-{sistema}", "version": VERSION, "sistema": sistema,
        "titulo": M.SISTEMAS[sistema]["titulo"], "grano": M.SISTEMAS[sistema]["grano"],
        "series": P.series, "n_series": P.S,
        "objetivo": "validaciones (abordajes registrados) por unidad y hora, horizonte 24 h, "
                    "contexto hasta el día previo 23:00",
        "pronostico": {"modelo_principal": principal, "modelos": specs,
                       "ensemble": {"miembros": miembros, "pesos": "promedio simple"} if miembros else None,
                       "seleccion": "menor WMAPE en validación 15–31 oct 2025 (no en test)",
                       "modo_ligero": ligero},
        "protocolo": {"validacion": [str(V.DIAS_VAL[0].date()), str(V.DIAS_VAL[-1].date())],
                      "test": [str(V.DIAS_TEST[0].date()), str(V.DIAS_TEST[-1].date())],
                      "rolling_origin": "diario", "refit_lightgbm_dias": 7},
        "metricas_test": {"principal": met_p, "mejor_baseline": base_mejor,
                          "diebold_mariano_vs": dm.to_dict(orient="records")},
        "intervalos_80": inter[inter["modelo"] == principal].to_dict(orient="records"),
        "aforo_test": af.to_dict(orient="records"),
        "regla_u_test": ru.to_dict(orient="records"),
        "eta": {"definicion": "headway(bucket) × factor(clase) con factores 1.0/1.1/1.3",
                "mae_proxy_min": af_p.get("eta_mae_min"),
                "nota": "sin GPS/AVL no hay llegadas reales: el MAE mide el error del ETA inducido por el "
                        "modelo (clase predicha vs clase observada), no contra llegadas reales"},
        "criterios_aceptacion": criterios,
        "limitaciones": [
            "validaciones = abordajes, no ocupación a bordo; el aforo es un proxy de presión (crowding_index)",
            "umbrales p60/p90 por franja: 'Saturado' es relativo a la franja (ver aforo_sensibilidad_umbrales.csv)",
            "un solo año de historia (2025); feriados móviles 2026 tomados del calendario oficial",
            "paros de transportistas no se anticipan: el detector de anomalías los marca después",
        ],
    }
    escribir_json(dst / "model_card.json", card)

    # 6) Referencias de entrada/salida para verificar la recarga
    ctx_ini = len(P.index) - DIAS_CTX_REFERENCIA * 24
    contexto = pd.DataFrame(P.Y[ctx_ini:], index=P.index[ctx_ini:], columns=P.series)
    contexto.index.name = "Fecha_Hora"
    contexto.to_csv(dst / "referencia_contexto.csv")

    modelo = ModeloSistema.cargar(sistema, MODELS, verificar_hash=False)
    salida = modelo.pronosticar(contexto, DIA_REFERENCIA)
    salida.to_csv(dst / "referencia_salida.csv", index=False)
    modelo.pronosticar(contexto, DIA_REFERENCIA, modo="ligero").to_csv(dst / "referencia_salida_ligero.csv", index=False)

    Pr, pr = panel_desde_contexto(sistema, contexto, DIA_REFERENCIA)
    X_lgb = V.features_dia(Pr.Y, pr, Pr.index[pr])
    X_clf = pd.DataFrame({"hora_n": np.tile(np.arange(24), P.S), "mes": DIA_REFERENCIA.month,
                          "dow": DIA_REFERENCIA.dayofweek, "es_feriado_i": 1,
                          "est_cod": np.repeat([cod.get(s, -1) for s in P.series], 24)})
    X_clf["hora_sin"] = np.sin(2 * np.pi * X_clf["hora_n"] / 24)
    X_clf["hora_cos"] = np.cos(2 * np.pi * X_clf["hora_n"] / 24)
    X_if = df_ops[cols_if].fillna(0).tail(500).astype(float)
    np.savez_compressed(
        dst / "referencia_artefactos.npz",
        lgb_X=X_lgb, lgb_pred=lgbm.model.booster_.predict(X_lgb),
        clf_X=X_clf[feats_clf].to_numpy(dtype=float), clf_proba=clf.predict_proba(X_clf[feats_clf]),
        if_X=X_if.to_numpy(dtype=float), if_score=ifo.score_samples(X_if),
    )
    log(f"[{sistema}] artefactos listos en {dst}")
    return {
        "sistema": sistema, "modelo_principal": principal, "miembros_ensemble": miembros,
        "wmape_test": met_p["todos"].get("WMAPE"), "mae_test": met_p["todos"].get("MAE"),
        "mase_test": met_p["todos"].get("MASE"), "wmape_test_ligero": ligero["wmape_test"],
        "wmape_mejor_baseline": base_mejor.get("WMAPE"),
        "mejor_baseline": base_mejor.get("modelo"),
        "aforo_f1_weighted": af_p.get("f1_weighted"), "aforo_f1_macro": af_p.get("f1_macro"),
        "regla_u_acuerdo": ru_p.get("acuerdo"), "criterios": criterios,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sistemas", nargs="+", default=SISTEMAS, choices=SISTEMAS)
    ap.add_argument("--evaluacion", type=Path, default=None,
                    help="carpeta results_v2 con la evaluación (por defecto week10 o week09)")
    args = ap.parse_args()
    eval_dir = args.evaluacion or next(p for p in EVAL_DEFECTO if (p / "metro_l1" / "resumen.json").exists())
    eval_dir = Path(eval_dir).resolve()
    log(f"Evaluación: {eval_dir}")
    MODELS.mkdir(parents=True, exist_ok=True)

    resumenes = [serializar_sistema(s, eval_dir) for s in args.sistemas]

    escribir_json(MODELS / "calendario_eventos.json", {
        "feriados": V.FERIADOS, "paros_2025": {k: {"descripcion": d, "fuente": u} for k, (d, u) in V.PAROS.items()},
        "visperas": V.VISPERAS,
    })
    escribir_json(MODELS / "regla_u.json", {
        "version": VERSION, "entradas": ["clase de aforo (h)", "clase de aforo (h+1)", "eta_min"],
        "reglas": [
            {"si": "clase == Saturado y eta <= 10 y clase_siguiente != Saturado", "entonces": "esperar_siguiente"},
            {"si": "clase == Saturado y eta > 10", "entonces": "cambiar_paradero"},
            {"si": "en otro caso", "entonces": "abordar"},
        ],
        "origen": "decision_u de model_atu_common (week08), vectorizada en model_atu_v2.recomendaciones",
    })
    escribir_json(MODELS / "eta_config.json", {
        "version": VERSION,
        "eta_min": "headway(bucket LAB/SAB/DOM, feriado = DOM) × factor(clase)",
        "factores": V.FACTOR_ETA, "eta2_min": "eta_min + headway (RF-02: dos próximas unidades)",
        "headways": "por sistema en <sistema>/crowding_config.json",
        "limitacion": "sin GPS/AVL el ETA no se valida contra llegadas reales",
    })

    datos = RAIZ / "data_processed" / "clean" / "demanda_consolidada_fiable.parquet"
    artefactos = {}
    for f in sorted(MODELS.rglob("*")):
        if f.is_file() and f.name not in ("manifest.json", "verify_report.json", "verify_report.md", "README.md"):
            artefactos[f.relative_to(MODELS).as_posix()] = {"bytes": f.stat().st_size, "sha256": sha256(f)}
    manifiesto = {
        "nombre": "urbansafe-ai-modelos", "version": VERSION,
        "creado_en": dt.datetime.now().isoformat(timespec="seconds"), "git_commit": git_commit(),
        "codigo_con_cambios_sin_commit": git_codigo_modificado(),
        "issue": "EV081/DPD_project#19",
        "datos": {"archivo": "data_processed/clean/demanda_consolidada_fiable.parquet",
                  "sha256": sha256(datos) if datos.exists() else None,
                  "filas": int(len(pd.read_parquet(datos, columns=["sistema"]))) if datos.exists() else None,
                  "periodo": "2025-01-01 → 2025-12-31"},
        "entorno": {"python": platform.python_version(), "plataforma": platform.platform(),
                    **{p: ver(p) for p in ("numpy", "pandas", "scikit-learn", "lightgbm", "statsforecast",
                                           "torch", "chronos-forecasting", "joblib")}},
        "evaluacion": str(eval_dir.relative_to(REPO)) if eval_dir.is_relative_to(REPO) else str(eval_dir),
        "dia_referencia": str(DIA_REFERENCIA.date()),
        "resumen": resumenes, "artefactos": artefactos,
        "seguridad": "los .joblib son pickles: cargar solo artefactos cuyo sha256 coincida con este manifiesto",
    }
    escribir_json(MODELS / "manifest.json", manifiesto)
    log(f"manifest.json: {len(artefactos)} artefactos | versión {VERSION}")


if __name__ == "__main__":
    main()
