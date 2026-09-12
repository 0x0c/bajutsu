"""Shared lookups over a composed (`yaml.compose`) raw node tree.

Split out of `edit.py` (the Author editor's scoped splices) so `raw_source.py` (the report's
verbatim-YAML / line-number recovery) can locate the same nodes without re-parsing rules that must
stay identical — both need "which node is scenario *i*" and "what lines does it really span" to
agree on the same file.
"""

from __future__ import annotations

import yaml


def _scalar_value(node: yaml.Node | None) -> str | None:
    return node.value if isinstance(node, yaml.ScalarNode) else None


def _mapping_get(node: yaml.Node | None, key: str) -> yaml.Node | None:
    if not isinstance(node, yaml.MappingNode):
        return None
    return next((v for k, v in node.value if _scalar_value(k) == key), None)


def _scenario_nodes(root: yaml.Node) -> list[yaml.Node]:
    """The MappingNode of each scenario, for the bare-list or `{scenarios: […]}` file form."""
    if isinstance(root, yaml.SequenceNode):
        return list(root.value)
    if isinstance(root, yaml.MappingNode):
        node = _mapping_get(root, "scenarios")
        if isinstance(node, yaml.SequenceNode):
            return list(node.value)
    return []


def _leaf_max_end(node: yaml.Node) -> tuple[int, int]:
    """The furthest (line, column) any scalar leaf under *node* ends at.

    A collection node's own `end_mark` overshoots to the next sibling — sweeping up trailing
    comments and blank lines — so the real content end is the max end over its scalar leaves.
    """
    if isinstance(node, yaml.ScalarNode):
        return (node.end_mark.line, node.end_mark.column)
    children = (
        list(node.value)
        if isinstance(node, yaml.SequenceNode)
        else [child for pair in node.value for child in pair]
    )
    best = (-1, -1)
    for child in children:
        best = max(best, _leaf_max_end(child))
    return best


def _content_span(node: yaml.Node) -> tuple[int, int]:
    """`(start_line, end_line_exclusive)` of *node*'s real content, excluding trailing comments."""
    line, column = _leaf_max_end(node)
    # A leaf ending at column 0 closed on the previous line (a block scalar's terminator); otherwise
    # its content is on `line` itself.
    last = line if column > 0 else line - 1
    return node.start_mark.line, last + 1
