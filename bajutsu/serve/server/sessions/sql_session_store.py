"""The session store over a sessions table, on Postgres or SQLite (BE-0106)."""

from __future__ import annotations

import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ._shared import _DEFAULT_TTL

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class SqlSessionStore:
    """SessionStore backed by a Postgres (or SQLite) sessions table (BE-0106).

    Replaces `RedisSessionStore`: sessions survive a restart and span replicas exactly as the Redis
    store did, with no second stateful service. Expiry is enforced on read; the engine is injected
    so a test can hand in an in-memory SQLite."""

    def __init__(self, engine: Engine, *, ttl: int = _DEFAULT_TTL) -> None:
        self._engine = engine
        self._ttl = ttl

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        # SQLite returns naive datetimes; Postgres returns aware ones.
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    def issue(self, identity: str | None = None) -> str:
        from sqlalchemy.orm import Session

        from bajutsu.serve.server.models import SessionRecord

        sid = secrets.token_urlsafe(32)
        expires = self._now() + timedelta(seconds=self._ttl)
        with Session(self._engine) as session:
            session.add(SessionRecord(id=sid, identity=identity, expires_at=expires))
            session.commit()
        return sid

    def valid(self, sid: str) -> bool:
        from sqlalchemy.orm import Session

        from bajutsu.serve.server.models import SessionRecord

        with Session(self._engine) as session:
            row = session.get(SessionRecord, sid)
            if row is None:
                return False
            return self._ensure_aware(row.expires_at) >= self._now()

    def identity(self, sid: str) -> str | None:
        from sqlalchemy.orm import Session

        from bajutsu.serve.server.models import SessionRecord

        with Session(self._engine) as session:
            row = session.get(SessionRecord, sid)
            if row is None or self._ensure_aware(row.expires_at) < self._now():
                return None
            return row.identity

    def revoke_identities(self, identities: Iterable[str]) -> int:
        from sqlalchemy import delete
        from sqlalchemy.orm import Session

        from bajutsu.serve.server.models import SessionRecord

        wanted = list(set(identities))
        if not wanted:
            return 0
        # Rows are removed rather than expired in place: a revoked session must not come back if a
        # clock moves, and `valid`/`identity` both read the row before checking its expiry.
        with Session(self._engine) as session:
            result = session.execute(
                delete(SessionRecord).where(SessionRecord.identity.in_(wanted))
            )
            session.commit()
            return int(getattr(result, "rowcount", 0) or 0)
