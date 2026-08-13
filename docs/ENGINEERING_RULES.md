# Engineering Rules

## Scope

- Make all new code changes inside this repository.
- Treat every repository under `../upstream/` as read-only reference code.
- Do not refactor, format, patch, commit, or change remotes in `../upstream/`
  unless the user explicitly requests a specific upstream change.
- Do not vendor or copy an entire upstream repository. Use a narrow adapter,
  subprocess boundary, or configuration path instead.
- Put exact pipeline code in `src/automated_differential_analysis/`, optional
  learned guidance in `src/ml_guided_sat/`, and common contracts in
  `src/shared/`.
- Treat GIFT-64, BAKSHEESH, CRAFT, and WARP as case studies or benchmarks, not
  separate research projects.

## Reproducibility

- Keep pipeline stages composable, deterministic where possible, and testable.
- Record small experiment configurations and seeds, but never generated outputs.
- Add unit tests for encodings and transformations and integration tests for
  adapter boundaries.
- Prefer relative, configurable upstream paths over machine-specific paths.
- Keep ML guidance optional. Exact SAT verification is required for final
  cryptanalytic results and optimality claims.
- Organize experiment manifests under `experiments/gift64/`,
  `experiments/baksheesh/`, or `experiments/craft_warp/`; never place generated
  outputs there for Git tracking.

## Repository hygiene

- Never commit PDFs, CNF instances, datasets, model weights, solver logs,
  generated outputs, unpublished results, credentials, or internal notes.
- Before committing, inspect both `git status` and the complete staged diff.
- Keep commits small and focused. Separate framework changes, cipher adapters,
  tests, documentation, and experiment manifests when practical.

## Public contributions

- Do not fork or prepare a public pull request unless explicitly authorized.
- For an approved upstream contribution, start from a fresh fork branch and
  create a new minimal commit containing only the independently reviewable
  upstream change.
- Never transplant private research history, internal documentation, failed
  experiments, datasets, or unpublished conclusions into a public branch.
