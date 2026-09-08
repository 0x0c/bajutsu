"""The defaults and directory rules the server's state is initialized from."""

from __future__ import annotations

from bajutsu.serve.orgs import DEFAULT_ORG

# The org an unassigned user/app falls into. Re-exported from serve.orgs (the org model's home) so
# job persistence and the operations layer share one source of truth.
_DEFAULT_ORG = DEFAULT_ORG
