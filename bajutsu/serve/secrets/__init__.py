"""The SecretStore seam: how serve holds an operator credential (BE-0136 write-once secrets).

Shaped like the other serve seams (`artifacts.py`): a `Protocol` with a local implementation
(`EnvSecretStore`) and a hosted one (`server/secrets.py`), selected by whichever `ServeState`
carries. Two operations only — `set` and `describe` — and deliberately **no `get(name) -> value`**
an HTTP handler can reach: a secret is write-once, so no endpoint ever discloses the plaintext
again, matching how GitHub Actions Secrets work. The plaintext lives only where it is consumed
(a spawned record/run/crawl job inheriting it from the environment), never on a response path.
"""

from .env_secret_store import EnvSecretStore
from .secret_store import SecretStore

__all__ = ["EnvSecretStore", "SecretStore"]
