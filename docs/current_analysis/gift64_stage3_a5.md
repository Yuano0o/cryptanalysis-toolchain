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
  -> complete count only when native enumeration ends UNSAT
  -> mean(count / 2^43), with a descriptive sample interval when n >= 2
```

The tracked request
[`experiments/gift64/stage3_probability_a5.request.json`](../../experiments/gift64/stage3_probability_a5.request.json)
uses fixture key position 0, physical trail-record position 0, eight
deterministic subcube samples, 21 fixed bits and a 30-second limit per sample.
Run it from the repository root with:

```bash
PYTHONPATH=src python3 scripts/run_gift64_stage3_probability_demo.py
```

The command prints a JSON-compatible observation only. Generated stdout,
per-sample assignments, binaries and result files are temporary and untracked.

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
   unambiguously per sample;
3. replaces `std::random_device` with `mt19937_64`, seeded from the request
   seed and a per-process sample index; and
4. emits a marker containing the sampled bit/value restriction, solution count
   and terminal enumeration status.

The GIFT model, DDT construction, key schedule, clauses, solver calls and
solution-blocking loop remain in the legacy execution path.

## Completion and statistical policy

A sample contributes to the estimate only when its solution-blocking loop
terminates with native `UNSAT`: that means the temporary process exhausted the
solutions for its selected subcube. `UNKNOWN`, process `TIMEOUT`, marker error
or nonzero exit makes the whole estimate unavailable rather than silently
treating the partial count as exact.

With at least two complete samples, A5 additionally emits a normal-approximate
95% interval over the sample fractions. This is descriptive only: the samples
are deterministic pseudo-random subcubes, are too few for a strong asymptotic
claim in the default configuration, and are not PAC approximate model counts.

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

Tests cover request limits, estimator arithmetic, impossible counts,
hash-pinned instrumentation, exact marker parsing and a real fixture-backed
integration run. The integration test executes the same one-sample request
twice and requires identical sampled restrictions, terminal status and solution
count. A local eight-sample run of the tracked request completed under its
limits; its generated values are intentionally not committed.

## Reporting language and boundaries

The supported wording is:

> A5 provides a deterministic, resource-bounded reproduction of the observable
> Stage 3 subcube-counting workflow for one selected key from the supplied
> 1,000-key fixture and one selected physical trail record. It records a
> descriptive empirical estimate only when every selected subcube is fully
> enumerated.

Do not state that A5:

- reproduces the authors' original entropy sequence, all 100 repetitions, all
  1,000 fixture keys or any paper table/result;
- proves that the fixture is representative, independently regenerable or a
  subset of `KeyCandidate.out`;
- produces an exact global probability, an exact model count, a PAC guarantee
  or an independent proof of an `UNSAT` termination;
- validates all 32 trail records, a producer `GroupIndex`, the full differential
  or a key-recovery claim.

## Next boundary

For a stronger demo, choose an explicit total time budget and then extend the
request across selected fixture-key positions and physical trail-record
positions. Any aggregation must report its conditioning and assumptions rather
than summing per-trail estimates as if they were automatically independent.
