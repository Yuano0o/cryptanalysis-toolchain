from __future__ import annotations

from decimal import Decimal
import unittest

from automated_differential_analysis.formats import (
    GIFT64_STAGE3_PROBABILITY_REQUEST_SCHEMA_VERSION,
    Gift64Stage3ProbabilityError,
    Gift64Stage3ProbabilityRequest,
    estimate_subcube_probability,
)


def valid_request() -> Gift64Stage3ProbabilityRequest:
    return Gift64Stage3ProbabilityRequest(
        schema_version=GIFT64_STAGE3_PROBABILITY_REQUEST_SCHEMA_VERSION,
        request_id="gift64-stage3-test",
        key_position=0,
        trail_position=0,
        repeat_count=3,
        fixed_bit_count=21,
        sampling_seed=20260726,
        solver_name="cryptominisat",
        solver_version="5.14.7",
        per_sample_time_limit_s=30.0,
    )


class Gift64Stage3ProbabilityTests(unittest.TestCase):
    def test_request_round_trips_and_exposes_subcube_size(self) -> None:
        request = valid_request()
        round_trip = Gift64Stage3ProbabilityRequest.from_json(request.to_json())

        self.assertEqual(round_trip.to_dict(), request.to_dict())
        self.assertEqual(request.free_bit_count, 43)
        self.assertEqual(request.subcube_size, 2**43)

    def test_request_rejects_outside_fixture_positions(self) -> None:
        data = valid_request().to_dict()
        data["key_position"] = 1000
        with self.assertRaisesRegex(Gift64Stage3ProbabilityError, "0..999"):
            Gift64Stage3ProbabilityRequest.from_dict(data)
        data = valid_request().to_dict()
        data["fixed_bit_count"] = 64
        with self.assertRaisesRegex(Gift64Stage3ProbabilityError, "1..63"):
            Gift64Stage3ProbabilityRequest.from_dict(data)

    def test_estimate_is_mean_over_complete_subcube_fractions(self) -> None:
        estimate = estimate_subcube_probability((2, 4), fixed_bit_count=62)

        self.assertEqual(estimate.solution_count_total, 6)
        self.assertEqual(estimate.point_estimate, Decimal("0.75"))
        self.assertIsNotNone(estimate.normal_95_lower)
        self.assertIsNotNone(estimate.normal_95_upper)

    def test_one_complete_sample_has_no_descriptive_interval(self) -> None:
        estimate = estimate_subcube_probability((3,), fixed_bit_count=62)

        self.assertEqual(estimate.point_estimate, Decimal("0.75"))
        self.assertIsNone(estimate.normal_95_lower)
        self.assertIsNone(estimate.normal_95_upper)

    def test_impossible_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(Gift64Stage3ProbabilityError, "exceeds"):
            estimate_subcube_probability((5,), fixed_bit_count=62)


if __name__ == "__main__":
    unittest.main()
