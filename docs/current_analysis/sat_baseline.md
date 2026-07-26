# SAT Baseline: GIFT-64 Four-Round Differential Search

> Last updated: 2026-07-26
>
> This is an exact baseline and regression boundary, not a claim of reproducing
> the full *Improved Attacks on GIFT-64* paper.

## Purpose

The first baseline validates the shared exact-search infrastructure needed by
both research workstreams:

- GIFT-64 state/bit ordering;
- differential S-box encoding;
- bit permutation;
- split probability-weight cardinality bounds;
- solver request/result semantics;
- SAT-model-to-trail decoding;
- independent exact trail validation;
- deterministic provenance and regression capture.

## Selected source

| Item | Value |
|---|---|
| Archive | `../upstream/_archives/Improved_Attacks_GIFT64-main.zip` |
| Extracted read-only source | `../upstream/Improved_Attacks_GIFT64/Differential.cpp` |
| Archive commit metadata | `0dff1caf65675de6ab0aa7edf0f51883a576eacc` |
| Member | `Improved_Attacks_GIFT64-main/Differential.cpp` |
| Cipher | GIFT-64 |
| Analysis | single-key differential characteristic search |
| Rounds | 4 |
| Integral weight bound | `<= 11` |
| Decimal-component count bound | `<= 1` |
| Solver API | CryptoMiniSat 5 C++ |
| Threads in source | 1 |
| Runtime inputs | none; all parameters are compiled into source |
| Source output | one SAT model decoded as per-round `xin`/`xout` on stdout |

The split bound mirrors the paper's treatment of weights expressible as an
integer component plus `0.415` times a decimal-component count. The baseline
must record both components separately and must not silently collapse them
into a rounded float.

## Non-goals

The first baseline will not:

- reproduce 5120 optimal 12-round linear trails;
- reproduce 92768 13-round differential trails or 2392 differentials;
- reproduce L16/D03 selection;
- implement the 19/20-round attacks;
- benchmark server speedup;
- train an ML model;
- modify or vendor the upstream archive.

## Required materials

### Present

- paper and source archive;
- C++ compiler;
- encoding constants and fixed search configuration;
- research-side schema draft.

### Missing for controlled execution

- an owned adapter that exposes every solver status explicitly;
- a versioned model/result artifact boundary;
- an independently validated expected trail.

No additional paper or source file is required to begin static implementation.
The solver is an environment dependency and must not be copied into the
workspace.

## Planned research-side artifacts

These are authored in `learning-guided-cryptanalysis/`, not upstream:

1. a versioned baseline configuration;
2. a static source/variable map;
3. `SolverRequest` and `SolverResult` contracts;
4. a decoded `TrailRecord`;
5. an independent GIFT-64 differential-transition verifier;
6. a small regression expectation after the first validated solve.

Generated CNF, build output, solver logs and complete raw models are not tracked
in Git.

## Acceptance criteria

The baseline passes only when all criteria hold:

1. The source archive and member hash are recorded.
2. The exact solver/library version and compiler are recorded.
3. Compilation occurs without modifying upstream/archive contents.
4. The adapter distinguishes `SAT`, `UNSAT`, `UNKNOWN`, `TIMEOUT` and `ERROR`.
5. A SAT model is decoded into four per-round input/output differences.
6. Every S-box transition is valid under the GIFT-64 DDT.
7. Every round permutation is independently verified.
8. Integral and decimal weight bounds are independently recomputed.
9. The decoded trail is nonzero at the input.
10. A repeated run under the same controlled configuration returns a valid
    result with equivalent objective semantics.
11. The expected regression summary contains no machine-specific absolute
    path.

SAT alone is insufficient: acceptance requires independent verification of the
decoded trail.

## Baseline comparison levels

| Level | Meaning |
|---|---|
| Legacy | Preserve the upstream encoding and solve semantics as closely as possible |
| Controlled | Parameterised paths, explicit solver status, hashes, limits and independent validation |
| Enhanced | Optional incremental solving, alternative bounds, solver portfolio, parallel scheduling or ML guidance |

Enhanced variants must remain behind explicit configuration and must compare
against the controlled baseline on the same instances.

## Metrics

- result status and objective/bound semantics;
- variable and clause counts when available;
- number of solver calls;
- wall time and CPU time;
- peak memory;
- solver/thread/version;
- time to first independently validated trail;
- validation pass/failure reason.

Historical M2 Ultra, EPYC and Intel runtimes are context only. They are not
comparable performance baselines without rerunning the same instance.

## Implementation checkpoints

| Checkpoint | Status | Exit condition |
|---|---|---|
| B0 Source/paper inspection | complete | Encoding purpose and coverage limits documented |
| B1 Static variable/constraint map | complete | Variables, clauses, DDT/weight semantics, permutation and output mapped |
| B2 Versioned config/contracts | complete | Request/result can be represented and validated without solver execution |
| B3 Independent verifier | complete | Hand-constructed trail and targeted invalid cases are checked independently |
| B4 Compile and smoke solve | complete | CryptoMiniSat 5.14.7 compiled and ran the unchanged legacy source |
| B5 Decode and validate | complete | Controlled SAT model independently passes all checks |
| B6 Regression capture | next | Stable validated summary recorded |
| B7 Controlled comparison | deferred | At least one alternative configuration compared fairly |

## B2 result

Implemented:

- `experiments/gift64/sat_baseline_b2.solver_request.json`;
- strict standard-library contracts in `src/shared/sat/contracts.py`;
- deterministic JSON serialization and strict unknown-field rejection;
- static expectations of 2740 variables, 8091 clauses and one solver call;
- separate integral-weight and `0.415` decimal-component bounds;
- explicit `SAT`, `UNSAT`, `UNKNOWN`, `TIMEOUT` and `ERROR` result semantics;
- independent-verification gating for exact ML labels.

The generic request property remains intentionally not execution-ready because
`instance` and `variable_map` are null. B4 records CryptoMiniSat `5.14.7`; B5
adds a `30 s` limit and enforces separate hash-pinned source-adapter readiness.

## B3 result

Implemented:

- minimal versioned `TrailRecord`/`TrailRound` representation;
- GIFT DDT generation from the S-box rather than the upstream SAT restriction
  table;
- independent permutation-direction and round-continuity checks;
- exact recomputation of integral weight and `0.415` component count;
- rejection of invalid transitions, zero input, malformed states and false
  claimed weights;
- conversion to the B2 independent-verification result.

The fixed positive fixture is a structurally valid four-round trail with
recomputed components `33` and `4`. It intentionally does not satisfy the B2
bounds `11` and `1`; no bound-satisfying solver result is claimed.

## B4 result

CryptoMiniSat `5.14.7` and GMP `6.3.0` were installed through Homebrew. The
unchanged upstream source compiled out of tree with Apple clang `14.0.3` and
C++17, then completed one short legacy smoke solve. It printed four round-state
blocks and returned exit code `0`; generated output and binaries were not
tracked.

The unmodified legacy process does not satisfy the controlled result contract
because it prints no explicit solver status and cannot distinguish `UNSAT`
from `UNKNOWN` at its process boundary. B5 resolves that observability gap in a
temporary, hash-pinned build copy.

## B5 result

Implemented:

- a pinned-source adapter that adds only an explicit `lbool` marker to a
  temporary build copy;
- strict `SAT`, `UNSAT`, `UNKNOWN`, `TIMEOUT` and `ERROR` mapping;
- exact four-round stdout decoding into canonical `TrailRecord`;
- content-addressed model references outside Git;
- B3 independent verification and `SolverResult` construction;
- a request-controlled `30 s` solver time limit.

Two controlled invocations produced the same canonical model hash and
objective semantics. The result was definitive `SAT`, recomputed to integral
weight `11` and decimal-component count `1`, passed all independent checks and
was exact-label eligible. No raw model, solver log or binary is tracked.

## Immediate next implementation

B6 should capture the normalized regression expectation without committing
the generated model. After B6, the first useful Workstream A step is the
`TrailInformation.out` parser/schema boundary.

B3-B5 details are in [sat_baseline_b3.md](sat_baseline_b3.md),
[sat_baseline_b4.md](sat_baseline_b4.md) and
[sat_baseline_b5.md](sat_baseline_b5.md).
