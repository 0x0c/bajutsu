"""The `push` action: deliver a simulated push notification to the app."""

from __future__ import annotations

from typing import Any

from bajutsu.common.scenario.models._base import _Model


class Push(_Model):
    """Deliver a simulated push notification (simctl push) to the app under test.

    Carries this APNs payload, e.g. `{"aps": {"alert": "..."}}`.
    """

    payload: dict[str, Any]
