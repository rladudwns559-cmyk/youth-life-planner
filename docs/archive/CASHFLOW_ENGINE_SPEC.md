# 월 현금흐름 엔진 입력·출력 계약 — M2.0

> 현재 구현 상태는 21절 M2.2를 따른다. 1~19절은 M2.0 설계 기록, 20절은 M2.1 모델 구현 당시 기록이다. 순수 계산 함수가 구현되었으며 benefit bridge는 미구현이다.

작성일: **2026-10-20 / Asia/Seoul**. **설계 문서 전용**. 최종 판단: **READY_TO_IMPLEMENT_CASHFLOW_MODELS**.

이번 산출물은 이 문서 하나다. Cashflow 모델·함수·API·정책 혜택 bridge를 구현하지 않는다. 기존 Policy Engine·releases·synthetic 자료·tests는 변경하지 않는다. 거주기간은 **OFFICIAL_INQUIRY_REQUIRED 상태로 보류**하며 공식 답변 전 ResidenceHistory Fact/Rule/Evaluator를 구현하지 않는다.

## 1. 목적

사용자가 명시한 한 달의 수입·지출과 별도로 검증된 현금 혜택으로 월 총수입·필수지출·기타지출·가처분액·저축투입 가능액을 결정적으로 계산할 계약을 확정한다. 적자를 숨기지 않고 같은 입력은 같은 결과를 낸다.

기획의 흐름은 경제정보 → 정책 판정 → 월 현금흐름 → 저축 가능 금액 → 예·적금 비교 → What-if다. 정책 심사용 소득과 생활비용 소득은 별개다. Python이 수치 계산을 하고 생성형 AI는 이미 계산된 결과만 설명한다. 로그인·계좌 연결·소득/월세 영구 저장·전체 입력 로그를 추가하지 않는다.

검토 기준: 기존 PROJECT_PLAN.md의 기획 PDF 요구, ARCHITECTURE.md/DATA_MODEL.md의 엔진 분리·불변 입력 원칙, 실제 Q3 DRAFT/CONDITION_SLICE 구현 기록, REAL_POLICY_001_RESIDENCE_DURATION_EVIDENCE.md의 보류 결정. 이번 범위는 현금흐름이며 금융상품 수익·세금·투자 조언은 포함하지 않는다.

## 2. 정책 엔진과 책임 분리

| 모듈 | 입력과 책임 | 범위 밖 |
|---|---|---|
| Policy Engine | 정책 Rule과 사실을 비교해 조건별 상태·근거 반환 | 월 가처분액·저축액 계산 |
| Cashflow Engine | 정규화된 월 금액만 산술 계산 | 자격 판정·정책 원문 해석·혜택 금액 추정·출처 조회 |
| 향후 Benefit bridge | 정책·혜택 정의·적용 사실·승인 자료를 검증하여 반영할 월 현금액을 명시적으로 산출 | PASS만 보고 금액 생성, 자동 분기 선택 |
| 향후 금융 계산 | cashflow의 savable_amount 등을 받아 상품 납입·만기 계산 | 현금흐름의 입력 소득을 정책 소득으로 재해석 |

Cashflow는 PolicyEvaluation이나 정책 ID별 if문을 받지 않는다. PASS/FAIL/UNKNOWN을 import하거나 현금흐름 상태로 재사용하지 않는다. Cashflow 모델은 정책 엔진 모델·UserProfile을 상속하지 않는다. 외부 검증 경계와 계산 함수의 책임을 분리하며 계산 함수가 검증된 금액의 원문 진위까지 인증한다고 주장하지 않는다.

## 3. 입력 모델

추천: 독립 frozen/slots **CashflowInput**. 다음 여섯 필드만 갖는 작은 값 모델로 시작한다. 네 필수 금액은 모두 명시해야 한다.

| 필드 | 타입 | 필수/기본값 |
|---|---|---|
| monthly_income | int, KRW, 0 이상 | 필수 |
| monthly_rent | int, KRW, 0 이상 | 필수 |
| monthly_fixed_expenses | int, KRW, 0 이상 | 필수 |
| other_monthly_expenses | int, KRW, 0 이상 | 필수 |
| user_savings_capacity | int 또는 None, 값이 있으면 0 이상 | 선택, 기본 None |
| monthly_policy_cash_benefit | int, KRW, 0 이상 | 선택, 기본 0 |

`monthly_policy_cash_benefit`은 이미 bridge에서 검증·합산된 **한 달의 사용 제한 없는 현금 반영액**이다. 정책 자격이나 payment 주기를 계산하라는 입력이 아니다. 정수만으로 승인 여부를 증명할 수 없으므로 **외부 요청에서 이 필드를 그대로 신뢰하는 서비스는 허용하지 않는다**. 실제 데이터 경계는 15절을 따른다. 현재 bridge는 미구현이고 실제 정책을 반영할 수 있는 경로는 없다.

필드 이름의 자동 별칭·문자열 숫자 변환은 없다. 원래 기획의 monthly_saving_capacity와 이번 user_savings_capacity, 다른 문서의 other_fixed_expenses는 향후 API adapter에서 의미를 확인하고 명시적으로 매핑할 수 있다. 정책 UserProfile 필드에 지출을 추가하는 작업은 이번에 하지 않는다. 새 JSON loader/Pydantic/API schema도 만들지 않는다.

## 4. 각 입력 의미

| 필드 | 정확한 의미 / 중복 방지 |
|---|---|
| monthly_income | 계산할 한 달에 생활비로 사용할 **개인 순현금 유입**. 급여 등에서 실제 사용할 금액을 호출자가 정규화해 제공. 별도 monthly_policy_cash_benefit에 넣는 금액은 제외 |
| monthly_rent | 해당 월 현금으로 부담할 월세. fixed/other에 다시 넣지 않음. 보증금·보증금 반환·일시 이사비는 초기 단일 월 정기예산에서 제외 |
| monthly_fixed_expenses | 월세를 제외한 해당 월의 정기·필수 부담. 예: 통신·정기 공과금·명시된 채무 상환 등. 저축·예금 이체는 포함하지 않음 |
| other_monthly_expenses | rent/fixed에 포함하지 않은 나머지 월 소비 예산. 변동 생활비·기타 소비 등을 호출자가 합산. 전부 필수지출이라고 이름 붙이지 않음 |
| user_savings_capacity | 그 달에 저축으로 투입하겠다고 사용자가 정한 **절대 상한**. 소득이나 이미 실행된 지출이 아님. 정책 혜택을 여기에 다시 더하지 않음 |
| monthly_policy_cash_benefit | 8·15절 요건을 만족한 별도 월 현금 유입의 정규화 합계. 월 소득에 이미 포함된 동일 지급액은 중복 반영 금지 |

**Assumption A1:** 한 입력의 모든 금액은 같은 월·같은 KRW 예산 기준이고 지출 항목은 서로 중복되지 않는다. 엔진은 정기 항목과 실제 은행 거래를 자동 분류하지 않는다. 합계만으로 같은 지출/수입이 두 번 들어갔는지 알 수 없으므로 호출자·입력 화면의 책임이다.

**Assumption A2:** 첫 MVP는 정적인 한 달 예산이다. 변동 소득의 평균·세전→세후·연봉÷12·환율·부채 상환표·보유 현금·이월 적자·이미 존재하는 저축잔액은 자동 계산하지 않는다. 월 구별용 날짜·ID도 이 함수에 필수로 추가하지 않는다. 향후 서로 다른 월을 비교하는 호출자는 어떤 월인지 별도 시나리오 metadata로 명시한다.

monthly_income은 정책의 가구소득·중위소득·공식 소득인정액이 아니다. 현재 UserProfile.monthly_income과 숫자가 같을 수 있어도 Cashflow가 PolicyFact/FactBasis를 생성하거나 역으로 정책 사실을 채우지 않는다.

## 5. 돈 타입

**MVP 선택: 원 단위 정확한 int KRW.** `type(value) is int`에 해당하는 값만 받는다. bool은 int의 하위 타입이더라도 거부한다. 음수 입력·float·Decimal·숫자 문자열·NaN/Infinity·다른 통화는 거부하며 자동 반올림·절삭하지 않는다.

Decimal은 향후 이자·세금·금리·원 미만 계산에서 별도 검토한다. 이번에는 덧셈·뺄셈·min/max만 필요하므로 도입하지 않는다. 금액 상한은 임의로 설정하지 않으며 Python 정수 범위에서 큰 값도 정확히 계산하는 계약이다. 입력 길이·요청 크기 제한은 향후 외부 API 경계의 별도 문제다.

**API 기술 쟁점:** Python int 정확성과 브라우저 JavaScript Number 정확성은 같지 않다. huge integer를 JSON Number로 전송해도 안전하다고 보장하지 않는다. 향후 API의 최대 금액 검증 또는 문자열 금액 직렬화는 HTTP 계약에서 정해야 한다. 이번 모델의 int를 편의상 float로 바꾸지 않는다. 이 후속 wire encoding 결정은 Python 모델 구현을 막지 않는다.

## 6. 지출 계산

```text
essential_monthly_expenses = monthly_rent + monthly_fixed_expenses
total_monthly_expenses = essential_monthly_expenses + other_monthly_expenses
```

지시문의 essential_expenses=rent+fixed+other 후보는 기타지출까지 필수로 부르는 문제가 있어 **총지출**과 **필수지출**을 구분한다. 산술상 가처분액을 뺄 때에는 세 지출 모두를 포함한다. 기타지출을 빠뜨려 저축 가능액이 부풀지 않게 한다.

분류는 사용자 예산 표현이며 소비의 도덕적·행정적 필수성을 엔진이 판정하지 않는다. 식비를 어느 범주에 넣을지는 입력 경계가 정하되 같은 금액을 두 군데 넣지 않는다. user_savings_capacity는 배분 상한이므로 지출에 빼지 않는다. 이미 저축으로 옮긴 금액의 실제 거래 원장은 이번 모델의 범위가 아니다.

## 7. 가처분액

```text
disposable_before_policy = monthly_income - total_monthly_expenses
policy_benefit_applied = monthly_policy_cash_benefit
total_monthly_income = monthly_income + policy_benefit_applied
disposable_after_policy = total_monthly_income - total_monthly_expenses
```

두 disposable 값은 **정상적인 음수**를 허용한다. 0으로 clamp하지 않아 적자 규모를 보존한다. benefit 적용 전후 차이는 정확히 policy_benefit_applied다. total_monthly_income은 입력 소득과 **반영된 현금 혜택만** 합한 값이다. 반영되지 않은 지역화폐·분기액의 명목 금액까지 월 총수입이라고 표시하지 않는다.

여기서 가처분액은 입력된 월 생활비를 뺀 **서비스의 월 예산 잔여액**이다. 세법·국민계정의 가처분소득이나 정책 심사용 소득이라는 뜻이 아니다. 지출 누락·사용자 추정 때문에 실제 통장 잔액과 다를 수 있다.

## 8. 정책 혜택 처리

초기 MVP는 다음을 **모두** 만족한 혜택만 반영할 수 있다.

| 조건 | 경계 |
|---|---|
| 지급수단 | 현금이며 사용처·목적 제한이 없는 금액 |
| 주기 | 해당 시나리오 월에 실제 사용할 월 지급액으로 확인됨. MONTHLY 지급만 초기 지원 |
| 저축 사용 | 자유로운 현금 잔여액으로 저축에 사용할 수 있음이 확인됨 |
| 자격·정의 | 부분조건 PASS가 아닌 필요한 전체 검증·개인 적용 확인 및 혜택 정의가 외부에서 완료됨 |
| 서비스 수용 | 향후 production acceptance 경계를 통과한 자료. VERIFIED 문자열만으로 대체하지 않음 |
| 중복 | monthly_income 또는 다른 적용 항목에 같은 지급액이 이미 포함되지 않음 |

현재 실제 001/002 정책은 DRAFT/CONDITION_SLICE이며 지역화폐 혜택이므로 **monthly_policy_cash_benefit=0**이다. leaf PASS·ALL PASS와 지급 보장/금액 적용을 연결하지 않는다. 현재 엔진은 혜택액 정의·전체 자격·운영 승인을 제공하지 않는다.

분기 지급을 3으로 나누거나 일시금을 기간으로 나눠 월 현금에 더하지 않는다. 달력으로 분기를 자동 선택하거나 현재 월에 입금됐다고 추정하지 않는다. 향후 실제 월별 지급 일정 모델이 필요할 때 별도 계약으로 확장한다.

정수 금액에만 의존하는 순수 산술 엔진은 그 금액이 공식적으로 수용 가능한지 확인하지 못한다. 따라서 개발용 합성/가상 시나리오에서는 양수 혜택 산술을 테스트할 수 있어도 **실제 정책을 승인했다는 뜻은 아니다**. 서비스의 정책 혜택 입력 경계는 독립적인 필수 선행조건이다.

## 9. 제한형 혜택 처리

| 혜택 유형 | 초기 cashflow 반영 |
|---|---|
| 월 지급·사용 제한 없는 승인 현금 | 외부 검증 후 월 cash 입력으로 가능 |
| 지역화폐·바우처·사용처 제한 현금 | **0**. 자유 현금이나 저축 투입액으로 간주하지 않음 |
| 예·적금 전용 정부 매칭/잠긴 지원금 | **0**. 월세·생활비 현금으로 사용할 수 없음 |
| 일시금·분기·연간 지급 | **0**. 월할·일할 환산 미지원 |
| 지급수단·주기·용도·적용 자격 미상 | **0 / 외부 적용 보류**. 혜택 적용이 없다는 뜻이지 정책 자격 FAIL이 아님 |

**Assumption A3:** 초기에는 제한형 혜택으로 기존 지출을 대체해 현금을 절약하는 효과도 계산하지 않는다. 사용 가능한 소비 항목·잔여 한도·이미 계획한 소비와의 매칭이 없으므로 명목 금액만큼 지출을 줄이면 과대계산할 수 있다.

제한형 혜택을 이미 식비에 썼다는 경우에도 엔진이 임의로 현금 지출을 줄이지 않는다. 입력한 금액이 총 소비예산인지 실제 현금부담액인지 명시적으로 정규화해야 하며, 중복 대체를 피하는 상세 모델은 후속이다. 비교 결과에는 필요 시 외부 계층이 반영 제외 사유를 설명한다. CashflowResult에 정책 원문·제외 혜택 목록을 복제하지 않는다.

## 10. 저축 가능액

```text
budget_surplus = max(0, disposable_after_policy)

if user_savings_capacity is None:
    savable_amount = budget_surplus
else:
    savable_amount = min(budget_surplus, user_savings_capacity)
```

명시된 capacity가 있을 때 사용자가 제시한 max(0,min(disposable_after_policy,capacity))와 같다. capacity=0은 저축 투입 0이라는 유효한 선택이고, None은 미입력으로서 다른 의미다. 누락됐다고 capacity를 0으로 바꾸지 않는다.

None일 때 잉여 전부를 계산상 상한으로 반환하는 것은 **추천 설계 선택**이다. 실제 저축 실적이나 가입 보장이 아니다. 필요한 사용자 지출이 모두 포함됐다는 Assumption 아래 **예·적금 비교에 쓸 수 있는 월 계산상 투입 가능액**을 뜻한다. 별도 capacity가 없다는 사실은 result의 None으로 보존하고 향후 화면에서 상한 추정임을 설명한다.

언제나 0<=savable_amount<=max(0,disposable_after_policy)다. capacity가 있으면 savable_amount<=capacity다. 적자를 숨기는 clamp는 disposable에 적용하지 않고 저축 투입액에만 적용한다. savings라는 배분액을 다시 지출에서 빼는 순환 계산은 없다. 투자 범위로 오해될 investable_amount 명칭은 사용하지 않는다.

## 11. 음수/0

| 입력/결과 | 계약 |
|---|---|
| income/rent/fixed/other/benefit/capacity=0 | valid. 무소득·무상거주·무지출·미적용·저축 안 함을 명시적으로 표현 |
| 위 입력 금액이 음수 | validation error. 환불·대출·계좌 조정 등을 음수 지출로 우회하지 않음 |
| disposable_before/after<0 | 정상적인 월 예산 적자. 절댓값만 따로 저장하거나 0으로 숨기지 않음 |
| savable_amount<0 | 불가능. 계산 오류 또는 결과 계약 위반 |
| capacity>잉여 | 입력 오류가 아님. 실제 계산상 잉여로 제한 |

수입 0과 미입력 None은 다르다. 경제 상태의 적자와 잘못된 입력을 구별한다. 정수 한도를 임의로 넘었다는 이유로 금액을 포화·반올림하지 않는다.

## 12. Missing/error 계약

추천: 기존 Policy 오류와 별개의 **CashflowValidationError(ValueError)**. code/field 등 안정적인 구조를 제안하며 정확한 메시지 문구는 후속 모델 구현에서 고정한다. 원래 입력값·전체 프로필을 예외 문장에 넣지 않는다.

- 필수 네 금액을 None으로 주면 validation error. 필수 생성자 인자 자체 누락은 Python TypeError로 구별할 수 있다. 향후 요청 adapter는 필수 키 누락을 자체 입력 오류로 처리한다.
- optional capacity의 누락/None만 허용한다. optional benefit은 **생략 시 0**, 명시적 None은 오류다. 혜택 미확정 객체를 이 금액 필드에 그대로 넣지 않는다.
- int 대신 float/bool/Decimal/str/list/dict 등을 주면 오류. 문자열 변환·소수점 절삭·자동 기본값 대체를 하지 않는다.
- invalid 입력에서는 정상 CashflowResult를 반환하지 않는다. 부분 계산값과 오류를 섞은 새 응답 모델이나 UNKNOWN 상태를 만들지 않는다.
- 유효하게 모든 항목을 0으로 입력한 경우에는 정상 결과 0이다.

**외부 benefit 후보의 제외**와 **engine 입력 오류**는 다르다. adapter는 restricted/분기/불완전 승인 후보를 applied 금액에서 제외하고 그 사유를 보관할 수 있다. 그런 객체가 int 전용 CashflowInput 안에 직접 들어오면 타입 오류다. 누락 지출을 0으로 채우는 것과 정책 후보를 미반영하는 것을 혼동하지 않는다.

## 13. 결과 모델

추천 frozen/slots **CashflowResult**, 필드 순서는 아래와 같다. 함수의 최소 공개 이름 후보는 calculate_cashflow(input:CashflowInput)->CashflowResult다. 아직 구현된 API가 아니다.

| 필드 | 타입 / 의미 |
|---|---|
| monthly_income | int / 정책 반영액을 제외한 입력 순현금 유입 |
| essential_monthly_expenses | int / rent+fixed |
| other_monthly_expenses | int / 별도 기타지출 |
| total_monthly_expenses | int / essential+other |
| policy_benefit_applied | int / 승인 경계에서 전달된 월 현금 반영액 |
| total_monthly_income | int / income+applied |
| disposable_before_policy | int / income-total expenses, 음수 허용 |
| disposable_after_policy | int / total income-total expenses, 음수 허용 |
| user_savings_capacity | int 또는 None / 사용자가 명시한 상한 여부 보존 |
| savable_amount | int / 위 규칙으로 제한한 0 이상 저축 투입액 |

필수지출을 월세/고정지출로 다시 나누어 결과에 중복 보관하지 않는다. 입력은 호출자가 별도로 유지할 수 있고 result가 CashflowInput 객체를 보관하지 않는다. 사용자 ID·주소·정책 ID·자격 상태·자동 생성시각·추천 금융상품·이자·원본 증빙을 넣지 않는다.

입력/결과 모델은 각 필드의 정확한 타입·부호·필수성을 검증할 수 있게 한다. 산술 정의는 이후 calculator 한 곳에 둔다. Result 생성자에서 전체 계산을 다시 실행하는 두 번째 엔진을 만들지 않고, 정책 엔진 결과 객체도 재사용하지 않는다. 후속 테스트가 함수의 산술·상한 불변조건을 검증한다.

작은 to_dict를 구현한다면 새 dict에 Python int와 None을 그대로 내보내는 값 snapshot으로 한정한다. 임의 raw payload·입력 객체를 복사하지 않는다. JSON의 wire schema나 JavaScript 정밀도 계약까지 구현됐다고 주장하지 않는다. 결과는 개인 경제정보를 포함하므로 영구 저장·자동 로그·LLM 전송을 이 문서로 허용하지 않는다.

## 14. What-if 호환성

함수는 명시적 immutable 입력만 사용하고 시간·네트워크·파일·DB·난수·전역 캐시·원본 변경 없이 계산한다. Before/After는 각각 독립 CashflowInput으로 calculate_cashflow를 호출한다. 차이는 외부 비교 계층에서 `after-before`로 구한다. 변동하지 않는 필드도 명시적으로 같은 값으로 고정한다.

저축 상한이 고정돼 있으면 소득 증가·현금 혜택 증가가 가처분액을 늘려도 savable_amount는 동일할 수 있다. 이를 오류로 보지 않는다. policy 혜택 입력을 고정한 cashflow What-if는 소득 변경에 따른 정책 자격 재판정이 아니다. 향후 전체 시나리오 orchestrator가 같은 정책 자료·승인 경계로 다시 검토한 적용액을 각 input에 명시적으로 전달해야 한다.

이번에는 ScenarioComparison 모델·delta 함수·정책 재실행·GUI slider를 만들지 않는다. 같은 input은 같은 result이며, 동일 옵션으로 직렬화하면 같은 값 표현을 얻는 계약만 정한다.

## 15. Policy Engine 인터페이스

다음은 **향후 서비스 연결 계약**이며 현재 구현된 gate가 아니다.

```text
PolicyEvaluation + 원래 PolicyEnvelope + 혜택 정의 + 개인 적용/지급 확인
  → 외부 Benefit bridge의 전체 검증
  → 해당 월의 사용 제한 없는 현금액만 중복 없이 합산
  → CashflowInput.monthly_policy_cash_benefit
  → calculate_cashflow
```

bridge의 필수 확인사항은 full eligibility 범위 충족, production acceptance, 시나리오 개인 적용 확인, 해당 월 지급 주기·금액·수단·용도 확인, 소득/다른 후보와의 중복 여부다. PolicyEvaluation에는 이 정보가 모두 없으며 **PASS 하나만으로 만들 수 없다**. CONDITION_SLICE/DRAFT는 제외한다. 정책 JSON에 새로운 FULL_POLICY 값을 임의로 넣거나 기존 승인 상태를 올리지 않는다.

현재는 그 gate·혜택 모델이 없으므로 **실제 Policy Engine 결과 → 적용 현금액은 0**이다. 금융상품·만기 계산으로 값을 전달하는 service도 없다. 양수 benefit 수치 산술은 개발용 합성/명시적 가상 시나리오로만 검증할 수 있고, 실제 사용자에게 미승인 정책을 지급 예상으로 보여주는 우회 수단이 되어서는 안 된다.

경계의 보장 한계: CashflowInput에 int를 직접 생성하면 그 수치의 승인 사실까지 증명할 수 없다. 운영 서비스에서는 외부 사용자 payload의 benefit 필드를 신뢰하지 않고 승인된 bridge가 작성해야 한다. 이번 최소 모델에 가짜 approved=True 또는 자유 문자열 full_eligibility를 붙여 신뢰 문제가 해결됐다고 하지 않는다. 실제 bridge가 준비되기 전 운영 연결을 막는 것이 명확한 경계다.

## 16. 수동 시나리오

**32개 수동 기대값이며 신규 실행 테스트가 아니다.** 기본 단위는 KRW. 기본 B는 income=2,000,000 / rent=500,000 / fixed=300,000 / other=200,000 / benefit=0 / capacity=400,000이다. 따라서 essential=800,000, other=200,000, total expenses=1,000,000, total income=2,000,000, before=after=1,000,000, savable=400,000이다.

benefit 양수 사례는 개발용 합성·가상 입력이며 실제 정책 승인 예제가 아니다. restricted/분기/DRAFT 사례는 외부 입력 경계와 엔진 산술을 구별한다. delta는 외부 수동 비교의 기대이며 비교 함수를 구현했다는 뜻이 아니다.

| ID | 입력 변화 / 점검 | 기대 |
|---|---|---|
| CF01 | B 정상 흑자 | disposable=1,000,000, savable=400,000 |
| CF02 | income=1,000,000 | before=after=0, savable=0 |
| CF03 | income=800,000 | before=after=-200,000, savable=0 |
| CF04 | rent=0 | essential=300,000, total expense=500,000, disposable=1,500,000, savable=400,000 |
| CF05 | income=0 | disposable=-1,000,000, savable=0 |
| CF06 | benefit=0 명시 | B와 동일. 누락 기본 0과 같음 |
| CF07 | 합성 benefit=100,000 | total income=2,100,000, before=1,000,000, after=1,100,000, savable=400,000 |
| CF08 | 외부 restricted benefit 후보=250,000 | adapter에서 반영 0, engine은 B. 제한형 객체를 금액 필드로 주면 타입 오류 |
| CF09 | capacity=200,000 | savable=200,000 |
| CF10 | capacity=1,500,000 | savable=1,000,000, 초과 상한 입력 자체는 valid |
| CF11 | capacity=0 | savable=0. None과 다름 |
| CF12 | capacity=None 또는 생략 | disposable=1,000,000, savable=1,000,000의 계산상 상한, result capacity=None |
| CF13 | CF03에 capacity=None | disposable=-200,000 보존, savable=0 |
| CF14 | income=-1 | validation error, 정상 result 없음 |
| CF15 | rent=-1 | validation error |
| CF16 | fixed=-1 또는 other=-1 | 각각 validation error |
| CF17 | income=10**30, 모든 지출=0, capacity=None | total income=disposable=savable=10**30, 정수 정확성 유지 |
| CF18 | 금액에 2000000.0 또는 0.1 | float 타입 오류, 반올림 안 함 |
| CF19 | 금액 또는 capacity에 True/False | bool 타입 오류, 0/1로 해석 안 함 |
| CF20 | 필수 income 인자 누락 / None | 각각 TypeError / validation error, 0 대체 없음 |
| CF21 | 필수 rent/fixed/other 중 하나 누락 / None | 각각 오류. 지출 0을 추정하지 않음 |
| CF22 | B before → benefit=100,000 after | disposable delta=+100,000, savable delta=0 |
| CF23 | B before → rent=700,000 after | disposable delta=-200,000, after=800,000, savable delta=0 |
| CF24 | B before → income=2,300,000 after, 양쪽 capacity=None | disposable/savable delta=+300,000 |
| CF25 | B before → other=1,400,000 after | total expense=2,200,000, disposable=-200,000, savable=0, disposable delta=-1,200,000 / savable delta=-400,000 |
| CF26 | 같은 B 반복 계산·to_dict | 전체 결과 값 동일, 원본 입력·결과 불변 |
| CF27 | income/rent/fixed/other/benefit=0, capacity=None | 모든 합계·disposable·savable=0 |
| CF28 | benefit=-1 / 명시적 None | 각각 validation error. 생략 기본 0과 구별 |
| CF29 | capacity=-1 / Decimal / 숫자 문자열 | 각각 validation error, 자동 변환 없음 |
| CF30 | 외부 분기 현금 300,000 또는 일시금 1,200,000 | 초기 adapter 반영 0. 100,000 월할 금액으로 만들지 않음 |
| CF31 | 현재 실제 Q3 CONDITION_SLICE 결과 PASS | 적용액 0. 기존 DRAFT/지역화폐와 전체 자격 미확정 경계 유지 |
| CF32 | income=800,000, 합성 월 현금 benefit=300,000, capacity=None | before=-200,000, after=100,000, total income=1,100,000, savable=100,000 |

후속 테스트는 각 금액 필드의 정확한 int/0/음수/잘못된 타입, capacity None/0, 적자 보존, 상한 불변조건, 반복 결과·입력 불변성을 의미 있게 검증한다. 문서 표를 임의로 실행된 pytest 수로 보고하지 않는다.

## 17. 미해결 문제

| 항목 | 현재 선택 / 미해결 / 모델 구현 영향 |
|---|---|
| 한 달 기준 | 정적 월 예산·동일 통화·중복 없는 합계라는 Assumption A1/A2. 거래 자동 분류는 미지원 |
| 필수/기타 분류 | rent+fixed를 필수로 표시, other는 별도. 총지출에는 모두 포함하는 설계로 확정 |
| capacity None | 잉여의 0 이상 금액을 계산상 상한으로 반환. actual 저축 보장 아님 |
| Benefit MVP | 사용 제한 없는 월 현금만, 나머지 0. 계산 입력 semantics는 확정 |
| 실제 benefit bridge | full eligibility·production acceptance·개인 적용·지급 정의가 미구현. 운영 연결 차단, 실제 반영액 0 |
| 제한형 대체 효과 | 소비 항목 매칭·잔여 한도·현금 대체 계산은 후속. 이번에는 미반영 |
| API 금액 encoding | huge int와 TypeScript 정밀도를 위한 wire 계약 미정. Python 모델 범위와 구별 |
| 월별 일정·비정기금 | 일시금·분기·연간·변동 소득 정규화와 실제 지급일 추적은 후속 |
| 금융상품 | 납입한도·금리·세금·만기·초기 원금은 별도 금융 계산 계약 |
| 거주기간 | OFFICIAL_INQUIRY_REQUIRED 유지. 공식 답변 전 관련 Fact/Rule/Evaluator 구현 안 함 |

위 후속 문제가 현재 작은 CashflowInput/Result의 수치·필수성·타입·계산상 의미를 모호하게 만들지는 않는다. 실제 혜택을 적용할 수 없는 상태와 합성 금액으로 순수 계산 모델을 구현할 준비 상태는 구별한다.

## 18. 추천 구현 구조

다음은 **후속 제안**이며 이번에 폴더·코드를 만들지 않는다.

```text
backend/cashflow/
  __init__.py       승인된 최소 모델/함수만 공개
  models.py         독립 CashflowInput / CashflowResult / 입력 오류
  calculator.py     후속 단일 순수 calculate_cashflow
tests/
  test_cashflow_models.py       다음 모델 milestone
  test_cashflow_calculator.py   그 다음 산술 milestone
```

첫 구현은 **입력·결과 값 모델과 타입·필수성·불변성 테스트만**으로 작게 진행한다. 계산 함수·정책 bridge·실제 혜택 연결·What-if 비교·API/UI/DB/LLM은 자동 포함하지 않는다. 기존 Policy Engine 파일을 공통 모델 프레임워크로 재설계하지 않는다. 다음 calculator에서는 이 문서의 수식을 한 곳에서 구현하고 의미 있는 경계 테스트로 검증한다.

## 19. 최종 판단

**READY_TO_IMPLEMENT_CASHFLOW_MODELS**

입력 6개, 결과 10개, 정확한 int KRW, 적자 보존, capacity None/0의 구별, 사용 제한 없는 월 현금만의 입력 경계, 실제 DRAFT 혜택 적용 금지, 순수 함수/What-if 재현성, 32개 수동 사례를 정리했다. benefit 계산 의미를 임의로 넓히지 않고 실제 서비스 연결은 아직 차단한다.

**다음 가장 작은 작업 1개:** 승인 후 독립 CashflowInput/CashflowResult와 오류·검증·불변성 테스트만 구현한다. calculate_cashflow·Policy benefit bridge·ResidenceHistory·실제 release 변경은 포함하지 않는다.

### M2.0 검증 기록

작업 전 전체 pytest: **2372 passed in 6.51s**. 새 실행 테스트·모델·계산 코드·실제 데이터 변경은 없다. 문서 형식·전체 회귀·기존 파일 SHA256 대조 결과는 아래에 기록한다.

작성 후 전체 pytest: **2372 passed in 6.26s**. 기존 backend/tests/data/docs **88개 파일 전부 SHA256 동일**, 추가 파일은 이 문서 하나다. 기존 Policy Engine·두 실제 releases·synthetic 자료·테스트와 기대값·기존 문서를 보존했다. 19개 필수 절, CF01~CF32의 순서·중복·누락, 입력 6개/결과 10개 및 문서 언어를 확인했다. 이는 문서 형식·기존 회귀 검증이며 새 Cashflow 구현의 테스트 통과를 의미하지 않는다.

## 20. M2.1 — IMPLEMENTED: 불변 Cashflow 값 모델

backend/cashflow/models.py에 CashflowInput/CashflowResult를 frozen/slots dataclass로 구현했다. errors.py의 CashflowValidationError는 ValueError를 직접 상속한다. __init__.py는 두 모델과 오류만 공개한다. Policy Engine import·공통 프레임워크·외부 의존성은 없다.

Input은 3절의 정확한 여섯 필드와 순서를 따른다. 네 필수 금액은 정확한 0 이상 int다. user_savings_capacity 기본값은 None, monthly_policy_cash_benefit 기본값은 0이며 명시적 None은 거부한다. Result는 13절의 정확한 열 필드와 순서를 따르고 **열 인자 모두 필수**다. capacity 인자도 명시해야 하되 값으로 None을 허용한다.

공유된 작은 KRW validator가 bool/int 하위 타입/IntEnum/float/Decimal/str/list/dict/None 등 잘못된 타입을 거부하고 음수 금액을 거부한다. Result의 disposable_before_policy/disposable_after_policy만 음수 int를 허용한다. 금액 상한·환산·절삭·반올림은 없고 큰 int도 그대로 보존한다.

오류 code는 INVALID_KRW_TYPE / NEGATIVE_KRW_AMOUNT, field는 해당 정확한 모델 필드명이다. 원본 금액·전체 payload를 오류 문장에 넣지 않는다. 필수 인자 누락/정의되지 않은 keyword는 Python TypeError다. PASS/FAIL/UNKNOWN 상태는 없다.

Result constructor는 타입·부호만 검증한다. 합계·가처분액·savable_amount와 capacity/잉여 사이의 산술 관계를 다시 계산하지 않는다. 구조적으로 유효한 수동 snapshot이 계산적으로 올바르다는 보장은 아니다. 10절 상한 관계를 포함한 산술 정확성은 다음 calculator의 단일 책임이다. 이 경계를 테스트로 명시했다.

to_dict는 필드 순서를 유지한 **새 dict**에 int/None만 보존한다. 값 snapshot이며 JSON 입력 parser·API wire schema가 아니다. 생성 후 필드 변경/삭제는 거부되고 입력/결과 equality·결정적 값 표현·snapshot 변경의 독립성을 검증했다. 사용자 정보 저장·자동 로그·LLM 전송 기능은 없다.

정책 현금액의 양수 값은 구조적으로 담을 수 있지만 실제 정책 승인·지급 사실을 검증하지 않는다. 현재 DRAFT/CONDITION_SLICE의 혜택 반영 금지와 실제 benefit bridge 미구현 경계는 유지한다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 계속 보류한다.

IMPLEMENTED: CashflowInput, CashflowResult, strict KRW/optional 검증, 독립 오류, 불변성, 작은 to_dict, 모델 단위 테스트.

NOT IMPLEMENTED: calculate_cashflow, benefit bridge, 정책 eligibility 연결, restricted benefit 계산, What-if, 금융상품, FastAPI/React.

검증: 작업 전 **2372 passed in 7.91s**, 신규 tests/test_cashflow_models.py **360 passed in 0.78s**. 각 필드의 exact int·0/음수·None·큰 정수·필수성, 적자 보존, 불변성·새 snapshot·오류 메시지, 정책 엔진 import를 차단한 독립 프로세스에서 import/생성을 검증했다. 실제 계산 테스트는 아니다. 최종 전체 회귀·파일 대조 결과는 아래 기록을 따른다.

최종 판단: **READY_TO_IMPLEMENT_CASHFLOW_CALCULATION**. 다음 가장 작은 작업 한 개는 calculate_cashflow(input) 순수 함수와 승인된 수식·적자/저축 상한·capacity None 경계 테스트를 구현하는 것이다. bridge/정책 혜택 연결·What-if·금융상품·ResidenceHistory는 포함하지 않는다.

### M2.1 최종 검증 기록

완료 기록일: **2026-10-21 / Asia/Seoul**. 최종 전체 pytest는 **2732 passed in 6.71s**다. 기존 2372개 테스트·기대값을 수정하지 않고 신규 모델 테스트 360개를 추가했다. 작업 전 backend/tests/data/docs 89개 파일의 SHA256과 대조하여 승인된 문서 세 개만 변경했고 나머지 **86개는 동일**하다. 신규 파일은 독립 Cashflow 패키지 세 파일과 테스트 한 파일, 총 네 개다.

기존 Policy Engine·actual releases·synthetic 자료·ResidenceHistory 관련 문서·모든 기존 테스트 파일은 바이트 단위 동일하다. 신규 소스의 문법·한국어 문서·Policy Engine import 부재·calculate_cashflow 부재를 확인했다. 계산 함수·benefit bridge·What-if·금융상품 구현은 없으며 실제 정책 혜택 승인도 수행하지 않는다.

## 21. M2.2 — IMPLEMENTED: 순수 월 현금흐름 계산

공개 API는 `from backend.cashflow.calculator import calculate_cashflow`이며 서명은 `calculate_cashflow(cashflow_input: CashflowInput) -> CashflowResult`다. 인자를 추가하지 않았다. 패키지 최상위의 기존 models/errors 공개 계약과 기존 테스트를 보존하기 위해 선택 사항인 __init__.py 재공개는 추가하지 않았다.

기존 evaluator의 exact 객체 타입 경계와 일관되게 CashflowInput 이외 객체와 하위 타입은 기존 CashflowValidationError로 거부한다. code는 INVALID_CASHFLOW_INPUT_TYPE, field는 cashflow_input이다. 원본 값을 예외에 넣지 않으며 필드별 생성자 검증은 복제하지 않는다. 기존 모델·오류 파일은 변경하지 않았다.

```text
essential_monthly_expenses = monthly_rent + monthly_fixed_expenses
total_monthly_expenses = essential_monthly_expenses + other_monthly_expenses
policy_benefit_applied = monthly_policy_cash_benefit
total_monthly_income = monthly_income + policy_benefit_applied
disposable_before_policy = monthly_income - total_monthly_expenses
disposable_after_policy = total_monthly_income - total_monthly_expenses
capacity is None: savable_amount = max(0, disposable_after_policy)
capacity is int:  savable_amount = max(0, min(disposable_after_policy, capacity))
```

두 가처분액은 음수여도 보존한다. capacity=0은 잉여와 무관하게 저축 투입 0이며 None은 잉여 상한 계산이다. 저축 투입액은 실제 저축 실적·상품 가입 보장이 아니다. 결과 열 필드를 모두 채우고 monthly_income/other_monthly_expenses/user_savings_capacity 의미를 보존한다. Python int 산술만 사용하며 환산·반올림·인위적인 최대 금액 제한은 없다.

계산 함수는 로컬 모델·오류만 import한다. 정책 상태·실제 releases·사용자 프로필·시각·DB·파일·네트워크·난수·변경 가능한 전역 상태에 의존하지 않으며 입력을 변경하지 않는다. 양수 benefit은 외부에서 정규화한 가상 월 현금액 산술을 검증한다. 계산이 혜택 승인이나 자격 확인을 대신하지 않는다. 현재 실제 DRAFT/CONDITION_SLICE·지역화폐의 자동 적용 경로는 없고 분기액 월할·지출 대체도 없다.

IMPLEMENTED: calculate_cashflow, 결정적 월 현금흐름 계산, 적자 보존, 저축 상한 계산, 독립 계산 테스트.

NOT IMPLEMENTED: benefit bridge, 실제 정책 결과 연결, restricted benefit 효과, What-if 비교, 금융상품, FastAPI/React. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 상태로 계속 보류한다.

검증: 작업 전 전체 **2732 passed in 6.85s**, 신규 tests/test_cashflow_calculator.py **78 passed in 0.38s**. 수동 예제의 열 필드, 흑자/손익분기/적자/혜택으로 적자 해소, 10**100 산술, None/0/작은·같은·큰 capacity, 여섯 산술 불변식, 반복 결과·snapshot 동일성, 입력 보존·결과 불변성을 확인했다. 별도 프로세스에서 Policy Engine import를 차단하고 파일 열기·socket·난수·시각 호출을 실패 처리한 상태로 계산했다. 이 검증은 운영 정책 혜택 승인을 의미하지 않는다.

최종 판단: **READY_FOR_CASHFLOW_BENEFIT_BRIDGE**. 다음 가장 작은 작업 한 개는 benefit bridge의 입력·반영 제외·중복 방지 계약을 설계하는 것이다. 실제 정책 적용·운영 수용을 승인한 것으로 해석하지 않는다.

### M2.2 최종 검증 기록

완료 기록일: **2026-10-21 / Asia/Seoul**. 전체 pytest는 **2810 passed in 6.98s**로 기존 2732개와 신규 78개가 모두 통과했다. Git 저장소가 없어 git status는 확인할 수 없었으며 작업 전 backend/tests/data/docs의 93개 파일 SHA256으로 변경 범위를 대조했다. 문서 두 개만 변경했고 기존 **91개 파일은 동일**, 새 파일은 calculator와 계산 테스트 두 개, 삭제는 없다. 기존 테스트·기대값·Cashflow 모델/오류/최상위 export·Policy Engine·실제 releases·합성 자료를 변경하지 않았다. 변경 파일의 한국어 표기와 계산 함수의 외부 의존 부재를 확인했다.
