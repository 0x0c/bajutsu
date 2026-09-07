"""The error raised when an adb operation fails in a way the user can act on."""

from __future__ import annotations

from bajutsu.common.devices import errors as device_errors


class DeviceError(device_errors.DeviceError):
    """An adb operation failed in a way the user can act on (e.g. no emulator, app not installed).

    Carries a clean, actionable message — the CLI surfaces it and exits 2, the same boundary as the
    iOS device errors. The Android-specific subclass of the platform-neutral
    `device_errors.DeviceError` (BE-0260): the generic CLI entrypoints (`run` / `crawl` / `audit` /
    `record`) catch that base, so an Android device failure surfaces the same way — a clean exit-2
    rather than an unhandled traceback — without their handlers importing the iOS `simctl` module.
    """
