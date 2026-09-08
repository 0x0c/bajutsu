"""The error raised when an uploaded bundle is rejected."""

from __future__ import annotations


class BundleError(ValueError):
    """An uploaded bundle is rejected: a malformed zip, a zip-slip entry, or a crossed resource
    bound. A ``ValueError`` subclass so callers' ``except ValueError`` covers it. The message names
    the violated rule and is safe to surface to the uploader — it never leaks a host path."""
