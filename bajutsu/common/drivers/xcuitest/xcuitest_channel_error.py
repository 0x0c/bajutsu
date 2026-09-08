"""The error raised when the runner channel never came up, stopped answering, or replied badly."""

from __future__ import annotations


class XcuitestChannelError(RuntimeError):
    """The runner channel failed: it never came up, stopped answering, or returned a bad response.

    An infrastructure failure, kept distinct from a test outcome — a crashed/absent runner fails the
    run loudly rather than being read as "element not found".
    """
