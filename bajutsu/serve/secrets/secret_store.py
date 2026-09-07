"""The seam a named operator secret is written once and read through."""

from __future__ import annotations

from typing import Protocol


class SecretStore(Protocol):
    """Write-once storage for a named operator secret."""

    def set(self, name: str, value: str, *, updated_by: str | None = None) -> str | None:
        """Set or replace secret *name* to *value* (an empty *value* clears it).

        *updated_by* is best-effort audit metadata (who wrote it) the hosted store persists and the
        local store ignores. Returns the masked preview of what was stored, or None when cleared.
        """

    def describe(self, name: str) -> str | None:
        """The masked preview of secret *name*, or None when it is unset — never the plaintext."""
