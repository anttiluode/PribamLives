# SCALE0 result — the candidate does not survive an independently chosen testable scale

Date: 2026-08-28

## What was selected

Scale selection used only `2.edf` and `3.edf` signal values.
`1.edf` was held out; only its duration/sample rate constrained whether a candidate scale could physically test a loop.

The predictive ranking preferred longer windows:

```text
20 s / 25 ms    predictive gain 0.4634   untestable on 1.edf
16 s / 25 ms    predictive gain 0.4143   untestable on 1.edf
12 s / 25 ms    predictive gain 0.3632   testable on 1.edf
10 s / 25 ms    predictive gain 0.3187
 8 s / 25 ms    predictive gain 0.2566
```

So the selected scale was:

```text
window = 12 s
lag    = 25 ms
hop    = 3 s
minimum loop duration = 36 s
```

Important:

> **12 seconds is not an independently discovered physiological optimum. It is the best predictive scale that is still physically testable on the 61-second held-out recording.**

The forward-prediction objective did not peak inside the tested range; it favored more data.

## Held-out winding result

At the frozen scale:

```text
real safe odd loops       0
surrogate mean            0.314 ± 0.563
real - null              -0.314
upper-tail p              1.0
lower-tail p              0.732
operator windows          17
minimum required          13
```

So this run is genuinely testable, unlike the first 20-second SCALE0 attempt.

## What it means

The original `1.edf` baseline candidate:

```text
window = 12.8 s
lag    = 50 ms
real odd loops = 2
null mean ~= 0.25
```

does **not** survive when window/lag are chosen independently of winding.

That is the strongest evidence so far that the original positive was an analysis-scale-dependent event rather than a robust physical holonomy observation.

## Current empirical status

Across the three local EEG recordings:

- `2.edf`: no excess winding at the original default scale;
- `3.edf`: no excess winding at the original default scale;
- `1.edf`: one baseline-scale positive candidate, but it weakens under scale attacks and disappears at the independently selected testable scale.

Therefore:

> **PribamLives currently has no robust real-EEG evidence that Gate-4 odd-winding holonomy occurs above a phase-randomized null floor.**

This does not invalidate the synthetic Gate-4 failure mode.

It says the phenomenon has not been shown to be empirically live in these recordings under this lag-operator measurement.

## What SCALE0 itself taught us

The prediction criterion did not identify a natural analysis timescale. Predictive gain increased with longer windows over the tested range.

That suggests the current local linear predictor is still mostly in an estimator-variance regime: more samples help more than local drift hurts, at least out to 20 seconds on `2.edf` and `3.edf`.

So if a future project needs a genuine physical timescale, it needs a criterion that exhibits an interior optimum or is externally grounded.

## Stop condition

Do not tune the winding detector further on these three files.

The next scientifically distinct question should either:

1. test the holonomy bug in an actual adaptive BSS/frame-tracking system with a sign-sensitive downstream task; or
2. move to the second real-data question: whether relational/subspace geometry remains stable when coordinate-level decoders drift.

Further parameter tuning on the same three EDFs would mostly be analysis gardening.
