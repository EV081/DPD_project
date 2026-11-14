import type { MatchedRoute } from './types';

export const ROUTE_PAGE_SIZE = 6;

// La selección identifica el recorrido, no su posición ni los valores estimados.
export function tripRouteKey(route: MatchedRoute): string {
  const transfer = route.transbordo;
  return JSON.stringify([
    route.type, route.system, route.route_code, route.boarding_id, route.leaving_id,
    transfer?.system ?? '', transfer?.route_code ?? '',
    transfer?.boarding_id ?? '', transfer?.leaving_id ?? '',
  ]);
}

export function formatMinutes(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value) || value < 0) return 'No disponible';
  return `${new Intl.NumberFormat('es-PE', { maximumFractionDigits: 1 }).format(value)} min`;
}

export function comparedRoutes(routes: MatchedRoute[], selectedKeys: string[]): MatchedRoute[] {
  return selectedKeys.flatMap((key) => {
    const route = routes.find((item) => tripRouteKey(item) === key);
    return route ? [route] : [];
  });
}

/** Qué tomar: "Ruta 301", "Expreso 9"… null si el sistema basta (Metro L1, o Metropolitano sin horario). */
export function routeServiceLabel(route: Pick<MatchedRoute, 'system' | 'route_code' | 'servicio_troncal'>): string | null {
  if (route.system === 'metropolitano') return route.servicio_troncal?.texto ?? null;
  if (route.system === 'metro_l1' || !route.route_code) return null;
  return `Ruta ${route.route_code}`;
}

export const tripRouteLabel = (route: MatchedRoute) => {
  const servicio = routeServiceLabel(route);
  return `${servicio ? `${servicio} · ` : ''}${route.boarding_station} → ${route.leaving_station}`
  + (route.transbordo ? ` · Transbordo ${route.transbordo.route_code}: ${route.transbordo.boarding_station} → ${route.transbordo.leaving_station}` : '');
};
