import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

async function loadHelper(relativePath) {
  const source = await readFile(new URL(relativePath, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}

const { tripRouteKey, comparedRoutes, formatMinutes, ROUTE_PAGE_SIZE, routeServiceLabel, tripRouteLabel } = await loadHelper('../src/lib/trip-comparison.ts');
const { parseWalkingLimit } = await loadHelper('../src/lib/walking-preferences.ts');

const route = {
  type: 'DIRECTO_POR_RUTA', system: 'corredores', route_code: '301',
  boarding_id: 'a', leaving_id: 'b', boarding_station: 'Origen', leaving_station: 'Destino',
  origin_walk_m: 100, dest_walk_m: 80,
};

test('la selección conserva el recorrido al mostrar más opciones o cambiar estimaciones', () => {
  const routes = Array.from({ length: 13 }, (_, index) => ({ ...route, leaving_id: `b${index}` }));
  const selectedKeys = [tripRouteKey(routes[4]), tripRouteKey(routes[1])];
  assert.deepEqual(comparedRoutes(routes.slice(0, ROUTE_PAGE_SIZE), selectedKeys), [routes[4], routes[1]]);
  assert.deepEqual(comparedRoutes(routes.slice(0, ROUTE_PAGE_SIZE * 2), selectedKeys), [routes[4], routes[1]]);
  const updated = routes.map(item => ({ ...item, espera_min: 5, viaje_min: 20 }));
  assert.deepEqual(comparedRoutes(updated.toReversed(), selectedKeys).map(item => item.leaving_id), ['b4', 'b1']);
});

test('rutas y transbordos distintos no comparten selección aunque usen el mismo paradero', () => {
  assert.notEqual(tripRouteKey(route), tripRouteKey({ ...route, route_code: '302' }));
  const transfer = { ...route, type: 'TRANSBORDO', transbordo: { system: 'metropolitano', route_code: 'A', boarding_id: 'c', leaving_id: 'd' } };
  assert.notEqual(tripRouteKey(transfer), tripRouteKey({ ...transfer, transbordo: { ...transfer.transbordo, leaving_id: 'e' } }));
  assert.deepEqual(comparedRoutes([route], [tripRouteKey(transfer)]), []);
});

test('un dato ausente no se convierte en cero; un cero informado sigue siendo válido', () => {
  for (const value of [undefined, null, NaN, Infinity, -1]) assert.equal(formatMinutes(value), 'No disponible');
  assert.equal(formatMinutes(0), '0 min');
  assert.equal(formatMinutes(5), '5 min');
});

test('el límite vacío preserva la configuración y cero no se interpreta como ausencia', () => {
  assert.equal(parseWalkingLimit(''), null);
  assert.equal(parseWalkingLimit('  '), null);
  assert.equal(parseWalkingLimit('0'), 0);
  assert.equal(parseWalkingLimit('2.5'), 2.5);
  assert.equal(parseWalkingLimit('120'), 120);
});

test('el límite rechaza valores negativos o no finitos antes de consultar al servidor', () => {
  for (const value of ['-1', 'Infinity', 'NaN', 'abc', '1e999']) {
    assert.throws(() => parseWalkingLimit(value), /cero o más minutos/);
  }
});

test('el Metropolitano dice qué servicio tomar, no "Ruta METROPOLITANO"', () => {
  const metro = { ...route, type: 'DIRECTO_POR_SISTEMA', system: 'metropolitano', route_code: 'METROPOLITANO',
    boarding_station: 'Canaval y Moreyra', leaving_station: 'España' };
  assert.equal(routeServiceLabel(metro), null);
  const conServicio = { ...metro, servicio_troncal: { texto: 'Expreso 5 o Expreso 9', sentido: 'desc', transbordos: 0, tramos: [] } };
  assert.equal(routeServiceLabel(conServicio), 'Expreso 5 o Expreso 9');
  assert.equal(tripRouteLabel(conServicio), 'Expreso 5 o Expreso 9 · Canaval y Moreyra → España');
  assert.equal(routeServiceLabel(route), 'Ruta 301');
  assert.equal(routeServiceLabel({ ...metro, system: 'metro_l1', route_code: 'METRO_L1' }), null);
});
