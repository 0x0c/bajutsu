"""The per-target XCUITest runner block, as written under `xcuitest:` (BE-0019)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._model import _Model


class XcuitestConfig(_Model):
    """Per-target XCUITest runner config (`targets.<name>.xcuitest`, BE-0019)."""

    test_runner: str | None = Field(default=None, alias="testRunner")
    build: str | None = None
    # Which iOS target the same `xcodebuild` driving layer runs against (BE-0238): `simulator`
    # (the BE-0019 default) or a real `device`. It only selects the `-destination` platform and
    # whether simctl device-prep applies; an unknown value fails closed here at config load.
    device_type: Literal["simulator", "device"] = Field(default="simulator", alias="deviceType")
