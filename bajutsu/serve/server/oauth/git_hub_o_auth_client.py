"""The real GitHub OAuth client, holding only configuration until a call is made."""

from __future__ import annotations

from urllib.parse import urlencode

from ._functions import _fetch_orgs, _fetch_teams
from .identity import Identity

_AUTHORIZE = "https://github.com/login/oauth/authorize"
_EXCHANGE_URL = "https://github.com/login/oauth/access_token"  # the OAuth token-exchange endpoint
_USER = "https://api.github.com/user"
# `read:org` lets us read the user's org memberships (including private ones) to map them to a
# bajutsu org, and their Team memberships for the sign-in gate and the editor/admin role check
# (BE-0313); `read:user`
# covers the login itself (BE-0015 multi-tenancy).
_SCOPE = "read:user read:org"


class GitHubOAuthClient:
    """Real GitHub OAuth client. Holds only config at construction (no network, no authlib); authlib
    is imported when a code is exchanged."""

    def __init__(self, *, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "scope": _SCOPE,
                "state": state,
            }
        )
        return f"{_AUTHORIZE}?{query}"

    def fetch_identity(self, code: str) -> Identity | None:
        from authlib.integrations.httpx_client import OAuth2Client

        # `with` closes the underlying httpx client, so connections/fds aren't leaked on a busy server.
        with OAuth2Client(
            self._client_id, self._client_secret, redirect_uri=self._redirect_uri
        ) as client:
            # GitHub returns form-encoded by default; ask for JSON so authlib parses the token.
            client.fetch_token(_EXCHANGE_URL, code=code, headers={"Accept": "application/json"})
            headers = {"Accept": "application/vnd.github+json"}
            user = client.get(_USER, headers=headers)
            if user.status_code != 200:
                return None
            login = user.json().get("login")
            if not login:
                return None
            return Identity(
                login=str(login),
                orgs=_fetch_orgs(client, headers),
                teams=_fetch_teams(client, headers),
            )
