# Benefit Snapshot 정의·출처·지문 계약 — M2.42

> 현재 구현 상태는 **37절 M2.44**를 따른다.1~35절은 M2.42 설계,36절은 M2.43 모델 구현 기록이다. BenefitSnapshot/4개 Enum과 전용 지문·BV 실행 테스트를 구현했고 Acceptance·Bridge는 아직 없다. 현재 최종 판단은 **READY_FOR_BENEFIT_ACCEPTANCE_MODEL_DESIGN**이다.

작성일: **2026-10-22 / Asia/Seoul**. **문서 전용**. 최종 판단: **READY_TO_IMPLEMENT_BENEFIT_SNAPSHOT_MODEL**.

이번 변경은 이 문서 한 개 추가다. 아래 타입·Enum·필드·함수는 **승인 검토를 위한 후속 구현 계약**이다. 모델/지문 함수/Acceptance/Bridge를 구현하지 않았고 실제 정책 snapshot·혜택 금액·승인 기록을 만들지 않았다.

## 1. 목적과 기존 계약 확인

Acceptance가 “정확히 어떤 policy/scope/benefit/version의 어떤 금액·주기·수단·제한·월·근거를 검토했는가”를 결정적으로 식별하도록 정의 단위를 고정한다. 정의 내용, 배포 provenance, 검토 행위, 개인별 경제 계산을 분리한다.

| 다시 확인한 Source of Truth | 적용한 현재 계약 |
|---|---|
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md | stable ID·scope·Coverage9개 binding·혜택 version/fingerprint 필요성·검토/Bridge 경계 |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md | accepted_terms 기존 이름, 고정 int≥0·명시 YYYY-MM·근거·기한·별도 실제 검토 |
| CASHFLOW_BENEFIT_BRIDGE_SPEC.md | cadence7개·medium10개, stable dedupe, 무환산·개인/월 적용·0원 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | generic core 동결·FULL≠Verification/Acceptance·실제 정책별 blocker |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md | 기존 ApplicabilityScope·현재 baseline·공식 Result 경로·same-version 모순 경계 |
| POLICY_DATA_ENVELOPE_SPEC.md | SourceBinding·document/dataset version·별도 Registry·immutable release·freshness 의무 |
| COVERAGE_FINGERPRINT_SPEC.md | explicit payload·version 포함·근거 순서 보존·canonical JSON/strict UTF-8/SHA256 |
| DATA_MODEL.md / ARCHITECTURE.md | 독립 Cashflow와 Coverage 구현 상태, 사용자 경제정보 비영구 저장 |

현재 backend에는 BenefitCandidate/BenefitSnapshot/Benefit 관련 Enum·version 계약이 없다. 따라서 기존 **개념 이름과 taxonomy**를 유지하면서 아래 최소 타입 이름을 제안한다. `BenefitSnapshot`, `BenefitAmountType`, `BenefitPaymentCadence`, `BenefitMedium`, `BenefitRestriction`다. 기존 SourceBinding/ApplicabilityScope/parse_evidence_ref는 재사용한다.

현재 `parse_evidence_ref`는 형식만 검사하며, `validate_evidence_refs`는 명시 Registry에 대한 중복/존재/참조 수명까지 검사한다. Snapshot 생성에는 전자만 사용한다. Registry 지문은 기존 `fingerprint_source_registry`이며 전체 source metadata 확인본을 뜻한다. Cashflow의 exact int 관례는 따르되 Cashflow private validator를 import하지 않는다.

이번 계약은 M2.41의 미확정 Benefit 필드·version·지문·검토 연결을 구체화한다. frozen Coverage와 Bridge 지원 유형·금액 산술은 변경하지 않는다.

## 2. 정확한 의미와 확정 필드

BenefitSnapshot은 **특정 policy/scope의 특정 혜택을 시스템이 어떤 정의로 이해하는지 고정한 불변 값**이다. Acceptance record·실제 사용자 지급액·자격 결과·행정 승인·Bridge 결과·Cashflow 입력·검토 수행 사실이 아니다.

후속 모델은 다음 **16개 필드를 모두 keyword-only 필수 인자**로 받는 방향을 확정한다. nullable 값도 생략/default로 채우지 않고 명시한다. 표의 순서는 저장/일반 to_dict 순서이며 지문 JSON의 key 정렬과 구별한다.

| 필드 | 정확한 타입·계약 |
|---|---|
| policy_id | exact str, `[A-Z0-9]+(?:-[A-Z0-9]+)*` |
| scope | exact 기존 ApplicabilityScope, 원래 값 보존 |
| benefit_id | exact str, policy_id와 같은 canonical 문법 |
| benefit_version | exact str,6절의 b version |
| amount_type | exact BenefitAmountType |
| amount_krw | exact int≥0 또는 None,8절의 교차 규칙 |
| amount_description | exact 비공백 str 또는 None,8절의 교차 규칙 |
| payment_cadence | exact BenefitPaymentCadence |
| benefit_medium | exact BenefitMedium |
| restriction | exact BenefitRestriction |
| restriction_details | exact 비공백 str 또는 None,11절의 교차 규칙 |
| applicable_months | exact 비어 있지 않은 정렬·유일 YYYY-MM str tuple 또는 None |
| benefit_evidence_refs | exact 비어 있지 않은 canonical ref str tuple, 순서/중복 보존 |
| source_bindings | exact 비어 있지 않은 기존 SourceBinding tuple, source ID 유일·오름차순 |
| dataset_version | exact 비공백 str, 현재 선택 release ID |
| source_registry_fingerprint | exact 소문자16진64자리 str, 선택 Registry 전체 지문 |

benefit_fingerprint는 저장 필드/생성 인자가 아니다. 별도 전용 순수 함수로 계산한다. currency는 `_krw`와 계약으로 KRW에 고정하여 별도 Enum을 만들지 않는다. schema/status/review/current date/사용자 값도 모델에 넣지 않는다.

## 3. Stable identity와 component 분리

stable benefit identity는 **`(policy_id, benefit_id)`**다. scope·edition·amount·version·URL·표시명 변경만으로 새 benefit_id를 발급하지 않는다. 금액/수단이 바뀌어도 같은 지원 component의 제도 개정이면 같은 계보와 새 version을 사용할 수 있다.

공식적으로 별개 지원이 신설되었거나 독립적으로 동시 지급/제외할 수 있는 component로 분리된 경우 새 benefit_id를 발급한다. 현금+포인트, 기본 지급+별도 추가 지급처럼 경제적으로 다른 component는 각각 별도 benefit_id로 나눈다. 금액만 다른 개인 경로를 근거 없이 새 ID로 쪼개 이중 합산하지 않는다. 계보/중복의 실제 의미는 외부 검토 책임이다.

같은 정책의 여러 혜택은 독립 Snapshot/Acceptance를 가진다. 하나의 승인으로 정책의 모든 component를 승인하지 않는다. dataset 내 동일 대상/version 중복은 같은 값이어도 오류이며 조용한 dedupe는 금지한다. 한 실행에서 같은 stable benefit을 여러 scope/version으로 중복 반영하지 않는 Bridge 원칙은 유지한다.

단일 Snapshot 모델은 collection 중복을 알 수 없다. 지금 별도 BenefitSnapshotCollection/index/loader를 만들지 않는다. 향후 batch 준비에서 uniqueness를 검사하고 명시적으로 한 확인본을 선택한다. 이력 보관에서 다른 version을 함께 갖는 것과 실행 batch 선택은 구별한다.

## 4. Snapshot identity의 두 차원

| 차원 | identity / 역할 |
|---|---|
| 정의 version identity | `(policy_id, scope, benefit_id, benefit_version)` |
| 정의 내용 식별 | 위 identity + 계산한 `benefit_fingerprint` |
| 배포 확인본 식별 | 위 값 + `dataset_version`, `source_registry_fingerprint` |

정의 지문은 의미 있는 값과 **그 정의가 사용하는 refs/document versions**를 고정한다. 배포 ID·Registry 전체 지문은 해당 정의를 어느 불변 자료 묶음에서 사용했는지를 고정한다. 이 두 provenance 필드는 모델에 보존하지만 정의 지문에는 넣지 않는 결정을20·23절에 설명한다.

전체 dataclass equality는16필드 모두를 비교한다. 따라서 정의 지문이 같아도 배포 provenance가 다르면 Snapshot 객체 전체 값은 다르며 Acceptance는 재검토해야 한다. 지문 equality를 객체 전체 equality·승인 승계로 사용하지 않는다.

## 5. ApplicabilityScope

기존 exact ApplicabilityScope를 사용한다. edition_id는 ASCII 네 자리 str, quarter는 exact int1~4 또는 None이며 None은 annual이다. 기존 문법의0000 허용도 변경하지 않는다. Snapshot에서 별도의 year/quarter parser나 scope Enum을 만들지 않는다.

Q3→Q4/annual/다른 연도는 다른 정의 target이다. 지문에도 scope를 포함하고 Acceptance 자동 승계를 금지한다. 현재날짜·지급월·금액으로 scope를 추론하지 않는다.

scope는 **혜택이 귀속되는 자격/정책 회차**, applicable_months는 **명시적으로 정규화한 월별 지급 적용월**이다. 서로 같은 분기/연도라고 자동 가정하지 않는다. 실제 근거가 지급월을 scope 밖으로 정한 경우를 생성자가 임의로 잘라내지 않으며 근거 검토는 외부 책임이다. 알려지지 않은 지급월은 None이다.

## 6. Benefit version

기존 Benefit version 문법은 없다. r/d/i/a의 기존 양의 버전 관례를 따라 **b0001부터의 명시 version**을 채택한다. 정확한 식은 `b(?:[0-9]{4}|[1-9][0-9]{4,})`, 단 b0000 제외다. b0001~b9999, b10000 이상을 허용하며 축약·대문자·불필요한 선행0·공백·자동 숫자 변환은 거부한다.

version namespace는 `(policy_id, scope, benefit_id)`다. 서로 다른 scope에 b0001이 있어도 동일 정의 version이라고 비교하지 않는다. M2.41의 후보명 benefit_definition_version/fingerprint는 이 문서에서 **benefit_version/benefit_fingerprint**로 단일화한다. JSON alias를 두 개 만들지 않는다.

14개 정의 필드 중 하나라도 바뀌면 같은 target의 새 b version으로 발행한다. 정의는 그대로이고 dataset/Registry 전체 provenance만 바뀌면 b version 유지가 가능하지만 Acceptance는 재검토한다. 자동 증가·최신 선택·날짜 version 생성·같은 version 덮어쓰기는 없다.

## 7. Version/fingerprint 비교 원칙

| 현재와 과거 비교 | 처리 |
|---|---|
| 같은 policy/scope/benefit/version, 같은 정의 지문 | 정의 binding 통과 가능; 나머지 gate는 별도 |
| 같은 policy/scope/benefit/version, 다른 정의 지문 | Data Error, immutable 정의 모순 |
| 같은 target, 정상 새 b version | 정상 변경, 기존 Acceptance unusable |
| 같은 계보, 다른 scope | 정상 범위 변경, 자동 승계 금지 |
| 다른 policy/benefit의 record를 현재 대상에 직접 연결 | Data Error, M2.41 유지 |

정의 version 변경과 dataset 변경은 독립이다. 새 dataset이라고 같은 b version의 금액/근거 모순을 정상 stale로 낮추지 않는다. 반대로 dataset만 바뀐 동일 정의를 지문 모순으로 오진하지 않는다. 같은 dataset의 다른 Registry 지문은 별도의 Data Error다.

이 비교는 향후 Acceptance 연결/외부 발급 감사 책임이다. 모델과 지문 함수는 과거 이력을 조회하지 않는다. 한 객체만으로 과거 overwrite를 탐지할 수 있다고 주장하지 않는다.

## 8. Amount definition

고정·비고정·미정의를 구별하는 **BenefitAmountType: FIXED / VARIABLE / UNKNOWN** 세 값으로 제한한다. RANGE/FORMULA/각 계산 방식별 Enum이나 실행 가능한 금액 AST를 만들지 않는다. VARIABLE은 알려진 비고정 정의의 포괄 분류이며 범위·상한·사용자 조건별 산정식을 포함한다.

| amount_type | amount_krw | amount_description | Snapshot / 초기 Acceptance |
|---|---|---|---|
| FIXED | exact int≥0 필수 | None 필수 | 구조 유효, 나머지 gate 후 수용 검토 가능 |
| VARIABLE | None 필수 | exact 비공백 str 필수 | 구조 유효, 초기 수용 불가 |
| UNKNOWN | None 필수 | None 필수 | 정상 incomplete, 초기 수용 불가 |

VARIABLE의 description은 정규화한 정의 설명과 근거 연결을 보존하는 용도다. 범위/산식/상한을 fixed amount로 바꾸지 않으며 문자열을 실행·파싱·LLM 계산하지 않는다. 예: “가구 조건에 따라 금액이 달라짐”. 정확한 산식 모델과 개인별 산출은 명시적으로 후속 범위다.

FIXED의 amount_krw는 **cadence 한 회의 공통 고정 금액**이다. 사용자 지급 심사 결과나 최대 지급액이 아니다. 예산 월 환산·저축 매칭의 잠긴 금액을 자유 현금으로 바꾸지 않는다. Snapshot은 정의를 표현하고 Bridge는 같은 정의에 대응하는 개인 후보를 받는다.

비현금 혜택의 금액은 공식 근거가 명시한 원 단위 액면/지원 정의에 한정한다. 현물의 시장가격·포인트 환전가치·지역화폐의 현금가치를 임의로 추정해 FIXED로 채우지 않는다. 그 금액 정의가 없으면 amount_type=UNKNOWN으로 보존한다. 금액이 알려져도 medium의 비현금성은 그대로다.

0원은 기존 M2.4와 일치하도록 유효하다. None과 구별하며 모든 후단 gate 통과 시 applied0원이 가능하다. Snapshot 단계에서 positive-only로 바꾸지 않는다. 음수·bool·float·Decimal·문자열·int 하위 타입은 모두 거부하고 exact int만 받는다. 반올림·절삭·임의 상한은 없다. 큰 int의 Python 정확성과 브라우저 Number 안전성은 별개다.

통화는 KRW로 고정한다. 외화 환산·Currency 추상화·소수 원 단위 지원은 하지 않는다. `_krw` 값이 없다고 다른 통화로 추정하지 않는다.

## 9. Cadence

기존 M2.3 taxonomy를 그대로 채택한다. **BenefitPaymentCadence**의7개 값은 MONTHLY / QUARTERLY / SEMIANNUAL / ANNUAL / ONE_TIME / IRREGULAR / UNKNOWN이다. 새로운 VARIABLE/OTHER alias는 넣지 않는다.

UNKNOWN은 정상 미정의다. 알려지지 않은 문자열을 UNKNOWN으로 자동 변환하지 않는다. IRREGULAR는 주기가 불규칙하다는 정의가 알려진 것이며 UNKNOWN과 다르다. Snapshot에서 유효해도 Bridge는 기존대로 MONTHLY만 직접 반영한다. QUARTERLY를3으로 나누거나 ANNUAL을12로 나누지 않는다.

## 10. Payment medium

**BenefitMedium**은 기존10개 값 UNRESTRICTED_CASH / RESTRICTED_CASH_EQUIVALENT / LOCAL_CURRENCY / POINTS / VOUCHER / IN_KIND / SAVINGS_MATCH / LOAN / INTEREST_SUPPORT / UNKNOWN을 그대로 사용한다. OTHER를 추가하지 않는다.

물리적 입금 수단뿐 아니라 경제유형을 포함한다. 현금으로 들어오는 대출·이자지원을 UNRESTRICTED_CASH로 분류하지 않는다. 분류를 모르면 UNKNOWN으로 명시하고 미완료로 둔다. 새 유형은 명시 계약 개정이 필요하며 임의 문자열 alias를 허용하지 않는다.

LOCAL_CURRENCY/VOUCHER/IN_KIND/SAVINGS_MATCH 등도 유효한 정의 snapshot이다. 정의 수용과 Bridge 지원은 별개이며 유형을 저축 가능한 자유 현금으로 바꾸지 않는다.

## 11. Restriction과 details

기존 medium이 경제유형을 포함하더라도 검토할 제한 내용을 잃지 않도록 **BenefitRestriction: UNRESTRICTED / RESTRICTED / UNKNOWN**을 정의 snapshot에 둔다. Bridge candidate에 같은 bool들을 추가하는 변경이 아니다.

restriction은 사용처/목적·저축/인출에 관한 제한을 뜻한다. medium 자체의 비현금성·대출 상환 의무 전체를 새 제한 계산기로 해석하지 않는다. medium gate는 독립적으로 유지한다.

| restriction | restriction_details | 구조 계약 |
|---|---|---|
| UNRESTRICTED | None | 해당 제한이 없다고 정규화함 |
| RESTRICTED | exact 비공백 str 필수 | 지역·업종·목적·잠금 등 검토할 제한 설명 |
| UNKNOWN | None | 제한 확인 미완료, 무제한으로 추정 금지 |

확정된 UNRESTRICTED_CASH는 restriction=UNRESTRICTED만, RESTRICTED_CASH_EQUIVALENT는 RESTRICTED만 허용한다. 전자의 UNKNOWN/RESTRICTED 또는 후자의 UNRESTRICTED/UNKNOWN은 명칭 자체와 충돌하므로 Data Error다. 제한을 아직 모르는 현금성 자료는 medium=UNKNOWN으로 미완료를 표현한다.

나머지 medium에서 restriction 값을 자동 유도하지 않는다. IN_KIND에 사용 제한이 없을 수도 있고 LOCAL_CURRENCY의 구체적 제한은 근거로 검토해야 한다. 예컨대 지역화폐를 UNRESTRICTED라 잘못 선언한 사실을 타입만으로 인증하지 않으며 외부 의미 검토에서 거부해야 한다. Snapshot constructor는 임의 제도별 추론을 추가하지 않는다.

details는 설명/감사 자료이며 **runtime 조건 판단에 사용하지 않는다**. 의미 있는 제한 변경·설명 수정은 정의 확인본의 변경이므로 지문에 포함한다. 자동 strip·번역·요약·Unicode 정규화 없이 원래 문자열을 보존한다. 이로 인해 문구만 달라도 새 정의 version이 필요하다는 보수적 표현 계약을 선택한다.

## 12. Applicable months와 교차 필드 검증

M2.4의 **정확한 YYYY-MM 문자열 tuple**을 유지한다. 숫자1~12는 연도를 잃으므로 채택하지 않는다. 의미는 “이 고정 정의의 혜택을 월별 시뮬레이션에서 지급 적용월로 사용할 수 있다고 명시적으로 정규화한 월”이다. 신청월·자격 기준월·확인일과 다르다.

| 값/조합 | 구조 처리 |
|---|---|
| None | 월 정보가 미확정/개인 일정 의존, 정상 incomplete·초기 수용 불가 |
| 비어 있지 않은 정렬·유일 YYYY-MM tuple | 연도0001~9999·월01~12, exact str만 허용 |
| 빈 tuple | 거부: 지급 없는 정의와 미정의를 섞지 않음; 미정은 None, 종료/철회는 별도 lifecycle |
| 중복/역순/잘못된 월/숫자 월/list | Data Error, sort/dedupe/변환 금지 |
| ONE_TIME + 알려진 월2개 이상 | Data Error: 한 target의 일회 정의는 정확히 한 월만 |
| ONE_TIME + None | 유효 incomplete |
| MONTHLY + 드문 월 목록 | 구조 허용, 중단·조건별 지급월인지 근거 검토 필요 |
| QUARTERLY + 한 월 또는 여러 명시 월 | 구조 허용, 분기액/3·3/6/9/12 자동 추론 금지 |
| UNKNOWN cadence + 알려진 월 | 구조 허용, 주기 미정의로 수용 불가 |

월 목록은 ordered schedule event가 아니라 **지급 적용월 집합의 canonical 표현**이다. 한 월에 여러 지급 event나 개인별 일정/소급 계산은 표현하지 않는다. 월 목록에서 cadence를 역산하거나 누락월을 자동 채우지 않는다. ANNUAL/SEMIANNUAL/IRREGULAR의 개수를 단순 기간 산술로 제한하지 않는다.

scope 분기/연도와 월 목록의 동일성을 생성자가 강제하지 않는다. 명시 근거가 없는 범위 밖 월을 넣어도 된다는 뜻은 아니다. 외부 검토가 target scope와 모든 적용월의 관계를 확인하고 확인 불가하면 None으로 남긴다. 연도0000을 형식상 허용하는 기존 Scope와, 실제 달력 월의0000 거부도 서로 다른 계약이다.

## 13. Evidence binding과 claim별 추적

기존 이름 **benefit_evidence_refs**를 유지한다. 최소 하나의 canonical `source_document_id#locator_id`가 필요하며 각 요소는 기존 `parse_evidence_ref`로 검사한다. 완전히 근거 없는 수집 메모는 이 Snapshot이 아니라 외부 수집 단계에 둔다. Snapshot은 일부 필드가 미정이어도 알려진 정의의 근거는 있어야 한다.

| 선택 | 정확성/비용 | 결정 |
|---|---|---|
| A 전체 refs + 실제 검토 artifact의 claim별 대응표 | 작은 모델 유지, 검토 때 금액/주기/수단/제한/월 각각의 근거를 명시해야 함 | **채택** |
| B 필드별 refs5개 또는 별도 EvidenceBindings 객체 | claim 연결을 runtime 값에 포함하지만 필드/교차검증이 늘고 현재 Bridge에는 불필요 | 현재 미채택 |

실제 Acceptance review artifact는 **amount / cadence / medium / restriction / applicable_months → 이 Snapshot refs의 비어 있지 않은 부분목록** 대응표를 필수로 남긴다. 같은 ref를 여러 claim에 재사용할 수 있다. 각 claim의 전체 의미를 뒷받침하는지 사람이 확인한다. refs 합집합만 있다는 이유로 모든 claim 검토가 완료됐다고 하지 않는다.

claim 대응표는 “누가 무엇을 검토했는가”라는 검토 자료이며 snapshot 내용 필드는 아니다. 대응표 변경은 불변 검토 artifact/Acceptance revision으로 추적하고 정의 지문을 바꾸지 않는다. refs 자체가 바뀌면 정의 version/지문이 바뀐다. 서명/검토 진실성을 모델로 인증하지 않는 경계는 유지한다.

refs 순서와 중복은 구조 값 및 지문에서 보존한다. duplicate refs를 constructor에서 dedupe하지 않는다. 그러나 향후 실제 사용 검증에서 기존 `validate_evidence_refs`가 중복을 오류로 거부하므로 **중복이 있는 Snapshot은 구조 표현/지문은 가능하지만 Acceptance 대상은 아니다**. 이것은 정상 UNKNOWN이 아니라 source 사용 검증의 Data Error다. field별 mapping 부재는 검토 미완료이며 가짜 승인으로 채우지 않는다.

## 14. Source binding과 dataset provenance

기존 exact **SourceBinding(source_document_id, document_version)**을 사용한다. source_bindings는 비어 있지 않은 tuple이며 ID가 유일하고 ASCII 문자열 오름차순이어야 한다. refs에서 추출한 source ID 집합과 정확히 같아야 한다. 불필요 source·누락 source·상충하는 d version·역순/중복 binding을 거부한다. d version은 기존 d0001 이상 규약을 그대로 사용한다.

dataset_version과 source_registry_fingerprint는 **항상 필수**다. 어떤 고정 자료 묶음의 근거인지 모르는 Snapshot은 만들지 않는다. UNKNOWN은 혜택 metadata 미완료를 나타내며 provenance를 임의 None으로 바꾸는 이유가 아니다. Registry 객체/원문/Manifest를 모델에 저장하지 않는다.

생성자는 refs의 형식과 source ID 집합만 검사한다. 고정 Registry에 그 document version/locator가 실제 존재하는지, 대상 policy에 적용되는지, ACTIVE/VERIFIED인지, freshness를 만족하는지는 외부 준비/후속 Acceptance 사용 gate 책임이다. 원문 bytes hash·Registry 전체 domain 지문·Benefit 정의 지문은 서로 대체하지 않는다.

**MVP의 현재 실행은 동일 dataset/Registry를 사용한다.** Benefit Snapshot의 dataset/Registry와 Coverage의 present baseline·현재 Envelope/Manifest/Registry가 정확히 일치해야 한다. 다르면 current 입력 결합 Data Error다. 독립 변경이 가능하다는 이유로 다른 release를 즉석 병합하지 않는다.

Benefit 전용 source는 같은 전체 Registry에 포함될 수 있지만 기존 Envelope.source_bindings에 억지로 추가하지 않는다. Envelope는 leaf source 집합과의 equality를 요구한다. Benefit binding은 별도로 유지하고 전체 source는 기존 Manifest에 고정한다. 향후 별도 benefit source release 지원은 명시적인 자료 결합 계약 개정 대상이며 지금 구현하지 않는다.

## 15. Snapshot validity와 completeness

| 구분 | 의미 |
|---|---|
| 구조 유효 |16필드 타입·문법·로컬 교차 규칙·refs/bindings 대응 충족 |
| 초기 시뮬레이션 정의 완전 | FIXED, cadence/medium/restriction 모두 UNKNOWN 아님, applicable_months 알려짐 |
| 근거/metadata 검토 완료 | 모든 claim의 공식 근거·version·사용요건 및 실제 교차 검토 완료 |
| Acceptance 현재 usable | 위 요건 + Coverage FULL/verification·정확한 binding·선택 승인·기한/철회 gate 통과 |

valid Snapshot이라고 completeness/검토/승인을 자동 부여하지 않는다. VARIABLE은 정의가 상세히 알려져 있어도 **초기 fixed-only 수용 범위 밖**이며 UNKNOWN과 같은 뜻이 아니다. 설명 자료로 보존하되 계산용 fixed amount를 만들어 넣지 않는다.

UNKNOWN Enum/nullable 필드를 canonical payload에 명시한다. arbitrary 문자열·잘못된 타입·상충 조합·깨진 명시 ref는 정상 incomplete로 숨기지 않는다. 별도 completeness/status 필드나 Benefit Coverage subsystem을 만들지 않는다. 향후 Acceptance evaluator가 위 유한 completeness 요건을 확인한다.

## 16. Benefit metadata review와 분리

**별도 BenefitDefinitionReview 모델은 현재 MVP에 추가하지 않는다.** BenefitSnapshot은 하나의 정의 검토 단위이고 기존 PolicyBenefitAcceptance의 실제 review_ref/artifact가 해당 snapshot metadata 검토까지 기록한다. 검토가 끝났으나 아직 simulation 수용하지 않은 작업 메모는 artifact 쪽에 남길 수 있으나 runtime 승인 record를 발급하지 않는다.

Coverage에는 목록 완결성과 각 condition별 구현이라는 여러 검토 단위가 있어 별도 records가 필요했다. 단일 Benefit 정의에 같은 패턴을 자동 복제할 이유는 없다. 준비자/별도 검토자·대상 identity/fp·claim 대응표·날짜·수동 사례·발급/철회 사유는 실제 Acceptance artifact에 필수다.

M2.41 13절의 “검토 참조·검토일 연결” 후보는 **Snapshot 저장 필드가 아니라 Acceptance artifact의 연결**로 확정한다.16필드에 reviewed_at/reviewer/review_ref를 넣지 않는다.17절의 gate를 없애는 것이 아니라 그 검토를 기록하는 위치를 최소화하는 결정이다.

## 17. Acceptance binding과 분리

Acceptance는 정확한 benefit_version/fingerprint, 사람이 읽을 accepted_terms, provenance를 Coverage9개 binding과 함께 고정한다. Snapshot 자체의 성공/지문 계산은 승인 행위가 아니다. 초기 발급은 fixed-only·유한 명시 월·metadata 근거 검토·FULL/VERIFIED 요건을 모두 요구한다.

M2.41의 immutable ACCEPTED/REVOKED·명시 data_use_date·기한·정상 stale/오류·현재 usable 결과 분리는 유지한다. Snapshot에 acceptance_ref/version/status를 넣지 않는다. 과거 record와 현재 Snapshot의 same-version content guard는 dataset 변경/만료/철회와 독립적으로 검사한다.

review_ref의 claim 대응표가 실제로 존재하고 검토되었는지는 외부 준비가 확인한다. pure evaluator가 artifact 파일을 찾거나 존재하지 않는 검토를 자동 생성하지 않는다. 별도 Review 모델이 없다는 이유로 metadata review를 PASS로 가정하지 않는다.

## 18. Benefit Bridge와 분리

Snapshot에는 bridge_supported/cashflow_applicable/savings_allowed/월 환산액을 저장하지 않는다. Bridge version과 개인/월 상황에 따라 달라질 수 있는 값이기 때문이다. 현재 MONTHLY+UNRESTRICTED_CASH 및 다른 gate 충족이라는 지원 범위는 그대로다.

Snapshot의 restriction은 정의 검토/모순 방어이며 새 Bridge 지원 판정 bool이 아니다. UNRESTRICTED_CASH와 restriction의 명확한 모순은11절에서 거부하고, 정의가 수용됐어도 medium/cadence별 Bridge 제외는 유지한다. 후보의 fixed 금액·주기·수단·월이 승인 정의와 다른 결합이면 오류다.

M2.41대로 Bridge는 현재 Acceptance 평가 결과를 받는다. 원본 수용 record resolve·기한·snapshot matching을 재실행하지 않는다. Snapshot/Acceptance를 임의 scalar ACCEPTED로 변환해 근거를 잃지 않는다.

## 19. Cashflow와 분리

Snapshot은 사용자 소득/지출·개인 지급액·예산 month·저축 가능액을 저장하지 않는다. 월 환산·현금흐름 합산·금융상품 계산·LLM 자격 판정을 수행하지 않는다.

향후 검토된 Snapshot + Coverage/Verification/Acceptance + 사용자·월 확인 → Bridge → 명시 월 int → 새 CashflowInput의 경계를 유지한다. 기존 Cashflow 모델/계산식/기본 혜택0을 변경하지 않는다. 실제 안산 반영액도0원 원칙을 유지한다. Snapshot으로 포인트/지역화폐를 자유 저축 재원으로 만들지 않는다.

## 20. Benefit fingerprint 의미와 provenance 제외 결정

benefit_fingerprint는 **대상·version·시뮬레이션 관련 정의 표현 + 해당 정의의 evidence/source binding**의 지문이다. 원문 파일 bytes 전체나 자연어 의미 동치의 지문이 아니다. review 진실성·공식성·서명·사용자 자격·지급 보장을 인증하지 않는다.

dataset_version과 **전체** source_registry_fingerprint는 정의 지문에서 제외한다. 포함하면 무관한 정책 source metadata만 바뀐 새 dataset에서 같은 b version의 Benefit 지문이 달라져 M2.41의 same-version conflict를 잘못 일으킨다. 이 두 값은 삭제하는 것이 아니라 **독립 Acceptance binding**으로 보존한다.

반면 정의가 실제로 사용하는 benefit_evidence_refs·그 문서의 source_bindings는 포함한다. 같은 source ID의 d version 갱신도 정의 근거 확인본 변경이므로 새 b version과 재검토가 필요하다. unrelated Registry 변경과 해당 Benefit source 변경을 구별한다.

같은 source ID/d version의 원문/metadata가 과거와 달라졌다는 문제는 전체 Registry/dataset·외부 불변 원본 감사에서 판별한다. Benefit 지문 하나가 참조 문서의 모든 bytes를 포함한다고 주장하지 않는다. 새 dataset으로 그 overwrite를 정당화할 수도 없다.

## 21. Fingerprint schema와 함수 경계

schema discriminator를 **`fingerprint_schema: "benefit-snapshot-1.0"`**로 고정한다. Payload 의미·필드·순서 규칙 변경에는 새 schema와 migration/기존 벡터 보존 검토가 필요하다. 기존 digest 기대값을 조용히 덮어쓰지 않는다.

후속 공개 API 후보는 **`fingerprint_benefit_snapshot(snapshot: BenefitSnapshot) -> str`** 하나다. exact Snapshot만 받고 raw dict/list·subclass·임의 to_dict 객체를 자동 변환하지 않는다. hash(any)·범용 payload 해시 API를 만들지 않는다.

모델에 fingerprint를 저장하거나 매번 자동 계산하는 property를 넣지 않는다. 함수는23절의 explicit projection만 구성하고 승인/구조 완결성/Registry 조회를 수행하지 않는다. 부분 Snapshot도 동일 계약으로 지문 계산이 가능하다.

## 22. Canonical JSON·UTF-8·SHA256

다음 recipe를 그대로 사용한다. 이것은 이번에 구현한 함수가 아니라 encoding 계약이다.

```text
json.dumps(payload, sort_keys=True, separators=(",", ":"),
           ensure_ascii=False, allow_nan=False)
→ encode("utf-8", errors="strict")
→ SHA256 → lowercase hexdigest
```

모든 깊이에서 key 사전순, indent/구조 공백/BOM/마지막 newline 없음, exact int10진수·None=null·Enum.value·tuple→새 list다. 문자열 내용의 공백·개행·대소문자·Unicode NFC/NFD는 변경하지 않는다. 한글은 실제 UTF-8이며 표준 JSON escaping을 사용한다. surrogate 등 strict encoding 실패는 오류이며 replace/ignore하지 않는다. 결과는 접두사 없는 exact 소문자hex64 str다.

Python hash/repr/asdict/임의 to_dict 전체/파일명/경로/시각/Git/캐시를 해시하지 않는다. 자동 float·Decimal·NaN·Infinity 변환도 없다. 이 recipe는 RFC8785/JCS 전체 구현이 아니며 다른 언어는 literal golden bytes와 맞춰야 한다.

기존 Coverage의 `_digest_payload`는 **private·동결 영역**이다. 후속 Benefit 함수가 이를 public처럼 import하거나 helper 추출을 위해 frozen 파일을 수정하지 않는다. 표준 json/hashlib와 동일한 작은 encoding recipe를 새 Benefit 전용 함수에서 사용하고 BV로 검증하는 방향이다. 공통 helper framework를 선행 생성하지 않는다.

## 23. Fingerprint payload의 정확한 포함/제외

최상위 key는 **15개**다. nullable key도 항상 포함한다.

| key | 값 |
|---|---|
| fingerprint_schema | benefit-snapshot-1.0 |
| policy_id | 원래 문자열 |
| scope | edition_id/quarter 두 key; annual은 quarter=null |
| benefit_id | 원래 문자열 |
| benefit_version | 원래 b version, label만 바뀌어도 지문 변경 |
| amount_type | Enum.value |
| amount_krw | exact int 또는 null |
| amount_description | 원래 문자열 또는 null |
| payment_cadence | Enum.value |
| benefit_medium | Enum.value |
| restriction | Enum.value |
| restriction_details | 원래 문자열 또는 null |
| applicable_months | 원래 canonical 월 tuple→list 또는 null |
| benefit_evidence_refs | 원래 순서/중복의 새 list |
| source_bindings | 각 document_version/source_document_id 두 key의 새 object 목록 |

제외: dataset_version, source_registry_fingerprint, 계산 결과 benefit_fingerprint 자체, Acceptance identity/status/version/ref, reviewed_at/reviewer/review artifact/claim 검토 대응표, 정책 표시명, 사용자/개인 판정, data_use_date/현재 시각, Bridge 지원 여부·월 환산액, 원문 객체/URL/파일 bytes.

schema는 함수의 상수이며 Snapshot 생성 필드가 아니다. definition version을 포함하는 이유는 Tree의 rule_version 포함 철학과 같다. 정상 version 변경과 같은 version의 내용 모순은 version을 별도 비교해 구별한다. “내용이 같으니 새 version도 자동 승인”은 금지한다.

## 24. Ordering과 serialization

| 항목 | 구조/일반 to_dict | 지문 |
|---|---|---|
| fields |2절16개 key 순서, null도 생략 안 함 |23절15개 projection 후 recursive key sort |
| scope | 기존 exact 값·새2key dict | 동일 값 projection |
| months | 입력부터 strict 오름차순·유일, 자동 정렬 없음 | 검증된 순서 유지 |
| evidence | 입력 순서/중복 보존 | 동일하게 보존, reorder/duplicate는 다른 지문 |
| source bindings | 입력부터 source ID strict 오름차순·유일 | 검증된 순서 유지 |
| text | 유효 비공백 문자열의 앞뒤 공백도 원문 보존 | 변환 없음 |

일반 to_dict는16개 저장 필드만 새 nested dict/list로 반환한다. scope는 기존 to_dict를 재사용한다. 현재 SourceBinding에는 자체 to_dict가 없으므로 각 binding의 source_document_id/document_version 두 필드를 명시적으로 새 dict에 담는다. Enum은 value 문자열이며 nullable 값도 key를 생략하지 않는다. fingerprint는 일반 serializer 전체가 아닌 explicit projection이다. 지문용 JSON과 release loader 형식은 다르며 이번에 JSON loader/schema_version을 추가하지 않는다.

Snapshot 순서 입력을 잘못 주면 거부한다. 유효하지 않은 역순 months/bindings의 지문을 비교해 같다고 만들지 않는다. Evidence는 설명/검토 표현의 순서를 보존하므로 두 유효 Snapshot의 refs 순서가 달라지면 지문도 달라진다.

## 25. Change matrix와 Acceptance invalidation

아래 “변경”은 구조적으로 유효한 두 정의 또는 정상 배포 갱신을 비교한 것이다. 같은 target의 정의가 바뀌면 **새 b version을 발급**해야 하며 같은 b로 덮어쓰면 Data Error다. SHA256의 수학적 무충돌을 주장하지 않는다.

| 변경 축 | Benefit fp 변경? | 재검토/처리 |
|---|---|---|
| policy_id | 예 | 다른 대상, 직접 record 연결 오류 |
| benefit_id | 예 | 다른 component, 직접 record 연결 오류 |
| scope | 예 | 정상 다른 target, 승인 자동 승계 금지 |
| benefit_version label만 | 예 | 새 version, 재수용 필요 |
| amount_krw | 예 | 새 b/review, 같은 b면 오류 |
| amount_type/description | 예 | 새 b/review, VARIABLE/UNKNOWN은 초기 수용 불가 |
| cadence | 예 | 새 b/review, Bridge 유형은 별도 |
| medium | 예 | 새 b/review, 분류를 자유 현금으로 추정 금지 |
| restriction/details | 예 | 새 b/review, 텍스트 수정도 표현 변경 |
| applicable_months/None | 예 | 새 b/review, 임의 월 추론 금지 |
| evidence 추가/교체/삭제 | 예 | 새 b/review, 빈 refs는 구조 오류 |
| evidence 순서/중복 | 예 | 새 표현 version; 중복은 사용 gate 오류 |
| 관련 source binding d version | 예 | 새 b/review |
| dataset만 변경, 정의/관련 bindings 동일 | 아니오 | b 유지 가능하지만 Acceptance 재검토 필요 |
| Registry 전체만 변경, 관련 정의 동일 | 아니오 | 새 dataset이면 수용 재검토; 같은 dataset이면 모순 오류 |
| Acceptance status/version | 아니오 | 수용 revision/lifecycle만 별도 변경 |
| Acceptance reviewed_at/기한 | 아니오 | 새 수용 revision, 날짜 gate 별도 |
| review artifact/ref/reviewer/claim 대응표 | 아니오 | 불변 검토 이력/새 Acceptance revision |
| 사용자/월 시나리오/현재시각 | 아니오 | Snapshot 필드 아님, 개인 적용 재평가 |

## 26. Immutability와 모델 구현 범위

후속 모델은 frozen=True, slots=True, kw_only=True와16개 필수 필드를 사용한다. Enum은 str/Enum 방향이며 exact 타입을 요구한다. tuple/list 변환·ID 보정·자동 version·현재시각 default·캐시·외부 조회가 없다. 하위 immutable Scope/SourceBinding 원본을 보존한다.

일반 equality/hash는16개 저장 값 전체에 기반한다. to_dict는 새 중첩 값을 만들고 반환 dict/list를 변경해도 원본이 바뀌지 않아야 한다. 같은 입력 반복 serialization은 같은 값이다. 사용자 facts·경제정보·계좌/로그/저장소를 넣지 않는다.

M2.43의 가장 작은 모델 구현 범위는4개 Enum + Snapshot + 로컬 validation/to_dict + 합성 unit tests다. 지문 함수·새 Review/Acceptance/Collection·source 검증 orchestration·실제 데이터 연결은 포함하지 않는다.

## 27. Errors와 검증 책임

모델 오류는 기존 **PolicyDataError**로 두고 고정 prefix `INVALID_BENEFIT_SNAPSHOT: field: reason` 방향을 채택한다. 오류에 원본 payload·개인값을 넣지 않는다. 기존 parse_evidence_ref가 내는 SourceValidationError는 PolicyDataError 하위이므로 그대로 전파한다. 새 범용 오류 플랫폼을 만들지 않는다.

검증 순서는16개 필드 표 순서의 exact 타입/문법 → amount 조합 → restriction 조합 → medium/restriction의 두 명확한 모순 → ONE_TIME/month count → refs와 source binding ID 집합 correspondence다. source_bindings 자체의 유일/오름차순은 해당 필드 로컬 검사다. 필수 인자 누락/정의되지 않은 extra 인자는 Python TypeError다.

nullable amount의 bool/float 등은 None으로 완화하지 않는다. unknown Enum 문자열·partial provenance·잘못된 refs/월·중복 binding은 오류다. Registry의 source 미존재/버전/수명·claim 검토 진실성·중복 refs 사용 검증은 모델 밖이다. Coverage Data Error를 catch해 정상 incomplete로 변환하지 않는다.

후속 지문 함수의 exact Snapshot 입력/명시 projection/encoding 실패도 PolicyDataError이며 `benefit snapshot fingerprint: ...`로 구별한다. 고립 surrogate를 모델의 비공백 문자열 검사가 통과할 수 있어도 지문은 strict UTF-8 오류로 거부한다. raw dict 확장/객체 복구/자동 정규화는 하지 않는다.

## 28. Synthetic examples

**모든 예시는 문서상 합성 자료**다. 실제 공식 source/reviewer/승인 파일을 만든 것이 아니다. 지시문의 SYNTH_POLICY/SYNTH_BENEFIT은 개념 이름으로 이해하고 기존 canonical ID에 맞춰 SYNTH-POLICY/SYNTH-BENEFIT을 사용한다.

기본 예시 S: policy=SYNTH-POLICY, scope=2026/Q3, benefit=SYNTH-BENEFIT, b0001, FIXED/100000/description=None, MONTHLY, UNRESTRICTED_CASH, UNRESTRICTED/details=None, months=(2026-09), refs=(SYNTH-SOURCE#benefit-definition), bindings=(SYNTH-SOURCE/d0001), dataset=SYNTH-DATASET-1, Registry fp는 합성 형식값으로만 가정한다.30절 BV01은 이 정의 projection이다.

요청의 “Q3 +1~12월” 예시는 **Q3 자격 회차와 연간 지급월의 관계를 가상 근거가 명시한다는 Assumption**이 있을 때만 의미 검토 가능하다. 정규화 표현은2026-01~2026-12의12개 YYYY-MM이다. Snapshot 구조가 이를 임의 거부/자동 생성하지 않지만 Q3라는 이유만으로 그 목록을 정당화하지 않는다. 일반 Q3 예시 S는9월 하나를 명시한다. annual scope에12개월 목록을 넣은 별도 예시도 가능하며 Q3 수용의 연간 자동 승계는 없다.

분기 지역화폐 예시 Q는 S의 cadence=QUARTERLY, medium=LOCAL_CURRENCY, restriction=RESTRICTED/details=지역 내 사용, amount=100000, 명시 월=(2026-09)인 별도 가상 정의다. Snapshot 유효·실제 검토 후 Acceptance 가능성이 있지만 **현행 Bridge는 NON_MONTHLY_PAYMENT/RESTRICTED_MEDIUM으로0원**이다. 월액을100000/3으로 만들지 않는다.

VARIABLE 예시는 amount_krw=None/description=가구 조건에 따라 금액이 달라짐, UNKNOWN 예시는 amount/cadence/medium/restriction을 미정의하고 months=None이다. 유효 부분 Snapshot을 지문으로 구별할 수 있지만 초기 Acceptance는 불가다. 이 예시들이 실제 record 발급을 승인하지 않는다.

## 29. Current Ansan boundary

실제 안산 releases001/002는 기존 DRAFT/CONDITION_SLICE 상태다. 실제 전체 Coverage Inventory/Review/FULL Result·검토된 Benefit metadata/Acceptance는 없다. source VERIFIED나 주민등록/출생일 PASS로 승격하지 않는다.

이번 단계에서 실제 Ansan benefit_id/b version/금액/월/refs 매핑·snapshot·지문·검토 기록을 만들지 않는다. 실제 source를 새로 조사/재확인한 날짜도 기록하지 않는다. actual releases는 불변으로 유지한다.

ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**이며 Fact/Rule/evaluator 구현을 계속 보류한다. generic core는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**다. 실제 정책의 혜택 직접 Cashflow 반영0원 원칙을 유지하며 없는 Bridge가 실행됐다고 주장하지 않는다.

## 30. Golden vectors — BV01~BV16

후속 지문 utility의 기준으로 **합성 literal canonical JSON + strict UTF-8 byte length + SHA25616개**를 문서에 고정한다. 이번에 표준 JSON/해시 도구로 문서상 literal payload만 계산했으며 BenefitSnapshot 클래스/전용 fingerprint 함수·테스트 파일은 구현하지 않았다. 실제 안산 자료를 입력하지 않았다.

BV01은 S, BV02 금액, BV03 cadence, BV04 IN_KIND, BV05는 BV04의 제한/영문 details, BV06 월, BV07 evidence 추가, BV08 annual scope, BV09 version label, BV10은 BV05의 한글 details, BV11 VARIABLE, BV12 UNKNOWN/None, BV13은 BV07의 evidence 순서 반전, BV14 중복 refs, BV15 관련 source d version, BV16 months=None이다. BV14는 구조 표현용이며 source 사용 gate가 거부한다.

각 vector는 독립적인 정의 payload다. BV02~BV16이 같은 b0001을 쓰는 것은 **충돌 탐지용 대조 벡터**이며 같은 version으로 실제 다른 정의를 발행하라는 뜻이 아니다. 새 정의 발행에는 새 b version이 필요하다. 검토 metadata/배포 provenance 제외는 별도 동일-payload 사례로 검증한다.

| ID | UTF-8 bytes | SHA256 |
|---|---|---|
| BV01 | 535 | 46c9a388b359c3e782e0a1d0d484ce8d19afe92e37080b20adda7000bcd45cd3 |
| BV02 | 535 | 0da2a6ef35da21eb9b296f708154773a5e5cc6422e9a06694076d00af0e2b2c0 |
| BV03 | 537 | 59456a9b057751bdebc3a7c3521175abd7dc4c8ac75b26075c379e9e3d448043 |
| BV04 | 525 | bb6f1e779880fb25c98d03a3acabbde6e9a294849a5081bd98ccfebe30d88ac5 |
| BV05 | 535 | cb5fd08dbb8ce3c2ba3e0e7dc42b3ee64dc28350746569e0b89f37ecf3ac9151 |
| BV06 | 545 | 6ba5de9d61b2ed68b04ceac98eedc4149703aaa6ed7132e0783c376e1ff431b4 |
| BV07 | 565 | d9d2bb4963dbce79f54a81007dd04d13c5453ca96fbb685110626bb4102dda50 |
| BV08 | 538 | 48f2a5b47e9d545c01584548e4303df1a94746ff5835709e43ddbff0c38faa20 |
| BV09 | 535 | 89c309d32965d335b39f009a7422530e4447e803c257fa4d2786248acc30e95d |
| BV10 | 541 | 88ec6da60cae53840b3ad3dab072f795e29b9698587c388cfae8f74f0d58f51f |
| BV11 | 577 | 13d1fd894a2a49e90c1b3b17d8a2d9dc9a89fe5e2788ac443634974613b132ee |
| BV12 | 513 | fd04ca7d068e1377d9c18f51a19f8c2e5669049191ade3734277b20bea5a4bc2 |
| BV13 | 565 | a4c583320d2ecc98d5da11512b055ad34c974879d70363798df35b896eb16408 |
| BV14 | 569 | d23e9c96c5ce11e52cf613d0cfac2336c357c60aa9460c00cbfbfd5db440a3a9 |
| BV15 | 535 | 8194798e866570af26d32216f77da3cc3fda07387043fccd0ebfd8bd35df9902 |
| BV16 | 528 | 8cf044c857382b867507cb3954d5e6dc73232c9f8cae55fab47c587a66552255 |

### BV01 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV02 literal canonical JSON

```json
{"amount_description":null,"amount_krw":125000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV03 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"QUARTERLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV04 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"IN_KIND","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV05 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"IN_KIND","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"RESTRICTED","restriction_details":"Education only","scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV06 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-08","2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV07 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition","SYNTH-SOURCE#payment-months"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV08 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":null},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV09 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0002","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV10 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"IN_KIND","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"RESTRICTED","restriction_details":"교육 목적 사용","scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV11 literal canonical JSON

```json
{"amount_description":"가구 조건에 따라 금액이 달라짐","amount_krw":null,"amount_type":"VARIABLE","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV12 literal canonical JSON

```json
{"amount_description":null,"amount_krw":null,"amount_type":"UNKNOWN","applicable_months":null,"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNKNOWN","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"UNKNOWN","policy_id":"SYNTH-POLICY","restriction":"UNKNOWN","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV13 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#payment-months","SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV14 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition","SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

### BV15 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":["2026-09"],"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0002","source_document_id":"SYNTH-SOURCE"}]}
```

### BV16 literal canonical JSON

```json
{"amount_description":null,"amount_krw":100000,"amount_type":"FIXED","applicable_months":null,"benefit_evidence_refs":["SYNTH-SOURCE#benefit-definition"],"benefit_id":"SYNTH-BENEFIT","benefit_medium":"UNRESTRICTED_CASH","benefit_version":"b0001","fingerprint_schema":"benefit-snapshot-1.0","payment_cadence":"MONTHLY","policy_id":"SYNTH-POLICY","restriction":"UNRESTRICTED","restriction_details":null,"scope":{"edition_id":"2026","quarter":3},"source_bindings":[{"document_version":"d0001","source_document_id":"SYNTH-SOURCE"}]}
```

후속 테스트는 위 JSON 문자열·byte length·digest를 literal 기대값으로 고정하고, 기대값을 구현 함수로 다시 계산하지 않는다.16개 literal 기준 외에 wrong type/strict encoding·불변성·100회 결정성·provenance/검토 metadata 제외를 별도 검증한다. schema/payload를 개정하면 과거 BV를 보존하고 새 schema/vector를 추가한다. Coverage GV01~GV15는 변경하지 않는다.

## 31. Acceptance binding matrix와 같은 자료 요구

| 항목 | Acceptance binds? | 변경/모순 기준 |
|---|---|---|
| policy_id | 예 | 다른 대상 직접 연결 오류 |
| scope | 예 | 정상 scope 변경은 unusable; ref가 선언한 대상과 다르면 오류 |
| benefit_id | 예 | component별 독립 수용 |
| benefit_version | 예 | 정상 새 version은 unusable |
| benefit_fingerprint | 예 | 같은 target/version의 다른 내용은 Data Error |
| dataset_version | 예 | 새 dataset은 정의 fp 같아도 unusable |
| source_registry_fingerprint | 예 | 같은 dataset의 다른 값은 Data Error, 정상 새 dataset은 재검토 |
| accepted_terms | 예, 읽을 수 있는 정의 snapshot | 금액/분류/제한/월/refs/bindings를 승인 지문과 같은 내용으로 보존 |

M2.41의 Coverage9개 값은 그대로 결합한다. 현재 Benefit와 Coverage/Envelope/Manifest가 서로 다른 dataset/Registry를 주장하면 과거 Acceptance stale가 아니라 current 입력 오류다. provenance가 중복되어도 **두 입력을 같은 확인본으로 결합했는지 검사할 값**이므로 Snapshot에서 제거하지 않는다. Acceptance record 안에서는 동일 dataset/Registry 값을 한 번 저장하고 두 입력의 일치 검증으로 중복을 줄일 수 있다.

review metadata는 정의 지문에 없지만 Acceptance review artifact에 반드시 연결한다. 이 설계는 M2.41의 metadata review gate를 유지하면서 별도 BenefitDefinitionReview runtime 모델을 생략한다. 구조/equality/hash 통과는 실제 review 수행 증명이 아니다.

## 32. 후속 구현 순서와 완료조건

| 순서 | 최소 작업 | 완료조건/테스트 |
|---|---|---|
| M2.43 후보 | **BenefitSnapshot 값 모델 +4개 Enum만 구현** |16필드 exact 타입·버전·amount/restriction 조합·월/refs/bindings·불변성/새 serializer 합성 unit tests, 전체 기존 회귀 보존 |
| 다음 승인 단계 | 전용 fingerprint utility |15key explicit payload·BV01~BV16 literal bytes/length/digest·strict UTF-8/타입·100회 결정성 검증 |
| 다음 승인 단계 | Acceptance record/result 모델 | Coverage9개+Benefit binding·기한/철회·actual review artifact 책임·기존 reasons/Trace를 작은 단위로 구현 |
| 다음 승인 단계 | Acceptance pure evaluator | completeness/source 사용요건·정확한 같은 확인본·독립 guarded comparisons·기한/정상 사유 테스트 |
| 다음 승인 단계 | Bridge/개인·월 정규화 | 기존 유형·중복·무환산·현재 수용 결과와 후보 대응·개인 적용 테스트 |
| 실제 연결 단계 | 검토된 데이터→Cashflow | 실제 FULL/VERIFIED/Benefit 검토/수용·개인 확인 모두 완료해야 연결 |

모델을 먼저 구현한다. 명시16필드/교차 규칙 없이 raw dict용 지문 함수부터 만들지 않는다. 반대로 모델 구현에 fingerprint utility·실제 source 연결을 함께 넣지도 않는다. Acceptance 전에 stable ID/scope/b version/정의 필드·provenance·전용 지문과 회귀 벡터가 모두 준비되어야 한다.

모델의 후속 파일 후보는 기존 policy_data 안의 `backend/policy_engine/policy_data/benefit_snapshot.py`, 합성 테스트는 `tests/test_benefit_snapshot.py`다.4개 Enum과 값 모델을 같은 작은 모듈에 두는 방향이며 지금 파일/폴더/export를 생성하지 않는다. 전용 지문은 별도 승인 단계에서 같은 패키지의 독립 함수로 추가한다.

새 Collection/loader/DB/API/UI/자동 수집/검토 플랫폼은 선행조건이 아니다. 공식 답변 전 실제 안산 FULL이나 ResidenceHistory 구현으로 확장하지 않는다.

## 33. 수동 시나리오 — BS01~BS100

**100개 문서상 사례**이며 실행 테스트가 아니다. 기본은28절 S다. “수용 가능”은 구조/지원 범위만 통과한다는 뜻이며 실제 FULL·VERIFIED·근거/수용 기록·기한 요건을 별도로 요구한다. 변경 비교는 유효한 payload를 사용하며 실제 발행 시 새 b version이 필요하다.

| ID | 입력·변경 | 기대 |
|---|---|---|
| BS01 | canonical policy_id | 구조 통과, lineage의 정책 차원 |
| BS02 | canonical benefit_id | 구조 통과, 정책 안의 component |
| BS03 | exact Scope2026/Q3 | 원래 값 보존·지문에 포함 |
| BS04 | scope quarter=None | annual로 명시, 미입력 아님 |
| BS05 | b0001 | version 통과, 자동 생성 없음 |
| BS06 | FIXED100000 | 유효, 다른 요건 후 수용 검토 가능 |
| BS07 | FIXED0 | 유효, None과 구별·B applied0 가능 |
| BS08 | amount=-1 | Data Error |
| BS09 | amount=True | Data Error·1로 변환 금지 |
| BS10 | amount=100000.0 | Data Error·반올림 없음 |
| BS11 | VARIABLE/None/비공백 설명 | 유효 비고정 정의, 초기 Acceptance 불가 |
| BS12 | MONTHLY | 정의 유효, B 지원 주기 |
| BS13 | QUARTERLY | 정의 유효, B 비월 지급 제외 |
| BS14 | ANNUAL | 정의 유효, /12 금지 |
| BS15 | ONE_TIME + 한 월 | 정의 유효, B 비월 지급 제외 |
| BS16 | cadence UNKNOWN | 유효 incomplete, 수용 불가 |
| BS17 | UNRESTRICTED_CASH+UNRESTRICTED | 조합 통과, B 유형 gate 가능 |
| BS18 | LOCAL_CURRENCY+RESTRICTED/details | 정의 유효, B 제한수단 제외 |
| BS19 | VOUCHER | 올바른 제한 검토 전제 유효, B 제외 |
| BS20 | IN_KIND+UNRESTRICTED | 정의 유효, 현물은 자유 현금 아님 |
| BS21 | SAVINGS_MATCH+잠금 제한 설명 | 정의 유효, B 제외 |
| BS22 | UNRESTRICTED/details=None | 제한 값 통과 |
| BS23 | RESTRICTED+비공백 details, 적합 medium | 제한 값 통과, 자유 텍스트로 조건 판정 안 함 |
| BS24 | restriction UNKNOWN+medium UNKNOWN | 정상 incomplete, 수용 불가 |
| BS25 | annual scope+2026-01~12 정렬 목록 | 구조 유효, 자동 목록 생성 없음 |
| BS26 | QUARTERLY+명시2026-03/06/09/12 | 구조 유효, 공식 지급월 근거 별도 |
| BS27 | 한 월 tuple | 구조 통과 |
| BS28 | months 중복 | Data Error·dedupe 없음 |
| BS29 | months 역순 | Data Error·자동 정렬 없음 |
| BS30 | 2026-13/2026-00 | Data Error |
| BS31 | months=None | 정상 미확정, 수용 불가 |
| BS32 | evidence 하나 | refs 형식 통과·실제 존재는 외부 검사 |
| BS33 | evidence 여러 개·정확한 source 집합 | 구조 통과 |
| BS34 | 동일 evidence 중복 | 구조/지문 보존, 사용 gate에서 중복 오류 |
| BS35 | evidence 순서 반전 | 두 유효 표현의 지문 다름 |
| BS36 | evidence=() | Snapshot 구조 오류 |
| BS37 | 현재 dataset 일치 | provenance 결합 통과 가능 |
| BS38 | 현재 Registry fp 일치 | provenance 결합 통과 가능 |
| BS39 | 관련 source d version 변경 | 정의 지문 변경·새 b/review 필요 |
| BS40 | 같은 정의 반복 지문 | 같은 canonical bytes/digest |
| BS41 | amount125000으로 변경 | 정의 지문 변경 |
| BS42 | cadence 변경 | 정의 지문 변경 |
| BS43 | medium을 IN_KIND로 변경 | 정의 지문 변경, 제한조합도 유효해야 함 |
| BS44 | IN_KIND의 제한/details 변경 | 정의 지문 변경 |
| BS45 | 명시 months 변경 | 정의 지문 변경 |
| BS46 | evidence ref 추가 | 정의 지문 변경 |
| BS47 | scope Q3→annual | 정의 지문 변경, 승인 승계 없음 |
| BS48 | b0001→b0002만 변경 | 지문 변경, 동일 금액이어도 재수용 |
| BS49 | Acceptance reviewed_at 변경 | 정의 지문 불변, Snapshot 필드 아님 |
| BS50 | Acceptance status 변경 | 정의 지문 불변, lifecycle 별도 |
| BS51 | review artifact ref 변경 | 정의 지문 불변, 검토 revision 추적 |
| BS52 | S + FULL/VERIFIED/정확한 수용·개인/월 요건 | B 합성100000 가능, Snapshot만으로 적용 안 함 |
| BS53 | 검토된 quarterly cash | 유효/수용 가능, B NON_MONTHLY_PAYMENT·0 |
| BS54 | 검토된 monthly local currency | 유효/수용 가능, B RESTRICTED_MEDIUM·0 |
| BS55 | 검토된 voucher | 정의 유효, B0 |
| BS56 | 유효 Snapshot이나 record 없음 | 미수용, 자동 ACCEPTED 안 만듦 |
| BS57 | 정상 새 b version에 과거 Acceptance | 정상 unusable |
| BS58 | 정확한 정의/provenance의 Acceptance | 해당 binding만 통과, FULL 등 별도 |
| BS59 | frozen 값 변경/삭제 시도 | 불변성 유지·거부 |
| BS60 | to_dict 반복·반환 nested list 변경 | 새 값 표현, 원본 영향 없음 |
| BS61 | amount UNKNOWN/None/description=None | 유효 incomplete |
| BS62 | cadence UNKNOWN, 나머지 알려짐 | 정상 incomplete·수용 불가 |
| BS63 | medium UNKNOWN | 정상 incomplete·수용 불가 |
| BS64 | 유효하지만 미완료 definition | metadata gate에서 수용 차단 |
| BS65 | 같은 policy의 서로 다른 benefit IDs | 독립 Snapshot/Acceptance, 일괄 승인 없음 |
| BS66 | 실행 dataset에 같은 target/version 두 번 | 외부 batch Data Error·자동 dedupe 없음 |
| BS67 | 같은 definition version에 서로 다른 내용 | 외부 발급/Acceptance 비교 Data Error |
| BS68 | 정상 지문을 가진 조작 metadata | 지문은 서명/검토 진실성 인증 아님 |
| BS69 | 생성/타입 검증 성공 | 공식 의미/자격/지급 확정 아님 |
| BS70 | 현재 실제 안산 metadata | 이번에 실제 Snapshot/금액/지문 생성 금지 |
| BS71 | 실제 Coverage SLICE | Acceptance 발급 불가·반영0 유지 |
| BS72 | 가상 FULL의 S | 정의/수용/개인·월 gate를 분리해 검토 |
| BS73 | 가상 quarterly local currency Q | valid·검토 후 수용 가능성, B 두 이유로0 |
| BS74 | 같은 target/b version, 다른 fp | Data Error·정상 stale로 완화 금지 |
| BS75 | 잘못된 SourceBinding/d version | 기존 SourceBinding 생성/필드 검사 오류 |
| BS76 | 동일 입력100회 | 지문/serialization 동일·입력 불변 |
| BS77 | 함수가 파일을 열어 source resolve | 계약 위반·외부 준비 책임 |
| BS78 | 함수가 네트워크로 공식 자료 갱신 | 계약 위반 |
| BS79 | 현재시간으로 월/version 결정 | 계약 위반 |
| BS80 | 미등록 medium OTHER | Data Error·계약 개정 전 허용 안 함 |
| BS81 | 미등록 cadence VARIABLE | Data Error·IRREGULAR/UNKNOWN과 자동 매핑 안 함 |
| BS82 | Q3→Q4 | 지문 변경·scope 자동 승계 없음 |
| BS83 | Q3→annual | 지문 변경·연간 범위 확대 금지 |
| BS84 | amount claim이 ref A에서 검토됨 | Acceptance artifact의 amount 대응표에 명시 |
| BS85 | cadence claim이 ref B에서 검토됨 | 별도 대응표·refs에 B 포함 |
| BS86 | medium claim이 ref C에서 검토됨 | 공식 경제유형 검토, 입금 방식만으로 분류 금지 |
| BS87 | restriction claim이 ref D에서 검토됨 | typed restriction+details와 대응, 텍스트 실행 금지 |
| BS88 | payload dict key 생성 순서만 다름 | canonical recursive sort로 같은 bytes |
| BS89 | UNKNOWN/nullable 정의 | Enum 문자열/null key를 명시, key 생략 안 함 |
| BS90 | 한글 description/details | UTF-8 원문, BV10/11 기준 |
| BS91 | dataset만 새 값·관련 정의 동일 | Benefit fp 같음, 전체 Snapshot 다름·수용 재검토 |
| BS92 | 새 dataset의 unrelated Registry metadata 변경 | Benefit fp 같음·b 유지 가능, Acceptance 재검토 |
| BS93 | 같은 dataset의 Registry fp 변경 | current/발급 감사 Data Error |
| BS94 | source ID 누락/불필요 binding/중복 ID/역순 | 모델 correspondence 또는 로컬 오류 |
| BS95 | UNRESTRICTED_CASH+RESTRICTED/UNKNOWN | 모델 모순 오류 |
| BS96 | ONE_TIME+여러 알려진 월 | 모델 모순 오류; 한 월/None만 허용 |
| BS97 | VARIABLE에 amount int 또는 description 없음 | 모델 amount 조합 오류 |
| BS98 | amount_description에 고립 surrogate | 비공백 검사 통과 가능, strict 지문 encoding 오류 |
| BS99 | 현금+포인트를 한 fixed cash ID로 합침 | 외부 의미 검토에서 거부·독립 component ID 사용 |
| BS100 | 최소 Snapshot 값 모델을 다음 단계 구현 | 지문/Review/Acceptance/Bridge·실제 연결은 포함하지 않음 |

## 34. 미해결 문제·Assumptions·계약 보완 범위

**MVP Snapshot 모델의 필드/타입/version/로컬 규칙·payload는 이 문서에서 확정했다.** 구현을 막는 amount/evidence/source 구조 미정은 남겨두지 않는다. 실제 의미 검토와 후속 subsystem은 별도 미완료다.

| 후속/비목표 | 현재 경계 |
|---|---|
| 개인별 variable 금액 계산 | description/evidence 보존만, 산식 AST/정규화·계산은 미지원 |
| 복잡한 지급 event/개인 일정 | None 또는 외부 준비, schedule engine 없음 |
| 별도 benefit source release | MVP 동일 dataset/Registry, 향후 명시 계약 개정 필요 |
| 실제 claim별 근거 검토·현재 철회 선택 | Acceptance artifact·외부 준비 책임, 구조/지문이 진실성 인증 안 함 |
| FULL legacy 자료 연결·freshness 실행 gate·개인 적용 | 기존 M2.41 미완료 유지, Snapshot이 대신하지 않음 |
| 실제 안산 전체 정책 | 공식 거주 의미/다른 목록·조건·자료 검토 보류, 이번에 해결하지 않음 |

**Assumption A1:** 현재 정책 범위는 KRW이고 초기 수용은 고정 금액·명시 지급월이다. VARIABLE/UNKNOWN 표현은 수집 정의 보존을 위한 것이며 계산 범위 확장이 아니다.

**Assumption A2:** 단일 내부 dataset/Registry 확인본으로 현재 Coverage·Benefit·Envelope를 결합한다. source가 개념적으로 독립 변경 가능해도 서로 다른 release를 임의 혼합하지 않는다.

**Assumption A3:** Q3 회차와 범위 밖/연간 지급월의 관계는 가상/실제 근거가 명시해야 한다. constructor의 구조 허용은 그 의미의 승인과 다르다.

M2.41 보완: Benefit review ref/date는 Snapshot 필드가 아닌 Acceptance artifact, benefit_definition_* 후보명은 benefit_version/fingerprint로 확정, context provenance는 저장하되 정의 fp에서 제외, completeness와 구조 유효성을 분리한다. M2.4의 fixed-only 수용·기존 월/근거 이름과 M2.3 taxonomy/지원 범위는 유지한다. frozen Coverage 변경은 없다.

## 35. 최종 판단과 검증 기록

**READY_TO_IMPLEMENT_BENEFIT_SNAPSHOT_MODEL**

16필드·4개 최소 Enum·b version·로컬 교차 규칙·UNKNOWN/None·근거/provenance·15key 지문 projection과16개 literal vectors를 문서로 확정했다. 별도 amount 계산 모델/BenefitDefinitionReview/Collection을 선행 구현할 필요는 없다. 다만 지문 utility가 아직 없으므로 Acceptance 구현 준비 완료를 선언하지 않는다.

다음 가장 작은 작업 한 개: **BenefitSnapshot 값 모델과4개 Enum만 합성 unit tests로 구현**한다. exact 타입·금액/제한/월/refs/binding 경계·불변성·16key 새 serializer를 검증하고 기존5,687개 회귀를 보존한다. 지문 함수·Acceptance·Bridge·실제 데이터 연결은 포함하지 않는다.

사전 전체 pytest: **5687 passed in 14.07s**. 문서 작성 후 전체 pytest: **5687 passed in 13.80s**. 신규 실행 테스트는 없으며 기존 suite가 미구현 Benefit/Acceptance를 검증한 것은 아니다.

문서35개 절과 BS01~BS100의 연속/유일 ID, BV01~BV16의 literal JSON key 수·canonical 표현·strict UTF-8 byte length·SHA256을 대조했다. 표/코드 블록·한국어 표기도 확인했다. BV 계산은 문서의 합성 literals만 대상으로 했고 전용 함수·모델·테스트 코드를 생성하지 않았다.

사전 actual releases/pycache 제외 backend/tests/data/docs149개 파일 SHA256 대조에서 **기존149개 모두 동일, 이 문서1개만 추가되어150개**이며 수정/삭제는 없다. Coverage freeze·GV01~GV15·기존 테스트/기대값·M2.41 및 기존 명세·Cashflow·ResidenceHistory 자료를 보존했다. 실제 release6개 파일의 경로/크기/수정시각도 모두 동일하다. 실제 Ansan snapshot·지문·금액·Review·Acceptance를 생성하지 않았다.

## 36. M2.43 — IMPLEMENTED: BenefitSnapshot 불변 값 모델

`backend/policy_engine/policy_data/benefit_snapshot.py`에 BenefitAmountType, BenefitPaymentCadence, BenefitMedium, BenefitRestriction와 BenefitSnapshot을 구현했다. `policy_data` public export에는 이5개 타입만 additive하게 추가했다. 기존 Coverage public API/의미와 기존 export는 변경하지 않았다.

2절의 정확한16개 필드·순서·타입을 그대로 사용하며 nullable 필드도 모두 keyword-only 필수다. frozen/slots dataclass이고 equality는16개 저장 값 전체를 비교한다. 기존 ApplicabilityScope/SourceBinding 원본·tuple 순서·유효 문자열을 보존한다. b version/ID grammar·exact Enum/int·비공백 문자열·YYYY-MM·lowercase hex64를 엄격히 검사하며 자동 보정/변환은 없다.

27절 순서대로 로컬 필드를 먼저 검사한 뒤 amount·restriction·두 cash medium 모순·ONE_TIME/month count·evidence/source 집합 대응을 검사한다. ID grammar는 기존과 동일한 작은 식을 사용하되 Envelope private validator의 오류에 결합하지 않는다. parse_evidence_ref는 기존 helper를 재사용하고 SourceValidationError는 원래 객체로 전파한다. SourceBinding을 재정의하거나 Registry를 조회하지 않는다.

FIXED는 exact int≥0/description=None, VARIABLE은 amount=None/비공백 설명, UNKNOWN은 amount/description=None이다.0원·큰 int·유효 부분 Snapshot을 보존한다. 제한·월 교차 규칙도11~12절 그대로다. evidence 중복/순서는 구조 값에서 보존하고, bindings는 source ID 유일·오름차순 및 refs source 집합과의 정확한 대응을 요구한다. dataset/Registry 지문은 값으로 저장하며 실제 자료 일치는 판정하지 않는다.

to_dict는 정확한16개 key의 새 중첩 dict/list를 반환한다. Enum.value·기존 Scope.to_dict·명시 SourceBinding 두 필드 projection·nullable key를 사용한다. 파생 completeness/status·review metadata·benefit_fingerprint·Bridge 지원/월 환산액은 없다. 직접 의존은 dataclasses/enum/re·기존 PolicyDataError/parse_evidence_ref/Scope/SourceBinding뿐이다. 지문/Acceptance/Bridge/Cashflow·시각/I/O를 호출하거나 import하지 않는다.

신규 `tests/test_benefit_snapshot.py` **292개**는16fields/slots/annotations/keyword-only 필수성·4개 Enum 전체 member·엄격한 타입/grammar·fixed/variable/unknown·모든 cadence/medium·제한/월/refs/binding 교차 규칙·오류 순서/전파·불변성·전체 필드 equality·provenance 차이·새 serializer·nested mutation isolation·100회 결정성을 검증한다. Registry 미조회와 직접 의존/산술·실행 부재도 확인했다. 기존 테스트/fixture/기대값은 수정하지 않았다.

사전 전체 **5687 passed in 15.05s**, 신규 **292 passed in 0.83s**, 전체 **5979 passed in 14.87s**다. BV01~BV16은 문서 literal 그대로이며 이번에는 실행 지문 테스트로 옮기거나 SHA256을 계산하지 않았다. 이 결과는 Snapshot 구조 모델의 검증이며 공식 근거·검토/수용 완료를 뜻하지 않는다.

**IMPLEMENTED:** BenefitSnapshot·4개 Benefit Enum·strict 로컬 검증·불변성/equality·16key serializer·합성292개 테스트.

**NOT IMPLEMENTED:** Benefit fingerprint 함수/BV 실행 golden tests·BenefitAcceptance·Acceptance evaluator·review artifact resolution·Benefit Bridge·Cashflow 연결·실제 Ansan Snapshot/금액/지문. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, generic Coverage는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**를 유지한다.

최종 판단: **READY_TO_IMPLEMENT_BENEFIT_FINGERPRINT**. 다음 가장 작은 작업 한 개는 별도 승인 후 `fingerprint_benefit_snapshot(snapshot)` 하나를 구현하고 기존 BV01~BV16 literal JSON/bytes/digest를 실행 테스트로 고정하는 것이다. 이번 모델/생성/직렬화가 지문을 자동 계산하게 바꾸거나 Acceptance로 진행하지 않는다.

### M2.43 최종 변경 범위

사전 actual releases/pycache 제외 backend/tests/data/docs150개 파일 SHA256 대조에서 기존146개가 동일하다. 변경은 public export와 이 명세·DATA_MODEL.md·ARCHITECTURE.md의4개 파일뿐이며 새 모델/합성 테스트2개를 추가해152개가 됐다. 삭제는 없다. frozen Coverage source·freeze 문서·기존 모든 테스트/기대값·GV01~GV15·Cashflow·ResidenceHistory 관련 자료는 변경하지 않았다. 실제 release6개 파일의 경로/크기/수정시각도 동일하다.

문서의36개 절·기존 BS01~BS100·BV01~BV16 literal 블록과 기준값·코드 블록/한국어 표기를 확인했다. 이번 신규 테스트는 지문을 계산하거나 BV digest를 실행 검증하지 않는다. 실제 정책 정의·금액·지문·검토/수용 기록은 생성하지 않았다.

## 37. M2.44 — IMPLEMENTED: 전용 Benefit 정의 지문과 BV 실행 검증

`backend/policy_engine/policy_data/benefit_fingerprint.py`에 공개 순수 함수 `fingerprint_benefit_snapshot(snapshot: BenefitSnapshot) -> str` 하나와 private payload helper를 추가했다. policy_data public export에는 이 함수만 추가했다. 입력은 exact BenefitSnapshot이며 None/dict/list/tuple/문자열/가짜 객체/subclass는 payload 구성 전에 PolicyDataError로 거부한다. 추가 semantics 옵션은 없다.

23절의 정확한15개 key를 명시적으로 projection한다. schema는 benefit-snapshot-1.0이고 policy/scope/benefit/version·금액 정의·주기·수단·제한·월·근거·관련 SourceBinding을 포함한다. 일반 to_dict/asdict 전체를 hash하지 않으며 Scope도 edition_id/quarter를 직접 선택한다. dataset_version/Registry 전체 지문은 제외한다. 이 둘은16필드 값 equality/일반 serializer에는 남지만 정의 지문에는 영향을 주지 않는다.

월·refs·bindings 순서와 evidence 중복을 그대로 유지하고 nullable key는 null로 명시한다. Enum은 canonical value다. canonical JSON은 sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False이며 strict UTF-8·BOM/말미 newline 없음·SHA256 lowercase hex64를 따른다. Unicode/공백/개행을 정규화하지 않는다. JSON/UTF-8의 TypeError/ValueError/UnicodeError는 원본 payload 없이 PolicyDataError로 전달하고 fallback 결과는 없다.

22절대로 동결 Coverage private helper를 import/추출하지 않았다. 새 모듈의 작은 표준 json/hashlib recipe만 사용하며 Coverage 코드·schema·GV는 변경하지 않는다. Snapshot 생성/로컬 검증·Registry resolve·원문/파일/Git/환경/시각·Acceptance·Bridge·Cashflow를 호출하지 않는다. 원래 Snapshot/Scope/tuple/bindings는 변경하지 않는다.

신규 `tests/test_benefit_snapshot_fingerprint.py` **74개**를 추가했다.30절에서 복사한 literal JSON/UTF-8 길이/digest와 별도로 구성한 실제 합성 모델을 대조해 **BV01~BV16 전체 일치**를 확인했다. 실제 JSON payload/옵션·문자열과 hash에 전달한 bytes를 캡처해 비교하며 기대값을 구현 함수로 계산하지 않는다. BV05는 IN_KIND의 제한/영문 details, BV10은 한글 details 등 문서의 실제 vector 의미를 그대로 사용했다.

추가 검증은 dataset-only/Registry-only/둘 변경의 equality≠·fingerprint=, 정의/identity/scope/version 변경의 지문 변화, evidence 순서/중복·관련 source d version, UNKNOWN/null, serializer/constructor/Registry 미사용, UTF-8 strict 오류·JSON 오류 wrapping, Unicode/NFC·NFD/escaping 보존, mutation isolation·100회 결정성·public export/입력 서명이다. 기존 M2.43 모델292개와 나머지 기존 테스트/기대값은 수정하지 않았다.

검증: 사전 전체 **5979 passed in 13.91s**, 신규 **74 passed in 0.41s**, 전체 **6053 passed in 13.39s**다. 전체 회귀에 기존 Coverage/GV·Cashflow·모델 tests가 포함된다. 이 결과는 정의 지문 동일성을 검증하며 검토 진실성·공식 자격·수용/지급을 승인하지 않는다.

**IMPLEMENTED:** fingerprint_benefit_snapshot·정확한15key projection/encoding·BV01~BV16 executable golden tests·합성74개 지문 테스트.

**NOT IMPLEMENTED:** BenefitAcceptance/status/evaluator·review artifact resolution·Bridge·Cashflow 연결·actual BenefitSnapshot/지문/금액. Snapshot의16개 저장 필드·4개 Enum·일반 serializer는 바꾸지 않았다. 실제 안산은 DRAFT/CONDITION_SLICE·반영0원 원칙, ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, Coverage freeze는 유지한다.

최종 판단: **READY_FOR_BENEFIT_ACCEPTANCE_MODEL_DESIGN**. 정의 binding 기반은 준비됐지만 M2.41의 수용 record/result exact 계약은 아직 후보 단계다. 다음 가장 작은 작업 한 개는 **PolicyBenefitAcceptance record의 정확한 필드·scope/version identity·Coverage9개/Benefit/provenance 결합·기한/철회 불변조건을 문서로 확정**하는 것이다. Acceptance 코드/evaluator/Bridge로 자동 진행하지 않는다.

### M2.44 최종 변경 범위

사전 actual releases/pycache 제외 backend/tests/data/docs152개 파일 SHA256 대조에서 기존149개가 동일하다. 변경은 public export와 이 명세·ARCHITECTURE.md의3개 파일뿐이며 새 전용 함수/합성 테스트2개를 추가해154개가 됐다. 삭제는 없다. BenefitSnapshot 모델·M2.43의292개 테스트·나머지 기존 테스트/기대값·DATA_MODEL.md·동결 Coverage source/문서/GV01~GV15·Cashflow·ResidenceHistory 관련 자료는 변경하지 않았다.

문서37개 절·BS01~BS100·코드 블록/한국어 표기를 확인했다. BV01~BV16의 문서 JSON literal·byte length·digest는 사전 확인본과 그대로 일치한다. 실제 release6개 파일도 경로/크기/수정시각이 동일하며 actual Ansan Snapshot·지문·혜택 금액·Review/Acceptance는 생성하지 않았다.
