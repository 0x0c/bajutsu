"""The error raised when a device operation runs past its deadline rather than failing."""

from __future__ import annotations

from .device_error import DeviceError


class DeviceTimeout(DeviceError):
    """A device operation exceeded its deadline rather than failing — the host stopped answering.

    What every backend raises when a device command ran out its own deadline: the iOS
    `simctl.DeviceTimeout` today (BE-0363), and whichever type a later item gives the adb surface
    once its commands carry deadlines too. The distinction from a plain `DeviceError` is what a
    caller learns from the fault — a device that refused an operation produced evidence about that
    one operation, while a device that never answered produced evidence that the service behind
    every operation stopped serving — so the run pipeline branches on it without importing an iOS
    backend module to name it (BE-0374).
    """
