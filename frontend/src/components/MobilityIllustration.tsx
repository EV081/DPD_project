'use client';

import { useState } from 'react';
import { ArrowUpRight, MapPin } from 'lucide-react';

// La ilustración acompaña la presentación; nunca reemplaza al mapa ni a sus datos.
export default function MobilityIllustration({ className = '' }: { className?: string }) {
  const [disponible, setDisponible] = useState(true);
  return (
    <figure className={`mobility-illustration ${className}`}>
      {disponible ? (
        <img src="/imagenes/movilidad-lima.webp" alt="Ilustración de movilidad urbana en Lima" onError={() => setDisponible(false)} />
      ) : (
        <div className="mobility-illustration-fallback" aria-hidden="true">
          <MapPin size={36} strokeWidth={1.5} />
          <span>Lima<br />se mueve.</span>
          <ArrowUpRight size={66} strokeWidth={1} />
        </div>
      )}
      <figcaption>Ilustración conceptual · no representa una ruta real</figcaption>
    </figure>
  );
}
