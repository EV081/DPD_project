'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { divIcon, geoJSON, latLngBounds } from 'leaflet';
import { MapContainer, Marker, Popup, GeoJSON, ZoomControl, useMap, useMapEvents } from 'react-leaflet';
import type { GeoJsonObject } from 'geojson';
import type { Station } from '@/lib/types';
import type { Coords } from '@/lib/geolocation';
import { systemInfo } from '@/lib/systems';
import { useTheme } from '@/context/ThemeContext';
import { visibleStations } from '@/lib/map-stations';
import Basemap from './map/Basemap';

interface Destination { lat: number; lon: number; name: string }
interface Caminata { normal: GeoJsonObject; segura: GeoJsonObject | null; seleccionada: 'normal' | 'segura' }
interface Props {
  center: Coords; centerIsReference: boolean; stations: Station[]; filterIds: string[] | null;
  showAll: boolean; focus: Coords | null; routeGeoJson: GeoJsonObject | null;
  destination: Destination | null; walk: Caminata | null; onStationClick: (station: Station) => void;
}
const userIcon = divIcon({ className: 'custom-marker', iconSize: [20, 20], iconAnchor: [10, 10],
  html: '<span class="us-location-dot"><span class="user-pulse"></span></span>' });
const destinationIcon = divIcon({ className: 'custom-marker', iconSize: [26, 30], iconAnchor: [13, 30],
  html: '<span class="us-destination-pin"></span>' });
const stationIcon = (color: string) => divIcon({ className: 'custom-marker', iconSize: [18, 18], iconAnchor: [9, 9],
  html: `<span class="us-station-dot" style="background:${color}"></span>` });

function Stations({ stations, filterIds, showAll, onStationClick }: Pick<Props, 'stations' | 'filterIds' | 'showAll' | 'onStationClick'>) {
  const [viewport, setViewport] = useState(0);
  const map = useMapEvents({ moveend: () => setViewport((v) => v + 1), zoomend: () => setViewport((v) => v + 1) });
  const visible = useMemo(() => visibleStations(stations, filterIds, showAll, map.getZoom(),
    (lat, lon) => map.getBounds().contains([lat, lon])), [stations, filterIds, showAll, map, viewport]);
  const icons = useMemo(() => new Map(visible.map((s) => [s.system, stationIcon(systemInfo(s.system).color)])), [visible]);
  return visible.map((s, i) => <Marker key={`${s.system}-${s.id}-${i}`} position={[s.latitude, s.longitude]}
    icon={icons.get(s.system)!} title={s.name} alt={s.name}>
    <Popup><div className="us-map-popup">
      <span className="eyebrow">{systemInfo(s.system).label}</span>
      <strong>{s.name}</strong><p>{s.avenida || 'Paradero de transporte público'}</p>
      <button type="button" className="btn btn-primary" onClick={() => onStationClick(s)}>Consultar aforo →</button>
    </div></Popup>
  </Marker>);
}

function Viewport({ center, focus, destination, stations, filterIds, walk }: Props) {
  const map = useMap();
  const previousDestination = useRef(false);
  const walkFit = useRef(false);
  const latest = useRef({ center, stations, filterIds });
  latest.current = { center, stations, filterIds };
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  useEffect(() => { if (focus) map.setView([focus.lat, focus.lon], 16); }, [focus, map]);
  useEffect(() => {
    const { center: origin, stations: all, filterIds: ids } = latest.current;
    if (destination) {
      const points: [number, number][] = [[origin.lat, origin.lon], [destination.lat, destination.lon],
        ...all.filter((s) => ids?.includes(s.id)).map((s): [number, number] => [s.latitude, s.longitude])];
      map.fitBounds(latLngBounds(points), { paddingTopLeft: [32, 100], paddingBottomRight: [32, 240], maxZoom: 17 });
      previousDestination.current = true;
    } else if (previousDestination.current) {
      previousDestination.current = false;
      map.setView([origin.lat, origin.lon], 15);
    }
  }, [destination, map]);
  useEffect(() => {
    if (!walk) { walkFit.current = false; return; }
    const active = walk[walk.seleccionada];
    if (active && !walkFit.current) {
      const bounds = geoJSON(active).getBounds();
      if (bounds.isValid()) map.fitBounds(bounds, { paddingTopLeft: [40, 100], paddingBottomRight: [40, 240], maxZoom: 17 });
      walkFit.current = true;
    }
  }, [walk, map]);
  return null;
}

function Routes({ routeGeoJson, walk }: Pick<Props, 'routeGeoJson' | 'walk'>) {
  const { resolved } = useTheme();
  const casing = resolved === 'dark' ? '#0a101c' : '#ffffff';
  // GeoJSON data/style are immutable in React Leaflet: remount only the layers when geometry or theme changes.
  const routeKey = useMemo(() => JSON.stringify(routeGeoJson), [routeGeoJson]);
  const walkKey = useMemo(() => JSON.stringify(walk), [walk]);
  const other = walk?.seleccionada === 'segura' ? 'normal' : 'segura';
  return <>
    {routeGeoJson && <>
      <GeoJSON key={`casing-${resolved}-${routeKey}`} data={routeGeoJson} filter={(f) => !f.properties?.punteada}
        style={{ color: casing, weight: 10 }} />
      <GeoJSON key={`route-${resolved}-${routeKey}`} data={routeGeoJson} style={(f) => ({
        color: f?.properties?.color_hex || '#2563eb', weight: f?.properties?.punteada ? 4 : 6,
        dashArray: f?.properties?.punteada ? '2 8' : undefined, smoothFactor: 5,
      })} />
    </>}
    {walk && <>
      {walk[other] && <GeoJSON key={`other-${walkKey}`} data={walk[other]!}
        style={{ color: other === 'segura' ? '#16a34a' : '#2563eb', weight: 4, opacity: 0.6, dashArray: '6 8' }} />}
      {walk[walk.seleccionada] && <>
        <GeoJSON key={`walk-casing-${resolved}-${walkKey}`} data={walk[walk.seleccionada]!} style={{ color: casing, weight: 11 }} />
        <GeoJSON key={`walk-${walkKey}`} data={walk[walk.seleccionada]!}
          style={{ color: walk.seleccionada === 'segura' ? '#16a34a' : '#2563eb', weight: 6 }} />
      </>}
    </>}
  </>;
}
export default function LeafletMap(props: Props) {
  return <MapContainer center={[props.center.lat, props.center.lon]} zoom={15} maxZoom={19} zoomControl={false}
    className="h-full w-full" aria-label="Mapa de transporte de Lima">
    <Basemap /><ZoomControl position="topright" /><Viewport {...props} />
    <Routes routeGeoJson={props.routeGeoJson} walk={props.walk} />
    <Stations {...props} />
    <Marker position={[props.center.lat, props.center.lon]} icon={userIcon} title={props.centerIsReference ? 'Origen de referencia' : 'Mi ubicación'}>
      <Popup>{props.centerIsReference ? 'Origen de referencia · centro de Lima' : 'Mi ubicación'}</Popup>
    </Marker>
    {props.destination && <Marker position={[props.destination.lat, props.destination.lon]} icon={destinationIcon} title="Destino">
      <Popup><strong>Destino</strong><br />{props.destination.name}</Popup>
    </Marker>}
  </MapContainer>;
}
