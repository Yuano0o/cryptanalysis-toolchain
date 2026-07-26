#!/usr/bin/env python3
"""Run the controlled GIFT-64 B5 adapter and print SolverResult JSON."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.adapters import (  # noqa: E402
    run_controlled_gift64,
)
from shared.sat import SolverStatus, load_solver_request  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the controlled four-round GIFT-64 SAT baseline"
    )
    parser.add_argument(
        "--request",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "experiments"
            / "gift64"
            / "sat_baseline_b2.solver_request.json"
        ),
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=(
            REPOSITORY_ROOT.parent
            / "upstream"
            / "Improved_Attacks_GIFT64"
            / "Differential.cpp"
        ),
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        required=True,
        help="untracked root for the decoded TrailRecord artifact",
    )
    arguments = parser.parse_args()
    artifact_root = arguments.artifact_root.resolve()
    if artifact_root.is_relative_to(REPOSITORY_ROOT.resolve()):
        parser.error("--artifact-root must be outside the Git repository")

    request = load_solver_request(arguments.request)
    controlled = run_controlled_gift64(
        request,
        source_path=arguments.source,
        artifact_root=artifact_root,
    )
    sys.stdout.write(controlled.result.to_json())
    return 0 if controlled.result.status in {
        SolverStatus.SAT,
        SolverStatus.UNSAT,
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
