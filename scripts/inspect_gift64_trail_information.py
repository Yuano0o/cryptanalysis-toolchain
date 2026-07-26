#!/usr/bin/env python3
"""Validate the bundled TrailInformation.out and print a compact summary."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.formats import (  # noqa: E402
    GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
    parse_gift64_trail_information,
)


def main() -> int:
    source = (
        REPOSITORY_ROOT.parent
        / "upstream"
        / "Supplementary_Material_GIFT-64_Differential"
        / "Source_code"
        / "2.Finding_linear_constraints"
        / "TrailInformation.out"
    )
    corpus = parse_gift64_trail_information(
        source,
        expected_source_sha256=GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
    )
    sys.stdout.write(corpus.summary_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
