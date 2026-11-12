'use client';

import { useEffect, useState } from 'react';
import { TileLayer, useMap } from 'react-leaflet';
import { setWorkerUrl, type StyleSpecification } from 'maplibre-gl';
import { useTheme } from '@/context/ThemeContext';
import { mobilityStyle } from '@/lib/map-style';

setWorkerUrl(new URL('maplibre-gl/dist/maplibre-gl-worker.mjs', import.meta.url).href);
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas';

export default function Basemap() {
  const map = useMap();
  const { resolved } = useTheme();
  const [vectorReady, setVectorReady] = useState(false);
  useEffect(() => {
    let disposed = false;
    let failed = false;
    let layer: import('leaflet').Layer | undefined;
    let gl: import('maplibre-gl').Map | undefined;
    const controller = new AbortController();
    setVectorReady(false);
    const fail = () => {
      if (disposed || failed) return;
      failed = true;
      controller.abort();
      clearTimeout(timeout);
      setVectorReady(false);
      if (layer && map.hasLayer(layer)) map.removeLayer(layer);
    };
    const timeout = setTimeout(fail, 15000);
    void Promise.all([
      import('@maplibre/maplibre-gl-leaflet'),
      fetch('https://tiles.openfreemap.org/styles/positron', { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error('No se pudo cargar el estilo cartográfico');
        return response.json() as Promise<StyleSpecification>;
      }),
    ]).then(([{ maplibreGL }, style]) => {
      if (disposed || failed) return;
      try {
        const vector = maplibreGL({ style: mobilityStyle(style, resolved === 'dark'), attributionControl: false });
        layer = vector;
        vector.addTo(map);
        vector.getContainer().style.zIndex = '3';
        gl = vector.getMaplibreMap();
        gl.once('load', () => {
          if (!disposed && !failed) { setVectorReady(true); clearTimeout(timeout); }
        });
        // Un error posterior de un mosaico no sustituye todo el mapa ya cargado.
        gl.on('error', () => { if (!gl?.isStyleLoaded()) fail(); });
      } catch { fail(); }
    }).catch(fail);
    return () => {
      disposed = true;
      controller.abort();
      clearTimeout(timeout);
      if (layer && map.hasLayer(layer)) map.removeLayer(layer);
    };
  }, [map, resolved]);

  useEffect(() => {
    if (!vectorReady) return;
    const attribution = '© <a href="https://openfreemap.org">OpenFreeMap</a> · <a href="https://www.openmaptiles.org/">OpenMapTiles</a> · © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
    map.attributionControl.addAttribution(attribution);
    return () => { map.attributionControl.removeAttribution(attribution); };
  }, [map, vectorReady]);

  // El respaldo también es gris y sigue el tema: nunca vuelve al mapa multicolor.
  const canvas = resolved === 'dark' ? 'Dark' : 'Light';
  return !vectorReady ? <>
    <TileLayer key={`base-${canvas}`} url={`${ESRI}/World_${canvas}_Gray_Base/MapServer/tile/{z}/{y}/{x}`}
      maxZoom={19} maxNativeZoom={16} zIndex={1} attribution='Tiles © Esri · Esri, HERE, Garmin, OpenStreetMap contributors' />
    <TileLayer key={`labels-${canvas}`} url={`${ESRI}/World_${canvas}_Gray_Reference/MapServer/tile/{z}/{y}/{x}`}
      maxZoom={19} maxNativeZoom={16} zIndex={2} />
  </> : null;
}
