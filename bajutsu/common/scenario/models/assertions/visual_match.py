"""The `visual` assertion: a screenshot against its approved baseline."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector

from .exclude_region import ExcludeRegion
from .selector_region import SelectorRegion


class VisualMatch(_Model):
    """Visual regression assertion — compare a screenshot to a baseline image.

    By default the whole screen is compared. `element` (BE-0171) scopes the comparison to one
    element's frame: the screenshot is cropped to it and the baseline is that crop, so unrelated
    on-screen changes no longer churn the baseline.
    """

    baseline: str
    element: Selector | None = None  # scope the comparison to this element's frame (BE-0171)
    compare: Literal["exact", "pixelmatch"] | None = None
    threshold: float = 0.0  # allowed diff percentage (0.0 = exact match)
    color_tolerance: float = Field(default=0.1, ge=0.0, le=1.0, alias="colorTolerance")
    antialiasing: bool = True
    exclude: list[ExcludeRegion | SelectorRegion] | None = None

    @model_validator(mode="after")
    def _engine_fields(self) -> Self:
        pm_fields = {"color_tolerance", "antialiasing"} & self.model_fields_set
        if self.compare == "exact" and pm_fields:
            raise ValueError(
                "colorTolerance/antialiasing are pixelmatch-only; "
                "remove them or set compare to 'pixelmatch'"
            )
        return self
