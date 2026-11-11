import type { Station } from './types';

export function visibleStations(stations: Station[], ids: string[] | null, showAll: boolean, zoom: number,
  contains: (latitude: number, longitude: number) => boolean) {
  if (ids) { const selected = new Set(ids); return stations.filter((s) => selected.has(s.id)); }
  if (!showAll) return [];
  return stations.filter((s) => contains(s.latitude, s.longitude)
    && (zoom >= 13 || s.system === 'metropolitano' || s.system === 'metro_l1'));
}
