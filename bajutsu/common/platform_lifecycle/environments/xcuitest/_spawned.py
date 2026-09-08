"""One cold-spawn attempt's live handles, injectable so the retry seam is Simulator-free (BE-0319)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from bajutsu.common.drivers import base

from ._functions import _never_ended


@dataclass
class _Spawned:
    """One cold-spawn attempt's live handles, injectable so the retry seam is Simulator-free (BE-0319 unit 5).

    Callables rather than the concrete process/driver, so a test can drive `_spawn_cold_with_retry`
    with fakes: `ready` is one `/health` probe, `poll` the `xcodebuild` handle's exit code (`None`
    while alive), `run_ended` the captured output's verdict on whether the test run already finished,
    `log_tail` the captured-output trailer folded into a loud failure, and `discard` the attempt's
    teardown. `run_ended` defaults to the neutral probe so a fake that exercises only the process
    paths need not supply one.
    """

    driver: base.Driver
    ready: Callable[[], bool]
    poll: Callable[[], int | None]
    log_tail: Callable[[], str]
    discard: Callable[[], None]
    run_ended: Callable[[], str | None] = _never_ended
