# GIFT-64 Pipeline A4: Controlled Stage 2 Fixed-Key Boundary

> Completed locally: 2026-07-26
>
> Scope: replace the unavailable author key corpus with an explicitly labelled,
> deterministic demo corpus; expose the legacy Stage 2 trail selection; and
> record bounded native solver statuses with provenance. This checkpoint is not
> a reproduction of the paper's million-key experiment.

## Result

Stage 2 can now run as a controlled, reproducible demo:

```text
versioned generated-for-demo key-corpus specification
  -> canonical temporary KeyCandidate.out (eight 16-bit words per key)
  -> hash-pinned temporary one-key / one-trail Stage 2 source copy
  -> native CryptoMiniSat status marker
  -> gift64-stage2-observation/v2 JSON-compatible summary
```

The formal demo request
[`experiments/gift64/stage2_demo_a4.request.json`](../../experiments/gift64/stage2_demo_a4.request.json)
selects physical trail-record position 0 and 1,000 deterministic 128-bit keys.
It has a 30-second limit per key and a finite 120-second total run budget. The
separate default smoke request
[`experiments/gift64/stage2_demo_smoke_a4.request.json`](../../experiments/gift64/stage2_demo_smoke_a4.request.json)
uses eight keys and a 60-second total budget. Generated keys, solver stdout,
logs, binaries and result summaries remain temporary and untracked.

Run the demo from the repository root with:

```bash
PYTHONPATH=src python3 scripts/run_gift64_stage2_demo.py
```

The command runs the smoke request by default and prints a structured summary
to stdout. Use `--request experiments/gift64/stage2_demo_a4.request.json` for
the formal 1,000-key demo. Redirect output outside the repository if a local
result needs to be retained.

## What the upstream Stage 2 program tests

For a fixed primary 128-bit master key, the legacy SAT model constrains a
related second key by the selected trail's key-state difference, constrains the
eight-round differential from the supplied `TrailInformation.out`, and asks
whether a satisfying pair remains. Its native outcome is therefore a per-key
`SAT`, `UNSAT` or `UNKNOWN` status for that selected trail record.

This is a fixed-key validity query. It is **not** a recovered key, an exact
right-key-space enumeration, a probability estimate, or an independent proof
of an `UNSAT` result. The legacy program produces no proof artifact, so A4
does not label its `UNSAT` statuses as independently verified exact results.

## Recovered legacy limitations

The original `main.cpp`:

- reads `KeyCandidate.out` as exactly 1,000,000 records of eight hexadecimal
  16-bit words;
- allocates a matching fixed-size buffer;
- loads all 32 supplied records but executes only
  `for (int trail = 0; trail < 1; trail++)`;
- reports only unstructured `l_True` / `l_False` terminal text; and
- does not validate its input-file length, key provenance or trail selection.

The author `KeyCandidate.out` is absent. Its generator, distribution, seed,
ordering and hash are also absent. Consequently, the original population and
its paper-level count cannot be reconstructed from the available materials.

## Controlled adapter semantics

The adapter pins the supplied source and trail corpus:

| Artifact | SHA-256 |
|---|---|
| Stage 2 `main.cpp` | `58f5d24110cf8170de6cc0f1cdd29657abc1463bf044703756e052b640275964` |
| `TrailInformation.out` | `fe40ca7b81d4c362d45db58c7c4448317d0305bbd149e04abe12bcede8c02335` |

For each configured key, it creates an out-of-tree source copy that is checked
against fixed source anchors before changing only these controls:

1. the key buffer and both key loops are bound to one record;
2. the legacy `trail < 1` loop is replaced by the explicitly configured
   physical record position; and
3. the existing `solver.solve()` call emits one adapter-owned status marker to
   stderr.

The DDT construction, key schedule, SAT clauses, affine constraints, solver
call and legacy stdout are otherwise left in the source's execution path. Each
key is launched in a separate process, which makes the configured timeout a
real per-key resource limit rather than a single ambiguous batch timeout. The
request also has a finite total budget covering compilation and all key runs.
If it expires before a key starts, the result records
`execution_state: not_started_total_budget` and `status: null`; it is not
counted as a native solver status. If it expires while a launched key is still
running, that launched process is recorded as `TIMEOUT` with a total-budget
diagnostic. Every observation records `run_wall_time_s` and whether its total
budget was exhausted.

The selected position is deliberately a **physical TrailInformation record
position** in `0..31`, not an inferred producer `GroupIndex`. The supplied
corpus's concatenation order is not proven to match the producer's group order.

## Deterministic demo key corpus

`gift64-stage2-key-corpus/v1` generates each 128-bit key with a domain-separated
SHA-256 calculation over a 64-bit seed and sequential record index. The first
16 digest bytes are emitted as eight big-endian 16-bit words, one canonical
lowercase record per line. This avoids relying on a language/runtime random
number generator and gives every run a corpus SHA-256.

The key-corpus contract rejects a non-demo purpose, unsupported generator,
missing final newline, blank records, malformed words and count mismatches.
It also caps a standalone demo request at 100,000 keys, so key generation and
canonical corpus hashing cannot allocate an unbounded request before the run
budget is checked.
Its purpose is permanently `generated-for-demo`; its hash records the exact
sample that was queried, but does not make it comparable to the missing author
sample.

The adapter separately distinguishes its 60-second compile guard from the
request total budget. A compile-guard timeout is a stage failure; only a
timeout caused by the shorter remaining total budget may mark all keys
`not_started_total_budget`.

## Acceptance evidence

Implementation:

- `src/automated_differential_analysis/formats/gift64_stage2_key_corpus.py`
- `src/automated_differential_analysis/formats/gift64_stage2_demo_request.py`
- `src/automated_differential_analysis/adapters/gift64_stage2_legacy.py`
- `scripts/run_gift64_stage2_demo.py`

Tests cover deterministic generation/encoding, malformed-corpus rejection,
strict request validation including finite total budgets, hash-pinned source
instrumentation, explicit trail binding, marker parsing and the distinction
between unstarted budget-skipped keys and solver statuses. A real one-key
integration test compiles the temporary source with CryptoMiniSat 5.14.7 and
requires one definitive native `SAT` or `UNSAT` status with exit code zero. A
local eight-key smoke run completed under the configured limits; the generated
outcome is intentionally not committed as a research result.

## Reporting language and boundaries

The supported wording is:

> A4 provides a reproducible, resource-bounded Stage 2 fixed-key validation
> demo for a deterministic generated corpus and an explicitly selected supplied
> trail record. It records native solver statuses with source, input and corpus
> provenance.

Do not state that A4:

- reproduces the original million-key `KeyCandidate.out` experiment or its
  numerical outcome;
- validates all 32 trails, the producer's semantic `GroupIndex` cases, or the
  complete LC/LNC corpus simultaneously;
- proves an `UNSAT` answer independently or supplies a proof certificate;
- establishes a complete right-key space, probability, key recovery or
  paper-level differential result.

## Integration boundary

A4 is included in the unified controlled orchestration. Its generated demo
corpus is not asserted to be the source of A5's supplied
`KeyCandidate1000.out`; that lineage remains unavailable. Any extension to
more physical trail positions must retain the `generated-for-demo` label and
declare its own total budget.
