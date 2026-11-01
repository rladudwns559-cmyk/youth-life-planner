# 진행자 전용 정답·채점표

Source of Truth: study_v2/private/study_key.json. 문항·보기·정답·채점은 수정하지 않았다. 참가자에게 이 문서를 보여주지 않는다.

각 문항1점, 정확 일치만 인정. 다중 선택은 정답 집합 전체가 같아야1점, 부분점수 없음. 빈칸은 원자료에서 빈칸, DK는 별도 응답이며 오답 비득점. NONE은 미응답과 다르다.

## T01 / EX01 — 입력 유지

- q1: 월 여유자금은 얼마나 변했나요?
  정답: 0원 / 변화 없음
  근거 필드: `money_facts.disposable_after_policy.delta` / 범주: `money`
- q2: 변경 후 SAMPLE-001의 표시 상태는 무엇인가요?
  정답: 이용 가능성 높음 (PASS)
  근거 필드: `policy_facts.SAMPLE-001.after_status` / 범주: `policy`
- q3: 이 합성 결과의 PASS만으로 실제 지원금 수령이 확정되나요?
  정답: 아니요. 실제 자격·수령 확정이 아니며 지원금 반영도0원이다
  근거 필드: `synthetic/test_only/benefit_applied_krw0 + disclaimer` / 범주: `certainty`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`

## T02 / EX02 — 취업 상태 변경

- q1: 월 여유자금은 얼마나 변했나요?
  정답: 0원 / 변화 없음
  근거 필드: `money_facts.disposable_after_policy.delta` / 범주: `money`
- q2: 변경 후 SAMPLE-002의 표시 상태는 무엇인가요?
  정답: 현재 조건과 맞지 않음 (FAIL)
  근거 필드: `policy_facts.SAMPLE-002.after_status` / 범주: `policy`
- q3: SAMPLE-002의 결과가 바뀐 직접 조건은?
  정답: 미취업에서 취업으로 변경
  근거 필드: `SAMPLE-002.rules: FAIL + input_changed` / 범주: `reason`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`

## T03 / EX04 — 취업 정보 미입력

- q1: 월 여유자금은 얼마나 변했나요?
  정답: 0원 / 변화 없음
  근거 필드: `money_facts.disposable_after_policy.delta` / 범주: `money`
- q2: 변경 후 SAMPLE-002의 표시 상태는 무엇인가요?
  정답: 추가 확인 필요 (UNKNOWN)
  근거 필드: `policy_facts.SAMPLE-002.after_status` / 범주: `policy`
- q3: 취업 상태를 입력하지 않은 SAMPLE-002를 어떻게 해석해야 하나요?
  정답: 판단할 정보가 없어 추가 확인한다
  근거 필드: `SAMPLE-002.rules UNKNOWN/MISSING_FIELD` / 범주: `unknown`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 취업 상태 / 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`

## T04 / EX07 — 월소득 증가

- q1: 월 여유자금은 얼마나 변했나요?
  정답: +300,000원
  근거 필드: `money_facts.disposable_after_policy.delta` / 범주: `money`
- q2: 변경 후 SAMPLE-003의 표시 상태는 무엇인가요?
  정답: 추가 확인 필요 (UNKNOWN)
  근거 필드: `policy_facts.SAMPLE-003.after_status` / 범주: `policy`
- q3: 개인 월소득이 늘었는데 SAMPLE-003이 UNKNOWN인 이유는?
  정답: 정책 가구소득 정보가 여전히 없으며 개인 월소득과 다르다
  근거 필드: `SAMPLE-003.household_income MISSING_FIELD + assumptions` / 범주: `unknown`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`

## T05 / EX09 — 월세 증가

- q1: 월 여유자금은 얼마나 변했나요?
  정답: -100,000원
  근거 필드: `money_facts.disposable_after_policy.delta` / 범주: `money`
- q2: 변경 후 SAMPLE-003의 표시 상태는 무엇인가요?
  정답: 추가 확인 필요 (UNKNOWN)
  근거 필드: `policy_facts.SAMPLE-003.after_status` / 범주: `policy`
- q3: 여유자금 감소를 만든 입력 변화는?
  정답: 월세 증가
  근거 필드: `changed_input_fields/monthly_rent` / 범주: `reason`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`

## T06 / EX11 — 저축 투입 상한 증가

- q1: 저축 투입 가능액은 얼마나 변했나요?
  정답: +200,000원
  근거 필드: `money_facts.savable_amount.delta` / 범주: `money`
- q2: 변경 후 SAMPLE-003의 표시 상태는 무엇인가요?
  정답: 추가 확인 필요 (UNKNOWN)
  근거 필드: `policy_facts.SAMPLE-003.after_status` / 범주: `policy`
- q3: 저축 투입 가능액 증가를 어떻게 해석해야 하나요?
  정답: 여유자금은 그대로이며 사용자가 설정한 저축 상한이 증가했다
  근거 필드: `user_savings_capacity delta + disposable delta0` / 범주: `reason`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`

## T07 / EX12 — 월소득 감소와 적자

- q1: 변경 후 월 여유자금은 얼마인가요?
  정답: -900,000원
  근거 필드: `money_facts.disposable_after_policy.after` / 범주: `money`
- q2: 변경 후 SAMPLE-003의 표시 상태는 무엇인가요?
  정답: 추가 확인 필요 (UNKNOWN)
  근거 필드: `policy_facts.SAMPLE-003.after_status` / 범주: `policy`
- q3: 적자일 때 저축 투입 가능액0은 무엇을 뜻하나요?
  정답: 여유자금 적자는 남고 저축 투입 가능액만0으로 제한된다
  근거 필드: `disposable_after_policy<0, savable_amount0` / 범주: `money`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`

## T08 / FU01 — 소득·월세·취업 동시 변경

- q1: 월 여유자금은 얼마나 변했나요?
  정답: +200,000원
  근거 필드: `money_facts.disposable_after_policy.delta` / 범주: `money`
- q2: 변경 후 SAMPLE-002의 표시 상태는 무엇인가요?
  정답: 현재 조건과 맞지 않음 (FAIL)
  근거 필드: `policy_facts.SAMPLE-002.after_status` / 범주: `policy`
- q3: 이 합성 결과의 PASS만으로 실제 지원금 수령이 확정되나요?
  정답: 아니요. 실제 자격·수령 확정이 아니며 지원금 반영도0원이다
  근거 필드: `synthetic/test_only/benefit_applied_krw0 + disclaimer` / 범주: `certainty`
- q4: 변경 후 UNKNOWN 조건을 판단하려면 어떤 누락 정보를 더 확인해야 하나요? 모두 선택하세요.
  정답: 정책 기준의 가구소득
  근거 필드: `unknown_information[].after_missing_fields 합집합` / 범주: `confirmation`
