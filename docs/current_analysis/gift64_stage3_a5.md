# GIFT-64 Pipeline A5: Controlled Stage 3 Remaining-Probability Boundary

> Completed locally: 2026-07-26
>
> Scope: reproduce the observable Stage 3 subcube-counting procedure with a
> deterministic replacement for its unrecorded entropy source, a supplied
> 1,000-key fixture, explicit physical trail/key selection, and bounded sample
> runs. This checkpoint does not reproduce a paper-level probability result.

## Result

Stage 3 is now available as a bounded fixed-key subcube-counting demo:

```text
provided KeyCandidate1000.out fixture (read-only, hash-pinned)
  + supplied TrailInformation.out record position
  + deterministic 21-bit input restriction per sample
  -> enumerate all surviving first-round input states in that subcube
  -> complete count only when native enumeration ends UNSAT and all 64 target
     input bits are defined in every enumerated model
  -> mean(count / 2^43), with descriptive dispersion only
```

The tracked request
[`experiments/gift64/stage3_probability_a5.request.json`](../../experiments/gift64/stage3_probability_a5.request.json)
uses fixture key position 0, physical trail-record position 0, the legacy
default of 100 deterministic subcube samples, 21 fixed bits, a 30-second limit
per sample and a 300-second total wall-time budget. The separate
[`experiments/gift64/stage3_probability_smoke_a5.request.json`](../../experiments/gift64/stage3_probability_smoke_a5.request.json)
retains eight samples and a 60-second total budget for smoke testing.
Run it from the repository root with:

```bash
PYTHONPATH=src python3 scripts/run_gift64_stage3_probability_demo.py
```

The command prints a JSON-compatible observation only. Generated stdout,
per-sample assignments, binaries and result files are temporary and untracked.
The observation schema is `gift64-stage3-probability-observation/v3`.

## What the legacy program actually does

The upstream Stage 3 source does not loop over all supplied fixture keys in one
execution. Its checked-in settings are:

- `TargetKeyIndex = 0` from `KeyCandidate1000.out`;
- `TestTrailIndex = 0` from the 32 physical `TrailInformation.out` records;
- `RepeatTestTime = 100`; and
- `RandomFixBitNum = 21`.

For every repetition, it selects 21 distinct positions from the 64-bit first
input state, assigns random values to those positions, then repeatedly solves
and blocks each discovered `xin_pair1[0]` assignment. The counter is therefore
the number of satisfying states in one sampled subcube of size:

```text
2^(64 - 21) = 2^43.
```

For a complete enumeration count `C_i`, A5 records the per-sample quantity
`C_i / 2^43`; the point estimate is their arithmetic mean. This is a
subcube-sampling estimate of the selected fixed-key/trail probability, not a
Markov trail probability or a full right-key-space measurement.

## Controlled changes and provenance

| Artifact | SHA-256 |
|---|---|
| Stage 3 `main.cpp` | `40b71f4fd21798bcae68bcd76922e788eb19f795d5a0e788abd0cc721c6f81ca` |
| `TrailInformation.out` | `fe40ca7b81d4c362d45db58c7c4448317d0305bbd149e04abe12bcede8c02335` |
| `KeyCandidate1000.out` | `d97ee7bedccfe2f8d6df9e48a2da7e0bdb6524cfe1188e8e5e6bf8a8107d761e` |

The adapter uses an out-of-tree source copy and rejects any changed source
anchor. It changes only the experiment controls:

1. binds the legacy loop to one configured fixture-key position and one
   configured physical trail-record position;
2. changes the repeat loop to one sample per process, so the process timeout is
   unambiguously per sample, and enforces a request-level total wall-time
   budget across compilation and every sample;
3. replaces `std::random_device` with `mt19937_64`, seeded from the request
   seed and a per-process sample index; and
4. replaces the legacy 32-bit solution counter with an unsigned 64-bit counter,
   requires all 64 blocked `xin_pair1[0]` model bits to be defined, and emits a
   controlled `ERROR` marker if that completeness condition fails; and
5. emits a marker containing the sampled bit/value restriction, solution count
   and terminal enumeration status.

The GIFT model, DDT construction, key schedule, clauses, solver calls and
solution-blocking loop remain in the legacy execution path.

## Completion and statistical policy

A sample contributes to the estimate only when its solution-blocking loop
terminates with native `UNSAT` and every blocked model had a fully defined
64-bit `xin_pair1[0]` assignment. That means the temporary process exhausted
the distinct target-input states for its selected subcube. `UNKNOWN`, process
`TIMEOUT`, undefined-model `ERROR`, marker error or nonzero exit makes the
whole estimate unavailable rather than silently treating a partial count as
exact.

If the total budget expires before a later sample process starts, that sample
is recorded as `execution_state: not_started_total_budget` with a null terminal
status. It is reported separately and is not counted as a solver `TIMEOUT`.

A5 emits the point estimate, sample minimum/maximum and sample standard
deviation when at least two samples complete. It deliberately does **not** emit
a confidence interval: deterministic pseudo-random subcubes and especially
all-zero samples do not justify a zero-width "95%" interval or a claim that the
underlying probability is zero. These values are not PAC approximate model
counts or certified probability bounds.

The provided `KeyCandidate1000.out` file is an upstream fixture, not a corpus
we generated. Its random-generation algorithm, seed, distribution and relation
to the missing Stage 2 million-key file are unknown. It may be used as a
hash-pinned read-only input, but not as evidence that its population is a
reproducible representative sample.

## Acceptance evidence

Implementation:

- `src/automated_differential_analysis/formats/gift64_stage3_probability.py`
- `src/automated_differential_analysis/adapters/gift64_stage3_legacy.py`
- `scripts/run_gift64_stage3_probability_demo.py`

Tests cover request limits, finite resource budgets, estimator arithmetic,
impossible counts, hash-pinned instrumentation, exact marker parsing including
the undefined-model error state, and a real fixture-backed integration run. The
integration test executes the same one-sample request twice and requires
identical sampled restrictions, terminal status and solution count. Generated
values are intentionally not committed.

## Reporting language and boundaries

The supported wording is:

> A5 provides a deterministic, resource-bounded reproduction of the observable
> Stage 3 subcube-counting workflow for one selected key from the supplied
> 1,000-key fixture and one selected physical trail record. It records a
> descriptive empirical estimate only when every selected subcube is fully
> enumerated.

Do not state that A5:

- reproduces the authors' original entropy sequence, all 1,000 fixture keys or
  any paper table/result;
- proves that the fixture is representative, independently regenerable or a
  subset of `KeyCandidate.out`;
- produces an exact global probability, an exact model count, a PAC guarantee
  or an independent proof of an `UNSAT` termination;
- validates all 32 trail records, a producer `GroupIndex`, the full differential
  or a key-recovery claim.

## Integration boundary

For a stronger demo, extend the explicitly budgeted request across selected
fixture-key positions and physical trail-record positions. Any aggregation must
report its conditioning and assumptions rather than summing per-trail estimates
as if they were automatically independent. The supplied fixture has no proven
lineage from A4's generated demo corpus, so A5 remains an independently
provenanced boundary inside the unified orchestration.
