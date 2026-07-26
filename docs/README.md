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
- [sat_baseline_b7.md](current_analysis/sat_baseline_b7.md): bounded alternating
  one-thread/two-thread comparison and its reproducibility limits.
- [sat_baseline_audit.md](current_analysis/sat_baseline_audit.md): current
  credibility decision, rerun evidence, supported-claim boundary and tracked
  maintenance follow-ups for B1-B7.
- [gift64_trail_information_a1.md](current_analysis/gift64_trail_information_a1.md):
  recovered `TrailInformation.out` record/round/bit semantics, strict versioned
  parser, provenance limits and A1 test evidence.
- [gift64_linear_constraints_a2.md](current_analysis/gift64_linear_constraints_a2.md):
  recovered LC matrix/round-constant semantics, versioned GF(2)
  `ConstraintSet`, semantic affine-space hashing and bounded equivalence
  evidence.
- [gift64_linearized_constraints_a3.md](current_analysis/gift64_linearized_constraints_a3.md):
  recovered global LNC-stage semantics, combined LC-plus-linearised spaces,
  exact LC implication and incremental-rank evidence.
- [gift64_stage2_a4.md](current_analysis/gift64_stage2_a4.md): deterministic
  generated-for-demo key-corpus contract, bounded hash-pinned Stage 2 adapter,
  explicit physical trail selection and fixed-key status boundary.

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

1. Keep the root `README.md` as an outcome-first project overview. After each
   completed part, add only a short result summary, its detail link, the current
   progress link and the next step.
2. Put implementation evidence, methodology, commands, limitations and
   detailed results in a dedicated `current_analysis/<part>.md` file.
3. Update `current_analysis/materials_status.md` when a paper, archive, dataset,
   solver, expected output or external code source is added or confirmed
   unavailable.
4. Update `current_analysis/project_status.md` after a milestone changes state
   or a blocker is added/removed.
5. Update the relevant part index, such as
   `current_analysis/sat_baseline.md`, after each checkpoint, including static
   review, configuration, execution, independent validation and regression
   capture.
6. End each completed part by updating the recorded next step and linking both
   its detail file and `project_status.md` from the root README.
7. Keep generated CNF, solver logs, binaries, datasets and model outputs out of
   this directory and out of Git.
8. Record evidence and paths. Do not mark a result reproduced until the exact
   configuration and independent validation are both available.
9. Treat `prior_planning/` as a preserved reference set. Reconcile differences
   explicitly instead of silently merging it into the current analysis.
10. Keep review conclusions in a durable audit file with dated evidence and
    stable follow-up IDs. Update the root summary only when the audit decision
    or project next step changes.
