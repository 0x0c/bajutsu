"""The seam opaque login-session ids are issued and validated through."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable


@runtime_checkable
class SessionStore(Protocol):
    """Issues and validates opaque login-session ids, optionally bound to an identity."""

    def issue(self, identity: str | None = None) -> str:
        """Mint and remember a new opaque session id, optionally bound to *identity*."""

    def valid(self, sid: str) -> bool:
        """Whether *sid* is a known, live session."""

    def identity(self, sid: str) -> str | None:
        """The identity bound to *sid* (e.g. a GitHub login), or None if it has none / is unknown."""

    def revoke_identities(self, identities: Iterable[str]) -> int:
        """Drop every live session bound to one of *identities*; returns how many were dropped.

        Retiring an org has to reach the sessions its members already hold (BE-0375): a soft delete
        turns away their *next* sign-in, but a cookie issued before it keeps acting as that tenant
        until it expires. Sessions carrying no identity (a shared-token login) are never touched —
        they belong to no org.
        """
