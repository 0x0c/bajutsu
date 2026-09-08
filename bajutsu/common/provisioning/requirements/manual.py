"""The install method for a tool with no automatic install — the hint tells the user what to do."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Manual:
    """No automatic install exists — ``hint`` tells the user what to do (e.g. install Xcode)."""

    hint: str
