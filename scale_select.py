#!/usr/bin/env python3
"""Select an EEG/operator time scale WITHOUT looking at winding.

The criterion is forward predictive validity.

For each candidate window duration and lag:
1. standardize + globally whiten each recording;
2. fit a local linear lag predictor on the immediately preceding window;
3. score one-step/lag prediction on the immediately following held-out block;
4. summarize held-out predictive gain within each file;
5. choose the window/lag pair with the highest median file-level gain.

This creates a frozen physical scale (seconds), after which winding_count.py
may be run with --scale-json.

The selector never computes a winding number.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from winding_count import global_whiten, load_stream, standardize

Array = np.ndarray


@dataclass
class ScoreRow:
    file: str
    sample_rate: float
    window_seconds: float
    lag_seconds: float
    window_samples: int
    lag_samples: int
    folds: int
    predictive_gain_median: float
    predictive_gain_mean: float
    predictive_gain_std: float


def parse_float_list(text: str) -> List[float]:
    values = [float(piece.strip()) for piece in text.split(",") if piece.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected comma-separated numbers")
    return values


def ridge_lag_predictor(train: Array, lag: int, ridge_fraction: float) -> Array:
    """Fit x[t-lag] -> x[t] using ridge regression."""
    if lag < 1 or len(train) <= lag + 4:
        raise ValueError("training block too short for lag")

    x = train[:-lag]
    y = train[lag:]

    xx = x.T @ x
    scale = float(np.trace(xx) / max(xx.shape[0], 1))
    ridge = max(1e-10, ridge_fraction * scale)
    system = xx + ridge * np.eye(xx.shape[0])
    return np.linalg.solve(system, x.T @ y)


def forward_predictive_gains(
    whitened: Array,
    *,
    window: int,
    lag: int,
    test_block: int,
    step: int,
    ridge_fraction: float,
) -> Array:
    """Blocked forward validation.

    At each fold, fit on [end-window, end) and test on [end, end+test_block).
    Test predictors use observed lagged samples, i.e. this is direct lag
    prediction rather than recursive rollout.
    """
    n = len(whitened)

    if window <= lag + 8:
        return np.empty(0, dtype=float)
    if test_block <= lag:
        test_block = lag + 1

    gains: List[float] = []

    for end in range(window, n - test_block + 1, step):
        train = whitened[end - window : end]
        model = ridge_lag_predictor(train, lag, ridge_fraction)

        current = whitened[end : end + test_block]
        past = whitened[end - lag : end + test_block - lag]

        prediction = past @ model
        mse = float(np.mean((current - prediction) ** 2))
        zero_mse = float(np.mean(current ** 2))

        if zero_mse <= 1e-12:
            continue

        gains.append(1.0 - mse / zero_mse)

    return np.asarray(gains, dtype=float)


def score_recording(
    path: Path,
    *,
    window_seconds: Sequence[float],
    lag_seconds: Sequence[float],
    edf_eeg_only: bool,
    max_channels: int | None,
    max_seconds: float | None,
    test_fraction: float,
    step_fraction: float,
    ridge_fraction: float,
    min_folds: int,
) -> List[ScoreRow]:
    data, sample_rate = load_stream(
        path,
        edf_eeg_only=edf_eeg_only,
        max_channels=max_channels,
        max_seconds=max_seconds,
    )

    if sample_rate is None:
        raise ValueError(
            f"{path}: scale selection needs a known sample rate; use WAV/EDF"
        )

    whitened, _ = global_whiten(standardize(data))
    rows: List[ScoreRow] = []

    for ws in window_seconds:
        window = max(16, int(round(ws * sample_rate)))
        if window >= len(whitened) - 16:
            continue

        test_block = max(16, int(round(test_fraction * window)))
        step = max(16, int(round(step_fraction * window)))

        for ls in lag_seconds:
            lag = max(1, int(round(ls * sample_rate)))
            gains = forward_predictive_gains(
                whitened,
                window=window,
                lag=lag,
                test_block=test_block,
                step=step,
                ridge_fraction=ridge_fraction,
            )

            if len(gains) < min_folds:
                continue

            rows.append(
                ScoreRow(
                    file=path.name,
                    sample_rate=float(sample_rate),
                    window_seconds=float(window / sample_rate),
                    lag_seconds=float(lag / sample_rate),
                    window_samples=int(window),
                    lag_samples=int(lag),
                    folds=int(len(gains)),
                    predictive_gain_median=float(np.median(gains)),
                    predictive_gain_mean=float(np.mean(gains)),
                    predictive_gain_std=float(np.std(gains)),
                )
            )

    return rows


def aggregate_scores(rows: Sequence[ScoreRow]) -> List[Dict[str, float]]:
    grouped: Dict[Tuple[float, float], List[ScoreRow]] = {}

    for row in rows:
        key = (row.window_seconds, row.lag_seconds)
        grouped.setdefault(key, []).append(row)

    result: List[Dict[str, float]] = []

    for (window_seconds, lag_seconds), group in grouped.items():
        per_file = np.asarray(
            [row.predictive_gain_median for row in group],
            dtype=float,
        )
        result.append(
            {
                "window_seconds": float(window_seconds),
                "lag_seconds": float(lag_seconds),
                "files": int(len(group)),
                "median_file_predictive_gain": float(np.median(per_file)),
                "mean_file_predictive_gain": float(np.mean(per_file)),
                "worst_file_predictive_gain": float(np.min(per_file)),
            }
        )

    result.sort(
        key=lambda row: (
            row["median_file_predictive_gain"],
            row["worst_file_predictive_gain"],
            -row["window_seconds"],
        ),
        reverse=True,
    )
    return result


def plot_scores(path: Path, aggregates: Sequence[Dict[str, float]]) -> None:
    import matplotlib.pyplot as plt

    windows = sorted({row["window_seconds"] for row in aggregates})
    lags = sorted({row["lag_seconds"] for row in aggregates})

    matrix = np.full((len(lags), len(windows)), np.nan, dtype=float)
    lookup = {
        (row["window_seconds"], row["lag_seconds"]): row[
            "median_file_predictive_gain"
        ]
        for row in aggregates
    }

    for i, lag in enumerate(lags):
        for j, window in enumerate(windows):
            if (window, lag) in lookup:
                matrix[i, j] = lookup[(window, lag)]

    fig, ax = plt.subplots(figsize=(9, 5))
    image = ax.imshow(matrix, aspect="auto", origin="lower")
    ax.set_xticks(np.arange(len(windows)))
    ax.set_xticklabels([f"{value:g}" for value in windows])
    ax.set_yticks(np.arange(len(lags)))
    ax.set_yticklabels([f"{1000*value:g}" for value in lags])
    ax.set_xlabel("training window (s)")
    ax.set_ylabel("lag (ms)")
    ax.set_title("Independent scale selection: held-out forward predictive gain")
    fig.colorbar(image, ax=ax, label="median file-level predictive gain")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Choose window/lag by held-out forward prediction, without computing winding."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--pattern", default="*.edf")
    parser.add_argument("--edf-eeg-only", action="store_true")
    parser.add_argument("--max-channels", type=int, default=None)
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument(
        "--window-seconds",
        type=parse_float_list,
        default=parse_float_list("4,6,8,10,12,16,20"),
    )
    parser.add_argument(
        "--lag-seconds",
        type=parse_float_list,
        default=parse_float_list("0.025,0.05,0.1,0.2"),
    )
    parser.add_argument("--test-fraction", type=float, default=0.25)
    parser.add_argument("--step-fraction", type=float, default=0.25)
    parser.add_argument("--ridge-fraction", type=float, default=1e-3)
    parser.add_argument("--min-folds", type=int, default=4)
    parser.add_argument("--hop-fraction", type=float, default=0.25)
    parser.add_argument("--min-loop-window-multiple", type=float, default=3.0)
    parser.add_argument("--out-dir", type=Path, default=Path("results/scale"))
    args = parser.parse_args()

    if args.input.is_dir():
        files = sorted(args.input.glob(args.pattern))
    else:
        files = [args.input]

    if not files:
        raise SystemExit("no input files")

    all_rows: List[ScoreRow] = []

    for path in files:
        print(f"\n=== scale scoring {path.name} ===")
        rows = score_recording(
            path,
            window_seconds=args.window_seconds,
            lag_seconds=args.lag_seconds,
            edf_eeg_only=args.edf_eeg_only,
            max_channels=args.max_channels,
            max_seconds=args.max_seconds,
            test_fraction=args.test_fraction,
            step_fraction=args.step_fraction,
            ridge_fraction=args.ridge_fraction,
            min_folds=args.min_folds,
        )
        all_rows.extend(rows)

    aggregates = aggregate_scores(all_rows)

    if not aggregates:
        raise SystemExit("no candidate scale had enough validation folds")

    # Require the winning scale to have a score from every supplied file.
    complete = [row for row in aggregates if row["files"] == len(files)]
    if not complete:
        raise SystemExit(
            "no window/lag candidate had enough folds in every recording"
        )

    selected = complete[0]

    scale = {
        "selection_rule": "maximize median file-level held-out forward predictive gain",
        "files_used": [path.name for path in files],
        "window_seconds": selected["window_seconds"],
        "lag_seconds": selected["lag_seconds"],
        "hop_fraction": float(args.hop_fraction),
        "min_loop_window_multiple": float(args.min_loop_window_multiple),
        "max_loop_seconds": None,
        "median_file_predictive_gain": selected[
            "median_file_predictive_gain"
        ],
        "worst_file_predictive_gain": selected[
            "worst_file_predictive_gain"
        ],
        "note": "Scale selected without computing winding.",
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows_path = args.out_dir / "scale_scores.csv"
    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(all_rows[0]).keys()))
        writer.writeheader()
        for row in all_rows:
            writer.writerow(asdict(row))

    aggregate_path = args.out_dir / "scale_aggregate.json"
    aggregate_path.write_text(
        json.dumps(aggregates, indent=2) + "\n",
        encoding="utf-8",
    )

    selected_path = args.out_dir / "selected_scale.json"
    selected_path.write_text(
        json.dumps(scale, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    plot_scores(args.out_dir / "scale_selection.png", complete)

    print("\n=== frozen predictive scale ===")
    print(json.dumps(scale, indent=2, sort_keys=True))
    print(f"wrote {selected_path}")
    print("\nThen run winding without changing the scale:")
    print(
        "python winding_count.py RECORDING.edf "
        f"--scale-json {selected_path} --edf-eeg-only --surrogates 1000"
    )


if __name__ == "__main__":
    main()
