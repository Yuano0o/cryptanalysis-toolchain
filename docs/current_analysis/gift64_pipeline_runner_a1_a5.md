# GIFT-64 Pipeline A1-A5: Unified Runner

> Implemented locally: 2026-07-26
>
> Scope: execute the pinned, controlled A1-A5 smoke or formal demo plan and
> return one generated structured observation. This is not a paper-level
> reproduction or an attack-level result.

## Result

`src/automated_differential_analysis/pipeline_runner.py` consumes a validated
`gift64-pipeline-demo-request/v1` plan, runs A1 through A5 in dependency order
and emits `gift64-pipeline-observation/v1`. The command-line entry point is
`scripts/run_gift64_pipeline_demo.py`.

The runner retains each native stage summary under its matching `a1` through
`a5` entry. It records the configuration, read-only source root, per-stage and
total wall time, terminal state, and a claim boundary in one JSON document.
It writes that document to standard output only: it does not create or track a
result artifact in the repository.

## Stage and failure semantics

| Stage | Runner input | Dependency use |
|---|---|---|
| A1 | hash-pinned `TrailInformation.out` | parses the 32-record corpus |
| A2 | LC source and A1 fixture | observes canonical LC spaces |
| A3 | LNC source and A1 fixture | receives the A2 LC constraint sets |
| A4 | Stage 2 source, fixture and referenced request | runs the deterministic generated-key corpus |
| A5 | Stage 3 source, fixture, supplied key fixture and referenced request | runs seeded subcube samples |

An `OSError` or validation error from a stage marks that stage `failed` and
marks every later stage `not_run_upstream_failure`. A skipped stage is never
reported as a solver status or cryptanalytic outcome. A fully successful run
has five `completed` stages; the process exits with code 0. A started but
failed pipeline (including a missing stage input) still prints its structured
observation and exits with code 1; an invalid plan or runner invocation exits
with code 2.

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

On 2026-07-26, the smoke command completed all five stages in 4.65 seconds of
reported pipeline wall time. Its summary reported A1's 32 records, A2 rank 6,
A3 combined rank 8 with all LC bases implied, eight A4 outcomes, and eight
complete A5 samples. These values demonstrate interface composition only; the
small key/sample budgets and non-proof-producing solver workflow prohibit a
paper-level probability, right-key-space or `UNSAT` claim.

## Validation

`tests/test_gift64_pipeline_runner.py` covers ordered hand-off, the A2-to-A3
constraint-set dependency, failure propagation, and a smoke-sized end-to-end
run when the read-only source, compiler and solver environment are available.
