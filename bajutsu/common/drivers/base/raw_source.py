"""A device's own reply behind a backend's last read, untouched by Bajutsu's processing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawSource:
    """The device's own reply behind a backend's last `_describe()`, untouched by bajutsu's processing.

    `text` is the reply exactly as the device/runner answered it — before any structural transform a
    backend applies and before `Element` normalization — so a diagnosis can tell "the device's own dump
    already looked wrong" apart from "bajutsu's own processing changed it". `parsed_input` is the same
    read *after* a backend's own structural transform of it, when that transform actually changed
    something: adb's resident channel strips SystemUI decor windows (`narrow_to_active_window`) before
    handing the result to `parse_hierarchy`, so `parsed_input` is what the parser actually consumed.
    `None` when the backend applies no such transform (the dump-subprocess path, XCUITest) or the
    transform left `text` unchanged — `text` alone already describes what was parsed. `suffix` names the
    format `text` is actually written in (adb: `.xml`; XCUITest's `GET /elements` body is undecoded JSON,
    so it sets `.json`) — carried here rather than hardcoded by the writer, so a future
    `RawSourceProvider` with a different dump format needs no edit outside the backend that produces it.
    Required, not defaulted: a default of `.xml` would let a future backend construct
    `RawSource(text=body)` and silently mislabel a non-XML dump, the exact bug this field exists to
    prevent — every producer must state its own format, or mypy catches the omission at the call site.
    """

    text: str
    suffix: str
    parsed_input: str | None = None
