# Learning-Guided Cryptanalysis

Private research repository for reproducible, testable cryptanalysis workflows.

## Research projects

### 1. Automated Differential-Level Analysis Pipeline

Turn the scattered GIFT-64 workflow into a modular pipeline:

`SAT trail search → enumeration/grouping → LC/LNC analysis → fixed-key
validation → coexistence/right-key-space analysis → probability evaluation →
differential construction → reporting`

GIFT-64 is the first full application. BAKSHEESH is the initial implementation
benchmark; CRAFT and WARP are later portability targets.

### 2. ML-Guided SAT Search

Explore learned partial-trail scoring, candidate ranking, instance-difficulty
prediction, and branch/search-region prioritisation. ML is an optional
acceleration module: every final result, correctness claim, and optimality claim
must be verified by an exact SAT solver.

## Repository layout

```text
src/
  automated_differential_analysis/  exact pipeline stages and orchestration
  ml_guided_sat/                    optional learned search guidance
  shared/                           common schemas and solver interfaces
adapters/                         narrow wrappers around read-only upstream code
benchmarks/                       small benchmark definitions and test vectors
configs/                          versioned, non-secret configurations
experiments/
  gift64/                         GIFT-64 experiment manifests
  baksheesh/                      initial benchmark manifests
  craft_warp/                     later portability manifests
tests/                            unit, integration, and regression tests
docs/                             design, inventory, mapping, and roadmap
```

The four public reference repositories remain independent siblings under
`../upstream/`. Do not vendor or edit them; invoke them through adapters or
wrappers.

## Repository policy

Commit only source code, small configurations, tests, experiment manifests, and
research documentation. Do not commit PDF papers, CNF/WCNF instances, large
datasets, model weights, solver logs, generated outputs, unpublished results,
credentials, or internal notes.

Start with [the project overview](docs/project_overview.md),
[the repository–paper map](docs/repo_paper_map.md), and
[the research roadmap](docs/research_roadmap.md).
