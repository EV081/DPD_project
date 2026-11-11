import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

async function loadHelper(relativePath) {
  const source = await readFile(new URL(relativePath, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
  return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}

const { lineasDe, origenesDe, destinosDe, seleccion, etiquetaEstacion, hoyLima, sumarDias } = await loadHelper('../src/lib/simulacion.ts');

const corredor = (id, name, ruta, orden) => ({ id, name, system: 'corredores', model_series: ruta, route_order: orden });
const ESTACIONES = [
  { id: 'Naranjal', name: 'Naranjal', system: 'metropolitano', model_series: 'Naranjal' },
  { id: 'Angamos', name: 'Angamos', system: 'metropolitano', model_series: 'Angamos' },
  { id: 'Matellini', name: 'Matellini', system: 'metropolitano', model_series: 'Matellini' },
  corredor('3BNS', 'B', '301', 1), corredor('3ANS', 'A', '301', 0), corredor('3CNS', 'C', '301', 2),
  corredor('3CSN', 'C', '301', 0), corredor('3ASN', 'A', '301', 1),
  corredor('2XEO', 'X', '201', 0), corredor('2YEO', 'Y', '201', 1),
  { id: 'AN-15', name: 'Maracuyá', system: 'alimentadores', model_series: 'Alisos' },
  { id: 'AN-15', name: 'Maracuyá', system: 'alimentadores', model_series: 'Alisos' },
  { id: 'AN-15', name: 'Huandoy', system: 'alimentadores', model_series: 'Alisos' },
];
const nombres = (opciones) => opciones.map((o) => o.estacion.id);

test('solo corredores y alimentadores piden ruta, en orden numérico', () => {
  assert.deepEqual(lineasDe(ESTACIONES, 'metropolitano'), []);
  assert.deepEqual(lineasDe(ESTACIONES, 'corredores'), ['201', '301']);
  assert.deepEqual(lineasDe(ESTACIONES, 'alimentadores'), ['Alisos']);
});

test('los orígenes de un corredor salen por sentido y en el orden del recorrido', () => {
  assert.deepEqual(nombres(origenesDe(ESTACIONES, 'corredores', '301')), ['3ANS', '3BNS', '3CNS', '3CSN', '3ASN']);
});

test('los paraderos repetidos de un alimentador se ofrecen una sola vez', () => {
  assert.deepEqual(origenesDe(ESTACIONES, 'alimentadores', 'Alisos').map((o) => o.estacion.name), ['Maracuyá', 'Huandoy']);
});

test('en un corredor solo se ofrecen destinos posteriores del mismo sentido', () => {
  const origenes = origenesDe(ESTACIONES, 'corredores', '301');
  const desde = (id) => nombres(destinosDe(origenes, ESTACIONES.find((e) => e.id === id)));
  assert.deepEqual(desde('3ANS'), ['3BNS', '3CNS']);
  assert.deepEqual(desde('3BNS'), ['3CNS']);
  assert.deepEqual(desde('3CNS'), []);
  assert.deepEqual(desde('3CSN'), ['3ASN']);
});

test('en una troncal cualquier otra estación es destino', () => {
  const origenes = origenesDe(ESTACIONES, 'metropolitano', '');
  assert.deepEqual(nombres(destinosDe(origenes, ESTACIONES[1])), ['Naranjal', 'Matellini']);
  assert.deepEqual(destinosDe(origenes, undefined), []);
});

test('la selección conserva lo válido y corrige lo que deja de serlo', () => {
  assert.deepEqual(seleccion(ESTACIONES, 'metropolitano'), { linea: '', origen: 0, destino: 2 });
  assert.deepEqual(seleccion(ESTACIONES, 'metropolitano', { origen: 1, destino: 0 }), { linea: '', origen: 1, destino: 0 });
  // el destino anterior coincide con el nuevo origen: se reemplaza
  assert.deepEqual(seleccion(ESTACIONES, 'metropolitano', { origen: 2, destino: 2 }), { linea: '', origen: 2, destino: 1 });
  // cambio de ruta: el origen de la otra ruta no sirve
  assert.deepEqual(seleccion(ESTACIONES, 'corredores', { linea: '201', origen: 4 }), { linea: '201', origen: 8, destino: 9 });
  // último paradero del sentido: no queda destino
  assert.equal(seleccion(ESTACIONES, 'corredores', { linea: '301', origen: 5 }).destino, -1);
  assert.deepEqual(seleccion([], 'metro_l1'), { linea: '', origen: -1, destino: -1 });
});

test('la etiqueta de un paradero de corredor dice su sentido', () => {
  assert.equal(etiquetaEstacion(ESTACIONES[3]), 'B · norte a sur');
  assert.equal(etiquetaEstacion(ESTACIONES[8]), 'X · este a oeste');
  assert.equal(etiquetaEstacion(ESTACIONES[0]), 'Naranjal');
});

test('fechas de Lima', () => {
  assert.equal(hoyLima(new Date('2026-11-12T03:30:00Z')), '2026-11-11');   // aún es día 11 en Lima (UTC-5)
  assert.equal(sumarDias('2026-12-20', 60), '2027-02-18');
  assert.equal(sumarDias('2025-02-28', 1), '2025-03-01');
});
