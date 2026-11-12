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
    assert {k: len(v) for k, v in data['servicios'].items()} == {'metropolitano': 20, 'metro_l1': 1, 'corredor': 16}
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
