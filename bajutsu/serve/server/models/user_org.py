"""One organization a user may act as, with the role they hold in it."""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserOrg(Base):
    """One org a user may act as, with the role they hold in it.

    A login whose GitHub memberships match several orgs gets a row per match, written fresh on every
    sign-in — the only moment those memberships are known, since no GitHub token is kept afterward.
    `users.org_id` names which one of them is active. The role lives here rather than only on the
    user because a role is per-org by construction: an org's `editor_teams` promotes a member inside
    that org and says nothing about any other.
    """

    __tablename__ = "user_orgs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), primary_key=True)
    role: Mapped[str]  # viewer | editor | admin, resolved for this (user, org) pair
