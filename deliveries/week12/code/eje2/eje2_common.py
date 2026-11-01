from pathlib import Path

import numpy as np
import pandas as pd

OBS_FORZADA = "GEO FORZADA AL CENTROIDE DE COMISARIA"
ANIO_MIN, ANIO_MAX = 2018, 2024          # años con registro estable; el test llega hasta agosto de 2024
UMBRAL_APILADA = 500                      # coordenadas "reales" repetidas >= N veces = punto por defecto del geocodificador
PROVINCIAS_OK = ("LIMA", "CALLAO")

# Grupos de hecho -> ¿sirven para el riesgo peatonal por calle?
GRUPOS_EJE2 = {
    "robo_persona": True,        # robo / robo agravado / arrebato: el riesgo principal del peatón
    "hurto": True,               # hurto simple/agravado, hurto de celular, falta de hurto
    "acoso": True,               # acoso y acoso sexual: señal propia aunque sea poca (subregistro alto)
    "agresion_sexual": True,     # violación, tocamientos, actos contra el pudor
    "violencia_fisica": True,    # lesiones, homicidio, tentativa (excluye violencia familiar)
    "vehiculo": False,           # robo/hurto de vehículo y autopartes: no es riesgo del peatón
    "domicilio": False,          # hurto/robo en casa habitada
    "fraude_extorsion": False,   # estafa, extorsión, delitos informáticos: sin ubicación callejera
    "violencia_familiar": False, # ocurre en el hogar; no es inseguridad en la calle
    "intervencion_policial": False,  # visitas de medidas de protección, personas desaparecidas, etc.
    "otros": False,
}


def clasificar_grupo(df: pd.DataFrame) -> pd.Series:
    """Asigna un grupo de GRUPOS_EJE2 a cada denuncia a partir de tipo/subtipo/modalidad."""
    t = df["tipo_hecho"].fillna("")
    s = df["subtipo_hecho"].fillna("")
    m = df["modalidad_hecho"].fillna("")
    g = pd.Series("otros", index=df.index)
    g[s.str.contains("ESTAFA|EXTORSION|RECEPTACION|APROPIACION|USURPACION", regex=True)
      | t.str.contains("INFORMATICOS|FE PUBLICA|ORDEN FINANCIERO", regex=True)] = "fraude_extorsion"
    g[(s == "HURTO") | (s == "ROBO") | m.str.contains("HURTO|ROBO|ARREBATO", regex=True) & t.isin(["PATRIMONIO (DELITO)", "FALTAS"])] = "hurto"
    g[m.str.startswith("ROBO") | m.str.contains("ARREBATO|ASALTO", regex=True) & (g == "hurto")] = "robo_persona"
    g[(g.isin(["hurto", "robo_persona"])) & m.str.contains("VEHICUL|AUTOPARTE|MOTO|ACCESORIOS", regex=True)] = "vehiculo"
    g[(g.isin(["hurto", "robo_persona"])) & m.str.contains("CASA|DOMICILIO|VIVIENDA", regex=True)] = "domicilio"
    g[t.str.contains("LIBERTAD") & m.str.contains("ACOSO")] = "acoso"
    g[t.str.contains("LIBERTAD") & m.str.contains("VIOLACION|PUDOR|TOCAMIENTO|SEXUAL", regex=True) & ~m.str.contains("ACOSO")] = "agresion_sexual"
    g[t.str.contains("VIDA, EL CUERPO") & m.str.contains("LESIONES|HOMICIDIO|FEMINICIDIO|TENTATIVA", regex=True)
      & ~m.str.contains("CULPOSA|GRUPO FAMILIAR|MUJERES", regex=True)] = "violencia_fisica"
    g[t.str.contains("VIOLENCIA CONTRA LA MUJER")] = "violencia_familiar"
    g[t.str.contains("INTERVENCION POLICIALES")] = "intervencion_policial"
    return g


def puntos_apilados(df: pd.DataFrame) -> set:
    """Coordenadas 'reales' repetidas >= UMBRAL_APILADA veces (se calculan en train y se reutilizan en valid/test)."""
    real = df.loc[df["observacion"].ne(OBS_FORZADA)]
    cuenta = real.groupby([real.lat_hecho.round(5), real.long_hecho.round(5)]).size()
    return set(cuenta[cuenta >= UMBRAL_APILADA].index)


def marcar_calidad(df: pd.DataFrame, apiladas: set | None = None) -> pd.DataFrame:
    """Agrega banderas de calidad. No elimina filas. `apiladas`: conjunto de puntos (ver puntos_apilados)."""
    out = df.copy()
    out["coord_real"] = out["observacion"].ne(OBS_FORZADA)
    out["verificar_ubigeo"] = out["observacion"].fillna("").str.contains("VERIFICAR|CORREGIR")
    if apiladas is None:
        apiladas = puntos_apilados(out)
    claves = list(zip(out.lat_hecho.round(5), out.long_hecho.round(5)))
    out["coord_apilada"] = out.coord_real & pd.Series([k in apiladas for k in claves], index=out.index)
    out["anio"] = out["fecha_hora_hecho"].dt.year
    out["hora_00_exacta"] = (out["fecha_hora_hecho"].dt.hour == 0) & (out["fecha_hora_hecho"].dt.minute == 0)
    out["grupo"] = clasificar_grupo(out)
    out["sirve_eje2"] = out["grupo"].map(GRUPOS_EJE2).astype(bool)
    return out


def filtrar_eje2(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el embudo del EDA. df debe pasar antes por marcar_calidad."""
    ok = (
        df["sirve_eje2"] & df["coord_real"] & ~df["coord_apilada"]
        & df["anio"].between(ANIO_MIN, ANIO_MAX)
        & df["provincia_hecho"].isin(PROVINCIAS_OK)
    )
    return df.loc[ok]
