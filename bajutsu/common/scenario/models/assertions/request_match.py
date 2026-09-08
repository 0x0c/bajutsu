"""The `request` assertion: a network call the app made."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from ._endpoint_match import _EndpointMatch


class RequestMatch(_EndpointMatch):
    """Network-traffic matcher, shared by the `request` assertion and `until: { request: ... }`.

    The fields (method / url / urlMatches / path / pathMatches / status / bodyMatches) are AND-ed;
    `count` is how many exchanges matched — exact for the assertion, a lower bound for the wait.
    The endpoint can be pinned by `url` (exact full URL) or `urlMatches` (regex/substring; query
    strings live here), or just the `path`; `bodyMatches` checks the request body. At least one
    match field is required.
    """

    status: int | None = None
    body_matches: str | None = Field(
        default=None, alias="bodyMatches"
    )  # regex/substring over request body
    count: int | None = None

    @model_validator(mode="after")
    def _has_criterion(self) -> Self:
        if self._endpoint_is_empty() and self.status is None and self.body_matches is None:
            raise ValueError(
                "request requires at least one of method/url/urlMatches/path/pathMatches/status/bodyMatches"
            )
        return self
