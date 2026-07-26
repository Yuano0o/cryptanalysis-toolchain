from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from automated_differential_analysis.adapters.gift64_stage2_legacy import (
    Gift64Stage2AdapterError,
    instrument_gift64_stage2_source,
    parse_stage2_status_marker,
    run_gift64_stage2_demo,
)
from automated_differential_analysis.formats import Gift64Stage2KeyCorpusSpec
from shared.sat import SolverStatus


SYNTHETIC_SOURCE = b"""int AllTestKeyValue[1000000][8];
for (int testkeyindex = 0; testkeyindex < 1000000; testkeyindex++) {}
for(int testkeyindex = 0; testkeyindex < 1000000; testkeyindex++)
{
    for (int trail = 0; trail < 1; trail++)//TrailPerGroup
    {
            lbool ret = solver.solve();
    }
}
"""
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STAGE2_ROOT = (
    REPOSITORY_ROOT.parent
    / "upstream"
    / "Supplementary_Material_GIFT-64_Differential"
    / "Source_code"
    / "4.Stage2_test"
)


class Gift64Stage2AdapterTests(unittest.TestCase):
    def test_hash_pinned_instrumentation_binds_one_key_and_selected_trail(self) -> None:
        expected = hashlib.sha256(SYNTHETIC_SOURCE).hexdigest()
        with patch(
            "automated_differential_analysis.adapters."
            "gift64_stage2_legacy.GIFT64_STAGE2_SOURCE_SHA256",
            expected,
        ):
            instrumented = instrument_gift64_stage2_source(
                SYNTHETIC_SOURCE, trail_position=7
            )
        text = instrumented.decode("utf-8")

        self.assertNotIn("1000000", text)
        self.assertIn("int AllTestKeyValue[1][8];", text)
        self.assertIn("testkeyindex < 1", text)
        self.assertIn("int trail = 7; trail < 8", text)
        self.assertEqual(text.count("LGCA_STAGE2_STATUS="), 1)
        self.assertNotIn("LGCA_STAGE2_STATUS=", SYNTHETIC_SOURCE.decode("utf-8"))

    def test_unpinned_source_and_outside_trail_are_rejected(self) -> None:
        with self.assertRaisesRegex(Gift64Stage2AdapterError, "SHA-256 mismatch"):
            instrument_gift64_stage2_source(SYNTHETIC_SOURCE, trail_position=0)
        with patch(
            "automated_differential_analysis.adapters."
            "gift64_stage2_legacy.GIFT64_STAGE2_SOURCE_SHA256",
            hashlib.sha256(SYNTHETIC_SOURCE).hexdigest(),
        ):
            with self.assertRaisesRegex(Gift64Stage2AdapterError, "outside"):
                instrument_gift64_stage2_source(SYNTHETIC_SOURCE, trail_position=32)

    def test_status_marker_is_strictly_bound_to_one_key_and_one_trail(self) -> None:
        self.assertIs(
            parse_stage2_status_marker(
                "legacy notice\nLGCA_STAGE2_STATUS=0,3,SAT\n",
                expected_key_index=0,
                expected_trail_position=3,
            ),
            SolverStatus.SAT,
        )
        with self.assertRaisesRegex(Gift64Stage2AdapterError, "wrong trail"):
            parse_stage2_status_marker(
                "LGCA_STAGE2_STATUS=0,1,UNSAT\n",
                expected_key_index=0,
                expected_trail_position=3,
            )
        with self.assertRaisesRegex(Gift64Stage2AdapterError, "exactly one"):
            parse_stage2_status_marker(
                "LGCA_STAGE2_STATUS=0,3,SAT\nLGCA_STAGE2_STATUS=0,3,SAT\n",
                expected_key_index=0,
                expected_trail_position=3,
            )


@unittest.skipUnless(
    (STAGE2_ROOT / "main.cpp").is_file()
    and (STAGE2_ROOT / "TrailInformation.out").is_file()
    and shutil.which("clang++") is not None
    and shutil.which("brew") is not None,
    "read-only Stage 2 source, compiler or Homebrew is unavailable",
)
class Gift64Stage2IntegrationTests(unittest.TestCase):
    def test_one_key_demo_runs_with_hash_pinned_provenance(self) -> None:
        observation = run_gift64_stage2_demo(
            source_path=STAGE2_ROOT / "main.cpp",
            trail_path=STAGE2_ROOT / "TrailInformation.out",
            key_corpus_spec=Gift64Stage2KeyCorpusSpec(
                "gift64-stage2-key-corpus/v1",
                "generated-for-demo",
                "sha256-counter-v1",
                20260726,
                1,
            ),
            trail_position=0,
            per_key_time_limit_s=30.0,
        )

        self.assertEqual(observation.source_sha256, "58f5d24110cf8170de6cc0f1cdd29657abc1463bf044703756e052b640275964")
        self.assertEqual(observation.trail_position, 0)
        self.assertEqual(observation.key_corpus_spec.key_count, 1)
        self.assertEqual(len(observation.results), 1)
        self.assertIn(
            observation.results[0].status,
            {SolverStatus.SAT, SolverStatus.UNSAT},
        )
        self.assertEqual(observation.results[0].exit_code, 0)


if __name__ == "__main__":
    unittest.main()
