"""Genera un escenario sintético y reproducible para el tablero de UrbanSafe AI.

Los registros NO representan personas, viajes, delitos ni ventas reales. Los valores
de ETA, aforo, disponibilidad y latencia provienen de supuestos aleatorios de este
generador: no son salidas del LightGBM ni mediciones de la API. Sirven para probar
el comportamiento visual y los cálculos del panel.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analytics" / "output"
PUBLIC = ROOT / "frontend" / "public" / "simulacion"

CATALOGOS = {
    "metro_l1": (ROOT / "backend/data/geo/puntos_metro_l1.geojson", "estacion", None),
    "metropolitano": (ROOT / "backend/data/geo/puntos_troncal.geojson", "estacion", None),
    "corredores": (ROOT / "backend/data/geo/paradas_corredores.geojson", "paradero", "ruta"),
    "alimentadores": (ROOT / "backend/data/geo/puntos_alimentadores.geojson", "paradero", "ruta"),
}

PESOS_SISTEMA = {"metro_l1": 0.31, "metropolitano": 0.34, "corredores": 0.22, "alimentadores": 0.13}
AFOROS = ("Asientos", "De_pie", "Saturado")
REPORTES = ("acoso", "seguimiento", "robo")


@dataclass(frozen=True)
class Registro:
    sesion_id: str
    usuario_id: str
    fecha_hora_lima: str
    sistema: str
    estacion: str
    ruta: str
    consulta_generada: bool
    recomendacion_vista: bool
    abordaje_confirmado: bool
    feedback_enviado: bool
    eta_pred_min: float
    eta_obs_min: float | None
    error_eta_abs_min: float | None
    aforo_pred: str
    aforo_observado: str | None
    ruta_segura_solicitada: bool
    reporte_seguridad: bool
    tipo_reporte: str | None
    latencia_api_ms: int
    api_correcta: bool
    fallback_historico: bool
    cache_hit: bool
    modo_datos: str = "simulado"


def catalogos() -> dict[str, list[tuple[str, str]]]:
    """Lee nombres y rutas del catálogo del propio proyecto; no inventa estaciones."""
    salida: dict[str, list[tuple[str, str]]] = {}
    for sistema, (archivo, nombre, ruta) in CATALOGOS.items():
        geo = json.loads(archivo.read_text(encoding="utf-8"))
        vistos: set[tuple[str, str]] = set()
        filas: list[tuple[str, str]] = []
        for feature in geo.get("features", []):
            propiedades = feature.get("properties") or {}
            estacion = str(propiedades.get(nombre) or "").strip()
            linea = str(propiedades.get(ruta) or ("Línea 1" if sistema == "metro_l1" else "Troncal"))
            if estacion and (estacion, linea) not in vistos:
                vistos.add((estacion, linea))
                filas.append((estacion, linea))
        if not filas:
            raise ValueError(f"El catálogo {archivo} no contiene estaciones utilizables")
        salida[sistema] = filas
    return salida


def elegir_ponderado(rng: random.Random, pesos: dict[str, float]) -> str:
    return rng.choices(list(pesos), weights=list(pesos.values()), k=1)[0]


def limitar(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def aforo_por_nivel(valor: float) -> str:
    # Cortes de demostración; las clases coinciden con la app, no sus umbrales operativos.
    return AFOROS[0 if valor < 0.45 else 1 if valor < 0.75 else 2]


def hora_sintetica(rng: random.Random) -> int:
    # Dos puntas visibles y una distribución menor durante el resto del día.
    bloque = rng.choices(("manana", "tarde", "valle"), weights=(0.36, 0.35, 0.29), k=1)[0]
    if bloque == "manana":
        return int(limitar(round(rng.gauss(7.5, 1.25)), 5, 10))
    if bloque == "tarde":
        return int(limitar(round(rng.gauss(18.0, 1.4)), 15, 22))
    return rng.randint(6, 22)


def generar(n: int, hasta: date, semilla: int) -> list[Registro]:
    rng = random.Random(semilla)
    estaciones = catalogos()
    inicio = hasta - timedelta(days=29)
    filas: list[Registro] = []
    for indice in range(1, n + 1):
        sistema = elegir_ponderado(rng, PESOS_SISTEMA)
        estacion, ruta = rng.choice(estaciones[sistema])
        dia = inicio + timedelta(days=rng.randrange(30))
        hora = hora_sintetica(rng)
        minuto = rng.randrange(0, 60, 5)
        fecha_hora = datetime.combine(dia, time(hora, minuto))

        pico = 1.0 if 6 <= hora <= 9 or 17 <= hora <= 20 else 0.0
        aforo_continuo = limitar(rng.gauss(0.48 + pico * 0.31, 0.16), 0.08, 0.98)
        aforo_pred = aforo_por_nivel(aforo_continuo)
        aforo_real = aforo_por_nivel(limitar(aforo_continuo + rng.gauss(0, 0.15), 0.03, 1.0))

        eta_base = {"metro_l1": 4.8, "metropolitano": 6.3, "corredores": 8.1, "alimentadores": 10.2}[sistema]
        eta_pred = limitar(rng.gauss(eta_base + pico * 2.3, 1.5), 1.0, 24.0)
        eta_obs = limitar(eta_pred + rng.gauss(0.25, 2.1 + pico * 0.7), 0.5, 32.0)

        api_correcta = rng.random() < 0.982
        recomendacion = api_correcta and rng.random() < 0.93
        abordaje = recomendacion and rng.random() < (0.51 if pico else 0.43)
        feedback = abordaje and rng.random() < 0.28
        ruta_segura = rng.random() < 0.24
        reporte = ruta_segura and rng.random() < 0.045
        latencia = int(limitar(math.exp(rng.gauss(math.log(340), 0.48)), 95, 2600))
        fallback = api_correcta and rng.random() < 0.115
        cache_hit = api_correcta and rng.random() < 0.62

        filas.append(Registro(
            sesion_id=f"SIM-{indice:04d}", usuario_id=f"USR-SIM-{indice:04d}",
            fecha_hora_lima=fecha_hora.isoformat(timespec="minutes"),
            sistema=sistema, estacion=estacion, ruta=ruta, consulta_generada=True,
            recomendacion_vista=recomendacion, abordaje_confirmado=abordaje,
            feedback_enviado=feedback,
            eta_pred_min=round(eta_pred, 1), eta_obs_min=round(eta_obs, 1) if abordaje else None,
            error_eta_abs_min=round(abs(eta_obs - eta_pred), 1) if abordaje else None,
            aforo_pred=aforo_pred, aforo_observado=aforo_real if abordaje else None,
            ruta_segura_solicitada=ruta_segura, reporte_seguridad=reporte,
            tipo_reporte=rng.choices(REPORTES, weights=(0.48, 0.22, 0.30), k=1)[0] if reporte else None,
            latencia_api_ms=latencia, api_correcta=api_correcta,
            fallback_historico=fallback, cache_hit=cache_hit,
        ))
    return sorted(filas, key=lambda fila: fila.fecha_hora_lima)


def resumen(filas: list[Registro], semilla: int, hasta: date) -> dict:
    abordajes = [f for f in filas if f.abordaje_confirmado]
    feedback = [f for f in filas if f.feedback_enviado]
    errores = [f.error_eta_abs_min for f in abordajes if f.error_eta_abs_min is not None]
    aciertos_aforo = [f for f in abordajes if f.aforo_observado == f.aforo_pred]
    latencias = sorted(f.latencia_api_ms for f in filas)
    return {
        "metadatos": {
            "modo_datos": "simulado", "filas": len(filas), "semilla": semilla,
            "usuarios_simulados": len({f.usuario_id for f in filas}),
            "diseno_escenario": "Un usuario ficticio por sesión; identificadores sin datos personales.",
            "periodo_desde": min(f.fecha_hora_lima for f in filas)[:10], "periodo_hasta": hasta.isoformat(),
            "advertencia": "Escenario sintético para demostración. ETA, aforo, disponibilidad y latencia son supuestos del generador; no son predicciones LightGBM ni mediciones reales de la API. No representa usuarios, viajes, delitos ni ventas reales.",
        },
        "indicadores_control": {
            "usuarios_simulados": len({f.usuario_id for f in filas}),
            "consultas": len(filas), "recomendaciones_vistas": sum(f.recomendacion_vista for f in filas),
            "abordajes_confirmados": len(abordajes), "feedback": len(feedback),
            "mae_eta_min": round(sum(errores) / len(errores), 2) if errores else None,
            "acierto_aforo": round(len(aciertos_aforo) / len(abordajes), 4) if abordajes else None,
            "api_exito": round(sum(f.api_correcta for f in filas) / len(filas), 4),
            "latencia_p95_ms": latencias[min(len(latencias) - 1, math.ceil(len(latencias) * .95) - 1)],
            "por_sistema": Counter(f.sistema for f in filas),
        },
    }


def escribir(filas: list[Registro], datos_resumen: dict) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    objetos = [asdict(fila) for fila in filas]
    csv_path = OUTPUT / "urbansafe_simulacion_600.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=list(objetos[0]))
        writer.writeheader()
        writer.writerows(objetos)
    (PUBLIC / "urbansafe_simulacion_600.json").write_text(json.dumps(objetos, ensure_ascii=False, indent=2), encoding="utf-8")
    texto_resumen = json.dumps(datos_resumen, ensure_ascii=False, indent=2, default=dict)
    (OUTPUT / "resumen_simulacion_600.json").write_text(texto_resumen, encoding="utf-8")
    (PUBLIC / "resumen_simulacion_600.json").write_text(texto_resumen, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registros", type=int, default=600)
    parser.add_argument("--hasta", type=date.fromisoformat, default=date(2026, 11, 12))
    parser.add_argument("--semilla", type=int, default=20261112)
    args = parser.parse_args()
    if args.registros < 50:
        parser.error("La demostración necesita al menos 50 registros")
    filas = generar(args.registros, args.hasta, args.semilla)
    escribir(filas, resumen(filas, args.semilla, args.hasta))
    print(f"Generados {len({f.usuario_id for f in filas})} usuarios ficticios con {len(filas)} sesiones entre {filas[0].fecha_hora_lima[:10]} y {filas[-1].fecha_hora_lima[:10]}")


if __name__ == "__main__":
    main()
