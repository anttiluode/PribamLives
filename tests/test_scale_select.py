import unittest

import numpy as np

from scale_select import forward_predictive_gains, target_scale_feasibility


class ScaleSelectorTests(unittest.TestCase):
    def test_target_feasibility_rejects_scale_that_cannot_fit_loop(self):
        # 1.edf is approximately 61 s at 160 Hz.
        bad = target_scale_feasibility(
            target_samples=9760,
            target_sample_rate=160.0,
            window_seconds=20.0,
            hop_fraction=0.25,
            min_loop_window_multiple=3.0,
        )
        good = target_scale_feasibility(
            target_samples=9760,
            target_sample_rate=160.0,
            window_seconds=12.0,
            hop_fraction=0.25,
            min_loop_window_multiple=3.0,
        )
        self.assertFalse(bad["testable"])
        self.assertTrue(good["testable"])
        self.assertLess(
            bad["operator_windows"],
            bad["required_operator_windows"],
        )

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
