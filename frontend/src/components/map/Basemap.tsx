'use client';

import { useEffect, useState } from 'react';
import { TileLayer, useMap } from 'react-leaflet';
import { setWorkerUrl } from 'maplibre-gl';
import { useTheme } from '@/context/ThemeContext';

// MapLibre 6 separa el worker: el bundler publica este recurso con hash y sirve la URL local.
setWorkerUrl(new URL('maplibre-gl/dist/maplibre-gl-worker.mjs', import.meta.url).href);

/** Un solo motor de interacción (Leaflet); MapLibre dibuja únicamente el fondo vectorial. */
export default function Basemap() {
  const map = useMap();
  const { resolved } = useTheme();
  const [fallback, setFallback] = useState(false);
  const [vectorReady, setVectorReady] = useState(false);
  useEffect(() => {
    let disposed = false;
    let layer: import('leaflet').Layer | undefined;
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let gl: import('maplibre-gl').Map | undefined;
    let loaded = false;
    setFallback(false);
    setVectorReady(false);
    const fail = (error?: unknown) => {
      if (disposed || loaded) return;
      if (error) console.warn('No se pudo cargar el mapa vectorial; se usa OpenStreetMap.', error);
      setFallback(true);
      if (layer && map.hasLayer(layer)) map.removeLayer(layer);
    };
    void import('@maplibre/maplibre-gl-leaflet').then(({ maplibreGL }) => {
      if (disposed) return;
      try {
        const vector = maplibreGL({
          style: `https://tiles.openfreemap.org/styles/${resolved === 'dark' ? 'dark' : 'positron'}`,
          attributionControl: false,
        });
        layer = vector;
        vector.addTo(map);
        vector.getContainer().style.zIndex = '2';
        gl = vector.getMaplibreMap();
        gl.once('load', () => { if (!disposed) { loaded = true; setVectorReady(true); clearTimeout(timeout); } });
        gl.on('error', fail);
        timeout = setTimeout(fail, 12000);
      } catch (error) { fail(error); }
    }).catch(fail);
    return () => {
      disposed = true;
      clearTimeout(timeout);
      gl?.off('error', fail);
      if (layer && map.hasLayer(layer)) map.removeLayer(layer);
    };
  }, [map, resolved]);

  useEffect(() => {
    const attribution = '© <a href="https://openfreemap.org">OpenFreeMap</a> · <a href="https://www.openmaptiles.org/">OpenMapTiles</a> · © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
    if (!fallback) map.attributionControl.addAttribution(attribution);
    return () => { map.attributionControl.removeAttribution(attribution); };
  }, [map, fallback]);

  return fallback || !vectorReady ? <TileLayer attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19} /> : null;
}
