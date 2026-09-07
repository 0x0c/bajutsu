"""The resolved web (Playwright) target knobs, present only on a web target (BE-0126)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebConfig:
    """Web (Playwright) target knobs (BE-0126). On `Effective` only when `platform == "web"`."""

    # Web (Playwright) target URL. None when unset (the config gate then fails cleanly).
    base_url: str | None = None
    # Run headless (default) or headed (visible browser). The `--headed` flag overrides per run.
    headless: bool = True
    # The rendering engine to drive — chromium (default) / firefox / webkit. The `--browser` flag
    # overrides per run (BE-0076).
    browser: str = "chromium"
    # The device mode a browser context is created with (BE-0228): "desktop" (default, unchanged) or
    # a Playwright device preset name (e.g. "iPhone 13") emulating a mobile viewport / touch / user
    # agent. Resolved against `playwright.devices` in the driver, lazily.
    device_mode: str = "desktop"
