from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import folium
    from branca.colormap import linear as _cm
except ImportError:
    folium = None
    _cm = None

LIMA = [-12.0464, -77.0428]


def load_puntos(geo_dir: Path, sistema: str) -> pd.DataFrame:
    path = geo_dir / f"puntos_{sistema}.geojson"
    if not path.exists():
        # aliases
        alt = {
            "metro_l1": "puntos_metro_l1.geojson",
            "corredor": "puntos_corredores.geojson",
            "corredores": "puntos_corredores.geojson",
            "troncal": "puntos_troncal.geojson",
            "alimentador": "puntos_alimentadores.geojson",
            "alimentadores": "puntos_alimentadores.geojson",
        }
        path = geo_dir / alt.get(sistema, f"puntos_{sistema}.geojson")
    if not path.exists():
        return pd.DataFrame(columns=["unidad", "lat", "lon", "label"])
    fc = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for f in fc.get("features", []):
        props = f.get("properties", {})
        lon, lat = f["geometry"]["coordinates"][:2]
        unidad = props.get("unidad") or props.get("estacion") or props.get("cod_paradero")
        label = (
            props.get("estacion")
            or props.get("paradero")
            or props.get("cod_paradero")
            or str(unidad)
        )
        rows.append({"unidad": str(unidad), "lat": float(lat), "lon": float(lon), "label": str(label)})
    return pd.DataFrame(rows).drop_duplicates("unidad")


def load_trazado_path(geo_dir: Path, sistema: str) -> Path | None:
    candidates = [
        geo_dir / f"trazado_{sistema}.geojson",
        geo_dir / f"trazados_{sistema}.geojson",
        geo_dir / {
            "metro_l1": "trazado_metro_l1.geojson",
            "corredor": "trazados_corredores.geojson",
            "corredores": "trazados_corredores.geojson",
            "troncal": "trazado_troncal.geojson",
            "alimentador": "trazados_alimentadores.geojson",
            "alimentadores": "trazados_alimentadores.geojson",
        }.get(sistema, ""),
    ]
    for p in candidates:
        if p and p.exists():
            return p
    return None


def mapa_demanda(
    df: pd.DataFrame,
    puntos: pd.DataFrame,
    *,
    unidad_col: str,
    trazado: Path | None = None,
    nivel: str = "dow",
    fecha: str = "2025-07-15",
    dia_sem: str = "MAR",
    hora: int = 8,
    color_linea: str = "#1f4e79",
    save_html: Path | None = None,
    trazado_filter: dict | None = None,
    highlight_unidad: str | None = None,
    tooltip_extra: dict | None = None,
    unidades_keep: list | None = None,
):
    """Mapa estilo week07 TransMilenio. Devuelve folium.Map o None.

    trazado_filter: p.ej. {"ruta": "204"} o {"servicio_slug": "RegularA"}
    highlight_unidad: resalta una estación/paradero
    tooltip_extra: dict unidad -> texto extra (servicios que pasan)
    unidades_keep: si se pasa, filtra burbujas a esas unidades
    """
    import re
    import unicodedata

    def _norm(s: str) -> str:
        t = unicodedata.normalize("NFKD", str(s).lower())
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", " ", t).strip()

    if folium is None:
        print("Instala folium/branca para ver el mapa")
        return None
    if puntos is None or puntos.empty:
        print("Sin puntos geocodificados para este sistema")
        return None

    d = df.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    if nivel == "dia":
        day = pd.Timestamp(fecha).date()
        sub = d[d["fecha"].dt.date == day]
        label = f"día {day}"
    elif nivel == "dow":
        sub = d[d["dia_semana"] == dia_sem]
        label = f"total de todos los {dia_sem} del periodo"
    else:
        sub = d[d["hora"].astype(int) == int(hora)]
        label = f"hora {int(hora):02d}:00 (todo el periodo)"

    print(f"Viendo {label}: {len(sub):,} filas, {sub['validaciones'].sum():,.0f} validaciones")
    if sub.empty:
        print("Sin datos para esa selección")
        return None

    agg = (
        sub.groupby(unidad_col, as_index=False)["validaciones"]
        .sum()
        .rename(columns={unidad_col: "unidad", "validaciones": "val"})
    )
    agg["unidad"] = agg["unidad"].astype(str)
    pts = puntos.copy()
    pts["unidad"] = pts["unidad"].astype(str)

    # 1) exact join
    geo = agg.merge(pts, on="unidad", how="inner")
    # 2) if poor match, join on normalized names
    if len(geo) < max(3, 0.3 * agg["unidad"].nunique()):
        agg2 = agg.copy()
        agg2["unidad_norm"] = agg2["unidad"].map(_norm)
        pts2 = pts.copy()
        pts2["unidad_norm"] = pts2["label"].map(_norm)
        # also try unidad field
        pts2b = pts.copy()
        pts2b["unidad_norm"] = pts2b["unidad"].map(_norm)
        pts_n = pd.concat([pts2, pts2b]).drop_duplicates("unidad_norm")
        geo = agg2.merge(pts_n, on="unidad_norm", how="inner", suffixes=("", "_p"))
        if "label" not in geo.columns:
            geo["label"] = geo["unidad"]

    print(
        f"Unidades en mapa: {len(geo)} / {agg['unidad'].nunique()} con demanda en la selección "
        f"({100 * len(geo) / max(agg['unidad'].nunique(), 1):.1f}% geocodificadas)"
    )
    if unidades_keep is not None:
        keep = {str(x) for x in unidades_keep}
        # also allow match by label
        geo = geo[
            geo["unidad"].astype(str).isin(keep)
            | geo.get("label", geo["unidad"]).astype(str).isin(keep)
        ].copy()
        print(f"  filtrado a unidades del trazado: {len(geo)}")
    if geo.empty:
        return None

    vmax = float(geo["val"].max()) if geo["val"].max() > 0 else 1.0
    cmap = _cm.YlOrRd_09.scale(0.0, float(np.log1p(vmax)))
    _fmt = lambda x: (f"{x/1e6:.1f}M" if x >= 1e6 else (f"{x/1e3:.0f}k" if x >= 1e3 else f"{x:.0f}"))
    _breaks = sorted({0.0, vmax} | {t for t in [1e3, 5e3, 1e4, 5e4, 1e5, 2.5e5, 5e5, 1e6]
                                   if 0 < t < vmax})

    def _pct(v):
        return float(np.log1p(v)) / float(np.log1p(vmax)) * 100

    _stops = ", ".join(f"{cmap(float(np.log1p(v)))} {_pct(v):.1f}%" for v in _breaks)
    _labels = "".join(
        f'<span style="position:absolute;left:{_pct(v):.1f}%;transform:translateX(-50%)">'
        f"{_fmt(v)}</span>" for v in [_breaks[0], _breaks[-1]]
    )
    leyenda = f'''
<div style="position:fixed;bottom:30px;right:15px;z-index:9999;background:#fff;
            padding:8px 14px;border-radius:6px;border:1px solid #ccc;
            box-shadow:0 1px 4px rgba(0,0,0,.2);font:12px sans-serif;line-height:1.2;">
  <div><b>Total de validaciones</b> <span style="color:#888">(escala log)</span></div>
  <div style="width:200px;height:12px;border-radius:3px;margin:6px 0 2px;
              background:linear-gradient(to right, {_stops});"></div>
  <div style="position:relative;width:200px;height:14px;">{_labels}</div>
  <div style="margin-top:4px;color:#555;font-size:11px;">{label}</div>
</div>'''

    m = folium.Map(location=LIMA, zoom_start=11, tiles="OpenStreetMap")
    if trazado is not None and Path(trazado).exists():
        fc = json.loads(Path(trazado).read_text(encoding="utf-8"))
        if trazado_filter:
            key, val = next(iter(trazado_filter.items()))
            fc = {
                **fc,
                "features": [
                    f for f in fc.get("features", [])
                    if str(f.get("properties", {}).get(key, "")) == str(val)
                ],
            }
        if fc.get("features"):
            # color from first feature if present
            col0 = fc["features"][0].get("properties", {}).get("color_hex") or color_linea

            def _split_jumps(feat, max_km=3.0):
                """Parte LineString si hay saltos absurdos (join erróneo)."""
                geom = feat.get("geometry") or {}
                if geom.get("type") != "LineString":
                    return [feat]
                coords = geom.get("coordinates") or []
                if len(coords) < 2:
                    return [feat]
                segs, cur = [], [coords[0]]
                for i in range(1, len(coords)):
                    a = (coords[i - 1][1], coords[i - 1][0])
                    b = (coords[i][1], coords[i][0])
                    lon1, lat1 = np.radians(a[1]), np.radians(a[0])
                    lon2, lat2 = np.radians(b[1]), np.radians(b[0])
                    dlat, dlon = lat2 - lat1, lon2 - lon1
                    x = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
                    km = float(2 * 6371 * np.arcsin(np.sqrt(x)))
                    if km > max_km:
                        if len(cur) >= 2:
                            segs.append(cur)
                        cur = [coords[i]]
                    else:
                        cur.append(coords[i])
                if len(cur) >= 2:
                    segs.append(cur)
                out = []
                for s in segs:
                    nf = {"type": "Feature", "properties": dict(feat.get("properties") or {}),
                          "geometry": {"type": "LineString", "coordinates": s}}
                    out.append(nf)
                return out or [feat]

            feats2 = []
            for f in fc["features"]:
                feats2.extend(_split_jumps(f))
            fc = {**fc, "features": feats2}
            folium.GeoJson(
                fc,
                name="Trazado",
                style_function=lambda _, c=col0: {"color": c, "weight": 3, "opacity": 0.75},
            ).add_to(m)

    r = np.sqrt(geo["val"] / vmax) * 14 + 3
    highlight_norm = _norm(highlight_unidad) if highlight_unidad else None
    for i, row in geo.iterrows():
        c = cmap(float(np.log1p(row["val"])))
        tip = f"{row.get('label', row['unidad'])}<br>{row['val']:,.0f} validaciones"
        if tooltip_extra and row["unidad"] in tooltip_extra:
            tip += f"<br>{tooltip_extra[row['unidad']]}"
        weight = 1
        if highlight_norm and _norm(str(row.get("label", row["unidad"]))) == highlight_norm:
            weight = 4
            c = "#0d47a1"
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=float(r.loc[i]),
            color=c, fillColor=c, fill=True,
            fillOpacity=0.85, weight=weight, opacity=0.9,
            tooltip=tip,
        ).add_to(m)

    m.get_root().html.add_child(folium.Element(leyenda))
    folium.LayerControl(collapsed=False).add_to(m)
    if save_html is not None:
        save_html = Path(save_html)
        save_html.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(save_html))
        print(f"  [mapa] {save_html}")
    return m


def find_mapa_atu_corredor(fuentes: Path, corredor: str, ruta: str) -> Path | None:
    """Primera imagen tipo mapa_ruta para corredor+ruta."""
    csv_p = Path(fuentes) / "mapas_corredores_atu.csv"
    if not csv_p.exists():
        return None
    df = pd.read_csv(csv_p)
    df = df[(df["corredor"].astype(str) == str(corredor)) & (df["ruta"].astype(str) == str(ruta))]
    df = df[df["ok"].astype(str).str.lower().isin(["true", "1"]) & df["archivo_local"].notna()]
    prefer = df[df["tipo"] == "mapa_ruta"]
    use = prefer if len(prefer) else df
    for _, r in use.iterrows():
        p = Path(fuentes) / str(r["archivo_local"])
        if p.exists():
            return p
    return None


def find_mapa_atu_metro(fuentes: Path, servicio_slug: str) -> Path | None:
    csv_p = Path(fuentes) / "mapas_metropolitano_servicios_atu.csv"
    if not csv_p.exists():
        return None
    df = pd.read_csv(csv_p)
    df = df[df["servicio_slug"].astype(str) == str(servicio_slug)]
    df = df[df["ok"].astype(str).str.lower().isin(["true", "1"]) & df["archivo_local"].notna()]
    prefer = df[df["tipo"] == "mapa_ruta"]
    use = prefer if len(prefer) else df
    for _, r in use.iterrows():
        p = Path(fuentes) / str(r["archivo_local"])
        if p.exists():
            return p
    return None


def servicios_por_estacion(fuentes: Path) -> dict[str, str]:
    """unidad/estacion -> texto 'Servicios: A | B' para tooltips."""
    p = Path(fuentes) / "estaciones_por_servicio_atu.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    out = {}
    for est, g in df.groupby("estacion"):
        slugs = sorted(g["servicio_slug"].astype(str).unique())
        out[str(est)] = "Servicios: " + " | ".join(slugs)
    return out


def list_rutas_corredor(fuentes: Path) -> dict[str, list[str]]:
    from download_transport_pages import RUTAS_CORREDOR
    return {k: list(v) for k, v in RUTAS_CORREDOR.items()}


def list_servicios_metro(fuentes: Path) -> list[str]:
    p = Path(fuentes) / "estaciones_por_servicio_atu.csv"
    if p.exists():
        df = pd.read_csv(p)
        return sorted(df["servicio_slug"].astype(str).unique())
    p2 = Path(fuentes) / "mapas_metropolitano_servicios_atu.csv"
    if p2.exists():
        df = pd.read_csv(p2)
        return sorted(df["servicio_slug"].astype(str).unique())
    return ["RegularA", "RegularB", "RegularC"]
