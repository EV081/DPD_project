import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';
async function load(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
  return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}
const { visibleStations } = await load('../src/lib/map-stations.ts');
const { encodeCsv } = await load('../src/lib/csv.ts');
const stations = [
  { id:'metro', system:'metro_l1', latitude:0, longitude:0 },
  { id:'bus', system:'corredores', latitude:1, longitude:1 },
  { id:'outside', system:'metropolitano', latitude:9, longitude:9 },
];
test('el mapa respeta selección del viaje aunque esté fuera de la vista', () => {
  assert.deepEqual(visibleStations(stations, ['outside'], false, 10, () => false).map((s) => s.id), ['outside']);
  assert.deepEqual(visibleStations(stations, [], true, 15, () => true), []);
});
test('el mapa filtra por visibilidad y zoom sin ocultar estaciones seleccionadas', () => {
  const contains = (lat) => lat < 5;
  assert.deepEqual(visibleStations(stations, null, false, 15, contains), []);
  assert.deepEqual(visibleStations(stations, null, true, 12, contains).map((s) => s.id), ['metro']);
  assert.deepEqual(visibleStations(stations, null, true, 13, contains).map((s) => s.id), ['metro', 'bus']);
});
test('CSV conserva cifras, comillas y saltos y neutraliza fórmulas en cadenas', () => {
  const csv = encodeCsv(['Nombre','Valor'], [['a,"b"', 0], ['=1+1', -2], ['  @SUM(A1)', null]]);
  assert.ok(csv.startsWith('\uFEFF'));
  assert.ok(csv.includes('"a,""b""","0"'));
  assert.ok(csv.includes('"\'=1+1","-2"'));
  assert.ok(csv.includes('"\'  @SUM(A1)",""'));
  assert.equal(csv.split('\r\n').length, 4);
});
