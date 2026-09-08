"""The endpoint criteria the request and event assertions share."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class _EndpointMatch(_Model):
    """The endpoint criteria shared by `RequestMatch` and `EventMatch`.

    Pins which exchange to match by `url` (exact full URL), `urlMatches` (regex/substring; query
    strings live here), or just the `path` (`pathMatches` for a regex over the path), optionally
    AND-ed with `method`. Subclasses add their own extra criteria (status / body) and require at
    least one criterion overall.
    """

    method: str | None = None
    url: str | None = None  # exact full URL (the endpoint)
    url_matches: str | None = Field(
        default=None, alias="urlMatches"
    )  # regex/substring over the URL
    path: str | None = None  # exact path (query ignored)
    path_matches: str | None = Field(default=None, alias="pathMatches")  # regex over path

    def _endpoint_is_empty(self) -> bool:
        """Whether no endpoint criterion (method / url / urlMatches / path / pathMatches) is set."""
        return all(
            v is None
            for v in (self.method, self.url, self.url_matches, self.path, self.path_matches)
        )
