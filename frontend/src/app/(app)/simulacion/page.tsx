'use client';

import { useEffect, useState, type FormEvent, type CSSProperties } from 'react';
import Link from 'next/link';
import { ArrowUpRight, ChartColumn, Download, MapPin } from 'lucide-react';
import Alert from '@/components/Alert';
import MobilityIllustration from '@/components/MobilityIllustration';
import { Spinner } from '@/components/Spinner';
import { claseAforo, etiquetaClase, etiquetaRecomendacion, formatoHora } from '@/lib/aforo';
import { getStationPrediction, getStations, mapSystemToBackendApi } from '@/lib/services';
import { systemInfo } from '@/lib/systems';
import type { PredictionItem, Station, StationPrediction } from '@/lib/types';

const PRIMER_DIA = '2025-01-29';
const ULTIMO_DIA = '2025-12-31';
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

function nombreEstacion(estacion: Station) {
  if (estacion.system === 'corredores') return `${estacion.name} · ${estacion.model_series} · ${estacion.id}`;
  if (estacion.system === 'alimentadores') return `${estacion.name} · ${estacion.model_series}`;
  return estacion.name;
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

function Comparacion({ resultado }: { resultado: StationPrediction }) {
  const horas = resultado.forecast;
  const [primera, setPrimera] = useState('07:00');
  const [segunda, setSegunda] = useState('18:00');
  const maxima = Math.max(100, ...horas.map((item) =>
    item.class === 'Sin_servicio' ? 0 : Math.ceil((item.crowding ?? 0) * 4) * 25
  ));
  const referencia = resultado.referencia;

  return (
    <section aria-labelledby="escenario-titulo" className="min-w-0 space-y-5">
      <div className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="eyebrow">Tu escenario · 24 horas</p>
            <h2 id="escenario-titulo" className="mt-1 text-xl font-bold text-fg">{resultado.station}</h2>
            <p className="mt-1 text-sm text-muted">
              {referencia.fecha_objetivo} · {systemInfo(mapSystemToBackendApi(resultado.system)).label} · Hora de Lima
            </p>
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => descargarDia(resultado)}>
            <Download size={16} /> Descargar CSV
          </button>
        </div>
        <p className="mt-4 rounded-lg bg-surface-2 p-3 text-xs leading-relaxed text-muted">
          Referencia ATU {referencia.fecha_referencia_datos} · {referencia.criterio}
        </p>

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
                  <select className={CAMPO} value={seleccion} onChange={(e) => cambiar(e.target.value)}>
                    {horas.map((fila) => {
                      const hora = formatoHora(fila.datetime);
                      return <option key={fila.datetime} value={hora}>{hora}</option>;
                    })}
                  </select>
                </label>
                {item && (
                  <>
                    <p className={`mt-3 inline-block rounded-full px-2.5 py-1 text-xs font-semibold ${claseAforo(item.class)}`}>{etiquetaClase(item.class)}</p>
                    <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
                      <div><dt className="text-xs text-muted">Ocupación</dt><dd className="mobility-number text-fg">{ocupacion(item)}</dd></div>
                      <div><dt className="text-xs text-muted">Espera</dt><dd className="mobility-number text-fg">{espera(item)}</dd></div>
                      <div className="col-span-2">
                        <dt className="mt-2 border-t border-line pt-2 text-xs text-muted">Recomendación del modelo</dt>
                        <dd className="mt-1 text-sm font-semibold text-fg">{etiquetaRecomendacion(item.recommendation)}</dd>
                      </div>
                    </dl>
                    <p className="mt-3 text-xs text-muted">
                      {[item.sentido, item.model ?? resultado.model].filter(Boolean).join(' · ')}
                    </p>
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
        <p className="mt-2 text-xs leading-relaxed text-muted">Porcentaje de la capacidad al salir del paradero. Las dos horas elegidas se destacan; una raya indica falta de servicio o estimación.</p>
        <div className="mt-5" aria-hidden="true">
          <div className="flex justify-between text-xs text-muted"><span>{maxima}%</span><span>Hora de Lima</span></div>
          <div className="mobility-chart">
            <div className="mobility-chart-grid"><span /><span /><span /></div>
            <div className="mobility-chart-bars">
            {horas.map((item) => {
              const hora = formatoHora(item.datetime);
              const marcado = hora === primera && hora === segunda ? 'both' : hora === primera ? 'a' : hora === segunda ? 'b' : undefined;
              const tieneDato = item.class !== 'Sin_servicio' && item.crowding != null;
              const alto = tieneDato ? Math.max(1, item.crowding! * 100 / maxima * 100) : 0;
              return (
                <div key={item.datetime} title={`${hora} · ${ocupacion(item)}`}
                  className="mobility-chart-bar" data-hour={marcado} data-empty={!tieneDato}
                  style={tieneDato ? { height: `${alto}%` } : undefined}
                />
              );
            })}
            </div>
          </div>
          <div className="mt-1 flex justify-between text-xs tabular-nums text-muted">
            <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:00</span>
          </div>
        </div>
        <details className="mt-4 border-t border-line pt-3">
          <summary className="cursor-pointer text-sm font-semibold text-brand">Ver tabla de las 24 horas</summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-line text-muted">
                <th scope="col" className="py-2 pr-3">Hora</th><th scope="col" className="pr-3">Aforo</th>
                <th scope="col" className="pr-3">Ocupación</th><th scope="col">Espera</th>
              </tr></thead>
              <tbody>{horas.map((item) => (
                <tr key={item.datetime} className="border-b border-line/60 text-fg">
                  <th scope="row" className="py-2 pr-3 font-medium">{formatoHora(item.datetime)}</th>
                  <td className="pr-3">{etiquetaClase(item.class)}</td>
                  <td className="pr-3">{ocupacion(item)}</td><td>{espera(item)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </details>
      </div>
    </section>
  );
}

export default function SimulacionPage() {
  const [estaciones, setEstaciones] = useState<Station[]>([]);
  const [sistema, setSistema] = useState<Station['system']>('metro_l1');
  const [estacionIndice, setEstacionIndice] = useState(-1);
  const [dia, setDia] = useState('2025-11-17');
  const [cargaCatalogo, setCargaCatalogo] = useState(true);
  const [errorCatalogo, setErrorCatalogo] = useState(false);
  const [intento, setIntento] = useState(0);
  const [calculando, setCalculando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState<StationPrediction | null>(null);

  useEffect(() => {
    let vigente = true;
    getStations().then((catalogo) => {
      if (!vigente) return;
      const disponibles = catalogo.filter((estacion) => Boolean(estacion.model_series));
      setEstaciones(disponibles);
      const inicio = disponibles.findIndex((estacion) => estacion.id === 'Villa El Salvador' && estacion.system === 'metro_l1');
      setEstacionIndice(inicio >= 0 ? inicio : disponibles.findIndex((estacion) => estacion.system === 'metro_l1'));
    }).catch(() => {
      if (vigente) setErrorCatalogo(true);
    }).finally(() => {
      if (vigente) setCargaCatalogo(false);
    });
    return () => { vigente = false; };
  }, [intento]);

  async function simular(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const estacion = estaciones[estacionIndice];
    if (!estacion || calculando) return;
    setCalculando(true);
    setResultado(null);
    setError('');
    try {
      const datos = await getStationPrediction(estacion, undefined, { dia, hora: 7 });
      if (datos) setResultado(datos);
      else setError('Este paradero no tiene pronóstico disponible. Prueba con otra estación.');
    } catch {
      setError('No se pudo calcular este escenario. Comprueba la conexión con la API o prueba otra fecha.');
    } finally {
      setCalculando(false);
    }
  }

  return (
    <div className="mobility-workspace">
      <div className="mobility-workspace-header"><span>UrbanSafe / Simulación</span><Link href="/destinations">Comparar destinos <ArrowUpRight size={15} /></Link></div>
      <header className="mobility-workspace-hero">
        <div>
          <p className="mobility-kicker"><span /> Laboratorio de movilidad</p>
          <h1>Un mismo viaje.<br /><em>Distintas horas.</em></h1>
          <p>Elige una estación y un día de 2025. Compara dos horas para entender cómo cambian el aforo, la espera y la recomendación.</p>
        </div>
        <MobilityIllustration className="mobility-sim-visual" />
      </header>
      <div className="mobility-process" aria-label="Pasos de la simulación"><span><b>1</b> Prepara el escenario</span><span><b>2</b> Compara dos horas</span><span><b>3</b> Revisa y descarga</span></div>

      <div className="mobility-sim-grid">
      <form onSubmit={simular} className="card mobility-sim-form">
        <div className="mb-3 flex items-center gap-2"><span className="mobility-section-number">01</span><MapPin size={17} className="text-muted" /></div>
        <h2 className="text-lg font-semibold tracking-tight text-fg">Tu escenario</h2>
        <p className="mt-1.5 text-xs leading-relaxed text-muted">Usa los modelos del proyecto y datos históricos ATU. No muestra el aforo en vivo.</p>
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
              <select className={CAMPO} value={sistema} onChange={(e) => {
                const elegido = e.target.value as Station['system'];
                setSistema(elegido);
                setEstacionIndice(estaciones.findIndex((estacion) => estacion.system === elegido));
              }}>
                {SISTEMAS.map((valor) => <option key={valor} value={valor}>{systemInfo(valor).label}</option>)}
              </select>
            </label>
            <label className="min-w-0 text-sm font-medium text-fg">
              Estación o paradero
              <select className={CAMPO} value={estacionIndice} onChange={(e) => setEstacionIndice(Number(e.target.value))}>
                {estacionIndice < 0 && <option value={-1}>{cargaCatalogo ? 'Cargando…' : 'Sin estaciones disponibles'}</option>}
                {estaciones.map((estacion, indice) => estacion.system === sistema && (
                  <option key={indice} value={indice}>{nombreEstacion(estacion)}</option>
                ))}
              </select>
            </label>
            <label className="min-w-0 text-sm font-medium text-fg">
              Día de 2025
              <input type="date" className={CAMPO} min={PRIMER_DIA} max={ULTIMO_DIA} required
                value={dia} onChange={(e) => setDia(e.target.value)} />
            </label>
            <button type="submit" className="btn btn-primary mt-1" disabled={estacionIndice < 0}>
              {calculando && <Spinner size={16} />}
              {calculando ? 'Calculando…' : 'Simular el día'}
            </button>
          </fieldset>
        )}
        {calculando && <p role="status" className="sr-only">Calculando escenario histórico</p>}
        {error && <Alert tono="danger" className="mt-4">{error}</Alert>}
      </form>

      {resultado ? <Comparacion resultado={resultado} /> : (
        <section className="mobility-sim-empty" aria-label="Cómo comenzar">
          <span className="mobility-sim-empty-icon"><ChartColumn size={38} strokeWidth={1.3} aria-hidden="true" /></span>
          <h2>{calculando ? 'Estamos leyendo el día.' : 'Un día completo, hora por hora.'}</h2>
          <p>{calculando ? 'Calculando el escenario con los modelos y datos disponibles del proyecto.' : 'Prepara el escenario y pulsa «Simular el día». Aquí verás dos horarios, la gráfica de ocupación y la tabla completa.'}</p>
          <span className="mt-5 rounded-full border border-line px-3 py-1.5 text-xs text-muted">Estimaciones con datos ATU de 2025</span>
        </section>
      )}
      </div>
    </div>
  );
}
