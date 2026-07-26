"""Controlled, bounded observation boundary for GIFT-64 legacy Stage 2.

The upstream program hard-codes an unavailable million-key corpus and silently
tests only trail position zero.  This adapter hash-pins that source, creates a
temporary one-key/one-trail copy, and records the native SAT result for each
key in a deterministic demo corpus.  It does not modify the upstream tree or
claim to reproduce the unavailable author corpus.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

from automated_differential_analysis.formats import (
    DEFAULT_GIFT64_TRAIL_INFORMATION_LAYOUT,
    GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
    Gift64Stage2KeyCorpusSpec,
    Gift64TrailInformationCorpus,
    generate_stage2_key_corpus,
    parse_gift64_trail_information,
    stage2_key_corpus_legacy_bytes,
)
from shared.sat import SolverStatus


GIFT64_STAGE2_ADAPTER_VERSION = "gift64-stage2-legacy-adapter/v1"
GIFT64_STAGE2_OBSERVATION_SCHEMA_VERSION = "gift64-stage2-observation/v2"
GIFT64_STAGE2_SOURCE_SHA256 = (
    "58f5d24110cf8170de6cc0f1cdd29657abc1463bf044703756e052b640275964"
)
GIFT64_STAGE2_TRAIL_SHA256 = GIFT64_TRAIL_INFORMATION_SOURCE_SHA256
GIFT64_STAGE2_SOLVER_VERSION = "5.14.7"
_KEY_BUFFER_LINE = "int AllTestKeyValue[1000000][8];"
_KEY_LOOP_FRAGMENT = "testkeyindex < 1000000"
_TRAIL_LOOP_LINE = "for (int trail = 0; trail < 1; trail++)//TrailPerGroup"
_SOLVE_LINE = "            lbool ret = solver.solve();"
_STATUS_PREFIX = "LGCA_STAGE2_STATUS="
_STATUS_RE = re.compile(
    r"^LGCA_STAGE2_STATUS=(?P<key_index>[0-9]+),(?P<trail_position>[0-9]+),"
    r"(?P<status>SAT|UNSAT|UNKNOWN)$"
)
_SOLVER_VERSION_RE = re.compile(r"CryptoMiniSat version ([0-9][0-9.]*)")
_COMPILE_GUARD_S = 60.0


class Gift64Stage2AdapterError(ValueError):
    """Raised when Stage 2 cannot be observed without ambiguity."""


@dataclass(frozen=True)
class Gift64Stage2KeyResult:
    """One controlled SAT query for one generated primary master key."""

    key_index: int
    execution_state: str
    status: SolverStatus | None
    wall_time_s: float
    cpu_time_s: float
    exit_code: int | None
    stdout_sha256: str | None
    diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.key_index, bool) or not isinstance(self.key_index, int):
            raise Gift64Stage2AdapterError("key_index must be an integer")
        if self.key_index < 0:
            raise Gift64Stage2AdapterError("key_index must be non-negative")
        if self.execution_state not in {"ran", "not_started_total_budget"}:
            raise Gift64Stage2AdapterError("unsupported Stage 2 execution state")
        if self.execution_state == "ran" and not isinstance(self.status, SolverStatus):
            raise Gift64Stage2AdapterError("ran key result must carry a SolverStatus")
        if self.execution_state == "not_started_total_budget":
            if self.status is not None:
                raise Gift64Stage2AdapterError(
                    "unstarted key result must not carry a solver status"
                )
            if any((self.wall_time_s, self.cpu_time_s)) or self.exit_code is not None:
                raise Gift64Stage2AdapterError(
                    "unstarted key result must not carry execution measurements"
                )
        if self.wall_time_s < 0 or self.cpu_time_s < 0:
            raise Gift64Stage2AdapterError("run times must be non-negative")
        if self.stdout_sha256 is not None and re.fullmatch(
            r"[0-9a-f]{64}", self.stdout_sha256
        ) is None:
            raise Gift64Stage2AdapterError("stdout_sha256 must be a SHA-256 or null")

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_index": self.key_index,
            "execution_state": self.execution_state,
            "status": None if self.status is None else self.status.value,
            "wall_time_s": self.wall_time_s,
            "cpu_time_s": self.cpu_time_s,
            "exit_code": self.exit_code,
            "stdout_sha256": self.stdout_sha256,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class Gift64Stage2Observation:
    """Provenanced result summary for a bounded Stage 2 demo run."""

    adapter_version: str
    source_sha256: str
    trail_source_sha256: str
    key_corpus_sha256: str
    key_corpus_spec: Gift64Stage2KeyCorpusSpec
    trail_position: int
    solver_version: str
    per_key_time_limit_s: float
    total_time_limit_s: float
    results: tuple[Gift64Stage2KeyResult, ...]
    compile_wall_time_s: float
    run_wall_time_s: float
    total_time_budget_exhausted: bool
    instrumented_source_sha256: str

    def __post_init__(self) -> None:
        if self.adapter_version != GIFT64_STAGE2_ADAPTER_VERSION:
            raise Gift64Stage2AdapterError("unsupported Stage 2 adapter version")
        for field_name in (
            "source_sha256",
            "trail_source_sha256",
            "key_corpus_sha256",
            "instrumented_source_sha256",
        ):
            if re.fullmatch(r"[0-9a-f]{64}", getattr(self, field_name)) is None:
                raise Gift64Stage2AdapterError(f"{field_name} must be a SHA-256")
        if not isinstance(self.key_corpus_spec, Gift64Stage2KeyCorpusSpec):
            raise Gift64Stage2AdapterError(
                "key_corpus_spec must be a Gift64Stage2KeyCorpusSpec"
            )
        if (
            isinstance(self.trail_position, bool)
            or not isinstance(self.trail_position, int)
            or self.trail_position < 0
        ):
            raise Gift64Stage2AdapterError("trail_position must be non-negative")
        if self.per_key_time_limit_s <= 0:
            raise Gift64Stage2AdapterError("per_key_time_limit_s must be positive")
        if self.total_time_limit_s <= 0:
            raise Gift64Stage2AdapterError("total_time_limit_s must be positive")
        if self.compile_wall_time_s < 0:
            raise Gift64Stage2AdapterError("compile_wall_time_s must be non-negative")
        if self.run_wall_time_s < 0:
            raise Gift64Stage2AdapterError("run_wall_time_s must be non-negative")
        if len(self.results) != self.key_corpus_spec.key_count:
            raise Gift64Stage2AdapterError(
                "Stage 2 result count must match the configured key corpus"
            )
        if tuple(item.key_index for item in self.results) != tuple(
            range(self.key_corpus_spec.key_count)
        ):
            raise Gift64Stage2AdapterError("Stage 2 result key indices must be sequential")

    def summary_dict(self) -> dict[str, Any]:
        status_counts = {
            status.value: sum(
                item.execution_state == "ran" and item.status is status
                for item in self.results
            )
            for status in SolverStatus
        }
        return {
            "schema_version": GIFT64_STAGE2_OBSERVATION_SCHEMA_VERSION,
            "adapter_version": self.adapter_version,
            "scope": "generated-for-demo fixed-key validation",
            "source_sha256": self.source_sha256,
            "trail_source_sha256": self.trail_source_sha256,
            "key_corpus_sha256": self.key_corpus_sha256,
            "key_corpus": self.key_corpus_spec.to_dict(),
            "trail_position": self.trail_position,
            "solver_version": self.solver_version,
            "per_key_time_limit_s": self.per_key_time_limit_s,
            "total_time_limit_s": self.total_time_limit_s,
            "compile_wall_time_s": self.compile_wall_time_s,
            "run_wall_time_s": self.run_wall_time_s,
            "total_time_budget_exhausted": self.total_time_budget_exhausted,
            "instrumented_source_sha256": self.instrumented_source_sha256,
            "status_counts": status_counts,
            "not_started_total_budget_count": sum(
                item.execution_state == "not_started_total_budget"
                for item in self.results
            ),
            "results": [item.to_dict() for item in self.results],
            "claim_boundary": (
                "native solver statuses for a generated demo corpus; not a "
                "reproduction of the missing author KeyCandidate.out experiment"
            ),
        }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def instrument_gift64_stage2_source(source: bytes, *, trail_position: int) -> bytes:
    """Return a pinned, temporary source copy that runs one key and one trail."""

    if _sha256(source) != GIFT64_STAGE2_SOURCE_SHA256:
        raise Gift64Stage2AdapterError(
            "Stage 2 source SHA-256 mismatch: "
            f"expected {GIFT64_STAGE2_SOURCE_SHA256}, got {_sha256(source)}"
        )
    if isinstance(trail_position, bool) or not isinstance(trail_position, int):
        raise Gift64Stage2AdapterError("trail_position must be an integer")
    if not 0 <= trail_position < DEFAULT_GIFT64_TRAIL_INFORMATION_LAYOUT.record_count:
        raise Gift64Stage2AdapterError("trail_position is outside the 32-trail corpus")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Gift64Stage2AdapterError("Stage 2 source must be UTF-8") from exc
    if text.count(_KEY_BUFFER_LINE) != 1:
        raise Gift64Stage2AdapterError("expected one pinned Stage 2 key buffer")
    if text.count(_KEY_LOOP_FRAGMENT) != 2:
        raise Gift64Stage2AdapterError("expected two pinned Stage 2 key loops")
    if text.count(_TRAIL_LOOP_LINE) != 1:
        raise Gift64Stage2AdapterError("expected one pinned Stage 2 trail loop")
    if text.count(_SOLVE_LINE) != 1:
        raise Gift64Stage2AdapterError("expected one pinned solver.solve() call")
    text = text.replace(_KEY_BUFFER_LINE, "int AllTestKeyValue[1][8];", 1)
    text = text.replace(_KEY_LOOP_FRAGMENT, "testkeyindex < 1")
    text = text.replace(
        _TRAIL_LOOP_LINE,
        "for (int trail = "
        f"{trail_position}; trail < {trail_position + 1}; trail++)//TrailPerGroup",
        1,
    )
    instrumentation = """            lbool ret = solver.solve();
            cerr<<\"LGCA_STAGE2_STATUS=\"<<testkeyindex<<\",\"<<trail<<\",\";
            if (ret == l_True)
            {
                cerr<<\"SAT\";
            }
            else if (ret == l_False)
            {
                cerr<<\"UNSAT\";
            }
            else
            {
                cerr<<\"UNKNOWN\";
            }
            cerr<<\"\\n\";"""
    return text.replace(_SOLVE_LINE, instrumentation, 1).encode("utf-8")


def parse_stage2_status_marker(
    stderr: str, *, expected_key_index: int, expected_trail_position: int
) -> SolverStatus:
    """Read exactly one adapter-owned native solver status marker."""

    markers = [
        _STATUS_RE.fullmatch(line)
        for line in stderr.splitlines()
        if line.startswith(_STATUS_PREFIX)
    ]
    if len(markers) != 1 or markers[0] is None:
        raise Gift64Stage2AdapterError(
            f"expected exactly one Stage 2 status marker, got {len(markers)}"
        )
    marker = markers[0]
    assert marker is not None
    if int(marker.group("key_index")) != expected_key_index:
        raise Gift64Stage2AdapterError("Stage 2 status marker has wrong key index")
    if int(marker.group("trail_position")) != expected_trail_position:
        raise Gift64Stage2AdapterError("Stage 2 status marker has wrong trail position")
    return SolverStatus(marker.group("status"))


def _formula_prefix(formula: str) -> Path:
    brew = shutil.which("brew")
    if brew is None:
        raise Gift64Stage2AdapterError("Homebrew is not available")
    try:
        completed = subprocess.run(
            [brew, "--prefix", formula],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise Gift64Stage2AdapterError(
            f"timed out resolving Homebrew prefix for {formula}"
        ) from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        raise Gift64Stage2AdapterError(f"cannot resolve Homebrew prefix for {formula}")
    return Path(completed.stdout.strip())


def _installed_solver_version(cms_prefix: Path) -> str:
    try:
        completed = subprocess.run(
            [str(cms_prefix / "bin" / "cryptominisat5"), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise Gift64Stage2AdapterError(
            "timed out determining installed CryptoMiniSat version"
        ) from exc
    match = _SOLVER_VERSION_RE.search(completed.stdout + "\n" + completed.stderr)
    if completed.returncode != 0 or match is None:
        raise Gift64Stage2AdapterError("cannot determine installed CryptoMiniSat version")
    return match.group(1)


def _cpu_time(before: os.times_result, after: os.times_result) -> float:
    return max(
        0.0,
        after.children_user
        + after.children_system
        - before.children_user
        - before.children_system,
    )


def _compile_timeout_exhausted_total_budget(
    remaining_before_compile: float,
) -> bool:
    """Distinguish the total budget from the independent compile guard."""

    return remaining_before_compile <= _COMPILE_GUARD_S


def _run_one_key(
    executable: Path,
    build_root: Path,
    key_words: tuple[int, ...],
    *,
    key_index: int,
    trail_position: int,
    time_limit_s: float,
    timeout_reason: str,
) -> Gift64Stage2KeyResult:
    (build_root / "KeyCandidate.out").write_bytes(
        stage2_key_corpus_legacy_bytes((key_words,))
    )
    before_cpu = os.times()
    start = time.monotonic()
    try:
        completed = subprocess.run(
            [str(executable)],
            cwd=build_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=time_limit_s,
        )
    except subprocess.TimeoutExpired:
        return Gift64Stage2KeyResult(
            key_index=key_index,
            execution_state="ran",
            status=SolverStatus.TIMEOUT,
            wall_time_s=time.monotonic() - start,
            cpu_time_s=_cpu_time(before_cpu, os.times()),
            exit_code=None,
            stdout_sha256=None,
            diagnostics=(timeout_reason,),
        )
    wall_time_s = time.monotonic() - start
    cpu_time_s = _cpu_time(before_cpu, os.times())
    stdout_sha256 = _sha256(completed.stdout.encode("utf-8"))
    if completed.returncode != 0:
        return Gift64Stage2KeyResult(
            key_index=key_index,
            execution_state="ran",
            status=SolverStatus.ERROR,
            wall_time_s=wall_time_s,
            cpu_time_s=cpu_time_s,
            exit_code=completed.returncode,
            stdout_sha256=stdout_sha256,
            diagnostics=("Stage 2 process returned a nonzero exit code",),
        )
    try:
        status = parse_stage2_status_marker(
            completed.stderr,
            expected_key_index=0,
            expected_trail_position=trail_position,
        )
    except Gift64Stage2AdapterError as exc:
        return Gift64Stage2KeyResult(
            key_index=key_index,
            execution_state="ran",
            status=SolverStatus.ERROR,
            wall_time_s=wall_time_s,
            cpu_time_s=cpu_time_s,
            exit_code=completed.returncode,
            stdout_sha256=stdout_sha256,
            diagnostics=(str(exc),),
        )
    return Gift64Stage2KeyResult(
        key_index=key_index,
        execution_state="ran",
        status=status,
        wall_time_s=wall_time_s,
        cpu_time_s=cpu_time_s,
        exit_code=completed.returncode,
        stdout_sha256=stdout_sha256,
        diagnostics=("native status from hash-pinned temporary instrumentation",),
    )


def _not_started_total_budget_result(key_index: int) -> Gift64Stage2KeyResult:
    """Record a key skipped before process launch because total budget ended."""

    return Gift64Stage2KeyResult(
        key_index=key_index,
        execution_state="not_started_total_budget",
        status=None,
        wall_time_s=0.0,
        cpu_time_s=0.0,
        exit_code=None,
        stdout_sha256=None,
        diagnostics=("Stage 2 total run time budget was exhausted before launch",),
    )


def run_gift64_stage2_demo(
    *,
    source_path: Path,
    trail_path: Path,
    key_corpus_spec: Gift64Stage2KeyCorpusSpec,
    trail_position: int,
    per_key_time_limit_s: float,
    total_time_limit_s: float,
    compiler: str = "clang++",
    cms_prefix: Path | None = None,
    gmp_prefix: Path | None = None,
) -> Gift64Stage2Observation:
    """Compile one controlled source copy and query every generated demo key."""

    if per_key_time_limit_s <= 0:
        raise Gift64Stage2AdapterError("per_key_time_limit_s must be positive")
    if total_time_limit_s <= 0:
        raise Gift64Stage2AdapterError("total_time_limit_s must be positive")
    if not isinstance(key_corpus_spec, Gift64Stage2KeyCorpusSpec):
        raise Gift64Stage2AdapterError(
            "key_corpus_spec must be a Gift64Stage2KeyCorpusSpec"
        )
    run_start = time.monotonic()
    source = source_path.read_bytes()
    instrumented = instrument_gift64_stage2_source(
        source, trail_position=trail_position
    )
    corpus: Gift64TrailInformationCorpus = parse_gift64_trail_information(
        trail_path, expected_source_sha256=GIFT64_STAGE2_TRAIL_SHA256
    )
    if not 0 <= trail_position < len(corpus.records):
        raise Gift64Stage2AdapterError("trail_position is outside the parsed corpus")
    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise Gift64Stage2AdapterError(f"compiler is not available: {compiler}")
    cms_prefix = cms_prefix or _formula_prefix("cryptominisat")
    gmp_prefix = gmp_prefix or _formula_prefix("gmp")
    solver_version = _installed_solver_version(cms_prefix)
    if solver_version != GIFT64_STAGE2_SOLVER_VERSION:
        raise Gift64Stage2AdapterError(
            "CryptoMiniSat version mismatch: "
            f"expected {GIFT64_STAGE2_SOLVER_VERSION}, got {solver_version}"
        )
    keys = generate_stage2_key_corpus(key_corpus_spec)
    key_corpus_bytes = stage2_key_corpus_legacy_bytes(keys)
    total_time_budget_exhausted = False
    with tempfile.TemporaryDirectory(prefix="gift64-stage2-") as temporary_directory:
        build_root = Path(temporary_directory)
        temporary_source = build_root / "main.instrumented.cpp"
        executable = build_root / "gift64_stage2"
        temporary_source.write_bytes(instrumented)
        (build_root / "TrailInformation.out").write_bytes(trail_path.read_bytes())
        compile_command = [
            compiler_path,
            "-std=c++17",
            "-O2",
            f"-I{cms_prefix / 'include'}",
            f"-I{gmp_prefix / 'include'}",
            str(temporary_source),
            f"-L{cms_prefix / 'lib'}",
            f"-L{gmp_prefix / 'lib'}",
            f"-Wl,-rpath,{cms_prefix / 'lib'}",
            f"-Wl,-rpath,{gmp_prefix / 'lib'}",
            "-lcryptominisat5",
            "-lgmpxx",
            "-lgmp",
            "-o",
            str(executable),
        ]
        remaining_before_compile = total_time_limit_s - (time.monotonic() - run_start)
        if remaining_before_compile <= 0:
            compile_wall_time_s = 0.0
            total_time_budget_exhausted = True
            results = tuple(_not_started_total_budget_result(index) for index in range(len(keys)))
        else:
            compile_start = time.monotonic()
            try:
                compiled = subprocess.run(
                    compile_command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=min(_COMPILE_GUARD_S, remaining_before_compile),
                )
            except subprocess.TimeoutExpired as exc:
                compile_wall_time_s = time.monotonic() - compile_start
                if not _compile_timeout_exhausted_total_budget(
                    remaining_before_compile
                ):
                    raise Gift64Stage2AdapterError(
                        "temporary Stage 2 compilation exceeded the "
                        f"{_COMPILE_GUARD_S:g}-second compile guard"
                    ) from exc
                total_time_budget_exhausted = True
                results = tuple(
                    _not_started_total_budget_result(index)
                    for index in range(len(keys))
                )
            else:
                compile_wall_time_s = time.monotonic() - compile_start
                if compiled.returncode != 0:
                    raise Gift64Stage2AdapterError(
                        "temporary Stage 2 compilation failed: " + compiled.stderr.strip()
                    )
                result_items: list[Gift64Stage2KeyResult] = []
                for key_index, key_words in enumerate(keys):
                    remaining = total_time_limit_s - (time.monotonic() - run_start)
                    if remaining <= 0:
                        total_time_budget_exhausted = True
                        result_items.extend(
                            _not_started_total_budget_result(index)
                            for index in range(key_index, len(keys))
                        )
                        break
                    time_limit_s = min(per_key_time_limit_s, remaining)
                    timeout_reason = (
                        "Stage 2 total run time budget was exhausted during this key"
                        if remaining < per_key_time_limit_s
                        else "Stage 2 process exceeded per-key timeout"
                    )
                    result = _run_one_key(
                        executable,
                        build_root,
                        key_words,
                        key_index=key_index,
                        trail_position=trail_position,
                        time_limit_s=time_limit_s,
                        timeout_reason=timeout_reason,
                    )
                    result_items.append(result)
                    if result.status is SolverStatus.TIMEOUT and remaining < per_key_time_limit_s:
                        total_time_budget_exhausted = True
                results = tuple(result_items)
    run_wall_time_s = time.monotonic() - run_start
    return Gift64Stage2Observation(
        adapter_version=GIFT64_STAGE2_ADAPTER_VERSION,
        source_sha256=_sha256(source),
        trail_source_sha256=_sha256(trail_path.read_bytes()),
        key_corpus_sha256=_sha256(key_corpus_bytes),
        key_corpus_spec=key_corpus_spec,
        trail_position=trail_position,
        solver_version=solver_version,
        per_key_time_limit_s=per_key_time_limit_s,
        total_time_limit_s=total_time_limit_s,
        results=results,
        compile_wall_time_s=compile_wall_time_s,
        run_wall_time_s=run_wall_time_s,
        total_time_budget_exhausted=total_time_budget_exhausted,
        instrumented_source_sha256=_sha256(instrumented),
    )
