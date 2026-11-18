// Agregaciones del escenario. Ningún cálculo añade ventas, costos ni usuarios reales.
export const LABELS = { metro_l1: 'Metro Línea 1', metropolitano: 'Metropolitano', corredores: 'Corredores', alimentadores: 'Alimentadores' };
export const COLORS = { metro_l1: '#2563eb', metropolitano: '#7c3aed', corredores: '#0891b2', alimentadores: '#f59e0b' };
const systems = Object.keys(LABELS);
const levels = ['Asientos', 'De_pie', 'Saturado'];
const levelColors = ['#10b981', '#f59e0b', '#e05a76'];
const finite = x => typeof x === 'number' && Number.isFinite(x);
const count = (rows, predicate) => rows.filter(predicate).length;
const sum = rows => rows.reduce((a, b) => a + b, 0);
const mean = values => values.length ? sum(values) / values.length : null;
const rate = (numerator, denominator) => denominator ? numerator / denominator : null;
const day = r => r.fecha_hora_lima.slice(0, 10);
const hour = r => Number(r.fecha_hora_lima.slice(11, 13));
const weekday = r => new Date(`${day(r)}T12:00:00Z`).getUTCDay();
const paired = rows => rows.filter(r => finite(r.eta_obs_min) && finite(r.eta_pred_min));
const errors = rows => paired(rows).map(r => Math.abs(r.eta_obs_min - r.eta_pred_min));
const observedAforo = rows => rows.filter(r => levels.includes(r.aforo_observado));
const dates = rows => [...new Set(rows.map(day))].sort();
export function quantile(values, q) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b), index = (sorted.length - 1) * q;
  const lo = Math.floor(index), hi = Math.ceil(index);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (index - lo);
}
export function filterRows(rows, { system = 'todos', from = '', to = '' } = {}) {
  return rows.filter(r => (system === 'todos' || r.sistema === system) && (!from || day(r) >= from) && (!to || day(r) <= to));
}
export function summarize(rows) {
  const users = rows.every(r => typeof r.usuario_id === 'string' && r.usuario_id.trim())
    ? new Set(rows.map(r => r.usuario_id)).size : null;
  return { users, sessions: rows.length, recommendations: count(rows, r => r.recomendacion_vista), boardings: count(rows, r => r.abordaje_confirmado), feedback: count(rows, r => r.feedback_enviado),
    availability: rate(count(rows, r => r.api_correcta), rows.length), maeEta: mean(errors(rows)), latencyP95: quantile(rows.map(r => r.latencia_api_ms).filter(finite), .95),
    stations: new Set(rows.map(r => r.estacion)).size, days: dates(rows).length };
}
function groupedSystems(rows, calculate) { return systems.map(s => ({ label: LABELS[s], color: COLORS[s], system: s, ...calculate(rows.filter(r => r.sistema === s)) })); }
function groupDaily(rows, calculate) { return dates(rows).map(date => ({ label: date, ...calculate(rows.filter(r => day(r) === date)) })); }
function top(rows, key, limit = 10) {
  const grouped = new Map();
  for (const r of rows) { const label = String(r[key] || '').trim() || 'Sin referencia'; grouped.set(label, (grouped.get(label) || 0) + 1); }
  return [...grouped].map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value || a.label.localeCompare(b.label)).slice(0, limit);
}
function histogram(values, edges) {
  return edges.map((edge, i) => ({ label: i === edges.length - 1 ? `${edge}+` : `${edge}–${edges[i + 1]}`, value: count(values, value => value >= edge && (i === edges.length - 1 || value < edges[i + 1])) }));
}
export function pearsonPairs(rows, getX, getY) {
  const pairs = rows.map(r => [getX(r), getY(r)]).filter(([x, y]) => finite(x) && finite(y));
  const n = pairs.length;
  if (n < 2) return { value: null, n };
  const mx = mean(pairs.map(p => p[0])), my = mean(pairs.map(p => p[1]));
  let numerator = 0, vx = 0, vy = 0;
  for (const [x, y] of pairs) { numerator += (x - mx) * (y - my); vx += (x - mx) ** 2; vy += (y - my) ** 2; }
  return { value: vx && vy ? Math.max(-1, Math.min(1, numerator / Math.sqrt(vx * vy))) : null, n };
}
const series = (key, label, color = '#2563eb', extra = {}) => ({ key, label, color, ...extra });
const sCount = series('value', 'Consultas');
export function buildViews(rows) {
  const views = [];
  const add = (id, group, title, description, type, data, options = {}) => views.push({ id, group, title, description, type, data, ...options });
  const daily = groupDaily(rows, list => ({ consultas: list.length, abordajes: count(list, r => r.abordaje_confirmado), conversion: rate(count(list, r => r.abordaje_confirmado), list.length) }));
  add('actividad-diaria', 'uso', 'Actividad y confirmación diaria', 'Barras: consultas. Línea: abordajes / consultas; dos escalas explícitas.', 'combo', daily, { unit: 'consultas', rightUnit: '%', series: [series('consultas', 'Consultas'), series('conversion', 'Tasa de abordaje', '#10b981', { axis: 'right' })] });
  add('embudo', 'uso', 'Embudo de la experiencia', 'Cada etapa es subconjunto de la anterior; todas son acciones simuladas.', 'funnel', [{ label: 'Consultas', value: rows.length }, { label: 'Recomendaciones vistas', value: count(rows, r => r.recomendacion_vista) }, { label: 'Abordajes confirmados', value: count(rows, r => r.abordaje_confirmado) }, { label: 'Feedback', value: count(rows, r => r.feedback_enviado) }]);
  add('participacion-sistema', 'uso', 'Participación por sistema', 'Distribución de las consultas en la selección.', 'donut', groupedSystems(rows, list => ({ value: list.length })));
  add('consultas-hora', 'uso', 'Consultas por hora', 'Hora local de Lima; suma de todo el período seleccionado.', 'bar', Array.from({ length: 24 }, (_, h) => ({ label: `${h}:00`, value: count(rows, r => hour(r) === h) })), { series: [sCount] });
  const days = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  add('sistema-dia-semana', 'uso', 'Sistemas por día de semana', 'Las barras apiladas separan la actividad de cada sistema.', 'stacked', days.map((label, i) => ({ label, ...Object.fromEntries(systems.map(s => [s, count(rows, r => weekday(r) === i && r.sistema === s)])) })), { series: systems.map(s => series(s, LABELS[s], COLORS[s])) });
  add('mapa-hora-dia', 'uso', 'Mapa de calor día y hora', 'Intensidad según el número de consultas; incluye las 24 horas.', 'heatmap', { xLabels: Array.from({ length: 24 }, (_, i) => `${i}h`), yLabels: days, values: days.map((_, i) => Array.from({ length: 24 }, (_, h) => count(rows, r => weekday(r) === i && hour(r) === h))) });
  add('estaciones-top', 'uso', 'Estaciones con más consultas', 'Diez estaciones con mayor actividad en el filtro.', 'hbar', top(rows, 'estacion'), { unit: 'consultas' });
  add('conversion-sistema', 'uso', 'Alcance y abordaje por sistema', 'Consultas y proporción de abordajes confirmados sobre consultas.', 'combo', groupedSystems(rows, list => ({ consultas: list.length, conversion: rate(count(list, r => r.abordaje_confirmado), list.length) })), { unit: 'consultas', rightUnit: '%', series: [series('consultas', 'Consultas'), series('conversion', 'Tasa de abordaje', '#7c3aed', { axis: 'right' })] });
  add('feedback-sistema', 'uso', 'Participación en feedback', 'Respuestas y tasa de feedback entre los abordajes de cada sistema.', 'combo', groupedSystems(rows, list => ({ feedback: count(list, r => r.feedback_enviado), tasa: rate(count(list, r => r.feedback_enviado), count(list, r => r.abordaje_confirmado)) })), { unit: 'respuestas', rightUnit: '%', series: [series('feedback', 'Feedback', '#0891b2'), series('tasa', 'Feedback / abordajes', '#7c3aed', { axis: 'right' })] });
  add('eta-observado', 'calidad', 'ETA calculado y observado', 'Pares observados del escenario. La diagonal indica coincidencia.', 'scatter', paired(rows).map(r => ({ x: r.eta_pred_min, y: r.eta_obs_min, label: r.sesion_id, group: LABELS[r.sistema], color: COLORS[r.sistema] })), { xLabel: 'ETA calculado (min)', yLabel: 'ETA observado (min)', xUnit: 'min', yUnit: 'min', reference: 'diagonal' });
  add('error-absoluto', 'calidad', 'Distribución del error absoluto', 'Se recalcula como |ETA observado − calculado|; intervalos cerrados por la izquierda.', 'histogram', histogram(errors(rows), [0, 1, 2, 3, 4, 5, 7, 10]), { unit: 'observaciones' });
  add('residuos-eta', 'calidad', 'Sesgo en los tiempos de espera', 'Observado − calculado: valores positivos indican una espera mayor a la calculada.', 'histogram', histogram(paired(rows).map(r => r.eta_obs_min - r.eta_pred_min), [-120, -5, -3, -1, 0, 1, 3, 5, 10]), { unit: 'observaciones' });
  add('caja-error', 'calidad', 'Variación del error por sistema', 'Mínimo, cuartiles, mediana y máximo. No se excluyen valores extremos.', 'boxplot', groupedSystems(rows, list => { const values = errors(list); return { min: values.length ? Math.min(...values) : null, q1: quantile(values, .25), median: quantile(values, .5), q3: quantile(values, .75), max: values.length ? Math.max(...values) : null, n: values.length }; }).filter(r => r.n), { unit: 'min' });
  add('error-diario', 'calidad', 'Error medio y mediano diario', 'Solo pares de ETA disponibles. Un día sin observaciones no se trata como error cero.', 'line', groupDaily(rows, list => ({ mae: mean(errors(list)), mediana: quantile(errors(list), .5) })), { unit: 'min', series: [series('mae', 'Error medio'), series('mediana', 'Error mediano', '#7c3aed')] });
  add('aforo-sistema', 'calidad', 'Ocupación calculada por sistema', 'Categorías del generador, sin presentarlas como predicciones reales del modelo.', 'stacked', groupedSystems(rows, list => Object.fromEntries(levels.map(level => [level, count(list, r => r.aforo_pred === level)]))), { unit: 'consultas', series: levels.map((level, i) => series(level, level.replace('_', ' '), levelColors[i])) });
  add('matriz-aforo', 'calidad', 'Matriz de aforo calculado y observado', 'Filas: calculado. Columnas: observado. Incluye solo observaciones disponibles.', 'heatmap', { xLabels: levels.map(x => x.replace('_', ' ')), yLabels: levels.map(x => x.replace('_', ' ')), values: levels.map(pred => levels.map(obs => count(rows, r => r.aforo_pred === pred && r.aforo_observado === obs))) });
  add('acierto-sistema', 'calidad', 'Coincidencia de aforo por sistema', 'Categorías coincidentes / observaciones de aforo; una muestra vacía no vale cero.', 'bar', groupedSystems(rows, list => { const obs = observedAforo(list); return { value: rate(count(obs, r => r.aforo_pred === r.aforo_observado), obs.length) }; }).filter(r => r.value !== null), { unit: '%', series: [series('value', 'Coincidencia', '#10b981')] });
  add('latencia-sistema', 'tecnologia', 'Latencia media y p95 por sistema', 'Ambas series en milisegundos; p95 calculado por interpolación lineal.', 'combo', groupedSystems(rows, list => { const values = list.map(r => r.latencia_api_ms).filter(finite); return { media: mean(values), p95: quantile(values, .95) }; }), { unit: 'ms', series: [series('media', 'Promedio'), series('p95', 'Percentil 95', '#7c3aed', { type: 'line' })] });
  add('latencia-diaria', 'tecnologia', 'Evolución diaria de latencia', 'Promedio y p95 del escenario; no son mediciones del servidor real.', 'line', groupDaily(rows, list => ({ media: mean(list.map(r => r.latencia_api_ms).filter(finite)), p95: quantile(list.map(r => r.latencia_api_ms).filter(finite), .95) })), { unit: 'ms', series: [series('media', 'Promedio'), series('p95', 'Percentil 95', '#7c3aed')] });
  add('latencia-distribucion', 'tecnologia', 'Distribución de tiempos de respuesta', 'Número de consultas por intervalo de latencia simulada, en ms.', 'histogram', histogram(rows.map(r => r.latencia_api_ms).filter(finite), [0, 100, 200, 300, 500, 750, 1000, 1500]), { unit: 'consultas' });
  add('disponibilidad-diaria', 'tecnologia', 'Éxito de API por día', 'Respuestas correctas / consultas de cada fecha del escenario.', 'line', groupDaily(rows, list => ({ value: rate(count(list, r => r.api_correcta), list.length) })), { unit: '%', series: [series('value', 'Respuestas correctas', '#10b981')] });
  add('cache-respaldo', 'tecnologia', 'Caché y respaldo por sistema', 'Tasas independientes sobre consultas; una sesión puede tener ambas señales.', 'bar', groupedSystems(rows, list => ({ cache: rate(count(list, r => r.cache_hit), list.length), fallback: rate(count(list, r => r.fallback_historico), list.length) })), { unit: '%', series: [series('cache', 'Uso de caché', '#0891b2'), series('fallback', 'Respaldo histórico', '#f59e0b')] });
  const causes = [{ label: 'Error ETA > 3 min', value: count(paired(rows), r => Math.abs(r.eta_obs_min - r.eta_pred_min) > 3) }, { label: 'Aforo diferente', value: count(observedAforo(rows), r => r.aforo_pred !== r.aforo_observado) }, { label: 'Latencia > 1 s', value: count(rows, r => r.latencia_api_ms > 1000) }, { label: 'Respaldo histórico', value: count(rows, r => r.fallback_historico) }, { label: 'Falla API', value: count(rows, r => !r.api_correcta) }].sort((a, b) => b.value - a.value);
  const causeTotal = sum(causes.map(r => r.value)); let cumulative = 0;
  add('pareto-incidencias', 'tecnologia', 'Pareto de incidencias del escenario', 'Una sesión puede aparecer en varias causas. El porcentaje usa apariciones, no sesiones únicas.', 'pareto', causes.map(r => { cumulative += r.value; return { ...r, acumulado: rate(cumulative, causeTotal) }; }), { unit: 'apariciones', rightUnit: '%', series: [series('value', 'Apariciones', '#f59e0b'), series('acumulado', 'Porcentaje acumulado', '#2563eb', { axis: 'right' })] });
  const variables = [{ label: 'ETA calculado', read: r => r.eta_pred_min }, { label: 'Error ETA', read: r => finite(r.eta_obs_min) && finite(r.eta_pred_min) ? Math.abs(r.eta_obs_min - r.eta_pred_min) : null }, { label: 'Latencia', read: r => r.latencia_api_ms }, { label: 'Caché', read: r => typeof r.cache_hit === 'boolean' ? +r.cache_hit : null }, { label: 'Respaldo', read: r => typeof r.fallback_historico === 'boolean' ? +r.fallback_historico : null }, { label: 'Abordaje', read: r => typeof r.abordaje_confirmado === 'boolean' ? +r.abordaje_confirmado : null }];
  const correlations = variables.map(x => variables.map(y => pearsonPairs(rows, x.read, y.read)));
  add('correlaciones', 'tecnologia', 'Relaciones entre señales', 'Pearson con pares disponibles; los sí/no se codifican 1/0. Correlación no implica causa.', 'correlation', { xLabels: variables.map(v => v.label), yLabels: variables.map(v => v.label), values: correlations.map(row => row.map(x => x.value)), counts: correlations.map(row => row.map(x => x.n)) });
  add('seguridad-sistema', 'seguridad', 'Consultas peatonales y reportes', 'Acciones simuladas por sistema, sin interpretarlas como tasas de delitos.', 'bar', groupedSystems(rows, list => ({ consultas: count(list, r => r.ruta_segura_solicitada), reportes: count(list, r => r.reporte_seguridad) })), { unit: 'acciones', series: [series('consultas', 'Rutas consultadas', '#0891b2'), series('reportes', 'Reportes', '#e05a76')] });
  add('tipos-reportes', 'seguridad', 'Tipos de reportes simulados', 'Distribución entre los registros que sí incluyen un reporte.', 'donut', ['acoso', 'seguimiento', 'robo'].map((label, i) => ({ label, value: count(rows, r => r.reporte_seguridad && r.tipo_reporte === label), color: ['#7c3aed', '#0891b2', '#e05a76'][i] })));
  add('peatonal-hora', 'seguridad', 'Interacciones peatonales por hora', 'Consultas de caminata y reportes por hora local; las series son conteos.', 'line', Array.from({ length: 24 }, (_, h) => ({ label: `${h}h`, consultas: count(rows, r => hour(r) === h && r.ruta_segura_solicitada), reportes: count(rows, r => hour(r) === h && r.reporte_seguridad) })), { unit: 'acciones', series: [series('consultas', 'Rutas consultadas', '#0891b2'), series('reportes', 'Reportes', '#e05a76')] });
  add('cobertura-estaciones', 'datos', 'Estaciones representadas cada día', 'Número de estaciones distintas consultadas en cada fecha; no es cobertura de toda Lima.', 'area', groupDaily(rows, list => ({ value: new Set(list.map(r => r.estacion)).size })), { unit: 'estaciones', series: [series('value', 'Estaciones distintas', '#0891b2')] });
  add('rutas-top', 'datos', 'Rutas con más consultas', 'Diez referencias de ruta más frecuentes; se recortan espacios del catálogo.', 'hbar', top(rows, 'ruta'), { unit: 'consultas' });
  const obsCount = paired(rows).length;
  add('cobertura-observaciones', 'datos', 'Cobertura de observaciones ETA', 'Consulta con ambos tiempos disponibles frente a consulta sin observación comparable.', 'donut', [{ label: 'Con observación', value: obsCount, color: '#2563eb' }, { label: 'Sin observación', value: rows.length - obsCount, color: '#b8c8df' }]);
  if (!rows.length) return views.map(view => ({ ...view, data: ['heatmap', 'correlation'].includes(view.type) ? { xLabels: [], yLabels: [], values: [], counts: [] } : [] }));
  return views;
}

/** Cifras de cabecera del laboratorio para un conjunto de sesiones ya filtrado. */
export function indicadores(rows) {
  const resumen = summarize(rows);
  const consultas = rows.length;
  const vistas = count(rows, r => r.recomendacion_vista);
  const abordajes = count(rows, r => r.abordaje_confirmado);
  const errores = errors(rows);
  return {
    usuarios: resumen.users,
    consultas,
    estaciones: resumen.stations,
    vistas,
    abordajes,
    errorEta: mean(errores),
    paresEta: errores.length,
    exitoApi: rate(count(rows, r => r.api_correcta), consultas),
    tasaVistas: rate(vistas, consultas),
    tasaAbordajes: rate(abordajes, consultas),
  };
}
