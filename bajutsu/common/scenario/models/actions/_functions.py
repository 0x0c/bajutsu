"""The load-time validators an action's fields are checked by, so a typo fails before the run."""

from __future__ import annotations

import re


def _check_regex(pattern: str, field: str) -> None:
    """Reject an uncompilable regex at load time, so a typo is a scenario error, not a mid-run crash."""
    try:
        re.compile(pattern)
    except re.error as e:
        raise ValueError(f"{field} is not a valid regex: {e}") from e


def bypass_hint(bypass: str | None) -> str:
    """The shared phrase describing a `manual` step's bypass, or its absence (BE-0185).

    Naming what deterministic bridge to wire (`bypass`) or that none exists — the one wording every
    surface that mentions a takeover's bypass reuses (the run-time FAIL message, the codegen `// TODO`,
    and the `record` marker's TODO), so a future tweak edits one place, not three. Each caller keeps
    its own prefix/suffix around this core; only the shared clause lives here.
    """
    return (
        f"wire a deterministic bypass: {bypass}"
        if bypass
        else "no deterministic run-time equivalent"
    )
