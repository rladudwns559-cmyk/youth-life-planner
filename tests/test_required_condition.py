"""합성 condition identity·근거 문자열로 의미 모델만 검증한다."""

import ast
from dataclasses import FrozenInstanceError, fields, replace
from enum import Enum, IntEnum
import inspect
import json

import pytest

from backend.policy_engine.errors import EngineValidationError, PolicyDataError
from backend.policy_engine.policy_data import ConditionRequirement, RequiredCondition
from backend.policy_engine.policy_data import required_condition as domain
from backend.policy_engine.sources import SourceRegistry, SourceValidationError


FIRST = "SYN-DOC-A#eligibility-test"
SECOND = "SYN-DOC-B#conditional-test"


def values(**changes):
    return {
        "condition_id": "SYN_ELIGIBILITY_001",
        "meaning": "합성 자격조건의 의미",
        "requirement": ConditionRequirement.REQUIRED,
        "evidence_refs": (FIRST,),
        **changes,
    }


class StringSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class RequirementLike(str, Enum):
    REQUIRED = "REQUIRED"


class IntRequirement(IntEnum):
    REQUIRED = 1


@pytest.mark.parametrize("requirement", list(ConditionRequirement))
@pytest.mark.parametrize("refs", [(FIRST,), (SECOND, FIRST), (FIRST, SECOND, FIRST)])
def test_valid_conditions_preserve_all_values_and_new_json_snapshot(requirement, refs):
    condition = RequiredCondition(**values(requirement=requirement, evidence_refs=refs))
    expected = {
        "condition_id": "SYN_ELIGIBILITY_001", "meaning": "합성 자격조건의 의미",
        "requirement": requirement.value, "evidence_refs": list(refs),
    }
    assert condition.to_dict() == expected
    assert condition.evidence_refs == refs
    assert condition == RequiredCondition(**values(requirement=requirement, evidence_refs=refs))
    assert hash(condition) == hash(RequiredCondition(**values(requirement=requirement, evidence_refs=refs)))
    assert json.loads(json.dumps(condition.to_dict())) == expected


@pytest.mark.parametrize("condition_id", [
    None, 1, True, 1.0, [], {}, "", " ", "\t", "\n", "SYN 001", "syn_001",
    " SYN_001", "SYN_001 ", "SYN_001\n", "표시 문장", "ＳＹＮ_001",
    "SYN-001", StringSubclass("SYN_001"),
])
def test_id_is_explicit_exact_string_without_normalization(condition_id):
    with pytest.raises(PolicyDataError, match="condition_id"):
        RequiredCondition(**values(condition_id=condition_id))


@pytest.mark.parametrize("meaning", [None, 1, True, 1.0, [], {}, "", " ", "\n", StringSubclass("합성 의미")])
def test_meaning_requires_nonempty_exact_string(meaning):
    with pytest.raises(PolicyDataError, match="meaning"):
        RequiredCondition(**values(meaning=meaning))


def test_meaning_is_not_identity_and_whitespace_is_not_stripped():
    original = RequiredCondition(**values())
    changed = RequiredCondition(**values(meaning="  합성 의미를 보존함  "))
    assert changed.meaning == changed.to_dict()["meaning"] == "  합성 의미를 보존함  "
    assert original.condition_id == changed.condition_id
    assert original != changed
    # 동일 ID의 metadata 충돌을 이 모델에서 해결하지 않는다.


@pytest.mark.parametrize("requirement", [
    "REQUIRED", "required", "CONDITIONAL", "INFORMATIONAL", "", None, 1, True,
    [], {}, RequirementLike.REQUIRED, IntRequirement.REQUIRED,
])
def test_requirement_requires_exact_enum_member(requirement):
    with pytest.raises(PolicyDataError, match="requirement"):
        RequiredCondition(**values(requirement=requirement))


def test_only_two_eligibility_classifications_are_available():
    assert [(member.name, member.value) for member in ConditionRequirement] == [
        ("REQUIRED", "REQUIRED"), ("CONDITIONAL", "CONDITIONAL"),
    ]
    assert not hasattr(ConditionRequirement, "INFORMATIONAL")
    assert RequiredCondition(**values()) != RequiredCondition(**values(requirement=ConditionRequirement.CONDITIONAL))


@pytest.mark.parametrize("refs", [None, [], [FIRST], FIRST, {FIRST}, {}, (), TupleSubclass((FIRST,))])
def test_refs_require_nonempty_exact_tuple(refs):
    with pytest.raises(PolicyDataError, match="evidence_refs"):
        RequiredCondition(**values(evidence_refs=refs))


@pytest.mark.parametrize("ref", [
    None, 1, True, 1.0, [], {}, "", " ", "\t", StringSubclass(FIRST),
    "SYN-DOC-A", "SYN-DOC-A#", "#test", "SYN-DOC-A#test#extra",
    "syn-doc-a#test", "SYN_DOC_A#test", "SYN-DOC-A#UPPER",
    "SYN-DOC-A#test_value", " SYN-DOC-A#test", "SYN-DOC-A#test ",
])
def test_each_ref_uses_existing_canonical_structural_parser(ref):
    with pytest.raises(SourceValidationError) as caught:
        RequiredCondition(**values(evidence_refs=(FIRST, ref)))
    assert isinstance(caught.value, PolicyDataError)
    assert isinstance(caught.value, EngineValidationError)


def test_duplicate_order_is_preserved_and_snapshot_mutation_is_independent():
    refs = (SECOND, FIRST, SECOND)
    condition = RequiredCondition(**values(evidence_refs=refs))
    first, second = condition.to_dict(), condition.to_dict()
    assert first == second and first is not second
    assert first["evidence_refs"] is not second["evidence_refs"]
    first["condition_id"] = "SYN_CHANGED"
    first["evidence_refs"].clear()
    assert condition.evidence_refs == refs
    assert condition.to_dict() == second


@pytest.mark.parametrize("field", ["condition_id", "meaning", "requirement", "evidence_refs"])
def test_mutation_and_deletion_are_rejected(field):
    condition = RequiredCondition(**values())
    with pytest.raises(FrozenInstanceError):
        setattr(condition, field, None)
    with pytest.raises(FrozenInstanceError):
        delattr(condition, field)
    assert not hasattr(condition, "__dict__")


@pytest.mark.parametrize("missing", ["condition_id", "meaning", "requirement", "evidence_refs"])
def test_all_fields_are_explicit_and_required(missing):
    payload = values()
    del payload[missing]
    with pytest.raises(TypeError):
        RequiredCondition(**payload)


@pytest.mark.parametrize("extra", [
    "scope", "edition_id", "quarter", "rule_id", "rule_root_id", "implementation_review_ref",
    "implemented", "coverage_status", "verification_status", "accepted", "simulation_accepted",
    "benefit_amount", "payment_cadence", "policy_id", "application_date",
])
def test_no_scope_binding_implementation_or_benefit_fields(extra):
    assert [field.name for field in fields(RequiredCondition)] == [
        "condition_id", "meaning", "requirement", "evidence_refs",
    ]
    condition = RequiredCondition(**values())
    assert not hasattr(condition, extra)
    with pytest.raises(TypeError):
        RequiredCondition(**values(**{extra: None}))


def test_replace_revalidates_without_mutating_original():
    original = RequiredCondition(**values())
    changed = replace(original, requirement=ConditionRequirement.CONDITIONAL)
    assert original.requirement is ConditionRequirement.REQUIRED
    assert changed.requirement is ConditionRequirement.CONDITIONAL
    with pytest.raises(PolicyDataError):
        replace(original, evidence_refs=())


def test_registry_existence_is_not_a_constructor_requirement(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("조건 값 생성에서 출처 조회 또는 I/O를 호출했습니다")
    monkeypatch.setattr(SourceRegistry, "get_source", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    condition = RequiredCondition(**values(evidence_refs=("SYN-UNREGISTERED#missing-locator",)))
    assert condition.evidence_refs == ("SYN-UNREGISTERED#missing-locator",)
    assert condition.to_dict()["evidence_refs"] == ["SYN-UNREGISTERED#missing-locator"]


def test_direct_dependencies_exclude_scope_evaluation_and_application_logic():
    tree = ast.parse(inspect.getsource(domain))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports == {"dataclasses", "enum", "errors", "sources.models"}
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert classes == {"ConditionRequirement", "RequiredCondition"}
    imported_names = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    assert imported_names == {"dataclass", "Enum", "PolicyDataError", "parse_evidence_ref"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {
        "ApplicabilityScope", "PolicyEvaluation", "PolicyEnvelope", "ConditionInventory",
        "ConditionBinding", "EligibilityCoverage", "PolicyBenefitAcceptance", "CashflowInput",
        "date", "datetime", "UserProfile",
    }
