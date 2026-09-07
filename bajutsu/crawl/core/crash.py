"""A path whose last action collapsed the app's UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .action import Action


@dataclass(frozen=True)
class Crash:
    """A path whose last action collapsed the app UI.

    `path` holds the human-readable action descriptions (for the report); `actions` the structured,
    replayable sequence the same path is built from, so a deterministic repro scenario can be
    emitted from it (BE-0038). `actions` is empty for a map saved before crashes carried it.
    """

    path: tuple[str, ...]
    actions: tuple[Action, ...] = ()
