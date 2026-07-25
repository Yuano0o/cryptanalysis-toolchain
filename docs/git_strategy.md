# Git and GitHub Strategy

## Repository and remotes

The `learning-guided-cryptanalysis/` directory is the only private research
repository and is also the planned GitHub repository name.

- Planned GitHub repository: `Yuano0o/learning-guided-cryptanalysis`
- Visibility: private
- Planned research remote:
  `git@github.com:Yuano0o/learning-guided-cryptanalysis.git`
- Local remote name: `origin`

Do not add the four public reference repositories as research remotes and do not
use Git submodules yet. They remain independent sibling repositories under
`../upstream/`, and adapters resolve them through configuration.

## Branches

- `main`: stable, reproducible framework state.
- `feature/<topic>`: framework or adapter development.
- `experiment/<topic>`: versioned experiment code and manifests only.
- `fix/<topic>`: focused correctness fixes.

Avoid a long-lived `develop` branch until collaboration volume justifies it.
After the private GitHub repository exists, protect `main` and merge reviewed
branches through pull requests.

## Commit policy

Use small, single-purpose commits with prefixes such as:

- `feat:` framework, adapter, or cipher capability;
- `fix:` correctness or reproducibility correction;
- `test:` unit, integration, or regression coverage;
- `exp:` experiment launcher or small manifest;
- `docs:` architecture, methodology, or inventory;
- `chore:` tooling and repository maintenance.

Do not commit generated results merely to reproduce an experiment. Commit the
code, seed, solver/version metadata, small configuration, and expected
validation criteria; keep raw outputs in ignored storage.

## Initial commit sequence

1. `chore: scaffold private research repository`
2. `docs: record upstream and paper mappings`
3. `test: add benchmark smoke-test harness`
4. `feat: add BAKSHEESH upstream adapter`
5. `feat: define differential pipeline interfaces`

The first two may be combined if the initial scaffold is reviewed as one unit.

## Future public pull requests

Do not fork or prepare public changes until the upstream maintainer confirms
that publication is appropriate. Then:

1. create a fresh fork of only the relevant upstream repository;
2. branch from its current public default branch;
3. reproduce the minimal independent change without copying private history;
4. add focused tests and public-safe documentation;
5. inspect the full branch diff and commit history for internal material;
6. open a narrowly scoped pull request.

Never merge, rebase, or cherry-pick the private research branch into a public
fork.
