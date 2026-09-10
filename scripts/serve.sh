#!/usr/bin/env bash
# Launch the bajutsu web UI, installing the configured backends' dependencies on demand.
#
# A backend's extra dependencies aren't in the base install, and a missing one only surfaces at run
# time (e.g. `no available actuator among ['xcuitest']`, or `ModuleNotFoundError: playwright`).
# Provisioning is delegated to the shared, config-aware installer (scripts/install.sh, BE-0164),
# which resolves exactly what a config's `targets.*` need, so "what a backend needs" lives in one
# requirements mapping instead of being re-hardcoded here. Idempotent: nothing already present is
# reinstalled.
#
# When a local `--config <file>` is passed, provision that config's actual backends — iOS (XCUITest),
# web (Playwright), or both — so a web-target UI doesn't get an iOS-only sync that prunes Playwright
# (and vice versa). Otherwise (no config, or a `github:`/`https:` spec install.sh can't resolve to
# a local file) fall back to the iOS backend: serve's historical iOS-first default.
#
# On macOS it also stages the wheel-bundled XCUITest Simulator runner (BE-0292) when a source
# checkout ships none or has drifted from it
# (docs/specs/xcuitest-bundled-runner-auto-refresh.md), so a serve-launched XCUITest run resolves to
# a current one with no per-target `testRunner`. This runs only when the serve actually drives the
# XCUITest backend (the no-config iOS default, or a config with an iOS target) — a web-only serve
# stays free of the toolchain build. Set BAJUTSU_SKIP_RUNNER_BUNDLE=1 to skip it regardless.
#
# Usage: scripts/serve.sh [bajutsu serve flags…]   e.g. scripts/serve.sh --config demos/web/demo.config.yaml
set -euo pipefail

cd "$(dirname "$0")/.."

# Extract the value of a --config flag (both `--config X` and `--config=X`), without disturbing the
# original argv forwarded to `serve` verbatim below.
config=""
prev=""
for arg in "$@"; do
  case "$arg" in
    --config=*) config="${arg#--config=}" ;;
    *) [ "$prev" = "--config" ] && config="$arg" ;;
  esac
  prev="$arg"
done

# True when this serve will drive the iOS/XCUITest backend, so the runner staging below runs only
# when it is actually wanted. With no local config, serve falls back to `--backend ios` (the branch
# at the bottom), so the default is iOS; a passed config is resolved through the same backend
# resolver the installer uses, keeping "which backend" in one place rather than re-parsed here.
serve_uses_xcuitest() {
  if [ -z "$config" ] || [ ! -f "$config" ]; then
    return 0
  fi
  uv run python - "$config" <<'PY'
import sys

from bajutsu.common.backends import resolve_actuators
from bajutsu.common.config import load_config, resolve

try:
    cfg = load_config(open(sys.argv[1], encoding="utf-8").read())
    actuators = {a for name in cfg.targets for a in resolve_actuators(resolve(cfg, name).backend)}
except Exception:
    # A malformed config is install.sh's problem to report below, not this probe's; treat it as
    # "no XCUITest" so a parse error never triggers a runner build.
    raise SystemExit(1)
raise SystemExit(0 if "xcuitest" in actuators else 1)
PY
}

# Stage the bundled XCUITest Simulator runner so `make serve` on a Mac makes XCUITest work out of
# the box (BE-0292), and keeps working as BajutsuKit's own source changes
# (docs/specs/xcuitest-bundled-runner-auto-refresh.md). Delegates the staleness check and rebuild to
# `ensure_bundled_runner_fresh` — the same function every other xcuitest entry point calls through
# `_resolve_runner` — so the algorithm lives in one place instead of a second, bash copy that could
# drift from it. That function itself no-ops on a wheel install (no BajutsuKit source to compare
# against) and honors BAJUTSU_SKIP_RUNNER_BUNDLE=1; a stale or missing bundle it cannot rebuild
# (Xcode/xcodegen missing, or the build itself failing) raises, which aborts serve before it starts —
# the same "never keep a stale bundle" contract every other entry point gets, rather than the silent
# per-target testRunner fallback this script used to degrade to.
if [ "${BAJUTSU_SKIP_RUNNER_BUNDLE:-}" != "1" ] &&
  [ "$(uname)" = "Darwin" ] &&
  serve_uses_xcuitest; then
  echo "serve: checking the bundled XCUITest runner…" >&2
  uv run python -c '
import sys

from bajutsu.common.backend_cli.simctl import DeviceError
from bajutsu.common.platform_lifecycle.environments._bundled_runner import (
    ensure_bundled_runner_fresh,
)

try:
    ensure_bundled_runner_fresh()
except DeviceError as exc:
    print(f"serve: {exc}", file=sys.stderr)
    sys.exit(1)
'
fi

if [ -n "$config" ] && [ -f "$config" ]; then
  ./scripts/install.sh --config "$config"
else
  ./scripts/install.sh --backend ios
fi

exec uv run python -m bajutsu serve "$@"
