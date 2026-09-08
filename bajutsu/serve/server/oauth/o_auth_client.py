"""The slice of the GitHub OAuth flow serve drives, so a fake can stand in."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .identity import Identity


@runtime_checkable
class OAuthClient(Protocol):
    """The slice of the GitHub OAuth flow the serve operations drive (so a fake can stand in)."""

    def authorize_url(self, state: str) -> str:
        """The GitHub authorize URL to redirect the browser to, carrying the CSRF *state*."""

    def fetch_identity(self, code: str) -> Identity | None:
        """Exchange an authorization *code* for a token and return the GitHub identity (login + org +
        Team memberships), or None on a failed exchange."""
