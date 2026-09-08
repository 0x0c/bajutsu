"""Acquire a config (and its scenario tree) from a Git source (BE-0063).

`--config` keeps accepting a local path; in addition it accepts a Git spec
(`github:<owner>/<repo>[@<ref>][:<path>]`, or `git+https://<host>/<owner>/<repo>.git[@<ref>][#<path>]`).
The spec is materialized at an immutable commit SHA into a content-addressed cache, and the config's
relative paths resolve against that checkout root. Only *acquisition* changes — the schema, runner,
drivers, and the deterministic gate are untouched (DESIGN §6.5: git holds the history).

The GitHub transport (commits API + tarball endpoint) is the one external dependency; it is a small
injectable seam so the materialization logic tests offline against a fake.
"""

from ._functions import _FULL_SHA_RE as _FULL_SHA_RE
from ._functions import _GIT_URL_RE as _GIT_URL_RE
from ._functions import _GITHUB_RE as _GITHUB_RE
from ._functions import (
    DEFAULT_CONFIG,
    GIT_CONFIG_TOKEN_ENV,
    config_source_record,
    config_spec_from_record,
    github_http_error_message,
    github_token,
    is_full_sha,
    materialize,
    parse_config_spec,
    resolve_github_credential,
    source_provenance,
)
from ._functions import _bajutsu_cache_root as _bajutsu_cache_root
from ._functions import _default_cache_root as _default_cache_root
from ._functions import _extract_into as _extract_into
from ._functions import _extract_stripped as _extract_stripped
from ._functions import _github_app_credential as _github_app_credential
from ._functions import _github_app_private_key as _github_app_private_key
from ._functions import _spec as _spec
from ._git_hub_transport import _GitHubTransport as _GitHubTransport
from ._shared import _OWNER as _OWNER
from ._shared import _REPO as _REPO
from .git_config_spec import GitConfigSpec
from .materialized import Materialized
from .transport import Transport

__all__ = [
    "DEFAULT_CONFIG",
    "GIT_CONFIG_TOKEN_ENV",
    "GitConfigSpec",
    "Materialized",
    "Transport",
    "config_source_record",
    "config_spec_from_record",
    "github_http_error_message",
    "github_token",
    "is_full_sha",
    "materialize",
    "parse_config_spec",
    "resolve_github_credential",
    "source_provenance",
]
