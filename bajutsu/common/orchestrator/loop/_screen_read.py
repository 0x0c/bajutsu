"""A step's post-step screen read, taken at most once and cached (BE-0234)."""

from __future__ import annotations

from collections.abc import Callable

from bajutsu.common.drivers import base


class _ScreenRead:
    """A step's post-step screen read, taken at most once and cached (BE-0234 Unit 2).

    On the adb backend a screen read (`uiautomator dump`) is the dominant per-step cost — ~2.4s
    against ~0.1-0.3s for a lighter read channel — so the end-of-step read is deferred until a
    consumer actually needs it: a `screenChanged` capture, an `extract`, a `wait`-timeout
    diagnostic, or the always-on post-step `elements` write. That last one makes the read
    unconditional under any sink that writes, so the deferral now buys a run nothing beyond a
    `NullSink` — where a plain `tap`/`assert` step with none of the other three still never reads.
    When it is read, the tree also seeds the next step's `before` — nothing actuates between a
    step's `after` and the next step's `before`, so they observe identical device state.

    A non-mutating step (`assert`, `wait`) already queried the tree to evaluate itself, and nothing
    actuates between that query and this read, so the caller can `seed` it with that snapshot: a
    consumer then reuses it instead of issuing a second identical query (BE-0259). A seeded read is
    not a runner-issued read — `queried` stays False — so the BE-0234 read-count yardstick keeps
    counting only the queries this class actually performs. The seed is also the one tree that
    predates the step's post-action shutter (`_handle_action`), since the body took it: on those two
    step kinds the recorded `elements.json` is that fraction older than the `after.png` beside it.

    `read` overrides the default `query()` for the first, uncached read: a step whose `extract` will
    consume the tree passes a property-aware settle poll here (`_settle_extract_read`), so the value
    it copies out is a settled one rather than whichever was still propagating when a single read
    fired (BE-0299 Unit 3). It is mutually exclusive with `seed` — a seeded step is refined at its
    earlier read site instead — and only fires on a genuine read, so `queried` still reflects one.
    """

    def __init__(
        self,
        driver: base.Driver,
        seed: list[base.Element] | None = None,
        *,
        read: Callable[[], list[base.Element]] | None = None,
    ) -> None:
        # A seed short-circuits `.get()`, so a `read` passed alongside one would be silently dropped —
        # fail loudly instead (the two are mutually exclusive by construction; see the class docstring).
        assert not (seed is not None and read is not None), "seed and read are mutually exclusive"
        self._driver = driver
        self._tree = seed
        self._available = seed is not None
        self._queried = False
        self._read = read

    def get(self) -> list[base.Element]:
        """The post-step tree: the seed if one was given, else read once (via `read`) and cached."""
        if not self._available:
            self._tree = self._read() if self._read is not None else self._driver.query()
            self._available = True
            self._queried = True
        assert (
            self._tree is not None
        )  # set on seed or the read above; narrows the Optional for mypy
        return self._tree

    @property
    def cached(self) -> list[base.Element] | None:
        """The tree if seeded or already read, else None — so a capture can read lazily on its own."""
        return self._tree if self._available else None

    @property
    def queried(self) -> bool:
        """Whether `get()` issued a `query()` — False for a seeded (reused) tree."""
        return self._queried
