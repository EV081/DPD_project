'use client';

import { useEffect, useRef, useState } from 'react';
import type * as LType from 'leaflet';
import { Station } from '@/lib/types';
import { Coords } from '@/lib/geolocation';
import { systemInfo } from '@/lib/systems';
import { useTheme } from '@/context/ThemeContext';

interface Destination { lat: number; lon: number; name: string }
interface Caminata { normal: any; segura: any | null; seleccionada: 'normal' | 'segura' }

interface Props {
  center: Coords;
  stations: Station[];
  /** Si viene, solo se dibujan estas estaciones (subida y bajada del viaje). */
  filterIds: string[] | null;
  /** Dibuja todos los paraderos visibles (apagado por defecto: solo se muestran los del viaje o el enfocado). */
  showAll: boolean;
  /** Centra el mapa en este punto (p. ej. un paradero elegido desde su detalle). */
  focus: Coords | null;
  routeGeoJson: any | null;
  destination: Destination | null;
  /** Ruta a pie hasta el paradero: la elegida va continua y la otra punteada. */
  walk: Caminata | null;
  onStationClick: (station: Station) => void;
}

// Lienzos grises de Esri (sin clave), sobrios como los de Uber/inDrive: base + etiquetas, en claro y oscuro.
// (Los mosaicos de CARTO ya piden clave de API.) Nota: Esri sirve {z}/{y}/{x}; su nivel nativo máximo es 16.
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas';
// Lienzos grises de Esri en ambos temas, estilo Uber. Ojo: dibujan pocas calles menores, así que una ruta puede
// parecer ir por una manzana aunque siga una calle de OSM (el grafo de rutas sale de OSM).
const TILES = {
  light: { base: `${ESRI}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`, labels: `${ESRI}/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}` as string | null, nativo: 16 },
  dark: { base: `${ESRI}/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`, labels: `${ESRI}/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}` as string | null, nativo: 16 },
};
const ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · Esri, HERE, Garmin';

// Trazo con borde blanco (o casi negro en oscuro) para que la ruta resalte sobre las calles
// Simplifica el trazo según el zoom (px de pantalla): quita zigzags de pocos metros (plazas, cruces) sin alejar la línea de la calle
const SUAVIZADO = 5;
const CASING_LIGHT = '#ffffff';
const CASING_DARK = '#0a101c';

const dot = (color: string, size: number) =>
  `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:2.5px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`;

const userDot = `<div style="position:relative;width:18px;height:18px">
  <span class="user-pulse" style="position:absolute;inset:0;border-radius:50%;background:#2563eb"></span>
  <span style="position:absolute;inset:0;border-radius:50%;background:#2563eb;border:3px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,.45)"></span>
</div>`;

export default function LeafletMap({ center, stations, filterIds, showAll, focus, routeGeoJson, destination, walk, onStationClick }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const L = useRef<typeof LType | null>(null);
  const map = useRef<LType.Map | null>(null);
  const markers = useRef<LType.LayerGroup | null>(null);
  const routeLayer = useRef<LType.LayerGroup | null>(null);
  const tiles = useRef<{ base: LType.TileLayer; labels: LType.TileLayer } | null>(null);
  const { resolved } = useTheme();
  const casing = resolved === 'dark' ? CASING_DARK : CASING_LIGHT;
  const walkLayer = useRef<LType.LayerGroup | null>(null);
  const destMarker = useRef<LType.Marker | null>(null);
  const userMarker = useRef<LType.Marker | null>(null);
  const render = useRef<() => void>(() => {});
  const [ready, setReady] = useState(false);
  const hadDestination = useRef(false);
  const walkFit = useRef(false);

  // El callback y los datos vigentes se leen vía ref para no reconstruir el mapa
  const latest = useRef({ stations, filterIds, showAll, onStationClick });
  latest.current = { stations, filterIds, showAll, onStationClick };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const leaflet = (await import('leaflet')).default;
      if (cancelled || !el.current || map.current) return;
      L.current = leaflet;

      const m = leaflet.map(el.current, { zoomControl: false }).setView([center.lat, center.lon], 15);
      map.current = m;
      leaflet.control.zoom({ position: 'topright' }).addTo(m);
      const t = TILES[document.documentElement.classList.contains('dark') ? 'dark' : 'light'];
      // Esri solo tiene detalle hasta el zoom 16: se amplía hasta 18 y las etiquetas se ocultan desde el 18 (si no, salen gigantes y borrosas)
      const opts = { maxZoom: 17 };
      // Etiquetas sobre los mosaicos pero debajo de las rutas (overlayPane = 400)
      const etiquetas = m.createPane('etiquetas');
      etiquetas.style.zIndex = '250';
      etiquetas.style.pointerEvents = 'none';
      tiles.current = {
        base: leaflet.tileLayer(t.base, { ...opts, maxNativeZoom: t.nativo, className: 'tiles-base', attribution: ATTRIBUTION }).addTo(m),
        labels: leaflet.tileLayer(t.labels ?? '', { ...opts, maxZoom: 16, maxNativeZoom: 16, pane: 'etiquetas' }),
      };
      if (t.labels) tiles.current.labels.addTo(m);

      userMarker.current = leaflet
        .marker([center.lat, center.lon], {
          icon: leaflet.divIcon({ className: 'custom-marker', html: userDot, iconSize: [18, 18] }),
        })
        .addTo(m)
        .bindPopup('Mi ubicación');

      markers.current = leaflet.layerGroup().addTo(m);

      render.current = () => {
        const { stations: all, filterIds: ids, showAll: todos, onStationClick: click } = latest.current;
        markers.current!.clearLayers();
        if (!ids && !todos) return;
        const zoom = m.getZoom();
        const bounds = m.getBounds();
        all.forEach((st) => {
          if (ids && !ids.includes(st.id)) return;
          const pos = leaflet.latLng(st.latitude, st.longitude);
          if (!ids && !bounds.contains(pos)) return;
          if (!ids && zoom < 13 && st.system !== 'metropolitano' && st.system !== 'metro_l1') return;
          const marker = leaflet.marker(pos, {
            icon: leaflet.divIcon({
              className: 'custom-marker',
              html: dot(systemInfo(st.system).color, 14),
              iconSize: [14, 14],
            }),
          });
          marker.bindPopup(`<b>${st.name}</b><br>${systemInfo(st.system).label}`);
          marker.on('click', () => click(st));
          markers.current!.addLayer(marker);
        });
      };
      m.on('moveend zoomend', () => render.current());
      render.current();
      // El contenedor puede haber cambiado de tamaño al montarse (layout responsive)
      setTimeout(() => m.invalidateSize(), 0);
      setReady(true);
    })();

    return () => {
      cancelled = true;
      map.current?.remove();
      map.current = null;
      setReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cambia de mosaicos al alternar claro/oscuro
  useEffect(() => {
    const t = tiles.current, m = map.current;
    if (!t || !m) return;
    const cfg = TILES[resolved];
    t.base.options.maxNativeZoom = cfg.nativo;
    t.base.setUrl(cfg.base);
    if (cfg.labels) { t.labels.setUrl(cfg.labels); if (!m.hasLayer(t.labels)) t.labels.addTo(m); }
    else m.removeLayer(t.labels);
  }, [resolved, ready]);

  // Se adapta si cambia el tamaño de la ventana o del panel contenedor
  useEffect(() => {
    if (!el.current) return;
    const ro = new ResizeObserver(() => map.current?.invalidateSize());
    ro.observe(el.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    userMarker.current?.setLatLng([center.lat, center.lon]);
  }, [center, ready]);

  useEffect(() => { render.current(); }, [stations, filterIds, showAll, ready]);

  useEffect(() => {
    if (focus) map.current?.setView([focus.lat, focus.lon], 16);
  }, [focus, ready]);

  useEffect(() => {
    const leaflet = L.current;
    const m = map.current;
    if (!leaflet || !m) return;
    if (routeLayer.current) { m.removeLayer(routeLayer.current); routeLayer.current = null; }
    if (routeGeoJson) {
      const g = leaflet.layerGroup();
      // Los tramos a pie (punteados) no llevan borde: se verían como una banda sólida
      leaflet.geoJSON(routeGeoJson, { filter: (f) => !f.properties?.punteada, style: () => ({ color: casing, weight: 10, opacity: 1, lineCap: 'round', lineJoin: 'round', smoothFactor: SUAVIZADO }) }).addTo(g);
      leaflet.geoJSON(routeGeoJson, {
        style: (f) => f?.properties?.punteada
          ? { color: f.properties.color_hex, weight: 4, opacity: 0.9, dashArray: '2 8', lineCap: 'round', lineJoin: 'round' }
          : { color: f?.properties?.color_hex || '#2563eb', weight: 6, opacity: 1, lineCap: 'round', lineJoin: 'round', smoothFactor: SUAVIZADO },
      }).addTo(g);
      routeLayer.current = g.addTo(m);
    }
  }, [routeGeoJson, ready, casing]);

  useEffect(() => {
    const leaflet = L.current;
    const m = map.current;
    if (!leaflet || !m) return;
    if (walkLayer.current) { m.removeLayer(walkLayer.current); walkLayer.current = null; }
    if (!walk) return;
    const grupo = leaflet.layerGroup();
    const dibujar = (geo: any, activa: boolean, tipo: 'normal' | 'segura') => {
      if (!geo) return null;
      return leaflet.geoJSON(geo, {
        style: () => ({
          color: tipo === 'segura' ? '#16a34a' : '#2563eb',
          weight: activa ? 6 : 4,
          opacity: activa ? 1 : 0.6,
          dashArray: activa ? undefined : '6 8',
          lineCap: 'round', lineJoin: 'round', smoothFactor: SUAVIZADO,
        }),
      });
    };
    const otra = walk.seleccionada === 'segura' ? 'normal' : 'segura';
    dibujar(walk[otra], false, otra)?.addTo(grupo);
    // Borde blanco bajo la ruta elegida
    if (walk[walk.seleccionada]) {
      leaflet.geoJSON(walk[walk.seleccionada], { style: () => ({ color: casing, weight: 11, opacity: 1, lineCap: 'round', lineJoin: 'round', smoothFactor: SUAVIZADO }) }).addTo(grupo);
    }
    const activa = dibujar(walk[walk.seleccionada], true, walk.seleccionada);
    activa?.addTo(grupo);
    grupo.addTo(m);
    walkLayer.current = grupo;
    // Encuadra la caminata solo cuando aparece (no al alternar entre normal y segura)
    if (activa && !walkFit.current) { m.fitBounds(activa.getBounds(), { padding: [60, 60], maxZoom: 17 }); }
    walkFit.current = true;
  }, [walk, ready, casing]);

  useEffect(() => { if (!walk) walkFit.current = false; }, [walk]);

  useEffect(() => {
    const leaflet = L.current;
    const m = map.current;
    if (!leaflet || !m) return;
    if (destMarker.current) { m.removeLayer(destMarker.current); destMarker.current = null; }
    if (destination) {
      destMarker.current = leaflet
        .marker([destination.lat, destination.lon], {
          icon: leaflet.divIcon({
            className: 'custom-marker',
            html: '<div style="background:#dc2626;width:22px;height:22px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.45)"></div>',
            iconSize: [22, 22],
            iconAnchor: [11, 26],
          }),
        })
        .addTo(m)
        .bindPopup(`<b>Destino:</b><br>${destination.name}`);
      const pts: LType.LatLngExpression[] = [[center.lat, center.lon], [destination.lat, destination.lon]];
      latest.current.stations.forEach((s) => {
        if (latest.current.filterIds?.includes(s.id)) pts.push([s.latitude, s.longitude]);
      });
      m.fitBounds(leaflet.latLngBounds(pts), { padding: [50, 50] });
      hadDestination.current = true;
    } else if (hadDestination.current) {
      // Se cerró el viaje: volver a mi ubicación (no al montar, para no pisar un paradero enfocado)
      hadDestination.current = false;
      m.setView([center.lat, center.lon], 15);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [destination, ready]);

  return <div ref={el} className="h-full w-full" />;
}
