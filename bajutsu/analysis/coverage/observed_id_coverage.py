"""Which declared namespaces a run set actually rendered ids under."""

from __future__ import annotations

from dataclasses import dataclass

from .namespace_coverage import NamespaceCoverage

# --- observed-id coverage: ids rendered across a run set (elements.json) vs declared namespaces ---


@dataclass(frozen=True)
class ObservedIdCoverage:
    """Which declared namespaces a run set actually rendered ids under.

    The run-evidence counterpart to `Coverage` (static references): `coverage()` grades the ids the
    scenarios *write* (statically reference); this grades the ids the runs *showed* (observed across
    every `elements.json`), exposing namespaces the suite never exercised at runtime.
    """

    namespaces: list[
        NamespaceCoverage
    ]  # declared namespaces with at least one observed id, in declared order
    unobserved: list[str]  # declared namespaces rendered in no run
    off_namespace: list[str]  # observed ids whose namespace was never declared
    total: int  # declared namespaces
    covered: int  # declared namespaces with at least one observed id
    coverage: float  # covered / total (1.0 when no namespaces are declared)
