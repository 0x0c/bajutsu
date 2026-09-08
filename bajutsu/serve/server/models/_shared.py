"""The column types every model shares, including the JSON variant Postgres upgrades to JSONB."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

# JSONB on Postgres (production); the portable JSON type on SQLite (the gate).
_JSON = JSON().with_variant(JSONB, "postgresql")
