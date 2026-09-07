"""Server SessionStore implementations for the hosted backend.

`RedisSessionStore` (BE-0015 7b, legacy) keeps sessions in Redis; `SqlSessionStore` (BE-0106) keeps
them in the same Postgres the system of record already uses, so Redis is no longer needed. Both
survive a control-plane restart and span replicas. Clients are **injected**, so the module imports
neither redis nor SQLAlchemy at the top — safe to import and unit-test without the optional extras;
the real client/engine is wired in by the server selection."""

from ._shared import _DEFAULT_TTL as _DEFAULT_TTL
from .redis_like import RedisLike
from .redis_session_store import _SESSION as _SESSION
from .redis_session_store import RedisSessionStore
from .sql_session_store import SqlSessionStore

__all__ = ["RedisLike", "RedisSessionStore", "SqlSessionStore"]
