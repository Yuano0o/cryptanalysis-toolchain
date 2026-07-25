# Research Roadmap

## Governing principle

Build one exact, reproducible differential-analysis platform with an optional
ML-guidance layer. ML may prioritise work, but an exact solver must validate all
final trails, bounds, probabilities, and cryptanalytic claims.

## Phase 0 — Reproducibility contract

- Define versioned schemas for cipher parameters, trail records, constraints,
  solver results, right-key spaces, probability estimates, and reports.
- Add deterministic seeds, provenance, time/memory limits, and solver-version
  recording.
- Implement adapters that call sibling upstream repositories without copying or
  modifying them.
- Add one tiny fixture and one expected-output regression test per boundary.

**Exit criterion:** a short smoke workflow can be rerun from a clean checkout
and produces validated, schema-conforming metadata.

## Phase 1 — BAKSHEESH benchmark

- Wrap the existing encryption implementation and preserve the known test
  vector as a regression test.
- Independently specify the linear-characteristic SAT encoding and validate
  small-round cases by exhaustive or independently checked results.
- Measure exact-solver runtime and create small, non-sensitive benchmark
  manifests.

**Exit criterion:** small-round results agree across at least two independent
checks.
**TODO:** determine whether the original optimal-search code can be obtained.

## Phase 2 — GIFT-64 automated differential-level pipeline

Implement explicit stages:

1. SAT trail search;
2. trail enumeration and grouping;
3. LC/LNC extraction;
4. fixed-key validation;
5. trail coexistence and right-key-space analysis;
6. probability evaluation;
7. differential construction;
8. result reporting.

First reproduce a small, bounded subset of the published workflow. Only then
scale toward the full 8.25-round core and 18/19-round extensions.

**Exit criterion:** each stage is independently testable, records provenance,
and can resume without relying on implicit filenames or hard-coded constants.
**TODO:** recover/replace `KeyCandidate.out`, confirm exact paper-section
provenance, and identify how the published extensions were generated.

## Phase 3 — ML-guided SAT module

- Establish exact-solver-only baselines before training.
- Start with low-risk tasks: instance difficulty prediction and candidate
  ranking.
- Compare partial-trail scoring and search-region/branch prioritisation against
  deterministic heuristics under fixed budgets.
- Send every selected candidate back to the exact solver; track speedup,
  coverage, false-negative risk, and verification cost separately.

**Exit criterion:** a held-out benchmark shows reproducible end-to-end benefit
without changing the verified result set.
**TODO:** confirm whether NeuroGIFT code, training data, and trained models are
available.

## Phase 4 — Portability evaluation

- Add CRAFT and WARP only after the GIFT interfaces stabilise.
- Separate cipher-specific transition/key-schedule logic from general trail,
  constraint, probability, and reporting interfaces.
- Test whether guidance transfers across round counts and ciphers, and compare
  against retraining from scratch.

**Exit criterion:** the same pipeline API supports a second cipher without
forking the framework architecture.
**TODO:** obtain *Key-Recovery Attacks on CRAFT and WARP* and map every
supplementary pattern/code stage to a published result.

## Near-term order

1. Read the GIFT repository `Source_code/README.md`, the Linearisation paper
   Sections 4–6, and the GIFT paper Sections 3–4 together.
2. Turn the BAKSHEESH test vector into the first adapter regression test.
3. Design schemas and exact-solver interfaces before implementing ML.
4. Reproduce a deliberately small GIFT subset, then add candidate ranking.

Do not begin long experiments until dependencies, resource limits, seeds,
artifact locations, and expected outputs are explicitly configured.
