# Acceptance 평가 결과·명시 선택·철회 효과 계약 — M2.49

현재 결과 값 모델의 구현 상태는 **29절 M2.50**을 따른다.9필드 Result/Status/Reason·로컬 검증·파생 status·serializer만 구현했고 실제 evaluator/adapter는 없다. 아래1~28절은 승인된 M2.49 설계와 당시 검증 이력이다.

작성일: **2026-10-22 / Asia/Seoul**. **문서 전용**. 최종 판단: **READY_TO_IMPLEMENT_ACCEPTANCE_EVALUATION_RESULT_MODEL**.

이번 산출물은 이 문서 한 개다. 아래 Enum/result/평가·철회 helper/Bridge 연결은 **설계 계약이며 미구현**이다. 기존 코드·tests·fixture·golden·명세·실제 releases를 바꾸지 않는다. 실제 안산 Acceptance/평가 결과를 만들지 않는다.

## 1. 목적과 확인 근거

**명시적으로 선택한 Acceptance revision을, 공급된 현재 확인본·알려진 관련 철회 이력·명시 사용일에서 시뮬레이션 사용 근거로 삼을 수 있는가**를 작은 결과로 표현한다. stored ACCEPTED와 현재 사용요건 충족을 구분한다.

| 확인 자료 | 적용한 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md 3~30·35절 | one target·명시 ref·엄격한 조회/부재·직접 철회 최대1개·조회와 현재 효과 분리·미결정 선택 계약 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md 9·12·16·21~28·37절 |21필드/2상태·철회 검토일/horizon·예약 철회 없음·동일 release·독립 guards·typed reasons 방향 |
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md 5~19절 | FULL/verification·기준 비교·no-record·여러 사유·Bridge와의 책임 |
| BENEFIT_SNAPSHOT_SPEC.md 7·14~18·36~37절 | FIXED/분류/유한 월 completeness·근거 사용·정의 지문과 provenance 분리 |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md 13~23절 | 명시 사용일·포함 기한·외부 선택/완전성·기존 Bridge 이유 |
| CASHFLOW_BENEFIT_BRIDGE_SPEC.md 10~22절 | 사용자/월·유형·중복/병급·무환산·trusted 내부 정규화 |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md / ELIGIBILITY_COVERAGE_CORE_FREEZE.md |8필드 Result/9key·정상 all-None baseline·공식 생성 경로·동결 지문/오류/한계 |
| POLICY_DATA_ENVELOPE_SPEC.md 10~16·수용 gate | source/locator 수명·검토 상태·명시 freshness·불변 release·외부 실제 review/bytes |
| DATA_MODEL.md 34~35절 / ARCHITECTURE.md 50~51절 | record/Context/resolver 완료, current result/evaluator/Bridge 미구현 |
| 현재 Acceptance/Context/resolver·Scope·PolicyDataError | exact 값·immutable 관계·원본 identity·기존 오류 계층 |
| 현재 EligibilityCoverageResult/Status·findings | present 지문과 optional baseline 구별, factory/sentinel/파생 상태 |
| 현재 BenefitSnapshot/fingerprint_benefit_snapshot |16필드와 정의15key 지문·dataset/Registry 제외 |
| 현재 Envelope/Manifest/SourceRegistry/validators | 아래20절의 구현된 검사와 아직 없는 사용 gate 구별 |

우선순위는 frozen Coverage → 구현된 record/Context/resolver 계약 → 이번 current 평가 구체화 → 과거 미구현 후보다. 후보 API/사유 목록/Bridge 결합을 보완한 사항은26절에 명시한다. 기존 문서를 소급 수정하지 않는다.

사전 전체 baseline: **6725 passed in 13.98s**. 신규 실행 테스트는0개다.

## 2. 평가 결과의 이름·상태·비의미

기존 개념명을 유지해 **BenefitAcceptanceEvaluation**으로 확정한다. **BenefitAcceptanceEvaluationStatus(str, Enum)**는 USABLE/UNUSABLE 두 member, **BenefitAcceptanceReason(str, Enum)**는13절의12개 member로 정한다. 이번에 구현/export하지 않는다.

status는 reasons가 비면 USABLE, 비어 있지 않으면 UNUSABLE로 **파생**한다. status·usable bool·accepted bool을 저장하지 않는다. 별도 usable property도 두지 않고 status 한 표현을 사용한다. 과거 문서의 evaluation.usable은 개념 설명이며 후속 API에서는 이 파생 status로 표현한다.

USABLE은 이 내부 평가 호출의 Acceptance 계층 요건 충족이다. 실제 지급/행정 승인·사용자 PASS·개인/대상 월·병급·MONTHLY/자유 현금·Bridge 합산·배포 승인을 뜻하지 않는다. ERROR/VERIFIED/PASS/FAIL/UNKNOWN을 정상 평가 상태로 만들지 않는다. 잘못된 입력/참조/모순은 PolicyDataError로 실패한다.

## 3. 현재 사용 평가와 과거 재현

이 계약은 **공급된 현재 확인본·Context의 지식과 명시 data_use_date에 대한 현재 사용 평가**다. 과거 당시 알고 있던 자료/철회 상태를 복원하는 as-of replay가 아니다. data_use_date는 자료 사용 기준일이며 사용자 신청일·지급월·시스템 오늘의 자동 별칭이 아니다.

명시 사용일은 ACCEPTED 기한/source freshness에 사용한다. 현재 Context에 이미 포함된 철회를 과거 날짜 입력으로 회피하지 못한다. 없는 실제 철회 기록을 알아낼 수는 없다. Context 구조 일관성, supplied history 완전성, 실제 결정 진실성은 다른 축이다.

## 4. 결과와 입력의 결합 — 요청 내부 결과 선택

다음 두 대안을 비교하고 **B를 선택**한다.

| 대안 | 비용/보장 | 결정 |
|---|---|---|
| A 결과에 재사용 가능한 snapshot identity 보존 | Coverage/Benefit/provenance뿐 아니라 Envelope/Manifest/검토·철회 이력까지 결합해야 함. Benefit fp 하나나 target/date만으로는 새 B가 생긴 Context를 구별하지 못함 | 이번 최소 모델에 미채택 |
| B 같은 호출의 원본 입력과 함께만 사용하는 내부 결과 | 기존 객체를 복제하거나 새 Context 지문/schema를 만들지 않음. 결과 단독 재사용/캐시/외부 재입력을 금지해야 함 | **채택** |

후속 서비스의 단일 trusted 정규화 adapter는 current CoverageResult/Envelope/BenefitSnapshot/AcceptanceContext/ref/Manifest/Registry·data_use_date를 불변으로 고정하고, **그 호출 안에서 evaluator를 호출한 뒤 바로 같은 Benefit 원본으로 Bridge candidate를 생성**해야 한다. 이 adapter의 공개 입력에 미리 계산된 BenefitAcceptanceEvaluation 또는 serialized 결과를 받는 인자를 제공하지 않는다. Bridge의 외부 입력도 raw 평가 결과를 승인 토큰처럼 받지 않는다. 기존 trusted candidate 경계를 유지한다.

다른 Benefit/version/provenance/Scope/date/Envelope/Manifest/Context로 바뀌면 새 adapter 호출에서 다시 평가한다. 특히 같은 A·Benefit fp·날짜여도 Context에 B가 추가되면 재평가해야 한다. 이전 result를 새 입력에 끼워 넣는 경로 자체를 지원하지 않는다. 동일 호출 안의 후보는 전달된 원래 Benefit 객체에서 조립하고 target/date와 ref를 대응시킨다. 원본 사이의 구조 검사는18절 책임이다.

이9필드 값만으로 모든 snapshot/이력 동일성을 검사할 수 있다고 주장하지 않는다. 결과 equality/status/target 일치나 JSON 수신만으로 재사용을 허용하면 계약 위반이다. UI serializer는 표시/설명용이고 운영 수용 입력이 아니다. 캐시·요청 간 결과 재사용·단독 서명 토큰이 필요해지면 별도 binding spec revision부터 해야 한다.

이 경계는 아직 없는 adapter/Bridge의 **필수 구현 조건**이다. 모델만 구현한 단계에서는 production 연결을 열지 않는다. 과거 재현/감사에는 외부에 보존한 정확한 입력·자료/엔진/검토/Context snapshot을 함께 사용해야 하며 이 작은 result 단독으로 재현을 보장하지 않는다.

## 5. 최종 stored fields — 정확히9개

BenefitAcceptanceEvaluation은 frozen=True, slots=True, kw_only=True다. 다음 순서의9개를 default 없이 모두 명시한다. nullable 값도 필수다. 원본 전체·current fingerprint·index·금액·사용자 정보를 복제 저장하지 않는다.

| 순서 | 필드 | 정확한 타입·의미 |
|---|---|---|
| 1 | policy_id | exact canonical str, 현재 target |
| 2 | scope | exact 기존 ApplicabilityScope, 현재 target·원본 보존 |
| 3 | benefit_id | exact canonical str, 현재 target |
| 4 | data_use_date | exact datetime.date, 명시 사용일 |
| 5 | selected_acceptance_ref | exact 비공백 str 또는 None, 외부가 지정한 원문 ref |
| 6 | selected_acceptance_version | exact a0001 이상 기존 문법 str 또는 None |
| 7 | selected_acceptance_status | exact 기존 BenefitAcceptanceStatus 또는 None |
| 8 | revocation_acceptance_ref | exact 비공백 str 또는 None, 철회 판단 근거 B의 ref |
| 9 | reasons | exact tuple[BenefitAcceptanceReason, ...], canonical 순서·유일·빈 tuple 허용 |

selected3개는 모두 None 또는 모두 present다. resolution 성공이면 ref는 지정한 원문, version/status는 찾은 원본의 값이다. ref를 B/C로 교체하지 않는다.9개 value equality/hash를 사용한다. 결과 값이 우연히 같아도 다른 요청 입력에 재사용할 수 있다는 뜻은 아니다.

현재 snapshot 전체 identity를 저장하지 않는 대신4절의 제한을 필수로 선택했다. 향후 이 제한을 없애면서9필드 그대로 유지하는 변경은 허용하지 않는다.

## 6. 명시 선택·no-selection 표

아래 표는 **기본 입력/현재 자료 정합성 검사에서 별도 Data Error가 없다는 전제**다. 정상 선택 상태는 evaluator/호출 경계가 처리하며 기존 strict resolver를 바꾸지 않는다.

| 경우 | Context | acceptance_ref | 의미와 결과 |
|---|---|---|---|
| A | None | None | 자료 자체 미제공. NO_ACCEPTANCE_CONTEXT |
| B | empty | None | supplied 집합에 기록 없음. NO_ACCEPTANCE_RECORDS |
| C | nonempty | None | 기록은 있으나 선택하지 않음. ACCEPTANCE_NOT_SELECTED |
| D | None | 비공백 exact str | **ACCEPTANCE_CONTEXT_REQUIRED** Data Error. 명시 ref를 조용한 부재로 낮추지 않음 |
| E | empty | 비공백 exact str | 기존 resolver의 ACCEPTANCE_REF_NOT_FOUND |
| F | nonempty | 지정한 비공백 ref가 집합에 없음 | 기존 resolver의 ACCEPTANCE_REF_NOT_FOUND |
| G | nonempty | ACCEPTED를 가리킴 | 원본 선택 후 관련 B·기한·current gates/guards 평가 |
| H | nonempty | REVOKED를 가리킴 | 원본 선택, ACCEPTANCE_REVOKED. 다른 독립 검사도 수행 |
| I | 현재 target과 다른 Context | None | **ACCEPTANCE_CONTEXT_TARGET_MISMATCH**, no-selection으로 숨기지 않음 |

F는 “ref 인자가 None”이 아니라 **존재한다고 지정한 ref가 collection에 없다**는 뜻이다. A/B/C는 selected3개와 revocation ref가 모두 None이고 선택 사유는 각각 정확히 하나다. source/current gate 실패 사유는 함께 남길 수 있다.

None 이외의 ref는 exact 비공백 str이어야 한다. blank/str subclass/숫자·dict는 INVALID_ACCEPTANCE_EVALUATION_INPUT이다. Context도 exact 타입 또는 None만 허용한다. Context 잘못된 타입/target·현재 자료 모순은 A/B/C 처리보다 먼저 확인한다. max(version)/최근 날짜/마지막 원소를 골라 C를 G로 바꾸지 않는다.

## 7. Context target과 scope 경계

현재 target은 BenefitSnapshot의 (policy_id, scope, benefit_id)다. CoverageResult는 policy_id/scope, Envelope는 policy_id/edition_id/rule_version이 대응해야 한다. 제공된 Context의 세 값은 현재 target과 정확히 같아야 한다. 값이 같은 별개 Scope는 허용하며 Q3/Q4/annual/다른 연도는 구별한다.

이 current-use 경로는 Context+ref를 정식 입력 경계로 선택한다. 과거 raw record를 직접 받는 overload는 두지 않는다. 다른 scope의 역사 Context를 현재 scope에 연결하면 Data Error다. M2.41의 “정직한 과거 scope record와 현재 scope 비교는 정상 변경” 예시는 raw resolved-record 후보의 설명이었고, 이 API가 그 비교 기능을 제공하지 않는다. 이 인터페이스 제한을26절에 명시적으로 기록하며 record의 역사 의미나 frozen Scope를 바꾸지 않는다.

## 8. 철회된 A와 독립 재승인 C

선택 ACCEPTED A에 대해서만 **같은 supplied Context에서 status=REVOKED이고 revokes_acceptance_ref==A.acceptance_ref인 B**를 확인한다. 기존 Context가 대상 존재·ACCEPTED 상태·같은11 binding·후행 revision/검토일·직접 철회 최대1개를 보장한다. evaluator가 전체 Context를 재생성/재검증하지 않는다.

| 명시 선택 | 관련 이력 | 효과와 result trace |
|---|---|---|
| A | A 단독 | 철회 사유 없음. 나머지 gate 통과 시 USABLE 후보 |
| A | B→A 있음 | ACCEPTANCE_REVOKED, selected_ref=A, revocation_ref=B |
| A | B→A와 새 C 있음 | 계속 A를 평가, B 근거로 사용 불가. C로 대체하지 않음 |
| B | B→A | selected_status=REVOKED, selected_ref=B, revocation_ref=B, ACCEPTANCE_REVOKED |
| C | B→A, C는 새 ACCEPTED | B를 C의 철회로 확대하지 않음. C의 독립 gate 평가 |

관련 B의 exact ref만 조회/보존한다. 다른 ACCEPTED를 찾거나 대안 승인을 자동 선택하지 않는다. Context 원소 순열로 결과 의미·selected/ref/reasons가 달라지지 않는다. stored A/B 상태는 변하지 않는다.

## 9. 철회 시간 의미 — 알려진 철회를 보수적으로 적용

기존 record의 B.reviewed_at은 **철회 결정 검토일**이다. effective_at/효력 시작일로 확정된 필드가 아니고 M2.45 16절은 예약 철회/미래 자동 전환을 지원하지 않는다.

| 선택지 | 의미·한계 | 결정 |
|---|---|---|
| 날짜 기준: data_use_date>=B.reviewed_at일 때만 철회 | 검토일을 효력 시작일로 재해석해야 함. 실제 효력일/당시 지식 이력이 없음 | 미채택. 지원하려면 record 의미/필드와 replay change-control 필요 |
| supplied 현재 Context의 알려진 B를 적용 | 검토일을 새 효력일로 만들지 않고 과거 날짜를 입력해 알려진 철회를 회피하지 않음. 역사 시점 재현은 보장하지 않음 | **채택** |

선택 A에 관련 B가 있으면 **data_use_date가 B.reviewed_at 이전/당일/이후 모두** ACCEPTANCE_REVOKED다. B 자체를 선택한 경우도 날짜와 무관하게 같다. 이것은 “실제 효력이 과거에도 있었다”는 행정적 주장이나 소급효 판단이 아니라 **현재 공급 지식으로 그 기록을 사용하지 않는 서비스 규칙**이다.

B.valid_until 경과로 철회를 종료하거나 A를 부활시키지 않는다. A/B 검토일이 같은 날도 적용한다. A가 이미 기한을 지난 뒤 B가 기록돼도 A의 EXPIRED와 REVOKED를 함께 남길 수 있다. B에 대한 NOT_YET_VALID/EXPIRED를 계산하지 않는다. 철회 기록의 날짜 구조는 기존 constructor가 이미 검증했다.

## 10. ACCEPTED의 사용기한

정확한 date만 사용하고 datetime/date subclass/ISO 문자열·bool·None을 거부한다. 현재시각 조회/기본 오늘·자동 parsing은 없다.

| 선택 ACCEPTED A와 data_use_date | 사유 |
|---|---|
| A.reviewed_at 직전 | ACCEPTANCE_NOT_YET_VALID |
| A.reviewed_at 당일 | 하한 충족 |
| A.valid_until 당일 | 상한 충족 |
| A.valid_until 다음 날 | ACCEPTANCE_EXPIRED |
| reviewed_at==valid_until인 그날 | 기한 충족 |

기한은 양끝 포함이다. NOT_YET_VALID와 EXPIRED는 유효한 A 하나에서 동시에 생기지 않는다. A가 B로 철회됐어도 A의 기한 검사는 실행 가능하므로 독립 날짜 사유를 함께 남긴다. selected REVOKED B에는 A용 사용기한 사유를 붙이지 않는다. target_month/신청창/실제 지급일은 이 날짜에서 추론하지 않는다.

## 11. 현재 입력끼리의 일관성

현재 자료끼리의 결합과 과거 승인 비교를 구별한다. 다음은 정상 사용 불가가 아니라 Data Error다.

| 축 | 현재 입력 의무 |
|---|---|
| target | Coverage/Benefit policy_id·scope 일치, Envelope policy_id/edition 대응, Context 제공 시 benefit 포함 target 일치 |
| current rule/tree | Coverage.rule_version==Envelope.rule_version, 기존 Tree 지문으로 같은 실제 트리 대응 확인 |
| MVP release | Benefit.dataset==Envelope.dataset==Manifest.dataset, Benefit Registry 지문==실제 고정 Registry 지문==Manifest Registry 지문 |
| Coverage present baseline | dataset/Registry가 위 현재 release와 같음. all-None이면 이 두 값 비교를 생략하되 추론/채우지 않음 |
| 근거 | 현재 refs/locator 존재·version·policy 적용·중복/metadata 정합성, source binding/Manifest 대응 |
| artifact | 선택된 불변 release/실제 엔진·원문·검토 bytes 대응은 외부 준비 의무. supplied hash가 실제 bytes라는 인증은 아님 |

Coverage implementation_fingerprint와 Manifest.engine_artifact_sha256은 모두 hex64라는 이유로 같다고 강제하지 않는다. 각 값이 어떤 input/evaluator/engine artifact를 의미하는지 외부 준비가 명시해야 하며, 정확한 대응 검증 연결은20절 후속 evaluator 의존사항이다. 별도 구현 version을 발명하지 않는다.

Coverage는 공식 public evaluator가 만든 exact Result를 받는다. Acceptance 계층이 private Coverage findings/factory/token으로 FULL을 만들거나 Envelope의 legacy CONDITION_SLICE를 FULL로 고치지 않는다. 현재 실제 FULL release 연결은 미완료다.

## 12. 과거 선택 record와 현재 snapshot 비교

selected가 없으면 아래 과거-현재 비교를 실행하지 않는다. selected가 REVOKED여도 저장 binding은 존재하므로 독립 모순 검사를 생략하지 않는다. Context target 검사를 통과했으므로 이번 API에서 policy/scope/benefit domain은 같다.

| 비교 축 | 실행 전제 | 정상 변경 | Data Error/비교 불가 |
|---|---|---|---|
| Inventory i version/fp | selected 존재, 현재 version/findings fp 존재 | i version 다름→COVERAGE_SNAPSHOT_CHANGED | 같은 i의 다른 fp→INVENTORY_FINGERPRINT_CONFLICT |
| Rule version/Tree fp | selected 존재, 현재 version/Tree fp 존재 | rule version 다름→COVERAGE_SNAPSHOT_CHANGED | 같은 rule의 다른 Tree→POLICY_TREE_FINGERPRINT_CONFLICT |
| Coverage dataset/Registry | selected 존재, 현재 baseline present | 새 dataset→COVERAGE_SNAPSHOT_CHANGED | 같은 dataset의 다른 Registry→SOURCE_REGISTRY_FINGERPRINT_CONFLICT. all-None이면 이 축 비교 불가 |
| Coverage implementation fp | selected 존재, 현재 baseline present | 다름→COVERAGE_SNAPSHOT_CHANGED | 별도 version이 없어 차이 자체는 정상 변경. all-None이면 비교 불가 |
| Benefit b version/정의 fp | selected 존재, exact 현재 Benefit의 기존 지문 계산 가능 | 새 b→BENEFIT_SNAPSHOT_CHANGED | 같은 b의 다른 fp→BENEFIT_FINGERPRINT_CONFLICT |
| Benefit dataset/Registry | selected 존재, 현재 Benefit provenance 항상 존재 | 새 dataset→BENEFIT_PROVENANCE_CHANGED | 같은 dataset의 다른 Registry→SOURCE_REGISTRY_FINGERPRINT_CONFLICT |

비교 불가는 mismatch가 아니다. 정상 SLICE/all-None baseline에는 COVERAGE_NOT_FULL이 생기지만 None 대 과거 지문 차이만으로 SNAPSHOT_CHANGED나 conflict를 만들지 않는다. Inventory/Tree 지문은 findings에 존재하므로 같은 SLICE에서도 해당 guard는 실행한다. Benefit provenance도 항상 존재하므로 그 독립 guard는 유지한다.

version 차이는 **그 쌍의** 내용 동일성 의무만 면제한다. 새 rule이어도 같은 i version의 다른 fp는 오류다. 새 dataset이어도 같은 b version의 다른 정의는 오류다. 철회·만료·SLICE·no-selection이 현재 입력 자체의 모순을 숨기지 않는다. selected가 없는 경우에는 비교 상대를 꾸며 만들지 않는다.

정의 fp가 같아도 release가 정상 변경되면 재검토가 필요하다. 현재 양 subsystem이 D2로 함께 이동한 경우 Coverage/Benefit provenance 사유를 각각 남길 수 있다. 한쪽만 D2인 현재 혼합은 먼저11절 Data Error다.

## 13. 정상 사용 불가 사유 — 정확히12개·고정 순서

다음 선언 순서를 canonical 순서로 확정한다. UI 문장·raw payload·ERROR는 member가 아니다. 여러 독립 사유를 모두 남기고 같은 사유는 한 번만 저장한다.

| 순서 | BenefitAcceptanceReason | 정확한 발생 조건 |
|---|---|---|
| 1 | NO_ACCEPTANCE_CONTEXT | Context=None, ref=None |
| 2 | NO_ACCEPTANCE_RECORDS | exact empty Context, ref=None |
| 3 | ACCEPTANCE_NOT_SELECTED | exact nonempty Context, ref=None |
| 4 | ACCEPTANCE_REVOKED | selected REVOKED 또는 selected ACCEPTED에 알려진 직접 B 존재 |
| 5 | ACCEPTANCE_NOT_YET_VALID | selected ACCEPTED, 사용일<해당 reviewed_at |
| 6 | ACCEPTANCE_EXPIRED | selected ACCEPTED, 사용일>해당 valid_until |
| 7 | COVERAGE_NOT_FULL | 현재 정상 Coverage status가 CONDITION_SLICE |
| 8 | POLICY_NOT_VERIFIED | 현재 Envelope DRAFT/STALE 또는 구조는 유효하나 정책 근거의 검토 상태/freshness 사용요건 미충족 |
| 9 | BENEFIT_METADATA_NOT_REVIEWED | 현재 Benefit의 초기 completeness 또는 유효한 혜택 근거의 검토 상태/freshness 사용요건 미충족 |
| 10 | COVERAGE_SNAPSHOT_CHANGED |12절에서 비교 가능한 Coverage 축의 정상 변경 하나 이상 |
| 11 | BENEFIT_SNAPSHOT_CHANGED | selected와 current의 정상 새 b version |
| 12 | BENEFIT_PROVENANCE_CHANGED | selected와 current Benefit의 정상 새 dataset. 정의 fp 동일해도 포함 |

1~3은 mutually exclusive이며 selected가 없으면 그중 하나만 반드시 존재한다. selected가 있으면1~3은 없다.4~6 및10~12는 selected가 있어야 한다.5/6은 동시에 금지하고 selected REVOKED에는 붙이지 않는다.7~9는 selection 유무와 독립적으로 확인한다. 모든 정상 사유는 구조/참조/지문 guards를 통과한 뒤 반환한다.

9의 과거 명칭을 유지하지만 이 Enum 자체가 사람이 실제 검토했는지를 검사한다는 뜻은 아니다. completeness는 **FIXED, cadence/medium/restriction이 모두 UNKNOWN 아님, applicable_months가 알려진 유한 tuple**이라는 M2.42 기준이다. 분기/지역화폐를 Acceptance에서 월 현금으로 필터링하지 않는다. 실제 claim 검토·artifact 보존은 외부 의무다. 존재하지 않는 ref/잘못된 version/중복 evidence는9가 아닌 Data Error다.

기존 NO_ACCEPTANCE 후보는1~3으로 세분화하여 C를 “기록 없음”으로 설명하지 않는다. 기존 BENEFIT_SNAPSHOT_CHANGED 후보 중 release 변경은12로 분리한다. Bridge 사유로 매핑하는 단계는 후속이며 기존 순서/중복 제거 계약을 별도로 지켜야 한다. 이번에 새 Bridge exclusion Enum을 만들지 않는다.

## 14. 철회 근거와 optional 관계

| selected 상태 | selected3개 | revocation_acceptance_ref | ACCEPTANCE_REVOKED |
|---|---|---|---|
| 선택 없음 | 모두 None | None | 없음 |
| ACCEPTED, 직접 B 없음 | 모두 present | None | 없음 |
| ACCEPTED, 직접 B 있음 | A의 ref/version/status | B.ref, 반드시 A.ref와 다름 | 있음 |
| REVOKED B 선택 | B의 ref/version/status | B.ref와 정확히 같음 | 있음 |

revocation ref가 present인 것과 reason4 존재는 동치다. B를 A 대신 selected ref에 쓰지 않는다. B.version/검토일/원본 artifact는 외부 고정 Context에서 해당 ref로 추적하며 결과에 다시 복제하지 않는다. B 자체 선택과 A+B의 경우는 selected_status와 두 ref의 관계로 구별한다.

## 15. 결과 모델의 로컬 불변조건과 검증 순서

후속 모델은 다음 순서로 검사한다. field/type 검사는5절9필드 순서다. exact date·Scope/Enum/tuple·canonical ID·기존 a 문법·비공백 opaque ref를 적용하고 자동 변환/strip/정렬/default는 없다.

1. 정상 내부 생성 token 확인. token 없는 일반 생성/replace는 TypeError.
2.9필드 exact 타입/문법. reasons의 모든 원소도 exact BenefitAcceptanceReason.
3. reasons가 canonical 순서이며 중복이 없는지 검사. 자동 보정하지 않음.
4. selected3개 all-None/all-present. 부분 None 거부.
5. selected 없음이면 선택 사유1~3 중 정확히 하나, revocation=None, selected 전용4~6/10~12 없음.
6. selected 있음이면1~3 없음.
7. revocation ref와 reason4의 동치. selected REVOKED이면 ref=self, selected ACCEPTED이면 present ref는 self와 다름.
8.5/6의 동시 존재 금지, 두 사유는 selected ACCEPTED에서만 허용.
9. 나머지 조합으로 파생 status를 얻음. 별도 상태 입력/저장/보정 없음.

selected ACCEPTED이고 reasons=()면 구조적으로 USABLE을 표현한다. 그러나9필드만으로 실제 Coverage/source 기한/모든 gate의 진실성을 재검사할 수는 없다. 그 대응과 실제 날짜/철회·snapshot 관계는 evaluator 책임이다. 모델은 Context/기한을 조회하거나 이유를 새로 계산하지 않는다.

로컬 모순은 기존 PolicyDataError의 **INVALID_ACCEPTANCE_EVALUATION_RESULT: field: reason**이다. 누락/extra/positional 인자는 Python TypeError다. 원문 ref/소득/지문/payload를 오류 메시지에 넣지 않는다. 새 exception hierarchy나 DATA_ERROR reason은 없다.

## 16. 생성 책임·불변성·serializer

**factory-only 생성**을 채택한다. Coverage Result의 내부 token+InitVar 패턴을 참고하되 Coverage 코드는 수정하지 않는다. 새 result 모듈의 `_creation_token`은 keyword-only InitVar(default=None)이며9 stored fields나 serializer에 포함하지 않는다. private `_create_benefit_acceptance_evaluation`이9개 명시 값과 로컬 검사 경로를 연결한다. exact 위치/이름은 이 계약대로 후속 작은 구현에서 사용할 수 있고 public export하지 않는다.

정상 production 경로는 future evaluator가 입력/gates를 계산한 뒤 private factory1회다. factory/model 자체는9개 구조만 확인하며 gate를 재실행하지 않는다. 모델 구현 단계의 합성 factory tests는 실제 source/철회/검토를 인증하지 않는다. private 접근·강제 객체 조작의 위조 방지·권한 인증을 보장하지 않는다. 일반 constructor를 허용한 historical record/Context의 정책은 그대로다.

9개 필드 assignment/deletion을 거부하고 Scope/문자열/date/Enum/tuple 원본을 보존한다. status는 read-only 파생 property다. to_dict는 **저장9key와 마지막 status의 정확한10key**를 같은 순서로 반환한다. Scope는 새 nested dict, 날짜는 ISO, Enum은 canonical value, reasons는 새 문자열 list, optional None key도 생략하지 않는다. token/현재 raw 객체·raw 문서·사용자 값·금액을 넣지 않는다. nested 반환값 변경은 원본에 영향을 주지 않는다.

## 17. Data Error와 정상 UNUSABLE

| 정상 UNUSABLE | Data Error |
|---|---|
| Context 미제공/기록 없음/의도적 미선택 | 잘못된 타입/date/현재 target 또는 제공 Context target 모순 |
| B 선택/A에 알려진 B 적용 | 명시 ref가 있는데 Context 없음 또는 ref를 못 찾음 |
| A 기한 전/후 | malformed refs·잘못된 source binding/version·깨진 locator·중복 evidence |
| 정상 SLICE·정책/혜택 검토 상태/freshness 미충족 | 현재 자료끼리 다른 target/rule/tree/release·잘못된 Manifest 대응 |
| 유효 부분/비고정 Benefit | 같은 domain/version의 다른 지문 |
| 정상 version/provenance/artifact 변경 | Context가 이미 차단하는 중복/깨진 edge·결과 optional/reason 조합 모순 |

SourceRegistry.resolve/validate_evidence_refs가 ACTIVE가 아닌 source/locator를 거부하는 기존 SOURCE_NOT_REFERENCEABLE/EVIDENCE_NOT_REFERENCEABLE도 PolicyDataError로 전파한다. 이 오류를 POLICY_NOT_VERIFIED/metadata reason으로 catch하지 않는다. ACTIVE이면서 DRAFT/STALE·정상 날짜가 freshness 밖인 경우와 깨진/비참조 ref를 구별한다. 기존 SourceValidationError·EnvelopeValidationError·ManifestValidationError는 모두 PolicyDataError 하위 타입이다.

## 18. 후속 평가 순서·오류 우선순위

이 순서는 입력·정상 결과 의미를 닫기 위한 계약이며 evaluator 코드는 없다. production에서 재료 준비가 실패하면 정상 Result를 만들지 않는다.

| phase | 책임/오류 선택 |
|---|---|
| 0 외부 준비 | 고정 전체 release/원본 bytes·검토 자료·현재 완전 Context 준비. 기존 전체 dataset validator 연결은20절 의존사항 |
| 1 타입/date | CoverageResult→Envelope→BenefitSnapshot→Context 또는 None→ref 또는 None→Manifest→Registry→data_use_date 순서. INVALID_ACCEPTANCE_EVALUATION_INPUT |
| 2 현재 target | 현재 policy_id→scope/edition→rule identity. 불일치는 ACCEPTANCE_CURRENT_INPUT_MISMATCH |
| 3 Context target | 제공되면 policy_id→scope→benefit_id. ACCEPTANCE_CONTEXT_TARGET_MISMATCH. 선택 없음도 수행 |
| 4 현재 자료 정합성 | source/Manifest 참조 정합성→현재 release 결합→실제 현재 Tree 대응. 기존 validator 오류 전파 또는 ACCEPTANCE_CURRENT_INPUT_MISMATCH. 정상 selection/gate 이전 |
| 5 선택 | None이면 A/B/C 분류만 준비. Context=None+str이면 ACCEPTANCE_CONTEXT_REQUIRED. 그 외 기존 private resolver1회, 없는 ref는 기존 오류 |
| 6 관련 철회 | selected ACCEPTED의 정확한 incoming B만 확인. selected REVOKED는 자기 ref를 근거로 사용. Context 재검증·대안 선택 없음 |
| 7 과거/current guards | selected가 있으면 Inventory→Tree→Coverage Registry→Benefit 정의→Benefit Registry 순서의 같은-version 모순 검사. baseline 없는 해당 축만 생략 |
| 8 정상 사유 수집 | 실행 가능한 selection/철회/기한/current gate·정상 변경 사유를 모두 모아13절 canonical tuple 구성 |
| 9 결과 | private factory1회. 정상9필드와 파생 status, 원본 불변 |

phase4의 여러 참조 오류는 기존 validator가 보장한 순서를 유지한다. 전체 release 함수 연결의 정확한 call graph는 후속 evaluator 설계에서 고정해야 하며 이번 모델 설계로 기존 validator의 순서를 바꾸지 않는다. 동일 입력의 결과/첫 오류는 결정적이어야 한다. 정상 Context 순열은 selected 결과/관련 B/reasons를 바꾸지 않는다.

만료/철회/SLICE를 먼저 보고 조기 UNUSABLE을 반환하지 않는다. phase7의 독립 conflict를 통과해야 정상 사유를 반환한다. no-selection이면7의 비교 상대가 없으므로 생략하지만4의 현재 자료 모순은 생략하지 않는다. partial Result/부분 Bridge 합계를 반환하지 않는다.

## 19. Verification·completeness 정상 gate

기존 실제 Envelope PolicyVerificationStatus는 DRAFT/VERIFIED/STALE이다. source의 VerificationStatus나 lifecycle ACTIVE를 대체하지 않는다. Envelope VERIFIED와 실제 사용 source/locator의 ACTIVE·VERIFIED·policy 적용·일치 version·명시 freshness는 별개다.

정상 current 근거에서 확인일이 없거나 아직 미래이거나 명시 data_use_date와 manifest.freshness_max_age_days를 이용한 포함 구간 밖이면 정책/혜택 쪽 reason8/9 후보다. 기존 파생 last_verified_at/locator-date 구조 모순·잘못된 refs는17절 오류다. freshness는 `[verified_at, verified_at+N일]` 양끝 포함이며 N은 명시 Manifest의 양의 int, 자동7일 기본값을 새로 넣지 않는다. publication_date=null을 단독 실패로 만들지 않는다.

source 수명/존재 검사 오류를 정상 사용요건으로 낮추지 않는다. 정책 leaf refs와 혜택 refs를 분리해 판정하고 같은 Registry/Manifest를 사용한다. 이미 ACTIVE/VERIFIED인 source를 읽을 수 있다고 실제 사람이 claim을 검토했다고 인증하지 않는다. 실제 acceptance artifact에 claim별 대응표/원본 정의가 보존됐다는 외부 전제를 유지한다.

Benefit completeness는13절의 기존 기준이다. 분기/지역화폐/기타 경제유형을 Acceptance 단계에서 현금으로 환산하거나 직접 제외하지 않는다. 정책 효력일/신청창/지급월/사용자 조건은 서로 다른 의미이며 data_use_date만으로 재판정하지 않는다. 정확한 legacy FULL release/verification 연결이 끝나기 전 실제 USABLE 경로를 열지 않는다.

## 20. 구현된 검사와 미구현 의존사항

| 대상 | 현재 실제 제공 | 아직 필요한 것/제한 |
|---|---|---|
| Context/resolver |200개 합성 tests, 소속/유일성/철회 edge 구조·명시 조회 | 관련 B의 현재 사용 차단·selection/no-selection orchestration 없음 |
| Coverage Result/public evaluator | completeness/지문/Review/current baseline | Policy VERIFIED/Benefit 수용·실제 안산 FULL 아님 |
| fingerprint_benefit_snapshot | exact 정의15key 지문·BV01~BV16 | 검토·provenance·current 사용 판정 안 함 |
| SourceRegistry/validate_evidence_refs | 존재/수명·locator·중복/형식 | VERIFIED/freshness·실제 원문 bytes/검토 진실성 검사 아님 |
| validate_envelope_sources | version·적용 대상·파생 last_verified_at 정합성 | 명시 사용일 기준 freshness/운영 수용 아님 |
| validate_dataset_manifest | 명시 전체 envelopes와 Registry·version/domain fingerprint·engine 호환 정합성 | 파일 bytes·실제 artifact/review·source freshness 검사 아님 |
| 현재 Envelope | DRAFT/VERIFIED/STALE metadata·legacy CONDITION_SLICE | 새 Coverage FULL과 실제 full release의 연결은 미완료 |

**후속 evaluator 구현 선행 의존:** 전체 release 검증을 어느 준비 경계에서 수행할지, exact 함수 인자와 source 사용 gate의 call graph, Manifest engine artifact와 Coverage implementation artifact의 실제 대응을 명시해야 한다. validate_dataset_manifest는 Manifest의 **전체** policy reference 집합과 envelopes tuple을 요구하므로 여러 정책 Manifest에 `(현재 Envelope,)`만 넣어 성공한다고 가정하면 안 된다.

외부 단일 adapter가 전체 검증을 수행하고 그 고정 원본을 evaluator와 정규화에 함께 전달하는 방향을 우선한다. 새 “verified=True” 입력으로 이 의무를 대체하지 않는다. exact evaluator signature/validator 연결은 후속 작은 설계에서 닫는다. 이 미완료는 결과9필드/사유/시간 계약의 local 구현을 막지 않지만 **evaluator/실제 서비스 연결 준비 완료를 뜻하지 않는다**.

## 21. 입력 재사용·Bridge 경계 검증 계획

후속 구현은 최소 다음을 검증해야 한다.

- adapter가 외부 precomputed Result/serialized status를 인자로 받지 않음.
- 같은 호출에서 고정한 원본 Benefit으로 평가와 candidate 생성. 다른 target/date/Benefit를 섞는 테스트는 거부.
- Benefit 정의 version/fp·양 provenance·Envelope/Manifest·Scope/date·Context 어느 하나라도 변경하면 새 호출에서 평가.
- 같은 A/date/정의 fp라도 B가 새로 공급되면 과거 USABLE 결과를 재사용하지 않고 ACCEPTANCE_REVOKED.
- serialization/equality를 수용 증거로 사용하지 않음. requests 사이의 cache hit로 current 평가를 생략하지 않음.

이 계약을 구현할 때까지 Result가 단독으로 Bridge에서 소비되는 API를 만들지 않는다. 단일 호출의 내부 pairing은 암호학적 서명/외부 인증 토큰이 아니다. trusted adapter의 코드/테스트와 기존 외부 자료 보존 의무로 제한한다.

## 22. 수동 사례의 공통 전제

아래는 **문서상 수동 사례**다. 실제 객체/승인/결과를 생성하지 않는다. S는 현재 target과 모든 current 자료가 일치하며 FULL/VERIFIED·정의 completeness/근거 사용·외부 실제 검토/준비가 충족된 합성 기준이다. A는 기존 합성 ACCEPTED, B는 Context가 허용한 같은 binding의 후행 REVOKED→A, C는 독립 새 ACCEPTED다. 기준 사용일은 A의 포함 기한 안이다.

표에서 데이터 변경은 정상 constructor를 거친 입력으로 준비한다고 가정한다. 현재 release 전환은 양쪽 dataset/Registry를 함께 고정한다. “이론”은 정상 기존 constructor로 만들 수 없거나 아직 없는 model의 방어 사례이며 실제 runnable fixture로 위조하지 않는다. 모든 USABLE 예시는 합성 gate 전제이지 actual 안산 승인이 아니다.

## 23. 수동 검증 대응표

| ID | 계약/사례 | 기대·검증 단계 |
|---|---|---|
| AE01 | S, Context=None/ref=None | UNUSABLE, NO_ACCEPTANCE_CONTEXT, selected3개/revocation=None |
| AE02 | S, empty Context/ref=None | NO_ACCEPTANCE_RECORDS, 미제공과 구별 |
| AE03 | S, nonempty/ref=None | ACCEPTANCE_NOT_SELECTED, “기록 없음”으로 설명 금지 |
| AE04 | Context=None/명시 ref | ACCEPTANCE_CONTEXT_REQUIRED Data Error |
| AE05 | empty Context/명시 ref | 기존 ACCEPTANCE_REF_NOT_FOUND |
| AE06 | nonempty/없는 명시 ref | 기존 ACCEPTANCE_REF_NOT_FOUND |
| AE07 | S, A 단독 명시 선택 | USABLE, reasons=(), selected는 A |
| AE08 | S, B 명시 선택 | ACCEPTANCE_REVOKED, selected=B/status REVOKED, evidence=B |
| AE09 | 잘못된 target Context/ref=None | TARGET_MISMATCH Data Error, no-selection으로 숨기지 않음 |
| AE10 | raw Context/blank·subclass ref | INVALID_ACCEPTANCE_EVALUATION_INPUT |
| AE11 | S, A+B에서 A 선택 | ACCEPTANCE_REVOKED, selected=A/evidence=B |
| AE12 | S, A+B+C에서 A 선택 | 계속 A 차단, C 자동 선택 없음 |
| AE13 | S, A+B+C에서 C 선택 | C에 직접 철회 없고 C gate 일치 시 USABLE |
| AE14 | B 검토일 이전의 사용일, A 선택 | 현재 supplied B로 ACCEPTANCE_REVOKED, 역사 replay 아님 |
| AE15 | B 검토일 당일 A 선택 | ACCEPTANCE_REVOKED |
| AE16 | B 검토일 이후 A 선택 | ACCEPTANCE_REVOKED |
| AE17 | B.valid_until 이후 A 선택 | 철회 유지, A 부활 없음. A도 만료면 EXPIRED 함께 |
| AE18 | A/B 검토일 동일 | 정상 Context, 알려진 B 적용 |
| AE19 | A 만료 뒤 B 기록 | A 선택에 REVOKED+EXPIRED, B 기한으로 철회 해제 안 함 |
| AE20 | A/B/C의 모든 tuple 위치 순열 | selected/ref/B/reasons 의미 동일 |
| AE21 | B 선택, 사용일이 B 검토일 이전 | REVOKED만 해당, B의 NOT_YET_VALID를 계산하지 않음 |
| AE22 | A.reviewed_at 직전 | NOT_YET_VALID |
| AE23 | A.reviewed_at 당일 | 날짜 gate 통과 |
| AE24 | A.valid_until 당일 | 날짜 gate 통과 |
| AE25 | A.valid_until 다음 날 | EXPIRED |
| AE26 | A의 reviewed_at==valid_until, 해당일 | 날짜 gate 통과 |
| AE27 | datetime/str/date subclass/None 사용일 | 입력 Data Error, 변환 없음 |
| AE28 | S의 current 확인본 정확히 일치 | snapshot 사유 없음 |
| AE29 | 정상 새 i/r version과 대응 fp | COVERAGE_SNAPSHOT_CHANGED |
| AE30 | 정상 새 b version | BENEFIT_SNAPSHOT_CHANGED |
| AE31 | 같은 i version·다른 Inventory fp | INVENTORY_FINGERPRINT_CONFLICT |
| AE32 | 같은 rule version·다른 Tree fp | POLICY_TREE_FINGERPRINT_CONFLICT |
| AE33 | 같은 b version·다른 정의 fp | BENEFIT_FINGERPRINT_CONFLICT |
| AE34 | 양 current D2/G2, 정의 fp 동일 | COVERAGE_SNAPSHOT_CHANGED+BENEFIT_PROVENANCE_CHANGED, 자동 승계 없음 |
| AE35 | 현재 Coverage/Benefit release 혼합 | ACCEPTANCE_CURRENT_INPUT_MISMATCH, 정상 stale 아님 |
| AE36 | 같은 dataset·다른 Registry fp | SOURCE_REGISTRY_FINGERPRINT_CONFLICT |
| AE37 | 정상 SLICE/all-None baseline, 다른 present 축은 같음 | COVERAGE_NOT_FULL. None 차이만으로 변경/conflict 안 만듦 |
| AE38 | SLICE/all-None이지만 같은 i/다른 fp | Inventory conflict 우선, COVERAGE_NOT_FULL 결과로 은폐 금지 |
| AE39 | present implementation fp만 변경 | COVERAGE_SNAPSHOT_CHANGED, 새 implementation version 없음 |
| AE40 | 새 rule이지만 같은 i의 다른 fp | 독립 Inventory conflict 유지 |
| AE41 | 새 dataset이지만 같은 b의 다른 fp | 독립 Benefit conflict 유지 |
| AE42 | Envelope DRAFT 또는 정상 freshness 초과 | POLICY_NOT_VERIFIED, stored VERIFIED를 STALE로 변이하지 않음 |
| AE43 | VARIABLE/UNKNOWN·미완성 분류/월 | BENEFIT_METADATA_NOT_REVIEWED, 임의 고정액 없음 |
| AE44 | 유효 혜택 source 검토상태/freshness 미충족 | BENEFIT_METADATA_NOT_REVIEWED |
| AE45 | quarterly/local currency지만 Acceptance 요건 완결 | Acceptance USABLE 가능, 직접 월 현금은 Bridge 별도 |
| AE46 | A 철회+만료+SLICE+정책 미검토 | REVOKED→EXPIRED→COVERAGE_NOT_FULL→POLICY_NOT_VERIFIED 순서 |
| AE47 | no-selection+SLICE+정책/혜택 gate 실패 | 선택 사유1개+7/8/9, 과거 mismatch 사유를 만들어내지 않음 |
| AE48 | 만료/철회와 같은-version conflict 동시 | Data Error, 정상 Result 없음 |
| AE49 | no-selection과 현재 release 모순 동시 | current Data Error 우선 |
| AE50 | 같은 reason을 중복 저장하거나 순서를 뒤집은 모델 값 | local INVALID_ACCEPTANCE_EVALUATION_RESULT, 자동 정렬/dedupe 없음 |
| AE51 | selected3개가 부분 None인 모델 값 | local Data Error |
| AE52 | selected=None이지만 selection reason 없음/복수 | local Data Error |
| AE53 | selected가 present인데 selection reason 존재 | local Data Error |
| AE54 | selected ACCEPTED/ref=A, evidence=B | REVOKED reason이 있을 때만 유효. selected=A 보존 |
| AE55 | selected REVOKED/ref=B, evidence가 None/다른 ref | local Data Error |
| AE56 | ACCEPTED의 evidence=self 또는 reason4와 ref 비대응 | local Data Error |
| AE57 | NOT_YET_VALID+EXPIRED 또는 REVOKED에 날짜 reason | local Data Error. 정상 평가에선 생성되지 않음 |
| AE58 | derived status 입력/empty reasons에 저장 UNUSABLE 시도 | status는 stored field가 아님. 일반 생성/extra/replace 거부 |
| AE59 | 같은9필드 반복·serializer 수정 | immutable equality/결정성·10key·nested 변경 격리 예정 |
| AE60 | 다른 Benefit/Scope/date로 과거 result 재입력 | adapter가 precomputed Result를 받지 않음. 새 원본으로 재평가 필요 |
| AE61 | 같은 A/date/Benefit라도 Context에 B 추가 | 과거 USABLE 재사용 금지, 새 호출에서 REVOKED |
| AE62 | Context 유효하나 실제 B가 누락 | 실제 철회 부재 인증 못함. 외부 완전성 의무 |
| AE63 | structurally valid 가짜 ACCEPTED/Context | 실제 발급·artifact 진실성 인증 아님 |
| AE64 | USABLE과 사용자 PASS/현금 적용 | 다른 의미. 개인·월·병급·유형 확인 생략 금지 |
| AE65 | 현재 자료로 과거 사용일 입력 | 당시 정보 재현 보장 없음, 알려진 B를 무시하지 않음 |
| AE66 | 없는/중복 evidence·비참조 source/locator | 기존 SourceValidationError(PolicyDataError) 전파, reason8/9로 숨기지 않음 |
| AE67 | 현재 부분 baseline/잘못된 record self-link/날짜 역전 | 기존 constructor가 거부하는 이론적 방어 사례. 객체 훼손 fixture로 만들지 않음 |
| AE68 | 다중정책 Manifest에 현재 Envelope 하나만 제출 | 기존 전체 validator 집합 불일치. 준비 경계 보완 없이는 evaluator 연결 금지 |

**68개 수동 사례**이며 신규 실행 테스트가 아니다. AE50~AE59는 후속 결과 모델 테스트, AE01~AE49/AE66의 정상·오류 계산은 후속 evaluator/준비 경계 tests로 대응한다. AE60~AE61은 adapter API/결합 tests, AE62~AE65는 신뢰·의미 한계의 문서/운영 검증이다. AE67은 기존 constructor 회귀, AE68은 기존 validator 계약과 미래 release 연결 tests다. 한 행의 여러 parameter를 실행 테스트 수로 미리 합산하지 않는다.

## 24. 후속 구현 단위와 검증 계획

| 순서 | 최소 작업 | 완료조건 |
|---|---|---|
| 다음 승인 단계 | **BenefitAcceptanceEvaluation/Status/Reason 값 모델만 구현** |9fields/2상태/12사유·strict 타입·nullable/사유 조합·token 생성 제한·파생 status·10key mutation-isolated serializer·합성 모델 tests, 기존6725개 보존 |
| 이후 별도 설계 | evaluator 정확한 입력/준비·source gates 연결 |20절 전체 release/Manifest·현재 Tree/근거/freshness·artifact 대응·4절 내부 pairing·18절 call/error 순서 확정 |
| 이후 별도 승인 | selection/철회/current 비교 pure evaluator | 표의 선택/시간/guards/사유·오류 전파·순열/반복·공식 factory 연결 tests |
| 이후 별도 승인 | trusted 정규화 adapter/Bridge | 외부 Result 반입 금지·같은 원본/사용일 결합·개인/월·병급·유형·합산, 그 뒤 Cashflow |

모델 전용 구현에서는 Context 검색·관련 B 계산·Coverage/지문/Registry 검증을 호출하지 않는다. synthetic local factory 값은 실제 gate를 실행한 것으로 보고하지 않는다. 현재 result/status/reason/evaluator/Bridge 코드는 없다.

## 25. 미해결 의존사항과 Assumptions

**결과 이름/9필드/2파생 상태/12사유·선택 표·현재 알려진 철회·기한·local invariant·내부 전용 binding 계약은 닫았다.** 다음 결과 모델 구현에 field/time 의미 미결정은 없다.

남은 의존사항은 exact evaluator 입력과 전체 release validator 연결·source 사용 gate 구현·artifact 대응·legacy FULL 연결·trusted adapter 구현이다. 이들을 생략해 실제 USABLE을 발급할 수는 없다. 실제 안산의 거주기간/다른 조건/전체 목록·검토 자료는 계속 별도 blocker다.

**Assumption A1:** 내부 준비 경로가 실제 검토 자료·불변 release/Context를 정직하고 완전하게 공급한다. 이9필드/Context token·지문 문자열이 그 진실성·전역 이력 완전성을 인증하지 않는다.

**Assumption A2:** 초기 서비스는 작은 request 단위 계산이다. 요청 간 cached approval/result 재사용은 지원하지 않는다. 이를 요구하면4절 binding 계약을 먼저 개정한다.

**Assumption A3:** 정상 Coverage Result/record/Context는 기존 constructor/public 경로로 생성된다. 강제 object 훼손·private token 위조를 보안상 방지한다고 주장하지 않는다.

## 26. 기존 계약과 명시적 구체화·대체

| 기존 항목 | 이번 결정/영향 |
|---|---|
| frozen Coverage8필드/지문/GV·record21필드·Context4필드/resolver | **변경 없음**. 새 property/meaning/현재 책임을 가져오지 않음 |
| M2.45 reviewed_at=철회 검토일·예약 철회 없음·horizon은 종료일 아님 | 그대로 유지. effective_at 해석을 추가하지 않고 현재 알려진 B 차단 방식 채택 |
| M2.41의 resolved record 또는 None evaluator 후보·history 검색 없음 | **미구현 후보를 Context+명시 ref 경계로 구체화**. 관련 incoming B 확인만 허용하고 대안/최신 승인 검색은 금지 |
| M2.41의 다른 과거 scope raw record 정상 비교 예시 | 이 current Context API는 target 정확 일치를 요구하므로 해당 기능을 제공하지 않음. 잘못 연결한 Context는 오류. 별도 historical comparer/replay는 미구현 |
| M2.41/45 usable bool·사유 후보 | 저장 bool 대신9필드와 파생 status Enum 선택. NO_ACCEPTANCE를3가지 선택 사유로 분리, Benefit provenance 사유 추가 |
| M2.41의 작은 결과→BenefitCandidate 결합 방향 | **동일 호출 원본으로 생성하는 내부 결과**로 제한. 외부 precomputed Result 재입력/재사용 API 금지. raw Context를 Bridge에 전달하지 않음 |
| broad source 사용요건 실패 표현 | 유효한 검토 상태/freshness 실패는 정상 사유. 기존 Registry가 거부하는 깨진/비참조 ref는 PolicyDataError 그대로 유지 |

위 항목은 이번 설계의 명시적 후보 확정/인터페이스 보완이며 기존 실행 코드·확정된 record의 날짜/철회 의미를 바꾸지 않는다. 사용자 검토 후 모델 구현으로 진행하며 이번에 계약의 소급 수정/fixture 변경은 하지 않는다. 날짜 기반 예약/소급 철회·독립 release 결합·다른 scope 직접 평가·외부 결과 재사용을 지원하려면 별도 spec/impact/호환·테스트 검토가 필요하다.

## 27. 실제 안산·동결·범위 제한

Generic Coverage는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**다. 실제 안산001/002는 DRAFT/CONDITION_SLICE이고 실제 BenefitAcceptance/Context/평가 결과는 없다. source VERIFIED·두 leaf PASS·generic 완료로 FULL/USABLE을 만들지 않는다.

정책 혜택 Cashflow 반영0원 원칙과 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다. 이번에 실제 승인/철회/result·Benefit 금액·현재 정책 지문을 생성하지 않는다.0원은 기존 제한 원칙이며 아직 없는 Bridge를 실행한 결과가 아니다.

## 28. 최종 판단과 검증 기록

**READY_TO_IMPLEMENT_ACCEPTANCE_EVALUATION_RESULT_MODEL**

다음 가장 작은 작업 한 개는 **BenefitAcceptanceEvaluation과 Status/Reason 값 타입만 합성 모델 tests로 구현**하는 것이다. selection/철회 helper/evaluator·verification/Bridge·실제 결과를 포함하지 않는다. evaluator/서비스 연결 준비 완료 판정이 아니다.

사전 전체 pytest: **6725 passed in 13.98s**. 문서 작성 후 전체 pytest: **6725 passed in 14.70s**. 신규 실행 테스트/기대값은0개다. 기존 Context/resolver200개·record472개·Snapshot292개·Benefit 지문74개·Coverage/Cashflow·GV01~GV15/BV01~BV16 회귀를 포함한다. 이 회귀는 아직 없는 current evaluator/결과 모델 구현을 검증한 것이 아니다.

문서28개 절의 연속 순서·정확한9필드·12개 canonical 사유·A~I 선택 표·AE01~AE68의68개 유일/연속 ID·표 열 수·코드 블록·한국어 표기를 확인했다. 정상 기존 생성 경로로 가능한 사례, 아직 없는 결과 모델의 local 방어 사례, 기존 constructor에서 차단되는 이론적 사례와 운영 한계를 구별했다.

사전 actual releases/pycache 제외 backend/tests/data/docs161개 파일 SHA256 대조에서 **기존161개 전부 동일·이 문서1개 추가·수정/삭제0개·총162개**다. 코드·기존 모든 tests/fixture/기대값·동결 명세/지문/golden·기존 Acceptance/Benefit/Context/Cashflow·ResidenceHistory 자료를 보존했다. 실제 release6개 파일도 **SHA256 전부 일치**하고 경로/크기/수정시각이 동일하다. 실제 승인/철회/평가 결과·새 정책 도메인 지문·혜택 금액은 만들지 않았다.

## 29. M2.50 — IMPLEMENTED: Acceptance 평가 결과 값 모델

`backend/policy_engine/policy_data/benefit_acceptance_evaluation_result.py`에 **BenefitAcceptanceEvaluation**, **BenefitAcceptanceEvaluationStatus**, **BenefitAcceptanceReason**과 최소 로컬 helper/private factory만 구현했다. 같은 호출의 원본 입력과 함께 쓰는 내부 결과 경계를 유지해 **policy_data public export는 추가하지 않았다**. 기존 record/Context/resolver·Coverage·Benefit·Cashflow는 수정하지 않았다.

5절의 정확한9필드·타입·순서를 frozen/slots/keyword-only로 구현했다. nullable 값도 default 없는 필수 인자다. `_creation_token`은 keyword-only InitVar(default=None)이며 저장 필드/serializer/equality에는 포함하지 않는다. module private token을 전달하는 `_create_benefit_acceptance_evaluation`이9개 원본 인자를 그대로 생성자1회에 전달한다. token 없는 일반 생성/replace를 TypeError로 거부하고 factory 오류는 원래 객체로 전파한다. private 호출/강제 조작을 방지하는 권한 인증은 아니다.

선택된 record status는 기존 **BenefitAcceptanceStatus**를 그대로 사용한다. 새 평가 Status는 USABLE/UNUSABLE 정확히2개, Reason은13절 순서의 정확한12개다. raw 문자열/다른 Enum·list/tuple subclass를 자동 변환하지 않고 reasons의 원래 tuple을 보존한다. duplicate/역순을 거부하며 canonical subset은 의미 조합이 유효하면 허용한다.

15절의 검증 순서를 그대로 적용했다. token →9필드 타입/문법 →사유 순서/중복 →selected3개 all-None/all-present →미선택/선택 사유 →철회 근거/사유/ref 관계 →기한 사유 조합이다. 같은 오류 phase의 field path는9필드 중 해당 필드를 사용한다. partial selection은 selected_acceptance_ref, 사유 조합은 reasons, 철회 근거 관계는 revocation_acceptance_ref로 표시하며 prefix는 **INVALID_ACCEPTANCE_EVALUATION_RESULT: field: reason**이다. 입력 payload는 출력하지 않는다.

미선택이면 사유1~3 중 정확히 하나와 optional 독립 사유7~9를 허용한다. 선택 전용4~6/10~12·철회 근거는 금지한다. 선택된 기록에는 미선택 사유를 붙일 수 없다. 따라서 미선택+빈 사유를 USABLE로 만드는 경로가 없다.

ACCEPTED A에 별도 B가 철회 근거인 결과는 selected=A/evidence=B로 보존한다. 직접 REVOKED B를 선택한 결과는 selected=B/evidence=B이며 REVOKED reason이 필수다. record의 self-revocation 금지를 결과의 두 ref에 복사하지 않았다. evidence 존재와 REVOKED reason은 동치다. 기한 전/후 사유는 서로 배타적이며 선택된 ACCEPTED에만 허용한다. 실제 A/B 연결·reviewed_at/valid_until은 조회하지 않는다.

read-only status는 reasons가 비면 USABLE, 아니면 UNUSABLE이다. stored status·usable bool/property·setter는 없다. equality/hash는9개 저장 값 전체다. serializer는 저장9key와 마지막 status의 정확한10key를 반환한다. Scope.to_dict·ISO 날짜·Enum.value·새 reasons 문자열 list·명시 None key를 사용하며 반환 nested 값을 변경해도 원본은 바뀌지 않는다. loader/from_dict는 없다.

### 합성 모델 검증과 AE 대응

신규 `tests/test_benefit_acceptance_evaluation_result.py`는 **237개**다.9필드/InitVar/필수성 reflection·2상태/12사유·기존 record Enum 재사용·strict 타입/grammar/date·factory 전달/생성 제한·선택 partial6패턴·미선택3분기와 독립 사유·철회4조합·배타 기한·오류 순서·동결·전체 필드 equality·10key serializer·nested mutation isolation·100회 결정성을 검증했다. 전체 subset을 무작정 생성하거나68개 수동 사례를237개 실행 사례로 세지 않았다.

| AE 계약군 | 이번에 검증한 범위 | 후속으로 남긴 범위 |
|---|---|---|
| AE50~AE59 | 잘못된 사유 순서/중복·partial metadata·미선택/선택 모순·A/B ref·직접 REVOKED·기한 사유 모순·생성/status 제한·불변/serializer | 실제 current gate 계산 없음 |
| AE01~AE03·AE07~AE08·AE11~AE13 | 미선택3상태·USABLE/UNUSABLE·선택 A/B/C의 결과 trace를 합성 값으로 표현 | Context를 받아 자동 분류/resolve/철회 탐지하는 계산 |
| AE17·AE19·AE21~AE30·AE34·AE37·AE39·AE42~AE47 | 기한/변경/불완전 gate 사유와 복수 사유의 정상 결과 표현, exact date 타입 검증 | 날짜 경계·원본 version/provenance/FULL/verification/completeness를 실제 비교해 사유를 산출하는 것 |
| AE04~AE06·AE09~AE10·AE14~AE16·AE18·AE20·AE31~AE33·AE35~AE36·AE38·AE40~AE41·AE48~AE49·AE66·AE68 | 기존 관련 코드/회귀를 보존. 결과 모델이 새로 계산하지 않음 | evaluator/전체 release·근거/지문 guard·related B/순열의 실제 end-to-end 검증 |
| AE60~AE65 | 내부 결과·재사용/신뢰 한계를 유지하고 외부 수용 API/adapter를 추가하지 않음 | 실제 adapter가 과거 Result 반입/재사용을 차단함·운영 이력 완전성/진실성 |
| AE67 | 기존 constructor/frozen 회귀 보존 | 불변 객체를 강제 훼손한 fixture는 만들지 않음 |

이 테스트는 정상 결과의 표현 공간/불가능한 로컬 조합 거부를 입증한다. 실제 Context/날짜/현재 자료에서 해당 결과가 산출돼야 한다는 평가 정확성·운영 사용 승인을 입증하지 않는다. 합성 factory를 거친 USABLE도 실제 발급/검토 인증이 아니다.

검증: 사전 전체 **6725 passed in 15.39s**, 신규 **237 passed in 0.89s**, 최종 전체 **6962 passed in 18.84s**. 기존6725개 테스트/fixture/기대값을 수정하지 않았다. Context/resolver200개·record472개·Snapshot292개·Benefit 지문74개·Coverage/Cashflow·GV/BV 회귀를 포함한다.

**IMPLEMENTED:**9필드 결과 모델·평가 Status/Reason·private 생성 경로·로컬 조합 검증·파생 status·10key serializer·합성 모델 tests.

**NOT IMPLEMENTED:** 실제 Acceptance evaluator/placeholder·Context/ref 조회/related B 검색·현재 gate/기한/철회 효과·snapshot 비교·verification/Registry/Manifest/artifact 검증·지문 계산·adapter·Bridge/Cashflow·실제 안산 평가 결과.

최종 판단: **READY_FOR_ACCEPTANCE_EVALUATOR_CONTRACT_DESIGN**. 다음 가장 작은 작업 한 개는 **evaluator의 정확한 입력과 전체 release/근거 사용 gate·verification/artifact 대응·같은 호출 원본 결합의 계약을 문서로 설계**하는 것이다. 결과 모델 완료가 evaluator 구현 준비 완료는 아니다. 실제 안산 DRAFT/CONDITION_SLICE·반영0원 원칙과 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, Coverage freeze는 유지한다.

### M2.50 최종 변경 범위

사전 actual releases/pycache 제외 backend/tests/data/docs162개 파일과 실제 release6개 파일의 SHA256을 확보했다. 최종 대조에서 **기존159개 동일·문서3개 수정·새 모듈/테스트2개 추가·삭제0개·총164개**를 확인했다. package __init__/public export·기존 모든 source/tests/fixture/기대값·record/Context/resolver·BenefitSnapshot/지문·frozen Coverage source/명세·GV01~GV15/BV01~BV16·Cashflow·ResidenceHistory 자료는 SHA256이 같다.

실제 release6개도 **SHA256 전부 일치**하고 경로/크기/수정시각이 동일하다. 실제 안산 평가 결과·승인/철회·혜택 금액·새 정책 도메인 지문은 만들지 않았다. 문서29개 절·DATA_MODEL36개 절·ARCHITECTURE52개 절의 연속 순서·표/코드 블록·한국어 표기를 확인했고,23절의 기존 AE01~AE68 수동 ID는 유일/연속 상태를 유지한다. 수동68개와 신규 모델 실행237개를 구별한다.
