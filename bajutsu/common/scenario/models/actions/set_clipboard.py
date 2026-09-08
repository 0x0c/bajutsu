"""The `setClipboard` action: seed the pasteboard for a paste flow."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class SetClipboard(_Model):
    """Seed the Simulator's pasteboard with text (simctl pbcopy), for paste flows."""

    text: str
