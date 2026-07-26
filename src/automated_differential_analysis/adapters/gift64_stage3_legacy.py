"""Controlled, deterministic observation boundary for GIFT-64 legacy Stage 3.

The legacy program estimates a remaining fixed-key trail probability by
counting solutions inside random 43-bit input subcubes. It uses an unrecorded
``random_device`` source and only one hard-coded key/trail. This adapter keeps
the supplied key fixture read-only, makes the choices explicit, replaces the
entropy source in a temporary copy, and reports each complete or incomplete
subcube count separately.
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
    GIFT64_STAGE3_PROBABILITY_OBSERVATION_SCHEMA_VERSION,
    GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
    Gift64Stage3ProbabilityRequest,
    Gift64TrailInformationCorpus,
    SubcubeProbabilityEstimate,
    estimate_subcube_probability,
    parse_gift64_trail_information,
    parse_stage2_key_corpus,
)
from shared.sat import SolverStatus


GIFT64_STAGE3_ADAPTER_VERSION = "gift64-stage3-legacy-adapter/v1"
GIFT64_STAGE3_SOURCE_SHA256 = (
    "40b71f4fd21798bcae68bcd76922e788eb19f795d5a0e788abd0cc721c6f81ca"
)
GIFT64_STAGE3_TRAIL_SHA256 = GIFT64_TRAIL_INFORMATION_SOURCE_SHA256
GIFT64_STAGE3_KEY_CORPUS_SHA256 = (
    "d97ee7bedccfe2f8d6df9e48a2da7e0bdb6524cfe1188e8e5e6bf8a8107d761e"
)
GIFT64_STAGE3_SOLVER_VERSION = "5.14.7"
_REPEAT_DEFINE = "#define RepeatTestTime 100"
_FIXED_BITS_DEFINE = "#define RandomFixBitNum 21"
_KEY_DEFINE = "#define TargetKeyIndex 0"
_TRAIL_DEFINE = "#define TestTrailIndex 0"
_RANDOM_DEVICE_LINE = "                random_device rand;"
_COUNT_LINE = '                cout<<"Number of Solution: "<<(dec)<<Solution << endl;'
_SAMPLE_PREFIX = "LGCA_STAGE3_SAMPLE="
_SAMPLE_RE = re.compile(
    r"^LGCA_STAGE3_SAMPLE=(?P<sample>[0-9]+);key=(?P<key>[0-9]+);"
    r"trail=(?P<trail>[0-9]+);fixed=(?P<fixed>[0-9:,]*);"
    r"solutions=(?P<solutions>[0-9]+);terminal=(?P<terminal>UNSAT|UNKNOWN)$"
)
_SOLVER_VERSION_RE = re.compile(r"CryptoMiniSat version ([0-9][0-9.]*)")


class Gift64Stage3AdapterError(ValueError):
    """Raised when Stage 3 cannot be observed with clear count semantics."""


@dataclass(frozen=True)
class Gift64Stage3SampleResult:
    sample_index: int
    terminal_status: SolverStatus
    fixed_assignments: tuple[tuple[int, int], ...]
    solution_count: int | None
    wall_time_s: float
    cpu_time_s: float
    exit_code: int | None
    stdout_sha256: str | None
    diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.sample_index, bool) or not isinstance(self.sample_index, int):
            raise Gift64Stage3AdapterError("sample_index must be an integer")
        if self.sample_index < 0:
            raise Gift64Stage3AdapterError("sample_index must be non-negative")
        if not isinstance(self.terminal_status, SolverStatus):
            raise Gift64Stage3AdapterError("terminal_status must be a SolverStatus")
        if self.solution_count is not None and (
            isinstance(self.solution_count, bool)
            or not isinstance(self.solution_count, int)
            or self.solution_count < 0
        ):
            raise Gift64Stage3AdapterError("solution_count must be non-negative or null")
        if self.terminal_status is SolverStatus.UNSAT and self.solution_count is None:
            raise Gift64Stage3AdapterError(
                "a complete UNSAT enumeration must provide solution_count"
            )
        if self.wall_time_s < 0 or self.cpu_time_s < 0:
            raise Gift64Stage3AdapterError("run times must be non-negative")
        seen_bits: set[int] = set()
        for bit, value in self.fixed_assignments:
            if not 0 <= bit < 64 or value not in {0, 1} or bit in seen_bits:
                raise Gift64Stage3AdapterError("fixed assignments are malformed")
            seen_bits.add(bit)

    @property
    def complete(self) -> bool:
        return self.terminal_status is SolverStatus.UNSAT

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_index": self.sample_index,
            "terminal_status": self.terminal_status.value,
            "complete": self.complete,
            "fixed_assignments": [
                {"bit": bit, "value": value}
                for bit, value in self.fixed_assignments
            ],
            "solution_count": self.solution_count,
            "wall_time_s": self.wall_time_s,
            "cpu_time_s": self.cpu_time_s,
            "exit_code": self.exit_code,
            "stdout_sha256": self.stdout_sha256,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class Gift64Stage3Observation:
    adapter_version: str
    source_sha256: str
    trail_source_sha256: str
    key_corpus_sha256: str
    request: Gift64Stage3ProbabilityRequest
    solver_version: str
    instrumented_source_sha256: str
    compile_wall_time_s: float
    samples: tuple[Gift64Stage3SampleResult, ...]
    estimate: SubcubeProbabilityEstimate | None

    def __post_init__(self) -> None:
        if self.adapter_version != GIFT64_STAGE3_ADAPTER_VERSION:
            raise Gift64Stage3AdapterError("unsupported Stage 3 adapter version")
        if not isinstance(self.request, Gift64Stage3ProbabilityRequest):
            raise Gift64Stage3AdapterError(
                "request must be a Gift64Stage3ProbabilityRequest"
            )
        for field_name in (
            "source_sha256",
            "trail_source_sha256",
            "key_corpus_sha256",
            "instrumented_source_sha256",
        ):
            if re.fullmatch(r"[0-9a-f]{64}", getattr(self, field_name)) is None:
                raise Gift64Stage3AdapterError(f"{field_name} must be a SHA-256")
        if self.compile_wall_time_s < 0:
            raise Gift64Stage3AdapterError("compile_wall_time_s must be non-negative")
        if len(self.samples) != self.request.repeat_count:
            raise Gift64Stage3AdapterError("sample count must match request repeats")
        if tuple(item.sample_index for item in self.samples) != tuple(
            range(self.request.repeat_count)
        ):
            raise Gift64Stage3AdapterError("sample indices must be sequential")
        if any(
            len(item.fixed_assignments) != self.request.fixed_bit_count
            for item in self.samples
            if item.solution_count is not None
        ):
            raise Gift64Stage3AdapterError(
                "complete sample fixed-bit counts must match request"
            )
        complete = tuple(
            item.solution_count
            for item in self.samples
            if item.complete and item.solution_count is not None
        )
        if self.estimate is not None and len(complete) != len(self.samples):
            raise Gift64Stage3AdapterError(
                "an estimate is invalid when any sample is incomplete"
            )

    def summary_dict(self) -> dict[str, Any]:
        status_counts = {
            status.value: sum(item.terminal_status is status for item in self.samples)
            for status in SolverStatus
        }
        return {
            "schema_version": GIFT64_STAGE3_PROBABILITY_OBSERVATION_SCHEMA_VERSION,
            "adapter_version": self.adapter_version,
            "scope": "provided-fixture deterministic subcube probability estimate",
            "source_sha256": self.source_sha256,
            "trail_source_sha256": self.trail_source_sha256,
            "key_corpus_sha256": self.key_corpus_sha256,
            "request": self.request.to_dict(),
            "solver_version": self.solver_version,
            "instrumented_source_sha256": self.instrumented_source_sha256,
            "compile_wall_time_s": self.compile_wall_time_s,
            "status_counts": status_counts,
            "estimate": None if self.estimate is None else self.estimate.to_dict(),
            "samples": [item.to_dict() for item in self.samples],
            "claim_boundary": (
                "descriptive fixed-key subcube sampling estimate from the supplied "
                "KeyCandidate1000 fixture; not exact counting, a proof, or a "
                "paper-level probability reproduction"
            ),
        }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def instrument_gift64_stage3_source(
    source: bytes, *, request: Gift64Stage3ProbabilityRequest
) -> bytes:
    """Bind one key/trail, one sample per process and deterministic sampling."""

    if _sha256(source) != GIFT64_STAGE3_SOURCE_SHA256:
        raise Gift64Stage3AdapterError(
            "Stage 3 source SHA-256 mismatch: "
            f"expected {GIFT64_STAGE3_SOURCE_SHA256}, got {_sha256(source)}"
        )
    if not isinstance(request, Gift64Stage3ProbabilityRequest):
        raise Gift64Stage3AdapterError(
            "request must be a Gift64Stage3ProbabilityRequest"
        )
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Gift64Stage3AdapterError("Stage 3 source must be UTF-8") from exc
    anchors = (
        _REPEAT_DEFINE,
        _FIXED_BITS_DEFINE,
        _KEY_DEFINE,
        _TRAIL_DEFINE,
        _RANDOM_DEVICE_LINE,
        _COUNT_LINE,
    )
    if any(text.count(anchor) != 1 for anchor in anchors):
        raise Gift64Stage3AdapterError("one or more pinned Stage 3 source anchors changed")
    text = text.replace(_REPEAT_DEFINE, "#define RepeatTestTime 1", 1)
    text = text.replace(
        _FIXED_BITS_DEFINE, f"#define RandomFixBitNum {request.fixed_bit_count}", 1
    )
    text = text.replace(_KEY_DEFINE, f"#define TargetKeyIndex {request.key_position}", 1)
    text = text.replace(
        _TRAIL_DEFINE, f"#define TestTrailIndex {request.trail_position}", 1
    )
    deterministic_rng = f"""                const char* lgca_sample_env = getenv("LGCA_STAGE3_SAMPLE_INDEX");
                if (lgca_sample_env == NULL)
                {{
                    cerr<<"LGCA_STAGE3_ERROR=missing-sample-index\\n";
                    return 2;
                }}
                const unsigned long long lgca_sample_index = strtoull(lgca_sample_env, NULL, 10);
                mt19937_64 rand(0x{request.sampling_seed:016x}ULL ^
                    (lgca_sample_index * 0x9e3779b97f4a7c15ULL));"""
    text = text.replace(_RANDOM_DEVICE_LINE, deterministic_rng, 1)
    marker = """                cerr<<"LGCA_STAGE3_SAMPLE="<<lgca_sample_index
                    <<";key="<<testkeyindex<<";trail="<<trail<<";fixed=";
                for (int bit = 0; bit < RandomFixBitNum; bit++)
                {
                    if (bit > 0)
                    {
                        cerr<<",";
                    }
                    cerr<<RandomFixBitIndex[bit]<<":"<<RandomFixValue[bit];
                }
                cerr<<";solutions="<<Solution<<";terminal=";
                if (ret == l_False)
                {
                    cerr<<"UNSAT";
                }
                else
                {
                    cerr<<"UNKNOWN";
                }
                cerr<<"\\n";"""
    text = text.replace(_COUNT_LINE, _COUNT_LINE + "\n" + marker, 1)
    return text.encode("utf-8")


def parse_stage3_sample_marker(
    stderr: str,
    *,
    expected_sample_index: int,
    expected_key_position: int,
    expected_trail_position: int,
    expected_fixed_bit_count: int,
) -> tuple[SolverStatus, tuple[tuple[int, int], ...], int]:
    """Parse one adapter marker and validate the sampled subcube exactly."""

    matches = [
        _SAMPLE_RE.fullmatch(line)
        for line in stderr.splitlines()
        if line.startswith(_SAMPLE_PREFIX)
    ]
    if len(matches) != 1 or matches[0] is None:
        raise Gift64Stage3AdapterError(
            f"expected exactly one Stage 3 sample marker, got {len(matches)}"
        )
    marker = matches[0]
    assert marker is not None
    if int(marker.group("sample")) != expected_sample_index:
        raise Gift64Stage3AdapterError("Stage 3 marker has wrong sample index")
    if int(marker.group("key")) != expected_key_position:
        raise Gift64Stage3AdapterError("Stage 3 marker has wrong key position")
    if int(marker.group("trail")) != expected_trail_position:
        raise Gift64Stage3AdapterError("Stage 3 marker has wrong trail position")
    assignments: list[tuple[int, int]] = []
    fixed_text = marker.group("fixed")
    if fixed_text:
        for item in fixed_text.split(","):
            bit_text, separator, value_text = item.partition(":")
            if not separator or not bit_text.isdigit() or value_text not in {"0", "1"}:
                raise Gift64Stage3AdapterError("Stage 3 marker has malformed fixed bits")
            assignments.append((int(bit_text), int(value_text)))
    if len(assignments) != expected_fixed_bit_count:
        raise Gift64Stage3AdapterError("Stage 3 marker has wrong fixed-bit count")
    if len({bit for bit, _ in assignments}) != len(assignments) or any(
        not 0 <= bit < 64 for bit, _ in assignments
    ):
        raise Gift64Stage3AdapterError("Stage 3 marker has invalid fixed-bit indices")
    terminal = SolverStatus(marker.group("terminal"))
    return terminal, tuple(assignments), int(marker.group("solutions"))


def _formula_prefix(formula: str) -> Path:
    brew = shutil.which("brew")
    if brew is None:
        raise Gift64Stage3AdapterError("Homebrew is not available")
    completed = subprocess.run(
        [brew, "--prefix", formula],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise Gift64Stage3AdapterError(f"cannot resolve Homebrew prefix for {formula}")
    return Path(completed.stdout.strip())


def _installed_solver_version(cms_prefix: Path) -> str:
    completed = subprocess.run(
        [str(cms_prefix / "bin" / "cryptominisat5"), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    match = _SOLVER_VERSION_RE.search(completed.stdout + "\n" + completed.stderr)
    if completed.returncode != 0 or match is None:
        raise Gift64Stage3AdapterError("cannot determine installed CryptoMiniSat version")
    return match.group(1)


def _cpu_time(before: os.times_result, after: os.times_result) -> float:
    return max(
        0.0,
        after.children_user
        + after.children_system
        - before.children_user
        - before.children_system,
    )


def _run_one_sample(
    executable: Path,
    build_root: Path,
    *,
    request: Gift64Stage3ProbabilityRequest,
    sample_index: int,
) -> Gift64Stage3SampleResult:
    before_cpu = os.times()
    start = time.monotonic()
    try:
        completed = subprocess.run(
            [str(executable)],
            cwd=build_root,
            env={**os.environ, "LGCA_STAGE3_SAMPLE_INDEX": str(sample_index)},
            check=False,
            capture_output=True,
            text=True,
            timeout=request.per_sample_time_limit_s,
        )
    except subprocess.TimeoutExpired:
        return Gift64Stage3SampleResult(
            sample_index=sample_index,
            terminal_status=SolverStatus.TIMEOUT,
            fixed_assignments=(),
            solution_count=None,
            wall_time_s=time.monotonic() - start,
            cpu_time_s=_cpu_time(before_cpu, os.times()),
            exit_code=None,
            stdout_sha256=None,
            diagnostics=("Stage 3 process exceeded per-sample timeout",),
        )
    wall_time_s = time.monotonic() - start
    cpu_time_s = _cpu_time(before_cpu, os.times())
    stdout_sha256 = _sha256(completed.stdout.encode("utf-8"))
    if completed.returncode != 0:
        return Gift64Stage3SampleResult(
            sample_index=sample_index,
            terminal_status=SolverStatus.ERROR,
            fixed_assignments=(),
            solution_count=None,
            wall_time_s=wall_time_s,
            cpu_time_s=cpu_time_s,
            exit_code=completed.returncode,
            stdout_sha256=stdout_sha256,
            diagnostics=("Stage 3 process returned a nonzero exit code",),
        )
    try:
        terminal, assignments, solution_count = parse_stage3_sample_marker(
            completed.stderr,
            expected_sample_index=sample_index,
            expected_key_position=request.key_position,
            expected_trail_position=request.trail_position,
            expected_fixed_bit_count=request.fixed_bit_count,
        )
    except Gift64Stage3AdapterError as exc:
        return Gift64Stage3SampleResult(
            sample_index=sample_index,
            terminal_status=SolverStatus.ERROR,
            fixed_assignments=(),
            solution_count=None,
            wall_time_s=wall_time_s,
            cpu_time_s=cpu_time_s,
            exit_code=completed.returncode,
            stdout_sha256=stdout_sha256,
            diagnostics=(str(exc),),
        )
    return Gift64Stage3SampleResult(
        sample_index=sample_index,
        terminal_status=terminal,
        fixed_assignments=assignments,
        solution_count=solution_count,
        wall_time_s=wall_time_s,
        cpu_time_s=cpu_time_s,
        exit_code=completed.returncode,
        stdout_sha256=stdout_sha256,
        diagnostics=(
            "solution enumeration ended with native status from temporary instrumentation",
        ),
    )


def run_gift64_stage3_probability_demo(
    *,
    source_path: Path,
    trail_path: Path,
    key_corpus_path: Path,
    request: Gift64Stage3ProbabilityRequest,
    compiler: str = "clang++",
    cms_prefix: Path | None = None,
    gmp_prefix: Path | None = None,
) -> Gift64Stage3Observation:
    """Run a deterministic bounded subcube-counting estimate over one fixture key."""

    if not isinstance(request, Gift64Stage3ProbabilityRequest):
        raise Gift64Stage3AdapterError(
            "request must be a Gift64Stage3ProbabilityRequest"
        )
    source = source_path.read_bytes()
    instrumented = instrument_gift64_stage3_source(source, request=request)
    corpus: Gift64TrailInformationCorpus = parse_gift64_trail_information(
        trail_path, expected_source_sha256=GIFT64_STAGE3_TRAIL_SHA256
    )
    if not 0 <= request.trail_position < len(corpus.records):
        raise Gift64Stage3AdapterError("trail_position is outside the parsed corpus")
    key_fixture = key_corpus_path.read_bytes()
    if _sha256(key_fixture) != GIFT64_STAGE3_KEY_CORPUS_SHA256:
        raise Gift64Stage3AdapterError("Stage 3 key fixture SHA-256 mismatch")
    parse_stage2_key_corpus(key_corpus_path, expected_key_count=1000)
    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise Gift64Stage3AdapterError(f"compiler is not available: {compiler}")
    cms_prefix = cms_prefix or _formula_prefix("cryptominisat")
    gmp_prefix = gmp_prefix or _formula_prefix("gmp")
    solver_version = _installed_solver_version(cms_prefix)
    if solver_version != GIFT64_STAGE3_SOLVER_VERSION:
        raise Gift64Stage3AdapterError(
            "CryptoMiniSat version mismatch: "
            f"expected {GIFT64_STAGE3_SOLVER_VERSION}, got {solver_version}"
        )
    with tempfile.TemporaryDirectory(prefix="gift64-stage3-") as temporary_directory:
        build_root = Path(temporary_directory)
        temporary_source = build_root / "main.instrumented.cpp"
        executable = build_root / "gift64_stage3"
        temporary_source.write_bytes(instrumented)
        (build_root / "TrailInformation.out").write_bytes(trail_path.read_bytes())
        (build_root / "KeyCandidate1000.out").write_bytes(key_fixture)
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
        compile_start = time.monotonic()
        try:
            compiled = subprocess.run(
                compile_command,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            raise Gift64Stage3AdapterError(
                "temporary Stage 3 compilation timed out"
            ) from exc
        compile_wall_time_s = time.monotonic() - compile_start
        if compiled.returncode != 0:
            raise Gift64Stage3AdapterError(
                "temporary Stage 3 compilation failed: " + compiled.stderr.strip()
            )
        samples = tuple(
            _run_one_sample(
                executable, build_root, request=request, sample_index=sample_index
            )
            for sample_index in range(request.repeat_count)
        )
    complete_counts = tuple(
        item.solution_count
        for item in samples
        if item.complete and item.solution_count is not None
    )
    estimate: SubcubeProbabilityEstimate | None = None
    if len(complete_counts) == len(samples):
        estimate = estimate_subcube_probability(
            complete_counts, fixed_bit_count=request.fixed_bit_count
        )
    return Gift64Stage3Observation(
        adapter_version=GIFT64_STAGE3_ADAPTER_VERSION,
        source_sha256=_sha256(source),
        trail_source_sha256=_sha256(trail_path.read_bytes()),
        key_corpus_sha256=_sha256(key_fixture),
        request=request,
        solver_version=solver_version,
        instrumented_source_sha256=_sha256(instrumented),
        compile_wall_time_s=compile_wall_time_s,
        samples=samples,
        estimate=estimate,
    )
