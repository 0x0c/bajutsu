"""The per-organization AI provider selection, stored in the clear (BE-0229)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ._shared import _JSON
from .base import Base


class ProviderSettingsRow(Base):
    """A per-org AI provider selection, stored in the clear (BE-0229) — the per-organization,
    DB-backed shape BE-0184 deferred until per-org runtime resolution existed to read it. Keyed by
    ``org_id`` (one selection per org): the active provider plus the per-provider model/effort/region
    slot map (BE-0183) and, folded into ``provider``'s companion payload, the output language
    (BE-0188). Unlike `Secret` these are not sensitive — they are read back for editing — so no
    encryption; the ``settings`` map is JSON (JSONB on Postgres) like the other variable payloads."""

    __tablename__ = "provider_settings"

    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), primary_key=True)
    provider: Mapped[str] = mapped_column(default="")  # the active provider ("" = none selected)
    settings: Mapped[dict[str, Any]] = mapped_column(_JSON, default=dict)  # provider -> slot map
