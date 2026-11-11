'use client';

import { Clock, MapPin, Navigation, Search, Siren } from 'lucide-react';
import Link from 'next/link';
import BottomSheet from './BottomSheet';
import { RecentDestination } from '@/lib/recents';

interface Props {
  name?: string;
  recents: RecentDestination[];
  showStations: boolean;
  onToggleStations: () => void;
  onReport: () => void;
  onPickRecent: (item: RecentDestination) => void;
}

const saludo = () => {
  const h = new Date().getHours();
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
};

// Pantalla de inicio del mapa: saludo, accesos rápidos y destinos recientes
export default function HomeSheet({ name, recents, showStations, onToggleStations, onReport, onPickRecent }: Props) {
  const first = name?.split(/\s+/)[0];

  return (
    <BottomSheet
      header={
        <div className="px-5 pb-3 pt-1">
          <h2 className="text-xl font-bold tracking-tight text-fg">{saludo()}{first ? `, ${first}` : ''}</h2>
          <p className="text-sm text-muted">Busca tu destino arriba y te decimos qué paradero conviene.</p>
        </div>
      }
    >
      <div className="space-y-4 px-5 pb-5 pt-2">
        <div className="stagger grid grid-cols-2 items-stretch gap-2.5">
          <Link href="/destinations" className="group flex h-full flex-col gap-2.5 rounded-2xl border border-brand/25 bg-brand-soft p-3.5 text-sm font-semibold text-fg transition-[transform,background-color,border-color] hover:-translate-y-0.5 hover:border-brand/50 active:scale-[.97]">
            <Navigation size={20} className="text-brand transition-transform duration-300 group-hover:rotate-12" />
            Planificar viaje
          </Link>
          <button
            type="button"
            aria-pressed={showStations}
            onClick={onToggleStations}
            className={`group flex h-full flex-col items-start gap-2.5 rounded-2xl border p-3.5 text-left text-sm font-semibold text-fg transition-[transform,background-color,border-color] hover:-translate-y-0.5 active:scale-[.97] ${
              showStations ? 'border-brand/50 bg-brand-soft' : 'border-line bg-surface-2 hover:border-brand/30'
            }`}
          >
            <MapPin size={20} className={`transition-colors ${showStations ? 'text-brand' : 'text-muted group-hover:text-brand'}`} />
            {showStations ? 'Ocultar paraderos' : 'Ver paraderos'}
          </button>
        </div>

        <button type="button" onClick={onReport} className="group flex w-full items-center gap-3 rounded-2xl border border-line bg-surface-2 p-3.5 text-left text-sm font-semibold text-fg transition-[transform,border-color] hover:border-danger/40 active:scale-[.98]">
          <Siren size={20} className="shrink-0 text-danger" />
          <span>Reportar un incidente<span className="block text-xs font-normal text-muted">Puedes revisar tus reportes en tu cuenta.</span></span>
        </button>

        <div>
          <p className="eyebrow mb-1.5">Recientes</p>
          {recents.length === 0 ? (
            <p className="flex items-center gap-2.5 rounded-xl bg-surface-2 px-3.5 py-3 text-sm text-muted">
              <Search size={16} className="shrink-0" /> Tus destinos buscados aparecerán aquí.
            </p>
          ) : (
            <ul className="-mx-2">
              {recents.map((r, i) => (
                <li key={r.label} className="rise" style={{ '--i': i + 2 } as React.CSSProperties}>
                  <button
                    type="button"
                    onClick={() => onPickRecent(r)}
                    className="flex w-full items-center gap-3 rounded-xl px-2 py-2.5 text-left transition-colors hover:bg-surface-2"
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-muted">
                      <Clock size={16} />
                    </span>
                    <span className="line-clamp-2 text-sm font-medium text-fg">{r.label}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </BottomSheet>
  );
}
