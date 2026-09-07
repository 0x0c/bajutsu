"""The process-local session store — a restart drops every session."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Iterable


class InMemorySessionStore:
    """Sessions in a process-local map (the pre-7b behavior) — a restart drops them, so the user
    simply logs in again. Maps each id to its identity (None for a shared-token login)."""

    def __init__(self) -> None:
        self._sessions: dict[str, str | None] = {}
        self._lock = threading.Lock()

    def issue(self, identity: str | None = None) -> str:
        sid = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[sid] = identity
        return sid

    def valid(self, sid: str) -> bool:
        with self._lock:
            return sid in self._sessions

    def identity(self, sid: str) -> str | None:
        with self._lock:
            return self._sessions.get(sid)

    def revoke_identities(self, identities: Iterable[str]) -> int:
        wanted = set(identities)
        if not wanted:
            return 0
        with self._lock:
            doomed = [sid for sid, who in self._sessions.items() if who in wanted]
            for sid in doomed:
                del self._sessions[sid]
        return len(doomed)
