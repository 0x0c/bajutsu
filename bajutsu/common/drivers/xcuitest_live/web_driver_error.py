"""The error raised when a WebDriver endpoint never answered or answered badly."""

from __future__ import annotations


class WebDriverError(RuntimeError):
    """The WebDriver endpoint failed: it never answered, returned a non-WebDriver reply, or errored.

    An infrastructure failure, kept distinct from a test outcome — a wedged / absent grid fails the
    run loudly rather than being read as "element not found".
    """
