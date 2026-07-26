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
        total_time_limit_s=60.0,
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

    def test_estimate_is_mean_with_descriptive_dispersion(self) -> None:
        estimate = estimate_subcube_probability((2, 4), fixed_bit_count=62)

        self.assertEqual(estimate.solution_count_total, 6)
        self.assertEqual(estimate.point_estimate, Decimal("0.75"))
        self.assertEqual(estimate.sample_fraction_minimum, Decimal("0.5"))
        self.assertEqual(estimate.sample_fraction_maximum, Decimal("1"))
        self.assertEqual(estimate.sample_standard_deviation, Decimal("0.35355339059327376220042218105242451964241796884424"))

    def test_one_complete_sample_has_no_sample_standard_deviation(self) -> None:
        estimate = estimate_subcube_probability((3,), fixed_bit_count=62)

        self.assertEqual(estimate.point_estimate, Decimal("0.75"))
        self.assertIsNone(estimate.sample_standard_deviation)
        self.assertEqual(estimate.sample_fraction_minimum, Decimal("0.75"))
        self.assertEqual(estimate.sample_fraction_maximum, Decimal("0.75"))

    def test_zero_counts_are_descriptive_not_a_zero_width_interval(self) -> None:
        estimate = estimate_subcube_probability((0, 0), fixed_bit_count=62)

        self.assertEqual(estimate.point_estimate, Decimal("0"))
        self.assertEqual(estimate.sample_standard_deviation, Decimal("0"))
        self.assertNotIn("normal_95_lower", estimate.to_dict())
        self.assertNotIn("normal_95_upper", estimate.to_dict())

    def test_impossible_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(Gift64Stage3ProbabilityError, "exceeds"):
            estimate_subcube_probability((5,), fixed_bit_count=62)

    def test_request_rejects_nonfinite_time_limits(self) -> None:
        data = valid_request().to_dict()
        data["resources"]["total_time_limit_s"] = float("inf")

        with self.assertRaisesRegex(Gift64Stage3ProbabilityError, "positive"):
            Gift64Stage3ProbabilityRequest.from_dict(data)


if __name__ == "__main__":
    unittest.main()
