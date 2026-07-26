from __future__ import annotations

import unittest

from automated_differential_analysis.formats import (
    GIFT64_STAGE2_DEMO_REQUEST_SCHEMA_VERSION,
    GIFT64_STAGE2_DEMO_GENERATOR_ID,
    GIFT64_STAGE2_DEMO_PURPOSE,
    GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION,
    Gift64Stage2DemoRequest,
    Gift64Stage2DemoRequestError,
)


def valid_request() -> dict[str, object]:
    return {
        "schema_version": GIFT64_STAGE2_DEMO_REQUEST_SCHEMA_VERSION,
        "request_id": "gift64-stage2-demo-test",
        "trail_position": 0,
        "key_corpus": {
            "schema_version": GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION,
            "purpose": GIFT64_STAGE2_DEMO_PURPOSE,
            "generator_id": GIFT64_STAGE2_DEMO_GENERATOR_ID,
            "seed": 1,
            "key_count": 2,
        },
        "solver": {"name": "cryptominisat", "version": "5.14.7"},
        "resources": {"per_key_time_limit_s": 3.0, "total_time_limit_s": 10.0},
    }


class Gift64Stage2DemoRequestTests(unittest.TestCase):
    def test_request_round_trips_canonically(self) -> None:
        request = Gift64Stage2DemoRequest.from_dict(valid_request())
        self.assertEqual(
            Gift64Stage2DemoRequest.from_json(request.to_json()).to_dict(),
            request.to_dict(),
        )

    def test_request_rejects_unknown_fields_and_non_cryptominisat(self) -> None:
        data = valid_request()
        data["extra"] = True
        with self.assertRaisesRegex(Gift64Stage2DemoRequestError, "unknown"):
            Gift64Stage2DemoRequest.from_dict(data)
        data = valid_request()
        data["solver"] = {"name": "cadical", "version": "1"}
        with self.assertRaisesRegex(Gift64Stage2DemoRequestError, "cryptominisat"):
            Gift64Stage2DemoRequest.from_dict(data)
        data = valid_request()
        data["trail_position"] = 32
        with self.assertRaisesRegex(Gift64Stage2DemoRequestError, "0..31"):
            Gift64Stage2DemoRequest.from_dict(data)

    def test_request_requires_finite_total_time_budget(self) -> None:
        data = valid_request()
        data["resources"]["total_time_limit_s"] = float("inf")
        with self.assertRaisesRegex(Gift64Stage2DemoRequestError, "positive"):
            Gift64Stage2DemoRequest.from_dict(data)


if __name__ == "__main__":
    unittest.main()
