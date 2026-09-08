"""The correlation context variables and reserved record attributes the log schema is built on."""

from __future__ import annotations

import logging
from contextvars import ContextVar

# Correlation ids, carried out-of-band so they need not thread through every signature.
_request_id: ContextVar[str | None] = ContextVar("bajutsu_request_id", default=None)
_org: ContextVar[str | None] = ContextVar("bajutsu_org", default=None)
_actor: ContextVar[str | None] = ContextVar("bajutsu_actor", default=None)
_job_id: ContextVar[str | None] = ContextVar("bajutsu_job_id", default=None)
_run_id: ContextVar[str | None] = ContextVar("bajutsu_run_id", default=None)

# The schema's correlation keys, rendered explicitly (and so excluded from the generic extras).
_CONTEXT_KEYS: tuple[tuple[str, ContextVar[str | None]], ...] = (
    ("request_id", _request_id),
    ("org", _org),
    ("actor", _actor),
    ("job_id", _job_id),
    ("run_id", _run_id),
)

# LogRecord attributes present on a bare record — anything else a caller attached via `extra`.
_RESERVED: frozenset[str] = frozenset(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "taskName",
    "event",
}
