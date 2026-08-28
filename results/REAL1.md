# REAL1 — three-file EEG batch

Date: 2026-08-28

This batch is the first independent-file check after REAL0.

All three EDF files expose 64 channels marked EEG by MNE.

## Results

| file | samples | real odd | null mean ± std | excess | upper p | lower p | two-sided p |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1.edf | 9,760 | 2 | 0.25 ± 0.46 | +1.75 | 0.0198 | 1.0000 | 0.0396 |
| 2.edf | 19,680 | 1 | 3.31 ± 1.67 | -2.31 | 0.9703 | 0.1485 | 0.2970 |
| 3.edf | 19,680 | 2 | 3.64 ± 1.74 | -1.64 | 0.9208 | 0.2772 | 0.5545 |

Descriptive direction:

```text
positive excess   1 file
negative excess   2 files
zero excess       0 files
```

No combined p-value is reported.

## What changed

REAL0 looked uniformly negative.

REAL1 breaks that pattern because **1.edf** has two safe odd loops while its
phase-randomized surrogates almost never do.

That is interesting enough to attack, not enough to claim.

## Why 1.edf is fragile

1.edf is much shorter:

```text
1.edf     9,760 samples -> 16 analysis windows
2/3.edf 19,680 samples -> 35 analysis windows
```

Its two detected loops span almost the entire available trajectory:

```text
pair 2-4
    windows 2 -> 15
    winding +1
    closure error 0.058
    min radius 0.0924
    median radius 0.2605

pair 3-4
    windows 0 -> 14
    winding -1
    closure error 0.0686
    min radius 0.1090
    median radius 0.2247
```

The default finite-sample radius floor is

```text
4 / sqrt(2048-8) ~= 0.0886
```

so the pair 2-4 event clears the floor only modestly:

```text
0.0924 / 0.0886 ~= 1.04 x
```

while pair 3-4 clears it by about:

```text
0.1090 / 0.0886 ~= 1.23 x
```

That is the most important caveat in this batch.

One event is sitting just above the safety threshold.

## Statistical caution

The empirical upper-tail p=0.0198 comes from only 100 surrogates, so the Monte
Carlo resolution is coarse.

The two-sided p=0.0396 also does not survive a naive correction for looking at
three files:

```text
0.0396 * 3 ~= 0.119
```

That correction is not claimed as a formal batch model because the recordings'
independence / subject structure is not established. It simply shows why the
single-file p-value must not be treated as a discovery.

## Decision

> **Do not interpret 1.edf biologically yet. Stress the detector around that file.**

Pre-specified stress checks:

1. increase surrogates from 100 to at least 1,000;
2. vary window length around 2048;
3. vary hop;
4. vary lag;
5. vary return-fraction / winding-tolerance slightly;
6. vary finite-sample radius floor from 3 to 6 times 1/sqrt(N);
7. require the candidate to survive without moving from "safe" to "unsafe";
8. report which mode pair persists.

A real event should not depend on one permissive detector threshold.

## Current status

The three-file batch does **not** support a population-level claim of either
winding excess or winding suppression.

It does produce one candidate recording worth targeted robustness analysis.

That is the next measurement.


## Stress-test outcome

The requested one-factor-at-a-time robustness run is complete.

Raw aggregate:

```text
16 settings
11/16 positive real-minus-null
11/16 with at least one real safe odd loop
8/16 upper-tail p <= 0.05
```

However, inspection of the individual pair files shows that this aggregate is
too optimistic as a measure of a physical event.

The exact baseline loops survive detector-definition changes but disappear or
change identity under modest window/hop/lag perturbations. Both also sit close
to the configured finite-sample safety floor.

Therefore 1.edf remains a candidate only.

See [REAL1_STRESS.md](REAL1_STRESS.md) for the full interpretation.
