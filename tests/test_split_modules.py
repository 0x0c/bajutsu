"""Tests for the one-class-per-file splitting script (BE-0411).

The script rewrites 86 modules holding 459 classes between them, so a rule it applies wrongly is a
defect repeated hundreds of times. Each of the item's five split rules is pinned here against a
small fixture module, together with the refusals that keep a file needing human judgment — a
`__file__`-relative path, a star import, a computed `__all__` — from being split silently.
"""

from __future__ import annotations

import textwrap

import pytest

from scripts.split_modules import SplitError, SplitPlan, plan_split, snake_case


def _plan(source: str) -> SplitPlan:
    return plan_split(textwrap.dedent(source).lstrip("\n"))


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("LongPress", "long_press"),
        ("Impact", "impact"),
        ("_HotspotTally", "_hotspot_tally"),
        ("HTTPError", "http_error"),
        ("XcuitestDriver", "xcuitest_driver"),
        ("_JSON", "_json"),
        # PEP 8's trailing underscore: `if.py` is unimportable, so the scenario schema's `If` step
        # cannot simply take its own lowercase name.
        ("If", "if_"),
        ("Not", "not_"),
    ],
)
def test_snake_case_keeps_leading_underscores(name: str, expected: str) -> None:
    assert snake_case(name) == expected


def test_each_class_gets_its_own_file() -> None:
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass
        """
    )
    assert set(plan.files) == {"__init__.py", "alpha.py", "beta.py"}
    assert "class Alpha:" in plan.files["alpha.py"]
    assert "class Beta:" in plan.files["beta.py"]


def test_init_re_exports_in_declaration_order_with_dunder_all() -> None:
    plan = _plan(
        """
        \"\"\"Original docstring.\"\"\"


        class Beta:
            pass


        class Alpha:
            pass
        """
    )
    init = plan.files["__init__.py"]
    assert init.startswith('"""Original docstring."""')
    assert init.index("from .beta import Beta") < init.index("from .alpha import Alpha")
    assert '__all__ = ["Beta", "Alpha"]' in init


def test_existing_dunder_all_is_preserved_verbatim() -> None:
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass


        __all__ = ["Alpha"]
        """
    )
    init = plan.files["__init__.py"]
    assert '__all__ = ["Alpha"]' in init
    # Beta stays importable from the package even though it is outside `__all__`, so the explicit
    # re-export form is what keeps ruff's F401 from reading the import as dead.
    assert "from .beta import Beta as Beta" in init


def test_private_class_keeps_its_underscore_and_uses_the_re_export_form() -> None:
    plan = _plan(
        """
        class Alpha:
            pass


        class _Helper:
            pass
        """
    )
    assert "_helper.py" in plan.files
    init = plan.files["__init__.py"]
    assert "from ._helper import _Helper as _Helper" in init
    assert '__all__ = ["Alpha"]' in init


def test_leading_comment_travels_with_its_class() -> None:
    plan = _plan(
        """
        class Alpha:
            pass


        # Kept deliberately narrow: widening it would change the verdict.
        class Beta:
            pass
        """
    )
    assert "# Kept deliberately narrow" in plan.files["beta.py"]
    assert "# Kept deliberately narrow" not in plan.files["alpha.py"]


def test_runtime_sibling_reference_becomes_a_relative_import() -> None:
    plan = _plan(
        """
        class Base:
            pass


        class Child(Base):
            pass
        """
    )
    assert "from .base import Base" in plan.files["child.py"]
    assert "from .child import" not in plan.files["base.py"]


def test_an_annotation_only_sibling_is_still_a_runtime_import() -> None:
    # Pydantic rebuilds a model from its annotations at run time, so a name mentioned only in one
    # still needs a real binding: deferring it under `TYPE_CHECKING` leaves the model undefined.
    plan = _plan(
        """
        from __future__ import annotations


        class Alpha:
            pass


        class Beta:
            def take(self, value: Alpha) -> None:
                pass
        """
    )
    beta = plan.files["beta.py"]
    assert "from .alpha import Alpha" in beta
    assert "if TYPE_CHECKING:" not in beta


def test_an_annotation_only_edge_is_deferred_only_to_break_a_cycle() -> None:
    plan = _plan(
        """
        from __future__ import annotations


        class Alpha:
            def take(self, value: Beta) -> None:
                pass


        class Beta:
            def make(self) -> object:
                return Alpha()
        """
    )
    # Beta reads Alpha at run time and cannot be deferred; Alpha reads Beta only in an annotation,
    # so that is the edge rule 5 breaks — and the cycle needs no hand-written in-method import.
    alpha = plan.files["alpha.py"]
    assert "if TYPE_CHECKING:" in alpha
    assert alpha.index("if TYPE_CHECKING:") < alpha.index("from .beta import Beta")
    assert "from .alpha import Alpha" in plan.files["beta.py"]
    assert plan.notes == ()


def test_top_level_functions_move_together_into_one_file() -> None:
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass


        def first() -> None:
            pass


        def second() -> None:
            pass
        """
    )
    functions = plan.files["_functions.py"]
    assert "def first()" in functions
    assert "def second()" in functions
    assert "from ._functions import first, second" in plan.files["__init__.py"]


def test_unused_imports_are_pruned_from_each_split_file() -> None:
    plan = _plan(
        """
        import json
        import os


        class Alpha:
            def dump(self) -> str:
                return json.dumps({})


        class Beta:
            def cwd(self) -> str:
                return os.getcwd()
        """
    )
    assert "import json" in plan.files["alpha.py"]
    assert "import os" not in plan.files["alpha.py"]
    assert "import os" in plan.files["beta.py"]
    assert "import json" not in plan.files["beta.py"]


def test_one_import_line_keeps_only_the_names_each_file_reads() -> None:
    plan = _plan(
        """
        from dataclasses import dataclass, field


        @dataclass
        class Alpha:
            values: list[str] = field(default_factory=list)


        @dataclass
        class Beta:
            pass
        """
    )
    assert "from dataclasses import dataclass, field" in plan.files["alpha.py"]
    assert "from dataclasses import dataclass\n" in plan.files["beta.py"]


def test_module_level_code_with_one_owner_moves_into_that_owner() -> None:
    plan = _plan(
        """
        _LIMIT = 5


        class Alpha:
            def cap(self) -> int:
                return _LIMIT


        class Beta:
            pass
        """
    )
    assert "_LIMIT = 5" in plan.files["alpha.py"]
    assert "_shared.py" not in plan.files
    assert "from .alpha import _LIMIT as _LIMIT" in plan.files["__init__.py"]


def test_module_level_code_with_several_owners_is_shared_and_reported() -> None:
    plan = _plan(
        """
        _LIMIT = 5


        class Alpha:
            def cap(self) -> int:
                return _LIMIT


        class Beta:
            def cap(self) -> int:
                return _LIMIT
        """
    )
    assert "_LIMIT = 5" in plan.files["_shared.py"]
    assert "from ._shared import _LIMIT" in plan.files["alpha.py"]
    assert "from ._shared import _LIMIT" in plan.files["beta.py"]
    assert any("alpha, beta" in note for note in plan.notes)


def test_code_that_binds_nothing_runs_at_the_end_of_the_package_init() -> None:
    # `If.model_rebuild()` in scenario/models/steps.py. It has to run where every name is in scope,
    # which after the split is the package `__init__` — from a sibling module it resolves against
    # that module's globals instead, and Pydantic cannot find the forward-referenced `Step`.
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass


        Alpha.rebuild()
        """
    )
    init = plan.files["__init__.py"]
    assert init.index("__all__") < init.index("Alpha.rebuild()")
    assert "_shared.py" not in plan.files


def test_module_level_code_with_no_owner_is_shared_without_a_note() -> None:
    plan = _plan(
        """
        DEFAULT_LIMIT = 200


        class Alpha:
            pass


        class Beta:
            pass
        """
    )
    assert "DEFAULT_LIMIT = 200" in plan.files["_shared.py"]
    assert "from ._shared import DEFAULT_LIMIT" in plan.files["__init__.py"]
    assert plan.notes == ()


def test_a_global_rebinding_keeps_the_memo_with_the_function() -> None:
    plan = _plan(
        """
        _MEMO = None


        class Alpha:
            pass


        class Beta:
            pass


        def memoized() -> object:
            global _MEMO
            if _MEMO is None:
                _MEMO = object()
            return _MEMO
        """
    )
    # `global` cannot reach a name in another module, so splitting these apart would stop the
    # rebinding from taking effect — silently, with no import error to catch it.
    assert "_MEMO = None" in plan.files["_functions.py"]
    assert "_shared.py" not in plan.files
    assert any("_MEMO" in note for note in plan.notes)


def test_file_relative_paths_are_refused() -> None:
    with pytest.raises(SplitError, match="__file__"):
        _plan(
            """
            from pathlib import Path

            _TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


            class Alpha:
                pass


            class Beta:
                pass
            """
        )


def test_star_imports_are_refused() -> None:
    with pytest.raises(SplitError, match="star import"):
        _plan(
            """
            from os.path import *


            class Alpha:
                pass


            class Beta:
                pass
            """
        )


def test_a_computed_dunder_all_is_refused() -> None:
    with pytest.raises(SplitError, match="computed"):
        _plan(
            """
            class Alpha:
                pass


            class Beta:
                pass


            __all__ = [Alpha.__name__, Beta.__name__]
            """
        )


def test_a_module_level_compound_statement_is_refused() -> None:
    with pytest.raises(SplitError, match="unsupported module-level"):
        _plan(
            """
            try:
                import tomllib
            except ImportError:
                tomllib = None


            class Alpha:
                pass


            class Beta:
                pass
            """
        )


def test_a_single_class_module_is_refused() -> None:
    with pytest.raises(SplitError, match="nothing to split"):
        _plan(
            """
            class Alpha:
                pass


            def helper() -> None:
                pass
            """
        )


def test_two_classes_mapping_to_one_filename_are_refused() -> None:
    with pytest.raises(SplitError, match="both map to"):
        _plan(
            """
            class HTTPError:
                pass


            class HttpError:
                pass
            """
        )


def test_file_relative_paths_split_once_their_depth_is_corrected() -> None:
    source = textwrap.dedent(
        """
        from pathlib import Path

        _TEMPLATES = Path(__file__).resolve().parent.parent.parent / "templates"


        class Alpha:
            pass


        class Beta:
            pass
        """
    ).lstrip("\n")
    plan = plan_split(source, allow_file_paths=True)
    assert "_TEMPLATES" in plan.files["_shared.py"]


def test_a_field_sharing_a_siblings_name_is_not_read_as_a_reference() -> None:
    # `Coverage` in bajutsu/analysis/coverage.py declares a `coverage: float` field alongside a
    # module-level `coverage()` function. Reading that binding as a reference imports the function
    # into the class's file and closes a cycle with `_functions.py`, which fails at import time.
    plan = _plan(
        """
        from __future__ import annotations

        from dataclasses import dataclass


        @dataclass
        class Alpha:
            value: float


        @dataclass
        class Beta:
            value: float


        def value() -> float:
            return Alpha(value=1.0).value
        """
    )
    assert "from ._functions import value" not in plan.files["alpha.py"]
    assert plan.notes == ()


def test_a_runtime_cycle_between_split_files_is_reported() -> None:
    plan = _plan(
        """
        class Alpha:
            def make(self) -> object:
                return Beta()


        class Beta:
            def make(self) -> object:
                return Alpha()
        """
    )
    assert any("circular import" in note for note in plan.notes)


def test_a_tuple_unpacking_assignment_binds_every_one_of_its_names() -> None:
    # `_EV_SYN, _EV_KEY, _EV_ABS = 0, 1, 3` in bajutsu/common/backend_cli/adb.py. Reading only the
    # tuple as a whole leaves all three invisible, so nothing imports them and the split file fails
    # ruff's F821 on names it still reads.
    plan = _plan(
        """
        _FIRST, _SECOND = 1, 2


        class Alpha:
            def total(self) -> int:
                return _FIRST


        class Beta:
            def total(self) -> int:
                return _SECOND
        """
    )
    assert "_FIRST, _SECOND = 1, 2" in plan.files["_shared.py"]
    assert "from ._shared import _FIRST" in plan.files["alpha.py"]
    assert "from ._shared import _SECOND" in plan.files["beta.py"]
    assert "from ._shared import _FIRST as _FIRST" in plan.files["__init__.py"]


def test_a_pep_695_type_parameter_bound_reads_names_too() -> None:
    # `def _wedge_guard[F: Callable[..., Any]](method: F) -> F` in drivers/playwright.py. Skipping
    # the bound leaves `Callable` unimported, and the split file fails ruff's F821 on it.
    plan = _plan(
        """
        from collections.abc import Callable
        from typing import Any


        class Alpha:
            pass


        class Beta:
            pass


        def guard[F: Callable[..., Any]](method: F) -> F:
            return method
        """
    )
    assert "from collections.abc import Callable" in plan.files["_functions.py"]


def test_a_quoted_forward_reference_in_a_type_alias_is_read_as_a_name() -> None:
    # `BlockedHandler = Callable[[base.Driver], "AlertEvent | None"]` in orchestrator/types.py. The
    # quote sits in a plain subscript, not an annotation, so reading only annotations leaves
    # `AlertEvent` unimported and the split file fails ruff's F821 on it.
    plan = _plan(
        """
        from __future__ import annotations

        from collections.abc import Callable

        Handler = Callable[[int], "Alpha | None"]


        class Alpha:
            pass


        class Beta:
            pass
        """
    )
    assert "from .alpha import Alpha" in plan.files["_shared.py"]


def test_an_entry_point_guard_becomes_the_packages_dunder_main() -> None:
    # `python -m pkg` runs `__main__.py`, never `__init__.py`, so leaving the guard behind would
    # take the entry point out silently — `bajutsu.common.provisioning.provision` is invoked that
    # way by scripts/install.sh and by the web-e2e job.
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass


        def main() -> int:
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )
    main = plan.files["__main__.py"]
    assert "from . import main" in main
    assert 'if __name__ == "__main__":' in main
    assert "__main__" not in plan.files["__init__.py"]


def test_module_level_code_derived_from_its_owner_follows_it() -> None:
    # `_ASSERTION_KINDS = tuple(f for f in Assertion.model_fields …)` in scenario/models/assertions.py.
    # It belongs in `Assertion`'s own file by rule 4, but above the class it raises NameError on
    # import rather than failing anything statically.
    plan = _plan(
        """
        class Alpha:
            def fields(self) -> tuple[str, ...]:
                return _FIELDS


        _FIELDS = tuple(Alpha.__annotations__)


        class Beta:
            pass
        """
    )
    alpha = plan.files["alpha.py"]
    assert alpha.index("class Alpha:") < alpha.index("_FIELDS = ")


def test_module_level_code_read_by_its_neighbour_stays_beside_it() -> None:
    # `oplog.py`'s `_CONTEXT_KEYS` is built from the context variables declared beside it. Counting
    # only classes and functions as owners sends the two to different files, which then import each
    # other — a cycle no rule-5 in-method import can break, since both run at module load.
    plan = _plan(
        """
        _FIRST = 1
        _SECOND = (_FIRST, 2)


        class Alpha:
            def read(self) -> tuple[int, int]:
                return _SECOND


        class Beta:
            pass


        def helper() -> int:
            return _FIRST
        """
    )
    # `_FIRST` has a second reader in `_SECOND`, so it lands in `_shared.py` rather than following
    # `helper` — which keeps `_shared.py` a leaf, importing nothing that imports it back.
    assert "_FIRST = 1" in plan.files["_shared.py"]
    assert "from ." not in plan.files["_shared.py"]
    assert "_SECOND = (_FIRST, 2)" in plan.files["alpha.py"]
