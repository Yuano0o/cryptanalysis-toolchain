"""Shared contracts used by the exact pipeline and optional ML guidance."""

from .constraints import (
    CONSTRAINT_SET_SCHEMA_VERSION,
    CanonicalGF2Row,
    ConstraintKind,
    ConstraintSet,
    ConstraintValidationError,
    GF2Equation,
    GF2FixedTerm,
    canonicalize_gf2_equations,
)

__all__ = [
    "CONSTRAINT_SET_SCHEMA_VERSION",
    "CanonicalGF2Row",
    "ConstraintKind",
    "ConstraintSet",
    "ConstraintValidationError",
    "GF2Equation",
    "GF2FixedTerm",
    "canonicalize_gf2_equations",
]
