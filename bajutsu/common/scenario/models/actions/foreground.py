"""The `foreground` action: resume a backgrounded app without restarting it."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class Foreground(_Model):
    """Resume a backgrounded app to the foreground (simctl launch, without terminating it).

    The other half of `background`. It adds no settle sleep — any wait after resuming is the
    scenario's own condition wait.
    """
