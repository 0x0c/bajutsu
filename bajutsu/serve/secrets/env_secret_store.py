"""The process-environment secret store, in memory for the server's lifetime only."""

from __future__ import annotations

import os
from collections.abc import Callable

from bajutsu.serve.helpers import mask_secret


class EnvSecretStore:
    """Holds a secret in the serve process's environment for its lifetime (in memory only, never
    written to disk) — today's local behavior, moved behind the seam. A logical secret *name* maps
    to an env var through *env_var_for* (honoring a bound config's ``ai.keyEnv``, BE-0097), so a
    spawned record/run job inherits the value under the name it expects."""

    def __init__(self, env_var_for: Callable[[str], str]) -> None:
        self._env_var_for = env_var_for

    def set(self, name: str, value: str, *, updated_by: str | None = None) -> str | None:  # noqa: ARG002  # SecretStore shape
        var = self._env_var_for(name)
        if value:
            os.environ[var] = value
            return mask_secret(value)
        os.environ.pop(var, None)
        return None

    def describe(self, name: str) -> str | None:
        value = os.environ.get(self._env_var_for(name)) or None
        return mask_secret(value) if value is not None else None
