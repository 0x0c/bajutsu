"""The built-in `appium` provider: the live path to a reserved iOS device (BE-0238)."""

from __future__ import annotations

from bajutsu.common.config import Effective
from bajutsu.common.platform_lifecycle import ProvisionProfile

from .device_lease import DeviceLease


class _AppiumProvider:
    """The built-in `appium` provider: the live path to a reserved iOS device (BE-0238 Unit 4).

    A cloud (or a self-hosted grid) already holds an iOS device behind a fixed Appium / WebDriver
    endpoint, so this provider hands that endpoint over as the udid spec — the address a *future*
    WebDriver transport will drive, in place of a simctl udid. The device is a live remote one Bajutsu
    never boots or installs onto through simctl, so the profile reports it booted with its build
    already in place; the reservation is the grid's, not this run's, so there is nothing to release.
    The endpoint is required — a missing one fails closed at resolution, never a silent fall back to a
    local device.

    This ships the seam only; the endpoint is *not* yet drivable end-to-end, and that transport
    cannot simply layer a WebDriver client on today's path. The udid spec flows unchanged into
    `XcuitestEnvironment`, whose `_destination()` runs it through `simctl.validated_udid`, and the
    shared `device_id` charset excludes the `/` in a URL — so a real `http(s)://` endpoint would raise
    `DeviceError: invalid udid` today (a message that reads as a bad `--udid`, not "transport not
    wired"). The follow-up slice must route this value around the simctl / xcodebuild udid machinery
    entirely, which structurally cannot carry a URL.
    """

    def acquire(self, eff: Effective, requested_udid: str) -> DeviceLease:  # noqa: ARG002  # DeviceProvider shape
        raw = eff.device_provider.endpoint if eff.device_provider is not None else None
        endpoint = raw.strip() if raw else ""
        # An empty or whitespace-only endpoint is no drivable address, so fail closed at resolution
        # rather than pass blank (or padded) space downstream as a udid spec.
        if not endpoint:
            raise ValueError(
                "device provider 'appium' requires an endpoint "
                "(targets.<name>.deviceProvider.endpoint)"
            )
        return DeviceLease(
            udid_spec=endpoint,  # normalized: any surrounding whitespace trimmed off
            provision=ProvisionProfile(boot_ready=True, app_preinstalled=True),
        )
