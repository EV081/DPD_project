'use client';

import { useState } from 'react';
import { ArrowRight, ExternalLink, Moon, Sun } from 'lucide-react';
import Alert from '@/components/Alert';
import { claseAforo, etiquetaClase, textoOcupacion } from '@/lib/aforo';
import type { OpcionSalida, PlanSalida as Plan, ServicioPlan } from '@/lib/types';

const minutos = (valor: number) => `${Math.max(1, Math.round(valor))} min`;
const margen = (o: OpcionSalida) => (o.margen_min >= 0 ? `${Math.round(o.margen_min)} min antes` : `${Math.round(-o.margen_min)} min tarde`);
const esNoche = (hhmm: string) => { const h = Number(hhmm.slice(0, 2)); return h >= 18 || h < 6; };

const ESTADO: Record<OpcionSalida['estado'], { texto: string; corto: string; clase: string }> = {
  con_margen: { texto: 'A tiempo, con margen', corto: 'Con margen', clase: 'bg-ok/12 text-ok' },
  justo: { texto: 'A tiempo, justo', corto: 'Justo', clase: 'bg-warn/12 text-warn' },
  tarde: { texto: 'Llega tarde', corto: 'Tarde', clase: 'bg-danger/12 text-danger' },
};

function Estado({ estado, corto = false }: { estado: OpcionSalida['estado']; corto?: boolean }) {
  const { texto, corto: breve, clase } = ESTADO[estado];
  return <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${clase}`}>{corto ? breve : texto}</span>;
}

function etiquetas(plan: Plan, o: OpcionSalida): string[] {
  return [
    o.salida === plan.recomendada && 'Recomendada',
    o.salida === plan.ultima_puntual && o.salida !== plan.recomendada && 'Última a tiempo',
    o.salida === plan.mas_comoda && o.salida !== plan.recomendada && 'Más cómoda',
  ].filter(Boolean) as string[];
}

function Detalle({ plan, opcion }: { plan: Plan; opcion: OpcionSalida }) {
  const recomendada = opcion.salida === plan.recomendada;
  const noche = [opcion.franja === 'noche', esNoche(opcion.llegada)];
  const Franja = noche[0] || noche[1] ? Moon : Sun;
  return (
    <div className="card p-5 sm:p-6" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">{recomendada ? 'Salida recomendada' : 'Salida elegida'}</p>
          <p className="mt-1 text-4xl font-bold tracking-tight tabular-nums text-fg">{opcion.salida}</p>
          <p className="mt-1 text-sm text-muted">
            Hora para estar en {plan.origen.name}{plan.sentido ? ` · ${plan.sentido}` : ''}
          </p>
        </div>
        <Estado estado={opcion.estado} />
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl bg-surface-2 px-3 py-2.5">
          <dt className="text-xs text-muted">Llegas a {plan.destino.name}</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-fg">{opcion.llegada}</dd>
          <dd className="text-xs text-muted">{margen(opcion)} de las {plan.llegada_limite}</dd>
        </div>
        <div className="rounded-xl bg-surface-2 px-3 py-2.5">
          <dt className="text-xs text-muted">Aforo al subir</dt>
          <dd className={`mt-1 text-lg font-semibold ${claseAforo(opcion.clase)}`}>{etiquetaClase(opcion.clase)}</dd>
          <dd className="text-xs text-muted">{textoOcupacion(opcion.ocupacion)} de ocupación (aprox.)</dd>
        </div>
        <div className="rounded-xl bg-surface-2 px-3 py-2.5">
          <dt className="text-xs text-muted">Espera</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-fg">{minutos(opcion.espera_min)}</dd>
          <dd className="text-xs text-muted">pasa cada {minutos(opcion.intervalo_min)}</dd>
        </div>
        <div className="rounded-xl bg-surface-2 px-3 py-2.5">
          <dt className="text-xs text-muted">A bordo</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-fg">{minutos(opcion.viaje_min)}</dd>
          <dd className="text-xs text-muted">{opcion.tramos && opcion.tramos.length > 1 ? 'con un transbordo' : 'viaje directo'}</dd>
        </div>
      </dl>

      {opcion.tramos && (
        <ol className="mt-4 space-y-2 text-sm text-fg">
          {opcion.tramos.map((tramo, indice) => (
            <li key={`${tramo.servicio}-${tramo.sube}`} className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl border border-line px-3 py-2.5">
              <span className="font-semibold">{opcion.tramos!.length > 1 ? `${indice + 1}. ` : ''}{tramo.servicio}</span>
              <span className="inline-flex items-center gap-1.5 text-muted">{tramo.sube} <ArrowRight size={14} aria-label="hasta" /> {tramo.baja}</span>
              <span className="text-xs text-muted">
                · {minutos(tramo.viaje_min)} a bordo · {tramo.paradas_intermedias === 0 ? 'sin paradas intermedias' : `${tramo.paradas_intermedias} paradas intermedias`}
                {!tramo.frecuencia_publicada && ' · frecuencia típica'}
              </span>
            </li>
          ))}
        </ol>
      )}

      {recomendada && <p className="mt-4 text-sm leading-relaxed text-fg">{plan.motivo}</p>}

      {plan.seguridad && (
        <p className="mt-4 flex gap-2 border-t border-line pt-4 text-xs leading-relaxed text-muted">
          <Franja size={16} className="mt-0.5 shrink-0" aria-hidden />
          <span>
            <strong className="font-semibold text-fg">Sales de {noche[0] ? 'noche' : 'día'} y llegas de {noche[1] ? 'noche' : 'día'}.</strong>{' '}
            {plan.seguridad.nota}
          </span>
        </p>
      )}
    </div>
  );
}

function Servicio({ servicio, hora }: { servicio: ServicioPlan; hora: string }) {
  const estado = servicio.opera === null
    ? { texto: 'Horario no publicado', clase: 'bg-surface-2 text-muted' }
    : servicio.opera
      ? { texto: `Circula a las ${hora}`, clase: 'bg-ok/12 text-ok' }
      : { texto: `No circula a las ${hora}`, clase: 'bg-surface-2 text-muted' };
  return (
    <li className="rounded-xl border border-line px-3.5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-fg">{servicio.nombre}</span>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${estado.clase}`}>{estado.texto}</span>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-muted">
        {[
          servicio.horario ? `Horario del día: ${servicio.horario}` : 'La fuente no publica su horario',
          servicio.intervalo_min != null ? `cada ${minutos(servicio.intervalo_min)}` : 'frecuencia no publicada',
          servicio.viaje_min != null && `${minutos(servicio.viaje_min)} a bordo`,
          servicio.paradas_intermedias != null && (servicio.paradas_intermedias === 0 ? 'sin paradas intermedias' : `${servicio.paradas_intermedias} paradas intermedias`),
        ].filter(Boolean).join(' · ')}
      </p>
      {servicio.notas.map((nota) => <p key={nota} className="mt-1 text-xs leading-relaxed text-muted">{nota}</p>)}
    </li>
  );
}

export default function PlanSalida({ plan }: { plan: Plan }) {
  const [elegida, setElegida] = useState(plan.recomendada ?? plan.ultima_puntual);
  const opcion = plan.opciones.find((o) => o.salida === elegida);
  const horaServicios = opcion?.salida ?? plan.recomendada ?? plan.llegada_limite;

  return (
    <section aria-labelledby="plan-titulo" className="min-w-0 space-y-5">
      <h2 id="plan-titulo" className="sr-only">Tu salida para llegar a las {plan.llegada_limite}</h2>

      {opcion ? <Detalle plan={plan} opcion={opcion} /> : <Alert tono="warn">{plan.motivo}</Alert>}

      {plan.opciones.length > 0 && (
        <div className="card p-5 sm:p-6">
          <p className="eyebrow">Otras salidas</p>
          <h3 className="mt-1 font-semibold text-fg">Cada 10 minutos, de la más temprana a la más tardía</h3>
          <p className="mt-2 text-xs leading-relaxed text-muted">Toca una hora para ver su detalle. «Con margen» significa que llegas a tiempo aunque pierdas un vehículo.</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Salidas posibles con su hora de llegada, margen, aforo, espera y tiempo a bordo</caption>
              <thead>
                <tr className="border-b border-line text-xs text-muted">
                  <th scope="col" className="py-2 pr-3 font-medium">Sales</th>
                  <th scope="col" className="pr-3 font-medium">Llegas</th>
                  <th scope="col" className="pr-3 font-medium">Margen</th>
                  <th scope="col" className="pr-3 font-medium">Aforo</th>
                  <th scope="col" className="hidden pr-3 font-medium sm:table-cell">Espera</th>
                  <th scope="col" className="hidden font-medium sm:table-cell">A bordo</th>
                </tr>
              </thead>
              <tbody>
                {plan.opciones.map((o) => {
                  const marcas = etiquetas(plan, o);
                  const activa = o.salida === elegida;
                  return (
                    <tr key={o.salida} className={`border-b border-line/60 ${activa ? 'bg-brand-soft' : ''}`}>
                      <th scope="row" className="py-2 pl-2 pr-2 font-normal">
                        <button type="button" onClick={() => setElegida(o.salida)} aria-pressed={activa}
                          className="rounded-md font-semibold tabular-nums text-brand underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-brand">
                          {o.salida}
                        </button>
                        {marcas.map((marca) => <span key={marca} className="block text-xs text-muted">{marca}</span>)}
                      </th>
                      <td className="pr-3 tabular-nums text-fg">{o.llegada}</td>
                      <td className="pr-3"><Estado estado={o.estado} corto /><span className="block text-xs text-muted">{margen(o)}</span></td>
                      <td className={`pr-3 font-medium ${claseAforo(o.clase)}`}>{etiquetaClase(o.clase)}<span className="block text-xs font-normal text-muted">{textoOcupacion(o.ocupacion)}</span></td>
                      <td className="hidden pr-3 tabular-nums text-fg sm:table-cell">{minutos(o.espera_min)}</td>
                      <td className="hidden tabular-nums text-fg sm:table-cell">{minutos(o.viaje_min)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card p-5 sm:p-6">
        <p className="eyebrow">Qué te lleva</p>
        <h3 className="mt-1 font-semibold text-fg">
          {plan.servicios.length > 1 ? `Servicios directos entre ${plan.origen.name} y ${plan.destino.name}` : 'Horario del servicio'}
        </h3>
        {plan.servicios.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {plan.servicios.map((servicio) => <Servicio key={servicio.nombre} servicio={servicio} hora={horaServicios} />)}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">Ningún servicio une estas dos estaciones sin transbordo.</p>
        )}
        <p className="mt-4 text-xs leading-relaxed text-muted">
          Horarios y frecuencias:{' '}
          <a href={plan.fuente_horarios.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-brand hover:underline">
            {plan.fuente_horarios.nombre} <ExternalLink size={12} aria-label="(se abre en otra pestaña)" />
          </a>{' '}
          (consultado el {plan.fuente_horarios.consultado}). {plan.fuente_horarios.aviso}
        </p>
        <details className="mt-3 border-t border-line pt-3">
          <summary className="cursor-pointer text-sm font-semibold text-brand">Cómo se calcula</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-relaxed text-muted">
            {plan.supuestos.map((supuesto) => <li key={supuesto}>{supuesto}</li>)}
          </ul>
        </details>
      </div>
    </section>
  );
}
