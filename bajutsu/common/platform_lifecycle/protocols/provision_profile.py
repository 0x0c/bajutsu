"""What a device provider already did to the device a lease hands over."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProvisionProfile:
    """What a `DeviceProvider` already did to the device the lease hands over.

    Carries the state the provider set up before the lease reached the environment (BE-0236). A
    locally-attached device (the default `local` provider) boots and installs the app itself, so
    both flags are False and `start` runs the full adb/simctl bring-up unchanged. A device-cloud
    provider that hands over an already-booted device carrying the build sets them, letting the
    environment skip the boot-readiness wait and/or the install — the one difference a cloud target
    needs, expressed as data on the lease rather than a branch in the runner. Pure config carried
    through the seam; never a verdict input (prime directive 1).
    """

    boot_ready: bool = False
    app_preinstalled: bool = False
