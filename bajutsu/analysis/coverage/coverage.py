"""How a scenario suite's stable-id references cover an app's declared namespaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .namespace_coverage import NamespaceCoverage


@dataclass(frozen=True)
class Coverage:
    """How a scenario suite's stable-id references cover an app's declared namespaces."""

    namespaces: list[
        NamespaceCoverage
    ]  # declared namespaces the suite references, in declared order
    gaps: list[str]  # declared namespaces no scenario references
    off_namespace: list[str]  # referenced ids whose namespace was never declared
    total: int  # declared namespaces
    covered: int  # declared namespaces with at least one referenced id
    coverage: float  # covered / total (1.0 when no namespaces are declared)
