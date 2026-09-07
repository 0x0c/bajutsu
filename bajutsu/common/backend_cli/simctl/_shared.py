"""The `SIMCTL_CHILD_*` keys and command shapes the simctl front end is built from."""

from __future__ import annotations

from collections.abc import Callable, Mapping

# (argv, extra_env) -> stdout
RunFn = Callable[[list[str], Mapping[str, str] | None], str]

# The two global-domain keys that decide which language SpringBoard renders in. `AppleLanguages` is
# written as a one-element array (not appended to) so the pinned language is the device's first
# choice with nothing behind it to fall back to — the same single value `locale_args` gives the app.
_LANGUAGES_KEY = "AppleLanguages"
_LOCALE_KEY = "AppleLocale"
