# GIFT-64 Pipeline A1-A5: Unified Runner

> Implemented locally: 2026-07-26
>
> Scope: execute the pinned, controlled A1-A5 smoke or formal demo plan and
> return one generated structured observation. This is not a paper-level
> reproduction or an attack-level result.

## Result

`src/automated_differential_analysis/pipeline_runner.py` consumes a validated
`gift64-pipeline-demo-request/v2` plan, runs the A1-A5 controlled boundary
orchestration and emits `gift64-pipeline-observation/v2`. The command-line
entry point is `scripts/run_gift64_pipeline_demo.py`.

The runner retains each native stage summary under its matching `a1` through
`a5` entry. It records the resolved pipeline/A4/A5 requests, composition mode,
read-only source root, per-stage and total wall time, execution state, result
state, and a claim boundary in one JSON document.
It writes that document to standard output only: it does not create or track a
result artifact in the repository.

## Stage and failure semantics

| Stage | Runner input | Relationship |
|---|---|---|
| A1 | hash-pinned `TrailInformation.out` | parses the 32-record corpus |
| A2 | LC source and A1 fixture | observes canonical LC spaces |
| A3 | LNC source and A1 fixture | receives the A2 LC constraint sets |
| A4 | Stage 2 source, fixture and referenced request | independently runs the deterministic generated-key demo corpus |
| A5 | Stage 3 source, fixture, supplied key fixture and referenced request | independently runs seeded samples; the key fixture is not an A4 output |

A stage now has two independent classifications:

- `state` describes execution: `completed`, `failed`, or
  `not_run_upstream_failure`;
- `result_state` describes analytical completeness: `complete`, `incomplete`,
  `inconclusive`, or `not_available`.

Validation, I/O and expected subprocess failures mark the stage `failed` and
all later stages `not_run_upstream_failure`. Native A4/A5 `ERROR`, `TIMEOUT`
or total-budget unstarted records instead preserve `state: completed` while
setting `result_state: incomplete`; native `UNKNOWN` produces
`inconclusive`. A5 is complete only when every sample is complete and its
estimate exists. Skipped work is never counted as a solver status.

The process exits 0 only when both pipeline execution and result are complete.
A structured failed, incomplete or inconclusive observation exits 1. An
invalid plan or runner invocation exits 2.

## Run commands

From the repository root:

```sh
PYTHONPATH=src python3 scripts/run_gift64_pipeline_demo.py
PYTHONPATH=src python3 scripts/run_gift64_pipeline_demo.py \
  --request experiments/gift64/pipeline_demo_formal_a1_a5.request.json
```

The first command uses the eight-key/eight-sample smoke profile. The second
uses the declared 1,000-key/100-sample formal-demo profile. Both require the
read-only `../upstream/Supplementary_Material_GIFT-64_Differential/Source_code`
layout, `clang++`, and the locally configured CryptoMiniSat environment.

## Local smoke evidence

After the joint-review hardening on 2026-07-26, the smoke command completed all
five stages with `state: completed`, `result_state: complete` and exit code 0
in 4.12 seconds of reported pipeline wall time. Its summary reported A1's 32 records, A2 rank 6,
A3 combined rank 8 with all LC bases implied, eight A4 outcomes, and eight
complete A5 samples. These values demonstrate interface composition only; the
small key/sample budgets and non-proof-producing solver workflow prohibit a
paper-level probability, right-key-space or `UNSAT` claim.

## Validation

`tests/test_gift64_pipeline_runner.py` covers ordered hand-off, the A2-to-A3
constraint-set dependency, execution/result-state separation, subprocess
failure propagation, and a smoke-sized end-to-end run when the read-only
source, compiler and solver environment are available.

The post-hardening complete suite contains 106 passing tests.
