import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

CRS_M = 32718          # UTM 18S
RADIO_M = 800          # ~10 min caminando (80 m/min)
TAU_ANIOS = 1.5        # vida media del decaimiento temporal
COB_MIN = 0.25         # tope de ponderación: peso máximo = 1 / COB_MIN = 4
HW_GRUPOS = {          # tipo de vía OSM agrupado
    "residential": "residencial", "living_street": "residencial", "service": "servicio",
    "footway": "peatonal", "pedestrian": "peatonal", "path": "peatonal", "steps": "peatonal", "corridor": "peatonal",
    "primary": "arterial", "secondary": "arterial", "tertiary": "arterial", "trunk": "arterial",
    "primary_link": "arterial", "secondary_link": "arterial", "tertiary_link": "arterial", "trunk_link": "arterial",
    "unclassified": "otra", "track": "otra", "cycleway": "peatonal",
}
GRUPOS_PATRIMONIO = ("robo_persona", "hurto")
GRUPOS_PERSONA = ("acoso", "agresion_sexual", "violencia_fisica")


# ----------------------------------------------------------------------------- grafo / segmentos
def preparar_segmentos(aristas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Aristas dirigidas de OSM -> segmentos físicos únicos (una calle = una fila), en metros (UTM)."""
    g = aristas.to_crs(CRS_M).copy()
    a, b = np.minimum(g["u"], g["v"]), np.maximum(g["u"], g["v"])
    g["seg_id"] = a.astype(str) + "_" + b.astype(str) + "_" + g["key"].astype(str)
    g["u"], g["v"] = a.values, b.values
    g = g.drop_duplicates("seg_id")
    g["length_m"] = g.geometry.length
    g["highway"] = g["highway"].fillna("otra").str.split(";").str[0]
    g["via"] = g["highway"].map(HW_GRUPOS).fillna("otra")
    return g[["seg_id", "u", "v", "highway", "via", "length_m", "geometry"]].reset_index(drop=True)


def membresia_accesos(segs: gpd.GeoDataFrame, nodos: gpd.GeoDataFrame, accesos: gpd.GeoDataFrame, radio=RADIO_M):
    """Para cada punto de acceso, los segmentos a <= radio metros CAMINANDO por la red (Dijkstra con límite).

    Devuelve (membresia, snap): membresia = DataFrame(acceso_id, seg_id, dist_m); snap = distancia (m) del punto de
    acceso al nodo de la red más cercano (si es grande, la ubicación del acceso es dudosa).
    """
    ids = np.unique(np.r_[segs["u"].values, segs["v"].values])
    pos = pd.Series(np.arange(len(ids)), index=ids)
    su, sv = pos[segs["u"].values].values, pos[segs["v"].values].values
    l = segs["length_m"].values
    # aristas paralelas entre el mismo par de nodos: nos quedamos con la más corta (csr sumaría duplicados)
    par = pd.DataFrame({"a": su, "b": sv, "l": l}).groupby(["a", "b"], as_index=False)["l"].min()
    A = csr_matrix((par["l"], (par["a"], par["b"])), shape=(len(ids), len(ids)))
    nxy = nodos.to_crs(CRS_M).set_index("osmid").loc[ids]
    xy = np.c_[nxy.geometry.x, nxy.geometry.y]
    axy = np.c_[accesos.geometry.x, accesos.geometry.y]
    snap, nn = cKDTree(xy).query(axy)
    filas = []
    for k, (i, s) in enumerate(zip(nn, snap)):
        lim = radio - s
        if lim <= 0:
            continue
        d = dijkstra(A, directed=False, indices=int(i), limit=lim)
        dm = np.minimum(d[su], d[sv])
        m = np.isfinite(dm)
        filas.append(pd.DataFrame({"acceso_id": accesos["acceso_id"].iloc[k], "seg_id": segs["seg_id"].values[m],
                                   "dist_m": dm[m] + s}))
    return pd.concat(filas, ignore_index=True), pd.Series(snap, index=accesos["acceso_id"].values, name="snap_m")


# ----------------------------------------------------------------------------- eventos -> segmentos
def asignar_eventos(ev: pd.DataFrame, segs_zona: gpd.GeoDataFrame, max_m=40) -> pd.DataFrame:
    """Cada evento va al segmento más cercano a <= max_m metros (si no hay, queda sin asignar)."""
    pts = gpd.GeoDataFrame(ev[["id_dgc"]], geometry=gpd.points_from_xy(ev["long_hecho"], ev["lat_hecho"]), crs=4326).to_crs(CRS_M)
    x0, y0, x1, y1 = segs_zona.total_bounds
    pts = pts.cx[x0 - max_m: x1 + max_m, y0 - max_m: y1 + max_m]
    j = gpd.sjoin_nearest(pts, segs_zona[["seg_id", "geometry"]], max_distance=max_m, distance_col="dist_evento_m")
    return j.drop_duplicates("id_dgc")[["id_dgc", "seg_id", "dist_evento_m"]]


def comisaria_por_segmento(ev_seg: pd.DataFrame, segs: gpd.GeoDataFrame) -> pd.Series:
    """Comisaría de cada segmento = la del evento (ya asignado) más cercano. Sirve para la cobertura."""
    c = segs.set_index("seg_id").geometry.centroid
    e = ev_seg.drop_duplicates("seg_id").set_index("seg_id")
    pe = np.c_[c.loc[e.index].x, c.loc[e.index].y]
    _, k = cKDTree(pe).query(np.c_[c.x, c.y])
    return pd.Series(e["comisaria_hecho"].values[k], index=c.index, name="comisaria")


def matriz_vecindad(segs: gpd.GeoDataFrame) -> csr_matrix:
    """Matriz binaria segmento x segmento: 1 si comparten un nodo (calles contiguas)."""
    ids = np.unique(np.r_[segs["u"].values, segs["v"].values])
    pos = pd.Series(np.arange(len(ids)), index=ids)
    n = len(segs)
    r = np.r_[np.arange(n), np.arange(n)]
    c = np.r_[pos[segs["u"].values].values, pos[segs["v"].values].values]
    B = coo_matrix((np.ones(2 * n), (r, c)), shape=(n, len(ids))).tocsr()
    S = (B @ B.T).tocsr()
    S.setdiag(0); S.eliminate_zeros(); S.data[:] = 1
    return S


def conteo_pois(pois: gpd.GeoDataFrame, segs: gpd.GeoDataFrame, max_m=50) -> pd.DataFrame:
    """POIs de OSM por categoría a <= max_m metros de cada segmento (uso del suelo, no ingreso)."""
    p = pois.to_crs(CRS_M)
    j = gpd.sjoin_nearest(p, segs[["seg_id", "geometry"]], max_distance=max_m)
    t = j.groupby(["seg_id", "cat"]).size().unstack(fill_value=0).add_prefix("poi_")
    return t.reindex(segs["seg_id"]).fillna(0)


# ----------------------------------------------------------------------------- panel segmento x año
def peso_cobertura(ev: pd.DataFrame, cob: pd.DataFrame) -> pd.Series:
    """Peso = 1 / cobertura(comisaría, año), con tope 1/COB_MIN. cob: columnas comisaria_hecho, anio, cobertura."""
    m = ev.merge(cob[["comisaria_hecho", "anio", "cobertura"]], on=["comisaria_hecho", "anio"], how="left")
    return (1 / m["cobertura"].fillna(cob["cobertura"].median()).clip(lower=COB_MIN)).values


def meses_validos(anio: int, meses_bajos: set, desde=2018) -> int:
    """Meses del año `anio` con cobertura suficiente (no están en la lista de meses de baja cobertura)."""
    return sum(f"{anio}-{m:02d}" not in meses_bajos for m in range(1, 13))


def construir_panel(ev: pd.DataFrame, segs: pd.DataFrame, seg_com: pd.Series, S: csr_matrix, cob: pd.DataFrame,
                    meses_bajos: set, anios_obj, anio_ini=2018) -> pd.DataFrame:
    """Una fila por (segmento, año objetivo). Features con eventos de años < Y; objetivos con eventos del año Y.

    ev: eventos ya asignados a segmento, con id_dgc, seg_id, fecha_hora_hecho, anio, turno_hecho, grupo, comisaria_hecho.
    Los meses de baja cobertura se descartan tanto de features como de objetivos.
    """
    ev = ev.copy()
    ev["ym"] = ev["fecha_hora_hecho"].dt.strftime("%Y-%m")
    ev = ev[~ev["ym"].isin(meses_bajos)]
    ev["w"] = peso_cobertura(ev, cob)
    ev["noche"] = ev["turno_hecho"].isin(["noche", "madrugada"])
    ev["pat"] = ev["grupo"].isin(GRUPOS_PATRIMONIO)
    ev["per"] = ev["grupo"].isin(GRUPOS_PERSONA)
    idx = pd.Series(np.arange(len(segs)), index=segs["seg_id"].values)
    n = len(segs)
    estat = segs.set_index("seg_id")
    out = []
    for Y in anios_obj:
        past, tgt = ev[ev["anio"] < Y], ev[ev["anio"] == Y]
        m_past = max(sum(meses_validos(a, meses_bajos) for a in range(anio_ini, Y)), 1)
        m_prev = max(meses_validos(Y - 1, meses_bajos), 1)
        def agg(df, col="w", mask=None):
            d = df if mask is None else df[mask]
            return np.bincount(idx[d["seg_id"]].values, weights=d[col].values if col else None, minlength=n)
        pw = past["w"].values
        edad = (Y - past["fecha_hora_hecho"].dt.year - past["fecha_hora_hecho"].dt.month / 12.0 + 1).clip(lower=0.0)
        dec = np.bincount(idx[past["seg_id"]].values, weights=pw * np.exp(-edad.values / TAU_ANIOS), minlength=n)
        tasa_all = agg(past) / m_past
        tasa_prev = agg(past[past["anio"] == Y - 1]) / m_prev
        tasa_pat = agg(past, mask=past["pat"]) / m_past
        tasa_per = agg(past, mask=past["per"]) / m_past
        noche = agg(past, mask=past["noche"]) / m_past
        n1 = S @ tasa_all
        n2 = S @ n1
        f = pd.DataFrame({
            "seg_id": segs["seg_id"].values, "anio_obj": Y,
            "tasa_all": tasa_all, "tasa_prev": tasa_prev, "decay": dec / m_past * 12,
            "tasa_pat": tasa_pat, "tasa_per": tasa_per, "frac_noche": np.where(tasa_all > 0, noche / np.maximum(tasa_all, 1e-12), np.nan),
            "vec1": n1, "vec2": n2, "n_vec1": np.asarray(S.sum(axis=1)).ravel(),
            "n_eventos_pasado": np.bincount(idx[past["seg_id"]].values, minlength=n),
        })
        # objetivos: conteos observados (sin ponderar) en meses válidos del año Y
        f["y_total"] = agg(tgt, None)
        f["y_noche"] = agg(tgt, None, tgt["noche"])
        f["y_dia"] = f["y_total"] - f["y_noche"]
        f["y_pat"] = agg(tgt, None, tgt["pat"])
        f["y_per"] = agg(tgt, None, tgt["per"])
        cb = cob[cob["anio"] == Y].set_index("comisaria_hecho")["cobertura"]
        cobY = np.asarray(seg_com.reindex(f["seg_id"]).map(cb.astype(float)).astype(float).fillna(float(cob["cobertura"].astype(float).median())).values, dtype=float)
        f["cobertura"] = cobY
        f["expo"] = meses_validos(Y, meses_bajos) / 12.0 * np.maximum(cobY, 0.02)   # exposición del Poisson (offset); sin el tope de los pesos
        out.append(f)
    p = pd.concat(out, ignore_index=True)
    st = estat[["via", "length_m"]].reset_index()
    return p.merge(st, on="seg_id", how="left")
