"""The workers table: a worker's advertised capabilities and liveness (BE-0166)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from ._functions import _created_at
from ._shared import _JSON
from .base import Base


class WorkerRecord(Base):
    """A worker's advertised capabilities and liveness, refreshed on every lease poll (BE-0166).

    The post-completion worker model (BE-0106) keeps no standing worker table — a worker is known
    only transiently as `jobs.leased_by`. Capability routing needs one more thing: what the *live*
    pool can serve, so the control plane can tell an operator a queued job is **unroutable** (no
    worker advertises its required capabilities) rather than letting it hang silently. The lease
    path upserts this row each poll (`last_seen` = the poll clock); a worker is "live" while
    `last_seen` is within the lease timeout, the same freshness window heartbeats use.
    """

    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(primary_key=True)  # the worker_id it leases under
    capabilities: Mapped[list[str]] = mapped_column(_JSON, default=list)
    last_seen: Mapped[datetime] = _created_at()  # refreshed on every lease poll / heartbeat
