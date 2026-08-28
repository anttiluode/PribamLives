# REAL0 — first local EDF streams

Date: 2026-08-28

This is the first real-stream receipt in PribamLives.

The raw EDF files are not committed. Only derived counts are recorded.

## Measurement

Default detector settings:

```text
64 channels
160 Hz
19680 samples
window 2048
hop 512
lag 8
6 modes -> 15 mode pairs
100 phase-randomized surrogates
```

The EDFs contain a mixture of channel types, including non-neural auxiliary
channels such as temperature/device channels. Therefore this is a test of
**generic multichannel drift**, not yet an EEG-only brain claim.

## Local file 2.edf

```text
real safe odd loops       1
surrogate mean            3.31 ± 1.67
real - null              -2.31
z                        -1.382
upper-tail empirical p    0.9703
```

No excess winding.

## Local file 3.edf

```text
real safe odd loops       2
surrogate mean            3.64 ± 1.74
real - null              -1.64
z                        -0.942
upper-tail empirical p    0.9208
```

No excess winding.

The two detected real candidate loops were:

```text
mode pair 0-5
    closure error / median radius   0.193
    minimum radius                  0.232
    median radius                   0.451

mode pair 2-4
    closure error / median radius   0.206
    minimum radius                  0.204
    median radius                   0.572
```

With the default finite-sample floor,

```text
4 / sqrt(window-lag)
= 4 / sqrt(2040)
≈ 0.0886
```

both candidates are well outside the detector's unsafe near-degeneracy region.

That does **not** make them discoveries. The surrogate produces more such
events on average.

## Result

> **REAL0 is negative: these two mixed-channel EDF streams do not show excess safe odd-winding near-return loops above the phase-randomized null.**

Indeed the direction is reversed in both files.

This is not evidence that real streams never contain Gate-4 holonomy. It says
that under this fixed-gauge lag-operator measurement and these two recordings,
the effect is not above the null floor.

## Interesting anti-result

Both recordings have fewer real loops than phase-randomized surrogates.

A possible interpretation is that real cross-channel coupling constrains the
operator trajectory and suppresses random winding, while destroying coupling
releases more wandering.

That is **post-hoc** and is not claimed from two files.

If the same negative excess repeats across many independent recordings, it
becomes a different measurable question.

## Pre-specified replication

Because the EDFs contain temperature / device / auxiliary channels, the next
replication should be selected by channel metadata/name **before** rerunning.

Inspect:

```bash
python winding_count.py 3.edf --list-channels
```

If MNE channel types are trustworthy:

```bash
python winding_count.py 3.edf --edf-eeg-only --surrogates 100
```

If channel types are not trustworthy, use channel-name rules, for example:

```bash
python winding_count.py 3.edf \
  --exclude-regex "TEMP|TEMPERATURE|ECG|EKG|EOG|EMG|RESP|STATUS|EVENT|TRIG|STIM" \
  --surrogates 100
```

The all-channel REAL0 result remains frozen regardless of what EEG-only does.

## Decision rule

EEG-only real > null:
    the holonomy question remains live in neural channels.

EEG-only real ~= null:
    no evidence; move to the geometry-vs-coordinate drift measurement.

EEG-only real < null:
    replicate the apparent suppression effect before interpreting it.
