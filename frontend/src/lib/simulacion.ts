import type { Station } from './types';

// Lógica del formulario de simulación: qué líneas, orígenes y destinos se ofrecen (sin React).

export type OpcionEstacion = { estacion: Station; indice: number };
type Sistema = Station['system'];

/** Sistemas donde primero se elige la ruta: sus paraderos solo conectan dentro de ella. */
const CON_RUTA: Sistema[] = ['corredores', 'alimentadores'];
const SENTIDOS: Record<string, string> = { NS: 'norte a sur', SN: 'sur a norte', EO: 'este a oeste', OE: 'oeste a este' };

/** Los códigos de paradero de corredor terminan en el sentido del recorrido (NS, SN, EO, OE). */
export const sentidoCorredor = (estacion: Station): string => estacion.id.slice(-2).toUpperCase();

/** Los paraderos de un alimentador comparten id: se distinguen por id + nombre. */
export const mismaParada = (a: Station, b: Station): boolean => a.id === b.id && a.name === b.name;

export const usaRuta = (sistema: Sistema): boolean => CON_RUTA.includes(sistema);

export function lineasDe(estaciones: Station[], sistema: Sistema): string[] {
  if (!usaRuta(sistema)) return [];
  const series = new Set(estaciones.filter((e) => e.system === sistema && e.model_series).map((e) => e.model_series as string));
  return [...series].sort((a, b) => a.localeCompare(b, 'es', { numeric: true }));
}

export function origenesDe(estaciones: Station[], sistema: Sistema, linea: string): OpcionEstacion[] {
  const vistas = new Set<string>();
  const opciones = estaciones.flatMap((estacion, indice) => {
    if (estacion.system !== sistema || (usaRuta(sistema) && estacion.model_series !== linea)) return [];
    const clave = `${estacion.id}|${estacion.name}`;
    if (vistas.has(clave)) return [];
    vistas.add(clave);
    return [{ estacion, indice }];
  });
  if (sistema !== 'corredores') return opciones;
  // Corredores: agrupados por sentido y en el orden del recorrido
  return opciones.sort((a, b) =>
    sentidoCorredor(a.estacion).localeCompare(sentidoCorredor(b.estacion))
    || (a.estacion.route_order ?? 1e9) - (b.estacion.route_order ?? 1e9));
}

/** Destinos válidos para `origen`: otro paradero y, en corredores, uno posterior del mismo sentido. */
export function destinosDe(origenes: OpcionEstacion[], origen?: Station): OpcionEstacion[] {
  if (!origen) return [];
  return origenes.filter(({ estacion }) => {
    if (mismaParada(estacion, origen)) return false;
    if (origen.system !== 'corredores') return true;
    if (sentidoCorredor(estacion) !== sentidoCorredor(origen)) return false;
    return origen.route_order == null || estacion.route_order == null || estacion.route_order > origen.route_order;
  });
}

export function etiquetaEstacion(estacion: Station): string {
  if (estacion.system !== 'corredores') return estacion.name;
  const sentido = sentidoCorredor(estacion);
  return `${estacion.name} · ${SENTIDOS[sentido] ?? estacion.id}`;
}

/**
 * Selección coherente tras un cambio: conserva lo elegido si sigue siendo válido y, si no, toma la
 * primera línea, el primer origen y el último destino posible (-1 si no hay ninguno).
 */
export function seleccion(
  estaciones: Station[], sistema: Sistema, previa: { linea?: string; origen?: number; destino?: number } = {}
): { linea: string; origen: number; destino: number } {
  const lineas = lineasDe(estaciones, sistema);
  const linea = previa.linea && lineas.includes(previa.linea) ? previa.linea : lineas[0] ?? '';
  const origenes = origenesDe(estaciones, sistema, linea);
  const origen = origenes.find((o) => o.indice === previa.origen) ?? origenes[0];
  const destinos = destinosDe(origenes, origen?.estacion);
  const destino = destinos.find((d) => d.indice === previa.destino) ?? destinos[destinos.length - 1];
  return { linea, origen: origen?.indice ?? -1, destino: destino?.indice ?? -1 };
}

/** Fecha de hoy en Lima (YYYY-MM-DD). */
export const hoyLima = (ahora: Date = new Date()): string =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(ahora);

export function sumarDias(iso: string, dias: number): string {
  const fecha = new Date(`${iso}T12:00:00Z`);
  fecha.setUTCDate(fecha.getUTCDate() + dias);
  return fecha.toISOString().slice(0, 10);
}
