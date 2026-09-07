"""One transition: taking an action from one screen landed on another."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    """A transition: taking `action` from screen `src` landed on screen `dst`.

    `alert` holds the OS-prompt button(s) the guard dismissed during this transition (empty when
    none) — so the graph can show that the step required tapping through a system alert.
    """

    src: str
    action: str
    dst: str
    alert: tuple[str, ...] = ()
