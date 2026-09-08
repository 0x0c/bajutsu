"""The lifecycle hooks a backend runs around a single run (BE-0141)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BackendLifecycle(Protocol):
    """The full set of lifecycle hooks backends run around a single run (BE-0141).

    A run launches, tears down, and resets a backend, but those steps are platform-shaped: the web
    (Playwright) backend navigates / closes / resets a browser context, the XCUITest backend waits
    for its on-device runner to answer (and probes its health once during a cold spawn, BE-0319), and
    the fake backend needs none of them. These hooks are therefore split disjointly across backends —
    no single driver implements the whole set — so this is a *typing umbrella* for the call sites, not
    a conformance target: the `platform_lifecycle` environments reach each hook through
    `cast(BackendLifecycle, driver)` under the platform invariant that already scopes the driver,
    which turns "the hook exists" into a mypy-checked fact (a renamed or dropped hook fails
    `make check` instead of at runtime) without forcing a lifecycle-free backend to stub no-op methods. `@runtime_checkable`
    mirrors `EvidenceProvider`, but a structural `isinstance` holds only for a class implementing the
    whole set — which the concrete drivers, owning disjoint subsets, deliberately do not.
    """

    def navigate(self) -> None: ...
    def close(self) -> None: ...
    def reset_context(self) -> None: ...
    def await_ready(self, timeout: float = 10.0, poll: float = 0.1) -> None: ...
    def health_ready(self) -> bool: ...
