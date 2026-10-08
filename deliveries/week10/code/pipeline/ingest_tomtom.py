from __future__ import annotations

import datetime as dt
import json
import time

import httpx
import numpy as np

from pipeline import config
from storage import db

# Puntos de muestreo en ejes principales de Lima (coordenadas de referencia).
SEGMENTOS: list[dict] = [
    {"segmento": "javier_prado_salaverry", "lat": -12.0949, "lon": -77.0320},
    {"segmento": "via_expresa_pardo", "lat": -12.0795, "lon": -77.0385},
    {"segmento": "argentina_mexico", "lat": -12.0589, "lon": -77.0406},
    {"segmento": "brasil_28julio", "lat": -12.1064, "lon": -77.0246},
    {"segmento": "evitamiento_norte", "lat": -12.0050, "lon": -77.0750},
    {"segmento": "panamericana_norte", "lat": -11.9900, "lon": -77.0550},
]

TOMTOM_URL = (
    "https://api.tomtom.com/traffic/services/4/flowSegmentData"
    "/relative/{segment}/json"
)

FREE_FLOW_KPH = 50.0  # velocidad libre asumida en el backend sintetico


def _ratio_por_hora(hora: int, es_habil: bool = True, seed: int = 0) -> float:
    rng = np.random.default_rng(seed + hora)
    jitter = 1.0 + rng.uniform(-0.03, 0.03)
    if es_habil:
        if 6 <= hora <= 9:
            return 1.75 * jitter
        if 17 <= hora <= 20:
            return 1.85 * jitter
        if 12 <= hora <= 16:
            return 1.35 * jitter
        if hora <= 5 or hora >= 22:
            return 1.08 * jitter
        return 1.25 * jitter
    if 10 <= hora <= 19:
        return 1.30 * jitter
    return 1.10 * jitter


def _aplica_eventos(ts: dt.datetime, es_habil: bool, seed: int) -> float:
    mult = 1.0
    if es_habil and (ts.hour in (7, 8, 17, 18)):
        mult *= 1.15
    if 30 <= ts.day <= 31 and ts.hour in (14, 15, 16, 17):
        mult *= 1.30
    day = ts.timetuple().tm_yday + ts.hour
    if day % 6 == 0 and 8 <= ts.hour <= 20:
        mult *= 1.20
    return mult


def ratio_sintetico(ts: dt.datetime, seed: int = 42) -> float:
    es_habil = ts.weekday() < 5
    ratio = _ratio_por_hora(ts.hour, es_habil, seed) * _aplica_eventos(
        ts, es_habil, seed
    )
    return float(min(max(ratio, 1.0), 3.0))


# Consulta TomTom + fallback
def _obtener(client: httpx.Client, seg: dict) -> dict:
    if not config.TOMTOM_API_KEY:
        raise RuntimeError("API key TomTom ausente (API_TOMTOM/TOMMTOM_KEY)")
    url = TOMTOM_URL.format(segment=config.TOMTOM_SEGMENT)
    resp = client.get(
        url,
        params={
            "point": f"{seg['lat']},{seg['lon']}",
            "key": config.TOMTOM_API_KEY,
            "unit": "KMPH",
        },
        timeout=config.TOMTOM_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()["flowSegmentData"]
    actual = float(data["currentSpeed"])
    libre = float(data["freeFlowSpeed"])
    ratio = libre / actual if actual > 0 else 1.0
    return {
        "actual": actual,
        "libre": libre,
        "ratio": ratio,
        "detalle": data,
    }


def _snapshot_segmento(client: httpx.Client, seg: dict) -> dict:
    t0 = time.perf_counter()
    try:
        res = _obtener(client, seg)
        fuente, status = "tomtom", "ok"
    except Exception as exc:  # noqa: BLE001 - cualquier fallo cae a fallback
        ts = dt.datetime.now()
        ratio = ratio_sintetico(ts)
        res = {
            "actual": round(FREE_FLOW_KPH / ratio, 2),
            "libre": FREE_FLOW_KPH,
            "ratio": ratio,
            "detalle": {
                "motivo": f"{type(exc).__name__}: {exc}",
                "hora_local": ts.isoformat(timespec="seconds"),
            },
        }
        fuente, status = "fallback", f"fallback:{type(exc).__name__}"
    latencia_ms = (time.perf_counter() - t0) * 1000.0
    return {
        **seg,
        "actual": res["actual"],
        "libre": res["libre"],
        "ratio": res["ratio"],
        "fuente": fuente,
        "status": status,
        "latencia_ms": latencia_ms,
        "detalle": res["detalle"],
    }


def snapshot(conn) -> dict:
    resumen = {"tomtom": 0, "fallback": 0, "segmentos": 0}
    with httpx.Client() as client:
        for seg in SEGMENTOS:
            r = _snapshot_segmento(client, seg)
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO trafico_en_vivo
                        (segmento, lat, lon, actual_speed_kph,
                         free_flow_speed_kph, ratio_congestion, fuente,
                         actualizado_en)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (segmento) DO UPDATE SET
                        lat = EXCLUDED.lat,
                        lon = EXCLUDED.lon,
                        actual_speed_kph = EXCLUDED.actual_speed_kph,
                        free_flow_speed_kph = EXCLUDED.free_flow_speed_kph,
                        ratio_congestion = EXCLUDED.ratio_congestion,
                        fuente = EXCLUDED.fuente,
                        actualizado_en = now()
                    """,
                    (
                        r["segmento"], r["lat"], r["lon"], r["actual"],
                        r["libre"], r["ratio"], r["fuente"],
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO log_inferencia
                        (fuente, segmento, lat, lon, latencia_ms, status,
                         ratio_congestion, detalle)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        r["fuente"], r["segmento"], r["lat"], r["lon"],
                        round(r["latencia_ms"], 2), r["status"], r["ratio"],
                        json.dumps(r["detalle"], ensure_ascii=False, default=str),
                    ),
                )
            resumen[r["fuente"]] += 1
            resumen["segmentos"] += 1
            print(
                f"[tomtom] {r['segmento']:<24} {r['fuente']:<9} "
                f"ratio={r['ratio']:.3f} {r['latencia_ms']:6.1f}ms "
                f"({r['status']})"
            )
    return resumen


def main() -> None:
    conn = db.connect()
    try:
        resumen = snapshot(conn)
    finally:
        conn.close()
    print(
        f"[tomtom] listo: {resumen['segmentos']} segmentos "
        f"({resumen['tomtom']} tomtom, {resumen['fallback']} fallback)"
    )


if __name__ == "__main__":
    main()
