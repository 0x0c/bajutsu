"""The session store over Redis keys with a TTL, so finished sessions expire themselves."""

from __future__ import annotations

import secrets
from collections.abc import Iterable

from ._shared import _DEFAULT_TTL
from .redis_like import RedisLike

_SESSION = "bajutsu:session:"  # Redis key prefix for a login-session id


class RedisSessionStore:
    """SessionStore backed by Redis keys with a TTL, so finished sessions self-expire. The key's
    value carries the session's identity (or an empty string when it has none)."""

    def __init__(self, redis: RedisLike, *, ttl: int = _DEFAULT_TTL) -> None:
        self._redis = redis
        self._ttl = ttl

    def issue(self, identity: str | None = None) -> str:
        sid = secrets.token_urlsafe(32)
        self._redis.setex(f"{_SESSION}{sid}", self._ttl, identity or "")
        return sid

    def valid(self, sid: str) -> bool:
        return bool(self._redis.exists(f"{_SESSION}{sid}"))

    def identity(self, sid: str) -> str | None:
        raw = self._redis.get(f"{_SESSION}{sid}")
        if raw is None:
            return None
        value = raw.decode() if isinstance(raw, bytes) else str(raw)
        return value or None

    def revoke_identities(self, identities: Iterable[str]) -> int:
        wanted = set(identities)
        if not wanted:
            return 0
        # The identity is the key's *value*, so there is no index to look it up by — every live
        # session key has to be read. Acceptable because revocation is a rare admin action (retiring
        # an org), and the alternative is leaving this store unable to revoke at all, which is the
        # hole BE-0375 closed for the two stores a deployment actually runs.
        doomed = []
        for key in self._redis.scan_iter(f"{_SESSION}*"):
            name = key.decode() if isinstance(key, bytes) else str(key)
            raw = self._redis.get(name)
            if raw is None:
                continue
            who = raw.decode() if isinstance(raw, bytes) else str(raw)
            if who in wanted:
                doomed.append(name)
        if doomed:
            self._redis.delete(*doomed)
        return len(doomed)
