#!/usr/bin/env python3
"""Run the bounded GIFT-64 LC/LNC comparison and print a compact summary."""

from __future__ import annotations

import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.adapters import (  # noqa: E402
    run_gift64_lc_observation,
    run_gift64_lnc_observation,
)


def main() -> int:
    source_root = (
        REPOSITORY_ROOT.parent
        / "upstream"
        / "Supplementary_Material_GIFT-64_Differential"
        / "Source_code"
    )
    lc_stage = source_root / "2.Finding_linear_constraints"
    lnc_stage = (
        source_root / "3.Finding_linearized_nonlinear_constraints"
    )
    lc_observation = run_gift64_lc_observation(
        source_path=lc_stage / "main.cpp",
        trail_path=lc_stage / "TrailInformation.out",
    )
    lnc_observation = run_gift64_lnc_observation(
        source_path=lnc_stage / "main.cpp",
        trail_path=lnc_stage / "TrailInformation.out",
        lc_constraint_sets=lc_observation.constraint_sets,
    )
    sys.stdout.write(
        json.dumps(
            lnc_observation.summary_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
