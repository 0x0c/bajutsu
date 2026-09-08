"""Where a target's devices come from, as written under `deviceProvider` (BE-0236)."""

from __future__ import annotations

from ._model import _Model


class DeviceProvider(_Model):
    """Where a target's devices come from (`targets.<name>.deviceProvider`, BE-0236).

    `kind` selects the provider adapter from the device-provider registry, defaulting to `local` — a
    locally-attached simulator / emulator / device, exactly today's `--udid` path — so an omitted
    block is unchanged. A device-cloud `kind` reserves a device off-host and hands the run its serial
    / endpoint instead. `endpoint` carries that address for the kinds that need one (the `appium` live
    path points at a reserved iOS device's Appium / WebDriver endpoint, BE-0238). Like the mailbox
    `kind`, an unknown value — or a required-but-missing endpoint — fails closed when the run resolves
    the provider, not here: the deterministic config must not import a cloud SDK (BE-0112).
    """

    kind: str = "local"
    endpoint: str | None = None
