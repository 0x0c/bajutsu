"""The error raised when the resident hierarchy channel fails to answer a read."""

from __future__ import annotations


class AdbResidentError(RuntimeError):
    """The resident hierarchy channel failed to answer a read.

    An infrastructure failure, kept distinct from a test outcome (like `XcuitestChannelError`): the
    driver catches it, logs loudly, and degrades to the `uiautomator dump` subprocess rather than
    reading a failed channel as an empty screen.
    """
