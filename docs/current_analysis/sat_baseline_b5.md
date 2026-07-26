# SAT Baseline B5: Controlled Decode and Independent Validation

> Completed: 2026-07-26
>
> Scope: a hash-pinned adapter around the public four-round legacy source,
> explicit solver status, strict stdout decoding, independent verification and
> a versioned result contract. No upstream or generated artifact is tracked.

## Outcome

B5 closes the controlled result boundary for the selected four-round GIFT-64
baseline.

Implementation:

- `src/automated_differential_analysis/adapters/gift64_improved_legacy.py`;
- `scripts/run_gift64_b5.py`;
- `tests/test_gift64_legacy_adapter.py`.

A real controlled invocation produced:

| Field | Result |
|---|---|
| Solver status | `SAT` |
| Definitive | `true` |
| Decoded rounds | `4` |
| Integral weight | `11` |
| Decimal-component count | `1` |
| Componentwise bound | passed |
| Independent verification | passed |
| Exact-label eligible | `true` |
| Solver exit code | `0` |

The canonical decoded model had trail identifier
`gift64-b5-babf7ec018a82ed0` and SHA-256
`8e42de961476884641e53b2e15b1596f920aa84b3bcb4ff22fc8c7d9b47bac87`.
A repeated controlled invocation produced the same trail identifier, model hash
and objective semantics. The model file itself was kept in a temporary
artifact root and removed after inspection.

## Trust boundary

The adapter does not edit or vendor the upstream source. It:

1. requires the original `Differential.cpp` SHA-256 to equal the B1 pinned
   value;
2. creates a temporary source copy;
3. inserts only an `lbool` status marker immediately after the single pinned
   `solver.solve()` call;
4. compiles the temporary copy and removes the build directory automatically;
5. parses the status marker from stderr and the legacy model from stdout.

The temporary instrumentation changes observability, not variables,
constraints, bounds, solver options or model printing. Any source change,
missing/duplicate instrumentation point or missing/duplicate status marker is
an `ERROR`.

## Status semantics

| Observation | `SolverResult.status` | Definitive |
|---|---|---|
| CryptoMiniSat `l_True` | `SAT` | yes |
| CryptoMiniSat `l_False` | `UNSAT` | yes |
| CryptoMiniSat `l_Undef` | `UNKNOWN` | no |
| Controlled solver timeout | `TIMEOUT` | no |
| Compile failure, nonzero exit, malformed marker/model or environment mismatch | `ERROR` | no |

An `UNSAT` result is not marked exact-label eligible without an independently
checked proof. A `SAT` result becomes exact-label eligible only after a
content-addressed decoded model passes B3 verification.

## Decode and verification

The stdout decoder requires exactly four sequential blocks. Every block must
contain:

- one `Round` header with the expected index;
- one 16-nibble `xin`;
- one 16-nibble `xout`.

The decoded record is serialized as canonical `trail-record/v1` JSON in a
caller-provided artifact root outside the Git repository. B3 then independently
checks:

- state layout and round continuity;
- nonzero initial difference;
- all 64 S-box transitions;
- GIFT permutation direction;
- recomputed integral and decimal weight components;
- the B2 componentwise bounds.

The resulting `solver-result/v1` includes a relative artifact path, content
hash, byte size, explicit status, objective components, timings, diagnostics,
verification status and exact-label eligibility.

## Controlled configuration

The request now pins:

- CryptoMiniSat `5.14.7`;
- one solver thread;
- a `30 s` solver-process limit;
- the original source and archive hashes;
- the `2740` variable, `8091` clause and one-call static expectations;
- separate bounds `integral_weight <= 11` and
  `decimal_weight_count <= 1`.

The expected variable/clause counts remain a static source audit because the
legacy API program does not expose runtime counts. Peak memory is also not yet
collected. The request records seed `0`, but the legacy source does not call an
explicit seed-setting API; B5 therefore reports seed application as an
unverified solver default. Compile time and solve time are reported separately,
but the local times are smoke evidence rather than cross-machine benchmarks.

## Validation

The 31-test standard-library suite covers:

- source hash and instrumentation immutability checks;
- native `SAT`/`UNSAT`/`UNKNOWN` marker parsing;
- missing and duplicate marker rejection;
- malformed state, round count and round order rejection;
- a hand-constructed structural stdout fixture;
- operational error mapping and repository artifact-root rejection;
- all B2 contract and B3 verifier tests.

The actual CryptoMiniSat integration was also run twice with equivalent
verified results. Raw stdout, binaries, model files and result logs remain
untracked.

## Subsequent boundary

B6 subsequently added the normalized regression expectation and an end-to-end
temporary-artifact checker. The observed model hash remains provenance rather
than a hard cross-environment oracle. See
[sat_baseline_b6.md](sat_baseline_b6.md).
