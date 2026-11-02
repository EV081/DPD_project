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
      return 'var(--danger)';
    case 'De_pie':
      return 'var(--warn)';
    case 'Asientos':
      return 'var(--ok)';
    default:
      return 'var(--muted)';
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
      return 'bg-ok/15 text-ok';
    case 'esperar_siguiente':
      return 'bg-warn/15 text-warn';
    case 'cambiar_paradero':
      return 'bg-danger/15 text-danger';
    default:
      return 'bg-surface-2 text-muted';
  }
};

// Clases para el estado del aforo (punto de color + texto)
export const claseAforo = (clase?: ClaseAforo | string | null): string => {
  switch (clase) {
    case 'Saturado':
      return 'text-danger';
    case 'De_pie':
      return 'text-warn';
    case 'Asientos':
      return 'text-ok';
    default:
      return 'text-muted';
  }
};
