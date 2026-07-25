"""Strict, versioned data contracts for exact SAT boundaries.

The contracts use only the Python standard library. They intentionally separate
"representable" requests from "execution-ready" requests so static experiment
configuration does not need fake CNF hashes or a guessed solver version.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
import json
from pathlib import Path, PurePath
import re
from typing import Any, Mapping


REQUEST_SCHEMA_VERSION = "solver-request/v1"
RESULT_SCHEMA_VERSION = "solver-result/v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_JSON_SCALAR = str | int | float | bool | None


class ContractValidationError(ValueError):
    """Raised when contract data is incomplete, inconsistent, or ambiguous."""


class ProblemKind(str, Enum):
    DIFFERENTIAL_CHARACTERISTIC = "differential_characteristic"
    LINEAR_CHARACTERISTIC = "linear_characteristic"
    TRAIL_COEXISTENCE = "trail_coexistence"


class ObjectiveKind(str, Enum):
    ACTIVE_SBOXES = "active_sboxes"
    SPLIT_PROBABILITY_WEIGHT = "split_probability_weight"
    PROBABILITY = "probability"
    BIAS = "bias"
    COEXISTENCE = "coexistence"


class Comparison(str, Enum):
    LT = "<"
    LE = "<="
    EQ = "="
    GE = ">="


class SolverStatus(str, Enum):
    SAT = "SAT"
    UNSAT = "UNSAT"
    UNKNOWN = "UNKNOWN"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class VerificationStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


def _expect_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{field_name} must be an object")
    return value


def _expect_keys(
    data: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
    context: str,
) -> None:
    optional = optional or set()
    missing = required - set(data)
    unknown = set(data) - required - optional
    if missing:
        raise ContractValidationError(
            f"{context} is missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ContractValidationError(
            f"{context} has unknown fields: {', '.join(sorted(unknown))}"
        )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} must be a non-empty string")
    return value


def _require_nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractValidationError(f"{field_name} must be a non-negative integer")
    return value


def _require_positive_int(value: Any, field_name: str) -> int:
    result = _require_nonnegative_int(value, field_name)
    if result == 0:
        raise ContractValidationError(f"{field_name} must be greater than zero")
    return result


def _require_nonnegative_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ContractValidationError(f"{field_name} must be a non-negative number")
    return float(value)


def _require_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ContractValidationError(
            f"{field_name} must be a lowercase 64-character SHA-256"
        )
    return value


def _require_relative_path(
    value: Any, field_name: str, *, allow_parent: bool = False
) -> str:
    path = _require_nonempty(value, field_name)
    parsed = PurePath(path)
    if parsed.is_absolute():
        raise ContractValidationError(f"{field_name} must be machine-independent")
    if not allow_parent and ".." in parsed.parts:
        raise ContractValidationError(f"{field_name} must not escape its artifact root")
    return path


def _optional_hex(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or not _HEX_RE.fullmatch(value):
        raise ContractValidationError(f"{field_name} must be hexadecimal or null")
    return value.lower()


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(str(item.value) for item in enum_type)
        raise ContractValidationError(
            f"{field_name} must be one of: {allowed}"
        ) from exc


@dataclass(frozen=True)
class SourceReference:
    repository: str
    revision: str
    entry_point: str
    source_sha256: str
    archive_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_relative_path(
            self.repository, "source.repository", allow_parent=True
        )
        if not isinstance(self.revision, str) or not _REVISION_RE.fullmatch(
            self.revision
        ):
            raise ContractValidationError(
                "source.revision must be a lowercase 40-character Git revision"
            )
        _require_relative_path(self.entry_point, "source.entry_point")
        _require_sha256(self.source_sha256, "source.source_sha256")
        if self.archive_sha256 is not None:
            _require_sha256(self.archive_sha256, "source.archive_sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "revision": self.revision,
            "entry_point": self.entry_point,
            "source_sha256": self.source_sha256,
            "archive_sha256": self.archive_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> SourceReference:
        data = _expect_mapping(value, "source")
        _expect_keys(
            data,
            required={
                "repository",
                "revision",
                "entry_point",
                "source_sha256",
                "archive_sha256",
            },
            context="source",
        )
        return cls(**data)


@dataclass(frozen=True)
class CipherSpec:
    name: str
    variant: str
    analysis_kind: str
    round_start: int
    round_end: int
    state_layout_id: str
    bit_order_id: str
    nibble_order_id: str

    def __post_init__(self) -> None:
        _require_nonempty(self.name, "cipher.name")
        _require_nonempty(self.variant, "cipher.variant")
        _require_nonempty(self.analysis_kind, "cipher.analysis_kind")
        _require_nonnegative_int(self.round_start, "cipher.round_start")
        _require_positive_int(self.round_end, "cipher.round_end")
        if self.round_end <= self.round_start:
            raise ContractValidationError(
                "cipher.round_end must be greater than cipher.round_start"
            )
        _require_nonempty(self.state_layout_id, "cipher.state_layout_id")
        _require_nonempty(self.bit_order_id, "cipher.bit_order_id")
        _require_nonempty(self.nibble_order_id, "cipher.nibble_order_id")

    @property
    def round_count(self) -> int:
        return self.round_end - self.round_start

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "variant": self.variant,
            "analysis_kind": self.analysis_kind,
            "round_start": self.round_start,
            "round_end": self.round_end,
            "round_count": self.round_count,
            "state_layout_id": self.state_layout_id,
            "bit_order_id": self.bit_order_id,
            "nibble_order_id": self.nibble_order_id,
        }

    @classmethod
    def from_dict(cls, value: Any) -> CipherSpec:
        data = _expect_mapping(value, "cipher")
        _expect_keys(
            data,
            required={
                "name",
                "variant",
                "analysis_kind",
                "round_start",
                "round_end",
                "round_count",
                "state_layout_id",
                "bit_order_id",
                "nibble_order_id",
            },
            context="cipher",
        )
        spec = cls(
            name=data["name"],
            variant=data["variant"],
            analysis_kind=data["analysis_kind"],
            round_start=data["round_start"],
            round_end=data["round_end"],
            state_layout_id=data["state_layout_id"],
            bit_order_id=data["bit_order_id"],
            nibble_order_id=data["nibble_order_id"],
        )
        if data["round_count"] != spec.round_count:
            raise ContractValidationError(
                "cipher.round_count does not match round_start/round_end"
            )
        return spec


@dataclass(frozen=True)
class BoundComponent:
    name: str
    unit: str
    bound: int

    def __post_init__(self) -> None:
        _require_nonempty(self.name, "objective.components[].name")
        _require_nonnegative_int(self.bound, "objective.components[].bound")
        try:
            unit = Decimal(self.unit)
        except (InvalidOperation, TypeError) as exc:
            raise ContractValidationError(
                "objective.components[].unit must be an exact decimal string"
            ) from exc
        if unit <= 0:
            raise ContractValidationError(
                "objective.components[].unit must be greater than zero"
            )

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "unit": self.unit, "bound": self.bound}

    @classmethod
    def from_dict(cls, value: Any) -> BoundComponent:
        data = _expect_mapping(value, "objective component")
        _expect_keys(
            data,
            required={"name", "unit", "bound"},
            context="objective component",
        )
        return cls(**data)


@dataclass(frozen=True)
class ObjectiveSpec:
    kind: ObjectiveKind
    comparison: Comparison
    combination: str
    components: tuple[BoundComponent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ObjectiveKind):
            raise ContractValidationError("objective.kind must be an ObjectiveKind")
        if not isinstance(self.comparison, Comparison):
            raise ContractValidationError(
                "objective.comparison must be a Comparison"
            )
        if self.combination not in {"componentwise", "weighted_sum"}:
            raise ContractValidationError(
                "objective.combination must be componentwise or weighted_sum"
            )
        if not isinstance(self.components, tuple) or not self.components:
            raise ContractValidationError("objective.components must not be empty")
        if not all(
            isinstance(component, BoundComponent) for component in self.components
        ):
            raise ContractValidationError(
                "objective.components must contain BoundComponent values"
            )
        names = [component.name for component in self.components]
        if len(names) != len(set(names)):
            raise ContractValidationError("objective component names must be unique")
        if (
            self.kind is ObjectiveKind.SPLIT_PROBABILITY_WEIGHT
            and self.combination != "componentwise"
        ):
            raise ContractValidationError(
                "split_probability_weight must preserve componentwise bounds"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "comparison": self.comparison.value,
            "combination": self.combination,
            "components": [component.to_dict() for component in self.components],
        }

    @classmethod
    def from_dict(cls, value: Any) -> ObjectiveSpec:
        data = _expect_mapping(value, "objective")
        _expect_keys(
            data,
            required={"kind", "comparison", "combination", "components"},
            context="objective",
        )
        if not isinstance(data["components"], list):
            raise ContractValidationError("objective.components must be an array")
        return cls(
            kind=_enum(ObjectiveKind, data["kind"], "objective.kind"),
            comparison=_enum(
                Comparison, data["comparison"], "objective.comparison"
            ),
            combination=data["combination"],
            components=tuple(
                BoundComponent.from_dict(item) for item in data["components"]
            ),
        )


@dataclass(frozen=True)
class FixedDifferences:
    input: str | None
    output: str | None
    key: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "input", _optional_hex(self.input, "fixed.input"))
        object.__setattr__(self, "output", _optional_hex(self.output, "fixed.output"))
        object.__setattr__(self, "key", _optional_hex(self.key, "fixed.key"))

    def to_dict(self) -> dict[str, Any]:
        return {"input": self.input, "output": self.output, "key": self.key}

    @classmethod
    def from_dict(cls, value: Any) -> FixedDifferences:
        data = _expect_mapping(value, "fixed_differences")
        _expect_keys(
            data,
            required={"input", "output", "key"},
            context="fixed_differences",
        )
        return cls(**data)


@dataclass(frozen=True)
class ArtifactReference:
    relative_path: str
    sha256: str
    media_type: str
    byte_size: int

    def __post_init__(self) -> None:
        _require_relative_path(self.relative_path, "artifact.relative_path")
        _require_sha256(self.sha256, "artifact.sha256")
        _require_nonempty(self.media_type, "artifact.media_type")
        _require_nonnegative_int(self.byte_size, "artifact.byte_size")

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "byte_size": self.byte_size,
        }

    @classmethod
    def from_dict(cls, value: Any) -> ArtifactReference:
        data = _expect_mapping(value, "artifact")
        _expect_keys(
            data,
            required={"relative_path", "sha256", "media_type", "byte_size"},
            context="artifact",
        )
        return cls(**data)


@dataclass(frozen=True)
class SolverSpec:
    name: str
    version: str | None
    threads: int
    options: Mapping[str, _JSON_SCALAR] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.name, "solver.name")
        if self.version is not None:
            _require_nonempty(self.version, "solver.version")
        _require_positive_int(self.threads, "solver.threads")
        if not isinstance(self.options, Mapping):
            raise ContractValidationError("solver.options must be an object")
        for key, value in self.options.items():
            _require_nonempty(key, "solver option name")
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ContractValidationError(
                    f"solver option {key} must be a JSON scalar"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "threads": self.threads,
            "options": dict(sorted(self.options.items())),
        }

    @classmethod
    def from_dict(cls, value: Any) -> SolverSpec:
        data = _expect_mapping(value, "solver")
        _expect_keys(
            data,
            required={"name", "version", "threads", "options"},
            context="solver",
        )
        return cls(**data)


@dataclass(frozen=True)
class ResourceLimits:
    time_limit_s: float | None
    memory_limit_mb: int | None

    def __post_init__(self) -> None:
        if self.time_limit_s is not None:
            _require_nonnegative_number(
                self.time_limit_s, "resources.time_limit_s"
            )
        if self.memory_limit_mb is not None:
            _require_positive_int(
                self.memory_limit_mb, "resources.memory_limit_mb"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_limit_s": self.time_limit_s,
            "memory_limit_mb": self.memory_limit_mb,
        }

    @classmethod
    def from_dict(cls, value: Any) -> ResourceLimits:
        data = _expect_mapping(value, "resources")
        _expect_keys(
            data,
            required={"time_limit_s", "memory_limit_mb"},
            context="resources",
        )
        return cls(**data)


@dataclass(frozen=True)
class ExpectedStaticCounts:
    variables: int
    clauses: int
    solver_calls: int

    def __post_init__(self) -> None:
        _require_positive_int(self.variables, "expected_static_counts.variables")
        _require_positive_int(self.clauses, "expected_static_counts.clauses")
        _require_positive_int(
            self.solver_calls, "expected_static_counts.solver_calls"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": self.variables,
            "clauses": self.clauses,
            "solver_calls": self.solver_calls,
        }

    @classmethod
    def from_dict(cls, value: Any) -> ExpectedStaticCounts:
        data = _expect_mapping(value, "expected_static_counts")
        _expect_keys(
            data,
            required={"variables", "clauses", "solver_calls"},
            context="expected_static_counts",
        )
        return cls(**data)


@dataclass(frozen=True)
class SolverRequest:
    schema_version: str
    request_id: str
    problem_kind: ProblemKind
    encoding_version: str
    source: SourceReference
    cipher: CipherSpec
    objective: ObjectiveSpec
    fixed_differences: FixedDifferences
    assumptions: tuple[int, ...]
    instance: ArtifactReference | None
    variable_map: ArtifactReference | None
    solver: SolverSpec
    resources: ResourceLimits
    expected_static_counts: ExpectedStaticCounts
    seed: int

    def __post_init__(self) -> None:
        if self.schema_version != REQUEST_SCHEMA_VERSION:
            raise ContractValidationError(
                f"schema_version must be {REQUEST_SCHEMA_VERSION}"
            )
        _require_nonempty(self.request_id, "request_id")
        if not isinstance(self.problem_kind, ProblemKind):
            raise ContractValidationError("problem_kind must be a ProblemKind")
        _require_nonempty(self.encoding_version, "encoding_version")
        nested_contracts = (
            ("source", self.source, SourceReference),
            ("cipher", self.cipher, CipherSpec),
            ("objective", self.objective, ObjectiveSpec),
            ("fixed_differences", self.fixed_differences, FixedDifferences),
            ("solver", self.solver, SolverSpec),
            ("resources", self.resources, ResourceLimits),
            (
                "expected_static_counts",
                self.expected_static_counts,
                ExpectedStaticCounts,
            ),
        )
        for field_name, value, expected_type in nested_contracts:
            if not isinstance(value, expected_type):
                raise ContractValidationError(
                    f"{field_name} must be a {expected_type.__name__}"
                )
        if self.instance is not None and not isinstance(
            self.instance, ArtifactReference
        ):
            raise ContractValidationError(
                "instance must be an ArtifactReference or null"
            )
        if self.variable_map is not None and not isinstance(
            self.variable_map, ArtifactReference
        ):
            raise ContractValidationError(
                "variable_map must be an ArtifactReference or null"
            )
        if not isinstance(self.assumptions, tuple):
            raise ContractValidationError("assumptions must be a tuple")
        for literal in self.assumptions:
            if isinstance(literal, bool) or not isinstance(literal, int) or literal == 0:
                raise ContractValidationError(
                    "assumptions must contain non-zero integer literals"
                )
        _require_nonnegative_int(self.seed, "seed")

    @property
    def execution_ready(self) -> bool:
        return (
            self.instance is not None
            and self.variable_map is not None
            and self.solver.version is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "problem_kind": self.problem_kind.value,
            "encoding_version": self.encoding_version,
            "source": self.source.to_dict(),
            "cipher": self.cipher.to_dict(),
            "objective": self.objective.to_dict(),
            "fixed_differences": self.fixed_differences.to_dict(),
            "assumptions": list(self.assumptions),
            "instance": None if self.instance is None else self.instance.to_dict(),
            "variable_map": (
                None if self.variable_map is None else self.variable_map.to_dict()
            ),
            "solver": self.solver.to_dict(),
            "resources": self.resources.to_dict(),
            "expected_static_counts": self.expected_static_counts.to_dict(),
            "seed": self.seed,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> SolverRequest:
        data = _expect_mapping(value, "solver request")
        _expect_keys(
            data,
            required={
                "schema_version",
                "request_id",
                "problem_kind",
                "encoding_version",
                "source",
                "cipher",
                "objective",
                "fixed_differences",
                "assumptions",
                "instance",
                "variable_map",
                "solver",
                "resources",
                "expected_static_counts",
                "seed",
            },
            context="solver request",
        )
        if not isinstance(data["assumptions"], list):
            raise ContractValidationError("assumptions must be an array")
        return cls(
            schema_version=data["schema_version"],
            request_id=data["request_id"],
            problem_kind=_enum(
                ProblemKind, data["problem_kind"], "problem_kind"
            ),
            encoding_version=data["encoding_version"],
            source=SourceReference.from_dict(data["source"]),
            cipher=CipherSpec.from_dict(data["cipher"]),
            objective=ObjectiveSpec.from_dict(data["objective"]),
            fixed_differences=FixedDifferences.from_dict(
                data["fixed_differences"]
            ),
            assumptions=tuple(data["assumptions"]),
            instance=(
                None
                if data["instance"] is None
                else ArtifactReference.from_dict(data["instance"])
            ),
            variable_map=(
                None
                if data["variable_map"] is None
                else ArtifactReference.from_dict(data["variable_map"])
            ),
            solver=SolverSpec.from_dict(data["solver"]),
            resources=ResourceLimits.from_dict(data["resources"]),
            expected_static_counts=ExpectedStaticCounts.from_dict(
                data["expected_static_counts"]
            ),
            seed=data["seed"],
        )

    @classmethod
    def from_json(cls, value: str) -> SolverRequest:
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(data)


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    verifier_version: str | None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, VerificationStatus):
            raise ContractValidationError(
                "verification.status must be a VerificationStatus"
            )
        if self.status is VerificationStatus.NOT_RUN:
            if self.verifier_version is not None:
                raise ContractValidationError(
                    "verification.verifier_version must be null when not_run"
                )
        else:
            _require_nonempty(
                self.verifier_version, "verification.verifier_version"
            )
        if not isinstance(self.diagnostics, tuple) or not all(
            isinstance(item, str) for item in self.diagnostics
        ):
            raise ContractValidationError(
                "verification.diagnostics must be a tuple of strings"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "verifier_version": self.verifier_version,
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, value: Any) -> VerificationResult:
        data = _expect_mapping(value, "verification")
        _expect_keys(
            data,
            required={"status", "verifier_version", "diagnostics"},
            context="verification",
        )
        if not isinstance(data["diagnostics"], list):
            raise ContractValidationError(
                "verification.diagnostics must be an array"
            )
        return cls(
            status=_enum(
                VerificationStatus, data["status"], "verification.status"
            ),
            verifier_version=data["verifier_version"],
            diagnostics=tuple(data["diagnostics"]),
        )


@dataclass(frozen=True)
class SolverResult:
    schema_version: str
    result_id: str
    request_id: str
    status: SolverStatus
    definitive: bool
    model: ArtifactReference | None
    proof: ArtifactReference | None
    objective_components: Mapping[str, int] | None
    satisfied_bound: bool | None
    wall_time_s: float
    cpu_time_s: float
    peak_memory_mb: int | None
    solver_statistics: Mapping[str, _JSON_SCALAR]
    exit_code: int | None
    parse_diagnostics: tuple[str, ...]
    verification: VerificationResult
    exact_label_eligible: bool
    exact_label_reason: str

    def __post_init__(self) -> None:
        if self.schema_version != RESULT_SCHEMA_VERSION:
            raise ContractValidationError(
                f"schema_version must be {RESULT_SCHEMA_VERSION}"
            )
        _require_nonempty(self.result_id, "result_id")
        _require_nonempty(self.request_id, "request_id")
        if not isinstance(self.status, SolverStatus):
            raise ContractValidationError("status must be a SolverStatus")
        if self.model is not None and not isinstance(
            self.model, ArtifactReference
        ):
            raise ContractValidationError(
                "model must be an ArtifactReference or null"
            )
        if self.proof is not None and not isinstance(
            self.proof, ArtifactReference
        ):
            raise ContractValidationError(
                "proof must be an ArtifactReference or null"
            )
        if not isinstance(self.verification, VerificationResult):
            raise ContractValidationError(
                "verification must be a VerificationResult"
            )
        if not isinstance(self.definitive, bool):
            raise ContractValidationError("definitive must be boolean")
        if self.definitive and self.status not in {
            SolverStatus.SAT,
            SolverStatus.UNSAT,
        }:
            raise ContractValidationError(
                "only SAT or UNSAT results may be definitive"
            )
        if self.status is SolverStatus.SAT and self.model is None:
            raise ContractValidationError("SAT result must reference a model")
        if self.status is not SolverStatus.SAT and self.model is not None:
            raise ContractValidationError("only SAT result may reference a model")
        if self.status is not SolverStatus.UNSAT and self.proof is not None:
            raise ContractValidationError("only UNSAT result may reference a proof")
        if self.status is SolverStatus.SAT:
            if self.objective_components is None or self.satisfied_bound is None:
                raise ContractValidationError(
                    "SAT result must report objective components and bound status"
                )
        elif (
            self.objective_components is not None or self.satisfied_bound is not None
        ):
            raise ContractValidationError(
                "non-SAT result must not report a satisfied objective"
            )
        if self.objective_components is not None:
            if not isinstance(self.objective_components, Mapping):
                raise ContractValidationError(
                    "objective_components must be an object or null"
                )
            for name, value in self.objective_components.items():
                _require_nonempty(name, "objective component name")
                _require_nonnegative_int(value, f"objective_components.{name}")
        if self.satisfied_bound is not None and not isinstance(
            self.satisfied_bound, bool
        ):
            raise ContractValidationError("satisfied_bound must be boolean or null")
        _require_nonnegative_number(self.wall_time_s, "wall_time_s")
        _require_nonnegative_number(self.cpu_time_s, "cpu_time_s")
        if self.peak_memory_mb is not None:
            _require_nonnegative_int(self.peak_memory_mb, "peak_memory_mb")
        if not isinstance(self.solver_statistics, Mapping):
            raise ContractValidationError("solver_statistics must be an object")
        for name, value in self.solver_statistics.items():
            _require_nonempty(name, "solver statistic name")
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ContractValidationError(
                    f"solver statistic {name} must be a JSON scalar"
                )
        if self.exit_code is not None and (
            isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int)
        ):
            raise ContractValidationError("exit_code must be an integer or null")
        if not isinstance(self.parse_diagnostics, tuple) or not all(
            isinstance(item, str) for item in self.parse_diagnostics
        ):
            raise ContractValidationError(
                "parse_diagnostics must be a tuple of strings"
            )
        if not isinstance(self.exact_label_eligible, bool):
            raise ContractValidationError("exact_label_eligible must be boolean")
        _require_nonempty(self.exact_label_reason, "exact_label_reason")
        if self.exact_label_eligible and (
            not self.definitive
            or self.verification.status is not VerificationStatus.PASSED
        ):
            raise ContractValidationError(
                "exact ML labels require a definitive, independently verified result"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "result_id": self.result_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "definitive": self.definitive,
            "model": None if self.model is None else self.model.to_dict(),
            "proof": None if self.proof is None else self.proof.to_dict(),
            "objective_components": (
                None
                if self.objective_components is None
                else dict(sorted(self.objective_components.items()))
            ),
            "satisfied_bound": self.satisfied_bound,
            "wall_time_s": self.wall_time_s,
            "cpu_time_s": self.cpu_time_s,
            "peak_memory_mb": self.peak_memory_mb,
            "solver_statistics": dict(sorted(self.solver_statistics.items())),
            "exit_code": self.exit_code,
            "parse_diagnostics": list(self.parse_diagnostics),
            "verification": self.verification.to_dict(),
            "exact_label_eligible": self.exact_label_eligible,
            "exact_label_reason": self.exact_label_reason,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> SolverResult:
        data = _expect_mapping(value, "solver result")
        _expect_keys(
            data,
            required={
                "schema_version",
                "result_id",
                "request_id",
                "status",
                "definitive",
                "model",
                "proof",
                "objective_components",
                "satisfied_bound",
                "wall_time_s",
                "cpu_time_s",
                "peak_memory_mb",
                "solver_statistics",
                "exit_code",
                "parse_diagnostics",
                "verification",
                "exact_label_eligible",
                "exact_label_reason",
            },
            context="solver result",
        )
        if not isinstance(data["parse_diagnostics"], list):
            raise ContractValidationError("parse_diagnostics must be an array")
        return cls(
            schema_version=data["schema_version"],
            result_id=data["result_id"],
            request_id=data["request_id"],
            status=_enum(SolverStatus, data["status"], "status"),
            definitive=data["definitive"],
            model=(
                None
                if data["model"] is None
                else ArtifactReference.from_dict(data["model"])
            ),
            proof=(
                None
                if data["proof"] is None
                else ArtifactReference.from_dict(data["proof"])
            ),
            objective_components=data["objective_components"],
            satisfied_bound=data["satisfied_bound"],
            wall_time_s=data["wall_time_s"],
            cpu_time_s=data["cpu_time_s"],
            peak_memory_mb=data["peak_memory_mb"],
            solver_statistics=data["solver_statistics"],
            exit_code=data["exit_code"],
            parse_diagnostics=tuple(data["parse_diagnostics"]),
            verification=VerificationResult.from_dict(data["verification"]),
            exact_label_eligible=data["exact_label_eligible"],
            exact_label_reason=data["exact_label_reason"],
        )

    @classmethod
    def from_json(cls, value: str) -> SolverResult:
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"invalid JSON: {exc}") from exc
        return cls.from_dict(data)


def load_solver_request(path: str | Path) -> SolverRequest:
    """Load and validate a solver request without executing a solver."""

    return SolverRequest.from_json(Path(path).read_text(encoding="utf-8"))
