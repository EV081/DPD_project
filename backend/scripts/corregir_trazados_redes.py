"""Repara geometrías con segmentos existentes y secuencias revisadas en mapas ATU.
No usa líneas rectas para completar desconexiones. Reproducible sin acceso a red.
"""
from collections import defaultdict
from copy import deepcopy
import heapq
import json
from pathlib import Path
from limpiar_trazados_corredores import limpiar, distancia
from validar_paradas_atu import normalizar, ALIAS

BASE=Path(__file__).resolve().parents[1]
GEO=BASE/'data/geo'


def leer(name):
    return json.loads((GEO/name).read_text())


def guardar(name,data):
    (GEO/name).write_text(json.dumps(data,ensure_ascii=False)+'\n')


def canon(name):
    value=normalizar(name)
    return ALIAS.get(value,value)


def grafo(features):
    adj=defaultdict(dict)
    for f in features:
        g=f['geometry']
        lines=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
        for line in lines:
            for a,b in zip(line,line[1:]):
                a,b=tuple(a),tuple(b);d=distancia(a,b)
                if 0<d<=1200:
                    adj[a][b]=d;adj[b][a]=d
    return adj


def camino(adj,a,b):
    queue=[(0,a)];costs={a:0};prev={}
    while queue:
        cost,node=heapq.heappop(queue)
        if cost!=costs[node]:continue
        if node==b:
            path=[b]
            while path[-1]!=a:path.append(prev[path[-1]])
            return list(reversed(path))
        for dest,weight in adj[node].items():
            new=cost+weight
            if new<costs.get(dest,float('inf')):
                costs[dest]=new;prev[dest]=node;heapq.heappush(queue,(new,dest))
    return None


def run():
    previous_path=BASE/'data/atu/correccion_trazados_redes.json'
    previous=json.loads(previous_path.read_text()) if previous_path.exists() else {}
    previous_feeders={(r['ruta'],r['sentido']):r for r in previous.get('alimentadores',[])}
    report={'metropolitano':[],'alimentadores':[],'linea_1':{}}
    # Los extremos de ambos archivos coinciden exactamente: no insertar ningún segmento.
    rail=leer('trazado_metro_l1.geojson')
    if len(rail['features'])==2:
        a,b=(f['geometry']['coordinates'] for f in rail['features'])
        if a[-1]!=b[0]:raise ValueError('Los tramos de Línea 1 no conectan: requiere revisión')
        f=deepcopy(rail['features'][0]);f['geometry']['coordinates']=a+b[1:]
        f['properties'].update(fuente_secuencia='https://portal.atu.gob.pe/QR/MetroLima/L1/',nota='Tramos consecutivos unidos en su extremo común, sin agregar geometría.')
        rail['features']=[f];guardar('trazado_metro_l1.geojson',rail)
    report['linea_1']={'trazos_continuos':len(rail['features']),'fuente':'https://portal.atu.gob.pe/QR/MetroLima/L1/'}
    # Recorridos revisados visualmente: usar sus estaciones en orden sobre calles BRT existentes.
    metro=leer('trazados_metropolitano_servicios.geojson');adj=grafo(metro['features'])
    stations={canon(f['properties']['estacion']):f['geometry']['coordinates'] for f in leer('puntos_troncal.geojson')['features']}
    reviews=json.loads((BASE/'data/atu/paradas_mapas_revisadas.json').read_text())['mapas']
    originals={f['properties']['servicio_slug']:f for f in metro['features']}
    output=[]
    for review in reviews:
        if review['sistema']!='metropolitano':continue
        slug=review['pagina'].split('?',1)[0].rsplit('/',1)[-1].removesuffix('.php')
        nodes=[]
        for name in review['nombres']:
            coordinate=stations.get(canon(name))
            if coordinate is None:raise ValueError('Estación sin ubicación: '+name)
            node=min(adj,key=lambda n:distancia(n,coordinate))
            if distancia(node,coordinate)>250:raise ValueError('Estación lejos del trazado: '+name)
            nodes.append(node)
        lines=[];part=[];missing=[]
        for index,(a,b) in enumerate(zip(nodes,nodes[1:])):
            if not review['orden_completo'] and {canon(n) for n in review['nombres'][index:index+2]} == {'espana','estacion central'}:
                if len(part)>1:lines.append(part)
                part=[]
                continue
            path=camino(adj,a,b)
            if path is None:
                if len(part)>1:lines.append(part)
                part=[];missing.append([list(a),list(b)]);continue
            part.extend(path if not part else path[1:])
        if len(part)>1:lines.append(part)
        if not lines:raise ValueError('Servicio sin trazado: '+slug)
        properties={'servicio_slug':slug,'servicio_nombre':review['servicio'],'color_hex':'#1f4e79','fuente_secuencia':review['imagen'],
                    'fuente_geometria':'Segmentos OSM existentes; sin conexiones rectas mayores de 1200 m',
                    'orden_completo':review['orden_completo'],'sentido':review['sentido'],'bidireccional':review['bidireccional'],'tramos_sin_conexion':len(missing)}
        output.append({'type':'Feature','properties':properties,'geometry':{'type':'MultiLineString','coordinates':lines}})
        report['metropolitano'].append({'servicio':slug,'estado':'reconstruido_por_estaciones_atu','conexiones_pendientes':missing,'fuente':review['imagen']})
    metro['features']=output;guardar('trazados_metropolitano_servicios.geojson',metro)
    regular_c=next(f for f in output if f['properties']['servicio_slug']=='RegularC')
    troncal=leer('trazado_troncal.geojson');troncal['features']=[deepcopy(regular_c)];guardar('trazado_troncal.geojson',troncal)
    # Alimentadores: retirar únicamente lazos redundantes con control de cercanía a paradas.
    feeders=leer('trazados_alimentadores_atu.geojson');stops=leer('paradas_alimentadores.geojson')['features']
    archived=[]
    active=[]
    official_keys={s['properties'].get('servicio') for s in stops}
    for f in feeders['features']:
        key=f['properties']['ruta']
        if key not in official_keys:
            archived.append(f)
            report['alimentadores'].append({'ruta':key,'sentido':f['properties']['direccion'],'estado':'archivado_sin_ficha_vigente_en_catalogo_revisado'})
            continue
        active.append(f)
        if f['properties'].get('limpieza','').startswith('Lazos redundantes retirados'):
            report['alimentadores'].append(previous_feeders.get((key,f['properties']['direccion']),{'ruta':key,'sentido':f['properties']['direccion'],'estado':'limpieza_previa_conservada'}))
            continue
        points=[s['geometry']['coordinates'] for s in stops if s.get('geometry') and s['properties'].get('servicio')==key]
        if not points:
            report['alimentadores'].append({'ruta':key,'sentido':f['properties']['direccion'],'estado':'sin_paradas_geolocalizadas_para_comprobar'});continue
        cleaned,count=limpiar(f['geometry']['coordinates'],points)
        f['geometry']['coordinates']=cleaned
        f['properties']['limpieza']='Lazos redundantes retirados; conserva segmentos existentes y cercanía a paraderos, tolerancia 35 m.'
        report['alimentadores'].append({'ruta':key,'sentido':f['properties']['direccion'],'desvios_eliminados':count})
    feeders['features']=active
    if archived:
        (BASE/'data/atu/trazados_alimentadores_sin_ficha.json').write_text(json.dumps({'nota':'Trazados antiguos excluidos del mapa: sin ficha vigente en el catálogo ATU revisado. Carabayllo y Collique vigentes usan LosIncas, no Norte. Santo Domingo y Tungasuca no tienen serie de modelo ni ficha en el catálogo consultado.','features':archived},ensure_ascii=False)+'\n')
    guardar('trazados_alimentadores_atu.geojson',feeders)
    (BASE/'data/atu/correccion_trazados_redes.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Servicios Metropolitano:',len(output),'Desvíos alimentadores eliminados:',sum(r.get('desvios_eliminados',0) for r in report['alimentadores']))


if __name__=='__main__':run()
