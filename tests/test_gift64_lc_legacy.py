from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from automated_differential_analysis.adapters.gift64_lc_legacy import (
    GIFT64_LC_SOURCE_SHA256,
    Gift64LCAdapterError,
    instrument_gift64_lc_source,
    parse_gift64_lc_markers,
    run_gift64_lc_observation,
)
from automated_differential_analysis.formats import (
    Gift64TrailInformationLayout,
    parse_gift64_trail_information_bytes,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LC_STAGE = (
    REPOSITORY_ROOT.parent
    / "upstream"
    / "Supplementary_Material_GIFT-64_Differential"
    / "Source_code"
    / "2.Finding_linear_constraints"
)
SMALL_LAYOUT = Gift64TrailInformationLayout(
    group_count=1,
    trails_per_group=1,
    round_start=5,
    round_count=2,
    key_state_anchor_round=4,
)
SMALL_TRAIL = """0000 0000 0000 0000 0000 0000 000a 0000
0000 0000 0000 0001
0000 0000 0000 0002
0000 0000 0000 0002
0000 0000 0000 0004"""
SYNTHETIC_SOURCE = b"""int main()
{
                    if (flag == true)
                    {
                        cout<<"$";
}
"""


class Gift64LCUnitTests(unittest.TestCase):
    def test_hash_pinned_instrumentation_preserves_input(self) -> None:
        expected = hashlib.sha256(SYNTHETIC_SOURCE).hexdigest()

        with patch(
            "automated_differential_analysis.adapters."
            "gift64_lc_legacy.GIFT64_LC_SOURCE_SHA256",
            expected,
        ):
            instrumented = instrument_gift64_lc_source(SYNTHETIC_SOURCE)

        self.assertEqual(SYNTHETIC_SOURCE.count(b"LGCA_LC_ROW="), 0)
        self.assertEqual(instrumented.count(b"LGCA_LC_ROW="), 1)
        self.assertEqual(len(GIFT64_LC_SOURCE_SHA256), 64)

    def test_unpinned_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            Gift64LCAdapterError, "source SHA-256 mismatch"
        ):
            instrument_gift64_lc_source(SYNTHETIC_SOURCE)

    def test_marker_maps_key_columns_and_fixed_unit(self) -> None:
        corpus = parse_gift64_trail_information_bytes(
            SMALL_TRAIL.encode("ascii"), layout=SMALL_LAYOUT
        )
        marker = (
            "LGCA_LC_ROW=0,0,0;"
            "columns=151,159,192;rhs=0\n"
        )

        result = parse_gift64_lc_markers(marker, corpus)[0]
        equation = result.equations[0]

        self.assertEqual(equation.variable_indices, (87, 95))
        self.assertEqual(equation.source_round, 5)
        self.assertEqual(equation.source_rhs, 0)
        self.assertEqual(equation.effective_rhs, 1)
        self.assertEqual(result.rank, 1)
        self.assertEqual(result.nullity, 127)

    def test_unexpected_stderr_is_rejected(self) -> None:
        corpus = parse_gift64_trail_information_bytes(
            SMALL_TRAIL.encode("ascii"), layout=SMALL_LAYOUT
        )

        with self.assertRaisesRegex(
            Gift64LCAdapterError, "unexpected LC runtime stderr"
        ):
            parse_gift64_lc_markers("legacy warning\n", corpus)


@unittest.skipUnless(
    (LC_STAGE / "main.cpp").is_file()
    and (LC_STAGE / "TrailInformation.out").is_file()
    and shutil.which("clang++") is not None,
    "read-only LC stage or C++ compiler is unavailable",
)
class Gift64LCIntegrationTests(unittest.TestCase):
    def test_bounded_observation_matches_published_first_trail(self) -> None:
        observation = run_gift64_lc_observation(
            source_path=LC_STAGE / "main.cpp",
            trail_path=LC_STAGE / "TrailInformation.out",
        )
        first = observation.constraint_sets[0]
        summary = observation.summary_dict()

        self.assertEqual(len(observation.constraint_sets), 32)
        self.assertEqual(summary["equation_count"], 192)
        self.assertEqual(summary["rank_total"], 192)
        self.assertEqual(summary["rank_values"], [6])
        self.assertEqual(summary["unique_semantic_spaces"], 32)
        self.assertEqual(first.rank, 6)
        self.assertEqual(first.nullity, 122)
        self.assertEqual(
            [
                (
                    item.source_round,
                    item.variable_indices,
                    item.effective_rhs,
                )
                for item in first.equations
            ],
            [
                (5, (87, 95), 0),
                (7, (30,), 1),
                (9, (68, 88), 1),
                (9, (76,), 1),
                (9, (80, 88), 0),
                (11, (17, 25), 0),
            ],
        )


if __name__ == "__main__":
    unittest.main()
