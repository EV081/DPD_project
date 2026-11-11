// El campo vacío conserva el criterio original del planificador.
export function parseWalkingLimit(raw: string): number | null {
  if (!raw.trim()) return null;
  const value = Number(raw);
  if (!Number.isFinite(value) || value < 0) {
    throw new Error('Escribe cero o más minutos, o deja el campo vacío para usar el criterio habitual.');
  }
  return value;
}
