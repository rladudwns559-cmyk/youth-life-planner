"""합성 review 결과의 닫힌 상태 공간. 실제 matching이나 지문 비교를 실행하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from enum import Enum
from itertools import combinations
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.policy_data import (
    ImplementationReviewMatch, InventoryReviewMatch, ReviewMatchStatus, ReviewMissingReason, ReviewStaleReason,
)
from backend.policy_engine.policy_data import coverage_review_match as domain


S = ReviewMatchStatus
M = ReviewMissingReason
T = ReviewStaleReason
MODELS = (InventoryReviewMatch, ImplementationReviewMatch)
IDENTITY = {"condition_id": "SYNTH_CONDITION_A", "rule_root_id": "SYNTH_RULE_A"}
STALE_SUBSETS = tuple(subset for size in range(1, 5) for subset in combinations(tuple(T), size))


def payload(model, **changes):
    result = dict(review_ref="SYNTH_REVIEW_001", status=S.MATCHED, stale_reasons=(), missing_reasons=())
    if model is ImplementationReviewMatch:
        result.update(IDENTITY)
    result.update(changes)
    return result


VALID = (
    (InventoryReviewMatch, {}),
    (InventoryReviewMatch, dict(status=S.MISSING, missing_reasons=(M.NO_REVIEW_CONTEXT,))),
    (InventoryReviewMatch, dict(review_ref=None, status=S.MISSING, missing_reasons=(M.INVENTORY_REVIEW_NOT_DECLARED,))),
    (InventoryReviewMatch, dict(review_ref=None, status=S.MISSING,
                               missing_reasons=(M.NO_REVIEW_CONTEXT, M.INVENTORY_REVIEW_NOT_DECLARED))),
    *((InventoryReviewMatch, dict(status=S.STALE, stale_reasons=reasons)) for reasons in (
        (T.INVENTORY_VERSION_CHANGED,), (T.DATASET_VERSION_CHANGED,),
        (T.INVENTORY_VERSION_CHANGED, T.DATASET_VERSION_CHANGED),
    )),
    (ImplementationReviewMatch, {}),
    (ImplementationReviewMatch, dict(status=S.MISSING, missing_reasons=(M.NO_REVIEW_CONTEXT,))),
    *((ImplementationReviewMatch, dict(status=S.STALE, stale_reasons=reasons)) for reasons in STALE_SUBSETS),
)


@pytest.mark.parametrize("model,changes", VALID)
def test_all_valid_outcomes_and_canonical_stale_subsets(model, changes):
    values = payload(model, **changes)
    result = model(**values)
    assert result == model(**values)
    assert result.stale_reasons is values["stale_reasons"]
    assert result.missing_reasons is values["missing_reasons"]
    expected = {
        "review_ref": values["review_ref"], "status": values["status"].value,
        "stale_reasons": [reason.value for reason in values["stale_reasons"]],
        "missing_reasons": [reason.value for reason in values["missing_reasons"]],
    }
    if model is ImplementationReviewMatch:
        expected = {**IDENTITY, **expected}
    first, second = result.to_dict(), result.to_dict()
    assert first == second == expected and first is not second
    assert first["stale_reasons"] is not second["stale_reasons"]
    assert first["missing_reasons"] is not second["missing_reasons"]
    assert json.loads(json.dumps(first)) == expected
    first["status"] = "SYNTH-CHANGED"
    first["stale_reasons"].append("CHANGED")
    first["missing_reasons"].clear()
    assert result.to_dict() == second


def test_enum_members_are_exact_minimal_names_and_canonical_order():
    assert [(r.name, r.value) for r in S] == [(name, name) for name in ("MATCHED", "MISSING", "STALE")]
    assert [(r.name, r.value) for r in M] == [(name, name) for name in (
        "NO_REVIEW_CONTEXT", "INVENTORY_REVIEW_NOT_DECLARED",
    )]
    assert [(r.name, r.value) for r in T] == [(name, name) for name in (
        "INVENTORY_VERSION_CHANGED", "RULE_VERSION_CHANGED", "DATASET_VERSION_CHANGED", "IMPLEMENTATION_CHANGED",
    )]
    assert len(S.__members__) == 3 and len(M.__members__) == 2 and len(T.__members__) == 4
    for enum_type in (S, M, T):
        with pytest.raises(ValueError):
            enum_type("SYNTH-UNKNOWN")


class OtherStatus(str, Enum):
    MATCHED = "MATCHED"


class TextSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("bad", ["MATCHED", "matched", "ERROR", None, True, 1, OtherStatus.MATCHED])
def test_status_requires_exact_enum_member(model, bad):
    with pytest.raises(PolicyDataError, match="status"):
        model(**payload(model, status=bad))


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("name", ["stale_reasons", "missing_reasons"])
@pytest.mark.parametrize("bad", [None, [], {}, set(), "", iter(()), TupleSubclass()])
def test_reason_collection_requires_exact_tuple_without_coercion(model, name, bad):
    with pytest.raises(PolicyDataError, match=name):
        model(**payload(model, **{name: bad}))


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("name,bad", [
    ("stale_reasons", "INVENTORY_VERSION_CHANGED"), ("stale_reasons", M.NO_REVIEW_CONTEXT),
    ("stale_reasons", S.STALE), ("stale_reasons", None), ("stale_reasons", True),
    ("missing_reasons", "NO_REVIEW_CONTEXT"), ("missing_reasons", T.INVENTORY_VERSION_CHANGED),
    ("missing_reasons", S.MISSING), ("missing_reasons", None), ("missing_reasons", True),
])
def test_reason_elements_require_exact_correct_enum(model, name, bad):
    with pytest.raises(PolicyDataError, match=name):
        model(**payload(model, **{name: (bad,)}))


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("reasons", [
    (T.DATASET_VERSION_CHANGED, T.INVENTORY_VERSION_CHANGED),
    (T.DATASET_VERSION_CHANGED, T.RULE_VERSION_CHANGED),
    (T.IMPLEMENTATION_CHANGED, T.DATASET_VERSION_CHANGED),
    (T.INVENTORY_VERSION_CHANGED, T.INVENTORY_VERSION_CHANGED),
    (T.RULE_VERSION_CHANGED, T.RULE_VERSION_CHANGED),
])
def test_stale_reasons_reject_wrong_order_or_duplicates_without_normalization(model, reasons):
    with pytest.raises(PolicyDataError, match="canonical"):
        model(**payload(model, status=S.STALE, stale_reasons=reasons))


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("reasons", [
    (M.INVENTORY_REVIEW_NOT_DECLARED, M.NO_REVIEW_CONTEXT),
    (M.NO_REVIEW_CONTEXT, M.NO_REVIEW_CONTEXT),
    (M.INVENTORY_REVIEW_NOT_DECLARED, M.INVENTORY_REVIEW_NOT_DECLARED),
])
def test_missing_reasons_reject_wrong_order_or_duplicates(model, reasons):
    with pytest.raises(PolicyDataError, match="canonical"):
        model(**payload(model, status=S.MISSING, missing_reasons=reasons))


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("changes", [
    dict(status=S.MATCHED, stale_reasons=(T.INVENTORY_VERSION_CHANGED,)),
    dict(status=S.MATCHED, missing_reasons=(M.NO_REVIEW_CONTEXT,)),
    dict(status=S.MATCHED, review_ref=None),
    dict(status=S.STALE),
    dict(status=S.STALE, review_ref=None, stale_reasons=(T.INVENTORY_VERSION_CHANGED,)),
    dict(status=S.STALE, stale_reasons=(T.INVENTORY_VERSION_CHANGED,), missing_reasons=(M.NO_REVIEW_CONTEXT,)),
    dict(status=S.MISSING),
    dict(status=S.MISSING, stale_reasons=(T.INVENTORY_VERSION_CHANGED,), missing_reasons=(M.NO_REVIEW_CONTEXT,)),
])
def test_status_reason_combinations_are_closed(model, changes):
    with pytest.raises(PolicyDataError):
        model(**payload(model, **changes))


@pytest.mark.parametrize("reasons", [
    (T.RULE_VERSION_CHANGED,), (T.IMPLEMENTATION_CHANGED,),
    (T.INVENTORY_VERSION_CHANGED, T.RULE_VERSION_CHANGED),
])
def test_inventory_stale_cannot_use_implementation_specific_reasons(reasons):
    with pytest.raises(PolicyDataError, match="Inventory"):
        InventoryReviewMatch(**payload(InventoryReviewMatch, status=S.STALE, stale_reasons=reasons))


@pytest.mark.parametrize("ref,reasons", [
    (None, (M.NO_REVIEW_CONTEXT,)),
    ("SYNTH-REF", (M.INVENTORY_REVIEW_NOT_DECLARED,)),
    ("SYNTH-REF", (M.NO_REVIEW_CONTEXT, M.INVENTORY_REVIEW_NOT_DECLARED)),
])
def test_inventory_missing_ref_and_reasons_must_be_consistent(ref, reasons):
    with pytest.raises(PolicyDataError):
        InventoryReviewMatch(**payload(InventoryReviewMatch, review_ref=ref, status=S.MISSING, missing_reasons=reasons))


@pytest.mark.parametrize("reasons", [
    (M.INVENTORY_REVIEW_NOT_DECLARED,), (M.NO_REVIEW_CONTEXT, M.INVENTORY_REVIEW_NOT_DECLARED),
])
def test_implementation_missing_only_allows_no_context(reasons):
    with pytest.raises(PolicyDataError, match="Implementation"):
        ImplementationReviewMatch(**payload(ImplementationReviewMatch, status=S.MISSING, missing_reasons=reasons))


def test_implementation_missing_still_requires_explicit_review_ref():
    with pytest.raises(PolicyDataError, match="review_ref"):
        ImplementationReviewMatch(**payload(ImplementationReviewMatch, review_ref=None, status=S.MISSING,
                                             missing_reasons=(M.NO_REVIEW_CONTEXT,)))


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("bad", ["", " \t\n", 1, True, [], TextSubclass("SYNTH-REF")])
def test_review_ref_exact_text_without_coercion(model, bad):
    with pytest.raises(PolicyDataError, match="review_ref"):
        model(**payload(model, review_ref=bad))


@pytest.mark.parametrize("model", MODELS)
def test_review_ref_retains_padding_and_need_not_exist(model):
    ref = " \tSYNTH://nonexistent/review\n"
    result = model(**payload(model, review_ref=ref))
    assert result.review_ref == ref and result.to_dict()["review_ref"] == ref


@pytest.mark.parametrize("bad", ["", " ", "synth", "SYNTH-A", " SYNTH", None, 1, True, TextSubclass("SYNTH")])
def test_implementation_condition_id_uses_binding_contract(bad):
    with pytest.raises(PolicyDataError, match="condition_id"):
        ImplementationReviewMatch(**payload(ImplementationReviewMatch, condition_id=bad))


@pytest.mark.parametrize("bad", ["", " ", None, 1, True, [], TextSubclass("SYNTH_ROOT")])
def test_implementation_root_requires_exact_nonblank_text(bad):
    with pytest.raises(PolicyDataError, match="rule_root_id"):
        ImplementationReviewMatch(**payload(ImplementationReviewMatch, rule_root_id=bad))


def test_implementation_root_retains_padding_without_lookup():
    root = " SYNTH nonexistent root "
    result = ImplementationReviewMatch(**payload(ImplementationReviewMatch, rule_root_id=root))
    assert result.rule_root_id == root and result.to_dict()["rule_root_id"] == root


@pytest.mark.parametrize("model", MODELS)
def test_fields_are_explicit_required_frozen_and_part_of_value_equality(model):
    original = model(**payload(model))
    expected = ("review_ref", "status", "stale_reasons", "missing_reasons")
    if model is ImplementationReviewMatch:
        expected = ("condition_id", "rule_root_id", *expected)
    assert tuple(f.name for f in fields(model)) == expected
    assert tuple(original.to_dict()) == expected
    assert not hasattr(original, "__dict__")
    for name in expected:
        values = payload(model)
        del values[name]
        with pytest.raises(TypeError):
            model(**values)
        with pytest.raises(FrozenInstanceError):
            setattr(original, name, None)
        with pytest.raises(FrozenInstanceError):
            delattr(original, name)
    assert original != replace(original, review_ref="SYNTH-OTHER-REF")
    stale = model(**payload(model, status=S.STALE, stale_reasons=(T.INVENTORY_VERSION_CHANGED,)))
    assert stale != original
    assert stale != replace(stale, stale_reasons=(T.DATASET_VERSION_CHANGED,))
    missing = model(**payload(model, status=S.MISSING, missing_reasons=(M.NO_REVIEW_CONTEXT,)))
    assert missing != original
    if model is InventoryReviewMatch:
        undeclared = model(None, S.MISSING, (), (M.INVENTORY_REVIEW_NOT_DECLARED,))
        assert undeclared != replace(undeclared, missing_reasons=(M.NO_REVIEW_CONTEXT, M.INVENTORY_REVIEW_NOT_DECLARED))
    else:
        assert original != replace(original, condition_id="SYNTH_OTHER")
        assert original != replace(original, rule_root_id="SYNTH_OTHER")


@pytest.mark.parametrize("model", MODELS)
def test_no_fingerprints_records_coverage_or_candidate_singular_field(model):
    result = model(**payload(model))
    for name in ("missing_reason", "inventory", "binding", "review", "review_context", "policy", "coverage",
                 "expected_fingerprint", "current_fingerprint", "reviewed_at", "coverage_status", "is_full",
                 "verification_status", "acceptance_status", "policy_evaluation", "cashflow"):
        assert not hasattr(result, name)
        with pytest.raises(TypeError):
            model(**payload(model, **{name: None}))


def test_result_construction_and_serialization_have_no_hash_lookup_or_io(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("결과 값 처리에서 지문 계산·lookup·외부 조회를 수행했습니다")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("hashlib.sha256", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    for model, changes in VALID:
        result = model(**payload(model, **changes))
        assert result.to_dict()["status"] == result.status.value


def test_errors_use_existing_hierarchy_without_raw_payload():
    private = "private-invalid-condition-payload"
    with pytest.raises(PolicyDataError) as caught:
        ImplementationReviewMatch(**payload(ImplementationReviewMatch, condition_id=private))
    assert isinstance(caught.value, EngineValidationError)
    assert private not in str(caught.value)


def test_direct_dependencies_are_only_value_validation():
    tree = ast.parse(inspect.getsource(domain))
    assert {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} == {"dataclasses", "enum", "errors"}
    assert {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} == {"re"}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"Policy", "EligibilityCoverage", "ConditionBinding", "InventoryCompletenessReview",
                        "ImplementationBindingReview", "CoverageReviewContext", "hashlib", "date", "datetime",
                        "PolicyEvaluation", "CashflowInput", "CoverageResult"}
    assert {n.name for n in tree.body if isinstance(n, ast.ClassDef)} == {
        "ReviewMatchStatus", "ReviewMissingReason", "ReviewStaleReason", "InventoryReviewMatch", "ImplementationReviewMatch",
    }
    assert all(n.name.startswith("_") for n in tree.body if isinstance(n, ast.FunctionDef))
