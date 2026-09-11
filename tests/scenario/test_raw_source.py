"""Tests for recovering each scenario's verbatim YAML from its source file (BE-xxxx).

`scenario_sources` composes the raw node tree instead of re-serializing the parsed model, so a
report can show a scenario exactly as authored — comments, formatting, and all — plus each of its
steps' original line number.
"""

from __future__ import annotations

from bajutsu.common.scenario import load_scenario_file
from bajutsu.common.scenario.raw_source import scenario_sources


def test_scenario_sources_keeps_comments_verbatim() -> None:
    text = (
        "# suite header\n"
        "- name: demo\n"
        "  # verify the happy path\n"
        "  steps:\n"
        "    - tap: { id: a }  # open it\n"
        "    - tap: { id: b }\n"
    )
    [src] = scenario_sources(text)
    assert src.text == text.rstrip("\n")
    assert src.step_lines == [5, 6]


def test_scenario_sources_attaches_a_scenario_own_leading_comment() -> None:
    # A comment directly above a scenario's own `- name:` line belongs to it and survives in its
    # slice; the file's own leading comment (separated by a blank line) does not bleed into it.
    text = (
        "# file header, unrelated to either scenario\n"
        "\n"
        "# login flow\n"
        "- name: login\n"
        "  steps:\n"
        "    - tap: { id: a }\n"
        "\n"
        "- name: logout\n"
        "  steps:\n"
        "    - tap: { id: b }\n"
    )
    login, logout = scenario_sources(text)
    assert login.text.splitlines()[0] == "# login flow"
    assert "file header" not in login.text
    assert logout.text.splitlines()[0] == "- name: logout"


def test_scenario_sources_aligns_with_load_scenario_file() -> None:
    text = "scenarios:\n  - name: a\n    steps: []\n  - name: b\n    steps: []\n"
    sources = scenario_sources(text)
    scenarios = load_scenario_file(text).scenarios
    assert len(sources) == len(scenarios) == 2


def test_scenario_sources_masks_a_literal_totp_secret() -> None:
    text = (
        "- name: 2fa\n"
        "  steps:\n"
        "    - totp:\n"
        "        secret: JBSWY3DPEHPK3PXP\n"
        "        into: { var: code }\n"
    )
    [src] = scenario_sources(text)
    assert "JBSWY3DPEHPK3PXP" not in src.text
    assert "<redacted>" in src.text


def test_scenario_sources_keeps_a_totp_secret_reference() -> None:
    text = (
        "- name: 2fa\n"
        "  steps:\n"
        "    - totp:\n"
        "        secret: ${secrets.TOTP_SEED}\n"
        "        into: { var: code }\n"
    )
    [src] = scenario_sources(text)
    assert "${secrets.TOTP_SEED}" in src.text


def test_scenario_sources_finds_a_nested_totp_secret() -> None:
    # `totp` can appear inside a container step's own nested steps (if/forEach/web), mirroring
    # `serialize._mask_totp_secrets`'s own reach.
    text = (
        "- name: 2fa\n"
        "  steps:\n"
        "    - if:\n"
        "        condition: { exists: { id: a } }\n"
        "        then:\n"
        "          - totp: { secret: JBSWY3DPEHPK3PXP, into: { var: code } }\n"
    )
    [src] = scenario_sources(text)
    assert "JBSWY3DPEHPK3PXP" not in src.text


def test_scenario_sources_empty_steps_yields_no_lines() -> None:
    text = "- name: demo\n  steps: []\n"
    [src] = scenario_sources(text)
    assert src.step_lines == []
