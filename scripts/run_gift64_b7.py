#!/usr/bin/env python3
"""Run a bounded 1-thread versus 2-thread GIFT-64 B7 comparison."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from automated_differential_analysis.adapters import (  # noqa: E402
    run_controlled_gift64,
)
from shared.sat import (  # noqa: E402
    SolverResult,
    SolverStatus,
    VerificationStatus,
    load_solver_request,
)


def _checked_summary(
    results: list[SolverResult], threads: int
) -> dict[str, Any]:
    if not results:
        raise ValueError("B7 configuration produced no results")
    semantics = {
        (
            result.status.value,
            result.definitive,
            tuple(sorted((result.objective_components or {}).items())),
            result.satisfied_bound,
            result.verification.status.value,
            result.exact_label_eligible,
        )
        for result in results
    }
    if len(semantics) != 1:
        raise ValueError("B7 repetitions disagree on normalized semantics")
    required = (
        SolverStatus.SAT.value,
        True,
        True,
        VerificationStatus.PASSED.value,
        True,
    )
    result = results[0]
    observed = (
        result.status.value,
        result.definitive,
        result.satisfied_bound,
        result.verification.status.value,
        result.exact_label_eligible,
    )
    if observed != required:
        raise ValueError("B7 result is not a verified bound-satisfying SAT")
    wall_times = [item.wall_time_s for item in results]
    cpu_times = [item.cpu_time_s for item in results]
    compile_times = [
        float(item.solver_statistics["compile_wall_time_s"])
        for item in results
    ]
    return {
        "threads": threads,
        "repetitions": len(results),
        "status": result.status.value,
        "objective_components": dict(sorted((result.objective_components or {}).items())),
        "verification": result.verification.status.value,
        "wall_time_s": {
            "min": min(wall_times),
            "median": statistics.median(wall_times),
            "max": max(wall_times),
        },
        "cpu_time_s": {
            "min": min(cpu_times),
            "median": statistics.median(cpu_times),
            "max": max(cpu_times),
        },
        "compile_wall_time_s": {
            "min": min(compile_times),
            "median": statistics.median(compile_times),
            "max": max(compile_times),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--baseline-threads", type=int, default=1)
    parser.add_argument("--alternative-threads", type=int, default=2)
    arguments = parser.parse_args()
    if arguments.repetitions < 2:
        parser.error("--repetitions must be at least 2")
    if min(arguments.baseline_threads, arguments.alternative_threads) < 1:
        parser.error("thread counts must be positive")
    if arguments.baseline_threads == arguments.alternative_threads:
        parser.error("B7 requires two distinct thread configurations")

    request = load_solver_request(
        REPOSITORY_ROOT
        / "experiments"
        / "gift64"
        / "sat_baseline_b2.solver_request.json"
    )
    source = (
        REPOSITORY_ROOT.parent
        / "upstream"
        / "Improved_Attacks_GIFT64"
        / "Differential.cpp"
    )
    results_by_threads: dict[int, list[SolverResult]] = {
        arguments.baseline_threads: [],
        arguments.alternative_threads: [],
    }
    for repetition in range(arguments.repetitions):
        thread_order = (
            (arguments.baseline_threads, arguments.alternative_threads)
            if repetition % 2 == 0
            else (arguments.alternative_threads, arguments.baseline_threads)
        )
        for threads in thread_order:
            configured = replace(
                request,
                request_id=f"{request.request_id}-b7-t{threads}",
                solver=replace(request.solver, threads=threads),
            )
            with tempfile.TemporaryDirectory(prefix="gift64-b7-") as root:
                controlled = run_controlled_gift64(
                    configured,
                    source_path=source,
                    artifact_root=Path(root),
                )
            results_by_threads[threads].append(controlled.result)

    baseline = _checked_summary(
        results_by_threads[arguments.baseline_threads],
        arguments.baseline_threads,
    )
    alternative = _checked_summary(
        results_by_threads[arguments.alternative_threads],
        arguments.alternative_threads,
    )
    output = {
        "comparison": "same source/instance/solver/version/limit; threads only",
        "execution_order": "alternating configurations by repetition",
        "machine": {
            "logical_cpus": os.cpu_count(),
            "platform": os.uname().sysname,
            "release": os.uname().release,
        },
        "source_sha256": request.source.source_sha256,
        "solver": request.solver.name,
        "solver_version": request.solver.version,
        "time_limit_s": request.resources.time_limit_s,
        "baseline": baseline,
        "alternative": alternative,
        "median_wall_speedup": (
            baseline["wall_time_s"]["median"]
            / alternative["wall_time_s"]["median"]
        ),
        "interpretation": (
            "descriptive only; legacy source does not set an explicit solver seed"
        ),
    }
    sys.stdout.write(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
