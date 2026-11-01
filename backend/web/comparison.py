"""두 기존 simulation 실행 결과의 차이와 근거만 계산한다. 정책/예산 재판정 없음."""
from . import service
from .comparison_schemas import (
    ComparisonInput, ComparisonResponse, InputChange, NumericDeltas,
    PolicyTransition, RuleComparison, UnknownInformation,
)

LABELS = {
    'age':'만 나이', 'region':'거주 지역', 'student_status':'재학 상태',
    'employment_status':'취업상태', 'monthly_income':'월소득', 'monthly_rent':'월세',
    'monthly_fixed_expenses':'고정지출', 'other_monthly_expenses':'기타지출',
    'user_savings_capacity':'사용자 저축 상한', 'household_income':'정책 기준의 가구소득',
}
STATUS_LABELS={'PASS':'충족','FAIL':'미충족','UNKNOWN':'추가 확인 필요'}
DISCLAIMER='합성 데이터 비교입니다. 실제 정책 승인·지원금 수령 또는 미래 금융수익을 보장하지 않습니다. 정책 지원금은 0원만 반영합니다.'

def _value(field, value):
    if value is None: return '미입력'
    if field=='employment_status': return {'employed':'취업','unemployed':'미취업'}[value]
    if field=='student_status': return '재학 중' if value else '재학하지 않음'
    return str(value)

def _amount_change(label, delta):
    if delta==0: return f'{label} 변화는 0원입니다.'
    particle='가' if label=='월세' else '이'
    return f'{label}{particle} {abs(delta):,}원 {"증가" if delta>0 else "감소"}했습니다.'

def compare_scenarios(data: ComparisonInput) -> ComparisonResponse:
    # 기존 adapter를 그대로 두 번 호출한다. 한쪽 실패 시 비교 결과를 반환하지 않는다.
    before=service.simulate(data.before)
    after=service.simulate(data.after)
    b=data.before.model_dump()
    a=data.after.model_dump()
    changed=[InputChange(field=field,before=b[field],after=a[field]) for field in b if b[field]!=a[field]]
    changed_names={item.field for item in changed}
    bc,ac=before.cashflow,after.cashflow
    differences={field:ac[field]-bc[field] for field in (
        'monthly_income','total_monthly_income','total_monthly_expenses',
        'disposable_before_policy','disposable_after_policy','savable_amount','policy_benefit_applied')}
    differences.update({field:a[field]-b[field] for field in ('monthly_rent','monthly_fixed_expenses','other_monthly_expenses')})
    # 미지정은 0원이 아니다. 둘 다 정수인 경우에만 사용자 지정 상한의 숫자 차이를 계산한다.
    differences['user_savings_capacity']=(a['user_savings_capacity']-b['user_savings_capacity']
        if a['user_savings_capacity'] is not None and b['user_savings_capacity'] is not None else None)
    deltas=NumericDeltas(**differences)
    transitions=[]
    unknown=[]
    ap={policy['policy_id']:policy for policy in after.policies}
    if set(ap)!={p['policy_id'] for p in before.policies}: raise RuntimeError('비교 정책 집합이 다릅니다')
    for bp in before.policies:
        aft=ap[bp['policy_id']]
        ar={r['rule_id']:r for r in aft['rule_results']}
        rules=[]
        for br in bp['rule_results']:
            field=br['expected_condition'].get('field')
            if field is None: continue  # 그룹 상태는 기존 엔진 결과를 그대로 정책 상태에 사용
            rr=ar[br['rule_id']]
            input_changed=field in changed_names
            status_changed=br['status']!=rr['status']
            explanation=f'{LABELS.get(field,field)} 조건: {STATUS_LABELS[br["status"]]} → {STATUS_LABELS[rr["status"]]}.'
            if input_changed:
                explanation=(f'{LABELS.get(field,field)} 입력이 {_value(field,br["evaluated_value"])}에서 '
                             f'{_value(field,rr["evaluated_value"])}으로 바뀌었습니다. '+explanation)
            if rr['missing_fields']:
                explanation+=' 추가 확인: '+', '.join(LABELS.get(f,f) for f in rr['missing_fields'])+'.'
            rules.append(RuleComparison(rule_id=br['rule_id'],field=field,before=br,after=rr,
                input_changed=input_changed,status_changed=status_changed,explanation=explanation))
        relevant=[r for r in rules if r.input_changed]
        explanation=' '.join(r.explanation for r in relevant) if relevant else '이 정책에서 평가한 입력 조건의 변화는 없습니다.'
        if aft['missing_fields']:
            explanation+=' 변경 후에도 추가 확인할 정보: '+', '.join(LABELS.get(f,f) for f in aft['missing_fields'])+'.'
        transitions.append(PolicyTransition(policy_id=bp['policy_id'],policy_name=bp['policy_name'],
            before_status=bp['overall_status'],after_status=aft['overall_status'],
            status_changed=bp['overall_status']!=aft['overall_status'],rules=rules,explanation=explanation))
        # 전체 FAIL이어도 누락된 조건은 보존한다. 누락과 최종 UNKNOWN을 동일시하지 않는다.
        if bp['missing_fields'] or aft['missing_fields'] or 'UNKNOWN' in (bp['overall_status'],aft['overall_status']):
            unknown.append(UnknownInformation(policy_id=bp['policy_id'],before_status=bp['overall_status'],
                after_status=aft['overall_status'],before_missing_fields=bp['missing_fields'],after_missing_fields=aft['missing_fields']))
    explanations=[_amount_change(LABELS[field],differences[field]) for field in
                  ('monthly_income','monthly_rent','monthly_fixed_expenses','other_monthly_expenses') if differences[field]!=0]
    explanations += [_amount_change('월 여유자금',deltas.disposable_after_policy),_amount_change('저축 투입 상한',deltas.savable_amount)]
    if not changed: explanations.insert(0,'변경한 입력이 없어 두 시나리오의 결과가 같습니다.')
    if 'user_savings_capacity' in changed_names:
        explanations.append('사용자 저축 상한의 미입력은 별도 상한 없음, 0원은 저축하지 않음을 뜻합니다. 저축 투입 상한은 각 상황의 여유자금과 입력한 상한을 함께 반영한 금액입니다.')
    explanations.append('생활비 소득은 정책 기준의 가구소득을 대신하지 않습니다. 정책 지원금 반영은 전후 모두 0원입니다.')
    return ComparisonResponse(before=before,after=after,numeric_deltas=deltas,
        policy_transitions=transitions,changed_input_fields=changed,
        explanation_facts={'cashflow':{'before':bc,'after':ac,'numeric_deltas':deltas.model_dump()},
            'policy_rule_refs':[{'policy_id':t.policy_id,'rule_ids':[r.rule_id for r in t.rules if r.input_changed]} for t in transitions],
            'method':'DETERMINISTIC_CORE_RESULT_COMPARISON','benefit_applied_krw':0},
        explanations=explanations,unknown_information=unknown,disclaimer=DISCLAIMER)
