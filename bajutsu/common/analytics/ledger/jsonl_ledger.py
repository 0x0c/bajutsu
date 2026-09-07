"""The append-only JSONL usage sink, lock-guarded for a concurrent `run --workers`."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .usage_event import UsageEvent


class JsonlLedger:
    """An append-only JSONL sink: one line per event, lock-guarded for concurrent `run --workers`."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()

    def append(self, event: UsageEvent) -> None:
        """Append one event as a JSON line, creating the parent directory on first write."""
        line = json.dumps(event.to_record(), ensure_ascii=False)
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
