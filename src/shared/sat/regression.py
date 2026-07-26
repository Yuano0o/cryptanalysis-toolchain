"""Normalized regression expectations for exact solver boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .contracts import (
    ContractValidationError,
    SolverRequest,
    SolverResult,
    SolverStatus,
    VerificationStatus,
)


REGRESSION_SCHEMA_VERSION = "solver-regression-expectation/v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ModelHashPolicy(str, Enum):
    EXACT = "exact"
    RECORD_ONLY = "record_only"


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} must be a non-empty string")
    return value


def _require_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ContractValidationError(
            f"{field_name} must be a lowercase 64-character SHA-256"
        )
    return value


def _require_exact_keys(
    value: Any, expected: set[str], field_name: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{field_name} must be an object")
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise ContractValidationError(
            f"{field_name} is missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ContractValidationError(
            f"{field_name} has unknown fields: {', '.join(sorted(unknown))}"
        )
    return value


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(str(item.value) for item in enum_type)
        raise ContractValidationError(
            f"{field_name} must be one of: {allowed}"
        ) from exc


@dataclass(frozen=True)
class RequiredResultSummary:
    status: SolverStatus
    definitive: bool
    objective_components: Mapping[str, int] | None
    satisfied_bound: bool | None
    verification_status: VerificationStatus
    exact_label_eligible: bool

    def __post_init__(self) -> None:
        if not isinstance(self.status, SolverStatus):
            raise ContractValidationError(
                "required.status must be a SolverStatus"
            )
        if not isinstance(self.definitive, bool):
            raise ContractValidationError("required.definitive must be boolean")
        if self.objective_components is not None:
            if not isinstance(self.objective_components, Mapping):
                raise ContractValidationError(
                    "required.objective_components must be an object or null"
                )
            for name, value in self.objective_components.items():
                _require_nonempty(name, "required objective component name")
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                ):
                    raise ContractValidationError(
                        f"required objective component {name} must be non-negative"
                    )
        if self.satisfied_bound is not None and not isinstance(
            self.satisfied_bound, bool
        ):
            raise ContractValidationError(
                "required.satisfied_bound must be boolean or null"
            )
        if self.status is SolverStatus.SAT:
            if (
                self.objective_components is None
                or self.satisfied_bound is None
            ):
                raise ContractValidationError(
                    "required SAT summary must include objective components "
                    "and bound status"
                )
        elif (
            self.objective_components is not None
            or self.satisfied_bound is not None
        ):
            raise ContractValidationError(
                "required non-SAT summary must not include objective semantics"
            )
        if not isinstance(self.verification_status, VerificationStatus):
            raise ContractValidationError(
                "required.verification_status must be a VerificationStatus"
            )
        if not isinstance(self.exact_label_eligible, bool):
            raise ContractValidationError(
                "required.exact_label_eligible must be boolean"
            )
        if self.exact_label_eligible and (
            not self.definitive
            or self.verification_status is not VerificationStatus.PASSED
        ):
            raise ContractValidationError(
                "required exact label must be definitive and independently verified"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "definitive": self.definitive,
            "objective_components": (
                None
                if self.objective_components is None
                else dict(sorted(self.objective_components.items()))
            ),
            "satisfied_bound": self.satisfied_bound,
            "verification_status": self.verification_status.value,
            "exact_label_eligible": self.exact_label_eligible,
        }

    @classmethod
    def from_dict(cls, value: Any) -> RequiredResultSummary:
        data = _require_exact_keys(
            value,
            {
                "status",
                "definitive",
                "objective_components",
                "satisfied_bound",
                "verification_status",
                "exact_label_eligible",
            },
            "required",
        )
        return cls(
            status=_enum(SolverStatus, data["status"], "required.status"),
            definitive=data["definitive"],
            objective_components=data["objective_components"],
            satisfied_bound=data["satisfied_bound"],
            verification_status=_enum(
                VerificationStatus,
                data["verification_status"],
                "required.verification_status",
            ),
            exact_label_eligible=data["exact_label_eligible"],
        )


@dataclass(frozen=True)
class SolverProvenance:
    name: str
    version: str
    threads: int

    def __post_init__(self) -> None:
        _require_nonempty(self.name, "provenance.solver.name")
        _require_nonempty(self.version, "provenance.solver.version")
        if (
            isinstance(self.threads, bool)
            or not isinstance(self.threads, int)
            or self.threads <= 0
        ):
            raise ContractValidationError(
                "provenance.solver.threads must be a positive integer"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "threads": self.threads,
        }

    @classmethod
    def from_dict(cls, value: Any) -> SolverProvenance:
        data = _require_exact_keys(
            value, {"name", "version", "threads"}, "provenance.solver"
        )
        return cls(**data)


@dataclass(frozen=True)
class RegressionExpectation:
    schema_version: str
    expectation_id: str
    request_id: str
    request_sha256: str
    adapter_version: str
    verifier_version: str
    source_sha256: str
    solver: SolverProvenance
    required: RequiredResultSummary
    observed_model_sha256: str
    model_hash_policy: ModelHashPolicy

    def __post_init__(self) -> None:
        if self.schema_version != REGRESSION_SCHEMA_VERSION:
            raise ContractValidationError(
                f"schema_version must be {REGRESSION_SCHEMA_VERSION}"
            )
        _require_nonempty(self.expectation_id, "expectation_id")
        _require_nonempty(self.request_id, "request_id")
        _require_sha256(self.request_sha256, "request_sha256")
        _require_nonempty(self.adapter_version, "adapter_version")
        _require_nonempty(self.verifier_version, "verifier_version")
        _require_sha256(self.source_sha256, "source_sha256")
        if not isinstance(self.solver, SolverProvenance):
            raise ContractValidationError(
                "solver must be a SolverProvenance"
            )
        if not isinstance(self.required, RequiredResultSummary):
            raise ContractValidationError(
                "required must be a RequiredResultSummary"
            )
        _require_sha256(
            self.observed_model_sha256, "observed_model_sha256"
        )
        if not isinstance(self.model_hash_policy, ModelHashPolicy):
            raise ContractValidationError(
                "model_hash_policy must be a ModelHashPolicy"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "expectation_id": self.expectation_id,
            "request_id": self.request_id,
            "request_sha256": self.request_sha256,
            "adapter_version": self.adapter_version,
            "verifier_version": self.verifier_version,
            "source_sha256": self.source_sha256,
            "solver": self.solver.to_dict(),
            "required": self.required.to_dict(),
            "observed_model_sha256": self.observed_model_sha256,
            "model_hash_policy": self.model_hash_policy.value,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> RegressionExpectation:
        data = _require_exact_keys(
            value,
            {
                "schema_version",
                "expectation_id",
                "request_id",
                "request_sha256",
                "adapter_version",
                "verifier_version",
                "source_sha256",
                "solver",
                "required",
                "observed_model_sha256",
                "model_hash_policy",
            },
            "regression expectation",
        )
        return cls(
            schema_version=data["schema_version"],
            expectation_id=data["expectation_id"],
            request_id=data["request_id"],
            request_sha256=data["request_sha256"],
            adapter_version=data["adapter_version"],
            verifier_version=data["verifier_version"],
            source_sha256=data["source_sha256"],
            solver=SolverProvenance.from_dict(data["solver"]),
            required=RequiredResultSummary.from_dict(data["required"]),
            observed_model_sha256=data["observed_model_sha256"],
            model_hash_policy=_enum(
                ModelHashPolicy,
                data["model_hash_policy"],
                "model_hash_policy",
            ),
        )

    @classmethod
    def from_json(cls, value: str) -> RegressionExpectation:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(
                f"invalid regression JSON: {exc}"
            ) from exc
        return cls.from_dict(decoded)


@dataclass(frozen=True)
class RegressionCheck:
    passed: bool
    failures: tuple[str, ...]
    advisories: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool):
            raise ContractValidationError("regression check passed must be boolean")
        for field_name in ("failures", "advisories"):
            value = getattr(self, field_name)
            if not isinstance(value, tuple) or not all(
                isinstance(item, str) for item in value
            ):
                raise ContractValidationError(
                    f"regression check {field_name} must be a tuple of strings"
                )
        if self.passed != (not self.failures):
            raise ContractValidationError(
                "regression check passed must equal absence of failures"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failures": list(self.failures),
            "advisories": list(self.advisories),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True
        ) + "\n"


def check_solver_regression(
    expectation: RegressionExpectation,
    request: SolverRequest,
    result: SolverResult,
) -> RegressionCheck:
    """Compare semantic invariants while ignoring timing and local paths."""

    failures: list[str] = []
    advisories: list[str] = []

    def require_equal(field_name: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            failures.append(
                f"{field_name}: expected {expected!r}, got {actual!r}"
            )

    require_equal("request.request_id", request.request_id, expectation.request_id)
    require_equal("result.request_id", result.request_id, expectation.request_id)
    require_equal(
        "request.sha256",
        hashlib.sha256(request.to_json().encode("utf-8")).hexdigest(),
        expectation.request_sha256,
    )
    require_equal(
        "request.source_sha256",
        request.source.source_sha256,
        expectation.source_sha256,
    )
    require_equal("request.solver.name", request.solver.name, expectation.solver.name)
    require_equal(
        "request.solver.version",
        request.solver.version,
        expectation.solver.version,
    )
    require_equal(
        "request.solver.threads",
        request.solver.threads,
        expectation.solver.threads,
    )
    require_equal("result.status", result.status, expectation.required.status)
    require_equal(
        "result.definitive",
        result.definitive,
        expectation.required.definitive,
    )
    require_equal(
        "result.objective_components",
        result.objective_components,
        expectation.required.objective_components,
    )
    require_equal(
        "result.satisfied_bound",
        result.satisfied_bound,
        expectation.required.satisfied_bound,
    )
    require_equal(
        "result.verification.status",
        result.verification.status,
        expectation.required.verification_status,
    )
    require_equal(
        "result.verification.verifier_version",
        result.verification.verifier_version,
        expectation.verifier_version,
    )
    require_equal(
        "result.exact_label_eligible",
        result.exact_label_eligible,
        expectation.required.exact_label_eligible,
    )
    require_equal(
        "result.solver_statistics.adapter_version",
        result.solver_statistics.get("adapter_version"),
        expectation.adapter_version,
    )

    actual_model_sha256 = (
        None if result.model is None else result.model.sha256
    )
    if actual_model_sha256 != expectation.observed_model_sha256:
        message = (
            "result.model.sha256: observed provenance "
            f"{expectation.observed_model_sha256!r}, got {actual_model_sha256!r}"
        )
        if expectation.model_hash_policy is ModelHashPolicy.EXACT:
            failures.append(message)
        else:
            advisories.append(
                message
                + "; ignored because explicit seed control is unavailable"
            )

    return RegressionCheck(
        passed=not failures,
        failures=tuple(failures),
        advisories=tuple(advisories),
    )


def load_regression_expectation(path: str | Path) -> RegressionExpectation:
    return RegressionExpectation.from_json(
        Path(path).read_text(encoding="utf-8")
    )
