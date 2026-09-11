"""Recover each scenario's verbatim YAML — comments and formatting intact — from its source file.

`load_scenario_file` parses through pydantic, which drops comments and source positions the
moment a `Scenario` model exists — the report's YAML tab has re-serialized the parsed model ever
since, so an author's comments never survived into it. This instead composes the file's raw node
tree (`yaml.compose`, the same one-shot parse `edit.py`'s scoped splices already use) and slices
the original text by each scenario's line span, so comments and formatting simply aren't touched.

A literal (non-`${...}`) `totp.secret` is still masked in place, mirroring
`serialize._mask_totp_secrets` (BE-0152) — the one credential shape structural knowledge alone
can catch and the generic pattern backstop (`redaction.mask_credential_shapes`, run over every
artifact `RunArtifactWriter` writes) cannot. Nothing else here re-derives or reformats anything.
"""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from bajutsu.common import _yaml
from bajutsu.common.scenario import interp
from bajutsu.common.scenario._yaml_nodes import _content_span, _mapping_get, _scenario_nodes

_TOTP_PLACEHOLDER = "<redacted>"


@dataclass(frozen=True)
class RawScenario:
    """One scenario's verbatim source text and each of its steps' original line number."""

    text: str
    # 1-based line, in the *original file*, where each of the scenario's `steps:` items starts.
    # Meaningful only while nothing has changed that step list's shape since; a caller whose own
    # setup/component expansion added or replaced steps drops these rather than show a wrong line.
    step_lines: list[int]


def scenario_sources(text: str) -> list[RawScenario]:
    """Each scenario's verbatim slice of *text*, aligned with `load_scenario_file(text).scenarios`."""
    root = yaml.compose(text, Loader=_yaml._Loader)  # noqa: SLF001  # see bajutsu/common/_yaml.py
    lines = text.split("\n")
    out: list[RawScenario] = []
    for node in _scenario_nodes(root):
        start, end = _content_span(node)
        start = _with_leading_comments(lines, start)
        raw_lines = _redact_totp_secrets(lines[start:end], node, start)
        steps_node = _mapping_get(node, "steps")
        step_lines = (
            [n.start_mark.line + 1 for n in steps_node.value]
            if isinstance(steps_node, yaml.SequenceNode)
            else []
        )
        out.append(RawScenario(text="\n".join(raw_lines), step_lines=step_lines))
    return out


def _with_leading_comments(lines: list[str], start: int) -> int:
    """Extend *start* back over contiguous `#`-comment lines directly above it (no blank gap).

    A scenario's own leading comment (`# login flow` right above `- name: ...`) sits outside its
    node's `start_mark` — comments carry no position in the parsed stream — so without this it
    would silently vanish from the slice.
    """
    i = start
    while i > 0 and lines[i - 1].strip().startswith("#"):
        i -= 1
    return i


def _totp_secret_scalars(node: yaml.Node) -> list[yaml.ScalarNode]:
    """Every literal (non-`${...}`) `totp.secret` scalar nested anywhere under *node*."""
    found: list[yaml.ScalarNode] = []
    if isinstance(node, yaml.MappingNode):
        totp = _mapping_get(node, "totp")
        if isinstance(totp, yaml.MappingNode):
            secret = _mapping_get(totp, "secret")
            if isinstance(secret, yaml.ScalarNode) and not interp.is_reference(secret.value):
                found.append(secret)
        for _, v in node.value:
            found.extend(_totp_secret_scalars(v))
    elif isinstance(node, yaml.SequenceNode):
        for child in node.value:
            found.extend(_totp_secret_scalars(child))
    return found


def _redact_totp_secrets(raw_lines: list[str], node: yaml.Node, offset: int) -> list[str]:
    """Mask any literal `totp.secret` value in *raw_lines* in place.

    *raw_lines* is already sliced to *node*'s span, starting at file line *offset*. Processed
    bottom-up (like `edit._spliced`) so a multi-line block-scalar secret's own splice
    never shifts the line numbers a still-pending earlier secret was computed against.
    """
    out = list(raw_lines)
    secrets = sorted(_totp_secret_scalars(node), key=lambda s: s.start_mark.line, reverse=True)
    for secret in secrets:
        start_line = secret.start_mark.line - offset
        end_line = secret.end_mark.line - offset
        if start_line == end_line:
            col_start, col_end = secret.start_mark.column, secret.end_mark.column
            out[start_line] = (
                out[start_line][:col_start] + _TOTP_PLACEHOLDER + out[start_line][col_end:]
            )
        else:
            # A block-scalar secret spans multiple lines — collapse the whole span to one
            # placeholder line rather than leave any of its literal content visible.
            indent = out[start_line][: len(out[start_line]) - len(out[start_line].lstrip(" "))]
            out[start_line : end_line + 1] = [f"{indent}{_TOTP_PLACEHOLDER}"]
    return out
