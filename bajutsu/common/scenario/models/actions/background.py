"""The `background` action: send the app away, as pressing Home does."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class Background(_Model):
    """Send the app to the background, as pressing the Home button does.

    Backgrounds without terminating (SpringBoard is brought to the front), so the app's state
    survives for a later `foreground`.
    """
