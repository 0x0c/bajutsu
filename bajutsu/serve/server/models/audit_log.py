"""The audit table: one row per recorded control-plane action."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ._functions import _created_at
from ._shared import _JSON
from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)
    action: Mapped[str] = mapped_column(default="")
    target: Mapped[str] = mapped_column(default="")
    at: Mapped[datetime] = _created_at()
    detail: Mapped[dict[str, Any]] = mapped_column(_JSON, default=dict)
