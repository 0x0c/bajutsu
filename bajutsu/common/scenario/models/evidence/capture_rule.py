"""One `capture` entry: which evidence kind to take, and when."""

from __future__ import annotations

from pydantic import Field, field_validator

from bajutsu.common.scenario.models._base import _Model, _validate_capture

from .trigger import Trigger


class CaptureRule(_Model):
    """A `capturePolicy` rule — capture the artifacts in `capture` when its `on` trigger fires."""

    on: Trigger
    capture: list[str]
    # Provenance (BE-0044): the instruction this evidence rule was normalized from. Authoring
    # metadata only — `run` never reads it.
    from_: str | None = Field(default=None, alias="from")

    @field_validator("capture")
    @classmethod
    def _cap(cls, v: list[str]) -> list[str]:
        return _validate_capture(v)
