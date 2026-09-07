"""A parsed Git config source: which repository subtree, at which ref, to load a config from."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitConfigSpec:
    """A parsed Git config source: which repo subtree, at which ref, to load the config from."""

    host: str
    owner: str
    repo: str
    ref: str | None  # branch / tag / SHA; None = the repo's default branch
    path: str | None  # config path within the repo; None = DEFAULT_CONFIG at the root
