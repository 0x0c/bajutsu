"""The real transport: GitHub's commits and tarball endpoints over urllib."""

from __future__ import annotations

import urllib.error
import urllib.request

from bajutsu.common.github.errors import GitHubAccessError

from .git_config_spec import GitConfigSpec


class _GitHubTransport:
    """The real transport: GitHub's commits API (ref → SHA) and tarball endpoint, over urllib."""

    def __init__(self, token: str | None) -> None:
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    def _get(self, url: str, accept: str, spec: GitConfigSpec) -> bytes:
        req = urllib.request.Request(url, headers={**self._headers, "Accept": accept})  # noqa: S310 — https GitHub API URL
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                return bytes(resp.read())
        except urllib.error.HTTPError as e:
            # Map the status (and 403 sub-type) to a cause-naming message instead of letting a raw
            # HTTPError — a bare "404" that really means "no access" — reach the operator (BE-0224).
            # Imported in the method, not at module load: `_functions` constructs this transport,
            # and rule 5 breaks the cycle the split creates on the error path's single edge.
            from ._functions import github_http_error_message

            raise GitHubAccessError(github_http_error_message(e.code, e.headers, spec)) from e

    def commit_sha(self, spec: GitConfigSpec, ref: str) -> str:
        # The `…+sha` media type makes the commits endpoint return the bare SHA as the body.
        url = f"https://api.github.com/repos/{spec.owner}/{spec.repo}/commits/{ref}"
        return self._get(url, "application/vnd.github.sha", spec).decode().strip()

    def tarball_bytes(self, spec: GitConfigSpec, sha: str) -> bytes:
        url = f"https://api.github.com/repos/{spec.owner}/{spec.repo}/tarball/{sha}"
        return self._get(url, "application/vnd.github+json", spec)
