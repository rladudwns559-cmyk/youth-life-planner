"""계산 없이 합성 facts의 대상/참조와 불변 Result 값 계약만 검증한다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
from itertools import permutations, product
import textwrap

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.models import Field, GroupOperator, Operator, Policy, PolicyRule, RuleGroup, _jsonable
from backend.policy_engine.policy_data import (
    ApplicabilityScope, ConditionBinding, ConditionInventory, ConditionRequirement, CoverageReviewContext,
    EligibilityCoverage, EligibilityCoverageResult, EligibilityCoverageStatus, RequiredCondition,
)
from backend.policy_engine.policy_data import eligibility_coverage_result as domain
from backend.policy_engine.policy_data.coverage_integration_findings import (
    _CoverageIntegrationFindings as Findings, _ImplementationIntegrationFinding as BindingFinding,
)
from backend.policy_engine.policy_data.coverage_review_match import (
    ImplementationReviewMatch, InventoryReviewMatch, ReviewMatchStatus as Match,
    ReviewMissingReason as Missing, ReviewStaleReason as Stale,
)


STORED = ("policy_id", "scope", "inventory_version", "rule_version", "dataset_version",
          "source_registry_fingerprint", "implementation_fingerprint", "findings")
SHA_A, SHA_B, SHA_C = "a" * 64, "b" * 64, "c" * 64


def inventory_match(status=Match.MATCHED, declared=True):
    ref = "SYNTH-INV-REVIEW" if declared else None
    if not declared:
        status = Match.MISSING
    return InventoryReviewMatch(ref, status,
        (Stale.INVENTORY_VERSION_CHANGED,) if status is Match.STALE else (),
        ((Missing.NO_REVIEW_CONTEXT,) if declared else (Missing.INVENTORY_REVIEW_NOT_DECLARED,))
        if status is Match.MISSING else ())


def binding_finding(binding, status=Match.MATCHED):
    return BindingFinding(SHA_C, ImplementationReviewMatch(
        binding.condition_id, binding.rule_root_id, binding.implementation_review_ref, status,
        (Stale.RULE_VERSION_CHANGED,) if status is Match.STALE else (),
        (Missing.NO_REVIEW_CONTEXT,) if status is Match.MISSING else (),
    ))


def prepared(ids=("COND_A", "COND_B", "COND_C"), bound=None, context=True, declared=True,
             inventory_status=None, implementation_statuses=None, unmapped=(), gaps=()):
    """이미 계산되었다고 가정한 합성 값. gate/지문/matcher를 실행하지 않는다.

    빈 Context records는 baseline 값 검사에만 쓴다. 실제 Review resolve 성공을 주장하지 않는다.
    """
    if bound is None:
        bound = ids[::-1]
    conditions = tuple(RequiredCondition(cid, "합성 조건", ConditionRequirement.CONDITIONAL if index % 2 else
                                        ConditionRequirement.REQUIRED, ("SYNTH-SRC#a",))
                       for index, cid in enumerate(ids))
    inventory = ConditionInventory("SYNTH-POLICY", ApplicabilityScope("2026", 3), "i0001", conditions,
                                   "SYNTH-INV-REVIEW" if declared else None)
    bindings = tuple(ConditionBinding(cid, "ROOT_" + cid, "SYNTH-REVIEW-" + cid) for cid in bound)
    value = EligibilityCoverage(inventory, bindings)
    leaves = tuple(PolicyRule(binding.rule_root_id, Field.AGE, Operator.GTE, 19,
                             evidence_refs=("SYNTH-SRC#a",)) for binding in bindings)
    root = RuleGroup("TOP_ALL", GroupOperator.ALL, leaves) if leaves else PolicyRule(
        "UNMAPPED", Field.AGE, Operator.GTE, 19, evidence_refs=("SYNTH-SRC#a",))
    current = Policy(inventory.policy_id, "합성 정책", "r0001", root)
    review_context = CoverageReviewContext(inventory.policy_id, inventory.scope, "SYNTH-DATASET",
                                           SHA_A, SHA_B, (), ()) if context else None
    default_status = Match.MATCHED if context else Match.MISSING
    outcomes = implementation_statuses or {}
    items = tuple(binding_finding(binding, outcomes.get(binding.condition_id, default_status))
                  for binding in sorted(bindings, key=lambda item: item.condition_id))
    facts = Findings(tuple(cid for cid in ids if cid not in set(bound)), unmapped, gaps, SHA_A, SHA_B,
                     inventory_match(inventory_status or default_status, declared), items)
    return value, current, review_context, facts


def create(*args, **kwargs):
    return domain._create_eligibility_coverage_result(*args, **kwargs)


def local_values():
    result = create(*prepared())
    return {item.name: getattr(result, item.name) for item in fields(result)}


def internal_local(**overrides):
    # 비공개 token을 명시하는 로컬 값 검증 전용 테스트 경로다. 출처 인증을 뜻하지 않는다.
    values = local_values()
    values.update(overrides)
    return EligibilityCoverageResult(**values, _creation_token=domain._RESULT_CREATION_TOKEN)


def test_enum_has_exact_two_canonical_members_and_result_has_exact_eight_stored_fields():
    assert list(EligibilityCoverageStatus.__members__) == ["FULL_POLICY", "CONDITION_SLICE"]
    assert [item.value for item in EligibilityCoverageStatus] == ["FULL_POLICY", "CONDITION_SLICE"]
    assert issubclass(EligibilityCoverageStatus, str)
    assert tuple(item.name for item in fields(EligibilityCoverageResult)) == STORED
    assert tuple(EligibilityCoverageResult.__slots__) == STORED
    assert "status" not in inspect.signature(EligibilityCoverageResult).parameters
    assert isinstance(EligibilityCoverageResult.status, property)
    assert EligibilityCoverageResult.status.fset is None


@pytest.mark.parametrize("count", [1, 2, 3])
def test_synthetic_full_preserves_original_scope_findings_and_all_current_identity(count):
    args = prepared(ids=tuple("COND_" + letter for letter in "ABC"[:count]))
    value, current, context, facts = args
    result = create(*args)
    assert type(result) is EligibilityCoverageResult
    assert result.status is EligibilityCoverageStatus.FULL_POLICY
    assert result.policy_id is value.inventory.policy_id and result.scope is value.inventory.scope
    assert result.inventory_version is value.inventory.inventory_version
    assert result.rule_version is current.rule_version and result.findings is facts
    assert result.dataset_version is context.dataset_version
    assert result.source_registry_fingerprint is context.source_registry_fingerprint
    assert result.implementation_fingerprint is context.implementation_fingerprint


@pytest.mark.parametrize("declared", [False, True])
@pytest.mark.parametrize("bound", [(), ("COND_A",), ("COND_A", "COND_B", "COND_C")])
def test_context_none_all_missing_and_all_none_baseline_is_normal_slice(declared, bound):
    result = create(*prepared(bound=bound, declared=declared, context=False))
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    assert (result.dataset_version, result.source_registry_fingerprint, result.implementation_fingerprint) == (None,) * 3
    assert result.findings.inventory_review_match.status is Match.MISSING
    assert all(item.review_match.status is Match.MISSING for item in result.findings.implementation_findings)


@pytest.mark.parametrize("bound", [(), ("COND_A",), ("COND_C", "COND_A")])
@pytest.mark.parametrize("unmapped,gaps", [((), ()), (("U_Z", "U_A"), ()), ((), ("G_Z", "G_A")),
                                          (("U_Z",), ("G_Z",))])
def test_incomplete_partition_and_all_audit_facts_preserved(bound, unmapped, gaps):
    args = prepared(ids=("COND_C", "COND_B", "COND_A"), bound=bound, unmapped=unmapped, gaps=gaps)
    result = create(*args)
    expected_missing = tuple(cid for cid in ("COND_C", "COND_B", "COND_A") if cid not in bound)
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    assert result.findings.missing_condition_ids == expected_missing
    assert result.findings.unmapped_rule_ids == unmapped and result.findings.composition_gap_group_ids == gaps
    actual_ids = tuple(item.review_match.condition_id for item in result.findings.implementation_findings)
    assert actual_ids == tuple(sorted(bound))
    assert set(expected_missing).isdisjoint(actual_ids)
    assert set(expected_missing) | set(actual_ids) == {"COND_A", "COND_B", "COND_C"}


@pytest.mark.parametrize("inventory_status", [Match.MATCHED, Match.STALE])
@pytest.mark.parametrize("states", list(product((Match.MATCHED, Match.STALE), repeat=3)))
def test_current_context_matched_stale_combinations_derive_status_without_modifying_reasons(inventory_status, states):
    args = prepared(inventory_status=inventory_status,
                    implementation_statuses=dict(zip(("COND_A", "COND_B", "COND_C"), states)))
    result = create(*args)
    expected = EligibilityCoverageStatus.FULL_POLICY if inventory_status is Match.MATCHED and all(
        status is Match.MATCHED for status in states) else EligibilityCoverageStatus.CONDITION_SLICE
    assert result.status is expected
    assert result.findings is args[3]
    assert tuple(item.review_match.status for item in result.findings.implementation_findings) == states


@pytest.mark.parametrize("states", list(product((Match.MATCHED, Match.STALE), repeat=3)))
def test_undeclared_inventory_review_is_slice_with_normal_implementation_outcomes(states):
    result = create(*prepared(declared=False,
                    implementation_statuses=dict(zip(("COND_A", "COND_B", "COND_C"), states))))
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE
    assert result.findings.inventory_review_match.missing_reasons == (Missing.INVENTORY_REVIEW_NOT_DECLARED,)


def test_zero_binding_with_empty_context_and_undeclared_inventory_is_normal_slice():
    result = create(*prepared(bound=(), declared=False))
    assert result.findings.implementation_findings == ()
    assert result.dataset_version is not None
    assert result.status is EligibilityCoverageStatus.CONDITION_SLICE


def test_conditional_is_not_optional_and_complete_conditional_can_be_full():
    value, current, context, facts = prepared(ids=("COND_A", "COND_B"), bound=("COND_A",))
    assert value.inventory.conditions[1].requirement is ConditionRequirement.CONDITIONAL
    assert create(value, current, context, facts).status is EligibilityCoverageStatus.CONDITION_SLICE
    assert create(*prepared(ids=("COND_A", "COND_B"))).status is EligibilityCoverageStatus.FULL_POLICY


@pytest.mark.parametrize("token", [None, False, True, "token", {}, object()])
def test_direct_construction_without_exact_private_token_is_rejected_before_local_validation(token):
    values = local_values()
    values["policy_id"] = None
    with pytest.raises(TypeError, match="내부 검증 factory"):
        EligibilityCoverageResult(**values, _creation_token=token)


def test_direct_construction_with_all_eight_fields_and_fabricated_full_is_rejected():
    with pytest.raises(TypeError, match="내부 검증 factory"):
        EligibilityCoverageResult(**local_values())
    with pytest.raises(TypeError):
        EligibilityCoverageResult()


@pytest.mark.parametrize("status", [EligibilityCoverageStatus.FULL_POLICY,
    EligibilityCoverageStatus.CONDITION_SLICE, "FULL_POLICY", None])
def test_status_cannot_be_passed_to_constructor_or_factory(status):
    with pytest.raises(TypeError):
        EligibilityCoverageResult(**local_values(), status=status)
    with pytest.raises(TypeError):
        create(*prepared(), status=status)


@pytest.mark.parametrize("changes", [{}, {"policy_id": "OTHER-POLICY"}, {"dataset_version": "OTHER"},
                                     {"status": EligibilityCoverageStatus.FULL_POLICY}])
def test_dataclass_replace_is_not_a_result_update_path(changes):
    result = create(*prepared())
    with pytest.raises(TypeError):
        replace(result, **changes)


class TextSubclass(str):
    pass


class CoverageSubclass(EligibilityCoverage):
    pass


class PolicySubclass(Policy):
    pass


class ContextSubclass(CoverageReviewContext):
    pass


class FindingsSubclass(Findings):
    pass


class ScopeSubclass(ApplicabilityScope):
    pass


class FakeInput:
    @property
    def inventory(self):
        pytest.fail("exact type 확인 전에 내부 속성을 읽었습니다")


@pytest.mark.parametrize("slot,bad", [
    (slot, bad) for slot in ("coverage", "policy", "review_context", "findings")
    for bad in (None, {}, [], "raw", 1, True, FakeInput())
    if not (slot == "review_context" and bad is None)
])
def test_factory_exact_inputs_without_raw_conversion(slot, bad):
    inputs = dict(zip(("coverage", "policy", "review_context", "findings"), prepared()))
    inputs[slot] = bad
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: " + slot + ":"):
        create(**inputs)


@pytest.mark.parametrize("slot", ["coverage", "policy", "review_context", "findings"])
def test_factory_rejects_subclasses(slot):
    value, current, context, facts = prepared()
    inputs = dict(coverage=value, policy=current, review_context=context, findings=facts)
    if slot == "coverage":
        inputs[slot] = CoverageSubclass(value.inventory, value.bindings)
    elif slot == "policy":
        inputs[slot] = PolicySubclass(current.policy_id, current.policy_name, current.rule_version, current.root)
    else:
        original = context if slot == "review_context" else facts
        cls = ContextSubclass if slot == "review_context" else FindingsSubclass
        inputs[slot] = cls(**{item.name: getattr(original, item.name) for item in fields(original)})
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: " + slot + ":"):
        create(**inputs)


@pytest.mark.parametrize("bad", [None, "", " ", "lower-id", "A_B", "A--B", "-A", "A-", True, 1, {},
                                TextSubclass("SYNTH-POLICY")])
def test_local_policy_id_strict_canonical(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: policy_id:"):
        internal_local(policy_id=bad)


@pytest.mark.parametrize("bad", [None, {}, "2026/Q3", ("2026", 3), ScopeSubclass("2026", 3)])
def test_local_scope_requires_exact_immutable_value(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: scope:"):
        internal_local(scope=bad)


@pytest.mark.parametrize("bad", [None, "i0000", "i0", "i001", "i00001", "i-0001", "I0001", "i0001 ",
                                True, 1, TextSubclass("i0001")])
def test_local_inventory_version_uses_existing_positive_version_contract(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: inventory_version:"):
        internal_local(inventory_version=bad)


@pytest.mark.parametrize("name", ["rule_version", "dataset_version"])
@pytest.mark.parametrize("bad", ["", " ", 1, True, {}, [], TextSubclass("valid")])
def test_local_rule_and_dataset_exact_nonblank_without_normalization(name, bad):
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: " + name + ":"):
        internal_local(**{name: bad})


def test_local_rule_version_cannot_be_none_and_does_not_require_r_number_format():
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: rule_version:"):
        internal_local(rule_version=None)
    result = internal_local(rule_version="  의미 버전  ", dataset_version="  합성 dataset  ")
    assert result.rule_version == "  의미 버전  " and result.dataset_version == "  합성 dataset  "


@pytest.mark.parametrize("name", ["source_registry_fingerprint", "implementation_fingerprint"])
@pytest.mark.parametrize("bad", ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "0x" + "a" * 62,
                                " " + "a" * 63, "a" * 63 + "\n", 1, True, {}, TextSubclass(SHA_A)])
def test_local_fingerprints_are_exact_lowercase_hex64(name, bad):
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: " + name + ":"):
        internal_local(**{name: bad})


@pytest.mark.parametrize("presence", [state for state in product((False, True), repeat=3) if 0 < sum(state) < 3])
def test_all_six_partial_baseline_combinations_rejected(presence):
    values = dict(zip(("dataset_version", "source_registry_fingerprint", "implementation_fingerprint"),
                      (value if present else None for present, value in zip(presence, ("SYNTH", SHA_A, SHA_B)))))
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: review_baseline:"):
        internal_local(**values)


@pytest.mark.parametrize("bad", [None, {}, [], "raw", 1, True])
def test_local_findings_exact_type(bad):
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings:"):
        internal_local(findings=bad)


@pytest.mark.parametrize("mismatch", ["policy", "context_policy", "annual", "quarter", "edition", "both"])
def test_factory_checks_policy_and_context_identity_without_lookup(mismatch):
    value, current, context, facts = prepared()
    if mismatch == "policy":
        current = replace(current, policy_id="OTHER-POLICY")
        field = "policy_id"
    else:
        changes = {
            "context_policy": dict(policy_id="OTHER-POLICY"), "annual": dict(scope=ApplicabilityScope("2026", None)),
            "quarter": dict(scope=ApplicabilityScope("2026", 4)), "edition": dict(scope=ApplicabilityScope("2027", 3)),
            "both": dict(policy_id="OTHER-POLICY", scope=ApplicabilityScope("2026", None)),
        }[mismatch]
        context = replace(context, **changes)
        field = "review_context.policy_id" if mismatch in ("context_policy", "both") else "review_context.scope"
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: " + field + ":"):
        create(value, current, context, facts)


@pytest.mark.parametrize("missing", [(), ("COND_OTHER",), ("COND_B",), ("COND_A", "COND_C")])
def test_missing_correspondence_rejects_omission_extra_wrong_id_and_reordering(missing):
    value, current, context, facts = prepared(ids=("COND_C", "COND_B", "COND_A"), bound=("COND_B",))
    assert facts.missing_condition_ids == ("COND_C", "COND_A")
    altered = replace(facts, missing_condition_ids=missing, implementation_findings=())
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.missing_condition_ids:"):
        create(value, current, context, altered)


@pytest.mark.parametrize("mode", ["empty", "omit", "extra", "same_count_wrong_id", "root", "review_ref"])
def test_binding_finding_exact_triples_catch_fabricated_full_and_slice(mode):
    value, current, context, facts = prepared(ids=("COND_A", "COND_B"))
    items = facts.implementation_findings
    if mode == "empty":
        items = ()
    elif mode == "omit":
        items = items[:1]
    elif mode == "extra":
        items += (binding_finding(ConditionBinding("COND_C", "ROOT_C", "REF_C")),)
    else:
        changes = {"same_count_wrong_id": dict(condition_id="COND_C"), "root": dict(rule_root_id="WRONG"),
                   "review_ref": dict(review_ref="WRONG")}[mode]
        items = (items[0], replace(items[1], review_match=replace(items[1].review_match, **changes)))
    altered = replace(facts, implementation_findings=items)
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.implementation_findings:"):
        create(value, current, context, altered)


@pytest.mark.parametrize("declared", [False, True])
def test_inventory_review_ref_must_match_original_declaration(declared):
    value, current, context, facts = prepared(declared=declared)
    altered = replace(facts, inventory_review_match=replace(inventory_match(), review_ref="SYNTH-WRONG-REF"))
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.inventory_review_match.review_ref:"):
        create(value, current, context, altered)


@pytest.mark.parametrize("inventory_status", [Match.MATCHED, Match.STALE])
def test_all_none_baseline_cannot_accept_matched_or_stale_inventory(inventory_status):
    value, current, _, facts = prepared(inventory_status=inventory_status)
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.inventory_review_match:"):
        create(value, current, None, facts)


@pytest.mark.parametrize("state", [Match.MATCHED, Match.STALE])
def test_all_none_baseline_requires_existing_implementations_missing(state):
    value, current, _, facts = prepared(context=False)
    item = replace(facts.implementation_findings[0], review_match=replace(
        facts.implementation_findings[0].review_match, status=state, missing_reasons=(),
        stale_reasons=(Stale.RULE_VERSION_CHANGED,) if state is Match.STALE else ()))
    altered = replace(facts, implementation_findings=(item,) + facts.implementation_findings[1:])
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.implementation_findings:"):
        create(value, current, None, altered)


def test_current_baseline_rejects_context_missing_inventory_and_implementation_outcomes():
    value, current, context, _ = prepared()
    missing_facts = prepared(context=False)[3]
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.inventory_review_match:"):
        create(value, current, context, missing_facts)
    missing_impls = replace(missing_facts, inventory_review_match=inventory_match())
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.implementation_findings:"):
        create(value, current, context, missing_impls)


def test_mixed_inventory_stale_implementation_missing_is_not_constructible_normal_result():
    args = prepared(bound=("COND_A",), unmapped=("U",), gaps=("G",), inventory_status=Match.STALE,
                    implementation_statuses={"COND_A": Match.MISSING})
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.implementation_findings:"):
        create(*args)
    valid = prepared(bound=("COND_A",), unmapped=("U",), gaps=("G",), inventory_status=Match.STALE)
    assert create(*valid).status is EligibilityCoverageStatus.CONDITION_SLICE


@pytest.mark.parametrize("context", [False, True])
def test_inventory_missing_reason_combination_must_match_actual_gate_precedence(context):
    value, current, review_context, facts = prepared(context=context, declared=False)
    inv = replace(facts.inventory_review_match,
                  missing_reasons=(Missing.NO_REVIEW_CONTEXT, Missing.INVENTORY_REVIEW_NOT_DECLARED))
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.inventory_review_match:"):
        create(value, current, review_context, replace(facts, inventory_review_match=inv))


def test_local_empty_implementation_without_missing_is_rejected_before_vacuous_full():
    altered = replace(prepared()[3], implementation_findings=())
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.implementation_findings:"):
        internal_local(findings=altered)


def test_factory_error_precedence_types_identity_missing_rows_inventory_ref_and_local_checks():
    value, current, context, facts = prepared()
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: coverage:"):
        create(None, None, {}, {})
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: policy:"):
        create(value, None, {}, {})
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: review_context:"):
        create(value, current, {}, {})
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings:"):
        create(value, replace(current, policy_id="OTHER"), context, {})
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: policy_id:"):
        create(value, replace(current, policy_id="OTHER"), replace(context, policy_id="ALSO-OTHER"), facts)
    # 형식상 유효한 여러 결합 모순을 두고 post-check 오류 우선순위를 확인한다.
    bad = replace(facts, missing_condition_ids=("COND_Z",), implementation_findings=(),
                  inventory_review_match=replace(inventory_match(), review_ref="WRONG"))
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.missing_condition_ids:"):
        create(value, current, context, bad)
    bad = replace(bad, missing_condition_ids=())
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.implementation_findings:"):
        create(value, current, context, bad)
    bad = replace(bad, implementation_findings=facts.implementation_findings)
    with pytest.raises(PolicyDataError, match="^INVALID_COVERAGE_RESULT: findings.inventory_review_match.review_ref:"):
        create(value, current, context, bad)


@pytest.mark.parametrize("context", [False, True])
@pytest.mark.parametrize("incomplete", [False, True])
def test_serialization_has_exact_nine_keys_canonical_status_and_explicit_none(context, incomplete):
    result = create(*prepared(context=context, bound=("COND_A",) if incomplete else None))
    snapshot = result.to_dict()
    assert tuple(snapshot) == STORED + ("status",)
    assert snapshot["status"] == result.status.value
    assert type(snapshot["status"]) is str
    assert snapshot["scope"] == result.scope.to_dict()
    assert snapshot["findings"] == result.findings.to_dict()
    for name in ("dataset_version", "source_registry_fingerprint", "implementation_fingerprint"):
        assert snapshot[name] == getattr(result, name)
        assert (snapshot[name] is None) is (not context)


@pytest.mark.parametrize("name", STORED + ("status",))
def test_all_stored_fields_and_status_are_immutable(name):
    result = create(*prepared())
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        setattr(result, name, None)
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        delattr(result, name)
    assert not hasattr(result, "__dict__")


def test_snapshot_mutation_does_not_affect_result_or_original_findings():
    result = create(*prepared(bound=("COND_A",), gaps=("G",)))
    before = result.to_dict()
    exported = result.to_dict()
    exported["scope"]["quarter"] = 4
    exported["findings"]["missing_condition_ids"].append("CHANGED")
    exported["findings"]["inventory_review_match"]["status"] = "WRONG"
    exported["findings"]["implementation_findings"][0]["review_match"]["condition_id"] = "WRONG"
    exported["findings"]["implementation_findings"].clear()
    assert result.to_dict() == before


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_binding_order_does_not_change_correspondence_or_result(order):
    value, current, context, facts = prepared()
    result = create(value, current, context, facts)
    alternate = replace(value, bindings=tuple(value.bindings[index] for index in order))
    assert create(alternate, current, context, facts) == result


def test_100_repeats_equality_and_all_input_values_identities_unchanged():
    args = prepared(bound=("COND_A",), unmapped=("U",), gaps=("G",))
    value, current, context, facts = args
    before = (value.to_dict(), _jsonable(current), context.to_dict(), facts.to_dict())
    result = create(*args)
    for _ in range(100):
        assert create(*args) == result and result.status is EligibilityCoverageStatus.CONDITION_SLICE
    assert (value.to_dict(), _jsonable(current), context.to_dict(), facts.to_dict()) == before
    assert result.findings is facts and result.scope is value.inventory.scope
    assert tuple(getattr(result, name) for name in STORED) == tuple(getattr(create(*args), name) for name in STORED)


def test_changed_identity_changes_value_equality_without_independent_status_state():
    result = create(*prepared())
    for changes in (dict(policy_id="OTHER-POLICY"), dict(inventory_version="i0002"), dict(rule_version="other"),
                    dict(scope=ApplicabilityScope("2026", None)), dict(dataset_version="OTHER"),
                    dict(source_registry_fingerprint="d" * 64), dict(implementation_fingerprint="e" * 64)):
        other = internal_local(**changes)
        assert other != result and other.status is result.status


def test_factory_preserves_explicit_annual_scope_versions_and_current_baseline_verbatim():
    value, current, context, facts = prepared()
    scope = ApplicabilityScope("2027", None)
    value = replace(value, inventory=replace(value.inventory, scope=scope, inventory_version="i12345"))
    current = replace(current, rule_version="  합성 버전  ")
    context = replace(context, scope=scope, dataset_version="  현재 합성 dataset  ",
                      source_registry_fingerprint="d" * 64, implementation_fingerprint="e" * 64)
    result = create(value, current, context, facts)
    assert result.scope is scope and result.inventory_version == "i12345"
    assert result.rule_version == "  합성 버전  " and result.dataset_version == "  현재 합성 dataset  "
    assert result.source_registry_fingerprint == "d" * 64 and result.implementation_fingerprint == "e" * 64


def test_future_recomputation_and_subordinate_constructors_are_not_called(monkeypatch):
    from backend.policy_engine.policy_data import coverage_integration, coverage_fingerprint, coverage_review_matching
    from backend.policy_engine.policy_data import coverage_structure, coverage_composition
    value, current, context, facts = prepared()
    def fail(*args, **kwargs):
        pytest.fail("모델 단계에서 계산 또는 하위 생성자를 재실행했습니다")
    for module, names in (
        (coverage_integration, ("_collect_coverage_integration_findings",)),
        (coverage_fingerprint, ("fingerprint_condition_inventory", "fingerprint_policy_tree", "fingerprint_rule_subtree")),
        (coverage_review_matching, ("_match_inventory_review", "_match_implementation_review")),
        (coverage_structure, ("_analyze_coverage_structure",)),
        (coverage_composition, ("_find_composition_gap_group_ids",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, fail)
    for cls in (EligibilityCoverage, ConditionInventory, ConditionBinding, Policy, CoverageReviewContext,
                Findings, BindingFinding, InventoryReviewMatch, ImplementationReviewMatch, ApplicabilityScope):
        monkeypatch.setattr(cls, "__post_init__", fail)
    result = create(value, current, context, facts)
    assert result.status is EligibilityCoverageStatus.FULL_POLICY
    assert result.to_dict()["status"] == "FULL_POLICY"


def test_public_exports_private_factory_boundary_and_no_external_dependencies():
    from backend.policy_engine import policy_data
    assert policy_data.EligibilityCoverageResult is EligibilityCoverageResult
    assert policy_data.EligibilityCoverageStatus is EligibilityCoverageStatus
    assert "EligibilityCoverageResult" in policy_data.__all__ and "EligibilityCoverageStatus" in policy_data.__all__
    assert not hasattr(policy_data, "_create_eligibility_coverage_result")
    result = create(*prepared())
    assert not any(hasattr(result, name) for name in ("slice_reasons", "is_full", "is_complete", "verified", "accepted"))
    # 현재 네 함수의 의존만 검사한다. 같은 모듈의 미래 독립 함수/import 추가는 제한하지 않는다.
    functions = (domain._create_eligibility_coverage_result, EligibilityCoverageResult.__post_init__,
                 EligibilityCoverageResult.status.fget, EligibilityCoverageResult.to_dict)
    for function in functions:
        source = ast.parse(textwrap.dedent(inspect.getsource(function)))
        named_calls = {node.func.id for node in ast.walk(source)
                       if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        assert named_calls <= {"type", "_invalid", "TypeError", "any", "all", "getattr", "tuple", "sorted",
                               "EligibilityCoverageResult"}
        attribute_calls = {node.func.attr for node in ast.walk(source)
                           if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        assert attribute_calls <= {"fullmatch", "strip", "to_dict"}
    signature = inspect.signature(domain._create_eligibility_coverage_result)
    assert tuple(signature.parameters) == ("coverage", "policy", "review_context", "findings")
    assert all(parameter.default is inspect.Parameter.empty for parameter in signature.parameters.values())
