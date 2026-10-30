import { PredictionItem } from '@/lib/types';
import {
  etiquetaClase, etiquetaRecomendacion, claseRecomendacion, claseAforo, textoOcupacion, textoEspera,
  anchoBarra, colorOcupacion, formatoHora,
} from '@/lib/aforo';

export default function PredictionCard({ prediction }: { prediction: PredictionItem }) {
  const sinServicio = prediction.class === 'Sin_servicio';
  return (
    <div className={`card flex w-44 shrink-0 flex-col gap-3 p-4 ${sinServicio ? 'opacity-60' : ''}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold tabular-nums text-fg">{formatoHora(prediction.datetime)}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${claseRecomendacion(prediction.recommendation)}`}>
          {etiquetaRecomendacion(prediction.recommendation)}
        </span>
      </div>

      <div>
        <p className={`text-base font-semibold ${claseAforo(prediction.class)}`}>{etiquetaClase(prediction.class)}</p>
        {prediction.sentido && <p className="truncate text-xs text-muted">{prediction.sentido}</p>}
      </div>

      <div>
        <div className="mb-1.5 flex items-center justify-between text-xs">
          <span className="text-muted">Ocupación</span>
          <span className="font-semibold tabular-nums text-fg">{textoOcupacion(prediction.crowding)}</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
          <div className="h-full rounded-full" style={{ width: `${anchoBarra(prediction.crowding)}%`, backgroundColor: colorOcupacion(prediction.class) }} />
        </div>
        <p className="mt-2 text-xs text-muted">Espera <span className="font-semibold text-fg">{textoEspera(prediction)}</span></p>
      </div>
    </div>
  );
}
