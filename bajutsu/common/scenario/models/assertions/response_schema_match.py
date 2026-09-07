"""The `responseSchema` assertion: a response's shape, checked against a JSON schema."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model

from .request_match import RequestMatch


class ResponseSchemaMatch(_Model):
    """Validate a captured response body against a stored JSON Schema (BE-0048).

    `request` selects the exchange whose response is checked (reusing the request matcher); `schema`
    is the schema file, resolved against the app's schemas dir. `schema_path` carries the value (the
    field is aliased `schema` to avoid shadowing pydantic's own `schema` attribute).
    """

    request: RequestMatch
    schema_path: str = Field(alias="schema")
