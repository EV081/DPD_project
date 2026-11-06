import { Bus, TrainFront, X, Lightbulb, Info } from 'lucide-react';
import { TripMatchResponse, MatchedRoute, ForecastView } from '@/lib/types';
import ForecastPanel from './ForecastPanel';
import BottomSheet from './BottomSheet';
import { systemInfo } from '@/lib/systems';

interface Props {
  tripData: TripMatchResponse;
  selectedRoute: MatchedRoute;
  forecast: ForecastView | null;
  loadingForecast: boolean;
  forecastError?: boolean;
  onRetry?: () => void;
  /** Cómo llegar caminando al paradero (ruta segura e índice de seguridad). */
  walkSlot?: React.ReactNode;
  onClose: () => void;
  children?: React.ReactNode;
}

const nombreDe = (sistema: string, codigo: string): string => {
  switch (sistema) {
    case 'metropolitano': return !codigo || codigo.toUpperCase() === 'METROPOLITANO' ? 'Metropolitano' : `Metropolitano · ${codigo}`;
    case 'metro_l1': return 'Metro Línea 1';
    case 'alimentadores': return `Alimentador ${codigo}`;
    default: return `Corredor ${codigo}`;
  }
};
const nombreServicio = (route: MatchedRoute): string => nombreDe(route.system, route.route_code);

// Paso de la línea de tiempo: punto de color + línea que lo une con el siguiente
function Step({ color, last, children }: { color: string; last?: boolean; children: React.ReactNode }) {
  return (
    <li className="relative flex gap-3.5 pb-5 last:pb-0">
      {!last && <span aria-hidden className="absolute left-[0.4375rem] top-4 h-full w-0.5 bg-line" />}
      <span aria-hidden className="relative z-10 mt-1 h-4 w-4 shrink-0 rounded-full border-[3px] border-surface" style={{ backgroundColor: color, boxShadow: `0 0 0 2px ${color}` }} />
      <div className="min-w-0 text-sm">{children}</div>
    </li>
  );
}

export default function TripSummaryCard({ tripData, selectedRoute, forecast, loadingForecast, forecastError, onRetry, walkSlot, onClose, children }: Props) {
  const t = selectedRoute.transbordo;
  const totalWalk = Math.round(selectedRoute.origin_walk_m + selectedRoute.dest_walk_m + (t?.caminata_m ?? 0));
  const Icon = selectedRoute.system === 'metropolitano' || selectedRoute.system === 'metro_l1' ? TrainFront : Bus;
  const color = systemInfo(selectedRoute.system).color;
  const color2 = t ? systemInfo(t.system).color : color;

  return (
    <BottomSheet
      header={
        <header className="flex items-start justify-between gap-3 px-5 pb-3 pt-1">
          <div className="min-w-0">
            <p className="eyebrow">Ruta recomendada</p>
            <h3 className="mt-0.5 truncate text-lg font-bold text-fg">{tripData.destination.resolved_name}</h3>
          </div>
          <button onClick={onClose} aria-label="Cerrar" className="btn btn-ghost !rounded-full !bg-surface-2 !p-2"><X size={18} /></button>
        </header>
      }
    >
      <div className="space-y-5 px-5 pb-5">
        <div className="flex items-center gap-3.5 rounded-2xl p-3.5 text-white" style={{ background: `linear-gradient(135deg, ${color}, color-mix(in srgb, ${color} 70%, #000))` }}>
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/20 backdrop-blur">
            <Icon size={24} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-base font-bold">{t ? `${nombreServicio(selectedRoute)} + ${nombreDe(t.system, t.route_code)}` : nombreServicio(selectedRoute)}</p>
            <p className="text-sm text-white/85">
              {t ? 'Con transbordo · ' : ''}Caminata total · {totalWalk} m
              {t && selectedRoute.costo_generalizado_min != null ? ` · ≈ ${Math.round(selectedRoute.costo_generalizado_min)} min` : ''}
            </p>
          </div>
        </div>

        <ol aria-label="Itinerario" className="px-1">
          <Step color="var(--muted)">
            <p className="font-semibold text-fg">Camina {Math.round(selectedRoute.origin_walk_m)} m</p>
            <p className="text-muted">hasta el paradero</p>
          </Step>
          <Step color={color}>
            <p className="font-semibold text-fg">Sube en {selectedRoute.boarding_station}</p>
            <p className="text-muted">{nombreServicio(selectedRoute)}</p>
          </Step>
          <Step color={color}>
            <p className="font-semibold text-fg">Bájate en {selectedRoute.leaving_station}</p>
            <p className="text-muted">
              {t ? `y camina ${Math.round(t.caminata_m)} m hasta ${t.boarding_station}` : `y camina ${Math.round(selectedRoute.dest_walk_m)} m`}
            </p>
          </Step>
          {t && (
            <>
              <Step color={color2}>
                <p className="font-semibold text-fg">Sube en {t.boarding_station}</p>
                <p className="text-muted">{nombreDe(t.system, t.route_code)}</p>
              </Step>
              <Step color={color2}>
                <p className="font-semibold text-fg">Bájate en {t.leaving_station}</p>
                <p className="text-muted">y camina {Math.round(selectedRoute.dest_walk_m)} m</p>
              </Step>
            </>
          )}
          <Step color="var(--ok)" last>
            <p className="font-semibold text-fg">Llegas a tu destino</p>
          </Step>
        </ol>

        {t && (
          <p className="flex gap-2.5 rounded-xl bg-surface-2 px-3.5 py-3 text-sm text-muted">
            <Info size={16} className="mt-0.5 shrink-0" />
            <span>No hay ruta directa. Los tiempos del transbordo son estimados (caminata, espera y viaje típicos) y el aforo de abajo es del primer paradero.</span>
          </p>
        )}

        {tripData.recomendacion_viaje?.mensaje && (
          <p className="flex gap-2.5 rounded-xl bg-ok/12 px-3.5 py-3 text-sm text-ok">
            <Lightbulb size={16} className="mt-0.5 shrink-0" />
            {tripData.recomendacion_viaje.mensaje}
          </p>
        )}

        {walkSlot && (
          <div className="border-t border-line pt-4">
            <h4 className="mb-3 text-sm font-semibold text-fg">Cómo llegar a {selectedRoute.boarding_station}</h4>
            {walkSlot}
          </div>
        )}

        <div className="border-t border-line pt-4">
          <h4 className="mb-3 text-sm font-semibold text-fg">Aforo en {selectedRoute.boarding_station}</h4>
          <ForecastPanel forecast={forecast} loading={loadingForecast} error={forecastError} onRetry={onRetry} />
          {children}
        </div>
      </div>
    </BottomSheet>
  );
}
