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

export const tripRouteLabel = (route: MatchedRoute) =>
  `${route.route_code ? `Ruta ${route.route_code} · ` : ''}${route.boarding_station} → ${route.leaving_station}`
  + (route.transbordo ? ` · Transbordo ${route.transbordo.route_code}: ${route.transbordo.boarding_station} → ${route.transbordo.leaving_station}` : '');
