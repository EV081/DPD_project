import { readFileSync } from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import { validarDatos } from '../src/lib/bi/validation.mjs';

const escenario = JSON.parse(readFileSync(new URL('../public/simulacion/urbansafe_simulacion_600.json', import.meta.url), 'utf8'));

function comprobar(datos) {
  return validarDatos(datos);
}

test('el tablero acepta el escenario que entrega el proyecto', () => {
  assert.equal(comprobar(escenario).length, 600);
});
test('identificadores de usuario sintéticos válidos admiten varias sesiones y archivos anteriores', () => {
  const rows = [{ ...escenario[0], usuario_id: 'USR-SIM-0001' }, { ...escenario[1], usuario_id: 'USR-SIM-0001' }];
  assert.equal(validarDatos(rows).length, 2);
  const legacy = { ...escenario[0] }; delete legacy.usuario_id;
  assert.equal(validarDatos([legacy]).length, 1);
  assert.throws(() => validarDatos([{ ...escenario[0], usuario_id: 'ID-INVALIDO' }]), /usuario simulado inválido/);
});

test('el tablero rechaza sistemas y categorías de aforo ajenos al proyecto', () => {
  assert.throws(() => comprobar([{ ...escenario[0], sistema: '__proto__' }]), /sistema desconocido/);
  assert.throws(() => comprobar([{ ...escenario[0], aforo_pred: 'Alto' }]), /aforo inválido/);
});

test('el tablero rechaza fechas corruptas y escenarios excesivos', () => {
  assert.throws(() => comprobar([{ ...escenario[0], fecha_hora_lima: '2026-02-31T12:30' }]), /fecha y hora fuera de rango/);
  assert.throws(() => comprobar(Array(10001).fill(escenario[0])), /10 000 registros/);
});

test('el tablero rechaza identificadores repetidos para evitar dobles conteos', () => {
  assert.throws(() => comprobar([escenario[0], { ...escenario[0] }]), /duplicad|repetid/i);
});
