# Design

How the toolchain drives unmodified analysis programs while keeping results
reproducible and checkable.

## The starting point

The GIFT-64 reference material is six standalone C++ programs, 5,723 lines,
each compiled by hand. Their authors aimed at a published result, and four
properties follow from that which a script has to work around:

| Property | Consequence |
|---|---|
| Parameters are constants edited into the source before each build. The upstream README documents changing `ObjectiveProb` and `GroupIndex` in `main.cpp`. | A run is described by a source diff rather than by a configuration. |
| Stages exchange results as files copied between directories. The same `TrailInformation.out` sits in three stage folders. | The interface between stages is a filename, and copies are indistinguishable. |
| One stage draws its experimental subcubes from `random_device`. | Two runs sample different subspaces, so their numbers are not comparable. |
| Keys and trail positions are hard-coded, one per program. | Varying coverage means editing and recompiling. |

None of this is a shortcoming. It is what analysis code looks like when the
goal is a published result rather than a reusable tool.

## The boundary

Each adapter converts one implicit property into an explicit, recorded one,
while leaving the original file read-only.

| In the original program | At the boundary |
|---|---|
| Parameters edited into the source | Explicit fields in a versioned request schema |
| `.out` files copied between directories | Typed contracts passed between stages |
| Subcubes drawn from `random_device` | Explicit seed; the same request reproduces the same subcubes |
| One hard-coded key and trail | Explicit key/trail positions; deterministic key generation at 8-key and 1,000-key scale |
| Runs until it finishes | Per-sample and total budget caps |
| Prints a number regardless of completion | An unfinished run returns a distinct unstarted state, never a usable-looking number |
| Solver output trusted as decoded | An independent verifier that shares no logic with the encoder |

Adapters instrument a temporary copy. The original tree is never written to.

## Independent evolution

Upstream sources are never vendored or copied into this repository. They are
reached through narrow adapters and subprocess boundaries, and each adapter
verifies a pinned source hash before running.

This is what allows the two sides to be maintained separately. A researcher
keeps working in their own tree and never has to touch this repository. If that
tree changes, the pinned hash reports it, rather than the toolchain silently
producing results against a program it no longer recognises.

## Versioned contracts

Eleven schemas carry data between stages:

```text
solver-request/v1                    solver-result/v1
solver-regression-expectation/v1     trail-record/v1
constraint-set/v1                    gift64-trail-information/v1
gift64-stage2-demo-request/v2        gift64-stage2-key-corpus/v1
gift64-stage2-observation/v2         gift64-pipeline-demo-request/v2
gift64-pipeline-observation/v2
```

A stage depends on a declared interface with a version number, not on the byte
layout of whatever file the previous stage happened to leave behind. Adding a
field is a version bump, not a silent break.

## Determinism

- Fixed seeds and pinned fixtures for every sampled stage
- `sha256-counter-v1` key generation, reproducible at both 8-key smoke and
  1,000-key formal scale
- Finite per-sample and total budgets, so a run cannot become unbounded
- **Completion-gated results.** A probability estimate is emitted only when
  sampling actually finished. An interrupted or budget-exhausted run returns a
  distinct unstarted state. There is no third outcome in which a partial run
  looks complete.

## Verification that cannot validate itself

The trail and objective verifier shares no code with the encoder. It decodes the
solver's model independently and re-derives the objective, so an error in the
encoding cannot be confirmed by the component that produced it.

This is what makes the four-round `11 / 1` result a witness rather than a
printout.

## Provenance

Every stage output records the hashes of everything that produced it — the
adapter's pinned source, the legacy program's captured stdout, and the input
fixture. Any result can be traced back to its exact inputs.

```json
{
  "adapter_version": "gift64-lc-legacy-adapter/v1",
  "constraint_set_schema_version": "constraint-set/v1",
  "legacy_stdout_sha256": "b03a368c3128edf7042f57a9609822be968a324e7163f38c933782c779412a13",
  "source_sha256": "42f734a6cc7969a55fca5ad498ae319c2676fe4c6e3178ff633efa6295df7bd2",
  "trail_source_sha256": "fe40ca7b81d4c362d45db58c7c4448317d0305bbd149e04abe12bcede8c02335"
}
```

## Regression as a semantic boundary

A frozen expectation and checker detect behavioural change across edits,
including a controlled one-thread/two-thread comparison confirming that
parallelism does not alter semantics. A smoke-sized end-to-end test exercises the
real runner whenever the upstream sources, a compiler and CryptoMiniSat are
present, and skips rather than silently passing when they are not.

## Claim boundaries

A fixed status vocabulary is used across every status document:

```text
complete   complete-draft   in-progress   ready
ready-for-static-work       blocked       not-started   deferred
```

"Finished", "usable" and "stuck" therefore never blur together. Each milestone
states what its results support and what they do not, and reproduction blockers
are recorded as material gaps rather than worked around silently.

## Related documents

- [Project status](current_analysis/project_status.md) — per-component progress, next actions, blockers
- [SAT baseline](current_analysis/sat_baseline.md) — scope and acceptance criteria
- [Credibility audit](current_analysis/sat_baseline_audit.md) — what the baseline supports and does not
- [Pipeline acceptance](current_analysis/gift64_pipeline_acceptance_a1_a5.md) — the seven acceptance criteria
- [References](references.md) — papers and reference implementations this builds on
- [Engineering rules](ENGINEERING_RULES.md) — working rules this repository follows
