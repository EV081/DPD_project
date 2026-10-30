import { Bus, TrainFront, X, Footprints, MapPinned, Lightbulb } from 'lucide-react';
import { TripMatchResponse, MatchedRoute, ForecastView } from '@/lib/types';
import ForecastPanel from './ForecastPanel';

interface Props {
  tripData: TripMatchResponse;
  selectedRoute: MatchedRoute;
  forecast: ForecastView | null;
  loadingForecast: boolean;
  onClose: () => void;
  children?: React.ReactNode;
}

const nombreServicio = (route: MatchedRoute): string => {
  switch (route.system) {
    case 'metropolitano': return 'Metropolitano';
    case 'metro_l1': return 'Metro Línea 1';
    case 'alimentadores': return `Alimentador ${route.route_code}`;
    default: return `Corredor ${route.route_code}`;
  }
};

export default function TripSummaryCard({ tripData, selectedRoute, forecast, loadingForecast, onClose, children }: Props) {
  const totalWalk = Math.round(selectedRoute.origin_walk_m + selectedRoute.dest_walk_m);
  const Icon = selectedRoute.system === 'metropolitano' || selectedRoute.system === 'metro_l1' ? TrainFront : Bus;

  return (
    <div className="float-panel max-h-[62dvh] overflow-y-auto md:max-h-[calc(100dvh-8rem)]">
      <header className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-line bg-surface px-5 py-4">
        <div className="min-w-0">
          <p className="eyebrow">Ruta recomendada</p>
          <h3 className="mt-0.5 truncate text-lg font-semibold text-fg">{tripData.destination.resolved_name}</h3>
        </div>
        <button onClick={onClose} aria-label="Cerrar" className="btn btn-ghost !p-1.5"><X size={18} /></button>
      </header>

      <div className="space-y-4 p-5">
        <div className="flex items-center gap-3 rounded-xl bg-brand-soft p-3.5">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-brand text-white dark:text-[#06101f]">
            <Icon size={21} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-fg">{nombreServicio(selectedRoute)}</p>
            <p className="truncate text-sm text-muted">Sube en <b className="font-semibold text-fg">{selectedRoute.boarding_station}</b></p>
          </div>
        </div>

        <ol className="space-y-3 text-sm">
          <li className="flex items-start gap-3">
            <Footprints size={17} className="mt-0.5 shrink-0 text-muted" />
            <span className="text-muted">Camina <b className="font-semibold text-fg">{Math.round(selectedRoute.origin_walk_m)} m</b> hasta el paradero</span>
          </li>
          <li className="flex items-start gap-3">
            <MapPinned size={17} className="mt-0.5 shrink-0 text-muted" />
            <span className="text-muted">Bájate en <b className="font-semibold text-fg">{selectedRoute.leaving_station}</b> y camina {Math.round(selectedRoute.dest_walk_m)} m</span>
          </li>
          <li className="pl-8 text-xs text-muted">Caminata total: {totalWalk} m</li>
        </ol>

        {tripData.recomendacion_viaje?.mensaje && (
          <p className="flex gap-2.5 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-3 py-2.5 text-sm text-emerald-800 dark:text-emerald-300">
            <Lightbulb size={16} className="mt-0.5 shrink-0" />
            {tripData.recomendacion_viaje.mensaje}
          </p>
        )}

        <div className="border-t border-line pt-4">
          <h4 className="mb-3 text-sm font-semibold text-fg">Aforo en {selectedRoute.boarding_station}</h4>
          <ForecastPanel forecast={forecast} loading={loadingForecast} />
          {children}
        </div>
      </div>
    </div>
  );
}
