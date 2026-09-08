"""The error raised when a device operation fails in a way the user can act on."""

from __future__ import annotations


class DeviceError(RuntimeError):
    """A device operation failed in a way the user can act on.

    Carries a clean, actionable message (a bad udid/serial, an app that isn't installed, a wedged
    simulator or browser) — the CLI surfaces it and exits 2, instead of dumping a Python traceback.
    Each backend subclasses it for platform-specific detail; a generic handler catches this base.
    """
