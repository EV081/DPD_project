import { useId, useState } from 'react';
import { Bus, TrainFront, X, Lightbulb, TriangleAlert, ChevronDown } from 'lucide-react';
import { TripMatchResponse, MatchedRoute, ForecastView } from '@/lib/types';
import ForecastPanel from './ForecastPanel';
import BottomSheet from './BottomSheet';
import { systemInfo } from '@/lib/systems';
import { etiquetaClase, claseAforo, colorOcupacion, textoEspera } from '@/lib/aforo';

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

// Sección plegable: solo una abierta a la vez para que la hoja no se vuelva una columna larga
function Seccion({ titulo, abierta, onToggle, children }: { titulo: string; abierta: boolean; onToggle: () => void; children: React.ReactNode }) {
  const id = useId();
  return (
    <section className="border-t border-line">
      <h4>
        <button type="button" onClick={onToggle} aria-expanded={abierta} aria-controls={id} className="flex w-full items-center justify-between gap-3 py-3.5 text-left text-sm font-semibold text-fg outline-none focus-visible:text-brand">
          <span className="min-w-0 truncate">{titulo}</span>
          <ChevronDown size={18} aria-hidden className={`shrink-0 text-muted transition-transform ${abierta ? 'rotate-180' : ''}`} />
        </button>
      </h4>
      <div id={id} hidden={!abierta} className="pb-4">{children}</div>
    </section>
  );
}

export default function TripSummaryCard({ tripData, selectedRoute, forecast, loadingForecast, forecastError, onRetry, walkSlot, onClose, children }: Props) {
  const [abierta, setAbierta] = useState<'aforo' | 'camino' | null>('aforo');
  const alternar = (k: 'aforo' | 'camino') => setAbierta((a) => (a === k ? null : k));
  const t = selectedRoute.transbordo;
  const Icon = selectedRoute.system === 'metropolitano' || selectedRoute.system === 'metro_l1' ? TrainFront : Bus;
  const color = systemInfo(selectedRoute.system).color;
  const color2 = t ? systemInfo(t.system).color : color;
  const actual = forecast && !forecast.sinDatos ? forecast.current : null;
  // Misma clase que el panel: la del minuto actual (interpolada) si el backend la envía
  const claseAhora = (forecast && !forecast.sinDatos && forecast.ahora?.class) || actual?.class;
  const servicio = t ? `${nombreServicio(selectedRoute)} + ${nombreDe(t.system, t.route_code)}` : nombreServicio(selectedRoute);

  // Un solo aviso, el más accionable: cambiar de paradero > recomendación del viaje
  const alternativa = actual?.recommendation === 'cambiar_paradero' ? actual.alternativa : null;
  const mensaje = tripData.recomendacion_viaje?.mensaje;

  return (
    <BottomSheet
      header={
        <header className="px-5 pb-3 pt-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="eyebrow">Ruta seleccionada</p>
              <h3 className="mt-0.5 truncate text-lg font-bold text-fg">{tripData.destination.resolved_name}</h3>
            </div>
            <button onClick={onClose} aria-label="Cerrar" className="btn btn-ghost !rounded-full !bg-surface-2 !p-2"><X size={18} /></button>
          </div>
          {/* Resumen siempre visible, incluso con la hoja plegada */}
          <div className="mt-2.5 flex items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white" style={{ backgroundColor: color }}>
              <Icon size={18} aria-hidden />
            </span>
            <div className="min-w-0 flex-1 text-sm">
              <p className="truncate font-semibold text-fg">{servicio}</p>
              <p className="flex items-center gap-1.5 truncate text-muted">
                <span className="truncate">Sube en {selectedRoute.boarding_station}</span>
                {actual && actual.class !== 'Sin_servicio' && (
                  <>
                    <span aria-hidden>·</span>
                    <span aria-hidden className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: colorOcupacion(claseAhora) }} />
                    <span className={`shrink-0 font-medium ${claseAforo(claseAhora)}`}>{etiquetaClase(claseAhora)}</span>
                    <span className="shrink-0">· {textoEspera(actual)}</span>
                  </>
                )}
              </p>
            </div>
          </div>
        </header>
      }
    >
      <div className="px-5 pb-2">
        <ol aria-label="Itinerario" className="px-1 pb-4">
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
                <p className="text-muted">{nombreDe(t.system, t.route_code)} · tiempos estimados</p>
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

        {alternativa ? (
          <p className="mb-4 flex gap-2.5 rounded-xl bg-danger/10 px-3.5 py-3 text-sm text-danger">
            <TriangleAlert size={16} className="mt-0.5 shrink-0" />
            <span>
              Sube en <b>{alternativa.paradero}</b> ({alternativa.distancia_m} m antes): el bus viene más vacío y ahorras ~{Math.round(alternativa.ahorro_min)} min.
            </span>
          </p>
        ) : mensaje ? (
          <p className="mb-4 flex gap-2.5 rounded-xl bg-ok/12 px-3.5 py-3 text-sm text-ok">
            <Lightbulb size={16} className="mt-0.5 shrink-0" />
            {mensaje}
          </p>
        ) : null}

        <Seccion titulo={t ? `Aforo en ${selectedRoute.boarding_station} (primer paradero)` : `Aforo en ${selectedRoute.boarding_station}`} abierta={abierta === 'aforo'} onToggle={() => alternar('aforo')}>
          <ForecastPanel compact forecast={forecast} loading={loadingForecast} error={forecastError} onRetry={onRetry} />
          {children}
        </Seccion>

        {walkSlot && (
          <Seccion titulo={`Cómo llegar a ${selectedRoute.boarding_station}`} abierta={abierta === 'camino'} onToggle={() => alternar('camino')}>
            {walkSlot}
          </Seccion>
        )}
      </div>
    </BottomSheet>
  );
}
