"""The error raised when a request reached the device but its effect is unknown."""

from __future__ import annotations

from .adb_resident_error import AdbResidentError


class AdbActUncertain(AdbResidentError):
    """The actuation request reached the device, and whether it applied is unknown.

    The device injects the gesture *before* it writes its response, so a socket lost after the request
    went out cannot be read as "nothing happened". Falling back to a coordinate injection here would
    actuate a second time — a tap fired twice, or a double tap landing as four contacts — which is the
    retry-an-already-applied-gesture hazard this item's design rejected. Held apart from its base so
    the driver can do *less* rather than more: it treats the gesture as having happened and lets the
    step's own condition wait fail loudly if it did not, because a missed gesture fails one assertion
    while an extra one can navigate the screen out from under the rest of the scenario.
    """
