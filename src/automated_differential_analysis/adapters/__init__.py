"""Narrow boundaries around read-only reference implementations."""

from .gift64_lc_legacy import (
    GIFT64_LC_ADAPTER_VERSION,
    GIFT64_LC_SOURCE_SHA256,
    Gift64LCAdapterError,
    Gift64LCObservation,
    instrument_gift64_lc_source,
    parse_gift64_lc_markers,
    run_gift64_lc_observation,
)
from .gift64_lnc_legacy import (
    GIFT64_LNC_ADAPTER_VERSION,
    GIFT64_LNC_SOURCE_SHA256,
    Gift64LNCAdapterError,
    Gift64LNCObservation,
    compare_lnc_with_lc,
    instrument_gift64_lnc_source,
    parse_gift64_lnc_markers,
    run_gift64_lnc_observation,
)
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
    "GIFT64_LC_ADAPTER_VERSION",
    "GIFT64_LC_SOURCE_SHA256",
    "GIFT64_LNC_ADAPTER_VERSION",
    "GIFT64_LNC_SOURCE_SHA256",
    "ControlledRun",
    "Gift64LegacyAdapterError",
    "Gift64LCAdapterError",
    "Gift64LCObservation",
    "Gift64LNCAdapterError",
    "Gift64LNCObservation",
    "compare_lnc_with_lc",
    "decode_legacy_stdout",
    "instrument_gift64_lc_source",
    "instrument_gift64_lnc_source",
    "instrument_status_output",
    "parse_gift64_lc_markers",
    "parse_gift64_lnc_markers",
    "parse_status_marker",
    "run_controlled_gift64",
    "run_gift64_lc_observation",
    "run_gift64_lnc_observation",
]
