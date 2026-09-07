"""The `clearKeychain` action: reset saved passwords and certificates."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class ClearKeychain(_Model):
    """Reset the Simulator's keychain (saved passwords, certificates)."""
