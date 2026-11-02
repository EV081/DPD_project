'use client';

import { useEffect, useRef, useState } from 'react';
import { Footprints, Phone, ShieldCheck } from 'lucide-react';
import Alert from './Alert';
import { Skeleton } from './Spinner';
import { Coords } from '@/lib/geolocation';
import { errorMessage } from '@/lib/client';
import {
  claseBanda, etiquetaBanda, getRutaPeatonal, NUMERO_EMERGENCIA, RespuestaRuta, RutaPeatonal,
} from '@/lib/eje2';
import { Station } from '@/lib/types';

export interface CaminataMapa { normal: any; segura: any | null; seleccionada: 'normal' | 'segura' }

interface Props {
  station: Station;
  origen: Coords;
  origenReal: boolean;
  /** Carga la ruta sin esperar el clic (en el planificador, la caminata ya es parte del viaje). */
  auto?: boolean;
  onChange: (caminata: CaminataMapa | null) => void;
}

const AVISO = 'Basado en denuncias registradas. No es la probabilidad de ser víctima. En una emergencia llama al 105.';
const NOMBRE = { normal: 'Más corta', segura: 'Más segura' } as const;

// Cómo llegar caminando al paradero: ruta más corta vs. más segura, con la explicación del backend
export default function RutaSegura({ station, origen, origenReal, auto = false, onChange }: Props) {
  const [res, setRes] = useState<RespuestaRuta | null>(null);
  const [sel, setSel] = useState<'normal' | 'segura'>('segura');
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pedido = useRef(0);   // descarta respuestas de un paradero anterior

  const cargar = async () => {
    const n = ++pedido.current;
    setCargando(true);
    setError(null);
    try {
      const r = await getRutaPeatonal(origen, station);
      if (n !== pedido.current) return;
      const inicial = 'segura';   // la segura siempre va por defecto, aunque sea más larga: la persona elige
      setRes(r);
      setSel(inicial);
      onChange({ normal: r.rutas.normal.geojson, segura: r.recomendada === 'misma' ? null : r.rutas.segura.geojson, seleccionada: inicial });
    } catch (e: any) {
      if (n !== pedido.current) return;
      setRes(null);
      onChange(null);
      setError(errorMessage(e, 'No se pudo calcular la ruta a pie.'));
    } finally {
      if (n === pedido.current) setCargando(false);
    }
  };

  // Otro paradero: se descarta lo anterior (y se vuelve a pedir si es automático)
  useEffect(() => {
    pedido.current++;
    setRes(null);
    setError(null);
    onChange(null);
    if (auto && origenReal) cargar();
    return () => { pedido.current++; onChange(null); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [station.id, station.system, auto, origenReal]);

  const elegir = (s: 'normal' | 'segura') => {
    if (!res) return;
    setSel(s);
    onChange({ normal: res.rutas.normal.geojson, segura: res.recomendada === 'misma' ? null : res.rutas.segura.geojson, seleccionada: s });
  };

  if (!res && !cargando && !error) {
    return (
      <div>
        <button type="button" onClick={cargar} disabled={!origenReal} className="btn btn-secondary w-full">
          <Footprints size={18} /> Ver ruta a pie segura
        </button>
        {!origenReal && <p className="mt-2 text-xs text-muted">Activa tu ubicación para calcular el camino hasta este paradero.</p>}
      </div>
    );
  }
  if (cargando) return <div className="space-y-2"><Skeleton className="h-10 w-full" /><Skeleton className="h-24 w-full" /></div>;
  if (error || !res) {
    return (
      <div className="space-y-2">
        <Alert tono="warn">{error}</Alert>
        <button type="button" onClick={cargar} className="btn btn-secondary w-full">Reintentar</button>
      </div>
    );
  }

  const misma = res.recomendada === 'misma';
  const r: RutaPeatonal = res.rutas[misma ? 'normal' : sel];
  const ex = res.explicacion;
  const desvios = r.tramos.filter((t) => t.desvio);

  return (
    <section aria-label="Ruta a pie" className="space-y-3">
      {!misma && (
        <div role="radiogroup" aria-label="Tipo de ruta" className="grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
          {(['segura', 'normal'] as const).map((k) => (
            <button key={k} type="button" role="radio" aria-checked={sel === k} onClick={() => elegir(k)}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${sel === k ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg'}`}>
              {k === 'segura' && <ShieldCheck size={14} className="mr-1 inline -mt-0.5" />}
              {NOMBRE[k]}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4 rounded-xl border border-line p-3.5">
        <div>
          <p className="text-xl font-bold tabular-nums text-fg">{Math.round(r.minutos)} min</p>
          <p className="text-xs text-muted">{Math.round(r.distancia_m)} m a pie</p>
        </div>
        <span className={`ml-auto rounded-full px-2.5 py-1 text-xs font-semibold ${claseBanda(r.banda_riesgo)}`}>{etiquetaBanda(r.banda_riesgo)}</span>
      </div>

      <p className="text-sm text-fg">{ex.resumen}</p>

      {!misma && sel === 'segura' && ex.motivos.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted">{ex.motivos.map((m, i) => <li key={i}>{m}</li>)}</ul>
      )}
      {!misma && sel === 'segura' && ex.tramos_evitados.length > 0 && (
        <p className="text-sm text-muted">Evita: {ex.tramos_evitados.map((t) => `${t.nombre} (${t.largo_m} m)`).join(', ')}.</p>
      )}

      <details className="text-sm">
        <summary className="cursor-pointer font-medium text-fg">Calles del recorrido{desvios.length ? ` · ${desvios.length} del desvío` : ''}</summary>
        <ol className="mt-2 space-y-1.5">
          {r.tramos.map((t, i) => (
            <li key={i} className="flex items-center justify-between gap-2">
              <span className="min-w-0 truncate text-fg">{t.nombre}{t.desvio && <span className="ml-1.5 text-xs font-semibold text-brand">desvío</span>}</span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-xs tabular-nums text-muted">{t.largo_m} m</span>
                <span className={`rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold ${claseBanda(t.riesgo)}`}>{etiquetaBanda(t.riesgo)}</span>
              </span>
            </li>
          ))}
        </ol>
      </details>

      <Alert tono="info">{AVISO}</Alert>
      {ex.llamar_105 && (
        <a href={`tel:${NUMERO_EMERGENCIA}`} className="btn btn-danger w-full"><Phone size={16} /> Emergencia: llamar al {NUMERO_EMERGENCIA}</a>
      )}
    </section>
  );
}
