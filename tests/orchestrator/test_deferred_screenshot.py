"""BE-0407 Unit 2: the step's `after.png` overlaps the post-step read instead of preceding it.

The mandatory shot is a device round trip — 103 ms on Android, measured — that the run loop used to
pay in front of the post-step tree read. On a backend whose channel admits a second call in flight
(`base.BackgroundScreenshotProvider`; adb does, XCUITest does not) the loop now starts the shot and
joins it at the end of the same step, so the read runs inside it. These tests pin the two properties
that make that safe: the read really does happen while the shot is pending, and the shot is always
joined before the step ends — including when the step body raises, which is the path where a pending
capture would otherwise land on the *next* step's screen.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from _orch import FakeClock, _scenario
from conftest import el

from bajutsu.common.drivers import base
from bajutsu.common.drivers.fake import FakeDriver
from bajutsu.common.evidence import FileSink
from bajutsu.common.orchestrator import run_scenario

_GATE_TIMEOUT_S = 5.0


class _OverlappingDriver(FakeDriver):
    """A backend that reports its shot may overlap, and logs the order the loop drives it in.

    The background shot blocks until a `query()` has been seen, so "the read ran inside the shot" is
    proven by the recorded order rather than by a sleep. A loop that joined too early does not hang:
    the gate times out, the shot finishes, and the order it recorded is what fails the assertion.
    """

    def __init__(self, screen: Sequence[base.Element] | None = None) -> None:
        super().__init__(screen)
        self.order: list[str] = []
        self.joins = 0
        self.query_seen = threading.Event()
        self.fail_query_after: int | None = None
        self._queries = 0

    def query(self) -> list[base.Element]:
        self._queries += 1
        self.order.append("query")
        self.query_seen.set()
        if self.fail_query_after is not None and self._queries > self.fail_query_after:
            raise RuntimeError("the device stopped answering mid-step")
        return super().query()

    def screenshot_in_background(self, path: str) -> Callable[[], None]:
        self.order.append("shot started")

        def run() -> None:
            self.query_seen.wait(timeout=_GATE_TIMEOUT_S)
            Path(path).write_bytes(b"\x89PNG")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        def join() -> None:
            thread.join(timeout=_GATE_TIMEOUT_S)
            self.joins += 1
            self.order.append("shot joined")

        return join


def test_the_post_step_read_runs_inside_the_pending_shot(tmp_path: Path) -> None:
    driver = _OverlappingDriver([el("go", "Go", ["button"])])
    result = run_scenario(
        driver,
        _scenario({"name": "x", "steps": [{"tap": {"id": "go"}}]}),
        clock=FakeClock(),
        sink=FileSink(tmp_path / "run1"),
    )
    assert result.ok
    # The read sits between the two, which is the whole saving: before this unit the shot's own round
    # trip completed first and the read followed it.
    assert driver.order == ["shot started", "query", "shot joined"]
    assert (tmp_path / "run1" / "x" / "step0" / "after.png").exists()


def test_a_step_that_raises_still_joins_its_pending_shot(tmp_path: Path) -> None:
    # The `finally` this pins is not tidiness: an unjoined capture would still be writing while the
    # next step actuates, so `after.png` would show a screen this step never saw. It is also what
    # keeps the artifact on the failure path at all — the synchronous shutter got that for free.
    driver = _OverlappingDriver([el("go", "Go", ["button"])])
    driver.fail_query_after = 0  # the post-step read is the first `query()` a plain tap issues
    with pytest.raises(RuntimeError):
        run_scenario(
            driver,
            _scenario({"name": "x", "steps": [{"tap": {"id": "go"}}]}),
            clock=FakeClock(),
            sink=FileSink(tmp_path / "run1"),
        )
    assert driver.joins == 1
    assert (tmp_path / "run1" / "x" / "step0" / "after.png").exists()
