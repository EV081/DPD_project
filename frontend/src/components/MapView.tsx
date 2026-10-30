'use client';

import dynamic from 'next/dynamic';

// Leaflet necesita `window`: solo se carga en el navegador
const MapView = dynamic(() => import('./LeafletMap'), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-slate-900" />,
});

export default MapView;
