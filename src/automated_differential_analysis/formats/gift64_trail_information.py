"""Strict parser for the supplementary GIFT-64 TrailInformation.out format."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


GIFT64_TRAIL_INFORMATION_SCHEMA_VERSION = "gift64-trail-information/v1"
GIFT64_TRAIL_INFORMATION_SOURCE_SHA256 = (
    "fe40ca7b81d4c362d45db58c7c4448317d0305bbd149e04abe12bcede8c02335"
)
_WORD_RE = re.compile(r"^[0-9a-fA-F]{4}$")


class Gift64TrailInformationError(ValueError):
    """Raised when an upstream trail-information artifact is ambiguous."""


def _require_positive_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise Gift64TrailInformationError(
            f"{field_name} must be a positive integer"
        )
    return value


def _require_nonnegative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Gift64TrailInformationError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _validate_words(
    values: tuple[int, ...], expected_count: int, field_name: str
) -> None:
    if not isinstance(values, tuple) or len(values) != expected_count:
        raise Gift64TrailInformationError(
            f"{field_name} must contain {expected_count} 16-bit words"
        )
    for index, value in enumerate(values):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 0xFFFF
        ):
            raise Gift64TrailInformationError(
                f"{field_name}[{index}] must be a 16-bit word"
            )


def _canonical_words(values: tuple[int, ...]) -> list[str]:
    return [f"{value:04x}" for value in values]


@dataclass(frozen=True)
class Gift64TrailInformationLayout:
    group_count: int
    trails_per_group: int
    round_start: int
    round_count: int
    key_state_anchor_round: int

    def __post_init__(self) -> None:
        _require_positive_integer(self.group_count, "layout.group_count")
        _require_positive_integer(
            self.trails_per_group, "layout.trails_per_group"
        )
        _require_nonnegative_integer(self.round_start, "layout.round_start")
        _require_positive_integer(self.round_count, "layout.round_count")
        _require_nonnegative_integer(
            self.key_state_anchor_round,
            "layout.key_state_anchor_round",
        )
        if self.key_state_anchor_round != self.round_start - 1:
            raise Gift64TrailInformationError(
                "layout key-state anchor must be the round before round_start"
            )

    @property
    def round_end(self) -> int:
        return self.round_start + self.round_count

    @property
    def record_count(self) -> int:
        return self.group_count * self.trails_per_group

    @property
    def lines_per_record(self) -> int:
        return 1 + 2 * self.round_count

    @property
    def tokens_per_record(self) -> int:
        return 8 + 8 * self.round_count

    def to_dict(self) -> dict[str, int]:
        return {
            "group_count": self.group_count,
            "trails_per_group": self.trails_per_group,
            "round_start": self.round_start,
            "round_end": self.round_end,
            "round_count": self.round_count,
            "key_state_anchor_round": self.key_state_anchor_round,
        }


DEFAULT_GIFT64_TRAIL_INFORMATION_LAYOUT = Gift64TrailInformationLayout(
    group_count=8,
    trails_per_group=4,
    round_start=5,
    round_count=8,
    key_state_anchor_round=4,
)


@dataclass(frozen=True)
class Gift64WordState:
    words: tuple[int, ...]

    def __post_init__(self) -> None:
        _validate_words(self.words, 4, "state.words")

    @property
    def hex_words(self) -> tuple[str, ...]:
        return tuple(f"{value:04x}" for value in self.words)

    @property
    def hex_state(self) -> str:
        return "".join(self.hex_words)

    @property
    def nibbles(self) -> tuple[int, ...]:
        return tuple(
            (word >> shift) & 0xF
            for word in self.words
            for shift in (12, 8, 4, 0)
        )

    @property
    def bits(self) -> tuple[int, ...]:
        return tuple(
            (word >> shift) & 1
            for word in self.words
            for shift in range(15, -1, -1)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "words": _canonical_words(self.words),
            "hex_state": self.hex_state,
        }


@dataclass(frozen=True)
class Gift64TrailInformationRound:
    round_index: int
    absolute_round: int
    input_state: Gift64WordState
    output_state: Gift64WordState

    def __post_init__(self) -> None:
        _require_nonnegative_integer(self.round_index, "round.round_index")
        _require_nonnegative_integer(self.absolute_round, "round.absolute_round")
        if not isinstance(self.input_state, Gift64WordState):
            raise Gift64TrailInformationError(
                "round.input_state must be a Gift64WordState"
            )
        if not isinstance(self.output_state, Gift64WordState):
            raise Gift64TrailInformationError(
                "round.output_state must be a Gift64WordState"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "absolute_round": self.absolute_round,
            "input_state": self.input_state.to_dict(),
            "output_state": self.output_state.to_dict(),
        }


@dataclass(frozen=True)
class Gift64TrailInformationRecord:
    group_position: int
    trail_position: int
    key_state_anchor_round: int
    key_state_difference_words: tuple[int, ...]
    rounds: tuple[Gift64TrailInformationRound, ...]

    def __post_init__(self) -> None:
        _require_nonnegative_integer(
            self.group_position, "record.group_position"
        )
        _require_nonnegative_integer(
            self.trail_position, "record.trail_position"
        )
        _require_nonnegative_integer(
            self.key_state_anchor_round,
            "record.key_state_anchor_round",
        )
        _validate_words(
            self.key_state_difference_words,
            8,
            "record.key_state_difference_words",
        )
        if not isinstance(self.rounds, tuple) or not self.rounds:
            raise Gift64TrailInformationError(
                "record.rounds must be a non-empty tuple"
            )
        if not all(
            isinstance(item, Gift64TrailInformationRound)
            for item in self.rounds
        ):
            raise Gift64TrailInformationError(
                "record.rounds must contain Gift64TrailInformationRound values"
            )
        for position, round_record in enumerate(self.rounds):
            if round_record.round_index != position:
                raise Gift64TrailInformationError(
                    "record round indices must be sequential from zero"
                )
        for position in range(len(self.rounds) - 1):
            if (
                self.rounds[position].output_state
                != self.rounds[position + 1].input_state
            ):
                raise Gift64TrailInformationError(
                    f"record round continuity fails after round {position}"
                )
        if not any(self.rounds[0].input_state.words):
            raise Gift64TrailInformationError(
                "record first-round input difference must be nonzero"
            )

    @property
    def key_state_difference_hex(self) -> str:
        return "".join(_canonical_words(self.key_state_difference_words))

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_position": self.group_position,
            "trail_position": self.trail_position,
            "key_state_anchor_round": self.key_state_anchor_round,
            "key_state_difference_words": _canonical_words(
                self.key_state_difference_words
            ),
            "rounds": [item.to_dict() for item in self.rounds],
        }


@dataclass(frozen=True)
class Gift64TrailInformationCorpus:
    schema_version: str
    source_sha256: str
    layout: Gift64TrailInformationLayout
    records: tuple[Gift64TrailInformationRecord, ...]

    def __post_init__(self) -> None:
        if self.schema_version != GIFT64_TRAIL_INFORMATION_SCHEMA_VERSION:
            raise Gift64TrailInformationError(
                "unsupported trail-information schema version"
            )
        if re.fullmatch(r"[0-9a-f]{64}", self.source_sha256) is None:
            raise Gift64TrailInformationError(
                "corpus.source_sha256 must be a lowercase SHA-256"
            )
        if not isinstance(self.layout, Gift64TrailInformationLayout):
            raise Gift64TrailInformationError(
                "corpus.layout must be a Gift64TrailInformationLayout"
            )
        if (
            not isinstance(self.records, tuple)
            or len(self.records) != self.layout.record_count
        ):
            raise Gift64TrailInformationError(
                f"corpus must contain {self.layout.record_count} records"
            )

        group_keys: list[tuple[int, ...]] = []
        for group_position in range(self.layout.group_count):
            start = group_position * self.layout.trails_per_group
            group = self.records[start : start + self.layout.trails_per_group]
            expected_key = group[0].key_state_difference_words
            group_keys.append(expected_key)
            for trail_position, record in enumerate(group):
                if (
                    record.group_position != group_position
                    or record.trail_position != trail_position
                ):
                    raise Gift64TrailInformationError(
                        "corpus record positions do not match file order"
                    )
                if record.key_state_difference_words != expected_key:
                    raise Gift64TrailInformationError(
                        f"group {group_position} has inconsistent key differences"
                    )
                if len(record.rounds) != self.layout.round_count:
                    raise Gift64TrailInformationError(
                        "record round count does not match corpus layout"
                    )
                if (
                    record.key_state_anchor_round
                    != self.layout.key_state_anchor_round
                ):
                    raise Gift64TrailInformationError(
                        "record key-state anchor does not match corpus layout"
                    )
                for round_record in record.rounds:
                    expected_absolute = (
                        self.layout.round_start + round_record.round_index
                    )
                    if round_record.absolute_round != expected_absolute:
                        raise Gift64TrailInformationError(
                            "record absolute round does not match corpus layout"
                        )
        if len(set(group_keys)) != len(group_keys):
            raise Gift64TrailInformationError(
                "corpus groups must have distinct key-state differences"
            )

    def record(
        self, group_position: int, trail_position: int
    ) -> Gift64TrailInformationRecord:
        if not 0 <= group_position < self.layout.group_count:
            raise IndexError("group_position is outside the corpus")
        if not 0 <= trail_position < self.layout.trails_per_group:
            raise IndexError("trail_position is outside the group")
        offset = (
            group_position * self.layout.trails_per_group + trail_position
        )
        return self.records[offset]

    def summary_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_sha256": self.source_sha256,
            "layout": self.layout.to_dict(),
            "record_count": len(self.records),
            "unique_key_state_differences": len(
                {
                    record.key_state_difference_words
                    for record in self.records
                }
            ),
            "round_continuity": "passed",
            "first_input_nonzero": "passed",
        }

    def summary_json(self) -> str:
        return json.dumps(
            self.summary_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"


def _parse_word_line(
    line: str, expected_count: int, line_number: int
) -> tuple[int, ...]:
    tokens = line.split()
    if len(tokens) != expected_count:
        raise Gift64TrailInformationError(
            f"line {line_number} must contain {expected_count} words, "
            f"got {len(tokens)}"
        )
    for token in tokens:
        if _WORD_RE.fullmatch(token) is None:
            raise Gift64TrailInformationError(
                f"line {line_number} has invalid 16-bit hex word {token!r}"
            )
    return tuple(int(token, 16) for token in tokens)


def parse_gift64_trail_information_bytes(
    data: bytes,
    *,
    layout: Gift64TrailInformationLayout = (
        DEFAULT_GIFT64_TRAIL_INFORMATION_LAYOUT
    ),
    expected_source_sha256: str | None = None,
) -> Gift64TrailInformationCorpus:
    source_sha256 = hashlib.sha256(data).hexdigest()
    if (
        expected_source_sha256 is not None
        and source_sha256 != expected_source_sha256
    ):
        raise Gift64TrailInformationError(
            "TrailInformation source SHA-256 mismatch: "
            f"expected {expected_source_sha256}, got {source_sha256}"
        )
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise Gift64TrailInformationError(
            "TrailInformation must be ASCII"
        ) from exc
    lines = text.splitlines()
    if any(not line.strip() for line in lines):
        raise Gift64TrailInformationError(
            "TrailInformation must not contain blank lines"
        )
    expected_line_count = layout.record_count * layout.lines_per_record
    if len(lines) != expected_line_count:
        raise Gift64TrailInformationError(
            f"expected {expected_line_count} logical lines, got {len(lines)}"
        )

    records: list[Gift64TrailInformationRecord] = []
    cursor = 0
    for group_position in range(layout.group_count):
        for trail_position in range(layout.trails_per_group):
            key_words = _parse_word_line(lines[cursor], 8, cursor + 1)
            cursor += 1
            rounds: list[Gift64TrailInformationRound] = []
            for round_index in range(layout.round_count):
                input_words = _parse_word_line(
                    lines[cursor], 4, cursor + 1
                )
                cursor += 1
                output_words = _parse_word_line(
                    lines[cursor], 4, cursor + 1
                )
                cursor += 1
                rounds.append(
                    Gift64TrailInformationRound(
                        round_index=round_index,
                        absolute_round=layout.round_start + round_index,
                        input_state=Gift64WordState(input_words),
                        output_state=Gift64WordState(output_words),
                    )
                )
            records.append(
                Gift64TrailInformationRecord(
                    group_position=group_position,
                    trail_position=trail_position,
                    key_state_anchor_round=layout.key_state_anchor_round,
                    key_state_difference_words=key_words,
                    rounds=tuple(rounds),
                )
            )
    return Gift64TrailInformationCorpus(
        schema_version=GIFT64_TRAIL_INFORMATION_SCHEMA_VERSION,
        source_sha256=source_sha256,
        layout=layout,
        records=tuple(records),
    )


def parse_gift64_trail_information(
    path: str | Path,
    *,
    layout: Gift64TrailInformationLayout = (
        DEFAULT_GIFT64_TRAIL_INFORMATION_LAYOUT
    ),
    expected_source_sha256: str | None = None,
) -> Gift64TrailInformationCorpus:
    return parse_gift64_trail_information_bytes(
        Path(path).read_bytes(),
        layout=layout,
        expected_source_sha256=expected_source_sha256,
    )
