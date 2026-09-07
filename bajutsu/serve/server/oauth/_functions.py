"""Walk GitHub's paginated collections to resolve a signed-in identity."""

from __future__ import annotations

_ORGS = "https://api.github.com/user/orgs"
_TEAMS = "https://api.github.com/user/teams"


def _paginate(client: object, headers: dict[str, str], url: str) -> list[dict[str, object]]:
    """Every list item across a paginated GitHub collection starting at *url*, following the `Link`
    header. Any failure — a non-200, a parse error, or a non-list page — stops and returns what was
    gathered so far; the caller decides what an empty result means for its own failure direction."""
    items: list[dict[str, object]] = []
    next_url: str | None = url
    while next_url:
        resp = client.get(next_url, headers=headers)  # type: ignore[attr-defined]
        if resp.status_code != 200:
            break
        try:
            page = resp.json()
        except ValueError:
            break
        if not isinstance(page, list):
            break
        items.extend(o for o in page if isinstance(o, dict))
        # httpx parses the GitHub `Link` header into `.links`; follow `next` until it's gone.
        next_url = resp.links.get("next", {}).get("url")
    return items


def _fetch_orgs(client: object, headers: dict[str, str]) -> list[str]:
    """Every GitHub org the user belongs to, following pagination (so a user in >30 orgs isn't
    truncated). Org membership maps the user to a bajutsu org *and*, since BE-0313, decides the
    sign-in gate (`identity_matches_org` reads this same list), so a failure here has effects that
    depend on how the login was admitted: an explicit `members` login is unaffected — its org comes
    from that `members` entry, which never consults this list — and so is a login admitted by an
    org's `githubTeams` or `editorTeams`, which reads the Team list below instead. A login relying
    only on `githubOrgs` is turned away at sign-in, since the gate sees no matching org to admit it
    through, *unless* the login is also a member of a configured admin Team, in which case the
    admin-Team bypass admits it into `default` regardless of this failure."""
    return [
        str(o["login"])
        for o in _paginate(client, headers, f"{_ORGS}?per_page=100")
        if o.get("login")
    ]


def _fetch_teams(client: object, headers: dict[str, str]) -> list[str]:
    """Every GitHub Team the user is a *direct* member of, as `"<github-org>/<team-slug>"`, following
    pagination. Team membership grants the editor/admin role (BE-0313) and decides the sign-in gate
    for an org declaring `githubTeams` or `editorTeams`, as well as for a configured admin Team, so
    a failure never *invents* a team: a failure on the first page yields no teams, and a failure
    partway through pagination keeps only the teams already confirmed from earlier pages, never
    granting one that wasn't actually returned by GitHub. For the editor role, and for a login some
    org's `members`/`githubOrgs` entry already admits, that is the opposite failure direction from
    `_fetch_orgs` — the failure costs only a role, never grants one. For a login whose sign-in rests
    on Team membership alone (the admin-Team bypass, or an org whose only roster is a Team), the same
    fail-closed behavior costs sign-in itself, which is the direction a gate has to fail in: one that
    admitted on an unread Team list would admit everyone for the length of the outage. `/user/teams`
    lists a child Team distinct from its parent, so every exact-match check stays flat by
    construction: only the configured Team matches, never a nested one beneath it."""
    teams: list[str] = []
    for t in _paginate(client, headers, f"{_TEAMS}?per_page=100"):
        org = t.get("organization")
        slug = t.get("slug")
        if isinstance(org, dict) and org.get("login") and slug:
            teams.append(f"{org['login']}/{slug}")
    return teams
