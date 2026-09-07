"""One discovered screen in the map."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    """A discovered screen.

    Its fingerprint, the identifiers present, the candidate action keys leaving it, `blocked` —
    actionable controls present but disabled (known but un-pressable until a precondition is met) —
    and `targets`: per candidate action, the on-screen rectangle it taps, normalized to [0,1] of
    the screen and keyed by the action's description, so the web UI can highlight on the screenshot
    where a transition's tap lands.
    """

    fingerprint: str
    kind: str
    ids: tuple[str, ...]
    actions: tuple[str, ...]
    blocked: tuple[str, ...] = ()
    targets: tuple[tuple[str, tuple[float, float, float, float]], ...] = ()
