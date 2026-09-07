"""What the guide is told about how this screen was reached."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuideContext:
    """Side information for the guide about how this screen was reached.

    Currently the OS-alert button(s) just dismissed to get here, so an AI guide can factor them
    into its next moves.
    """

    dismissed: tuple[str, ...] = ()
