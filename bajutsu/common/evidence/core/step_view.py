"""The one screenshot and one element tree a viewer shows for a step."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StepView:
    """The one screenshot and one element tree a viewer shows for a step.

    `paired` says whether the two describe the same screen. A viewer that draws element frames onto
    the image — the HTML report's element viewer, the serve editor's picker — must draw none when
    `paired` is false: the frames would land at coordinates that never described that image.
    """

    screenshot: str | None
    elements: str | None
    paired: bool
