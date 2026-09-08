"""The ref patterns and cache layout a Git config source is materialized against."""

from __future__ import annotations

# owner/repo constrained to GitHub's real charset (BE-0124): an owner is alphanumeric + hyphen (a
# username/org — no dot, so it can never be a `.`/`..` traversal token), a repo also allows `_`/`.`
# but a bare `.`/`..` segment is rejected in `parse_config_spec`. Neither admits `%`, so a
# percent-encoded segment simply fails to match — it never reaches the API URL or the cache path.
# These are single-character classes; each regex applies its own quantifier (`+`, or `+?` for the
# git-url repo so a trailing `.git` is stripped rather than folded into the name).
_OWNER = r"[A-Za-z0-9-]"
_REPO = r"[A-Za-z0-9._-]"
