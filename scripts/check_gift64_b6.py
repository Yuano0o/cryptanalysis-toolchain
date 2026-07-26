#!/usr/bin/env python3
"""Run B5 in a temporary artifact root and check the B6 expectation."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.adapters import (  # noqa: E402
    run_controlled_gift64,
)
from shared.sat import (  # noqa: E402
    check_solver_regression,
    load_regression_expectation,
    load_solver_request,
)


def main() -> int:
    request = load_solver_request(
        REPOSITORY_ROOT
        / "experiments"
        / "gift64"
        / "sat_baseline_b2.solver_request.json"
    )
    expectation = load_regression_expectation(
        REPOSITORY_ROOT
        / "experiments"
        / "gift64"
        / "sat_baseline_b6.regression.json"
    )
    source = (
        REPOSITORY_ROOT.parent
        / "upstream"
        / "Improved_Attacks_GIFT64"
        / "Differential.cpp"
    )
    with tempfile.TemporaryDirectory(prefix="gift64-b6-") as artifact_root:
        controlled = run_controlled_gift64(
            request,
            source_path=source,
            artifact_root=Path(artifact_root),
        )
        check = check_solver_regression(
            expectation, request, controlled.result
        )
    sys.stdout.write(check.to_json())
    return 0 if check.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
