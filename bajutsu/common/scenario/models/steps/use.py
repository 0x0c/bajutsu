"""The `use` step: invoke a component, substituting its declared parameters."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class Use(_Model):
    """Invoke a reusable component, substituting its declared params with `with`.

    The `use` step is expanded away (replaced by the component's steps) before the run, so it is a
    compile-time macro, not a runtime action — determinism is unaffected.
    """

    component: str
    with_: dict[str, str] = Field(default_factory=dict, alias="with")
