"""The crawl's accumulated model: its screens, transitions, crashes, plan, and why it stopped."""

from __future__ import annotations

from dataclasses import dataclass, field

from .action import Action
from .alert import Alert
from .crash import Crash
from .edge import Edge
from .node import Node
from .pruned import Pruned


@dataclass
class ScreenMap:
    """The crawl's accumulated model: the discovered screens, transitions, crashes, alerts, the live exploration plan, and why it stopped."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    crashes: list[Crash] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    # The exploration plan: still-untried operations per screen fingerprint (what the crawl will
    # try next), refreshed as it advances so a reader can visualize the frontier live.
    plan: dict[str, list[str]] = field(default_factory=dict)
    # Operations pruned as duplicate global controls (explored once from their owner screen).
    pruned: list[Pruned] = field(default_factory=list)
    # The canonical replayable action path from the entry screen to each discovered screen, keyed by
    # fingerprint (empty for the entry screen itself). This is what turns a discovered screen into a
    # committable candidate flow scenario (`flows.py`, BE-0038).
    paths: dict[str, tuple[Action, ...]] = field(default_factory=dict)
    # Why the crawl stopped: "completed" (frontier exhausted — everything reachable in the model
    # was explored), "max_screens", or "max_steps" (a budget was hit, so screens may remain).
    stop_reason: str = ""
