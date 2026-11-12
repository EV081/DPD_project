"""Regresión de horarios oficiales y reglas que se perdían al reducir todo a LAB/SAB/DOM."""
import datetime as dt
import importlib.util
import json
from pathlib import Path

from services import horarios as H

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('extraer_atu', BASE / 'scripts/extraer_horarios_atu.py')
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


def test_cobertura_y_evidencias():
    data = json.loads((BASE / 'data/horarios_atu_oficial.json').read_text())
    assert {k: len(v) for k, v in data['servicios'].items()} == {'metropolitano': 20, 'metro_l1': 1, 'corredor': 16, 'alimentador': 23}
    docs = {d['url']: d['sha256'] for d in data['documentos']}
    for services in data['servicios'].values():
        for ficha in services.values():
            for direction in ficha['direcciones']:
                assert direction['texto_fuente']
                assert len(docs[direction['evidencia']]) == 64
                for rule in direction['reglas']:
                    assert all(0 <= d <= 6 for d in rule['dias_semana'])
                    assert rule['tramos']
                    assert all(0 <= int(t[:2]) < 24 and 0 <= int(t[3:]) < 60 for tramo in rule['tramos'] for t in tramo)


def test_html_no_extrae_horarios_en_comentarios_o_scripts():
    groups, text = extractor.parse_html('''<!-- Horario falso Lunes a viernes: 00:00 a.m. a 01:00 a.m. -->
      <h2>Horario Corredor 206</h2><p>Santa María a San Marcos</p><p>Lunes a viernes:</p>
      <p>5:00 a. m. a 10:17 p. m.</p><script>Horario falso</script>''')
    assert groups[0]['reglas'][0]['tramos'] == [['05:00', '22:17']]
    assert 'falso' not in text


def test_expreso_1_respeta_inicios_por_sentido_y_dia():
    reg = H.servicio('troncal', 'Expreso 1')
    assert H.opera(reg, 'asc', dt.datetime(2026, 11, 9, 5, 10)) is True
    assert H.opera(reg, 'desc', dt.datetime(2026, 11, 9, 5, 10)) is False
    assert H.opera(reg, 'asc', dt.datetime(2026, 11, 14, 6, 10)) is True
    assert H.opera(reg, 'desc', dt.datetime(2026, 11, 14, 6, 10)) is False


def test_corredor_305_conserva_miercoles_a_viernes_y_excepciones():
    reg = H.servicio('corredor', '305')
    assert H.opera(reg, 'sentido_1', dt.datetime(2026, 11, 11, 23, 30)) is True
    assert H.opera(reg, 'sentido_1', dt.datetime(2026, 11, 9, 23, 30)) is False
    assert H.texto_horario(reg, 'sentido_2', dt.date(2026, 11, 14)) == '05:42–23:00'
    assert H.texto_horario(reg, 'sentido_2', dt.date(2026, 11, 15)) == '05:45–22:30'


def test_no_inventa_feriados_ni_sentido_del_corredor():
    reg = H.servicio('corredor', '301')
    assert H.opera(reg, None, dt.datetime(2026, 11, 9, 23, 30)) is None
    assert H.opera(reg, 'sentido_1', dt.datetime(2026, 12, 8, 8)) is None
    assert H.texto_horario(reg, 'sentido_1', dt.date(2026, 12, 8)) == 'Horario no publicado para este día'


def test_metro_l1_y_regular_b_no_usan_horarios_antiguos():
    metro = H.servicio('metro_l1', 'Gamarra')
    assert H.opera(metro, 'asc', dt.datetime(2026, 11, 15, 5, 15)) is False
    assert H.opera(metro, 'asc', dt.datetime(2026, 11, 15, 5, 30)) is True
    assert H.opera(metro, 'asc', dt.datetime(2026, 11, 15, 22)) is False
    assert H.opera(H.servicio('troncal', 'Ruta B'), 'desc', dt.datetime(2026, 11, 9, 9)) is False


def test_alimentadores_usan_atu_y_conservan_frecuencias_secundarias():
    original = json.loads((BASE / 'data/horarios_servicios.json').read_text())['servicios']['alimentador']
    for nombre in original:
        reg = H.servicio('alimentador', nombre)
        assert reg['fuente_horario'] == 'ATU'
        assert reg['intervalo_min'] == original[nombre]['intervalo_min']
        assert reg['url'].startswith('https://portal.atu.gob.pe/QR/Alimentadores/')
    america = H.servicio('alimentador', 'Las Américas')
    assert H.texto_horario(america, 'sentido_1', dt.date(2026, 11, 9)) == '05:30–00:00'
    assert H.texto_horario(america, 'sentido_2', dt.date(2026, 11, 9)) == '05:00–23:30'


def test_alimentador_trapiche_no_confirma_salidas_con_horario_ambiguo():
    reg = H.servicio('alimentador', 'Trapiche')
    assert H.opera(reg, None, dt.datetime(2026, 11, 9, 18)) is None
    assert 'pendiente de aclaración' in H.texto_horario(reg, None, dt.date(2026, 11, 9))


def test_parser_distingue_al_del_nombre_de_los_sentidos():
    html = '<h2>Horario Belaunde</h2><p>Paradero final al Terminal Naranjal</p><p>Lunes a sábado:</p><p>05:00 a. m. - 11:30 p. m.</p><p>Terminal Naranjal al Paradero final</p><p>Lunes a sábado:</p><p>05:30 a. m. - 12:00 p. m.</p>'
    grupos, _ = extractor.parse_html(html)
    assert len(grupos) == 2
    assert grupos[1]['reglas'][0]['tramos'] == [['05:30', '12:00']]


def test_auditoria_de_paradas_no_confunde_nombres_con_coordenadas():
    spec = importlib.util.spec_from_file_location('validar_atu', BASE / 'scripts/validar_paradas_atu.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    assert audit.comparar(['Estación Álamo', 'Final'], ['Estacion Alamo', 'Final'])['coincide_secuencia_completa'] is True
    assert audit.comparar(['A', 'B', 'C'], ['A', 'C', 'B'])['coincide_secuencia_completa'] is False
    assert audit.comparar(['A', 'B'], ['A', 'B', 'B'])['faltan_en_catalogo'] == ['b']
    data = json.loads((BASE / 'data/atu/validacion_paradas.json').read_text())
    assert len(data['resultados']) == 97
    assert all('coordenadas' in r for r in data['resultados'])
    assert not any(r['estado'] == 'pendiente_revision_listas_en_imagen' for r in data['resultados'])


def test_paradas_linea_1_y_asimetria_metropolitano():
    audit = json.loads((BASE / 'data/atu/validacion_paradas.json').read_text())['resultados']
    line = [r for r in audit if r['sistema'] == 'metro_l1']
    assert len(line) == 2
    assert all(r['comparacion']['n_oficial'] == 26 and r['estado'] == 'coincide_nombre_y_orden' for r in line)
    exp11 = {r['sentido']:r['comparacion']['secuencia_oficial'] for r in audit if r['servicio'] == 'Expreso 11' and r.get('catalogo') == 'planificador'}
    assert 'Naranjal' not in exp11['desc'] and 'Pacífico' in exp11['desc']
    assert 'Naranjal' in exp11['asc'] and 'Pacífico' not in exp11['asc']
    assert all('Las Vegas' in stops for stops in exp11.values())
    partial = [r for r in audit if r['estado'] == 'orden_parcial_en_fuente']
    assert len(partial) == 3
    maps = json.loads((BASE / 'data/atu/paradas_mapas_revisadas.json').read_text())['mapas']
    assert len(maps) == 29
    assert len({r['servicio'] for r in maps if r['sistema'] == 'metropolitano'}) == 20
    assert all(len(r['sha256']) == 64 for r in maps)


def test_correcciones_atu_no_dejan_discrepancias_de_listas():
    data = json.loads((BASE / 'data/atu/validacion_paradas.json').read_text())
    assert data['resumen'].get('discrepancias', 0) == 0
    assert data['resumen']['coincide_pertenencia'] == 20
    assert data['resumen']['orden_parcial_en_fuente'] == 3
    assert H.servicio('troncal', 'Expreso 11')['paradas']['desc'] == [
        'Los Incas', 'Andres Belaunde', '22 De Agosto', 'Las Vegas', 'Universidad', 'Pacifico', 'Estacion Central']
    assert 'Naranjal' in H.servicio('troncal', 'Expreso 11')['paradas']['asc']
    assert H.servicio('troncal', 'Super Expreso')['paradas']['asc'] == ['Aramburu', 'Canaval y Moreyra', 'Naranjal']
    assert H.servicio('troncal', 'Super Expreso Norte')['paradas']['desc'] == ['Naranjal', '2 de Mayo', 'Quilca', 'España', 'Estacion Central']
