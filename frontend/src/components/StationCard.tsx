import Link from 'next/link';
import { MapPin, ChevronRight, Bus, TrainFront } from 'lucide-react';
import { systemInfo } from '@/lib/systems';
import SystemBadge from './SystemBadge';
import { Station } from '@/lib/types';

export default function StationCard({ station, index = 0 }: { station: Station; index?: number }) {
  const info = systemInfo(station.system);
  const Icon = station.system === 'metropolitano' || station.system === 'metro_l1' ? TrainFront : Bus;
  return (
    <Link
      href={`/station/${encodeURIComponent(station.id)}`}
      className="card rise group relative flex items-center gap-3.5 overflow-hidden p-4"
      style={{ '--i': index } as React.CSSProperties}
    >
      <span aria-hidden className="absolute inset-y-0 left-0 w-1" style={{ backgroundColor: info.color }} />
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-white shadow-sm transition-transform duration-300 group-hover:scale-105 group-hover:-rotate-3" style={{ background: `linear-gradient(135deg, ${info.color}, color-mix(in srgb, ${info.color} 75%, #000))` }}>
        <Icon size={22} />
      </span>
      <div className="min-w-0 flex-1">
        <SystemBadge system={station.system} />
        <p className="mt-2 truncate text-base font-semibold text-fg">{station.name}</p>
        <p className="mt-0.5 flex items-center gap-1 truncate text-sm text-muted">
          <MapPin size={13} className="shrink-0" />
          {station.avenida || 'Sin referencia'}
          {station.distance_m !== undefined && (
            <span className="ml-1 shrink-0 font-medium text-brand">
              · {station.distance_m < 1000 ? `${Math.round(station.distance_m)} m` : `${(station.distance_m / 1000).toFixed(1)} km`}
            </span>
          )}
        </p>
      </div>
      <ChevronRight size={18} className="shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" />
    </Link>
  );
}
