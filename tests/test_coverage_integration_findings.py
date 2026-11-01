"""계산 없이 합성 facts를 보존하는 두 private findings 값 모델의 계약."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import json

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import coverage_integration_findings as domain
from backend.policy_engine.policy_data.coverage_integration_findings import (
    _CoverageIntegrationFindings as CoverageFindings,
    _ImplementationIntegrationFinding as BindingFinding,
)
from backend.policy_engine.policy_data.coverage_review_match import (
    ImplementationReviewMatch, InventoryReviewMatch, ReviewMatchStatus, ReviewMissingReason, ReviewStaleReason,
)


SHA_A, SHA_B, SHA_C = "a" * 64, "b" * 64, "c" * 64


def implementation_match(condition_id="COND_A", root_id="ROOT_A", status=ReviewMatchStatus.MATCHED):
    stale = (ReviewStaleReason.RULE_VERSION_CHANGED,) if status is ReviewMatchStatus.STALE else ()
    missing = (ReviewMissingReason.NO_REVIEW_CONTEXT,) if status is ReviewMatchStatus.MISSING else ()
    return ImplementationReviewMatch(condition_id, root_id, "SYNTH-IMPL-REVIEW", status, stale, missing)


def inventory_match(status=ReviewMatchStatus.MATCHED, declared=True):
    ref = "SYNTH-INVENTORY-REVIEW" if declared else None
    stale = (ReviewStaleReason.INVENTORY_VERSION_CHANGED,) if status is ReviewMatchStatus.STALE else ()
    missing = ()
    if status is ReviewMatchStatus.MISSING:
        missing = (ReviewMissingReason.NO_REVIEW_CONTEXT if declared else ReviewMissingReason.INVENTORY_REVIEW_NOT_DECLARED,)
    return InventoryReviewMatch(ref, status, stale, missing)


def binding(condition_id="COND_A", root_id="ROOT_A", status=ReviewMatchStatus.MATCHED, fingerprint=SHA_C):
    return BindingFinding(fingerprint, implementation_match(condition_id, root_id, status))


def facts(**overrides):
    values = {
        "missing_condition_ids": (),
        "unmapped_rule_ids": (),
        "composition_gap_group_ids": (),
        "inventory_fingerprint": SHA_A,
        "policy_tree_fingerprint": SHA_B,
        "inventory_review_match": inventory_match(),
        "implementation_findings": (binding(),),
    }
    values.update(overrides)
    return CoverageFindings(**values)


class StringSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class InventoryMatchSubclass(InventoryReviewMatch):
    pass


class ImplementationMatchSubclass(ImplementationReviewMatch):
    pass


class BindingFindingSubclass(BindingFinding):
    pass


class FakeMatch:
    @property
    def condition_id(self):
        pytest.fail("정확한 하위 값 타입 확인 전에 ID를 읽었습니다")


BAD_HASHES = [None, 1, True, b"a" * 64, [], {}, "", "a" * 63, "a" * 65, "A" * 64, "g" * 64,
              "0x" + "a" * 62, " " + "a" * 63, "a" * 63 + "\n", "ａ" * 64, StringSubclass(SHA_A)]


@pytest.mark.parametrize("status", list(ReviewMatchStatus))
def test_binding_accepts_all_normal_review_states_and_preserves_original_match(status):
    match = implementation_match(status=status)
    result = BindingFinding(SHA_C, match)
    assert result.review_match is match and result.subtree_fingerprint is SHA_C
    assert result.review_match.status is status


@pytest.mark.parametrize("value", BAD_HASHES)
def test_subtree_fingerprint_is_exact_lowercase_hex64(value):
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: subtree_fingerprint:"):
        BindingFinding(value, implementation_match())


@pytest.mark.parametrize("field", ["inventory_fingerprint", "policy_tree_fingerprint"])
@pytest.mark.parametrize("value", BAD_HASHES)
def test_coverage_fingerprints_use_same_strict_format(field, value):
    with pytest.raises(PolicyDataError, match=f"^INVALID_INTEGRATION_FINDINGS: {field}:"):
        facts(**{field: value})


@pytest.mark.parametrize("value", ["0" * 64, "f" * 64, "0123456789abcdef" * 4])
def test_valid_fingerprint_shapes_are_preserved_without_calculation(value):
    finding = BindingFinding(value, implementation_match())
    result = facts(inventory_fingerprint=value, policy_tree_fingerprint=value, implementation_findings=(finding,))
    assert result.inventory_fingerprint is value and result.policy_tree_fingerprint is value
    assert finding.subtree_fingerprint is value


@pytest.mark.parametrize("bad", [None, {}, "MATCHED", (), inventory_match(), FakeMatch(),
    ImplementationMatchSubclass("COND_A", "ROOT_A", "REVIEW", ReviewMatchStatus.MATCHED, (), ()),
])
def test_binding_requires_exact_implementation_match_without_conversion(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: review_match:"):
        BindingFinding(SHA_C, bad)


@pytest.mark.parametrize("bad", [None, {}, "MATCHED", (), implementation_match(), FakeMatch(),
    InventoryMatchSubclass("REVIEW", ReviewMatchStatus.MATCHED, (), ()),
])
def test_coverage_requires_exact_inventory_match_without_conversion(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: inventory_review_match:"):
        facts(inventory_review_match=bad)


def test_binding_identity_has_one_source_and_cannot_have_contradictory_duplicate_fields():
    match = implementation_match("COND_B", "  한글 ROOT  ")
    result = BindingFinding(SHA_C, match)
    assert tuple(field.name for field in fields(result)) == ("subtree_fingerprint", "review_match")
    assert result.to_dict()["review_match"]["condition_id"] == "COND_B"
    assert result.to_dict()["review_match"]["rule_root_id"] == "  한글 ROOT  "
    with pytest.raises(TypeError):
        BindingFinding(SHA_C, match, condition_id="COND_A")
    with pytest.raises(TypeError):
        BindingFinding(SHA_C, match, rule_root_id="OTHER_ROOT")


@pytest.mark.parametrize("inventory_status", list(ReviewMatchStatus))
@pytest.mark.parametrize("implementation_status", list(ReviewMatchStatus))
def test_coverage_accepts_review_state_combinations_without_deriving_status(inventory_status, implementation_status):
    inv = inventory_match(inventory_status)
    item = binding(status=implementation_status)
    result = facts(inventory_review_match=inv, implementation_findings=(item,))
    assert result.inventory_review_match is inv and result.implementation_findings[0] is item
    assert result.missing_condition_ids == result.unmapped_rule_ids == result.composition_gap_group_ids == ()
    assert not hasattr(result, "status") and not hasattr(result, "is_complete")


@pytest.mark.parametrize("unmapped,gaps", [((), ()), (("RULE_Z",), ()), ((), ("ANY_Z",)), (("RULE_Z",), ("ANY_Z",))])
def test_incomplete_facts_are_preserved_with_or_without_unmapped_and_gaps(unmapped, gaps):
    result = facts(missing_condition_ids=("COND_Z", "COND_B"), unmapped_rule_ids=unmapped,
                   composition_gap_group_ids=gaps, inventory_review_match=inventory_match(ReviewMatchStatus.STALE),
                   implementation_findings=(binding(status=ReviewMatchStatus.MISSING),))
    assert result.missing_condition_ids == ("COND_Z", "COND_B")
    assert result.unmapped_rule_ids is unmapped and result.composition_gap_group_ids is gaps


@pytest.mark.parametrize("unmapped,gaps", [(("RULE",), ()), ((), ("ANY",)), (("RULE",), ("ANY",))])
def test_no_missing_with_unmapped_or_gaps_violates_local_findings_contract(unmapped, gaps):
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: missing_condition_ids:") as caught:
        facts(unmapped_rule_ids=unmapped, composition_gap_group_ids=gaps)
    assert not str(caught.value).startswith(("COVERAGE_UNMAPPED_RULE", "COVERAGE_COMPOSITION_GAP"))


def test_empty_facts_and_zero_binding_findings_are_locally_representable_without_claiming_full():
    result = facts(implementation_findings=())
    assert result.implementation_findings == ()
    assert result.missing_condition_ids == result.unmapped_rule_ids == result.composition_gap_group_ids == ()
    assert "status" not in result.to_dict()


def test_zero_binding_with_pending_conditions_and_undeclared_inventory_review():
    result = facts(missing_condition_ids=("COND_B", "COND_A"), unmapped_rule_ids=("RULE_Z", "RULE_A"),
                   composition_gap_group_ids=("ANY_X",), implementation_findings=(),
                   inventory_review_match=inventory_match(ReviewMatchStatus.MISSING, declared=False))
    assert result.implementation_findings == ()
    assert result.inventory_review_match.review_ref is None
    assert result.to_dict()["missing_condition_ids"] == ["COND_B", "COND_A"]


@pytest.mark.parametrize("field", ["missing_condition_ids", "unmapped_rule_ids", "composition_gap_group_ids"])
@pytest.mark.parametrize("kind", ["none", "list", "set", "dict", "string", "generator", "tuple_subclass"])
def test_id_collections_require_exact_tuple(field, kind):
    makers = {"none": lambda: None, "list": lambda: ["ID"], "set": lambda: {"ID"}, "dict": lambda: {"ID": True},
              "string": lambda: "ID", "generator": lambda: iter(("ID",)), "tuple_subclass": lambda: TupleSubclass(("ID",))}
    with pytest.raises(PolicyDataError, match=f"^INVALID_INTEGRATION_FINDINGS: {field}:"):
        facts(**{field: makers[kind]()})


@pytest.mark.parametrize("field", ["missing_condition_ids", "unmapped_rule_ids", "composition_gap_group_ids"])
@pytest.mark.parametrize("bad", [None, 1, True, b"ID", (), {}, "", " ", "\t\n", StringSubclass("ID")])
def test_each_id_requires_exact_nonblank_string(field, bad):
    with pytest.raises(PolicyDataError, match=f"^INVALID_INTEGRATION_FINDINGS: {field}:"):
        facts(**{field: (bad,)})


@pytest.mark.parametrize("bad", ["cond_a", " COND_A", "COND_A ", "COND-A", "조건", "Ａ"])
def test_missing_ids_use_existing_canonical_condition_id_format(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: missing_condition_ids:"):
        facts(missing_condition_ids=(bad,))


@pytest.mark.parametrize("field", ["missing_condition_ids", "unmapped_rule_ids", "composition_gap_group_ids"])
def test_duplicate_id_within_each_tuple_is_rejected_without_deduplication(field):
    with pytest.raises(PolicyDataError, match=f"^INVALID_INTEGRATION_FINDINGS: {field}:"):
        facts(**{field: ("ID", "OTHER", "ID")})


def test_all_three_fact_orders_and_free_rule_id_text_are_preserved():
    missing = ("COND_Z", "COND_B")
    unmapped = ("RULE_Z", " A ", "a", "é", "e\u0301")
    gaps = ("한글 ANY", 'quote"', "line\nNOT")
    result = facts(missing_condition_ids=missing, unmapped_rule_ids=unmapped, composition_gap_group_ids=gaps)
    assert result.missing_condition_ids is missing and result.unmapped_rule_ids is unmapped
    assert result.composition_gap_group_ids is gaps
    snapshot = result.to_dict()
    assert snapshot["missing_condition_ids"] == list(missing)
    assert snapshot["unmapped_rule_ids"] == list(unmapped)
    assert snapshot["composition_gap_group_ids"] == list(gaps)


@pytest.mark.parametrize("kind", ["none", "list", "set", "dict", "string", "generator", "tuple_subclass"])
def test_implementation_findings_collection_is_exact_tuple(kind):
    item = binding()
    makers = {"none": lambda: None, "list": lambda: [item], "set": lambda: {item}, "dict": lambda: {"A": item},
              "string": lambda: "A", "generator": lambda: iter((item,)), "tuple_subclass": lambda: TupleSubclass((item,))}
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: implementation_findings:"):
        facts(implementation_findings=makers[kind]())


@pytest.mark.parametrize("bad", [None, {}, "finding", implementation_match(), inventory_match(), FakeMatch(),
                                 BindingFindingSubclass(SHA_C, implementation_match())])
def test_each_implementation_finding_requires_exact_type_before_id_access(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: implementation_findings:"):
        facts(implementation_findings=(bad,))


def test_implementation_findings_canonical_order_preserves_original_instances():
    items = (binding("COND_10", "ROOT_10"), binding("COND_2", "ROOT_2"), binding("COND_A", "ROOT_A"))
    result = facts(implementation_findings=items)
    assert result.implementation_findings is items
    assert all(a is b for a, b in zip(result.implementation_findings, items, strict=True))


@pytest.mark.parametrize("ids", [("COND_B", "COND_A"), ("COND_2", "COND_10"),
                              ("COND_A", "COND_A"), ("COND_A", "COND_B", "COND_A")])
def test_noncanonical_or_duplicate_condition_order_is_rejected_not_sorted(ids):
    items = tuple(binding(cid, "ROOT_" + str(index)) for index, cid in enumerate(ids))
    before = tuple(item.review_match.condition_id for item in items)
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: implementation_findings:"):
        facts(implementation_findings=items)
    assert tuple(item.review_match.condition_id for item in items) == before


@pytest.mark.parametrize("missing", [("COND_A",), ("COND_Z", "COND_A")])
def test_missing_and_existing_implementation_conditions_must_be_disjoint(missing):
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: missing_condition_ids:"):
        facts(missing_condition_ids=missing)


def test_all_implementation_element_types_checked_before_order_or_intersection():
    items = (binding("COND_B"), binding("COND_A"), {})
    with pytest.raises(PolicyDataError, match="^INVALID_INTEGRATION_FINDINGS: implementation_findings: 정확한 Binding"):
        facts(missing_condition_ids=("COND_A",), implementation_findings=items)


def test_no_missing_tuple_checks_require_runtime_inventory_or_policy():
    result = facts(missing_condition_ids=("PENDING",), implementation_findings=())
    assert result.missing_condition_ids == ("PENDING",)
    assert set(result.to_dict()) == {field.name for field in fields(CoverageFindings)}


@pytest.mark.parametrize("status", list(ReviewMatchStatus))
def test_binding_serialization_has_only_stored_fields_and_reuses_match_representation(status):
    result = binding(status=status)
    assert result.to_dict() == {"subtree_fingerprint": SHA_C, "review_match": result.review_match.to_dict()}
    assert result.to_dict()["review_match"]["status"] == status.value


def test_coverage_serialization_matches_exact_seven_field_shape():
    items = (binding("COND_A", " ROOT A ", ReviewMatchStatus.MISSING),
             binding("COND_B", "ROOT_B", ReviewMatchStatus.STALE))
    inv = inventory_match(ReviewMatchStatus.STALE)
    result = facts(missing_condition_ids=("COND_Z",), unmapped_rule_ids=("RULE_Z",),
                   composition_gap_group_ids=("ANY_Z",), implementation_findings=items, inventory_review_match=inv)
    assert result.to_dict() == {
        "missing_condition_ids": ["COND_Z"], "unmapped_rule_ids": ["RULE_Z"], "composition_gap_group_ids": ["ANY_Z"],
        "inventory_fingerprint": SHA_A, "policy_tree_fingerprint": SHA_B, "inventory_review_match": inv.to_dict(),
        "implementation_findings": [item.to_dict() for item in items],
    }
    assert json.loads(json.dumps(result.to_dict(), ensure_ascii=False)) == result.to_dict()


def test_serialization_returns_independent_nested_lists_and_dicts():
    result = facts(missing_condition_ids=("PENDING",), unmapped_rule_ids=("RULE",), composition_gap_group_ids=("ANY",),
                   inventory_review_match=inventory_match(ReviewMatchStatus.STALE),
                   implementation_findings=(binding(status=ReviewMatchStatus.MISSING),))
    original = result.to_dict()
    changed = result.to_dict()
    for name in ("missing_condition_ids", "unmapped_rule_ids", "composition_gap_group_ids"):
        changed[name].append("CHANGED")
    changed["inventory_review_match"]["stale_reasons"].clear()
    changed["implementation_findings"][0]["review_match"]["missing_reasons"].clear()
    changed["implementation_findings"][0]["review_match"]["condition_id"] = "CHANGED"
    changed["implementation_findings"].append({})
    assert result.to_dict() == original
    assert changed != original
    one, two = result.implementation_findings[0].to_dict(), result.implementation_findings[0].to_dict()
    one["review_match"]["missing_reasons"].clear()
    assert two == result.implementation_findings[0].to_dict()


def test_100_serializations_are_deterministic_and_leave_original_matches_unchanged():
    inv = inventory_match(ReviewMatchStatus.MISSING, declared=False)
    match = implementation_match(status=ReviewMatchStatus.STALE)
    item = BindingFinding(SHA_C, match)
    items = (item,)
    result = facts(missing_condition_ids=("COND_Z",), implementation_findings=items, inventory_review_match=inv)
    expected = result.to_dict()
    original_matches = (inv.to_dict(), match.to_dict())
    for _ in range(100):
        assert result.to_dict() == expected and result.to_dict() is not expected
    assert result.inventory_review_match is inv and result.implementation_findings is items
    assert result.implementation_findings[0] is item and item.review_match is match
    assert original_matches == (inv.to_dict(), match.to_dict())


def test_value_equality_uses_every_binding_field_and_nested_match():
    first = binding()
    assert first == BindingFinding(SHA_C, implementation_match()) and hash(first) == hash(binding())
    assert first != replace(first, subtree_fingerprint=SHA_A)
    assert first != replace(first, review_match=implementation_match("COND_B", "ROOT_B"))
    assert first != replace(first, review_match=implementation_match(status=ReviewMatchStatus.STALE))


def test_value_equality_preserves_fact_tuple_order_and_all_coverage_fields():
    first = facts(missing_condition_ids=("MISSING_Z", "MISSING_A"), unmapped_rule_ids=("Z", "A"),
                  composition_gap_group_ids=("NOT_Z", "ANY_A"))
    assert first == replace(first) and hash(first) == hash(replace(first))
    variants = {"missing_condition_ids": ("MISSING_A", "MISSING_Z"), "unmapped_rule_ids": ("A", "Z"),
                "composition_gap_group_ids": ("ANY_A", "NOT_Z"), "inventory_fingerprint": SHA_B,
                "policy_tree_fingerprint": SHA_A, "inventory_review_match": inventory_match(ReviewMatchStatus.STALE),
                "implementation_findings": (binding(status=ReviewMatchStatus.MISSING),)}
    for name, value in variants.items():
        assert first != replace(first, **{name: value})


@pytest.mark.parametrize("factory", [binding, facts])
def test_frozen_slots_prevent_assignment_deletion_and_arbitrary_attributes(factory):
    value = factory()
    assert not hasattr(value, "__dict__")
    assert type(value).__dataclass_params__.frozen
    assert tuple(type(value).__slots__) == tuple(field.name for field in fields(value))
    for field in fields(value):
        with pytest.raises(FrozenInstanceError):
            setattr(value, field.name, getattr(value, field.name))
        with pytest.raises(FrozenInstanceError):
            delattr(value, field.name)
    with pytest.raises((AttributeError, TypeError)):
        value.extra = "FORBIDDEN"


def test_all_fields_required_and_unapproved_identity_or_status_arguments_rejected():
    assert all(p.default is inspect.Parameter.empty for p in inspect.signature(BindingFinding).parameters.values())
    assert all(p.default is inspect.Parameter.empty for p in inspect.signature(CoverageFindings).parameters.values())
    with pytest.raises(TypeError):
        BindingFinding(SHA_C)
    with pytest.raises(TypeError):
        CoverageFindings()
    for extra in ("policy_id", "scope", "rule_version", "dataset_version", "source_registry_fingerprint",
                  "implementation_fingerprint", "status", "binding_findings", "is_complete"):
        with pytest.raises(TypeError):
            facts(**{extra: "UNAPPROVED"})


def test_existing_match_constructors_are_not_reexecuted(monkeypatch):
    inv, match = inventory_match(), implementation_match()
    def forbidden(*args):
        pytest.fail("하위 모델의 검증을 재실행했습니다")
    monkeypatch.setattr(InventoryReviewMatch, "__post_init__", forbidden)
    monkeypatch.setattr(ImplementationReviewMatch, "__post_init__", forbidden)
    item = BindingFinding(SHA_C, match)
    result = CoverageFindings((), (), (), SHA_A, SHA_B, inv, (item,))
    assert result.inventory_review_match is inv and result.implementation_findings[0].review_match is match


def test_model_dependencies_exclude_computation_runtime_objects_and_public_exports():
    from backend.policy_engine import policy_data
    assert tuple(field.name for field in fields(BindingFinding)) == ("subtree_fingerprint", "review_match")
    assert tuple(field.name for field in fields(CoverageFindings)) == (
        "missing_condition_ids", "unmapped_rule_ids", "composition_gap_group_ids", "inventory_fingerprint",
        "policy_tree_fingerprint", "inventory_review_match", "implementation_findings",
    )
    for model in (BindingFinding, CoverageFindings):
        assert model.__name__ not in policy_data.__all__ and not hasattr(policy_data, model.__name__)
        for name in ("status", "is_full", "is_complete", "review_complete", "policy", "root", "binding", "review_context"):
            assert not hasattr(model, name)
        for method in (model.__post_init__, model.to_dict):
            source = ast.parse(inspect.getsource(method).lstrip())
            names = {node.id for node in ast.walk(source) if isinstance(node, ast.Name)}
            assert not names & {"Policy", "RuleNode", "RuleGroup", "ConditionBinding", "CoverageReviewContext",
                                "EligibilityCoverage", "UserProfile", "EvaluationFacts", "ReviewMatchStatus"}
            called = {node.func.id for node in ast.walk(source) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
            assert called <= {"type", "getattr", "len", "set", "tuple", "list", "any", "zip", "PolicyDataError"}
            assert not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)) for node in ast.walk(source))
    # 직접 import만 제한하고 같은 모듈의 미래 별도 기능을 금지하지 않는다.
    for model in (BindingFinding, CoverageFindings):
        annotations = repr(model.__annotations__)
        assert not any(name in annotations for name in ("RuleNode", "ConditionBinding", "CoverageReviewContext", "Policy"))
