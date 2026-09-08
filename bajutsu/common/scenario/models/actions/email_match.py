"""Which message the `email` action waits for."""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model

from ._functions import _check_regex


class EmailMatch(_Model):
    """Which message `email` waits for: recipient and/or subject, AND-ed. At least one is required."""

    to: str | None = None
    subject: str | None = None
    subject_matches: str | None = Field(default=None, alias="subjectMatches")

    @model_validator(mode="after")
    def _has_criterion(self) -> Self:
        if self.to is None and self.subject is None and self.subject_matches is None:
            raise ValueError("email.match needs at least one of: to / subject / subjectMatches")
        if self.subject_matches is not None:
            _check_regex(self.subject_matches, "email.match.subjectMatches")
        return self
