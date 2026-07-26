# Learning-Guided Cryptanalysis

An exploratory research workspace for automated differential analysis and
learning-guided exact search on lightweight block ciphers.

## Working Proposal

SAT-based tools can search for differential or linear characteristics
automatically, but moving from individual trails to a complete
differential-level result still involves several separate programs, data files,
and analysis steps.

This repository explores two connected directions: organising those steps into
a reproducible pipeline, and testing whether machine learning can help
prioritise the exact search.

### 1. Automated Differential-Level Analysis Pipeline

The first direction is to connect the main analysis steps into a modular
workflow:

```text
SAT trail search
  → trail enumeration and grouping
  → LC/LNC constraint analysis
  → fixed-key validation
  → trail coexistence and right-key-space analysis
  → probability evaluation
  → differential construction
  → result reporting
```

GIFT-64 is the first target. The immediate goal is to reproduce a manageable
part of the published analysis with clear inputs and outputs, configurable
parameters, independent checks, and regression tests.

### 2. ML-Guided SAT Search

The second direction explores whether machine learning can help the exact
solver focus on more promising candidates. Possible tasks include:

- partial-trail scoring;
- candidate ranking;
- SAT-instance difficulty prediction;
- branch and search-region prioritisation.

Machine learning is used only for guidance. Every accepted trail, bound, and
final result must still be verified by an exact SAT solver.

### How the two directions fit together

The automated pipeline is the main framework. ML-guided SAT search is an
optional acceleration module within it:

```text
candidate space
  → optional ML ranking or prioritisation
  → exact SAT search and verification
  → differential-level analysis
  → verified result
```

## Current Update — SAT Baseline B1-B7

The first six baseline checkpoints are complete. B1 maps the four-round
GIFT-64 differential program from the Improved Attacks reference source without
yet compiling or invoking a solver.

- fixed instance: 4 rounds, integral weight bound `<= 11`, decimal-component
  bound `<= 1`;
- recovered size: 2,740 Boolean variables and 8,091 clauses;
- independently checked the encoded S-box transition/weight table against the
  GIFT DDT, with no semantic mismatches;
- documented the permutation direction, model decoding and the need for an
  explicit `SAT` / `UNSAT` / `UNKNOWN` result contract.

B2 adds strict, versioned `SolverRequest` and `SolverResult` contracts plus a
machine-independent GIFT-64 request configuration. The request preserves the
integer and `0.415` weight components separately, records the B1 static counts,
and remains explicitly not execution-ready while the CNF and variable map are
unavailable. Contract validation also prevents timeouts or unverified results
from becoming exact ML labels.

B3 adds an independent four-round GIFT-64 trail verifier. It rebuilds the DDT
from the published S-box, checks the permutation direction and round
continuity, rejects malformed/zero-input trails, and recomputes both weight
components. Its fixed structural fixture is deliberately outside the B2 bounds;
it tests the verifier and is not presented as a baseline SAT solution.

B4 records CryptoMiniSat 5.14.7, compiles the unchanged upstream source out of
tree with C++17, and completes one short four-round legacy smoke solve. Build
artifacts and raw solver output are not tracked.

B5 adds a hash-pinned temporary status adapter without modifying upstream. It
distinguishes `SAT`, `UNSAT`, `UNKNOWN`, `TIMEOUT` and `ERROR`, decodes the
four-round stdout into `TrailRecord`, invokes the B3 verifier and emits
`SolverResult`. The controlled run returned verified `SAT` with objective
components `11` and `1`; the decoded artifact remained outside Git.

B6 adds a compact semantic regression expectation. It requires the normalized
status, objective components, verification and exact-label result while
ignoring runtime and local paths. The observed model hash is provenance-only
until the legacy seed is explicitly controlled. The real end-to-end B6 check
passes without retaining generated artifacts.

B7 compares the same pinned four-round instance with one and two
CryptoMiniSat threads, in alternating order across five repetitions. Both
configurations remain independently verified `SAT` with components `11` and
`1`; the observed local median is descriptive only, because the legacy source
does not set an explicit solver seed. See
[`docs/current_analysis/sat_baseline_b7.md`](docs/current_analysis/sat_baseline_b7.md).

This is an infrastructure and regression baseline, not a reproduction of the
full Improved Attacks paper. See
[`docs/current_analysis/sat_baseline.md`](docs/current_analysis/sat_baseline.md)
and
[`docs/current_analysis/sat_baseline_b6.md`](docs/current_analysis/sat_baseline_b6.md).

## Planned Evaluation

| Cipher | Role |
|---|---|
| GIFT-64 | Primary differential-level analysis case study |
| BAKSHEESH | Initial benchmark for rebuilding exact search and testing ML guidance |
| CRAFT / WARP | Later checks of cross-cipher portability |

## Repository Structure

```text
src/
├── automated_differential_analysis/
├── ml_guided_sat/
└── shared/
adapters/       interfaces to the upstream reference implementations
benchmarks/     benchmark definitions and test vectors
configs/        reproducible configurations
experiments/    experiment definitions for each evaluation cipher
tests/          unit, integration, and regression tests
```

The public reference repositories remain unchanged and are accessed through
adapters rather than copied into this repository.
