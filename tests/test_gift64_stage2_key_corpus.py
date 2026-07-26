from __future__ import annotations

import hashlib
import unittest

from automated_differential_analysis.formats import (
    GIFT64_STAGE2_DEMO_GENERATOR_ID,
    GIFT64_STAGE2_DEMO_PURPOSE,
    GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION,
    GIFT64_STAGE2_MAX_DEMO_KEY_COUNT,
    Gift64Stage2KeyCorpusError,
    Gift64Stage2KeyCorpusSpec,
    generate_stage2_key_corpus,
    generated_stage2_key_corpus_bytes,
    parse_stage2_key_corpus_bytes,
    stage2_key_corpus_legacy_bytes,
)


def demo_spec(*, seed: int = 20260726, key_count: int = 2) -> Gift64Stage2KeyCorpusSpec:
    return Gift64Stage2KeyCorpusSpec(
        schema_version=GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION,
        purpose=GIFT64_STAGE2_DEMO_PURPOSE,
        generator_id=GIFT64_STAGE2_DEMO_GENERATOR_ID,
        seed=seed,
        key_count=key_count,
    )


class Gift64Stage2KeyCorpusTests(unittest.TestCase):
    def test_sha256_counter_generator_has_stable_two_key_fixture(self) -> None:
        data = generated_stage2_key_corpus_bytes(demo_spec())

        self.assertEqual(
            data,
            b"7fde 638a 52bc 2b03 f690 dab7 4f38 87bb\n"
            b"71c9 ae3e 8bcc f16b 7178 e78d b7f6 f22a\n",
        )
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            "c0972685b79f93e68dca0f05437eeab1ec737eb5b1217195babdab845bc80ba5",
        )

    def test_encoding_round_trips_generated_keys(self) -> None:
        keys = generate_stage2_key_corpus(demo_spec(key_count=3))
        data = stage2_key_corpus_legacy_bytes(keys)

        self.assertEqual(parse_stage2_key_corpus_bytes(data, expected_key_count=3), keys)

    def test_seed_and_position_change_key_material(self) -> None:
        first = generate_stage2_key_corpus(demo_spec(seed=1, key_count=2))
        second = generate_stage2_key_corpus(demo_spec(seed=2, key_count=2))

        self.assertNotEqual(first[0], first[1])
        self.assertNotEqual(first[0], second[0])

    def test_parser_rejects_incomplete_or_ambiguous_records(self) -> None:
        with self.assertRaisesRegex(Gift64Stage2KeyCorpusError, "eight words"):
            parse_stage2_key_corpus_bytes(b"0000 0001\n")
        with self.assertRaisesRegex(Gift64Stage2KeyCorpusError, "blank"):
            parse_stage2_key_corpus_bytes(
                b"0000 0000 0000 0000 0000 0000 0000 0000\n\n"
            )
        with self.assertRaisesRegex(Gift64Stage2KeyCorpusError, "end with one newline"):
            parse_stage2_key_corpus_bytes(
                b"0000 0000 0000 0000 0000 0000 0000 0000"
            )

    def test_spec_rejects_non_demo_or_nonportable_generator(self) -> None:
        with self.assertRaisesRegex(Gift64Stage2KeyCorpusError, "purpose"):
            Gift64Stage2KeyCorpusSpec(
                GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION,
                "paper-reproduction",
                GIFT64_STAGE2_DEMO_GENERATOR_ID,
                0,
                1,
            )
        with self.assertRaisesRegex(Gift64Stage2KeyCorpusError, "generator"):
            Gift64Stage2KeyCorpusSpec(
                GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION,
                GIFT64_STAGE2_DEMO_PURPOSE,
                "python-random",
                0,
                1,
            )

    def test_spec_rejects_key_count_above_demo_resource_bound(self) -> None:
        with self.assertRaisesRegex(
            Gift64Stage2KeyCorpusError, "bounded demo maximum"
        ):
            demo_spec(key_count=GIFT64_STAGE2_MAX_DEMO_KEY_COUNT + 1)


if __name__ == "__main__":
    unittest.main()
