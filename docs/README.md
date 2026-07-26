# Local Research Control

> `current_analysis/` and this index are project documentation. The restored
> `prior_planning/` set is intentionally ignored by Git and retained only as a
> local historical reference.

## Document groups

### Current analysis

These files reflect the latest full workspace and paper scan:

- [research_scan.md](current_analysis/research_scan.md): evidence-backed scan
  of repositories, papers, source relationships, schemas and compute
  environments.
- [materials_status.md](current_analysis/materials_status.md): materials and
  dependencies needed by each workstream, what is present, and what is missing.
- [project_status.md](current_analysis/project_status.md): current status,
  blockers and next milestone for the overall project and every component.
- [sat_baseline.md](current_analysis/sat_baseline.md): scope, inputs,
  acceptance criteria and execution checklist for the first exact SAT baseline.
- [sat_baseline_static_map.md](current_analysis/sat_baseline_static_map.md):
  source hashes, variable/clause counts, DDT/weight check, permutation
  direction and model decoding for baseline checkpoint B1.
- [sat_baseline_b2.md](current_analysis/sat_baseline_b2.md): implemented
  request/result contracts, configuration semantics, invariants and tests for
  checkpoint B2.
- [sat_baseline_b3.md](current_analysis/sat_baseline_b3.md): independent
  GIFT-64 DDT, permutation, continuity and split-weight verification for
  checkpoint B3.
- [sat_baseline_b4.md](current_analysis/sat_baseline_b4.md): CryptoMiniSat
  environment, out-of-tree compile and short legacy smoke-solve evidence for
  checkpoint B4.
- [sat_baseline_b5.md](current_analysis/sat_baseline_b5.md): hash-pinned status
  adapter, strict model decoding, independent verification and controlled
  `SolverResult` evidence for checkpoint B5.
- [sat_baseline_b6.md](current_analysis/sat_baseline_b6.md): normalized semantic
  regression expectation, non-deterministic-field policy and temporary
  end-to-end checker for checkpoint B6.

### Prior planning

These eight files are restored unchanged from the planning set that existed
before commit `49fd340`:

- `project_overview.md`
- `research_workstreams.md`
- `research_roadmap.md`
- `open_questions.md`
- `repo_inventory.md`
- `repo_paper_map.md`
- `paper_repo_map.md`
- `git_strategy.md`

## Update rules

1. Update `current_analysis/materials_status.md` when a paper, archive, dataset,
   solver, expected output or external code source is added or confirmed
   unavailable.
2. Update `current_analysis/project_status.md` after a milestone changes state
   or a blocker is added/removed.
3. Update `current_analysis/sat_baseline.md` after each baseline checkpoint,
   including static review, configuration, compilation, solve, independent
   validation and regression capture.
4. Keep generated CNF, solver logs, binaries, datasets and model outputs out of
   this directory and out of Git.
5. Record evidence and paths. Do not mark a result reproduced until the exact
   configuration and independent validation are both available.
6. Treat `prior_planning/` as a preserved reference set. Reconcile differences
   explicitly instead of silently merging it into the current analysis.
