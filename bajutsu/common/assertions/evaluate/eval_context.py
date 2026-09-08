"""The per-run inputs the context-bearing assertion kinds read, bundled as one value (BE-0250)."""

from __future__ import annotations

from dataclasses import dataclass

from bajutsu.common.assertions.schema import SchemaContext
from bajutsu.common.assertions.visual import VisualContext

from .golden_context import GoldenContext


@dataclass(frozen=True)
class EvalContext:
    """The per-run inputs the context-bearing assertion kinds need, bundled as one value (BE-0250).

    Each field feeds exactly one kind: `visual` the screenshot/baseline paths, `schema` the
    JSON-Schema directory, `golden` the goldens directory, and `clipboard` the device pasteboard
    text already read for the block. Bundling replaces the four loose keyword-only parameters that
    were threaded in lockstep through `evaluate` -> `evaluate_one` -> `run_scenario` ->
    `_run_step_body` -> the runner, so a new context-bearing kind adds a field here instead of a
    parameter at every layer. `clipboard` stays a resolved value, not a reader: the read is gated
    and performed once per block by the runner's `_clipboard_for`, so bundling never turns it into a
    per-step read.
    """

    visual: VisualContext | None = None
    schema: SchemaContext | None = None
    golden: GoldenContext | None = None
    clipboard: str | None = None
