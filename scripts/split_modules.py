"""Split a module that defines several top-level classes into one file per class (BE-0411).

Applies the item's rules 1-3 and 5 mechanically, so a batch never hand-copies a class body or
forgets an intra-package import. It parses with `libcst` rather than the standard library's `ast`
because `ast` drops comments, and many of the classes this moves carry a leading comment that
explains a design choice the split must not lose.

The two calls the item leaves to human judgment stay human: rule 4's ownership question for
module-level code with more than one referencing owner, and the `D100` module docstring each new
file under a `DOCSTRING_PATHS` entry needs. This script decides only the unambiguous half of rule 4
(no referencing owner, or exactly one) and reports the rest.
"""

from __future__ import annotations

import argparse
import keyword
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import libcst as cst

# Where a split file's non-class, non-function pieces land. `_functions.py` is rule 2's group file.
# `_shared.py` holds module-level code with no single owner, which the item's rule 4 places in
# `__init__.py`: that placement cannot work here, because `__init__.py` re-exports the very modules
# that would read the name back, so the name has to be bound before those imports run — and an
# assignment above them trips ruff's E402. A sibling module has neither problem.
FUNCTIONS_MODULE = "_functions"
SHARED_MODULE = "_shared"
# Module-level code that binds nothing — a `model_rebuild()` call, a registration — is rule 4's
# no-single-owner case in its purest form, and `__init__.py` is where the item's design puts it.
# Binding nothing is exactly what makes that placement safe: appended after the re-export imports it
# trips neither E402 nor a cycle, and every name it reads is already in scope.
INIT_MODULE = "__init__"
RESERVED_STEMS = frozenset({"__init__", FUNCTIONS_MODULE, SHARED_MODULE})


class SplitError(Exception):
    """A file this script refuses to split, because doing so would need a judgment call."""


def snake_case(name: str) -> str:
    """Render a class name as its module filename, keeping any leading underscores.

    A name that lands on a Python keyword takes PEP 8's trailing underscore: the scenario schema's
    `If` step would otherwise want `if.py`, which no import statement can name.
    """
    underscores = len(name) - len(name.lstrip("_"))
    core = name[underscores:]
    core = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", core)
    core = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", core)
    stem = "_" * underscores + core.lower()
    return f"{stem}_" if keyword.iskeyword(stem) else stem


class _References(cst.CSTVisitor):
    """Collect the names a subtree reads, separating annotation-only reads from runtime ones.

    The separation is what lets rule 5 hold without a special case: a sibling referenced only from
    an annotation can be imported under `TYPE_CHECKING`, where a cycle between two split-off
    classes cannot form.
    """

    def __init__(self) -> None:
        self.all: set[str] = set()
        self.runtime: set[str] = set()
        self.rebound: set[str] = set()
        self.uses_file: bool = False
        self._annotation_depth = 0

    def _record(self, name: str) -> None:
        self.all.add(name)
        if self._annotation_depth == 0:
            self.runtime.add(name)

    def visit_Name(self, node: cst.Name) -> bool:
        if node.value == "__file__":
            self.uses_file = True
        self._record(node.value)
        return False

    def visit_Attribute(self, node: cst.Attribute) -> bool:
        # `.attr` is a member name, never a module-level binding this file has to import.
        node.value.visit(self)
        return False

    def visit_Arg(self, node: cst.Arg) -> bool:
        # Same for a keyword argument's name.
        node.value.visit(self)
        return False

    def visit_Param(self, node: cst.Param) -> bool:
        # A parameter binds its own name; only its annotation and default read outer names.
        if node.annotation is not None:
            node.annotation.visit(self)
        if node.default is not None:
            node.default.visit(self)
        return False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        for decorator in node.decorators:
            decorator.visit(self)
        if node.type_parameters is not None:
            # A PEP 695 bound reads names too: `def f[F: Callable[..., Any]](…)` needs `Callable`.
            node.type_parameters.visit(self)
        node.params.visit(self)
        if node.returns is not None:
            node.returns.visit(self)
        node.body.visit(self)
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        for decorator in node.decorators:
            decorator.visit(self)
        if node.type_parameters is not None:
            node.type_parameters.visit(self)
        for base in node.bases:
            base.visit(self)
        for kwarg in node.keywords:
            kwarg.visit(self)
        node.body.visit(self)
        return False

    def visit_Subscript(self, node: cst.Subscript) -> bool:
        # A quoted forward reference is not always inside an `Annotation`: a type alias writes it
        # straight into a subscript, as `Callable[[Driver], "AlertEvent | None"]` does. Read those
        # in annotation context, so the name is imported rather than left undefined.
        node.value.visit(self)
        self._annotation_depth += 1
        for element in node.slice:
            if isinstance(element.slice, cst.Index) and isinstance(
                element.slice.value, cst.SimpleString
            ):
                self._visit_quoted(element.slice.value)
            else:
                element.visit(self)
        self._annotation_depth -= 1
        return False

    def visit_Annotation(self, node: cst.Annotation) -> bool:
        self._annotation_depth += 1
        inner = node.annotation
        if isinstance(inner, cst.SimpleString):
            # A quoted forward reference still names something this file must import.
            self._visit_quoted(inner)
        else:
            inner.visit(self)
        self._annotation_depth -= 1
        return False

    def _visit_quoted(self, node: cst.SimpleString) -> None:
        text = node.evaluated_value
        if not isinstance(text, str):
            return
        try:
            expression = cst.parse_expression(text)
        except cst.ParserSyntaxError:
            return
        expression.visit(self)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        # `x: int = 1` binds `x`; only the annotation and the value read outer names. Without this,
        # a dataclass field that happens to share a sibling's name reads as a reference to it, and
        # the bogus import it produces can close a cycle between two split-off files.
        self._visit_target(node.target)
        node.annotation.visit(self)
        if node.value is not None:
            node.value.visit(self)
        return False

    def visit_AssignTarget(self, node: cst.AssignTarget) -> bool:
        self._visit_target(node.target)
        return False

    def visit_For(self, node: cst.For) -> bool:
        self._visit_target(node.target)
        node.iter.visit(self)
        node.body.visit(self)
        if node.orelse is not None:
            node.orelse.visit(self)
        return False

    def visit_CompFor(self, node: cst.CompFor) -> bool:
        self._visit_target(node.target)
        node.iter.visit(self)
        for condition in node.ifs:
            condition.visit(self)
        if node.inner_for_in is not None:
            node.inner_for_in.visit(self)
        return False

    def visit_AsName(self, _node: cst.AsName) -> bool:
        # `with … as x` / `except … as x` bind `x` rather than reading it.
        return False

    def _visit_target(self, target: cst.BaseExpression) -> None:
        """Record only the reads a binding target performs — `obj.attr` reads `obj`, `x` reads none."""
        if not isinstance(target, cst.Name):
            target.visit(self)

    def visit_Global(self, node: cst.Global) -> bool:
        for item in node.names:
            self.rebound.add(item.name.value)
        return False


def _references(node: cst.CSTNode) -> _References:
    collected = _References()
    node.visit(collected)
    return collected


def _alias_binding(alias: cst.ImportAlias) -> str:
    """The name an `import` statement's single alias binds in the importing module."""
    if alias.asname is not None:
        target = alias.asname.name
        if isinstance(target, cst.Name):
            return target.value
        raise SplitError(f"unsupported import alias target: {type(target).__name__}")
    name: cst.BaseExpression = alias.name
    while isinstance(name, cst.Attribute):
        # `import a.b.c` binds `a`, not `a.b.c`.
        name = name.value
    if not isinstance(name, cst.Name):
        raise SplitError(f"unsupported import name: {type(name).__name__}")
    return name.value


def _import_of(statement: cst.SimpleStatementLine) -> cst.Import | cst.ImportFrom:
    """The single `import` a header statement line holds."""
    small = statement.body[0]
    if not isinstance(small, (cst.Import, cst.ImportFrom)):
        raise SplitError(f"expected an import, found {type(small).__name__}")
    return small


def _filter_import(
    node: cst.Import | cst.ImportFrom, used: set[str]
) -> cst.Import | cst.ImportFrom | None:
    """Narrow one import statement to the aliases whose bound name is actually read.

    Returns None when none of them is. Dropping the unread aliases is not cosmetic: ruff's `F401`
    is on with no per-file ignore, so carrying an unread import into a split file fails the gate.
    """
    names = node.names
    if isinstance(names, cst.ImportStar):
        raise SplitError("a star import hides which names this module binds")
    aliases = [
        alias.with_changes(comma=cst.MaybeSentinel.DEFAULT)
        for alias in names
        if _alias_binding(alias) in used
    ]
    if not aliases:
        return None
    return node.with_changes(names=aliases)


def _is_main_guard(node: cst.BaseStatement) -> bool:
    """Whether this is the `if __name__ == "__main__":` entry point a package needs to keep."""
    return isinstance(node, cst.If) and '__name__ == "__main__"' in cst.Module(
        body=[]
    ).code_for_node(node.test)


def _is_type_checking_block(node: cst.BaseStatement) -> bool:
    return isinstance(node, cst.If) and "TYPE_CHECKING" in cst.Module(body=[]).code_for_node(
        node.test
    )


def _is_future_import(node: cst.CSTNode) -> bool:
    return (
        isinstance(node, cst.ImportFrom)
        and isinstance(node.module, cst.Name)
        and node.module.value == "__future__"
    )


@dataclass
class _Declaration:
    """One top-level class or function, and the file it moves to."""

    name: str
    stem: str
    node: cst.ClassDef | cst.FunctionDef
    is_class: bool


@dataclass
class _ModuleLevel:
    """One module-level statement that is neither an import nor a declaration (rule 4)."""

    node: cst.SimpleStatementLine
    binds: tuple[str, ...]
    reads: _References


@dataclass
class _Parsed:
    """The original module, taken apart into the pieces the split reassembles."""

    module: cst.Module
    docstring: cst.SimpleStatementLine | None = None
    future: cst.SimpleStatementLine | None = None
    imports: list[cst.SimpleStatementLine] = field(default_factory=list)
    type_checking: list[cst.SimpleStatementLine] = field(default_factory=list)
    declarations: list[_Declaration] = field(default_factory=list)
    module_level: list[_ModuleLevel] = field(default_factory=list)
    dunder_all: list[str] | None = None
    main_guard: cst.If | None = None


def _target_names(target: cst.BaseExpression) -> list[str]:
    """Every name one assignment target binds, unpacking `a, b = …` down to its elements."""
    if isinstance(target, cst.Name):
        return [target.value]
    if isinstance(target, (cst.Tuple, cst.List)):
        return [name for element in target.elements for name in _target_names(element.value)]
    if isinstance(target, cst.StarredElement):
        return _target_names(target.value)
    return []  # `obj.attr` / `seq[i]` bind nothing this module re-exports


def _assign_targets(statement: cst.SimpleStatementLine) -> tuple[str, ...]:
    names: list[str] = []
    for small in statement.body:
        if isinstance(small, cst.Assign):
            for target in small.targets:
                names.extend(_target_names(target.target))
        elif isinstance(small, (cst.AnnAssign, cst.AugAssign)):
            names.extend(_target_names(small.target))
        elif isinstance(small, cst.TypeAlias):
            names.append(small.name.value)
    return tuple(names)


def _literal_string_list(statement: cst.SimpleStatementLine) -> list[str] | None:
    """Read an `__all__ = [...]` of plain string literals, or None if it is computed."""
    small = statement.body[0]
    if not isinstance(small, cst.Assign):
        return None
    value = small.value
    if not isinstance(value, (cst.List, cst.Tuple)):
        return None
    names: list[str] = []
    for element in value.elements:
        if not isinstance(element.value, cst.SimpleString):
            return None
        text = element.value.evaluated_value
        if not isinstance(text, str):
            return None
        names.append(text)
    return names


def _parse(source: str) -> _Parsed:
    module = cst.parse_module(source)
    parsed = _Parsed(module=module)
    for index, statement in enumerate(module.body):
        if isinstance(statement, (cst.ClassDef, cst.FunctionDef)):
            is_class = isinstance(statement, cst.ClassDef)
            stem = snake_case(statement.name.value) if is_class else FUNCTIONS_MODULE
            parsed.declarations.append(
                _Declaration(
                    name=statement.name.value, stem=stem, node=statement, is_class=is_class
                )
            )
            continue
        if _is_main_guard(statement):
            assert isinstance(statement, cst.If)
            # `python -m pkg` runs `__main__.py`, never `__init__.py`, so the guard has to move
            # there or the entry point disappears without a word — `scripts/install.sh` and the
            # web-e2e job both invoke one this way.
            parsed.main_guard = statement
            continue
        if _is_type_checking_block(statement):
            assert isinstance(statement, cst.If)
            for inner in statement.body.body:
                if not isinstance(inner, cst.SimpleStatementLine):
                    raise SplitError("a TYPE_CHECKING block holds more than plain imports")
                parsed.type_checking.append(inner)
            continue
        if not isinstance(statement, cst.SimpleStatementLine):
            raise SplitError(
                f"unsupported module-level {type(statement).__name__} statement; split by hand"
            )
        small = statement.body[0]
        if index == 0 and isinstance(small, cst.Expr) and isinstance(small.value, cst.SimpleString):
            parsed.docstring = statement
            continue
        if isinstance(small, (cst.Import, cst.ImportFrom)):
            if len(statement.body) != 1:
                raise SplitError("a `;`-joined import line is ambiguous to split")
            if _is_future_import(small):
                parsed.future = statement
            else:
                parsed.imports.append(statement)
            continue
        targets = _assign_targets(statement)
        if targets == ("__all__",):
            names = _literal_string_list(statement)
            if names is None:
                raise SplitError("a computed `__all__` cannot be carried across the split")
            parsed.dunder_all = names
            continue
        parsed.module_level.append(
            _ModuleLevel(node=statement, binds=targets, reads=_references(statement))
        )
    return parsed


def _check_splittable(parsed: _Parsed, name: str, *, allow_file_paths: bool) -> None:
    classes = [d for d in parsed.declarations if d.is_class]
    if len(classes) < 2:
        raise SplitError(f"{name} defines {len(classes)} top-level class(es); nothing to split")
    stems: dict[str, str] = {}
    for declaration in parsed.declarations:
        if declaration.stem in RESERVED_STEMS and declaration.is_class:
            raise SplitError(f"class {declaration.name} would collide with {declaration.stem}.py")
        if declaration.is_class:
            if declaration.stem in stems:
                raise SplitError(
                    f"{declaration.name} and {stems[declaration.stem]} both map to "
                    f"{declaration.stem}.py"
                )
            stems[declaration.stem] = declaration.name
    if allow_file_paths:
        return
    scanned = [statement.reads for statement in parsed.module_level]
    scanned += [_references(declaration.node) for declaration in parsed.declarations]
    for reads in scanned:
        if reads.uses_file:
            raise SplitError(
                "`__file__` here resolves one directory deeper after the split, and would break "
                "silently; adjust its parent count by hand first"
            )


def _assign_owners(parsed: _Parsed) -> tuple[dict[int, str], list[str]]:
    """Place each module-level statement (rule 4) and say which placements a human must confirm."""
    # Keyed by target file, not by declaration: rule 2 sends every top-level function to one
    # `_functions.py`, so their reads have to merge or only the last one would count as an owner.
    declaration_reads: dict[str, _References] = {}
    for declaration in parsed.declarations:
        merged = declaration_reads.setdefault(declaration.stem, _References())
        reads = _references(declaration.node)
        merged.all |= reads.all
        merged.runtime |= reads.runtime
        merged.rebound |= reads.rebound
    rebound: set[str] = set()
    for reads in declaration_reads.values():
        rebound |= reads.rebound
    placement: dict[int, str] = {}
    notes: list[str] = []
    for index, statement in enumerate(parsed.module_level):
        if not statement.binds:
            placement[index] = INIT_MODULE
            continue
        bound = set(statement.binds)
        owners = sorted({stem for stem, reads in declaration_reads.items() if reads.all & bound})
        # A module-level statement can own another: `oplog.py`'s `_CONTEXT_KEYS` is built from the
        # context variables declared beside it. Counting only classes and functions as owners
        # scatters such a pair across two files that then import each other at module load, which
        # no rule-5 in-method import can break.
        if any(other is not statement and other.reads.all & bound for other in parsed.module_level):
            owners = sorted({*owners, SHARED_MODULE})
        names = ", ".join(statement.binds)
        if rebound & set(statement.binds):
            # `global` cannot reach a name in another module, so the memo has to sit with the
            # function that rebinds it — which rule 2 already sent to `_functions.py`.
            placement[index] = FUNCTIONS_MODULE
            notes.append(f"  {names}: kept with its `global` rebinding in {FUNCTIONS_MODULE}.py")
        elif not owners:
            placement[index] = SHARED_MODULE
        elif len(owners) == 1:
            placement[index] = owners[0]
        else:
            placement[index] = SHARED_MODULE
            notes.append(
                f"  {names}: read by {', '.join(owners)} — placed in {SHARED_MODULE}.py, "
                "confirm that is right"
            )
    return placement, notes


def _binding_stems(parsed: _Parsed, placement: dict[int, str]) -> dict[str, str]:
    """Map every top-level name the original module bound to the file it now lives in."""
    stems = {d.name: d.stem for d in parsed.declarations}
    for index, statement in enumerate(parsed.module_level):
        for name in statement.binds:
            stems[name] = placement[index]
    return stems


_Statement = cst.SimpleStatementLine | cst.BaseCompoundStatement


def _render(statements: list[_Statement]) -> str:
    return cst.Module(body=statements).code


def _file_reads(
    owned: list[cst.SimpleStatementLine], declarations: list[_Declaration]
) -> _References:
    """The names one split file reads, merged across everything that lands in it."""
    reads = _References()
    for node in [*owned, *(declaration.node for declaration in declarations)]:
        collected = _references(node)
        reads.all |= collected.all
        reads.runtime |= collected.runtime
    return reads


def _runtime_cycles(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Every cycle among the split files' runtime imports, which rule 5 has to break by hand."""
    cycles: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()

    def walk(stem: str, path: list[str]) -> None:
        for neighbour in sorted(graph.get(stem, ())):
            if neighbour in path:
                cycle = path[path.index(neighbour) :]
                key = tuple(sorted(cycle))
                if key not in seen:
                    seen.add(key)
                    cycles.append(tuple(cycle))
            elif len(path) < len(graph):
                walk(neighbour, [*path, neighbour])

    for stem in sorted(graph):
        walk(stem, [stem])
    return cycles


def _siblings(stem: str, reads: _References, stems: dict[str, str]) -> dict[str, str]:
    """The other split files this one reads a name from, keyed by that name."""
    return {name: where for name, where in stems.items() if where != stem and name in reads.all}


def _choose_deferred(
    reads_by_stem: dict[str, _References], stems: dict[str, str]
) -> tuple[dict[str, set[str]], list[str]]:
    """Decide which sibling imports move under `TYPE_CHECKING`, and report the cycles left over.

    Every sibling import is a runtime one by default. A name a class mentions only in an annotation
    still needs a runtime binding whenever something resolves those annotations at run time —
    Pydantic rebuilds a model from them, and a `TYPE_CHECKING` import leaves the name undefined. So
    an import is deferred only where a cycle forces it, and only on an edge that is annotation-only,
    which is rule 5's lazy treatment expressed as an import placement.
    """
    deferred: dict[str, set[str]] = {}
    notes: list[str] = []
    while True:
        graph = {
            stem: {
                where
                for name, where in _siblings(stem, reads, stems).items()
                if name not in deferred.get(stem, set())
            }
            for stem, reads in reads_by_stem.items()
        }
        cycles = _runtime_cycles(graph)
        if not cycles:
            return deferred, notes
        cycle = cycles[0]
        for index, stem in enumerate(cycle):
            target = cycle[(index + 1) % len(cycle)]
            reads = reads_by_stem[stem]
            names = {
                name
                for name, where in _siblings(stem, reads, stems).items()
                if where == target and name not in deferred.get(stem, set())
            }
            if names and not (names & reads.runtime):
                deferred.setdefault(stem, set()).update(names)
                break
        else:
            notes.append(
                f"  circular import {' -> '.join([*cycle, cycle[0]])}.py — break it with rule 5's "
                "in-method import before the package will load"
            )
            return deferred, notes


def _render_file(
    parsed: _Parsed,
    stem: str,
    owned: list[cst.SimpleStatementLine],
    declarations: list[_Declaration],
    stems: dict[str, str],
    deferred: set[str],
) -> str:
    reads = _file_reads(owned, declarations)
    siblings = _siblings(stem, reads, stems)
    runtime_siblings = {n: w for n, w in siblings.items() if n not in deferred}
    deferred_siblings = {n: w for n, w in siblings.items() if n in deferred}

    type_checking: list[_Statement] = []
    for statement in parsed.type_checking:
        kept = _filter_import(_import_of(statement), reads.all)
        if kept is not None:
            type_checking.append(statement.with_changes(body=[kept], leading_lines=[]))
    type_checking.extend(
        cst.parse_statement(f"from .{deferred_siblings[name]} import {name}")
        for name in sorted(deferred_siblings)
    )

    used = set(reads.all)
    if type_checking:
        used.add("TYPE_CHECKING")

    body: list[_Statement] = []
    if parsed.future is not None:
        body.append(parsed.future.with_changes(leading_lines=[]))
    imports: list[_Statement] = []
    for statement in parsed.imports:
        kept = _filter_import(_import_of(statement), used)
        if kept is not None:
            imports.append(statement.with_changes(body=[kept]))
    if type_checking and not any("TYPE_CHECKING" in _render([statement]) for statement in imports):
        imports.append(cst.parse_statement("from typing import TYPE_CHECKING"))
    body.extend(imports)
    body.extend(
        cst.parse_statement(f"from .{runtime_siblings[name]} import {name}")
        for name in sorted(runtime_siblings)
    )
    if type_checking:
        body.append(
            cst.parse_statement("if TYPE_CHECKING:\n    pass\n").with_changes(
                body=cst.IndentedBlock(body=type_checking)
            )
        )
    # A statement derived from its own owner has to follow it: `_ASSERTION_KINDS` reads
    # `Assertion.model_fields`, so emitting it above the class would raise a NameError on import.
    declared = {declaration.name for declaration in declarations}
    body.extend(statement for statement in owned if not (_references(statement).all & declared))
    body.extend(declaration.node for declaration in declarations)
    body.extend(statement for statement in owned if _references(statement).all & declared)
    return _render(body)


def _render_init(
    parsed: _Parsed, stems: dict[str, str], trailing: list[cst.SimpleStatementLine]
) -> str:
    exported: list[tuple[str, str]] = []
    seen: set[str] = set()
    for statement in parsed.module_level:
        for name in statement.binds:
            if name not in seen:
                exported.append((name, stems[name]))
                seen.add(name)
    for declaration in parsed.declarations:
        if declaration.name not in seen:
            exported.append((declaration.name, declaration.stem))
            seen.add(declaration.name)

    public = [name for name, _ in exported if not name.startswith("_")]
    dunder_all = parsed.dunder_all if parsed.dunder_all is not None else public

    body: list[_Statement] = []
    if parsed.docstring is not None:
        body.append(parsed.docstring)
    grouped: dict[str, list[str]] = {}
    order: list[str] = []
    for name, where in exported:
        if where not in grouped:
            grouped[where] = []
            order.append(where)
        grouped[where].append(name)
    for where in order:
        names = ", ".join(
            # `X as X` is ruff's explicit-re-export form: a name outside `__all__` needs it, or
            # `F401` reads the import as dead and the gate fails.
            name if name in dunder_all else f"{name} as {name}"
            for name in grouped[where]
        )
        body.append(cst.parse_statement(f"from .{where} import {names}"))
    listed = ", ".join(f'"{name}"' for name in dunder_all)
    body.append(cst.parse_statement(f"__all__ = [{listed}]"))
    body.extend(trailing)
    return _render(body)


def _render_main(parsed: _Parsed, stems: dict[str, str]) -> str:
    """The package's `__main__.py`: the original entry-point guard, over package-level imports."""
    assert parsed.main_guard is not None
    reads = _references(parsed.main_guard)
    imported = sorted(name for name in reads.all if name in stems)
    body: list[_Statement] = []
    if imported:
        body.append(cst.parse_statement(f"from . import {', '.join(imported)}"))
    body.append(parsed.main_guard.with_changes(leading_lines=[]))
    return _render(body)


@dataclass(frozen=True)
class SplitPlan:
    """The files one split writes, and the placements a human still has to confirm."""

    files: dict[str, str]
    notes: tuple[str, ...]


def plan_split(source: str, *, name: str = "<module>", allow_file_paths: bool = False) -> SplitPlan:
    """Work out the package one multi-class module becomes, without touching the filesystem.

    Args:
        source: The module's text.
        name: The module's path, used only in refusal messages.
        allow_file_paths: Split even though the module reads `__file__`, because its parent count
            has already been corrected for the directory level the split adds.

    Returns:
        The new package's files, keyed by filename, plus the rule-4 placements to review.

    Raises:
        SplitError: The file needs a judgment call this script will not make for you.
    """
    parsed = _parse(source)
    _check_splittable(parsed, name, allow_file_paths=allow_file_paths)
    placement, notes = _assign_owners(parsed)
    stems = _binding_stems(parsed, placement)

    owned: dict[str, list[cst.SimpleStatementLine]] = {}
    for index, statement in enumerate(parsed.module_level):
        owned.setdefault(placement[index], []).append(statement.node)
    grouped: dict[str, list[_Declaration]] = {}
    for declaration in parsed.declarations:
        grouped.setdefault(declaration.stem, []).append(declaration)

    reads_by_stem = {
        stem: _file_reads(owned.get(stem, []), grouped.get(stem, []))
        for stem in sorted((set(owned) | set(grouped)) - {INIT_MODULE})
    }
    deferred, cycle_notes = _choose_deferred(reads_by_stem, stems)
    files = {
        f"{stem}.py": _render_file(
            parsed,
            stem,
            owned.get(stem, []),
            grouped.get(stem, []),
            stems,
            deferred.get(stem, set()),
        )
        for stem in reads_by_stem
    }
    files["__init__.py"] = _render_init(parsed, stems, owned.get(INIT_MODULE, []))
    if parsed.main_guard is not None:
        files["__main__.py"] = _render_main(parsed, stems)
    return SplitPlan(files=files, notes=tuple(notes + cycle_notes))


def apply_split(path: Path, plan: SplitPlan) -> Path:
    """Replace `path` with the package `plan` describes, and return the new directory."""
    package = path.with_suffix("")
    package.mkdir()
    for filename, source in plan.files.items():
        (package / filename).write_text(source)
    path.unlink()
    return package


def _tidy(paths: list[Path]) -> None:
    """Sort each new file's imports and format it, so the gate sees the same text a human would."""
    targets = [str(path) for path in paths]
    # `I` sorts the imports and `RUF022` the generated `__all__`. Both are left to ruff rather than
    # reproduced here, so the script cannot disagree with the gate about what sorted means.
    subprocess.run(
        ["uv", "run", "ruff", "check", "--select", "I,RUF022", "--fix", "-q", *targets], check=False
    )
    subprocess.run(["uv", "run", "ruff", "format", "-q", *targets], check=False)


def main(argv: list[str] | None = None) -> int:
    """Split every module named on the command line, reporting what still needs a human."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", type=Path, help="modules to split into packages")
    parser.add_argument(
        "--dry-run", action="store_true", help="report the plan without writing anything"
    )
    parser.add_argument(
        "--allow-file-paths",
        action="store_true",
        help="split modules reading `__file__` whose parent count is already corrected",
    )
    args = parser.parse_args(argv)

    written: list[Path] = []
    failed = False
    for path in args.paths:
        try:
            plan = plan_split(
                path.read_text(), name=str(path), allow_file_paths=args.allow_file_paths
            )
        except SplitError as error:
            print(f"SKIP {path}: {error}", file=sys.stderr)
            failed = True
            continue
        print(f"{path} -> {len(plan.files)} files")
        for note in plan.notes:
            print(note)
        if not args.dry_run:
            written.append(apply_split(path, plan))
    if written:
        _tidy([path for package in written for path in sorted(package.glob("*.py"))])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
