'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { sendFeedback } from '@/lib/services';
import { etiquetaClase } from '@/lib/aforo';
import { PredictionItem, Station } from '@/lib/types';
import { Spinner } from './Spinner';

interface Props {
  station: Station;
  current: PredictionItem;
  /** Momento (Date.now) en que se mostró la predicción: de ahí se mide la espera real. */
  consultedAt: number;
}

const CLASES = ['Asientos', 'De_pie', 'Saturado'] as const;

// "Ya abordé": mide cuánto esperó de verdad el usuario frente al ETA mostrado
export default function FeedbackBox({ station, current, consultedAt }: Props) {
  const [step, setStep] = useState<'idle' | 'aforo' | 'sending' | 'done' | 'error'>('idle');

  // Otra predicción u otro paradero: el feedback anterior ya no aplica
  useEffect(() => setStep('idle'), [station.id, consultedAt]);

  const enviar = async (aforoPercibido: string | null) => {
    setStep('sending');
    try {
      await sendFeedback({
        station_id: station.id,
        sistema: station.model_system || station.system,
        espera_real_min: Math.min((Date.now() - consultedAt) / 60000, 180),
        eta_mostrado_min: current.eta_min,
        eta_base_min: current.eta_base_min ?? current.eta_min,
        factor_trafico: current.factor_trafico,
        modo_datos: current.modo_datos,
        aforo_mostrado: current.class,
        aforo_percibido: aforoPercibido,
      });
      setStep('done');
    } catch (e) {
      console.error('Error al enviar feedback:', e);
      setStep('error');
    }
  };

  if (current.eta_min == null) return null;   // fuera de servicio: no hay espera que medir

  if (step === 'done') {
    return (
      <p className="mt-4 flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2.5 text-sm font-medium text-emerald-700 dark:text-emerald-300">
        <CheckCircle2 size={16} /> Gracias, tu aporte mejora las estimaciones.
      </p>
    );
  }

  if (step === 'aforo' || step === 'sending') {
    return (
      <div className="mt-4 rounded-xl border border-line bg-surface-2/60 p-3.5">
        <p className="mb-2.5 text-sm font-medium text-fg">¿Cómo estaba el bus? <span className="font-normal text-muted">(opcional)</span></p>
        <div className="flex flex-wrap gap-2">
          {CLASES.map((c) => (
            <button key={c} disabled={step === 'sending'} onClick={() => enviar(c)} className="chip disabled:opacity-60">
              {etiquetaClase(c)}
            </button>
          ))}
          <button disabled={step === 'sending'} onClick={() => enviar(null)} className="btn btn-ghost !px-3 !py-1.5 !text-[0.8125rem]">
            {step === 'sending' ? <Spinner size={14} /> : 'Omitir'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4">
      <button onClick={() => setStep('aforo')} className="btn btn-primary w-full">Ya abordé</button>
      {step === 'error' && <p className="mt-2 text-center text-sm text-rose-600 dark:text-rose-400">No se pudo enviar. Inténtalo de nuevo.</p>}
    </div>
  );
}
