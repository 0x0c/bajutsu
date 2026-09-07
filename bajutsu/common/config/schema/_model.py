"""The strict Pydantic base every config model is built on, so an unknown key fails loudly."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
