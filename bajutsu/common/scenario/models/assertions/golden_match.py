"""The `golden` assertion: the live element tree against a recorded golden (BE-0006)."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class GoldenMatch(_Model):
    """`golden`: compare the live element tree against a recorded golden file (BE-0006).

    The `path` is resolved against the golden context's base directory. The comparison is
    field-level per BE-0006 rules: exact on identity/state, set-equal on traits, tolerant
    (sanity only) on frame geometry.
    """

    path: str = Field(min_length=1)
