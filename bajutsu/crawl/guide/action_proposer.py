"""The seam that proposes which operations to try from a screen."""

from __future__ import annotations

from typing import Protocol

from bajutsu.common.drivers import base
from bajutsu.crawl import core as crawl

from .proposal import Proposal


class ActionProposer(Protocol):
    """Proposes the operations to try from a screen, given its elements, screenshot, the deterministic candidates, and any OS prompt just dismissed."""

    def propose(
        self,
        elements: list[base.Element],
        screenshot: bytes | None,
        candidates: list[crawl.Action],
        dismissed: tuple[str, ...],
    ) -> Proposal: ...
