"""The selector fields a tool call may carry, as the model fills them in."""

from __future__ import annotations

from typing import TypedDict


class _TargetArgs(TypedDict, total=False):
    """The selector fields a tool call may carry (the runtime counterpart of `_TARGET_PROPS`).

    All optional — a call addresses an element by whichever of these the model filled in; `_target`
    picks id first, then label/value/traits, with index as a last-resort disambiguator.
    """

    id: str
    label: str
    value: str
    traits: list[str]
    index: int
