"""How a screen's platform-marked masked inputs can be addressed (BE-0331)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _SecureFields:
    """How the screen's platform-marked masked inputs can be addressed (BE-0331).

    A value the guide invents for such a field is masked in the screen map, and the map keeps no
    element to read the trait back from, so it has to be carried on the action the guide proposes.
    Labels are collected beside identifiers because the tool schema invites label targeting for an
    id-less element — the action that would otherwise reach a password field unmarked.
    """

    ids: frozenset[str]
    labels: frozenset[str]

    def covers(self, target: str, label: str | None) -> bool:
        """Whether an action addressed this way enters a masked input."""
        return bool(target and target in self.ids) or bool(label and label in self.labels)
