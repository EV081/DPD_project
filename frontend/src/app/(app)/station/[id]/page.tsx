'use client';

import { use, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, MapPin, Map, Info, CalendarX, CircleAlert, Activity } from 'lucide-react';
import SystemBadge from '@/components/SystemBadge';
import PredictionCard from '@/components/PredictionCard';
import FeedbackBox from '@/components/FeedbackBox';
import { Spinner, EmptyState } from '@/components/Spinner';
import { getStation, getStationPrediction } from '@/lib/services';
import { FOCUS_STORAGE_KEY } from '@/lib/constants';
import { etiquetaClase, claseAforo, textoEspera } from '@/lib/aforo';
import { Station, StationPrediction } from '@/lib/types';

export default function StationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [station, setStation] = useState<Station | null>(null);
  const [forecast, setForecast] = useState<StationPrediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [consultedAt, setConsultedAt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const st = await getStation(decodeURIComponent(id));
        if (cancelled) return;
        setStation(st);
        // Una llamada por id de estación; fecha y hora las pone el backend (hora de Lima)
        const pred = await getStationPrediction(st);
        if (!cancelled) { setForecast(pred); setConsultedAt(Date.now()); }
      } catch (err) {
        console.error('Error al cargar la estación:', err);
        if (!cancelled) setNotFound(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  if (loading && !station) {
    return <div className="flex justify-center py-28"><Spinner size={28} /></div>;
  }

  if (notFound || !station) {
    return (
      <div className="py-20">
        <EmptyState icon={CircleAlert} title="Estación no encontrada" text="No pudimos cargar este paradero. Puede que ya no exista o que el servidor no responda." />
        <div className="text-center"><button onClick={() => router.back()} className="btn btn-primary">Volver</button></div>
      </div>
    );
  }

  const cur = forecast?.current;
  const extraTrafico = cur?.eta_base_min != null && cur.eta_min != null && cur.eta_min - cur.eta_base_min >= 0.5
    ? Math.round(cur.eta_min - cur.eta_base_min) : null;

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
      <button onClick={() => router.back()} className="btn btn-ghost -ml-3 mb-4 !px-3">
        <ArrowLeft size={16} /> Volver
      </button>

      <header className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SystemBadge system={station.system} />
          <span className="font-mono text-xs text-muted">ID {station.id}</span>
        </div>
        <h1 className="mt-3 text-2xl font-bold tracking-tight text-fg">{station.name}</h1>
        <p className="mt-1 text-sm text-muted">{station.avenida || 'Sin referencia'}</p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
          <p className="flex items-center gap-2 text-sm text-muted">
            <MapPin size={15} /> {station.latitude.toFixed(5)}, {station.longitude.toFixed(5)}
          </p>
          <button
            className="btn btn-secondary !py-2"
            onClick={() => { sessionStorage.setItem(FOCUS_STORAGE_KEY, station.id); router.push('/map'); }}
          >
            <Map size={16} /> Ver en el mapa
          </button>
        </div>
      </header>

      <section className="mt-8" aria-label="Pronóstico de aforo">
        <h2 className="text-lg font-semibold text-fg">Pronóstico de aforo</h2>
        <p className="mt-0.5 text-sm text-muted">Ocupación estimada a bordo con demanda pronosticada (LightGBM) y matriz origen-destino.</p>

        {loading ? (
          <div className="flex items-center justify-center gap-2.5 py-16 text-sm text-muted"><Spinner size={18} /> Calculando predicciones…</div>
        ) : forecast && cur ? (
          <div className="mt-4 space-y-5">
            <div className="card flex flex-wrap items-center gap-x-8 gap-y-3 p-5">
              <div>
                <p className="eyebrow">Ahora</p>
                <p className={`mt-0.5 text-xl font-semibold ${claseAforo(cur.class)}`}>{etiquetaClase(cur.class)}</p>
              </div>
              <div>
                <p className="eyebrow">Espera estimada</p>
                <p className="mt-0.5 text-xl font-semibold tabular-nums text-fg">{textoEspera(cur)}</p>
              </div>
              {extraTrafico !== null && (
                <p className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-300">
                  <Activity size={16} /> Incluye +{extraTrafico} min por tráfico en vivo
                </p>
              )}
              <div className="w-full sm:ml-auto sm:w-56"><FeedbackBox station={station} current={cur} consultedAt={consultedAt} /></div>
            </div>

            <div>
              <h3 className="mb-3 text-sm font-semibold text-fg">Próximas horas</h3>
              <div className="scroll-thin -mx-1 flex gap-3 overflow-x-auto px-1 pb-3">
                {forecast.forecast.filter((p) => p.datetime >= cur.datetime).map((p, i) => <PredictionCard key={i} prediction={p} />)}
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-xl border border-brand/25 bg-brand-soft p-4">
              <Info size={18} className="mt-0.5 shrink-0 text-brand" />
              <p className="text-sm leading-relaxed text-fg">
                La ocupación es la de los vehículos al salir de este paradero. La recomendación
                (<b>Abordar</b>, <b>Esperar el siguiente</b> o <b>Cambiar de paradero</b>) considera el aforo de esta hora y de la siguiente.
                {forecast.referencia ? ` Estimado con datos ATU del ${forecast.referencia.fecha_referencia_datos} (día equivalente).` : ''}
              </p>
            </div>
          </div>
        ) : (
          <EmptyState icon={CalendarX} title="Sin pronóstico" text="Este paradero no tiene datos de validaciones ATU propios, así que no se muestra una predicción." />
        )}
      </section>
    </div>
  );
}
