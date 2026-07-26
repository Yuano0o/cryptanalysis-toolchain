"""Versioned contracts for exact affine constraints over GF(2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping


CONSTRAINT_SET_SCHEMA_VERSION = "constraint-set/v1"
CONSTRAINT_SPACE_COMPARISON_SCHEMA_VERSION = (
    "constraint-space-comparison/v1"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ConstraintValidationError(ValueError):
    """Raised when a constraint contract is incomplete or ambiguous."""


class ConstraintKind(str, Enum):
    LC = "LC"
    LNC = "LNC"
    LC_PLUS_LINEARIZED_RELATIONS = "LC_plus_linearized_relations"
    ADDITIONAL_EXACT = "additional_exact_constraint"
    UNCATEGORISED_NONLINEAR = "uncategorised_nonlinear_constraint"


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstraintValidationError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _require_nonnegative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConstraintValidationError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _require_positive_integer(value: Any, field_name: str) -> int:
    result = _require_nonnegative_integer(value, field_name)
    if result == 0:
        raise ConstraintValidationError(
            f"{field_name} must be greater than zero"
        )
    return result


def _require_bit(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or value not in (0, 1):
        raise ConstraintValidationError(f"{field_name} must be 0 or 1")
    return value


def _require_sha256(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ConstraintValidationError(
            f"{field_name} must be a lowercase SHA-256"
        )
    return value


def _expect_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConstraintValidationError(f"{field_name} must be an object")
    return value


def _expect_keys(
    data: Mapping[str, Any], required: set[str], context: str
) -> None:
    missing = required - set(data)
    unknown = set(data) - required
    if missing:
        raise ConstraintValidationError(
            f"{context} is missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ConstraintValidationError(
            f"{context} has unknown fields: {', '.join(sorted(unknown))}"
        )


@dataclass(frozen=True)
class GF2FixedTerm:
    name: str
    value: int

    def __post_init__(self) -> None:
        _require_nonempty(self.name, "fixed_term.name")
        _require_bit(self.value, "fixed_term.value")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}

    @classmethod
    def from_dict(cls, value: Any) -> GF2FixedTerm:
        data = _expect_mapping(value, "fixed_term")
        _expect_keys(data, {"name", "value"}, "fixed_term")
        return cls(name=data["name"], value=data["value"])


@dataclass(frozen=True)
class GF2Equation:
    variable_indices: tuple[int, ...]
    source_rhs: int
    source_round: int
    fixed_terms: tuple[GF2FixedTerm, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.variable_indices, tuple):
            raise ConstraintValidationError(
                "equation.variable_indices must be a tuple"
            )
        for index, value in enumerate(self.variable_indices):
            _require_nonnegative_integer(
                value, f"equation.variable_indices[{index}]"
            )
        if tuple(sorted(set(self.variable_indices))) != self.variable_indices:
            raise ConstraintValidationError(
                "equation.variable_indices must be sorted and unique"
            )
        _require_bit(self.source_rhs, "equation.source_rhs")
        _require_nonnegative_integer(
            self.source_round, "equation.source_round"
        )
        if not isinstance(self.fixed_terms, tuple) or not all(
            isinstance(item, GF2FixedTerm) for item in self.fixed_terms
        ):
            raise ConstraintValidationError(
                "equation.fixed_terms must contain GF2FixedTerm values"
            )
        names = tuple(item.name for item in self.fixed_terms)
        if tuple(sorted(set(names))) != names:
            raise ConstraintValidationError(
                "equation.fixed_terms must be sorted and unique by name"
            )

    @property
    def effective_rhs(self) -> int:
        value = self.source_rhs
        for term in self.fixed_terms:
            value ^= term.value
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_indices": list(self.variable_indices),
            "source_rhs": self.source_rhs,
            "source_round": self.source_round,
            "fixed_terms": [item.to_dict() for item in self.fixed_terms],
            "effective_rhs": self.effective_rhs,
        }

    @classmethod
    def from_dict(cls, value: Any) -> GF2Equation:
        data = _expect_mapping(value, "equation")
        _expect_keys(
            data,
            {
                "variable_indices",
                "source_rhs",
                "source_round",
                "fixed_terms",
                "effective_rhs",
            },
            "equation",
        )
        if not isinstance(data["variable_indices"], list):
            raise ConstraintValidationError(
                "equation.variable_indices must be an array"
            )
        if not isinstance(data["fixed_terms"], list):
            raise ConstraintValidationError(
                "equation.fixed_terms must be an array"
            )
        result = cls(
            variable_indices=tuple(data["variable_indices"]),
            source_rhs=data["source_rhs"],
            source_round=data["source_round"],
            fixed_terms=tuple(
                GF2FixedTerm.from_dict(item)
                for item in data["fixed_terms"]
            ),
        )
        if data["effective_rhs"] != result.effective_rhs:
            raise ConstraintValidationError(
                "equation.effective_rhs does not match its fixed terms"
            )
        return result


@dataclass(frozen=True)
class CanonicalGF2Row:
    variable_indices: tuple[int, ...]
    rhs: int

    def __post_init__(self) -> None:
        if not isinstance(self.variable_indices, tuple):
            raise ConstraintValidationError(
                "canonical row indices must be a tuple"
            )
        for index, value in enumerate(self.variable_indices):
            _require_nonnegative_integer(
                value, f"canonical_row.variable_indices[{index}]"
            )
        if tuple(sorted(set(self.variable_indices))) != self.variable_indices:
            raise ConstraintValidationError(
                "canonical row indices must be sorted and unique"
            )
        _require_bit(self.rhs, "canonical_row.rhs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_indices": list(self.variable_indices),
            "rhs": self.rhs,
        }


def canonicalize_gf2_equations(
    equations: tuple[GF2Equation, ...], variable_count: int
) -> tuple[CanonicalGF2Row, ...]:
    """Return deterministic RREF rows for the represented affine space."""

    _require_positive_integer(variable_count, "variable_count")
    if not isinstance(equations, tuple):
        raise ConstraintValidationError("equations must be a tuple")
    rows: list[list[int]] = []
    for equation in equations:
        if not isinstance(equation, GF2Equation):
            raise ConstraintValidationError(
                "equations must contain GF2Equation values"
            )
        if any(index >= variable_count for index in equation.variable_indices):
            raise ConstraintValidationError(
                "equation variable index is outside variable_count"
            )
        mask = sum(1 << index for index in equation.variable_indices)
        rows.append([mask, equation.effective_rhs])

    pivot_row = 0
    for column in range(variable_count):
        candidate = next(
            (
                row_index
                for row_index in range(pivot_row, len(rows))
                if (rows[row_index][0] >> column) & 1
            ),
            None,
        )
        if candidate is None:
            continue
        rows[pivot_row], rows[candidate] = rows[candidate], rows[pivot_row]
        pivot_mask, pivot_rhs = rows[pivot_row]
        for row_index, row in enumerate(rows):
            if row_index != pivot_row and ((row[0] >> column) & 1):
                row[0] ^= pivot_mask
                row[1] ^= pivot_rhs
        pivot_row += 1

    if any(mask == 0 and rhs == 1 for mask, rhs in rows):
        raise ConstraintValidationError(
            "constraint set is inconsistent over GF(2)"
        )
    nonzero = [(mask, rhs) for mask, rhs in rows if mask]
    nonzero.sort(key=lambda item: (item[0] & -item[0]).bit_length())
    return tuple(
        CanonicalGF2Row(
            variable_indices=tuple(
                index
                for index in range(variable_count)
                if (mask >> index) & 1
            ),
            rhs=rhs,
        )
        for mask, rhs in nonzero
    )


@dataclass(frozen=True)
class ConstraintSet:
    schema_version: str
    constraint_set_id: str
    constraint_kind: ConstraintKind
    field: str
    cipher: str
    variable_order_id: str
    variable_count: int
    source_artifact_sha256: str
    source_group_position: int
    source_trail_position: int
    source_round_start: int
    source_round_end: int
    derivation_method: str
    derivation_source_sha256: str
    exact_derivation: bool
    equations: tuple[GF2Equation, ...]

    def __post_init__(self) -> None:
        if self.schema_version != CONSTRAINT_SET_SCHEMA_VERSION:
            raise ConstraintValidationError(
                "unsupported constraint-set schema version"
            )
        _require_nonempty(self.constraint_set_id, "constraint_set_id")
        if not isinstance(self.constraint_kind, ConstraintKind):
            raise ConstraintValidationError(
                "constraint_kind must be a ConstraintKind"
            )
        if self.field != "GF(2)":
            raise ConstraintValidationError("field must be GF(2)")
        _require_nonempty(self.cipher, "cipher")
        _require_nonempty(self.variable_order_id, "variable_order_id")
        _require_positive_integer(self.variable_count, "variable_count")
        _require_sha256(
            self.source_artifact_sha256, "source_artifact_sha256"
        )
        _require_nonnegative_integer(
            self.source_group_position, "source_group_position"
        )
        _require_nonnegative_integer(
            self.source_trail_position, "source_trail_position"
        )
        _require_nonnegative_integer(
            self.source_round_start, "source_round_start"
        )
        _require_positive_integer(self.source_round_end, "source_round_end")
        if self.source_round_end <= self.source_round_start:
            raise ConstraintValidationError(
                "source_round_end must be greater than source_round_start"
            )
        _require_nonempty(self.derivation_method, "derivation_method")
        _require_sha256(
            self.derivation_source_sha256,
            "derivation_source_sha256",
        )
        if not isinstance(self.exact_derivation, bool):
            raise ConstraintValidationError(
                "exact_derivation must be a Boolean"
            )
        if not isinstance(self.equations, tuple) or not all(
            isinstance(item, GF2Equation) for item in self.equations
        ):
            raise ConstraintValidationError(
                "equations must contain GF2Equation values"
            )
        if any(
            not self.source_round_start
            <= item.source_round
            < self.source_round_end
            for item in self.equations
        ):
            raise ConstraintValidationError(
                "equation source round is outside the source interval"
            )
        canonicalize_gf2_equations(self.equations, self.variable_count)

    @property
    def canonical_rows(self) -> tuple[CanonicalGF2Row, ...]:
        return canonicalize_gf2_equations(
            self.equations, self.variable_count
        )

    @property
    def rank(self) -> int:
        return len(self.canonical_rows)

    @property
    def nullity(self) -> int:
        return self.variable_count - self.rank

    @property
    def semantic_sha256(self) -> str:
        semantic = {
            "field": self.field,
            "cipher": self.cipher,
            "variable_order_id": self.variable_order_id,
            "variable_count": self.variable_count,
            "canonical_rows": [
                item.to_dict() for item in self.canonical_rows
            ],
        }
        encoded = json.dumps(
            semantic,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()

    def is_semantically_equivalent(self, other: ConstraintSet) -> bool:
        return (
            isinstance(other, ConstraintSet)
            and self.semantic_sha256 == other.semantic_sha256
        )

    def implies(self, other: ConstraintSet) -> bool:
        """Return whether every solution of this set satisfies ``other``."""

        _validate_comparable_constraint_spaces(self, other)
        try:
            combined_rows = canonicalize_gf2_equations(
                self.equations + other.equations,
                self.variable_count,
            )
        except ConstraintValidationError:
            return False
        return len(combined_rows) == self.rank

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "constraint_set_id": self.constraint_set_id,
            "constraint_kind": self.constraint_kind.value,
            "field": self.field,
            "cipher": self.cipher,
            "variable_order_id": self.variable_order_id,
            "variable_count": self.variable_count,
            "source_artifact_sha256": self.source_artifact_sha256,
            "source_group_position": self.source_group_position,
            "source_trail_position": self.source_trail_position,
            "source_round_start": self.source_round_start,
            "source_round_end": self.source_round_end,
            "derivation_method": self.derivation_method,
            "derivation_source_sha256": self.derivation_source_sha256,
            "exact_derivation": self.exact_derivation,
            "equations": [item.to_dict() for item in self.equations],
            "canonical_rows": [
                item.to_dict() for item in self.canonical_rows
            ],
            "rank": self.rank,
            "nullity": self.nullity,
            "semantic_sha256": self.semantic_sha256,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> ConstraintSet:
        data = _expect_mapping(value, "constraint_set")
        _expect_keys(
            data,
            {
                "schema_version",
                "constraint_set_id",
                "constraint_kind",
                "field",
                "cipher",
                "variable_order_id",
                "variable_count",
                "source_artifact_sha256",
                "source_group_position",
                "source_trail_position",
                "source_round_start",
                "source_round_end",
                "derivation_method",
                "derivation_source_sha256",
                "exact_derivation",
                "equations",
                "canonical_rows",
                "rank",
                "nullity",
                "semantic_sha256",
            },
            "constraint_set",
        )
        if not isinstance(data["equations"], list):
            raise ConstraintValidationError(
                "constraint_set.equations must be an array"
            )
        try:
            kind = ConstraintKind(data["constraint_kind"])
        except (TypeError, ValueError) as exc:
            raise ConstraintValidationError(
                "unsupported constraint_kind"
            ) from exc
        result = cls(
            schema_version=data["schema_version"],
            constraint_set_id=data["constraint_set_id"],
            constraint_kind=kind,
            field=data["field"],
            cipher=data["cipher"],
            variable_order_id=data["variable_order_id"],
            variable_count=data["variable_count"],
            source_artifact_sha256=data["source_artifact_sha256"],
            source_group_position=data["source_group_position"],
            source_trail_position=data["source_trail_position"],
            source_round_start=data["source_round_start"],
            source_round_end=data["source_round_end"],
            derivation_method=data["derivation_method"],
            derivation_source_sha256=data["derivation_source_sha256"],
            exact_derivation=data["exact_derivation"],
            equations=tuple(
                GF2Equation.from_dict(item) for item in data["equations"]
            ),
        )
        expected = result.to_dict()
        for derived_field in (
            "canonical_rows",
            "rank",
            "nullity",
            "semantic_sha256",
        ):
            if data[derived_field] != expected[derived_field]:
                raise ConstraintValidationError(
                    f"constraint_set.{derived_field} is inconsistent"
                )
        return result

    @classmethod
    def from_json(cls, value: str) -> ConstraintSet:
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ConstraintValidationError(
                "constraint-set JSON is invalid"
            ) from exc
        return cls.from_dict(data)


def _validate_comparable_constraint_spaces(
    first: ConstraintSet,
    second: ConstraintSet,
) -> None:
    if not isinstance(first, ConstraintSet) or not isinstance(
        second, ConstraintSet
    ):
        raise ConstraintValidationError(
            "constraint-space comparison requires ConstraintSet values"
        )
    comparable_fields = (
        "field",
        "cipher",
        "variable_order_id",
        "variable_count",
        "source_artifact_sha256",
        "source_group_position",
        "source_trail_position",
        "source_round_start",
        "source_round_end",
    )
    mismatches = [
        field_name
        for field_name in comparable_fields
        if getattr(first, field_name) != getattr(second, field_name)
    ]
    if mismatches:
        raise ConstraintValidationError(
            "constraint spaces have incompatible metadata: "
            + ", ".join(mismatches)
        )


@dataclass(frozen=True)
class ConstraintSpaceComparison:
    """Stable algebraic relationship between a base and combined space."""

    schema_version: str
    source_artifact_sha256: str
    source_group_position: int
    source_trail_position: int
    base_constraint_set_id: str
    combined_constraint_set_id: str
    base_semantic_sha256: str
    combined_semantic_sha256: str
    base_rank: int
    combined_rank: int
    base_implied_by_combined: bool
    incremental_rank: int | None

    def __post_init__(self) -> None:
        if (
            self.schema_version
            != CONSTRAINT_SPACE_COMPARISON_SCHEMA_VERSION
        ):
            raise ConstraintValidationError(
                "unsupported constraint-space comparison schema version"
            )
        _require_sha256(
            self.source_artifact_sha256,
            "comparison.source_artifact_sha256",
        )
        _require_nonnegative_integer(
            self.source_group_position,
            "comparison.source_group_position",
        )
        _require_nonnegative_integer(
            self.source_trail_position,
            "comparison.source_trail_position",
        )
        _require_nonempty(
            self.base_constraint_set_id,
            "comparison.base_constraint_set_id",
        )
        _require_nonempty(
            self.combined_constraint_set_id,
            "comparison.combined_constraint_set_id",
        )
        _require_sha256(
            self.base_semantic_sha256,
            "comparison.base_semantic_sha256",
        )
        _require_sha256(
            self.combined_semantic_sha256,
            "comparison.combined_semantic_sha256",
        )
        _require_nonnegative_integer(
            self.base_rank, "comparison.base_rank"
        )
        _require_nonnegative_integer(
            self.combined_rank, "comparison.combined_rank"
        )
        if not isinstance(self.base_implied_by_combined, bool):
            raise ConstraintValidationError(
                "comparison.base_implied_by_combined must be a Boolean"
            )
        if self.incremental_rank is not None:
            _require_nonnegative_integer(
                self.incremental_rank,
                "comparison.incremental_rank",
            )
        expected_incremental_rank = (
            self.combined_rank - self.base_rank
            if self.base_implied_by_combined
            else None
        )
        if self.incremental_rank != expected_incremental_rank:
            raise ConstraintValidationError(
                "comparison.incremental_rank is inconsistent"
            )
        if self.base_implied_by_combined and self.combined_rank < self.base_rank:
            raise ConstraintValidationError(
                "an implying combined space cannot have lower rank"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_artifact_sha256": self.source_artifact_sha256,
            "source_group_position": self.source_group_position,
            "source_trail_position": self.source_trail_position,
            "base_constraint_set_id": self.base_constraint_set_id,
            "combined_constraint_set_id": self.combined_constraint_set_id,
            "base_semantic_sha256": self.base_semantic_sha256,
            "combined_semantic_sha256": self.combined_semantic_sha256,
            "base_rank": self.base_rank,
            "combined_rank": self.combined_rank,
            "base_implied_by_combined": self.base_implied_by_combined,
            "incremental_rank": self.incremental_rank,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> ConstraintSpaceComparison:
        data = _expect_mapping(value, "constraint_space_comparison")
        _expect_keys(
            data,
            {
                "schema_version",
                "source_artifact_sha256",
                "source_group_position",
                "source_trail_position",
                "base_constraint_set_id",
                "combined_constraint_set_id",
                "base_semantic_sha256",
                "combined_semantic_sha256",
                "base_rank",
                "combined_rank",
                "base_implied_by_combined",
                "incremental_rank",
            },
            "constraint_space_comparison",
        )
        return cls(
            schema_version=data["schema_version"],
            source_artifact_sha256=data["source_artifact_sha256"],
            source_group_position=data["source_group_position"],
            source_trail_position=data["source_trail_position"],
            base_constraint_set_id=data["base_constraint_set_id"],
            combined_constraint_set_id=(
                data["combined_constraint_set_id"]
            ),
            base_semantic_sha256=data["base_semantic_sha256"],
            combined_semantic_sha256=data["combined_semantic_sha256"],
            base_rank=data["base_rank"],
            combined_rank=data["combined_rank"],
            base_implied_by_combined=data["base_implied_by_combined"],
            incremental_rank=data["incremental_rank"],
        )

    @classmethod
    def from_json(cls, value: str) -> ConstraintSpaceComparison:
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ConstraintValidationError(
                "constraint-space comparison JSON is invalid"
            ) from exc
        return cls.from_dict(data)


def compare_constraint_spaces(
    *,
    base: ConstraintSet,
    combined: ConstraintSet,
) -> ConstraintSpaceComparison:
    """Compare a combined affine space against its required base space."""

    _validate_comparable_constraint_spaces(base, combined)
    base_implied = combined.implies(base)
    return ConstraintSpaceComparison(
        schema_version=CONSTRAINT_SPACE_COMPARISON_SCHEMA_VERSION,
        source_artifact_sha256=base.source_artifact_sha256,
        source_group_position=base.source_group_position,
        source_trail_position=base.source_trail_position,
        base_constraint_set_id=base.constraint_set_id,
        combined_constraint_set_id=combined.constraint_set_id,
        base_semantic_sha256=base.semantic_sha256,
        combined_semantic_sha256=combined.semantic_sha256,
        base_rank=base.rank,
        combined_rank=combined.rank,
        base_implied_by_combined=base_implied,
        incremental_rank=(
            combined.rank - base.rank if base_implied else None
        ),
    )
