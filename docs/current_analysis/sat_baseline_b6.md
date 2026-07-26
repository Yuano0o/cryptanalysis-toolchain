# SAT Baseline B6: Normalized Regression Expectation

> Completed: 2026-07-26
>
> Scope: a compact semantic expectation and checker. No generated trail,
> Boolean model, solver log, binary, runtime baseline or machine-specific path
> is tracked.

## Outcome

B6 completes the minimal GIFT-64 four-round SAT baseline by converting the B5
validated observation into a stable, reviewable regression boundary.

Implementation:

- `src/shared/sat/regression.py`;
- `experiments/gift64/sat_baseline_b6.regression.json`;
- `scripts/check_gift64_b6.py`;
- `tests/test_sat_regression.py`.

The real B6 check returned:

```json
{
  "advisories": [],
  "failures": [],
  "passed": true
}
```

The check runs B5 inside an automatically removed temporary artifact root. It
prints only the normalized comparison result.

## Required invariants

B6 fails when any of these change:

- request ID, canonical request hash or original source hash;
- solver name, version or thread count;
- adapter or verifier version;
- normalized solver status;
- definitive flag;
- integral and decimal objective components;
- componentwise bound result;
- independent verification status;
- exact-label eligibility.

For the current expectation these values are:

| Field | Required value |
|---|---|
| Status | `SAT` |
| Definitive | `true` |
| Integral weight | `11` |
| Decimal-component count | `1` |
| Bound satisfied | `true` |
| Verification | `passed` |
| Exact-label eligible | `true` |

## Deliberately excluded

The checker ignores:

- wall and CPU time;
- compile time;
- peak memory while it remains unavailable;
- temporary artifact paths and byte layout details;
- diagnostic wording;
- trail identifier.

These fields are environment- or presentation-sensitive and are not semantic
regression oracles.

## Model-hash policy

The B5 canonical model hash is recorded as provenance, but the policy is
`record_only`. A different valid model hash creates an advisory rather than a
failure.

This is intentional: the legacy source does not call an explicit solver
seed-setting API. The hard model hash must not become a cross-machine
determinism claim. Objective components and independent verification remain
hard requirements.

## Data hygiene

The expectation contains only compact metadata and normalized values. It does
not contain:

- per-round `xin`/`xout`;
- a SAT Boolean assignment;
- raw stdout/stderr;
- a solver log;
- executable or object code;
- local absolute paths.

`check_gift64_b6.py` uses `TemporaryDirectory`, so the decoded B5 model is
removed even when the comparison fails.

## Validation

The 38-test suite covers:

- deterministic expectation JSON round trip;
- timing-insensitive semantic matches;
- request- and objective-change failure;
- record-only model-hash advisories and exact-policy failures;
- strict unknown-field rejection;
- all B2-B5 tests.

The real CryptoMiniSat-backed B6 check also passed with no advisory.

Run:

```sh
PYTHONPATH=src python3 scripts/check_gift64_b6.py
```

## Next boundary

The minimal SAT baseline checkpoints B0-B6 are complete. B7 controlled
performance/configuration comparison remains deferred.

The next project phase should now begin the GIFT-64 differential-level
pipeline with the `TrailInformation.out` schema and parser boundary, followed
by LC/LNC extraction contracts.
