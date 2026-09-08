"""The BaselineStore seam: how visual-regression baselines are read and written (BE-0015).

A `visual` assertion compares a run's captured screenshot against a stored baseline image. Approve
promotes a screenshot to a baseline; a run reads baselines to compare against. This is the one
point where that storage diverges between local and server hosting: locally baselines are files
**confined to the baselines dir** (`LocalBaselineStore`), while a server store keeps them in object
storage. A baseline name is a relative path under one baselines root (the same single dir `serve`
uses today — subdirectories allowed, but never escaping it); per-tenant scoping comes from the
object-store prefix.
"""

from ._functions import _safe_baseline_name as _safe_baseline_name
from .baseline_store import BaselineStore
from .local_baseline_store import LocalBaselineStore

__all__ = ["BaselineStore", "LocalBaselineStore"]
