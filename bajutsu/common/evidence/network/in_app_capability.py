"""A piece of Bajutsu's own in-app instrumentation the control channel may address (BE-0365)."""

from __future__ import annotations

from enum import StrEnum


class InAppCapability(StrEnum):
    """A piece of bajutsu's own in-app instrumentation the control channel may address (BE-0365).

    Closed on purpose, and that is the boundary rather than a comment about it: the channel controls
    what bajutsu put inside the app, never the application's own state. A command that seeded app
    data or drove navigation would move per-app knowledge into the tool (prime directive 3), so a
    new capability is argued for here instead of being named as a free string at a call site.
    """

    TOUCH_VISUALIZATION = "touch_visualization"  # the touch markers BE-0371 draws
