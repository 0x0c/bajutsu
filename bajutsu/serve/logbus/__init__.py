"""The LogBus seam: how a job's live log reaches a subscriber (BE-0015 local/server parity).

A run/record/crawl job streams output line by line. `LogBus` is the one point where delivery
diverges between local and server hosting: locally lines are buffered in process
(`InMemoryLogBus`); the server backend instead uses `PostCompletionLogBus` (BE-0106), which
serves heartbeats while a job is in flight and the full log from object storage once it
completes, rather than relaying individual lines. A subscriber gets the backlog already
published plus any live lines, and the stream ends once the job is `close`d — so a subscriber
that attaches after the job finished still replays everything.
"""

from ._channel import _Channel as _Channel
from .in_memory_log_bus import InMemoryLogBus
from .log_bus import LogBus

__all__ = ["InMemoryLogBus", "LogBus"]
