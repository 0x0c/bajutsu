"""The `clearStatusBar` action: restore the live status bar."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class ClearStatusBar(_Model):
    """Remove any status bar overrides (restore the live status bar)."""
