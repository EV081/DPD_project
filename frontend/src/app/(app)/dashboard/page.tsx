'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, RefreshCw } from 'lucide-react';
import Alert from '@/components/Alert';
import { Skeleton } from '@/components/Spinner';
import { ChartCard, Cifra, Columnas, BarrasH, DECIMAL, ENTERO, Estado, LineasSistemas, SISTEMAS_MODELO, TablaDatos, claveSistema, fechaCorta, infoSistema, type Nivel } from '@/components/dashboard/viz';
import { getDashboard, type Dashboard, type EjecucionPipeline } from '@/lib/admin';
import { errorMessage } from '@/lib/client';

const REFRESCO_MS = 60_000;
const PORCENTAJE = new Intl.NumberFormat('es-PE', { style: 'percent', maximumFractionDigits: 1 });
const FECHA_HORA = new Intl.DateTimeFormat('es-PE', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima' });
const fechaHora = (iso: string | null) => (iso ? FECHA_HORA.format(new Date(iso)) : '—');

const ESTADO_JOB: Record<string, { nivel: Nivel; texto: string }> = {
  ok: { nivel: 'ok', texto: 'Correcto' },
  sin_datos: { nivel: 'muted', texto: 'Sin datos nuevos' },
  en_curso: { nivel: 'warn', texto: 'En curso' },
  error: { nivel: 'error', texto: 'Con error' },
};
const estadoJob = (e: string) => ESTADO_JOB[e] ?? { nivel: 'muted' as Nivel, texto: e };

function Seccion({ titulo, descripcion, children }: { titulo: string; descripcion?: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3" aria-labelledby={`sec-${titulo}`}>
      <div>
        <h2 id={`sec-${titulo}`} className="text-base font-bold text-fg">{titulo}</h2>
        {descripcion && <p className="text-xs text-muted">{descripcion}</p>}
      </div>
      {children}
    </section>
  );
}

function Fila({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return <div className="flex items-center justify-between gap-3 border-t border-line py-2.5 first:border-t-0"><span className="text-sm text-fg">{etiqueta}</span><span className="text-right">{children}</span></div>;
}

function Cargando() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Cargando el panel">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      <div className="grid gap-3 lg:grid-cols-2"><Skeleton className="h-64" /><Skeleton className="h-64" /></div>
      <Skeleton className="h-72" />
    </div>
  );
}

export default function DashboardPage() {
  const [datos, setDatos] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actualizando, setActualizando] = useState(false);

  const cargar = useCallback(async () => {
    setActualizando(true);
    try {
      setDatos(await getDashboard());
      setError(null);
    } catch (e) {
      setError(errorMessage(e, 'No se pudo cargar el panel.'));
    } finally {
      setActualizando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
    const id = setInterval(() => { if (!document.hidden) void cargar(); }, REFRESCO_MS);
    return () => clearInterval(id);
  }, [cargar]);

  return (
    <div className="viz-root mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Administración</p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight text-fg"><Activity size={22} aria-hidden className="text-brand" /> Panel operacional</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">Estado de la API, los modelos y los procesos programados, con el uso de la app. Todo es agregado: no se muestran personas ni reportes individuales.</p>
        </div>
        <div className="flex items-center gap-3">
          {datos && <span className="text-xs text-muted" aria-live="polite">Actualizado {fechaHora(datos.generado_en)}</span>}
          <button type="button" onClick={() => void cargar()} disabled={actualizando} className="btn" aria-label="Actualizar el panel">
            <RefreshCw size={16} aria-hidden className={actualizando ? 'animate-spin motion-reduce:animate-none' : ''} /> Actualizar
          </button>
        </div>
      </header>

      {error && <Alert tono="danger">{error}</Alert>}
      {!datos && !error && <Cargando />}
      {datos && <Contenido d={datos} desactualizado={actualizando || !!error} />}
    </div>
  );
}

function Contenido({ d, desactualizado }: { d: Dashboard; desactualizado: boolean }) {
  const { salud, uso, monitoreo, pipelines, eje2, modelos, feedback } = d;
  const abordajes14 = uso.abordajes_por_dia.reduce((a, x) => a + x.n, 0);
  const alertas = monitoreo.alertas_activas.length;

  /* Semanas en columnas, un valor por sistema: forma que pide el gráfico de líneas */
  const { semanas, sistemasMon } = useMemo(() => {
    const porSemana = new Map<string, Record<string, unknown>>();
    const sistemas = new Set<string>();
    for (const f of [...monitoreo.semanal].reverse()) {
      const k = claveSistema(f.sistema);
      sistemas.add(k);
      const fila = porSemana.get(f.semana) ?? { semana: f.semana };
      fila[k] = f.eta_mae_min; fila[`${k}__aforo`] = f.aforo_acierto;
      porSemana.set(f.semana, fila);
    }
    const orden = Object.keys(SISTEMAS_MODELO);       // orden fijo de la paleta validada: el color sigue al sistema, no a su posición
    return { semanas: [...porSemana.values()], sistemasMon: [...sistemas].sort((a, b) => orden.indexOf(a) - orden.indexOf(b)) };
  }, [monitoreo.semanal]);
  const filasAforo = useMemo<Record<string, unknown>[]>(() => semanas.map((f) => ({ semana: f.semana, ...Object.fromEntries(sistemasMon.map((s) => [s, f[`${s}__aforo`] ?? null])) })), [semanas, sistemasMon]);

  const sinMonitoreo = 'Aún no hay métricas semanales. Se generan con el comando pipeline-semanal cuando hay respuestas de «Ya abordé».';
  const feedbackPorModo = Object.entries(feedback.por_modo_datos);

  return (
    <div className="viz-refetch space-y-8" data-stale={desactualizado}>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Cifra etiqueta="Cuentas registradas" valor={ENTERO.format(uso.usuarios_total)} detalle={`${ENTERO.format(uso.usuarios_nuevos_7d)} nuevas en 7 días`} />
        <Cifra etiqueta="Abordajes registrados (14 días)" valor={ENTERO.format(abordajes14)} detalle="botón «Ya abordé»" />
        <Cifra etiqueta="Respuestas de feedback" valor={ENTERO.format(uso.feedback_total)} detalle={`${ENTERO.format(uso.feedback_7d)} en 7 días`} />
        <Cifra etiqueta="Alertas del modelo" valor={ENTERO.format(alertas)} nivel={alertas ? 'warn' : 'ok'} detalle={alertas ? 'en la última semana' : 'sin alertas'} />
      </div>

      <Seccion titulo="Salud del sistema" descripcion="Estado actual de cada componente.">
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="card px-4 py-1 sm:px-5">
            <Fila etiqueta="API"><Estado nivel={salud.api === 'ok' ? 'ok' : 'error'}>{salud.api === 'ok' ? 'Responde' : 'Con fallas'}</Estado></Fila>
            <Fila etiqueta={`Base de datos (${salud.base_datos.motor})`}><Estado nivel={salud.base_datos.ok ? 'ok' : 'error'}>{salud.base_datos.ok ? 'Conectada' : 'Sin conexión'}</Estado></Fila>
            <Fila etiqueta="Grafo peatonal (Eje 2)">
              {salud.eje2.cargado
                ? <span className="text-xs text-muted">{salud.eje2.version} · denuncias hasta {salud.eje2.datos_hasta}</span>
                : <Estado nivel="error">No cargado</Estado>}
            </Fila>
            <Fila etiqueta="Tráfico en vivo (TomTom)"><Estado nivel={salud.tomtom_configurado ? 'ok' : 'warn'}>{salud.tomtom_configurado ? 'Configurado' : 'Sin clave: ETA histórico'}</Estado></Fila>
            <Fila etiqueta="Búsqueda externa (LocationIQ)"><Estado nivel={salud.locationiq_configurado ? 'ok' : 'warn'}>{salud.locationiq_configurado ? 'Configurada' : 'Sin clave: solo alias locales'}</Estado></Fila>
          </div>
          <div className="card px-4 py-3 sm:px-5">
            <p className="text-sm font-semibold text-fg">Modelos</p>
            {modelos.manifest ? (
              <p className="mt-0.5 text-xs text-muted">Manifiesto v{modelos.manifest.version} · {fechaHora(modelos.manifest.fecha)} · día de verificación {modelos.manifest.dia_referencia_verificacion}</p>
            ) : <p className="mt-0.5 text-xs text-muted">No se encontró el manifiesto de modelos.</p>}
            <div className="mt-2">
              {modelos.sistemas.map((s) => (
                <Fila key={s.sistema} etiqueta={infoSistema(s.sistema).label}>
                  <Estado nivel={s.disponible ? 'ok' : 'error'}>{s.disponible ? `${s.artefactos} archivos · ${DECIMAL.format(s.bytes / 1_048_576)} MB` : 'No disponible'}</Estado>
                </Fila>
              ))}
            </div>
          </div>
        </div>
      </Seccion>

      <Seccion titulo="Uso" descripcion="Abordajes confirmados por las personas usuarias con «Ya abordé». Es una muestra de quienes usan la app, no la demanda real.">
        <div className="grid gap-3 lg:grid-cols-2">
          <ChartCard titulo="Abordajes por día" descripcion="Últimos 14 días"
            tabla={{ cabeceras: ['Fecha', 'Abordajes'], filas: uso.abordajes_por_dia.map((x) => [x.fecha, ENTERO.format(x.n)]) }}
            vacio={abordajes14 === 0 ? 'Todavía no hay abordajes registrados en los últimos 14 días.' : undefined}>
            <Columnas datos={uso.abordajes_por_dia} x="fecha" nombre="Abordajes" formatoX={(v) => fechaCorta(String(v))} formatoTip={(l) => fechaCorta(String(l))} />
          </ChartCard>
          <ChartCard titulo="Abordajes por hora del día" descripcion="Últimos 30 días · hora de Lima"
            tabla={{ cabeceras: ['Hora', 'Abordajes'], filas: uso.abordajes_por_hora.map((x) => [`${String(x.hora).padStart(2, '0')}:00`, ENTERO.format(x.n)]) }}
            vacio={uso.abordajes_por_hora.every((x) => x.n === 0) ? 'Sin abordajes en los últimos 30 días.' : undefined}>
            <Columnas datos={uso.abordajes_por_hora} x="hora" nombre="Abordajes" formatoX={(v) => `${v}h`} formatoTip={(l) => `${String(l).padStart(2, '0')}:00`} />
          </ChartCard>
          <ChartCard titulo="Abordajes por sistema" descripcion="Últimos 30 días" className="lg:col-span-2"
            tabla={{ cabeceras: ['Sistema', 'Abordajes'], filas: uso.abordajes_por_sistema.map((x) => [infoSistema(x.sistema).label, ENTERO.format(x.n)]) }}
            vacio={uso.abordajes_por_sistema.length === 0 ? 'Sin abordajes por sistema en los últimos 30 días.' : undefined}>
            <BarrasH nombre="Abordajes" datos={uso.abordajes_por_sistema.map((x) => ({ etiqueta: infoSistema(x.sistema).label, n: x.n, color: infoSistema(x.sistema).token }))} />
          </ChartCard>
        </div>
      </Seccion>

      <Seccion titulo="Calidad del modelo" descripcion="Se compara lo que dijo la app con lo que respondieron las personas al abordar. Pocas respuestas = métricas poco estables.">
        <div className="grid gap-3 lg:grid-cols-2">
          <ChartCard titulo="Error medio de la espera (MAE)" descripcion="Minutos de diferencia, por semana"
            tabla={{ cabeceras: ['Semana', ...sistemasMon.map((s) => infoSistema(s).label)], filas: semanas.map((f) => [String(f.semana), ...sistemasMon.map((s) => (f[s] == null ? '—' : DECIMAL.format(Number(f[s]))))]) }}
            vacio={semanas.length === 0 ? sinMonitoreo : undefined}>
            <LineasSistemas datos={semanas} series={sistemasMon} formato={(v) => `${DECIMAL.format(v)} min`} formatoTip={(l) => `Semana del ${fechaCorta(String(l))}`} />
          </ChartCard>
          <ChartCard titulo="Acierto del aforo mostrado" descripcion="Porcentaje que coincide con lo percibido, por semana"
            tabla={{ cabeceras: ['Semana', ...sistemasMon.map((s) => infoSistema(s).label)], filas: filasAforo.map((f) => [String(f.semana), ...sistemasMon.map((s) => (f[s] == null ? '—' : PORCENTAJE.format(Number(f[s]))))]) }}
            vacio={semanas.length === 0 ? sinMonitoreo : undefined}>
            <LineasSistemas datos={filasAforo} series={sistemasMon} formato={(v) => PORCENTAJE.format(v)} dominio={[0, 1]} formatoTip={(l) => `Semana del ${fechaCorta(String(l))}`} />
          </ChartCard>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="card p-4 sm:p-5">
            <h3 className="text-sm font-semibold text-fg">Feedback acumulado</h3>
            <p className="mt-0.5 text-xs text-muted">{ENTERO.format(feedback.n)} respuestas · error medio de la espera {feedback.eta.mae_min == null ? '—' : `${DECIMAL.format(feedback.eta.mae_min)} min`} · sesgo {feedback.eta.sesgo_min == null ? '—' : `${feedback.eta.sesgo_min > 0 ? '+' : ''}${DECIMAL.format(feedback.eta.sesgo_min)} min`}</p>
            <div className="mt-2">
              {feedbackPorModo.map(([modo, r]) => (
                <Fila key={modo} etiqueta={{ en_vivo: 'Tráfico en vivo', reciente: 'Tráfico reciente', historico: 'Solo histórico' }[modo] ?? modo}>
                  <span className="text-xs text-muted tabular-nums">{ENTERO.format(r.n)} respuestas · MAE {r.eta.mae_min == null ? '—' : `${DECIMAL.format(r.eta.mae_min)} min`}</span>
                </Fila>
              ))}
            </div>
          </div>
          <div className="card p-4 sm:p-5">
            <h3 className="text-sm font-semibold text-fg">Alertas y calibración</h3>
            {monitoreo.alertas_activas.length === 0
              ? <p className="mt-1"><Estado nivel="ok">Sin alertas en la última semana</Estado></p>
              : <ul className="mt-2 space-y-1.5">{monitoreo.alertas_activas.map((a) => <li key={`${a.sistema}-${a.semana}`} className="text-xs text-fg"><Estado nivel="warn">{infoSistema(a.sistema).label}</Estado> <span className="text-muted">{a.motivo}</span></li>)}</ul>}
            <p className="mt-3 text-xs font-medium text-muted">Calibración vigente del ETA</p>
            {monitoreo.calibracion.length === 0
              ? <p className="mt-1 text-xs text-muted">Todavía no hay una calibración promovida; se usa el ETA del modelo sin factor.</p>
              : <ul className="mt-1 space-y-1">{monitoreo.calibracion.map((c) => <li key={`${c.sistema}-${c.nombre}`} className="text-xs text-fg">{infoSistema(c.sistema).label} · v{c.version} <span className="text-muted">({fechaHora(c.creado_en)})</span></li>)}</ul>}
          </div>
        </div>
      </Seccion>

      <Seccion titulo="Procesos programados" descripcion="Mantenimiento diario y semanal. Una corrida «sin datos nuevos» es normal cuando no hubo actividad.">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(pipelines.por_job).map(([nombre, job]) => (
            <div key={nombre} className="card p-4">
              <p className="font-mono text-xs text-muted">{nombre}</p>
              <p className="mt-1">{job ? <Estado nivel={estadoJob(job.estado).nivel}>{estadoJob(job.estado).texto}</Estado> : <Estado nivel="muted">Nunca se ejecutó</Estado>}</p>
              {job && <p className="mt-1 text-xs text-muted">{fechaHora(job.inicio)}</p>}
            </div>
          ))}
        </div>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-fg">Últimas ejecuciones</h3>
          {pipelines.ultimas.length === 0
            ? <p className="mt-2 text-sm text-muted">Aún no se ha ejecutado ningún proceso. Se lanzan con <code className="rounded bg-surface-2 px-1.5 py-0.5 text-xs">flask --app app pipeline-diario</code> o desde el cron del despliegue.</p>
            : <div className="mt-3"><TablaPipelines filas={pipelines.ultimas} /></div>}
        </div>
      </Seccion>

      <Seccion titulo="Eje 2 · Reportes de seguridad" descripcion="Solo conteos. Los reportes individuales, las ubicaciones y las personas nunca se muestran.">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Cifra etiqueta="Reportes activos" valor={ENTERO.format(eje2.activos)} detalle={`${ENTERO.format(eje2.retirados)} retirados`} />
          <Cifra etiqueta="De día" valor={ENTERO.format(eje2.por_franja.dia)} />
          <Cifra etiqueta="De noche" valor={ENTERO.format(eje2.por_franja.noche)} />
          <Cifra etiqueta="Calles recalibradas" valor={ENTERO.format(eje2.segmentos_ajustados)} detalle={eje2.ajuste_actualizado_en ? `al ${fechaHora(eje2.ajuste_actualizado_en)}` : 'sin recalibración aún'} />
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          <ChartCard titulo="Reportes por tipo" descripcion="Activos"
            tabla={{ cabeceras: ['Tipo', 'Reportes'], filas: Object.entries(eje2.por_tipo).map(([t, n]) => [t, ENTERO.format(n)]) }}>
            <BarrasH nombre="Reportes" datos={Object.entries(eje2.por_tipo).map(([t, n]) => ({ etiqueta: t[0]!.toUpperCase() + t.slice(1), n }))} />
          </ChartCard>
          <ChartCard titulo="Reportes por día" descripcion="Últimos 14 días"
            tabla={{ cabeceras: ['Fecha', 'Reportes'], filas: eje2.por_dia.map((x) => [x.fecha, ENTERO.format(x.n)]) }}
            vacio={eje2.por_dia.every((x) => x.n === 0) ? 'Sin reportes nuevos en los últimos 14 días.' : undefined}>
            <Columnas datos={eje2.por_dia} x="fecha" nombre="Reportes" formatoX={(v) => fechaCorta(String(v))} formatoTip={(l) => fechaCorta(String(l))} />
          </ChartCard>
        </div>
        <p className="text-xs text-muted">{eje2.subregistro}</p>
      </Seccion>
    </div>
  );
}

function TablaPipelines({ filas }: { filas: EjecucionPipeline[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full min-w-[34rem] text-left text-xs">
        <caption className="sr-only">Últimas ejecuciones de los procesos programados</caption>
        <thead className="bg-surface-2 text-muted"><tr>{['Proceso', 'Estado', 'Inicio (Lima)', 'Duración', 'Detalle'].map((h) => <th key={h} scope="col" className="px-3 py-2 font-semibold">{h}</th>)}</tr></thead>
        <tbody>
          {filas.map((f) => (
            <tr key={f.id} className="border-t border-line">
              <td className="px-3 py-1.5 font-mono text-fg">{f.nombre}</td>
              <td className="px-3 py-1.5"><Estado nivel={estadoJob(f.estado).nivel}>{estadoJob(f.estado).texto}</Estado></td>
              <td className="px-3 py-1.5 tabular-nums text-fg">{fechaHora(f.inicio)}</td>
              <td className="px-3 py-1.5 tabular-nums text-fg">{f.duracion_s == null ? '—' : `${DECIMAL.format(f.duracion_s)} s`}</td>
              <td className="px-3 py-1.5 text-muted">{f.error ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
