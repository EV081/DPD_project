'use client';

import { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';

interface MiniMapProps {
  latitude: number;
  longitude: number;
  stationName: string;
  systemColor?: string;
}

export default function MiniMap({
  latitude,
  longitude,
  stationName,
  systemColor = '#2563eb',
}: MiniMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    import('leaflet').then((L) => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
      }

      const map = L.map(mapRef.current!, {
        center: [latitude, longitude],
        zoom: 15,
        zoomControl: false,
        attributionControl: false,
        scrollWheelZoom: false,
        dragging: true,
      });

      // Usamos OpenStreetMap estándar para evitar restricciones de API Key
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
      }).addTo(map);

      // Icono de puntito con el color del sistema
      const customIcon = L.divIcon({
        className: 'custom-station-pin',
        html: `<div style="background-color: ${systemColor}; width: 18px; height: 18px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.35);"></div>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });

      L.marker([latitude, longitude], { icon: customIcon })
        .addTo(map)
        .bindPopup(`<b>${stationName}</b>`);

      mapInstanceRef.current = map;
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [latitude, longitude, stationName, systemColor]);

  return <div ref={mapRef} className="h-48 w-full z-0" />;
}