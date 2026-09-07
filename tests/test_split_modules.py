"""Tests for the one-class-per-file splitting script (BE-0411).

The script rewrites 86 modules holding 459 classes between them, so a rule it applies wrongly is a
defect repeated hundreds of times. Each of the item's five split rules is pinned here against a
small fixture module, together with the refusals that keep a file needing human judgment — a
`__file__`-relative path, a star import, a computed `__all__` — from being split silently.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from scripts.split_modules import (
    SplitError,
    SplitPlan,
    apply_split,
    main,
    plan_split,
    snake_case,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


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
    # And the package must not re-export it: `from ._functions import _MEMO` copies the value once,
    # freezing the package attribute at `None` while the real binding moves on.
    assert "_MEMO" not in plan.files["__init__.py"]


def test_a_sibling_reading_a_global_rebound_name_is_refused() -> None:
    with pytest.raises(SplitError, match="rebinds with `global`"):
        _plan(
            """
            _MEMO = None


            class Alpha:
                def peek(self) -> object:
                    return _MEMO


            class Beta:
                pass


            def memoized() -> object:
                global _MEMO
                _MEMO = object()
                return _MEMO
            """
        )


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
    with pytest.raises(SplitError, match="not a plain list of string literals"):
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


def test_a_runtime_cycle_between_split_files_is_refused() -> None:
    # Written to disk it would be a package that cannot import at all, so the split stops here and
    # rule 5's in-method import is applied to the source first.
    with pytest.raises(SplitError, match=re.escape("circular import alpha -> beta -> alpha.py")):
        _plan(
            """
            class Alpha:
                def make(self) -> object:
                    return Beta()


            class Beta:
                def make(self) -> object:
                    return Alpha()
            """
        )


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


def test_a_name_an_inner_import_binds_is_not_read_as_a_reference() -> None:
    # `SqlRepository` imports its ORM models inside the methods that use them — rule 5's treatment,
    # applied before this split. Counting those as reads keeps the module-level `TYPE_CHECKING`
    # import alive in the split file with nothing left annotating it, which fails F401.
    plan = _plan(
        """
        from __future__ import annotations

        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from other.place import Model


        class Alpha:
            def make(self) -> object:
                from other.place import Model

                return Model()


        class Beta:
            pass
        """
    )
    alpha = plan.files["alpha.py"]
    assert alpha.count("from other.place import Model") == 1
    assert "if TYPE_CHECKING:" not in alpha


def test_a_comment_inside_a_type_checking_block_survives_the_filter() -> None:
    # The block is rebuilt to drop the imports a split file no longer reads, and rebuilding it
    # naively takes the note explaining the deferral with it — the one thing this item chose
    # `libcst` over `ast` to keep.
    plan = _plan(
        """
        from __future__ import annotations

        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            # Imported for typing only: importing it at run time would cycle.
            from other.place import Model
            from other.place import Unused


        class Alpha:
            value: Model


        class Beta:
            pass
        """
    )
    alpha = plan.files["alpha.py"]
    assert "# Imported for typing only" in alpha
    assert "Unused" not in alpha


def test_a_literal_value_is_not_read_as_a_forward_reference() -> None:
    # `Literal["Beta"]`'s string is a value, not a type. Parsing it as a forward reference imports a
    # sibling the file never uses, and two such strings can close a cycle out of nothing.
    plan = _plan(
        """
        from __future__ import annotations

        from typing import Literal


        class Alpha:
            kind: Literal["Beta"] = "Beta"


        class Beta:
            kind: Literal["Alpha"] = "Alpha"
        """
    )
    assert "from .beta import Beta" not in plan.files["alpha.py"]
    assert "from .alpha import Alpha" not in plan.files["beta.py"]
    assert plan.notes == ()


def test_a_class_never_leaks_into_a_siblings_file() -> None:
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass
        """
    )
    assert "class Beta" not in plan.files["alpha.py"]
    assert "class Alpha" not in plan.files["beta.py"]


def test_a_deferred_block_brings_its_type_checking_import_with_it() -> None:
    # Without the injected import the generated file raises NameError at package import time, which
    # is as far from the deferral as a failure can land.
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
    assert "from typing import TYPE_CHECKING" in plan.files["alpha.py"]


def test_a_three_file_cycle_is_broken_on_its_annotation_only_edge() -> None:
    plan = _plan(
        """
        from __future__ import annotations


        class Alpha:
            def make(self) -> object:
                return Beta()


        class Beta:
            def make(self) -> object:
                return Gamma()


        class Gamma:
            def take(self, value: Alpha) -> None:
                pass
        """
    )
    # Only Gamma reads its neighbour from an annotation, so only Gamma's import may be deferred.
    assert "if TYPE_CHECKING:" in plan.files["gamma.py"]
    assert "if TYPE_CHECKING:" not in plan.files["alpha.py"]
    assert "if TYPE_CHECKING:" not in plan.files["beta.py"]
    assert plan.notes == ()


def test_an_edge_carrying_a_runtime_name_is_reported_rather_than_deferred() -> None:
    # Deferring an edge that carries a runtime read would emit a `TYPE_CHECKING` import for a name
    # the file calls, turning a load-time cycle into a NameError at the call site instead.
    with pytest.raises(SplitError, match="no annotation-only edge to defer"):
        _plan(
            """
            from __future__ import annotations


            class Alpha:
                def take(self, value: Beta) -> object:
                    return Beta()


            class Beta:
                def make(self) -> object:
                    return Alpha()
            """
        )


def test_a_module_level_import_survives_a_method_that_re_imports_an_annotated_name() -> None:
    plan = _plan(
        """
        from __future__ import annotations

        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from other.place import Model


        class Alpha:
            def make(self) -> Model:
                from other.place import Model

                return Model()


        class Beta:
            pass
        """
    )
    # The annotation still reads the name outside the method, so the deferred import has to stay.
    alpha = plan.files["alpha.py"]
    assert "if TYPE_CHECKING:" in alpha
    assert alpha.count("from other.place import Model") == 2


def test_a_type_checking_block_holding_more_than_imports_is_refused() -> None:
    with pytest.raises(SplitError, match="more than plain imports"):
        _plan(
            """
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                class Proto:
                    pass


            class Alpha:
                pass


            class Beta:
                pass
            """
        )


def test_a_semicolon_joined_import_line_is_refused() -> None:
    # Splitting it would keep the first import and drop the second, silently.
    with pytest.raises(SplitError, match="`;`-joined import"):
        _plan(
            """
            import os; import json


            class Alpha:
                pass


            class Beta:
                pass
            """
        )


@pytest.mark.parametrize("name", ["_Shared", "_Functions"])
def test_a_class_colliding_with_a_generated_module_is_refused(name: str) -> None:
    # Without the refusal the class overwrites the generated file, taking the module-level code or
    # the top-level functions that landed there with it.
    with pytest.raises(SplitError, match="would collide with"):
        _plan(
            f"""
            class Alpha:
                pass


            class {name}:
                pass
            """
        )


def test_a_file_relative_path_inside_a_class_body_is_refused() -> None:
    # `_check_splittable` scans the declarations as well as the module-level statements; only the
    # module-level arm had a test.
    with pytest.raises(SplitError, match="__file__"):
        _plan(
            """
            from pathlib import Path


            class Alpha:
                def where(self) -> Path:
                    return Path(__file__).resolve().parent


            class Beta:
                pass
            """
        )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("A", "a"),
        ("HTTP2Client", "http2_client"),
        # `iskeyword` runs on the underscored stem, so a private `_If` needs no trailing underscore.
        ("_If", "_if"),
    ],
)
def test_snake_case_edge_cases(name: str, expected: str) -> None:
    assert snake_case(name) == expected


def test_import_aliases_bind_the_name_python_binds() -> None:
    plan = _plan(
        """
        import json as j
        import os.path


        class Alpha:
            def dump(self) -> str:
                return j.dumps({})


        class Beta:
            def join(self) -> str:
                return os.path.join("a", "b")
        """
    )
    assert "import json as j" in plan.files["alpha.py"]
    assert "import os.path" not in plan.files["alpha.py"]
    assert "import os.path" in plan.files["beta.py"]
    assert "import json as j" not in plan.files["beta.py"]


def test_a_name_inside_dunder_all_keeps_the_plain_import_form() -> None:
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
    assert "from .alpha import Alpha\n" in init
    assert "from .beta import Beta as Beta" in init


# --- the contract itself: the generated package imports, and ruff accepts it ----------------------
# Every assertion above is a proxy for these two properties. Asserting them directly is what catches
# a missing `TYPE_CHECKING` import, a statement emitted above the class that reads it, an
# over-pruned import, or a re-export ruff reads as dead.

_END_TO_END = {
    "plain": """
        from __future__ import annotations

        import json
        from dataclasses import dataclass

        DEFAULT = 3


        @dataclass
        class Base:
            name: str


        class Child(Base):
            def dump(self) -> str:
                return json.dumps({"n": self.name, "d": DEFAULT})


        def make() -> Child:
            return Child(name="x")
    """,
    "deferred_cycle": """
        from __future__ import annotations


        class Alpha:
            def take(self, value: Beta) -> None:
                pass


        class Beta:
            def make(self) -> object:
                return Alpha()
    """,
    "entry_point": """
        class Alpha:
            pass


        class Beta:
            pass


        def main() -> int:
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
    """,
}


def _write_package(root: Path, name: str, source: str) -> Path:
    package = root / name
    package.mkdir()
    for filename, text in _plan(source).files.items():
        (package / filename).write_text(text)
    # `check=True`: a formatter failure means the plan emitted source ruff cannot parse, and
    # swallowing it would leave these tests asserting against text no generated file ever holds.
    subprocess.run(["uv", "run", "ruff", "format", "-q", str(package)], check=True, cwd=_REPO_ROOT)
    return package


@pytest.mark.parametrize("shape", sorted(_END_TO_END))
def test_the_generated_package_imports_cleanly(shape: str, tmp_path: Path) -> None:
    package = _write_package(tmp_path, f"pkg_{shape}", _END_TO_END[shape])
    proc = subprocess.run(
        [sys.executable, "-c", f"import pkg_{shape}"],
        cwd=package.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("shape", sorted(_END_TO_END))
def test_the_generated_package_passes_ruffs_import_rules(shape: str, tmp_path: Path) -> None:
    package = _write_package(tmp_path, f"pkg_{shape}", _END_TO_END[shape])
    proc = subprocess.run(
        ["uv", "run", "ruff", "check", "--select", "F401,F811,F821", str(package)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout


# --- the command line ----------------------------------------------------------------------------


def _module(root: Path, name: str, source: str) -> Path:
    path = root / f"{name}.py"
    path.write_text(textwrap.dedent(source).lstrip("\n"))
    return path


def test_a_dry_run_writes_nothing_and_deletes_nothing(tmp_path: Path) -> None:
    # `apply_split` unlinks the source once the package is written, so an inverted `--dry-run`
    # branch would destroy a module on a run the operator believed was a preview.
    path = _module(tmp_path, "sample", _END_TO_END["plain"])
    assert main([str(path), "--dry-run"]) == 0
    assert path.exists()
    assert not (tmp_path / "sample").exists()


def test_a_refused_file_reports_itself_and_does_not_stop_the_batch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    refused = _module(
        tmp_path,
        "refused",
        """
        from os.path import *


        class Alpha:
            pass


        class Beta:
            pass
        """,
    )
    ok = _module(tmp_path, "ok", _END_TO_END["plain"])
    assert main([str(refused), str(ok), "--dry-run"]) == 1
    stderr = capsys.readouterr().err
    assert "REFUSED" in stderr
    assert "1 of 2 module(s) refused" in stderr
    assert refused.exists()


def test_the_escape_hatch_is_what_lets_a_file_relative_module_split(tmp_path: Path) -> None:
    source = """
        from pathlib import Path

        _ROOT = Path(__file__).resolve().parent.parent


        class Alpha:
            pass


        class Beta:
            pass
    """
    assert main([str(_module(tmp_path, "refused", source)), "--dry-run"]) == 1
    assert main([str(_module(tmp_path, "allowed", source)), "--dry-run", "--allow-file-paths"]) == 0


def test_a_module_that_cannot_be_parsed_is_refused_like_any_other(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # `cst.ParserSyntaxError` and `OSError` are not `SplitError`, and left uncaught they abandoned
    # the batch mid-way — after a success line had already been printed for the failing file.
    broken = tmp_path / "broken.py"
    broken.write_text("class Alpha:\n    def (\n")
    assert main([str(broken), str(tmp_path / "absent.py")]) == 1
    stderr = capsys.readouterr().err
    assert stderr.count("REFUSED") == 2
    assert broken.exists()


def test_an_entry_point_guard_keeps_the_imports_it_reads() -> None:
    # `sys.exit(main())` needs `sys` as much as it needs `main`, and `__main__.py` is the one file
    # nothing in the deterministic gate imports — so a missing import surfaces only in production.
    plan = _plan(
        """
        import sys


        class Alpha:
            pass


        class Beta:
            pass


        def main() -> int:
            return 0


        if __name__ == "__main__":
            sys.exit(main())
        """
    )
    entry = plan.files["__main__.py"]
    assert "import sys" in entry
    assert "from . import main" in entry


def test_an_inverted_type_checking_guard_is_not_treated_as_one() -> None:
    # `if not TYPE_CHECKING:` holds a runtime shim. Hoisting it into a real type-checking block
    # would reverse its meaning, with nothing raised.
    with pytest.raises(SplitError, match="unsupported module-level"):
        _plan(
            """
            from typing import TYPE_CHECKING

            if not TYPE_CHECKING:
                Shim = dict


            class Alpha:
                pass


            class Beta:
                pass
            """
        )


def test_a_type_checking_block_with_a_runtime_else_is_refused() -> None:
    # The `else` branch is the runtime half; parsing only the `if` body drops it silently.
    with pytest.raises(SplitError, match="`else`"):
        _plan(
            """
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from collections import OrderedDict
            else:
                OrderedDict = dict


            class Alpha:
                pass


            class Beta:
                pass
            """
        )


def test_a_dunder_all_naming_an_imported_name_is_refused() -> None:
    # `__init__.py` re-exports what the module defined, so such a name would be listed with nothing
    # importing it — ruff's F822, discovered only after the batch had written the package.
    with pytest.raises(SplitError, match="imports rather than defines"):
        _plan(
            """
            from other.place import Helper


            class Alpha:
                pass


            class Beta:
                pass


            __all__ = ["Alpha", "Beta", "Helper"]
            """
        )


def test_a_global_rebinding_inside_a_class_method_is_refused() -> None:
    # Rule 2 sends the binding to `_functions.py`, which a method's `global` cannot reach — the
    # rebinding would write the class's own module instead, and the memo never propagates.
    with pytest.raises(SplitError, match="rebinds _MEMO with `global`"):
        _plan(
            """
            _MEMO = None


            class Alpha:
                def load(self) -> object:
                    global _MEMO
                    _MEMO = object()
                    return _MEMO


            class Beta:
                pass
            """
        )


def test_a_sibling_a_method_already_imports_does_not_come_back() -> None:
    # A rule-5 in-method import, applied by hand before the split. Reading it as a module-level
    # reference restores the very cycle the human had broken.
    plan = _plan(
        """
        from __future__ import annotations


        class Engine:
            def build(self) -> object:
                from .widget import Widget

                return Widget(self)


        class Widget:
            def __init__(self, engine: Engine) -> None:
                self.engine = engine
        """
    )
    engine = plan.files["engine.py"]
    assert engine.count("from .widget import Widget") == 1
    assert "if TYPE_CHECKING:" not in engine
    assert plan.notes == ()


def test_a_trailing_statement_keeps_the_imports_it_reads() -> None:
    plan = _plan(
        """
        import atexit


        class Alpha:
            pass


        class Beta:
            pass


        def _cleanup() -> None:
            pass


        atexit.register(_cleanup)
        """
    )
    init = plan.files["__init__.py"]
    assert "import atexit" in init
    assert init.index("import atexit") < init.index("__all__")
    assert init.index("__all__") < init.index("atexit.register(_cleanup)")


def test_a_local_import_satisfies_only_the_scope_that_makes_it() -> None:
    # A method importing `json` for itself says nothing about a module-level statement in the same
    # generated file. Suppressing the header import for both leaves `_DEFAULTS` reading a name
    # nothing binds — a NameError at package import, past the compile check.
    plan = _plan(
        """
        import json

        _DEFAULTS = json.loads("{}")


        class Alpha:
            def dump(self) -> str:
                import json

                return json.dumps(_DEFAULTS)


        class Beta:
            pass
        """
    )
    assert "import json" in plan.files["alpha.py"]


def test_a_local_import_does_not_hide_a_siblings_own_read() -> None:
    plan = _plan(
        """
        from __future__ import annotations


        class Engine:
            def build(self) -> object:
                from .widget import Widget

                return Widget()

            def default(self) -> object:
                return _DEFAULT


        _DEFAULT = Widget


        class Widget:
            pass
        """
    )
    # `_DEFAULT` is read at module level, where the method's own import cannot reach it.
    engine = plan.files["engine.py"]
    assert "from .widget import Widget" in engine


def test_a_public_name_rebound_with_global_is_refused() -> None:
    # Re-exporting it freezes a copy, and dropping it takes a public name off the package's
    # surface — with ruff's F822 silent inside `__init__.py`, nothing downstream would say so.
    with pytest.raises(SplitError, match="public and rebound"):
        _plan(
            """
            MEMO = None


            class Alpha:
                pass


            class Beta:
                pass


            def load() -> object:
                global MEMO
                MEMO = object()
                return MEMO
            """
        )


def test_a_trailing_statement_reading_a_rebound_name_is_refused() -> None:
    with pytest.raises(SplitError, match="rebinds with `global`"):
        _plan(
            """
            import atexit

            _MEMO = None


            class Alpha:
                pass


            class Beta:
                pass


            def load() -> object:
                global _MEMO
                _MEMO = object()
                return _MEMO


            atexit.register(lambda: _MEMO)
            """
        )


def test_deferring_a_cycle_needs_string_annotations() -> None:
    # Without the future import the annotation is evaluated eagerly, so the deferred name is
    # undefined at class-definition time — a NameError the deferral itself would have caused.
    with pytest.raises(SplitError, match="evaluates eagerly"):
        _plan(
            """
            class Alpha:
                def take(self, value: "Beta") -> None:
                    pass


            class Beta:
                def make(self) -> object:
                    return Alpha()
            """
        )


def test_a_semicolon_joined_import_inside_a_type_checking_block_is_refused() -> None:
    with pytest.raises(SplitError, match="`;`-joined import"):
        _plan(
            """
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from a.b import One; from a.b import Two


            class Alpha:
                value: One


            class Beta:
                value: Two
            """
        )


def test_a_real_run_replaces_the_module_with_a_package_that_imports(tmp_path: Path) -> None:
    # The only test that takes the write path: `apply_split` compiles each file and then unlinks
    # the original, and `_tidy` formats what it wrote. Every other `main` case refuses first.
    path = _module(tmp_path, "sample", _END_TO_END["plain"])
    assert main([str(path)]) == 0
    assert not path.exists()
    package = tmp_path / "sample"
    assert (package / "__init__.py").exists()
    proc = subprocess.run(
        [sys.executable, "-c", "import sample"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    formatted = subprocess.run(
        ["uv", "run", "ruff", "format", "--check", str(package)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert formatted.returncode == 0, formatted.stdout


def _header_imports(source: str) -> set[str]:
    """The plain `import x` names a generated file binds at module level."""
    return {
        alias.name
        for node in ast.parse(source).body
        if isinstance(node, ast.Import)
        for alias in node.names
    }


@pytest.mark.parametrize(
    ("body", "needed"),
    [
        # A nested function's own import satisfies only itself; the outer read still needs the
        # header import.
        (
            """
            def outer(self) -> str:
                def inner() -> str:
                    import json

                    return json.dumps({})

                return inner() + json.dumps({})
            """,
            True,
        ),
        # A lambda, a comprehension and a class body inside the method all read through the
        # method's own frame, so the method's import satisfies them.
        (
            """
            def run(self) -> str:
                import json

                return (lambda: json.dumps({}))()
            """,
            False,
        ),
        (
            """
            def run(self) -> list[str]:
                import json

                return [json.dumps(x) for x in ()]
            """,
            False,
        ),
        (
            """
            def build(self) -> type:
                import json

                class Inner:
                    payload = json.dumps({})

                return Inner
            """,
            False,
        ),
        # A sibling method that makes no import of its own keeps the header import alive.
        (
            """
            def a(self) -> str:
                import json

                return json.dumps({})

            def b(self) -> str:
                return json.dumps({})
            """,
            True,
        ),
    ],
)
def test_a_local_import_satisfies_exactly_its_own_scope(body: str, needed: bool) -> None:
    plan = _plan(
        f"""
        import json


        class Alpha:
{textwrap.indent(textwrap.dedent(body).strip(), " " * 12)}


        class Beta:
            pass
        """
    )
    assert ("json" in _header_imports(plan.files["alpha.py"])) is needed


def test_an_annotation_is_never_satisfied_by_a_local_import() -> None:
    # The annotation is evaluated where the `def` is, so the method's own import cannot serve it.
    plan = _plan(
        """
        from __future__ import annotations

        import json


        class Alpha:
            def decode(self, value: json.JSONDecoder) -> None:
                import json

                json.dumps({})


        class Beta:
            pass
        """
    )
    assert "json" in _header_imports(plan.files["alpha.py"])


def test_a_runtime_subscript_is_not_read_as_annotation_only() -> None:
    # `table[Beta.KEY]` reads `Beta` where the expression runs. Classing it annotation-only lets
    # the cycle breaker defer the import, and the name is then undefined at the moment it is used —
    # past the compile check, past ruff, and past an `import` of the package.
    with pytest.raises(SplitError, match="no annotation-only edge to defer"):
        _plan(
            """
            from __future__ import annotations


            class Alpha:
                def pick(self, table: dict[int, str]) -> str:
                    return table[Beta.KEY]


            class Beta:
                KEY = 1

                def make(self) -> object:
                    return Alpha()
            """
        )


def test_a_literal_holding_an_enum_member_still_reads_its_name() -> None:
    plan = _plan(
        """
        from __future__ import annotations

        from typing import Literal


        class Colour:
            RED = "red"


        class Alpha:
            kind: Literal[Colour.RED]


        class Beta:
            pass
        """
    )
    assert "from .colour import Colour" in plan.files["alpha.py"]


def test_an_inverted_entry_point_guard_is_not_treated_as_one() -> None:
    # Its body runs on every import. Moved into `__main__.py` the condition is never true again,
    # so the statement stops running with nothing raised.
    with pytest.raises(SplitError, match="unsupported module-level"):
        _plan(
            """
            class Alpha:
                pass


            class Beta:
                pass


            if not (__name__ == "__main__"):
                _REGISTERED = True
            """
        )


def test_an_annotated_dunder_all_of_plain_literals_is_carried_across() -> None:
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass


        __all__: list[str] = ["Alpha"]
        """
    )
    assert '__all__ = ["Alpha"]' in plan.files["__init__.py"]
    assert "from .beta import Beta as Beta" in plan.files["__init__.py"]


def test_a_generated_file_that_will_not_compile_costs_no_original(tmp_path: Path) -> None:
    # The original is the only copy of what the split rewrote, and the half-written package must
    # not block the retry either.
    path = _module(tmp_path, "sample", _END_TO_END["plain"])
    plan = SplitPlan(files={"__init__.py": "", "alpha.py": "class Alpha(\n"}, notes=())
    with pytest.raises(SplitError, match="does not parse"):
        apply_split(path, plan)
    assert path.exists()
    assert not (tmp_path / "sample").exists()


def test_a_lookalike_import_does_not_pass_for_type_checking() -> None:
    # Decided from the alias, not from the rendered line: `IS_TYPE_CHECKING` contains the string.
    plan = _plan(
        """
        from __future__ import annotations

        from other.place import IS_TYPE_CHECKING


        class Alpha:
            flag = IS_TYPE_CHECKING

            def take(self, value: Beta) -> None:
                pass


        class Beta:
            def make(self) -> object:
                return Alpha()
        """
    )
    alpha = plan.files["alpha.py"]
    assert "from typing import TYPE_CHECKING" in alpha


@pytest.mark.parametrize(
    "signature",
    [
        "def take(self, values: list[Beta]) -> None: ...",
        "def all(self) -> dict[str, Beta]: ...",
    ],
)
def test_an_annotation_only_cycle_inside_a_subscript_is_still_deferrable(signature: str) -> None:
    # The subscript rule reads elements at the subscript's own context, but an annotation still
    # wraps the whole thing — so a cycle carried by `list[Beta]` breaks without a hand-written
    # in-method import, exactly as one carried by a bare `Beta` does.
    plan = _plan(
        f"""
        from __future__ import annotations


        class Alpha:
            {signature}


        class Beta:
            def make(self) -> object:
                return Alpha()
        """
    )
    assert "if TYPE_CHECKING:" in plan.files["alpha.py"]
    assert plan.notes == ()


def test_a_single_quoted_entry_point_guard_is_recognized() -> None:
    # The structural match accepts it; the substring test it replaced did not.
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass


        def main() -> int:
            return 0


        if __name__ == '__main__':
            raise SystemExit(main())
        """
    )
    assert "__main__.py" in plan.files


def test_an_annotated_but_computed_dunder_all_is_still_refused() -> None:
    with pytest.raises(SplitError, match="not a plain list of string literals"):
        _plan(
            """
            class Alpha:
                pass


            class Beta:
                pass


            __all__: list[str] = [Alpha.__name__]
            """
        )


def test_a_name_only_a_global_binds_needs_no_refusal() -> None:
    # It was never a module-level binding, so the package never carried it and the split takes
    # nothing away — refusing here would block a module that splits correctly.
    plan = _plan(
        """
        class Alpha:
            pass


        class Beta:
            pass


        def configure() -> None:
            global RUNTIME

            RUNTIME = object()
        """
    )
    assert "RUNTIME" not in plan.files["__init__.py"]
    assert plan.notes == ()
