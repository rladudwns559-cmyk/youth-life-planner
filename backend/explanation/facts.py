"""검증된 서버 비교 결과의 명시적 allowlist 투영. 원본 프로필/임의 지역 문자열 제외."""
from backend.web.comparison import LABELS, DISCLAIMER
from backend.web.comparison_schemas import ComparisonResponse
from .contracts import ExplanationFacts, ExplanationDocument, MoneyFact, RuleFact, PolicyFact, UnknownFact, NextAction

POLICY_LABELS = {'PASS':'이용 가능성 높음', 'FAIL':'현재 조건과 맞지 않음', 'UNKNOWN':'추가 확인 필요'}
CONDITION_LABELS = {'PASS':'충족', 'FAIL':'미충족', 'UNKNOWN':'추가 확인 필요'}
METRICS = (
    ('monthly_income', '월소득'), ('monthly_rent', '월세'),
    ('monthly_fixed_expenses', '고정지출'), ('other_monthly_expenses', '기타지출'),
    ('total_monthly_income', '월 총수입'), ('total_monthly_expenses', '월 총지출'),
    ('disposable_after_policy', '월 여유자금'), ('savable_amount', '저축 투입 상한'),
    ('user_savings_capacity', '사용자 저축 상한'), ('policy_benefit_applied', '정책 지원금 반영'),
)
ASSUMPTIONS = [
    '합성 정책 비교이며 실제 정책 신청·수급 자격 확정이 아닙니다.',
    '월 여유자금 변화는 기존 엔진이 계산한 총수입과 월세·고정지출·기타지출 변화를 반영합니다.',
    '저축 투입 상한은 기존 Cashflow의 여유자금과 사용자 지정 상한을 반영합니다. 적자이면 저축 투입 상한은 0원입니다.',
    '상한 미입력은 별도 상한 없음이며 0원 입력과 다릅니다.',
    '생활비 소득은 정책 기준의 가구소득을 대신하지 않습니다.',
    '실제 지원금 반영은 전후 모두 0원이며 실제 금융상품 만기 계산은 제공하지 않습니다.',
]

def _shown(value):
    return '별도 상한 없음' if value is None else f'{value:,}원'

def build_facts(comparison: ComparisonResponse) -> ExplanationFacts:
    if not comparison.synthetic or comparison.benefit_applied_krw != 0:
        raise ValueError('SYNTHETIC_RESULT_REQUIRED')
    facts=[]
    for field,label in METRICS:
        # Cashflow의 완성된 원 결과와 comparison의 delta를 복사할 뿐 재계산하지 않는다.
        # 기존 Cashflow DTO는 월세/고정지출을 개별 필드로 반환하지 않는다.
        # 이 둘은 서버가 검증·평가한 input_summary에서 읽고, 나머지는 완성된 Core 결과를 사용한다.
        b=getattr(comparison.before.input_summary,field) if field in ('monthly_rent','monthly_fixed_expenses') else comparison.before.cashflow[field]
        a=getattr(comparison.after.input_summary,field) if field in ('monthly_rent','monthly_fixed_expenses') else comparison.after.cashflow[field]
        d=getattr(comparison.numeric_deltas, field)
        change='숫자 차이 미산출(미입력은 0원이 아닙니다)' if d is None else (
            '변동 없음' if d==0 else f'{abs(d):,}원 {"증가" if d>0 else "감소"}')
        facts.append(MoneyFact(field=field,label=label,before=b,after=a,delta=d,
            text=f'{label}: {_shown(b)} → {_shown(a)} · {change}.'))
    policies=[]
    for p in comparison.policy_transitions:
        rules=[RuleFact(rule_id=r.rule_id,field=r.field,before_status=r.before['status'],after_status=r.after['status'],
            before_reason=r.before['reason_code'],after_reason=r.after['reason_code'],input_changed=r.input_changed,
            before_missing=r.before['missing_fields'],after_missing=r.after['missing_fields'],
            source_refs=sorted(set(r.before['evidence_refs']+r.after['evidence_refs']))) for r in p.rules]
        changed=[r for r in rules if r.input_changed]
        text=' '.join(
            f'{LABELS.get(r.field,r.field)} 입력 변경에 따라 조건 판정이 {CONDITION_LABELS[r.before_status]} 상태에서 {CONDITION_LABELS[r.after_status]} 상태로 달라졌습니다.'
            if r.before_status!=r.after_status else f'{LABELS.get(r.field,r.field)} 입력이 바뀌었지만 조건 판정은 {CONDITION_LABELS[r.after_status]} 상태로 유지됐습니다.' for r in changed)
        if not changed:text='이 정책에서 평가한 입력 조건의 변화는 없습니다.'
        if any(r.after_missing for r in rules):text+=' 미확인 조건은 추가 확인이 필요합니다.'
        policies.append(PolicyFact(policy_id=p.policy_id,before_status=p.before_status,after_status=p.after_status,rules=rules,text=text))
    unknown=[UnknownFact(**u.model_dump()) for u in comparison.unknown_information]
    actions=[NextAction(policy_id=u.policy_id,field=f,text=f'{LABELS.get(f,f)} 정보를 공식 기준과 별도로 확인해 주세요.')
             for u in unknown for f in sorted(set(u.after_missing_fields))]
    return ExplanationFacts(dataset_version=comparison.before.dataset_version,evaluation_date=comparison.before.evaluation_date,
        changed_input_fields=[x.field for x in comparison.changed_input_fields],money_facts=facts,policy_facts=policies,
        unknown_information=unknown,next_actions=actions,assumptions=list(ASSUMPTIONS))

def deterministic_document(comparison:ComparisonResponse,facts:ExplanationFacts) -> ExplanationDocument:
    # 기존 M3.1 정형 설명을 삭제/변경하지 않고 그대로 fallback의 요약으로 재사용.
    return ExplanationDocument(summary='\n'.join(comparison.explanations),changed_facts=facts.money_facts,
        policy_explanations=facts.policy_facts,unknown_information=facts.unknown_information,next_actions=facts.next_actions)

def render_document(document:ExplanationDocument,facts:ExplanationFacts) -> str:
    lines=[document.summary]+[m.text for m in document.changed_facts]
    for p in document.policy_explanations:
        lines.append(f'{p.policy_id}: {POLICY_LABELS[p.before_status]} → {POLICY_LABELS[p.after_status]}. {p.text}')
    for u in document.unknown_information:
        lines.append(f'{u.policy_id} 미확인 정보: 변경 전 {", ".join(LABELS.get(f,f) for f in u.before_missing_fields) or "누락 없음"}, 변경 후 {", ".join(LABELS.get(f,f) for f in u.after_missing_fields) or "누락 없음"}.')
    lines += [a.text for a in document.next_actions]+facts.assumptions+[DISCLAIMER]
    return '\n'.join(lines)
