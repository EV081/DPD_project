export interface SesionSimulada {
  sesion_id: string; usuario_id?: string; fecha_hora_lima: string; sistema: SistemaBi; estacion: string; ruta: string;
  consulta_generada: boolean; recomendacion_vista: boolean; abordaje_confirmado: boolean; feedback_enviado: boolean;
  eta_pred_min: number; eta_obs_min: number | null; error_eta_abs_min: number | null;
  aforo_pred: string; aforo_observado: string | null; ruta_segura_solicitada: boolean; reporte_seguridad: boolean;
  tipo_reporte: string | null; latencia_api_ms: number; api_correcta: boolean; fallback_historico: boolean; cache_hit: boolean;
  modo_datos: 'simulado';
}
export type SistemaBi = 'metro_l1' | 'metropolitano' | 'corredores' | 'alimentadores';
export type GrupoBi = 'uso' | 'calidad' | 'tecnologia' | 'seguridad' | 'datos';
export interface VistaBi {
  id: string; title: string; description: string; type: string; group: GrupoBi; wide?: boolean;
  data?: unknown; series?: { key: string; label?: string; color?: string; axis?: string; type?: string }[];
  unit?: string; rightUnit?: string; [clave: string]: unknown;
}
export interface Filtros { system?: string; from?: string; to?: string }
export interface Indicadores {
  usuarios: number | null; consultas: number; estaciones: number; vistas: number; abordajes: number;
  errorEta: number | null; paresEta: number; exitoApi: number | null; tasaVistas: number | null; tasaAbordajes: number | null;
}
export const LABELS: Record<SistemaBi, string>;
export const COLORS: Record<SistemaBi, string>;
export function quantile(values: number[], q: number): number | null;
export function filterRows(rows: SesionSimulada[], filtros?: Filtros): SesionSimulada[];
export function summarize(rows: SesionSimulada[]): { users: number | null; sessions: number; stations: number; [clave: string]: unknown };
export function pearsonPairs<T>(rows: T[], getX: (r: T) => number, getY: (r: T) => number): { value: number | null; n: number };
export function buildViews(rows: SesionSimulada[]): VistaBi[];
export function indicadores(rows: SesionSimulada[]): Indicadores;
