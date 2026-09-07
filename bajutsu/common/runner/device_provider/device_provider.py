"""The seam that reserves the devices for a run and hands back a lease (BE-0236)."""

from __future__ import annotations

from typing import Protocol

from bajutsu.common.config import Effective

from .device_lease import DeviceLease


class DeviceProvider(Protocol):
    """Reserve the device(s) for a run and hand back a `DeviceLease` (BE-0236).

    Off the verdict path: a provider decides *where* the run's devices come from, never whether a
    step passes. `acquire` is called once per run, upstream of the device pool; the returned lease's
    `release` is called once when the run finishes.
    """

    def acquire(self, eff: Effective, requested_udid: str) -> DeviceLease: ...
