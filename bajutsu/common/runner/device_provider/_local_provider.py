"""The built-in `local` provider: the locally-attached path, unchanged."""

from __future__ import annotations

from bajutsu.common.config import Effective
from bajutsu.common.platform_lifecycle import ProvisionProfile

from .device_lease import DeviceLease


class _LocalProvider:
    """The built-in `local` provider: today's locally-attached path, unchanged.

    The `--udid` string passes straight through as the udid spec, the profile is inert (a
    locally-attached device boots and installs the app itself), and there is nothing to release.
    """

    def acquire(self, eff: Effective, requested_udid: str) -> DeviceLease:  # noqa: ARG002  # DeviceProvider shape
        return DeviceLease(udid_spec=requested_udid, provision=ProvisionProfile())
