# REAL1 stress test — candidate weakens under time-scale attacks

Date: 2026-08-28

This receipt interprets the 16-setting one-factor-at-a-time stress test for
`1.edf`.

Raw aggregate:

```text
settings                         16
positive real-minus-null         11 / 16
at least one real safe odd loop  11 / 16
upper-tail p <= 0.05              8 / 16
```

Those numbers are descriptive sensitivity counts, not independent tests.

More importantly, **11/16 overstates robustness** because several perturbations
do not materially change the baseline operator path.

## Baseline

Two odd loops:

```text
pair 2-4
    windows 2 -> 15
    winding +1
    closure / median radius  0.0581
    min radius               0.09242

pair 3-4
    windows 0 -> 14
    winding -1
    closure / median radius  0.0686
    min radius               0.10904
```

With noise-floor multiple 4:

```text
floor = 4 / sqrt(2040) ~= 0.08856
```

so pair 2-4 clears the floor by only about 4%, and pair 3-4 by about 23%.

## Perturbations that preserve the same exact loops

These are useful checks of the event detector, but they are not independent
evidence that the physical phenomenon survives a changed analysis scale.

```text
modes 5
modes 7
return fraction 0.20
return fraction 0.30
winding tolerance 0.15
winding tolerance 0.25
noise-floor multiple 3.5
```

All retain the same pair 2-4 and pair 3-4 loop coordinates as baseline.

The surrogate excess remains positive in these settings.

## Noise-floor attack

```text
floor multiple 4.0:
    pair 2-4 + pair 3-4

floor multiple 4.5:
    only pair 3-4 survives
    real 1 vs null 0.185
    upper p 0.168

floor multiple 5.0:
    no real loop
```

At 4.5:

```text
floor ~= 0.09963
```

which removes pair 2-4 but leaves pair 3-4.

At 5.0:

```text
floor ~= 0.11070
```

which is just above pair 3-4's minimum radius 0.10904.

So both baseline events live close to the current finite-sample safety boundary.

## Time-scale / sampling attacks

These are more damaging.

| perturbation | real odd loops | null mean | excess | upper p | surviving pair |
|---|---:|---:|---:|---:|---|
| baseline | 2 | 0.246 | +1.754 | 0.022 | 2-4, 3-4 |
| window 1792 | 1 | 0.277 | +0.723 | 0.247 | **4-5** |
| window 2304 | 0 | 0.214 | -0.214 | 1.000 | none |
| hop 384 | 0 | 0.590 | -0.590 | 1.000 | none |
| hop 640 | 0 | 0.048 | -0.048 | 1.000 | none |
| lag 4 | 0 | 0.247 | -0.247 | 1.000 | none |
| lag 16 | 1 | 0.254 | +0.746 | 0.224 | **2-4, but different window path** |

This is the critical result.

The exact baseline loops are **not stable under modest changes in temporal
resolution / sampling**.

Window 1792 produces a different pair (4-5).

Lag 16 produces pair 2-4, but over windows 0 -> 14 with different geometry.

Changing hop alone removes the event entirely.

## Interpretation

The stress test does **not** justify upgrading 1.edf from "candidate" to
"observed real holonomy."

The honest statement is:

> **At the baseline temporal discretization, 1.edf contains two near-return odd-winding paths that are unusually rare under phase-randomized surrogates and are stable to several detector-definition changes. However, they are close to the finite-sample safety floor and do not persist as the same events under modest changes in window, hop, or lag.**

That makes them analysis-scale-sensitive candidate structures, not yet robust
physical loops.

## What the stress test did earn

It identified the next question more sharply:

> **Is there a physically meaningful time scale at which a drifting EEG operator path should be defined?**

If the event is real, arbitrary changes to window/hop are not necessarily
supposed to preserve it: those parameters change the temporal coarse-graining
of the path itself.

But choosing the favorable scale after seeing the answer would be circular.

Therefore the next useful experiment should obtain the time scale from an
independent criterion, for example:

- estimator-error vs drift tradeoff;
- cross-validated predictive stability;
- an external physiological time scale;
- a second recording with the analysis scale fixed in advance.

Until then, 1.edf remains a candidate only.

## Bottom line

```text
detector-definition robustness:  fairly good
finite-sample-margin robustness: weak
time-scale robustness:           poor
independent-file replication:    absent
```

That is weaker than the raw 11/16 count, but much more informative.
