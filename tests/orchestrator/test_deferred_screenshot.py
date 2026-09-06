"""BE-0407 Unit 2: the step's `after.png` overlaps the post-step read instead of preceding it.

The mandatory shot is a device round trip — 103 ms on Android, measured — that the run loop used to
pay in front of the post-step tree read. On a backend whose channel admits a second call in flight
(`base.BackgroundScreenshotProvider`; adb does, XCUITest does not) the loop now starts the shot and
joins it at the end of the same step, so the read runs inside it. These tests pin the properties that
make that safe: the read really does happen while the shot is pending; the shot is always joined
before the step ends, including when the step body raises, which is the path where a pending capture
would otherwise land on the *next* step's screen; and moving the join to the end of the step never
lets a failing shot stand in for the failure that caused it.
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
        self.shot_fails = False
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
            if self.shot_fails:
                raise OSError("screencap could not reach the device")

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
    # keeps the shot's bytes on the failure path — the synchronous shutter got that for free.
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


def test_a_failing_shot_is_the_steps_failure_when_nothing_else_failed(tmp_path: Path) -> None:
    # Deferring moves when the shot's failure surfaces, never whether it does: a step whose only
    # fault is its own capture still fails loudly, exactly as the synchronous shutter made it.
    driver = _OverlappingDriver([el("go", "Go", ["button"])])
    driver.shot_fails = True
    with pytest.raises(OSError, match="could not reach the device"):
        run_scenario(
            driver,
            _scenario({"name": "x", "steps": [{"tap": {"id": "go"}}]}),
            clock=FakeClock(),
            sink=FileSink(tmp_path / "run1"),
        )


def test_a_failing_shot_never_replaces_the_steps_own_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # A device that vanishes mid-step fails the read and then fails the shot against the same
    # device. The read's failure is the cause and the shot's is a symptom of it, so the run must
    # report the cause. The lost evidence is still disclosed, never dropped in silence.
    driver = _OverlappingDriver([el("go", "Go", ["button"])])
    driver.fail_query_after = 0
    driver.shot_fails = True
    with (
        caplog.at_level("WARNING"),
        pytest.raises(RuntimeError, match="stopped answering mid-step"),
    ):
        run_scenario(
            driver,
            _scenario({"name": "x", "steps": [{"tap": {"id": "go"}}]}),
            clock=FakeClock(),
            sink=FileSink(tmp_path / "run1"),
        )
    assert "dropping this step's after.png" in caplog.text


def test_the_next_step_reuses_the_deferred_shot_as_its_before_png(tmp_path: Path) -> None:
    # The deferred record is produced late, in the join, and it is what BE-0407 Unit 1's reuse reads
    # to copy the previous step's pixels into this step's `before.png`. A join moved back above that
    # assignment would leave the reuse with nothing and quietly reinstate a per-step screenshot.
    driver = _OverlappingDriver([el("go", "Go", ["button"])])
    result = run_scenario(
        driver,
        _scenario({"name": "x", "steps": [{"tap": {"id": "go"}}, {"tap": {"id": "go"}}]}),
        clock=FakeClock(),
        sink=FileSink(tmp_path / "run1"),
    )
    assert result.ok
    run = tmp_path / "run1" / "x"
    assert (run / "step1" / "before.png").read_bytes() == (run / "step0" / "after.png").read_bytes()
