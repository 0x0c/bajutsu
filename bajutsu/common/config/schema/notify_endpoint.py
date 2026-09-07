"""One webhook sink in the `notify:` list (BE-0099)."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from ._functions import _as_list
from ._model import _Model

_NOTIFY_EVENTS = frozenset({"failure", "change", "recovery", "always", "start"})


class NotifyEndpoint(_Model):
    """One webhook notification sink (`notify:` list entry, BE-0099)."""

    format: str = "slack"
    url: str
    on: list[str] = Field(default_factory=lambda: ["failure"])
    targets: list[str] = Field(default_factory=list)

    @field_validator("format")
    @classmethod
    def _known_format(cls, v: str) -> str:
        if v not in ("slack",):
            raise ValueError(f"unknown notify format {v!r}: use 'slack'")
        return v

    @field_validator("on", mode="before")
    @classmethod
    def _norm_on(cls, v: Any) -> Any:
        return _as_list(v)

    @model_validator(mode="after")
    def _known_events(self) -> NotifyEndpoint:
        for event in self.on:
            if event not in _NOTIFY_EVENTS:
                raise ValueError(
                    f"unknown notify event {event!r}: "
                    f"use any of {', '.join(sorted(_NOTIFY_EVENTS))}"
                )
        return self
