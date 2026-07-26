"""Dependency-ordered runner for the controlled GIFT-64 A1-A5 demo plan."""

from __future__ import annotations

from dataclasses import dataclass
import time
from pathlib import Path
from typing import Any, Callable

from automated_differential_analysis.adapters.gift64_lc_legacy import (
    Gift64LCObservation,
    run_gift64_lc_observation,
)
from automated_differential_analysis.adapters.gift64_lnc_legacy import (
    run_gift64_lnc_observation,
)
from automated_differential_analysis.adapters.gift64_stage2_legacy import (
    GIFT64_STAGE2_SOLVER_VERSION,
    run_gift64_stage2_demo,
)
from automated_differential_analysis.adapters.gift64_stage3_legacy import (
    GIFT64_STAGE3_SOLVER_VERSION,
    run_gift64_stage3_probability_demo,
)
from automated_differential_analysis.formats import (
    GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
    Gift64PipelineDemoPlan,
    parse_gift64_trail_information,
)


GIFT64_PIPELINE_RUNNER_VERSION = "gift64-pipeline-runner/v1"
GIFT64_PIPELINE_OBSERVATION_SCHEMA_VERSION = "gift64-pipeline-observation/v1"
_STAGE_IDS = ("a1", "a2", "a3", "a4", "a5")
_STAGE_STATES = {"completed", "failed", "not_run_upstream_failure"}


class Gift64PipelineRunnerError(ValueError):
    """Raised when a runner invocation cannot be configured safely."""


@dataclass(frozen=True)
class Gift64PipelineSourceTree:
    """Read-only upstream source layout selected by the unified manifest."""

    source_root: Path

    @property
    def a1_trail_path(self) -> Path:
        return self.source_root / "2.Finding_linear_constraints" / "TrailInformation.out"

    @property
    def a2_root(self) -> Path:
        return self.source_root / "2.Finding_linear_constraints"

    @property
    def a3_root(self) -> Path:
        return self.source_root / "3.Finding_linearized_nonlinear_constraints"

    @property
    def a4_root(self) -> Path:
        return self.source_root / "4.Stage2_test"

    @property
    def a5_root(self) -> Path:
        return self.source_root / "5.Stage3_test"


@dataclass(frozen=True)
class Gift64PipelineStageObservation:
    """One stage's terminal runner state and its structured stage output."""

    stage_id: str
    state: str
    wall_time_s: float
    summary: dict[str, Any] | None
    diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.stage_id not in _STAGE_IDS:
            raise Gift64PipelineRunnerError("unknown pipeline stage")
        if self.state not in _STAGE_STATES:
            raise Gift64PipelineRunnerError("unknown pipeline stage state")
        if self.wall_time_s < 0:
            raise Gift64PipelineRunnerError("stage wall time must be non-negative")
        if self.state == "completed" and self.summary is None:
            raise Gift64PipelineRunnerError("completed stage must have a summary")
        if self.state != "completed" and self.summary is not None:
            raise Gift64PipelineRunnerError("incomplete stage must not have a summary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "state": self.state,
            "wall_time_s": self.wall_time_s,
            "summary": self.summary,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class Gift64PipelineObservation:
    """Generated A1-A5 summary, including failures and skipped descendants."""

    runner_version: str
    request: dict[str, Any]
    source_root: str
    run_wall_time_s: float
    state: str
    failed_stage: str | None
    stages: tuple[Gift64PipelineStageObservation, ...]

    def __post_init__(self) -> None:
        if self.runner_version != GIFT64_PIPELINE_RUNNER_VERSION:
            raise Gift64PipelineRunnerError("unsupported pipeline runner version")
        if self.state not in {"completed", "failed"}:
            raise Gift64PipelineRunnerError("unknown pipeline observation state")
        if self.run_wall_time_s < 0:
            raise Gift64PipelineRunnerError("pipeline wall time must be non-negative")
        if tuple(stage.stage_id for stage in self.stages) != _STAGE_IDS:
            raise Gift64PipelineRunnerError("pipeline stages must be A1 through A5")
        failed = tuple(stage.stage_id for stage in self.stages if stage.state == "failed")
        if self.state == "completed":
            if self.failed_stage is not None or failed:
                raise Gift64PipelineRunnerError("completed pipeline cannot have failures")
            if any(stage.state != "completed" for stage in self.stages):
                raise Gift64PipelineRunnerError("completed pipeline cannot skip stages")
        else:
            if self.failed_stage is None or failed != (self.failed_stage,):
                raise Gift64PipelineRunnerError("failed pipeline must identify one failed stage")

    def summary_dict(self) -> dict[str, Any]:
        return {
            "schema_version": GIFT64_PIPELINE_OBSERVATION_SCHEMA_VERSION,
            "runner_version": self.runner_version,
            "scope": "controlled A1-A5 GIFT-64 pipeline demo",
            "request": self.request,
            "source_root": self.source_root,
            "run_wall_time_s": self.run_wall_time_s,
            "state": self.state,
            "failed_stage": self.failed_stage,
            "stages": [stage.to_dict() for stage in self.stages],
            "claim_boundary": (
                "composed controlled demo observations; not a paper-level "
                "reproduction, complete right-key-space result, or proof-producing "
                "UNSAT workflow"
            ),
        }


def _completed_stage(
    stage_id: str, start: float, observation: Any
) -> Gift64PipelineStageObservation:
    return Gift64PipelineStageObservation(
        stage_id=stage_id,
        state="completed",
        wall_time_s=time.monotonic() - start,
        summary=observation.summary_dict(),
        diagnostics=(),
    )


def _failed_stage(
    stage_id: str, start: float, error: Exception
) -> Gift64PipelineStageObservation:
    return Gift64PipelineStageObservation(
        stage_id=stage_id,
        state="failed",
        wall_time_s=time.monotonic() - start,
        summary=None,
        diagnostics=(f"{type(error).__name__}: {error}",),
    )


def _skipped_stage(stage_id: str, failed_stage: str) -> Gift64PipelineStageObservation:
    return Gift64PipelineStageObservation(
        stage_id=stage_id,
        state="not_run_upstream_failure",
        wall_time_s=0.0,
        summary=None,
        diagnostics=(f"not run because upstream stage {failed_stage} failed",),
    )


def _run_stage(
    stage_id: str, operation: Callable[[], Any]
) -> tuple[Gift64PipelineStageObservation, Any | None]:
    start = time.monotonic()
    try:
        observation = operation()
    except (OSError, ValueError) as exc:
        return _failed_stage(stage_id, start, exc), None
    return _completed_stage(stage_id, start, observation), observation


def run_gift64_pipeline_demo(
    *, plan: Gift64PipelineDemoPlan, source_tree: Gift64PipelineSourceTree
) -> Gift64PipelineObservation:
    """Run A1 through A5 in dependency order and return one generated summary.

    Stage errors are terminal for this invocation: their descendants are marked
    ``not_run_upstream_failure`` so an omitted stage can never be mistaken for
    a solver or cryptanalytic result.
    """

    if not isinstance(plan, Gift64PipelineDemoPlan):
        raise Gift64PipelineRunnerError("plan must be a Gift64PipelineDemoPlan")
    if not isinstance(source_tree, Gift64PipelineSourceTree):
        raise Gift64PipelineRunnerError("source_tree must be a Gift64PipelineSourceTree")
    if plan.stage2_request.solver_version != GIFT64_STAGE2_SOLVER_VERSION:
        raise Gift64PipelineRunnerError("A4 solver version does not match adapter")
    if plan.stage3_request.solver_version != GIFT64_STAGE3_SOLVER_VERSION:
        raise Gift64PipelineRunnerError("A5 solver version does not match adapter")

    run_start = time.monotonic()
    stages: list[Gift64PipelineStageObservation] = []
    failed_stage: str | None = None
    a2_observation: Gift64LCObservation | None = None

    stage, _ = _run_stage(
        "a1",
        lambda: parse_gift64_trail_information(
            source_tree.a1_trail_path,
            expected_source_sha256=GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
        ),
    )
    stages.append(stage)
    if stage.state == "failed":
        failed_stage = "a1"

    if failed_stage is None:
        stage, a2_observation = _run_stage(
            "a2",
            lambda: run_gift64_lc_observation(
                source_path=source_tree.a2_root / "main.cpp",
                trail_path=source_tree.a2_root / "TrailInformation.out",
            ),
        )
        stages.append(stage)
        if stage.state == "failed":
            failed_stage = "a2"
    else:
        stages.append(_skipped_stage("a2", failed_stage))

    if failed_stage is None:
        assert a2_observation is not None
        stage, _ = _run_stage(
            "a3",
            lambda: run_gift64_lnc_observation(
                source_path=source_tree.a3_root / "main.cpp",
                trail_path=source_tree.a3_root / "TrailInformation.out",
                lc_constraint_sets=a2_observation.constraint_sets,
            ),
        )
        stages.append(stage)
        if stage.state == "failed":
            failed_stage = "a3"
    else:
        stages.append(_skipped_stage("a3", failed_stage))

    if failed_stage is None:
        stage, _ = _run_stage(
            "a4",
            lambda: run_gift64_stage2_demo(
                source_path=source_tree.a4_root / "main.cpp",
                trail_path=source_tree.a4_root / "TrailInformation.out",
                key_corpus_spec=plan.stage2_request.key_corpus,
                trail_position=plan.stage2_request.trail_position,
                per_key_time_limit_s=plan.stage2_request.per_key_time_limit_s,
                total_time_limit_s=plan.stage2_request.total_time_limit_s,
            ),
        )
        stages.append(stage)
        if stage.state == "failed":
            failed_stage = "a4"
    else:
        stages.append(_skipped_stage("a4", failed_stage))

    if failed_stage is None:
        stage, _ = _run_stage(
            "a5",
            lambda: run_gift64_stage3_probability_demo(
                source_path=source_tree.a5_root / "main.cpp",
                trail_path=source_tree.a5_root / "TrailInformation.out",
                key_corpus_path=source_tree.a5_root / "KeyCandidate1000.out",
                request=plan.stage3_request,
            ),
        )
        stages.append(stage)
        if stage.state == "failed":
            failed_stage = "a5"
    else:
        stages.append(_skipped_stage("a5", failed_stage))

    return Gift64PipelineObservation(
        runner_version=GIFT64_PIPELINE_RUNNER_VERSION,
        request=plan.config.to_dict(),
        source_root=str(source_tree.source_root),
        run_wall_time_s=time.monotonic() - run_start,
        state="failed" if failed_stage is not None else "completed",
        failed_stage=failed_stage,
        stages=tuple(stages),
    )
