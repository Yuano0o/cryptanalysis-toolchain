#!/usr/bin/env python3
"""Run the bounded deterministic GIFT-64 Stage 3 probability demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.adapters.gift64_stage3_legacy import (  # noqa: E402
    GIFT64_STAGE3_SOLVER_VERSION,
    Gift64Stage3AdapterError,
    run_gift64_stage3_probability_demo,
)
from automated_differential_analysis.formats import (  # noqa: E402
    Gift64Stage3ProbabilityError,
    load_gift64_stage3_probability_request,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the controlled GIFT-64 Stage 3 probability demo"
    )
    parser.add_argument(
        "--request",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "experiments/gift64/stage3_probability_a5.request.json"
        ),
        help="versioned Stage 3 request JSON",
    )
    parser.add_argument(
        "--stage-root",
        type=Path,
        default=(
            REPOSITORY_ROOT.parent
            / "upstream/Supplementary_Material_GIFT-64_Differential/"
            "Source_code/5.Stage3_test"
        ),
        help="read-only upstream Stage 3 directory",
    )
    arguments = parser.parse_args()
    try:
        request = load_gift64_stage3_probability_request(arguments.request)
        if request.solver_version != GIFT64_STAGE3_SOLVER_VERSION:
            raise Gift64Stage3AdapterError(
                "request solver version does not match the hash-pinned adapter"
            )
        observation = run_gift64_stage3_probability_demo(
            source_path=arguments.stage_root / "main.cpp",
            trail_path=arguments.stage_root / "TrailInformation.out",
            key_corpus_path=arguments.stage_root / "KeyCandidate1000.out",
            request=request,
        )
    except (Gift64Stage3AdapterError, Gift64Stage3ProbabilityError, OSError) as exc:
        print(f"Stage 3 demo failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(observation.summary_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
