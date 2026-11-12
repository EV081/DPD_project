import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('limpieza', Path(__file__).parents[1]/'scripts/limpiar_trazados_corredores.py')
limpieza = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limpieza)


def test_desvio_cerrado_sin_paradas_se_elimina_sin_atajos():
    a,b,c,d = [-77.,-12.],[-77.001,-12.],[-77.001,-12.003],[-77.002,-12.]
    result, count = limpieza.limpiar([a,b,c,b,d], [a,d])
    assert result == [a,b,d]
    assert count == 1


def test_bucle_necesario_para_atender_paradero_se_conserva():
    a,b,c,d = [-77.,-12.],[-77.001,-12.],[-77.001,-12.003],[-77.002,-12.]
    result, count = limpieza.limpiar([a,b,c,b,d], [a,c,d])
    assert result == [a,b,c,b,d]
    assert count == 0
