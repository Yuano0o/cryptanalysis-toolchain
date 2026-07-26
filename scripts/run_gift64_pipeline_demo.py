#!/usr/bin/env python3
"""Run the controlled unified GIFT-64 A1-A5 smoke or formal demo plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.formats import (  # noqa: E402
    Gift64PipelineDemoError,
    load_gift64_pipeline_demo_plan,
)
from automated_differential_analysis.pipeline_runner import (  # noqa: E402
    Gift64PipelineRunnerError,
    Gift64PipelineSourceTree,
    run_gift64_pipeline_demo,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the controlled GIFT-64 A1-A5 pipeline demo"
    )
    parser.add_argument(
        "--request",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "experiments/gift64/pipeline_demo_smoke_a1_a5.request.json"
        ),
        help="unified smoke or formal pipeline request JSON",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=(
            REPOSITORY_ROOT.parent
            / "upstream/Supplementary_Material_GIFT-64_Differential/Source_code"
        ),
        help="read-only supplementary GIFT-64 Source_code directory",
    )
    arguments = parser.parse_args()
    try:
        plan = load_gift64_pipeline_demo_plan(arguments.request)
        observation = run_gift64_pipeline_demo(
            plan=plan,
            source_tree=Gift64PipelineSourceTree(arguments.source_root),
        )
    except (Gift64PipelineDemoError, Gift64PipelineRunnerError, OSError) as exc:
        print(f"GIFT-64 pipeline demo failed to start: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(observation.summary_dict(), ensure_ascii=True, indent=2, sort_keys=True))
    return (
        0
        if observation.state == "completed"
        and observation.result_state == "complete"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
