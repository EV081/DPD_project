import { readFileSync } from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildViews, filterRows, indicadores } from '../src/lib/bi/data.mjs';
import { renderChart, tableForView, formatValue } from '../src/lib/bi/charts.mjs';

const data = JSON.parse(readFileSync(new URL('../public/simulacion/urbansafe_simulacion_600.json', import.meta.url), 'utf8'));
const scenarios = {
  completo: data,
  metro: filterRows(data, { system: 'metro_l1' }),
  vacio: filterRows(data, { system: 'todos', from: '2030-01-01', to: '2030-01-02' }),
};

test('los treinta gráficos renderizan sin coordenadas inválidas con todos los datos, un sistema o una selección vacía', () => {
  for (const [name, rows] of Object.entries(scenarios)) {
    const views = buildViews(rows);
    assert.equal(views.length, 30, name);
    assert.equal(new Set(views.map(view => view.id)).size, 30, name);
    for (const view of views) {
      const markup = renderChart(view);
      assert.ok(markup.length, `${name}/${view.id}`);
      assert.doesNotMatch(markup, /NaN|Infinity|undefined/, `${name}/${view.id}`);
      for (const match of markup.matchAll(/\b(x|y|x1|x2|y1|y2|cx|cy|width|height|r|rx|fill-opacity)="([^"]*)"/g)) {
        assert.ok(Number.isFinite(Number(match[2])), `${name}/${view.id} ${match[1]}=${match[2]}`);
        if (['width', 'height', 'r', 'rx'].includes(match[1])) assert.ok(Number(match[2]) >= 0, `${name}/${view.id} ${match[1]}`);
      }
    }
  }
});

test('las tablas de todos los gráficos conservan encabezados y valores legibles', () => {
  for (const [name, rows] of Object.entries(scenarios)) for (const view of buildViews(rows)) {
    const table = tableForView(view);
    assert.ok(Array.isArray(table.rows), `${name}/${view.id}`);
    assert.ok(Array.isArray(table.headers) && table.headers.length >= (table.rows.length ? 2 : 1), `${name}/${view.id}`);
    for (const row of table.rows) {
      assert.equal(row.length, table.headers.length, `${name}/${view.id}`);
      assert.ok(row.every(value => value !== undefined && value !== null), `${name}/${view.id}`);
      assert.doesNotMatch(row.join('|'), /NaN|Infinity|undefined/, `${name}/${view.id}`);
    }
  }
});

test('las escalas porcentuales y sus tablas utilizan proporciones entre cero y uno', () => {
  for (const view of buildViews(data)) {
    const series = view.series?.length ? view.series : [{ key: 'value' }];
    if (!Array.isArray(view.data)) continue;
    for (const item of series) {
      const unit = item.axis === 'right' ? view.rightUnit : view.unit;
      if (!['%', 'percent', 'rate', 'porcentaje'].includes(unit)) continue;
      for (const row of view.data) if (row[item.key] !== null && row[item.key] !== undefined) {
        assert.ok(row[item.key] >= 0 && row[item.key] <= 1, `${view.id}/${item.key}: ${row[item.key]}`);
      }
    }
  }
  assert.equal(formatValue(.25, '%'), '25%');
  assert.equal(formatValue(1, '%'), '100%');
  assert.equal(formatValue(null, '%'), 'Sin datos');
});

test('los títulos y categorías se escapan antes de insertarlos en el gráfico', () => {
  const markup = renderChart({ type: 'bar', title: '<script>alert(1)</script>', data: [{ label: '<img src=x onerror=alert(1)>', value: 3 }] });
  assert.doesNotMatch(markup, /<script>|<img src=/);
  assert.match(markup, /&lt;script&gt;/);
});

test('los indicadores de cabecera salen de las sesiones filtradas', () => {
  const todo = indicadores(data);
  assert.equal(todo.usuarios, 600);
  assert.equal(todo.consultas, 600);
  assert.ok(todo.vistas <= todo.consultas && todo.abordajes <= todo.vistas);
  const metro = indicadores(scenarios.metro);
  assert.equal(metro.consultas, scenarios.metro.length);
  const nada = indicadores(scenarios.vacio);
  assert.equal(nada.consultas, 0);
  assert.equal(nada.tasaVistas, null);
  assert.equal(nada.errorEta, null);
});
