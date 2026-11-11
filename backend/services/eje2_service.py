"""Eje 2 · ruta peatonal segura sobre el grafo de calles de las zonas de ~10 min de cada estación o paradero.

Cómo funciona (detalle en docs/EJE2_RUTA_SEGURA.md):
- El grafo (146 607 segmentos) y el riesgo de cada calle (0-1, por franja día/noche) vienen de ``data/eje2``,
  exportados desde los notebooks de week12. No depende de geopandas ni de osmnx.
- Costo por calle ``largo × (1 + λ · riesgo)``; λ = 0 es la ruta más corta. Se resuelve con Dijkstra de scipy.
- ``riesgo_efectivo = clip(riesgo_base + ajuste_por_reportes, 0, 1)``; el ajuste lo calcula
  ``services/eje2_reportes`` con los reportes de usuarios (solo si hay evidencia suficiente en la zona).
- Siempre se calculan las dos rutas (normal y segura); la segura es la recomendada salvo que su desvío no valga la pena.

Es riesgo de **denuncias registradas** (subregistro, sesgo social), no probabilidad de ser víctima.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from functools import lru_cache
from pathlib import Path

import gc

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from services import calendario, polilinea

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_EJE2 = BASE_DIR / "data" / "eje2"

LAT0 = -12.05                                  # Lima: proyección equirectangular local (error < 0,3 % en la zona)
M_LAT = 111_132.0
M_LON = 111_320.0 * math.cos(math.radians(LAT0))

SNAP_MAX_M = 150.0                             # distancia máxima del punto del usuario a una calle del grafo
SNAP_ACCESO_MAX_M = 50.0                       # estación del backend -> punto de acceso del Eje 2
ALCANCE_MAX_M = 2500.0                         # el origen debe estar a ≤ 2,5 km caminando del destino
FRANJAS = ("dia", "noche")
ETIQUETA_VIA = {"peatonal": "pasaje o vereda peatonal", "residencial": "calle residencial", "arterial": "avenida",
                "servicio": "vía de servicio", "otra": "vía"}
AVISO = ("Basado en denuncias registradas (hay subregistro y sesgo social), con datos hasta {datos_hasta}. "
         "No es la probabilidad de ser víctima. En una emergencia llama al 105.")


class Eje2Error(ValueError):
    """Error de entrada o de cobertura: la API responde 4xx con el mensaje."""

    def __init__(self, mensaje: str, status: int = 400):
        super().__init__(mensaje)
        self.status = status


class SinAccesoError(Eje2Error):
    """La estación existe en /api/stations pero no tiene un punto de acceso del Eje 2 cerca (sin índice de seguridad)."""

    def __init__(self, mensaje: str, estacion: dict):
        super().__init__(mensaje, 404)
        self.estacion = estacion


# --------------------------------------------------------------------------- utilidades
def franja_de(momento: dt.datetime | None = None) -> str:
    """'noche' de 18:00 a 05:59 (hora de Lima) y 'dia' el resto, igual que el turno del modelo."""
    momento = momento or calendario.ahora_lima()
    return "noche" if momento.hour >= 18 or momento.hour < 6 else "dia"


def banda(r: float, bandas: dict) -> str:
    return "bajo" if r < bandas["bajo_hasta"] else ("medio" if r < bandas["alto_desde"] else "alto")


def _xy(lat, lon):
    return np.c_[np.asarray(lon, float) * M_LON, np.asarray(lat, float) * M_LAT]


def _liberar_memoria() -> None:
    """Devuelve al sistema la memoria temporal de la carga (pyarrow y el asignador de C)."""
    gc.collect()
    pa.default_memory_pool().release_unused()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:                                      # no es Linux/glibc: no pasa nada
        pass


# --------------------------------------------------------------------------- grafo
class GrafoEje2:
    """Grafo en memoria (arreglos numpy). Una instancia por proceso; las rutas no la modifican."""

    def __init__(self, directorio: Path = DATA_EJE2):
        directorio = Path(directorio)
        self.manifest = json.loads((directorio / "manifest.json").read_text(encoding="utf-8"))
        # Se lee con pyarrow y los textos (ids de calle, nombres, geometrías) se dejan en formato columnar compacto: como
        # objetos de Python ocuparían ~100 MB por proceso. Solo se materializan cuando una consulta los necesita.
        g = pq.read_table(directorio / "grafo.parquet")
        self.n_seg = g.num_rows
        self._seg_id = g["seg_id"].combine_chunks()
        self._nombre = g["nombre"].combine_chunks()
        via = g["via"].combine_chunks()
        via = via if pa.types.is_dictionary(via.type) else via.dictionary_encode()
        self._via_cod = via.indices.to_numpy(zero_copy_only=False).astype(np.int16)
        self._via_lista = via.dictionary.to_pylist()
        self.largo = g["largo_m"].to_numpy().astype(np.float64)
        self.riesgo = {f: g[f"riesgo_{f}"].to_numpy().astype(np.float64) for f in ("total", "noche", "dia")}
        u, v = g["u"].to_numpy(), g["v"].to_numpy()

        geo = pq.read_table(directorio / "geometrias.parquet")
        pos_geo = pc.index_in(self._seg_id, value_set=geo["seg_id"].combine_chunks())     # posición de cada segmento en geometrias
        self._geom = geo["geom"].combine_chunks().take(pos_geo)

        n = pq.read_table(directorio / "nodos.parquet")
        self.nodo_ids = n["nodo"].to_numpy().astype(np.int64)
        self.nodo_lonlat = np.c_[n["lon"].to_numpy(), n["lat"].to_numpy()].astype(np.float64)
        self.n = len(self.nodo_ids)
        orden = np.argsort(self.nodo_ids)
        self._ids_ord, self._pos_ord = self.nodo_ids[orden], orden                          # id de nodo OSM -> posición (sin dict ni Series)
        self.nodo_xy = _xy(self.nodo_lonlat[:, 1], self.nodo_lonlat[:, 0])
        self.tree = cKDTree(self.nodo_xy)
        self._muestras_cache = None
        self._por_nodo = None

        self.seg_u = self.posicion_nodos(u)                                                # índice del nodo u (la geometría va de u a v)
        self.seg_v = self.posicion_nodos(v)
        self._armar_csr()

        self.accesos = pd.read_parquet(directorio / "accesos.parquet").reset_index(drop=True)
        self.acc_indice = {a: i for i, a in enumerate(self.accesos["acceso_id"])}
        self.acc_tree = cKDTree(_xy(self.accesos["lat"], self.accesos["lon"]))
        self.acc_nodo = self.posicion_nodos(self.accesos["nodo"].to_numpy())
        del g, geo, n, via, pos_geo
        _liberar_memoria()

    # -- acceso compacto a los textos de cada segmento --
    def posicion_nodos(self, ids: np.ndarray) -> np.ndarray:
        j = np.searchsorted(self._ids_ord, ids)
        if np.any(j >= len(self._ids_ord)) or np.any(self._ids_ord[np.minimum(j, len(self._ids_ord) - 1)] != ids):
            raise ValueError("hay nodos del grafo sin coordenadas en nodos.parquet")
        return self._pos_ord[j]

    def seg_id_de(self, i) -> str:
        return self._seg_id[int(i)].as_py()

    def nombre_de(self, i) -> str | None:
        return self._nombre[int(i)].as_py()

    def via_de(self, i) -> str:
        return self._via_lista[self._via_cod[int(i)]]

    def geom_de(self, i) -> str | None:
        return self._geom[int(i)].as_py()

    @property
    def seg_id(self) -> np.ndarray:
        """Arreglo de ids (se materializa la primera vez; el código del servidor usa ``seg_id_de``)."""
        return self._seg_id.to_numpy(zero_copy_only=False)

    # -- estructura CSR fija: por consulta solo cambia `data` --
    def _armar_csr(self) -> None:
        a, b = self.seg_u, self.seg_v
        par = np.minimum(a, b).astype(np.int64) * self.n + np.maximum(a, b)
        orden = np.lexsort((self.largo, par))                             # por par y, dentro, la más corta primero
        primero = np.r_[True, par[orden][1:] != par[orden][:-1]]
        mantener = orden[primero]                                          # aristas paralelas: se conserva la más corta
        self.segmentos_omitidos = len(self.largo) - len(mantener)
        ka, kb = a[mantener], b[mantener]
        filas = np.r_[ka, kb]
        cols = np.r_[kb, ka]
        seg = np.r_[mantener, mantener]
        o = np.lexsort((cols, filas))
        self._indices = cols[o].astype(np.int32)
        self._seg_de_entrada = seg[o]
        self._indptr = np.r_[0, np.cumsum(np.bincount(filas[o], minlength=self.n))].astype(np.int32)
        self._claves = filas[o].astype(np.int64) * self.n + cols[o]        # ordenadas: (fila, col) -> segmento
        self._claves_seg = seg[o]

    def matriz(self, costo_por_segmento: np.ndarray) -> csr_matrix:
        return csr_matrix((costo_por_segmento[self._seg_de_entrada], self._indices, self._indptr), shape=(self.n, self.n))

    # -- puntos --
    def nodo_cercano(self, lat: float, lon: float, max_m: float = SNAP_MAX_M) -> tuple[int, float]:
        d, i = self.tree.query(_xy([lat], [lon])[0])
        if d > max_m:
            raise Eje2Error(
                f"Ese punto queda a {d:.0f} m de la red de calles cubierta (máximo {max_m:.0f} m). El Eje 2 cubre "
                "los alrededores (~10 min a pie) de estaciones y paraderos del Metro L1, Metropolitano, corredores y alimentadores.", 422)
        return int(i), float(d)

    def segmentos_de_nodo(self, nodo: int) -> np.ndarray:
        """Segmentos que tocan un nodo (adyacencia en arreglos; se arma la primera vez que se usa)."""
        if self._por_nodo is None:
            nodos = np.r_[self.seg_u, self.seg_v]
            segs = np.r_[np.arange(self.n_seg), np.arange(self.n_seg)]
            o = np.argsort(nodos, kind="stable")
            self._por_nodo = (segs[o], np.r_[0, np.cumsum(np.bincount(nodos, minlength=self.n))])
        segs, ptr = self._por_nodo
        return segs[ptr[nodo]:ptr[nodo + 1]]

    def indices_de(self, ids: list[str]) -> np.ndarray:
        """Índice de segmento de cada seg_id (-1 si no existe), con búsqueda vectorizada (sin diccionarios en memoria)."""
        if not ids:
            return np.array([], dtype=np.int64)
        r = pc.index_in(pa.array(ids, type=pa.string()), value_set=self._seg_id)
        return r.fill_null(-1).to_numpy(zero_copy_only=False).astype(np.int64)

    # -- calle más cercana a un punto (para ubicar reportes) --
    def _muestras(self):
        """Puntos cada ~50 m sobre cada segmento (recta u-v) para buscar candidatos rápido; se arma la primera vez que se usa."""
        if self._muestras_cache is None:
            n_i = np.maximum(1, np.ceil(self.largo / 50.0).astype(np.int64))
            seg = np.repeat(np.arange(len(self.largo)), n_i)
            k = np.arange(int(n_i.sum())) - np.repeat(np.cumsum(n_i) - n_i, n_i)
            t = ((k + 0.5) / np.repeat(n_i, n_i))[:, None]
            pu, pv = self.nodo_xy[self.seg_u[seg]], self.nodo_xy[self.seg_v[seg]]
            self._muestras_cache = (cKDTree(pu + (pv - pu) * t), seg)
            _liberar_memoria()
        return self._muestras_cache

    def _polilinea_xy(self, s: int) -> np.ndarray:
        g = self.geom_de(s)
        if g:
            lonlat = np.array(polilinea.decodificar(g))
            return _xy(lonlat[:, 1], lonlat[:, 0])
        return self.nodo_xy[[self.seg_u[s], self.seg_v[s]]]

    @staticmethod
    def _dist_a_polilinea(p: np.ndarray, pts: np.ndarray) -> float:
        a, b = pts[:-1], pts[1:]
        ab = b - a
        den = np.maximum((ab ** 2).sum(axis=1), 1e-9)
        t = np.clip(((p - a) * ab).sum(axis=1) / den, 0.0, 1.0)
        return float(np.linalg.norm(p - (a + ab * t[:, None]), axis=1).min())

    def segmento_cercano(self, lat: float, lon: float, max_m: float = 40.0) -> tuple[int, float]:
        """(índice del segmento, distancia en m) de la calle más cercana al punto; 422 si ninguna queda a ≤ max_m."""
        tree, seg_de_muestra = self._muestras()
        p = _xy([lat], [lon])[0]
        idx = tree.query_ball_point(p, r=max_m + 60.0)
        mejor_s, mejor_d = -1, float("inf")
        for s in np.unique(seg_de_muestra[idx]) if idx else []:
            d = self._dist_a_polilinea(p, self._polilinea_xy(int(s)))
            if d < mejor_d:
                mejor_s, mejor_d = int(s), d
        if mejor_s < 0 or mejor_d > max_m:
            raise Eje2Error(f"Ese punto queda a {mejor_d if mejor_s >= 0 else 'más de ' + str(int(max_m + 60))} m de una calle cubierta "
                            f"(máximo {max_m:.0f} m). Reporta en una calle cercana a una estación o paradero.", 422)
        return mejor_s, mejor_d

    def riesgo_efectivo(self, franja: str, deltas: dict | None = None) -> np.ndarray:
        r = self.riesgo[franja]
        if deltas and deltas.get(franja) is not None:
            r = np.clip(r + deltas[franja], 0.0, 1.0)
        return r

    def densidad(self, r: np.ndarray, franja: str) -> np.ndarray:
        """Eventos esperados por km y año (aprox.), deshaciendo la escala log1p(d)/log1p(p99) del modelo."""
        ref = self.manifest["ref_p99_densidad"][franja]
        return np.expm1(r * math.log1p(ref))

    # -- camino mínimo --
    def camino(self, origen: int, destino: int, costo: np.ndarray, limite: float) -> tuple[np.ndarray, list[int]] | None:
        """(segmentos en orden, nodos en orden) del camino de menor costo, o None si no se alcanza dentro del límite."""
        if origen == destino:
            return np.array([], dtype=np.int64), [origen]
        dist, pred = dijkstra(self.matriz(costo), directed=True, indices=origen, return_predecessors=True, limit=limite)
        if not np.isfinite(dist[destino]):
            return None
        nodos = [destino]
        while nodos[-1] != origen:
            nodos.append(int(pred[nodos[-1]]))
        nodos = nodos[::-1]
        a = np.array(nodos[:-1], dtype=np.int64)
        b = np.array(nodos[1:], dtype=np.int64)
        pos = np.searchsorted(self._claves, a * self.n + b)
        return self._claves_seg[pos], nodos

    def geometria(self, segs: np.ndarray, nodos: list[int]) -> list[list[float]]:
        """Coordenadas [lon, lat] de la ruta, orientando cada tramo según el sentido en que se recorre."""
        out: list[list[float]] = []
        for k, s in enumerate(segs):
            gm = self.geom_de(s)
            pts = polilinea.decodificar(gm) if gm else [tuple(self.nodo_lonlat[nodos[k]]), tuple(self.nodo_lonlat[nodos[k + 1]])]
            if nodos[k] != self.seg_u[s]:
                pts = pts[::-1]
            if out and out[-1] == list(pts[0]):
                pts = pts[1:]
            out.extend([list(p) for p in pts])
        if not out and nodos:
            out = [list(self.nodo_lonlat[nodos[0]])]
        return out

    # -- accesos (estaciones y paraderos) --
    def acceso_por_id(self, acceso_id: str) -> pd.Series:
        i = self.acc_indice.get(acceso_id)
        if i is None:
            raise Eje2Error(f"No existe el punto de acceso '{acceso_id}'", 404)
        return self.accesos.iloc[i]

    def accesos_cercanos(self, lat: float, lon: float, radio_m: float = 800.0, limite: int = 20) -> list[dict]:
        d, idx = self.acc_tree.query(_xy([lat], [lon])[0], k=min(max(limite * 4, 50), len(self.accesos)))
        out = []
        for dist, i in zip(np.atleast_1d(d), np.atleast_1d(idx)):
            if dist > radio_m:
                break
            out.append({**indice_de_acceso(self.accesos.iloc[int(i)]), "distancia_m": round(float(dist), 1)})
            if len(out) >= limite:
                break
        return out


@lru_cache(maxsize=1)
def grafo() -> GrafoEje2:
    return GrafoEje2(DATA_EJE2)


def precalentar() -> dict:
    """Carga el grafo y hace una consulta de prueba; devuelve el manifest (útil al arrancar el servidor)."""
    g = grafo()
    g.matriz(g.largo)
    return g.manifest


# --------------------------------------------------------------------------- índice por acceso
def indice_de_acceso(fila: pd.Series) -> dict:
    """Seguridad % de un acceso con su base del mismo tipo, intervalo y confianza (aproximación, no una probabilidad)."""
    return {
        "acceso_id": fila["acceso_id"], "tipo": fila["tipo"], "nombre": fila["nombre"],
        "ruta": None if pd.isna(fila["ruta"]) else fila["ruta"], "lat": float(fila["lat"]), "lon": float(fila["lon"]),
        "seguridad_pct": round(float(fila["seguridad_pct"])), "intervalo_pct": [round(float(fila["seg_lo"])), round(float(fila["seg_hi"]))],
        "base_tipo_pct": round(float(fila["base_tipo_pct"])), "confianza": fila["confianza"],
        "coordenada_aproximada": bool(fila["precision_coord"] == "aproximada") if "precision_coord" in fila else False,
        "aviso": "Estimación aproximada con denuncias registradas; compara contra la base del mismo tipo de acceso.",
    }


SISTEMA_A_TIPO = {"metropolitano": "troncal", "corredores": "corredor", "alimentadores": "alimentador", "metro_l1": "metro_l1"}


def acceso_de_estacion(g: GrafoEje2, station_id: str, sistema: str | None = None) -> pd.Series:
    """Punto de acceso del Eje 2 que corresponde a una estación/paradero de /api/stations (sistema + coordenada ≤ 50 m)."""
    from routes.stations import load_all_stations_into_memory      # import local: evita dependencias circulares
    cand = [e for e in load_all_stations_into_memory() if e["id"] == str(station_id) and (not sistema or e["system"] == sistema)]
    if not cand:
        raise Eje2Error(f"No existe la estación '{station_id}'", 404)
    mejor, mejor_d = None, 1e9
    for e in cand:
        tipo = SISTEMA_A_TIPO.get(e["system"])
        d, i = g.acc_tree.query(_xy([e["latitude"]], [e["longitude"]])[0], k=8)
        for dist, k in zip(np.atleast_1d(d), np.atleast_1d(i)):
            fila = g.accesos.iloc[int(k)]
            if fila["tipo"] == tipo and dist < mejor_d:
                mejor, mejor_d = fila, float(dist)
    if mejor is None or mejor_d > SNAP_ACCESO_MAX_M:
        raise SinAccesoError(f"La estación '{station_id}' no tiene un punto de acceso del Eje 2 a ≤ {SNAP_ACCESO_MAX_M:.0f} m", cand[0])
    return mejor


def resolver_destino(g: GrafoEje2, destino: dict) -> tuple[int, pd.Series | None]:
    """(nodo destino, punto de acceso o None) a partir de acceso_id, station_id o lat/lon."""
    if not isinstance(destino, dict):
        raise Eje2Error("destino debe ser un objeto con acceso_id, station_id o lat/lon")
    if destino.get("acceso_id"):
        fila = g.acceso_por_id(str(destino["acceso_id"]))
        return int(g.acc_nodo[g.acc_indice[fila["acceso_id"]]]), fila
    if destino.get("station_id"):
        try:
            fila = acceso_de_estacion(g, str(destino["station_id"]), destino.get("sistema"))
        except SinAccesoError as e:                    # paradero sin índice propio: se enruta hacia su coordenada
            return g.nodo_cercano(e.estacion["latitude"], e.estacion["longitude"])[0], None
        return int(g.acc_nodo[g.acc_indice[fila["acceso_id"]]]), fila
    if destino.get("lat") is not None and destino.get("lon") is not None:
        return g.nodo_cercano(float(destino["lat"]), float(destino["lon"]))[0], None
    raise Eje2Error("destino debe traer acceso_id, station_id o lat y lon")


# --------------------------------------------------------------------------- rutas
def _metricas(g: GrafoEje2, segs: np.ndarray, r: np.ndarray, franja: str) -> dict:
    largo = g.largo[segs]
    total = float(largo.sum())
    dens = g.densidad(r[segs], franja)
    return {
        "distancia_m": total,
        "minutos": total / g.manifest["velocidad_caminata_m_min"],
        "riesgo_medio": float((largo * r[segs]).sum() / total) if total > 0 else 0.0,
        "densidad_media": float((largo * dens).sum() / total) if total > 0 else 0.0,     # eventos/km·año, ponderada por largo
    }


def _tramos(g: GrafoEje2, segs: np.ndarray, r: np.ndarray, compartidos: set[int], bandas: dict) -> list[dict]:
    """Tramos consecutivos con el mismo nombre de calle (para mostrar la ruta por pasos)."""
    out: list[dict] = []
    for s in segs:
        nom = g.nombre_de(s) or ETIQUETA_VIA.get(g.via_de(s), "vía")
        desv = int(s) not in compartidos
        if out and out[-1]["nombre"] == nom and out[-1]["desvio"] == desv:
            t = out[-1]
            t["largo_m"] += float(g.largo[s]); t["_rl"] += float(g.largo[s] * r[s])
        else:
            out.append({"nombre": nom, "via": g.via_de(s), "largo_m": float(g.largo[s]), "_rl": float(g.largo[s] * r[s]), "desvio": desv})
    for t in out:
        t["riesgo"] = banda(t.pop("_rl") / t["largo_m"], bandas) if t["largo_m"] else "bajo"
        t["largo_m"] = round(t["largo_m"])
    return out


def _explicar(g, franja, lam, corta, segura, segs_c, segs_s, r, deltas, recomendada, motivo_no_segura, razon):
    bandas = g.manifest["bandas_riesgo"]
    set_c, set_s = set(map(int, segs_c)), set(map(int, segs_s))
    evitados = np.array(sorted(set_c - set_s), dtype=np.int64)
    tomados = np.array(sorted(set_s - set_c), dtype=np.int64)
    d_ev = float(np.sum(g.largo[evitados] * g.densidad(r[evitados], franja)) / max(g.largo[evitados].sum(), 1e-9)) if len(evitados) else 0.0
    d_to = float(np.sum(g.largo[tomados] * g.densidad(r[tomados], franja)) / max(g.largo[tomados].sum(), 1e-9)) if len(tomados) else 0.0
    por_nombre: dict[str, float] = {}
    for s in evitados:
        nom = g.nombre_de(s) or ETIQUETA_VIA.get(g.via_de(s), "vía")
        por_nombre[nom] = por_nombre.get(nom, 0.0) + float(g.largo[s])
    principales = [n for n, _ in sorted(por_nombre.items(), key=lambda kv: -kv[1])[:3]]
    con_reportes = bool(deltas and deltas.get(franja) is not None and len(evitados) and np.any(deltas[franja][evitados] > 0))
    motivos = []
    if len(evitados):
        riesgo_ev = banda(float(np.sum(g.largo[evitados] * r[evitados]) / g.largo[evitados].sum()), bandas)
        cuando = "de noche" if franja == "noche" else "de día"
        donde = f"{', '.join(principales)} ({round(float(g.largo[evitados].sum()))} m)" if principales else f"un tramo de {round(float(g.largo[evitados].sum()))} m"
        motivos.append(f"Evita {donde}, con un nivel {riesgo_ev} en el indicador de denuncias {cuando}.")
    if con_reportes:
        motivos.append("Hay reportes recientes de otras personas en esa zona.")
    return {
        "resumen": razon, "motivos": motivos,
        "tramos_evitados": [{"nombre": n, "largo_m": round(por_nombre[n])} for n in principales],
        "condiciones": {
            "franja": franja,
            "franja_regla": "noche de 18:00 a 05:59 (hora de Lima); día el resto",
            "lambda": lam, "forma_costo": g.manifest["forma_costo"],
            "datos_hasta": g.manifest["datos_hasta"], "version": g.manifest["version"],
            "recomendacion_si": (f"la ruta segura reduce el riesgo por metro ≥ {g.manifest['topes_recomendacion']['reduccion_min']:.0%} y "
                                 f"el camino extra es ≤ max({g.manifest['topes_recomendacion']['desvio_pct_max']:.0%}, "
                                 f"{g.manifest['topes_recomendacion']['desvio_m_max']} m)"),
            "reportes_aplicados": bool(deltas and deltas.get(franja) is not None and np.any(deltas[franja] > 0)),
        },
        "aviso": AVISO.format(datos_hasta=g.manifest["datos_hasta"]),
        "llamar_105": True,
    }


def rutas(origen: dict, destino: dict, preferencia: str = "segura", franja: str | None = None,
          salida: dt.datetime | None = None, lam: float | None = None, deltas: dict | None = None,
          g: GrafoEje2 | None = None, max_minutos_extra: float | None = None) -> dict:
    """Calcula la ruta normal y la segura entre un punto cualquiera y una estación/paradero.

    origen: {lat, lon}; destino: {acceso_id | station_id[, sistema] | lat, lon}; preferencia: 'segura' (defecto) | 'normal';
    franja: 'dia' | 'noche' (por defecto la de la hora de salida en Lima); lam: λ (por defecto el del manifest).
    max_minutos_extra: límite opcional respecto a la ruta corta. Filtra la candidata segura ya calculada;
    no busca todas las rutas posibles que podrían cumplir el límite. Sin valor conserva los topes anteriores.
    """
    g = g or grafo()
    if preferencia not in ("segura", "normal"):
        raise Eje2Error("preferencia debe ser 'segura' o 'normal'")
    if max_minutos_extra is not None:
        if isinstance(max_minutos_extra, bool):
            raise Eje2Error("max_minutos_extra debe ser un número finito mayor o igual que cero")
        try:
            max_minutos_extra = float(max_minutos_extra)
        except (TypeError, ValueError):
            raise Eje2Error("max_minutos_extra debe ser un número finito mayor o igual que cero") from None
        if not math.isfinite(max_minutos_extra) or max_minutos_extra < 0:
            raise Eje2Error("max_minutos_extra debe ser un número finito mayor o igual que cero")
    if franja is None:
        franja = franja_de(salida)
    if franja not in FRANJAS:
        raise Eje2Error("franja debe ser 'dia' o 'noche'")
    lam = float(g.manifest["lambda"] if lam is None else lam)
    if not 0 <= lam <= 50:
        raise Eje2Error("lambda debe estar entre 0 y 50")
    try:
        lat_o, lon_o = float(origen["lat"]), float(origen["lon"])
    except (KeyError, TypeError, ValueError):
        raise Eje2Error("origen debe traer lat y lon numéricos") from None
    o, d_snap = g.nodo_cercano(lat_o, lon_o)
    d, acceso = resolver_destino(g, destino)

    r = g.riesgo_efectivo(franja, deltas)
    corta = g.camino(o, d, g.largo, ALCANCE_MAX_M)
    if corta is None:
        raise Eje2Error(f"El origen queda a más de {ALCANCE_MAX_M / 1000:.1f} km caminando del destino (o sin camino por la red cubierta).", 422)
    segs_c, nodos_c = corta
    costo_seg = g.largo * (1.0 + lam * r)
    cota = float(costo_seg[segs_c].sum()) * (1 + 1e-9) + 1e-6                 # el camino seguro cuesta ≤ la corta evaluada con pesos de riesgo
    segura = g.camino(o, d, costo_seg, cota) or corta
    segs_s, nodos_s = segura

    m_c, m_s = _metricas(g, segs_c, r, franja), _metricas(g, segs_s, r, franja)
    iguales = list(map(int, segs_c)) == list(map(int, segs_s))
    extra_m = m_s["distancia_m"] - m_c["distancia_m"]
    extra_pct = extra_m / m_c["distancia_m"] if m_c["distancia_m"] > 0 else 0.0
    reduccion = 1 - m_s["densidad_media"] / m_c["densidad_media"] if m_c["densidad_media"] > 0 else 0.0
    t = g.manifest["topes_recomendacion"]
    minutos = extra_m / g.manifest["velocidad_caminata_m_min"]
    cumple_tolerancia = max_minutos_extra is None or minutos <= max_minutos_extra + 1e-9
    desvio_aceptable = (extra_m <= max(t["desvio_pct_max"] * m_c["distancia_m"], t["desvio_m_max"])
                       if max_minutos_extra is None else cumple_tolerancia)
    vale = reduccion >= t["reduccion_min"] and desvio_aceptable
    mas_tiempo = "menos de 1 minuto más" if minutos < 1 else f"unos {round(minutos)} minutos más"
    menos = f"un indicador estimado de denuncias por kilómetro {max(reduccion, 0):.0%} menor"
    if iguales:
        recomendada, razon = "misma", "El camino corto y la ruta segura coinciden."
    elif not cumple_tolerancia:
        recomendada = "normal"
        razon = (f"La ruta segura añade {minutos:.2f} min y supera tu límite de "
                 f"{max_minutos_extra:g} min adicionales. Seleccionamos el camino corto.")
    elif vale:
        recomendada = "segura"
        razon = f"Recomendamos la ruta segura. Caminas {mas_tiempo} ({extra_m:.0f} m más) y el trayecto tiene {menos}."
    elif reduccion >= t["reduccion_min"]:
        recomendada = "normal"
        razon = (f"La ruta segura tiene {menos}, pero añade {extra_m:.0f} m. "
                 f"Elige la que prefieras.")
    else:
        recomendada = "normal"
        razon = f"La ruta segura cambia poco el indicador y añade {extra_m:.0f} m. Elige la que prefieras."

    compartidos = set(map(int, segs_c)) & set(map(int, segs_s))
    bandas = g.manifest["bandas_riesgo"]

    def armar(tipo, segs, nodos, m):
        coords = g.geometria(segs, nodos)
        return {
            "tipo": tipo,
            "distancia_m": round(m["distancia_m"], 1), "minutos": round(m["minutos"], 1),
            "riesgo_medio": round(m["riesgo_medio"], 3), "banda_riesgo": banda(m["riesgo_medio"], bandas),
            "densidad_media_km_anio": round(m["densidad_media"], 2),
            "geojson": {"type": "Feature", "properties": {"tipo": tipo}, "geometry": {"type": "LineString", "coordinates": coords}},
            "tramos": _tramos(g, segs, r, compartidos if tipo == "segura" else set(map(int, segs_s)), bandas),
        }

    seleccionada = preferencia if recomendada != "misma" else "normal"
    if not cumple_tolerancia:
        seleccionada = "normal"
    explicacion = _explicar(g, franja, lam, m_c, m_s, segs_c, segs_s, r, deltas, recomendada, None, razon)
    respuesta = {
        "seleccionada": seleccionada,
        "recomendada": recomendada,
        "preferencia": preferencia,
        "franja": franja,
        "destino": indice_de_acceso(acceso) if acceso is not None else None,
        "origen_a_red_m": round(d_snap, 1),
        "comparacion": {"distancia_extra_m": round(extra_m, 1), "distancia_extra_pct": round(extra_pct, 3),
                        "minutos_extra": round(extra_m / g.manifest["velocidad_caminata_m_min"], 1),
                        "reduccion_riesgo_pct": round(reduccion, 3)},
        "rutas": {"normal": armar("normal", segs_c, nodos_c, m_c), "segura": armar("segura", segs_s, nodos_s, m_s)},
        "explicacion": explicacion,
    }
    if max_minutos_extra is not None:
        respuesta["tolerancia_caminata"] = {
            "max_minutos_extra": max_minutos_extra,
            "minutos_extra_segura": round(max(0.0, minutos), 3),
            "cumple_segura": cumple_tolerancia,
            "metodo": "comparacion_de_dos_rutas",
            "aviso": "Se comparan el camino corto y la ruta segura (ponderada por denuncias). No se buscan todas las rutas posibles que podrían cumplir tu límite.",
        }
        explicacion["condiciones"]["max_minutos_extra"] = max_minutos_extra
        explicacion["condiciones"]["recomendacion_si"] = (
            f"la alternativa calculada reduce el riesgo por metro ≥ {t['reduccion_min']:.0%} "
            f"y añade como máximo {max_minutos_extra:g} min respecto a la ruta normal")
    return respuesta


# --------------------------------------------------------------------------- ajustes por reportes (se llenan desde la base)
def deltas_desde_filas(g: GrafoEje2, filas) -> dict:
    """filas: iterable de (seg_id, franja, delta) -> {'dia': arreglo, 'noche': arreglo} alineados con los segmentos."""
    filas = list(filas)
    out = {f: np.zeros(g.n_seg) for f in FRANJAS}
    for i, (_, franja, delta) in zip(g.indices_de([f[0] for f in filas]), filas):
        if i >= 0 and franja in out:
            out[franja][i] = float(delta)
    return out
