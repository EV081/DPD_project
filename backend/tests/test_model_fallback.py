"""La contingencia sigue dando una referencia, sin fabricar datos ni certeza."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND), str(BACKEND / "model")]
from model.inferencia import ModeloSistema, panel_desde_contexto


class ModelFallbackTests(unittest.TestCase):
    def setUp(self):
        self.context = pd.DataFrame({"A": 20.0}, index=pd.date_range("2025-01-01", periods=28 * 24, freq="h"))
        self.model = object.__new__(ModeloSistema)
        self.model.sistema = "alimentador"
        self.model.series = ["A"]
        self.model.sentido = {"series_sentido": ["A|ida"]}
        self.model.conformal_sentido = {"tipo": "residuo", "por_hora": {}}
        self.model.principal = "lightgbm"
        self.model._operativa = Mock(return_value=({}, None))

    def test_failed_direction_model_uses_baseline_without_interval(self):
        self.model.pronostico_por_sentido = Mock(side_effect=RuntimeError("artefacto no disponible"))
        result = self.model.pronosticar(self.context, "2025-01-29", modo="ligero")
        self.assertTrue(result.validaciones_pron.eq(20).all())
        self.assertTrue(result.modelo.eq("media_4sem_fallback").all())
        self.assertTrue(result[["banda80_lo", "banda80_hi"]].isna().all().all())

    def test_missing_calibration_does_not_create_zero_width_interval(self):
        point = np.full((1, 24), 100.0)
        low, high = self.model._banda(point, None, np.ones_like(point), {"tipo": "residuo", "por_hora": {}})
        self.assertTrue(np.isnan(low).all() and np.isnan(high).all())

    def test_known_calibration_is_preserved_and_missing_hours_remain_unknown(self):
        point = np.full((1, 24), 100.0)
        low, high = self.model._banda(point, None, np.ones_like(point),
                                    {"tipo": "residuo", "por_hora": {"0": {"q_lo": 10, "q_hi": 20}}})
        self.assertEqual(low[0, 0], 90)
        self.assertEqual(high[0, 0], 120)
        self.assertTrue(np.isnan(low[:, 1:]).all() and np.isnan(high[:, 1:]).all())

    def test_incomplete_recent_history_is_not_filled_as_observed_zero(self):
        with self.assertRaisesRegex(ValueError, "completas"):
            panel_desde_contexto("alimentador", self.context.iloc[[0, -1]], "2025-01-29")

    def test_negative_counts_are_rejected(self):
        self.context.iloc[-1, 0] = -1
        with self.assertRaisesRegex(ValueError, "no negativas"):
            panel_desde_contexto("alimentador", self.context, "2025-01-29")

    def test_forecast_day_is_not_marked_observed(self):
        panel, start = panel_desde_contexto("alimentador", self.context, "2025-01-29")
        self.assertTrue(panel.obs[:start].all())
        self.assertFalse(panel.obs[start:].any())


if __name__ == "__main__":
    unittest.main()
