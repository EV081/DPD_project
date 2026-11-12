import type { StyleSpecification } from 'maplibre-gl';

/** Paleta de movilidad: la base cede protagonismo a las rutas y paraderos de UrbanSafe. */
export function mobilityStyle(source: StyleSpecification, dark: boolean): StyleSpecification {
  const colors = dark
    ? { land: '#151c26', block: '#1b2430', building: '#202c39', road: '#374454', edge: '#202a36', water: '#102b3c', park: '#1b302d', text: '#9eafbf', halo: '#151c26' }
    : { land: '#eef0f2', block: '#e7eaed', building: '#e0e4e8', road: '#ffffff', edge: '#d5dce2', water: '#cadfe9', park: '#dce7e0', text: '#667786', halo: '#f7f9fa' };
  return { ...source, name: `UrbanSafe · ${dark ? 'Noche' : 'Día'}`, layers: source.layers.map((layer) => {
    const id = `${layer.id} ${'source-layer' in layer ? layer['source-layer'] : ''}`.toLowerCase();
    const paint: Record<string, unknown> = { ...layer.paint };
    const layout: Record<string, unknown> = { ...layer.layout };
    // Fuera iconos comerciales, escudos de carretera y detalles que distraen de la ruta.
    if (/poi|shield|housenumber|aeroway|aerodrome|railway|transit/.test(id)) layout.visibility = 'none';
    if (layer.type === 'background') paint['background-color'] = colors.land;
    if (layer.type === 'fill') {
      paint['fill-color'] = /water/.test(id) ? colors.water : /park|wood|grass|landcover/.test(id) ? colors.park : /building/.test(id) ? colors.building : colors.block;
      paint['fill-outline-color'] = paint['fill-color'];
      if (/building/.test(id)) paint['fill-opacity'] = 0.55;
    }
    if (layer.type === 'line') {
      paint['line-color'] = /water/.test(id) ? colors.water : /boundary/.test(id) ? colors.edge : /casing|outline|border/.test(id) ? colors.edge : /road|transportation|highway|street|bridge|tunnel/.test(id) ? colors.road : colors.edge;
      if (/boundary/.test(id)) paint['line-opacity'] = 0.3;
    }
    if (layer.type === 'symbol') {
      paint['text-color'] = colors.text;
      paint['text-halo-color'] = colors.halo;
      paint['text-halo-width'] = 1.5;
      layout['text-allow-overlap'] = false;
      if (/transportation_name|road|highway/.test(id)) {
        layout['symbol-spacing'] = 450;
        layout['text-size'] = ['interpolate', ['linear'], ['zoom'], 12, 10, 17, 12];
      }
    }
    return { ...layer, paint, layout } as typeof layer;
  }) };
}
