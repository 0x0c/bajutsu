"""The wire keys a handoff request and response are serialized under."""

from __future__ import annotations

# Marks a serialized handoff request on the `record` process's stdout so `serve` can lift it
# out of the otherwise-textual narration stream and turn it into a structured `human-request`
# event rather than a `log` line. The control characters keep it from colliding with narration.
REQUEST_LINE_PREFIX = "\x1eBAJUTSU-HANDOFF-REQUEST\x1e"

# How long a handoff waits on a human before it resolves to a cancel — bounded so no surface
# (a terminal prompt, a `serve` worker) ever hangs indefinitely on someone who walked away.
DEFAULT_TIMEOUT_SECONDS = 300.0
