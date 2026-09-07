"""A repository subtree checked out at an immutable SHA — the config file, its root, and the SHA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Materialized:
    """A repo subtree checked out at an immutable SHA: the config file, the checkout root, and the SHA."""

    config_path: Path
    root: Path
    sha: str  # the resolved commit SHA (the determinism anchor / cache key)
