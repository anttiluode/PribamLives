#!/usr/bin/env python3
"""Robustness analysis for a single candidate recording.

This is intentionally one-factor-at-a-time around the frozen default detector.
It is not a hyperparameter search for the smallest p-value.

For every setting:
- rerun the real detector;
- generate a fresh phase-randomized null;
- report real odd loops, null mean, excess, and both-tail Monte Carlo p-values.

The main summary asks how often the *direction* and at least one safe odd event
survive modest detector perturbations.
"""
from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from pathlib import Path

from winding_count import build_parser, load_stream, run_analysis


def make_settings():
    base = {
        "name": "baseline",
        "window": 2048,
        "hop": 512,
        "lag": 8,
        "modes": 6,
        "return_fraction": 0.25,
        "winding_tolerance": 0.20,
        "noise_floor_multiple": 4.0,
    }
    settings = [base.copy()]

    def add(field, values):
        for value in values:
            if value == base[field]:
                continue
            row = base.copy()
            row["name"] = f"{field}={value}"
            row[field] = value
            settings.append(row)

    add("window", [1792, 2304])
    add("hop", [384, 640])
    add("lag", [4, 16])
    add("modes", [5, 7])
    add("return_fraction", [0.20, 0.30])
    add("winding_tolerance", [0.15, 0.25])
    add("noise_floor_multiple", [3.5, 4.5, 5.0])

    return settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--surrogates", type=int, default=250)
    parser.add_argument("--edf-eeg-only", action="store_true")
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--out-dir", type=Path, default=Path("results/candidate_stress"))
    args = parser.parse_args()

    data, sample_rate = load_stream(
        args.input,
        edf_eeg_only=args.edf_eeg_only,
    )

    default_args = build_parser().parse_args([])
    rows = []
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for index, setting in enumerate(make_settings()):
        run_args = deepcopy(default_args)
        run_args.surrogates = args.surrogates
        run_args.seed = args.seed + 1009 * index

        for key, value in setting.items():
            if key != "name":
                setattr(run_args, key, value)

        safe_name = setting["name"].replace("=", "_").replace(".", "p")
        run_args.out = str(args.out_dir / safe_name)

        print(f"\n=== {setting['name']} ===")
        summary = run_analysis(run_args, data, sample_rate)

        rows.append(
            {
                **setting,
                "real_odd": summary["real"]["odd_loops"],
                "null_mean": summary["null_odd_mean"],
                "null_std": summary["null_odd_std"],
                "excess": summary["odd_loop_excess"],
                "z": summary["odd_loop_z_vs_surrogate"],
                "p_upper": summary["odd_loop_empirical_p_upper"],
                "p_lower": summary["odd_loop_empirical_p_lower"],
                "p_two_sided": summary["odd_loop_empirical_p_two_sided"],
                "positive_excess": summary["odd_loop_excess"] > 0,
                "has_real_event": summary["real"]["odd_loops"] >= 1,
            }
        )

    fields = list(rows[0].keys())
    csv_path = args.out_dir / "robustness_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    json_path = args.out_dir / "robustness_summary.json"
    json_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    positive = sum(bool(row["positive_excess"]) for row in rows)
    has_event = sum(bool(row["has_real_event"]) for row in rows)
    p05 = sum(float(row["p_upper"]) <= 0.05 for row in rows)

    print("\n=== robustness, descriptive only ===")
    print(f"settings: {len(rows)}")
    print(f"positive real-minus-null excess: {positive}/{len(rows)}")
    print(f"at least one real safe odd loop: {has_event}/{len(rows)}")
    print(f"upper-tail p <= 0.05: {p05}/{len(rows)}")
    print("These settings are sensitivity checks, not independent hypothesis tests.")
    print(f"wrote {csv_path}")
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()
