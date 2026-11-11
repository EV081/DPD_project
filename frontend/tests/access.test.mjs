import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

async function loadHelper(relativePath) {
  const source = await readFile(new URL(relativePath, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
  return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}

const { isAdminRoute, destinoAdmin } = await loadHelper('../src/lib/access.ts');

test('el panel es ruta de administración; la simulación y el resto no', () => {
  for (const ruta of ['/dashboard', '/dashboard/extra']) assert.equal(isAdminRoute(ruta), true, ruta);
  for (const ruta of ['/map', '/account', '/destinations', '/simulacion', '/dashboardx', '/']) assert.equal(isAdminRoute(ruta), false, ruta);
});

test('?continuar solo acepta destinos de administración conocidos', () => {
  assert.equal(destinoAdmin('dashboard'), '/dashboard');
  assert.equal(destinoAdmin('/dashboard'), '/dashboard');
  for (const malo of [null, '', 'map', 'simulacion', 'https://evil.example', '//evil.example', '../account', 'simulacion/../x']) assert.equal(destinoAdmin(malo), null, String(malo));
});
