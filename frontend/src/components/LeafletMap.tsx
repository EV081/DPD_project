'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { divIcon, geoJSON, latLngBounds, Polyline, type PolylineOptions, type Layer } from 'leaflet';
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
  userLocation?: Coords; center: Coords; centerIsReference: boolean; stations: Station[]; filterIds: string[] | null;
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
    icon={filterIds ? divIcon({ className: 'custom-marker', iconSize: [30, 30], iconAnchor: [15, 15], html: `<span class="us-trip-stop" style="border-color:${systemInfo(s.system).color}">${filterIds.indexOf(s.id) + 1}</span>` }) : icons.get(s.system)!} zIndexOffset={filterIds ? 1000 : 0} title={s.name} alt={s.name}>
    <Popup><div className="us-map-popup">
      <span className="eyebrow">{systemInfo(s.system).label}</span>
      <strong>{s.name}</strong><p>{s.avenida || 'Paradero de transporte público'}</p>
      <button type="button" className="btn btn-primary" onClick={() => onStationClick(s)}>Consultar aforo →</button>
    </div></Popup>
  </Marker>);
}

function Viewport({ center, focus, destination, stations, filterIds, walk, routeGeoJson }: Props) {
  const map = useMap();
  const previousDestination = useRef(false);
  const walkFit = useRef(false);
  const latest = useRef({ center, destination, stations, filterIds, walk, routeGeoJson });
  latest.current = { center, destination, stations, filterIds, walk, routeGeoJson };

  const fit = useMemo(() => () => {
    const current = latest.current;
    const activeWalk = current.walk?.[current.walk.seleccionada];
    const geometry = activeWalk || current.routeGeoJson;
    const bounds = geometry ? geoJSON(geometry).getBounds() : latLngBounds([]);
    bounds.extend([current.center.lat, current.center.lon]);
    if (current.destination) bounds.extend([current.destination.lat, current.destination.lon]);
    current.stations.filter((s) => current.filterIds?.includes(s.id)).forEach((s) => bounds.extend([s.latitude, s.longitude]));
    const { x: width, y: height } = map.getSize();
    // Panel lateral en escritorio, hoja inferior en móvil; nunca usar un padding mayor al lienzo.
    const desktop = width >= 900;
    map.fitBounds(bounds, {
      paddingTopLeft: [desktop ? Math.min(460, width * 0.4) : 28, Math.min(110, height * 0.15)],
      paddingBottomRight: [28, desktop ? 40 : Math.min(260, height * 0.38)],
      maxZoom: 17, animate: false,
    });
  }, [map]);

  useEffect(() => {
    let frame = 0;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        map.stop();
        map.invalidateSize({ animate: false, pan: false });
        const current = latest.current;
        if (current.destination || current.walk) fit();
      });
    });
    observer.observe(map.getContainer());
    return () => { observer.disconnect(); cancelAnimationFrame(frame); };
  }, [map, fit]);
  useEffect(() => { if (focus) map.setView([focus.lat, focus.lon], 16, { animate: false }); }, [focus, map]);
  useEffect(() => {
    if (destination) { fit(); previousDestination.current = true; }
    else if (previousDestination.current) {
      previousDestination.current = false;
      map.setView([center.lat, center.lon], 15, { animate: false });
    }
  }, [destination?.lat, destination?.lon, center.lat, center.lon, routeGeoJson, filterIds, fit, map]);
  useEffect(() => {
    if (!walk) { walkFit.current = false; return; }
    if (!walkFit.current) { fit(); walkFit.current = true; }
  }, [walk, fit]);
  return null;
}

// El borde y el trazo usan los mismos vértices a cualquier zoom.
function preserveGeometry(_feature: unknown, layer: Layer) {
  if (layer instanceof Polyline) layer.setStyle({ smoothFactor: 0 } as PolylineOptions);
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
        onEachFeature={preserveGeometry} style={{ color: casing, weight: 10 }} />
      <GeoJSON key={`route-${resolved}-${routeKey}`} data={routeGeoJson} onEachFeature={preserveGeometry} style={(f) => ({
        color: f?.properties?.color_hex || '#2563eb', weight: f?.properties?.punteada ? 4 : 6,
        dashArray: f?.properties?.punteada ? '2 8' : undefined,
      })} />
    </>}
    {walk && <>
      {walk[other] && <GeoJSON key={`other-${walkKey}`} data={walk[other]!}
        onEachFeature={preserveGeometry} style={{ color: other === 'segura' ? '#16a34a' : '#2563eb', weight: 4, opacity: 0.6, dashArray: '6 8' }} />}
      {walk[walk.seleccionada] && <>
        <GeoJSON key={`walk-casing-${resolved}-${walkKey}`} data={walk[walk.seleccionada]!} onEachFeature={preserveGeometry} style={{ color: casing, weight: 11 }} />
        <GeoJSON key={`walk-${walkKey}`} data={walk[walk.seleccionada]!}
          onEachFeature={preserveGeometry} style={{ color: walk.seleccionada === 'segura' ? '#16a34a' : '#2563eb', weight: 6 }} />
      </>}
    </>}
  </>;
}
export default function LeafletMap(props: Props) {
  return <MapContainer center={[props.center.lat, props.center.lon]} zoom={15} maxZoom={19} zoomControl={false} zoomAnimation={false} markerZoomAnimation={false} fadeAnimation={false}
    className="h-full w-full" aria-label="Mapa de transporte de Lima">
    <Basemap /><ZoomControl position="topright" /><Viewport {...props} />
    <Routes routeGeoJson={props.routeGeoJson} walk={props.walk} />
    <Stations {...props} />
    <Marker position={[(props.userLocation ?? props.center).lat, (props.userLocation ?? props.center).lon]} icon={userIcon} title={!props.userLocation && props.centerIsReference ? 'Origen de referencia' : 'Mi ubicación'}>
      <Popup>{!props.userLocation && props.centerIsReference ? 'Origen de referencia · centro de Lima' : 'Mi ubicación'}</Popup>
    </Marker>
    {props.destination && <Marker position={[props.destination.lat, props.destination.lon]} icon={destinationIcon} zIndexOffset={1500} title="Destino">
      <Popup><strong>Destino</strong><br />{props.destination.name}</Popup>
    </Marker>}
  </MapContainer>;
}
