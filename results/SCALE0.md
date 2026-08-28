# SCALE0 — choose the operator time scale without looking at winding

Date: 2026-08-28

The REAL1 candidate became sensitive to window / hop / lag. That means the
analysis time scale cannot be chosen because it produces a winding event.

SCALE0 freezes the time scale by an independent criterion.

## Selection criterion

For every candidate:

```text
window duration
lag duration
```

and every supplied recording:

1. standardize channels;
2. apply one global whitening transform;
3. fit a ridge linear lag predictor on the immediately preceding local window;
4. test it on the immediately following held-out block;
5. compute predictive gain relative to a zero predictor;
6. summarize the held-out gains within each file.

Across files, select the candidate with the largest:

```text
median(file-level median forward predictive gain)
```

with worst-file predictive gain used only as a tie-breaker.

**No winding count is computed during scale selection.**

## What is selected

Only:

```text
window_seconds
lag_seconds
```

The rest follows from fixed rules:

```text
hop = window / 4

minimum loop duration
    = 3 * window duration
```

The three-window minimum preserves the original detector's numerical resolution:

```text
window = 2048
hop    = 512 = window/4
minimum loop samples on path = 12 hops

12 * hop = 3 * window
```

but now that rule is physical rather than hidden in window counts.

## Why forward prediction

This gives the intended bias / variance / drift tradeoff without asking whether
a loop appears:

```text
window too short
    -> local operator estimate is noisy

window too long
    -> estimate averages over dynamics that have already changed

best held-out forward prediction
    -> independently useful local time scale
```

It does not prove a biological time constant.

It gives a non-topological operational criterion for the analysis scale.

## Run on the local EEG files

### Hold the candidate out

Because `1.edf` is the candidate being tested, SCALE0 should not use it to
choose the time scale.

Choose the predictive scale from `2.edf` and `3.edf` only, then apply that
frozen scale to `1.edf`.


```bash
python scale_select.py E:\\DocsHouse\\450 \
  --pattern "*.edf" \
  --edf-eeg-only \
  --out-dir results\\scale0
```

Default candidates:

```text
window: 4, 6, 8, 10, 12, 16, 20 seconds
lag:    25, 50, 100, 200 ms
```

Outputs:

```text
results/scale0/scale_scores.csv
results/scale0/scale_aggregate.json
results/scale0/scale_selection.png
results/scale0/selected_scale.json
```

## Then freeze it

After `selected_scale.json` exists, do not manually change window / lag / hop
for the winding test.

For example:

```bash
python winding_count.py E:\\DocsHouse\\450\\1.edf \
  --edf-eeg-only \
  --scale-json results\\scale0\\selected_scale.json \
  --surrogates 1000 \
  --out results\\scale0_1edf
```

Repeat the same scale file for 2.edf and 3.edf.

The scale file is stored in physical seconds, so it can later be transferred to
a recording with a different sample rate.

## Correction to REAL1_STRESS

The original stress runner varied `hop` while keeping `min_loop_windows=12`.

That accidentally changed the minimum physical duration of a candidate loop.

Therefore the old statement

```text
hop 384 / hop 640 killed the event
```

is confounded.

The stress runner has been corrected to express the minimum loop duration in
seconds.

Window and lag sensitivity remain real attacks because they change the
coarse-grained operator itself.

## Decision rule

After the scale is selected independently:

```text
candidate survives at frozen scale
    -> inspect / replicate the physical event

candidate disappears
    -> baseline 2048/8 result was scale-selected luck

different independent files show effect
at the same frozen physical scale
    -> much stronger evidence

files remain heterogeneous
    -> no population claim
```

SCALE0 is designed to stop the project from choosing the time scale because it
likes the topological answer.
