"""A snapshot of the serve AI provider settings, as saved and loaded."""

from __future__ import annotations

from dataclasses import dataclass, field

from bajutsu.serve.state import ProviderSettings


@dataclass(frozen=True)
class PersistedProviderSettings:
    """A snapshot of the serve AI provider settings, as saved to and loaded from a store.

    Mirrors what the Web UI last saved: the active provider plus the per-provider model/effort/
    region map (BE-0183), so switching back to a provider left behind restores its settings too.
    """

    provider: str
    settings: dict[str, ProviderSettings] = field(default_factory=dict)
