# GIFT-64 A1-A5 Integrated Demo Acceptance

> Acceptance executed: 2026-07-26
>
> Decision: **pass within the controlled-boundary-orchestration claim**
>
> Reviewed baseline: `beb225d` (`Correct GIFT-64 final acceptance status`)

## Purpose

This audit is the explicit final review of the seven integrated-demo
requirements. It is separate from the component implementation review and from
the administrative status transition previously made in PR #25. A merged PR,
passing component tests, or changing a tracker row to `complete` is not by
itself treated as final acceptance.

The accepted object is the controlled A1-A5 orchestration. It is not a strict
artifact-lineage pipeline, a paper reproduction, a complete right-key-space
calculation, or a proof-producing `UNSAT` workflow.

## Acceptance method

The review combined:

1. static inspection of the seven contracts, adapters, manifests, runner,
   command-line entry point and their tests;
2. one real dependency-backed acceptance regression that compiles and executes
   the hash-pinned A1-A5 boundaries; and
3. one command-line smoke run whose standard output was parsed as JSON and
   checked for successful terminal states.

The real integration test is
`Gift64PipelineRunnerIntegrationTests.test_seven_item_acceptance_smoke`.
Unlike the earlier partial smoke assertion, it jointly checks all seven
requirements and the shared claim boundary.

## Seven-item decision

| # | Requirement | Decision | Acceptance evidence |
|---|---|---|---|
| 1 | A3 LNC semantics and adapter | pass | The real run produced 32 combined spaces with base rank 6, combined rank 8 and incremental rank 2 |
| 2 | LC/LNC merge or association rule | pass | All 32 combined spaces imply their position-matched LC bases; the runner passes the A2 `ConstraintSet` objects directly into A3 |
| 3 | Stage 2 configurable sample count and deterministic keys | pass | The resolved smoke request carries `sha256-counter-v1`, seed `20260726`, eight keys and finite per-key/total budgets; the observation accounts for all eight configured results |
| 4 | Stage 3 fixed seed and unified probability result | pass | The resolved request preserves seed `20260726`, eight samples and finite budgets; every sample completed and the v3 observation produced an estimate derived from all eight counts |
| 5 | Unified configuration and pipeline runner | pass | Request v2 resolved A1-A5 with one shared trail position and explicit controlled-orchestration mode; runner observation v2 retained all resolved requests and five ordered stage summaries |
| 6 | End-to-end small regression | pass | The real runner completed A1-A5 with every execution and result state equal to `complete` |
| 7 | Automatically generated result summary | pass | The complete observation round-tripped through JSON, retained provenance and the claim boundary, and the CLI emitted parseable `gift64-pipeline-observation/v2` JSON to standard output |

## Executed evidence

Targeted seven-item acceptance:

```text
PYTHONPATH=src python3 -m unittest -v \
  tests.test_gift64_pipeline_runner.Gift64PipelineRunnerIntegrationTests.test_seven_item_acceptance_smoke

Ran 1 test in 4.945s
OK
```

Command-line output check:

```text
exit_code: 0
schema_version: gift64-pipeline-observation/v2
state: completed
result_state: complete
stages: a1 complete, a2 complete, a3 complete, a4 complete, a5 complete
reported run_wall_time_s: 4.051322792016435
```

The generated JSON was held in process memory and was not written into the
repository.

Complete regression suite after the acceptance-test expansion:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v

Ran 106 tests in 9.242s
OK
```

## Review finding and resolution

`ACC-A1A5-01` — **resolved during this acceptance.** The earlier final-status
change had no dedicated audit artifact, and the real smoke test asserted only
a subset of the seven joint requirements. The integration test now checks the
resolved configuration, common fixture hash, LC/LNC ranks and implication,
complete A4/A5 accounting, Stage 3 estimate coverage, JSON serialization,
ordered stage summaries and the claim boundary in one run. This audit provides
the missing durable decision record.

No blocking implementation defect was found in the accepted controlled
orchestration after that evidence gap was corrected.

## Accepted claim and exclusions

The accepted statement is:

> The versioned GIFT-64 A1-A5 controlled demo can resolve one smoke manifest,
> execute all five hash-pinned boundaries, preserve the recovered A2-to-A3
> constraint relationship, account for the configured A4/A5 work, and emit one
> provenance-preserving structured summary with honest completion semantics.

Acceptance does not establish:

- provenance for the original `KeyCandidate.out`, `KeyCandidate1000.out` or
  trail-concatenation process;
- strict A3-to-A4 or A4-to-A5 artifact lineage;
- independent proof evidence for native `UNSAT` statuses;
- an exact global probability or complete right-key space;
- regeneration of `AllMatrix33Trail.out`; or
- reproduction of a paper-level differential or attack result.

Those exclusions are preserved in the emitted `claim_boundary` and remain
outside this milestone.
