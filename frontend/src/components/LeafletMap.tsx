'use client';

import { useEffect, useRef, useState } from 'react';
import type * as LType from 'leaflet';
import { Station } from '@/lib/types';
import { Coords } from '@/lib/geolocation';
import { systemInfo } from '@/lib/systems';

interface Destination { lat: number; lon: number; name: string }

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
  onStationClick: (station: Station) => void;
}

// Teselas de OpenStreetMap (sin clave). El modo oscuro se logra con un filtro CSS (globals.css)
const TILES_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

const dot = (color: string, size: number) =>
  `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:2.5px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`;

const userDot = `<div style="position:relative;width:18px;height:18px">
  <span class="user-pulse" style="position:absolute;inset:0;border-radius:50%;background:#2563eb"></span>
  <span style="position:absolute;inset:0;border-radius:50%;background:#2563eb;border:3px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,.45)"></span>
</div>`;

export default function LeafletMap({ center, stations, filterIds, showAll, focus, routeGeoJson, destination, onStationClick }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const L = useRef<typeof LType | null>(null);
  const map = useRef<LType.Map | null>(null);
  const markers = useRef<LType.LayerGroup | null>(null);
  const routeLayer = useRef<LType.GeoJSON | null>(null);
  const destMarker = useRef<LType.Marker | null>(null);
  const userMarker = useRef<LType.Marker | null>(null);
  const render = useRef<() => void>(() => {});
  const [ready, setReady] = useState(false);
  const hadDestination = useRef(false);

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
      leaflet.tileLayer(TILES_URL, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(m);

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
      routeLayer.current = leaflet.geoJSON(routeGeoJson, {
        style: (f) => ({ color: f?.properties?.color_hex || '#2563eb', weight: 5, opacity: 0.9, lineCap: 'round', lineJoin: 'round' }),
      }).addTo(m);
    }
  }, [routeGeoJson, ready]);

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
