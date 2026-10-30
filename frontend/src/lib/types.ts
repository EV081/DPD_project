export interface System {
  id: string;
  name: string;
  description: string;
  total_stations: number;
}

export interface Station {
  id: string;
  name: string;
  system: 'metropolitano' | 'corredores' | 'metro_l1' | 'alimentadores';
  avenida: string;
  latitude: number;
  longitude: number;
  distance_m?: number;
  raw_properties?: any;
  // Serie del modelo de demanda (la resuelve el backend). null = el paradero no tiene datos ATU
  // propios: la app muestra "sin predicción" en vez de usar la de otra estación.
  model_system?: string | null;
  model_series?: string | null;
}

export type ClaseAforo = 'Asientos' | 'De_pie' | 'Saturado' | 'Sin_servicio';
export type Recomendacion = 'abordar' | 'esperar_siguiente' | 'cambiar_paradero' | 'sin_servicio';

export interface OcupacionSentido {
  descripcion: string | null;
  ocupacion: number | null;
  pasajeros_por_tren: number | null;
  class: ClaseAforo;
  eta_min: number | null;
  recommendation: Recomendacion;
}

export interface PredictionItem {
  datetime: string;                 // fecha y hora del pronóstico (hora de Lima)
  value: number | null;             // subidas pronosticadas en la hora
  crowding: number | null;          // ocupación = pasajeros a bordo / capacidad (puede superar 1)
  class: ClaseAforo;
  eta_min: number | null;           // espera estimada en andén (min)
  eta2_min: number | null;          // espera hasta el segundo vehículo
  recommendation: Recomendacion;
  band80?: { low: number | null; high: number | null };
  sentido?: string | null;          // p. ej. "hacia Bayóvar" o "hacia CERES"
  pasajeros_por_tren?: number | null;  // pasajeros a bordo por vehículo al salir del paradero
  paradero?: string;                // corredores: nombre del paradero ATU
  intervalo_min?: number | null;
  por_sentido?: Record<'asc' | 'desc', OcupacionSentido>;
  probabilidad_no_subir?: number | null;   // P(el vehículo que te toca llega lleno)
  tiempo_viaje_min?: number | null;
  multiplicador_hacinamiento?: number | null;
  // Ajuste por tráfico en vivo (solo la hora actual de corredores y alimentadores)
  eta_base_min?: number | null;     // ETA antes de aplicar el tráfico
  factor_trafico?: number | null;
  modo_datos?: 'en_vivo' | 'reciente' | 'historico';
  alternativa?: { paradero: string; codigo: string; distancia_m: number; ahorro_min: number; ocupacion: number } | null;
}

export interface ReferenciaDatos {
  fecha_objetivo: string;
  fecha_referencia_datos: string;   // día de 2025 con datos ATU usado como base
  tipo_dia: string;
  evento: string | null;
  criterio: string;
}

// Respuesta de GET /api/predictions/estacion/<id>: estado actual + 24 h en una sola llamada
export interface StationPrediction {
  system: string;
  series: string;
  station: string;
  model: string;
  nivel: 'serie' | 'paradero';
  metodo_aforo: string;
  sentido: 'asc' | 'desc' | null;
  sentidos: Record<'asc' | 'desc', string> | null;
  referencia: ReferenciaDatos;
  current: PredictionItem;
  forecast: PredictionItem[];
}

// Para la sugerencia de ubicaciones en tiempo real
export interface AutocompleteSuggestion {
  display_name: string;
  lat: number;
  lon: number;
}

// Estructura de cada ruta encontrada por match-trip
export interface MatchedRoute {
  type: 'DIRECTO_POR_RUTA' | 'DIRECTO_POR_SISTEMA';
  route_code: string;
  system: string;
  boarding_station: string;
  boarding_id: string;
  origin_walk_m: number;
  leaving_station: string;
  leaving_id: string;
  dest_walk_m: number;
  // Recomendación por costo generalizado (backend v1.3.0)
  costo_generalizado_min?: number | null;   // minutos equivalentes: caminata + espera + aforo + viaje
  caminata_min?: number;
  espera_min?: number;
  viaje_min?: number;
  sentido_contrario?: boolean;              // paradero en la vereda equivocada: no se ofrece
  sin_prediccion?: boolean;
  aforo?: { clase?: string; ocupacion?: number | null; pasajeros_por_vehiculo?: number | null; sentido?: string | null };
}

export interface RecomendacionViaje {
  criterio: string;
  hora: number;
  mejor: { boarding_station: string; route_code: string };
  cambiar_paradero?: boolean;
  ahorro_min?: number;
  mensaje?: string;
}

// Respuesta completa del planificador
export interface TripMatchResponse {
  origin: { lat: number; lon: number };
  destination: { lat: number; lon: number; resolved_name: string };
  radius_meters: number;
  diagnostic?: {
    origin_stations_found: number;
    destination_stations_found: number;
    warning?: string;
  };
  found_routes: MatchedRoute[];
  recomendacion_viaje?: RecomendacionViaje | null;
}
// Vista del pronóstico en el mapa: estado actual + 24 h, o "sin datos ATU" para ese paradero
export type ForecastView =
  | { sinDatos: true }
  | { sinDatos?: false; current: PredictionItem; predictions: PredictionItem[]; referencia: ReferenciaDatos };
