# Project Status

> Last updated: 2026-07-26
>
> Status vocabulary: `complete`, `complete-draft`, `in-progress`, `ready`,
> `ready-for-static-work`, `blocked`, `not-started`, `deferred`.

## Overall status

| Item | Status | Evidence/meaning |
|---|---|---|
| Source and paper inventory | complete | Four upstream repositories, one additional source archive and eight papers inspected |
| Research structure | complete | Two workstreams distinguished from shared enabling milestones |
| Stage-contract schema design | in-progress | Solver, trail, TrailInformation, GF(2) `ConstraintSet`, space comparison, Stage 2 key corpus and bounded Stage 3 probability contracts are implemented; right-key contracts remain |
| SAT baseline | complete | B0-B7 pass; the 2026-07-26 credibility audit passed with scoped maintenance follow-ups |
| Workstream A pipeline implementation | in-progress | Controlled SAT, TrailInformation, LC/LNC normalization, Stage 2 fixed-key and Stage 3 probability demos are complete; coexistence and later stages remain |
| Workstream B exact benchmark | not-started | BAKSHEESH source/paper inspected; search code missing |
| ML-guided SAT implementation | blocked | Exact label pipeline and NeuroGIFT source/data are unavailable |
| CRAFT/WARP portability | deferred | Main paper/provenance missing; interfaces not stable |

## Completed milestone

**Milestone:** established a minimal exact GIFT-64 SAT baseline from
`../upstream/Improved_Attacks_GIFT64/Differential.cpp`, archived in
`../upstream/_archives/Improved_Attacks_GIFT64-main.zip`.

Completed checkpoints:

1. Source and paper relationship inspected - complete.
2. Baseline target and acceptance criteria - complete.
3. Static source-to-contract mapping - complete.
4. Research-side configuration/contracts - complete.
5. Compile/legacy smoke solve - complete with CryptoMiniSat 5.14.7.
6. Independent verifier implementation - complete.
7. Controlled decoding and validation of a real solver model - complete.
8. Compact regression expectation - complete.
9. Controlled one-thread/two-thread comparison - complete.

## Workstream A: Automated Differential-Level Analysis Pipeline

| Component | Status | Current result | Next step | Blocker |
|---|---|---|---|---|
| Source/paper map | complete | Six GIFT stages mapped to the three-stage/differential-level methods | Maintain as evidence changes | None |
| Common artifact contracts | in-progress | Solver, `TrailRecord`, TrailInformation, constraint spaces, Stage 2 corpus and Stage 3 subcube probability request/observation summaries implemented | Define right-key/aggregation contracts | Right-key sampling semantics remain |
| SAT trail search boundary | complete | B1-B7 pass; live audit reruns preserved verified `SAT` with components `11`/`1` | Maintain the audit register; reuse only within its supported-claim boundary | No A1/A2 blocker |
| `TrailInformation.out` parser | complete | A1 recovers 32 records, `[5,13)` rounds, round-4 key-state anchor and MSB-first order | Reuse as the normalized Stage 2 trail input | Exact trail selection/concatenation provenance is missing |
| LC extraction adapter | complete | A2 observes pinned matrices, folds fixed constants and canonicalizes 32 rank-6 GF(2) spaces | Add independent derivation later | Current exactness is relative to pinned legacy source |
| LNC extraction adapter | complete | A3 normalizes 32 combined rank-8 spaces; every LC base is implied with incremental rank 2 | Reuse the comparison boundary in Stage 2 reporting | Current exactness is relative to pinned legacy source |
| Stage 2 fixed-key validation | complete-draft | A4 has deterministic key generation, source/trail pinning, explicit physical trail selection, per-key timeout and native status summary | Select additional physical positions or proceed to Stage 3 | Original million-key result remains blocked by missing provenance and no UNSAT proof is emitted |
| Stage 3 probability | complete-draft | A5 has deterministic subcube sampling, source/fixture pinning, explicit key/trail positions, per-sample and total budgets, 64-bit complete-count checks and completion-gated descriptive estimates | Extend selected key/trail coverage under the declared total budget | Fixture generator/provenance is missing; no global exact/probability claim |
| Trail coexistence | ready-for-static-work | Code and matrix present | Recover matrix semantics | Matrix generator absent |
| 18/19-round construction | blocked | Paper results known | Obtain/formalise extension construction | No generator/entry found |
| Attack-level regression | blocked | Improved paper and two small source files present | Request missing enumeration/attack code | Public archive incomplete |

## Workstream B: ML-Guided SAT Search

| Component | Status | Current result | Next step | Blocker |
|---|---|---|---|---|
| Prior-work review | complete | NeuroSAT/NeuroGIFT tasks and limitations recorded | Keep as design constraints | None |
| Exact label contract | complete | B5 real result is definitive, independently verified and exact-label eligible | Preserve as benchmark evidence; do not treat one result as a dataset | None |
| BAKSHEESH cipher boundary | ready | Encryption source and paper oracles identified | Document/test ordering and vector | None for static work |
| BAKSHEESH exact search | blocked | Original search code absent | Request or independently rebuild later | Missing original encoding/search |
| Runtime prediction baseline | not-started | Recommended first ML task | Define after solver telemetry exists | No controlled runtime dataset |
| Candidate ranking | not-started | Recommended second ML task | Define after structured trails exist | No exact-labelled candidate set |
| NeuroGIFT reproduction | blocked | Paper only; source/data/checkpoints absent | Confirm availability | Missing external material |
| GIFT ML integration | deferred | Integration point identified | Start after exact GIFT pipeline subset | Pipeline not implemented |

## Portability

| Component | Status | Current result | Next step | Blocker |
|---|---|---|---|---|
| CRAFT/WARP source inventory | complete | Step0-Step7 and candidate files inspected | Obtain main paper | Main paper missing |
| Adapter design | deferred | Required key/tweak/candidate abstractions identified | Revisit after GIFT interfaces stabilise | Premature |
| Cross-cipher ML evaluation | deferred | OOD role identified | Revisit after ML baseline | No model/dataset |

## Immediate next actions

1. Decide whether to extend A5 across selected fixture-key/trail positions
   under a fixed total time budget, and define aggregation assumptions.
2. Recover the Stage 6 coexistence-matrix semantics without claiming to
   regenerate its missing producer artifact.

## SAT baseline maintenance register

The authoritative details and completion evidence are in
[sat_baseline_audit.md](sat_baseline_audit.md).

| ID | Status | Timing |
|---|---|---|
| SAT-AUD-01: automate the B1 restriction-table audit | open | non-blocking maintenance |
| SAT-AUD-02: add an external GIFT reference vector | open | non-blocking maintenance |
| SAT-AUD-03: require proof evidence for exact `UNSAT` labels | open | before ML dataset generation |
| SAT-AUD-04: clarify source revision provenance | open | low priority |
| SAT-AUD-05: controlled performance protocol | open | before performance/server claims |

## Change log

- 2026-07-25: created project-level status tracking before baseline
  implementation.
- 2026-07-25: completed baseline B1 static mapping, including source hashes,
  2740-variable/8091-clause counts and a full DDT/weight semantic check.
- 2026-07-26: completed baseline B2 with a versioned GIFT-64 request,
  strict `SolverRequest`/`SolverResult` contracts and deterministic contract
  tests; no solver was installed or invoked.
- 2026-07-26: completed baseline B3 with a minimal `TrailRecord`, independently
  generated GIFT DDT, permutation/continuity checks and split-weight
  recomputation; the test fixture is structural, not a baseline solver result.
- 2026-07-26: installed CryptoMiniSat 5.14.7 and completed B4 by compiling the
  unchanged upstream source out of tree with C++17 and running one short legacy
  smoke solve; no generated artifacts were tracked.
- 2026-07-26: completed B5 with hash-pinned temporary status instrumentation,
  strict four-round decoding, B3 independent verification and a controlled
  exact-label-eligible `SAT` result with objective components `11` and `1`.
- 2026-07-26: completed B6 with a normalized semantic expectation and
  temporary-artifact end-to-end checker; status, objective and verification are
  hard requirements while runtime and the uncontrolled-seed model hash are not.
- 2026-07-26: completed B7 locally with alternating five-repeat 1-thread versus
  2-thread runs; both configurations remained independently verified SAT, while
  the observed local median comparison is descriptive only.
- 2026-07-26: audited B1-B7 by static review, 39 tests, a live B6 regression
  and a repeated B7 comparison; accepted the baseline for scoped reuse and
  recorded five non-blocking or future-gated maintenance items.
- 2026-07-26: completed pipeline A1 with a strict
  `gift64-trail-information/v1` parser, recovered round/word/group semantics and
  integration checks for all four immutable upstream copies; trail
  selection/concatenation provenance remains unavailable.
- 2026-07-26: completed pipeline A2 locally with `constraint-set/v1`,
  deterministic GF(2) RREF/semantic hashes and a hash-pinned LC observation;
  all 32 trails yield rank 6 and the first six-equation fixture matches the
  supplement.
- 2026-07-26: completed pipeline A3 locally by recovering the global
  linearised-relation matrix, normalizing 32 combined rank-8 spaces and proving
  that each implies its rank-6 A2 LC base with incremental rank 2.
- 2026-07-26: completed pipeline A4 locally with a deterministic
  `generated-for-demo` key-corpus contract, a hash-pinned temporary Stage 2
  adapter, explicit physical trail selection, per-key timeout and structured
  native SAT-status summary; the absent author million-key corpus continues to
  block paper-level reproduction.
- 2026-07-26: completed pipeline A5 locally with a hash-pinned supplied
  1,000-key fixture, deterministic replacement of the legacy unseeded subcube
  sampler, per-sample timeout, completion-gated solution counting and a
  descriptive probability-estimate contract.
