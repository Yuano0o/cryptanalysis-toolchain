from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest

from shared.sat import (
    ArtifactReference,
    ContractValidationError,
    ModelHashPolicy,
    RegressionExpectation,
    SolverResult,
    SolverStatus,
    VerificationResult,
    VerificationStatus,
    check_solver_regression,
    load_regression_expectation,
    load_solver_request,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = (
    REPOSITORY_ROOT
    / "experiments"
    / "gift64"
    / "sat_baseline_b2.solver_request.json"
)
EXPECTATION_PATH = (
    REPOSITORY_ROOT
    / "experiments"
    / "gift64"
    / "sat_baseline_b6.regression.json"
)


def matching_result() -> SolverResult:
    return SolverResult(
        schema_version="solver-result/v1",
        result_id="gift64-b6-test-result",
        request_id="gift64-improved-attacks-differential-r4-w11-d1",
        status=SolverStatus.SAT,
        definitive=True,
        model=ArtifactReference(
            relative_path="models/ephemeral.trail.json",
            sha256=(
                "8e42de961476884641e53b2e15b1596f"
                "920aa84b3bcb4ff22fc8c7d9b47bac87"
            ),
            media_type="application/vnd.lgca.trail+json",
            byte_size=2144,
        ),
        proof=None,
        objective_components={
            "integral_weight": 11,
            "decimal_weight_count": 1,
        },
        satisfied_bound=True,
        wall_time_s=99.0,
        cpu_time_s=12.0,
        peak_memory_mb=None,
        solver_statistics={
            "adapter_version": "gift64-improved-legacy-adapter/v1",
            "compile_wall_time_s": 88.0,
        },
        exit_code=0,
        parse_diagnostics=(),
        verification=VerificationResult(
            status=VerificationStatus.PASSED,
            verifier_version="gift64-four-round-verifier/v1",
            diagnostics=(),
        ),
        exact_label_eligible=True,
        exact_label_reason="verified test result",
    )


class RegressionExpectationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = load_solver_request(REQUEST_PATH)
        self.expectation = load_regression_expectation(EXPECTATION_PATH)

    def test_checked_in_expectation_round_trip_is_deterministic(self) -> None:
        reconstructed = RegressionExpectation.from_json(
            self.expectation.to_json()
        )

        self.assertEqual(reconstructed, self.expectation)
        self.assertEqual(
            EXPECTATION_PATH.read_text(encoding="utf-8"),
            self.expectation.to_json(),
        )

    def test_matching_semantics_pass_and_ignore_timings(self) -> None:
        first = matching_result()
        second = replace(first, wall_time_s=0.01, cpu_time_s=0.0)

        first_check = check_solver_regression(
            self.expectation, self.request, first
        )
        second_check = check_solver_regression(
            self.expectation, self.request, second
        )

        self.assertTrue(first_check.passed)
        self.assertTrue(second_check.passed)
        self.assertEqual(first_check.failures, ())
        self.assertEqual(second_check.failures, ())

    def test_objective_change_is_a_regression(self) -> None:
        result = replace(
            matching_result(),
            objective_components={
                "integral_weight": 10,
                "decimal_weight_count": 1,
            },
        )

        check = check_solver_regression(
            self.expectation, self.request, result
        )

        self.assertFalse(check.passed)
        self.assertIn("objective_components", check.failures[0])

    def test_request_change_is_a_regression(self) -> None:
        changed_request = replace(self.request, seed=1)

        check = check_solver_regression(
            self.expectation, changed_request, matching_result()
        )

        self.assertFalse(check.passed)
        self.assertIn(
            "request.sha256",
            "\n".join(check.failures),
        )

    def test_model_hash_change_is_advisory_under_record_only_policy(self) -> None:
        result = replace(
            matching_result(),
            model=replace(matching_result().model, sha256="a" * 64),
        )

        check = check_solver_regression(
            self.expectation, self.request, result
        )

        self.assertTrue(check.passed)
        self.assertEqual(check.failures, ())
        self.assertEqual(len(check.advisories), 1)

    def test_model_hash_change_fails_under_exact_policy(self) -> None:
        expectation = replace(
            self.expectation, model_hash_policy=ModelHashPolicy.EXACT
        )
        result = replace(
            matching_result(),
            model=replace(matching_result().model, sha256="a" * 64),
        )

        check = check_solver_regression(expectation, self.request, result)

        self.assertFalse(check.passed)
        self.assertEqual(len(check.failures), 1)
        self.assertEqual(check.advisories, ())

    def test_unknown_expectation_field_is_rejected(self) -> None:
        data = deepcopy(self.expectation.to_dict())
        data["raw_model"] = "must-not-be-added"

        with self.assertRaisesRegex(
            ContractValidationError, "unknown fields: raw_model"
        ):
            RegressionExpectation.from_dict(data)


if __name__ == "__main__":
    unittest.main()
