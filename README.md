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

## Current Update — SAT Baseline B1-B2

The first two static baseline checkpoints are complete. B1 maps the four-round
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
and remains explicitly not execution-ready while the CNF, variable map and
exact CryptoMiniSat version are unavailable. Contract validation also prevents
timeouts or unverified results from becoming exact ML labels.

This is an infrastructure and regression baseline, not a reproduction of the
full Improved Attacks paper. The next checkpoint is B3: an independent GIFT-64
trail verifier. See
[`docs/current_analysis/sat_baseline.md`](docs/current_analysis/sat_baseline.md)
and
[`docs/current_analysis/sat_baseline_b2.md`](docs/current_analysis/sat_baseline_b2.md).

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
