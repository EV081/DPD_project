'use client';

import { Clock, MapPin, Navigation, Search } from 'lucide-react';
import Link from 'next/link';
import BottomSheet from './BottomSheet';
import { RecentDestination } from '@/lib/recents';

interface Props {
  name?: string;
  recents: RecentDestination[];
  showStations: boolean;
  onToggleStations: () => void;
  onPickRecent: (item: RecentDestination) => void;
}

const saludo = () => {
  const h = new Date().getHours();
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
};

// Pantalla de inicio del mapa: saludo, accesos rápidos y destinos recientes
export default function HomeSheet({ name, recents, showStations, onToggleStations, onPickRecent }: Props) {
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
      <div className="space-y-4 px-5 pb-5">
        <div className="grid grid-cols-2 gap-2.5">
          <Link href="/destinations" className="flex items-center gap-2.5 rounded-xl bg-brand-soft p-3 text-sm font-semibold text-brand transition-transform active:scale-[.98]">
            <Navigation size={18} /> Planificar viaje
          </Link>
          <button
            type="button"
            aria-pressed={showStations}
            onClick={onToggleStations}
            className={`flex items-center gap-2.5 rounded-xl p-3 text-sm font-semibold transition-all active:scale-[.98] ${
              showStations ? 'bg-brand text-white dark:text-[#06101f]' : 'bg-surface-2 text-fg'
            }`}
          >
            <MapPin size={18} /> {showStations ? 'Ocultar paraderos' : 'Ver paraderos'}
          </button>
        </div>

        <div>
          <p className="eyebrow mb-1.5">Recientes</p>
          {recents.length === 0 ? (
            <p className="flex items-center gap-2.5 rounded-xl bg-surface-2 px-3.5 py-3 text-sm text-muted">
              <Search size={16} className="shrink-0" /> Tus destinos buscados aparecerán aquí.
            </p>
          ) : (
            <ul className="-mx-2">
              {recents.map((r) => (
                <li key={r.label}>
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
