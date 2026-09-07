"""Golden element-tree comparison for BE-0006.

Compares a recorded golden (expected normalized Element dicts) against a live
query() result, field by field: exact on identity/state fields, set-equal on
traits, and tolerant (sanity only) on frame geometry.
"""

from ._functions import _DIAGNOSTIC_FIELDS as _DIAGNOSTIC_FIELDS
from ._functions import _ELEMENT_FIELDS as _ELEMENT_FIELDS
from ._functions import _validate_element as _validate_element
from ._functions import (
    assert_golden_tree,
    compare_element,
    compare_golden,
    frame_is_sane,
    load_golden,
    save_golden,
)
from .field_mismatch import FieldMismatch
from .golden_result import GoldenResult

__all__ = [
    "FieldMismatch",
    "GoldenResult",
    "assert_golden_tree",
    "compare_element",
    "compare_golden",
    "frame_is_sane",
    "load_golden",
    "save_golden",
]
