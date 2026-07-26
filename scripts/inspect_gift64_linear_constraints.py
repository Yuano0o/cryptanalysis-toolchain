#!/usr/bin/env python3
"""Run the bounded GIFT-64 LC observation and print a compact summary."""

from __future__ import annotations

import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.adapters import (  # noqa: E402
    run_gift64_lc_observation,
)


def main() -> int:
    stage = (
        REPOSITORY_ROOT.parent
        / "upstream"
        / "Supplementary_Material_GIFT-64_Differential"
        / "Source_code"
        / "2.Finding_linear_constraints"
    )
    observation = run_gift64_lc_observation(
        source_path=stage / "main.cpp",
        trail_path=stage / "TrailInformation.out",
    )
    sys.stdout.write(
        json.dumps(
            observation.summary_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
