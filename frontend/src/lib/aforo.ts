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

// El ETA puede incorporar tráfico y calibración. Una diferencia frente a la base
// no demuestra por sí sola que exista información de tráfico en vivo.
export const textoAjusteEspera = (p?: PredictionItem | null): string | null => {
  if (!p || p.eta_min == null || p.eta_base_min == null) return null;
  const extra = p.eta_min - p.eta_base_min;
  if (!Number.isFinite(extra) || extra < 0.5) return null;
  const minutos = Math.round(extra);
  const calibrado = p.factor_calibracion != null && Math.abs(p.factor_calibracion - 1) > 0.000001;
  if ((p.factor_trafico ?? 1) > 1 && !calibrado) {
    if (p.modo_datos === 'en_vivo') return `Tráfico en vivo: +${minutos} min de espera`;
    if (p.modo_datos === 'reciente') return `Tráfico reciente: +${minutos} min de espera`;
  }
  return `Ajuste de la espera estimada: +${minutos} min`;
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

/**
 * Opciones de viaje: las rutas directas; y si no hay ninguna, los viajes con un transbordo.
 * `conTransbordo` avisa a la pantalla para que lo explique ("no hay ruta directa, pero…").
 */
export const opcionesDeViaje = (resp: { found_routes?: MatchedRoute[]; found_transfers?: MatchedRoute[] }): { rutas: MatchedRoute[]; conTransbordo: boolean } => {
  const directas = rutasOfrecibles(resp.found_routes);
  if (directas.length > 0) return { rutas: directas, conTransbordo: false };
  const transbordos = resp.found_transfers ?? [];
  return { rutas: transbordos, conTransbordo: transbordos.length > 0 };
};

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
