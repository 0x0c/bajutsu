"""An input the caller can fix — no config, an unknown target, an unreadable suite."""

from __future__ import annotations


class _CoverageError(Exception):
    """An input the caller can fix (no config, unknown target, unreadable suite), with its status.

    Raised by `_aggregate` so the JSON and HTML entry points can report the same problem in the shape
    each one's client expects, without threading an error tuple through the aggregation.
    """

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status
