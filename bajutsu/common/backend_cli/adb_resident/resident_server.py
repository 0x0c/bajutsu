"""The on-device resident UiAutomator server for one device lease (BE-0245)."""

from __future__ import annotations

import contextlib
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from bajutsu.common.backend_cli import adb
from bajutsu.common.drivers.adb import ActOutcome, ActRequest, AdbResidentError, HierarchyRead

from ._functions import (
    _default_spawn,
    _parse_forward_port,
    act,
    fetch_clock,
    fetch_source,
    narrow_to_active_window,
)
from ._process import _Process
from ._shared import _SERVER_APK, _TEST_APK, logger
from .resident_channel import ResidentChannel

Spawn = Callable[[list[str]], _Process]
Fetch = Callable[[int, float | None], HierarchyRead]
ClockProbe = Callable[[int], float | None]
ActProbe = Callable[[int, ActRequest], ActOutcome]


class ResidentServer:
    """The on-device resident server for one device lease (BE-0245).

    `start` installs the server APKs, launches the blocking instrumentation, forwards a host port, and
    waits — a bounded connect retry, a condition wait with no fixed sleep — until the socket answers,
    returning a `ResidentChannel` (a per-read hierarchy fetch and a device-clock probe) the driver
    calls per read and per gesture. `stop` kills the instrumentation and removes the forward. Any
    startup failure raises `AdbResidentError`, so the caller degrades to `uiautomator dump` rather than
    failing the run.
    """

    _READY_TIMEOUT_S = 20.0  # generous: instrumentation install + UiAutomation session bring-up
    _READY_POLL_S = 0.2

    def __init__(
        self,
        serial: str,
        *,
        run: adb.RunFn = adb.real_run,
        spawn: Spawn = _default_spawn,
        fetch: Fetch = fetch_source,
        clock: ClockProbe = fetch_clock,
        act_probe: ActProbe = act,
        server_apk: Path = _SERVER_APK,
        test_apk: Path = _TEST_APK,
    ) -> None:
        self._serial = adb.checked_serial(serial)
        self._run = run
        self._spawn = spawn
        self._fetch = fetch
        self._clock = clock
        self._act = act_probe
        self._server_apk = server_apk
        self._test_apk = test_apk
        self._proc: _Process | None = None
        self._host_port: int | None = None

    def start(self) -> ResidentChannel:
        if not self._server_apk.exists() or not self._test_apk.exists():
            raise AdbResidentError(
                f"resident server APKs not built ({self._server_apk}); run "
                "`make -C BajutsuAndroidUIAutomatorServer build`"
            )
        try:
            # Clear both first. A device carrying an older pair fails `install -r` outright when the
            # signing key differs, and where it succeeds it can leave the instrumentation and the
            # server disagreeing about which endpoints exist — a `/act` that 404s against a server
            # that has one, which is the confusing half of this channel's failure modes.
            for package in (adb.RESIDENT_TEST_PACKAGE, adb.RESIDENT_SERVER_PACKAGE):
                with contextlib.suppress(subprocess.CalledProcessError, OSError):
                    self._run(adb.uninstall_cmd(self._serial, package))
            self._run(adb.install_cmd(self._serial, str(self._server_apk)))
            self._run(adb.install_cmd(self._serial, str(self._test_apk)))
            self._proc = self._spawn(adb.instrument_cmd(self._serial))
            self._host_port = _parse_forward_port(self._run(adb.forward_cmd(self._serial)))
        except (subprocess.CalledProcessError, OSError, AdbResidentError) as exc:
            # AdbResidentError included so an unparseable forward port (raised by _parse_forward_port
            # on the line above) still tears down the already-spawned instrumentation and forward
            # rather than leaking them — start() is the only place that can clean up, since the caller
            # never sees the ResidentServer when start() raises.
            self.stop()
            raise AdbResidentError(f"could not start the resident server: {exc}") from exc
        self._await_ready()
        # Capture the port (not self._host_port, which stop() clears): after stop() the fetch raises
        # AdbResidentError, which the driver latches into its dump fallback — a clean degrade.
        port = self._host_port

        def fetch(since: float | None) -> HierarchyRead:
            try:
                read = self._fetch(port, since)
                narrowed = narrow_to_active_window(read.text)
                # Only when narrowing actually changed something: an active-window dump with no system
                # decor to strip passes through unchanged, and carrying an identical `raw` alongside
                # `text` would make every `rawTree` capture write two copies of the same body.
                raw = read.text if narrowed != read.text else None
                return HierarchyRead(narrowed, read.mark, raw=raw, native_z=read.native_z)
            except AdbResidentError:
                # Stop the resident server before the driver degrades to `uiautomator dump`. A read
                # fault is usually a wedged-but-alive instrumentation — a read that outran the socket
                # timeout, not a dead process — and it still holds the device's single UiAutomation
                # session. A fallback dump connects its own (BE-0245: the dump path "spins up a fresh
                # instrumentation, connects a UiAutomation"), so while the resident server lives the
                # dump reads an empty tree for the rest of the lease, breaking every later read.
                # Tearing it down here releases that session, making the fallback a clean degrade
                # rather than one poisoned by the very server it replaces. stop() is idempotent, so
                # the environment's own end-of-lease stop() stays a safe no-op.
                self.stop()
                raise

        def clock() -> float | None:
            # The device-clock probe the driver takes before each gesture (BE-0332 Unit 3). Already
            # non-raising (None on any fault), so unlike `fetch` it never tears the channel down: a
            # missing mark only drops the barrier back to its wall-clock budget for that one gesture,
            # and a genuine channel death still surfaces through the next `fetch`.
            return self._clock(port)

        def act_on_device(request: ActRequest) -> ActOutcome:
            # Unlike `fetch`, a fault here does not tear the channel down. The reads are still good —
            # an older server answers 404 for this path alone — and the driver's own degrade puts the
            # gesture back on the coordinate actuators. Killing a working read channel over a missing
            # actuation endpoint would trade a small regression for a large one.
            return self._act(port, request)

        return ResidentChannel(fetch, clock, act_on_device)

    def stop(self) -> None:
        """Kill the instrumentation and remove the forward; safe to call on a partial start."""
        if self._proc is not None:
            with contextlib.suppress(OSError):
                self._proc.terminate()
            # Reap the terminated adb client so a long-lived `serve` process does not accumulate a
            # zombie per lease (terminate() alone leaves the child unwaited on POSIX). If terminate()
            # does not bring it down in time, escalate to kill() so a stuck process is still reaped —
            # otherwise the guarantee this wait exists for would silently not hold.
            with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                self._proc.wait(timeout=5)
            if self._proc.poll() is None:
                with contextlib.suppress(OSError):
                    self._proc.kill()
                with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                    self._proc.wait(timeout=5)
            self._proc = None
            # Killing the local adb client does not reliably stop the device-side instrumentation, so
            # force-stop its package too — otherwise a resident @Test could outlive the lease.
            try:
                self._run(adb.force_stop_cmd(self._serial, adb.RESIDENT_SERVER_PACKAGE))
            except (subprocess.CalledProcessError, OSError) as exc:
                logger.debug("resident force-stop failed (%s); instrumentation may linger", exc)
        if self._host_port is not None:
            with contextlib.suppress(subprocess.CalledProcessError, OSError):
                self._run(adb.forward_remove_cmd(self._serial, self._host_port))
            self._host_port = None

    def _await_ready(self) -> None:
        # A bounded condition wait, not a fixed sleep: poll until the socket answers. Before the server
        # binds, the connect is refused immediately (fast), so the fetch timeout only applies once the
        # server is essentially up — the effective ceiling stays ~_READY_TIMEOUT_S.
        assert self._host_port is not None
        deadline = time.monotonic() + self._READY_TIMEOUT_S
        while True:
            try:
                self._fetch(self._host_port, None)  # a readiness probe waits past no mark
            except AdbResidentError:
                # The polled fetch failing is the expected not-up-yet signal, not a cause to chain;
                # these raises are the terminal startup verdict, so break the exception chain.
                if self._proc is not None and self._proc.poll() is not None:
                    self.stop()
                    raise AdbResidentError(
                        "resident instrumentation exited before serving"
                    ) from None
                if time.monotonic() >= deadline:
                    self.stop()
                    raise AdbResidentError(
                        f"resident server did not answer within {self._READY_TIMEOUT_S:.0f}s"
                    ) from None
                time.sleep(self._READY_POLL_S)
            else:
                return
