import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model.calibracion_intervalos import cobertura_causal


class TemporalCoverageTests(unittest.TestCase):
    def test_future_error_cannot_widen_its_own_interval(self):
        # Con dos días previos de error cero, el salto del tercer día debe fallar.
        predicted = np.full((3, 1, 1), 10.)
        observed = predicted.copy()
        observed[-1] = 1000
        result = cobertura_causal(observed, predicted, np.ones_like(predicted), pd.date_range("2025-01-01", periods=3), window=2)
        self.assertEqual(result["coverage"], 0)
        self.assertEqual(result["evaluated_days"], 1)

    def test_matching_predictions_are_covered_after_calibration(self):
        values = np.full((16, 2, 24), 10.)
        result = cobertura_causal(values, values, np.ones_like(values), pd.date_range("2025-01-01", periods=16))
        self.assertEqual(result["coverage"], 1)
        self.assertEqual(result["evaluated_cells"], 96)
        self.assertEqual(result["first_evaluation"], "2025-01-15")

    def test_reversed_dates_are_rejected(self):
        values = np.ones((3, 1, 1))
        with self.assertRaisesRegex(ValueError, "ordenadas"):
            cobertura_causal(values, values, values, pd.date_range("2025-01-01", periods=3)[::-1], window=2)


if __name__ == "__main__":
    unittest.main()
