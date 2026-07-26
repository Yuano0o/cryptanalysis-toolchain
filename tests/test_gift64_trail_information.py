from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from automated_differential_analysis.formats import (
    GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
    Gift64TrailInformationError,
    Gift64TrailInformationLayout,
    parse_gift64_trail_information,
    parse_gift64_trail_information_bytes,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_ROOT = (
    REPOSITORY_ROOT.parent
    / "upstream"
    / "Supplementary_Material_GIFT-64_Differential"
    / "Source_code"
)
UPSTREAM_COPIES = (
    UPSTREAM_ROOT / "2.Finding_linear_constraints" / "TrailInformation.out",
    UPSTREAM_ROOT
    / "3.Finding_linearized_nonlinear_constraints"
    / "TrailInformation.out",
    UPSTREAM_ROOT / "4.Stage2_test" / "TrailInformation.out",
    UPSTREAM_ROOT / "5.Stage3_test" / "TrailInformation.out",
)

SMALL_LAYOUT = Gift64TrailInformationLayout(
    group_count=1,
    trails_per_group=1,
    round_start=5,
    round_count=2,
    key_state_anchor_round=4,
)
SMALL_FIXTURE = """0000 0000 0000 0000 0000 0000 000a 0000
0000 0000 0000 0001
0000 0000 0000 0002
0000 0000 0000 0002
0000 0000 0000 0004"""


class Gift64TrailInformationUnitTests(unittest.TestCase):
    def test_small_fixture_preserves_words_bits_nibbles_and_rounds(self) -> None:
        data = SMALL_FIXTURE.encode("ascii")

        corpus = parse_gift64_trail_information_bytes(
            data,
            layout=SMALL_LAYOUT,
            expected_source_sha256=hashlib.sha256(data).hexdigest(),
        )
        record = corpus.record(0, 0)

        self.assertEqual(corpus.schema_version, "gift64-trail-information/v1")
        self.assertEqual(record.key_state_anchor_round, 4)
        self.assertEqual(record.key_state_difference_words[6], 0x000A)
        self.assertEqual(record.rounds[0].absolute_round, 5)
        self.assertEqual(record.rounds[1].absolute_round, 6)
        self.assertEqual(record.rounds[0].input_state.hex_state, "0" * 15 + "1")
        self.assertEqual(record.rounds[0].input_state.nibbles[-1], 1)
        self.assertEqual(record.rounds[0].input_state.bits[-1], 1)
        self.assertEqual(record.rounds[0].input_state.bits[:-1], (0,) * 63)

    def test_missing_final_newline_and_trailing_spaces_are_accepted(self) -> None:
        with_spaces = "\n".join(
            line + " " for line in SMALL_FIXTURE.splitlines()
        ).encode("ascii")

        corpus = parse_gift64_trail_information_bytes(
            with_spaces, layout=SMALL_LAYOUT
        )

        self.assertEqual(len(corpus.records), 1)

    def test_broken_round_continuity_is_rejected(self) -> None:
        broken = SMALL_FIXTURE.replace(
            "0000 0000 0000 0002\n0000 0000 0000 0002",
            "0000 0000 0000 0002\n0000 0000 0000 0003",
        )

        with self.assertRaisesRegex(
            Gift64TrailInformationError, "continuity"
        ):
            parse_gift64_trail_information_bytes(
                broken.encode("ascii"), layout=SMALL_LAYOUT
            )

    def test_invalid_word_width_is_rejected(self) -> None:
        broken = SMALL_FIXTURE.replace("000a", "00a", 1)

        with self.assertRaisesRegex(
            Gift64TrailInformationError, "invalid 16-bit hex word"
        ):
            parse_gift64_trail_information_bytes(
                broken.encode("ascii"), layout=SMALL_LAYOUT
            )

    def test_wrong_line_count_is_rejected(self) -> None:
        broken = "\n".join(SMALL_FIXTURE.splitlines()[:-1])

        with self.assertRaisesRegex(
            Gift64TrailInformationError, "expected 5 logical lines"
        ):
            parse_gift64_trail_information_bytes(
                broken.encode("ascii"), layout=SMALL_LAYOUT
            )

    def test_source_hash_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            Gift64TrailInformationError, "source SHA-256 mismatch"
        ):
            parse_gift64_trail_information_bytes(
                SMALL_FIXTURE.encode("ascii"),
                layout=SMALL_LAYOUT,
                expected_source_sha256="0" * 64,
            )


@unittest.skipUnless(
    UPSTREAM_COPIES[0].is_file(),
    "read-only supplementary TrailInformation.out is not present",
)
class Gift64TrailInformationIntegrationTests(unittest.TestCase):
    def test_all_four_upstream_copies_are_byte_identical(self) -> None:
        hashes = {
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in UPSTREAM_COPIES
        }

        self.assertEqual(hashes, {GIFT64_TRAIL_INFORMATION_SOURCE_SHA256})

    def test_upstream_corpus_has_expected_structure(self) -> None:
        corpus = parse_gift64_trail_information(
            UPSTREAM_COPIES[0],
            expected_source_sha256=GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
        )

        self.assertEqual(len(corpus.records), 32)
        self.assertEqual(corpus.layout.group_count, 8)
        self.assertEqual(corpus.layout.trails_per_group, 4)
        self.assertEqual(corpus.layout.round_start, 5)
        self.assertEqual(corpus.layout.round_end, 13)
        self.assertEqual(corpus.layout.key_state_anchor_round, 4)
        self.assertEqual(
            corpus.summary_dict()["unique_key_state_differences"], 8
        )
        self.assertEqual(
            [
                corpus.record(group, 0).key_state_difference_words[6]
                for group in range(8)
            ],
            [0x000A, 0x0005, 0x00A0, 0x0050, 0x0A00, 0x0500, 0xA000, 0x5000],
        )


if __name__ == "__main__":
    unittest.main()
