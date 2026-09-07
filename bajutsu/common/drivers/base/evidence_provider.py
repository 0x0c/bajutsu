"""The read-only evidence seam a non-actuator backend implements (BE-0020)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bajutsu.common.evidence.network import Collector


@runtime_checkable
class EvidenceProvider(Protocol):
    """A read-only evidence source from a non-actuator backend (BE-0020).

    A multi-backend run keeps actuation on the one actuator and may consult another same-platform
    backend *read-only* to fill an evidence gap the actuator lacks (e.g. a backend with no native
    network capture, so a same-platform backend supplies it). The narrow surface — `capabilities` plus observation
    methods only, never `tap` / `type` / `swipe` / `wait` / `query` — makes "the fallback never
    actuates" a type-level fact rather than a convention.
    """

    name: str

    def capabilities(self) -> set[str]: ...
    def network_collector(self, mocks: list[object] | None = None) -> Collector: ...
