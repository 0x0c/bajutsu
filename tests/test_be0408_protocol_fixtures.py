"""Pin BE-0408's draft device-executor protocol against its own OpenAPI 3.1 schemas.

`roadmaps/BE-0408-step-latency-device-executor-protocol/protocol/device-executor.openapi.yaml` is
the single source of truth both a future iOS (BE-0409) and Android (BE-0410) implementation must
carry identical JSON schemas from. This module is the structural half of that contract's
enforcement: it validates the request/response fixtures at `tests/fixtures/be0408/protocol/`
against the document's own `components/schemas`, the same `jsonschema.validate` idiom
`bajutsu/common/assertions/schema.py` already uses for the `responseSchema` assertion kind. The
semantic half — whether a selector resolves to the *same element* — is
`tests/test_selector_fixtures.py`; a JSON Schema check cannot express that question.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import jsonschema
import pytest
import yaml
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

_PROTOCOL_DOC_PATH = (
    Path(__file__).parent.parent
    / "roadmaps"
    / "BE-0408-step-latency-device-executor-protocol"
    / "protocol"
    / "device-executor.openapi.yaml"
)
_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "be0408" / "protocol"
_SUPPORTED_FIXTURE_SCHEMA = 1
_DOC_URI = "urn:be0408-device-executor-protocol"

# operation name -> (request schema, reply schema), per the document's own naming convention.
_OPERATION_SCHEMAS = {
    "wait": ("WaitRequest", "WaitReply"),
    "assert": ("AssertRequest", "AssertReply"),
    "scenario": ("ScenarioRequest", "ScenarioReply"),
}


def _load_protocol_doc() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(_PROTOCOL_DOC_PATH.read_text(encoding="utf-8")))


def _walk_refs(node: object) -> list[str]:
    """Every `$ref` string anywhere in the document, in `paths` and `components` alike."""
    refs: list[str] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
        for value in node.values():
            refs.extend(_walk_refs(value))
    elif isinstance(node, list):
        for item in node:
            refs.extend(_walk_refs(item))
    return refs


def _resolve_local_pointer(doc: dict[str, Any], pointer: str) -> object:
    """Resolve a `#/a/b/c` JSON pointer against `doc`, raising `KeyError` on a broken one."""
    if not pointer.startswith("#/"):
        raise ValueError(f"only local pointers are supported, got {pointer!r}")
    node: object = doc
    for part in pointer[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"{pointer!r} does not resolve: {part!r} missing")
        node = node[part]
    return node


def _validator_for(doc: dict[str, Any], schema_name: str) -> jsonschema.protocols.Validator:
    """A Draft 2020-12 validator for one named `components/schemas` entry, `$ref`s resolved.

    OpenAPI 3.1's `components/schemas` are plain JSON Schema (2020-12), unlike 3.0. Handing a
    bare sub-dict straight to `Draft202012Validator` does not resolve its internal `$ref`s (they
    have no base document to resolve against), so the whole document is registered as one
    resource and the target schema is reached through a wrapper `$ref` into that resource —
    `jsonschema`/`referencing`'s documented way to validate against one schema in a multi-schema
    document.
    """
    resource = Resource.from_contents(doc, default_specification=DRAFT202012)
    registry = Registry().with_resource(uri=_DOC_URI, resource=resource)
    wrapper = {"$ref": f"{_DOC_URI}#/components/schemas/{schema_name}"}
    return jsonschema.Draft202012Validator(wrapper, registry=registry)


def _load_fixture(path: Path) -> dict[str, Any]:
    data = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if data["schema"] != _SUPPORTED_FIXTURE_SCHEMA:
        raise ValueError(f"{path.name}: unsupported fixture schema {data['schema']!r}")
    if data["operation"] not in _OPERATION_SCHEMAS:
        raise ValueError(f"{path.name}: unknown operation {data['operation']!r}")
    return data


_PROTOCOL_DOC = _load_protocol_doc()
_FIXTURE_FILES = sorted(_FIXTURES_DIR.glob("*.json"))


def test_every_ref_in_the_document_resolves() -> None:
    """A renamed or mistyped `$ref` anywhere in `paths` or `components` fails here, not silently."""
    for ref in _walk_refs(_PROTOCOL_DOC):
        _resolve_local_pointer(_PROTOCOL_DOC, ref)


def test_every_schema_is_referenced_from_somewhere() -> None:
    """An orphaned `components/schemas` entry — dead weight nothing in the document points to."""
    referenced = {
        ref.rsplit("/", 1)[-1]
        for ref in _walk_refs(_PROTOCOL_DOC)
        if ref.startswith("#/components/schemas/")
    }
    all_schemas = set(_PROTOCOL_DOC["components"]["schemas"])
    assert all_schemas <= referenced, f"orphaned schema(s): {all_schemas - referenced}"


@pytest.mark.parametrize("path", _FIXTURE_FILES, ids=[p.stem for p in _FIXTURE_FILES])
def test_protocol_fixture_matches_its_schema(path: Path) -> None:
    fixture = _load_fixture(path)
    request_schema, reply_schema = _OPERATION_SCHEMAS[fixture["operation"]]
    _validator_for(_PROTOCOL_DOC, request_schema).validate(fixture["request"])
    _validator_for(_PROTOCOL_DOC, reply_schema).validate(fixture["response"])


@pytest.mark.parametrize(
    "path",
    [p for p in _FIXTURE_FILES if _load_fixture(p)["operation"] == "wait"],
    ids=lambda p: p.stem,
)
def test_wait_trace_only_present_on_a_for_mode_timeout(path: Path) -> None:
    """`trace` mirrors `WaitTrace`, which today is populated only on the `for` branch."""
    fixture = _load_fixture(path)
    response = fixture["response"]
    request = fixture["request"]
    expect_trace = request["mode"] == "for" and response["status"] == "timeout"
    assert ("trace" in response) == expect_trace


def test_wait_request_rejects_a_missing_required_field() -> None:
    validator = _validator_for(_PROTOCOL_DOC, "WaitRequest")
    instance = {"mode": "for", "selector": {"id": "x"}, "timeoutMs": 1000}  # no pollBudgetMs
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)


def test_wait_request_selector_is_optional_for_screen_changed_and_settled() -> None:
    validator = _validator_for(_PROTOCOL_DOC, "WaitRequest")
    for mode in ("screenChanged", "settled"):
        validator.validate({"mode": mode, "timeoutMs": 1000, "pollBudgetMs": 500})
        with pytest.raises(jsonschema.ValidationError):
            # a selector is meaningless here — screenChanged/settled evaluate the whole tree.
            validator.validate(
                {"mode": mode, "timeoutMs": 1000, "pollBudgetMs": 500, "selector": {"id": "x"}}
            )


def test_wait_request_requires_a_selector_for_for_and_gone() -> None:
    validator = _validator_for(_PROTOCOL_DOC, "WaitRequest")
    for mode in ("for", "gone"):
        validator.validate(
            {"mode": mode, "timeoutMs": 1000, "pollBudgetMs": 500, "selector": {"id": "x"}}
        )
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({"mode": mode, "timeoutMs": 1000, "pollBudgetMs": 500})


def test_element_omits_absent_optional_fields_rather_than_nulling_them() -> None:
    """The wire convention (also pinned on the existing iOS Element schema): omit, never null."""
    validator = _validator_for(_PROTOCOL_DOC, "Element")
    minimal: dict[str, Any] = {"traits": [], "frame": [0.0, 0.0, 1.0, 1.0], "handle": "h"}
    validator.validate(minimal)
    with_null = copy.deepcopy(minimal)
    with_null["identifier"] = None
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(with_null)


def test_element_handle_is_optional_android_has_no_equivalent() -> None:
    """Android's own `Element` model mints no handle; requiring one would be an XCUITest-only obligation."""
    validator = _validator_for(_PROTOCOL_DOC, "Element")
    validator.validate({"traits": ["button"], "frame": [0.0, 0.0, 1.0, 1.0]})


def test_selector_rejects_an_unrecognized_field() -> None:
    """A misspelled key (a plausible hand-written-org.json typo) must fail loudly, not widen silently."""
    validator = _validator_for(_PROTOCOL_DOC, "Selector")
    validator.validate({"labelMatches": "Save"})
    with pytest.raises(jsonschema.ValidationError):
        # a typo of labelMatches — the correctly-spelled field is simply absent, matching nothing
        validator.validate({"labelmatches": "Save"})


def test_scenario_step_tap_payload_uses_a_selector_not_a_handle() -> None:
    """`ScenarioTapRequest` deliberately diverges from the standalone `TapRequest` shape."""
    validator = _validator_for(_PROTOCOL_DOC, "ScenarioTapRequest")
    validator.validate({"selector": {"id": "settings.open"}})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"handle": "h1"})  # the standalone shape, not this document's own


def test_scenario_step_payload_is_validated_at_the_bundle_level() -> None:
    """`ScenarioStep.payload`'s shape is tied to `kind`, not left unconstrained.

    Checked through `ScenarioStep` itself (not `ScenarioTapRequest` in isolation): a bundled
    step's payload must be rejected exactly as strictly as the same request would be standalone.
    """
    validator = _validator_for(_PROTOCOL_DOC, "ScenarioStep")
    validator.validate({"kind": "tap", "payload": {"selector": {"id": "x"}}})
    validator.validate({"kind": "type", "payload": {"text": "hello"}})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"kind": "tap", "payload": {"handle": "h1"}})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"kind": "wait", "payload": {"nonsense": 1}})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"kind": "tap", "payload": "not-an-object"})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"kind": "type", "payload": {}})  # `text` is required


def test_assert_request_forbids_more_than_one_comparison_field() -> None:
    """`AssertRequest`'s "exactly one comparison field" rule is enforced structurally."""
    validator = _validator_for(_PROTOCOL_DOC, "AssertRequest")
    validator.validate({"kind": "count", "selector": {"id": "x"}, "equals": 3})
    with pytest.raises(jsonschema.ValidationError):
        # equals and atLeast both set — count allows exactly one.
        validator.validate({"kind": "count", "selector": {"id": "x"}, "equals": 3, "atLeast": 1})
    with pytest.raises(jsonschema.ValidationError):
        # value/label requires exactly one comparison field; none given here.
        validator.validate({"kind": "value", "selector": {"id": "x"}})
    with pytest.raises(jsonschema.ValidationError):
        # exists takes no comparison field at all.
        validator.validate({"kind": "exists", "selector": {"id": "x"}, "equals": "a"})


def test_assert_request_equals_type_matches_its_kind() -> None:
    """`equals` is a string for value/label and an integer for count — never the other way."""
    validator = _validator_for(_PROTOCOL_DOC, "AssertRequest")
    validator.validate({"kind": "value", "selector": {"id": "x"}, "equals": "a"})
    validator.validate({"kind": "count", "selector": {"id": "x"}, "equals": 3})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"kind": "count", "selector": {"id": "x"}, "equals": "three"})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"kind": "value", "selector": {"id": "x"}, "equals": 7})
