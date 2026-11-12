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

const lineasDe = (f: any): LonLat[][] => {
  const g = f?.geometry;
  if (g?.type === 'LineString') return [g.coordinates];
  if (g?.type === 'MultiLineString') return g.coordinates;
  return [];
};

// Vértices del trazado cercanos a un paradero: los más próximos (hasta `holgura` m más lejos que el mejor) y a menos de maxM
const cercanos = (linea: LonLat[], p: Punto, maxM: number, holgura = 150): { i: number; d: number }[] => {
  const todos = linea.map((c, i) => ({ i, d: metros(c, p) }));
  const mejor = Math.min(...todos.map((t) => t.d));
  if (mejor > maxM) return [];
  return todos.filter((t) => t.d <= Math.min(maxM, mejor + holgura)).sort((x, y) => x.d - y.d).slice(0, 40);
};

// Metros entre dos vértices consecutivos
const entre = (a: LonLat, b: LonLat): number => metros(a, { lat: b[1], lon: b[0] });

// Penalización de ir "contra" el sentido del trazado (se prefiere subir → bajar en el sentido de la línea)
const CONTRA_M = 20000;

/**
 * Devuelve un único Feature con el tramo subida → bajada, o null si el trazado no pasa cerca de
 * ambos paraderos (no se dibuja un trazado ajeno al viaje).
 *
 * Los trazados de OSM recorren la línea de ida y vuelta (y los servicios del Metropolitano repiten
 * tramos). Quedarse con "el vértice más cercano" a cada paradero puede caer en la ida para subir y
 * en la vuelta para bajar, y entonces el recorte incluye media línea. Por eso se evalúan varios
 * vértices candidatos y se elige el par con MENOR longitud recorrida a lo largo del trazado,
 * sumando la distancia a pie hasta la línea y penalizando ir contra el sentido.
 */
export function tramoEntre(features: any[], subida: Punto, bajada: Punto, maxM = 1000): any | null {
  let mejor: { feature: any; coords: LonLat[]; i: number; j: number; costo: number } | null = null;

  for (const f of features) {
    for (const linea of lineasDe(f)) {
      if (linea.length < 2) continue;
      const A = cercanos(linea, subida, maxM);
      const B = cercanos(linea, bajada, maxM);
      if (!A.length || !B.length) continue;
      const acum = [0];
      for (let k = 1; k < linea.length; k++) acum.push(acum[k - 1] + entre(linea[k - 1], linea[k]));
      for (const a of A) {
        for (const b of B) {
          if (a.i === b.i) continue;
          // Los corredores tienen un trazado por sentido. No invertir una calle
          // de sentido único para ofrecer un tramo de la dirección contraria.
          if (f.properties?.direccion != null && a.i > b.i) continue;
          const arco = Math.abs(acum[b.i] - acum[a.i]);
          const costo = arco + 2 * (a.d + b.d) + (a.i > b.i ? CONTRA_M : 0);
          if (!mejor || costo < mejor.costo) mejor = { feature: f, coords: linea, i: a.i, j: b.i, costo };
        }
      }
    }
  }
  if (!mejor) return null;

  const [desde, hasta] = mejor.i <= mejor.j ? [mejor.i, mejor.j] : [mejor.j, mejor.i];
  return {
    type: 'Feature',
    properties: mejor.feature.properties || {},
    geometry: { type: 'LineString', coordinates: mejor.i <= mejor.j ? mejor.coords.slice(desde, hasta + 1) : mejor.coords.slice(desde, hasta + 1).reverse() },
  };
}
