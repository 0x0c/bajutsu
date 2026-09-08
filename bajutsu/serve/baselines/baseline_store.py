"""The seam visual-regression baselines are read and written through."""

from __future__ import annotations

from typing import Protocol


class BaselineStore(Protocol):
    """Reads and writes visual-regression baseline images."""

    def open_bytes(self, name: str) -> bytes | None:
        """The baseline image bytes for *name*, or None if absent (or *name* escapes the store)."""

    def write(self, name: str, data: bytes) -> str | None:
        """Persist *data* as baseline *name*, returning the saved name, or None if *name* is unsafe."""

    def names(self) -> list[str]:
        """Every stored baseline name (so a run host can materialize them all)."""
