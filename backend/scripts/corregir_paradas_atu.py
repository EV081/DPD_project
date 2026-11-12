"""Reconstruye catálogos con listas ATU revisadas; nunca interpola coordenadas.

Ejecutar desde cualquier directorio. Reproducible sin red. Las paradas nuevas sin
ubicación contrastable tienen geometry=null y los consumidores del mapa las omiten.
"""
from copy import deepcopy
from difflib import SequenceMatcher
import json
from pathlib import Path
from validar_paradas_atu import ALIAS, normalizar
from extraer_horarios_atu import ALIMENTADORES
BASE=Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((BASE/path).read_text())


def write(path,value):
    (BASE/path).write_text(json.dumps(value,ensure_ascii=False,indent=1 if path=='data/horarios_servicios.json' else None)+'\n')


def canonical(name):
    name=normalizar(name)
    return ALIAS.get(name,name)


def features_for(names,old,name_key,metadata):
    """Reutiliza ubicaciones únicamente de la misma secuencia, por nombre exacto.

    Un nombre repetido sin correspondencia de secuencia queda sin coordenada;
    no se elige una esquina arbitraria por proximidad ni por similitud del nombre.
    """
    matches={}
    a=[canonical(f['properties'][name_key]) for f in old]
    b=list(map(canonical,names))
    for block in SequenceMatcher(None,a,b,autojunk=False).get_matching_blocks():
        for offset in range(block.size):matches[block.b+offset]=old[block.a+offset]
    out=[]
    for i,name in enumerate(names):
        matched=matches.get(i)
        if not matched or not matched.get('geometry'):
            candidates=[f for f in old if canonical(f['properties'][name_key])==canonical(name) and f.get('geometry')]
            locations={json.dumps(f['geometry'],sort_keys=True) for f in candidates}
            if len(locations)==1:matched=candidates[0]
        feature=deepcopy(matched or {'type':'Feature','properties':{},'geometry':None})
        props=feature['properties'];props.update(metadata);props.update({name_key:name,'orden':i+1})
        props['fuente_paradas']='ATU · Portal QR oficial · revisión 2026-11-11'
        props['estado_coordenada']='conservada_de_catalogo' if feature.get('geometry') else 'pendiente_georreferenciacion'
        out.append(feature)
    return out


def run():
    official=read('data/horarios_atu_oficial.json')['servicios']
    blocks=read('data/atu/bloques_paradas_revisados.json')
    for system,filename in [('alimentador','paradas_alimentadores.geojson'),('corredor','paradas_corredores.geojson')]:
        path='data/geo/'+filename;geo=read(path);old=geo['features'];out=[]
        for name,service in official[system].items():
            key='/'.join(ALIMENTADORES[name][0].rstrip('/').split('/')[-2:]).replace('Alimentadores','') if system=='alimentador' else name
            candidates=sorted((f for f in old if str(f['properties'].get('servicio' if system=='alimentador' else 'ruta'))==key),key=lambda f:(f['properties'].get('bloque',f['properties'].get('direccion',1)),f['properties']['orden']))
            for evidence in service['paradas_publicadas']:
                # Cada variante tiene su propia ficha: nunca concatenar punta y valle.
                variant=[f for f in candidates if f['properties'].get('pagina_atu',evidence['pagina'])==evidence['pagina']]
                index=0
                for number,names in enumerate(blocks[evidence['pagina']]['bloques'],1):
                    group=[f for f in variant if f['properties'].get('bloque' if system=='alimentador' else 'direccion',1)==number]
                    # Las imágenes conservan la secuencia completa sin inferir bloques.
                    if len(blocks[evidence['pagina']]['bloques'])==1:group=variant
                    meta={'servicio':key,'grupo':ALIMENTADORES[name][0].split('/')[1],'bloque':number} if system=='alimentador' else {'ruta':name,'direccion':number}
                    meta.update(pagina_atu=evidence['pagina'],evidencia_atu=evidence['evidencia'])
                    out.extend(features_for(names,group,'paradero',meta));index+=len(names)
        geo['features']=out;write(path,geo)
    # El planificador conserva las claves de estación del modelo y sus frecuencias.
    reviews=read('data/atu/paradas_mapas_revisadas.json')['mapas']
    legacy=read('data/horarios_servicios.json')
    model_names=read('models/troncal/model_card.json')['series']
    by_name={canonical(n):n for n in model_names}
    for review in reviews:
        if review['sistema']!='metropolitano' or not review['orden_completo']:continue
        reg=legacy['servicios']['metropolitano'].get(review['servicio'])
        if reg is None:continue  # Variante SXN22: todavía no es un servicio independiente del modelo.
        names=[by_name.get(canonical(n),n) for n in review['nombres']]
        reg.setdefault('paradas',{})[review['sentido']]=names
        if review['bidireccional']:reg['paradas']['asc']=list(reversed(names))
        reg['fuente_paradas']='ATU · mapas revisados 2026-11-11'
    write('data/horarios_servicios.json',legacy)
    # Catálogo geográfico por sentido, sin campos de pertenencia obsoletos.
    path='data/geo/puntos_metropolitano_servicios.geojson';geo=read(path)
    coords={canonical(f['properties']['estacion']):f for f in read('data/geo/puntos_troncal.geojson')['features']}
    out=[]
    for review in reviews:
        if review['sistema']!='metropolitano':continue
        slug=review['pagina'].split('?',1)[0].rsplit('/',1)[-1].removesuffix('.php')
        for index,name in enumerate(review['nombres'],1):
            f=deepcopy(coords.get(canonical(name),{'type':'Feature','properties':{},'geometry':None}))
            f['properties'].update(estacion=name,unidad=by_name.get(canonical(name),name),servicio_slug=slug,servicio_nombre=review['servicio'],otros_servicios='',orden=index,sentido=review['sentido'],bidireccional=review['bidireccional'],orden_completo=review['orden_completo'],pagina_atu=review['pagina'],evidencia_atu=review['imagen'],fuente_paradas='ATU · mapas revisados 2026-11-11',estado_coordenada='conservada_de_catalogo' if f.get('geometry') else 'pendiente_georreferenciacion')
            out.append(f)
    geo['features']=out;write(path,geo)


if __name__=='__main__':run()
