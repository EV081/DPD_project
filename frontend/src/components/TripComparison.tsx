import { Scale } from 'lucide-react';
import { MatchedRoute } from '@/lib/types';
import { claseAforo, etiquetaClase, textoOcupacion } from '@/lib/aforo';
import { formatMinutes, tripRouteKey, tripRouteLabel } from '@/lib/trip-comparison';

const occupancyLabel = (route: MatchedRoute) => route.sin_prediccion
  ? 'Sin predicción' : route.aforo?.clase ? etiquetaClase(route.aforo.clase) : 'No disponible';

export function RouteMetrics({ route }: { route: MatchedRoute }) {
  const missing = route.sin_prediccion || !route.aforo?.clase || route.espera_min == null || route.viaje_min == null || route.caminata_min == null;
  return <>
    <dl className="mt-4 grid grid-cols-2 gap-2 border-t border-line pt-4 text-center">
      {[
        { label: 'Espera', value: formatMinutes(route.espera_min) },
        { label: 'A bordo', value: formatMinutes(route.viaje_min) },
        { label: 'Caminata', value: formatMinutes(route.caminata_min) },
      ].map((metric) => <div key={metric.label} className="rounded-xl bg-surface-2 px-2 py-2.5"><dt className="text-xs text-muted">{metric.label}</dt><dd className="mt-1 text-sm font-semibold tabular-nums text-fg">{metric.value}</dd></div>)}
      <div className="rounded-xl bg-surface-2 px-2 py-2.5"><dt className="text-xs text-muted">Aforo estimado</dt><dd className={`mt-1 text-sm font-semibold ${claseAforo(route.aforo?.clase)}`}>{occupancyLabel(route)}</dd>{!route.sin_prediccion && route.aforo?.ocupacion != null && <dd className="mt-0.5 text-xs text-muted">{textoOcupacion(route.aforo.ocupacion)} de ocupación</dd>}</div>
    </dl>
    {missing && <p className="mt-3 text-xs leading-relaxed text-muted">No todos los datos están disponibles para esta opción. Los campos faltantes no se completan con cero ni con valores de otra ruta.</p>}
    {route.costo_generalizado_min != null && <details className="mt-3 text-xs text-muted"><summary className="cursor-pointer font-medium text-fg">¿Cómo se ordenó esta opción?</summary><p className="mt-1">Índice de comparación: {formatMinutes(route.costo_generalizado_min)} equivalentes. Combina caminata, espera, aforo y viaje; no es la duración total del recorrido.</p></details>}
  </>;
}

export default function TripComparison({ routes, onOpen, onRemove, onClear }: {
  routes: MatchedRoute[];
  onOpen: (route: MatchedRoute) => void;
  onRemove: (route: MatchedRoute) => void;
  onClear: () => void;
}) {
  if (!routes.length) return null;
  return <section id="comparacion-rutas" aria-label="Comparación de opciones" className="card mt-5 p-4 sm:p-5">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 font-semibold text-fg"><Scale size={18} />Tu comparación</h2>
      <button className="btn btn-ghost !px-2 !py-1 text-sm" onClick={onClear}>Limpiar selección</button>
    </div>
    <p role="status" className="mt-1 text-sm text-muted">{routes.length === 1 ? 'Una opción seleccionada. Marca otra para comparar sus datos.' : 'Dos opciones seleccionadas. Los valores corresponden a la misma búsqueda.'}</p>
    {routes.length === 2 && <table className="mt-4 w-full table-fixed text-left text-sm">
      <caption className="sr-only">Espera, tiempo a bordo, caminata y aforo de las dos opciones elegidas</caption>
      <thead><tr><th scope="col" className="w-[28%] border-b border-line pb-3 pr-2">Dato</th>{routes.map((route, index) => <th scope="col" key={tripRouteKey(route)} className="border-b border-line px-2 pb-3 align-top font-medium"><span className="block text-brand">Opción {index + 1}</span><span className="mt-1 block break-words text-xs text-muted">{tripRouteLabel(route)}</span></th>)}</tr></thead>
      <tbody>{[
        { label: 'Espera', value: (route: MatchedRoute) => formatMinutes(route.espera_min) },
        { label: 'A bordo', value: (route: MatchedRoute) => formatMinutes(route.viaje_min) },
        { label: 'Caminata', value: (route: MatchedRoute) => formatMinutes(route.caminata_min) },
        { label: 'Aforo', value: occupancyLabel },
      ].map((row) => <tr key={row.label}><th scope="row" className="border-b border-line py-3 pr-2 font-medium">{row.label}</th>{routes.map((route) => <td key={tripRouteKey(route)} className="break-words border-b border-line px-2 py-3">{row.value(route)}</td>)}</tr>)}</tbody>
    </table>}
    <div className="mt-3 grid gap-2 sm:grid-cols-2">{routes.map((route, index) => <div key={tripRouteKey(route)} className="flex flex-wrap gap-2"><button onClick={() => onOpen(route)} className="btn btn-secondary flex-1 text-sm">Ver opción {index + 1} en mapa</button><button onClick={() => onRemove(route)} className="btn btn-ghost text-sm" aria-label={`Quitar opción ${index + 1} de la comparación`}>Quitar</button></div>)}</div>
  </section>;
}
