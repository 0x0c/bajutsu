"""How the `email` action pulls a value out of the matched message."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model

from ._functions import _check_regex


class EmailExtract(_Model):
    """Pull a value from the matched message body into `${vars.<var>}` via a regex.

    `bodyMatches` is a regex; its first capturing group (or the whole match, if it has none) is the
    value written to `var`. A matched message whose body the regex does not hit fails the step.
    """

    var: str
    body_matches: str = Field(alias="bodyMatches")

    @model_validator(mode="after")
    def _valid_regex(self) -> Self:
        _check_regex(self.body_matches, "email.extract.bodyMatches")
        return self
