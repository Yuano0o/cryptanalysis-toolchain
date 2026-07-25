# SAT Baseline B3: Independent GIFT-64 Trail Verifier

> Completed: 2026-07-26
>
> Scope: decoded-trail representation and independent verification only. No
> SAT solver, upstream executable or long experiment was run.

## Outcome

B3 implements an independent verifier for the selected four-round GIFT-64
baseline boundary.

Implementation:

- `src/shared/trails.py`;
- `src/shared/ciphers/gift64.py`;
- `tests/test_gift64_verifier.py`.

The verifier consumes the B2 `SolverRequest` when configuration/bound checking
is required and emits a `VerificationResult` suitable for the B2
`SolverResult`.

## Independence boundary

The verifier does not import or translate the 55-row SAT restriction table. It:

1. defines the published 4-bit GIFT S-box;
2. generates the complete DDT directly from that S-box;
3. maps each nonzero DDT count to the independently checked split-weight
   semantics;
4. uses the GIFT bit permutation to recover logical S-box outputs from the
   decoded post-permutation state.

The generated DDT reproduces the B1 audit totals:

| DDT value | Number of cells | Weight representation |
|---:|---:|---|
| `0` | 157 | impossible |
| `2` | 78 | integral `3` |
| `4` | 18 | integral `2` |
| `6` | 2 | integral `1`, decimal count `1` |
| `16` | 1 | zero-to-zero, weight `0` |

## Checks

For a four-round `TrailRecord`, the verifier checks:

- cipher and state/bit/nibble layout identifiers;
- four sequentially indexed rounds;
- exactly 16 nibbles in every input and output state;
- nonzero first-round input difference;
- `xout[r] == xin[r+1]` continuity;
- every S-box transition against the generated DDT;
- GIFT permutation direction;
- recomputed integral and decimal weight components;
- claimed objective components, when present;
- fixed input/output differences and B2 componentwise bounds, when a request is
  supplied.

The report contains structured issue codes, checked round/S-box counts,
recomputed objective components and a conversion to the shared solver
verification contract.

## Test fixture boundary

The checked-in positive fixture is constructed from valid DDT transitions and
the GIFT permutation. It is structurally valid and recomputes to:

```text
integral_weight = 33
decimal_weight_count = 4
```

It deliberately does not satisfy the B2 limits `11` and `1`. The test verifies
that supplying the B2 request rejects it on both bounds. This fixture must not
be described as a SAT result or as evidence that the selected baseline
instance is satisfiable.

A real bound-satisfying trail can only be added after B4 obtains a solver result
and B5 passes that model through this verifier.

## Validation

The test suite covers:

- DDT distribution and representative `2/4/6/16` transitions;
- permutation bijection and direction;
- deterministic `TrailRecord` JSON round trip;
- a structurally valid four-round trail;
- B2 bound rejection;
- invalid S-box transition;
- zero input;
- malformed state length;
- claimed-weight mismatch;
- conversion to passed/failed independent-verification status;
- all prior B2 contract tests.

Run:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Subsequent boundary

B4 subsequently established the CryptoMiniSat compile-and-run boundary. B5
must decode and validate a controlled result against this verifier. B4 is
documented in [sat_baseline_b4.md](sat_baseline_b4.md).
