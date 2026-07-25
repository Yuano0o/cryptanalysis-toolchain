"""Minimal versioned trail representation shared by exact verification stages."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping

from shared.sat.contracts import ContractValidationError


TRAIL_SCHEMA_VERSION = "trail-record/v1"


def _validate_nibbles(values: tuple[int, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise ContractValidationError(f"{field_name} must be a tuple")
    for index, value in enumerate(values):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 0xF
        ):
            raise ContractValidationError(
                f"{field_name}[{index}] must be a nibble in 0..15"
            )


@dataclass(frozen=True)
class TrailRound:
    round_index: int
    input_nibbles: tuple[int, ...]
    output_nibbles: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.round_index, bool)
            or not isinstance(self.round_index, int)
            or self.round_index < 0
        ):
            raise ContractValidationError(
                "trail round_index must be a non-negative integer"
            )
        _validate_nibbles(self.input_nibbles, "trail input_nibbles")
        _validate_nibbles(self.output_nibbles, "trail output_nibbles")

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "input_nibbles": list(self.input_nibbles),
            "output_nibbles": list(self.output_nibbles),
        }

    @classmethod
    def from_dict(cls, value: Any) -> TrailRound:
        if not isinstance(value, Mapping):
            raise ContractValidationError("trail round must be an object")
        expected = {"round_index", "input_nibbles", "output_nibbles"}
        if set(value) != expected:
            raise ContractValidationError(
                "trail round fields must be: "
                + ", ".join(sorted(expected))
            )
        if not isinstance(value["input_nibbles"], list) or not isinstance(
            value["output_nibbles"], list
        ):
            raise ContractValidationError(
                "trail round nibble states must be arrays"
            )
        return cls(
            round_index=value["round_index"],
            input_nibbles=tuple(value["input_nibbles"]),
            output_nibbles=tuple(value["output_nibbles"]),
        )


@dataclass(frozen=True)
class TrailRecord:
    schema_version: str
    trail_id: str
    cipher: str
    state_layout_id: str
    bit_order_id: str
    nibble_order_id: str
    rounds: tuple[TrailRound, ...]
    claimed_objective_components: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != TRAIL_SCHEMA_VERSION:
            raise ContractValidationError(
                f"trail schema_version must be {TRAIL_SCHEMA_VERSION}"
            )
        for field_name in (
            "trail_id",
            "cipher",
            "state_layout_id",
            "bit_order_id",
            "nibble_order_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ContractValidationError(
                    f"trail {field_name} must be a non-empty string"
                )
        if not isinstance(self.rounds, tuple) or not self.rounds:
            raise ContractValidationError("trail rounds must be a non-empty tuple")
        if not all(isinstance(item, TrailRound) for item in self.rounds):
            raise ContractValidationError(
                "trail rounds must contain TrailRound values"
            )
        if not isinstance(self.claimed_objective_components, Mapping):
            raise ContractValidationError(
                "trail claimed_objective_components must be an object"
            )
        for name, value in self.claimed_objective_components.items():
            if not isinstance(name, str) or not name:
                raise ContractValidationError(
                    "trail objective component names must be non-empty strings"
                )
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ContractValidationError(
                    f"trail objective component {name} must be non-negative"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trail_id": self.trail_id,
            "cipher": self.cipher,
            "state_layout_id": self.state_layout_id,
            "bit_order_id": self.bit_order_id,
            "nibble_order_id": self.nibble_order_id,
            "rounds": [item.to_dict() for item in self.rounds],
            "claimed_objective_components": dict(
                sorted(self.claimed_objective_components.items())
            ),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=True, indent=2, sort_keys=True
        ) + "\n"

    @classmethod
    def from_dict(cls, value: Any) -> TrailRecord:
        if not isinstance(value, Mapping):
            raise ContractValidationError("trail record must be an object")
        expected = {
            "schema_version",
            "trail_id",
            "cipher",
            "state_layout_id",
            "bit_order_id",
            "nibble_order_id",
            "rounds",
            "claimed_objective_components",
        }
        if set(value) != expected:
            raise ContractValidationError(
                "trail record fields must be: " + ", ".join(sorted(expected))
            )
        if not isinstance(value["rounds"], list):
            raise ContractValidationError("trail rounds must be an array")
        return cls(
            schema_version=value["schema_version"],
            trail_id=value["trail_id"],
            cipher=value["cipher"],
            state_layout_id=value["state_layout_id"],
            bit_order_id=value["bit_order_id"],
            nibble_order_id=value["nibble_order_id"],
            rounds=tuple(TrailRound.from_dict(item) for item in value["rounds"]),
            claimed_objective_components=value["claimed_objective_components"],
        )

    @classmethod
    def from_json(cls, value: str) -> TrailRecord:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"invalid trail JSON: {exc}") from exc
        return cls.from_dict(decoded)
