'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { Footprints, Phone, ShieldCheck } from 'lucide-react';
import Alert from './Alert';
import { Skeleton } from './Spinner';
import { Coords } from '@/lib/geolocation';
import { errorMessage } from '@/lib/client';
import {
  claseBanda, etiquetaBanda, getRutaPeatonal, NUMERO_EMERGENCIA, RespuestaRuta, RutaPeatonal,
} from '@/lib/eje2';
import { Station } from '@/lib/types';
import { initialWalkingRoute } from '@/lib/ui-state';
import { parseWalkingLimit } from '@/lib/walking-preferences';

export interface CaminataMapa { normal: any; segura: any | null; seleccionada: 'normal' | 'segura' }

interface Props {
  station: Station;
  origen: Coords;
  origenReal: boolean;
  /** La demostración permite usar el origen del viaje sólo tras un clic explícito. */
  permitirOrigenReferencia?: boolean;
  /** Carga la ruta sin esperar el clic (en el planificador, la caminata ya es parte del viaje). */
  auto?: boolean;
  onChange: (caminata: CaminataMapa | null) => void;
}

const AVISO = 'Basado en denuncias registradas. No es la probabilidad de ser víctima. En una emergencia llama al 105.';
const NOMBRE = { normal: 'Más corta', segura: 'Ponderada por denuncias' } as const;
const DECIMALES = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 3 });

function minutosDeCaminata(minutos: number) {
  if (minutos > 0 && minutos < 0.001) return 'menos de 0,001 min';
  return `${DECIMALES.format(minutos)} min`;
}

// Cómo llegar caminando al paradero: ruta más corta vs. más segura, con la explicación del backend
export default function RutaSegura({ station, origen, origenReal, permitirOrigenReferencia = false, auto = false, onChange }: Props) {
  const [res, setRes] = useState<RespuestaRuta | null>(null);
  const [sel, setSel] = useState<'normal' | 'segura'>('segura');
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limiteTexto, setLimiteTexto] = useState('');
  const [limiteAplicado, setLimiteAplicado] = useState<number | null>(null);
  const [errorLimite, setErrorLimite] = useState<string | null>(null);
  const [referenciaAceptada, setReferenciaAceptada] = useState(false);
  const origenHabilitado = origenReal || (permitirOrigenReferencia && referenciaAceptada);
  const limiteId = useId();
  const pedido = useRef(0);   // descarta respuestas de un paradero anterior

  const cargar = async (limite: number | null = limiteAplicado, aceptaReferencia = false) => {
    if (!origenHabilitado && !(permitirOrigenReferencia && aceptaReferencia)) return;
    if (aceptaReferencia) setReferenciaAceptada(true);
    const n = ++pedido.current;
    setCargando(true);
    setError(null);
    setRes(null);
    onChange(null);
    try {
      const r = await getRutaPeatonal(origen, station, 'segura', limite);
      if (n !== pedido.current) return;
      const inicial = r.tolerancia_caminata?.cumple_segura === false ? 'normal' : initialWalkingRoute(r.recomendada);
      setRes(r);
      setSel(inicial);
      onChange({ normal: r.rutas.normal.geojson, segura: r.recomendada === 'misma' ? null : r.rutas.segura.geojson, seleccionada: inicial });
    } catch (e: any) {
      if (n !== pedido.current) return;
      setRes(null);
      onChange(null);
      setError(errorMessage(e, 'No se pudo calcular la ruta a pie.'));
    } finally {
      if (n === pedido.current) setCargando(false);
    }
  };

  // Otro paradero: se descarta lo anterior (y se vuelve a pedir si es automático)
  useEffect(() => {
    pedido.current++;
    setRes(null);
    setCargando(false);
    setError(null);
    setReferenciaAceptada(false);
    onChange(null);
    if (auto && origenReal) cargar();
    return () => { pedido.current++; onChange(null); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [station.id, station.system, origen.lat, origen.lon, auto, origenReal, permitirOrigenReferencia]);

  const elegir = (s: 'normal' | 'segura') => {
    if (!res || (s === 'segura' && res.tolerancia_caminata?.cumple_segura === false)) return;
    setSel(s);
    onChange({ normal: res.rutas.normal.geojson, segura: res.recomendada === 'misma' ? null : res.rutas.segura.geojson, seleccionada: s });
  };

  const aplicarLimite = () => {
    try {
      const limite = parseWalkingLimit(limiteTexto);
      setErrorLimite(null);
      setLimiteAplicado(limite);
      void cargar(limite);
    } catch (e) {
      setErrorLimite(e instanceof Error ? e.message : 'Revisa los minutos adicionales.');
    }
  };
  const quitarLimite = () => {
    setLimiteTexto('');
    setLimiteAplicado(null);
    setErrorLimite(null);
    void cargar(null);
  };
  const controles = (
    <form noValidate onSubmit={(event) => { event.preventDefault(); aplicarLimite(); }} className="space-y-2 rounded-xl border border-line p-3">
      <label htmlFor={limiteId} className="block text-sm font-medium text-fg">¿Cuántos minutos extra aceptarías caminar?</label>
      <p id={`${limiteId}-ayuda`} className="text-xs leading-relaxed text-muted">Respecto al camino más corto. Déjalo vacío para usar el criterio habitual. Pulsa aplicar para recalcular.</p>
      <div className="flex flex-wrap gap-2">
        <input id={limiteId} type="number" min="0" step="any" inputMode="decimal" placeholder="Sin límite personal" value={limiteTexto}
          onChange={(event) => { setLimiteTexto(event.target.value); setErrorLimite(null); }} disabled={cargando || !origenHabilitado}
          aria-invalid={Boolean(errorLimite)} aria-describedby={`${limiteId}-ayuda${errorLimite ? ` ${limiteId}-error` : ''}`}
          className="input min-w-0 flex-1" />
        <button type="submit" className="btn btn-secondary" disabled={cargando || !origenHabilitado}>Aplicar</button>
        {limiteAplicado != null && <button type="button" className="btn btn-ghost" disabled={cargando || !origenHabilitado} onClick={quitarLimite}>Quitar límite</button>}
      </div>
      {errorLimite && <p id={`${limiteId}-error`} role="alert" className="text-xs text-danger">{errorLimite}</p>}
    </form>
  );
  const avisoReferencia = !origenReal && permitirOrigenReferencia
    ? <p className="rounded-xl bg-warn/12 p-3 text-xs leading-relaxed text-warn">Esta prueba parte del origen de referencia del viaje, no de tu ubicación real. La caminata sólo se calcula cuando eliges probarla.</p>
    : null;

  if (!res && !cargando && !error) {
    return (
      <div className="space-y-3">
        {avisoReferencia}
        <button type="button" onClick={() => void cargar(limiteAplicado, !origenReal && permitirOrigenReferencia)} disabled={!origenReal && !permitirOrigenReferencia} className="btn btn-secondary w-full">
          <Footprints size={18} /> {!origenReal && permitirOrigenReferencia ? 'Probar caminata desde el origen de referencia' : 'Comparar rutas a pie'}
        </button>
        {!origenReal && !permitirOrigenReferencia && <p className="mt-2 text-xs text-muted">Activa tu ubicación para calcular el camino hasta este paradero.</p>}
        {controles}
      </div>
    );
  }
  if (cargando) return <div className="space-y-3" aria-busy="true">{avisoReferencia}{controles}<p role="status" className="text-xs text-muted">Calculando las dos alternativas a pie…</p><Skeleton className="h-10 w-full" /><Skeleton className="h-24 w-full" /></div>;
  if (error || !res) {
    return (
      <div className="space-y-2">
        {avisoReferencia}
        <Alert tono="warn">{error}</Alert>
        <button type="button" onClick={() => void cargar()} className="btn btn-secondary w-full">Reintentar</button>
        {controles}
      </div>
    );
  }

  const misma = res.recomendada === 'misma';
  const r: RutaPeatonal = res.rutas[misma ? 'normal' : sel];
  const ex = res.explicacion;
  const desvios = r.tramos.filter((t) => t.desvio);

  return (
    <section aria-label="Ruta a pie" className="space-y-3">
      {avisoReferencia}
      {controles}
      {res.tolerancia_caminata && <div role="status" className="space-y-1 rounded-xl bg-surface-2 p-3 text-xs text-muted">
        <p>Límite aplicado: <b className="font-semibold text-fg">{minutosDeCaminata(res.tolerancia_caminata.max_minutos_extra)} extra</b>. La alternativa ponderada añade {minutosDeCaminata(res.tolerancia_caminata.minutos_extra_segura)}.</p>
        {!res.tolerancia_caminata.cumple_segura && <p className="font-medium text-fg">La alternativa ponderada supera tu límite. Se muestra el camino más corto; puedes ampliar los minutos o quitar el límite.</p>}
        <p>{res.tolerancia_caminata.aviso}</p>
      </div>}
      {!misma && (
        <div role="radiogroup" aria-label="Tipo de ruta" className="grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
          {(['segura', 'normal'] as const).map((k) => (
            <button key={k} type="button" role="radio" aria-checked={sel === k} onClick={() => elegir(k)} disabled={k === 'segura' && res.tolerancia_caminata?.cumple_segura === false}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${sel === k ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg'}`}>
              {k === 'segura' && <ShieldCheck size={14} className="mr-1 inline -mt-0.5" />}
              {NOMBRE[k]}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4 rounded-xl border border-line p-3.5">
        <div>
          <p className="text-xl font-bold tabular-nums text-fg">{Math.round(r.minutos)} min</p>
          <p className="text-xs text-muted">{Math.round(r.distancia_m)} m a pie</p>
        </div>
        <span className={`ml-auto rounded-full px-2.5 py-1 text-xs font-semibold ${claseBanda(r.banda_riesgo)}`}>{etiquetaBanda(r.banda_riesgo)}</span>
      </div>

      <p className="text-sm text-fg">{ex.resumen}</p>
      <p className="text-xs leading-relaxed text-muted">El recorrido se pondera con denuncias históricas; no garantiza seguridad ni describe incidentes en tiempo real.</p>

      {!misma && sel === 'segura' && ex.motivos.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted">{ex.motivos.map((m, i) => <li key={i}>{m}</li>)}</ul>
      )}
      {!misma && sel === 'segura' && ex.tramos_evitados.length > 0 && (
        <p className="text-sm text-muted">Evita: {ex.tramos_evitados.map((t) => `${t.nombre} (${t.largo_m} m)`).join(', ')}.</p>
      )}

      <details className="text-sm">
        <summary className="cursor-pointer font-medium text-fg">Calles del recorrido{desvios.length ? ` · ${desvios.length} del desvío` : ''}</summary>
        <ol className="mt-2 space-y-1.5">
          {r.tramos.map((t, i) => (
            <li key={i} className="flex items-center justify-between gap-2">
              <span className="min-w-0 truncate text-fg">{t.nombre}{t.desvio && <span className="ml-1.5 text-xs font-semibold text-brand">desvío</span>}</span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-xs tabular-nums text-muted">{t.largo_m} m</span>
                <span className={`rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold ${claseBanda(t.riesgo)}`}>{etiquetaBanda(t.riesgo)}</span>
              </span>
            </li>
          ))}
        </ol>
      </details>

      <Alert tono="info">{ex.aviso || AVISO}</Alert>
      {ex.llamar_105 && (
        <a href={`tel:${NUMERO_EMERGENCIA}`} className="btn btn-danger w-full"><Phone size={16} /> Emergencia: llamar al {NUMERO_EMERGENCIA}</a>
      )}
    </section>
  );
}
