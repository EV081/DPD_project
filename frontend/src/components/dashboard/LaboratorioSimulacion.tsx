'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Download, Maximize2, RotateCcw, Search } from 'lucide-react';
import Alert from '@/components/Alert';
import Modal from '@/components/Modal';
import { Skeleton } from '@/components/Spinner';
import { ChartCard, Cifra, TablaDatos } from '@/components/dashboard/viz';
import { errorMessage } from '@/lib/client';
import { LABELS, buildViews, filterRows, indicadores, type GrupoBi, type SesionSimulada, type VistaBi } from '@/lib/bi/data.mjs';
import { formatValue, renderChart, tableForView } from '@/lib/bi/charts.mjs';
import { validarDatos } from '@/lib/bi/validation.mjs';

const ESCENARIO = '/simulacion/urbansafe_simulacion_600.json';

const GRUPOS: Record<GrupoBi, string> = {
  uso: 'Uso del producto',
  calidad: 'Calidad de la estimación',
  tecnologia: 'Tecnología y operación',
  seguridad: 'Seguridad y feedback',
  datos: 'Comportamiento de datos',
};
/** Los seis gráficos de la vista Principal; los 30 están disponibles en sus secciones. */
const PRINCIPALES = ['embudo', 'actividad-diaria', 'participacion-sistema', 'mapa-hora-dia', 'eta-observado', 'disponibilidad-diaria'];
type Seccion = GrupoBi | 'principal';
const SISTEMAS = Object.entries(LABELS) as [string, string][];

const fechaDe = (r: SesionSimulada) => r.fecha_hora_lima.slice(0, 10);
const tablaDe = (vista: VistaBi) => {
  const t = tableForView(vista);
  return { cabeceras: t.headers, filas: t.rows };
};

/** Gráfico en SVG generado por el módulo `lib/bi`; los textos de los datos ya vienen escapados. */
function Grafico({ vista }: { vista: VistaBi }) {
  const marcado = useMemo(() => renderChart(vista), [vista]);
  return <div className="bi-chart" dangerouslySetInnerHTML={{ __html: marcado }} />;
}

export default function LaboratorioSimulacion() {
  const [datos, setDatos] = useState<SesionSimulada[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [sistema, setSistema] = useState('todos');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [grupo, setGrupo] = useState<Seccion>('principal');
  const [busqueda, setBusqueda] = useState('');
  const [ampliada, setAmpliada] = useState<string | null>(null);

  const limites = useRef<{ desde: string; hasta: string } | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  const aplicar = useCallback((nuevos: SesionSimulada[], conservarRango: boolean) => {
    const dias = nuevos.map(fechaDe).sort();
    const rango = { desde: dias[0], hasta: dias[dias.length - 1] };
    const anterior = limites.current;
    limites.current = rango;
    setDatos(nuevos);
    if (!conservarRango || !anterior) { setDesde(rango.desde); setHasta(rango.hasta); }
  }, []);

  const cargar = useCallback(async (conservarRango = true) => {
    setCargando(true);
    try {
      const respuesta = await fetch(ESCENARIO, { cache: 'no-store' });
      if (!respuesta.ok) throw new Error('No se pudo leer el escenario.');
      aplicar(validarDatos(await respuesta.json()), conservarRango);
      setError(null);
    } catch (e) {
      setError(errorMessage(e, 'No se actualizaron los datos.'));
    } finally {
      setCargando(false);
    }
  }, [aplicar]);

  useEffect(() => { void cargar(false); }, [cargar]);
  const rangoInvalido = !!desde && !!hasta && desde > hasta;
  const visibles = useMemo(
    () => (rangoInvalido ? [] : filterRows(datos, { system: sistema, from: desde, to: hasta })),
    [datos, sistema, desde, hasta, rangoInvalido],
  );
  const vistas = useMemo(() => buildViews(visibles), [visibles]);
  const ind = useMemo(() => indicadores(visibles), [visibles]);

  const mostradas = useMemo(() => {
    const q = busqueda.trim().toLocaleLowerCase('es');
    if (q) return vistas.filter((v) => `${v.title} ${v.description}`.toLocaleLowerCase('es').includes(q));
    if (grupo === 'principal') return PRINCIPALES.map((id) => vistas.find((v) => v.id === id)).filter((v): v is VistaBi => !!v);
    return vistas.filter((v) => v.group === grupo);
  }, [vistas, grupo, busqueda]);

  const vistaAmpliada = ampliada ? vistas.find((v) => v.id === ampliada) ?? null : null;

  const restablecer = () => {
    setSistema('todos'); setBusqueda(''); setGrupo('principal');
    if (limites.current) { setDesde(limites.current.desde); setHasta(limites.current.hasta); }
  };

  const descargarSvg = () => {
    const svg = modalRef.current?.querySelector('svg');
    if (!svg || !vistaAmpliada) return;
    const estilo = getComputedStyle(svg);
    const contenido = svg.outerHTML.replace(/var\((--[\w-]+)\)/g, (_, nombre: string) => estilo.getPropertyValue(nombre).trim() || '#5b6b82');
    const url = URL.createObjectURL(new Blob([contenido], { type: 'image/svg+xml;charset=utf-8' }));
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = `UrbanSafe_${vistaAmpliada.id}.svg`;
    enlace.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const sinUsuarios = ind.usuarios === null;
  const pct = (v: number | null) => formatValue(v, '%');

  const modificado = sistema !== 'todos' || busqueda !== '' || grupo !== 'principal'
    || (!!limites.current && (desde !== limites.current.desde || hasta !== limites.current.hasta));

  return (
    <div className="space-y-6">
      <section aria-label="Filtros del laboratorio" className="space-y-2">
        <div className="lab-bar">
          <select className="lab-field" aria-label="Sistema de transporte" value={sistema} onChange={(e) => setSistema(e.target.value)}>
            <option value="todos">Todos los sistemas</option>
            {SISTEMAS.map(([clave, nombre]) => <option key={clave} value={clave}>{nombre}</option>)}
          </select>
          <div className="lab-field lab-range">
            <input type="date" aria-label="Fecha inicial" value={desde} max={hasta || undefined} onChange={(e) => setDesde(e.target.value)} />
            <span aria-hidden>–</span>
            <input type="date" aria-label="Fecha final" value={hasta} min={desde || undefined} onChange={(e) => setHasta(e.target.value)} />
          </div>
          <label className="lab-field lab-search">
            <Search size={15} aria-hidden className="text-muted" />
            <input type="search" aria-label="Buscar un gráfico" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar un gráfico" />
          </label>
          {modificado && (
            <button type="button" className="lab-reset" onClick={restablecer}><RotateCcw size={14} aria-hidden /> Restablecer</button>
          )}
        </div>
        <p className="px-1 text-xs text-muted" role="status" aria-live="polite">
          {rangoInvalido ? 'La fecha inicial debe ser anterior o igual a la final.'
            : `${visibles.length} de ${datos.length} sesiones · ${sinUsuarios ? 'usuarios no identificados' : `${ind.usuarios} usuarios simulados`}`}
        </p>
      </section>

      {error && <Alert tono="danger">{error}</Alert>}

      {cargando && !datos.length ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}</div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
            <Cifra className="lab-lift" etiqueta="Usuarios simulados" valor={formatValue(ind.usuarios)} detalle={sinUsuarios ? 'El archivo no identifica usuarios' : 'identificadores ficticios únicos'} />
            <Cifra className="lab-lift" etiqueta="Consultas" valor={formatValue(ind.consultas)} detalle={`${ind.estaciones} estaciones`} />
            <Cifra className="lab-lift" etiqueta="Recomendaciones vistas" valor={formatValue(ind.vistas)} detalle={ind.consultas ? `${pct(ind.tasaVistas)} de consultas` : 'Sin observaciones'} />
            <Cifra className="lab-lift" etiqueta="Abordajes confirmados" valor={formatValue(ind.abordajes)} detalle={ind.consultas ? `${pct(ind.tasaAbordajes)} de consultas` : 'Sin observaciones'} />
            <Cifra className="lab-lift" etiqueta="Error medio del ETA" valor={formatValue(ind.errorEta, 'min')} detalle={`${ind.paresEta} pares observados`} />
            <Cifra className="lab-lift" etiqueta="Éxito de la API" valor={ind.consultas ? pct(ind.exitoApi) : 'Sin datos'} detalle="disponibilidad simulada" />
          </div>

          <div className="lab-tabs" role="group" aria-label="Sección de gráficos">
            {(['principal', ...Object.keys(GRUPOS)] as Seccion[]).map((g) => (
              <button key={g} type="button" aria-pressed={grupo === g} onClick={() => setGrupo(g)}>{g === 'principal' ? 'Principal' : GRUPOS[g]}</button>
            ))}
          </div>

          {(() => {
            const tarjeta = (v: VistaBi) => (
              <ChartCard key={v.id} titulo={v.title} descripcion={v.description} tabla={tablaDe(v)}
                className={`lab-lift ${v.wide ? 'lg:col-span-2' : ''}`}
                accion={<button type="button" className="btn btn-secondary px-2.5 py-1.5 text-xs" onClick={() => setAmpliada(v.id)} aria-label={`Ampliar ${v.title}`}><Maximize2 size={14} aria-hidden /> Ampliar</button>}>
                <Grafico vista={v} />
              </ChartCard>
            );
            const titulo = busqueda.trim() ? 'Resultados de la búsqueda' : grupo === 'principal' ? 'Lo más importante' : GRUPOS[grupo];
            return mostradas.length ? (
              <section aria-label={titulo} className="space-y-3">
                <div className="flex items-baseline justify-between gap-3"><h2 className="text-base font-semibold text-fg">{titulo}</h2><p className="text-xs text-muted" aria-live="polite">{mostradas.length} de {vistas.length} gráficos</p></div>
                <div className="grid gap-4 lg:grid-cols-2">{mostradas.map(tarjeta)}</div>
              </section>
            ) : null;
          })()}
          {!mostradas.length && <p className="card p-6 text-center text-sm text-muted">No hay gráficos que coincidan con la búsqueda.</p>}
        </>
      )}

      <p className="text-xs leading-relaxed text-muted">
        <strong className="font-semibold text-fg">Cómo interpretar este informe.</strong> El archivo inicial contiene 600 usuarios ficticios con una sesión
        sintética por usuario para demostrar cálculos y visualizaciones. Los ETA, aforos y latencias son supuestos del generador; no evalúan el
        desempeño real del modelo ni de la API. No se registran ventas, ingresos o ganancias en estos datos.
      </p>

      {vistaAmpliada && (
        <Modal title={vistaAmpliada.title} onClose={() => setAmpliada(null)} size="xl">
          <div ref={modalRef} className="space-y-4">
            <p className="text-sm text-muted">{vistaAmpliada.description}</p>
            <Grafico vista={vistaAmpliada} />
            <div className="flex justify-end">
              <button type="button" className="btn btn-secondary" onClick={descargarSvg}><Download size={16} aria-hidden /> Descargar SVG</button>
            </div>
            <TablaDatos tabla={tablaDe(vistaAmpliada)} titulo={vistaAmpliada.title} />
          </div>
        </Modal>
      )}
    </div>
  );
}
