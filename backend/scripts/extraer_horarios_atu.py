"""Extrae horarios de las fichas QR de ATU y transcripciones de imágenes revisadas.

python scripts/extraer_horarios_atu.py --cache /tmp/atu-oficial [--offline]
El OCR nunca se acepta automáticamente. Las imágenes se verifican por SHA-256
contra data/atu/imagenes_revisadas.json; un cambio exige nueva revisión visual.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import unicodedata
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parents[1]
ROOT = 'https://portal.atu.gob.pe/QR/'
METRO = {
 'Ruta A': ['RegularA.php'], 'Ruta B': ['RegularB.php'], 'Ruta C': ['RegularC.php'], 'Ruta D': ['RegularD.php'],
 'Expreso 1': ['X1-M.php', 'X1-SN-N.php'], 'Expreso 2': ['X2-NS-M.php?p=2', 'X2-SN-M.php'],
 'Expreso 3': ['X3-M.php', 'X3-N.php'], 'Expreso 5': ['X5.php'], 'Expreso 6': ['X6.php'],
 'Expreso 7': ['X7.php'], 'Expreso 8': ['X8.php'], 'Expreso 9': ['X9-NS.php', 'EX9-SN.php'],
 'Expreso 10': ['X10.php'], 'Expreso 11': ['EX11-NS.php', 'EX11-SN.php'], 'Expreso 12': ['X12.php'],
 'Expreso 13': ['EX13-NS.php', 'EX13-SN.php'], 'Super Expreso': ['SX-M.php', 'SX-N.php'],
 'Super Expreso Norte': ['SXN-NS-M.php', 'SXN-SN-M.php'],
 'Super Expreso Norte (22 de Agosto)': ['SXN22.php'], 'Lechucero': ['Lechucero.php'],
}
CORREDORES = {'Azul': ['301', '303', '305', '336', '370', '371', 'SE-08'],
              'Rojo': ['201', '204', '206', '209'], 'Morado': ['404', '405', '406', '412', 'SE-09']}
ALIMENTADORES = {
 "San Juan de Dios": [
  "Alimentadores/AlimentadoresChimpuOcllo/SanJuanDeDios/"
 ],
 "Universitaria": [
  "Alimentadores/AlimentadoresChimpuOcllo/Universitaria/"
 ],
 "Carabayllo": [
  "Alimentadores/AlimentadoresLosIncas/Carabayllo/"
 ],
 "Collique": [
  "Alimentadores/AlimentadoresLosIncas/Collique/"
 ],
 "Torre Blanca": [
  "Alimentadores/AlimentadoresLosIncas/TorreBlanca/"
 ],
 "Antúnez de Mayolo": [
  "Alimentadores/AlimentadoresNorte/AntunezDeMayolo/"
 ],
 "Belaunde": [
  "Alimentadores/AlimentadoresNorte/Belaunde/"
 ],
 "Bertello": [
  "Alimentadores/AlimentadoresNorte/Bertello/"
 ],
 "Izaguirre": [
  "Alimentadores/AlimentadoresNorte/Izaguirre/"
 ],
 "Ensenada": [
  "Alimentadores/AlimentadoresNorte/LaEnsenada/"
 ],
 "Alisos": [
  "Alimentadores/AlimentadoresNorte/LosAlisos/"
 ],
 "Los Olivos": [
  "Alimentadores/AlimentadoresNorte/LosOlivos/"
 ],
 "Milagro de Jesús": [
  "Alimentadores/AlimentadoresNorte/MilagroDeJesus/"
 ],
 "Naranjal": [
  "Alimentadores/AlimentadoresNorte/Naranjal/"
 ],
 "Payet": [
  "Alimentadores/AlimentadoresNorte/Payet/"
 ],
 "Puente Piedra": [
  "Alimentadores/AlimentadoresNorte/PuentePiedra/"
 ],
 "Puno": [
  "Alimentadores/AlimentadoresNorte/Puno/"
 ],
 "Tahuantinsuyo": [
  "Alimentadores/AlimentadoresNorte/Tahuantinsuyo/"
 ],
 "Las Américas": [
  "Alimentadores/AlimentadoresSur/America/"
 ],
 "Cedros de Villa": [
  "Alimentadores/AlimentadoresSur/CedrosDeVilla/"
 ],
 "Los Próceres": [
  "Alimentadores/AlimentadoresSur/LosProceres/"
 ],
 "Villa El Salvador": [
  "Alimentadores/AlimentadoresSur/VillaElSalvador/"
 ],
 "Trapiche": [
  "Alimentadores/AlimentadoresUniversidad/Trapiche/",
  "Alimentadores/AlimentadoresUniversidad/Trapiche/T-HV.php"
 ]
}
DAYS = {'lunes a viernes': [0,1,2,3,4], 'lunes a sabado': [0,1,2,3,4,5], 'lunes a domingo': list(range(7)),
 'miercoles a viernes': [2,3,4], 'sabado a martes': [5,6,0,1], 'viernes y sabado': [4,5],
 'sabado y domingo': [5,6], 'sabados': [5], 'sabado': [5], 'domingos': [6], 'domingo': [6]}
TIME = re.compile(r'(\d{1,2}):(\d{2})\s*([ap])\s*\.?\s*m\.?', re.I)

def norm(s):
 return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))

class Text(HTMLParser):
 def __init__(self): super().__init__(); self.lines=[]; self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'): self.skip+=1
 def handle_endtag(self,tag):
  if tag in ('script','style'): self.skip=max(0,self.skip-1)
 def handle_data(self,s):
  if not self.skip and s.strip(): self.lines.append(' '.join(s.split()))

def hhmm(match):
 h,m,ampm=match.groups();h=int(h);m=int(m)
 if not 0<=h<=12 or not 0<=m<=59: raise ValueError('Hora inválida')
 return f'{h%12+(12 if ampm.lower()=="p" else 0):02d}:{m:02d}'

def parse_html(content, header_hint=None):
 parser=Text();parser.feed(content)
 starts=[i for i,l in enumerate(parser.lines) if norm(l).startswith('horario')]
 if not starts and header_hint:
  starts=[i for i,l in enumerate(parser.lines) if norm(l)==norm(header_hint)]
 if not starts: return [], ''
 lines=parser.lines[starts[-1]:];lines=lines[:next((i for i,l in enumerate(lines) if '+511' in l),len(lines))]
 groups=[];label='Ambos sentidos';rules=[];pending=None
 def flush():
  nonlocal rules
  if rules:groups.append({'sentido_publicado':label,'reglas':rules});rules=[]
 for line in lines[1:]:
  clean=norm(line).strip(': ')
  matches=list(TIME.finditer(line))
  if clean in DAYS: pending=(line,DAYS[clean])
  elif len(matches)>=2 and pending:
   if len(matches)%2: raise ValueError(f'Número impar de horas: {line}')
   rules.append({'dias_texto':pending[0].rstrip(':'),'dias_semana':pending[1],
                 'tramos':[[hhmm(matches[i]),hhmm(matches[i+1])] for i in range(0,len(matches),2)]})
   pending=None
  elif re.search(r' a(?:l)? ', clean) and not matches and not clean.startswith('de sur a norte'):
   flush();label=line.rstrip(':');pending=None
 flush()
 return groups, '\n'.join(lines)

def cache_name(url): return re.sub(r'[^a-zA-Z0-9._-]','_',url.removeprefix(ROOT))

def run(cache,offline=False,output=None):
 reviews=json.loads((BASE/'data/atu/imagenes_revisadas.json').read_text())
 result={'fuente':{'nombre':'ATU · Portal QR oficial','url':ROOT,'consultado':dt.datetime.now(ZoneInfo('America/Lima')).date().isoformat(),
  'aviso':'Transcripción de las fichas oficiales consultadas. No son salidas en tiempo real. Los días no publicados y los feriados no se completan por suposición.'},
  'servicios':{'metropolitano':{},'metro_l1':{},'corredor':{},'alimentador':{}},'documentos':[]}
 cache.mkdir(parents=True,exist_ok=True)
 def read(url):
  p=cache/cache_name(url)
  if not offline:
   with urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(url,safe=':/?=&%'),headers={'User-Agent':'UrbanSafe-horarios/1.0'}),timeout=40) as r:p.write_bytes(r.read())
  content=p.read_bytes();digest=hashlib.sha256(content).hexdigest()
  if not any(d['url']==url for d in result['documentos']):result['documentos'].append({'url':url,'sha256':digest})
  return content,digest
 def entry(system,name,pages):
  dirs=[];sources=[];notes=[];stop_evidence=[]
  for page in pages:
   url=ROOT+page;body,_=read(url);sources.append(url)
   content=body.decode('utf-8',errors='replace')
   groups,text=parse_html(content, header_hint='San Juan de Dios' if name=='San Juan de Dios' else None)
   parser=Text();parser.feed(content)
   stops=[m.group(2) for line in parser.lines if (m:=re.match(r'^(\d+)[.)]\s+(.+)',line))]
   stops_method='html'
   if page in reviews:
    review=reviews[page];image_url=ROOT+review['imagen'];_,digest=read(image_url)
    if digest!=review['sha256']:raise ValueError(f'Imagen cambió: revisar {image_url}')
    groups=review['direcciones'];text=review['transcripcion'];evidence=image_url;method='imagen_revisada'
    notes.extend(review.get('notas',[]))
    if 'paradas_revisadas' in review:stops=review['paradas_revisadas'];stops_method='imagen_revisada'
   else:evidence=url;method='html'
   if not groups: raise ValueError(f'Sin horario extraíble: {url}')
   stop_evidence.append({'pagina':url,'evidencia':evidence,'metodo':stops_method,'nombres_en_orden':stops})
   for group in groups:
    dirs.append({**group,'pagina':url,'evidencia':evidence,'metodo':method,'texto_fuente':text})
  if name=='301':notes.append('La ficha publica cierre a las 10:47 a. m. (laborables) y 10:14 a. m. (sábado) en 24 de Junio → Plaza Butters. Se conserva literalmente; pendiente de aclaración por ATU.')
  if name=='305':notes.append('La ficha de vuelta dice lunes a domingo y además especifica sábado y domingo con otras horas. Se conservan las reglas; los días específicos prevalecen en la consulta.')
  if name=='Expreso 9':notes.append('Se usa el sentido escrito en el horario, no el sufijo NS/SN del enlace; hay pestañas oficiales con nombres inconsistentes.')
  if system=='alimentador' and name in ('Belaunde','Milagro de Jesús','Puno'):notes.append('La ficha publica 12:00 p. m. (mediodía), no 12:00 a. m., para el cierre desde Naranjal de lunes a sábado. Se conserva literalmente; pendiente de aclaración por ATU.')
  if name=='Carabayllo':notes.append('La URL y el menú no coinciden con el terminal escrito en el horario: la ficha dice Chimpu Ocllo. Se conserva el texto, no se cambia por Los Incas/Belaunde.')
  result['servicios'][system][name]={'url':sources[0],'paginas':sources,'direcciones':dirs,'notas':notes,'frecuencia_publicada_min':None,'paradas_publicadas':stop_evidence}
  if system=='alimentador' and name=='Trapiche':result['servicios'][system][name]['apto_para_planificador']=False
 for name,pages in METRO.items():entry('metropolitano',name,['Metropolitano/Servicios/'+p for p in pages])
 entry('metro_l1','Línea 1',['MetroLima/L1/'])
 for color,routes in CORREDORES.items():
  for route in routes:entry('corredor',route,[f'Corredor{color}/'+('index.php' if route in ('301','201','404') else route+'.php')])
 for name,pages in ALIMENTADORES.items():entry('alimentador',name,pages)
 path=output or BASE/'data/horarios_atu_oficial.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 with path.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as f:
  writer=csv.writer(f, lineterminator='\n')
  writer.writerow(['sistema','servicio','sentido','dias_publicados','dias_semana_0_lunes','inicio','fin','cruza_medianoche','pagina','evidencia','metodo','consultado','observaciones'])
  for system,services in result['servicios'].items():
   for name,record in services.items():
    for direction in record['direcciones']:
     for rule in direction['reglas']:
      for start,end in rule['tramos']:
       writer.writerow([system,name,direction['sentido_publicado'],rule['dias_texto'],','.join(map(str,rule['dias_semana'])),start,end,end<=start,direction['pagina'],direction['evidencia'],direction['metodo'],result['fuente']['consultado'],' '.join(record['notas'])])
 print(path, {k:len(v) for k,v in result['servicios'].items()})
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=Path('/tmp/atu-oficial'));p.add_argument('--offline',action='store_true');p.add_argument('--output',type=Path)
 a=p.parse_args();run(a.cache,a.offline,a.output)
