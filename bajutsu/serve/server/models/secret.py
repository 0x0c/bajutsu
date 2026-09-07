"""The secrets table: a per-organization operator secret, encrypted at rest (BE-0136)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ._functions import _created_at
from .base import Base


class Secret(Base):
    """A per-org operator secret, encrypted at rest (BE-0136 write-once secrets). Keyed by
    (org_id, name) — one value per named secret per org. Only the ciphertext is stored; the
    plaintext exists only transiently inside the store that decrypts it, never in a column."""

    __tablename__ = "secrets"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), primary_key=True)
    name: Mapped[str] = mapped_column(primary_key=True)  # the logical secret name, e.g. "aiApiKey"
    ciphertext: Mapped[str]  # a Fernet token (authenticated encryption), never the plaintext
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)
    updated_at: Mapped[datetime] = _created_at()
