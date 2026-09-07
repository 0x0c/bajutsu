"""The inbox seam the `email` step fetches through (BE-0046)."""

from __future__ import annotations

from typing import Protocol

from bajutsu.common.mailbox import MailboxMessage


class MailboxReader(Protocol):
    """Fetches the current inbox for the `email` step (BE-0046). Injected by the runner, built from
    `targets.<name>.mailbox`; None means no mailbox is configured (or the fake driver), in which case
    an `email` step fails cleanly. `fetch` may raise `base.SelectorError` on an unreachable / non-2xx
    endpoint — a clean step failure, never a silent wrong value.

    `timeout` (seconds) bounds a single fetch, so one slow request can't overrun the step's own
    `email.timeout`; the handler passes the time remaining in the poll."""

    def fetch(self, timeout: float) -> list[MailboxMessage]: ...
