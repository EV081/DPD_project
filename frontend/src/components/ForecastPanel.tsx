import { Activity, TriangleAlert } from 'lucide-react';
import { ForecastView } from '@/lib/types';
import {
  etiquetaClase, etiquetaRecomendacion, claseRecomendacion, claseAforo, textoOcupacion, textoEspera,
  anchoBarra, colorOcupacion, formatoHora, textoProbabilidadLleno,
} from '@/lib/aforo';
import { Spinner } from './Spinner';

interface Props {
  forecast: ForecastView | null;
  loading: boolean;
}

// Estado actual del paradero + pronóstico desde ahora (tarjeta del mapa y del planificador)
export default function ForecastPanel({ forecast, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2.5 py-6 text-sm text-muted">
        <Spinner size={18} /> Calculando aforo…
      </div>
    );
  }
  if (!forecast) {
    return <p className="py-3 text-center text-sm text-muted">No hay predicciones disponibles para esta estación.</p>;
  }
  if (forecast.sinDatos) {
    return (
      <p className="rounded-lg bg-surface-2 px-3 py-3 text-center text-sm text-muted">
        Sin predicción: este paradero no tiene datos de validaciones ATU propios.
      </p>
    );
  }

  const { current, referencia } = forecast;
  // Solo de la hora consultada en adelante: las horas pasadas ya no ayudan a decidir
  const predictions = forecast.predictions.filter((p) => p.datetime > current.datetime);
  const lleno = textoProbabilidadLleno(current.probabilidad_no_subir);
  const extraTrafico =
    current.eta_base_min != null && current.eta_min != null && current.eta_min - current.eta_base_min >= 0.5
      ? Math.round(current.eta_min - current.eta_base_min)
      : null;

  return (
    <div className="space-y-4">
      <section aria-label="Estado actual" className="rounded-xl border border-line bg-surface-2/60 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="eyebrow">Ahora · {formatoHora(current.datetime)}</p>
            <p className={`mt-1 text-xl font-semibold ${claseAforo(current.class)}`}>{etiquetaClase(current.class)}</p>
            {current.sentido && <p className="text-sm text-muted">{current.sentido}</p>}
          </div>
          <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${claseRecomendacion(current.recommendation)}`}>
            {etiquetaRecomendacion(current.recommendation)}
          </span>
        </div>

        <dl className="mt-4 grid grid-cols-3 gap-3">
          <div>
            <dt className="text-xs text-muted">Espera</dt>
            <dd className="text-lg font-semibold tabular-nums text-fg">{textoEspera(current)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Ocupación</dt>
            <dd className="text-lg font-semibold tabular-nums text-fg">{textoOcupacion(current.crowding)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">A bordo</dt>
            <dd className="text-lg font-semibold tabular-nums text-fg">
              {current.pasajeros_por_tren != null ? `≈ ${current.pasajeros_por_tren}` : '—'}
            </dd>
          </div>
        </dl>

        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-line">
          <div className="h-full rounded-full transition-all" style={{ width: `${anchoBarra(current.crowding)}%`, backgroundColor: colorOcupacion(current.class) }} />
        </div>

        {(extraTrafico !== null || lleno || (current.recommendation === 'cambiar_paradero' && current.alternativa)) && (
          <ul className="mt-4 space-y-2 border-t border-line pt-3 text-sm">
            {extraTrafico !== null && (
              <li className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
                <Activity size={15} className="shrink-0" /> Tráfico en vivo: +{extraTrafico} min de espera
              </li>
            )}
            {lleno && (
              <li className="flex items-center gap-2 text-muted"><TriangleAlert size={15} className="shrink-0" /> {lleno}</li>
            )}
            {current.recommendation === 'cambiar_paradero' && current.alternativa && (
              <li className="text-rose-700 dark:text-rose-300">
                Sube en <b>{current.alternativa.paradero}</b> ({current.alternativa.distancia_m} m antes): el bus viene
                más vacío y ahorras ~{Math.round(current.alternativa.ahorro_min)} min.
              </li>
            )}
          </ul>
        )}
      </section>

      {predictions.length > 0 && (
        <section aria-label="Próximas horas">
          <h4 className="mb-2 text-sm font-semibold text-fg">Próximas horas</h4>
          <div className="scroll-thin -mx-1 flex gap-2 overflow-x-auto px-1 pb-2">
            {predictions.map((item, i) => (
              <div key={i} className={`w-[7.5rem] shrink-0 rounded-lg border border-line bg-surface p-3 ${item.class === 'Sin_servicio' ? 'opacity-55' : ''}`}>
                <p className="text-sm font-semibold tabular-nums text-fg">{formatoHora(item.datetime)}</p>
                <p className={`mt-1 truncate text-sm font-medium ${claseAforo(item.class)}`}>{etiquetaClase(item.class)}</p>
                {item.class === 'Sin_servicio' ? (
                  <p className="mt-0.5 text-xs text-muted">—</p>
                ) : (
                  <>
                    <p className="mt-0.5 text-xs tabular-nums text-muted">{textoOcupacion(item.crowding)} ocupado</p>
                    <p className="text-xs tabular-nums text-muted">Espera {textoEspera(item)}</p>
                  </>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {referencia && (
        <p className="text-xs text-muted">Estimado con datos ATU del {referencia.fecha_referencia_datos} (día equivalente).</p>
      )}
    </div>
  );
}
