import pandas as pd
from datetime import date
from pathlib import Path
from meteostat import daily, hourly

DESDE = date(2026, 7, 1)      
HASTA = date(2026, 8, 31)     
ESTACION_ID = "80222"         # Bogota (código de Meteostat)
ZONA_HORARIA = "America/Bogota"
GRANULARIDAD = "todas"        # "hora" | "diario" | "semana" | "todas"

CODEDIR = Path(__file__).resolve().parent
SALIDA = CODEDIR.parent / "data" / "clima"

COLUMNAS_HORA = ["temp", "rhum", "prcp", "wspd", "wpgt",
                 "wdir", "pres", "cldc", "coco"]
COLUMNAS_DIA = ["temp", "tmin", "tmax", "rhum", "prcp", "wspd", "wpgt",
                "pres", "tsun", "cldc"]


def _disponibles(df: pd.DataFrame, columnas) -> list:
    return [c for c in columnas if c in df.columns]


def descargar_diario() -> pd.DataFrame:
    print("  Serie diaria ...")
    df = daily(ESTACION_ID, DESDE, HASTA).fetch()
    if df is None or df.empty:
        raise RuntimeError("No hay datos diarios de Meteostat para el periodo")
    return df


def descargar_horario() -> pd.DataFrame:
    print("  Serie horaria ...")
    df = hourly(ESTACION_ID, DESDE, HASTA, timezone=ZONA_HORARIA).fetch()
    if df is None or df.empty:
        raise RuntimeError("No hay datos horarios de Meteostat para el periodo")
    return df


def _renombrar_fecha(df: pd.DataFrame) -> pd.DataFrame:
    out = df.reset_index()
    out.columns = out.columns.map(str)
    out = out.rename(columns={"time": "fecha"})
    return out


def _diario_desde_horario(df_hora: pd.DataFrame) -> pd.DataFrame:
    agg = {"temp": "mean", "rhum": "mean", "prcp": "sum", "wspd": "mean",
           "wpgt": "max", "pres": "mean", "cldc": "mean", "coco": "mean"}
    d = df_hora.resample("D").agg({k: v for k, v in agg.items()
                                   if k in df_hora.columns})
    d["tmin"] = df_hora["temp"].resample("D").min()
    d["tmax"] = df_hora["temp"].resample("D").max()
    return d


def guardar(df: pd.DataFrame, nombre: str) -> Path:
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / nombre
    df.to_csv(ruta, index=False, encoding="utf-8")
    print(f"  OK: {len(df):,} filas -> {ruta}")
    return ruta


def main() -> None:
    print(f"Directorio de salida: {SALIDA}")
    print(f"Periodo: {DESDE.isoformat()} -> {HASTA.isoformat()} "
          f"({(HASTA - DESDE).days + 1} días) | estación {ESTACION_ID}")

    prefijo = f"{DESDE}_a_{HASTA}"
    gran = set(GRANULARIDAD.split(",") if isinstance(GRANULARIDAD, str)
               and "," in GRANULARIDAD else [GRANULARIDAD])
    if gran == {"todas"}:
        gran = {"hora", "diario", "semana"}

    if "hora" in gran or "diario" in gran:
        print("\nDescargando series de Meteostat ...")
        try:
            df_dia = descargar_diario()
        except Exception as e:
            print(f"  Error diario: {e}")
            df_dia = None
        try:
            df_hora = descargar_horario()
        except Exception as e:
            print(f"  Error horario: {e}")
            df_hora = None

    if "hora" in gran and df_hora is not None:
        h = _renombrar_fecha(df_hora)
        guardar(h[["fecha", *_disponibles(h, COLUMNAS_HORA)]],
                f"clima_hora_{prefijo}.csv")

    if "diario" in gran:
        if df_hora is not None:
            dia = _diario_desde_horario(df_hora)
        elif df_dia is not None:
            dia = df_dia.copy()
        else:
            dia = None
        if dia is not None:
            d = _renombrar_fecha(dia)
            guardar(d[["fecha", *_disponibles(d, COLUMNAS_DIA)]],
                    f"clima_dia_{prefijo}.csv")

    if "semana" in gran:
        base = None
        if df_hora is not None:
            base = _diario_desde_horario(df_hora)
        elif df_dia is not None:
            base = df_dia.copy()
        if base is not None:
            agg = {c: "mean" for c in base.columns if c not in ("prcp", "tmin", "tmax")}
            agg["prcp"] = "sum"
            agg["tmin"] = "min"
            agg["tmax"] = "max"
            w = base.resample("W", label="left", closed="left").agg(agg).dropna(how="all")
            w.index = w.index + pd.Timedelta(days=1)  # etiquetar con el lunes de cada semana
            w = _renombrar_fecha(w)
            guardar(w[["fecha", *_disponibles(w, COLUMNAS_DIA)]],
                    f"clima_semana_{prefijo}.csv")

    print("\nListo! Revisa:", SALIDA)


if __name__ == "__main__":
    main()