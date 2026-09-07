"""The seam one deployment's persisted AI provider settings are read and written through."""

from __future__ import annotations

from typing import Protocol

from .persisted_provider_settings import PersistedProviderSettings


class ProviderSettingsStore(Protocol):
    """Reads and writes the persisted provider settings for one serve deployment.

    Readable by design — the opposite of the write-once `serve.secrets.SecretStore`.
    """

    def load(self) -> PersistedProviderSettings | None:
        """Return the persisted snapshot, or None when nothing has been saved yet.

        Raises:
            ProviderSettingsError: A snapshot exists but is malformed.
        """
        ...

    def save(self, data: PersistedProviderSettings) -> None:
        """Persist *data*, replacing any earlier snapshot."""
        ...
