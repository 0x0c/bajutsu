"""GitHub OAuth client for the hosted backend (BE-0015 7b-2).

The `OAuthClient` seam is the slice of the OAuth web flow the serve operations need — build the
authorize URL, and exchange a callback code for the GitHub identity (login + org + Team memberships)
— so a fake can drive the gate without contacting GitHub. `GitHubOAuthClient` is the real
implementation; authlib is lazy-imported inside the exchange, so this module imports no authlib and
the default path / import guard stay clean. The org/Team-based sign-in gate and role resolution
(BE-0313) and the CSRF-state check live in the (provider-neutral) operations, not here."""

from ._functions import _ORGS as _ORGS
from ._functions import _TEAMS as _TEAMS
from ._functions import _fetch_orgs as _fetch_orgs
from ._functions import _fetch_teams as _fetch_teams
from ._functions import _paginate as _paginate
from .git_hub_o_auth_client import _AUTHORIZE as _AUTHORIZE
from .git_hub_o_auth_client import _EXCHANGE_URL as _EXCHANGE_URL
from .git_hub_o_auth_client import _SCOPE as _SCOPE
from .git_hub_o_auth_client import _USER as _USER
from .git_hub_o_auth_client import GitHubOAuthClient
from .identity import Identity
from .o_auth_client import OAuthClient

__all__ = ["GitHubOAuthClient", "Identity", "OAuthClient"]
