from __future__ import annotations

from typing import Protocol, runtime_checkable

from bajutsu.common.config import Effective
from bajutsu.crawl import AliveCheck, ClearBlocking, Recover, Reset


@runtime_checkable
class CrawlEnvironment(Protocol):
    """The `crawl` lease surface: the lane shape and health seams the CLI used to branch on the
    actuator for.

    This is the narrower surface the `crawl` command (`cli/commands/crawl.py`) holds; the concrete
    platform classes satisfy it alongside `RunEnvironment`. The three `crawl_*` health methods follow
    the module docstring's first-class-null contract — a platform without a given behavior returns
    `None` rather than raising.
    """

    def has_devices(self) -> bool:
        """Whether this platform drives real devices (web has none). Sizes the crawl's lane-prep
        message and distinguishes the web browser-lane sizing from a device pool."""

    def plan_lanes(self, udid_arg: str, workers: int) -> list[str]:
        """The crawl's lane udids. A device pool resolves *udid_arg* and caps to *workers*; web has no
        device, so *workers* alone sizes the browser-lane set (each lane one browser)."""

    def crawl_reset(self, eff: Effective) -> Reset:
        """A crawl `reset` to a clean start on this lane: relaunch the app (device) or open a fresh
        browser context (web), then wait until the first screen renders."""

    def crawl_aliveness(self) -> AliveCheck | None:
        """The crawl's crash signal for a driver-observed platform (web reads pageerror / HTTP status
        / blank DOM).

        Returns `None` for the device backends (the engine reads the accessibility tree) — a
        first-class "no such signal here", not an unimplemented stub.
        """

    def crawl_recover(self) -> Recover | None:
        """Heal a wedged lane (relaunch a crashed/hung browser) on web.

        Returns `None` where the platform has no in-lane recovery (the device backends) — a
        first-class "no recovery here", not an unimplemented stub.
        """

    def crawl_dialog_clearer(self) -> ClearBlocking | None:
        """Report blocking dialogs auto-cleared this step (web JS dialogs the driver dismisses).

        Returns `None` on platforms with no such auto-clear — a first-class "nothing auto-cleared
        here", not an unimplemented stub.
        """
