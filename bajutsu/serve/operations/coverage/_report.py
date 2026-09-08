"""One aggregated coverage map: the static dimension plus whichever evidence dimensions apply."""

from __future__ import annotations

import dataclasses

from bajutsu.analysis import coverage as _coverage


@dataclasses.dataclass(frozen=True)
class _Report:
    """One aggregated coverage map: the static dimension, plus whichever evidence dimensions the
    request supplied inputs for."""

    target: str
    static: _coverage.Coverage
    endpoints: _coverage.EndpointCoverage | None = None
    observed: _coverage.ObservedIdCoverage | None = None
    screens: _coverage.ScreenCoverage | None = None

    def html(self) -> str:
        return _coverage.render_html(
            self.static,
            endpoints=self.endpoints,
            observed=self.observed,
            screens=self.screens,
            target=self.target,
        )
