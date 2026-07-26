# SAT Baseline B2: Versioned Solver Contracts

> Completed: 2026-07-26
>
> Scope: configuration and data-contract implementation only. No solver,
> compilation or long experiment was run.

## Outcome

B2 provides a machine-independent, versioned representation of the selected
four-round GIFT-64 SAT request and of future solver results.

The implementation lives in:

- `src/shared/sat/contracts.py`;
- `experiments/gift64/sat_baseline_b2.solver_request.json`;
- `tests/test_sat_contracts.py`.

Both the automated differential-analysis pipeline and optional ML-guided search
can consume these contracts. Neither module may reinterpret solver status or
promote an unverified result to an exact label.

## Request semantics

`SolverRequest` records:

- schema and encoding versions;
- source revision, member hash and archive hash;
- cipher, analysis kind, round interval and layout identifiers;
- objective kind, comparison and component semantics;
- assumptions and fixed input/output/key differences;
- CNF and variable-map artifact references when generated;
- solver name/version/options/threads, seed and resource limits;
- expected static variable, clause and solver-call counts.

The GIFT configuration preserves the upstream source's two independent bounds:

| Component | Unit | Bound | Comparison |
|---|---:|---:|---|
| Integral weight | `1` | `11` | `<=` |
| Decimal weight count | `0.415` | `1` | `<=` |

The two fields are not collapsed into a rounded floating-point total.

The B2 request is representable but not execution-ready. Its `instance` and
`variable_map` are null because those artifacts do not yet exist. B4 later
recorded the selected CryptoMiniSat version as `5.14.7`, and B5 added a `30 s`
solver-process limit. The missing CNF-style artifacts still keep the generic
request property from reporting execution-ready; the B5 source adapter has its
own hash-pinned readiness checks.

## Result semantics

`SolverResult` distinguishes:

- `SAT`;
- `UNSAT`;
- `UNKNOWN`;
- `TIMEOUT`;
- `ERROR`.

It records definitive status, model/proof references, objective components,
bound satisfaction, timing, memory, solver statistics, exit/parse diagnostics,
independent verification and exact-label eligibility.

Important enforced invariants:

- only `SAT` and `UNSAT` may be definitive;
- `SAT` requires a content-addressed model reference;
- only `UNSAT` may carry a proof reference;
- non-`SAT` results cannot claim a satisfied objective;
- artifact paths must be relative and cannot escape the artifact root;
- an exact ML label requires both a definitive result and passed independent
  verification;
- unknown fields are rejected rather than silently changing semantics.

## Validation

Short standard-library tests cover:

- loading the checked-in GIFT request;
- B1 counts of 2740 variables, 8091 clauses and one solve;
- exact preservation of both weight components;
- deterministic canonical JSON round trips;
- honest non-execution-ready state;
- schema and path rejection cases;
- result-status/model invariants;
- exact-label verification gating.

Run:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Subsequent boundary

B3 subsequently added only the trail representation needed for an independent
four-round GIFT verifier. B4 then installed CryptoMiniSat and completed a short
smoke solve; B5 added controlled status/decode/validation. See
[sat_baseline_b3.md](sat_baseline_b3.md) and
[sat_baseline_b4.md](sat_baseline_b4.md) and
[sat_baseline_b5.md](sat_baseline_b5.md).
