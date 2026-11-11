import { api } from './client';

// Forma de GET /api/admin/dashboard (solo administradores). Sin datos personales: todo viene agregado.
export interface EstadoJob { nombre: string; estado: string; inicio: string | null; fin: string | null }
export interface EjecucionPipeline extends EstadoJob { id: number; duracion_s: number | null; error: string | null }

export interface MetricaSemanal {
  semana: string; sistema: string; abordajes: number; eta_n: number; eta_mae_min: number | null; eta_sesgo_min: number | null;
  aforo_n: number; aforo_acierto: number | null; alerta: boolean; motivo: string | null;
}

export interface Resumen {
  n: number;
  eta: { n: number; mae_min: number | null; sesgo_min: number | null };
  aforo: { n: number; acierto: number | null } & Record<string, unknown>;
  por_modo_datos: Record<string, { n: number; eta: { n: number; mae_min: number | null; sesgo_min: number | null } }>;
}

export interface Dashboard {
  generado_en: string;
  salud: {
    api: string;
    base_datos: { ok: boolean; motor: string; error?: string };
    eje2: { cargado: boolean; version?: string; datos_hasta?: string; n_segmentos?: number; n_accesos?: number; error?: string };
    tomtom_configurado: boolean;
    locationiq_configurado: boolean;
  };
  modelos: {
    manifest: { version: string; fecha: string; cambios: string; entorno: Record<string, string>; dia_referencia_verificacion: string } | null;
    sistemas: { sistema: string; artefactos: number; bytes: number; disponible: boolean }[];
  };
  pipelines: { ultimas: EjecucionPipeline[]; por_job: Record<string, EstadoJob | null>; con_error: number };
  monitoreo: {
    semanal: MetricaSemanal[];
    alertas_activas: MetricaSemanal[];
    calibracion: { sistema: string; nombre: string; version: number; parametros: Record<string, unknown>; metricas: Record<string, unknown> | null; creado_en: string | null }[];
  };
  uso: {
    usuarios_total: number; usuarios_nuevos_7d: number; feedback_total: number; feedback_7d: number;
    abordajes_por_dia: { fecha: string; n: number }[];
    abordajes_por_sistema: { sistema: string; n: number }[];
    abordajes_por_hora: { hora: number; n: number }[];
  };
  feedback: Resumen;
  eje2: {
    activos: number; retirados: number;
    por_tipo: Record<'acoso' | 'seguimiento' | 'robo', number>;
    por_franja: Record<'dia' | 'noche', number>;
    por_dia: { fecha: string; n: number }[];
    segmentos_ajustados: number; ajuste_actualizado_en: string | null; subregistro: string;
  };
}

export const getDashboard = async (): Promise<Dashboard> => (await api.get('/admin/dashboard')).data;
