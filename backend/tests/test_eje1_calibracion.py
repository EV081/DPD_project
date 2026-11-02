"""Eje 1 · calibración del ETA y métricas de monitoreo (funciones puras, sin base de datos)."""
import pytest

from services import calibracion as C
from services import monitoreo as M


def fb(real, pre, trafico=1.0, con_base=True):
    return {"espera_real_min": real, "eta_mostrado_min": pre * trafico, "eta_base_min": pre if con_base else None, "factor_trafico": trafico}


# --------------------------------------------------------------------------- factor estimado
def test_sin_datos_no_hay_factor():
    assert C.factor_estimado([]) == (None, 0)


def test_el_eta_previo_usa_la_base_por_el_trafico():
    assert C.eta_previo(fb(5, 4, trafico=1.25)) == pytest.approx(5.0)
    assert C.eta_previo(fb(5, 4, con_base=False)) == pytest.approx(4.0)                  # sin base: el mostrado ya es el del modelo
    assert C.eta_previo({"espera_real_min": 3}) is None


def test_la_contraccion_acerca_el_factor_a_uno_con_pocos_datos():
    k100, n = C.factor_estimado([fb(6.0, 4.0)] * 100)                  # k observado 1,5
    k400, _ = C.factor_estimado([fb(6.0, 4.0)] * 400)
    assert n == 100 and k100 == pytest.approx(1.25) and k400 == pytest.approx(1.4)       # 1 + 0,5·n/(n+100); tope 1,4 con n=400 (1,4)
    assert 1.0 < k100 < k400 <= 1.4


def test_el_factor_tiene_tope_inferior_y_superior():
    assert C.factor_estimado([fb(40.0, 2.0)] * 1000)[0] == 1.4
    assert C.factor_estimado([fb(0.1, 5.0)] * 1000)[0] == 0.8


def test_etas_menores_al_minimo_se_ignoran():
    assert C.factor_estimado([fb(5.0, 0.4)] * 200) == (None, 0)


def test_el_error_medio_con_un_factor():
    filas = [fb(6.0, 4.0), fb(8.0, 4.0)]
    assert C.mae(filas, 1.0) == pytest.approx(3.0) and C.mae(filas, 1.75) == pytest.approx(1.0)


# --------------------------------------------------------------------------- campeón vs retador
def historia(real_sobre_pre, n_fit=150, n_val=40):
    fit = [fb(4.0 * real_sobre_pre, 4.0) for _ in range(n_fit)]
    val = [fb(4.0 * real_sobre_pre, 4.0) for _ in range(n_val)]
    return fit, val


def test_con_menos_de_100_respuestas_no_se_calibra():
    fit, val = historia(1.4, n_fit=99)
    d = C.decidir(fit, val, 1.0)
    assert d["estado"] == "sin_datos" and d["k"] == 1.0 and "100" in d["motivo"]


def test_si_el_retador_mejora_se_promueve():
    fit, val = historia(1.4)
    d = C.decidir(fit, val, 1.0)
    assert d["estado"] == "campeon" and d["k"] > 1.1 and d["mae_retador"] < d["mae_campeon"] and d["mejora"] >= 0.05


def test_un_cambio_diminuto_del_factor_es_ruido_y_no_se_promueve():
    fit, val = historia(1.03, n_fit=500)                  # el modelo ya casi acierta: k ≈ 1,025 (< 3 % de cambio)
    d = C.decidir(fit, val, 1.0)
    assert d["estado"] == "retador" and "ruido" in d["motivo"]


def test_si_no_mejora_lo_suficiente_no_se_promueve():
    fit = [fb(4.0 * 1.275, 4.0)] * 1000                   # el retador sale con k = 1,25 (el campeón tiene 1,2: cambio de 5 %)...
    val = [fb(4.0 * 1.2255, 4.0)] * 40                    # ...pero en datos nuevos acierta solo ~4 % mejor
    d = C.decidir(fit, val, 1.2)
    assert d["estado"] == "retador" and 0 < d["mejora"] < 0.05 and "se mantiene el campeón" in d["motivo"]


def test_un_retador_igual_al_campeon_no_cambia_nada():
    fit, val = historia(1.4)
    k = C.factor_estimado(fit)[0]
    assert C.decidir(fit, val, k)["estado"] == "retador" and "igual" in C.decidir(fit, val, k)["motivo"]


def test_con_pocas_respuestas_de_validacion_no_se_promueve():
    fit, val = historia(1.4, n_val=5)
    d = C.decidir(fit, val, 1.0)
    assert d["estado"] == "retador" and "validación" in d["motivo"]


def test_un_retador_peor_que_el_campeon_no_se_promueve():
    fit, _ = historia(1.4)
    val = [fb(4.0, 4.0)] * 40                              # en la validación el modelo base acertaba: subir el ETA empeora
    d = C.decidir(fit, val, 1.0)
    assert d["estado"] == "retador" and d["mejora"] < 0


# --------------------------------------------------------------------------- monitoreo
def fila(real, mostrado, percibido=None, aforo=None):
    return {"espera_real_min": real, "eta_mostrado_min": mostrado, "aforo_percibido": percibido, "aforo_mostrado": aforo}


def test_metricas_de_una_semana():
    m = M.calcular_metricas([fila(8, 4, "Saturado", "De_pie"), fila(5, 4, "De_pie", "De_pie"), fila(3, None)])
    assert m["n"] == 3 and m["eta"] == {"n": 2, "mae_min": pytest.approx(2.5), "sesgo_min": pytest.approx(2.5)}
    assert m["aforo"] == {"n": 2, "acierto": 0.5}


def test_sin_suficientes_respuestas_no_hay_alerta():
    m = M.calcular_metricas([fila(30, 2)] * 10)                   # error enorme pero solo 10 respuestas
    assert M.evaluar_alerta(m) is None


def test_alerta_por_sesgo_del_eta():
    m = M.calcular_metricas([fila(9, 4)] * 40)
    motivo = M.evaluar_alerta(m)
    assert "sesgo del ETA +5.0" in motivo and "error medio del ETA 5.0" not in motivo.replace("5.0 min (> 5)", "x") or "error medio" not in motivo


def test_alerta_por_error_medio_con_sesgo_chico():
    m = M.calcular_metricas([fila(10, 4)] * 20 + [fila(0.5, 6.5)] * 20)          # errores +6 y -6: el sesgo se cancela, el MAE no
    motivo = M.evaluar_alerta(m)
    assert "error medio del ETA 6.0" in motivo and "sesgo" not in motivo


def test_alerta_por_aforo_mal_acertado():
    m = M.calcular_metricas([fila(4, 4, "Saturado", "Asientos")] * 40)
    assert "acierto del aforo 0%" in M.evaluar_alerta(m)


def test_sin_problemas_no_hay_alerta():
    m = M.calcular_metricas([fila(4.5, 4, "De_pie", "De_pie")] * 40)
    assert M.evaluar_alerta(m) is None


def test_los_umbrales_se_configuran_por_entorno(monkeypatch):
    monkeypatch.setenv("MONITOREO_MIN_N", "5")
    monkeypatch.setenv("MONITOREO_SESGO_MIN", "0.5")
    assert M.evaluar_alerta(M.calcular_metricas([fila(5, 4)] * 6)) is not None


def test_las_semanas_empiezan_el_lunes():
    import datetime as dt
    assert M.lunes_de(dt.date(2026, 11, 1)) == dt.date(2026, 10, 26)         # domingo -> lunes anterior
    assert M.lunes_de(dt.date(2026, 11, 2)) == dt.date(2026, 11, 2)
    ini, fin = M.rango_semana_utc(dt.date(2026, 11, 2))
    assert ini.isoformat() == "2026-11-02T05:00:00+00:00" and (fin - ini).days == 7        # 00:00 Lima = 05:00 UTC
