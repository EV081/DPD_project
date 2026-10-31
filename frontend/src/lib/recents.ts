// Destinos buscados recientemente (solo en este navegador)
export interface RecentDestination {
  label: string;
  lat?: number;
  lon?: number;
}

const KEY = 'urbansafe_recents';
const MAX = 4;

export function getRecents(): RecentDestination[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || '[]');
    return Array.isArray(parsed) ? parsed.slice(0, MAX) : [];
  } catch {
    return [];
  }
}

export function addRecent(item: RecentDestination): RecentDestination[] {
  const next = [item, ...getRecents().filter((r) => r.label !== item.label)].slice(0, MAX);
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* almacenamiento no disponible */ }
  return next;
}
