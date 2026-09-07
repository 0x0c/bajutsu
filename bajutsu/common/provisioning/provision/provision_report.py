"""What provisioning actually did, and what it could not do."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProvisionReport:
    """What an execution did: the commands it ran and the remedies it left for the user to do."""

    ran: tuple[tuple[str, ...], ...]
    manual: tuple[str, ...]
