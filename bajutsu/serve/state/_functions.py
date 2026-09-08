"""Resolve which directories and stores a target's operations act on."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bajutsu.serve.helpers import target_scenarios_dir

if TYPE_CHECKING:
    from .serve_state import ServeState


def _scenarios_dir_for(
    state: ServeState, target: str | None, session: str | None, org: str
) -> Path | None:
    """The scenarios dir to list/save for *target*: the ``--scenarios`` override if set, else the
    target's configured dir.  None when neither is available.

    A configured dir is **relative to the config's base** — the binding's `cwd` — so a Git-sourced
    (whose `cwd` is the checkout root) lists scenarios from the fetched tree, not serve's launch
    directory. A local config's `cwd` is its own directory too, so its scenarios resolve from beside
    the config file rather than from where serve was started (BE-0063, BE-0242)."""
    if state.scenarios_dir is not None:
        return state.scenarios_dir
    binding = state.binding_for(session, org)
    if binding.config is None or not target:
        return None
    configured = target_scenarios_dir(binding.config, target)
    if configured is None or configured.is_absolute():
        return configured
    return binding.cwd / configured
