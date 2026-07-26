"""Versioned contracts and estimator math for the bounded GIFT-64 Stage 3 demo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
import json
from pathlib import Path
from typing import Any, Mapping


GIFT64_STAGE3_PROBABILITY_REQUEST_SCHEMA_VERSION = (
    "gift64-stage3-probability-request/v1"
)
GIFT64_STAGE3_PROBABILITY_OBSERVATION_SCHEMA_VERSION = (
    "gift64-stage3-probability-observation/v1"
)


class Gift64Stage3ProbabilityError(ValueError):
    """Raised when Stage 3 configuration or count semantics are ambiguous."""


def _expect_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Gift64Stage3ProbabilityError(f"{field_name} must be an object")
    return value


def _expect_exact_keys(
    data: Mapping[str, Any], expected: set[str], context: str
) -> None:
    missing = expected - set(data)
    unknown = set(data) - expected
    if missing:
        raise Gift64Stage3ProbabilityError(
            f"{context} is missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise Gift64Stage3ProbabilityError(
            f"{context} has unknown fields: {', '.join(sorted(unknown))}"
        )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Gift64Stage3ProbabilityError(f"{field_name} must be non-empty")
    return value


def _require_integer_range(
    value: Any, field_name: str, lower: int, upper: int
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Gift64Stage3ProbabilityError(f"{field_name} must be an integer")
    if not lower <= value <= upper:
        raise Gift64Stage3ProbabilityError(
            f"{field_name} must be in {lower}..{upper}"
        )
    return value


def _require_positive_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise Gift64Stage3ProbabilityError(
            f"{field_name} must be a positive number"
        )
    return float(value)


@dataclass(frozen=True)
class Gift64Stage3ProbabilityRequest:
    """A bounded fixed-key/physical-trail subcube-counting request."""

    schema_version: str
    request_id: str
    key_position: int
    trail_position: int
    repeat_count: int
    fixed_bit_count: int
    sampling_seed: int
    solver_name: str
    solver_version: str
    per_sample_time_limit_s: float

    def __post_init__(self) -> None:
        if self.schema_version != GIFT64_STAGE3_PROBABILITY_REQUEST_SCHEMA_VERSION:
            raise Gift64Stage3ProbabilityError("unsupported Stage 3 request schema")
        _require_nonempty(self.request_id, "request_id")
        _require_integer_range(self.key_position, "key_position", 0, 999)
        _require_integer_range(self.trail_position, "trail_position", 0, 31)
        _require_integer_range(self.repeat_count, "repeat_count", 1, 10_000)
        _require_integer_range(self.fixed_bit_count, "fixed_bit_count", 1, 63)
        _require_integer_range(self.sampling_seed, "sampling_seed", 0, 2**64 - 1)
        if _require_nonempty(self.solver_name, "solver_name") != "cryptominisat":
            raise Gift64Stage3ProbabilityError("Stage 3 supports cryptominisat only")
        _require_nonempty(self.solver_version, "solver_version")
        _require_positive_number(
            self.per_sample_time_limit_s, "per_sample_time_limit_s"
        )

    @property
    def free_bit_count(self) -> int:
        return 64 - self.fixed_bit_count

    @property
    def subcube_size(self) -> int:
        return 1 << self.free_bit_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "key_position": self.key_position,
            "trail_position": self.trail_position,
            "repeat_count": self.repeat_count,
            "fixed_bit_count": self.fixed_bit_count,
            "sampling_seed": self.sampling_seed,
            "solver": {
                "name": self.solver_name,
                "version": self.solver_version,
            },
            "resources": {
                "per_sample_time_limit_s": self.per_sample_time_limit_s
            },
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> Gift64Stage3ProbabilityRequest:
        data = _expect_mapping(value, "Stage 3 request")
        _expect_exact_keys(
            data,
            {
                "schema_version",
                "request_id",
                "key_position",
                "trail_position",
                "repeat_count",
                "fixed_bit_count",
                "sampling_seed",
                "solver",
                "resources",
            },
            "Stage 3 request",
        )
        solver = _expect_mapping(data["solver"], "solver")
        _expect_exact_keys(solver, {"name", "version"}, "solver")
        resources = _expect_mapping(data["resources"], "resources")
        _expect_exact_keys(resources, {"per_sample_time_limit_s"}, "resources")
        return cls(
            schema_version=data["schema_version"],
            request_id=data["request_id"],
            key_position=data["key_position"],
            trail_position=data["trail_position"],
            repeat_count=data["repeat_count"],
            fixed_bit_count=data["fixed_bit_count"],
            sampling_seed=data["sampling_seed"],
            solver_name=solver["name"],
            solver_version=solver["version"],
            per_sample_time_limit_s=resources["per_sample_time_limit_s"],
        )

    @classmethod
    def from_json(cls, text: str) -> Gift64Stage3ProbabilityRequest:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise Gift64Stage3ProbabilityError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(value)


def load_gift64_stage3_probability_request(
    path: str | Path,
) -> Gift64Stage3ProbabilityRequest:
    return Gift64Stage3ProbabilityRequest.from_json(
        Path(path).read_text(encoding="utf-8")
    )


@dataclass(frozen=True)
class SubcubeProbabilityEstimate:
    """Descriptive estimate derived from complete same-size subcube counts."""

    completed_sample_count: int
    fixed_bit_count: int
    solution_count_total: int
    point_estimate: Decimal
    normal_95_lower: Decimal | None
    normal_95_upper: Decimal | None

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "completed_sample_count": self.completed_sample_count,
            "fixed_bit_count": self.fixed_bit_count,
            "solution_count_total": self.solution_count_total,
            "point_estimate": format(self.point_estimate, "f"),
            "normal_95_lower": (
                None if self.normal_95_lower is None else format(self.normal_95_lower, "f")
            ),
            "normal_95_upper": (
                None if self.normal_95_upper is None else format(self.normal_95_upper, "f")
            ),
        }


def estimate_subcube_probability(
    solution_counts: tuple[int, ...], *, fixed_bit_count: int
) -> SubcubeProbabilityEstimate:
    """Estimate probability as mean(count / 2^(64-fixed bits)).

    The optional interval is a descriptive normal approximation across complete
    deterministic pseudo-random subcube samples. It is not a certified PAC or
    exact counting bound.
    """

    _require_integer_range(fixed_bit_count, "fixed_bit_count", 1, 63)
    if not isinstance(solution_counts, tuple) or not solution_counts:
        raise Gift64Stage3ProbabilityError(
            "solution_counts must be a non-empty tuple"
        )
    subcube_size = 1 << (64 - fixed_bit_count)
    for index, value in enumerate(solution_counts):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise Gift64Stage3ProbabilityError(
                f"solution_counts[{index}] must be non-negative"
            )
        if value > subcube_size:
            raise Gift64Stage3ProbabilityError(
                f"solution_counts[{index}] exceeds the subcube size"
            )
    with localcontext() as context:
        context.prec = 50
        values = tuple(Decimal(value) / Decimal(subcube_size) for value in solution_counts)
        mean = sum(values) / Decimal(len(values))
        lower: Decimal | None = None
        upper: Decimal | None = None
        if len(values) >= 2:
            variance = sum((value - mean) ** 2 for value in values) / Decimal(
                len(values) - 1
            )
            margin = Decimal("1.96") * (variance / Decimal(len(values))).sqrt()
            lower = max(Decimal(0), mean - margin)
            upper = min(Decimal(1), mean + margin)
        return SubcubeProbabilityEstimate(
            completed_sample_count=len(values),
            fixed_bit_count=fixed_bit_count,
            solution_count_total=sum(solution_counts),
            point_estimate=mean,
            normal_95_lower=lower,
            normal_95_upper=upper,
        )
