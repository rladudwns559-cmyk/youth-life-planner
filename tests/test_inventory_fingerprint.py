"""합성 Inventory의 고정 지문 계약. GV01~GV06 기대값은 명세의 literal이다."""

import ast
from dataclasses import replace
import inspect
import json
import re
import unicodedata

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionInventory, ConditionRequirement, RequiredCondition,
    fingerprint_condition_inventory,
)
from backend.policy_engine.policy_data import coverage_fingerprint as domain


GOLDEN = (
    ("GV01", "{\"conditions\":[{\"condition_id\":\"COND_A\",\"evidence_refs\":[\"SYNTH-SRC#a\",\"SYNTH-SRC#b\"],\"meaning\":\"소득 조건\",\"requirement\":\"REQUIRED\"}],\"fingerprint_schema\":\"coverage-inventory-1.0\",\"inventory_version\":\"i0001\",\"policy_id\":\"SYNTH-POLICY\",\"scope\":{\"edition_id\":\"2026\",\"quarter\":3}}", 282, "abf20d120e93265b5b2e85851707d255693f833ee2dbdab8cd5741115fdf572a"),
    ("GV02", "{\"conditions\":[{\"condition_id\":\"COND_A\",\"evidence_refs\":[\"SYNTH-SRC#a\",\"SYNTH-SRC#b\"],\"meaning\":\"소득 조건\",\"requirement\":\"REQUIRED\"},{\"condition_id\":\"COND_B\",\"evidence_refs\":[\"SYNTH-SRC#c\"],\"meaning\":\"학생 조건\",\"requirement\":\"CONDITIONAL\"}],\"fingerprint_schema\":\"coverage-inventory-1.0\",\"inventory_version\":\"i0001\",\"policy_id\":\"SYNTH-POLICY\",\"scope\":{\"edition_id\":\"2026\",\"quarter\":3}}", 394, "3d0d97fc12200929459413e8bee59d9126a47749e34826a520529c80c6269946"),
    ("GV03", "{\"conditions\":[{\"condition_id\":\"COND_A\",\"evidence_refs\":[\"SYNTH-SRC#a\",\"SYNTH-SRC#b\"],\"meaning\":\"소득 조건\",\"requirement\":\"REQUIRED\"},{\"condition_id\":\"COND_B\",\"evidence_refs\":[\"SYNTH-SRC#c\"],\"meaning\":\"학생 조건\",\"requirement\":\"CONDITIONAL\"}],\"fingerprint_schema\":\"coverage-inventory-1.0\",\"inventory_version\":\"i0001\",\"policy_id\":\"SYNTH-POLICY\",\"scope\":{\"edition_id\":\"2026\",\"quarter\":3}}", 394, "3d0d97fc12200929459413e8bee59d9126a47749e34826a520529c80c6269946"),
    ("GV04", "{\"conditions\":[{\"condition_id\":\"COND_A\",\"evidence_refs\":[\"SYNTH-SRC#a\",\"SYNTH-SRC#b\"],\"meaning\":\"변경된 소득 조건\",\"requirement\":\"REQUIRED\"}],\"fingerprint_schema\":\"coverage-inventory-1.0\",\"inventory_version\":\"i0001\",\"policy_id\":\"SYNTH-POLICY\",\"scope\":{\"edition_id\":\"2026\",\"quarter\":3}}", 292, "36ccede8c75d342508a07e73109d71dd74cda11486e7672a8aa4a30daef69f42"),
    ("GV05", "{\"conditions\":[{\"condition_id\":\"COND_A\",\"evidence_refs\":[\"SYNTH-SRC#a\",\"SYNTH-SRC#b\",\"SYNTH-SRC#c\"],\"meaning\":\"소득 조건\",\"requirement\":\"REQUIRED\"}],\"fingerprint_schema\":\"coverage-inventory-1.0\",\"inventory_version\":\"i0001\",\"policy_id\":\"SYNTH-POLICY\",\"scope\":{\"edition_id\":\"2026\",\"quarter\":3}}", 296, "1e1e90ee0677437b84a0dc20ab23615a1ca98754f049dcbe7a2dafddb2f3e170"),
    ("GV06", "{\"conditions\":[{\"condition_id\":\"COND_A\",\"evidence_refs\":[\"SYNTH-SRC#b\",\"SYNTH-SRC#a\"],\"meaning\":\"소득 조건\",\"requirement\":\"REQUIRED\"}],\"fingerprint_schema\":\"coverage-inventory-1.0\",\"inventory_version\":\"i0001\",\"policy_id\":\"SYNTH-POLICY\",\"scope\":{\"edition_id\":\"2026\",\"quarter\":3}}", 282, "da0e87aea7d09b34afc088b1682de6b2ebd87939bf54c6249846512969f40344"),
)


def condition_a(**changes):
    payload = dict(condition_id="COND_A", meaning="소득 조건", requirement=ConditionRequirement.REQUIRED,
                   evidence_refs=("SYNTH-SRC#a", "SYNTH-SRC#b"))
    payload.update(changes)
    return RequiredCondition(**payload)


def condition_b():
    return RequiredCondition("COND_B", "학생 조건", ConditionRequirement.CONDITIONAL, ("SYNTH-SRC#c",))


def inventory(conditions=None, **changes):
    payload = dict(policy_id="SYNTH-POLICY", scope=ApplicabilityScope("2026", 3),
                   inventory_version="i0001", conditions=(condition_a(),) if conditions is None else conditions)
    payload.update(changes)
    return ConditionInventory(**payload)


def vector_inventory(vector_id):
    if vector_id == "GV02":
        return inventory((condition_b(), condition_a()))
    if vector_id == "GV03":
        return inventory((condition_a(), condition_b()))
    if vector_id == "GV04":
        return inventory((condition_a(meaning="변경된 소득 조건"),))
    if vector_id == "GV05":
        return inventory((condition_a(evidence_refs=("SYNTH-SRC#a", "SYNTH-SRC#b", "SYNTH-SRC#c")),))
    if vector_id == "GV06":
        return inventory((condition_a(evidence_refs=("SYNTH-SRC#b", "SYNTH-SRC#a")),))
    assert vector_id == "GV01"
    return inventory()


@pytest.mark.parametrize("vector_id,expected_json,expected_length,expected_hash", GOLDEN, ids=[v[0] for v in GOLDEN])
def test_document_golden_payload_json_utf8_length_and_literal_digest(
    vector_id, expected_json, expected_length, expected_hash, monkeypatch,
):
    value = vector_inventory(vector_id)
    before = value.to_dict()
    payload = domain._build_inventory_payload(value)
    assert payload == json.loads(expected_json)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    assert canonical == expected_json
    seen = []
    real_sha256 = domain.hashlib.sha256
    def spy_sha256(data):
        seen.append(data)
        return real_sha256(data)
    monkeypatch.setattr(domain.hashlib, "sha256", spy_sha256)
    assert fingerprint_condition_inventory(value) == expected_hash
    assert seen == [expected_json.encode("utf-8")]
    assert len(seen[0]) == expected_length
    assert not seen[0].startswith(b"\xef\xbb\xbf") and not seen[0].endswith(b"\n")
    assert value.to_dict() == before


def test_condition_order_is_canonical_but_model_serialization_order_stays_unchanged():
    first = inventory((condition_b(), condition_a()))
    second = inventory((condition_a(), condition_b()))
    assert first != second and first.to_dict() != second.to_dict()
    assert fingerprint_condition_inventory(first) == fingerprint_condition_inventory(second) == GOLDEN[1][3]
    assert [c.condition_id for c in first.conditions] == ["COND_B", "COND_A"]


def test_ascii_id_sort_is_not_numeric_or_locale_sort():
    values = tuple(condition_a(condition_id=name) for name in ("COND_2", "COND_10", "COND_A", "COND_1"))
    original = inventory(values)
    assert [c["condition_id"] for c in domain._build_inventory_payload(original)["conditions"]] == [
        "COND_1", "COND_10", "COND_2", "COND_A",
    ]
    assert original.conditions is values


@pytest.mark.parametrize("changes", [
    {"meaning": "변경된 소득 조건"},
    {"requirement": ConditionRequirement.CONDITIONAL},
    {"evidence_refs": ("SYNTH-SRC#a", "SYNTH-SRC#b", "SYNTH-SRC#c")},
    {"evidence_refs": ("SYNTH-SRC#b", "SYNTH-SRC#a")},
    {"evidence_refs": ("SYNTH-SRC#a", "SYNTH-SRC#a", "SYNTH-SRC#b")},
    {"condition_id": "COND_OTHER"},
])
def test_each_condition_semantic_field_changes_digest(changes):
    assert fingerprint_condition_inventory(inventory((condition_a(**changes),))) != GOLDEN[0][3]


def test_duplicate_evidence_is_preserved_without_dedupe():
    refs = ("SYNTH-SRC#a", "SYNTH-SRC#a")
    value = inventory((condition_a(evidence_refs=refs),))
    assert domain._build_inventory_payload(value)["conditions"][0]["evidence_refs"] == list(refs)
    assert fingerprint_condition_inventory(value) != fingerprint_condition_inventory(
        inventory((condition_a(evidence_refs=("SYNTH-SRC#a",)),))
    )


@pytest.mark.parametrize("ref", [None, "SYNTH-REVIEW-X", " SYNTH-REVIEW-Y "])
def test_completeness_review_ref_is_excluded(ref):
    value = inventory(completeness_review_ref=ref)
    assert fingerprint_condition_inventory(value) == GOLDEN[0][3]
    assert "completeness_review_ref" not in domain._build_inventory_payload(value)


@pytest.mark.parametrize("changes", [
    {"inventory_version": "i0002"},
    {"scope": ApplicabilityScope("2026", 4)},
    {"scope": ApplicabilityScope("2026", None)},
    {"scope": ApplicabilityScope("2027", 3)},
    {"policy_id": "SYNTH-OTHER-POLICY"},
])
def test_version_scope_and_policy_identity_change_digest(changes):
    assert fingerprint_condition_inventory(inventory(**changes)) != GOLDEN[0][3]


def test_annual_scope_keeps_null_in_payload():
    payload = domain._build_inventory_payload(inventory(scope=ApplicabilityScope("2026", None)))
    assert payload["scope"] == {"edition_id": "2026", "quarter": None}
    assert '"quarter":null' in json.dumps(payload, separators=(",", ":"))


@pytest.mark.parametrize("meaning", [" 소득 조건 ", "소득\n조건", "소득\t조건"])
def test_meaning_whitespace_is_not_stripped_or_replaced(meaning):
    value = inventory((condition_a(meaning=meaning),))
    assert domain._build_inventory_payload(value)["conditions"][0]["meaning"] == meaning
    assert fingerprint_condition_inventory(value) != GOLDEN[0][3]


def test_unicode_normalization_is_not_applied():
    nfc = "소득 조건"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfd != nfc
    assert fingerprint_condition_inventory(inventory((condition_a(meaning=nfd),))) != GOLDEN[0][3]
    assert domain._build_inventory_payload(inventory((condition_a(meaning=nfd),)))["conditions"][0]["meaning"] == nfd


class InventorySubclass(ConditionInventory):
    pass


class FakeInventory:
    def to_dict(self):
        pytest.fail("raw 객체 serializer를 호출했습니다")


@pytest.mark.parametrize("bad", [None, {}, [], (), "", 1, True, FakeInventory()])
def test_wrong_input_exact_type_is_rejected(bad):
    with pytest.raises(PolicyDataError, match="inventory"):
        fingerprint_condition_inventory(bad)


def test_inventory_subclass_is_rejected():
    value = inventory()
    subclass = InventorySubclass(value.policy_id, value.scope, value.inventory_version, value.conditions)
    with pytest.raises(PolicyDataError):
        fingerprint_condition_inventory(subclass)


def test_api_is_one_required_argument_without_optional_semantics():
    signature = inspect.signature(fingerprint_condition_inventory)
    assert list(signature.parameters) == ["inventory"]
    assert signature.parameters["inventory"].default is inspect.Parameter.empty
    for extra in ("schema_version", "sort_conditions", "include_reviews"):
        with pytest.raises(TypeError):
            fingerprint_condition_inventory(inventory(), **{extra: True})


def test_canonical_encoding_configuration_is_fixed(monkeypatch):
    calls = []
    real_dumps = domain.json.dumps
    def spy_dumps(payload, **kwargs):
        calls.append(kwargs)
        return real_dumps(payload, **kwargs)
    monkeypatch.setattr(domain.json, "dumps", spy_dumps)
    assert fingerprint_condition_inventory(inventory()) == GOLDEN[0][3]
    assert calls == [dict(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)]


def test_invalid_unicode_is_explicit_data_error_without_payload_leak():
    private = "SYNTH-private-" + chr(0xD800)
    value = inventory((condition_a(meaning=private),))
    with pytest.raises(PolicyDataError) as caught:
        fingerprint_condition_inventory(value)
    assert "SYNTH-private-" not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_json_encoding_failure_never_returns_placeholder(error_type, monkeypatch):
    value = inventory()
    def fail(*args, **kwargs):
        raise error_type("SYNTH-private-invalid-payload")
    monkeypatch.setattr(domain.json, "dumps", fail)
    with pytest.raises(PolicyDataError) as caught:
        fingerprint_condition_inventory(value)
    assert "SYNTH-private" not in str(caught.value)


def test_system_failures_are_not_hidden_as_validation_errors(monkeypatch):
    value = inventory()
    def fail(*args, **kwargs):
        raise MemoryError
    monkeypatch.setattr(domain.json, "dumps", fail)
    with pytest.raises(MemoryError):
        fingerprint_condition_inventory(value)


def test_repeated_calculation_is_stable_and_does_not_mutate_inputs():
    value = inventory((condition_b(), condition_a()), completeness_review_ref="SYNTH-REVIEW")
    conditions, scope = value.conditions, value.scope
    before = value.to_dict()
    result = fingerprint_condition_inventory(value)
    assert re.fullmatch(r"[0-9a-f]{64}", result)
    for _ in range(100):
        assert fingerprint_condition_inventory(value) == result
        assert value.to_dict() == before
    assert value.conditions is conditions and value.scope is scope


def test_private_payload_is_a_new_independent_projection():
    value = inventory()
    first, second = domain._build_inventory_payload(value), domain._build_inventory_payload(value)
    first["scope"]["quarter"] = None
    first["conditions"][0]["meaning"] = "changed"
    first["conditions"][0]["evidence_refs"].clear()
    assert domain._build_inventory_payload(value) == second


def test_no_model_serializer_revalidation_or_external_io_is_used(monkeypatch):
    value = inventory()
    def forbidden(*args, **kwargs):
        pytest.fail("지문 계산에서 serializer/하위 재검증/외부 조회를 호출했습니다")
    for model in (ConditionInventory, RequiredCondition, ApplicabilityScope):
        monkeypatch.setattr(model, "to_dict", forbidden)
        monkeypatch.setattr(model, "__post_init__", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("os.getenv", forbidden)
    assert fingerprint_condition_inventory(value) == GOLDEN[0][3]


def test_direct_dependencies_and_exports_do_not_include_future_features():
    tree = ast.parse(inspect.getsource(domain))
    assert {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} == {"errors", "condition_inventory", "models"}
    assert {alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names} == {"hashlib", "json"}
    assert {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")} == {
        "fingerprint_condition_inventory",
        "fingerprint_policy_tree",
        "fingerprint_rule_subtree",
    }
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"UserProfile", "BirthFact", "ResidentRegistrationFact",
                        "PolicyEvaluation", "CashflowInput", "InventoryCompletenessReview", "CoverageReviewContext"}
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr in {"today", "now", "getenv", "exists"} for n in ast.walk(tree))
    assert callable(domain.fingerprint_policy_tree)
    assert callable(domain.fingerprint_rule_subtree)

