"""The error raised when a persisted provider-settings file exists but is malformed."""

from __future__ import annotations


class ProviderSettingsError(ValueError):
    """A persisted provider-settings file exists but its contents are malformed.

    Raised instead of guessing at a partial value: the boot path turns it into a visible
    warning and falls back to the env-derived defaults, so a corrupt file never silently
    resets the operator's choice (determinism-first).
    """
