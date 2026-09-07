"""The `back` action: navigate back one level, each backend using its own primitive."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class Back(_Model):
    """`back` action — navigate back one level, each backend using its platform-correct primitive.

    Android has a true system back (a key event); iOS has no hardware back, so navigating back means
    tapping the OS-provided navigation back button, and the web goes back in history. The step is the
    one cross-backend expression of "go back" (BE-0210).
    """
