"""The `copy` action: put the active selection on the clipboard (BE-0265)."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class Copy(_Model):
    """`copy` action — copy the active selection to the clipboard (BE-0265).

    Acts on whatever a prior `select` left selected; it takes no target of its own. With no active
    selection it fails the step rather than silently copying nothing, and its result is verified
    through the existing `clipboard` read-back (BE-0052), never through any state this step holds.
    """
