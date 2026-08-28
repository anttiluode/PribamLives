import argparse
import tempfile
import unittest
from pathlib import Path

import numpy as np

from winding_count import (
    analyze_paths,
    detect_near_return_loops,
    operator_path,
    phase_randomized_surrogate,
    synthetic_loop_stream,
)


class WindingCounterTests(unittest.TestCase):
    def test_direct_plane_loop_detector_finds_odd_enclosing_loop(self):
        phi = np.linspace(0.0, 2.0 * np.pi, 101)
        path = np.column_stack([np.cos(phi), np.sin(phi)])
        events = detect_near_return_loops(
            path,
            (0, 1),
            min_loop_windows=50,
            max_loop_windows=120,
            return_fraction=0.15,
            min_radius_fraction=0.8,
            winding_tolerance=0.05,
        )
        self.assertTrue(any(e.parity == 1 for e in events))

    def test_direct_plane_non_enclosing_loop_has_no_winding(self):
        phi = np.linspace(0.0, 2.0 * np.pi, 101)
        path = np.column_stack([1.6 + np.cos(phi), np.sin(phi)])
        events = detect_near_return_loops(
            path,
            (0, 1),
            min_loop_windows=50,
            max_loop_windows=120,
            return_fraction=0.15,
            min_radius_fraction=0.1,
            winding_tolerance=0.05,
        )
        self.assertEqual(sum(e.parity == 1 for e in events), 0)

    def test_phase_randomization_preserves_channel_spectra(self):
        rng = np.random.default_rng(2)
        x = rng.normal(size=(4096, 4))
        y = phase_randomized_surrogate(x, rng)
        xmag = np.abs(np.fft.rfft((x - x.mean(0)) / x.std(0), axis=0))
        ymag = np.abs(np.fft.rfft(y, axis=0))
        self.assertLess(float(np.max(np.abs(xmag - ymag))), 1e-8)

    def test_synthetic_stream_yields_analyzable_operator_path(self):
        stream = synthetic_loop_stream(windows=40, window=256, seed=4)
        projected, starts = operator_path(
            stream,
            window=256,
            hop=256,
            lag=1,
            modes=2,
        )
        self.assertEqual(projected.shape[0], len(starts))
        self.assertEqual(projected.shape[1:], (2, 2))


if __name__ == "__main__":
    unittest.main()
