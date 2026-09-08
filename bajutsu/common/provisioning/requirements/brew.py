"""The install method for a tool a Homebrew formula provides (macOS only)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Brew:
    """Provided by a Homebrew formula (macOS only): ``brew install <formula>``."""

    formula: str
