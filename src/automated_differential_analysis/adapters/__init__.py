"""Narrow boundaries around read-only reference implementations."""

from .gift64_improved_legacy import (
    ADAPTER_VERSION,
    ControlledRun,
    Gift64LegacyAdapterError,
    decode_legacy_stdout,
    instrument_status_output,
    parse_status_marker,
    run_controlled_gift64,
)

__all__ = [
    "ADAPTER_VERSION",
    "ControlledRun",
    "Gift64LegacyAdapterError",
    "decode_legacy_stdout",
    "instrument_status_output",
    "parse_status_marker",
    "run_controlled_gift64",
]
