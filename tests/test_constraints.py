from __future__ import annotations

import unittest

from shared.constraints import (
    CONSTRAINT_SET_SCHEMA_VERSION,
    ConstraintKind,
    ConstraintSet,
    ConstraintValidationError,
    GF2Equation,
    GF2FixedTerm,
)


def constraint_set(
    identifier: str,
    equations: tuple[GF2Equation, ...],
) -> ConstraintSet:
    return ConstraintSet(
        schema_version=CONSTRAINT_SET_SCHEMA_VERSION,
        constraint_set_id=identifier,
        constraint_kind=ConstraintKind.LC,
        field="GF(2)",
        cipher="test-cipher",
        variable_order_id="test-bits/v1",
        variable_count=4,
        source_artifact_sha256="0" * 64,
        source_group_position=0,
        source_trail_position=0,
        source_round_start=5,
        source_round_end=7,
        derivation_method="handwritten test fixture",
        derivation_source_sha256="1" * 64,
        exact_derivation=True,
        equations=equations,
    )


class ConstraintSetTests(unittest.TestCase):
    def test_different_bases_have_the_same_semantic_hash(self) -> None:
        first = constraint_set(
            "first",
            (
                GF2Equation((0, 1), 0, 5),
                GF2Equation((1,), 1, 5),
            ),
        )
        second = constraint_set(
            "second",
            (
                GF2Equation((1,), 1, 6),
                GF2Equation((0,), 1, 6),
            ),
        )

        self.assertTrue(first.is_semantically_equivalent(second))
        self.assertEqual(first.semantic_sha256, second.semantic_sha256)
        self.assertEqual(first.rank, 2)
        self.assertEqual(first.nullity, 2)

    def test_fixed_terms_are_folded_into_the_effective_rhs(self) -> None:
        equation = GF2Equation(
            variable_indices=(0,),
            source_rhs=0,
            source_round=5,
            fixed_terms=(GF2FixedTerm("unit", 1),),
        )
        result = constraint_set("fixed", (equation,))

        self.assertEqual(equation.effective_rhs, 1)
        self.assertEqual(result.canonical_rows[0].rhs, 1)

    def test_inconsistent_equations_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            ConstraintValidationError, "inconsistent"
        ):
            constraint_set(
                "contradiction",
                (
                    GF2Equation((0,), 0, 5),
                    GF2Equation((0,), 1, 5),
                ),
            )

    def test_json_round_trip_recomputes_derived_fields(self) -> None:
        original = constraint_set(
            "round-trip",
            (
                GF2Equation((0, 2), 1, 5),
                GF2Equation((1,), 0, 6),
            ),
        )

        restored = ConstraintSet.from_json(original.to_json())

        self.assertEqual(restored, original)
        self.assertEqual(restored.to_json(), original.to_json())

    def test_tampered_semantic_hash_is_rejected(self) -> None:
        original = constraint_set(
            "tampered", (GF2Equation((0,), 0, 5),)
        )
        data = original.to_dict()
        data["semantic_sha256"] = "f" * 64

        with self.assertRaisesRegex(
            ConstraintValidationError, "semantic_sha256 is inconsistent"
        ):
            ConstraintSet.from_dict(data)


if __name__ == "__main__":
    unittest.main()
