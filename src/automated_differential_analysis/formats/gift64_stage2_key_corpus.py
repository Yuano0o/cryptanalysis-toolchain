"""Deterministic, bounded key-corpus contract for the GIFT-64 Stage 2 demo.

The supplied Stage 2 program consumes an unavailable ``KeyCandidate.out``.
This module deliberately does not attempt to recreate that corpus.  It defines
an explicitly labelled ``generated-for-demo`` replacement with a stable,
standard-library-only generator and the legacy eight-word text encoding.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any


GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION = "gift64-stage2-key-corpus/v1"
GIFT64_STAGE2_DEMO_GENERATOR_ID = "sha256-counter-v1"
GIFT64_STAGE2_DEMO_PURPOSE = "generated-for-demo"
GIFT64_STAGE2_MAX_DEMO_KEY_COUNT = 100_000
_WORD_RE = re.compile(r"^[0-9a-fA-F]{4}$")
_DOMAIN_SEPARATOR = b"lgca/gift64-stage2-key-corpus/v1\x00"


class Gift64Stage2KeyCorpusError(ValueError):
    """Raised when a Stage 2 key corpus is malformed or ambiguous."""


def _require_nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Gift64Stage2KeyCorpusError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _require_positive_int(value: Any, field_name: str) -> int:
    result = _require_nonnegative_int(value, field_name)
    if result == 0:
        raise Gift64Stage2KeyCorpusError(f"{field_name} must be greater than zero")
    return result


def _validate_key_words(value: tuple[int, ...], field_name: str) -> None:
    if not isinstance(value, tuple) or len(value) != 8:
        raise Gift64Stage2KeyCorpusError(
            f"{field_name} must contain exactly eight 16-bit words"
        )
    for position, word in enumerate(value):
        if (
            isinstance(word, bool)
            or not isinstance(word, int)
            or not 0 <= word <= 0xFFFF
        ):
            raise Gift64Stage2KeyCorpusError(
                f"{field_name}[{position}] must be a 16-bit word"
            )


@dataclass(frozen=True)
class Gift64Stage2KeyCorpusSpec:
    """Portable specification for a deterministic demo corpus."""

    schema_version: str
    purpose: str
    generator_id: str
    seed: int
    key_count: int

    def __post_init__(self) -> None:
        if self.schema_version != GIFT64_STAGE2_KEY_CORPUS_SCHEMA_VERSION:
            raise Gift64Stage2KeyCorpusError("unsupported key-corpus schema version")
        if self.purpose != GIFT64_STAGE2_DEMO_PURPOSE:
            raise Gift64Stage2KeyCorpusError(
                "key corpus purpose must be generated-for-demo"
            )
        if self.generator_id != GIFT64_STAGE2_DEMO_GENERATOR_ID:
            raise Gift64Stage2KeyCorpusError("unsupported key corpus generator")
        _require_nonnegative_int(self.seed, "key_corpus.seed")
        if self.seed >= 2**64:
            raise Gift64Stage2KeyCorpusError("key_corpus.seed must fit in 64 bits")
        _require_positive_int(self.key_count, "key_corpus.key_count")
        if self.key_count > GIFT64_STAGE2_MAX_DEMO_KEY_COUNT:
            raise Gift64Stage2KeyCorpusError(
                "key_corpus.key_count exceeds the bounded demo maximum "
                f"of {GIFT64_STAGE2_MAX_DEMO_KEY_COUNT}"
            )

    def to_dict(self) -> dict[str, str | int]:
        return {
            "schema_version": self.schema_version,
            "purpose": self.purpose,
            "generator_id": self.generator_id,
            "seed": self.seed,
            "key_count": self.key_count,
        }


def generated_stage2_key_words(
    spec: Gift64Stage2KeyCorpusSpec, index: int
) -> tuple[int, ...]:
    """Return one portable SHA-256-derived 128-bit master-key candidate."""

    if not isinstance(spec, Gift64Stage2KeyCorpusSpec):
        raise Gift64Stage2KeyCorpusError("spec must be a Gift64Stage2KeyCorpusSpec")
    _require_nonnegative_int(index, "key index")
    if index >= spec.key_count:
        raise IndexError("key index is outside the configured corpus")
    digest = hashlib.sha256(
        _DOMAIN_SEPARATOR
        + spec.seed.to_bytes(8, "big")
        + index.to_bytes(8, "big")
    ).digest()
    return tuple(
        int.from_bytes(digest[offset : offset + 2], "big")
        for offset in range(0, 16, 2)
    )


def generate_stage2_key_corpus(
    spec: Gift64Stage2KeyCorpusSpec,
) -> tuple[tuple[int, ...], ...]:
    """Generate all keys declared by ``spec`` without external randomness."""

    if not isinstance(spec, Gift64Stage2KeyCorpusSpec):
        raise Gift64Stage2KeyCorpusError("spec must be a Gift64Stage2KeyCorpusSpec")
    return tuple(generated_stage2_key_words(spec, index) for index in range(spec.key_count))


def stage2_key_corpus_legacy_bytes(
    keys: tuple[tuple[int, ...], ...],
) -> bytes:
    """Encode keys exactly as a canonical legacy ``KeyCandidate.out`` file."""

    if not isinstance(keys, tuple) or not keys:
        raise Gift64Stage2KeyCorpusError("key corpus must be a non-empty tuple")
    for index, key_words in enumerate(keys):
        _validate_key_words(key_words, f"key corpus record {index}")
    return (
        "\n".join(" ".join(f"{word:04x}" for word in key) for key in keys)
        + "\n"
    ).encode("ascii")


def generated_stage2_key_corpus_bytes(spec: Gift64Stage2KeyCorpusSpec) -> bytes:
    """Generate the canonical legacy bytes for a demo corpus specification."""

    return stage2_key_corpus_legacy_bytes(generate_stage2_key_corpus(spec))


def parse_stage2_key_corpus_bytes(
    data: bytes, *, expected_key_count: int | None = None
) -> tuple[tuple[int, ...], ...]:
    """Strictly parse the eight-word-per-record legacy key-corpus format."""

    if expected_key_count is not None:
        _require_positive_int(expected_key_count, "expected_key_count")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise Gift64Stage2KeyCorpusError("key corpus must be ASCII") from exc
    if not text or not text.endswith("\n"):
        raise Gift64Stage2KeyCorpusError(
            "key corpus must be non-empty and end with one newline"
        )
    lines = text.splitlines()
    if not lines or any(not line.strip() for line in lines):
        raise Gift64Stage2KeyCorpusError("key corpus must not contain blank records")
    keys: list[tuple[int, ...]] = []
    for line_number, line in enumerate(lines, start=1):
        tokens = line.split()
        if len(tokens) != 8:
            raise Gift64Stage2KeyCorpusError(
                f"key corpus line {line_number} must contain eight words"
            )
        if any(_WORD_RE.fullmatch(token) is None for token in tokens):
            raise Gift64Stage2KeyCorpusError(
                f"key corpus line {line_number} contains an invalid 16-bit word"
            )
        keys.append(tuple(int(token, 16) for token in tokens))
    if expected_key_count is not None and len(keys) != expected_key_count:
        raise Gift64Stage2KeyCorpusError(
            f"expected {expected_key_count} key records, got {len(keys)}"
        )
    return tuple(keys)


def parse_stage2_key_corpus(
    path: str | Path, *, expected_key_count: int | None = None
) -> tuple[tuple[int, ...], ...]:
    return parse_stage2_key_corpus_bytes(
        Path(path).read_bytes(), expected_key_count=expected_key_count
    )
