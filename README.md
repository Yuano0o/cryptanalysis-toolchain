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

The minimal four-round GIFT-64 SAT baseline is complete. It is an
infrastructure and regression baseline, not a reproduction of the full
Improved Attacks paper.

| Part | Completed result | Details |
|---|---|---|
| B1 | Static variable/clause, DDT, weight, permutation and decoding map | [B1 details](docs/current_analysis/sat_baseline_static_map.md) |
| B2 | Versioned `SolverRequest` / `SolverResult` contracts | [B2 details](docs/current_analysis/sat_baseline_b2.md) |
| B3 | Independent GIFT-64 trail and objective verifier | [B3 details](docs/current_analysis/sat_baseline_b3.md) |
| B4 | CryptoMiniSat 5.14.7 compile and smoke solve | [B4 details](docs/current_analysis/sat_baseline_b4.md) |
| B5 | Controlled status, decoding and verified SAT result `11 / 1` | [B5 details](docs/current_analysis/sat_baseline_b5.md) |
| B6 | Stable semantic regression expectation and checker | [B6 details](docs/current_analysis/sat_baseline_b6.md) |
| B7 | Bounded one-thread/two-thread comparison with preserved semantics | [B7 details](docs/current_analysis/sat_baseline_b7.md) |

See the [SAT baseline index](docs/current_analysis/sat_baseline.md) for scope
and acceptance criteria. A fresh
[credibility audit](docs/current_analysis/sat_baseline_audit.md) passed the
baseline for continued scoped engineering use: it supports a verified
four-round SAT witness and regression boundary, not optimality, paper-scale
reproduction or a general performance claim. See
[project status](docs/current_analysis/project_status.md) for current progress,
maintenance items, blockers and the next action.

**Next step:** resolve the missing GIFT differential-level materials and choose
a bounded formal pipeline target. A1/A2 exploratory work remains frozen; see
[materials status](docs/current_analysis/materials_status.md).

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
