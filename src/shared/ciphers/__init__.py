"""Cipher-specific independent verification primitives."""

from .gift64 import (
    GIFT64_BIT_ORDER_ID,
    GIFT64_NIBBLE_ORDER_ID,
    GIFT64_STATE_LAYOUT_ID,
    Gift64TrailVerification,
    TransitionWeight,
    logical_sbox_output_from_permuted_state,
    transition_weight,
    verify_gift64_four_round_trail,
)

__all__ = [
    "GIFT64_BIT_ORDER_ID",
    "GIFT64_NIBBLE_ORDER_ID",
    "GIFT64_STATE_LAYOUT_ID",
    "Gift64TrailVerification",
    "TransitionWeight",
    "logical_sbox_output_from_permuted_state",
    "transition_weight",
    "verify_gift64_four_round_trail",
]
