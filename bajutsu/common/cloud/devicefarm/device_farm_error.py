"""The error raised when a Device Farm submission fails, loudly rather than silently."""

from __future__ import annotations


class DeviceFarmError(RuntimeError):
    """A Device Farm submission failed loudly — a missing payload, a failed upload, or a run that
    never completed. Never swallowed: a test tool that hides its own failure is worse than none."""
