"""Versioned run configuration for the bounded GIFT-64 Stage 2 demo."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .gift64_stage2_key_corpus import (
    Gift64Stage2KeyCorpusError,
    Gift64Stage2KeyCorpusSpec,
)


GIFT64_STAGE2_DEMO_REQUEST_SCHEMA_VERSION = "gift64-stage2-demo-request/v1"


class Gift64Stage2DemoRequestError(ValueError):
    """Raised when a bounded Stage 2 demo request is incomplete or unsafe."""


def _expect_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Gift64Stage2DemoRequestError(f"{field_name} must be an object")
    return value


def _expect_exact_keys(
    data: Mapping[str, Any], keys: set[str], context: str
) -> None:
    missing = keys - set(data)
    unknown = set(data) - keys
    if missing:
        raise Gift64Stage2DemoRequestError(
            f"{context} is missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise Gift64Stage2DemoRequestError(
            f"{context} has unknown fields: {', '.join(sorted(unknown))}"
        )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Gift64Stage2DemoRequestError(f"{field_name} must be non-empty")
    return value


def _require_nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Gift64Stage2DemoRequestError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _require_positive_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise Gift64Stage2DemoRequestError(
            f"{field_name} must be a positive number"
        )
    return float(value)


@dataclass(frozen=True)
class Gift64Stage2DemoRequest:
    schema_version: str
    request_id: str
    trail_position: int
    key_corpus: Gift64Stage2KeyCorpusSpec
    solver_name: str
    solver_version: str
    per_key_time_limit_s: float

    def __post_init__(self) -> None:
        if self.schema_version != GIFT64_STAGE2_DEMO_REQUEST_SCHEMA_VERSION:
            raise Gift64Stage2DemoRequestError("unsupported Stage 2 request schema")
        _require_nonempty(self.request_id, "request_id")
        _require_nonnegative_int(self.trail_position, "trail_position")
        if self.trail_position >= 32:
            raise Gift64Stage2DemoRequestError(
                "trail_position must select one physical record in 0..31"
            )
        if not isinstance(self.key_corpus, Gift64Stage2KeyCorpusSpec):
            raise Gift64Stage2DemoRequestError(
                "key_corpus must be a Gift64Stage2KeyCorpusSpec"
            )
        _require_nonempty(self.solver_name, "solver_name")
        if self.solver_name != "cryptominisat":
            raise Gift64Stage2DemoRequestError("Stage 2 supports cryptominisat only")
        _require_nonempty(self.solver_version, "solver_version")
        _require_positive_number(self.per_key_time_limit_s, "per_key_time_limit_s")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "trail_position": self.trail_position,
            "key_corpus": self.key_corpus.to_dict(),
            "solver": {
                "name": self.solver_name,
                "version": self.solver_version,
            },
            "resources": {"per_key_time_limit_s": self.per_key_time_limit_s},
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> Gift64Stage2DemoRequest:
        data = _expect_mapping(value, "Stage 2 request")
        _expect_exact_keys(
            data,
            {
                "schema_version",
                "request_id",
                "trail_position",
                "key_corpus",
                "solver",
                "resources",
            },
            "Stage 2 request",
        )
        key_corpus = _expect_mapping(data["key_corpus"], "key_corpus")
        _expect_exact_keys(
            key_corpus,
            {"schema_version", "purpose", "generator_id", "seed", "key_count"},
            "key_corpus",
        )
        solver = _expect_mapping(data["solver"], "solver")
        _expect_exact_keys(solver, {"name", "version"}, "solver")
        resources = _expect_mapping(data["resources"], "resources")
        _expect_exact_keys(resources, {"per_key_time_limit_s"}, "resources")
        try:
            corpus_spec = Gift64Stage2KeyCorpusSpec(
                schema_version=key_corpus["schema_version"],
                purpose=key_corpus["purpose"],
                generator_id=key_corpus["generator_id"],
                seed=key_corpus["seed"],
                key_count=key_corpus["key_count"],
            )
        except Gift64Stage2KeyCorpusError as exc:
            raise Gift64Stage2DemoRequestError(str(exc)) from exc
        return cls(
            schema_version=data["schema_version"],
            request_id=data["request_id"],
            trail_position=data["trail_position"],
            key_corpus=corpus_spec,
            solver_name=solver["name"],
            solver_version=solver["version"],
            per_key_time_limit_s=resources["per_key_time_limit_s"],
        )

    @classmethod
    def from_json(cls, text: str) -> Gift64Stage2DemoRequest:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise Gift64Stage2DemoRequestError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(value)


def load_gift64_stage2_demo_request(path: str | Path) -> Gift64Stage2DemoRequest:
    return Gift64Stage2DemoRequest.from_json(Path(path).read_text(encoding="utf-8"))
