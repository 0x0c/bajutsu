"""The slice of an RQ queue the queue executor needs, so a fake can stand in."""

from __future__ import annotations

from typing import Protocol


class Queue(Protocol):
    """The slice of an RQ ``Queue`` that `QueueExecutor` needs (so a fake can stand in)."""

    def enqueue(self, func: object, *args: object, **kwargs: object) -> object:
        """Enqueue *func* with *args* for a worker to run; the return value is ignored."""
