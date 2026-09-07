"""The Git-host calls materialization makes, injected so the logic tests offline."""

from __future__ import annotations

from typing import Protocol

from .git_config_spec import GitConfigSpec


class Transport(Protocol):
    """The Git-host calls materialization makes — injected so the logic tests offline."""

    def commit_sha(self, spec: GitConfigSpec, ref: str) -> str: ...

    def tarball_bytes(self, spec: GitConfigSpec, sha: str) -> bytes: ...
