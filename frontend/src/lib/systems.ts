// Identidad visual de cada sistema de transporte (un solo lugar para etiquetas y colores)
export interface SystemInfo {
  id: string;
  label: string;
  color: string;      // marcador del mapa y acentos
  badge: string;      // clases del distintivo (claro y oscuro)
}

export const SYSTEMS: Record<string, SystemInfo> = {
  metropolitano: {
    id: 'metropolitano', label: 'Metropolitano', color: '#f59e0b',
    badge: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  },
  corredores: {
    id: 'corredores', label: 'Corredores', color: '#e11d48',
    badge: 'bg-rose-500/12 text-rose-700 dark:text-rose-300',
  },
  metro_l1: {
    id: 'metro_l1', label: 'Metro L1', color: '#16a34a',
    badge: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  },
  alimentadores: {
    id: 'alimentadores', label: 'Alimentadores', color: '#7c3aed',
    badge: 'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  },
};

const FALLBACK: SystemInfo = {
  id: 'otro', label: 'Transporte', color: '#2563eb',
  badge: 'bg-blue-500/15 text-blue-700 dark:text-blue-300',
};

export const systemInfo = (id?: string | null): SystemInfo => (id && SYSTEMS[id]) || FALLBACK;
