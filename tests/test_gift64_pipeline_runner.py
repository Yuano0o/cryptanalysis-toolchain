from __future__ import annotations

from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from automated_differential_analysis.formats import load_gift64_pipeline_demo_plan
from automated_differential_analysis.pipeline_runner import (
    Gift64PipelineSourceTree,
    run_gift64_pipeline_demo,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SMOKE_CONFIG = (
    REPOSITORY_ROOT
    / "experiments/gift64/pipeline_demo_smoke_a1_a5.request.json"
)
SOURCE_ROOT = (
    REPOSITORY_ROOT.parent
    / "upstream"
    / "Supplementary_Material_GIFT-64_Differential"
    / "Source_code"
)


def observed(summary: dict[str, object], **fields: object) -> SimpleNamespace:
    return SimpleNamespace(summary_dict=lambda: summary, **fields)


class Gift64PipelineRunnerTests(unittest.TestCase):
    def test_runner_composes_all_stage_summaries_in_order(self) -> None:
        plan = load_gift64_pipeline_demo_plan(SMOKE_CONFIG)
        source_tree = Gift64PipelineSourceTree(Path("/read-only-source"))
        a1 = observed({"stage": "a1"})
        a2 = observed({"stage": "a2"}, constraint_sets=("lc",))
        a3 = observed({"stage": "a3"})
        a4 = observed({"stage": "a4"})
        a5 = observed({"stage": "a5"})
        with (
            patch(
                "automated_differential_analysis.pipeline_runner."
                "parse_gift64_trail_information",
                return_value=a1,
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_lc_observation",
                return_value=a2,
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_lnc_observation",
                return_value=a3,
            ) as lnc,
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_stage2_demo",
                return_value=a4,
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_stage3_probability_demo",
                return_value=a5,
            ),
        ):
            observation = run_gift64_pipeline_demo(
                plan=plan, source_tree=source_tree
            )

        self.assertEqual(observation.state, "completed")
        self.assertIsNone(observation.failed_stage)
        self.assertEqual(
            [stage.state for stage in observation.stages],
            ["completed"] * 5,
        )
        self.assertEqual(
            [stage.summary for stage in observation.stages],
            [{"stage": "a1"}, {"stage": "a2"}, {"stage": "a3"}, {"stage": "a4"}, {"stage": "a5"}],
        )
        self.assertEqual(lnc.call_args.kwargs["lc_constraint_sets"], ("lc",))

    def test_runner_stops_after_failed_stage_and_marks_descendants_skipped(self) -> None:
        plan = load_gift64_pipeline_demo_plan(SMOKE_CONFIG)
        source_tree = Gift64PipelineSourceTree(Path("/read-only-source"))
        a1 = observed({"stage": "a1"})
        with (
            patch(
                "automated_differential_analysis.pipeline_runner."
                "parse_gift64_trail_information",
                return_value=a1,
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_lc_observation",
                side_effect=ValueError("synthetic LC failure"),
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_lnc_observation",
            ) as lnc,
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_stage2_demo",
            ) as stage2,
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_stage3_probability_demo",
            ) as stage3,
        ):
            observation = run_gift64_pipeline_demo(
                plan=plan, source_tree=source_tree
            )

        self.assertEqual(observation.state, "failed")
        self.assertEqual(observation.failed_stage, "a2")
        self.assertEqual(
            [stage.state for stage in observation.stages],
            [
                "completed",
                "failed",
                "not_run_upstream_failure",
                "not_run_upstream_failure",
                "not_run_upstream_failure",
            ],
        )
        self.assertIn("synthetic LC failure", observation.stages[1].diagnostics[0])
        lnc.assert_not_called()
        stage2.assert_not_called()
        stage3.assert_not_called()


@unittest.skipUnless(
    (SOURCE_ROOT / "2.Finding_linear_constraints" / "main.cpp").is_file()
    and (SOURCE_ROOT / "3.Finding_linearized_nonlinear_constraints" / "main.cpp").is_file()
    and (SOURCE_ROOT / "4.Stage2_test" / "main.cpp").is_file()
    and (SOURCE_ROOT / "5.Stage3_test" / "KeyCandidate1000.out").is_file()
    and shutil.which("clang++") is not None
    and shutil.which("brew") is not None,
    "read-only supplementary source, compiler or Homebrew is unavailable",
)
class Gift64PipelineRunnerIntegrationTests(unittest.TestCase):
    def test_smoke_plan_completes_all_a1_a5_stages(self) -> None:
        observation = run_gift64_pipeline_demo(
            plan=load_gift64_pipeline_demo_plan(SMOKE_CONFIG),
            source_tree=Gift64PipelineSourceTree(SOURCE_ROOT),
        )
        summaries = {stage.stage_id: stage.summary for stage in observation.stages}

        self.assertEqual(observation.state, "completed")
        self.assertTrue(all(stage.state == "completed" for stage in observation.stages))
        self.assertEqual(summaries["a1"]["record_count"], 32)
        self.assertTrue(summaries["a3"]["all_base_spaces_implied"])
        self.assertEqual(
            sum(summaries["a4"]["status_counts"].values())
            + summaries["a4"]["not_started_total_budget_count"],
            8,
        )
        self.assertEqual(len(summaries["a5"]["samples"]), 8)


if __name__ == "__main__":
    unittest.main()
