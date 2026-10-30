import { ClaseAforo, Recomendacion, PredictionItem, MatchedRoute } from './types';

// Textos y colores únicos para mostrar el aforo v2 (ocupación real estimada con matriz O-D)

export const etiquetaClase = (clase?: ClaseAforo | string | null): string => {
  switch (clase) {
    case 'Asientos':
      return 'Con asientos';
    case 'De_pie':
      return 'De pie';
    case 'Saturado':
      return 'Saturado';
    case 'Sin_servicio':
      return 'Fuera de horario';
    default:
      return 'Sin dato';
  }
};

export const etiquetaRecomendacion = (rec?: Recomendacion | string | null): string => {
  switch (rec) {
    case 'abordar':
      return 'Abordar';
    case 'esperar_siguiente':
      return 'Esperar el siguiente';
    case 'cambiar_paradero':
      return 'Cambiar de paradero';
    case 'sin_servicio':
      return 'Sin servicio';
    default:
      return '—';
  }
};

// "% de ocupación": pasajeros a bordo / capacidad nominal del vehículo. Puede superar 100 %
// cuando la demanda excede la oferta (hay pasajeros que no logran subir).
export const textoOcupacion = (crowding?: number | null): string => {
  if (crowding === null || crowding === undefined) return '—';
  return `${Math.round(crowding * 100)}%`;
};

export const anchoBarra = (crowding?: number | null): number =>
  Math.min(Math.max((crowding ?? 0) * 100, 4), 100);

export const colorOcupacion = (clase?: ClaseAforo | string | null): string => {
  switch (clase) {
    case 'Saturado':
      return '#ef4444';
    case 'De_pie':
      return '#f59e0b';
    case 'Asientos':
      return '#10b981';
    default:
      return '#94a3b8';
  }
};

export const textoEspera = (p?: PredictionItem | null): string => {
  if (!p || p.class === 'Sin_servicio' || p.eta_min === null || p.eta_min === undefined) return 'Sin servicio';
  return `${p.eta_min} min`;
};

// Hora local de Lima (UTC-5 fijo; Perú no tiene horario de verano)
export const formatoHora = (fechaHora?: string): string => {
  if (!fechaHora) return '';
  const hhmm = fechaHora.includes(' ') ? fechaHora.split(' ')[1] : fechaHora.slice(11, 16);
  return hhmm.slice(0, 5);
};

// Rutas que se ofrecen al usuario: sin las de sentido contrario (la vereda equivocada). El backend
// ya las entrega ordenadas por costo generalizado (caminata + espera + aforo + tiempo a bordo).
export const rutasOfrecibles = (rutas: MatchedRoute[] = []): MatchedRoute[] =>
  rutas.filter((r) => !r.sentido_contrario);

export const textoProbabilidadLleno = (p?: number | null): string | null =>
  p !== null && p !== undefined && p >= 0.2 ? `${Math.round(p * 100)}% de que llegue lleno` : null;

// Clases de Tailwind (claro y oscuro) para los distintivos de recomendación
export const claseRecomendacion = (rec?: Recomendacion | string | null): string => {
  switch (rec) {
    case 'abordar':
      return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300';
    case 'esperar_siguiente':
      return 'bg-amber-500/15 text-amber-700 dark:text-amber-300';
    case 'cambiar_paradero':
      return 'bg-rose-500/15 text-rose-700 dark:text-rose-300';
    default:
      return 'bg-slate-500/15 text-slate-600 dark:text-slate-300';
  }
};

// Clases para el estado del aforo (punto de color + texto)
export const claseAforo = (clase?: ClaseAforo | string | null): string => {
  switch (clase) {
    case 'Saturado':
      return 'text-rose-600 dark:text-rose-400';
    case 'De_pie':
      return 'text-amber-600 dark:text-amber-400';
    case 'Asientos':
      return 'text-emerald-600 dark:text-emerald-400';
    default:
      return 'text-muted';
  }
};
