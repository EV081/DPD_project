'use client';

import { use, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, MapPin, Map, Info, CalendarX, CircleAlert, Activity } from 'lucide-react';
import dynamic from 'next/dynamic';
import SystemBadge from '@/components/SystemBadge';
import PredictionCard from '@/components/PredictionCard';
import { ForecastScopeNote } from '@/components/ForecastPanel';
import FeedbackBox from '@/components/FeedbackBox';
import { Spinner, Skeleton, EmptyState } from '@/components/Spinner';
import SeguridadAcceso from '@/components/SeguridadAcceso';
import Alert from '@/components/Alert';
import { getStation, getStationPrediction } from '@/lib/services';
import { FOCUS_STORAGE_KEY } from '@/lib/constants';
import { etiquetaClase, claseAforo, textoEspera, textoAjusteEspera } from '@/lib/aforo';
import { systemInfo } from '@/lib/systems';
import { Station, StationPrediction } from '@/lib/types';

// Carga dinámica del MiniMapa sin SSR
const MiniMap = dynamic(() => import('@/components/MiniMap'), {
  ssr: false,
  loading: () => <div className="h-48 w-full animate-pulse rounded-2xl bg-surface-muted" />,
});

export default function StationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [station, setStation] = useState<Station | null>(null);
  const [forecast, setForecast] = useState<StationPrediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [predError, setPredError] = useState(false);
  const [reload, setReload] = useState(0);
  const [consultedAt, setConsultedAt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setForecast(null);
      setConsultedAt(0);
      setPredError(false);
      let st: Station;
      try {
        st = await getStation(decodeURIComponent(id));
      } catch (err: any) {
        console.error('Error al cargar la estación:', err);
        if (!cancelled) { setNotFound(true); setLoading(false); }
        return;
      }
      if (cancelled) return;
      setStation(st);
      setNotFound(false);
      try {
        const pred = await getStationPrediction(st);
        if (!cancelled) { setForecast(pred); setConsultedAt(Date.now()); }
      } catch (err) {
        console.error('Error al cargar el pronóstico:', err);
        if (!cancelled) { setForecast(null); setPredError(true); }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id, reload]);

  if (loading && !station) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 px-4 py-10 md:px-8" role="status" aria-label="Cargando">
        <Skeleton className="h-40 !rounded-2xl" />
        <Skeleton className="h-28 !rounded-2xl" />
      </div>
    );
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
  const ajusteEspera = textoAjusteEspera(cur);

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8 md:py-10">
      <button type="button" onClick={() => router.back()} className="btn btn-ghost -ml-3 mb-4 !px-3">
        <ArrowLeft size={16} /> Volver
      </button>

      <header className="card rise relative overflow-hidden p-6 pt-7" style={{ backgroundImage: `linear-gradient(160deg, color-mix(in srgb, ${systemInfo(station.system).color} 14%, var(--surface)), var(--surface) 55%)` }}>
        <div aria-hidden className="absolute inset-x-0 top-0 h-1.5" style={{ backgroundColor: systemInfo(station.system).color }} />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SystemBadge system={station.system} />
          <span className="font-mono text-xs text-muted">ID {station.id}</span>
        </div>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-fg">{station.name}</h1>
        <p className="mt-1 text-sm text-muted">{station.avenida || 'Sin referencia'}</p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
          <p className="flex items-center gap-2 text-sm text-muted">
            <MapPin size={15} /> {station.latitude.toFixed(5)}, {station.longitude.toFixed(5)}
          </p>
          <button
            className="btn btn-secondary !py-2"
            onClick={() => { sessionStorage.setItem(FOCUS_STORAGE_KEY, station.id); router.push('/map'); }}
          >
             Ver en el mapa
          </button>
        </div>
      </header>

      <section className="rise mt-6" style={{ '--i': 1 } as React.CSSProperties} aria-label="Seguridad del acceso">
        <SeguridadAcceso station={station} />
      </section>

      <section className="rise mt-8" style={{ '--i': 2 } as React.CSSProperties} aria-label="Pronóstico de aforo">
        <h2 className="text-lg font-semibold text-fg">Pronóstico de aforo</h2>
        <p className="mt-0.5 text-sm text-muted">Ocupación estimada a bordo con demanda pronosticada (LightGBM) y matriz origen-destino.</p>
        <ForecastScopeNote referenceDate={forecast?.referencia?.fecha_referencia_datos} />

        {loading ? (
          <div className="flex items-center justify-center gap-2.5 py-16 text-sm text-muted">
            <Spinner size={18} /> Calculando predicciones…
          </div>
        ) : forecast && cur ? (
          <div className="mt-4 space-y-5">
            <div className="card rise flex flex-wrap items-center gap-x-8 gap-y-3 p-5">
              <div>
                <p className="eyebrow">Ahora</p>
                <p className={`mt-0.5 text-3xl font-bold tracking-tight ${claseAforo(cur.class)}`}>{etiquetaClase(cur.class)}</p>
              </div>
              <div>
                <p className="eyebrow">Espera estimada</p>
                <p className="mt-0.5 text-3xl font-bold tracking-tight tabular-nums text-fg">{textoEspera(cur)}</p>
              </div>
              {ajusteEspera !== null && (
                <p className="flex items-center gap-2 text-sm text-warn">
                  <Activity size={16} /> {ajusteEspera}
                </p>
              )}
              <div className="w-full sm:ml-auto sm:w-56">
                <FeedbackBox station={station} current={cur} consultedAt={consultedAt} />
              </div>
            </div>

            <div>
              <h3 className="mb-3 text-sm font-semibold text-fg">Próximas horas</h3>
              <div className="scroll-thin -mx-1 flex gap-3 overflow-x-auto px-1 pb-3">
                {forecast.forecast.filter((p) => p.datetime >= cur.datetime).map((p, i) => (
                  <PredictionCard key={i} prediction={p} index={i} />
                ))}
              </div>
            </div>

            <div className="flex items-start gap-3 rounded-xl border border-brand/25 bg-brand-soft p-4">
              <Info size={18} className="mt-0.5 shrink-0 text-brand" />
              <p className="text-sm leading-relaxed text-fg">
                La ocupación es la de los vehículos al salir de este paradero. La recomendación
                (<b>Abordar</b>, <b>Esperar el siguiente</b> o <b>Cambiar de paradero</b>) considera el aforo de esta hora y de la siguiente.
              </p>
            </div>
          </div>
        ) : predError ? (
          <div className="mt-4 space-y-3">
            <Alert tono="warn">No se pudo calcular el pronóstico. Puede ser tu conexión o el servidor.</Alert>
            <button onClick={() => setReload((n) => n + 1)} className="btn btn-secondary">Reintentar</button>
          </div>
        ) : (
          <div className="mt-4">
            <EmptyState icon={CalendarX} title="Sin pronóstico" text="Este paradero no tiene datos de validaciones ATU propios, así que no se muestra una predicción." />
          </div>
        )}

        {/* MINI MAPA CON TIPOGRAFÍA UNIFORME */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-fg">Ubicación del paradero</h2>
          <p className="mt-0.5 text-sm text-muted">Vista satelital o de calles de la estación en el entorno urbano.</p>
        <div className="mt-3 overflow-hidden rounded-2xl border border-line shadow-sm">
        <MiniMap
          latitude={station.latitude}
          longitude={station.longitude}
          stationName={station.name}
          systemColor={systemInfo(station.system).color}
        />
        </div>
        </div>
      </section>
    </div>
  );
}
