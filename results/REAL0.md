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

The initial runs were treated conservatively as generic multichannel data because
the EDF channel typing had not yet been audited.

For **3.edf**, the pre-specified `--edf-eeg-only` replication selected all 64
channels, each marked `eeg` by MNE and carrying ordinary 10-10-style electrode
names. The EEG-only result was numerically identical to the original 3.edf run.

Therefore the mixed-channel caveat does **not** apply to 3.edf. The channel
typing of 2.edf should still be audited separately before calling that file EEG-only.

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

## EEG-only replication of 3.edf

Command:

```bash
python winding_count.py 3.edf --edf-eeg-only --surrogates 100 --out results/3_eeg
```

MNE selected all 64 channels as EEG.

The result was exactly identical to the original 3.edf run:

```text
real safe odd loops       2
surrogate mean            3.64 ± 1.74
real - null              -1.64
z                        -0.942
upper-tail empirical p    0.9208
```

So channel filtering did not rescue the holonomy hypothesis.

## Result

> **REAL0 is negative: neither recording shows excess safe odd-winding near-return loops above the phase-randomized null; 3.edf is confirmed EEG-only under MNE's channel typing.**

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

Because 3.edf has now been audited and all 64 channels are EEG, the next useful
step is no longer another filter of that same file. It is an **independent-file
replication** of the apparent negative excess.

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

Independent files repeatedly real > null:
    the holonomy question remains live.

Independent files repeatedly real ~= null:
    no evidence; move to the geometry-vs-coordinate drift measurement.

Independent files repeatedly real < null:
    quantify the apparent winding-suppression effect before interpreting it.
