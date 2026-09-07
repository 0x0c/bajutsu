"""One external piece a backend needs, and how to obtain it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._shared import InstallMethod


@dataclass(frozen=True)
class Tool:
    """An external piece a backend needs, and how to obtain it.

    ``exe`` is the ``command -v`` probe name (also the label `preflight`/`doctor` shows);
    ``install`` is how the installer provisions it when the probe misses.
    """

    exe: str
    install: InstallMethod
