"""Audita nombres y orden frente a fichas ATU. Nunca certifica coordenadas por coincidencia de nombre.

Entrada: horarios_atu_oficial.json, paradas_alimentadores.geojson, paradas_corredores.geojson.
Salida: data/atu/validacion_paradas.json + docs/VALIDACION_PARADAS_ATU.md.
"""
from collections import Counter
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
import unicodedata
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'scripts'))
from extraer_horarios_atu import ALIMENTADORES


def normalizar(s):
    s=''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))
    s=re.sub(r'\((?:inicial|final|inicio)\)','',s)
    return ' '.join(re.sub(r'[^\w\s]',' ',s).split())


def comparar(actual,oficial):
    a,b=list(map(normalizar,actual)),list(map(normalizar,oficial))
    ca,cb=Counter(a),Counter(b)
    return {'coincide_secuencia_completa':a==b,'n_actual':len(a),'n_oficial':len(b),
            'coincidencias_en_orden':sum(x.size for x in SequenceMatcher(None,a,b,autojunk=False).get_matching_blocks()),
            'faltan_en_catalogo':list((cb-ca).elements()),'sobran_en_catalogo':list((ca-cb).elements()),
            'secuencia_actual':actual,'secuencia_oficial':oficial}


# Equivalencias de escritura concretas; no se aprueban coincidencias difusas.
ALIAS={
    'm grau':'miguel grau','arriola':'nicolas arriola',
    'canaval moreyra':'canaval y moreyra','canavaly moreyra':'canaval y moreyra',
    '2 de mayo':'dos de mayo','dos mayo':'dos de mayo',
    'estadio union':'union','boulevar':'bulevar',
    'parque trabajo':'parque del trabajo','jiron union':'jiron de la union',
    'plaza flores':'plaza de flores',
}

def comparar_estaciones(actual,oficial):
    def canonical(value):
        value=normalizar(value)
        return ALIAS.get(value,value)
    c=comparar([canonical(v) for v in actual],[canonical(v) for v in oficial])
    c.update(secuencia_actual=actual,secuencia_oficial=oficial)
    return c


def run():
    official=json.loads((BASE/'data/horarios_atu_oficial.json').read_text())
    feeder=json.loads((BASE/'data/geo/paradas_alimentadores.geojson').read_text())['features']
    corridor=json.loads((BASE/'data/geo/paradas_corredores.geojson').read_text())['features']
    results=[]
    for sistema in ('alimentador','corredor'):
        for nombre,ficha in official['servicios'][sistema].items():
            if sistema=='alimentador':
                parts=ALIMENTADORES[nombre][0].rstrip('/').split('/')
                servicio=parts[-2].removeprefix('Alimentadores')+'/'+parts[-1]
                actual=sorted((f['properties'] for f in feeder if f['properties']['servicio']==servicio),key=lambda p:(p['bloque'],p['orden']))
            else:
                servicio=nombre
                actual=sorted((f['properties'] for f in corridor if str(f['properties']['ruta'])==nombre),key=lambda p:(p['direccion'],p['orden']))
            current=[p['paradero'] for p in actual]
            for evidence in ficha.get('paradas_publicadas',[]):
                stops=evidence['nombres_en_orden']
                selected=[p for p in actual if p.get('pagina_atu',evidence['pagina'])==evidence['pagina']]
                current=[p['paradero'] for p in selected]
                comparison=comparar(current,stops) if stops else None
                state='coincide_nombre_y_orden' if comparison and comparison['coincide_secuencia_completa'] else 'discrepancias' if stops and current else 'sin_catalogo_local' if stops else 'sin_lista_publicada_extraible'
                results.append({'sistema':sistema,'servicio':nombre,'clave_geografica':servicio,'pagina':evidence['pagina'],
                                'evidencia':evidence['evidencia'],'metodo':evidence['metodo'],'estado':state,
                                'comparacion':comparison,'coordenadas':'No certificadas por esta validación; conservar precisión/procedencia del GeoJSON.'})
    reviews=json.loads((BASE/'data/atu/paradas_mapas_revisadas.json').read_text())['mapas']
    legacy=json.loads((BASE/'data/horarios_servicios.json').read_text())['servicios']['metropolitano']
    metro=json.loads((BASE/'data/geo/puntos_metropolitano_servicios.geojson').read_text())['features']
    l1=json.loads((BASE/'data/geo/puntos_metro_l1.geojson').read_text())['features']
    for evidence in reviews:
        sistema,nombre=evidence['sistema'],evidence['servicio']
        directions=[evidence['sentido']]
        if evidence['bidireccional']:directions.append('asc')
        for direction in directions:
            stops=evidence['nombres'] if direction==evidence['sentido'] else list(reversed(evidence['nombres']))
            # El planificador usa asc = sur a norte, desc = norte a sur.
            current=legacy.get(nombre,{}).get('paradas',{}).get(direction,[]) if sistema=='metropolitano' else [f['properties']['estacion'] for f in l1][::1 if direction=='asc' else -1]
            c=comparar_estaciones(current,stops)
            state=('coincide_nombre_y_orden' if c['coincide_secuencia_completa'] else 'discrepancias') if evidence['orden_completo'] else 'orden_parcial_en_fuente'
            results.append({'sistema':sistema,'servicio':nombre,'sentido':direction,'catalogo':'planificador' if sistema=='metropolitano' else 'geo_linea_1',
                            'pagina':evidence['pagina'],'evidencia':evidence['imagen'],'sha256':evidence['sha256'],'metodo':evidence['metodo'],
                            'estado':'sin_catalogo_local' if not current else state,'orden_completo_en_fuente':evidence['orden_completo'],'nota':evidence.get('nota'),
                            'comparacion':c,'coordenadas':'No certificadas; solo se contrastan nombres y orden.'})
    # Los puntos guardan un slug principal y otros_servicios. La pertenencia requiere ambos.
    # Su campo orden es alfabético y no se toma como secuencia del recorrido.
    for nombre in dict.fromkeys(r['servicio'] for r in reviews if r['sistema']=='metropolitano'):
        sources=[r for r in reviews if r['servicio']==nombre and r['sistema']=='metropolitano']
        slugs={r['pagina'].split('?',1)[0].rsplit('/',1)[-1].removesuffix('.php') for r in sources}
        slugs|={ {'X1-NS':'X1-M','X1-SN':'X1-N','X3-NS':'X3-M','X3-SN':'X3-N','X9-NS':'EX9-NS'}.get(v,v) for v in slugs }
        actual=[]
        for feature in metro:
            props=feature['properties']
            memberships={props['servicio_slug']}|{x.strip() for x in props.get('otros_servicios','').split('|')}
            if memberships & slugs:actual.append(props['estacion'])
        current=list(dict.fromkeys(actual))
        stops=list(dict.fromkeys(n for r in sources for n in r['nombres']))
        c=comparar_estaciones(current,stops)
        c['coincide_secuencia_completa']=None
        c['coincidencias_en_orden']=None
        results.append({'sistema':'metropolitano','servicio':nombre,'catalogo':'geo_pertenencia_ambos_sentidos',
                        'pagina':sources[0]['pagina'],'estado':'coincide_pertenencia' if not(c['faltan_en_catalogo'] or c['sobran_en_catalogo']) else 'discrepancias',
                        'comparacion':c,'coordenadas':'No certificadas. El campo orden de este GeoJSON no representa el recorrido.'})
    counts=dict(Counter(r['estado'] for r in results))
    report={'georreferenciacion_pendiente':{name:sum(not f.get('geometry') for f in json.loads((BASE/('data/geo/'+name)).read_text())['features']) for name in ('paradas_alimentadores.geojson','paradas_corredores.geojson','puntos_metropolitano_servicios.geojson')},'alias_estaciones':ALIAS,'consultado':official['fuente']['consultado'],'alcance':'Comparación de nombres, multiplicidad y orden; no certifica ubicación ni trazados.',
            'normalizacion':'Tildes, puntuación y anotaciones inicial/final; para Metropolitano/L1 se documentan alias explícitos en alias_estaciones. Sin coincidencias difusas ni cambios automáticos.',
            'resumen':counts,'resultados':results}
    (BASE/'data/atu/validacion_paradas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# Validación de paradas contra ATU','',f"Consulta: {report['consultado']}. **No es una certificación de coordenadas.**",'',report['alcance'],'',report['normalizacion'],'',
           '| Sistema | Servicio / ficha | Estado | Paradas locales / oficiales | Coincidencias en orden | Fuente |','|---|---|---|---|---|---|']
    for r in results:
        c=r['comparacion'];sizes=f"{c['n_actual']} / {c['n_oficial']}" if c else '—'
        lines.append(f"| {r['sistema']} | {r['servicio']} {r.get('sentido', '')} ({r.get('catalogo', 'geo')}) | {r['estado']} | {sizes} | {c['coincidencias_en_orden'] if c else '—'} | [ATU]({r['pagina']}) |")
    lines+=['','## Interpretación','',
            '- Una coincidencia completa confirma únicamente que los nombres y la secuencia del catálogo coinciden con la ficha consultada.',
            '- Una discrepancia puede ser un cambio de parada, un terminal omitido, una diferencia de escritura o una variante distinta. El JSON incluye ambas secuencias y los nombres faltantes/sobrantes; no se usa similitud para darla por validada.',
            '- Trapiche tiene recorridos distintos en punta y valle; se comparan por separado contra el catálogo local y no se fusionan.',
            '- Las coordenadas de alimentadores tienen precisión aproximada y fuentes OSM/Google en el catálogo. Coincidir el nombre no las convierte en coordenadas oficiales ATU.',
            '- Metropolitano: 28 mapas revisados visualmente, comparados por sentido contra el planificador y por pertenencia contra el GeoJSON (incluyendo otros_servicios). El orden alfabético del GeoJSON no se certifica como recorrido.',
            '- Línea 1: 26 estaciones contrastadas en ambos sentidos; el GeoJSON se almacena de Villa El Salvador a Bayóvar.',
            '- Expresos 5 y 9: el ramal España/Central no permite certificar un orden total en el esquema; se mantiene esa limitación explícita.',
            '- Los catálogos fueron corregidos con `corregir_paradas_atu.py`. Se conservan coordenadas existentes por correspondencia exacta; las paradas sin ubicación contrastada tienen geometry=null y no se muestran como pins.',
            '- Las Vegas figura en las paradas oficiales pero no tiene serie entrenada: no se inventa aforo ni se usa como transbordo del modelo.','',
            'Reproducir: `python scripts/validar_paradas_atu.py` desde `backend/`.']
    (BASE/'docs/VALIDACION_PARADAS_ATU.md').write_text('\n'.join(lines)+'\n')
    print(counts)
    return report
if __name__=='__main__':run()
