"""The `overrideStatusBar` action: pin the status bar for deterministic screenshots."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class OverrideStatusBar(_Model):
    """Override the Simulator's status bar for deterministic screenshots.

    All fields are optional; only the provided fields are overridden.
    """

    time: str | None = None
    battery_level: int | None = Field(default=None, alias="batteryLevel")
    battery_state: str | None = Field(default=None, alias="batteryState")
    cellular_bars: int | None = Field(default=None, alias="cellularBars")
    wifi_bars: int | None = Field(default=None, alias="wifiBars")
