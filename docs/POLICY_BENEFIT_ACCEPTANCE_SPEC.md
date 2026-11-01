# 정책 혜택의 시뮬레이션 수용 계약 — M2.4

작성일: **2026-10-21 / Asia/Seoul**. **문서 전용**. 모델·Enum·validator·Bridge·정책 연결은 구현하지 않았다.

최종 판단: **NEEDS_POLICY_COVERAGE_MODEL_REVISION**. 수용 기록·버전·월 적용 계약은 아래와 같이 제안한다. 현재 CONDITION_SLICE 전용 모델을 FULL_POLICY라고 선언할 수 없으므로 실제 acceptance 발급/연결로 진행하지 않는다.

## 1. 목적

“정책 조건을 충족하는가?”와 “검토한 정책 혜택을 우리 서비스의 경제 시뮬레이션에 사용할 수 있는가?”를 분리한다. 정책 혜택 자체에 대한 수용 기록과 사용자별 판정·대상 월 확인·Bridge의 현금 유형 필터가 모두 필요하다.

검토 기준은 CASHFLOW_BENEFIT_BRIDGE_SPEC.md, CASHFLOW_ENGINE_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, POLICY_RULE_SPEC.md, RULE_ROUTING_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md와 현재 policy_data/envelope.py 및 실제 releases 001/002의 확인본이다. 공식 사이트의 정책 내용을 새로 조사하거나 실제 지급을 확인한 작업이 아니다.

이 문서는 M2.3의 미확정 acceptance_status를 구체화한다. 아래에 명시한 후속 설계 변경은 문서상 제안이며 기존 코드나 문서를 소급 수정한 것이 아니다. 실제 승인은 사용자 검토 후 별도 단계에서 구현한다.

## 2. Domain Validity / Verification / Acceptance 분리

| 층 | 정확한 의미 | 보장하지 않는 것 |
|---|---|---|
| DOMAIN VALID | 구조·타입·규칙·참조가 계약에 맞음 | 공식 근거 검토 완료, 전체 범위, 혜택 수용 |
| VERIFIED | 공식 근거와 정책 조건을 해당 확인본 기준으로 검토함 | 전체 범위, 개인 PASS, 혜택 금액 검토, 월 적용 |
| SIMULATION_ACCEPTED | 정해진 정책/혜택 버전·금액·범위의 시뮬레이션 사용 검토를 완료함 | 실제 지급 승인, 모든 사용자 적용, 직접 월 현금 반영, 배포 승인 |

원문 SourceDocument/locator VERIFIED와 PolicyEnvelope VERIFIED도 서로 다르다. source VERIFIED로 정책 DRAFT를 승격하지 않는다. 이 층들을 하나의 bool로 합치지 않는다.

## 3. Acceptance 의미

**“우리 서비스의 경제 시뮬레이션에서 이 정책 혜택을 계산에 포함해도 되는 수준으로 데이터·규칙·금액·적용범위 검토가 완료됐다.”**

정책/혜택 정의의 재사용 가능한 검토 결과이며 개인의 신청·지급 승인이나 현금 입금 사실이 아니다. 표시 문구는 “시뮬레이션 반영 검토 완료”다. 개인별 출력 금액은 “시뮬레이션상 반영 가능한 정책 혜택”으로 설명한다.

SIMULATION_ACCEPTED와 PRODUCTION_DEPLOYMENT_APPROVED는 별개다. 배포 승인 workflow·권한 시스템·전자서명·운영 인증을 이번 MVP에 추가하지 않는다. M2.3의 “production 수용 확인”은 이 문서 이후 **버전이 고정된 시뮬레이션 수용 확인**으로 정밀화한다. 기존 POLICY_DATA_ENVELOPE_SPEC.md의 자료 수용·review·freshness·참조 검증 의무를 삭제하거나 충족했다고 주장하지 않는다. 특히 ACCEPT(CONDITION_SLICE)는 전체 정책 혜택 수용으로 전환할 수 없다.

## 4. 최소 Acceptance 구조

별도 **PolicyBenefitAcceptance** 불변 객체를 추천한다. 아래는 미구현 후보 필드다.

| 필드 | 계약 |
|---|---|
| policy_id / edition_id / benefit_id | 검토한 혜택 component의 정확한 대상 identity |
| acceptance_version | a0001 형태의 명시적 양의 버전; 자동 생성 없음 |
| status | ACCEPTED 또는 REVOKED |
| rule_version | 수용한 정확한 정책 rule_version |
| dataset_version | 수용한 정확한 데이터 snapshot ID |
| source_bindings | 정책·혜택 근거의 (source_document_id, document_version) 유일 목록 |
| accepted_terms | 검토한 혜택 정의의 불변 작은 값 묶음: amount_krw, payment_cadence, benefit_medium, applicable_months, benefit_evidence_refs |
| reviewed_at | 명시적인 정확한 date; 시스템 오늘로 채우지 않음 |
| valid_until | 수용 확인을 사용할 마지막 data_use_date. 정확한 date, reviewed_at 이상 |
| review_ref | 불변 검토 기록의 안정 참조. 발급·철회 사유도 해당 기록으로 추적 |

별도의 acceptance_id 문자열 없이 `(policy_id, edition_id, benefit_id, acceptance_version)`를 수용 identity로 사용한다. 기존 benefit dedupe identity `(policy_id, benefit_id)`는 유지한다. acceptance_version은 내부 수용 기록 버전이며 rule/source/edition의 별칭이 아니다.

accepted_terms는 원문이나 사용자 입력을 복제하는 객체가 아니다. 수용한 금액/유형/지급월이 이후 바뀌지 않았는지 직접 비교할 최소 snapshot이다. 소득별 계산식·일정 엔진·사용자 결과·실제 계좌·자동 시각을 넣지 않는다. accepted_coverage 필드는 중복 저장하지 않는다. ACCEPTED의 생성 전제는 검토된 FULL_POLICY이며 실제 사용 시에도 현재 coverage를 다시 확인한다.

정책/benefit ID는 안정 ID 문법, edition/rule/dataset/source 버전은 기존 규약을 따른다. 문자열 자동 보정·숫자 변환은 없다. source_bindings와 evidence_refs는 불변 tuple이며 중복·미등록 연결을 외부 검토에서 거부한다. reviewed_at/valid_until과 월 표현의 정확한 타입은 후속 모델 승인 시 고정한다.

## 5. Status

**추천: 기록 없음 + ACCEPTED / REVOKED.** 미검토·검토 중·검토 미통과는 승인 기록을 발급하지 않는다. 검토 이력의 사유는 review_ref 쪽에 두며 runtime status를 늘리지 않는다. EXPIRED는 저장 상태가 아니라 명시적 data_use_date와 valid_until의 비교 결과다.

| 상태 | 적용 의미 |
|---|---|
| 해당 acceptance 없음 | 미수용. 정상 제외 |
| ACCEPTED | 버전·시점·범위 등 후속 gate를 검토할 수 있음 |
| REVOKED | 정상 제외. 이 기록을 다시 ACCEPTED로 변이시키지 않음 |

PENDING/REJECTED/EXPIRED를 모두 저장하면 검토 workflow와 시간 상태가 섞인다. bool만 쓰면 철회와 기록 identity·버전 추적이 사라진다. 그래서 작은 record와 두 상태를 선택한다. 실제 거절/철회를 했다는 가상 검토 기록은 생성하지 않는다.

## 6. Coverage gate

ACCEPTED 발급에는 **FULL_POLICY**가 필수다. 필요한 조건·적용 회차·효력/신청/지급 관련 범위가 검토되어 있어야 한다. 일부 root의 모든 노드가 PASS라는 이유로 FULL_POLICY로 만들지 않는다. CONDITION_SLICE에는 ACCEPTED를 발급할 수 없다. 사용 시에도 slice는 POLICY_NOT_FULLY_EVALUATED로 제외한다.

현재 코드의 EvaluationScope에는 CONDITION_SLICE만 있다. PolicyCoverage는 included_rule_ids와 **비어 있지 않은 excluded_conditions**를 요구한다. 현재 Envelope에는 FULL_POLICY를 유효하게 표현할 수 없다. 별도 acceptance 객체가 이 제약을 우회해서는 안 된다.

**다음 설계에서 필요한 범위:** FULL_POLICY의 검토 단위와 필수조건 완결성 근거, full/slice별 coverage 불변조건, edition=연도와 실제 회차 범위의 구별을 먼저 결정한다. 단순 Enum 추가·excluded_conditions를 빈 tuple로 바꾸는 것만으로 완결성을 증명하지 않는다. 이번에는 어느 모델도 수정하지 않는다.

## 7. Verification gate

발급 시 Envelope VERIFIED가 필수다. DRAFT/STALE에는 발급하지 않는다. 정책 조건 근거와 혜택 근거의 source/locator도 해당 확인본의 검토가 완료되어야 한다. 정책·source 검증 상태의 의미를 섞지 않는다.

사용 시에도 현재 고정 자료의 verification과 명시적 data_use_date에 대한 기존 freshness 조건을 별도 확인한다. acceptance의 valid_until 안이라는 사실만으로 source freshness를 통과시키지 않는다. data_use_date가 바뀌거나 철회·정정 사실이 확인되면 정규화 계층이 재검토한다. Bridge는 현재 시각·웹·DB를 조회하지 않는다.

## 8. User eligibility gate

정책 정의를 수용할 때 특정 사용자의 PASS를 요구하지 않는다. acceptance는 여러 가상 사용자에 재사용할 수 있는 **정책 혜택 자체의 검토**다. 대신 반영 시 **그 사용자에 대한 FULL_POLICY 평가 PASS**가 반드시 필요하다. FAIL/UNKNOWN은 ELIGIBILITY_NOT_PASS로 정상 제외한다.

평가 결과는 acceptance와 같은 policy/edition/rule/dataset·근거 확인본 및 명시적 기준으로 만들어져야 한다. PolicyEvaluation 단독에는 coverage·edition·모든 benefit 정보가 없으므로 기존 Envelope와 결합하는 외부 정규화 책임이 남는다. Bridge는 eligibility를 재계산하지 않는다. PASS의 사용자 문구와 행정적 자격 확정 금지 원칙을 유지한다.

## 9. Benefit metadata verification

수용 검토에서 조건 검증과 별도로 다음을 확인한다.

| 대상 | 검토 내용 |
|---|---|
| amount_krw | 지급 한 회의 확정 금액. 상한/예상/개인 심사 후 결정액과 구별 |
| payment_cadence | MONTHLY 등 원래 지급주기. 월 환산하지 않음 |
| benefit_medium | 자유 현금·지역화폐 등 경제유형과 사용/저축 제한 |
| applicable_months | 공식 근거로 확인한 적용 월의 유한 목록 |
| evidence | 안정 근거 ref가 검토한 source version의 locator에 연결됨 |

검토가 끝난 지역화폐·분기 지급 metadata도 수용 기록으로 표현할 수 있다. 이는 그 혜택 정의를 시뮬레이션에서 사용할 수준으로 검토했다는 뜻이며, **현재 direct monthly cash Bridge의 적용 승인이 아니다**. Bridge의 cadence/medium gate가 계속 제외한다. 이번에는 제한형 경제효과를 구현하지 않는다.

## 10. Rule/version binding

rule_version은 정확히 일치해야 한다. 새 rule_version에 기존 acceptance를 자동 승계하지 않는다. 다른 정상 버전으로 이동한 경우 ACCEPTANCE_VERSION_MISMATCH로 제외하고 새 검토 기록이 필요하다.

같은 버전인데 실제 규칙 내용이 달라졌다면 정상적인 갱신이 아니라 immutable version 계약 위반이며 Data Error다. 해시/기존 fingerprint와 검토 snapshot의 실제 일치는 외부 자료 준비 계층이 확인한다. Bridge가 원문 규칙을 import하거나 새 해시 framework를 만들지 않는다.

## 11. Dataset/source binding

dataset_version도 정확한 snapshot ID에 묶는다. 전체 DatasetManifest loader의 완성을 선행 구현하지 않고, 외부에서 고정한 dataset ID·규칙·source 확인본과 수용 기록을 대조한다. ID가 같다는 이유만으로 파일 동일성을 인증하지 않는다. 외부 검토는 immutable 확인본/기존 fingerprint 또는 실제 bytes hash를 review_ref에 연결해야 한다. 불변 snapshot을 확인할 수 없으면 수용 기록을 발급하지 않는다.

source_bindings는 정책 근거와 benefit 근거의 합집합이다. 각각의 document_version과 연결 ref는 정확히 같아야 한다. 정정공고·금액/지급수단 변경·새 source version은 새 검토 대상이다. URL 변경으로 저장 metadata version이 바뀌면 의미가 같아도 자동 승계하지 않는다. 재검토 범위가 URL 연결 확인에 한정될 수는 있으나 새 수용 버전은 명시적으로 발급한다.

기존 확인본을 수정하지 않은 단순 네트워크 redirect는 그 자체로 새 의미나 새 버전이라고 추정하지 않는다. 접근 문제·공식성/freshness 미확인은 기존 source 정책대로 재검토한다. URL 문자열 일치만으로 수용을 복구하지 않는다.

## 12. Individual applicability

사용자별 applicability_status=CONFIRMED도 필요하다. 의미는 M2.3을 유지한다: 해당 시나리오·월의 개인 적용조건 확인, monthly_income과 지급액 중복 없음, 다른 후보와 의미상 중복 없음, 병급/선택형 충돌 없음이다. UNCONFIRMED/NOT_APPLICABLE은 NOT_CASHFLOW_ELIGIBLE로 제외한다.

acceptance record에는 사용자 ID·소득·주민등록 사실·PASS를 저장하지 않는다. 개인 확인은 요청 단위 assessment_ref와 후보에만 결합한다. **Assumption A1:** 신뢰된 내부 정규화 계층이 사실·평가·시나리오 결합을 확인한다. 사용자나 LLM이 선언한 CONFIRMED를 신뢰하지 않는다. 구체적 개인 확인 adapter는 이번 범위 밖이고 미구현이다.

## 13. Target month

최소 일정 계약으로 accepted_terms.applicable_months를 **정렬된 중복 없는 비어 있지 않은 YYYY-MM tuple**로 제안한다. 정확한 달력 연월(연도0001~9999, 월01~12)이어야 한다. 월이 드문드문 있는 경우도 열거하므로 범위 안 모든 달이 지급월이라고 추측하지 않는다. cadence는 원래 주기이며 이 목록으로 분기 지급을 월 지급으로 바꾸지 않는다.

BridgeContext.target_month가 이 목록에 있어야 한다. 없다면 TARGET_MONTH_NOT_APPLICABLE로 정상 제외한다. MONTHLY라도 9월까지만 적용되면 10월은 제외다. target_month는 예산 대상 월, context.data_use_date는 자료 수용 유효성을 확인할 명시적 날짜다. 둘을 혼동하지 않는다. 연도 edition과 target_month의 숫자가 같다는 이유로 적용하지 않는다.

**Assumption A2:** 첫 계약은 공통으로 확정된 지급월 목록과 고정 금액의 단순 시뮬레이션만 지원한다. 가입일별 일할·부분 월·지연/소급 지급·개인별 지급 일정 미확정은 자동 계산하지 않고 개인 적용 미확인으로 제외한다. 기간 경계가 월 단위로 확정되지 않았다면 임의로 전월/전체 월을 넣지 않는다. schedule engine·현재 월/분기 자동 선택은 없다.

## 14. Fixed amount

초기 ACCEPTED record의 accepted_terms.amount_krw는 **확정된 0 이상 정확한 int**만 허용한다. None/상한액/범위/소득별 미계산 금액으로 발급하지 않는다. 고정 금액을 모든 사용자에게 일반화할 수 없는 혜택은 초기 수용 대상에서 보류한다. 후속 계산식 모델을 미리 추가하지 않는다.

candidate의 amount_krw=None은 M2.3처럼 정상 제외다. 정수로 확정된 candidate 금액과 accepted_terms의 금액이 다르면 같은 버전의 정의 모순이므로 Data Error다. 정상적으로 버전이 달라졌다면 먼저 version mismatch로 제외한다. 0원은 모든 gate 통과 시 applied에 남고 합계는0이다. bool/float/문자열/Decimal/음수는 오류, 큰 int는 정확하게 보존한다. 자동 월할·반올림·최대 금액 제한은 없다.

## 15. Evidence/reviewer

review_ref는 팀 내부의 **실제로 수행한 불변 검토 기록**을 가리킨다. 최소 기록 내용: prepared_by/reviewed_by의 서로 다른 팀 handle, reviewed_at, 대상 acceptance identity·rule/dataset/source 확인본, coverage 완결성 참조, benefit_evidence_refs, 수동 사례 ID, 승인/철회 사유와 note다. 실명·전자서명·계정 시스템을 요구하지 않는다.

Rule evidence 목록 전체를 runtime acceptance에 복제하지 않는다. 정책 근거는 검토한 rule/dataset/source bindings와 review_ref로 추적하고, 혜택 금액·수단·지급월의 근거만 accepted_terms의 stable ref로 연결한다. metadata 기록에서 refs는 실제 고정 source version의 locator에 연결되어야 한다. review_ref가 존재한다는 문자열만으로 검토 사실을 보장하지 않는다. 생성·근거 대조는 외부 검토 책임이다.

이 작업은 실제 reviewer·acceptance·승인 파일을 생성하지 않는다. 기존 M1 review/Manifest가 완성됐다고 주장하지 않는다. 경제정보나 사용자 결과를 감사 목적으로 영구 저장하지 않는다.

## 16. Expiry/revocation

**날짜와 버전 두 경계 모두 사용**한다. 명시적인 data_use_date가 reviewed_at 이상 valid_until 이하여야 수용 확인이 유효하다. 상한 초과는 ACCEPTANCE_EXPIRED, 검토일보다 이른 사용일은 SIMULATION_NOT_ACCEPTED로 제외한다. 자동 7일 만료·무기한 기본값은 만들지 않는다. valid_until은 실제 검토자가 근거와 재확인 기준으로 명시하고 source freshness gate를 대신하지 않는다.

대상 월이 미래라도 검토 사용일의 만료와 지급월 적합성은 각각 확인한다. 새 연도/edition·규칙·자료·source version은 정확한 결합 불일치로 재검토한다. 기존 범위 밖 분기를 수용 기록이 확장하지 않는다.

정정으로 과거 기록을 사용하면 안 되면 새 acceptance_version의 REVOKED record를 발급하고 review_ref에 이전 identity와 철회 사유를 연결한다. 새 조건을 승인할 때도 새 버전 ACCEPTED를 발급한다. 기존 기록은 수정/삭제하지 않는다. 호출자는 해당 benefit에 대한 **명시적으로 선택한 최신 유효 검토 상태**를 전달하며 임의의 과거 ACCEPTED만 골라 전달하지 않는다. Bridge는 최신 버전을 검색하지 않는다.

**Assumption A3:** 외부 준비 계층이 현재 사용 가능한 승인/철회 상태를 완전하게 선택한다. 폐기된 record를 누락한 입력만으로 순수 Bridge가 철회를 발견할 수는 없다. 과거 snapshot 재현은 별도 표기하며 현재 반영 승인으로 사용하지 않는다. workflow/registry 서버는 구현하지 않는다.

## 17. Current Ansan example

실제 policy_id=KR-GG-ANSAN-YOUTH-BASIC-INCOME, edition=2026이다. 001은 r0001 주민등록 한 조건, 002는 r0002 주민등록+Q3 출생일의 부분 범위다. 두 Envelope 모두 **DRAFT / CONDITION_SLICE**이고 excluded_conditions가 남아 있다. source/locator VERIFIED가 전체 정책 검증을 뜻하지 않는다.

따라서 **ACCEPTED 발급 불가, Bridge 반영액0**이다. 002에서 두 조건 모두 PASS여도 변하지 않는다. benefit 정의·금액·지급월도 실제 Envelope에는 아직 없다. 가짜 benefit_id나 승인 기록을 넣지 않는다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 보류한다.

## 18. Future full-policy example

**가상 예시:** 향후 안산 정책이 FULL_POLICY·VERIFIED가 되고, 고정 혜택 정의 검토와 acceptance 기록이 완료되며 사용자 PASS·대상 월 적용까지 확인됐다고 가정한다. 지급수단 LOCAL_CURRENCY, 지급주기 QUARTERLY이면 현재 direct Bridge는 계속 **0원**이다. NON_MONTHLY_PAYMENT / RESTRICTED_MEDIUM을 남긴다.

acceptance가 모든 Bridge gate를 대신하지 않는다. 분기액을 3으로 나누지 않고 지역화폐를 저축 가능한 현금으로 만들지 않는다. 실제 안산 정책을 완성/승인한 예시가 아니다.

## 19. BenefitCandidate 연결

| 방식 | 장점/한계 | 선택 |
|---|---|---|
| A 객체 직접 포함 | 로컬 대조 쉬움, 후보마다 검토 정보 반복 | 미채택 |
| B acceptance ID만 포함 | 후보 작음, 별도 공급 없으면 I/O 조회 유발 | 단독 채택 안 함 |
| C context가 불변 records 제공 | 후보와 검토 기록 분리, 순수 함수 안에서 참조 해결 | 추천 |

후속 candidate는 `acceptance_ref: AcceptanceIdentity | None`만 갖는다. M2.3의 acceptance_status scalar는 제거하는 설계 변경을 제안한다. status를 후보와 기록 양쪽에 중복 저장하지 않는다. ref=None은 정상 미수용, ref가 있는데 context에 없으면 broken reference Data Error다.

버전 대조를 위해 candidate의 정규화 metadata에 rule_version/dataset_version/source_bindings와 applicable_months/benefit_evidence_refs를 명시해야 한다. amount/cadence/medium은 M2.3 필드를 유지한다. 미래 adapter가 같은 확인본을 전달해야 하며 Policy Engine 객체를 직접 import하지 않는다. acceptance 연결과 metadata 구조 모두 미구현이다.

M2.3의 “같은 policy/edition의 acceptance_status는 동일” 규칙은 **혜택별 record 수용**으로 세분화한다. 같은 정책의 component A는 수용, B는 미수용일 수 있다. 정책 verification/scope/eligibility와 선택한 정책 버전은 여전히 같아야 한다. 서로 다른 component의 수용 여부를 억지로 같게 만들지 않는다.

## 20. BridgeContext 연결

최소 후보: target_month, **data_use_date**, assessment_ref, **acceptances: tuple[PolicyBenefitAcceptance, ...]**. mapping 대신 tuple로 전달하고 내부 임시 lookup만 만든다. 변경 가능한 전역 registry·파일 조회는 없다.

한 요청에는 (policy_id, edition_id, benefit_id)별 선택 record가 최대 하나다. 같은 acceptance identity 반복도 오류이고 서로 다른 acceptance_version 동시 전달도 오류다. 외부가 버전을 명시적으로 선택한다. 참조하지 않는 다른 대상 record도 불필요한 혼합을 막기 위해 오류로 거부한다. 기록이 전혀 없고 후보 ref=None이면 정상 미수용이다.

ref의 policy_id/benefit_id/edition이 후보와 다르면 잘못 연결한 것이므로 Data Error다. 이와 달리 대상이 같은 올바른 ref에서 rule/dataset/source가 갱신된 것은 정상적인 stale acceptance로 제외한다. Context는 사용자 프로필·계좌·소득·PolicyEvaluation을 보관하지 않는다.

## 21. Exclusion reasons

M2.3의 POLICY_NOT_ACCEPTED를 **SIMULATION_NOT_ACCEPTED**로 대체하여 배포 승인과 혼동하지 않는다. 다음 acceptance reason은 서로 중복되지 않게 선택한다.

| 조건 | reason |
|---|---|
| ref=None, REVOKED, reviewed_at 이전의 사용일 | SIMULATION_NOT_ACCEPTED |
| 같은 대상의 rule/dataset/source version 불일치 | ACCEPTANCE_VERSION_MISMATCH |
| 수용 사용기한 경과 | ACCEPTANCE_EXPIRED |

record가 있고 같은 대상이면 버전 불일치와 만료가 동시에 있는 경우 둘 다 남긴다. 단 REVOKED면 acceptance 이유는 SIMULATION_NOT_ACCEPTED 하나로 충분하다. acceptance 미존재/철회일 때도 다른 독립 gate의 제외 이유를 숨기지 않는다. TARGET_MONTH_NOT_APPLICABLE은 지급월 미해당을 위한 별도 reason이며 수용 기한 만료와 구별한다.

정책 범위/verification/사용자 eligibility/개인 적용/cadence/medium/금액 이유는 M2.3의 기존 의미를 유지한다. 제외 결과에는 후보 identity, acceptance_ref, 선택 record 상태·결합 버전·기간의 작은 값 snapshot을 남겨 사유를 추적한다. 원문·reviewer 실명·개인 프로필을 runtime 결과에 복제하지 않는다.

## 22. Error vs exclusion

| 상황 | 처리 |
|---|---|
| 수용 없음/철회/만료 | 정상 제외 |
| 같은 대상의 정상 rule/dataset/source 갱신 | 정상 제외, 재검토 필요 |
| ref가 타 policy/benefit/edition을 가리킴 | Data Error |
| ref는 있는데 record 없음 | Data Error |
| 중복 record·여러 선택 버전·불필요 record | Data Error |
| 같은 버전으로 금액/medium/cadence/지급월/refs가 바뀜 | Data Error, immutable metadata 모순 |
| 음수/잘못된 타입/알 수 없는 상태/불가능한 날짜 구간 | Data Error |
| candidate의 None 금액 | 정상 AMOUNT_NOT_FIXED; 확정 금액으로 발급한 record를 이 값으로 덮지 않음 |

edition의 정상 교체는 **이전 ref 재사용으로 해결하지 않는다**. 외부가 새 edition용 ref를 찾고 없으면 ref=None으로 미수용 처리한다. 명시적 ref의 대상 edition 불일치는 잘못된 연결이므로 오류다. 모든 오류는 전체 batch 실패이며 정상 합계/부분 성공 결과를 반환하지 않는다. 외부 상태를 UNKNOWN으로 바꿔 오류를 숨기지 않는다.

## 23. Gate ordering

먼저 구조·타입·ID 검사 → 후보 중복/edition·정책 metadata 검사 → context record 유일성/ref 대상·존재 검사 → 버전이 같은 metadata 내용 정합성 검사를 한다. Data Error가 있으면 합산하지 않는다. 버전 불일치 시 구버전 금액과 신버전 금액을 같은 버전 모순으로 오진하지 않는다.

그 후 독립 gate를 모두 확인하며 다음 고정 reason 순서로 반환한다.

1. SIMULATION_NOT_ACCEPTED
2. ACCEPTANCE_VERSION_MISMATCH
3. ACCEPTANCE_EXPIRED
4. POLICY_NOT_FULLY_EVALUATED
5. POLICY_NOT_VERIFIED
6. ELIGIBILITY_NOT_PASS
7. NOT_CASHFLOW_ELIGIBLE
8. TARGET_MONTH_NOT_APPLICABLE
9. NON_MONTHLY_PAYMENT
10. RESTRICTED_MEDIUM
11. AMOUNT_NOT_FIXED

적용월 확인에는 candidate의 현재 정규화 목록을 사용하며 version 일치 시 accepted_terms와 같아야 한다. 전체 reason은 고정 순서의 중복 없는 tuple이다. 첫 실패에서 다른 이유 수집을 멈추지 않는다. 정상 결과의 항목 정렬·합계·입력 불변성은 M2.3을 유지한다. 새 record 상태는 기존 PolicyEvaluation PASS/FAIL/UNKNOWN에 영향을 주지 않는다.

## 24. 최소 MVP 구조

업무 입력은 **BenefitCandidate + PolicyBenefitAcceptance + BenefitBridgeContext** 세 객체로 충분하다. identity/accepted_terms는 작은 불변 값 묶음이며 별도 서비스나 workflow engine이 아니다. 결과는 M2.3의 BridgeResult를 유지한다.

권장 후속 파일 위치는 backend/benefit_bridge/models.py의 독립 모델과 errors.py다. 실제 source/정책 연결 adapter, acceptance 발급 validator, Bridge 합산 함수, 저장소/registry 서버는 단계별 별도 승인 대상이다. 이번에는 폴더·빈 코드·테스트도 생성하지 않는다.

후속 호출 흐름: 외부가 고정 정책·혜택·검토 records와 개인/월 사실을 결합 → candidate/context → Bridge → 최종 int → 호출자가 새 CashflowInput 생성 → 기존 calculate_cashflow. Cashflow 모델/계산 함수는 변경하지 않는다.

## 25. 수동 시나리오

**40개 문서상 계약 사례이며 실행 테스트가 아니다.** 기준 V는 미래 합성 정책 P-A/2026/CASH-A, FULL_POLICY/VERIFIED, rule=r0001, dataset=D1, source=S1/d0001, 월 자유 현금100,000, 적용월=(2026-09,2026-10), 사용자 PASS·개인 CONFIRMED다. A1은 같은 정의/버전에 묶인 ACCEPTED a0001, reviewed_at=2026-09-01, valid_until=2026-10-31이다. context는 target_month=2026-10, data_use_date=2026-10-21이며 V.ref=A1이다. 가상 source/검토 기록이며 실제로 생성하지 않는다.

| ID | 사례 | 기대 |
|---|---|---|
| PA01 | V+A1 | 모든 gate 통과, 100,000 반영 |
| PA02 | acceptance 없음, ref=None | 0, SIMULATION_NOT_ACCEPTED |
| PA03 | 검토 중/미통과여서 record 미발급 | PA02와 동일, 가짜 PENDING record 만들지 않음 |
| PA04 | 외부가 선택한 record=REVOKED | 0, SIMULATION_NOT_ACCEPTED |
| PA05 | data_use_date=2026-11-01 | 0, ACCEPTANCE_EXPIRED |
| PA06 | current scope=CONDITION_SLICE | 수용 발급 불가, 사용 시 POLICY_NOT_FULLY_EVALUATED |
| PA07 | current scope=FULL_POLICY | scope gate 통과; 나머지 gate는 별도 |
| PA08 | Envelope DRAFT | 수용 발급 불가, POLICY_NOT_VERIFIED |
| PA09 | Envelope VERIFIED | verification gate만 통과 |
| PA10 | Envelope STALE | 수용 발급 불가, POLICY_NOT_VERIFIED |
| PA11 | rule_version=r0001 일치 | binding 통과 |
| PA12 | candidate rule=r0002, record r0001 | ACCEPTANCE_VERSION_MISMATCH, 자동 승계 없음 |
| PA13 | edition=2026 일치 | identity gate 통과 |
| PA14 | candidate edition2027에 edition2026 ref 명시 | 대상 edition 불일치 Data Error |
| PA15 | candidate dataset=D2, record D1 | ACCEPTANCE_VERSION_MISMATCH |
| PA16 | 사용자 FULL_POLICY PASS | eligibility gate 통과, 행정 승인 아님 |
| PA17 | 사용자 FAIL | ELIGIBILITY_NOT_PASS |
| PA18 | 사용자 UNKNOWN | ELIGIBILITY_NOT_PASS |
| PA19 | target_month=2026-09 | 적용월 gate 통과 |
| PA20 | target_month=2026-11, data_use_date는 기준값 | TARGET_MONTH_NOT_APPLICABLE, 수용 만료와 별개 |
| PA21 | MONTHLY + UNRESTRICTED_CASH | 유형 gate 통과 |
| PA22 | candidate/accepted_terms 모두 QUARTERLY | 수용 검토 가능, NON_MONTHLY_PAYMENT로 반영0 |
| PA23 | candidate/accepted_terms 모두 LOCAL_CURRENCY | 수용 검토 가능, RESTRICTED_MEDIUM으로 반영0 |
| PA24 | candidate amount=None | AMOUNT_NOT_FIXED; 미확정 정의에는 ACCEPTED 발급 금지 |
| PA25 | candidate/accepted_terms 모두 amount=0 | applied0원 기록, 합계0 |
| PA26 | 현재 안산002 DRAFT/slice, ref=None | 반영0, 미수용+범위+검증 이유; slice PASS여도 동일 |
| PA27 | 미래 가상 안산 full/verified/pass/accepted지만 quarterly/local | 여전히0, 두 유형 제외 이유 |
| PA28 | ref의 policy_id가 후보와 다름 | Data Error |
| PA29 | ref의 benefit_id가 후보와 다름 | Data Error |
| PA30 | 같은 버전·대상인데 금액100,000 vs200,000 | 모순 metadata Data Error |
| PA31 | 동일 acceptance 중복 또는 같은 benefit의 a0001/a0002 동시 제공 | Data Error, 최신 자동 선택 없음 |
| PA32 | 동일 입력 반복·정상 후보 순서 변경 | 같은 정렬 결과·합계·reasons·to_dict |
| PA33 | rule 업데이트 뒤 과거 acceptance 사용 | 반영0, 새 검토 필요 |
| PA34 | source d0001→d0002 | version mismatch, 금액 동일해도 재검토 |
| PA35 | 처리 전후 candidate/context/record snapshot | 값 동일, 입력 변경 없음 |
| PA36 | ref 존재, context에 record 없음 | broken reference Data Error |
| PA37 | 정상 새 edition2027, 해당 ref=None | 정상 미수용; 과거 ref를 새 edition에 연결하지 않음 |
| PA38 | URL metadata 갱신으로 source version 변경 | 자동 승계 없음, 새 검토 버전 필요 |
| PA39 | 같은 정책 CASH-A는 accepted, CASH-B는 ref=None | A만 반영, component별 수용 분리 |
| PA40 | scope slice + DRAFT + ref=None + 분기 지역화폐 | 미수용/범위/검증/주기/수단의 모든 이유, 고정 순서 |

각 gate 단독 변화 사례는 필터의 의미를 설명한다. 실제 발급 시 DRAFT/slice/미확정 금액으로 ACCEPTED를 만들 수 있다는 뜻이 아니다. 검증에는 만료 경계일 포함·reviewed_at 이전 사용일·source freshness·금액 타입·None/0·철회 선택·복수 이유를 추가할 수 있으며, 이번에는 테스트 코드를 추가하지 않는다.

## 26. 미해결 문제

**차단 항목은 현재 coverage 모델의 전체 범위 표현**이다. FULL_POLICY의 평가 단위·미구현 조건 없는 상태의 근거·회차/효력 의미를 결정하지 않은 채 수용 기록을 발급할 수 없다. 이번 acceptance는 이 경계를 독립적으로 정의했지만 기존 정책 모델을 우회하지 않는다.

버전 선택은 정확한 rule/dataset/source 결합, 월 적용은 명시적 월 목록, 수용 유효성은 명시적 data_use_date/기한으로 정리했다. 이 세 항목을 이유로 workflow나 schedule engine을 추가하지 않는다. 실제 외부 검토 발급·개인 확인 adapter·철회 선택 검증·source freshness enforcement는 여전히 미구현이며 합성 값 모델이 그 신뢰성을 인증하지 않는다.

**Assumption A4:** 현재는 고정 금액·열거 가능한 적용월을 검토할 수 있는 소수 정책만 대상으로 한다. 복잡한 개인별 금액이나 일정은 추가 조건을 추측하지 않고 미수용으로 둔다. 정책 범위를 줄여서 full이라고 부르거나 미구현 거주기간을 면제하지 않는다.

M1.18 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**를 유지한다. 공식 답변 전 Fact/Rule/Evaluator를 구현하지 않는다. 실제 안산 정책의 FULL_POLICY 완성을 이번 작업으로 승인하지 않는다.

## 27. 최종 판단

**NEEDS_POLICY_COVERAGE_MODEL_REVISION**

판단 근거: 현재 EvaluationScope는 CONDITION_SLICE뿐이며 PolicyCoverage는 excluded_conditions 비어 있음을 허용하지 않는다. 수용 가능한 전체 범위와 현재 모델 간의 의미 차이를 먼저 해결해야 한다. 코드·데이터·정책 결과·실제 혜택 금액 연결은 이번에 수행하지 않았다.

다음 가장 작은 작업 한 개: **FULL_POLICY와 CONDITION_SLICE의 coverage 불변조건을 문서로 설계**한다. 필수조건 완결성 근거와 회차 범위를 정의하고 현행 모델의 최소 변경 지점만 제시한다. 실제 조건 구현·Enum 추가·acceptance 모델/Bridge 구현으로 자동 진행하지 않는다.

### 검증 기록

기존 전체 pytest는 **2810 passed in 8.24s**다. 신규 실행 테스트는 추가하지 않았다. 문서의 27개 필수 절과 PA01~PA40의 순서·유일성·누락 여부 및 한국어 표기를 확인했다. 이 결과는 아직 없는 acceptance/Bridge 구현의 테스트 통과를 의미하지 않는다.

Git 저장소가 없어 git status는 조회할 수 없었다. 작업 전 backend/tests/data/docs의 기존 **96개 파일 SHA256이 모두 동일**하고 수정·삭제는 없다. 추가는 이 문서 한 개다. Policy Engine·Cashflow·actual releases·tests·기존 문서·ResidenceHistory를 변경하지 않았다.
