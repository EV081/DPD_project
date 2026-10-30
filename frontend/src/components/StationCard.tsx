import Link from 'next/link';
import { MapPin, ChevronRight } from 'lucide-react';
import SystemBadge from './SystemBadge';
import { Station } from '@/lib/types';

export default function StationCard({ station }: { station: Station }) {
  return (
    <Link
      href={`/station/${encodeURIComponent(station.id)}`}
      className="card group flex items-center gap-3 p-4 transition-colors hover:border-brand/60"
    >
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
