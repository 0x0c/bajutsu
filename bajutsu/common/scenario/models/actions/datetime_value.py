"""The `datetime` generator: the current time as text, optionally shifted and zoned."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from bajutsu.common.scenario.models._base import _Model

# A fixed instant every `strftime` directive renders against, so `datetime.format` is validated at
# load time without reading the clock (which would make the check itself time-dependent).
_FORMAT_PROBE = datetime(2001, 2, 3, 4, 5, 6, tzinfo=UTC)


class DatetimeValue(_Model):
    """`generate: { datetime: … }` — the current time as text, optionally shifted and zoned.

    `format` is a `strftime` pattern (ISO 8601 when omitted); the four `offset*` fields are signed
    and additive, so a value an hour before tomorrow is `offsetDays: 1, offsetHours: -1`. `timezone`
    is an IANA name; the default is UTC, so a scenario matching a date the app renders in the
    device's own zone must name that zone (pinning the device's zone is BE-0158's concern).
    """

    format: str | None = None
    offset_seconds: int | None = Field(default=None, alias="offsetSeconds")
    offset_minutes: int | None = Field(default=None, alias="offsetMinutes")
    offset_hours: int | None = Field(default=None, alias="offsetHours")
    offset_days: int | None = Field(default=None, alias="offsetDays")
    timezone: str | None = None

    @field_validator("format")
    @classmethod
    def _renderable(cls, v: str | None) -> str | None:
        """Reject a pattern `strftime` cannot render, at load time rather than mid-run (§6.2)."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("datetime.format must not be empty")
        try:
            _FORMAT_PROBE.strftime(v)
        except ValueError as e:
            raise ValueError(f"datetime.format is not a valid strftime pattern: {e}") from e
        return v

    @field_validator("timezone")
    @classmethod
    def _known_zone(cls, v: str | None) -> str | None:
        """Reject an unresolvable IANA name at load time, so a run never silently falls back to UTC."""
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f"datetime.timezone is not a known IANA zone: {v!r} ({e})") from e
        return v
