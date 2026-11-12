import json
from pathlib import Path

BASE=Path(__file__).parents[1]


def test_linea_1_continua_y_troncal_sin_diagonales():
    rail=json.loads((BASE/'data/geo/trazado_metro_l1.geojson').read_text())['features']
    assert len(rail)==1
    assert len(rail[0]['geometry']['coordinates'])==2713
    import importlib.util
    spec=importlib.util.spec_from_file_location('clean',BASE/'scripts/limpiar_trazados_corredores.py')
    clean=importlib.util.module_from_spec(spec);spec.loader.exec_module(clean)
    for filename in ('trazado_troncal','trazados_metropolitano_servicios'):
        for f in json.loads((BASE/f'data/geo/{filename}.geojson').read_text())['features']:
            g=f['geometry'];lines=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
            assert all(clean.distancia(a,b)<=1200 for line in lines for a,b in zip(line,line[1:]))


def test_alimentadores_activos_tienen_ficha_y_no_se_pierden_historicos():
    stops=json.loads((BASE/'data/geo/paradas_alimentadores.geojson').read_text())['features']
    keys={s['properties']['servicio'] for s in stops}
    active=json.loads((BASE/'data/geo/trazados_alimentadores_atu.geojson').read_text())['features']
    archive=json.loads((BASE/'data/atu/trazados_alimentadores_sin_ficha.json').read_text())['features']
    assert len(active)==46 and len(archive)==8
    assert all(f['properties']['ruta'] in keys for f in active)
    assert all(f['properties']['ruta'] not in keys for f in archive)
