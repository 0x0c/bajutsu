"""Who signed in: their login, the organizations they belong to, and what that grants."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Identity:
    """Who logged in: the GitHub *login*, the *orgs* (GitHub org logins) they belong to, and the
    *teams* they are a direct member of. Both lists feed the sign-in gate: the org list maps the user
    to a bajutsu org (BE-0015), and the team list (each `"<github-org>/<team-slug>"`) both places a
    login whose org declares Teams and decides the editor/admin role (BE-0313). Both are empty when
    GitHub isn't consulted for them."""

    login: str
    orgs: list[str] = field(default_factory=list)
    teams: list[str] = field(default_factory=list)
