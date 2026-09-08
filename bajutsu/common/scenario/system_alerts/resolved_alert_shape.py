"""One prompt's shape, resolved for a locale and a choice."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedAlertShape:
    """One shape of one prompt, resolved for a locale and a choice.

    The scenario layer's half of `orchestrator.types.ResolvedAlertRule`, kept here so the schema
    stays a portable inner contract that pulls in no orchestrator layer; `run` pairs each of these
    with the prompt's `AlertSurfaces` to build the rule the guard matches with.
    """

    identifying_labels: frozenset[str]
    tap_label: str
    excluded_labels: frozenset[str]
