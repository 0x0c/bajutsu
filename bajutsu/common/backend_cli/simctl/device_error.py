"""The error raised when a simctl operation fails in a way the user can act on."""

from __future__ import annotations

from bajutsu.common.devices import errors as device_errors


class DeviceError(device_errors.DeviceError):
    """A simctl operation failed in a way the user can act on (e.g. launching an
    app that isn't installed, or an invalid device).

    The iOS-specific subclass of the platform-neutral `device_errors.DeviceError` (BE-0260): a
    generic handler catches the base, iOS-only code catches this. Carries a clean, actionable
    message — the CLI surfaces it and exits 2, instead of dumping a Python traceback.
    """
