"""One request and response the app under test reported."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NetworkExchange(BaseModel):
    """One request/response the app reported.

    Extra keys from the SDK are ignored (forward-compatible); field names accept their JSON aliases.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    method: str = ""
    url: str = ""
    path: str = ""  # path only (no query), for matching
    status: int | None = None
    request_headers: dict[str, str] = Field(default_factory=dict, alias="requestHeaders")
    response_headers: dict[str, str] = Field(default_factory=dict, alias="responseHeaders")
    request_body: str | None = Field(default=None, alias="requestBody")
    response_body: str | None = Field(default=None, alias="responseBody")
    started_at: float | None = Field(default=None, alias="startedAt")
    duration_ms: float | None = Field(default=None, alias="durationMs")
    mocked: bool = False  # served by a bajutsu mock stub (not a real network call)
