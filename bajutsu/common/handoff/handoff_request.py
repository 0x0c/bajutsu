"""What a paused `record` asks a human: why it stopped, and the screen it stopped on."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HandoffRequest:
    """What a paused `record` asks a human: why it stopped, and the screen it stopped on.

    `target` is a compact description of the selector the paused action was aiming at (empty
    for a screen-level request); `screenshot` is the current screen as PNG bytes, shown in the
    Web UI pane.
    """

    reason: str
    screen: str = ""
    target: str = ""
    screenshot: bytes | None = None
