'use client';

import { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { Skeleton } from './Spinner';
import { getIndiceEstacion, IndiceAcceso } from '@/lib/eje2';
import { Station } from '@/lib/types';
import { systemInfo } from '@/lib/systems';

const CONF: Record<IndiceAcceso['confianza'], string> = { alta: 'Confianza alta', media: 'Confianza media', baja: 'Confianza baja' };

// Índice de seguridad del acceso: sobre denuncias REGISTRADAS (hay subregistro), no probabilidad de ser víctima
export default function SeguridadAcceso({ station }: { station: Station }) {
  const [indice, setIndice] = useState<IndiceAcceso | null | undefined>(undefined);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    let vigente = true;
    setIndice(undefined);
    setFallo(false);
    getIndiceEstacion(station)
      .then((r) => vigente && setIndice(r))
      .catch(() => vigente && (setFallo(true), setIndice(null)));
    return () => { vigente = false; };
  }, [station.id, station.system]);

  if (indice === undefined) return <Skeleton className="h-20 w-full" />;
  if (fallo) return <p className="text-xs text-muted">No se pudo cargar el índice de seguridad.</p>;
  if (!indice) return <p className="text-xs text-muted">Sin índice de seguridad para este punto (fuera de la zona con cobertura).</p>;

  const [lo, hi] = indice.intervalo_pct;
  const tipo = systemInfo(station.system).label.toLowerCase();
  const alimentador = station.system === 'alimentadores';

  return (
    <section aria-label="Índice de seguridad" className="rounded-xl border border-line bg-surface-2/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow flex items-center gap-1.5"><ShieldCheck size={14} /> Seguridad de la zona</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-fg">{Math.round(indice.seguridad_pct)} %</p>
          <p className="text-xs text-muted">Rango {Math.round(lo)}–{Math.round(hi)} % · promedio de {tipo}: {Math.round(indice.base_tipo_pct)} %</p>
        </div>
        <span className="shrink-0 rounded-full bg-surface px-2.5 py-1 text-xs font-semibold text-muted ring-1 ring-line">{CONF[indice.confianza]}</span>
      </div>
      <div className="relative mt-3 h-1.5 w-full rounded-full bg-line" role="img" aria-label={`Seguridad ${Math.round(indice.seguridad_pct)} por ciento, rango ${Math.round(lo)} a ${Math.round(hi)}`}>
        <div className="absolute inset-y-0 rounded-full bg-brand/30" style={{ left: `${lo}%`, width: `${Math.max(hi - lo, 1)}%` }} />
        <div className="absolute -top-0.5 h-2.5 w-1 rounded bg-brand" style={{ left: `calc(${indice.seguridad_pct}% - 2px)` }} />
        <div className="absolute -top-1 h-3.5 w-px bg-fg/50" style={{ left: `${indice.base_tipo_pct}%` }} title="Promedio del tipo de acceso" />
      </div>
      {alimentador && <p className="mt-3 text-xs text-muted">En alimentadores el índice suele ser alto en parte porque se registran menos denuncias; no significa que sean más seguros.</p>}
      {indice.coordenada_aproximada && <p className="mt-1 text-xs text-muted">Ubicación aproximada del paradero.</p>}
      <p className="mt-2 text-xs text-muted">Basado en denuncias registradas. No es la probabilidad de ser víctima.</p>
    </section>
  );
}
