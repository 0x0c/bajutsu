"""The error raised when a simctl command runs past its deadline — a wedged CoreSimulator."""

from __future__ import annotations

from bajutsu.common.devices import errors as device_errors

from .device_error import DeviceError


class DeviceTimeout(DeviceError, device_errors.DeviceTimeout):
    """A simctl command exceeded its deadline — the observable symptom of a wedged CoreSimulator.

    Subclassing `DeviceError` leaves every handler that already converts or propagates a device
    fault working unchanged. Being a distinct type is what lets the runner-discard teardown — which
    absorbs a device fault so an app that is not running cannot fail a teardown — still let a hang
    through (BE-0363). This module's own deliberate suppressions key on `CalledProcessError` alone,
    so a timeout escapes them with none of them narrowed.

    The platform-neutral `device_errors.DeviceTimeout` is a *second* base rather than a replacement
    (BE-0374), so this stays everything it already was — a `simctl.DeviceError`, and through it a
    `device_errors.DeviceError` — while the backend-agnostic run pipeline gains a name for it that
    costs it no iOS import.
    """
