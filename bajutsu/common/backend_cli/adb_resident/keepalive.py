"""One resident-server connection held across a lease's calls (BE-0407 unit 21)."""

from __future__ import annotations

import contextlib
import http.client
import time
from dataclasses import dataclass

from ._functions import _is_stale

# How long a kept-alive connection may sit unused before it is reconnected rather than reused
# (BE-0407 unit 21). The resident server's own idle ceiling is `SO_TIMEOUT_MS` (5 s), and `_is_stale`
# below narrows but cannot close the race against it — so this stays comfortably inside that ceiling,
# leaving a connection old enough for the staleness check to matter never old enough for the server's
# own timer to have plausibly fired between that check and the send. The same reasoning, and margin, as
# the XCUITest channel's `_KEEPALIVE_IDLE_RECONNECT_SECONDS`.
_KEEPALIVE_IDLE_RECONNECT_S = 2.0


@dataclass
class Keepalive:
    """One HTTP connection to the resident server, reused across a lease's calls (BE-0407 unit 21).

    Every read, clock probe and gesture used to pay its own TCP handshake — 30-150 ms each, against a
    channel a scenario touches several times per step. The server keeps its end open to match. Held by
    the lease's `ResidentServer` rather than by a module global, so two lanes driving two devices never
    share a socket, and passed explicitly to the functions below so a caller that wants a one-shot
    connection (a test, a probe) simply omits it.

    Safe to reuse serially because the driver issues these calls one at a time, on its own thread; the
    one call that does run on a worker — the overlapped screenshot (BE-0407 unit 2) — goes through
    `adb exec-out screencap` and never reaches here.
    """

    conn: http.client.HTTPConnection | None = None
    last_success_at: float | None = None

    def connection(self, host_port: int, timeout: float) -> http.client.HTTPConnection:
        """A connection ready to carry one request: the kept one when it is still good, else a new one."""
        conn = self.conn
        idle_too_long = (
            conn is not None
            and self.last_success_at is not None
            and time.monotonic() - self.last_success_at > _KEEPALIVE_IDLE_RECONNECT_S
        )
        if conn is not None and (idle_too_long or _is_stale(conn)):
            self.discard()
            conn = None
        if conn is not None and conn.sock is None:
            # Nothing to reuse after all; a fresh one below rather than a call on a dead handle.
            self.discard()
            conn = None
        if conn is None:
            conn = http.client.HTTPConnection("127.0.0.1", host_port, timeout=timeout)
            # Split from the send: a connect that fails has delivered nothing, which is what lets a
            # caller tell "never left the host" from "may already have been acted on".
            conn.connect()
            self.conn = conn
        else:
            # A reused connection would otherwise keep whatever timeout its last call set — a read
            # must not inherit an actuation's longer window, nor an actuation a read's shorter one.
            conn.sock.settimeout(timeout)
        return conn

    def succeeded(self) -> None:
        """Mark the exchange complete, so the next call measures its idle gap from here."""
        self.last_success_at = time.monotonic()

    def discard(self) -> None:
        """Drop the connection; the next call opens a fresh one. Never reuse one a failure touched."""
        conn, self.conn = self.conn, None
        if conn is not None:
            with contextlib.suppress(OSError):
                conn.close()
