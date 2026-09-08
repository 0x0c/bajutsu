"""One platform's whole app lifecycle: the union of the `run` and `crawl` lease surfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .crawl_environment import CrawlEnvironment
from .run_environment import RunEnvironment


@runtime_checkable
class Environment(RunEnvironment, CrawlEnvironment, Protocol):
    """One platform's whole app lifecycle: the union of the `run` and `crawl` lease surfaces.

    Every concrete platform class satisfies this combined surface, and `environment_for` returns it;
    each consumer then narrows to the one it needs (`RunEnvironment` for the run pipeline,
    `CrawlEnvironment` for the crawl command). See the module docstring for the "not applicable"
    contract and the "adding a platform" checklist.
    """
