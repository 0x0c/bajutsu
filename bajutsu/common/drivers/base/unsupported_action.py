"""The error raised when an actuator backend cannot perform an action at all."""

from __future__ import annotations


class UnsupportedAction(Exception):
    """The actuator backend cannot perform this action.

    For example, a multi-touch gesture on a single-touch backend. The tool surfaces it as a step
    failure with a clear reason rather than letting it pass silently.
    """
