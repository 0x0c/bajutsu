"""A candidate operation skipped because another screen already claimed it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .action import Action


@dataclass(frozen=True)
class Pruned:
    """A candidate operation skipped because the same operation was already claimed by another screen.

    A *global* control (e.g. a tab switch) the crawl explores once instead of from every screen
    that shows it. `src` is the screen where it was skipped, `action` its description, `key` its
    replay identity, `owner` the screen that did explore it, and `path` the replayable action
    sequence to reach `src` and perform the op (so a resume can re-walk to here). The WebUI shows
    these struck through, and a viewer can tap one to resume exploring that branch from `src`.
    """

    src: str
    action: str
    key: str
    owner: str
    path: tuple[Action, ...] = ()
