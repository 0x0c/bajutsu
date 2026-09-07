"""The error raised when the resident channel serves reads but has no actuation endpoint."""

from __future__ import annotations

from .adb_resident_error import AdbResidentError


class AdbActUnsupported(AdbResidentError):
    """The resident channel serves reads but has no actuation endpoint (an older server 404s `/act`).

    Held apart from its base so the driver can tell a *permanent* absence from a *transient* fault. The
    absence is a property of the deployed server and will not change within the lease, so the driver
    latches it and stops probing. A socket blip is the opposite: the endpoint is there, and giving up on
    it for the rest of the lease would put every later gesture back on the coordinate path this exists
    to avoid — under exactly the flaky conditions that produced the blip.
    """
