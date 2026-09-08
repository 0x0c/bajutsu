"""The mailbox an `email` step polls, as written under `mailbox:` (BE-0046, BE-0186)."""

from __future__ import annotations

from pydantic import Field

from ._model import _Model


class Mailbox(_Model):
    """A mailbox the `email` step polls (`targets.<name>.mailbox`, BE-0046 / BE-0186).

    `kind` selects the transport adapter (`http`, later `imap`) from the mailbox registry, defaulting
    to `http` so a pre-BE-0186 block is unchanged; an unknown `kind` fails closed when the runner
    resolves the mailbox, not here (the deterministic config must not import the registry, BE-0112).
    `url` is the inbox endpoint (GET; commonly `${secrets.*}`), `headers` any auth. The optional
    response mapping absorbs a provider's JSON shape without per-provider code: `messages` is a
    dotted path to the message array (empty = the response is the array), and `fields` maps each
    normalized field (`to` / `subject` / `body` / `receivedAt` / `id`) to the provider's key,
    defaulting to the field's own name.
    """

    kind: str = "http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    messages: str = ""
    fields: dict[str, str] = Field(default_factory=dict)
