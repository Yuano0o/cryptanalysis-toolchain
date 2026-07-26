from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from automated_differential_analysis.adapters.gift64_stage3_legacy import (
    GIFT64_STAGE3_ADAPTER_VERSION,
    Gift64Stage3AdapterError,
    Gift64Stage3Observation,
    Gift64Stage3SampleResult,
    instrument_gift64_stage3_source,
    parse_stage3_sample_marker,
    run_gift64_stage3_probability_demo,
)
from automated_differential_analysis.adapters import gift64_stage3_legacy
from automated_differential_analysis.formats import (
    GIFT64_STAGE3_PROBABILITY_REQUEST_SCHEMA_VERSION,
    Gift64Stage3ProbabilityRequest,
)
from shared.sat import SolverStatus


SYNTHETIC_SOURCE = b"""#define RepeatTestTime 100
#define RandomFixBitNum 21
#define TargetKeyIndex 0
#define TestTrailIndex 0
                random_device rand;
                int Solution = 0;
                    if (ret == l_True)
                    {
                        Solution += 1;
                        // Delete solution
                        clause.clear();
                        for (size_t bit = 0; bit < 64; bit++)
                        {
                            if (solver.get_model()[xin_pair1[0][bit]] != l_Undef)
                            {
                                clause.push_back(Lit(xin_pair1[0][bit], solver.get_model()[xin_pair1[0][bit]] == l_True));
                            }
                        }
                        solver.add_clause(clause);
                    }
                cout<<"Number of Solution: "<<(dec)<<Solution << endl;
"""
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE3_ROOT = (
    REPOSITORY_ROOT.parent
    / "upstream"
    / "Supplementary_Material_GIFT-64_Differential"
    / "Source_code"
    / "5.Stage3_test"
)


def request() -> Gift64Stage3ProbabilityRequest:
    return Gift64Stage3ProbabilityRequest(
        "gift64-stage3-probability-request/v2",
        "gift64-stage3-test",
        3,
        7,
        2,
        21,
        20260726,
        "cryptominisat",
        "5.14.7",
        30.0,
        60.0,
    )


class Gift64Stage3AdapterTests(unittest.TestCase):
    def test_homebrew_timeout_is_wrapped_as_adapter_error(self) -> None:
        with (
            patch(
                "automated_differential_analysis.adapters."
                "gift64_stage3_legacy.shutil.which",
                return_value="/opt/homebrew/bin/brew",
            ),
            patch(
                "automated_differential_analysis.adapters."
                "gift64_stage3_legacy.subprocess.run",
                side_effect=subprocess.TimeoutExpired("brew --prefix", 30),
            ),
        ):
            with self.assertRaisesRegex(
                Gift64Stage3AdapterError, "timed out resolving"
            ):
                gift64_stage3_legacy._formula_prefix("cryptominisat")

    def test_total_budget_unstarted_samples_are_not_solver_timeouts(self) -> None:
        samples = tuple(
            Gift64Stage3SampleResult(
                sample_index=index,
                execution_state="not_started_total_budget",
                terminal_status=None,
                fixed_assignments=(),
                solution_count=None,
                wall_time_s=0.0,
                cpu_time_s=0.0,
                exit_code=None,
                stdout_sha256=None,
                diagnostics=("budget exhausted before launch",),
            )
            for index in range(2)
        )
        observation = Gift64Stage3Observation(
            adapter_version=GIFT64_STAGE3_ADAPTER_VERSION,
            source_sha256="0" * 64,
            trail_source_sha256="1" * 64,
            key_corpus_sha256="2" * 64,
            request=request(),
            solver_version="5.14.7",
            instrumented_source_sha256="3" * 64,
            compile_wall_time_s=0.0,
            run_wall_time_s=60.0,
            samples=samples,
            estimate=None,
        )

        summary = observation.summary_dict()
        self.assertEqual(summary["not_started_total_budget_count"], 2)
        self.assertEqual(sum(summary["status_counts"].values()), 0)
        self.assertTrue(
            all(item["terminal_status"] is None for item in summary["samples"])
        )

    def test_instrumentation_pins_one_deterministic_sample_process(self) -> None:
        source_hash = hashlib.sha256(SYNTHETIC_SOURCE).hexdigest()
        with patch(
            "automated_differential_analysis.adapters."
            "gift64_stage3_legacy.GIFT64_STAGE3_SOURCE_SHA256",
            source_hash,
        ):
            instrumented = instrument_gift64_stage3_source(
                SYNTHETIC_SOURCE, request=request()
            )
        text = instrumented.decode("utf-8")

        self.assertIn("#define RepeatTestTime 1", text)
        self.assertIn("#define RandomFixBitNum 21", text)
        self.assertIn("#define TargetKeyIndex 3", text)
        self.assertIn("#define TestTrailIndex 7", text)
        self.assertIn("LGCA_STAGE3_SAMPLE_INDEX", text)
        self.assertIn("unsigned long long Solution = 0ULL", text)
        self.assertIn("lgca_all_xin_bits_defined", text)
        self.assertEqual(text.count("LGCA_STAGE3_SAMPLE="), 1)

    def test_unpinned_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(Gift64Stage3AdapterError, "SHA-256 mismatch"):
            instrument_gift64_stage3_source(SYNTHETIC_SOURCE, request=request())

    def test_marker_requires_complete_assignment_and_bound_positions(self) -> None:
        terminal, assignments, count = parse_stage3_sample_marker(
            "LGCA_STAGE3_SAMPLE=4;key=3;trail=7;fixed=0:1,5:0;solutions=17;terminal=UNSAT\n",
            expected_sample_index=4,
            expected_key_position=3,
            expected_trail_position=7,
            expected_fixed_bit_count=2,
        )
        self.assertIs(terminal, SolverStatus.UNSAT)
        self.assertEqual(assignments, ((0, 1), (5, 0)))
        self.assertEqual(count, 17)
        with self.assertRaisesRegex(Gift64Stage3AdapterError, "wrong fixed-bit count"):
            parse_stage3_sample_marker(
                "LGCA_STAGE3_SAMPLE=4;key=3;trail=7;fixed=0:1;solutions=17;terminal=UNSAT\n",
                expected_sample_index=4,
                expected_key_position=3,
                expected_trail_position=7,
                expected_fixed_bit_count=2,
            )
        terminal, assignments, count = parse_stage3_sample_marker(
            "LGCA_STAGE3_SAMPLE=4;key=3;trail=7;fixed=0:1,5:0;solutions=17;terminal=ERROR\n",
            expected_sample_index=4,
            expected_key_position=3,
            expected_trail_position=7,
            expected_fixed_bit_count=2,
        )
        self.assertIs(terminal, SolverStatus.ERROR)
        self.assertEqual(assignments, ((0, 1), (5, 0)))
        self.assertEqual(count, 17)


@unittest.skipUnless(
    (STAGE3_ROOT / "main.cpp").is_file()
    and (STAGE3_ROOT / "TrailInformation.out").is_file()
    and (STAGE3_ROOT / "KeyCandidate1000.out").is_file()
    and shutil.which("clang++") is not None
    and shutil.which("brew") is not None,
    "read-only Stage 3 source, fixture, compiler or Homebrew is unavailable",
)
class Gift64Stage3IntegrationTests(unittest.TestCase):
    def test_one_deterministic_subcube_count_completes(self) -> None:
        request = Gift64Stage3ProbabilityRequest(
            "gift64-stage3-probability-request/v2",
            "gift64-stage3-integration",
            0,
            0,
            1,
            21,
            20260726,
            "cryptominisat",
            "5.14.7",
            30.0,
            60.0,
        )
        observation = run_gift64_stage3_probability_demo(
            source_path=STAGE3_ROOT / "main.cpp",
            trail_path=STAGE3_ROOT / "TrailInformation.out",
            key_corpus_path=STAGE3_ROOT / "KeyCandidate1000.out",
            request=request,
        )
        repeated = run_gift64_stage3_probability_demo(
            source_path=STAGE3_ROOT / "main.cpp",
            trail_path=STAGE3_ROOT / "TrailInformation.out",
            key_corpus_path=STAGE3_ROOT / "KeyCandidate1000.out",
            request=request,
        )

        self.assertEqual(
            observation.source_sha256,
            "40b71f4fd21798bcae68bcd76922e788eb19f795d5a0e788abd0cc721c6f81ca",
        )
        self.assertEqual(observation.key_corpus_sha256, "d97ee7bedccfe2f8d6df9e48a2da7e0bdb6524cfe1188e8e5e6bf8a8107d761e")
        self.assertEqual(len(observation.samples), 1)
        self.assertTrue(observation.samples[0].complete)
        self.assertEqual(observation.samples[0].execution_state, "ran")
        self.assertEqual(observation.samples[0].terminal_status, SolverStatus.UNSAT)
        self.assertIsNotNone(observation.estimate)
        self.assertEqual(
            repeated.samples[0].fixed_assignments,
            observation.samples[0].fixed_assignments,
        )
        self.assertEqual(
            repeated.samples[0].solution_count,
            observation.samples[0].solution_count,
        )


if __name__ == "__main__":
    unittest.main()
