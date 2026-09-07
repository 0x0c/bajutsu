"""Whether a text selection is live, tracked across a run's steps (BE-0265)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SelectionState:
    """Whether a text selection is currently live, tracked across a run's steps (BE-0265).

    `copy` acts on the selection a prior `select` established; no backend exposes selection as
    queryable state, so this is kept Bajutsu-side and uniform across backends: `select` establishes
    it, `copy` reads it without clearing (one selection can be copied more than once), and every
    other *action* invalidates it. `wait` / `assert` are conditions handled in the run loop, never
    routed through the action dispatcher, so they leave a standing selection intact — a `select`,
    then a `wait` for a menu, then `copy` is a valid sequence. A `copy` with no live selection fails
    the step rather than silently copying nothing.

    The transitions live on this type (not in the caller) so the contract stays in one place.
    """

    active: bool = False

    def establish(self) -> None:
        self.active = True

    def invalidate(self) -> None:
        self.active = False
