from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
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
        a4 = observed(
            {
                "stage": "a4",
                "status_counts": {},
                "not_started_total_budget_count": 0,
            }
        )
        a5 = observed(
            {
                "stage": "a5",
                "status_counts": {},
                "not_started_total_budget_count": 0,
                "estimate": {"point_estimate": "0"},
            }
        )
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
        self.assertEqual(observation.result_state, "complete")
        self.assertIsNone(observation.failed_stage)
        self.assertEqual(
            [stage.state for stage in observation.stages],
            ["completed"] * 5,
        )
        self.assertEqual(
            [stage.result_state for stage in observation.stages],
            ["complete"] * 5,
        )
        self.assertEqual(
            [stage.summary for stage in observation.stages],
            [
                {"stage": "a1"},
                {"stage": "a2"},
                {"stage": "a3"},
                {
                    "stage": "a4",
                    "status_counts": {},
                    "not_started_total_budget_count": 0,
                },
                {
                    "stage": "a5",
                    "status_counts": {},
                    "not_started_total_budget_count": 0,
                    "estimate": {"point_estimate": "0"},
                },
            ],
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
        self.assertEqual(observation.result_state, "not_available")
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

    def test_runner_reports_incomplete_native_results_separately(self) -> None:
        plan = load_gift64_pipeline_demo_plan(SMOKE_CONFIG)
        source_tree = Gift64PipelineSourceTree(Path("/read-only-source"))
        with (
            patch(
                "automated_differential_analysis.pipeline_runner."
                "parse_gift64_trail_information",
                return_value=observed({"stage": "a1"}),
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_lc_observation",
                return_value=observed(
                    {"stage": "a2"}, constraint_sets=("lc",)
                ),
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_lnc_observation",
                return_value=observed({"stage": "a3"}),
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_stage2_demo",
                return_value=observed(
                    {
                        "status_counts": {"ERROR": 1},
                        "not_started_total_budget_count": 7,
                    }
                ),
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_stage3_probability_demo",
                return_value=observed(
                    {
                        "status_counts": {"TIMEOUT": 1},
                        "not_started_total_budget_count": 7,
                        "estimate": None,
                    }
                ),
            ),
        ):
            observation = run_gift64_pipeline_demo(
                plan=plan, source_tree=source_tree
            )

        self.assertEqual(observation.state, "completed")
        self.assertEqual(observation.result_state, "incomplete")
        self.assertEqual(observation.stages[3].result_state, "incomplete")
        self.assertEqual(observation.stages[4].result_state, "incomplete")

    def test_runner_structures_subprocess_operational_failure(self) -> None:
        plan = load_gift64_pipeline_demo_plan(SMOKE_CONFIG)
        source_tree = Gift64PipelineSourceTree(Path("/read-only-source"))
        with (
            patch(
                "automated_differential_analysis.pipeline_runner."
                "parse_gift64_trail_information",
                return_value=observed({"stage": "a1"}),
            ),
            patch(
                "automated_differential_analysis.pipeline_runner."
                "run_gift64_lc_observation",
                side_effect=subprocess.TimeoutExpired("brew --prefix", 30),
            ),
        ):
            observation = run_gift64_pipeline_demo(
                plan=plan, source_tree=source_tree
            )

        self.assertEqual(observation.state, "failed")
        self.assertEqual(observation.result_state, "not_available")
        self.assertEqual(observation.failed_stage, "a2")
        self.assertEqual(observation.stages[1].state, "failed")
        self.assertIn(
            "TimeoutExpired", observation.stages[1].diagnostics[0]
        )


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
    def test_seven_item_acceptance_smoke(self) -> None:
        plan = load_gift64_pipeline_demo_plan(SMOKE_CONFIG)
        observation = run_gift64_pipeline_demo(
            plan=plan,
            source_tree=Gift64PipelineSourceTree(SOURCE_ROOT),
        )
        summary = observation.summary_dict()
        serialized_summary = json.loads(
            json.dumps(summary, ensure_ascii=True, sort_keys=True)
        )
        summaries = {stage.stage_id: stage.summary for stage in observation.stages}

        # Unified plan, runner, terminal semantics and generated summary.
        self.assertEqual(observation.state, "completed")
        self.assertEqual(observation.result_state, "complete")
        self.assertTrue(all(stage.state == "completed" for stage in observation.stages))
        self.assertTrue(
            all(stage.result_state == "complete" for stage in observation.stages)
        )
        self.assertEqual(serialized_summary, summary)
        self.assertEqual(
            summary["schema_version"], "gift64-pipeline-observation/v2"
        )
        self.assertEqual(
            summary["composition_mode"], "controlled-boundary-orchestration/v1"
        )
        self.assertEqual(summary["request"]["pipeline"], plan.config.to_dict())
        self.assertEqual(summary["request"]["stage2"], plan.stage2_request.to_dict())
        self.assertEqual(summary["request"]["stage3"], plan.stage3_request.to_dict())
        self.assertEqual(
            [stage["stage_id"] for stage in summary["stages"]],
            ["a1", "a2", "a3", "a4", "a5"],
        )
        self.assertIn("not a paper-level reproduction", summary["claim_boundary"])

        # A1-A3 fixture identity, LNC semantics and the LC/LNC association rule.
        self.assertEqual(summaries["a1"]["record_count"], 32)
        self.assertEqual(
            summaries["a1"]["source_sha256"],
            plan.config.trail_information_source_sha256,
        )
        self.assertEqual(summaries["a2"]["constraint_set_count"], 32)
        self.assertEqual(summaries["a2"]["rank_values"], [6])
        self.assertEqual(
            summaries["a2"]["trail_source_sha256"],
            plan.config.trail_information_source_sha256,
        )
        self.assertEqual(summaries["a3"]["constraint_set_count"], 32)
        self.assertEqual(summaries["a3"]["base_rank_values"], [6])
        self.assertEqual(summaries["a3"]["combined_rank_values"], [8])
        self.assertEqual(summaries["a3"]["incremental_rank_values"], [2])
        self.assertTrue(summaries["a3"]["all_base_spaces_implied"])
        self.assertEqual(
            summaries["a3"]["trail_source_sha256"],
            plan.config.trail_information_source_sha256,
        )

        # Stage 2 configurable deterministic key corpus and complete accounting.
        self.assertEqual(
            summaries["a4"]["key_corpus"],
            plan.stage2_request.key_corpus.to_dict(),
        )
        self.assertEqual(
            summaries["a4"]["trail_position"], plan.config.trail_position
        )
        self.assertEqual(
            sum(summaries["a4"]["status_counts"].values())
            + summaries["a4"]["not_started_total_budget_count"],
            plan.stage2_request.key_corpus.key_count,
        )
        self.assertEqual(
            len(summaries["a4"]["results"]),
            plan.stage2_request.key_corpus.key_count,
        )
        self.assertEqual(
            summaries["a4"]["trail_source_sha256"],
            plan.config.trail_information_source_sha256,
        )

        # Stage 3 fixed seed, unified probability result and complete accounting.
        self.assertEqual(
            summaries["a5"]["request"], plan.stage3_request.to_dict()
        )
        self.assertEqual(
            len(summaries["a5"]["samples"]), plan.stage3_request.repeat_count
        )
        self.assertEqual(summaries["a5"]["not_started_total_budget_count"], 0)
        self.assertIsNotNone(summaries["a5"]["estimate"])
        self.assertEqual(
            summaries["a5"]["estimate"]["completed_sample_count"],
            plan.stage3_request.repeat_count,
        )
        self.assertTrue(
            all(sample["complete"] for sample in summaries["a5"]["samples"])
        )
        self.assertEqual(
            summaries["a5"]["trail_source_sha256"],
            plan.config.trail_information_source_sha256,
        )


if __name__ == "__main__":
    unittest.main()
