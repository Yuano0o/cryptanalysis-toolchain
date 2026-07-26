"""Controlled boundary around the archived GIFT-64 CryptoMiniSat program.

The adapter never edits the read-only upstream source. It verifies the pinned
source hash, creates a temporary instrumented copy that reports CryptoMiniSat's
three-valued return status, compiles that copy, decodes stdout, and validates
the decoded trail independently.
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

from shared.ciphers.gift64 import (
    GIFT64_BIT_ORDER_ID,
    GIFT64_NIBBLE_ORDER_ID,
    GIFT64_STATE_LAYOUT_ID,
    verify_gift64_four_round_trail,
)
from shared.sat import (
    ArtifactReference,
    SolverRequest,
    SolverResult,
    SolverStatus,
    VerificationResult,
    VerificationStatus,
)
from shared.trails import TRAIL_SCHEMA_VERSION, TrailRecord, TrailRound


ADAPTER_VERSION = "gift64-improved-legacy-adapter/v1"
EXPECTED_SOURCE_SHA256 = (
    "92b12fd9c65f5870c8f43b0b2e824c4afe789436290cc22e49d238362440c25c"
)
STATUS_PREFIX = "LGCA_SOLVER_STATUS="
_SOLVE_LINE = "    lbool ret = solver.solve();"
_ROUND_HEADER_RE = re.compile(r"^Round:\s+([0-9]+)\s+-+\s*$")
_SOLVER_VERSION_RE = re.compile(r"CryptoMiniSat version ([0-9][0-9.]*)")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

_STATUS_INSTRUMENTATION = """    lbool ret = solver.solve();
    cerr<<"LGCA_SOLVER_STATUS=";
    if (ret == l_True)
    {
        cerr<<"SAT";
    }
    else if (ret == l_False)
    {
        cerr<<"UNSAT";
    }
    else
    {
        cerr<<"UNKNOWN";
    }
    cerr<<"\\n";"""


class Gift64LegacyAdapterError(ValueError):
    """Raised when the pinned legacy boundary cannot be interpreted safely."""


@dataclass(frozen=True)
class ControlledRun:
    result: SolverResult
    trail: TrailRecord | None


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def instrument_status_output(source: bytes) -> bytes:
    """Return a temporary source copy with an explicit lbool status marker."""

    digest = _sha256_bytes(source)
    if digest != EXPECTED_SOURCE_SHA256:
        raise Gift64LegacyAdapterError(
            "source SHA-256 mismatch: "
            f"expected {EXPECTED_SOURCE_SHA256}, got {digest}"
        )
    text = source.decode("utf-8")
    if text.count(_SOLVE_LINE) != 1:
        raise Gift64LegacyAdapterError(
            "expected exactly one pinned solver.solve() instrumentation point"
        )
    return text.replace(
        _SOLVE_LINE, _STATUS_INSTRUMENTATION, 1
    ).encode("utf-8")


def parse_status_marker(stderr: str) -> SolverStatus:
    """Parse exactly one adapter-owned status marker from stderr."""

    markers = [
        line[len(STATUS_PREFIX) :].strip()
        for line in stderr.splitlines()
        if line.startswith(STATUS_PREFIX)
    ]
    if len(markers) != 1:
        raise Gift64LegacyAdapterError(
            f"expected exactly one solver status marker, got {len(markers)}"
        )
    try:
        status = SolverStatus(markers[0])
    except ValueError as exc:
        raise Gift64LegacyAdapterError(
            f"unsupported solver status marker: {markers[0]}"
        ) from exc
    if status not in {
        SolverStatus.SAT,
        SolverStatus.UNSAT,
        SolverStatus.UNKNOWN,
    }:
        raise Gift64LegacyAdapterError(
            f"instrumented solver returned invalid native status: {status.value}"
        )
    return status


def _parse_nibble_state(line: str, context: str) -> tuple[int, ...]:
    if not re.fullmatch(r"[0-9a-fA-F,\s]+", line):
        raise Gift64LegacyAdapterError(f"{context} contains unexpected characters")
    values = re.findall(r"[0-9a-fA-F]+", line)
    if len(values) != 16 or any(len(value) != 1 for value in values):
        raise Gift64LegacyAdapterError(
            f"{context} must contain exactly 16 single-hex-digit nibbles"
        )
    return tuple(int(value, 16) for value in values)


def decode_legacy_stdout(stdout: str, request: SolverRequest) -> TrailRecord:
    """Strictly decode the four legacy stdout blocks into a TrailRecord."""

    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    expected_line_count = request.cipher.round_count * 5
    if len(lines) != expected_line_count:
        raise Gift64LegacyAdapterError(
            f"expected {expected_line_count} non-empty model lines, got {len(lines)}"
        )

    rounds: list[TrailRound] = []
    for position in range(request.cipher.round_count):
        offset = position * 5
        header = _ROUND_HEADER_RE.fullmatch(lines[offset])
        if header is None:
            raise Gift64LegacyAdapterError(
                f"round {position} has an invalid header"
            )
        round_index = int(header.group(1))
        if round_index != position:
            raise Gift64LegacyAdapterError(
                f"expected round index {position}, got {round_index}"
            )
        if lines[offset + 1] != "xin:" or lines[offset + 3] != "xout:":
            raise Gift64LegacyAdapterError(
                f"round {position} must contain xin/xout labels in order"
            )
        rounds.append(
            TrailRound(
                round_index=round_index,
                input_nibbles=_parse_nibble_state(
                    lines[offset + 2], f"round {position} xin"
                ),
                output_nibbles=_parse_nibble_state(
                    lines[offset + 4], f"round {position} xout"
                ),
            )
        )

    state_fingerprint = hashlib.sha256(
        repr(
            tuple(
                (item.input_nibbles, item.output_nibbles) for item in rounds
            )
        ).encode("ascii")
    ).hexdigest()[:16]
    return TrailRecord(
        schema_version=TRAIL_SCHEMA_VERSION,
        trail_id=f"gift64-b5-{state_fingerprint}",
        cipher=request.cipher.name,
        state_layout_id=GIFT64_STATE_LAYOUT_ID,
        bit_order_id=GIFT64_BIT_ORDER_ID,
        nibble_order_id=GIFT64_NIBBLE_ORDER_ID,
        rounds=tuple(rounds),
    )


def _not_run_verification() -> VerificationResult:
    return VerificationResult(
        status=VerificationStatus.NOT_RUN,
        verifier_version=None,
        diagnostics=(),
    )


def _result(
    request: SolverRequest,
    *,
    status: SolverStatus,
    wall_time_s: float,
    cpu_time_s: float,
    exit_code: int | None,
    diagnostics: tuple[str, ...],
    model: ArtifactReference | None = None,
    objective_components: dict[str, int] | None = None,
    satisfied_bound: bool | None = None,
    verification: VerificationResult | None = None,
    solver_statistics: dict[str, str | int | float | bool | None] | None = None,
    exact_label_eligible: bool = False,
    exact_label_reason: str | None = None,
) -> SolverResult:
    definitive = status in {SolverStatus.SAT, SolverStatus.UNSAT}
    if exact_label_reason is None:
        exact_label_reason = {
            SolverStatus.SAT: "SAT result did not pass independent verification",
            SolverStatus.UNSAT: "UNSAT result has no independently checked proof",
            SolverStatus.UNKNOWN: "solver returned UNKNOWN",
            SolverStatus.TIMEOUT: "solver exceeded the controlled time limit",
            SolverStatus.ERROR: "controlled adapter failed",
        }[status]
    return SolverResult(
        schema_version="solver-result/v1",
        result_id=f"{request.request_id}-b5-controlled",
        request_id=request.request_id,
        status=status,
        definitive=definitive,
        model=model,
        proof=None,
        objective_components=objective_components,
        satisfied_bound=satisfied_bound,
        wall_time_s=wall_time_s,
        cpu_time_s=cpu_time_s,
        peak_memory_mb=None,
        solver_statistics=solver_statistics or {},
        exit_code=exit_code,
        parse_diagnostics=diagnostics,
        verification=verification or _not_run_verification(),
        exact_label_eligible=exact_label_eligible,
        exact_label_reason=exact_label_reason,
    )


def _formula_prefix(formula: str) -> Path:
    brew = shutil.which("brew")
    if brew is None:
        raise Gift64LegacyAdapterError("Homebrew is not available")
    completed = subprocess.run(
        [brew, "--prefix", formula],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise Gift64LegacyAdapterError(
            f"cannot resolve Homebrew prefix for {formula}"
        )
    return Path(completed.stdout.strip())


def _installed_solver_version(cms_prefix: Path) -> str:
    executable = cms_prefix / "bin" / "cryptominisat5"
    completed = subprocess.run(
        [str(executable), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    combined = completed.stdout + "\n" + completed.stderr
    match = _SOLVER_VERSION_RE.search(combined)
    if completed.returncode != 0 or match is None:
        raise Gift64LegacyAdapterError(
            "cannot determine installed CryptoMiniSat version"
        )
    return match.group(1)


def _write_model_artifact(
    artifact_root: Path, trail: TrailRecord
) -> ArtifactReference:
    relative_path = Path("models") / f"{trail.trail_id}.trail.json"
    artifact_path = artifact_root / relative_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    content = trail.to_json().encode("utf-8")
    artifact_path.write_bytes(content)
    return ArtifactReference(
        relative_path=relative_path.as_posix(),
        sha256=_sha256_bytes(content),
        media_type="application/vnd.lgca.trail+json",
        byte_size=len(content),
    )


def _validate_environment(
    request: SolverRequest, cms_prefix: Path
) -> None:
    if request.solver.name != "cryptominisat":
        raise Gift64LegacyAdapterError(
            f"unsupported solver: {request.solver.name}"
        )
    if request.solver.version is None:
        raise Gift64LegacyAdapterError(
            "request must pin the CryptoMiniSat version"
        )
    installed_version = _installed_solver_version(cms_prefix)
    if installed_version != request.solver.version:
        raise Gift64LegacyAdapterError(
            "CryptoMiniSat version mismatch: "
            f"request {request.solver.version}, installed {installed_version}"
        )
    if request.solver.threads != 1:
        raise Gift64LegacyAdapterError(
            "pinned legacy source supports only its hard-coded single thread"
        )


def run_controlled_gift64(
    request: SolverRequest,
    *,
    source_path: Path,
    artifact_root: Path,
    compiler: str = "clang++",
    cms_prefix: Path | None = None,
    gmp_prefix: Path | None = None,
) -> ControlledRun:
    """Compile and run the pinned source, returning a strict SolverResult."""

    try:
        artifact_root = artifact_root.resolve()
        if artifact_root.is_relative_to(_REPOSITORY_ROOT):
            raise Gift64LegacyAdapterError(
                "artifact_root must be outside the Git repository"
            )
        timeout_s = request.resources.time_limit_s
        if timeout_s is None or timeout_s <= 0:
            raise Gift64LegacyAdapterError(
                "request must define a positive solver time limit"
            )
        source = source_path.read_bytes()
        instrumented = instrument_status_output(source)
        artifact_root.mkdir(parents=True, exist_ok=True)
        compiler_path = shutil.which(compiler)
        if compiler_path is None:
            raise Gift64LegacyAdapterError(
                f"compiler is not available: {compiler}"
            )
        cms_prefix = cms_prefix or _formula_prefix("cryptominisat")
        gmp_prefix = gmp_prefix or _formula_prefix("gmp")
        _validate_environment(request, cms_prefix)
    except (
        Gift64LegacyAdapterError,
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
    ) as exc:
        return ControlledRun(
            result=_result(
                request,
                status=SolverStatus.ERROR,
                wall_time_s=0.0,
                cpu_time_s=0.0,
                exit_code=None,
                diagnostics=(str(exc),),
            ),
            trail=None,
        )

    compile_wall_time = 0.0
    with tempfile.TemporaryDirectory(prefix="gift64-b5-") as build_directory:
        build_root = Path(build_directory)
        temporary_source = build_root / "Differential.instrumented.cpp"
        executable = build_root / "gift64_differential"
        temporary_source.write_bytes(instrumented)
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
        except subprocess.TimeoutExpired:
            compile_wall_time = time.monotonic() - compile_start
            return ControlledRun(
                result=_result(
                    request,
                    status=SolverStatus.ERROR,
                    wall_time_s=0.0,
                    cpu_time_s=0.0,
                    exit_code=None,
                    diagnostics=("temporary adapter compilation timed out",),
                    solver_statistics={
                        "adapter_version": ADAPTER_VERSION,
                        "compile_wall_time_s": compile_wall_time,
                    },
                ),
                trail=None,
            )
        compile_wall_time = time.monotonic() - compile_start
        if compiled.returncode != 0:
            return ControlledRun(
                result=_result(
                    request,
                    status=SolverStatus.ERROR,
                    wall_time_s=0.0,
                    cpu_time_s=0.0,
                    exit_code=compiled.returncode,
                    diagnostics=("temporary adapter compilation failed",),
                    solver_statistics={
                        "adapter_version": ADAPTER_VERSION,
                        "compile_wall_time_s": compile_wall_time,
                    },
                ),
                trail=None,
            )

        before_cpu = os.times()
        solve_start = time.monotonic()
        try:
            solved = subprocess.run(
                [str(executable)],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            wall_time = time.monotonic() - solve_start
            after_cpu = os.times()
            cpu_time = (
                after_cpu.children_user
                + after_cpu.children_system
                - before_cpu.children_user
                - before_cpu.children_system
            )
            return ControlledRun(
                result=_result(
                    request,
                    status=SolverStatus.TIMEOUT,
                    wall_time_s=wall_time,
                    cpu_time_s=max(cpu_time, 0.0),
                    exit_code=None,
                    diagnostics=("solver process exceeded timeout",),
                    solver_statistics={
                        "adapter_version": ADAPTER_VERSION,
                        "compile_wall_time_s": compile_wall_time,
                    },
                ),
                trail=None,
            )
        wall_time = time.monotonic() - solve_start
        after_cpu = os.times()
        cpu_time = (
            after_cpu.children_user
            + after_cpu.children_system
            - before_cpu.children_user
            - before_cpu.children_system
        )
        statistics: dict[str, str | int | float | bool | None] = {
            "adapter_version": ADAPTER_VERSION,
            "compile_wall_time_s": compile_wall_time,
            "compiler_standard": "c++17",
            "expected_clauses": request.expected_static_counts.clauses,
            "expected_solver_calls": request.expected_static_counts.solver_calls,
            "expected_variables": request.expected_static_counts.variables,
            "instrumented_source_sha256": _sha256_bytes(instrumented),
            "request_seed": request.seed,
            "seed_application": "solver default; not explicit in legacy source",
            "source_instrumented_temporarily": True,
            "threads": request.solver.threads,
        }
        if solved.returncode != 0:
            return ControlledRun(
                result=_result(
                    request,
                    status=SolverStatus.ERROR,
                    wall_time_s=wall_time,
                    cpu_time_s=max(cpu_time, 0.0),
                    exit_code=solved.returncode,
                    diagnostics=("solver process returned a nonzero exit code",),
                    solver_statistics=statistics,
                ),
                trail=None,
            )
        try:
            status = parse_status_marker(solved.stderr)
        except Gift64LegacyAdapterError as exc:
            return ControlledRun(
                result=_result(
                    request,
                    status=SolverStatus.ERROR,
                    wall_time_s=wall_time,
                    cpu_time_s=max(cpu_time, 0.0),
                    exit_code=solved.returncode,
                    diagnostics=(str(exc),),
                    solver_statistics=statistics,
                ),
                trail=None,
            )

        if status is not SolverStatus.SAT:
            if solved.stdout.strip():
                return ControlledRun(
                    result=_result(
                        request,
                        status=SolverStatus.ERROR,
                        wall_time_s=wall_time,
                        cpu_time_s=max(cpu_time, 0.0),
                        exit_code=solved.returncode,
                        diagnostics=(
                            f"{status.value} solver branch emitted model stdout",
                        ),
                        solver_statistics=statistics,
                    ),
                    trail=None,
                )
            return ControlledRun(
                result=_result(
                    request,
                    status=status,
                    wall_time_s=wall_time,
                    cpu_time_s=max(cpu_time, 0.0),
                    exit_code=solved.returncode,
                    diagnostics=(),
                    solver_statistics=statistics,
                ),
                trail=None,
            )

        try:
            trail = decode_legacy_stdout(solved.stdout, request)
        except Gift64LegacyAdapterError as exc:
            return ControlledRun(
                result=_result(
                    request,
                    status=SolverStatus.ERROR,
                    wall_time_s=wall_time,
                    cpu_time_s=max(cpu_time, 0.0),
                    exit_code=solved.returncode,
                    diagnostics=(str(exc),),
                    solver_statistics=statistics,
                ),
                trail=None,
            )
        verification = verify_gift64_four_round_trail(trail, request)
        try:
            model = _write_model_artifact(artifact_root, trail)
        except OSError as exc:
            return ControlledRun(
                result=_result(
                    request,
                    status=SolverStatus.ERROR,
                    wall_time_s=wall_time,
                    cpu_time_s=max(cpu_time, 0.0),
                    exit_code=solved.returncode,
                    diagnostics=(f"cannot persist decoded model: {exc.strerror}",),
                    solver_statistics=statistics,
                ),
                trail=None,
            )
        exact_label_eligible = verification.valid
        return ControlledRun(
            result=_result(
                request,
                status=SolverStatus.SAT,
                wall_time_s=wall_time,
                cpu_time_s=max(cpu_time, 0.0),
                exit_code=solved.returncode,
                diagnostics=(
                    "status parsed from hash-pinned temporary instrumentation",
                    "stdout decoded into a canonical TrailRecord",
                ),
                model=model,
                objective_components=verification.objective_components,
                satisfied_bound=not any(
                    issue.code == "objective_bound"
                    for issue in verification.issues
                ),
                verification=verification.as_solver_verification(),
                solver_statistics=statistics,
                exact_label_eligible=exact_label_eligible,
                exact_label_reason=(
                    "definitive SAT trail passed independent GIFT-64 verification"
                    if exact_label_eligible
                    else "SAT trail failed independent GIFT-64 verification"
                ),
            ),
            trail=trail,
        )
