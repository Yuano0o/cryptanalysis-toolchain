"""Unified A1-A5 configuration for the controlled GIFT-64 pipeline demo.

This contract deliberately composes existing stage contracts instead of copying
their resource limits, seeds, or key-selection fields.  The composition mode
also states that the controlled boundaries are orchestrated without claiming
an unavailable A4-to-A5 artifact lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .gift64_stage2_demo_request import (
    Gift64Stage2DemoRequest,
    Gift64Stage2DemoRequestError,
    load_gift64_stage2_demo_request,
)
from .gift64_stage3_probability import (
    Gift64Stage3ProbabilityError,
    Gift64Stage3ProbabilityRequest,
    load_gift64_stage3_probability_request,
)
from .gift64_trail_information import (
    GIFT64_TRAIL_INFORMATION_SCHEMA_VERSION,
    GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
)


GIFT64_PIPELINE_DEMO_SCHEMA_VERSION = "gift64-pipeline-demo-request/v2"
GIFT64_PIPELINE_COMPOSITION_MODE = "controlled-boundary-orchestration/v1"
GIFT64_SUPPLEMENTARY_SOURCE_LAYOUT_ID = (
    "gift64-supplementary-differential-source-code/v1"
)


class Gift64PipelineDemoError(ValueError):
    """Raised when a composed A1-A5 demo plan is ambiguous or inconsistent."""


def _expect_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Gift64PipelineDemoError(f"{field_name} must be an object")
    return value


def _expect_exact_keys(
    data: Mapping[str, Any], expected: set[str], context: str
) -> None:
    missing = expected - set(data)
    unknown = set(data) - expected
    if missing:
        raise Gift64PipelineDemoError(
            f"{context} is missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise Gift64PipelineDemoError(
            f"{context} has unknown fields: {', '.join(sorted(unknown))}"
        )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Gift64PipelineDemoError(f"{field_name} must be non-empty")
    return value


def _require_trail_position(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 32:
        raise Gift64PipelineDemoError("trail_position must be an integer in 0..31")
    return value


def _require_relative_request_path(value: Any, field_name: str) -> str:
    path_text = _require_nonempty(value, field_name)
    if "\\" in path_text:
        raise Gift64PipelineDemoError(f"{field_name} must use a relative POSIX path")
    path = PurePosixPath(path_text)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".json":
        raise Gift64PipelineDemoError(
            f"{field_name} must be a relative JSON path without traversal"
        )
    return path.as_posix()


@dataclass(frozen=True)
class Gift64PipelineDemoConfig:
    """Static composition of the controlled A1-A5 boundaries."""

    schema_version: str
    request_id: str
    profile: str
    composition_mode: str
    upstream_layout_id: str
    trail_information_schema_version: str
    trail_information_source_sha256: str
    trail_position: int
    stage2_request_path: str
    stage3_request_path: str

    def __post_init__(self) -> None:
        if self.schema_version != GIFT64_PIPELINE_DEMO_SCHEMA_VERSION:
            raise Gift64PipelineDemoError("unsupported GIFT-64 pipeline schema")
        _require_nonempty(self.request_id, "request_id")
        if self.profile not in {"smoke", "formal"}:
            raise Gift64PipelineDemoError("profile must be smoke or formal")
        if self.composition_mode != GIFT64_PIPELINE_COMPOSITION_MODE:
            raise Gift64PipelineDemoError("unsupported pipeline composition mode")
        if self.upstream_layout_id != GIFT64_SUPPLEMENTARY_SOURCE_LAYOUT_ID:
            raise Gift64PipelineDemoError("unsupported GIFT-64 upstream layout")
        if self.trail_information_schema_version != GIFT64_TRAIL_INFORMATION_SCHEMA_VERSION:
            raise Gift64PipelineDemoError("unexpected TrailInformation schema")
        if self.trail_information_source_sha256 != GIFT64_TRAIL_INFORMATION_SOURCE_SHA256:
            raise Gift64PipelineDemoError("unexpected TrailInformation source hash")
        _require_trail_position(self.trail_position)
        _require_relative_request_path(self.stage2_request_path, "stages.a4.request_path")
        _require_relative_request_path(self.stage3_request_path, "stages.a5.request_path")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "profile": self.profile,
            "composition_mode": self.composition_mode,
            "upstream_layout_id": self.upstream_layout_id,
            "trail_information": {
                "schema_version": self.trail_information_schema_version,
                "source_sha256": self.trail_information_source_sha256,
            },
            "trail_position": self.trail_position,
            "stages": {
                "a1": {"enabled": True},
                "a2": {"enabled": True},
                "a3": {"enabled": True},
                "a4": {"request_path": self.stage2_request_path},
                "a5": {"request_path": self.stage3_request_path},
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> Gift64PipelineDemoConfig:
        data = _expect_mapping(value, "GIFT-64 pipeline request")
        _expect_exact_keys(
            data,
            {
                "schema_version",
                "request_id",
                "profile",
                "composition_mode",
                "upstream_layout_id",
                "trail_information",
                "trail_position",
                "stages",
            },
            "GIFT-64 pipeline request",
        )
        trail_information = _expect_mapping(
            data["trail_information"], "trail_information"
        )
        _expect_exact_keys(
            trail_information,
            {"schema_version", "source_sha256"},
            "trail_information",
        )
        stages = _expect_mapping(data["stages"], "stages")
        _expect_exact_keys(stages, {"a1", "a2", "a3", "a4", "a5"}, "stages")
        for stage_name in ("a1", "a2", "a3"):
            stage = _expect_mapping(stages[stage_name], f"stages.{stage_name}")
            _expect_exact_keys(stage, {"enabled"}, f"stages.{stage_name}")
            if stage["enabled"] is not True:
                raise Gift64PipelineDemoError(
                    f"stages.{stage_name}.enabled must be true for an A1-A5 plan"
                )
        a4 = _expect_mapping(stages["a4"], "stages.a4")
        a5 = _expect_mapping(stages["a5"], "stages.a5")
        _expect_exact_keys(a4, {"request_path"}, "stages.a4")
        _expect_exact_keys(a5, {"request_path"}, "stages.a5")
        return cls(
            schema_version=data["schema_version"],
            request_id=data["request_id"],
            profile=data["profile"],
            composition_mode=data["composition_mode"],
            upstream_layout_id=data["upstream_layout_id"],
            trail_information_schema_version=trail_information["schema_version"],
            trail_information_source_sha256=trail_information["source_sha256"],
            trail_position=data["trail_position"],
            stage2_request_path=a4["request_path"],
            stage3_request_path=a5["request_path"],
        )

    @classmethod
    def from_json(cls, text: str) -> Gift64PipelineDemoConfig:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise Gift64PipelineDemoError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(value)


@dataclass(frozen=True)
class Gift64PipelineDemoPlan:
    """Resolved configuration for the controlled A1-A5 orchestrator."""

    config: Gift64PipelineDemoConfig
    stage2_request: Gift64Stage2DemoRequest
    stage3_request: Gift64Stage3ProbabilityRequest

    def __post_init__(self) -> None:
        if self.stage2_request.trail_position != self.config.trail_position:
            raise Gift64PipelineDemoError(
                "A4 trail_position does not match the pipeline trail_position"
            )
        if self.stage3_request.trail_position != self.config.trail_position:
            raise Gift64PipelineDemoError(
                "A5 trail_position does not match the pipeline trail_position"
            )
        expected_counts = {
            "smoke": (8, 8),
            "formal": (1000, 100),
        }
        expected_key_count, expected_repeat_count = expected_counts[self.config.profile]
        if self.stage2_request.key_corpus.key_count != expected_key_count:
            raise Gift64PipelineDemoError(
                f"A4 key_count does not match {self.config.profile} profile"
            )
        if self.stage3_request.repeat_count != expected_repeat_count:
            raise Gift64PipelineDemoError(
                f"A5 repeat_count does not match {self.config.profile} profile"
            )


def load_gift64_pipeline_demo_config(path: str | Path) -> Gift64PipelineDemoConfig:
    return Gift64PipelineDemoConfig.from_json(Path(path).read_text(encoding="utf-8"))


def load_gift64_pipeline_demo_plan(path: str | Path) -> Gift64PipelineDemoPlan:
    config_path = Path(path)
    config = load_gift64_pipeline_demo_config(config_path)
    try:
        stage2_request = load_gift64_stage2_demo_request(
            config_path.parent / config.stage2_request_path
        )
        stage3_request = load_gift64_stage3_probability_request(
            config_path.parent / config.stage3_request_path
        )
    except (Gift64Stage2DemoRequestError, Gift64Stage3ProbabilityError) as exc:
        raise Gift64PipelineDemoError(str(exc)) from exc
    return Gift64PipelineDemoPlan(
        config=config,
        stage2_request=stage2_request,
        stage3_request=stage3_request,
    )
