"""M3.8D 순수 후보 계약. Provider/네트워크/API 등록 없이 합성 응답만 검사한다."""
from dataclasses import dataclass, field
from itertools import product
import json
from types import MappingProxyType

from . import narrative_contract as v1
from . import service as legacy
from .contracts import ExplanationDocument, ExplanationFacts

CONTRACT_VERSION = 'narrative-catalog-v2'
_BUDGET_INPUTS = ('monthly_income', 'monthly_rent', 'monthly_fixed_expenses', 'other_monthly_expenses')
_INPUT_LABELS = MappingProxyType({'age': '만 나이', 'region': '거주 지역',
                                 'student_status': '재학 상태', 'employment_status': '취업상태'})
_SUBJECTS = MappingProxyType({'monthly_income': '월소득은', 'monthly_rent': '월세는',
                             'monthly_fixed_expenses': '고정지출은', 'other_monthly_expenses': '기타지출은'})
_SUPPORTED_INPUTS = frozenset(_BUDGET_INPUTS) | frozenset(_INPUT_LABELS) | {'user_savings_capacity'}
_POLICIES = MappingProxyType({
    'P1': ('이 정책의 종합 판정은 같아요.', '이 정책의 종합 판정은 그대로예요.'),
    'P2': ('이 정책의 종합 판정이 달라졌어요.', '이 정책의 종합 판정이 바뀌었어요.'),
    'P3': ('종합 판정은 같아요. 더 확인할 조건이 남아 있어요.', '종합 판정은 그대로이며, 추가로 확인할 조건이 있어요.'),
    'P4': ('종합 판정이 바뀌었어요. 더 확인할 조건이 남아 있어요.', '종합 판정이 달라졌고, 추가로 확인할 조건이 있어요.'),
    'P5': ('종합 판정은 같고, 비교한 조건의 미확인 표시가 해소됐어요.', '종합 판정은 같아요. 이전의 미확인 표시가 해소됐어요.'),
    'P6': ('종합 판정이 바뀌고, 비교한 조건의 미확인 표시가 해소됐어요.', '종합 판정이 바뀌었어요. 이전의 미확인 표시가 해소됐어요.'),
})


@dataclass(frozen=True)
class PolicyOptions:
    slot: str
    family: str
    pending_before: bool
    pending_after: bool
    texts: tuple[str, ...]


@dataclass(frozen=True)
class CatalogPrepared:
    summary_family: str
    summary_options: tuple[str, ...]
    policy_options: tuple[PolicyOptions, ...]
    _narrative: v1.PreparedNarrative = field(repr=False)
    _binding: object = field(default_factory=object, repr=False, compare=False)

    def model_input(self):
        """미래 전송용 복사본. 원본 사실/ID/근거·요청 객체는 포함하지 않는다."""
        return dict(contract=CONTRACT_VERSION, summary_options=list(self.summary_options),
                    policy_options={item.slot: list(item.texts) for item in self.policy_options})

    @property
    def model_input_json(self):
        return _json(self.model_input())


@dataclass(frozen=True)
class CatalogChecked:
    _checked: v1.CheckedNarrative = field(repr=False)
    _binding: object = field(repr=False, compare=False)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _error(code, stage='catalog', reason='INVALID_JSON'):
    raise v1.NarrativeContractError(code, stage, reason)


def _canonical(expected):
    if type(expected) is not ExplanationDocument:
        raise TypeError('SERVER_DOCUMENT_REQUIRED')
    return ExplanationDocument.model_validate(expected.model_dump(warnings='error'))


def _check_display_metadata(facts):
    changed = set(facts.changed_input_fields)
    if not changed <= _SUPPORTED_INPUTS:
        _error('UNSUPPORTED_CATALOG_INPUT')
    money = {item.field: item for item in facts.money_facts}
    for name, item in money.items():
        # 이미 계산된 방향의 정합성만 비교한다. 금액/차액을 다시 산출하지 않는다.
        if item.before is not None and item.after is not None:
            coherent = item.delta is not None and (
                item.delta == 0 and item.before == item.after or
                item.delta > 0 and item.after > item.before or
                item.delta < 0 and item.after < item.before)
        else:
            coherent = name == 'user_savings_capacity' and item.delta is None
        if not coherent:
            _error('INCONSISTENT_DISPLAY_DIRECTION')
        if name in _BUDGET_INPUTS or name == 'user_savings_capacity':
            if (name in changed) != (item.before != item.after):
                _error('INCONSISTENT_INPUT_CHANGE')
    unknown = {item.policy_id: item for item in facts.unknown_information}
    for policy in facts.policy_facts:
        for rule in policy.rules:
            if rule.input_changed != (rule.field in changed):
                _error('INCONSISTENT_RULE_INPUT_CHANGE')
        if any('UNKNOWN' in (r.before_status, r.after_status) for r in policy.rules) and policy.policy_id not in unknown:
            _error('UNKNOWN_INFORMATION_MISSING')


def _same_comparison(facts):
    return (not facts.changed_input_fields and
            all(item.before == item.after for item in facts.money_facts) and
            all(p.before_status == p.after_status and
                all(not r.input_changed and r.before_status == r.after_status and
                    r.before_reason == r.after_reason and r.before_missing == r.after_missing for r in p.rules)
                for p in facts.policy_facts) and
            all(u.before_status == u.after_status and u.before_missing_fields == u.after_missing_fields
                for u in facts.unknown_information))


def _summary(facts):
    money = {item.field: item for item in facts.money_facts}
    changed = set(facts.changed_input_fields)
    if 'user_savings_capacity' in changed:
        return 'S1', ('저축 상한 설정이 달라진 비교예요.', '사용자 저축 상한의 설정 변화를 비교했어요.')
    budget = [name for name in _BUDGET_INPUTS if money[name].delta != 0]
    if len(budget) == 1:
        name = budget[0]
        first = '늘었' if money[name].delta > 0 else '줄었'
        delta = money['disposable_after_policy'].delta
        last = '늘었어요' if delta > 0 else '줄었어요' if delta < 0 else '같아요'
        return 'S2', tuple(f'{_SUBJECTS[name]} {first}{join}, 월 여유자금은 {last}.' for join in ('고', '으며'))
    if len(budget) > 1:
        return 'S3', ('월 예산의 여러 항목이 달라진 비교예요.', '월 예산에서 여러 항목의 변화를 비교했어요.')
    for name, label in _INPUT_LABELS.items():
        if name in changed:
            return 'S4', (f'{label} 입력이 바뀐 비교예요.', f'{label} 입력의 변화를 비교했어요.')
    if _same_comparison(facts):
        return 'S5', ('바뀐 입력이 없어 비교 결과도 같아요.', '입력에 변화가 없어 비교 결과가 같아요.')
    return 'S6', ('월 예산과 정책별 비교 결과를 함께 살펴보세요.', '월 예산과 정책별 비교 내용을 함께 살펴보세요.')


def _pending(policy, unknown, side):
    return (getattr(policy, side + '_status') == 'UNKNOWN' or
            any(getattr(r, side + '_status') == 'UNKNOWN' or getattr(r, side + '_missing') for r in policy.rules) or
            bool(unknown and getattr(unknown, side + '_missing_fields')))


def _preflight(prepared):
    if len(prepared.model_input_json.encode('utf-8')) > v1.MAX_CONTEXT_BYTES:
        _error('CATALOG_CONTEXT_TOO_LONG', reason='RESPONSE_TOO_LONG')
    sets = (prepared.summary_options,) + tuple(p.texts for p in prepared.policy_options)
    if any(type(values) is not tuple or not 1 <= len(values) <= 2 or len(set(values)) != len(values) for values in sets):
        _error('INVALID_CATALOG_OPTIONS')
    # 최대16개 조합을 기존 코어와 최종 검증기로 사전 검사한다.
    for combination in product(*sets):
        raw = _json(dict(summary=combination[0], policy_texts={
            p.slot: text for p, text in zip(prepared.policy_options, combination[1:], strict=True)}))
        checked = v1.parse_narrative(raw, prepared._narrative)
        v1.assemble_narrative(prepared._narrative, checked)


def prepare_catalog(facts: ExplanationFacts, expected: ExplanationDocument) -> CatalogPrepared:
    narrative = v1.prepare_narrative(facts, expected)
    snapshot = ExplanationFacts.model_validate(facts.model_dump(warnings='error'))
    _check_display_metadata(snapshot)
    family, summary = _summary(snapshot)
    unknown = {u.policy_id: u for u in snapshot.unknown_information}
    options = []
    for slot, policy in zip(narrative.projection.slots, snapshot.policy_facts, strict=True):
        before = bool(_pending(policy, unknown.get(policy.policy_id), 'before'))
        after = bool(_pending(policy, unknown.get(policy.policy_id), 'after'))
        same = policy.before_status == policy.after_status
        group = ('P3' if same else 'P4') if after else ('P5' if same else 'P6') if before else ('P1' if same else 'P2')
        options.append(PolicyOptions(slot.slot, group, before, after, _POLICIES[group]))
    prepared = CatalogPrepared(family, summary, tuple(options), narrative)
    _preflight(prepared)
    return prepared


def catalog_output_schema(prepared: CatalogPrepared):
    schema = v1.output_schema(prepared._narrative)
    schema['properties']['summary']['enum'] = list(prepared.summary_options)
    for policy in prepared.policy_options:
        schema['properties']['policy_texts']['properties'][policy.slot]['enum'] = list(policy.texts)
    return schema


def _membership(checked, prepared):
    if (checked.summary not in prepared.summary_options or
            tuple(slot for slot, _ in checked.policy_texts) != tuple(p.slot for p in prepared.policy_options) or
            any(text not in p.texts for p, (_, text) in zip(prepared.policy_options, checked.policy_texts, strict=True))):
        _error('TEXT_NOT_IN_REQUEST_CATALOG', 'catalog_membership', 'UNSUPPORTED_NARRATIVE')


def parse_catalog(raw, prepared: CatalogPrepared) -> CatalogChecked:
    checked = v1.parse_narrative(raw, prepared._narrative)
    _membership(checked, prepared)
    return CatalogChecked(checked, prepared._binding)


def assemble_catalog(prepared: CatalogPrepared, checked: CatalogChecked) -> ExplanationDocument:
    if type(checked) is not CatalogChecked or checked._binding is not prepared._binding:
        _error('REQUEST_MAPPING_MISMATCH', 'catalog_assembly')
    _membership(checked._checked, prepared)
    return v1.assemble_narrative(prepared._narrative, checked._checked)


def evaluate_synthetic_catalog(facts, expected, raw) -> v1.NarrativeCoreResult:
    """실제 AI 성공으로 표시하지 않는 독립 합성 진입점."""
    canonical = _canonical(expected)
    try:
        prepared = prepare_catalog(facts, canonical)
        document = assemble_catalog(prepared, parse_catalog(raw, prepared))
    except v1.NarrativeContractError as exc:
        return v1.NarrativeCoreResult(canonical, True, exc.reason, exc.code, exc.stage,
                                      False, 'deterministic_fallback')
    except legacy.OutputRejected as exc:
        return v1.NarrativeCoreResult(canonical, True, exc.code, exc.code, 'output_validator',
                                      False, 'deterministic_fallback')
    return v1.NarrativeCoreResult(document, False, None, None, None, True, 'validated_test_double')
