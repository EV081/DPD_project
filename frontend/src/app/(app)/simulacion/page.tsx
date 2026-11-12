'use client';

import { useEffect, useMemo, useState, type FormEvent, type CSSProperties } from 'react';
import { ChartColumn, Download, MapPin } from 'lucide-react';
import OccupancyChart from '@/components/OccupancyChart';
import { useAuth } from '@/context/AuthContext';
import { NativeSelect } from '@mantine/core';
import Alert from '@/components/Alert';
import PlanSalida from '@/components/PlanSalida';
import { Spinner } from '@/components/Spinner';
import { claseAforo, etiquetaClase, etiquetaRecomendacion, formatoHora } from '@/lib/aforo';
import { getStationPrediction, getStations, getTripPlan, mapSystemToBackendApi } from '@/lib/services';
import { destinosDe, etiquetaEstacion, hoyLima, lineasDe, origenesDe, seleccion, sumarDias, usaRuta } from '@/lib/simulacion';
import { systemInfo } from '@/lib/systems';
import type { PlanSalida as Plan, PredictionItem, Station, StationPrediction } from '@/lib/types';

const PRIMER_DIA = '2025-01-29';   // primer día con 28 días de historia ATU
const DIAS_ADELANTE = 60;          // los días posteriores a 2025 se estiman con su día homólogo
const SISTEMAS: Station['system'][] = ['metro_l1', 'metropolitano', 'corredores', 'alimentadores'];
const CAMPO = 'mt-1.5 block w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-fg focus-visible:outline-2 focus-visible:outline-brand';
const NUMERO = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1 });

function espera(item: PredictionItem) {
  if (item.class === 'Sin_servicio') return 'Fuera de horario';
  return item.eta_min == null ? 'Sin estimación' : `${NUMERO.format(item.eta_min)} min`;
}

function ocupacion(item: PredictionItem) {
  return item.class === 'Sin_servicio' || item.crowding == null ? '—' : `${NUMERO.format(item.crowding * 100)} %`;
}

function descargarDia(resultado: StationPrediction) {
  const filas = resultado.forecast.map((item) => [
    resultado.station,
    resultado.system,
    resultado.series,
    resultado.referencia.fecha_objetivo,
    resultado.referencia.fecha_referencia_datos,
    formatoHora(item.datetime),
    item.sentido,
    item.model ?? resultado.model,
    item.class,
    item.class === 'Sin_servicio' ? null : item.crowding,
    item.eta_min,
    item.recommendation,
  ]);
  const encabezados = ['estacion', 'sistema', 'serie', 'dia_consultado', 'dia_atu', 'hora_lima', 'sentido', 'metodo', 'clase', 'ocupacion_fraccion', 'espera_min', 'recomendacion'];
  const csv = [encabezados, ...filas].map((fila) => fila.map((valor) => {
    const texto = String(valor ?? '');
    const seguro = typeof valor === 'string' && /^[\s]*[=+\-@]/.test(texto) ? "'" + texto : texto;
    return '"' + seguro.replaceAll('"', '""') + '"';
  }).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }));
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = `UrbanSafe_${resultado.referencia.fecha_objetivo}.csv`;
  enlace.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Comparacion({ resultado, horaInicial }: { resultado: StationPrediction; horaInicial?: string }) {
  const horas = resultado.forecast;
  const [primera, setPrimera] = useState(horaInicial ?? '07:00');
  const [segunda, setSegunda] = useState(horaInicial === '18:00' ? '07:00' : '18:00');
  const referencia = resultado.referencia;

  return (
    <section aria-labelledby="escenario-titulo" className="min-w-0 space-y-5">
      <div className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="eyebrow">El día completo · 24 horas</p>
            <h2 id="escenario-titulo" className="mt-1 text-xl font-bold text-fg">{resultado.station}</h2>
            <p className="mt-1 text-sm text-muted">
              {[referencia.fecha_objetivo, systemInfo(mapSystemToBackendApi(resultado.system)).label,
                resultado.sentido && resultado.sentidos?.[resultado.sentido], 'Hora de Lima'].filter(Boolean).join(' · ')}
            </p>
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => descargarDia(resultado)}>
            <Download size={16} /> Descargar CSV
          </button>
        </div>


        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {([
            ['Hora A', primera, setPrimera],
            ['Hora B', segunda, setSegunda],
          ] as const).map(([etiqueta, seleccion, cambiar], indice) => {
            const item = horas.find((fila) => formatoHora(fila.datetime) === seleccion);
            return (
              <div key={etiqueta} className="mobility-compare-card" style={{ '--compare-color': indice === 0 ? '#3c69ce' : '#88a53d' } as CSSProperties}>
                <label className="block text-sm font-semibold text-fg">
                  <span className="mobility-compare-dot" />{etiqueta}
                  <NativeSelect mt={6} classNames={{ input: 'us-field-input' }} value={seleccion} onChange={(e) => cambiar(e.target.value)}>
                    {horas.map((fila) => {
                      const hora = formatoHora(fila.datetime);
                      return <option key={fila.datetime} value={hora}>{hora}</option>;
                    })}
                  </NativeSelect>
                </label>
                {item && (
                  <>
                    <p className={`mt-3 inline-block rounded-full px-2.5 py-1 text-xs font-semibold ${claseAforo(item.class)}`}>{etiquetaClase(item.class)}</p>
                    <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
                      <div><dt className="text-xs text-muted">Ocupación</dt><dd className="mobility-number text-fg">{ocupacion(item)}</dd></div>
                      <div><dt className="text-xs text-muted">Espera</dt><dd className="mobility-number text-fg">{espera(item)}</dd></div>
                      <div className="col-span-2">
                        <dt className="mt-2 border-t border-line pt-2 text-xs text-muted">Sugerencia para viajar</dt>
                        <dd className="mt-1 text-sm font-semibold text-fg">{etiquetaRecomendacion(item.recommendation)}</dd>
                      </div>
                    </dl>

                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><p className="eyebrow">El ritmo del día</p><h3 className="mt-1 font-semibold text-fg">Ocupación por hora</h3></div>
          <div className="flex gap-3 text-xs text-muted"><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#3c69ce]" />Hora A</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#88a53d]" />Hora B</span></div>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-muted">Compara qué tan lleno podría ir el transporte. Las horas que eliges aparecen resaltadas.</p>
        <OccupancyChart hours={horas} first={primera} second={segunda} />
      </div>
    </section>
  );
}

export default function SimulacionPage() {
  const { isAdmin } = useAuth();
  const [prioridad, setPrioridad] = useState('equilibrado');
  const [asiento, setAsiento] = useState('cualquiera');
  const [directo, setDirecto] = useState(false);
  const [estaciones, setEstaciones] = useState<Station[]>([]);
  const [sistema, setSistema] = useState<Station['system']>('metro_l1');
  const [linea, setLinea] = useState('');
  const [origenIndice, setOrigenIndice] = useState(-1);
  const [destinoIndice, setDestinoIndice] = useState(-1);
  const [hoy, setHoy] = useState('');
  const [dia, setDia] = useState('');
  const [llegada, setLlegada] = useState('08:00');
  const [cargaCatalogo, setCargaCatalogo] = useState(true);
  const [errorCatalogo, setErrorCatalogo] = useState(false);
  const [intento, setIntento] = useState(0);
  const [calculando, setCalculando] = useState(false);
  const [error, setError] = useState('');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [resultado, setResultado] = useState<StationPrediction | null>(null);

  useEffect(() => {   // la fecha de Lima se fija en el navegador para no desfasar el HTML del servidor
    const fecha = hoyLima();
    setHoy(fecha);
    setDia(fecha);
  }, []);

  const aplicar = (catalogo: Station[], nuevo: Station['system'], previa: Parameters<typeof seleccion>[2] = {}) => {
    const elegido = seleccion(catalogo, nuevo, previa);
    setSistema(nuevo);
    setLinea(elegido.linea);
    setOrigenIndice(elegido.origen);
    setDestinoIndice(elegido.destino);
  };

  useEffect(() => {
    let vigente = true;
    getStations().then((catalogo) => {
      if (!vigente) return;
      const disponibles = catalogo.filter((estacion) => Boolean(estacion.model_series));
      setEstaciones(disponibles);
      aplicar(disponibles, 'metro_l1', {
        origen: disponibles.findIndex((e) => e.system === 'metro_l1' && e.id === 'Villa El Salvador'),
        destino: disponibles.findIndex((e) => e.system === 'metro_l1' && e.id === 'Gamarra'),
      });
    }).catch(() => {
      if (vigente) setErrorCatalogo(true);
    }).finally(() => {
      if (vigente) setCargaCatalogo(false);
    });
    return () => { vigente = false; };
  }, [intento]);

  const lineas = useMemo(() => lineasDe(estaciones, sistema), [estaciones, sistema]);
  const origenes = useMemo(() => origenesDe(estaciones, sistema, linea), [estaciones, sistema, linea]);
  const origen = estaciones[origenIndice];
  const destino = estaciones[destinoIndice];
  const destinos = useMemo(() => destinosDe(origenes, origen), [origenes, origen]);

  async function simular(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!origen || !destino || calculando) return;
    setCalculando(true);
    setPlan(null);
    setResultado(null);
    setError('');
    try {
      const hora = Number(llegada.slice(0, 2));
      const troncal = sistema === 'metro_l1' || sistema === 'metropolitano';   // el destino fija el sentido
      const [nuevoPlan, datos] = await Promise.all([
        getTripPlan(origen, destino, dia, llegada, { prioridad, asiento, directo: String(directo) }),
        isAdmin ? getStationPrediction(origen, troncal ? destino.id : undefined, { dia, hora }).catch(() => null) : Promise.resolve(null),
      ]);
      setPlan(nuevoPlan);
      setResultado(datos);
    } catch (fallo: any) {
      setError(fallo?.response?.data?.error
        ?? 'No se pudo calcular este viaje. Comprueba la conexión con la API o prueba otra fecha.');
    } finally {
      setCalculando(false);
    }
  }

  const horaSalida = plan?.recomendada ?? plan?.ultima_puntual;

  return (
    <div className="mobility-workspace">
      <div className="mobility-workspace-header"><span>UrbanSafe / Simulación</span></div>
      <header className="mobility-workspace-hero mobility-sim-hero">
        <div>
          <p className="mobility-kicker"><span /> Planifica tu salida</p>
          <h1>Un mismo viaje.<br />Distintas horas.</h1>
          <p>Dinos de dónde sales, a dónde vas y a qué hora quieres llegar. Te sugerimos cuándo salir según la puntualidad, la espera y el aforo.</p>
        </div>
      </header>
      <div className="mobility-process" aria-label="Pasos de la simulación"><span><b>1</b> Arma tu viaje</span><span><b>2</b> Elige tu salida</span><span><b>3</b> Revisa el día</span></div>

      <div className="mobility-sim-grid">
      <form onSubmit={simular} className="card mobility-sim-form">
        <div className="mb-3 flex items-center gap-2"><span className="mobility-section-number">01</span><MapPin size={17} className="text-muted" /></div>
        <h2 className="text-lg font-semibold tracking-tight text-fg">Tu viaje</h2>
        <p className="mt-1.5 text-xs leading-relaxed text-muted">Elige tu recorrido y la hora a la que quieres llegar.</p>
        {errorCatalogo ? (
          <div className="mt-4 space-y-3">
            <Alert tono="danger">No pudimos cargar el catálogo.</Alert>
            <button type="button" className="btn btn-secondary" onClick={() => {
              setErrorCatalogo(false);
              setCargaCatalogo(true);
              setIntento((valor) => valor + 1);
            }}>Reintentar catálogo</button>
          </div>
        ) : (
          <fieldset disabled={cargaCatalogo || calculando} className="mt-5 grid gap-4">
            <label className="min-w-0 text-sm font-medium text-fg">
              Sistema
              <NativeSelect mt={6} classNames={{ input: 'us-field-input' }} value={sistema} onChange={(e) => aplicar(estaciones, e.target.value as Station['system'])}>
                {SISTEMAS.map((valor) => <option key={valor} value={valor}>{systemInfo(valor).label}</option>)}
              </NativeSelect>
            </label>
            {usaRuta(sistema) && (
              <label className="min-w-0 text-sm font-medium text-fg">
                Ruta
                <NativeSelect mt={6} classNames={{ input: 'us-field-input' }} value={linea} onChange={(e) => aplicar(estaciones, sistema, { linea: e.target.value })}>
                  {lineas.map((valor) => <option key={valor} value={valor}>{valor}</option>)}
                </NativeSelect>
              </label>
            )}
            <label className="min-w-0 text-sm font-medium text-fg">
              Subes en
              <NativeSelect mt={6} classNames={{ input: 'us-field-input' }} value={origenIndice}
                onChange={(e) => aplicar(estaciones, sistema, { linea, origen: Number(e.target.value), destino: destinoIndice })}>
                {origenIndice < 0 && <option value={-1}>{cargaCatalogo ? 'Cargando…' : 'Sin estaciones disponibles'}</option>}
                {origenes.map(({ estacion, indice }) => <option key={indice} value={indice}>{etiquetaEstacion(estacion)}</option>)}
              </NativeSelect>
            </label>
            <label className="min-w-0 text-sm font-medium text-fg">
              Bajas en
              <NativeSelect mt={6} classNames={{ input: 'us-field-input' }} value={destinoIndice} onChange={(e) => setDestinoIndice(Number(e.target.value))}>
                {destinoIndice < 0 && <option value={-1}>{cargaCatalogo ? 'Cargando…' : 'Sin paraderos posteriores'}</option>}
                {destinos.map(({ estacion, indice }) => <option key={indice} value={indice}>{etiquetaEstacion(estacion)}</option>)}
              </NativeSelect>
            </label>
            <label className="min-w-0 text-sm font-medium text-fg">
              Día
              <input type="date" className={CAMPO} min={PRIMER_DIA} max={hoy ? sumarDias(hoy, DIAS_ADELANTE) : undefined} required
                value={dia} onChange={(e) => setDia(e.target.value)} />
            </label>
            <label className="min-w-0 text-sm font-medium text-fg">
              Quiero llegar a las
              <input type="time" className={CAMPO} required value={llegada} onChange={(e) => setLlegada(e.target.value)} />
            </label>
            <label className="min-w-0 text-sm font-medium text-fg">
              ¿Qué priorizas?
              <NativeSelect mt={6} classNames={{ input: 'us-field-input' }} value={prioridad} onChange={(e) => setPrioridad(e.target.value)}>
                <option value="equilibrado">Equilibrar tiempo y comodidad</option>
                <option value="rapidez">Tardar menos en el viaje</option>
                <option value="comodidad">Viajar con menos gente</option>
              </NativeSelect>
            </label>
            <label className="min-w-0 text-sm font-medium text-fg">
              Para viajar
              <NativeSelect mt={6} classNames={{ input: 'us-field-input' }} value={asiento} onChange={(e) => setAsiento(e.target.value)}>
                <option value="cualquiera">Puedo ir de pie o sentado</option>
                <option value="sentado">Buscar opciones con asientos</option>
              </NativeSelect>
              <span className="mt-1.5 block text-xs font-normal text-muted">Los asientos son estimados; pueden variar.</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-fg">
              <input type="checkbox" checked={directo} onChange={(e) => setDirecto(e.target.checked)} />
              Sin transbordos
            </label>
            <button type="submit" className="btn btn-primary mt-1" disabled={origenIndice < 0 || destinoIndice < 0 || !dia}>
              {calculando && <Spinner size={16} />}
              {calculando ? 'Calculando…' : 'Calcular mi salida'}
            </button>
          </fieldset>
        )}
        {!cargaCatalogo && origenIndice >= 0 && destinoIndice < 0 && (
          <p className="mt-3 text-xs leading-relaxed text-muted">Ese paradero es el último de su sentido: elige otro punto de subida.</p>
        )}
        {calculando && <p role="status" className="sr-only">Calculando tu salida</p>}
        {error && <Alert tono="danger" className="mt-4">{error}</Alert>}
      </form>

      {plan ? (
        <div className="min-w-0 space-y-5">
          <PlanSalida key={`${plan.origen.id}-${plan.destino.id}-${plan.dia}-${plan.llegada_limite}`} plan={plan}>
          {isAdmin && resultado && <Comparacion key={`${resultado.station}-${plan.dia}-${horaSalida}`} resultado={resultado}
            horaInicial={horaSalida ? `${horaSalida.slice(0, 2)}:00` : undefined} />}
          </PlanSalida>
        </div>
      ) : (
        <section className="mobility-sim-empty" aria-label="Cómo comenzar">
          <span className="mobility-sim-empty-icon"><ChartColumn size={25} strokeWidth={1.3} aria-hidden="true" /></span>
          <h2>{calculando ? 'Estamos armando tu viaje.' : '¿A qué hora te conviene salir?'}</h2>
          <p>{calculando ? 'Buscando una hora de salida para tu viaje.' : 'Elige tu viaje y pulsa «Calcular mi salida» para ver cuándo salir y a qué hora llegarías.'}</p>
          <span className="mt-5 rounded-full border border-line px-3 py-1.5 text-xs text-muted">Estimaciones con datos de la ATU</span>
        </section>
      )}
      </div>
    </div>
  );
}
