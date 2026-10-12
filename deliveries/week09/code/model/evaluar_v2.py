"""Corre la evaluación v2 por sistema y guarda resultados (week09).

Uso (desde la raíz del repo):
    .venv/Scripts/python deliveries/week09/code/model/evaluar_v2.py                 # 4 sistemas
    .venv/Scripts/python deliveries/week09/code/model/evaluar_v2.py --sistemas metro_l1
    .venv/Scripts/python deliveries/week09/code/model/evaluar_v2.py --solo-analisis  # reusa predicciones

Salidas:
    code/model/outputs_v2/<sistema>/resultado.npz   predicciones día a día (gitignored)
    code/model/results_v2/<sistema>/*.csv|json      métricas y tablas (versionadas)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent
RAIZ = MODEL_DIR.parents[1]
sys.path.insert(0, str(MODEL_DIR))

import model_atu_common as M  # noqa: E402
import model_atu_v2 as V  # noqa: E402

FUENTES = RAIZ / "data" / "fuentes"
OUT = MODEL_DIR / "outputs_v2"
RES = MODEL_DIR / "results_v2"
SISTEMAS = ["metro_l1", "troncal", "corredor", "alimentador"]
CANDIDATOS = ["autoets", "mstl", "lightgbm", "chronos_bolt", "chronos2"]
# chronos2_xl (cross-learning) se probó en L1: mismo WMAPE que chronos2 y el doble de costo.
OPCIONALES = ["chronos2_xl"]


def log(msg: str) -> None:
    print(msg, flush=True)


# ── Predicciones ──────────────────────────────────────────────────────────

def guardar_resultado(R: V.Resultado, extra: dict, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    arrays = {"y": R.y, "obs": R.obs, "escala": R.escala}
    for m, a in R.point.items():
        arrays[f"point__{m}"] = a
    for m, a in R.quant.items():
        if a is not None:
            arrays[f"quant__{m}"] = a.astype(np.float32)
    np.savez_compressed(destino / "resultado.npz", **arrays)
    meta = {"sistema": R.sistema, "dias": [d.date().isoformat() for d in R.dias],
            "series": list(R.series), "segundos": R.segundos, **extra}
    (destino / "resultado_meta.json").write_text(V.a_json(meta), encoding="utf-8")


def cargar_resultado(sistema: str) -> tuple[V.Resultado, dict]:
    src = OUT / sistema
    meta = json.loads((src / "resultado_meta.json").read_text(encoding="utf-8"))
    z = np.load(src / "resultado.npz", allow_pickle=False)
    point = {k.split("__", 1)[1]: z[k] for k in z.files if k.startswith("point__")}
    quant = {m: None for m in point}
    quant.update({k.split("__", 1)[1]: z[k].astype(np.float64)
                  for k in z.files if k.startswith("quant__")})
    R = V.Resultado(sistema, pd.DatetimeIndex(meta["dias"]), meta["series"], z["y"], z["obs"],
                    point, quant, z["escala"], meta["segundos"])
    return R, meta


def predecir(sistema: str, pipes: dict, modelos_sel: list[str]) -> tuple[V.Resultado, dict]:
    t0 = time.time()
    P = V.cargar_panel(sistema, RAIZ)
    log(f"[{sistema}] panel {P.Y.shape} | series={P.S} | {P.index[0].date()} → {P.index[-1].date()}")
    n_est = V.lgb_early_stopping(P)
    log(f"[{sistema}] LightGBM early stopping: {n_est} árboles")
    fabricas = {
        "naive_7d": lambda: V.f_naive_7d,
        "hora_media": lambda: V.f_hora_media,
        "media_4sem": lambda: V.f_media_4sem,
        "autoets": lambda: V.hacer_autoets(ventana_dias=56),
        "mstl": lambda: V.hacer_mstl(ventana_dias=56),
        "lightgbm": lambda: V.LGBMDirecto(n_estimators=n_est, refit_cada=7),
        "chronos_bolt": lambda: V.hacer_bolt(pipes["bolt"]),
        "chronos2": lambda: V.hacer_chronos2(pipes["chronos2"], cross_learning=False),
        "chronos2_xl": lambda: V.hacer_chronos2(pipes["chronos2"], cross_learning=True),
    }
    modelos = {m: fabricas[m]() for m in modelos_sel}
    dias = V.DIAS_VAL.append(V.DIAS_TEST)
    R = V.rolling_origin(P, dias, modelos)
    extra = {"lgb_n_estimators": n_est, "segundos_total": time.time() - t0,
             "lgb_params": V.LGB_PARAMS, "lgb_feats": V.LGB_FEATS}
    guardar_resultado(R, extra, OUT / sistema)
    log(f"[{sistema}] predicciones guardadas ({time.time() - t0:.0f}s)")
    return R, extra


# ── Análisis ──────────────────────────────────────────────────────────────

def subset(R: V.Resultado, dias) -> V.Resultado:
    k = np.isin(R.dias, pd.DatetimeIndex(dias))
    return V.Resultado(
        R.sistema, R.dias[k], R.series, R.y[k], R.obs[k],
        {m: a[k] for m, a in R.point.items()},
        {m: (None if a is None else a[k]) for m, a in R.quant.items()},
        R.escala[k], R.segundos,
    )


def seleccionar(R: V.Resultado, mase_scale) -> dict:
    """Selección en validación: ganador individual, top-3 → ensemble, elección final."""
    Rv = subset(R, V.DIAS_VAL)
    cand = [m for m in CANDIDATOS + OPCIONALES if m in R.point]
    tab = V.tabla_metricas(Rv, mase_scale, modelos=list(R.point), estratos=("todos",))
    tab = tab.sort_values("WMAPE").reset_index(drop=True)
    top3 = [m for m in tab["modelo"] if m in cand][:3]
    V.agregar_ensemble(R, top3)
    Rv = subset(R, V.DIAS_VAL)
    ens = V.tabla_metricas(Rv, mase_scale, modelos=["ensemble"], estratos=("todos",))
    tab = pd.concat([tab, ens], ignore_index=True).sort_values("WMAPE").reset_index(drop=True)
    elegibles = cand + ["ensemble"]
    ganador = next(m for m in tab["modelo"] if m in elegibles)
    return {"tabla_validacion": tab, "top3": top3, "ganador": ganador}


def analizar(sistema: str, R: V.Resultado, extra: dict) -> dict:
    t0 = time.time()
    dst = RES / sistema
    dst.mkdir(parents=True, exist_ok=True)
    P = V.cargar_panel(sistema, RAIZ)
    mase_scale = V.escala_mase(P)

    sel = seleccionar(R, mase_scale)
    sel["tabla_validacion"].to_csv(dst / "seleccion_validacion.csv", index=False)
    ganador = sel["ganador"]
    log(f"[{sistema}] validación → top3={sel['top3']} | ganador={ganador}")

    Rt = subset(R, V.DIAS_TEST)
    modelos = list(R.point)
    tab = V.tabla_metricas(Rt, mase_scale, modelos=modelos)
    tab.to_csv(dst / "metricas_test.csv", index=False)
    diarias = V.metricas_diarias(Rt, modelos)
    diarias.to_csv(dst / "metricas_diarias_test.csv", index=False)

    # Diebold-Mariano: ganador vs cada modelo (MAE diario en test)
    piv = diarias.pivot_table(index="dia", columns="modelo", values="MAE")
    dm = []
    for m in modelos:
        if m == ganador:
            continue
        stat, p = V.diebold_mariano(piv[ganador].to_numpy(), piv[m].to_numpy())
        dm.append({"sistema": sistema, "ganador": ganador, "vs": m, "dm_stat": stat, "p_valor": p})
    pd.DataFrame(dm).to_csv(dst / "diebold_mariano.csv", index=False)

    # Intervalos (cobertura objetivo 80 %) y cuantiles para producción (últimos 14 días)
    inter = V.evaluar_intervalos(R, [m for m in modelos if m not in V.BASELINES], V.DIAS_TEST)
    inter.to_csv(dst / "intervalos_test.csv", index=False)
    dias_cal = V.DIAS_TEST[-V.VENTANA_CONFORMAL:]
    conformal = {m: V.cuantiles_conformal(R, m, dias_cal) for m in modelos if m not in V.BASELINES}
    (dst / "conformal_produccion.json").write_text(V.a_json(conformal), encoding="utf-8")

    # Aforo en cascada, ETA proxy y regla U
    cfg, df_ops = V.config_aforo(P, FUENTES)
    (dst / "config_aforo.json").write_text(V.a_json(cfg.to_dict()), encoding="utf-8")
    pred_clases = {f"cascada_{m}": V.clases_resultado(cfg, Rt, Rt.point[m])
                   for m in modelos if m != "hora_media"}
    pred_clases["mayoritaria"] = np.full(Rt.y.shape, "Asientos", dtype=object)
    pred_clases["moda_historica"] = V.moda_historica(cfg, P, Rt)
    _, _, _, pred_clases["histgb_directo"] = V.clasificador_directo(df_ops, Rt)
    af, rec, conf = V.evaluar_aforo(cfg, Rt, pred_clases, V.DIAS_TEST)
    af.to_csv(dst / "aforo_test.csv", index=False)
    rec.to_csv(dst / "regla_u_test.csv", index=False)
    for nombre in (f"cascada_{ganador}", "histgb_directo", "cascada_naive_7d"):
        if nombre in conf:
            conf[nombre].to_csv(dst / f"confusion_{nombre}.csv")

    # Sensibilidad: umbrales globales (p60/p90 sin separar franjas)
    tr = df_ops[df_ops["Fecha_Hora"] <= M.SPLIT]["crowding_index"]
    glob = (float(tr.quantile(0.6)), float(tr.quantile(0.9)))
    cfg_g = V.ConfigAforo(cfg.sistema, {fr: glob for fr in cfg.umbrales}, cfg.headway,
                          cfg.cap_vehiculo, cfg.orden)
    af_g, _, _ = V.evaluar_aforo(cfg_g, Rt, {
        f"cascada_{ganador}": V.clases_resultado(cfg_g, Rt, Rt.point[ganador]),
        "cascada_naive_7d": V.clases_resultado(cfg_g, Rt, Rt.point["naive_7d"]),
        "mayoritaria": np.full(Rt.y.shape, "Asientos", dtype=object),
    }, V.DIAS_TEST)
    verdad_f = V.clases_resultado(cfg, Rt, Rt.y)[Rt.obs]
    verdad_g = V.clases_resultado(cfg_g, Rt, Rt.y)[Rt.obs]
    noche = np.broadcast_to(V.FRANJA_H == "noche", Rt.y.shape)[Rt.obs]
    af_g.insert(1, "umbrales", "global")
    af_g["pct_saturado_noche"] = float((verdad_g[noche] == "Saturado").mean()) if noche.any() else np.nan
    af_f = af[af["modelo"].isin(af_g["modelo"])].copy()
    af_f.insert(1, "umbrales", "por_franja")
    af_f["pct_saturado_noche"] = float((verdad_f[noche] == "Saturado").mean()) if noche.any() else np.nan
    pd.concat([af_f, af_g], ignore_index=True).to_csv(dst / "aforo_sensibilidad_umbrales.csv", index=False)

    # Anomalías: año completo (detectores sin calendario) y test (residuos del ganador)
    desde = pd.Timestamp("2025-02-01")
    det_res = V.residuo_diario_baseline(P, desde)
    det_glob = V.score_total_global(P, desde)
    _, thr_if, det_if = V.score_isolation_forest(df_ops, desde)
    eval_an = [
        V.evaluar_detector(det_res, "residuo_media4sem_zrobusto", sistema, umbral=3.0),
        V.evaluar_detector(det_glob, "z_total_mismo_dow", sistema, umbral=2.0),
        V.evaluar_detector(det_if, "isolation_forest_w08", sistema,
                           umbral=float(det_if["score"].quantile(0.95))),
    ]
    det_res.to_csv(dst / "anomalias_residuo_diario.csv", index=False)
    det_if.to_csv(dst / "anomalias_isolation_forest.csv", index=False)
    real = Rt.y.sum(axis=(1, 2))
    esp = Rt.point[ganador].sum(axis=(1, 2))
    rel = (real - esp) / np.maximum(esp, 1e-9)
    top = (pd.DataFrame({"dia": Rt.dias, "residuo_rel": rel,
                         "tipo_dia": [V.tipo_evento(d) for d in Rt.dias]})
           .assign(abs_res=lambda d: d["residuo_rel"].abs())
           .sort_values("abs_res", ascending=False))
    top.to_csv(dst / "anomalias_test_residuo_ganador.csv", index=False)
    pd.DataFrame(eval_an).to_csv(dst / "anomalias_eval.csv", index=False)

    resumen = {
        "sistema": sistema, "ganador_validacion": ganador, "top3_validacion": sel["top3"],
        "lgb_n_estimators": extra.get("lgb_n_estimators"),
        "segundos_modelo": R.segundos, "n_series": len(R.series),
        "dias_val": [str(d.date()) for d in (V.DIAS_VAL[0], V.DIAS_VAL[-1])],
        "dias_test": [str(d.date()) for d in (V.DIAS_TEST[0], V.DIAS_TEST[-1])],
        "umbrales_globales": glob, "isolation_forest_umbral": thr_if,
        "segundos_analisis": time.time() - t0,
    }
    (dst / "resumen.json").write_text(V.a_json(resumen), encoding="utf-8")
    log(f"[{sistema}] análisis listo ({time.time() - t0:.0f}s) → {dst}")
    return resumen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sistemas", nargs="+", default=SISTEMAS, choices=SISTEMAS)
    ap.add_argument("--modelos", nargs="+", default=list(V.BASELINES) + CANDIDATOS)
    ap.add_argument("--solo-analisis", action="store_true", help="reusa outputs_v2/<sistema>/resultado.npz")
    ap.add_argument("--hilos", type=int, default=None, help="hilos de torch (útil al correr sistemas en paralelo)")
    args = ap.parse_args()

    if args.hilos:
        import torch
        torch.set_num_threads(args.hilos)
    pipes = {}
    if not args.solo_analisis:
        if "chronos_bolt" in args.modelos:
            pipes["bolt"] = V.cargar_bolt()
        if {"chronos2", "chronos2_xl"} & set(args.modelos):
            pipes["chronos2"] = V.cargar_chronos2()
    for s in args.sistemas:
        if args.solo_analisis:
            R, extra = cargar_resultado(s)
            extra = {k: v for k, v in extra.items() if k not in ("sistema", "dias", "series", "segundos")}
        else:
            R, extra = predecir(s, pipes, args.modelos)
        analizar(s, R, extra)


if __name__ == "__main__":
    main()
