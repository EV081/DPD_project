import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

// Usa TypeScript ya instalado para ejecutar los helpers puros; no requiere navegador
// ni un framework adicional. Ejecutar desde frontend: node --test tests/*.test.mjs
async function loadHelper(relativePath) {
  const source = await readFile(new URL(relativePath, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}

const { createRequestGate, initialWalkingRoute, boardingWaitMinutes } = await loadHelper('../src/lib/ui-state.ts');
const { textoAjusteEspera } = await loadHelper('../src/lib/aforo.ts');

test('una respuesta lenta no reemplaza el último destino elegido', async () => {
  const requests = createRequestGate();
  const displayed = [];
  let finishOld;
  const oldServer = new Promise(resolve => { finishOld = resolve; });
  const oldIsCurrent = requests.begin();
  const oldRequest = oldServer.then(value => { if (oldIsCurrent()) displayed.push(value); });
  const newIsCurrent = requests.begin();
  if (newIsCurrent()) displayed.push('destino nuevo');
  finishOld('destino anterior');
  await oldRequest;
  assert.deepEqual(displayed, ['destino nuevo']);
});

test('enviar o cerrar invalida sugerencias pendientes sin impedir una búsqueda posterior', () => {
  const requests = createRequestGate();
  const pendingSuggestion = requests.begin();
  requests.cancel();
  assert.equal(pendingSuggestion(), false);
  const nextSearch = requests.begin();
  assert.equal(nextSearch(), true);
  assert.equal(pendingSuggestion(), false);
});

test('la caminata inicial respeta normal, segura y ruta única del servidor', () => {
  assert.equal(initialWalkingRoute('normal'), 'normal');
  assert.equal(initialWalkingRoute('segura'), 'segura');
  assert.equal(initialWalkingRoute('misma'), 'normal');
});

test('la espera usa el instante de abordar y no el tiempo adicional del formulario', () => {
  const consulted = 1_000_000;
  const boarded = consulted + 3 * 60_000;
  const sentLater = boarded + 7 * 60_000;
  assert.equal(boardingWaitMinutes(consulted, boarded), 3);
  assert.notEqual(boardingWaitMinutes(consulted, boarded), boardingWaitMinutes(consulted, sentLater));
  assert.equal(boardingWaitMinutes(consulted, consulted - 5000), 0);
  assert.equal(boardingWaitMinutes(consulted, consulted + 200 * 60_000), 180);
});

test('solo la fuente en vivo se presenta como tráfico en vivo', () => {
  const base = { eta_min: 9, eta_base_min: 5, factor_trafico: 1.8 };
  assert.match(textoAjusteEspera({ ...base, modo_datos: 'en_vivo' }), /Tráfico en vivo/);
  assert.match(textoAjusteEspera({ ...base, modo_datos: 'reciente' }), /Tráfico reciente/);
  assert.doesNotMatch(textoAjusteEspera({ ...base, modo_datos: 'historico' }), /en vivo/);
  assert.doesNotMatch(textoAjusteEspera({ ...base, modo_datos: 'en_vivo', factor_calibracion: 1.2 }), /Tráfico en vivo/);
  assert.equal(textoAjusteEspera({ eta_min: null, eta_base_min: 5 }), null);
  assert.equal(textoAjusteEspera({ eta_min: 5, eta_base_min: 5 }), null);
});
