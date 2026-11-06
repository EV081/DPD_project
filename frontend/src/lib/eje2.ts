import { api } from './client';
import { Station } from './types';

// Eje 2 · ruta peatonal segura, índice de seguridad y reportes (API /api/eje2)

export type Banda = 'bajo' | 'medio' | 'alto';
export type TipoReporte = 'acoso' | 'seguimiento' | 'robo';

export interface IndiceAcceso {
  acceso_id: string;
  tipo: string;
  nombre: string;
  ruta: string | null;
  lat: number;
  lon: number;
  seguridad_pct: number;
  intervalo_pct: [number, number];
  base_tipo_pct: number;
  confianza: 'alta' | 'media' | 'baja';
  coordenada_aproximada: boolean;
  aviso: string;
}

export interface Tramo { nombre: string; via?: string; largo_m: number; riesgo: Banda; desvio: boolean }

export interface RutaPeatonal {
  tipo: 'normal' | 'segura';
  distancia_m: number;
  minutos: number;
  riesgo_medio: number;
  banda_riesgo: Banda;
  densidad_media_km_anio: number;
  geojson: any;
  tramos: Tramo[];
}

export interface RespuestaRuta {
  seleccionada: 'normal' | 'segura';
  recomendada: 'normal' | 'segura' | 'misma';
  preferencia: string;
  franja: 'dia' | 'noche';
  destino: IndiceAcceso | null;
  comparacion: { distancia_extra_m: number; distancia_extra_pct: number; minutos_extra: number; reduccion_riesgo_pct: number };
  rutas: { normal: RutaPeatonal; segura: RutaPeatonal };
  explicacion: {
    resumen: string;
    motivos: string[];
    tramos_evitados: { nombre: string; largo_m: number }[];
    condiciones: { franja: string; lambda: number; datos_hasta: string; version: string; [k: string]: any };
    aviso: string;
    llamar_105: boolean;
  };
}

export interface ReporteMio {
  id: string;
  tipo: TipoReporte;
  franja: string;
  estado: 'activo' | 'retirado';
  creado_en: string;
  ocurrido_en: string;
}

export interface ReporteCreado { id: string; mensaje: string; calle: string | null; llamar_105: boolean; numero_emergencia: string; aviso: string }

export const NUMERO_EMERGENCIA = '105';

export const TIPOS_REPORTE: { id: TipoReporte; label: string; hint: string }[] = [
  { id: 'acoso', label: 'Acoso', hint: 'Comentarios, hostigamiento o tocamientos' },
  { id: 'seguimiento', label: 'Seguimiento', hint: 'Alguien te siguió a pie o en vehículo' },
  { id: 'robo', label: 'Robo o hurto', hint: 'Arrebato, asalto o intento de robo' },
];

export const getRutaPeatonal = async (
  origen: { lat: number; lon: number },
  estacion: Station,
  preferencia: 'segura' | 'normal' = 'segura',
): Promise<RespuestaRuta> =>
  (await api.post('/eje2/ruta', {
    origen,
    destino: { station_id: estacion.id, sistema: estacion.system },
    preferencia,
  })).data;

export const getIndiceEstacion = async (estacion: Station): Promise<IndiceAcceso | null> => {
  try {
    const res = await api.get('/eje2/accesos/por-estacion', { params: { id: estacion.id, sistema: estacion.system } });
    return res.data;
  } catch (e: any) {
    const status = e?.response?.status;
    if (status === 404 || status === 422) return null;   // sin punto de acceso cercano / fuera de cobertura
    throw e;
  }
};

export const crearReporte = async (tipo: TipoReporte, lat: number, lon: number, ocurridoEn?: string): Promise<ReporteCreado> =>
  (await api.post('/eje2/reportes', { tipo, lat, lon, ...(ocurridoEn ? { ocurrido_en: ocurridoEn } : {}) })).data;

export const getMisReportes = async (): Promise<ReporteMio[]> => (await api.get('/eje2/reportes/mios')).data.reportes ?? [];

export const retirarReporte = async (id: string): Promise<void> => { await api.delete(`/eje2/reportes/${encodeURIComponent(id)}`); };

// Texto de la banda de riesgo (nunca solo color)
export const etiquetaBanda = (b: Banda): string => ({ bajo: 'Riesgo bajo', medio: 'Riesgo medio', alto: 'Riesgo alto' }[b]);
export const claseBanda = (b: Banda): string =>
  b === 'alto' ? 'bg-danger/12 text-danger' : b === 'medio' ? 'bg-warn/15 text-warn' : 'bg-ok/12 text-ok';
