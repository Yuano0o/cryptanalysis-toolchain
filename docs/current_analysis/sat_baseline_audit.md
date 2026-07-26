# SAT Baseline Credibility Audit

> Audit status: `passed-with-scoped-follow-ups`
>
> Last reviewed: 2026-07-26
>
> Baseline under review: B1-B7 of the four-round GIFT-64 differential
> characteristic search.

## Decision

The baseline is credible for continued engineering use within its recorded
boundary.

It supports the following claim:

> The hash-pinned four-round GIFT-64 `Differential.cpp`, compiled against
> CryptoMiniSat 5.14.7, produces a `SAT` trail satisfying the source's separate
> bounds `integral_weight <= 11` and `decimal_weight_count <= 1`. The decoded
> trail passes independent DDT, permutation, round-continuity, nonzero-input and
> component-weight verification.

This is a research-owned reproduction and validation boundary around a small
public upstream program. It is not a guarantee that every implementation
detail, runtime or result matches the original authors' environment, and it is
not a reproduction of the paper-scale trail enumerations or attacks.

## What can be reused

The following components are suitable foundations for later work:

- the pinned upstream source identity and four-round configuration;
- versioned `SolverRequest`, `SolverResult` and `TrailRecord` contracts;
- strict native-status and stdout decoding;
- the independently generated GIFT DDT and trail verifier;
- the normalized B6 semantic regression;
- the B7 runner as a bounded local comparison harness.

Future pipeline or ML work may reuse verified SAT trails as exact positive
examples. It must not treat the current single SAT result as a representative
dataset, an optimality certificate or evidence of solver scaling.

## Evidence reviewed

| Evidence | Review result |
|---|---|
| Archive SHA-256 | matched `0c08cc325e1e857e5e5a0015e1d5e30cd550aaf19ef8a6b10e9d19596008f52d` |
| `Differential.cpp` SHA-256 | matched `92b12fd9c65f5870c8f43b0b2e824c4afe789436290cc22e49d238362440c25c` |
| Standard-library test suite | 39/39 passed |
| B6 live CryptoMiniSat regression | passed with no failure or advisory |
| B7 live comparison | all five 1-thread and five 2-thread results were verified `SAT` with components `11` and `1` |
| B7 repeat medians on 2026-07-26 | about 145.5 ms for one thread and 132.0 ms for two threads; about 1.10x, descriptive only |
| Repository state after review | clean; no generated model, binary or log tracked |

Commands used for the short review:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=src python3 scripts/check_gift64_b6.py
PYTHONPATH=src python3 scripts/run_gift64_b7.py --repetitions 5
```

## Checkpoint assessment

| Part | Confidence | Audited conclusion |
|---|---|---|
| B1 | medium-high | Hashes and source structure support the recorded counts and semantics; the full restriction-table audit is not yet an automated checked-in test |
| B2 | high for current SAT use | Contracts strictly preserve split bounds, status and verification gating; future exact `UNSAT` labels need a stronger proof rule |
| B3 | medium-high | The verifier is independent of the upstream 55-row SAT table; an external GIFT reference vector would strengthen independence from manually entered constants |
| B4 | high for its narrow claim | Establishes only compilation and entry into the legacy SAT-output branch; B5/B6 supersede it as controlled evidence |
| B5 | high | Hash-pinned temporary instrumentation, strict decoding and independent semantic verification support the current SAT witness |
| B6 | high within the pinned local environment | Re-executes the real solver and checks stable semantic invariants while correctly treating model hash as provenance |
| B7 | medium | The result is repeatable as a small local observation, but seed control, sample size and instance diversity are insufficient for a performance claim |

## Claim boundary

| Claim | Status |
|---|---|
| A valid four-round trail exists under the two recorded component bounds | supported |
| The controlled adapter can reproduce and verify that semantic result locally | supported |
| The baseline can be reused as a regression and exact-positive-label boundary | supported |
| The result is bit-for-bit identical on every machine | not supported |
| The result proves the minimum or optimal differential weight | not supported |
| B7 demonstrates general two-thread or server speedup | not supported |
| The full *Improved Attacks on GIFT-64* results are reproduced | not supported |
| The GIFT differential-level paper pipeline is reproduced | not supported |

## Follow-up register

These are maintenance improvements, not blockers for starting bounded A1/A2
work.

| ID | Priority | Status | Follow-up | Completion evidence |
|---|---|---|---|---|
| SAT-AUD-01 | medium | open | Turn the B1 55-row restriction/DDT/weight audit into a checked-in deterministic test | Test parses or represents all restrictions and reports zero semantic mismatches |
| SAT-AUD-02 | medium | open | Add an external published GIFT-64 permutation/state-order known-answer vector | Test cites the source and passes independently of the SAT model fixture |
| SAT-AUD-03 | medium-before-ML-dataset | open | Require checked proof evidence before an `UNSAT` result can become an exact ML label | Contract and negative tests reject proofless exact `UNSAT` |
| SAT-AUD-04 | low | open | Make source revision provenance locally verifiable or label it archive metadata only | Revision source is documented and reproducibly checked |
| SAT-AUD-05 | low-before-performance-work | open | Add explicit seed control, host manifest and a multi-instance suite | Repeated isolated comparison records seed, machine and instance hashes |

## How to update this audit

When evidence changes:

1. update `Last reviewed`;
2. append or replace the relevant evidence row with the exact command and
   result;
3. change a follow-up status only when its completion evidence exists;
4. keep historical performance observations descriptive unless the
   performance protocol in `SAT-AUD-05` is complete;
5. update the short root README summary and
   [project_status.md](project_status.md) only when the overall decision,
   blocker or next action changes.
