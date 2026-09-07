"""The four per-tenant storage seams resolved for one organization (BE-0015)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bajutsu.serve.artifacts import ArtifactStore
from bajutsu.serve.baselines import BaselineStore
from bajutsu.serve.scenarios import ScenarioStore
from bajutsu.serve.secrets import SecretStore

if TYPE_CHECKING:
    from bajutsu.serve.provider_store import ProviderSettingsStore


@dataclass
class StoreBundle:
    """The four per-tenant storage seams resolved for one org (BE-0015 multi-tenancy). Operations
    fetch a bundle for the request's org and use it instead of the bare `ServeState` fields, so a
    server backend keeps each org's artifacts/scenarios/baselines/secrets under its own
    object-store prefix. Local serve has one tenant, so its bundle is just the default stores."""

    artifacts: ArtifactStore
    scenarios: ScenarioStore
    baselines: BaselineStore
    secrets: SecretStore
    # The org's durable AI provider settings (BE-0229): the per-organization, DB-backed store on a
    # hosted deployment, the single file-backed store on local serve. None when persistence is not
    # wired (a server backend without a database) — the selection is then session-only in-memory,
    # the pre-BE-0184 shape. Read/written through `for_org(org)` like the other per-tenant seams.
    provider_settings: ProviderSettingsStore | None = None
