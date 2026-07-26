"""Controlled observation boundary for the supplementary GIFT-64 LNC program."""

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
from automated_differential_analysis.adapters.gift64_lc_legacy import (
    GIFT64_MASTER_KEY_VARIABLE_ORDER_ID,
    GIFT64_ROUND_CONSTANTS,
)
from shared.constraints import (
    CONSTRAINT_SET_SCHEMA_VERSION,
    CONSTRAINT_SPACE_COMPARISON_SCHEMA_VERSION,
    ConstraintKind,
    ConstraintSet,
    ConstraintSpaceComparison,
    GF2Equation,
    GF2FixedTerm,
    compare_constraint_spaces,
)


GIFT64_LNC_ADAPTER_VERSION = "gift64-lnc-legacy-adapter/v1"
GIFT64_LNC_SOURCE_SHA256 = (
    "af9f7070e0c46e156ad168e2ae11b090679e74d034bf05ddfbb035800b732f60"
)

_MARKER_RE = re.compile(
    r"^LGCA_LNC_ROW=(?P<group>[0-9]+),(?P<trail>[0-9]+);"
    r"columns=(?P<columns>[0-9,]*);rhs=(?P<rhs>[01])$"
)
_INSTRUMENTATION_ANCHOR = """                if (flag == true)
                {
                    cout << "$";"""
_INSTRUMENTED_ANCHOR = """                if (flag == true)
                {
                    cerr << "LGCA_LNC_ROW=" << group << "," << trail
                         << ";columns=";
                    bool lgca_first_column = true;
                    for (int lgca_column = 576; lgca_column < 760; lgca_column++)
                    {
                        if (ConstraintMatrix[line][lgca_column])
                        {
                            if (!lgca_first_column)
                            {
                                cerr << ",";
                            }
                            cerr << lgca_column;
                            lgca_first_column = false;
                        }
                    }
                    cerr << ";rhs=" << ConstraintMatrix[line][760] << "\\n";
                    cout << "$";"""


class Gift64LNCAdapterError(ValueError):
    """Raised when the legacy LNC boundary cannot be interpreted exactly."""


@dataclass(frozen=True)
class Gift64LNCObservation:
    adapter_version: str
    source_sha256: str
    trail_source_sha256: str
    legacy_stdout_sha256: str
    combined_constraint_sets: tuple[ConstraintSet, ...]
    comparisons: tuple[ConstraintSpaceComparison, ...]

    def summary_dict(self) -> dict[str, object]:
        return {
            "adapter_version": self.adapter_version,
            "constraint_set_schema_version": (
                CONSTRAINT_SET_SCHEMA_VERSION
            ),
            "comparison_schema_version": (
                CONSTRAINT_SPACE_COMPARISON_SCHEMA_VERSION
            ),
            "source_sha256": self.source_sha256,
            "trail_source_sha256": self.trail_source_sha256,
            "legacy_stdout_sha256": self.legacy_stdout_sha256,
            "constraint_set_count": len(self.combined_constraint_sets),
            "equation_count": sum(
                len(item.equations)
                for item in self.combined_constraint_sets
            ),
            "base_rank_values": sorted(
                {item.base_rank for item in self.comparisons}
            ),
            "combined_rank_values": sorted(
                {item.combined_rank for item in self.comparisons}
            ),
            "incremental_rank_values": sorted(
                {
                    item.incremental_rank
                    for item in self.comparisons
                    if item.incremental_rank is not None
                }
            ),
            "all_base_spaces_implied": all(
                item.base_implied_by_combined
                for item in self.comparisons
            ),
            "unique_combined_semantic_spaces": len(
                {
                    item.semantic_sha256
                    for item in self.combined_constraint_sets
                }
            ),
        }


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def instrument_gift64_lnc_source(source: bytes) -> bytes:
    """Add machine-readable final-row observations to a temporary copy."""

    digest = _sha256(source)
    if digest != GIFT64_LNC_SOURCE_SHA256:
        raise Gift64LNCAdapterError(
            "LNC source SHA-256 mismatch: "
            f"expected {GIFT64_LNC_SOURCE_SHA256}, got {digest}"
        )
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Gift64LNCAdapterError("LNC source must be UTF-8") from exc
    if text.count(_INSTRUMENTATION_ANCHOR) != 1:
        raise Gift64LNCAdapterError(
            "expected exactly one pinned LNC instrumentation point"
        )
    return text.replace(
        _INSTRUMENTATION_ANCHOR,
        _INSTRUMENTED_ANCHOR,
        1,
    ).encode("utf-8")


def _fixed_term(
    column: int,
    corpus: Gift64TrailInformationCorpus,
) -> GF2FixedTerm:
    offset = column - 704
    round_offset, slot = divmod(offset, 7)
    if not 0 <= round_offset < corpus.layout.round_count:
        raise Gift64LNCAdapterError(
            "LNC row references a fixed term outside the trail interval"
        )
    absolute_round = corpus.layout.round_start + round_offset
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


def parse_gift64_lnc_markers(
    stderr: str,
    corpus: Gift64TrailInformationCorpus,
) -> tuple[ConstraintSet, ...]:
    """Normalize global post-elimination LNC-stage rows for every trail."""

    rows: dict[tuple[int, int], list[GF2Equation]] = {
        (group, trail): []
        for group in range(corpus.layout.group_count)
        for trail in range(corpus.layout.trails_per_group)
    }
    seen: set[tuple[int, int, tuple[int, ...], int]] = set()
    marker_count = 0
    for line in stderr.splitlines():
        if not line:
            continue
        match = _MARKER_RE.fullmatch(line)
        if match is None:
            raise Gift64LNCAdapterError(
                f"unexpected LNC runtime stderr line: {line!r}"
            )
        marker_count += 1
        group = int(match.group("group"))
        trail = int(match.group("trail"))
        if (group, trail) not in rows:
            raise Gift64LNCAdapterError(
                "LNC marker record position is outside the trail corpus"
            )
        column_text = match.group("columns")
        columns = (
            tuple(int(value) for value in column_text.split(","))
            if column_text
            else ()
        )
        if tuple(sorted(set(columns))) != columns:
            raise Gift64LNCAdapterError(
                "LNC marker columns must be sorted and unique"
            )
        if any(not 576 <= column < 760 for column in columns):
            raise Gift64LNCAdapterError(
                "LNC marker contains a state or RHS column"
            )
        rhs = int(match.group("rhs"))
        identity = (group, trail, columns, rhs)
        if identity in seen:
            raise Gift64LNCAdapterError("duplicate LNC row marker")
        seen.add(identity)

        key_indices = tuple(
            column - 576 for column in columns if column < 704
        )
        fixed_terms = tuple(
            sorted(
                (
                    _fixed_term(column, corpus)
                    for column in columns
                    if column >= 704
                ),
                key=lambda item: item.name,
            )
        )
        rows[(group, trail)].append(
            GF2Equation(
                variable_indices=key_indices,
                source_rhs=rhs,
                # The row is produced by a global eight-round elimination.
                # The set-level interval and derivation method carry its full
                # scope; this field anchors provenance at the interval start.
                source_round=corpus.layout.round_start,
                fixed_terms=fixed_terms,
            )
        )
    if marker_count == 0:
        raise Gift64LNCAdapterError("LNC runtime emitted no row markers")
    if any(not values for values in rows.values()):
        raise Gift64LNCAdapterError(
            "LNC runtime omitted one or more trail records"
        )

    constraint_sets: list[ConstraintSet] = []
    for group in range(corpus.layout.group_count):
        for trail in range(corpus.layout.trails_per_group):
            equations = tuple(
                sorted(
                    rows[(group, trail)],
                    key=lambda item: (
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
                        f"gift64-lc-plus-linearized-g{group:02d}-"
                        f"t{trail:02d}"
                    ),
                    constraint_kind=(
                        ConstraintKind.LC_PLUS_LINEARIZED_RELATIONS
                    ),
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
                        "hash-pinned temporary observation of the legacy "
                        "global LC-plus-linearized-relation elimination"
                    ),
                    derivation_source_sha256=GIFT64_LNC_SOURCE_SHA256,
                    exact_derivation=True,
                    equations=equations,
                )
            )
    return tuple(constraint_sets)


def compare_lnc_with_lc(
    *,
    lc_constraint_sets: tuple[ConstraintSet, ...],
    combined_constraint_sets: tuple[ConstraintSet, ...],
) -> tuple[ConstraintSpaceComparison, ...]:
    """Match every combined LNC-stage space to its A2 LC base."""

    base_by_position: dict[tuple[int, int], ConstraintSet] = {}
    for item in lc_constraint_sets:
        if item.constraint_kind is not ConstraintKind.LC:
            raise Gift64LNCAdapterError(
                "LNC comparison base must contain only LC constraint sets"
            )
        position = (
            item.source_group_position,
            item.source_trail_position,
        )
        if position in base_by_position:
            raise Gift64LNCAdapterError(
                "duplicate LC constraint-set position"
            )
        base_by_position[position] = item

    comparisons: list[ConstraintSpaceComparison] = []
    seen_combined: set[tuple[int, int]] = set()
    for combined in combined_constraint_sets:
        if (
            combined.constraint_kind
            is not ConstraintKind.LC_PLUS_LINEARIZED_RELATIONS
        ):
            raise Gift64LNCAdapterError(
                "combined input has the wrong constraint kind"
            )
        position = (
            combined.source_group_position,
            combined.source_trail_position,
        )
        if position in seen_combined:
            raise Gift64LNCAdapterError(
                "duplicate combined constraint-set position"
            )
        seen_combined.add(position)
        base = base_by_position.get(position)
        if base is None:
            raise Gift64LNCAdapterError(
                "combined constraint set has no matching LC base"
            )
        comparisons.append(
            compare_constraint_spaces(base=base, combined=combined)
        )
    if set(base_by_position) != seen_combined:
        raise Gift64LNCAdapterError(
            "one or more LC bases have no combined constraint set"
        )
    return tuple(comparisons)


def run_gift64_lnc_observation(
    *,
    source_path: Path,
    trail_path: Path,
    lc_constraint_sets: tuple[ConstraintSet, ...],
    compiler: str = "clang++",
    timeout_s: float = 30.0,
) -> Gift64LNCObservation:
    """Compile/run a temporary instrumented copy and compare all spaces."""

    if timeout_s <= 0:
        raise Gift64LNCAdapterError("timeout_s must be positive")
    source = source_path.read_bytes()
    instrumented = instrument_gift64_lnc_source(source)
    trail_bytes = trail_path.read_bytes()
    corpus = parse_gift64_trail_information_bytes(
        trail_bytes,
        expected_source_sha256=(
            GIFT64_TRAIL_INFORMATION_SOURCE_SHA256
        ),
    )
    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise Gift64LNCAdapterError(
            f"C++ compiler is not available: {compiler}"
        )

    with tempfile.TemporaryDirectory(prefix="gift64-lnc-a3-") as directory:
        root = Path(directory)
        temporary_source = root / "main.instrumented.cpp"
        temporary_trails = root / "TrailInformation.out"
        executable = root / "gift64_lnc"
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
            raise Gift64LNCAdapterError(
                "temporary LNC compilation timed out"
            ) from exc
        if compiled.returncode != 0:
            raise Gift64LNCAdapterError(
                "temporary LNC compilation failed"
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
            raise Gift64LNCAdapterError(
                "legacy LNC observation timed out"
            ) from exc
        if completed.returncode != 0:
            raise Gift64LNCAdapterError(
                "legacy LNC observation returned a nonzero exit code"
            )
        combined_constraint_sets = parse_gift64_lnc_markers(
            completed.stderr,
            corpus,
        )
        comparisons = compare_lnc_with_lc(
            lc_constraint_sets=lc_constraint_sets,
            combined_constraint_sets=combined_constraint_sets,
        )
        return Gift64LNCObservation(
            adapter_version=GIFT64_LNC_ADAPTER_VERSION,
            source_sha256=GIFT64_LNC_SOURCE_SHA256,
            trail_source_sha256=corpus.source_sha256,
            legacy_stdout_sha256=_sha256(
                completed.stdout.encode("utf-8")
            ),
            combined_constraint_sets=combined_constraint_sets,
            comparisons=comparisons,
        )
