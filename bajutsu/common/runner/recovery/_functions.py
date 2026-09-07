"""Tear a wedged backend down without letting the teardown's own failure mask the crash."""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Callable

from bajutsu.common.devices import errors as device_errors
from bajutsu.common.drivers import base

_logger = logging.getLogger(__name__)


# The default backend-crash retry budget, overridable per lane without a code change. A resident
# XCUITest runner crashes more on a loaded/contended CI host (the XCTest host's accessibility bridge
# under actuation), so a lane on such hardware can raise the budget for infrastructure crashes — the
# crash is the test host dying, not an app verdict, so riding it out is not flakiness-by-absorption
# (BE-0049): work that crashes every attempt still fails once the budget is spent. Default 1
# (two attempts), the value before this knob existed, so an unset environment is unchanged.
_CRASH_RETRIES_ENV = "BAJUTSU_CRASH_RETRIES"
_DEFAULT_CRASH_RETRIES = 1


# A wall-clock ceiling (seconds) on how long recovery may spend *respawning* after a backend crash,
# across all its `crash_retries`. `crash_retries` alone caps the retry *count*, not the time: a
# runner that crashes and never comes back makes each cold respawn pay a fresh cold-startup ceiling,
# so the count budget silently becomes count x that ceiling — enough to blow a job's `timeout-minutes`
# with a silent hang instead of a loud failure. This budget caps that: once the wall-clock spent
# respawning is exhausted, recovery stops and the work fails loudly (BE-0049), even if retries remain.
# It never blocks the first respawn (the deadline is set at the first crash), so a genuine one-off — a
# respawn that comes back quickly — is still ridden out; the budget bites only when respawns are slow,
# which is exactly the hang. Unset (the default) is unbounded: the count is the only cap, so every
# lane not opting in is byte-for-byte unchanged.
_CRASH_RECOVERY_BUDGET_ENV = "BAJUTSU_CRASH_RECOVERY_BUDGET"


# A wall-clock ceiling (seconds) on how long crash recovery may spend respawning across a *whole*
# run, not just one scenario. `crash_recovery_budget` resets for every new scenario, so a device that
# keeps degrading pays that budget again and again — each respawn its own cold-startup ceiling — until
# a job's own CI `timeout-minutes` cancels it with no diagnosable cause rather than a clean failure
# (an incident `.github/workflows/ios-e2e.yml` already documents). This budget bounds the cumulative
# spend instead: unset (the default) is unbounded, so a lane not opting in is unchanged.
_RUN_CRASH_RECOVERY_BUDGET_ENV = "BAJUTSU_RUN_CRASH_RECOVERY_BUDGET"


def guarded_teardown(teardown: Callable[[], None], *, mid_run: bool, what: str) -> None:
    """Run `teardown`, warning on an expected process failure instead of re-raising.

    A runner that had already exited, an unreachable `xcrun`, and a collector socket the OS already
    tore down all surface as `CalledProcessError` or `OSError`; those are always logged at warning
    and swallowed. The pair covers the subprocess-driven backends (simctl, adb) and the collector's
    own socket close; `PlaywrightDriver.close()` suppresses its own already-gone-target failure
    before it ever reaches this function, the same way `reset_context`/`relaunch` already do, so an
    ordinary dead browser never lands in the branch below either — and
    `XcuitestLiveEnvironment.teardown()` suppresses its own already-expired-session `WebDriverError`
    the same way, since that class subclasses `RuntimeError`, not `OSError`. A
    `device_errors.DeviceTimeout` joins them (BE-0363, widened to the platform-neutral type by
    BE-0374 so an adb timeout is covered the day the adb surface gets one, with no edit here): a
    device operation that exceeded its deadline says the device is wedged, which is a fact about the
    host and not about this run's wiring, and it reaches here from the two
    environment teardowns that deliberately let a timeout through (`_terminate_app_under_test` /
    `_terminate_runner_app`, and `IosEnvironment.teardown`'s own `Env.terminate`). Treating it as a
    defect below would let a run whose every scenario passed end with no verdicts at all, since
    `mid_run=False`'s re-raise surfaces inside `run`'s `finally: shutdown()` and a raising `finally`
    replaces the results being returned. The timeout still gets its warning, and the discard path
    BE-0363 audited — `_spawn_cold_with_retry`, which calls `discard()` directly — is untouched by
    this, so the signal still reaches the retry that acts on it. Anything
    else is a wiring defect: at most call sites (`mid_run=True`) it is also swallowed into a warning
    so it cannot mask the fault that prompted the teardown, or abandon cleanup the caller still owes
    (the pool's `free.put(udid)`, on a site that runs ahead of its own `try`); only `mid_run=False`
    re-raises it, for a caller that must still fail on a wiring defect — the pool's `shutdown()`
    catches that re-raise so the rest of its sweep still runs, then raises it once the sweep is done
    (BE-0342).

    Args:
        teardown: The zero-arg callable that tears the environment (or warm resident) down, or runs
            other best-effort cleanup on a failure path (the pool's own repeated `adopt_replacement()`
            call, which re-keys pool state rather than tearing anything down).
        mid_run: False when the caller must still see a wiring defect (and is responsible for any
            cleanup it owes first), True when re-raising would mask the fault that prompted this
            teardown or abandon cleanup the caller cannot resume.
        what: A short description of the teardown site, used as the warning's subject.
    """
    try:
        teardown()
    except (subprocess.CalledProcessError, OSError, device_errors.DeviceTimeout) as exc:
        _logger.warning("%s failed: %s", what, exc)
    except Exception:
        if mid_run:
            _logger.warning("%s failed", what, exc_info=True)
            return
        raise


def _default_crash_retries() -> int:
    """The backend-crash retry budget from `BAJUTSU_CRASH_RETRIES`, or the default when unset/invalid."""
    raw = os.environ.get(_CRASH_RETRIES_ENV)
    if not raw:
        return _DEFAULT_CRASH_RETRIES
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_CRASH_RETRIES


def _default_crash_recovery_budget() -> float | None:
    """The crash-recovery wall-clock budget (s) from the env, or None (unbounded) when unset/invalid.

    A non-positive or unparseable value reads as unbounded, never as zero: the budget only ever
    *reduces* recovery, and disabling recovery entirely is `crash_retries=0`'s job, not this knob's.
    """
    raw = os.environ.get(_CRASH_RECOVERY_BUDGET_ENV)
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def recovers_by_respawn(exc: BaseException) -> bool:
    """Whether re-leasing a fresh device may repair `exc` — the retry decision, and only that.

    The distinction is exactly the exception type the driver already raises: a runner crash, a
    readiness gate that killed the runner, and a lease bring-up that died all surface as
    `base.BackendCrashError` (or a subclass), so recovery is a deterministic `isinstance` branch. A
    mis-resolved selector (`SelectorError`), a refused actuator (`UnsupportedAction`), and a failed
    contract assertion are *not* infrastructure and must keep failing immediately.

    Narrower than `is_host_fault` on purpose (BE-0378): a `device_errors.DeviceTimeout` is the host's
    fault but not a respawn's to fix, since a respawn rebuilds the device out of the same `simctl`
    calls that just stalled — far too heavy an answer to a stall that outlives one deadline and not
    the next. Read this to decide a retry; read `is_host_fault` to report one.
    """
    return isinstance(exc, base.BackendCrashError)


def is_host_fault(exc: BaseException) -> bool:
    """Whether `exc` says something about the host rather than about the code under test.

    The diagnosis, never the retry decision (BE-0378) — call `recovers_by_respawn` for that. It
    covers everything a respawn recovers, plus the wedged device BE-0363 named on the iOS side: a
    `DeviceTimeout` is raised by a subprocess deadline, never by an assertion, so it can no more be
    a verdict about the app than a runner crash can. A lane that reports it as such shows a
    degrading host as a rising wedge count rather than as a conformance failure somebody re-ran.

    Names the platform-neutral `device_errors.DeviceTimeout` rather than the iOS type, so every
    backend that later adopts that base is covered here with no edit (BE-0374).
    """
    return isinstance(exc, base.BackendCrashError | device_errors.DeviceTimeout)


def _default_run_crash_recovery_budget() -> float | None:
    """The run-level crash-recovery wall-clock budget (s) from the env, or None (unbounded) when unset/invalid.

    Same unset-or-invalid-reads-as-unbounded parsing as `_default_crash_recovery_budget`.
    """
    raw = os.environ.get(_RUN_CRASH_RECOVERY_BUDGET_ENV)
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None
