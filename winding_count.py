#!/usr/bin/env python3
"""PribamLives: real-vs-surrogate holonomy / winding detector.

Primary measurement
-------------------
For a long multichannel stream, estimate a fixed-gauge path of symmetric
lag-covariance operators.  In a fixed reference eigenbasis, every mode pair
(i,j) gives a real-symmetric 2x2 block

    [[Lii, Lij],
     [Lij, Ljj]]

with traceless coordinates

    a = (Lii-Ljj)/2
    b = Lij.

A closed loop around (a,b)=(0,0) has the real-eigenvector Z2 sign holonomy from
MovingProblem Gate 4.

Important:
- An open session's total Delta atan2 / 2pi is descriptive, not a topological
  winding number.
- We therefore detect near-return loop segments and only call those loops.
- The reported finding is real count minus phase-randomized surrogate floor.

This is a measurement tool, not a Pribram or brain model.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

Array = np.ndarray


@dataclass
class LoopEvent:
    pair_i: int
    pair_j: int
    start_window: int
    end_window: int
    winding: int
    parity: int
    closure_error: float
    min_radius: float
    median_radius: float


def load_stream(
    path: Path,
    *,
    max_seconds: float | None = None,
    max_channels: int | None = None,
    edf_eeg_only: bool = False,
    include_regex: str | None = None,
    exclude_regex: str | None = None,
    list_channels: bool = False,
) -> Tuple[Array, float | None]:
    suffix = path.suffix.lower()

    if suffix == ".npy":
        data = np.load(path)
        sample_rate = None

    elif suffix == ".csv":
        try:
            data = np.loadtxt(path, delimiter=",")
        except ValueError:
            data = np.genfromtxt(path, delimiter=",", dtype=float)
            if data.ndim == 2:
                good_rows = np.all(np.isfinite(data), axis=1)
                data = data[good_rows]
        sample_rate = None

    elif suffix == ".wav":
        from scipy.io import wavfile

        sample_rate, data = wavfile.read(path)
        data = np.asarray(data)
        if np.issubdtype(data.dtype, np.integer):
            info = np.iinfo(data.dtype)
            scale = max(abs(info.min), abs(info.max))
            data = data.astype(float) / float(scale)
        else:
            data = data.astype(float)

    elif suffix == ".edf":
        try:
            import mne
        except ImportError as exc:
            raise RuntimeError(
                "EDF support requires MNE: python -m pip install mne"
            ) from exc

        raw = mne.io.read_raw_edf(path, preload=False, verbose=False)
        sample_rate = float(raw.info["sfreq"])
        channel_types = raw.get_channel_types()

        if list_channels:
            for index, (name, kind) in enumerate(zip(raw.ch_names, channel_types)):
                print(f"{index:3d}  {kind:8s}  {name}")
            raise SystemExit(0)

        picks = list(range(len(raw.ch_names)))

        if edf_eeg_only:
            eeg_picks = [
                index
                for index, kind in enumerate(channel_types)
                if kind == "eeg"
            ]
            if eeg_picks:
                picks = eeg_picks
            else:
                raise ValueError(
                    "--edf-eeg-only requested but MNE marked no EDF channels as EEG"
                )

        if include_regex:
            rx = re.compile(include_regex, re.IGNORECASE)
            picks = [index for index in picks if rx.search(raw.ch_names[index])]

        if exclude_regex:
            rx = re.compile(exclude_regex, re.IGNORECASE)
            picks = [index for index in picks if not rx.search(raw.ch_names[index])]

        if max_channels is not None:
            picks = picks[: int(max_channels)]

        if len(picks) < 2:
            raise ValueError("channel filters left fewer than two EDF channels")

        selected = [
            f"{index}:{channel_types[index]}:{raw.ch_names[index]}"
            for index in picks
        ]
        print("Selected EDF channels:")
        for item in selected:
            print("  " + item)

        stop = None
        if max_seconds is not None:
            stop = min(
                raw.n_times,
                int(round(float(max_seconds) * sample_rate)),
            )
        data = raw.get_data(picks=picks, start=0, stop=stop).T

    else:
        raise ValueError("supported input types: .npy, .csv, .wav, .edf")

    data = np.asarray(data, dtype=float)

    if data.ndim == 1:
        raise ValueError("need a multichannel stream; got one channel")
    if data.ndim != 2:
        raise ValueError(f"expected samples x channels, got shape {data.shape}")

    # WAV convention and most numeric files already use samples x channels.
    # If there are implausibly few rows and many columns, transpose.
    if data.shape[0] < data.shape[1] and data.shape[0] <= 64:
        data = data.T

    finite = np.all(np.isfinite(data), axis=1)
    data = data[finite]

    if len(data) < 256:
        raise ValueError("stream is too short after cleaning")

    if max_channels is not None and data.shape[1] > int(max_channels):
        data = data[:, : int(max_channels)]

    if (
        max_seconds is not None
        and sample_rate is not None
        and len(data) > int(round(float(max_seconds) * float(sample_rate)))
    ):
        data = data[: int(round(float(max_seconds) * float(sample_rate)))]

    if data.shape[1] < 2:
        raise ValueError("need at least two channels")

    return data, float(sample_rate) if sample_rate is not None else None


def standardize(data: Array) -> Array:
    data = data - np.mean(data, axis=0, keepdims=True)
    scale = np.std(data, axis=0, keepdims=True)
    keep = scale.ravel() > 1e-10
    if np.count_nonzero(keep) < 2:
        raise ValueError("fewer than two non-constant channels")
    data = data[:, keep]
    scale = scale[:, keep]
    return data / scale


def global_whiten(data: Array, eps: float = 1e-8) -> Tuple[Array, Array]:
    cov = (data.T @ data) / len(data)
    cov = 0.5 * (cov + cov.T)
    values, vectors = np.linalg.eigh(cov)
    keep = values > eps * max(float(values.max()), 1.0)

    if np.count_nonzero(keep) < 2:
        raise ValueError("global covariance has rank < 2")

    values = values[keep]
    vectors = vectors[:, keep]
    whitening = vectors @ np.diag(1.0 / np.sqrt(values))
    whitened = data @ whitening
    return whitened, whitening


def symmetric_lag_operator(block: Array, lag: int) -> Array:
    if lag < 1 or lag >= len(block):
        raise ValueError("lag must satisfy 1 <= lag < window length")

    current = block[lag:]
    past = block[:-lag]
    op = (current.T @ past) / (len(block) - lag)
    return 0.5 * (op + op.T)


def operator_path(
    data: Array,
    *,
    window: int,
    hop: int,
    lag: int,
    modes: int,
) -> Tuple[Array, Array]:
    if window <= lag:
        raise ValueError("window must exceed lag")
    if hop < 1:
        raise ValueError("hop must be >= 1")

    whitened, _ = global_whiten(standardize(data))
    starts = np.arange(0, len(whitened) - window + 1, hop, dtype=int)

    if len(starts) < 8:
        raise ValueError("need at least 8 analysis windows")

    operators = np.stack(
        [symmetric_lag_operator(whitened[s : s + window], lag) for s in starts]
    )

    mean_operator = np.mean(operators, axis=0)
    values, vectors = np.linalg.eigh(mean_operator)
    order = np.argsort(np.abs(values))[::-1]
    k = min(int(modes), vectors.shape[1])
    reference = vectors[:, order[:k]]

    projected = np.einsum("di,tdc,cj->tij", reference, operators, reference)
    return projected, starts


def pair_paths(projected: Array) -> Dict[Tuple[int, int], Array]:
    result: Dict[Tuple[int, int], Array] = {}
    k = projected.shape[1]

    for i in range(k):
        for j in range(i + 1, k):
            a = 0.5 * (projected[:, i, i] - projected[:, j, j])
            b = projected[:, i, j]
            result[(i, j)] = np.column_stack([a, b])

    return result


def _angle_increment(x: float) -> float:
    return float((x + np.pi) % (2.0 * np.pi) - np.pi)


def unwrapped_phase(path: Array) -> Array:
    angle = np.arctan2(path[:, 1], path[:, 0])
    return np.unwrap(angle)


def descriptive_turns(path: Array) -> float:
    phase = unwrapped_phase(path)
    return float((phase[-1] - phase[0]) / (2.0 * np.pi))


def detect_near_return_loops(
    path: Array,
    pair: Tuple[int, int],
    *,
    min_loop_windows: int = 12,
    max_loop_windows: int = 200,
    return_fraction: float = 0.25,
    min_radius_fraction: float = 0.35,
    winding_tolerance: float = 0.20,
    absolute_noise_floor: float = 0.0,
) -> List[LoopEvent]:
    """Detect approximately closed loops around the origin.

    Thresholds are relative to the pair's median radius, which keeps the first
    version scale-free.  Surrogates receive exactly the same thresholds.
    """
    radius = np.linalg.norm(path, axis=1)
    median_radius = float(np.median(radius))

    if median_radius <= 1e-12:
        return []

    close_tol = return_fraction * median_radius
    radius_floor = max(
        min_radius_fraction * median_radius,
        float(absolute_noise_floor),
    )
    phase = unwrapped_phase(path)

    events: List[LoopEvent] = []
    occupied_until = -1
    n = len(path)

    for start in range(n):
        if start <= occupied_until:
            continue

        lo = start + min_loop_windows
        hi = min(n, start + max_loop_windows + 1)
        if lo >= hi:
            break

        best = None
        for end in range(lo, hi):
            closure = float(np.linalg.norm(path[end] - path[start]))
            if closure > close_tol:
                continue

            turns = float((phase[end] - phase[start]) / (2.0 * np.pi))
            winding = int(np.rint(turns))

            if winding == 0:
                continue
            if abs(turns - winding) > winding_tolerance:
                continue

            min_radius = float(np.min(radius[start : end + 1]))
            if min_radius < radius_floor:
                continue

            score = closure / (median_radius + 1e-12)
            candidate = (score, end, winding, closure, min_radius)
            if best is None or candidate[0] < best[0]:
                best = candidate

        if best is not None:
            _, end, winding, closure, min_radius = best
            events.append(
                LoopEvent(
                    pair_i=pair[0],
                    pair_j=pair[1],
                    start_window=start,
                    end_window=end,
                    winding=winding,
                    parity=abs(winding) % 2,
                    closure_error=float(closure / (median_radius + 1e-12)),
                    min_radius=min_radius,
                    median_radius=median_radius,
                )
            )
            occupied_until = end

    return events


def analyze_paths(
    projected: Array,
    *,
    min_loop_windows: int,
    max_loop_windows: int,
    return_fraction: float,
    min_radius_fraction: float,
    winding_tolerance: float,
    absolute_noise_floor: float = 0.0,
) -> Tuple[List[LoopEvent], Dict[str, float]]:
    pairs = pair_paths(projected)
    all_events: List[LoopEvent] = []
    turns: List[float] = []

    for pair, path in pairs.items():
        turns.append(abs(descriptive_turns(path)))
        all_events.extend(
            detect_near_return_loops(
                path,
                pair,
                min_loop_windows=min_loop_windows,
                max_loop_windows=max_loop_windows,
                return_fraction=return_fraction,
                min_radius_fraction=min_radius_fraction,
                winding_tolerance=winding_tolerance,
                absolute_noise_floor=absolute_noise_floor,
            )
        )

    odd = sum(event.parity == 1 for event in all_events)
    even = sum(event.parity == 0 for event in all_events)

    diagnostics = {
        "pairs": float(len(pairs)),
        "loops_total": float(len(all_events)),
        "odd_loops": float(odd),
        "even_loops": float(even),
        "mean_abs_open_path_turns": float(np.mean(turns)) if turns else 0.0,
        "max_abs_open_path_turns": float(np.max(turns)) if turns else 0.0,
    }
    return all_events, diagnostics


def phase_randomized_surrogate(data: Array, rng: np.random.Generator) -> Array:
    """Independent channel-wise phase randomization with matched magnitudes."""
    x = standardize(data)
    n, channels = x.shape
    spec = np.fft.rfft(x, axis=0)
    magnitude = np.abs(spec)

    phase = rng.uniform(0.0, 2.0 * np.pi, size=spec.shape)
    phase[0, :] = 0.0
    if n % 2 == 0:
        phase[-1, :] = 0.0

    randomized = magnitude * np.exp(1j * phase)
    randomized[0, :] = spec[0, :].real
    if n % 2 == 0:
        randomized[-1, :] = spec[-1, :].real

    out = np.fft.irfft(randomized, n=n, axis=0)
    return np.asarray(out, dtype=float)


def empirical_p_value(real_value: float, null: Array) -> float:
    return float((1.0 + np.sum(null >= real_value)) / (len(null) + 1.0))


def write_events(path: Path, events: Sequence[LoopEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(LoopEvent(0,0,0,0,0,0,0,0,0)).keys()))
        writer.writeheader()
        for event in events:
            writer.writerow(asdict(event))


def plot_summary(
    out_path: Path,
    projected: Array,
    real_events: Sequence[LoopEvent],
    null_odd: Array,
    real_diag: Dict[str, float],
) -> None:
    import matplotlib.pyplot as plt

    pairs = pair_paths(projected)
    pair_counts: Dict[Tuple[int, int], int] = {pair: 0 for pair in pairs}
    for event in real_events:
        if event.parity == 1:
            pair_counts[(event.pair_i, event.pair_j)] += 1

    fig = plt.figure(figsize=(12, 8))
    gs = fig.add_gridspec(2, 2)

    ax = fig.add_subplot(gs[0, 0])
    ax.hist(null_odd, bins="auto")
    ax.axvline(real_diag["odd_loops"])
    ax.set_title("Safe odd loops: real vs surrogate null")
    ax.set_xlabel("odd near-return loops")
    ax.set_ylabel("surrogate count")

    ax = fig.add_subplot(gs[0, 1])
    labels = [f"{i}-{j}" for i, j in pair_counts]
    values = [pair_counts[pair] for pair in pair_counts]
    ax.bar(np.arange(len(values)), values)
    ax.set_xticks(np.arange(len(values)))
    ax.set_xticklabels(labels, rotation=90)
    ax.set_title("Real odd-loop count by mode pair")
    ax.set_ylabel("count")

    ax = fig.add_subplot(gs[1, 0])
    shown = 0
    for pair, path in pairs.items():
        if shown >= 4:
            break
        ax.plot(path[:, 0], path[:, 1], label=f"{pair[0]}-{pair[1]}")
        shown += 1
    ax.scatter([0.0], [0.0], marker="x")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title("Example 2x2 operator-plane paths")
    ax.set_xlabel("a=(Lii-Ljj)/2")
    ax.set_ylabel("b=Lij")
    ax.legend()

    ax = fig.add_subplot(gs[1, 1])
    pair_names = []
    min_r = []
    med_r = []
    for pair, path in pairs.items():
        pair_names.append(f"{pair[0]}-{pair[1]}")
        radius = np.linalg.norm(path, axis=1)
        min_r.append(float(np.min(radius)))
        med_r.append(float(np.median(radius)))
    x = np.arange(len(pair_names))
    ax.plot(x, med_r, marker="o", label="median radius")
    ax.plot(x, min_r, marker=".", label="minimum radius")
    ax.set_xticks(x)
    ax.set_xticklabels(pair_names, rotation=90)
    ax.set_title("Pair radius / gap diagnostics")
    ax.legend()

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def synthetic_loop_stream(
    *,
    windows: int = 80,
    window: int = 1024,
    noise: float = 0.10,
    enclosing: bool = True,
    seed: int = 0,
) -> Array:
    """Positive control: fixed latent dynamics, slowly rotating observation frame.

    Two independent stationary AR(1) sources have fixed lag eigenvalues.
    Their observation basis rotates slowly.

    For a symmetric 2x2 operator, rotating the observation frame by angle theta
    rotates the traceless coordinates (a,b) by 2*theta.  Therefore a physical
    frame rotation from 0 to pi creates one closed winding at constant
    population eigengap, exactly the Gate-4 geometry.

    The non-enclosing control rotates only through pi/4 and therefore never
    closes a loop.

    Channel-wise phase randomization preserves each observed channel's global
    spectrum but destroys the coherent cross-channel moving-frame relation.
    """
    rng = np.random.default_rng(seed)
    total = windows * window
    result = np.zeros((total, 2), dtype=float)

    source = np.zeros(2, dtype=float)
    rhos = np.array([0.88, 0.28], dtype=float)
    innovation = np.sqrt(1.0 - rhos * rhos)

    max_theta = np.pi if enclosing else (np.pi / 4.0)

    for w in range(windows):
        theta = max_theta * w / max(windows - 1, 1)
        ct, st = np.cos(theta), np.sin(theta)
        mixing = np.array([[ct, -st], [st, ct]], dtype=float)

        for t in range(w * window, (w + 1) * window):
            source = rhos * source + innovation * rng.normal(size=2)
            result[t] = mixing @ source + noise * rng.normal(size=2)

    return result


def run_analysis(args: argparse.Namespace, data: Array, sample_rate: float | None) -> Dict[str, object]:
    projected, starts = operator_path(
        data,
        window=args.window,
        hop=args.hop,
        lag=args.lag,
        modes=args.modes,
    )

    real_events, real_diag = analyze_paths(
        projected,
        min_loop_windows=args.min_loop_windows,
        max_loop_windows=args.max_loop_windows,
        return_fraction=args.return_fraction,
        min_radius_fraction=args.min_radius_fraction,
        winding_tolerance=args.winding_tolerance,
        absolute_noise_floor=(
            args.noise_floor_multiple
            / np.sqrt(max(args.window - args.lag, 1))
        ),
    )

    rng = np.random.default_rng(args.seed)
    null_odd = np.zeros(args.surrogates, dtype=float)
    null_total = np.zeros(args.surrogates, dtype=float)

    for s in range(args.surrogates):
        surrogate = phase_randomized_surrogate(data, rng)
        surrogate_projected, _ = operator_path(
            surrogate,
            window=args.window,
            hop=args.hop,
            lag=args.lag,
            modes=args.modes,
        )
        _, diag = analyze_paths(
            surrogate_projected,
            min_loop_windows=args.min_loop_windows,
            max_loop_windows=args.max_loop_windows,
            return_fraction=args.return_fraction,
            min_radius_fraction=args.min_radius_fraction,
            winding_tolerance=args.winding_tolerance,
            absolute_noise_floor=(
                args.noise_floor_multiple
                / np.sqrt(max(args.window - args.lag, 1))
            ),
        )
        null_odd[s] = diag["odd_loops"]
        null_total[s] = diag["loops_total"]

    real_odd = float(real_diag["odd_loops"])
    null_mean = float(np.mean(null_odd))
    null_std = float(np.std(null_odd))
    excess = real_odd - null_mean
    z = excess / (null_std + 1e-12)

    summary: Dict[str, object] = {
        "samples": int(len(data)),
        "channels": int(data.shape[1]),
        "sample_rate": sample_rate,
        "window": int(args.window),
        "hop": int(args.hop),
        "lag": int(args.lag),
        "modes": int(args.modes),
        "windows": int(len(starts)),
        "surrogates": int(args.surrogates),
        "real": real_diag,
        "null_odd_mean": null_mean,
        "null_odd_std": null_std,
        "odd_loop_excess": excess,
        "odd_loop_z_vs_surrogate": z,
        "odd_loop_empirical_p": empirical_p_value(real_odd, null_odd),
        "null_total_mean": float(np.mean(null_total)),
        "null_total_std": float(np.std(null_total)),
    }

    prefix = Path(args.out)
    write_events(prefix.with_name(prefix.name + "_pairs.csv"), real_events)
    prefix.with_name(prefix.name + "_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    plot_summary(
        prefix.with_name(prefix.name + ".png"),
        projected,
        real_events,
        null_odd,
        real_diag,
    )
    return summary


def self_test(args: argparse.Namespace) -> Dict[str, object]:
    enclosing = synthetic_loop_stream(window=1024, enclosing=True, seed=args.seed)
    missing = synthetic_loop_stream(window=1024, enclosing=False, seed=args.seed + 1)

    test_args = argparse.Namespace(**vars(args))
    test_args.window = 1024
    test_args.hop = 1024
    test_args.lag = 1
    test_args.modes = 2
    test_args.surrogates = max(12, min(args.surrogates, 24))
    test_args.min_loop_windows = 20
    test_args.max_loop_windows = 100
    test_args.return_fraction = 0.40
    test_args.min_radius_fraction = 0.20
    test_args.winding_tolerance = 0.30
    test_args.noise_floor_multiple = 4.0

    test_args.out = str(Path(args.out).with_name(Path(args.out).name + "_enclosing"))
    positive = run_analysis(test_args, enclosing, None)

    test_args.out = str(Path(args.out).with_name(Path(args.out).name + "_nonenclosing"))
    negative = run_analysis(test_args, missing, None)

    result = {
        "enclosing_real_odd": positive["real"]["odd_loops"],
        "enclosing_null_mean": positive["null_odd_mean"],
        "nonenclosing_real_odd": negative["real"]["odd_loops"],
        "nonenclosing_null_mean": negative["null_odd_mean"],
    }

    if result["enclosing_real_odd"] < 1:
        raise RuntimeError("self-test failed: enclosing synthetic path produced no odd loop")
    if result["enclosing_real_odd"] <= result["enclosing_null_mean"]:
        raise RuntimeError(
            "self-test failed: positive control does not clear phase-randomized null"
        )
    if result["nonenclosing_real_odd"] != 0:
        raise RuntimeError("self-test failed: non-enclosing control produced an odd loop")
    if result["nonenclosing_null_mean"] > 0.25:
        raise RuntimeError("self-test failed: non-enclosing null floor is too high")

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count safe odd-winding near-return loops above a phase-randomized surrogate floor."
    )
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--window", type=int, default=2048)
    parser.add_argument("--hop", type=int, default=512)
    parser.add_argument("--lag", type=int, default=8)
    parser.add_argument("--modes", type=int, default=6)
    parser.add_argument("--surrogates", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=None,
        help="optional input-duration cap (useful for large EDF/WAV files)",
    )
    parser.add_argument(
        "--max-channels",
        type=int,
        default=None,
        help="optional channel cap, taking the first channels in the file",
    )
    parser.add_argument(
        "--edf-eeg-only",
        action="store_true",
        help="for EDF input, keep only channels MNE marks as EEG",
    )
    parser.add_argument(
        "--include-regex",
        type=str,
        default=None,
        help="for EDF input, keep only channel names matching this regex",
    )
    parser.add_argument(
        "--exclude-regex",
        type=str,
        default=None,
        help="for EDF input, drop channel names matching this regex",
    )
    parser.add_argument(
        "--list-channels",
        action="store_true",
        help="for EDF input, print index/type/name and exit",
    )
    parser.add_argument("--min-loop-windows", type=int, default=12)
    parser.add_argument("--max-loop-windows", type=int, default=200)
    parser.add_argument("--return-fraction", type=float, default=0.25)
    parser.add_argument("--min-radius-fraction", type=float, default=0.35)
    parser.add_argument("--winding-tolerance", type=float, default=0.20)
    parser.add_argument(
        "--noise-floor-multiple",
        type=float,
        default=4.0,
        help="minimum safe radius = multiple / sqrt(window-lag)",
    )
    parser.add_argument("--out", type=str, default="results/winding")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.self_test:
        result = self_test(args)
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if args.input is None:
        parser.error("provide an input file or use --self-test")

    data, sample_rate = load_stream(
        args.input,
        max_seconds=args.max_seconds,
        max_channels=args.max_channels,
        edf_eeg_only=args.edf_eeg_only,
        include_regex=args.include_regex,
        exclude_regex=args.exclude_regex,
        list_channels=args.list_channels,
    )
    summary = run_analysis(args, data, sample_rate)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
