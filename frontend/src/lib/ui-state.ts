// Cada búsqueda recibe una comprobación de vigencia. Una nueva búsqueda o cerrar
// la vista invalida la anterior, aunque el servidor termine de responder después.
export function createRequestGate() {
  let version = 0;
  return {
    begin() {
      const requestVersion = ++version;
      return () => requestVersion === version;
    },
    cancel() { version++; },
  };
}

export function initialWalkingRoute(recommended: 'normal' | 'segura' | 'misma'): 'normal' | 'segura' {
  return recommended === 'segura' ? 'segura' : 'normal';
}

export function boardingWaitMinutes(consultedAt: number, boardedAt: number): number {
  return Math.max(0, Math.min((boardedAt - consultedAt) / 60000, 180));
}
