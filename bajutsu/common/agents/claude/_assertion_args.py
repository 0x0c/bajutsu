"""One entry of the `finish` tool's assertion list, as the model fills it in."""

from __future__ import annotations

from ._target_args import _TargetArgs


class _AssertionArgs(_TargetArgs, total=False):
    """One entry of `finish`'s `assertions` list: a target plus the check to run against it."""

    check: str
    text: str
    intent: str
