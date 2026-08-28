# PribamLives

> **Measurement: do real multichannel drift paths contain more safe odd-winding near-return loops than phase-randomized, spectrum-matched surrogates?**

The repository name is a joke, not a thesis.

No claim about Pribram, holography, engrams, fiber bundles, brains, or biological memory is required for the first experiment.

The first question is narrower:

> **Does the Gate-4 holonomy failure mode occur above its own finite-sample / phase-randomized null floor in an ordinary long multichannel stream?**

## Instrument status

The synthetic control is CI-verified:

```text
known enclosing moving-frame loop
    real odd-loop count       1
    phase-randomized null     0.0 mean

non-enclosing control
    real odd-loop count       0
    phase-randomized null     0.0 mean
```

A first version without the finite-sample safety floor failed this scientific control even though unit tests were green: its phase-randomized null produced about one spurious loop too. The current detector therefore requires a candidate loop to remain several `1/sqrt(N)` estimator-noise scales away from the degeneracy.

**No real-stream result has been claimed yet.**

## REAL0 — first real streams

Two local 64-channel EDF recordings were run with the default detector.

```text
2.edf
    real odd loops       1
    surrogate null       3.31 ± 1.67
    excess              -2.31
    empirical p          0.970

3.edf
    real odd loops       2
    surrogate null       3.64 ± 1.74
    excess              -1.64
    empirical p          0.921
```

**No excess holonomy was observed.** Both recordings went in the opposite direction: phase-randomized surrogates produced more safe odd loops than the real stream.

These EDFs contain mixed channel types, including auxiliary/device channels, so REAL0 is a generic multichannel result rather than an EEG-only neural result.

The all-channel result is frozen. The next pre-specified replication is EEG-only / channel-filtered, using:

```bash
python winding_count.py 3.edf --list-channels
python winding_count.py 3.edf --edf-eeg-only --surrogates 100
```

or explicit name-based exclusions if EDF type metadata are unreliable.

See [results/REAL0.md](results/REAL0.md).

## Why this repository exists

[MovingProblem](https://github.com/anttiluode/MovingProblem) was frozen at Gate 4 after finding a small but real failure mode:

- a real-symmetric frame can move around a degeneracy;
- the eigengap can remain safely large everywhere;
- every local confidence check can stay green;
- the operator can return to its starting point;
- yet a continuously transported **oriented** eigenvector can return with sign `-1`.

That topology is old mathematics. The open empirical question is whether real drifting streams actually execute such loops often enough to matter.

## One correction before measuring real data

For an arbitrary recording the operator trajectory is usually **open**.

Therefore

```text
Delta atan2(b,a) / (2 pi)
```

over the entire session is useful descriptive angular travel, but it is **not by itself a topological winding number** unless the path closes.

So the primary event detector here looks for **near-return loops**.

For each fixed pair of reference modes `(i,j)`, each window produces a 2x2 symmetric block

```text
[ L_ii  L_ij ]
[ L_ij  L_jj ]
```

and its traceless coordinates

```text
a_ij = (L_ii - L_jj) / 2
b_ij = L_ij
```

with local pair gap

```text
g_ij = 2 sqrt(a_ij^2 + b_ij^2).
```

A candidate loop must:

1. span at least `--min-loop-windows`;
2. return near its starting `(a,b)`;
3. have an unwrapped angle change near an integer multiple of `2 pi`;
4. stay above a configurable radial / gap floor;
5. have **odd winding parity** to imply the Gate-4 sign holonomy.

The raw count is still not the finding.

## The control comes first

Independent phase randomization is applied channel-by-channel:

- each channel keeps its Fourier magnitude spectrum;
- DC / Nyquist handling is preserved;
- random phases destroy cross-channel phase relationships;
- the surrogate has the same length, per-channel power spectrum and approximate autocorrelation structure.

Then the exact same winding detector runs on every surrogate.

The first reported quantity is:

```text
odd-loop excess
    =
real safe odd loops
    -
surrogate expected safe odd loops
```

plus a surrogate empirical p-value.

If the raw stream produces 30 loops and the surrogate produces 29, the result is zero.

## Fixed coordinate gauge

Window-to-window whitening would itself introduce a moving coordinate gauge.

So version 0 uses:

1. one global covariance whitening transform for the entire recording;
2. windowed symmetric lag covariances in that fixed whitened space;
3. one fixed reference eigenbasis from the mean lag operator;
4. pair trajectories measured in that common reference basis.

This is deliberately conservative. It makes the parameter path comparable across time before asking about winding.

## Accepted inputs

```text
.npy    samples x channels
.csv    numeric table; rows=samples, columns=channels
.wav    PCM WAV; mono is rejected, multichannel/stereo accepted
```

For CSV, non-numeric header rows are automatically dropped when possible.

## Run

```bash
python -m pip install -r requirements.txt

python winding_count.py my_recording.npy \
    --window 2048 \
    --hop 512 \
    --lag 8 \
    --modes 6 \
    --surrogates 100 \
    --out results/my_recording
```

Outputs:

```text
results/my_recording_summary.json
results/my_recording_pairs.csv
results/my_recording.png
```

The PNG contains:

- real versus surrogate safe odd-loop counts;
- pairwise real-minus-null excess;
- example operator-plane trajectories;
- current pair-gap / radius diagnostics.

## Synthetic self-test

Before trusting any real number:

```bash
python winding_count.py --self-test --out results/self_test
```

The self-test contains:

- an enclosing constant-gap loop: must produce an odd holonomy event;
- a non-enclosing loop: must not;
- a pure stationary multichannel null: real and surrogate counts should agree within noise.

CI runs this test.

## Interpretation

### If real >> surrogate

Then Gate 4 is not merely a constructed curiosity.

The next question becomes practical:

> how often would an oriented adaptive frame silently change meaning without local warning?

That can be turned into a calibration / audit rate.

### If real ~= surrogate

Say so.

Then the topological failure is not empirically live in that stream, and this repository should move to the cheaper second question:

> does relational geometry remain stable longer than individual coordinates?

No holography required.

## Current claim

None yet.

The repository begins with a detector, a surrogate, and a null.


## First real candidate

A convenient first real stream is already documented in [HeadAsResonator](https://github.com/anttiluode/HeadAsResonator):

```text
OpenNeuro ds007630
sub-03
ses-20240821
task-speechopen
acq-pangolin
run-02
140 channels
1200 Hz
```

The documented EDF filename is:

```text
sub-03_ses-20240821_task-speechopen_acq-pangolin_run-02_eeg.edf
```

A bounded first pass:

```bash
python -m pip install mne

python winding_count.py \
  sub-03_ses-20240821_task-speechopen_acq-pangolin_run-02_eeg.edf \
  --max-seconds 120 \
  --max-channels 32 \
  --window 2048 \
  --hop 512 \
  --lag 8 \
  --modes 6 \
  --surrogates 100 \
  --noise-floor-multiple 4 \
  --out results/ds007630_sub03_run02
```

That run has **not** been performed or claimed in this repository yet. The point of documenting it is to make the next move a measurement, not another synthetic gate.
