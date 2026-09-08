"""A region named by the element that occupies it, rather than by coordinates."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model
from bajutsu.common.scenario.models.selector import Selector


class SelectorRegion(_Model):
    """An element to ignore during visual comparison, addressed by selector (BE-0171).

    Resolved to the element's frame at evaluation time and masked exactly as an `ExcludeRegion`
    rectangle is. Robust where a pixel box is not: it follows the element across reflow, resolution,
    and locale changes. A selector matching nothing is a masking no-op (nothing on screen to hide);
    an ambiguous one fails, like every other selector resolution (prime directive 2).
    """

    selector: Selector
