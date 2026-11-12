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
  // Corredores: posición del paradero en el recorrido de su sentido (para ofrecer solo destinos posteriores)
  route_order?: number | null;
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
  model?: string | null;            // método usado en esta hora (modelo o respaldo)
  crowding: number | null;          // ocupación = pasajeros a bordo / capacidad (puede superar 1)
  class: ClaseAforo;
  eta_min: number | null;           // espera estimada en andén (min)
  eta2_min: number | null;          // espera hasta el segundo vehículo
  recommendation: Recomendacion;
  band80?: { low: number | null; high: number | null } | null;
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
  factor_calibracion?: number;      // Eje 1: ajuste del ETA según las esperas reales reportadas (1 = sin ajuste)
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
  // Solo cuando la consulta es del momento actual
  ahora?: AforoAhora | null;
  proximas_salidas?: ProximaSalida[];
}

// Respuesta de GET /api/predictions/viaje: ¿a qué hora salgo para llegar a tiempo?
export interface TramoPlan {
  servicio: string;                 // p. ej. "Expreso 5"
  sube: string;
  baja: string;
  viaje_min: number;
  espera_min: number;
  intervalo_min: number;
  paradas_intermedias: number;
  frecuencia_publicada: boolean;    // false: la espera usa el intervalo típico del modelo
  // Líneas comunes: servicios directos entre las dos estaciones; se sube al primero que pase
  servicios?: { nombre: string; viaje_min: number; intervalo_min: number; paradas_intermedias: number; probabilidad: number }[];
}

// Una salida desde el paradero (mapa): sin destino no hay llegada, tiempo a bordo ni servicio
export interface ProximaSalida {
  salida: string;                   // HH:MM en que hay que estar en el paradero
  llegada: string | null;           // HH:MM estimada de llegada
  espera_min: number;
  viaje_min: number | null;
  intervalo_min: number;
  ocupacion: number;                // interpolada dentro de la hora (aproximada)
  clase: ClaseAforo;
  franja: 'dia' | 'noche';
  tramos: TramoPlan[] | null;       // Metropolitano: servicio(s) a tomar; null en los demás sistemas
}

/** Aforo interpolado al minuto de la consulta (aproximado). */
export interface AforoAhora {
  hora: string;
  crowding: number;
  class: ClaseAforo;
}

// Una salida de la simulación: siempre con destino y hora límite
export interface OpcionSalida extends ProximaSalida {
  llegada: string;
  viaje_min: number;
  margen_min: number;               // minutos antes de la hora límite (negativo: tarde)
  estado: 'con_margen' | 'justo' | 'tarde';
  costo_min: number;
}

export interface ServicioPlan {
  nombre: string;
  opera: boolean | null;            // null: la fuente no publica el horario
  horario: string | null;
  intervalo_min: number | null;
  url?: string | null;
  notas: string[];
  viaje_min?: number;
  paradas_intermedias?: number;
  recomendado?: boolean;            // forma parte de la salida recomendada
}

export interface PlanSalida {
  origen: { id: string; name: string };
  destino: { id: string; name: string };
  system: string;
  series: string;
  sentido: string | null;
  dia: string;
  tipo_dia: 'LAB' | 'SAB' | 'DOM';
  llegada_limite: string;
  referencia: ReferenciaDatos;
  opciones: OpcionSalida[];
  recomendada: string | null;
  ultima_puntual: string | null;
  mas_comoda: string | null;
  motivo: string;
  servicios: ServicioPlan[];
  seguridad: { franja_salida: 'dia' | 'noche'; franja_llegada: 'dia' | 'noche'; nota: string } | null;
  supuestos: string[];
  fuente_horarios: { nombre: string; url: string; consultado: string; aviso: string };
}

// Para la sugerencia de ubicaciones en tiempo real
export interface AutocompleteSuggestion {
  display_name: string;
  lat: number;
  lon: number;
}

// Estructura de cada ruta encontrada por match-trip
// Segundo tramo de un viaje con transbordo: se baja del primer servicio, se camina `caminata_m` y se sube a este
export interface TramoTransbordo {
  route_code: string;
  system: string;
  caminata_m: number;
  boarding_station: string;
  boarding_id: string;
  leaving_station: string;
  leaving_id: string;
}

export interface MatchedRoute {
  type: 'DIRECTO_POR_RUTA' | 'DIRECTO_POR_SISTEMA' | 'TRANSBORDO';
  /** Solo en viajes con transbordo: el segundo servicio. Los campos de arriba describen el primero. */
  transbordo?: TramoTransbordo;
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
  /** Viajes con un transbordo (el backend los calcula cuando no hay ruta directa). */
  found_transfers?: MatchedRoute[];
  recomendacion_viaje?: RecomendacionViaje | null;
}
// Vista del pronóstico en el mapa: estado actual + 24 h, o "sin datos ATU" para ese paradero
export type ForecastView =
  | { sinDatos: true }
  | { sinDatos?: false; current: PredictionItem; predictions: PredictionItem[]; referencia: ReferenciaDatos;
      ahora?: AforoAhora | null; proximas?: ProximaSalida[] };
