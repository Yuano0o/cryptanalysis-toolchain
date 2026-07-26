# GIFT-64 Pipeline A1-A5: Unified Demo Configuration

> Defined locally: 2026-07-26
>
> Scope: compose the existing A1-A5 contracts into one validated smoke or
> formal demo plan. This is a configuration boundary only; it does not yet run
> stages or emit an integrated result summary.

## Result

`gift64-pipeline-demo-request/v1` is the single entry manifest for the
controlled A1-A5 demo. It records:

- one profile: `smoke` or `formal`;
- the fixed supplementary-source layout identity;
- the hash-pinned A1-A3 `TrailInformation.out` identity;
- one shared physical trail position; and
- relative references to the existing A4 and A5 request contracts.

Tracked entry configurations:

| Profile | Pipeline request | A4 | A5 |
|---|---|---|---|
| Smoke | [`pipeline_demo_smoke_a1_a5.request.json`](../../experiments/gift64/pipeline_demo_smoke_a1_a5.request.json) | eight deterministic generated keys | eight seeded Stage 3 subcube samples |
| Formal | [`pipeline_demo_formal_a1_a5.request.json`](../../experiments/gift64/pipeline_demo_formal_a1_a5.request.json) | 1,000 deterministic generated keys | 100 seeded Stage 3 subcube samples |

The manifest intentionally does **not** duplicate A4 key seeds, resource
limits, or A5 sampling fields. Those remain the single responsibility of their
stage request files. Changing a referenced request therefore remains visible
and independently validated.

## Resolution rules

Loading a pipeline plan validates all of the following before a future runner
can begin execution:

1. A1, A2 and A3 are all enabled; this is an A1-A5 integration plan, not a
   partial stage selector.
2. The source layout and `TrailInformation.out` schema/hash match the pinned
   GIFT-64 fixture contracts.
3. A4 and A5 request paths are relative JSON files beneath the pipeline
   configuration directory; absolute paths and `..` traversal are rejected.
4. A4 and A5 select the same physical trail position as the pipeline manifest.
5. `smoke` means exactly eight A4 keys and eight A5 repetitions; `formal`
   means exactly 1,000 A4 keys and 100 A5 repetitions.

This preserves the important distinction between physical record position and
the unavailable producer `GroupIndex` semantics.

## Implementation and tests

- `src/automated_differential_analysis/formats/gift64_pipeline_demo.py`
- `experiments/gift64/pipeline_demo_smoke_a1_a5.request.json`
- `experiments/gift64/pipeline_demo_formal_a1_a5.request.json`
- `tests/test_gift64_pipeline_demo.py`

Tests cover canonical round-tripping, actual resolution of both tracked
profiles, shared trail-position validation, profile sample-count validation,
required A1-A3 stage activation, and path-traversal rejection.

## Next boundary

The next change is a pipeline runner that loads this plan, invokes A1 through
A5 in dependency order, preserves each stage's structured summary, and stops
with explicit cross-stage failure semantics. The runner must keep generated
observations out of Git and must not upgrade the controlled demo into a
paper-level reproduction claim.
