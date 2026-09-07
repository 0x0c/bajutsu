"""What an AI call's tokens were spent on — the ledger's non-token dimensions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Attribution:
    """What an AI call's tokens were spent on — the ledger's non-token dimensions."""

    command: str | None = None
    scenario: str | None = None
    step: str | None = None
