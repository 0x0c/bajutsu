"""Why one cold-spawn attempt did not produce a ready runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class _AttemptFailure:
    """Why one cold-spawn attempt did not produce a ready runner.

    `kind` is what the recovery ladder keys on, so the choice of remedy never depends on parsing the
    prose: `process-exit` is an `xcodebuild` that gave up on its own (a fast, often transient blip),
    `run-ended` an XCTest run that finished without the runner ever serving (the app-launch timeout
    of a degraded Simulator), and `never-ready` a wait that reached its ceiling with the process
    still alive and the run still going. `detail` is the human sentence the failing error quotes.
    """

    kind: Literal["process-exit", "run-ended", "never-ready"]
    detail: str
