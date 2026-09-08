"""The `random.uuid` generator: a version-4 UUID."""

from __future__ import annotations

from bajutsu.common.scenario.models._base import _Model


class RandomUuid(_Model):
    """`random: { uuid: {} }` — a version-4 UUID. Fieldless: the shape carries the whole request."""
