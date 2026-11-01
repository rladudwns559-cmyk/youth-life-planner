"""narrative-v1 순수 코어. 네트워크/Provider/API 등록 없이 합성 응답만 검사한다."""
from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType
import unicodedata

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError

from backend.web.comparison import LABELS
from .contracts import ExplanationDocument, ExplanationFacts
from .facts import METRICS
from . import service as legacy

MAX_CONTEXT_BYTES = 4096
MAX_NARRATIVE_BYTES = 4096
MAX_POLICIES = 3
SUMMARY_MAX_CHARS = 60
POLICY_MAX_CHARS = 40
_BUDGET_FIELDS = ('monthly_income', 'monthly_rent', 'monthly_fixed_expenses',
                  'other_monthly_expenses', 'disposable_after_policy', 'savable_amount')
_FIELD_LABELS = MappingProxyType(dict(LABELS))
_FORBIDDEN = re.compile(
    r'[A-Za-z\d]|신청|수급|가입|승인|보장|확정|추천|기한|마감|지원금|충족|가능성|대상자|원|퍼센트|프로|[<>]'
)
# 알려진 위험 문구의 보수적 조기 거부일 뿐, 자연어 전체 의미 판정기는 아니다.
_ASSERTION = re.compile(r'(?:자격|적격|수혜).{0,8}(?:있|없|해당|되|됩|충분|완료)|'
                        r'수령|지급|만기|이자|수익|금리|무조건|'
                        r'(?:이용|참여).{0,8}(?:가능|할수|하셔도|해도)')
_UNCERTAINTY_DENIAL = re.compile(
    r'(?:확인|자료|정보|서류|검토|살펴보|알아보).{0,16}'
    r'(?:불필요|필요(?:가|는|도)?없|하지않아도|보지않아도|생략|면제)|'
    r'(?:모두|전부).{0,5}(?:해결|완료|문제없)'
)
_VERBAL_QUANTITY = re.compile(
    r'(?:금액|저축|소득|지출|예산|결과|잔액|잔고|예상).{0,8}'
    r'(?:백만|천만|십만|일억|이억|한배|두배|세배|네배|절반)'
)


class NarrativeContractError(ValueError):
    def __init__(self, code, stage, reason='INVALID_JSON'):
        self.code, self.stage, self.reason = code, stage, reason
        super().__init__(code)  # 입력/응답/예외 원문은 오류 메시지에 넣지 않는다.


@dataclass(frozen=True)
class PolicySlot:
    slot: str
    policy_id: str
    needs_confirmation_after: bool


@dataclass(frozen=True)
class NarrativeProjection:
    model_input_json: str
    slots: tuple[PolicySlot, ...] = field(repr=False)

    def model_input(self):
        """모델에는 이 복사본만 제공한다. 서버 슬롯 표를 직렬화하지 않는다."""
        return json.loads(self.model_input_json)


@dataclass(frozen=True)
class PreparedNarrative:
    projection: NarrativeProjection
    _expected_json: str = field(repr=False)
    _binding: object = field(default_factory=object, repr=False, compare=False)


@dataclass(frozen=True)
class CheckedNarrative:
    summary: str
    policy_texts: tuple[tuple[str, str], ...]
    _binding: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class NarrativeCoreResult:
    document: ExplanationDocument
    fallback: bool
    fallback_reason: str | None
    diagnostic_code: str | None
    failure_stage: str | None
    validation_passed: bool
    explanation_source: str
    ai_executed: bool = False
    ai_success: bool = False


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _labels(names):
    if len(names) != len(set(names)) or any(name not in _FIELD_LABELS for name in names):
        raise NarrativeContractError('INVALID_FIELD_SET', 'projection')
    return [_FIELD_LABELS[name] for name in sorted(names)]


def _facts_copy(facts):
    if type(facts) is not ExplanationFacts:
        raise NarrativeContractError('SERVER_FACTS_REQUIRED', 'projection')
    try:
        return ExplanationFacts.model_validate(facts.model_dump(warnings='error'))
    except (ValidationError, PydanticSerializationError):
        raise NarrativeContractError('INVALID_FACTS', 'projection') from None


def project_facts(facts: ExplanationFacts) -> NarrativeProjection:
    """확정값의 표시 분류만 수행한다. 차액 계산/정책 재판정은 하지 않는다."""
    facts = _facts_copy(facts)
    money = {value.field: value for value in facts.money_facts}
    if len(money) != len(facts.money_facts) or set(money) != {name for name, _ in METRICS}:
        raise NarrativeContractError('INVALID_MONEY_FIELD_SET', 'projection')
    if any(value.before is None or value.after is None or value.delta is None
           for name, value in money.items() if name != 'user_savings_capacity'):
        raise NarrativeContractError('INCOMPLETE_MONEY_FACT', 'projection')
    benefit = money['policy_benefit_applied']
    if (benefit.before, benefit.after, benefit.delta) != (0, 0, 0):
        raise NarrativeContractError('NONZERO_BENEFIT', 'projection')
    if any(value is not None and value < 0 for value in (
            money['user_savings_capacity'].before, money['user_savings_capacity'].after)):
        raise NarrativeContractError('INVALID_SAVINGS_CAP', 'projection')
    policies = facts.policy_facts
    ids = [p.policy_id for p in policies]
    if len(policies) > MAX_POLICIES:
        raise NarrativeContractError('UNSUPPORTED_POLICY_COUNT', 'projection')
    if len(ids) != len(set(ids)) or any(not key.strip() for key in ids):
        raise NarrativeContractError('INVALID_POLICY_IDS', 'projection')
    unknown = {u.policy_id: u for u in facts.unknown_information}
    if len(unknown) != len(facts.unknown_information) or not set(unknown) <= set(ids):
        raise NarrativeContractError('INVALID_UNKNOWN_IDS', 'projection')
    slots, contexts = [], {}
    for index, policy in enumerate(policies, 1):
        slot = f'p{index:02d}'
        rule_ids = [r.rule_id for r in policy.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise NarrativeContractError('DUPLICATE_RULE_ID', 'projection')
        missing = unknown.get(policy.policy_id)
        before_missing = missing.before_missing_fields if missing else []
        after_missing = missing.after_missing_fields if missing else []
        if missing and (missing.before_status, missing.after_status) != (policy.before_status, policy.after_status):
            raise NarrativeContractError('UNKNOWN_STATE_MISMATCH', 'projection')
        rule_before = {f for r in policy.rules for f in r.before_missing}
        rule_after = {f for r in policy.rules for f in r.after_missing}
        if not rule_before <= set(before_missing) or not rule_after <= set(after_missing) or (
                missing is None and 'UNKNOWN' in (policy.before_status, policy.after_status)):
            raise NarrativeContractError('UNKNOWN_INFORMATION_MISSING', 'projection')
        checks = []
        for rule in policy.rules:
            if rule.field not in _FIELD_LABELS:
                raise NarrativeContractError('UNSUPPORTED_RULE_FIELD', 'projection')
            _labels(rule.before_missing)
            _labels(rule.after_missing)
            if rule.input_changed or rule.before_status != rule.after_status:
                checks.append(dict(field_label=_FIELD_LABELS[rule.field],
                                   before_status=rule.before_status, after_status=rule.after_status))
        slots.append(PolicySlot(slot, policy.policy_id, bool(after_missing) or policy.after_status == 'UNKNOWN'))
        contexts[slot] = dict(before_status=policy.before_status, after_status=policy.after_status,
                              changed_checks=checks, missing_before=_labels(before_missing),
                              missing_after=_labels(after_missing))
    directions = {name: ('NOT_COMPARABLE' if money[name].delta is None else
                        'SAME' if money[name].delta == 0 else 'UP' if money[name].delta > 0 else 'DOWN')
                  for name in _BUDGET_FIELDS}
    def cap(value):
        return 'NOT_SET' if value is None else 'SET_ZERO' if value == 0 else 'SET_POSITIVE'
    amount = money['disposable_after_policy'].after
    context = dict(contract='narrative-v1', budget_changes=directions,
                   changed_input_fields=_labels(facts.changed_input_fields),
                   cashflow_after_state='DEFICIT' if amount < 0 else 'ZERO' if amount == 0 else 'SURPLUS',
                   savings_cap=dict(before=cap(money['user_savings_capacity'].before),
                                    after=cap(money['user_savings_capacity'].after)), policies=contexts)
    wire = _json(context)
    if len(wire.encode('utf-8')) > MAX_CONTEXT_BYTES:
        raise NarrativeContractError('CONTEXT_TOO_LONG', 'projection', 'RESPONSE_TOO_LONG')
    return NarrativeProjection(wire, tuple(slots))


def _server_document(expected):
    # canonical 문서 자체가 없거나 손상되면 정상 모델 품질 실패로 숨기지 않는다.
    if type(expected) is not ExplanationDocument:
        raise TypeError('SERVER_DOCUMENT_REQUIRED')
    return ExplanationDocument.model_validate(expected.model_dump(warnings='error'))


def prepare_narrative(facts, expected) -> PreparedNarrative:
    document = _server_document(expected)
    projection = project_facts(facts)
    facts = _facts_copy(facts)
    if (document.changed_facts != facts.money_facts or document.policy_explanations != facts.policy_facts
            or document.unknown_information != facts.unknown_information or document.next_actions != facts.next_actions):
        raise NarrativeContractError('CANONICAL_FACTS_MISMATCH', 'projection')
    return PreparedNarrative(projection, document.model_dump_json())


def output_schema(prepared: PreparedNarrative):
    slots = [item.slot for item in prepared.projection.slots]
    return dict(type='object', additionalProperties=False, required=['summary', 'policy_texts'], properties={
        'summary': dict(type='string', minLength=1, maxLength=SUMMARY_MAX_CHARS),
        'policy_texts': dict(type='object', additionalProperties=False, required=slots,
                             properties={slot: dict(type='string', minLength=1, maxLength=POLICY_MAX_CHARS)
                                         for slot in slots})})


def _text(text, maximum, pending):
    if type(text) is not str or not text.strip() or len(text) > maximum:
        raise NarrativeContractError('INVALID_TEXT_LENGTH_OR_TYPE', 'text')
    if any(unicodedata.category(char).startswith('C') or char in '\u2028\u2029' for char in text):
        raise NarrativeContractError('TEXT_CONTROL_CHARACTER', 'text')
    normalized = unicodedata.normalize('NFKC', text)
    if not re.search('[가-힣]', normalized) or _FORBIDDEN.search(normalized):
        raise NarrativeContractError('FORBIDDEN_NARRATIVE', 'text', 'UNSUPPORTED_NARRATIVE')
    compact = re.sub(r'\s+', '', normalized)
    if (_ASSERTION.search(compact) or _VERBAL_QUANTITY.search(compact)
            or pending and _UNCERTAINTY_DENIAL.search(compact)):
        raise NarrativeContractError('UNSUPPORTED_ASSERTION', 'text', 'UNSUPPORTED_NARRATIVE')
    return text  # 원문 보존. 정규화/strip/숫자 제거로 통과시키지 않는다.


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('DUPLICATE_KEY')
        value[key] = item
    return value


def _invalid_constant(_):
    raise ValueError('NONFINITE_JSON')


def parse_narrative(raw, prepared: PreparedNarrative) -> CheckedNarrative:
    if type(raw) not in (str, bytes):
        raise NarrativeContractError('RAW_TEXT_REQUIRED', 'parsing')
    if len(raw) > MAX_NARRATIVE_BYTES:
        raise NarrativeContractError('NARRATIVE_TOO_LONG', 'parsing', 'RESPONSE_TOO_LONG')
    try:
        encoded = raw.encode('utf-8') if type(raw) is str else raw
        if len(encoded) > MAX_NARRATIVE_BYTES:
            raise NarrativeContractError('NARRATIVE_TOO_LONG', 'parsing', 'RESPONSE_TOO_LONG')
        obj = json.loads(encoded.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, NarrativeContractError):
            raise
        raise NarrativeContractError('INVALID_NARRATIVE_JSON', 'parsing') from None
    if type(obj) is not dict or set(obj) != {'summary', 'policy_texts'} or type(obj['policy_texts']) is not dict:
        raise NarrativeContractError('INVALID_NARRATIVE_SHAPE', 'parsing')
    slots = prepared.projection.slots
    if set(obj['policy_texts']) != {item.slot for item in slots}:
        raise NarrativeContractError('SLOT_SET_MISMATCH', 'parsing')
    summary = _text(obj['summary'], SUMMARY_MAX_CHARS, any(item.needs_confirmation_after for item in slots))
    texts = tuple((item.slot, _text(obj['policy_texts'][item.slot], POLICY_MAX_CHARS, item.needs_confirmation_after))
                  for item in slots)
    return CheckedNarrative(summary, texts, prepared._binding)


def assemble_narrative(prepared: PreparedNarrative, checked: CheckedNarrative) -> ExplanationDocument:
    if type(checked) is not CheckedNarrative or checked._binding is not prepared._binding:
        raise NarrativeContractError('REQUEST_MAPPING_MISMATCH', 'assembly')
    slots = prepared.projection.slots
    if tuple(key for key, _ in checked.policy_texts) != tuple(item.slot for item in slots):
        raise NarrativeContractError('CHECKED_SLOTS_MISMATCH', 'assembly')
    # 호출자가 만든/수정한 내부 객체도 그대로 신뢰하지 않고 텍스트 경계를 다시 검사한다.
    _text(checked.summary, SUMMARY_MAX_CHARS, any(item.needs_confirmation_after for item in slots))
    for item, (_, text) in zip(slots, checked.policy_texts, strict=True):
        _text(text, POLICY_MAX_CHARS, item.needs_confirmation_after)
    expected = ExplanationDocument.model_validate_json(prepared._expected_json)
    if tuple(p.policy_id for p in expected.policy_explanations) != tuple(item.policy_id for item in slots):
        raise NarrativeContractError('CANONICAL_MAPPING_MISMATCH', 'assembly')
    texts = dict(checked.policy_texts)
    candidate = expected.model_copy(deep=True, update={
        'summary': checked.summary,
        'policy_explanations': [policy.model_copy(deep=True, update={'text': texts[item.slot]})
                                for item, policy in zip(slots, expected.policy_explanations, strict=True)]})
    # 최종 관문은 기존 검증기다. 여기서 실패한 문서를 부분 보정하지 않는다.
    return legacy.validate_output(candidate.model_dump_json(), expected)


def evaluate_synthetic_narrative(facts, expected, raw) -> NarrativeCoreResult:
    """합성 응답 전용 진입점. 예상한 계약 실패만 전체 정형 문서로 대체한다."""
    canonical = _server_document(expected)
    try:
        prepared = prepare_narrative(facts, canonical)
        checked = parse_narrative(raw, prepared)
        document = assemble_narrative(prepared, checked)
    except NarrativeContractError as exc:
        return NarrativeCoreResult(canonical, True, exc.reason, exc.code, exc.stage,
                                   False, 'deterministic_fallback')
    except legacy.OutputRejected as exc:
        return NarrativeCoreResult(canonical, True, exc.code, exc.code, 'output_validator',
                                   False, 'deterministic_fallback')
    return NarrativeCoreResult(document, False, None, None, None, True, 'validated_test_double')
