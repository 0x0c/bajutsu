"""The `setLocation` action: override the simulated device's GPS position."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class SetLocation(_Model):
    """Override the simulated device's GPS location (simctl location set)."""

    lat: float
    lon: float
