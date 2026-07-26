#!/usr/bin/env python3
"""Run the bounded, deterministic GIFT-64 Stage 2 demo without tracking output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.adapters.gift64_stage2_legacy import (  # noqa: E402
    GIFT64_STAGE2_SOLVER_VERSION,
    Gift64Stage2AdapterError,
    run_gift64_stage2_demo,
)
from automated_differential_analysis.formats import (  # noqa: E402
    Gift64Stage2DemoRequestError,
    load_gift64_stage2_demo_request,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the controlled GIFT-64 Stage 2 fixed-key demo"
    )
    parser.add_argument(
        "--request",
        type=Path,
        default=(
            REPOSITORY_ROOT / "experiments/gift64/stage2_demo_smoke_a4.request.json"
        ),
        help="versioned demo request JSON",
    )
    parser.add_argument(
        "--stage-root",
        type=Path,
        default=(
            REPOSITORY_ROOT.parent
            / "upstream/Supplementary_Material_GIFT-64_Differential/"
            "Source_code/4.Stage2_test"
        ),
        help="read-only upstream Stage 2 directory",
    )
    arguments = parser.parse_args()
    try:
        request = load_gift64_stage2_demo_request(arguments.request)
        if request.solver_version != GIFT64_STAGE2_SOLVER_VERSION:
            raise Gift64Stage2AdapterError(
                "request solver version does not match the hash-pinned adapter"
            )
        observation = run_gift64_stage2_demo(
            source_path=arguments.stage_root / "main.cpp",
            trail_path=arguments.stage_root / "TrailInformation.out",
            key_corpus_spec=request.key_corpus,
            trail_position=request.trail_position,
            per_key_time_limit_s=request.per_key_time_limit_s,
            total_time_limit_s=request.total_time_limit_s,
        )
    except (Gift64Stage2AdapterError, Gift64Stage2DemoRequestError, OSError) as exc:
        print(f"Stage 2 demo failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(observation.summary_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
