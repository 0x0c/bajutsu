"""What the evidence writer removes before anything reaches disk."""

from __future__ import annotations

from pydantic import Field

from bajutsu.common.scenario.models._base import _Model


class Redact(_Model):
    """Redaction config — element `labels`, network `headers`, and JSON `fields` to scrub from evidence.

    Each list names items that are zeroed out before evidence is written to the report.
    A standard set of credential-bearing headers (`authorization`, `cookie`, `set-cookie`, …)
    is masked by default (BE-0130); `unmask_headers` is the explicit, visible opt-out that
    releases a specific default — turning off protection is never the mere absence of `redact:`.

    Two element-level defaults join that header set (BE-0331) and take the same shape of opt-out:
    a field the platform itself marks secret, and a field whose identifier or label names a
    credential. Both cover cases a caller should never have to configure, so each releases only
    through its own explicit flag.
    """

    labels: list[str] = Field(default_factory=list)
    headers: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    unmask_headers: list[str] = Field(default_factory=list, alias="unmaskHeaders")
    unmask_secure_fields: bool = Field(default=False, alias="unmaskSecureFields")
    unmask_credential_names: bool = Field(default=False, alias="unmaskCredentialNames")
