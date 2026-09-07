"""The seam for a sink that starts a step's screenshot and hands back a join (BE-0407)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from bajutsu.common.drivers import base

from .artifact import Artifact


@runtime_checkable
class DeferredScreenshotSink(Protocol):
    """A sink that can start the step's `after.png` and hand back a join for it (BE-0407 Unit 2).

    The sink half of the overlap; `base.BackgroundScreenshotProvider` is the driver half, and
    `start_after_screenshot` below defers only when both sides answer. Separate from `EvidenceSink`
    so a sink that writes nothing, or one that only records what it was asked for, needs no opinion
    about it — `start_after_screenshot` falls back to the ordinary `capture` call such a sink already
    serves, which is the same shot at the same moment it took before this seam existed. The same
    narrow opt-in the driver-side protocols use.
    """

    def begin_after_screenshot(
        self, driver: base.Driver, step_id: str
    ) -> Callable[[], list[Artifact]]: ...
