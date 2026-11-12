"""Quita desvíos cerrados redundantes de trazados derivados, sin crear segmentos.

Solo une vértices exactamente iguales. Conserva los extremos y la cercanía (tolerancia adicional de 35 m)
a cada paradero localizado. Los bucles que sirven paraderos
se conservan. No convierte un trazado OSRM en un recorrido oficial ATU.
"""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def distancia(a, b):
    return math.hypot((a[0]-b[0])*111320*math.cos(math.radians(b[1])), (a[1]-b[1])*110540)


def limpiar(coords, paradas):
    if len(coords) < 3:
        return coords, 0
    referencias = []
    for parada in paradas:
        indice = min(range(len(coords)), key=lambda i: distancia(coords[i], parada))
        d = distancia(coords[indice], parada)
        if d <= 150:
            referencias.append((parada, d + 35))
    # Mantener índices originales permite conservar los segmentos originales.
    indices = list(range(len(coords)))
    quitados = 0
    while True:
        posiciones = defaultdict(list)
        for k, indice in enumerate(indices):
            posiciones[tuple(coords[indice])].append(k)
        candidatos = sorted(((b-a, a, b) for posiciones_iguales in posiciones.values()
                             for a, b in zip(posiciones_iguales, posiciones_iguales[1:]) if b-a > 1), reverse=True)
        for _, a, b in candidatos:
            # Un giro necesario para llegar a un paradero no se borra.
            candidato = indices[:a+1] + indices[b+1:]
            if any(min(distancia(coords[i], parada) for i in candidato) > limite
                   for parada, limite in referencias):
                continue
            indices = candidato
            quitados += 1
            break
        else:
            break
    result = [coords[i] for i in indices]
    assert result[0] == coords[0] and result[-1] == coords[-1]
    assert all(min(distancia(c, parada) for c in result) <= limite for parada, limite in referencias)
    # Todas las uniones nuevas enlazan una misma coordenada: no hay atajos rectos.
    original_edges = {(tuple(a),tuple(b)) for a,b in zip(coords,coords[1:])}
    assert all((tuple(a),tuple(b)) in original_edges for a,b in zip(result,result[1:]))
    return result, quitados


def run():
    path = BASE/'data/geo/trazados_corredores.geojson'
    original = path.read_bytes()
    geo = json.loads(original)
    stops = json.loads((BASE/'data/geo/paradas_corredores.geojson').read_text())['features']
    model_stops = json.loads((BASE/'data/geo/puntos_corredores.geojson').read_text())['features']
    report = []
    for feature in geo['features']:
        props = feature['properties']
        route, direction = str(props['ruta']), str(props['direccion'])
        # Proteger también los puntos del modelo: algunas fichas nuevas aún no tienen ubicación.
        paradas = [f['geometry']['coordinates'] for f in stops
                   if str(f['properties'].get('ruta')) == route
                   and str(f['properties'].get('direccion')) == direction and f.get('geometry')]
        paradas += [f['geometry']['coordinates'] for f in model_stops
                    if str(f['properties'].get('ruta')) == route and f.get('geometry')]
        coords = feature['geometry']['coordinates']
        result, count = limpiar(coords, paradas)
        report.append({'ruta':route, 'sentido':direction, 'vertices_antes':len(coords),
                       'vertices_despues':len(result), 'desvios_redundantes_eliminados':count,
                       'paraderos_con_ubicacion_protegidos':len(paradas)})
        if count:
            feature['geometry']['coordinates'] = result
            props['n_puntos'] = len(result)
            props['limpieza'] = 'Sin desvíos cerrados redundantes que omiten paraderos; conserva calles y extremos; tolerancia adicional máxima de 35 m a paraderos.'
    if any(r['desvios_redundantes_eliminados'] for r in report):
        path.write_text(json.dumps(geo, ensure_ascii=False)+'\n')
        output = {'sha256_entrada':hashlib.sha256(original).hexdigest(),
                  'alcance':'32 trazados: 16 corredores, dos sentidos. Conserva cercanía a paraderos (máximo 35 m adicionales) y segmentos originales. No certifica rutas oficiales.',
                  'trazados':report}
        (BASE/'data/atu/limpieza_trazados_corredores.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'trazados':len(report),'corregidos':sum(r['desvios_redundantes_eliminados']>0 for r in report),
                      'desvios_eliminados':sum(r['desvios_redundantes_eliminados'] for r in report)}))


if __name__ == '__main__':
    run()
