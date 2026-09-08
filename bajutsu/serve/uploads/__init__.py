"""Receive a config + scenarios + app-binary bundle as an uploaded zip and materialize it (BE-0073).

An uploaded ``.zip`` is treated as "a tree to materialize" — the same self-contained checkout a
local ``bajutsu run`` already consumes (``bajutsu.config.yaml`` + its scenario tree + the built
``appPath`` binary), just delivered over the wire. This module owns the security-sensitive
extraction: every entry is validated to land **strictly under** the extraction root (zip-slip), and
resource bounds (entry count, total uncompressed size, per-entry compression ratio) abort a
zip-bomb the moment a bound is crossed, rather than after filling the disk. The decompressed bytes
are counted as they stream — a lying ``file_size`` header can't slip a bomb past the size cap.

Pure packaging/plumbing: no device, no AI, no effect on the verdict — the deterministic ``run``
happens downstream against the materialized tree. Sits on the serve hardening in BE-0051 (token
auth + path confinement): extraction extends the same "confine to a root" invariant serve enforces
for config/baseline paths (`_confined_config_path`) to archive entries.
"""

from ._functions import _CHUNK as _CHUNK
from ._functions import _CONFIG_NAMES as _CONFIG_NAMES
from ._functions import _CRUFT_DIRS as _CRUFT_DIRS
from ._functions import _RATIO_FLOOR as _RATIO_FLOOR
from ._functions import (
    MAX_ENTRIES,
    MAX_RATIO,
    MAX_SCENARIO_ENTRY_BYTES,
    MAX_SCENARIO_ZIP_ENTRIES,
    MAX_SCENARIO_ZIP_TOTAL_BYTES,
    MAX_TOTAL_BYTES,
    extract_bundle,
    find_bundle_config,
    materialize_bundle,
    read_scenario_zip,
    validate_bundle_config,
)
from ._functions import _check_ratio as _check_ratio
from ._functions import _is_symlink as _is_symlink
from ._functions import _safe_target as _safe_target
from ._functions import _scenario_entry_name as _scenario_entry_name
from .bounded_zip_receiver import MAX_UPLOAD_BYTES, BoundedZipReceiver
from .bundle_error import BundleError
from .upload import Upload
from .upload_too_large import UploadTooLarge

__all__ = [
    "MAX_ENTRIES",
    "MAX_RATIO",
    "MAX_SCENARIO_ENTRY_BYTES",
    "MAX_SCENARIO_ZIP_ENTRIES",
    "MAX_SCENARIO_ZIP_TOTAL_BYTES",
    "MAX_TOTAL_BYTES",
    "MAX_UPLOAD_BYTES",
    "BoundedZipReceiver",
    "BundleError",
    "Upload",
    "UploadTooLarge",
    "extract_bundle",
    "find_bundle_config",
    "materialize_bundle",
    "read_scenario_zip",
    "validate_bundle_config",
]
