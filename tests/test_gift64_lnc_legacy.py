from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from automated_differential_analysis.adapters.gift64_lc_legacy import (
    run_gift64_lc_observation,
)
from automated_differential_analysis.adapters.gift64_lnc_legacy import (
    GIFT64_LNC_SOURCE_SHA256,
    Gift64LNCAdapterError,
    instrument_gift64_lnc_source,
    parse_gift64_lnc_markers,
    run_gift64_lnc_observation,
)
from automated_differential_analysis.formats import (
    Gift64TrailInformationLayout,
    parse_gift64_trail_information_bytes,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GIFT_STAGE_ROOT = (
    REPOSITORY_ROOT.parent
    / "upstream"
    / "Supplementary_Material_GIFT-64_Differential"
    / "Source_code"
)
LC_STAGE = GIFT_STAGE_ROOT / "2.Finding_linear_constraints"
LNC_STAGE = (
    GIFT_STAGE_ROOT / "3.Finding_linearized_nonlinear_constraints"
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
                    cout << "$";
}
"""


class Gift64LNCUnitTests(unittest.TestCase):
    def test_hash_pinned_instrumentation_preserves_input(self) -> None:
        expected = hashlib.sha256(SYNTHETIC_SOURCE).hexdigest()

        with patch(
            "automated_differential_analysis.adapters."
            "gift64_lnc_legacy.GIFT64_LNC_SOURCE_SHA256",
            expected,
        ):
            instrumented = instrument_gift64_lnc_source(SYNTHETIC_SOURCE)

        self.assertEqual(SYNTHETIC_SOURCE.count(b"LGCA_LNC_ROW="), 0)
        self.assertEqual(instrumented.count(b"LGCA_LNC_ROW="), 1)
        self.assertEqual(len(GIFT64_LNC_SOURCE_SHA256), 64)

    def test_unpinned_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            Gift64LNCAdapterError, "source SHA-256 mismatch"
        ):
            instrument_gift64_lnc_source(SYNTHETIC_SOURCE)

    def test_marker_maps_key_columns_and_global_fixed_terms(self) -> None:
        corpus = parse_gift64_trail_information_bytes(
            SMALL_TRAIL.encode("ascii"),
            layout=SMALL_LAYOUT,
        )
        marker = (
            "LGCA_LNC_ROW=0,0;"
            "columns=580,704;rhs=0\n"
        )

        result = parse_gift64_lnc_markers(marker, corpus)[0]
        equation = result.equations[0]

        self.assertEqual(equation.variable_indices, (4,))
        self.assertEqual(equation.source_round, 5)
        self.assertEqual(equation.source_rhs, 0)
        self.assertEqual(
            tuple((item.name, item.value) for item in equation.fixed_terms),
            (("gift64.round[5].constant_unit", 1),),
        )
        self.assertEqual(equation.effective_rhs, 1)
        self.assertEqual(result.rank, 1)
        self.assertEqual(result.nullity, 127)

    def test_marker_maps_round_constant_bit(self) -> None:
        corpus = parse_gift64_trail_information_bytes(
            SMALL_TRAIL.encode("ascii"),
            layout=SMALL_LAYOUT,
        )
        # Column 716 is round offset 1, slot 5: absolute round 6,
        # six-bit GIFT round-constant bit index 4. RC[6] = 0x3d, so
        # that bit is zero.
        marker = (
            "LGCA_LNC_ROW=0,0;"
            "columns=580,716;rhs=1\n"
        )

        equation = parse_gift64_lnc_markers(marker, corpus)[0].equations[0]

        self.assertEqual(
            tuple((item.name, item.value) for item in equation.fixed_terms),
            (("gift64.round[6].constant_bit[4]", 0),),
        )
        self.assertEqual(equation.effective_rhs, 1)

    def test_unexpected_stderr_is_rejected(self) -> None:
        corpus = parse_gift64_trail_information_bytes(
            SMALL_TRAIL.encode("ascii"),
            layout=SMALL_LAYOUT,
        )

        with self.assertRaisesRegex(
            Gift64LNCAdapterError, "unexpected LNC runtime stderr"
        ):
            parse_gift64_lnc_markers("legacy warning\n", corpus)


@unittest.skipUnless(
    (LC_STAGE / "main.cpp").is_file()
    and (LC_STAGE / "TrailInformation.out").is_file()
    and (LNC_STAGE / "main.cpp").is_file()
    and (LNC_STAGE / "TrailInformation.out").is_file()
    and shutil.which("clang++") is not None,
    "read-only LC/LNC stages or C++ compiler are unavailable",
)
class Gift64LNCIntegrationTests(unittest.TestCase):
    def test_combined_spaces_extend_lc_by_rank_two(self) -> None:
        lc_observation = run_gift64_lc_observation(
            source_path=LC_STAGE / "main.cpp",
            trail_path=LC_STAGE / "TrailInformation.out",
        )
        observation = run_gift64_lnc_observation(
            source_path=LNC_STAGE / "main.cpp",
            trail_path=LNC_STAGE / "TrailInformation.out",
            lc_constraint_sets=lc_observation.constraint_sets,
        )
        first = observation.combined_constraint_sets[0]
        summary = observation.summary_dict()

        self.assertEqual(len(observation.combined_constraint_sets), 32)
        self.assertEqual(summary["equation_count"], 256)
        self.assertEqual(summary["base_rank_values"], [6])
        self.assertEqual(summary["combined_rank_values"], [8])
        self.assertEqual(summary["incremental_rank_values"], [2])
        self.assertTrue(summary["all_base_spaces_implied"])
        self.assertEqual(summary["unique_combined_semantic_spaces"], 32)
        self.assertEqual(
            observation.legacy_stdout_sha256,
            "101e0f2918d167a7e3fdc38cdc3c622d0841b9217e0f58622260982bcb42fa2f",
        )
        self.assertEqual(first.rank, 8)
        self.assertEqual(first.nullity, 120)
        self.assertEqual(
            {
                (item.variable_indices, item.effective_rhs)
                for item in first.equations
            },
            {
                ((4, 12, 38, 40, 68, 95, 121, 123), 0),
                ((12, 30, 88, 122, 123), 0),
                ((17, 25), 0),
                ((30,), 1),
                ((68, 80), 1),
                ((76,), 1),
                ((80, 88), 0),
                ((87, 95), 0),
            },
        )


if __name__ == "__main__":
    unittest.main()
