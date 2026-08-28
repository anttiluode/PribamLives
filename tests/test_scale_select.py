import unittest

import numpy as np

from scale_select import forward_predictive_gains


class ScaleSelectorTests(unittest.TestCase):
    def test_forward_prediction_prefers_correct_lag_structure_over_zero_gain(self):
        rng = np.random.default_rng(5)
        n = 3000
        x = np.zeros((n, 3), dtype=float)
        rho = np.array([0.9, 0.6, 0.3])
        for t in range(1, n):
            x[t] = rho * x[t - 1] + np.sqrt(1.0 - rho * rho) * rng.normal(size=3)

        gains = forward_predictive_gains(
            x,
            window=600,
            lag=1,
            test_block=150,
            step=150,
            ridge_fraction=1e-3,
        )
        self.assertGreater(len(gains), 4)
        self.assertGreater(float(np.median(gains)), 0.15)


if __name__ == "__main__":
    unittest.main()
