#!/usr/bin/env python3
"""Batch PribamLives winding analysis across independent recordings.

This intentionally does NOT combine p-values or pretend recordings from the
same subject/session are statistically independent. It writes one row per file
so replication structure remains visible.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from winding_count import build_parser, load_stream, run_analysis


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--pattern", default="*.edf")
    parser.add_argument("--surrogates", type=int, default=100)
    parser.add_argument("--edf-eeg-only", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=None)
    parser.add_argument("--max-channels", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("results/batch"))
    args = parser.parse_args()

    files = sorted(args.folder.glob(args.pattern))
    if not files:
        raise SystemExit(f"no files matched {args.folder / args.pattern}")

    base = build_parser().parse_args([])
    base.surrogates = args.surrogates
    base.edf_eeg_only = args.edf_eeg_only
    base.max_seconds = args.max_seconds
    base.max_channels = args.max_channels
    base.list_channels = False

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    for path in files:
        print(f"\n=== {path.name} ===")
        data, sample_rate = load_stream(
            path,
            max_seconds=base.max_seconds,
            max_channels=base.max_channels,
            edf_eeg_only=base.edf_eeg_only,
            include_regex=base.include_regex,
            exclude_regex=base.exclude_regex,
            list_channels=False,
        )
        base.out = str(args.out_dir / path.stem)
        summary = run_analysis(base, data, sample_rate)

        row = {
            "file": path.name,
            "channels": summary["channels"],
            "samples": summary["samples"],
            "real_odd": summary["real"]["odd_loops"],
            "null_mean": summary["null_odd_mean"],
            "null_std": summary["null_odd_std"],
            "excess": summary["odd_loop_excess"],
            "z": summary["odd_loop_z_vs_surrogate"],
            "p_upper": summary["odd_loop_empirical_p_upper"],
            "p_lower": summary["odd_loop_empirical_p_lower"],
            "p_two_sided": summary["odd_loop_empirical_p_two_sided"],
        }
        rows.append(row)

    csv_path = args.out_dir / "batch_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = args.out_dir / "batch_summary.json"
    json_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    negative = sum(float(row["excess"]) < 0 for row in rows)
    positive = sum(float(row["excess"]) > 0 for row in rows)
    zero = len(rows) - negative - positive

    print("\n=== descriptive batch direction only ===")
    print(f"files: {len(rows)}")
    print(f"negative excess: {negative}")
    print(f"positive excess: {positive}")
    print(f"zero excess: {zero}")
    print("No combined significance is reported; independence must be justified separately.")
    print(f"wrote {csv_path}")
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()
