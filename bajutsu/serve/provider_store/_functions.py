"""Validate a decoded provider-settings mapping before anything trusts it."""

from __future__ import annotations

from bajutsu.serve.state import ProviderSettings

from .persisted_provider_settings import PersistedProviderSettings
from .provider_settings_error import ProviderSettingsError


def decode(raw: object, where: str) -> PersistedProviderSettings:
    """Validate a decoded ``{provider, settings}`` mapping into a `PersistedProviderSettings`.

    Shared by both stores — the local file store passes the file path as *where*, the DB store its
    ``provider_settings[<org>]`` label — so a malformed value (a non-object payload, a non-string
    leaf) fails identically whichever backend it came from, rather than the DB store trusting its
    own possibly-hand-edited rows.
    """
    if not isinstance(raw, dict):
        raise ProviderSettingsError(f"{where}: expected a JSON object, got {type(raw).__name__}")
    provider = raw.get("provider")
    settings_raw = raw.get("settings", {})
    if not isinstance(provider, str) or not isinstance(settings_raw, dict):
        raise ProviderSettingsError(f"{where}: 'provider' must be a string and 'settings' a map")
    settings: dict[str, ProviderSettings] = {}
    for name, slot in settings_raw.items():
        if not isinstance(slot, dict):
            raise ProviderSettingsError(f"{where}: settings[{name!r}] must be a map")
        settings[name] = ProviderSettings(
            model=_str_field(slot, "model", name, where),
            effort=_str_field(slot, "effort", name, where),
            region=_str_field(slot, "region", name, where),
        )
    return PersistedProviderSettings(provider=provider, settings=settings)


def _str_field(slot: dict[str, object], key: str, name: str, where: str) -> str:
    # Reject a non-string leaf rather than coercing it (`str(123)` → "123"): the module's contract is
    # to fail on a malformed value, not guess at a partial one.
    value = slot.get(key, "")
    if not isinstance(value, str):
        raise ProviderSettingsError(f"{where}: settings[{name!r}].{key} must be a string")
    return value


def encode_settings(settings: dict[str, ProviderSettings]) -> dict[str, dict[str, str]]:
    """The JSON-friendly slot map both stores serialize (the shape a ``settings`` value takes)."""
    return {
        name: {"model": s.model, "effort": s.effort, "region": s.region}
        for name, s in settings.items()
    }
