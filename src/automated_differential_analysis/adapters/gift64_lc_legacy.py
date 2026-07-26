"""Controlled observation boundary for the supplementary GIFT-64 LC program."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from automated_differential_analysis.formats import (
    GIFT64_TRAIL_INFORMATION_SOURCE_SHA256,
    Gift64TrailInformationCorpus,
    parse_gift64_trail_information_bytes,
)
from shared.constraints import (
    CONSTRAINT_SET_SCHEMA_VERSION,
    ConstraintKind,
    ConstraintSet,
    GF2Equation,
    GF2FixedTerm,
)


GIFT64_LC_ADAPTER_VERSION = "gift64-lc-legacy-adapter/v1"
GIFT64_LC_SOURCE_SHA256 = (
    "42f734a6cc7969a55fca5ad498ae319c2676fe4c6e3178ff633efa6295df7bd2"
)
GIFT64_MASTER_KEY_VARIABLE_ORDER_ID = "gift64-master-key-bit-msb/v1"
GIFT64_ROUND_CONSTANTS = (
    0x01,
    0x03,
    0x07,
    0x0F,
    0x1F,
    0x3E,
    0x3D,
    0x3B,
    0x37,
    0x2F,
    0x1E,
    0x3C,
    0x39,
    0x33,
    0x27,
    0x0E,
    0x1D,
    0x3A,
    0x35,
    0x2B,
    0x16,
    0x2C,
    0x18,
    0x30,
    0x21,
    0x02,
    0x05,
    0x0B,
    0x17,
    0x2E,
    0x1C,
    0x38,
    0x31,
    0x23,
    0x06,
    0x0D,
    0x1B,
    0x36,
    0x2D,
    0x1A,
    0x34,
    0x29,
    0x12,
    0x24,
    0x08,
    0x11,
    0x22,
    0x04,
)

_MARKER_RE = re.compile(
    r"^LGCA_LC_ROW=(?P<group>[0-9]+),(?P<trail>[0-9]+),"
    r"(?P<bridge>[0-9]+);columns=(?P<columns>[0-9,]*);"
    r"rhs=(?P<rhs>[01])$"
)
_INSTRUMENTATION_ANCHOR = """                    if (flag == true)
                    {
                        cout<<"$";"""
_INSTRUMENTED_ANCHOR = """                    if (flag == true)
                    {
                        cerr<<"LGCA_LC_ROW="<<group<<","<<trail<<","<<round
                            <<";columns=";
                        bool lgca_first_column = true;
                        for (int lgca_column = 64; lgca_column < 241; lgca_column++)
                        {
                            if (ConstraintMatrix[line][lgca_column])
                            {
                                if (!lgca_first_column)
                                {
                                    cerr<<",";
                                }
                                cerr<<lgca_column;
                                lgca_first_column = false;
                            }
                        }
                        cerr<<";rhs="<<ConstraintMatrix[line][241]<<"\\n";
                        cout<<"$";"""


class Gift64LCAdapterError(ValueError):
    """Raised when the legacy LC boundary cannot be interpreted exactly."""


@dataclass(frozen=True)
class Gift64LCObservation:
    adapter_version: str
    source_sha256: str
    trail_source_sha256: str
    legacy_stdout_sha256: str
    constraint_sets: tuple[ConstraintSet, ...]

    def summary_dict(self) -> dict[str, object]:
        return {
            "adapter_version": self.adapter_version,
            "constraint_set_schema_version": (
                CONSTRAINT_SET_SCHEMA_VERSION
            ),
            "source_sha256": self.source_sha256,
            "trail_source_sha256": self.trail_source_sha256,
            "legacy_stdout_sha256": self.legacy_stdout_sha256,
            "constraint_set_count": len(self.constraint_sets),
            "equation_count": sum(
                len(item.equations) for item in self.constraint_sets
            ),
            "rank_total": sum(item.rank for item in self.constraint_sets),
            "rank_values": sorted(
                {item.rank for item in self.constraint_sets}
            ),
            "unique_semantic_spaces": len(
                {item.semantic_sha256 for item in self.constraint_sets}
            ),
        }


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def instrument_gift64_lc_source(source: bytes) -> bytes:
    """Add machine-readable row observations to a temporary source copy."""

    digest = _sha256(source)
    if digest != GIFT64_LC_SOURCE_SHA256:
        raise Gift64LCAdapterError(
            "LC source SHA-256 mismatch: "
            f"expected {GIFT64_LC_SOURCE_SHA256}, got {digest}"
        )
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Gift64LCAdapterError("LC source must be UTF-8") from exc
    if text.count(_INSTRUMENTATION_ANCHOR) != 1:
        raise Gift64LCAdapterError(
            "expected exactly one pinned LC instrumentation point"
        )
    return text.replace(
        _INSTRUMENTATION_ANCHOR,
        _INSTRUMENTED_ANCHOR,
        1,
    ).encode("utf-8")


def _fixed_term(
    column: int,
    bridge_index: int,
    absolute_round: int,
) -> GF2FixedTerm:
    offset = column - 192
    encoded_bridge, slot = divmod(offset, 7)
    if encoded_bridge != bridge_index:
        raise Gift64LCAdapterError(
            "LC row references a fixed-term column from another bridge"
        )
    if slot == 0:
        return GF2FixedTerm(
            name=f"gift64.round[{absolute_round}].constant_unit",
            value=1,
        )
    constant_bit = slot - 1
    value = (
        GIFT64_ROUND_CONSTANTS[absolute_round]
        >> (5 - constant_bit)
    ) & 1
    return GF2FixedTerm(
        name=(
            f"gift64.round[{absolute_round}]."
            f"constant_bit[{constant_bit}]"
        ),
        value=value,
    )


def parse_gift64_lc_markers(
    stderr: str,
    corpus: Gift64TrailInformationCorpus,
) -> tuple[ConstraintSet, ...]:
    """Map adapter-owned row markers into one ConstraintSet per trail."""

    rows: dict[tuple[int, int], list[GF2Equation]] = {
        (group, trail): []
        for group in range(corpus.layout.group_count)
        for trail in range(corpus.layout.trails_per_group)
    }
    seen: set[tuple[int, int, int, tuple[int, ...], int]] = set()
    marker_count = 0
    for line in stderr.splitlines():
        if not line:
            continue
        match = _MARKER_RE.fullmatch(line)
        if match is None:
            raise Gift64LCAdapterError(
                f"unexpected LC runtime stderr line: {line!r}"
            )
        marker_count += 1
        group = int(match.group("group"))
        trail = int(match.group("trail"))
        bridge = int(match.group("bridge"))
        if (group, trail) not in rows:
            raise Gift64LCAdapterError(
                "LC marker record position is outside the trail corpus"
            )
        if not 0 <= bridge < corpus.layout.round_count - 1:
            raise Gift64LCAdapterError(
                "LC marker bridge is outside the trail interval"
            )
        column_text = match.group("columns")
        columns = (
            tuple(int(value) for value in column_text.split(","))
            if column_text
            else ()
        )
        if tuple(sorted(set(columns))) != columns:
            raise Gift64LCAdapterError(
                "LC marker columns must be sorted and unique"
            )
        if any(not 64 <= column < 241 for column in columns):
            raise Gift64LCAdapterError(
                "LC marker contains a state or RHS column"
            )
        rhs = int(match.group("rhs"))
        identity = (group, trail, bridge, columns, rhs)
        if identity in seen:
            raise Gift64LCAdapterError("duplicate LC row marker")
        seen.add(identity)

        absolute_round = corpus.layout.round_start + bridge
        key_indices = tuple(column - 64 for column in columns if column < 192)
        fixed_terms = tuple(
            sorted(
                (
                    _fixed_term(column, bridge, absolute_round)
                    for column in columns
                    if column >= 192
                ),
                key=lambda item: item.name,
            )
        )
        rows[(group, trail)].append(
            GF2Equation(
                variable_indices=key_indices,
                source_rhs=rhs,
                source_round=absolute_round,
                fixed_terms=fixed_terms,
            )
        )
    if marker_count == 0:
        raise Gift64LCAdapterError("LC runtime emitted no row markers")

    constraint_sets: list[ConstraintSet] = []
    for group in range(corpus.layout.group_count):
        for trail in range(corpus.layout.trails_per_group):
            equations = tuple(
                sorted(
                    rows[(group, trail)],
                    key=lambda item: (
                        item.source_round,
                        item.variable_indices,
                        item.source_rhs,
                        tuple(term.name for term in item.fixed_terms),
                    ),
                )
            )
            constraint_sets.append(
                ConstraintSet(
                    schema_version=CONSTRAINT_SET_SCHEMA_VERSION,
                    constraint_set_id=(
                        f"gift64-lc-g{group:02d}-t{trail:02d}"
                    ),
                    constraint_kind=ConstraintKind.LC,
                    field="GF(2)",
                    cipher="gift64",
                    variable_order_id=(
                        GIFT64_MASTER_KEY_VARIABLE_ORDER_ID
                    ),
                    variable_count=128,
                    source_artifact_sha256=corpus.source_sha256,
                    source_group_position=group,
                    source_trail_position=trail,
                    source_round_start=corpus.layout.round_start,
                    source_round_end=corpus.layout.round_end,
                    derivation_method=(
                        "hash-pinned temporary observation of legacy "
                        "Gaussian elimination"
                    ),
                    derivation_source_sha256=GIFT64_LC_SOURCE_SHA256,
                    exact_derivation=True,
                    equations=equations,
                )
            )
    return tuple(constraint_sets)


def run_gift64_lc_observation(
    *,
    source_path: Path,
    trail_path: Path,
    compiler: str = "clang++",
    timeout_s: float = 30.0,
) -> Gift64LCObservation:
    """Compile/run a temporary instrumented copy and normalize all LC rows."""

    if timeout_s <= 0:
        raise Gift64LCAdapterError("timeout_s must be positive")
    source = source_path.read_bytes()
    instrumented = instrument_gift64_lc_source(source)
    trail_bytes = trail_path.read_bytes()
    corpus = parse_gift64_trail_information_bytes(
        trail_bytes,
        expected_source_sha256=(
            GIFT64_TRAIL_INFORMATION_SOURCE_SHA256
        ),
    )
    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise Gift64LCAdapterError(
            f"C++ compiler is not available: {compiler}"
        )

    with tempfile.TemporaryDirectory(prefix="gift64-lc-a2-") as directory:
        root = Path(directory)
        temporary_source = root / "main.instrumented.cpp"
        temporary_trails = root / "TrailInformation.out"
        executable = root / "gift64_lc"
        temporary_source.write_bytes(instrumented)
        temporary_trails.write_bytes(trail_bytes)
        try:
            compiled = subprocess.run(
                [
                    compiler_path,
                    "-std=c++17",
                    "-O2",
                    str(temporary_source),
                    "-o",
                    str(executable),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            raise Gift64LCAdapterError(
                "temporary LC compilation timed out"
            ) from exc
        if compiled.returncode != 0:
            raise Gift64LCAdapterError(
                "temporary LC compilation failed"
            )
        try:
            completed = subprocess.run(
                [str(executable)],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise Gift64LCAdapterError(
                "legacy LC observation timed out"
            ) from exc
        if completed.returncode != 0:
            raise Gift64LCAdapterError(
                "legacy LC observation returned a nonzero exit code"
            )
        constraint_sets = parse_gift64_lc_markers(
            completed.stderr, corpus
        )
        return Gift64LCObservation(
            adapter_version=GIFT64_LC_ADAPTER_VERSION,
            source_sha256=GIFT64_LC_SOURCE_SHA256,
            trail_source_sha256=corpus.source_sha256,
            legacy_stdout_sha256=_sha256(
                completed.stdout.encode("utf-8")
            ),
            constraint_sets=constraint_sets,
        )
