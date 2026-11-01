# 월 현금 혜택 Bridge 계약 — M2.3

작성일: **2026-10-21 / Asia/Seoul**. **문서 설계 전용. 코드·Enum·모델·실제 연결은 구현하지 않았다.**

최종 판단: **NEEDS_POLICY_ACCEPTANCE_CONTRACT**. 정규화 후보·중복·제외 계약은 아래와 같이 제안하되, 현재 존재하지 않는 전체 정책 범위와 운영 수용 확인을 임의 승인 값으로 대체하지 않는다. 이 문서의 향후 적용 예시는 합성 수동 사례이며 실제 정책 반영 승인이 아니다.

## 1. 목적

외부 정책 계층이 제공한 혜택 후보에서 현금흐름에 직접 반영할 수 있는 한 달의 사용 제한 없는 현금만 합산한다. 적용·제외·입력 오류를 분리하고 같은 혜택의 이중 합산을 차단한다. 결과의 의미는 **시뮬레이션상 반영 가능한 정책 혜택**이며 실제 지급 확정액·수급 보장이 아니다.

Source of Truth: CASHFLOW_ENGINE_SPEC.md 2~15·21절, backend/cashflow/models.py 및 calculator.py, POLICY_DATA_ENVELOPE_SPEC.md의 production gate·현재 구현 기록, DATA_MODEL.md 21절, ARCHITECTURE.md 23절, 실제 releases 001/002의 README와 Envelope JSON이다. 이번에는 저장소의 확인본과 구현 경계를 검토했다. 공식 사이트의 최신 내용을 다시 확인하거나 정책 금액을 새로 수집한 작업은 아니다.

## 2. Policy/Cashflow 책임 경계

| 영역 | 책임 | 수행하지 않는 일 |
|---|---|---|
| Policy Engine | 명시된 조건·사실 평가 | 혜택 지급 확정·현금흐름 산술 |
| 향후 정책 정규화 계층 | Envelope·평가·혜택 정의·운영 수용 자료를 동일 버전으로 결합, 시나리오 개인 적용·월·중복·병급 확인 | PASS만 보고 지급액 생성 |
| Benefit Bridge | 정규화 후보의 구조·일관성 검사, 유한 gate 검사, 합산·적용/제외 이유 반환 | 자격 재평가·주민등록/소득 판정·신청 승인·지급 예측·정책 원문 해석 |
| Cashflow calculator | 최종 명시적 월 현금액과 수입·지출 산술 | Bridge 호출·정책 모델 import |

Bridge의 감사 가능한 결과는 요청 안의 값 표현이다. 감사 목적을 이유로 사용자 정보의 저장·자동 로그·외부 전송을 추가하지 않는다.

## 3. Bridge input

**방식 B 추천:** PolicyEvaluation + PolicyEnvelope를 직접 받는 A는 버전·coverage·근거 추적에 유리하지만 Bridge를 정책 내부 모델과 결합한다. B는 정책 계층에서 정규화한 불변 후보만 전달한다. 대신 정규화의 진실성·원본과의 일치는 외부 정책 계층의 필수 책임이다. B의 상태 문자열이 증빙을 대신하지 않는다.

아래는 구현할 필드 확정안이 아닌 **승인 검토를 위한 최소 후보 계약**이다. 서로 독립된 gate는 하나의 approved bool로 합치지 않는다.

| CashflowBenefitCandidate 후보 필드 | 타입·의미 |
|---|---|
| policy_id | 안정 정책 ID. 기존 정책과 동일 문자열 |
| benefit_id | 정책 안의 안정 혜택 component ID |
| edition_id | 외부에서 선택한 edition. 현행 정책 규약은 4자리 연도 문자열 |
| amount_krw | 정확한 0 이상 int 또는 None. cadence 한 회의 확정 금액; None은 미확정 |
| payment_cadence | 9절의 독립 유한 후보 값 |
| benefit_medium | 8절의 독립 유한 후보 값 |
| policy_verification_status | DRAFT / VERIFIED / STALE의 정규화 값 |
| eligibility_scope | CONDITION_SLICE / FULL_POLICY의 정규화 후보 값 |
| eligibility_status | PASS / FAIL / UNKNOWN의 정규화 값 |
| acceptance_status | ACCEPTED / NOT_ACCEPTED / UNCONFIRMED의 향후 외부 수용 확인 값 |
| applicability_status | CONFIRMED / NOT_APPLICABLE / UNCONFIRMED의 개인·월 적용 확인 값 |

입력 묶음에는 별도의 작은 **BridgeContext 후보**: `target_month`(정확한 YYYY-MM, 유효 연월), `assessment_ref`(비어 있지 않은 불투명 참조 문자열)를 둔다. 호출 후보 API는 `resolve_cashflow_benefits(candidates: tuple[CashflowBenefitCandidate, ...], *, context: BridgeContext) -> CashflowBenefitBridgeResult`다. 서명도 미구현 제안이다.

한 context는 한 사람의 한 시나리오·한 달·선택된 정책/edition·고정 데이터/규칙/혜택 정의·외부 수용 검토에 대응한다. 다른 사람/월/context의 후보를 섞는 것은 정규화 계층이 차단한다. assessment_ref는 주민번호·소득·원본 프로필을 포함하지 않는다. 그 참조를 해석·조회·저장하는 기능은 Bridge에 없다. 영구 저장 없이 요청 내 검토 묶음을 가리킬 수 있다.

policy_coverage의 rule 목록은 받지 않는다. 정규화 계층이 coverage와 미구현 조건을 확인하고 scope를 제공한다. restriction_type과 savings_allowed도 별도 중복 필드로 두지 않는다. UNRESTRICTED_CASH의 의미에 자유 사용·저축 가능을 포함한다. amount_is_fixed는 amount_krw=None과 중복되어 제외한다. 원문·UserProfile·RuleEvaluation·소득을 복사하지 않는다.

## 4. Stable benefit identity

논리적 혜택 identity는 **(policy_id, benefit_id)**다. benefit_id는 정책 안에서만 유일하다. 표시명·금액·입력 순서·URL을 ID로 사용하지 않는다. 같은 정책의 현금/지역화폐 component는 서로 다른 benefit_id다. 서로 다른 정책은 같은 benefit_id 이름을 사용해도 별개 identity다.

재현용 참조는 (policy_id, edition_id, benefit_id)로 남긴다. edition을 dedupe 키에 넣어 연도별 같은 혜택을 중복 합산하도록 만들지 않는다. ID 자동 대소문자 변환·공백 제거·추측 매칭은 없다. benefit_id는 초기 후보로 기존 정책 ID와 같은 대문자/숫자/하이픈 문법을 사용한다. ID 발급·서로 다른 ID가 사실은 같은 지급원인지 확인하는 책임은 외부 데이터 관리에 있다.

## 5. Policy/edition 관계

**Assumption A1:** 호출자는 시나리오 월에 사용할 한 policy_id의 edition을 하나만 선택한다. Bridge는 최신 연도·현재 시각·분기를 자동 선택하지 않는다. 한 batch에서 같은 policy_id에 서로 다른 edition이 있으면 component가 달라도 전체 Data Error다. 제외 후보라도 충돌을 숨기지 않는다.

같은 edition에 대해서도 dataset/rule/혜택 정의·assessment가 일치해야 한다. 이 일치는 외부 정규화 계층이 context에 묶는다. 현재 001/002는 같은 edition=2026의 다른 dataset/rule snapshot이므로 동시에 사용하지 않는다. Bridge는 내부 원문·버전 객체를 받지 않아 해당 결합의 진실성을 단독 증명할 수 없다.

## 6. Eligibility gate

필수 조건은 **FULL_POLICY + PASS**다. leaf PASS·slice ALL PASS는 적용 불가다. FAIL/UNKNOWN은 정상 제외다. FULL_POLICY는 필요한 모든 행정·경제 조건과 적용 범위를 외부에서 확인했다는 향후 정규화 의미이며 단순히 현재 root를 모두 평가했다는 뜻이 아니다.

**현재 코드 사실:** EvaluationScope에는 CONDITION_SLICE만 존재한다. PolicyCoverage는 included_rule_ids와 비어 있지 않은 excluded_conditions를 요구한다. 따라서 현재 모델을 그대로 FULL_POLICY로 선언할 수 없다. 기존 Enum에 새 값 추가·빈 제외 목록 허용·coverage 승격을 이번 문서로 승인하지 않는다. 향후 정책 범위 계약을 별도로 결정해야 한다. PolicyEvaluation 단독에는 coverage가 없으므로 단독 정규화도 금지한다.

## 7. Verification gate

정책 edition의 **PolicyVerificationStatus.VERIFIED**만 검토 후보가 된다. DRAFT/STALE는 정상 제외다. SourceDocument/locator의 VerificationStatus.VERIFIED와 혼동하지 않는다. 원문 세 개가 VERIFIED여도 Envelope DRAFT는 유지된다.

VERIFIED만으로 적용하지 않는다. acceptance_status=ACCEPTED도 필요하다. POLICY_DATA_ENVELOPE_SPEC.md의 기존 production gate가 요구하는 공식 근거·참조/버전·review·manifest/artifact·freshness 검토가 해당 scenario에 유효함을 외부에서 검증해야 한다. ACTIVE 선언이나 생성자·참조 validator 성공으로 대체할 수 없다. Bridge는 시스템 시각·공식 사이트·DB를 조회하지 않는다.

**현재 production acceptance validator/workflow는 미구현**이다. ACCEPTED는 향후 정규화 결과의 후보 명칭이며 기존 Enum이 아니다. 실제 자료를 임의 ACCEPTED로 생성하는 경로는 허용하지 않는다. 기존 검토일이 언제까지 유효한지 Bridge가 자체 일수 규칙을 추가하지 않고 외부 gate가 명시적 평가 기준으로 확인해야 한다.

기존 16절 production gate의 ACCEPT(CONDITION_SLICE)는 조건 자료의 수용에 한정된다. 이것을 전체 정책 혜택 반영을 위한 ACCEPTED로 그대로 매핑하지 않는다. 향후 수용 확인은 평가 범위까지 결합해야 한다. 23절에서 한 gate만 바꾼 합성 사례는 각 필터의 독립 의미를 설명하는 값 조합이며, 실제 정규화 계층이 모순된 수용 증빙을 발급해도 된다는 뜻이 아니다.

## 8. Benefit medium

| 후보 값 | 의미 | 직접 월 현금 반영 |
|---|---|---|
| UNRESTRICTED_CASH | 사용처·목적 제한 없고 저축 가능한 비상환 현금 지원 | 다른 gate도 모두 통과하면 적용 |
| RESTRICTED_CASH_EQUIVALENT | 사용처/목적 제한 현금 또는 등가 혜택 | 제외 |
| LOCAL_CURRENCY | 지역화폐 | 제외 |
| POINTS | 포인트 | 제외 |
| VOUCHER | 바우처 | 제외 |
| IN_KIND | 현물 | 제외 |
| SAVINGS_MATCH | 잠긴 저축 매칭 지원 | 제외 |
| LOAN | 상환 의무가 있는 대출 | 제외 |
| INTEREST_SUPPORT | 이자지원 | 제외 |
| UNKNOWN | 정상적인 지급수단 미확인 | 제외 |

이는 순수 물리적 지급수단만이 아닌 **혜택 경제유형을 포함한 최소 분류**다. 대출이 현금으로 입금된다는 이유로 UNRESTRICTED_CASH로 분류하지 않는다. 현금으로 지급되는 이자지원도 이번 범위에서는 제외한다. 알 수 없는 임의 문자열은 UNKNOWN으로 자동 변환하지 않고 Data Error다. Enum은 구현하지 않는다.

## 9. Payment cadence

후보 값: MONTHLY / QUARTERLY / SEMIANNUAL / ANNUAL / ONE_TIME / IRREGULAR / UNKNOWN. **MONTHLY만 적용**한다. 다른 정상 값은 NON_MONTHLY_PAYMENT로 제외한다. 미확정 UNKNOWN도 제외하며 임의 문자열은 오류다.

분기 250,000원을 3으로 나누지 않는다. 반기/연간/일시금을 기간으로 나누지 않는다. 평균 경제효과와 해당 월 현금 유입을 구별한다. MONTHLY여도 대상 월이 지급기간 안인지 외부 applicability 확인이 필요하다. 연체·소급 입금·월 안 복수 지급은 향후 cash-event 모델에서 다루며 초기 자동 처리하지 않는다.

## 10. Amount 의미

amount_krw는 cadence와 결합한 **한 회 지급의 개인별 확정 원 단위 금액**이다. MONTHLY는 context 해당 월의 지급액, QUARTERLY는 분기 총액, ONE_TIME은 일회 총액이다. 정규화 계층도 분기액을 미리 월액으로 변환해 MONTHLY라고 보내면 안 된다.

공고 최대액·소득별 계산 미완료·범위 금액·조건 미확정은 amount_krw=None이다. 확정 0원과 구분한다. 0은 구조적으로 유효하며 다른 gate 통과 시 applied 목록에 0원으로 남겨 판단을 추적한다. 음수·bool·float·Decimal·문자열·int 하위 타입은 오류다. 정확한 int만 허용하고 상한·반올림·절삭은 없다. 큰 int 값 표현은 Python 정밀도 계약이며 브라우저 JSON Number 안전성을 보장하지 않는다.

## 11. 적용 조건

다음 조건을 **모두** 만족한 후보만 적용한다.

1. batch 구조·identity·edition·metadata 일관성이 유효하다.
2. VERIFIED, FULL_POLICY, PASS다.
3. 외부 production 수용 확인이 ACCEPTED다.
4. applicability_status=CONFIRMED다.
5. MONTHLY이고 UNRESTRICTED_CASH다.
6. amount_krw가 확정된 0 이상 정확한 int다.

CONFIRMED의 계약: 해당 사람·시나리오 월에 정책 적용과 지급 정의/기간이 외부에서 확인됨, 저축 가능한 자유 현금임, 같은 지급액이 monthly_income에 포함되지 않음, 다른 후보와 의미상 중복되지 않음, 함께 적용하는 혜택 간 병급 금지·선택형 충돌이 없음. 실제 행정 지급 승인 또는 미래 지급 예측을 의미하지 않는다. 확인할 수 없으면 UNCONFIRMED, 적용되지 않거나 이미 소득에 포함된 것으로 확인되면 NOT_APPLICABLE이다. Bridge는 소득 총액만 보고 포함 여부나 병급을 추측하지 않는다.

**Assumption A2:** 입력은 신뢰된 내부 정규화 계층에서만 온다. 사용자/LLM이 설정한 FULL_POLICY·ACCEPTED·CONFIRMED 문자열을 신뢰하는 API는 금지한다. 단순 값 모델이 이 신뢰를 인증한다고 주장하지 않는다. 원본 확인·개인 적용 검토의 구체적 검증 인터페이스는 24절 미해결 항목이다.

## 12. 제외 조건

구조가 정상인 후보가 gate 하나라도 통과하지 못하면 0원 반영으로 excluded에 남긴다. DRAFT/STALE, slice, FAIL/UNKNOWN, 미수용/수용 미확인, 월 적용 미확인, 비월 지급, 제한·비현금·대출·이자지원, 금액 미확정 모두 정상 제외다. 정책 자격 FAIL로 상태를 덮어쓰지 않는다. 단순 제외를 위한 예외를 던지지 않는다.

## 13. Duplicate 방지

**stable identity 중복은 항상 명시적 Data Error**를 추천한다. 동일 객체 반복도 예외가 아니다. idempotent dedupe는 중복 원인과 잘못된 upstream 결합을 숨길 수 있어 이번 계약에서 채택하지 않는다. input object identity나 전체 필드 equality로 dedupe하지 않는다.

구조 검사 → policy별 edition 일치 → (policy_id, benefit_id) 유일성 검사 → 정상 gate 평가 → 합산 순서다. 제외될 후보도 중복 검사를 먼저 한다. 중복이면 일부 정상 후보 합계도 반환하지 않는 전체 실패다.

## 14. Conflict 처리

같은 identity의 다른 금액·medium·cadence·status는 선택하지 않고 오류다. 같은 policy/edition의 서로 다른 component라도 policy_verification_status / eligibility_scope / eligibility_status / acceptance_status는 동일해야 한다. component별 amount/medium/cadence/applicability는 다를 수 있다. 모순된 정책 metadata는 전체 Data Error다.

서로 다른 policy_id의 같은 benefit_id는 별개라 정상이다. 서로 다른 정책·ID가 실제 동일 지급을 가리키거나 상호 배타적인 경우는 ID 검사로 알 수 없으므로 외부 정규화가 차단한다. 이 확인 없이 다른 정책이라는 이유만으로 병급 가능을 가정하지 않는다. 잘못된 내부 상태 값·누락된 필수 구조·edition 혼합은 정상 제외로 숨기지 않는다.

## 15. Bridge Result

단순 int 반환은 제외 이유를 잃으므로 **CashflowBenefitBridgeResult 후보**를 추천한다.

| 필드 | 내용 |
|---|---|
| target_month / assessment_ref | 입력 context 값 보존 |
| monthly_cash_benefit | applied 항목 금액의 정확한 int 합. 빈 입력/전부 제외면 0 |
| applied_benefits | 불변 AppliedBenefit tuple |
| excluded_benefits | 불변 ExcludedBenefit tuple |

AppliedBenefit은 (policy_id, edition_id, benefit_id, amount_krw)를 보존한다. ExcludedBenefit은 정규화 candidate 값 snapshot과 reasons tuple을 보존한다. amount/cadence/medium과 각 gate 값을 남겨 왜 제외됐는지 요청 내 추적할 수 있다. 원본 PolicyEvaluation·Envelope·개인 프로필을 보관하지 않는다. 동일 후보는 applied/excluded 중 하나에 정확히 한 번 등장한다. 금액0 applied도 포함한다.

향후 모델은 frozen/slots를 우선하며 to_dict는 새 primitive snapshot을 반환한다. 후보 Enum은 문자열, tuple은 새 list, None은 null에 대응한다. 자동 저장·로그·외부 전송은 없다. Data Error면 정상 Result를 반환하지 않는다.

## 16. Exclusion reasons

복수 이유를 모두 보존하며 다음 **고정 순서**의 중복 없는 tuple을 추천한다. 첫 이유만 남기지 않는다.

| 순서 / reason | 발생 조건 |
|---|---|
| 1 POLICY_NOT_FULLY_EVALUATED | scope != FULL_POLICY |
| 2 POLICY_NOT_VERIFIED | verification != VERIFIED |
| 3 POLICY_NOT_ACCEPTED | acceptance != ACCEPTED |
| 4 ELIGIBILITY_NOT_PASS | eligibility != PASS |
| 5 NOT_CASHFLOW_ELIGIBLE | applicability != CONFIRMED |
| 6 NON_MONTHLY_PAYMENT | cadence != MONTHLY |
| 7 RESTRICTED_MEDIUM | medium != UNRESTRICTED_CASH |
| 8 AMOUNT_NOT_FIXED | amount_krw is None |

RESTRICTED_MEDIUM은 대출·비현금·미확인 등 모든 비허용 유형도 포함하는 포괄 코드다. 원래 medium snapshot으로 구분한다. 수용/적용의 UNCONFIRMED와 명시적 부정도 snapshot으로 구별한다. 동일 코드의 세부 문구 때문에 Enum을 추가하지 않는다. 이유가 없을 때만 applied다.

## 17. Error vs exclusion

| 정상 제외 → 결과 0원 및 이유 | Data Error → batch 전체 실패 |
|---|---|
| DRAFT / STALE / slice | 알려지지 않은 Enum·내부 상태·잘못된 필수 타입 |
| FAIL / UNKNOWN | 음수·float·bool·문자열 금액 |
| 지역화폐·비월 지급·금액 None | 중복 identity·같은 정책의 edition 혼합 |
| acceptance/applicability 미확인 | 동일 policy/edition의 정책 metadata 모순 |

향후 독립 BenefitBridgeValidationError(ValueError)의 code/field를 추천한다. 모델별 구조 오류와 batch DUPLICATE_BENEFIT_IDENTITY / MIXED_POLICY_EDITIONS / CONFLICTING_POLICY_METADATA를 구별한다. 현재 CashflowValidationError 메시지는 KRW 계약 전용이므로 변경/재사용하지 않는다. 오류 문구에 원본 금액·개인 입력을 넣지 않는다. 이 오류 클래스도 이번에 구현하지 않는다.

## 18. Current Ansan example

확인한 저장소 snapshot:

| 항목 | release 001 | release 002 |
|---|---|---|
| dataset_version | ansan-youth-2026-10-20-001 | ansan-youth-2026-10-20-002 |
| edition / rule | 2026 / r0001 | 2026 / r0002 |
| Envelope 상태 | DRAFT / CONDITION_SLICE | DRAFT / CONDITION_SLICE |
| 포함 범위 | 주민등록 한 조건 | 주민등록 + Q3 생년월일 |
| 전체 적용 | 불가 | 불가 |

policy_id는 KR-GG-ANSAN-YOUTH-BASIC-INCOME이다. 002의 excluded_conditions에는 거주기간·등록분류/국적·신청창·지급 계산 등이 남아 있다. 주민등록·출생일 모두 PASS여도 전체 정책 PASS가 아니다. 현재 production 수용도 미구현이다. 따라서 **Cashflow 반영액은 반드시 0원**이다.

기존 CASHFLOW_ENGINE_SPEC.md에 기록된 청년기본소득의 지역화폐·분기 지급 의미 역시 직접 월 현금 대상에서 제외한다. 실제 Envelope에 benefit component/금액 metadata는 아직 없으므로 가짜 실제 benefit_id·확정 금액을 만들어 추가하지 않는다. 아래 수동 사례에서는 LOCAL_CURRENCY/QUARTERLY를 명시한 가상 후보로 그 제외 동작을 설명한다.

향후 현재 상태를 정규화한 후보의 예상 reasons는 최소 POLICY_NOT_FULLY_EVALUATED / POLICY_NOT_VERIFIED / POLICY_NOT_ACCEPTED다. 월 개인 적용도 확인되지 않았다면 NOT_CASHFLOW_ELIGIBLE, 분기 지역화폐 metadata가 정규화되어 있으면 NON_MONTHLY_PAYMENT / RESTRICTED_MEDIUM도 함께 남긴다. amount가 미확정이면 AMOUNT_NOT_FIXED도 남긴다. Bridge가 미구현 조건을 대신 PASS/FAIL로 결정하지 않는다.

## 19. Multiple benefits

외부에서 동시 적용·중복 없음이 확인된 서로 다른 월 현금 혜택은 합산한다. 예: 정책 A의 CASH=100,000 + 정책 B의 CASH=200,000 → 300,000원. 같은 benefit_id여도 policy_id가 다르면 별개다.

같은 정책의 CASH-A=100,000 + CASH-B=200,000도 합산한다. 같은 정책의 현금100,000 + 지역화폐50,000이면 현금만 적용하고 지역화폐만 excluded에 남긴다. 같은 정책이라는 이유로 전체를 제거하지 않는다. 정책 단위 상태는 같아야 하지만 혜택 적용 여부는 component 단위다.

## 20. Deterministic behavior

각 applied/excluded 목록은 (policy_id, benefit_id, edition_id) 문자열 오름차순으로 정렬한다. reasons는 16절 순서를 사용한다. 유효한 같은 후보 집합의 입력 순서가 바뀌어도 합계와 전체 결과 값 표현이 동일하다. 같은 입력을 반복하면 equality와 to_dict도 동일해야 한다.

검증 실패는 전체 실패다. 여러 오류가 있을 때 임의 금액이나 부분 성공 결과를 반환하지 않는다. 오류를 모두 수집하는 framework는 도입하지 않는다. 같은 입력 순서의 첫 오류는 결정적이어야 하며, 잘못된 batch의 순서 변경까지 동일 첫 오류로 보장할 필요는 없다.

시스템 시각·파일·DB·네트워크·난수·캐시·입력 변경을 사용하지 않는다. 결과 계산은 context를 명시적으로 받으며 최신 자료를 재조회하지 않는다.

## 21. What-if 관계

향후 before/after를 각각 같은 Bridge 계약으로 평가하고 각 결과 금액을 각 CashflowInput에 전달할 수 있다. 전체 범위·수용·월 적용 등 모든 gate를 통과해야 FAIL→PASS 변화가 실제 반영액 증가로 이어진다. 단순 slice PASS 변화는 계속 0원이다.

비교는 같은 대상 월·자료/규칙/혜택 정의·평가 기준을 고정한다. 개인 시나리오가 바뀌면 정규화·개인 적용 확인도 각각 다시 수행한다. 서로 다른 assessment_ref로 before/after 요청 묶음을 구분할 수 있다. 이번에는 비교 모델·delta·재평가 orchestrator·API를 구현하지 않는다.

## 22. Cashflow integration flow

```text
Policy domain + 고정 Envelope/자료 + 혜택 정의 + 외부 검토
  → 시나리오 월별 정규화 BenefitCandidate tuple + BridgeContext
  → Benefit Bridge: 구조/중복 검사 → gate → 합계·적용/제외 기록
  → 호출자가 result.monthly_cash_benefit을 명시적으로 매핑
  → 새 CashflowInput(monthly_policy_cash_benefit=해당 합계, 나머지 금액 명시)
  → 기존 calculate_cashflow()
```

calculator는 Bridge를 import/호출하지 않고 서명·모델을 변경하지 않는다. 호출자는 benefit을 이미 포함한 monthly_income을 다시 주면 안 된다. 최종 int는 승인 증거를 담지 않으므로 외부 payload의 임의 양수 금액을 신뢰하는 운영 연결은 금지한다. 현재 flow 전체는 향후 계약이며 실제 연결은 없다.

## 23. 수동 시나리오

**40개 문서상 기대값이며 신규 실행 테스트가 아니다.** 기준 V: policy_id=P-A, benefit_id=CASH-A, edition=2026, amount=100,000, MONTHLY, UNRESTRICTED_CASH, VERIFIED, FULL_POLICY, PASS, ACCEPTED, CONFIRMED. 같은 유효 context와 동시 적용 확인이 전제다. FULL_POLICY/ACCEPTED의 사용은 미래 합성 예시이며 현재 실제 모델에 생성할 수 있다는 뜻이 아니다.

| ID | 입력/변경 | 기대 |
|---|---|---|
| BB01 | V | 100,000 적용, excluded 없음 |
| BB02 | V + P-B/CASH-A 200,000 | 별개 identity, 300,000 적용 |
| BB03 | V + P-A/CASH-B 200,000 | 같은 정책 두 component, 300,000 적용 |
| BB04 | V의 verification=DRAFT | 0, POLICY_NOT_VERIFIED |
| BB05 | V의 scope=CONDITION_SLICE | 0, POLICY_NOT_FULLY_EVALUATED |
| BB06 | V의 eligibility=FAIL | 0, ELIGIBILITY_NOT_PASS |
| BB07 | V의 eligibility=UNKNOWN | 0, ELIGIBILITY_NOT_PASS |
| BB08 | V의 cadence=QUARTERLY, amount=250,000 | 0, NON_MONTHLY_PAYMENT; 나누기 없음 |
| BB09 | V의 cadence=ONE_TIME | 0, NON_MONTHLY_PAYMENT |
| BB10 | V의 cadence=ANNUAL | 0, NON_MONTHLY_PAYMENT |
| BB11 | V의 medium=LOCAL_CURRENCY | 0, RESTRICTED_MEDIUM |
| BB12 | V의 medium=VOUCHER | 0, RESTRICTED_MEDIUM |
| BB13 | V의 medium=IN_KIND | 0, RESTRICTED_MEDIUM |
| BB14 | V의 medium=SAVINGS_MATCH | 0, RESTRICTED_MEDIUM |
| BB15 | V의 medium=RESTRICTED_CASH_EQUIVALENT | 0, RESTRICTED_MEDIUM |
| BB16 | V의 amount=None | 0, AMOUNT_NOT_FIXED |
| BB17 | V를 동일 객체/동일 값으로 두 번 | DUPLICATE_BENEFIT_IDENTITY, 전체 실패 |
| BB18 | 같은 identity에 100,000과 200,000 | DUPLICATE_BENEFIT_IDENTITY, 값 선택 금지 |
| BB19 | P-A/CASH-A + P-B/CASH-A | 다른 정책 identity, 200,000 적용 |
| BB20 | P-A/CASH-A + P-A/CASH-B | 다른 component identity, 200,000 적용 |
| BB21 | V의 amount=0 | applied에 0원 한 항목, 합계0 |
| BB22 | V의 amount=-1 | 금액 Data Error, 결과 없음 |
| BB23 | V의 amount=100000.0 | 타입 Data Error, 변환 없음 |
| BB24 | V의 amount=True | 타입 Data Error, 1원으로 처리 금지 |
| BB25 | V의 amount=10**100 | 정확한 int 합계10**100 |
| BB26 | V + P-A/LOCAL medium=LOCAL_CURRENCY amount=50,000 | 적용100,000 + 제외 한 항목 |
| BB27 | V에서 DRAFT + slice + QUARTERLY + LOCAL_CURRENCY | 0; 1·2·6·7 순서의 네 이유 |
| BB28 | V + P-B/CASH-A 200,000 + P-C/CASH-A 300,000 | 동시 적용 확인 시 합계600,000 |
| BB29 | 빈 후보 tuple, 유효 context | 합계0, 두 목록 빈 tuple |
| BB30 | 현재 안산002 DRAFT/slice, 수용·월 적용 미확인인 가상 정규화 | 0, 전체 정책/검증/수용/적용 제외 |
| BB31 | BB30의 resident+birth가 모두 PASS | 여전히0; slice PASS로 승격 금지 |
| BB32 | 가상 분기 지역화폐 amount=250,000 | 0; NON_MONTHLY_PAYMENT + RESTRICTED_MEDIUM |
| BB33 | 같은 유효 입력 반복 및 순서 뒤집기 | 합계·정렬된 목록·reasons 동일 |
| BB34 | 결과 to_dict 반복, 반환 dict 수정 | 값 표현 동일, 원래 불변 결과 영향 없음 |
| BB35 | Bridge 처리 전후 input/context snapshot | 값 동일, mutation 없음 |
| BB36 | 같은 P-A의 edition2025와2026 | MIXED_POLICY_EDITIONS, 최신 자동선택 없음 |
| BB37 | V의 acceptance=UNCONFIRMED 또는 NOT_ACCEPTED | 0, POLICY_NOT_ACCEPTED |
| BB38 | V의 applicability=UNCONFIRMED 또는 NOT_APPLICABLE | 0, NOT_CASHFLOW_ELIGIBLE |
| BB39 | V의 medium=POINTS/LOAN/INTEREST_SUPPORT/UNKNOWN, 또는 cadence=SEMIANNUAL/IRREGULAR/UNKNOWN | 해당 비허용 gate로0; 임의 문자열이면 Data Error |
| BB40 | P-A/CASH-A VERIFIED + P-A/CASH-B DRAFT | CONFLICTING_POLICY_METADATA, 전체 실패 |

이 표의 apply 예시는 외부 수용·전체 범위 계약이 존재하는 미래 합성 상태를 전제한다. 현재 2810개 실행 테스트가 이 가상 Bridge를 검증했다는 뜻은 아니다.

## 24. 미해결 문제

**현재 다음 단계의 선행 차단 항목:**

1. 전체 정책 평가 범위: 현재 CONDITION_SLICE 전용 Enum/coverage와 향후 FULL_POLICY의 의미·완료 근거를 어떻게 연결할지 별도 결정해야 한다. 이번에는 모델을 변경하지 않는다.
2. 정책 운영 수용: 기존 문서의 production gate를 어떤 명시적 입력·검증 결과로 표현할지, 누가 어떤 자료/엔진/평가 기준에 대해 수용을 확인할지 결정해야 한다. ACCEPTED bool/문자열만 추가하는 것으로 해결되지 않는다.
3. 개인·월 적용과 병급·소득 중복: CONFIRMED를 발급하는 외부 정규화의 근거·context 결합을 결정해야 한다. 실제 지급 승인 예측이나 LLM 판단으로 채우면 안 된다.

**Assumption A3:** 이 작업에서는 위 항목을 미래 경계의 의무로 문서화하고 실제 연결을 막는다. 읽기 전용으로 확인한 기존 모델에서 이미 구현됐다고 가정하지 않는다. 합성 candidate 모델만 나중에 구현할 수는 있으나 현 단계 READY 판정을 내리면 수용 확인 경계가 확정됐다는 오해가 생기므로 최종 판정은 NEEDS_POLICY_ACCEPTANCE_CONTRACT다.

향후 항목: 분기·현금 이벤트·지출 대체·금융 매칭·API 금액 wire encoding은 별도 범위다. 초기 ID·중복·0원·정렬·정상 제외 의미는 이 문서에 제안했으며 별도 identity 결정을 이유로 작업을 확장하지 않는다.

ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 상태로 보류하며 공식 답변 전 Fact/Rule/Evaluator를 구현하지 않는다. 거주기간 보류를 Bridge가 우회하지 않는다.

## 25. 추천 구현 구조

향후 승인 후 최소 구조 후보만 제시하며 지금 폴더·코드·테스트는 생성하지 않는다.

```text
backend/benefit_bridge/
  models.py      독립 candidate/context/result 및 유한 값 계약
  errors.py      독립 구조·batch 오류
  bridge.py      순수 검증·정렬·gate·합산
  __init__.py    승인한 공개 API만
tests/
  test_benefit_bridge_models.py
  test_benefit_bridge.py
```

Policy Engine과 Cashflow의 형제 패키지로 두고 둘을 import하지 않는 독립 값 계약을 우선한다. 후속 정책 정규화 adapter는 필요한 수용 계약이 확정된 뒤 정책 계층에서 설계한다. 범용 rule framework·새 loader·DB·API를 선행 구현하지 않는다. 이 문서의 40개 사례는 나중에 모델/순수 Bridge/외부 연결 테스트로 구분해 실행 검증할 수 있다.

## 26. 최종 판단

**NEEDS_POLICY_ACCEPTANCE_CONTRACT**

이번 산출물은 이 문서 하나다. 중복 identity는 오류, 비허용 후보는 이유를 보존한 정상 제외, 확정된 월 자유 현금만 합산한다는 계약을 정리했다. 실제 정책이 들어올 양수 경로는 아직 열 수 없다. 특히 현재 안산001/002의 반영액은0이다.

다음 가장 작은 작업 한 개: **정규화 후보의 외부 수용 확인 계약을 문서로 확정**한다. 현재 Envelope/coverage의 표현 한계와 연결하여 수용 확인의 입력·근거 결합·미확인 결과·실제 연결 금지 경계를 정한다. 전체 정책 모델 확장·production validator·Bridge 코드 구현으로 자동 진행하지 않는다.

### 검증 기록

기존 전체 테스트 **2810 passed in 6.95s**. 신규 실행 테스트는 추가하지 않았다. 문서의 필수 26개 절과 BB01~BB40 수동 사례의 순서·누락·중복, 한국어 표기를 확인했다. Bridge 계약·실행 코드는 아직 없으므로 이 테스트 결과가 Bridge 구현을 검증한 것은 아니다. Git 저장소가 없어 git status는 조회할 수 없었으며 변경 범위는 작업 전 파일 SHA256으로 대조한다.

작업 전 backend/tests/data/docs의 기존 **95개 파일 SHA256이 모두 동일**하다. 수정·삭제는 없고 추가는 이 문서 한 개다. Cashflow 모델/계산기·Policy Engine·actual releases·synthetic 자료·기존 테스트/기대값·ResidenceHistory 관련 문서를 보존했다.
