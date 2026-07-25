from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from shared.sat import (
    ArtifactReference,
    ContractValidationError,
    SolverRequest,
    SolverResult,
    SolverStatus,
    VerificationResult,
    VerificationStatus,
    load_solver_request,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CONFIG = (
    REPOSITORY_ROOT
    / "experiments"
    / "gift64"
    / "sat_baseline_b2.solver_request.json"
)


class SolverRequestTests(unittest.TestCase):
    def test_baseline_configuration_preserves_b1_contract(self) -> None:
        request = load_solver_request(BASELINE_CONFIG)

        self.assertEqual(request.schema_version, "solver-request/v1")
        self.assertEqual(request.cipher.name, "GIFT-64")
        self.assertEqual(request.cipher.round_count, 4)
        self.assertEqual(request.expected_static_counts.variables, 2740)
        self.assertEqual(request.expected_static_counts.clauses, 8091)
        self.assertEqual(request.expected_static_counts.solver_calls, 1)
        self.assertEqual(
            [(item.name, item.unit, item.bound) for item in request.objective.components],
            [
                ("integral_weight", "1", 11),
                ("decimal_weight_count", "0.415", 1),
            ],
        )

    def test_static_request_is_honestly_not_execution_ready(self) -> None:
        request = load_solver_request(BASELINE_CONFIG)

        self.assertIsNone(request.instance)
        self.assertIsNone(request.variable_map)
        self.assertIsNone(request.solver.version)
        self.assertFalse(request.execution_ready)

    def test_request_round_trip_is_deterministic(self) -> None:
        request = load_solver_request(BASELINE_CONFIG)

        first = request.to_json()
        second = SolverRequest.from_json(first).to_json()

        self.assertEqual(first, second)
        self.assertEqual(BASELINE_CONFIG.read_text(encoding="utf-8"), first)

    def test_unknown_request_field_is_rejected(self) -> None:
        data = json.loads(BASELINE_CONFIG.read_text(encoding="utf-8"))
        data["silent_new_semantics"] = True

        with self.assertRaisesRegex(
            ContractValidationError, "unknown fields: silent_new_semantics"
        ):
            SolverRequest.from_dict(data)

    def test_inconsistent_round_count_is_rejected(self) -> None:
        data = json.loads(BASELINE_CONFIG.read_text(encoding="utf-8"))
        data["cipher"]["round_count"] = 5

        with self.assertRaisesRegex(ContractValidationError, "round_count"):
            SolverRequest.from_dict(data)

    def test_absolute_artifact_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ContractValidationError, "must be machine-independent"
        ):
            ArtifactReference(
                relative_path="/tmp/problem.cnf",
                sha256="a" * 64,
                media_type="application/x-dimacs",
                byte_size=10,
            )

    def test_artifact_parent_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ContractValidationError, "artifact root"):
            ArtifactReference(
                relative_path="../outside/problem.cnf",
                sha256="a" * 64,
                media_type="application/x-dimacs",
                byte_size=10,
            )


class SolverResultTests(unittest.TestCase):
    @staticmethod
    def valid_sat_result() -> SolverResult:
        return SolverResult(
            schema_version="solver-result/v1",
            result_id="gift64-r4-example-result",
            request_id="gift64-improved-attacks-differential-r4-w11-d1",
            status=SolverStatus.SAT,
            definitive=True,
            model=ArtifactReference(
                relative_path="artifacts/models/gift64-r4.model",
                sha256="b" * 64,
                media_type="text/plain",
                byte_size=2048,
            ),
            proof=None,
            objective_components={
                "integral_weight": 11,
                "decimal_weight_count": 1,
            },
            satisfied_bound=True,
            wall_time_s=1.25,
            cpu_time_s=1.20,
            peak_memory_mb=64,
            solver_statistics={"conflicts": 12, "decisions": 34},
            exit_code=0,
            parse_diagnostics=(),
            verification=VerificationResult(
                status=VerificationStatus.PASSED,
                verifier_version="gift64-trail-verifier/v1",
                diagnostics=(),
            ),
            exact_label_eligible=True,
            exact_label_reason="definitive SAT model passed independent verification",
        )

    def test_verified_sat_result_round_trip(self) -> None:
        result = self.valid_sat_result()

        reconstructed = SolverResult.from_json(result.to_json())

        self.assertEqual(reconstructed, result)
        self.assertTrue(reconstructed.exact_label_eligible)

    def test_timeout_cannot_be_definitive(self) -> None:
        data = self.valid_sat_result().to_dict()
        data.update(
            {
                "status": "TIMEOUT",
                "definitive": True,
                "model": None,
                "objective_components": None,
                "satisfied_bound": None,
                "verification": {
                    "status": "not_run",
                    "verifier_version": None,
                    "diagnostics": [],
                },
                "exact_label_eligible": False,
                "exact_label_reason": "solver timed out",
            }
        )

        with self.assertRaisesRegex(
            ContractValidationError, "only SAT or UNSAT results may be definitive"
        ):
            SolverResult.from_dict(data)

    def test_sat_requires_model_reference(self) -> None:
        data = self.valid_sat_result().to_dict()
        data["model"] = None

        with self.assertRaisesRegex(ContractValidationError, "must reference a model"):
            SolverResult.from_dict(data)

    def test_exact_label_requires_independent_verification(self) -> None:
        data = deepcopy(self.valid_sat_result().to_dict())
        data["verification"] = {
            "status": "not_run",
            "verifier_version": None,
            "diagnostics": [],
        }

        with self.assertRaisesRegex(
            ContractValidationError, "exact ML labels require"
        ):
            SolverResult.from_dict(data)


if __name__ == "__main__":
    unittest.main()
