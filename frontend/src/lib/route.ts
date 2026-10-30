// Recorta el trazado de una ruta al tramo que el usuario realmente viaja:
// desde el paradero de subida hasta el de bajada.

type LonLat = [number, number];
interface Punto { lat: number; lon: number }

// Distancia en metros (aproximación plana, suficiente a escala de ciudad)
const metros = (a: LonLat, p: Punto): number => {
  const dx = (a[0] - p.lon) * 111320 * Math.cos((p.lat * Math.PI) / 180);
  const dy = (a[1] - p.lat) * 110540;
  return Math.hypot(dx, dy);
};

const masCercano = (linea: LonLat[], p: Punto): { i: number; d: number } => {
  let best = { i: 0, d: Infinity };
  linea.forEach((c, i) => {
    const d = metros(c, p);
    if (d < best.d) best = { i, d };
  });
  return best;
};

const lineasDe = (f: any): LonLat[][] => {
  const g = f?.geometry;
  if (g?.type === 'LineString') return [g.coordinates];
  if (g?.type === 'MultiLineString') return g.coordinates;
  return [];
};

/**
 * Devuelve un único Feature con el tramo subida → bajada, o null si el trazado no pasa cerca de
 * ambos paraderos (entonces conviene mostrar la ruta completa).
 * Entre varias líneas candidatas (sentidos, servicios) elige la que pasa más cerca de ambos y,
 * a igualdad, la que recorre subida → bajada en el sentido del trazado.
 */
export function tramoEntre(features: any[], subida: Punto, bajada: Punto, maxM = 1000): any | null {
  let mejor: { feature: any; coords: LonLat[]; i: number; j: number; costo: number; contra: boolean } | null = null;

  for (const f of features) {
    for (const linea of lineasDe(f)) {
      if (linea.length < 2) continue;
      const a = masCercano(linea, subida);
      const b = masCercano(linea, bajada);
      if (a.d > maxM || b.d > maxM || a.i === b.i) continue;
      const cand = { feature: f, coords: linea, i: a.i, j: b.i, costo: a.d + b.d, contra: a.i > b.i };
      if (!mejor || (cand.contra ? 1 : 0) < (mejor.contra ? 1 : 0) ||
          (cand.contra === mejor.contra && cand.costo < mejor.costo)) mejor = cand;
    }
  }
  if (!mejor) return null;

  const [desde, hasta] = mejor.i <= mejor.j ? [mejor.i, mejor.j] : [mejor.j, mejor.i];
  return {
    type: 'Feature',
    properties: mejor.feature.properties || {},
    geometry: { type: 'LineString', coordinates: mejor.coords.slice(desde, hasta + 1) },
  };
}
