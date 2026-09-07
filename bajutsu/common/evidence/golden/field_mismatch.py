"""One field of one control that differs between the golden and the actual screen."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMismatch:
    """One field of one control that differs between golden and actual."""

    control_id: str
    field: str
    expected: object
    actual: object

    def __str__(self) -> str:
        return f"`{self.control_id}`: {self.field} expected {self.expected!r} got {self.actual!r}"
