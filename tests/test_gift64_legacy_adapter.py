from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from automated_differential_analysis.adapters.gift64_improved_legacy import (
    EXPECTED_SOURCE_SHA256,
    Gift64LegacyAdapterError,
    decode_legacy_stdout,
    instrument_status_output,
    parse_status_marker,
    run_controlled_gift64,
)
from shared.ciphers.gift64 import verify_gift64_four_round_trail
from shared.sat import SolverStatus, load_solver_request


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CONFIG = (
    REPOSITORY_ROOT
    / "experiments"
    / "gift64"
    / "sat_baseline_b2.solver_request.json"
)
SYNTHETIC_SOURCE = b"""int main()
{
    lbool ret = solver.solve();
}
"""

STRUCTURAL_STDOUT = """Round: 0 ----------------------------
xin:
1,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0,
xout:
4,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0,
Round: 1 ----------------------------
xin:
4,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0,
xout:
4,0,4,0, 2,0,0,0, 1,0,1,0, 0,0,0,0,
Round: 2 ----------------------------
xin:
4,0,4,0, 2,0,0,0, 1,0,1,0, 0,0,0,0,
xout:
5,4,5,0, 2,0,0,0, 5,1,5,0, 2,0,0,0,
Round: 3 ----------------------------
xin:
5,4,5,0, 2,0,0,0, 5,1,5,0, 2,0,0,0,
xout:
7,4,5,4, b,0,b,0, 5,1,5,1, e,0,e,0,
"""


class Gift64LegacyInstrumentationTests(unittest.TestCase):
    def test_pinned_source_is_instrumented_without_mutating_input(self) -> None:
        source = SYNTHETIC_SOURCE
        expected_sha256 = hashlib.sha256(source).hexdigest()

        with patch(
            "automated_differential_analysis.adapters."
            "gift64_improved_legacy.EXPECTED_SOURCE_SHA256",
            expected_sha256,
        ):
            instrumented = instrument_status_output(source)

        self.assertNotEqual(instrumented, source)
        self.assertIn(b"LGCA_SOLVER_STATUS=", instrumented)
        self.assertEqual(source, SYNTHETIC_SOURCE)
        self.assertEqual(len(EXPECTED_SOURCE_SHA256), 64)

    def test_unpinned_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            Gift64LegacyAdapterError, "source SHA-256 mismatch"
        ):
            instrument_status_output(SYNTHETIC_SOURCE)

    def test_nondefault_threads_require_a_pinned_thread_line(self) -> None:
        source = b"""int main()
{
    solver.set_num_threads(1);
    lbool ret = solver.solve();
}
"""
        expected_sha256 = hashlib.sha256(source).hexdigest()

        with patch(
            "automated_differential_analysis.adapters."
            "gift64_improved_legacy.EXPECTED_SOURCE_SHA256",
            expected_sha256,
        ):
            instrumented = instrument_status_output(source, threads=2)

        self.assertIn(b"solver.set_num_threads(2);", instrumented)
        self.assertIn(b"LGCA_SOLVER_STATUS=", instrumented)

    def test_status_marker_requires_exactly_one_native_status(self) -> None:
        self.assertEqual(
            parse_status_marker("LGCA_SOLVER_STATUS=SAT\n"),
            SolverStatus.SAT,
        )
        self.assertEqual(
            parse_status_marker("warning\nLGCA_SOLVER_STATUS=UNSAT\n"),
            SolverStatus.UNSAT,
        )
        self.assertEqual(
            parse_status_marker("LGCA_SOLVER_STATUS=UNKNOWN\n"),
            SolverStatus.UNKNOWN,
        )
        with self.assertRaisesRegex(Gift64LegacyAdapterError, "got 0"):
            parse_status_marker("")
        with self.assertRaisesRegex(Gift64LegacyAdapterError, "got 2"):
            parse_status_marker(
                "LGCA_SOLVER_STATUS=SAT\nLGCA_SOLVER_STATUS=SAT\n"
            )

    def test_missing_source_maps_to_error_result(self) -> None:
        request = load_solver_request(BASELINE_CONFIG)
        with tempfile.TemporaryDirectory() as artifact_root:
            controlled = run_controlled_gift64(
                request,
                source_path=REPOSITORY_ROOT / "missing.cpp",
                artifact_root=Path(artifact_root),
            )

        self.assertEqual(controlled.result.status, SolverStatus.ERROR)
        self.assertFalse(controlled.result.definitive)
        self.assertIsNone(controlled.trail)

    def test_repository_artifact_root_is_rejected(self) -> None:
        request = load_solver_request(BASELINE_CONFIG)

        controlled = run_controlled_gift64(
            request,
            source_path=REPOSITORY_ROOT / "missing.cpp",
            artifact_root=REPOSITORY_ROOT / "generated-artifacts",
        )

        self.assertEqual(controlled.result.status, SolverStatus.ERROR)
        self.assertIn(
            "outside the Git repository",
            controlled.result.parse_diagnostics[0],
        )
        self.assertFalse((REPOSITORY_ROOT / "generated-artifacts").exists())


class Gift64LegacyDecodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = load_solver_request(BASELINE_CONFIG)

    def test_structural_stdout_decodes_and_verifies(self) -> None:
        trail = decode_legacy_stdout(STRUCTURAL_STDOUT, self.request)

        report = verify_gift64_four_round_trail(trail)

        self.assertTrue(report.valid)
        self.assertEqual(report.integral_weight, 33)
        self.assertEqual(report.decimal_weight_count, 4)
        self.assertEqual(trail.rounds[0].input_nibbles[0], 0x1)

    def test_missing_round_is_rejected(self) -> None:
        truncated = "\n".join(STRUCTURAL_STDOUT.splitlines()[:-5])

        with self.assertRaisesRegex(
            Gift64LegacyAdapterError, "expected 20 non-empty model lines"
        ):
            decode_legacy_stdout(truncated, self.request)

    def test_wrong_round_order_is_rejected(self) -> None:
        reordered = STRUCTURAL_STDOUT.replace("Round: 1", "Round: 2", 1)

        with self.assertRaisesRegex(
            Gift64LegacyAdapterError, "expected round index 1"
        ):
            decode_legacy_stdout(reordered, self.request)

    def test_non_hex_state_is_rejected(self) -> None:
        malformed = STRUCTURAL_STDOUT.replace("1,0,0,0", "g,0,0,0", 1)

        with self.assertRaisesRegex(
            Gift64LegacyAdapterError, "unexpected characters"
        ):
            decode_legacy_stdout(malformed, self.request)


if __name__ == "__main__":
    unittest.main()
