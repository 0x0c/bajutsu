"""The slice of a redis-py client the Redis session store uses, so a fake can stand in."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class RedisLike(Protocol):
    """The slice of a redis-py client `RedisSessionStore` uses (so a fake can stand in)."""

    def setex(self, key: str, seconds: int, value: str) -> object:
        """Set *key* to *value* with a *seconds* time-to-live."""

    def exists(self, key: str) -> object:
        """Return a truthy count when *key* exists."""

    def get(self, key: str) -> object:
        """Return *key*'s value (bytes), or None if unset."""

    def scan_iter(self, match: str) -> Iterable[object]:
        """Iterate the keys matching *match* (a glob), as redis-py's own `scan_iter` does."""

    def delete(self, *keys: str) -> object:
        """Delete the named keys, returning how many existed."""
