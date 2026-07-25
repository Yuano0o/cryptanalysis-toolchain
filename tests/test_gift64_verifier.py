from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from shared.ciphers.gift64 import (
    GIFT64_BIT_ORDER_ID,
    GIFT64_DDT,
    GIFT64_NIBBLE_ORDER_ID,
    GIFT64_PERMUTATION,
    GIFT64_STATE_LAYOUT_ID,
    TransitionWeight,
    logical_sbox_output_from_permuted_state,
    transition_weight,
    verify_gift64_four_round_trail,
)
from shared.sat import VerificationStatus, load_solver_request
from shared.trails import TrailRecord, TrailRound


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CONFIG = (
    REPOSITORY_ROOT
    / "experiments"
    / "gift64"
    / "sat_baseline_b2.solver_request.json"
)


def structurally_valid_four_round_trail() -> TrailRecord:
    """Return a fixed valid trail; it is not claimed to meet the B2 bounds."""

    return TrailRecord(
        schema_version="trail-record/v1",
        trail_id="gift64-b3-structural-fixture",
        cipher="GIFT-64",
        state_layout_id=GIFT64_STATE_LAYOUT_ID,
        bit_order_id=GIFT64_BIT_ORDER_ID,
        nibble_order_id=GIFT64_NIBBLE_ORDER_ID,
        rounds=(
            TrailRound(
                round_index=0,
                input_nibbles=(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                output_nibbles=(4, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0),
            ),
            TrailRound(
                round_index=1,
                input_nibbles=(4, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0),
                output_nibbles=(4, 0, 4, 0, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0),
            ),
            TrailRound(
                round_index=2,
                input_nibbles=(4, 0, 4, 0, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0),
                output_nibbles=(5, 4, 5, 0, 2, 0, 0, 0, 5, 1, 5, 0, 2, 0, 0, 0),
            ),
            TrailRound(
                round_index=3,
                input_nibbles=(5, 4, 5, 0, 2, 0, 0, 0, 5, 1, 5, 0, 2, 0, 0, 0),
                output_nibbles=(7, 4, 5, 4, 11, 0, 11, 0, 5, 1, 5, 1, 14, 0, 14, 0),
            ),
        ),
        claimed_objective_components={
            "integral_weight": 33,
            "decimal_weight_count": 4,
        },
    )


class Gift64PrimitiveTests(unittest.TestCase):
    def test_ddt_distribution_matches_b1_static_audit(self) -> None:
        counts = [value for row in GIFT64_DDT for value in row]

        self.assertEqual(counts.count(0), 157)
        self.assertEqual(counts.count(2), 78)
        self.assertEqual(counts.count(4), 18)
        self.assertEqual(counts.count(6), 2)
        self.assertEqual(counts.count(16), 1)

    def test_ddt_weight_classes_match_b1_semantics(self) -> None:
        self.assertEqual(transition_weight(0x0, 0x0), TransitionWeight(0, 0))
        self.assertEqual(transition_weight(0x1, 0x5), TransitionWeight(3, 0))
        self.assertEqual(transition_weight(0x2, 0x5), TransitionWeight(2, 0))
        self.assertEqual(transition_weight(0x4, 0x7), TransitionWeight(1, 1))
        self.assertIsNone(transition_weight(0x1, 0x0))

    def test_permutation_is_a_bijection(self) -> None:
        self.assertEqual(sorted(GIFT64_PERMUTATION), list(range(64)))

    def test_permutation_direction_recovers_logical_sbox_output(self) -> None:
        first_round_output = (
            4,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )

        logical_output = logical_sbox_output_from_permuted_state(
            first_round_output
        )

        self.assertEqual(logical_output, (5,) + (0,) * 15)


class Gift64TrailVerificationTests(unittest.TestCase):
    def test_structurally_valid_trail_recomputes_weight(self) -> None:
        report = verify_gift64_four_round_trail(
            structurally_valid_four_round_trail()
        )

        self.assertTrue(report.valid)
        self.assertEqual(report.checked_rounds, 4)
        self.assertEqual(report.checked_sboxes, 64)
        self.assertEqual(report.integral_weight, 33)
        self.assertEqual(report.decimal_weight_count, 4)
        self.assertEqual(report.issues, ())
        self.assertEqual(
            report.as_solver_verification().status, VerificationStatus.PASSED
        )

    def test_trail_record_json_round_trip_is_deterministic(self) -> None:
        trail = structurally_valid_four_round_trail()

        reconstructed = TrailRecord.from_json(trail.to_json())

        self.assertEqual(reconstructed, trail)
        self.assertEqual(reconstructed.to_json(), trail.to_json())

    def test_b2_request_bounds_are_checked_independently(self) -> None:
        request = load_solver_request(BASELINE_CONFIG)

        report = verify_gift64_four_round_trail(
            structurally_valid_four_round_trail(), request
        )

        self.assertFalse(report.valid)
        self.assertEqual(
            [issue.code for issue in report.issues],
            ["objective_bound", "objective_bound"],
        )

    def test_invalid_sbox_transition_is_rejected(self) -> None:
        trail = structurally_valid_four_round_trail()
        broken_first_round = replace(
            trail.rounds[0], output_nibbles=(0,) * 16
        )
        broken = replace(
            trail, rounds=(broken_first_round,) + trail.rounds[1:]
        )

        report = verify_gift64_four_round_trail(broken)

        self.assertFalse(report.valid)
        self.assertIn(
            "invalid_sbox_transition",
            {issue.code for issue in report.issues},
        )
        self.assertEqual(
            report.as_solver_verification().status, VerificationStatus.FAILED
        )

    def test_zero_initial_difference_is_rejected(self) -> None:
        zero_rounds = tuple(
            TrailRound(
                round_index=index,
                input_nibbles=(0,) * 16,
                output_nibbles=(0,) * 16,
            )
            for index in range(4)
        )
        trail = replace(
            structurally_valid_four_round_trail(),
            rounds=zero_rounds,
            claimed_objective_components={
                "integral_weight": 0,
                "decimal_weight_count": 0,
            },
        )

        report = verify_gift64_four_round_trail(trail)

        self.assertFalse(report.valid)
        self.assertEqual([issue.code for issue in report.issues], ["zero_input"])

    def test_malformed_state_length_is_rejected(self) -> None:
        trail = structurally_valid_four_round_trail()
        short_round = replace(
            trail.rounds[2], input_nibbles=trail.rounds[2].input_nibbles[:-1]
        )
        malformed = replace(
            trail,
            rounds=trail.rounds[:2] + (short_round,) + trail.rounds[3:],
        )

        report = verify_gift64_four_round_trail(malformed)

        self.assertFalse(report.valid)
        self.assertIn("input_state_length", {item.code for item in report.issues})

    def test_claimed_weight_mismatch_is_rejected(self) -> None:
        trail = replace(
            structurally_valid_four_round_trail(),
            claimed_objective_components={
                "integral_weight": 32,
                "decimal_weight_count": 4,
            },
        )

        report = verify_gift64_four_round_trail(trail)

        self.assertFalse(report.valid)
        self.assertEqual(
            [issue.code for issue in report.issues],
            ["claimed_objective_mismatch"],
        )


if __name__ == "__main__":
    unittest.main()
