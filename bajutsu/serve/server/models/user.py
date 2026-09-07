"""The users table: one row per identity that has signed in."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from ._functions import _created_at
from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"))
    email: Mapped[str] = mapped_column(unique=True)
    github_login: Mapped[str | None] = mapped_column(default=None)
    # Default editor to match the role policy (an allowlisted user can run); admins/viewers come
    # from the env lists, recomputed on each login. Aligned across model / migration / upsert (7c-2).
    role: Mapped[str] = mapped_column(server_default="editor")  # viewer | editor | admin
    # When this user last picked their active org themselves, rather than having it resolved for
    # them at sign-in. Null means `org_id` is whatever the membership ranking answered, which a
    # later sign-in re-resolves freely; set means the user chose it, and sign-in keeps that choice
    # for as long as the org is still one they may act as. A timestamp rather than a flag, like
    # `Org.membership_seeded_at`: it records when.
    org_selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = _created_at()
