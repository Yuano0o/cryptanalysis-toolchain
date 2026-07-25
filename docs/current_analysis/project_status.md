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
| Stage-contract schema design | in-progress | `SolverRequest`/`SolverResult` implemented; trail and later-stage contracts remain drafts |
| SAT baseline | in-progress | B0-B2 complete; independent verifier is next and solver execution remains blocked |
| Workstream A pipeline implementation | not-started | Source map exists; parser/adapter code not created |
| Workstream B exact benchmark | not-started | BAKSHEESH source/paper inspected; search code missing |
| ML-guided SAT implementation | blocked | Exact label pipeline and NeuroGIFT source/data are unavailable |
| CRAFT/WARP portability | deferred | Main paper/provenance missing; interfaces not stable |

## Current milestone

**Milestone:** establish a minimal exact GIFT-64 SAT baseline from
`../upstream/Improved_Attacks_GIFT64/Differential.cpp`, archived in
`../upstream/_archives/Improved_Attacks_GIFT64-main.zip`.

Current checkpoint:

1. Source and paper relationship inspected - complete.
2. Baseline target and acceptance criteria - complete.
3. Static source-to-contract mapping - complete.
4. Research-side configuration/contracts - complete.
5. Compile/solve - blocked by missing CryptoMiniSat 5.
6. Independent trail validation - next.
7. Regression fixture - not started.

## Workstream A: Automated Differential-Level Analysis Pipeline

| Component | Status | Current result | Next step | Blocker |
|---|---|---|---|---|
| Source/paper map | complete | Six GIFT stages mapped to the three-stage/differential-level methods | Maintain as evidence changes | None |
| Common artifact contracts | in-progress | Strict versioned solver request/result contracts implemented; later-stage fields remain specified drafts | Add `TrailRecord` only with the B3 verifier boundary | Later representation choices need validation |
| SAT trail search boundary | in-progress | B1 static map and B2 machine-independent request/result contracts complete | Implement independent four-round trail verifier | CryptoMiniSat blocks execution only |
| `TrailInformation.out` parser | ready | Inputs available | Recover exact token boundaries and ordering | None |
| LC extraction adapter | ready | Source and fixture available; no external solver | Define `ConstraintSet` equivalence oracle | None |
| LNC extraction adapter | ready | Source and fixture available; no external solver | Define `ConstraintSet` provenance | None |
| Stage 2 fixed-key validation | blocked | Code inspected | Obtain/generate `KeyCandidate.out` reproducibly | Missing generator/file provenance |
| Stage 3 probability | ready-for-static-work | Code and `KeyCandidate1000.out` present | Specify sampling/probability contract | Exact reproduction needs seed/statistical decisions |
| Trail coexistence | ready-for-static-work | Code and matrix present | Recover matrix semantics | Matrix generator absent |
| 18/19-round construction | blocked | Paper results known | Obtain/formalise extension construction | No generator/entry found |
| Attack-level regression | blocked | Improved paper and two small source files present | Request missing enumeration/attack code | Public archive incomplete |

## Workstream B: ML-Guided SAT Search

| Component | Status | Current result | Next step | Blocker |
|---|---|---|---|---|
| Prior-work review | complete | NeuroSAT/NeuroGIFT tasks and limitations recorded | Keep as design constraints | None |
| Exact label contract | complete | `SolverResult` rejects non-definitive or independently unverified exact labels | Exercise with real results after B5 | Solver environment blocks data, not the contract |
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

1. Define an independent verifier for a decoded four-round trail.
2. Request approval before installing or connecting CryptoMiniSat 5.
3. In parallel, begin `TrailInformation.out` schema recovery because it has no
   dependency blocker.

## Change log

- 2026-07-25: created project-level status tracking before baseline
  implementation.
- 2026-07-25: completed baseline B1 static mapping, including source hashes,
  2740-variable/8091-clause counts and a full DDT/weight semantic check.
- 2026-07-26: completed baseline B2 with a versioned GIFT-64 request,
  strict `SolverRequest`/`SolverResult` contracts and deterministic contract
  tests; no solver was installed or invoked.
