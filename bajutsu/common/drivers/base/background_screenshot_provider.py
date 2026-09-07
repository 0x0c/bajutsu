"""The seam for a backend that can screenshot while another of its calls is in flight (BE-0407)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable


@runtime_checkable
class BackgroundScreenshotProvider(Protocol):
    """A backend whose screenshot can be taken while another of its calls is in flight (BE-0407 Unit 2).

    The step's mandatory `after.png` is a device round trip, not a write — 103 ms on Android, 90 ms on
    iOS — and the run loop pays it in front of the post-step tree read that follows it. Overlapping the
    two is worth the whole shot, but only where the backend's own channel actually admits a second call.
    Whether it does is the backend's own property, so it is declared here rather than decided by the run
    loop: the orchestrator asks for a handle and, getting none, keeps today's synchronous shot unchanged
    (prime directive 3 — the runner is the same across targets).

    `AdbDriver` implements it: its screenshot is an `adb exec-out screencap` subprocess that touches no
    driver state, and the device really does serve it alongside a hierarchy read (measured on an API 34
    emulator: 456 ms + 1960 ms sequentially, 2189 ms overlapped). XCUITest deliberately does not.
    `APIHandler.serialized` funnels every XCUITest operation onto the runner's main thread because
    XCUITest is not re-entrant — BE-0323 records that concurrent use aborts the XCTest host — so a second
    call would at best be serialized anyway and at worst take the runner down. Playwright's sync API is
    single-threaded for the same kind of reason. Not implementing this means "shoot synchronously",
    which is exactly what those backends did before this seam existed — the same narrow opt-in as the
    protocols above.
    """

    # Start the capture and return the join that finishes it. The join must wait for the bytes to land
    # at `path` and re-raise, unchanged, whatever the synchronous `screenshot()` would have raised — the
    # caller's error handling is the same either way, only its moment moves. Write *into* `path`
    # rather than replacing it (no temp file plus rename): the caller pre-creates it owner-only
    # with `RunArtifactWriter.reserve_restricted`, so a shot holding on-screen secrets is never at
    # the ambient umask for the overlap window; a replacing write would hand that window back
    # (BE-0131).
    def screenshot_in_background(self, path: str) -> Callable[[], None]: ...
