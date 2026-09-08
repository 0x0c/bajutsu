"""One job's buffered lines and the subscribers waiting on them."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class _Channel:
    lines: list[str] = field(default_factory=list)
    closed: bool = False
    final: str | None = None  # terminal status payload recorded at close (a JSON view)
    cond: threading.Condition = field(default_factory=threading.Condition)
