import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { filterRows, summarize } from '../src/lib/bi/data.mjs';
import { validarDatos } from '../src/lib/bi/validation.mjs';

const leer = (ruta) => readFile(new URL(ruta, import.meta.url), 'utf8');
const rows = JSON.parse(await leer('../public/simulacion/urbansafe_simulacion_600.json'));
const resumen = JSON.parse(await leer('../public/simulacion/resumen_simulacion_600.json'));
const SISTEMAS = ['metro_l1', 'metropolitano', 'corredores', 'alimentadores'];

test('la muestra tiene 600 usuarios distintos, uno por sesión', () => {
  assert.equal(validarDatos(rows).length, 600);
  assert.equal(new Set(rows.map((r) => r.usuario_id)).size, 600);
  assert.equal(new Set(rows.map((r) => r.sesion_id)).size, 600);
  assert.ok(rows.every((r) => /^USR-SIM-\d{4}$/.test(r.usuario_id)));
});

test('dos sesiones del mismo usuario cuentan 1 usuario y 2 consultas', () => {
  const repetidas = [{ ...rows[0], usuario_id: 'USR-SIM-0001' }, { ...rows[1], usuario_id: 'USR-SIM-0001' }];
  const r = summarize(repetidas);
  assert.equal(r.users, 1);
  assert.equal(r.sessions, 2);
});

test('sin usuario_id el conteo de usuarios no está disponible, no es cero', () => {
  const antiguas = rows.slice(0, 5).map(({ usuario_id, ...resto }) => resto);
  const r = summarize(antiguas);
  assert.equal(r.users, null);
  assert.equal(r.sessions, 5);
  // una sola fila sin identificador invalida el conteo completo
  const mixtas = [...rows.slice(0, 3), { ...rows[3], usuario_id: '' }];
  assert.equal(summarize(mixtas).users, null);
});

test('los usuarios por sistema suman 600 y Metro L1 tiene 207', () => {
  const por = Object.fromEntries(SISTEMAS.map((s) => [s, summarize(filterRows(rows, { system: s })).users]));
  assert.equal(por.metro_l1, 207);
  assert.equal(SISTEMAS.reduce((n, s) => n + por[s], 0), 600);
  assert.deepEqual(por, resumen.indicadores_control.por_sistema);
});

test('el filtro por fechas recalcula usuarios y no supera el total', () => {
  const dias = [...new Set(rows.map((r) => r.fecha_hora_lima.slice(0, 10)))].sort();
  const medio = dias[Math.floor(dias.length / 2)];
  const mitad = summarize(filterRows(rows, { to: medio }));
  const resto = summarize(filterRows(rows, { from: medio }));
  assert.ok(mitad.users > 0 && mitad.users < 600);
  assert.ok(mitad.users + resto.users >= 600); // el día de corte entra en ambos
});

test('JSON y resumen coinciden en el embudo de 600 usuarios', () => {
  const ic = resumen.indicadores_control;
  const r = summarize(rows);
  assert.equal(resumen.metadatos.usuarios_simulados, 600);
  assert.equal(ic.usuarios_simulados, r.users);
  assert.equal(ic.consultas, r.sessions);
  assert.equal(ic.recomendaciones_vistas, r.recommendations);
  assert.equal(ic.abordajes_confirmados, r.boardings);
  assert.equal(ic.feedback, r.feedback);
});

test('el CSV generado coincide con el JSON servido', async () => {
  const lineas = (await leer('../../analytics/output/urbansafe_simulacion_600.csv')).replace(/^﻿/, '').trim().split(/\r?\n/);
  const cab = lineas[0].split(',');
  const iu = cab.indexOf('usuario_id'), is = cab.indexOf('sesion_id');
  assert.equal(lineas.length - 1, 600);
  assert.deepEqual(lineas.slice(1).map((l) => l.split(',')[iu]), rows.map((r) => r.usuario_id));
  assert.deepEqual(lineas.slice(1).map((l) => l.split(',')[is]), rows.map((r) => r.sesion_id));
});
