'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Search, X, SearchX } from 'lucide-react';
import StationCard from '@/components/StationCard';
import { Spinner, EmptyState } from '@/components/Spinner';
import { getStations } from '@/lib/services';
import { SYSTEMS } from '@/lib/systems';
import { Station } from '@/lib/types';

const FILTERS = [{ id: undefined, label: 'Todos' }, ...Object.values(SYSTEMS).map((s) => ({ id: s.id as string | undefined, label: s.label }))];

function SearchContent() {
  const params = useSearchParams();
  const [query, setQuery] = useState('');
  const [stations, setStations] = useState<Station[]>([]);
  const [loading, setLoading] = useState(false);
  const [system, setSystem] = useState<string | undefined>(params.get('system') || undefined);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const first = useRef(true);
  const [visible, setVisible] = useState(60);   // evita pintar miles de tarjetas de una vez

  const fetchStations = async (text: string, filter?: string) => {
    setLoading(true);
    try {
      setStations(await getStations(filter, text));
      setVisible(60);
    } catch (error) {
      console.error('Error al buscar estaciones:', error);
    } finally {
      setLoading(false);
    }
  };

  // Búsqueda inmediata al cambiar de sistema; con debounce al escribir
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const delay = first.current ? 0 : 350;
    first.current = false;
    timer.current = setTimeout(() => fetchStations(query, system), delay);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [query, system]);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8 md:py-10">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-fg">Paraderos y estaciones</h1>
        <p className="mt-1 text-sm text-muted">Busca por nombre o avenida y consulta el aforo previsto.</p>
      </header>

      <div className="relative mt-6">
        <Search size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ej: Naranjal, Angamos, Plaza Butters…"
          aria-label="Buscar paradero"
          className="input !pl-11 !pr-10 !py-3"
        />
        {query && (
          <button onClick={() => setQuery('')} aria-label="Limpiar" className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted hover:bg-surface-2 hover:text-fg">
            <X size={16} />
          </button>
        )}
      </div>

      <div className="scroll-thin -mx-1 mt-4 flex gap-2 overflow-x-auto px-1 pb-1" role="group" aria-label="Filtrar por sistema">
        {FILTERS.map((f) => (
          <button key={f.label} className="chip" data-active={system === f.id} aria-pressed={system === f.id} onClick={() => setSystem(f.id)}>
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-6" aria-live="polite">
        {loading ? (
          <div className="flex items-center justify-center gap-2.5 py-20 text-sm text-muted"><Spinner size={18} /> Buscando paraderos…</div>
        ) : stations.length === 0 ? (
          <EmptyState icon={SearchX} title="Sin resultados" text="No encontramos paraderos que coincidan. Prueba con otro nombre o avenida." />
        ) : (
          <>
            <p className="mb-3 text-sm text-muted">{stations.length} resultado{stations.length === 1 ? '' : 's'}</p>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {stations.slice(0, visible).map((s, i) => <StationCard key={`${s.id}-${i}`} station={s} />)}
            </div>
            {visible < stations.length && (
              <div className="mt-6 text-center">
                <button className="btn btn-secondary" onClick={() => setVisible((v) => v + 60)}>Mostrar más</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return <Suspense><SearchContent /></Suspense>;
}
