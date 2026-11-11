'use client';

import { useEffect, useMemo } from 'react';
import { divIcon } from 'leaflet';
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';

interface MiniMapProps { latitude: number; longitude: number; stationName: string; systemColor?: string }
function Position({ latitude, longitude }: Pick<MiniMapProps, 'latitude' | 'longitude'>) {
  const map = useMap();
  useEffect(() => { map.setView([latitude, longitude], 15); }, [map, latitude, longitude]);
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}
export default function MiniMap({ latitude, longitude, stationName, systemColor = '#2563eb' }: MiniMapProps) {
  const icon = useMemo(() => divIcon({ className: 'custom-marker', iconSize: [18, 18], iconAnchor: [9, 9],
    html: `<span class="us-station-dot" style="background:${systemColor}"></span>` }), [systemColor]);
  return <MapContainer center={[latitude, longitude]} zoom={15} zoomControl={false} scrollWheelZoom={false} className="h-48 w-full z-0">
    <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19}
      attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' />
    <Position latitude={latitude} longitude={longitude} />
    <Marker position={[latitude, longitude]} icon={icon} title={stationName}><Popup><strong>{stationName}</strong></Popup></Marker>
  </MapContainer>;
}
