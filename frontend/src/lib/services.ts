import { api } from './client';
import { System, Station, StationPrediction } from './types';
import { AutocompleteSuggestion, TripMatchResponse } from './types';

// 1. Mapeador para llamadas a endpoints de Backend (p. ej. GET /api/stations?system=...)
export const mapSystemToBackendApi = (system: string): string => {
  const cleanSystem = system ? system.toLowerCase().trim() : '';

  switch (cleanSystem) {
    case 'alimentador':
    case 'alimentadores':
      return 'alimentadores';
    case 'corredor':
    case 'corredores':
      return 'corredores';
    case 'metro_l1':
    case 'metrol_l1':
    case 'metro_linea1':
      return 'metro_l1';
    case 'troncal':
    case 'metropolitano':
      return 'metropolitano';
    default:
      return cleanSystem;
  }
};

// 2. Mapeador para las series del Modelo de ML / Predicción (singular / troncal)
export const mapSystemToBackendModel = (system: string): string => {
  const cleanSystem = system ? system.toLowerCase().trim() : '';

  switch (cleanSystem) {
    case 'alimentadores':
    case 'alimentador':
      return 'alimentador';
    case 'corredores':
    case 'corredor':
      return 'corredor';
    case 'metro_l1':
    case 'metrol_l1':
    case 'metro_linea1':
      return 'metro_l1';
    case 'metropolitano':
    case 'troncal':
      return 'troncal';
    default:
      return cleanSystem;
  }
};

export const getSystems = async (): Promise<System[]> => {
  const res = await api.get('/systems');
  return res.data;
};

export const getStations = async (system?: string, q?: string): Promise<Station[]> => {
  const params: any = {};
  if (system) params.system = mapSystemToBackendApi(system); // Envía 'alimentadores', 'corredores', etc.
  if (q) params.q = q;
  const res = await api.get('/stations', { params });
  return res.data;
};

export const getNearbyStations = async (lat: number, lng: number, radius = 1500): Promise<Station[]> => {
  const res = await api.get('/stations/nearby', {
    params: { latitude: lat, longitude: lng, radius }
  });
  return res.data;
};

export const getRouteGeoJson = async (systemName: string, routeCode?: string | number) => {
  const mappedSystem = mapSystemToBackendModel(systemName);
  
  const params: any = {};
  if (routeCode) {
    // Pasamos el string limpio; Axios se encarga de codificar la barra '/' a '%2F' automáticamente
    params.code = routeCode; 
  }

  const res = await api.get(`/geo/routes/${mappedSystem}`, { params });
  return res.data;
};

/**
 * Predicción de una estación o paradero: estado actual + pronóstico de las 24 h en UNA llamada.
 *
 * - El backend resuelve qué serie del modelo corresponde al paradero (ya no hay reglas de texto
 *   ni series "por defecto"). Si el paradero no tiene datos ATU propios responde 404 y aquí se
 *   devuelve null: la app muestra "sin predicción" en vez de la de otra estación.
 * - No se envían fecha ni hora: el backend usa la fecha y la hora de Lima.
 * - `haciaId` (estación de bajada) fija el sentido de viaje en Metro L1 y Metropolitano; en
 *   corredores el código del paradero ya trae el sentido. `ruta` desambigua paraderos de
 *   corredor compartidos por varias rutas.
 */
export const getStationPrediction = async (
  station: Station,
  haciaId?: string
): Promise<StationPrediction | null> => {
  if (station.model_series === null) return null;   // el backend ya sabe que no hay datos
  const params: Record<string, string> = {};
  if (haciaId) params.hacia_id = haciaId;
  const ruta = station.raw_properties?.ruta;
  if (station.system === 'corredores' && ruta) params.ruta = String(ruta);
  try {
    const res = await api.get(`/predictions/estacion/${encodeURIComponent(station.id)}`, {
      params,
      timeout: 60000, // el primer pedido puede despertar la instancia de Render
    });
    return res.data;
  } catch (error: any) {
    if (error?.response?.status === 404) return null;
    throw error;
  }
};

// Extrae el código o servicio de la ruta según el tipo de sistema del paradero
export const getRouteCodeFromStation = (station: Station): string | undefined => {
  switch (station.system) {
    case "corredores":
      return station.raw_properties?.ruta; // Ej: "306", "201" (Sí usa código específico)
    case "alimentadores":
      return station.raw_properties?.servicio; // Ej: "ChimpuOcllo/SanJuanDeDios" (Sí usa servicio)
    case "metropolitano":
      return undefined; // Retornamos undefined para que cargue toda la troncal/servicios del Metropolitano
    case "metro_l1":
      return undefined; // Retornamos undefined para que cargue toda la Línea 1 completa
    default:
      return undefined;
  }
};

export const getAutocompleteSuggestions = async (
  query: string
): Promise<AutocompleteSuggestion[]> => {
  if (!query || query.trim().length < 3) return [];
  const res = await api.get('/geo/autocomplete', {
    params: { q: query }
  });
  return res.data;
};

/**
 * Planifica el viaje entre la ubicación actual del usuario y un destino
 * (ya sea texto buscado o coordenadas seleccionadas).
 */
export const matchTrip = async (
  originLat: number,
  originLon: number,
  destination: string | { lat: number; lon: number },
  radius = 1000
): Promise<TripMatchResponse> => {
  const params: any = {
    origin_lat: originLat,
    origin_lon: originLon,
    radius
  };

  if (typeof destination === 'string') {
    params.destination = destination;
  } else {
    params.dest_lat = destination.lat;
    params.dest_lon = destination.lon;
  }

  const res = await api.get('/geo/match-trip', { params });
  return res.data;
};


export const getStation = async (id: string): Promise<Station> => {
  const res = await api.get(`/stations/${encodeURIComponent(id)}`);
  return res.data;
};

export interface FeedbackPayload {
  station_id: string;
  sistema: string;
  espera_real_min: number;
  eta_mostrado_min?: number | null;
  eta_base_min?: number | null;
  factor_trafico?: number | null;
  modo_datos?: string;
  aforo_mostrado?: string;
  aforo_percibido?: string | null;
}

export const sendFeedback = async (payload: FeedbackPayload): Promise<void> => {
  await api.post('/feedback', payload);
};
