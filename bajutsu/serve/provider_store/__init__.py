"""Durable store for the serve AI provider settings (BE-0184).

The serve Web UI's provider choice, model, and reasoning effort lived only in the serve
process's environment, so every restart reset them to the launch environment and the operator
re-entered them by hand. This store persists them so a saved choice survives a restart, the way
the Claude API key already does through the write-once secret store (BE-0136).

Unlike that secret store, these values are **not secrets**: they are read back and displayed for
editing, so the store is plainly readable and unencrypted — deliberately *not* the write-once,
no-reveal shape of `serve.secrets` (see BE-0184 *Alternatives considered*). The local, file-backed
shape lives here; the per-organization, DB-backed shape a hosted deployment needs lives in
`serve.server.provider_store.DbProviderSettingsStore` (behind the `db` extra), landed by BE-0229
once serve resolves these settings per organization rather than process-globally.
"""

from ._functions import _str_field as _str_field
from ._functions import decode, encode_settings
from .local_provider_settings_store import LocalProviderSettingsStore
from .persisted_provider_settings import PersistedProviderSettings
from .provider_settings_error import ProviderSettingsError
from .provider_settings_store import ProviderSettingsStore

__all__ = [
    "LocalProviderSettingsStore",
    "PersistedProviderSettings",
    "ProviderSettingsError",
    "ProviderSettingsStore",
    "decode",
    "encode_settings",
]
