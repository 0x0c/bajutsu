"""The `event` assertion: an analytics event the app sent (BE-0048)."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from ._endpoint_match import _EndpointMatch
from .count_op import CountOp


class EventMatch(_EndpointMatch):
    """An analytics / telemetry event the app *sent* (BE-0048).

    Matched over the captured request timeline by endpoint (url / urlMatches / path / pathMatches /
    method, AND-ed, same meaning as `RequestMatch`) and structured request-body fields (`body`: each
    given key must be present in the JSON request body and equal — compared as text — the given
    value). `count` is the expected multiplicity (default: at least one). At least one of an endpoint
    criterion or `body` is required, so an event always pins *something*.
    """

    body: dict[str, str] = Field(default_factory=dict)
    count: CountOp | None = None

    @model_validator(mode="after")
    def _has_criterion(self) -> Self:
        if self._endpoint_is_empty() and not self.body:
            raise ValueError(
                "event requires at least one of method/url/urlMatches/path/pathMatches/body (§6.4)"
            )
        return self
