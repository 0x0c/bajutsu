"""The result of comparing a whole golden against a screen read (BE-0006)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .field_mismatch import FieldMismatch


@dataclass
class GoldenResult:
    """Aggregate result of comparing a full golden against a query() snapshot."""

    mismatches: list[FieldMismatch] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    frame_failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.mismatches and not self.missing and not self.frame_failures
