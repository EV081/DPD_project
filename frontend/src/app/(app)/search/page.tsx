'use client';

import { ActionIcon, SegmentedControl, TextInput } from '@mantine/core';
import DataTable, { type DataColumn } from '@/components/DataTable';
import Link from 'next/link';
import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Search, X, SearchX, MapPinned } from 'lucide-react';
import StationCard from '@/components/StationCard';
import { Skeleton, EmptyState } from '@/components/Spinner';
import { getStations } from '@/lib/services';
import { SYSTEMS, systemInfo } from '@/lib/systems';
import { Station } from '@/lib/types';
import Alert from '@/components/Alert';

const FILTERS = [{ id: undefined, label: 'Todos' }, ...Object.values(SYSTEMS).map((s) => ({ id: s.id as string | undefined, label: s.label }))];

const stationColumns: DataColumn<Station>[] = [
  { id: 'name', label: 'Paradero', value: (s) => s.name, render: (s) => <Link className="font-semibold text-brand hover:underline" href={`/station/${encodeURIComponent(s.id)}`}>{s.name}</Link> },
  { id: 'system', label: 'Sistema', value: (s) => systemInfo(s.system).label },
  { id: 'avenida', label: 'Avenida', value: (s) => s.avenida || 'Sin referencia' },
];

function SearchContent() {
  const params = useSearchParams();
  const [view, setView] = useState('cards');
  const [query, setQuery] = useState('');
  const [stations, setStations] = useState<Station[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const pedido = useRef(0);
  const [system, setSystem] = useState<string | undefined>(params.get('system') || undefined);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const first = useRef(true);
  const [visible, setVisible] = useState(60);   // evita pintar miles de tarjetas de una vez

  const fetchStations = async (text: string, filter?: string) => {
    const n = ++pedido.current;   // una respuesta vieja no pisa a la más reciente
    setLoading(true);
    setError(false);
    try {
      const res = await getStations(filter, text);
      if (n !== pedido.current) return;
      setStations(res);
      setVisible(60);
    } catch (e) {
      console.error('Error al buscar estaciones:', e);
      if (n === pedido.current) { setError(true); setStations([]); }
    } finally {
      if (n === pedido.current) setLoading(false);
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
      <header className="rise flex items-center gap-4">
        <span aria-hidden className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-brand"><MapPinned size={26} /></span>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-fg">Paraderos y estaciones</h1>
          <p className="mt-1 text-sm text-muted">Busca por nombre o avenida y consulta el aforo previsto.</p>
        </div>
      </header>

      <div className="card mt-6 p-4 sm:p-5">
        <TextInput size="lg" value={query} onChange={(e) => setQuery(e.currentTarget.value)} type="search"
          placeholder="Ej: Naranjal, Angamos, Plaza Butters…" aria-label="Buscar paradero"
          leftSection={<Search size={20} />} rightSection={query ? <ActionIcon variant="subtle" aria-label="Limpiar búsqueda" onClick={() => setQuery('')}><X size={16} /></ActionIcon> : undefined} />
      <div className="scroll-thin -mx-1 mt-4 flex gap-2 overflow-x-auto px-1 pb-1" role="group" aria-label="Filtrar por sistema">
        {FILTERS.map((f) => (
          <button key={f.label} type="button" className="chip" data-active={system === f.id} aria-pressed={system === f.id} onClick={() => setSystem(f.id)}>
            {f.label}
          </button>
        ))}
      </div>

      </div>
      <div className="mt-6" aria-live="polite">
        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" role="status" aria-label="Buscando paraderos">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[5.5rem] !rounded-2xl" />)}
          </div>
        ) : error ? (
          <div className="space-y-3 py-8 text-center">
            <Alert tono="warn" className="mx-auto max-w-md text-left">No se pudo cargar la lista. Puede ser tu conexión o el servidor.</Alert>
            <button className="btn btn-secondary" onClick={() => fetchStations(query, system)}>Reintentar</button>
          </div>
        ) : stations.length === 0 ? (
          <EmptyState icon={SearchX} title="Sin resultados" text="No encontramos paraderos que coincidan. Prueba con otro nombre o avenida." />
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted"><strong className="text-fg">{stations.length}</strong> resultado{stations.length === 1 ? '' : 's'}</p>
              <SegmentedControl size="xs" value={view} onChange={setView} aria-label="Vista de paraderos"
                data={[{ value: 'cards', label: 'Tarjetas' }, { value: 'table', label: 'Tabla' }]} />
            </div>
            {view === 'table' ? <div className="card p-4"><DataTable rows={stations} columns={stationColumns} title="Paraderos y estaciones" searchable={false} /></div> : <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {stations.slice(0, visible).map((s, i) => <StationCard key={`${s.id}-${i}`} station={s} index={i} />)}
            </div>
            {visible < stations.length && (
              <div className="mt-6 text-center">
                <button className="btn btn-secondary" onClick={() => setVisible((v) => v + 60)}>Mostrar más</button>
              </div>
            )}
            </> }
          </>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return <Suspense><SearchContent /></Suspense>;
}
