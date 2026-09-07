"""Install, start, and read from the resident server, and narrow its hierarchy dumps."""

from __future__ import annotations

import http.client
import math
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

from bajutsu.common.drivers.adb import (
    ActOutcome,
    ActRequest,
    AdbActUncertain,
    AdbActUnsupported,
    AdbResidentError,
    HierarchyRead,
    slice_hierarchy_root,
)

from ._shared import _SERVER_APK, _TEST_APK, logger

if TYPE_CHECKING:
    from ._process import _Process

# The response header the resident server stamps `GET /source` with: the device-clock time
# (`SystemClock.uptimeMillis`) of the most recent accessibility event it had observed (BE-0332 Unit 3).
# Carried in a header so the XML body stays byte-identical to `uiautomator dump`'s, keeping
# `parse_hierarchy` and `narrow_to_active_window` unchanged.
_READ_MARK_HEADER = "X-Bajutsu-Read-Mark"

# The response header carrying each opted-in view's own `View.getZ()` (BE-0355 Unit 3), in the same
# header rather than the body and for the same reason as the mark above. Its value is
# `<key>=<z>` pairs joined by `;`, where the key names the node by what the host can recompute from
# the `<node>` it is reading — see `adb.py`'s `_native_z_key`. Absent on a server that does not
# report it and on an app that opted no view in.
_NATIVE_Z_HEADER = "X-Bajutsu-Native-Z"

# The response header `POST /act` stamps when an accessibility event postdated the injection it just
# made (BE-0339 Unit 5), carrying that event's device-clock time. Absent when the device saw none
# within its budget — and absent from an older server that never waited at all — so its presence, and
# nothing else, is what tells the driver the tree has already caught up with the gesture.
_ACT_PUBLISH_HEADER = "X-Bajutsu-Act-Publish"

# The status the resident server answers when the identity the host sent no longer names the same
# number of nodes on its own dump: the screen moved between the two resolves, so nothing was injected.
_STALE_STATUS = 409

# What an older resident server answers for a path it does not serve. Permanent for the lease, unlike a
# socket fault, so the driver latches it instead of probing again on every gesture.
_NO_ENDPOINT_STATUS = 404

# SystemUI owns the status and navigation bars — separate windows that `dumpWindowHierarchy` traverses
# but the platform `uiautomator dump` (active window only) omits. Dropping them is a uniform
# system-chrome filter, not per-app config, so the resident dump yields the same Elements as the dump
# path (prime directive 3, app-agnostic).
_SYSTEM_DECOR_PACKAGES = frozenset({"com.android.systemui"})


def narrow_to_active_window(xml: str) -> str:
    """Drop system-decor windows from a `dumpWindowHierarchy` tree so it matches the active-window dump.

    `dumpWindowHierarchy` emits one top-level `<node>` per window; `uiautomator dump` scopes to the
    active window. Removing the SystemUI status/navigation-bar windows reconciles the two so
    `parse_hierarchy` produces identical Elements. A tree with no system window (the active-window dump
    itself) passes through unchanged, and unparseable input is returned as-is so the driver's existing
    empty-tree handling still applies.

    Scope: this drops only SystemUI decor. The Android e2e lane (BE-0208) exercises the resident path
    across the showcase scenarios, including one that raises the IME (`search`); the `permission`
    scenario does not exercise this — Android pre-grants the permission
    (`demos/showcase/scenarios/permission.yaml`), so no dialog ever appears there. A permission-dialog
    window leaking past this filter is therefore not yet caught by CI; broadening the filter for that
    case is still a design decision deferred rather than guessed at here.
    """
    root = slice_hierarchy_root(xml)
    if root is None:
        return xml
    decor = [window for window in root if window.get("package") in _SYSTEM_DECOR_PACKAGES]
    if not decor:
        return xml
    for window in decor:
        root.remove(window)
    return ET.tostring(root, encoding="unicode")


def fetch_source(
    host_port: int, since: float | None = None, *, timeout: float = 5.0
) -> HierarchyRead:
    """GET the resident server's current hierarchy over the forwarded loopback host port.

    Returns the XML plus its read mark (BE-0332 Unit 3): the `X-Bajutsu-Read-Mark` header carries the
    device-clock time of the most recent accessibility event the reader had seen, so the driver can
    trust a read only once it postdates the gesture. A response without the header (an older server)
    yields a None mark, and the driver's barrier falls back to its wall-clock budget — never a failure.

    Args:
        since: The device-clock mark the read must postdate (BE-0332 Unit 4). When given, it rides on
            the request as `?since=`, and the resident server blocks until an accessibility event
            postdates it before dumping once — collapsing the host's re-poll into one round trip. None
            (a read with no gesture pending) requests the current hierarchy with no wait.

    Raises:
        AdbResidentError: the channel could not be reached or did not answer 200 — an infrastructure
            failure the driver catches to fall back to `uiautomator dump`, never a test outcome.
    """
    conn = http.client.HTTPConnection("127.0.0.1", host_port, timeout=timeout)
    path = "/source" if since is None else f"/source?since={since}"
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            raise AdbResidentError(f"resident server returned HTTP {resp.status}")
        # An absent or malformed mark here degrades the driver's barrier to its wall-clock budget
        # rather than failing the read: the mark only ever tightens the wait.
        mark = _parse_mark(resp.getheader(_READ_MARK_HEADER))
        native_z = _parse_native_z(resp.getheader(_NATIVE_Z_HEADER))
        # A truncated/garbled body (a mid-write device server) must degrade to the dump fallback, not
        # escape past the driver's AdbResidentError-only catch — whether it surfaces as a
        # UnicodeDecodeError (garbled bytes) or an http.client.HTTPException (IncompleteRead from a
        # short body, BadStatusLine/UnknownProtocol from a malformed status line).
        return HierarchyRead(body.decode("utf-8"), mark, native_z=native_z)
    except (OSError, UnicodeDecodeError, http.client.HTTPException) as exc:
        raise AdbResidentError(f"resident channel unreachable on port {host_port}: {exc}") from exc
    finally:
        conn.close()


def act(host_port: int, request: ActRequest, *, timeout: float = 10.0) -> ActOutcome:
    """Ask the resident server to perform one gesture on an element the host already resolved.

    The element crosses as its four accessibility fields plus its ordinal among the nodes sharing them,
    never as a coordinate: the device re-finds it in a dump of its own and reads the bounds microseconds
    before injecting, closing the window in which a settling screen moves out from under a coordinate
    the host computed a round trip earlier.

    Returns:
        The device's answer: `acted` False for a `409` — the identity no longer names the same nodes
        there, so the host must re-resolve rather than let a coordinate be guessed — and, when the
        gesture landed, whether an accessibility event postdated it before the server replied
        (`_ACT_PUBLISH_HEADER`). A server that never sends that header reports no confirmation, which
        is what leaves the driver's read-lag barrier armed exactly as it was.

    Raises:
        AdbResidentError: the channel could not be reached, or answered anything else — including the
            `404` an older server without the endpoint returns. The driver degrades to its coordinate
            actuators, so a device that cannot serve this is never worse off than before.
    """
    fields = {
        "kind": request.kind,
        "index": str(request.index),
        "count": str(request.count),
        "rid": request.identity[0],
        "desc": request.identity[1],
        "text": request.identity[2],
        "cls": request.identity[3],
    }
    if request.since is not None:
        fields["since"] = str(request.since)
    if request.duration_ms is not None:
        fields["durationMs"] = str(request.duration_ms)
    # A longer timeout than a read: the server honors the `since` mark and settles before it injects,
    # and a press-and-hold then holds for its own duration on top of that.
    conn = http.client.HTTPConnection("127.0.0.1", host_port, timeout=timeout)
    try:
        try:
            conn.request("POST", "/act?" + urllib.parse.urlencode(fields))
        except (OSError, http.client.HTTPException) as exc:
            # Nothing left the host, so nothing was injected: the caller may safely take the
            # coordinate path. This is the only fault where that is safe.
            raise AdbResidentError(
                f"resident actuation unreachable on port {host_port}: {exc}"
            ) from exc
        try:
            resp = conn.getresponse()
            body = resp.read().decode("utf-8", "replace").strip()
        except (OSError, http.client.HTTPException) as exc:
            # The request went out, and the device injects before it answers, so the gesture may
            # already have happened. Re-actuating on the coordinate path would be a second touch.
            raise AdbActUncertain(
                f"resident actuation was sent but its reply was lost on port {host_port}: {exc}"
            ) from exc
        if resp.status == _STALE_STATUS:
            logger.debug("resident actuation reported the target moved: %s", body)
            return ActOutcome(acted=False, published_mark=None)
        if resp.status == _NO_ENDPOINT_STATUS:
            raise AdbActUnsupported(f"resident server has no /act endpoint (HTTP {resp.status})")
        if resp.status != 200:
            raise AdbResidentError(f"resident actuation returned HTTP {resp.status}: {body}")
        # `_parse_mark` reads a malformed value as no value, so a garbled header degrades to "the
        # device could not confirm" — the barrier stays armed — rather than failing a gesture that
        # actually landed.
        return ActOutcome(
            acted=True, published_mark=_parse_mark(resp.getheader(_ACT_PUBLISH_HEADER))
        )
    finally:
        conn.close()


def _parse_mark(raw: str | None) -> float | None:
    """A device-clock mark header as a float, or None when the header is absent or unparseable.

    Shared by the two headers that carry one: `X-Bajutsu-Read-Mark` on a read and
    `X-Bajutsu-Act-Publish` on an actuation. What an absent mark *costs* differs between them, so each
    caller states its own consequence; what they share is that a mark is never required — an older
    server sends neither header, and reading None rather than raising is what keeps such a server
    working.
    """
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_native_z(raw: str | None) -> dict[str, float]:
    """The `X-Bajutsu-Native-Z` header as content key to measured position, empty when absent.

    A malformed pair is dropped rather than failing the read: `nativeZ` is diagnostic (BE-0355), so a
    garbled reading costs one element its position and leaves the rest of the tree intact — the same
    honest absence an app that never opted in reports.
    """
    if not raw:
        return {}
    found: dict[str, float] = {}
    for pair in raw.split(";"):
        key, sep, value = pair.rpartition("=")
        if not sep or not key:
            continue
        try:
            z = float(value)
        except ValueError:
            continue
        # `NaN` / `Infinity` parse but name no position, the same reading `native_z_from_json`
        # already refuses for a value read back off an artifact.
        if math.isfinite(z):
            found[key] = z
    return found


def fetch_clock(host_port: int, *, timeout: float = 5.0) -> float | None:
    """GET the resident server's current device clock (`SystemClock.uptimeMillis`), or None.

    Read just before a gesture (BE-0332 Unit 3) so a later read must postdate it, on the device's own
    clock, to count as caught up. Returns None on any fault or a non-200 rather than raising: the mark
    is an optimisation over the wall-clock budget, so a clock hiccup slows the barrier at worst, never
    fails a read or accepts a stale one.
    """
    conn = http.client.HTTPConnection("127.0.0.1", host_port, timeout=timeout)
    try:
        conn.request("GET", "/clock")
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            return None
        return float(body.decode("utf-8").strip())
    except (OSError, ValueError, UnicodeDecodeError, http.client.HTTPException):
        return None
    finally:
        conn.close()


def server_apks_built(server_apk: Path = _SERVER_APK, test_apk: Path = _TEST_APK) -> bool:
    """True when both resident-server APKs exist, so the resident read channel can start.

    The default-on gate reads this to pick the resident channel over `uiautomator dump` only when
    `make -C BajutsuAndroidUIAutomatorServer build` has produced both outputs; a fresh clone that never built
    them (the build outputs are gitignored) falls back to the dump path untouched.
    """
    return server_apk.exists() and test_apk.exists()


def _default_spawn(argv: list[str]) -> _Process:
    # The instrumentation blocks (serve() never returns), so it runs in the background for the lease;
    # its output is drained to DEVNULL so a full pipe never wedges it.
    return subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _parse_forward_port(stdout: str) -> int:
    """The host port `adb forward tcp:0 …` chose, printed on stdout.

    Read as the last bare-number line rather than the whole output, because adb prepends its own
    chatter whenever the invocation happens to be the one that starts the server ("* daemon not
    running; starting now at tcp:5037", "* daemon started successfully"). Parsing the whole string
    would raise on exactly those runs, and a failed forward takes the resident channel down with it —
    the lease then reads through `uiautomator dump`, which carries no device mark, so every read-lag
    barrier silently falls back to spending its full budget. Tolerating the banner keeps a cosmetic
    line from costing the channel.
    """
    ports = [line.strip() for line in stdout.splitlines() if line.strip().isdigit()]
    if not ports:
        raise AdbResidentError(f"adb forward did not report a host port: {stdout!r}")
    return int(ports[-1])
