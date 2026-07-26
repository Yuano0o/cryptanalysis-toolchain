from __future__ import annotations

from pathlib import Path
import unittest

from automated_differential_analysis.formats import (
    GIFT64_PIPELINE_COMPOSITION_MODE,
    Gift64PipelineDemoConfig,
    Gift64PipelineDemoError,
    load_gift64_pipeline_demo_config,
    load_gift64_pipeline_demo_plan,
)
from automated_differential_analysis.formats.gift64_stage2_demo_request import (
    load_gift64_stage2_demo_request,
)
from automated_differential_analysis.formats.gift64_stage3_probability import (
    load_gift64_stage3_probability_request,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPOSITORY_ROOT / "experiments" / "gift64"
SMOKE_CONFIG = EXPERIMENT_ROOT / "pipeline_demo_smoke_a1_a5.request.json"
FORMAL_CONFIG = EXPERIMENT_ROOT / "pipeline_demo_formal_a1_a5.request.json"


class Gift64PipelineDemoTests(unittest.TestCase):
    def test_smoke_configuration_round_trips_and_resolves_shared_trail(self) -> None:
        config = load_gift64_pipeline_demo_config(SMOKE_CONFIG)
        plan = load_gift64_pipeline_demo_plan(SMOKE_CONFIG)

        self.assertEqual(
            Gift64PipelineDemoConfig.from_json(config.to_json()).to_dict(),
            config.to_dict(),
        )
        self.assertEqual(config.profile, "smoke")
        self.assertEqual(config.composition_mode, GIFT64_PIPELINE_COMPOSITION_MODE)
        self.assertEqual(plan.stage2_request.key_corpus.key_count, 8)
        self.assertEqual(plan.stage3_request.repeat_count, 8)
        self.assertEqual(plan.stage2_request.trail_position, config.trail_position)
        self.assertEqual(plan.stage3_request.trail_position, config.trail_position)

    def test_formal_configuration_resolves_declared_sample_counts(self) -> None:
        plan = load_gift64_pipeline_demo_plan(FORMAL_CONFIG)

        self.assertEqual(plan.config.profile, "formal")
        self.assertEqual(plan.stage2_request.key_corpus.key_count, 1000)
        self.assertEqual(plan.stage3_request.repeat_count, 100)

    def test_config_rejects_traversal_and_disabled_required_stage(self) -> None:
        data = load_gift64_pipeline_demo_config(SMOKE_CONFIG).to_dict()
        data["stages"]["a4"]["request_path"] = "../stage2.json"
        with self.assertRaisesRegex(Gift64PipelineDemoError, "traversal"):
            Gift64PipelineDemoConfig.from_dict(data)
        data = load_gift64_pipeline_demo_config(SMOKE_CONFIG).to_dict()
        data["stages"]["a3"]["enabled"] = False
        with self.assertRaisesRegex(Gift64PipelineDemoError, "must be true"):
            Gift64PipelineDemoConfig.from_dict(data)
        data = load_gift64_pipeline_demo_config(SMOKE_CONFIG).to_dict()
        data["composition_mode"] = "strict-a4-a5-lineage"
        with self.assertRaisesRegex(Gift64PipelineDemoError, "composition mode"):
            Gift64PipelineDemoConfig.from_dict(data)

    def test_plan_rejects_profile_sample_count_mismatch(self) -> None:
        config = load_gift64_pipeline_demo_config(SMOKE_CONFIG)
        stage2 = load_gift64_stage2_demo_request(
            EXPERIMENT_ROOT / config.stage2_request_path
        )
        stage3 = load_gift64_stage3_probability_request(
            EXPERIMENT_ROOT / "stage3_probability_a5.request.json"
        )
        from automated_differential_analysis.formats.gift64_pipeline_demo import (
            Gift64PipelineDemoPlan,
        )

        with self.assertRaisesRegex(Gift64PipelineDemoError, "repeat_count"):
            Gift64PipelineDemoPlan(
                config=config,
                stage2_request=stage2,
                stage3_request=stage3,
            )


if __name__ == "__main__":
    unittest.main()
