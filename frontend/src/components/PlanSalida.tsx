'use client';

import { useState, type ReactNode } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Tabs } from '@mantine/core';
import { ArrowRight, ExternalLink } from 'lucide-react';
import Alert from '@/components/Alert';
import { claseAforo, etiquetaClase, textoOcupacion } from '@/lib/aforo';
import type { OpcionSalida, PlanSalida as Plan, ServicioPlan } from '@/lib/types';

const minutos = (valor: number) => `${Math.max(1, Math.round(valor))} min`;
const margen = (o: OpcionSalida) => (o.margen_min >= 0 ? `${Math.round(o.margen_min)} min antes` : `${Math.round(-o.margen_min)} min tarde`);


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

        </div>
        <div className="rounded-xl bg-surface-2 px-3 py-2.5">
          <dt className="text-xs text-muted">Espera</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-fg">{minutos(opcion.espera_min)}</dd>

        </div>
        <div className="rounded-xl bg-surface-2 px-3 py-2.5">
          <dt className="text-xs text-muted">A bordo</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-fg">{minutos(opcion.viaje_min)}</dd>
          <dd className="text-xs text-muted">{opcion.tramos && opcion.tramos.length > 1 ? 'con un transbordo' : 'viaje directo'}</dd>
        </div>
      </dl>

      {opcion.tramos && (
        <ol className="mt-4 space-y-2 text-sm text-fg">
          {opcion.tramos.map((tramo, indice) => tramo.servicios && tramo.servicios.length > 1 ? (
            <li key={`${tramo.servicio}-${tramo.sube}`} className="rounded-xl border border-line px-3 py-2.5">
              <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="font-semibold">Sube al primero que pase</span>
                <span className="inline-flex items-center gap-1.5 text-muted">{tramo.sube} <ArrowRight size={14} aria-label="hasta" /> {tramo.baja}</span>
              </p>
              <ul className="mt-2 space-y-1">
                {tramo.servicios.map((s, i) => (
                  <li key={s.nombre} className="flex flex-wrap items-baseline justify-between gap-x-3 text-xs text-muted">
                    <span><strong className="text-sm font-semibold text-fg">{s.nombre}</strong>{i === 0 && ' · el más rápido'}</span>
                    <span className="tabular-nums">
                      {minutos(s.viaje_min)} a bordo · {s.paradas_intermedias === 0 ? 'sin paradas intermedias' : `${s.paradas_intermedias} paradas`} · cada {minutos(s.intervalo_min)}
                    </span>
                  </li>
                ))}
              </ul>
            </li>
          ) : (
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

      <p className="mt-4 text-xs text-muted">Los tiempos y la ocupación son estimados; pueden variar durante tu viaje.</p>

    </div>
  );
}

function Servicio({ servicio, hora }: { servicio: ServicioPlan; hora: string }) {
  const estado = servicio.opera === null
    ? { texto: servicio.horario ? 'Horario por confirmar' : 'Horario no publicado', clase: 'bg-surface-2 text-muted' }
    : servicio.opera
      ? { texto: `Circula a las ${hora}`, clase: 'bg-ok/12 text-ok' }
      : { texto: `No circula a las ${hora}`, clase: 'bg-surface-2 text-muted' };
  return (
    <li className="rounded-xl border border-line px-3.5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-fg">
          {servicio.nombre}
          {servicio.recomendado && <span className="ml-2 rounded-full bg-brand-soft px-2 py-0.5 text-xs font-semibold text-brand">Te sirve</span>}
        </span>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${estado.clase}`}>{estado.texto}</span>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-muted">
        {[
          servicio.horario ? `Horario del día: ${servicio.horario}` : 'La fuente no publica su horario',
          servicio.intervalo_min != null ? `intervalo de referencia: ${minutos(servicio.intervalo_min)}` : 'frecuencia no publicada',
          servicio.viaje_min != null && `${minutos(servicio.viaje_min)} a bordo`,
          servicio.paradas_intermedias != null && (servicio.paradas_intermedias === 0 ? 'sin paradas intermedias' : `${servicio.paradas_intermedias} paradas intermedias`),
        ].filter(Boolean).join(' · ')}
      </p>

      {servicio.url && <a href={servicio.url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand hover:underline">Consultar la fuente del horario <ExternalLink size={12} aria-label="(se abre en otra pestaña)" /></a>}
    </li>
  );
}

export default function PlanSalida({ plan, children }: { plan: Plan; children?: ReactNode }) {
  const { isAdmin } = useAuth();
  const [pestana, setPestana] = useState<string | null>('resumen');
  const [elegida, setElegida] = useState(plan.recomendada ?? plan.ultima_puntual);
  const opcion = plan.opciones.find((o) => o.salida === elegida);
  const horaServicios = opcion?.salida ?? plan.recomendada ?? plan.llegada_limite;

  return (
    <section aria-labelledby="plan-titulo" className="min-w-0 space-y-5">
      <h2 id="plan-titulo" className="sr-only">Tu salida para llegar a las {plan.llegada_limite}</h2>

      <Tabs value={pestana} onChange={setPestana} keepMounted={false} className="mobility-result-tabs">
        <Tabs.List aria-label="Resultados de tu viaje">
          <Tabs.Tab value="resumen">Tu salida</Tabs.Tab>
          <Tabs.Tab value="alternativas">Otras horas</Tabs.Tab>
          <Tabs.Tab value="servicios">Servicios</Tabs.Tab>
          {isAdmin && children && <Tabs.Tab value="dia">Durante el día</Tabs.Tab>}
        </Tabs.List>
        <Tabs.Panel value="resumen" pt="md">
      {opcion ? <Detalle plan={plan} opcion={opcion} /> : <Alert tono="warn">{plan.motivo}</Alert>}

        </Tabs.Panel>
        <Tabs.Panel value="alternativas" pt="md">
      {plan.opciones.length > 0 ? (
        <div className="card p-5 sm:p-6">
          <p className="eyebrow">Otras salidas</p>
          <h3 className="mt-1 font-semibold text-fg">Elige otra hora para comparar</h3>
          <p className="mt-2 text-xs leading-relaxed text-muted">Toca una hora para ver cómo cambia tu viaje.</p>
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
                        <button type="button" onClick={() => { setElegida(o.salida); setPestana('resumen'); }} aria-pressed={activa}
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
      ) : <p className="p-5 text-sm text-muted">No hay otras salidas disponibles para este viaje.</p>}
        </Tabs.Panel>
        <Tabs.Panel value="servicios" pt="md">
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
        <p className="mt-4 text-xs leading-relaxed text-muted">Horarios publicados por la ATU. Las frecuencias son de referencia y la espera puede variar.</p>

      </div>
        </Tabs.Panel>
        {isAdmin && children && <Tabs.Panel value="dia" pt="md">{children}</Tabs.Panel>}
      </Tabs>
    </section>
  );
}
