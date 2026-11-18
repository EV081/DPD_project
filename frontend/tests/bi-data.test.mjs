import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { buildViews, filterRows, summarize, pearsonPairs, quantile } from '../src/lib/bi/data.mjs';
const rows = JSON.parse(await readFile(new URL('../public/simulacion/urbansafe_simulacion_600.json', import.meta.url), 'utf8'));
test('escenario completo produce 30 vistas únicas y conserva el embudo', () => {
  assert.equal(rows.length, 600);
  assert.equal(summarize(rows).users, 600);
  const views = buildViews(rows);
  assert.equal(views.length, 30); assert.equal(new Set(views.map(v => v.id)).size, 30);
  assert.deepEqual(views.find(v => v.id === 'embudo').data.map(r => r.value), [600, 549, 266, 77]);
  assert.equal(views.find(v => v.id === 'consultas-hora').data.reduce((n, r) => n + r.value, 0), 600);
  assert.equal(views.find(v => v.id === 'mapa-hora-dia').data.values.flat().reduce((a, b) => a + b, 0), 600);
});
test('usuarios únicos y sesiones son conteos diferentes', () => {
  const repeated = [{ ...rows[0], usuario_id: 'USR-SIM-0001' }, { ...rows[1], usuario_id: 'USR-SIM-0001' }];
  assert.equal(summarize(repeated).users, 1);
  assert.equal(summarize(repeated).sessions, 2);
  assert.equal(summarize([{ ...rows[0], usuario_id: undefined }]).users, null);
  assert.equal(summarize([]).users, 0);
});
test('filtros combinan sistema y fechas inclusivas sin mutar la fuente', () => {
  const chosen = filterRows(rows, { system: 'metro_l1', from: '2026-10-20', to: '2026-10-21' });
  assert.ok(chosen.length); assert.ok(chosen.every(r => r.sistema === 'metro_l1' && r.fecha_hora_lima >= '2026-10-20' && r.fecha_hora_lima < '2026-10-22'));
  assert.equal(rows.length, 600);
  assert.equal(filterRows(rows, { from: '2026-11-20', to: '2026-10-01' }).length, 0);
});
test('tasas respetan sus denominadores y observaciones faltantes no se convierten en cero', () => {
  const data = [{ sistema: 'metro_l1', estacion: 'A', ruta: 'R', fecha_hora_lima: '2026-11-01T08:00', recomendacion_vista: true, abordaje_confirmado: true, feedback_enviado: true, api_correcta: true, eta_pred_min: 3, eta_obs_min: 5, latencia_api_ms: 100 }, { sistema: 'metro_l1', estacion: 'A', ruta: 'R', fecha_hora_lima: '2026-11-01T09:00', recomendacion_vista: true, abordaje_confirmado: false, feedback_enviado: false, api_correcta: true, eta_pred_min: 50, eta_obs_min: null, latencia_api_ms: 200 }];
  const views = buildViews(data);
  assert.equal(summarize(data).maeEta, 2);
  assert.equal(views.find(v => v.id === 'feedback-sistema').data[0].tasa, 1);
  assert.equal(views.find(v => v.id === 'conversion-sistema').data[0].conversion, .5);
  assert.equal(views.find(v => v.id === 'eta-observado').data.length, 1);
});
test('selección vacía entrega 30 vistas vacías y medidas ausentes, sin NaN ni infinito', () => {
  assert.equal(buildViews([]).length, 30);
  const summary = summarize([]); assert.equal(summary.sessions, 0); assert.equal(summary.availability, null); assert.equal(summary.maeEta, null); assert.equal(summary.latencyP95, null);
  const walk = value => { if (typeof value === 'number') assert.ok(Number.isFinite(value)); else if (Array.isArray(value)) value.forEach(walk); else if (value && typeof value === 'object') Object.values(value).forEach(walk); };
  walk(buildViews([])); walk(buildViews(rows));
});
test('Pearson usa pares válidos y conserva n; una constante no tiene correlación definida', () => {
  const data = [{ x: 1, y: 2 }, { x: 2, y: 4 }, { x: 3, y: 6 }, { x: 100, y: null }];
  assert.deepEqual(pearsonPairs(data, r => r.x, r => r.y), { value: 1, n: 3 });
  assert.deepEqual(pearsonPairs(data, () => 1, r => r.y), { value: null, n: 3 });
  assert.deepEqual(pearsonPairs([], r => r.x, r => r.y), { value: null, n: 0 });
  assert.equal(quantile([0, 10], .95), 9.5);
});
