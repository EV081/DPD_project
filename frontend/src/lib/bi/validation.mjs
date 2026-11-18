import { LABELS as LABEL } from './data.mjs';
const AFORO=new Set(['Asientos','De_pie','Saturado']);
const esNumero=(x,min,max)=>typeof x==='number'&&Number.isFinite(x)&&x>=min&&x<=max;
export function validarDatos(datos){
  if(!Array.isArray(datos)||datos.length<1||datos.length>10000)throw new Error('Se necesita una lista de 1 a 10 000 registros.');
  const booleanos=['consulta_generada','recomendacion_vista','abordaje_confirmado','feedback_enviado','ruta_segura_solicitada','reporte_seguridad','api_correcta','fallback_historico','cache_hit'];
  const ids=new Set();
  datos.forEach((r,i)=>{
    const error=motivo=>{throw new Error(`Registro ${i+1}: ${motivo}`)};
    if(!r||typeof r!=='object'||Array.isArray(r))error('debe ser un objeto.');
    if(typeof r.sesion_id!=='string'||!r.sesion_id||r.sesion_id.length>80)error('identificador de sesión inválido.');
    if(ids.has(r.sesion_id))error('identificador de sesión duplicado.');
    ids.add(r.sesion_id);
    if(r.usuario_id!==undefined && (typeof r.usuario_id!=='string'||!/^USR-SIM-\d{4,6}$/.test(r.usuario_id)))error('identificador de usuario simulado inválido.');
    if(typeof r.fecha_hora_lima!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(r.fecha_hora_lima))error('fecha y hora inválidas.');
    const [fecha,hora]=r.fecha_hora_lima.split('T');
    if(new Date(`${fecha}T12:00:00Z`).toISOString().slice(0,10)!==fecha||Number(hora.slice(0,2))>23||Number(hora.slice(3))>59)error('fecha y hora fuera de rango.');
    if(!Object.hasOwn(LABEL,r.sistema))error('sistema desconocido.');
    if(typeof r.estacion!=='string'||!r.estacion||r.estacion.length>160||typeof r.ruta!=='string'||r.ruta.length>160)error('estación o ruta inválida.');
    if(r.modo_datos!=='simulado')error('el laboratorio solo acepta escenarios sintéticos.');
    if(booleanos.some(c=>typeof r[c]!=='boolean'))error('faltan indicadores de tipo sí/no.');
    if(!esNumero(r.eta_pred_min,0,120)||!esNumero(r.latencia_api_ms,0,60000)||!AFORO.has(r.aforo_pred))error('ETA, latencia o aforo inválido.');
    if(r.eta_obs_min!==null&&!esNumero(r.eta_obs_min,0,120))error('ETA observado inválido.');
    if(r.error_eta_abs_min!==null&&!esNumero(r.error_eta_abs_min,0,120))error('error ETA inválido.');
    if(r.aforo_observado!==null&&!AFORO.has(r.aforo_observado))error('aforo observado inválido.');
    if(r.tipo_reporte!==null&&!['acoso','seguimiento','robo'].includes(r.tipo_reporte))error('tipo de reporte inválido.');
    if(!r.consulta_generada||r.recomendacion_vista&&!r.api_correcta||r.abordaje_confirmado&&!r.recomendacion_vista||r.feedback_enviado&&!r.abordaje_confirmado)error('el recorrido de uso es incoherente.');
    if(r.abordaje_confirmado&&(r.eta_obs_min===null||r.error_eta_abs_min===null||r.aforo_observado===null))error('faltan observaciones del abordaje.');
    if(r.reporte_seguridad&&!r.ruta_segura_solicitada)error('reporte sin consulta de ruta segura.');
  });
  return datos;
}

