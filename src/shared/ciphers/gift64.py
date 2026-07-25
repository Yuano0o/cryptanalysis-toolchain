"""Independent GIFT-64 differential-trail verification.

This module derives the DDT from the published GIFT S-box. It does not import
the upstream SAT restriction table and does not invoke a solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shared.sat import (
    Comparison,
    ObjectiveKind,
    SolverRequest,
    VerificationResult,
    VerificationStatus,
)
from shared.trails import TrailRecord


GIFT64_STATE_LAYOUT_ID = "gift64_reference_state_v1"
GIFT64_BIT_ORDER_ID = "gift64_reference_bit_index_v1"
GIFT64_NIBBLE_ORDER_ID = "gift64_reference_nibble_index_v1"
GIFT64_VERIFIER_VERSION = "gift64-four-round-verifier/v1"
GIFT64_BASELINE_ROUNDS = 4
GIFT64_STATE_NIBBLES = 16

GIFT64_SBOX = (
    0x1,
    0xA,
    0x4,
    0xC,
    0x6,
    0xF,
    0x3,
    0x9,
    0x2,
    0xD,
    0xB,
    0x7,
    0x5,
    0x0,
    0x8,
    0xE,
)

GIFT64_PERMUTATION = (
    48,
    1,
    18,
    35,
    32,
    49,
    2,
    19,
    16,
    33,
    50,
    3,
    0,
    17,
    34,
    51,
    52,
    5,
    22,
    39,
    36,
    53,
    6,
    23,
    20,
    37,
    54,
    7,
    4,
    21,
    38,
    55,
    56,
    9,
    26,
    43,
    40,
    57,
    10,
    27,
    24,
    41,
    58,
    11,
    8,
    25,
    42,
    59,
    60,
    13,
    30,
    47,
    44,
    61,
    14,
    31,
    28,
    45,
    62,
    15,
    12,
    29,
    46,
    63,
)


def _build_ddt() -> tuple[tuple[int, ...], ...]:
    table = [[0 for _ in range(16)] for _ in range(16)]
    for input_difference in range(16):
        for value in range(16):
            output_difference = (
                GIFT64_SBOX[value] ^ GIFT64_SBOX[value ^ input_difference]
            )
            table[input_difference][output_difference] += 1
    return tuple(tuple(row) for row in table)


GIFT64_DDT = _build_ddt()


@dataclass(frozen=True)
class TransitionWeight:
    integral_weight: int
    decimal_weight_count: int


@dataclass(frozen=True)
class VerificationIssue:
    code: str
    message: str
    round_index: int | None = None
    sbox_index: int | None = None


@dataclass(frozen=True)
class Gift64TrailVerification:
    valid: bool
    checked_rounds: int
    checked_sboxes: int
    integral_weight: int
    decimal_weight_count: int
    issues: tuple[VerificationIssue, ...]

    @property
    def objective_components(self) -> dict[str, int]:
        return {
            "integral_weight": self.integral_weight,
            "decimal_weight_count": self.decimal_weight_count,
        }

    def as_solver_verification(self) -> VerificationResult:
        return VerificationResult(
            status=(
                VerificationStatus.PASSED
                if self.valid
                else VerificationStatus.FAILED
            ),
            verifier_version=GIFT64_VERIFIER_VERSION,
            diagnostics=tuple(
                f"{issue.code}: {issue.message}" for issue in self.issues
            ),
        )


def transition_weight(
    input_difference: int, output_difference: int
) -> TransitionWeight | None:
    """Return the exact split-weight semantics for a GIFT S-box transition."""

    if (
        isinstance(input_difference, bool)
        or isinstance(output_difference, bool)
        or not isinstance(input_difference, int)
        or not isinstance(output_difference, int)
        or not 0 <= input_difference <= 0xF
        or not 0 <= output_difference <= 0xF
    ):
        raise ValueError("S-box differences must be nibbles")
    count = GIFT64_DDT[input_difference][output_difference]
    if count == 0:
        return None
    if count == 16:
        return TransitionWeight(0, 0)
    if count == 6:
        return TransitionWeight(1, 1)
    if count == 4:
        return TransitionWeight(2, 0)
    if count == 2:
        return TransitionWeight(3, 0)
    raise ValueError(f"unsupported GIFT DDT count: {count}")


def _nibbles_to_bits(nibbles: Iterable[int]) -> tuple[int, ...]:
    return tuple(
        (nibble >> bit_index) & 1
        for nibble in nibbles
        for bit_index in (3, 2, 1, 0)
    )


def _bits_to_nibbles(bits: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        (bits[offset] << 3)
        | (bits[offset + 1] << 2)
        | (bits[offset + 2] << 1)
        | bits[offset + 3]
        for offset in range(0, len(bits), 4)
    )


def logical_sbox_output_from_permuted_state(
    output_nibbles: tuple[int, ...],
) -> tuple[int, ...]:
    """Undo the source's `xout[P[i]]` placement for S-box DDT checking."""

    if len(output_nibbles) != GIFT64_STATE_NIBBLES:
        raise ValueError("GIFT-64 state must contain 16 nibbles")
    output_bits = _nibbles_to_bits(output_nibbles)
    logical_bits = tuple(
        output_bits[GIFT64_PERMUTATION[index]] for index in range(64)
    )
    return _bits_to_nibbles(logical_bits)


def _comparison_holds(value: int, bound: int, comparison: Comparison) -> bool:
    if comparison is Comparison.LT:
        return value < bound
    if comparison is Comparison.LE:
        return value <= bound
    if comparison is Comparison.EQ:
        return value == bound
    if comparison is Comparison.GE:
        return value >= bound
    raise ValueError(f"unsupported comparison: {comparison}")


def _state_hex(nibbles: tuple[int, ...]) -> str:
    return "".join(f"{value:x}" for value in nibbles)


def verify_gift64_four_round_trail(
    trail: TrailRecord,
    request: SolverRequest | None = None,
) -> Gift64TrailVerification:
    """Verify one decoded four-round trail independently of the SAT encoding."""

    issues: list[VerificationIssue] = []
    checked_sboxes = 0
    integral_weight = 0
    decimal_weight_count = 0

    expected_layouts = {
        "state_layout_id": GIFT64_STATE_LAYOUT_ID,
        "bit_order_id": GIFT64_BIT_ORDER_ID,
        "nibble_order_id": GIFT64_NIBBLE_ORDER_ID,
    }
    if trail.cipher != "GIFT-64":
        issues.append(
            VerificationIssue(
                "wrong_cipher", f"expected GIFT-64, got {trail.cipher}"
            )
        )
    for field_name, expected in expected_layouts.items():
        actual = getattr(trail, field_name)
        if actual != expected:
            issues.append(
                VerificationIssue(
                    "layout_mismatch",
                    f"{field_name} expected {expected}, got {actual}",
                )
            )
    if len(trail.rounds) != GIFT64_BASELINE_ROUNDS:
        issues.append(
            VerificationIssue(
                "round_count",
                f"expected {GIFT64_BASELINE_ROUNDS} rounds, got {len(trail.rounds)}",
            )
        )

    for position, round_record in enumerate(trail.rounds):
        if round_record.round_index != position:
            issues.append(
                VerificationIssue(
                    "round_index",
                    f"expected round index {position}, got {round_record.round_index}",
                    round_index=round_record.round_index,
                )
            )
        if len(round_record.input_nibbles) != GIFT64_STATE_NIBBLES:
            issues.append(
                VerificationIssue(
                    "input_state_length",
                    "GIFT-64 input state must contain 16 nibbles",
                    round_index=round_record.round_index,
                )
            )
        if len(round_record.output_nibbles) != GIFT64_STATE_NIBBLES:
            issues.append(
                VerificationIssue(
                    "output_state_length",
                    "GIFT-64 output state must contain 16 nibbles",
                    round_index=round_record.round_index,
                )
            )

    if (
        trail.rounds
        and len(trail.rounds[0].input_nibbles) == GIFT64_STATE_NIBBLES
        and not any(trail.rounds[0].input_nibbles)
    ):
        issues.append(
            VerificationIssue(
                "zero_input", "the first-round input difference must be nonzero"
            )
        )

    for position in range(len(trail.rounds) - 1):
        current = trail.rounds[position]
        following = trail.rounds[position + 1]
        if current.output_nibbles != following.input_nibbles:
            issues.append(
                VerificationIssue(
                    "round_continuity",
                    f"round {position} output does not equal round {position + 1} input",
                    round_index=position,
                )
            )

    for round_record in trail.rounds:
        if (
            len(round_record.input_nibbles) != GIFT64_STATE_NIBBLES
            or len(round_record.output_nibbles) != GIFT64_STATE_NIBBLES
        ):
            continue
        logical_output = logical_sbox_output_from_permuted_state(
            round_record.output_nibbles
        )
        for sbox_index, (input_difference, output_difference) in enumerate(
            zip(round_record.input_nibbles, logical_output, strict=True)
        ):
            checked_sboxes += 1
            weight = transition_weight(input_difference, output_difference)
            if weight is None:
                issues.append(
                    VerificationIssue(
                        "invalid_sbox_transition",
                        (
                            f"DDT[{input_difference:x}][{output_difference:x}] "
                            "is zero"
                        ),
                        round_index=round_record.round_index,
                        sbox_index=sbox_index,
                    )
                )
                continue
            integral_weight += weight.integral_weight
            decimal_weight_count += weight.decimal_weight_count

    recomputed_components = {
        "integral_weight": integral_weight,
        "decimal_weight_count": decimal_weight_count,
    }
    for name, claimed_value in trail.claimed_objective_components.items():
        if name not in recomputed_components:
            issues.append(
                VerificationIssue(
                    "unknown_claimed_component",
                    f"cannot independently recompute {name}",
                )
            )
        elif claimed_value != recomputed_components[name]:
            issues.append(
                VerificationIssue(
                    "claimed_objective_mismatch",
                    (
                        f"{name} claimed {claimed_value}, recomputed "
                        f"{recomputed_components[name]}"
                    ),
                )
            )

    if request is not None:
        if request.cipher.name != trail.cipher:
            issues.append(
                VerificationIssue(
                    "request_cipher_mismatch",
                    f"request cipher {request.cipher.name} does not match trail",
                )
            )
        if request.cipher.round_count != len(trail.rounds):
            issues.append(
                VerificationIssue(
                    "request_round_mismatch",
                    (
                        f"request expects {request.cipher.round_count} rounds, "
                        f"trail has {len(trail.rounds)}"
                    ),
                )
            )
        for field_name in expected_layouts:
            request_value = getattr(request.cipher, field_name)
            trail_value = getattr(trail, field_name)
            if request_value != trail_value:
                issues.append(
                    VerificationIssue(
                        "request_layout_mismatch",
                        (
                            f"request {field_name} {request_value} does not "
                            f"match trail {trail_value}"
                        ),
                    )
                )
        if request.fixed_differences.input is not None and trail.rounds:
            actual_input = _state_hex(trail.rounds[0].input_nibbles)
            if actual_input != request.fixed_differences.input:
                issues.append(
                    VerificationIssue(
                        "fixed_input_mismatch",
                        (
                            f"request input {request.fixed_differences.input} "
                            f"does not match trail {actual_input}"
                        ),
                    )
                )
        if request.fixed_differences.output is not None and trail.rounds:
            actual_output = _state_hex(trail.rounds[-1].output_nibbles)
            if actual_output != request.fixed_differences.output:
                issues.append(
                    VerificationIssue(
                        "fixed_output_mismatch",
                        (
                            f"request output {request.fixed_differences.output} "
                            f"does not match trail {actual_output}"
                        ),
                    )
                )
        if request.objective.kind is not ObjectiveKind.SPLIT_PROBABILITY_WEIGHT:
            issues.append(
                VerificationIssue(
                    "unsupported_objective",
                    (
                        "four-round verifier expects split_probability_weight, "
                        f"got {request.objective.kind.value}"
                    ),
                )
            )
        else:
            for component in request.objective.components:
                if component.name not in recomputed_components:
                    issues.append(
                        VerificationIssue(
                            "unsupported_bound_component",
                            f"cannot verify request component {component.name}",
                        )
                    )
                    continue
                actual_value = recomputed_components[component.name]
                if not _comparison_holds(
                    actual_value,
                    component.bound,
                    request.objective.comparison,
                ):
                    issues.append(
                        VerificationIssue(
                            "objective_bound",
                            (
                                f"{component.name}={actual_value} does not satisfy "
                                f"{request.objective.comparison.value}"
                                f"{component.bound}"
                            ),
                        )
                    )

    return Gift64TrailVerification(
        valid=not issues,
        checked_rounds=len(trail.rounds),
        checked_sboxes=checked_sboxes,
        integral_weight=integral_weight,
        decimal_weight_count=decimal_weight_count,
        issues=tuple(issues),
    )
