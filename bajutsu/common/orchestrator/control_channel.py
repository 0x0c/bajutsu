"""The acknowledgement wait behind a mid-scenario command (BE-0365 unit 3).

`NetworkCollector` holds the queue and the reports; this turns them into something the run loop can
depend on. A caller that queued a command and then slept for "long enough" would be exactly the
fixed sleep prime directive 2 forbids, so a command here either provably took effect before the
caller continues or the caller fails saying why — the three answers `report_for` keeps distinct
(nothing yet, applied, refused with the app's own reason) reach the caller as three outcomes, never
collapsed into one.

Nothing here reads a verdict or feeds one: a command names a piece of bajutsu's own in-app
instrumentation and the state it should take, and no assertion sees this module.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from bajutsu.common.cancellation import CancelSource, RunCancelled, not_cancelled
from bajutsu.common.drivers.base import deadline_ticks
from bajutsu.common.evidence.network import Collector, ControlChannel, InAppCapability

_logger = logging.getLogger(__name__)

# The app polls the collector on its own timer, so the round trip is that interval plus a main-thread
# hop and the acknowledging POST. The ceiling is generous against it rather than tuned to it: a wait
# that expires is reporting a channel that is not answering at all, not one that answered slowly.
ACK_TIMEOUT = 5.0
_ACK_POLL_INIT = 0.02
_ACK_POLL_MAX = 0.2


class ControlChannelError(RuntimeError):
    """A command did not provably take effect, so the caller must fail rather than continue."""


def apply_capability(
    channel: Collector | None,
    capability: InAppCapability,
    *,
    enabled: bool,
    timeout: float = ACK_TIMEOUT,
    cancelled: CancelSource = not_cancelled,
) -> None:
    """Ask the running app to put one in-app capability into `enabled`, and wait for it to confirm.

    Args:
        channel: The run's collector. One that carries no channel is an error, not a no-op — see
            below.
        capability: The piece of bajutsu's in-app instrumentation to address.
        enabled: The state it should take.
        timeout: Seconds to wait for the app's acknowledgement.
        cancelled: The run's own cancel source (BE-0370), checked inside the poll like every other
            condition wait — so a cancelled run does not spend the full timeout here before its
            `SIGTERM` reaches the caller.

    Raises:
        ControlChannelError: The collector carries no channel, the app never acknowledged, or it
            acknowledged a refusal. A run that reached this call needs the command to have taken
            effect, so every one of those is louder than skipping: skipping would leave the caller
            proceeding on an app state it never established.
        RunCancelled: The run was cancelled while this wait was still polling.
    """
    if not isinstance(channel, ControlChannel):
        raise ControlChannelError(
            f"cannot set {capability.value}={str(enabled).lower()}: this run's collector "
            f"({type(channel).__name__}) carries no control channel. The channel rides the HTTP "
            "collector the app POSTs to, so it reaches an app bajutsu launched with "
            "BAJUTSU_COLLECTOR — not a backend whose network is observed through the driver."
        )
    command_id = channel.enqueue_command(capability, enabled=enabled)
    for _ in deadline_ticks(timeout, _ACK_POLL_INIT, _ACK_POLL_MAX):
        report = channel.report_for(command_id)
        if report is None:
            if cancelled():
                raise RunCancelled
            continue
        if report.applied:
            return
        raise ControlChannelError(
            f"the app refused to set {capability.value}={str(enabled).lower()}: {report.reason}"
            if report.reason
            else f"the app refused to set {capability.value}={str(enabled).lower()}, "
            "without saying why"
        )
    raise ControlChannelError(
        f"the app did not acknowledge {capability.value}={str(enabled).lower()} "
        f"(command {command_id}) within {timeout:g}s. The channel is gated twice: BajutsuKit must be "
        "compiled with -DBAJUTSU_ENABLE_CONTROL_CHANNEL, and the app must be launched with "
        "BAJUTSU_CONTROL_CHANNEL=1."
    )


@contextmanager
def capability_suspended(
    channel: Collector | None,
    capability: InAppCapability,
    *,
    timeout: float = ACK_TIMEOUT,
    cancelled: CancelSource = not_cancelled,
) -> Iterator[None]:
    """Turn one in-app capability off for the body, and back on when it ends.

    Both edges are acknowledged waits, so the body runs against a state the app confirmed rather
    than one it was merely asked for — which is what makes hiding the touch markers for a screenshot
    correct rather than hopeful.

    Raises:
        ControlChannelError: Turning the capability off failed, or turning it back on failed after a
            body that itself succeeded. A restore that fails while the body is already failing is
            logged instead, so the body's own failure stays the one the caller reports.
        RunCancelled: The run was cancelled while an edge was still waiting for an acknowledgement.
            A cancellation observed while restoring after a failing body is logged like any other
            restore failure, not raised, for the same reason — the body's own failure wins.
    """
    apply_capability(channel, capability, enabled=False, timeout=timeout, cancelled=cancelled)
    try:
        yield
    except BaseException:
        try:
            apply_capability(
                channel, capability, enabled=True, timeout=timeout, cancelled=cancelled
            )
        except Exception as exc:  # any restore failure, RunCancelled included — the
            # body's own failure is what the caller must see, so this is logged rather than
            # raised regardless of what the restore itself raised (BaseException stays
            # unswallowed: a KeyboardInterrupt or SystemExit from the restore still propagates).
            _logger.warning("restoring %s after a failure also failed: %s", capability.value, exc)
        raise
    apply_capability(channel, capability, enabled=True, timeout=timeout, cancelled=cancelled)
