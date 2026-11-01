# Benefit Acceptance 불변 결정 기록 계약 — M2.45

현재 구현 상태는 **37절 M2.46**을 따른다. BenefitAcceptanceStatus와 PolicyBenefitAcceptance 두 값 타입만 구현했다. 아래 M2.45 설계/검증 기록은 당시 이력으로 유지한다.

작성일: **2026-10-22 / Asia/Seoul**. **문서 전용**. 최종 판단: **READY_TO_IMPLEMENT_BENEFIT_ACCEPTANCE_MODEL**.

이번 산출물은 이 문서 한 개다. Acceptance 모델/Enum/result/context/evaluator·Bridge·Cashflow·실제 정책 기록을 구현하거나 생성하지 않는다. 아래는 다음 모델 구현의 계약이며 이미 존재하는 API가 아니다.

## 1. 목적과 Source of Truth

외부 검토가 승인/철회한 **정확한 Coverage·Benefit 정의/provenance 확인본과 불변 revision**을 하나의 record로 표현한다. 단일 기록의 구조, 외부 검토·이력 선택, 현재 사용 가능성 평가를 분리한다.

| 다시 확인한 문서/코드 | 이번 설계에 적용한 계약 |
|---|---|
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md | FULL 필요조건·Coverage9개 binding·scope/현재 usability·기한/철회·오류 경계 |
| BENEFIT_SNAPSHOT_SPEC.md, 특히14·16~17·31·36~37절 |16필드 모델·정의/배포 분리·동일 dataset/Registry의 MVP 원칙·검토 artifact·실제 지문 API |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md | PolicyBenefitAcceptance 개념명·상태2개·a revision·명시 날짜·accepted_terms·실제 교차검토 |
| CASHFLOW_BENEFIT_BRIDGE_SPEC.md | 사용자/월 적용·중복·유형·무환산·합산 경계 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md / ELIGIBILITY_COVERAGE_RESULT_SPEC.md | 동결된 FULL/SLICE·8필드 Result·현재 baseline·same-version guarded comparisons |
| POLICY_DATA_ENVELOPE_SPEC.md | 기존 verification·immutable dataset/manifest·source version·freshness와 실제 검토 책임 |
| DATA_MODEL.md / ARCHITECTURE.md | 독립 Snapshot/지문 구현 완료, Acceptance/Bridge/실제 연결 미구현 |
| 현재 EligibilityCoverageResult/Status·Review 값 모델 | exact Scope/date·비공백 refs·i version·비공백 rule version·hex64·구조/계산 경계 |
| 현재 BenefitSnapshot·fingerprint_benefit_snapshot | exact16필드·b version·정의15key 지문, dataset/Registry 제외 |
| 현재 PolicyEnvelope/SourceBinding/DatasetManifest/PolicyDataError | 실제 DRAFT/VERIFIED/STALE·자료 identity·기존 오류 계층 |

현재 Acceptance record/status/context/result 코드는 없다. 기존 개념명을 유지하여 **구현 클래스명은 PolicyBenefitAcceptance**, 새 상태 타입명은 **BenefitAcceptanceStatus**로 확정한다. 문서의 BenefitAcceptance는 subsystem 개념명이며 별도 alias 클래스를 만들지 않는다.

동결 Coverage와 Snapshot/지문 의미는 그대로다. 기존 Acceptance 후보를 보완하는 범위는17절에 명시한다. 과거 문서/코드는 이번에 수정하지 않는다.

## 2. Acceptance의 정확한 의미

PolicyBenefitAcceptance는 **특정 policy/scope의 특정 Benefit 정의와 그 Coverage/provenance 확인본을 서비스 경제 시뮬레이션에서 사용하도록 외부 검토가 승인하거나 특정 승인을 철회했다고 기록한 불변 결정 revision**이다.

행정기관의 신청/지급 승인, 사용자 eligibility PASS, 입금 확정, Policy VERIFIED, Coverage FULL, Bridge 적용액·Cashflow 결과를 뜻하지 않는다. ACCEPTED라는 저장 사실과 현재 usable이라는 평가 결과를 합치지 않는다. 사용자 문구는 기존 “시뮬레이션 반영 검토 완료” 의미를 유지한다.

## 3. Record validity와 truthfulness boundary

생성 성공은21개 값의 타입/문법/로컬 관계가 유효하다는 뜻이다. 사람이 실제 검토했는지, artifact가 존재하는지, 그 검토가 정확한지, 현재 자료에도 사용할 수 있는지를 인증하지 않는다. 유효해 보이는 ACCEPTED metadata를 직접 만들 수 있다는 한계를 명시한다.

실제 원문 의미 대조·별도 검토자·불변 artifact 보존·현재 철회 상태의 완전한 선택은 팀의 자료 준비/발행 절차 책임이다. 전자서명·인증/권한 서버·새 검토 플랫폼을 선행 구현하지 않는다. ref·해시 문자열은 그 진실성을 대신하지 않는다.

단일 record는 완전한 과거 감사 archive가 아니다. 정확한 원본 Snapshot/Manifest/Registry/Review/artifact를 외부에서 불변 보존해야 재현할 수 있다. 사용자 소득·주소·facts·시나리오 입력을 그 보존 자료에 넣지 않는다.

## 4. Target identity

stable Benefit lineage는 **(policy_id, benefit_id)**, 수용 target은 **(policy_id, scope, benefit_id)**다. scope는 기존 exact ApplicabilityScope이고 edition_id를 별도 저장하지 않는다. Q3/Q4/annual/다른 연도는 다른 target이며 자동 승계하지 않는다.

정책·혜택 ID는 기존 canonical 문법을 그대로 사용한다. component 분할이나 동일 사업 여부를 constructor가 추론하지 않는다. 현재와 다른 policy/benefit의 승인을 직접 연결하면 오류다. 같은 계보의 정직한 과거 scope와 현재 범위 비교는 M2.41대로 정상 범위 변경이다.

## 5. Record identity와 revision key

| 차원 | 확정 의미 |
|---|---|
| target | (policy_id, scope, benefit_id) |
| record identity | **acceptance_ref**: 정확히 한 immutable decision revision을 가리킴 |
| revision | **acceptance_version**: 같은 target 안의 명시적 결정 버전 |
| revision uniqueness key | (policy_id, scope, benefit_id, acceptance_version) |

하나의 acceptance_ref를 새 내용에 재사용하지 않는다. 같은 target/version에 서로 다른 ref를 붙여 두 revision처럼 만들지도 않는다. 이 두 유일성은 단일 record가 아니라 외부 이력/후속 collection에서 검사한다. 동일 객체/동일 내용 반복도 collection에서는 중복 오류이며 조용히 dedupe하지 않는다.

acceptance_ref의 전역 유일성은 외부 발급 범위의 의무다. 한 target의 작은 collection만으로 모든 다른 target의 충돌까지 발견한다고 주장하지 않는다. 표시명·날짜·version을 합쳐 ref를 자동 생성하지 않는다.

## 6. acceptance_ref

exact 비공백 str이다. 검사용 strip 결과가 비어 있는지만 확인하고 원래 문자열은 보존한다. 대소문자·공백·Unicode 보정·자동 UUID·business ID 인코딩·파일 경로/URL 해석을 하지 않는다. 문자열 하위 타입도 거부한다. 기존 Review ref의 작은 opaque 문자열 관례를 따른다.

새 ACCEPTED/REVOKED/재승인/기간 연장 revision은 새 ref를 가진다. 명시 ref가 있는데 실제 record가 없거나 선언한 대상/버전과 resolve 결과가 다르면 후속 resolution의 Data Error다. ref=None인 외부 상태는 정상 no record와 구별해 처리한다. record 자신의 acceptance_ref는 None일 수 없다.

## 7. acceptance_version

기존 a0001 방향을 정확한 grammar로 확정한다. **`a(?:[0-9]{4}|[1-9][0-9]{4,})`이며 a0000은 금지**다. a0001~a9999/a10000 이상을 허용하고 축약·대문자·불필요한 선행0·공백·Unicode 숫자·숫자 자동 변환은 거부한다.

target별 revision이다. i/r/b/d/dataset의 별칭이 아니며 version 크기로 최신 기록을 자동 선택하지 않는다. 외부 발급 시 기존 target 이력과 대조하여 새 version을 명시한다. 특정 A를 철회하는 B는 같은 target의 더 뒤 revision이어야 하지만 이전 A를 보지 않는 constructor는 그 비교를 수행하지 않는다.

## 8. Stored status

**BenefitAcceptanceStatus(str, Enum): ACCEPTED / REVOKED** 두 canonical member만 사용한다. 정확한 Enum 객체만 받고 raw string을 자동 변환하지 않는다. PENDING/REJECTED/MISSING/STALE/EXPIRED/USABLE/UNUSABLE은 저장 member가 아니다.

| 저장/외부 상태 | 의미 |
|---|---|
| record 없음 | 미발급/선택 없음, 향후 정상 NO_ACCEPTANCE |
| ACCEPTED | 해당 revision에서 사용 검토를 승인했다고 기록함 |
| REVOKED | 명시 과거 승인 revision을 철회했다고 기록함 |

현재 오래됨·기한 초과·Scope 변경으로 과거 status를 바꾸지 않는다. status가 ACCEPTED인 역사 기록은 그대로 보존한다.

## 9. Revocation semantics와 선택 비교

| 방안 | 검토 | 결정 |
|---|---|---|
| target/snapshot만으로 철회 | 같은 확인본을 재승인한 여러 revision 중 무엇을 철회했는지 모호함 | 미채택 |
| **revokes_acceptance_ref** | 정확한 과거 승인 한 개를 식별하고 self-link를 로컬 거부할 수 있음 | 채택 |

REVOKED는 **특정 immutable ACCEPTED revision의 철회**다. Benefit 계보 전체의 영구 금지나 정책 전체 철회로 확대하지 않는다. 새 REVOKED B는 새 ref/version/artifact를 갖고 A의 target·Coverage/Benefit binding을 그대로 고정한다. A는 수정/삭제하지 않는다.

후속 이력 검증은 B의 ref가 존재하는 ACCEPTED A를 가리키는지, 같은 target·동일 binding인지, B의 revision이 더 뒤인지, B.reviewed_at이 A.reviewed_at 이상인지 확인한다. REVOKED를 다시 revoke하는 chain은 지원하지 않는다. 재승인은 새 ACCEPTED revision으로 표현하고 과거 철회 기록은 남긴다. 현재 사용할 결정의 선택은 외부에서 명시하며 옛 A를 자동 fallback하지 않는다.

철회 발급은 현재 FULL/VERIFIED를 요구하지 않는다. 정정·검증 실패·기한 경과 후에도 과거 잘못된 승인을 철회할 수 있어야 한다. B는 철회 대상 A의 과거 binding을 보존하고 새 검토 artifact에 철회 근거/사유를 남긴다. 새 source를 반영해 A의 binding을 덮어쓰지 않는다.

## 10. Coverage snapshot binding

M2.41의9개 identity를 모두 유지한다. target의 policy_id/scope를 공유하고 나머지7개는 coverage_ prefix로 명확히 구별한다.

| 기존 CoverageResult 경로 | Record 필드 |
|---|---|
| policy_id | policy_id |
| scope | scope |
| inventory_version | coverage_inventory_version |
| findings.inventory_fingerprint | coverage_inventory_fingerprint |
| rule_version | coverage_rule_version |
| findings.policy_tree_fingerprint | coverage_policy_tree_fingerprint |
| dataset_version | coverage_dataset_version |
| source_registry_fingerprint | coverage_source_registry_fingerprint |
| implementation_fingerprint | coverage_implementation_fingerprint |

record의 승인 binding은 모두 필수다. current Result의 baseline=None은 유효한 SLICE일 수 있지만 **record의** 승인 binding을 None으로 비워두는 것은 오류다. 발급 당시 FULL을 확인한 자료/refs는 artifact로 연결하며 coverage_status bool/Enum·Result 전체·private findings 객체를 저장하지 않는다.

## 11. Benefit snapshot binding

target policy_id/scope/benefit_id에 더해 **benefit_version, benefit_fingerprint, benefit_dataset_version, benefit_source_registry_fingerprint**를 저장한다. version은 Snapshot의 b grammar, 지문은 구현된 기존 정의15key 지문이다.

Snapshot 전체·금액/주기·근거 객체를 runtime record에 중복 복제하지 않는다. 외부에서 보존한 읽을 수 있는 승인 정의는17절의 artifact에 연결한다. 이 결정의 기존 accepted_terms 보완 범위를 명시적으로 적용한다.

지문 계산은 기존 public 함수의 외부 계산 결과를 공급받는다. record는 그 형식만 검사하며 지문 utility를 import/호출하지 않는다. payload에 없는 dataset/Registry provenance도 별도로 고정하므로 정의 지문이 같다는 이유로 배포 승인을 승계하지 않는다.

## 12. Provenance separation과 MVP equality

두 subsystem provenance는 각각의 의미를 분명히 하도록 **별도4필드**로 보존한다. 동시에 현재 MVP의 local invariant는 다음 두 equality다.

```text
coverage_dataset_version == benefit_dataset_version
coverage_source_registry_fingerprint == benefit_source_registry_fingerprint
```

이유는 일반적인 추측이 아니라 **승인된 BENEFIT_SNAPSHOT_SPEC.md14·34절의 동일 dataset/Registry 원칙**이다. M2.41 역시 현재 Coverage/Envelope/Manifest/Benefit의 같은 고정 확인본 결합을 요구한다. 지금 별도 Benefit release를 결합하는 실행 계약은 없다. 문자열이 같은 source를 썼을 것이라는 추론으로 equality를 추가한 것이 아니다.

record의 두 값이 다르면 현재 MVP에서 서로 다른 자료를 묶은 구조 오류다. 둘 다 동일한 과거 D1/G1인 역사 record는 유효하며 현재 D2/G2와 비교될 때 정상 unusable이다. **새 current 입력에서 한쪽만 D2로 바뀐 혼합**은 과거 stale가 아니라 current 입력 오류다.

별도 prefix는 snapshot provenance 출처를 보존하고 후속 연결 검사를 명료하게 한다. 향후 독립 release를 허용하려면 이 local invariant와 manifest/source 결합 규칙을 명시 개정해야 한다. 이번에 범용 다중 release 지원·loader를 추가하거나 equality를 암묵적으로 면제하지 않는다.

## 13. Verification relationship와 최소 provenance

기존 실제 타입은 **PolicyEnvelope.verification_status: PolicyVerificationStatus(DRAFT/VERIFIED/STALE)**다. source의 VerificationStatus나 lifecycle ACTIVE를 대체 사용하지 않는다. record에는 policy_verified bool·verification status/ref/version·새 VerificationResult를 추가하지 않는다.

정책의 정확한 검토 확인본은 record의 policy_id/scope.edition_id/coverage_rule_version/coverage_dataset_version과, 외부에 보존한 기존 DatasetManifest의 PolicyEditionReference로 추적한다. 그 기존 reference에는 Envelope domain fingerprint와 artifact 참조가 이미 있다. 검토 artifact는 그 manifest/Envelope 확인본과 source 검토를 명시한다. record에 두 번째 Envelope 지문을 복제하는 새 축은 필요하지 않다.

이 최소안은 **dataset ID의 immutable 보존과 기존 manifest/artifact 검증이 실제로 수행된다는 외부 전제**가 있다. ID만 같으면 내용을 인증한다는 주장이 아니다. 같은 dataset에서 Envelope metadata가 몰래 달라지면 기존 manifest/발행 감사 오류이며 constructor가 이를 발견할 수는 없다.

ACCEPTED 발급 및 현재 사용 시 기존 Envelope의 VERIFIED·source/locator 상태/적용 대상·명시 날짜 기준 freshness·실제 교차 검토가 별도 gate다. Acceptance 기한이 남아 있어도 자동 통과시키지 않는다. legacy Envelope는 여전히 slice-only이며 새 CoverageResult FULL이 그 값을 바꾸지 않는다. 실제 full release 연결은 미완료다.

## 14. 최종 stored fields — 정확히21개

후속 **PolicyBenefitAcceptance**는 frozen=True, slots=True, kw_only=True다. 아래21개를 순서대로 **모두 필수 인자**로 받는다. nullable revokes_acceptance_ref도 default 없이 명시한다. 별도 acceptance_id/edition_id/accepted_terms/status cache/현재 usable 필드를 추가하지 않는다.

| 순서 | 필드 | 정확한 타입·규칙 |
|---|---|---|
| 1 | acceptance_ref | exact 비공백 str, opaque 불변 revision ref |
| 2 | acceptance_version | exact str, a0001 이상 grammar |
| 3 | status | exact BenefitAcceptanceStatus |
| 4 | policy_id | exact str, 기존 canonical ID grammar |
| 5 | scope | exact 기존 ApplicabilityScope |
| 6 | benefit_id | exact str, 기존 canonical ID grammar |
| 7 | coverage_inventory_version | exact str, i0001 이상 기존 grammar |
| 8 | coverage_inventory_fingerprint | exact 소문자hex64 str |
| 9 | coverage_rule_version | exact 비공백 str, 기존 Result/Review와 동일 |
| 10 | coverage_policy_tree_fingerprint | exact 소문자hex64 str |
| 11 | coverage_dataset_version | exact 비공백 str |
| 12 | coverage_source_registry_fingerprint | exact 소문자hex64 str |
| 13 | coverage_implementation_fingerprint | exact 소문자hex64 str |
| 14 | benefit_version | exact str, b0001 이상 기존 grammar |
| 15 | benefit_fingerprint | exact 소문자hex64 str |
| 16 | benefit_dataset_version | exact 비공백 str |
| 17 | benefit_source_registry_fingerprint | exact 소문자hex64 str |
| 18 | reviewed_at | exact datetime.date |
| 19 | valid_until | exact datetime.date |
| 20 | review_artifact_ref | exact 비공백 str |
| 21 | revokes_acceptance_ref | exact 비공백 str 또는 None,18~19절의 status 규칙 |

6개 지문은 모두 같은 hex64 구조로 검사하지만 역할을 교환하지 않는다. coverage_rule_version은 frozen Result/Review와 같은 비공백 str이며 record에서 r#### 제한을 신설하지 않는다. 기존 Envelope와 실제 rule 대응은 외부 입력 결합에서 확인한다. nullable baseline이나 문자열 자동 변환은 없다.

## 15. Local structural validation

로컬 검증 순서는14절의21개 필드 순서대로 exact 타입/문법을 확인한 뒤 **날짜 순서 → dataset equality → Registry equality → status/link 조합 → self-revocation 금지**다. ref에 대한 strip은 blank 검사에만 사용하고 값을 바꾸지 않는다.

policy_id/benefit_id는 `[A-Z0-9]+(?:-[A-Z0-9]+)*`, i/a/b version은 각각 해당 prefix의 양의 기존4자리 이상 규약이다. coverage_rule_version과 두 dataset/ref 필드는 exact 비공백 str이다.6개 지문은 접두사 없는 `[0-9a-f]{64}`다. raw Enum string·subclass Scope/date·datetime·ISO 문자열 날짜를 자동 변환하지 않는다.

구조 오류는 기존 **PolicyDataError**, 고정 prefix 방향은 **INVALID_BENEFIT_ACCEPTANCE: field: reason**이다. 추가 오류 Enum/새 framework는 없다. 필수/extra 인자 오용은 Python TypeError다. 메시지에 원문/사용자 입력·payload·가짜 승인 내용을 출력하지 않는다.

constructor는 Coverage evaluator·Benefit 지문·Policy verification·artifact resolve·context lookup·현재 usability·Bridge/Cashflow를 실행하지 않는다. 같은 version/다른 지문 비교는 비교 상대가 필요한 후속 평가/이력 책임이다. 로컬 모델에 hash(any)·최신 선택·원문 의미 추론을 넣지 않는다.

## 16. Date contract와 REVOKED horizon

reviewed_at/valid_until은 모두 **required exact date**다. None/무기한 기본값/현재시각 default/문자열 parser는 없다. `reviewed_at <= valid_until`은 local invariant이며 같은 날도 유효하다.

ACCEPTED의 reviewed_at은 해당 승인 revision 검토일, valid_until은 승인 확인을 사용할 마지막 날짜다. 현재 평가에서 `reviewed_at <= data_use_date <= valid_until` 양끝 포함이다. 하한 전·상한 후는 정상 unusable이며 과거 status를 바꾸지 않는다.

REVOKED의 reviewed_at은 철회 결정 검토일이다. valid_until도 통일된 record 구조의 명시 metadata 재확인 horizon으로 요구하고 reviewed_at 이상이어야 한다. **철회 효과의 종료일은 아니다.** 기한을 지났다고 철회가 풀리거나 과거 A가 다시 usable해지지 않는다. 과거 A.valid_until을 기계적으로 복사해 날짜 역전을 만들지 않는다.

선택한 REVOKED는 날짜 범위 안/밖과 관계없이 현재 사용 불가다. 예약 철회·미래 자동 전환은 지원하지 않는다. 과거 감사 재현에서 어떤 revision을 선택할지는 외부가 목적/기준일을 명시하며 current-service 승인을 과거 replay로 우회하지 않는다. data_use_date/target_month는 record 필드가 아니다.

## 17. Review artifact와 기존 accepted_terms 보완

review_artifact_ref는 기존 Review 값 모델과 같은 exact 비공백 opaque str이다. record가 파일/DB/URL을 열지 않는다. 기존 M2.4 review_ref의 역할은 **결정 identity=acceptance_ref, 실제 검토 자료 참조=review_artifact_ref**로 명확히 구별한다. 별도 두 번째 review_ref 필드를 두지 않는다.

artifact에는 실제 준비자/별도 검토자의 팀 handle·검토일·record ref/target/revision/status·Coverage9개 binding과 원래 Review/자료 참조·Benefit version/지문/provenance·승인/철회 사유·수동 사례를 연결한다. 실명/사용자 경제정보는 요구하지 않는다.

**읽을 수 있는 accepted_terms와 정책/혜택 source binding 합집합을 불변 artifact에 보존**한다. 해당 BenefitSnapshot의 정확한16key 값 또는 이를 재현할 불변 원본 참조가 있어야 한다. 승인 지문에 대응하는 정의·제한·금액·월·근거를 사람이 다시 확인할 수 있어야 하며, hash 문자열만 남기는 것은 불충분하다.

claim별 amount/cadence/medium/restriction/applicable_months → Snapshot refs의 비어 있지 않은 부분목록 대응표도 artifact가 담당한다. 관련 source document versions·공식성/locator·freshness 검토와 고정 Manifest/Envelope 확인본을 연결한다. refs가 존재한다는 사실로 모든 claim 검토를 대체하지 않는다. artifact contents와 실제 지문 일치 검증은 외부 자료 준비 책임이다.

| 기존 계약 | 이번 명시적 보완/대체 |
|---|---|
| M2.4 4절의 composite identity | target/version revision key는 유지, 조회 identity acceptance_ref를 별도로 도입 |
| M2.4 review_ref | acceptance_ref와 review_artifact_ref의 두 역할로 구체화 |
| M2.4 4·11·15절, M2.41 13·15·27절의 runtime accepted_terms/source bindings 복제 | **record stored field에서는 제외하고 불변 artifact/정확한 원본에 보존** |
| M2.42 17·31절의 읽을 수 있는 승인 정의 보존 | 보존 의무 유지, 위치는 artifact로 단일화 |
| M2.41의 Coverage identity/기한/status/현재 평가 분리 | 그대로 유지 |
| M2.42의 단일 dataset/Registry·별도 BenefitReview 불필요 | 그대로 유지 |

판단 근거: M2.4 당시에는 안정된 Benefit 값/지문 계약이 없었지만 현재는16필드 모델과 BV로 고정된 전용 지문이 있다. record에 다시 부분 정의 객체를 만들면 같은 의미가 두 표현으로 갈라질 수 있다. 읽을 수 있는 정확한 정의와 감사 근거는 필수로 보존하고, runtime record는21개 identity/decision 값으로 제한한다. 이 문서가 승인되면 위 후보 Acceptance 조항의 위치 변경을 적용하며 frozen Coverage/Snapshot 의미를 바꾸지 않는다.

## 18. ACCEPTED invariants

로컬로 status=ACCEPTED이면 **revokes_acceptance_ref=None**이다.21개 필드와 날짜/provenance 구조 요건을 모두 만족해야 한다. 미검토 상태를 PENDING record로 생성하지 않는다.

실제 승인 발급은 외부에서 Coverage FULL·Policy VERIFIED/근거 사용요건·초기 fixed-only Benefit completeness·claim 검토·정확한 원본 지문/binding·기한을 확인한 뒤 수행한다. constructor는 Snapshot을 받지 않으므로 VARIABLE/UNKNOWN·SLICE를 스스로 발견하지 않는다. 구조적으로 생성 가능한 ACCEPTED가 실제 발급 승인이라는 뜻은 아니다.

후속 현재 평가에서도 FULL/verification·complete definition·정확한 binding·선택 승인·날짜가 필요하다. 사용자 PASS·개인/월 적용·현금 유형은 별도다.

## 19. REVOKED invariants

로컬로 status=REVOKED이면 **revokes_acceptance_ref는 exact 비공백 str이며 자신의 acceptance_ref와 달라야 한다**. 나머지21필드 구조·날짜/provenance invariant도 유지한다. 이것만으로 연결 대상의 실제 존재/상태/동일성을 증명하지 않는다.

후속 resolution/발급 검증은9절의 ACCEPTED target·동일 binding·revision/날짜 선후 관계를 검사한다. target ref가 없거나 다른 policy/scope/benefit·다른 snapshot·REVOKED를 가리키면 오류다. 과거 A의 만료 이후에도 새 철회 record를 발급할 수 있다.

well-formed selected REVOKED는 정상 unusable이다. 단 잘못된 current 입력/깨진 ref/독립 같은-version 지문 모순까지 정상 철회로 숨기지 않는다. M2.41의 독립 오류 검사 우선 원칙을 유지한다.

## 20. Immutable revisions와 이력

재검토·기간 연장·오류 정정·철회·재승인에는 새 ref/version/artifact를 발급하고 과거 기록을 수정/삭제하지 않는다. 동일 ref 또는 동일 target/version의 다른 내용은 이력 충돌이다. 단일 constructor는 그 과거 상대를 조회하지 않는다.

REVOKED B는 A 하나를 지목한다. 이후 C가 같은 target을 새로 승인할 수 있지만 C의 발급 근거와 모든 현재 gate가 다시 필요하다. B의 horizon 경과·새 데이터 존재만으로 C를 만들거나 A를 자동 복구하지 않는다. 자동 최신 선택·예약된 version 전환·revocation chain engine은 없다.

외부 준비는 현재 쓸 승인/철회 상태와 관련 이력을 완전하게 제공해야 한다. 이미 철회된 A만 골라 공급한 불완전 입력으로 pure evaluator가 누락 B를 발견할 수는 없다. 이 trust boundary를 상태 bool로 감추지 않는다.

## 21. Current usability와 record 분리

| 외부 선택/record | 현재 조건 | 향후 결과 |
|---|---|---|
| 없음 | 어떤 current 자료든 | 정상 unusable, no-record 사유 |
| ACCEPTED | 동일한 완전 자료·FULL/VERIFIED·날짜 등 모두 통과 | usable 후보, 개인/Bridge 적용 별도 |
| ACCEPTED | 정상 새 scope/version/provenance | 정상 unusable, 재검토 필요 |
| ACCEPTED | reviewed_at 이전 / valid_until 이후 | 정상 unusable, status는 유지 |
| REVOKED | 잘못된 연결/모순 없는 현재 입력 | 정상 unusable, 만료 뒤에도 동일 |
| 어느 record든 | malformed/broken ref/같은-version 내용 모순 | Data Error, 정상 사용 결과 없음 |

향후 gate의 첫 **정상 사용요건**은 current Coverage FULL이다. 입력·ref 정합성/독립 같은-version guard를 생략하는 조기 return을 뜻하지 않는다. current SLICE·REVOKED·만료도 독립 Data Error를 가리지 않는다. current Result의 정상 all-None baseline은 SLICE로 보존하며 old 값으로 채우지 않는다.

record에는 usable/is_current/is_complete/reasons/캐시를 넣지 않는다. 평가 결과의 상태/사유는 별도 값으로 반환하고 입력 record를 변이시키지 않는다.

## 22. Normal unusable vs Data Error

| 정상 unusable | Data Error |
|---|---|
| record 없음 | 명시 ref가 없거나 다른 record로 resolve됨 |
| well-formed selected REVOKED | self-link·잘못된 철회 대상/chain·이력 충돌 |
| ACCEPTED 날짜 하한 전/상한 후 | date 타입/순서 오류 |
| current 정상 SLICE·Policy DRAFT/STALE·근거 사용요건 미충족 | Coverage 자체 오류·현재 자료 간 다른 target/provenance |
| 정상 새 scope/i/r/b/dataset/artifact baseline | 같은 identity/version의 다른 Inventory/Tree/Benefit 지문 |
| 유효 VARIABLE/UNKNOWN 정의 | 명시 source/ref 깨짐·metadata 구조 모순 |

record와 current가 각각 내부적으로 정합한 과거/새 확인본인 경우가 정상 stale다. current Coverage와 current Benefit가 서로 다른 dataset을 주장하는 경우는 stale가 아니다. 같은 dataset에서 Registry 내용만 달라진 것도 오류다. 오류를0원 합계·SLICE·UNKNOWN으로 catch하지 않는다.

## 23. Invalidation matrices와 guarded comparisons

| Coverage binding | 정상 변경 | 동일 domain의 모순 |
|---|---|---|
| policy_id | 다른 대상 직접 record 연결은 오류 | identity 오류 |
| scope | 정상 다른 scope는 unusable | 선언 ref와 resolve target 불일치는 오류 |
| inventory_version/fingerprint | 새 i version은 unusable | 같은 (policy,scope,i version)의 다른 fp는 오류 |
| rule_version/tree fingerprint | 새 rule version은 unusable | 같은 (policy,rule version)의 다른 Tree fp는 오류 |
| coverage_dataset_version | 새 dataset은 unusable | 동일 ID overwrite는 외부 불변 자료 감사 오류 |
| coverage_source_registry_fingerprint | 새 dataset에서 정상 Registry 변경은 unusable | 같은 dataset의 다른 Registry fp는 오류 |
| coverage_implementation_fingerprint | 새 값은 정상 unusable | 별도 구현 version이 없으므로 차이 자체를 같은-version 오류로 만들지 않음 |

| Benefit binding | 정상 변경 | 동일 domain의 모순 |
|---|---|---|
| benefit_id | 다른 component 직접 record 연결 오류 | identity 오류 |
| benefit_version/fingerprint | 같은 target의 새 b version은 unusable | 같은 (policy,scope,benefit,b version)의 다른 fp는 오류 |
| benefit_dataset_version | 새 dataset은 fp 같아도 unusable | 단일 release 전제의 current 결합 오류와 구별 |
| benefit_source_registry_fingerprint | 새 dataset에서 Registry만 바뀌어도 재검토 | 같은 dataset의 다른 Registry fp는 오류 |

버전 차이는 **그 쌍**의 content 비교만 면제한다. 새 dataset이라고 같은 b/Tree/Inventory 모순을 면제하지 않는다. scope가 다르면 scoped Inventory/Benefit version domain도 다르지만 Tree의 domain에는 scope가 없으므로 같은 policy/rule의 Tree 모순은 여전히 오류다. 새 Review로 현재 FULL이 됐어도 과거 Acceptance와의 same-version 모순 guard는 별도로 필요하다.

현재 단일 release 정책 때문에 정상 dataset/Registry 전환은 양 current subsystem을 함께 고정한 뒤 record와 비교한다. 각 matrix의 열은 해당 binding mismatch의 의미이며 current 한쪽 provenance만 바꾸라는 지시가 아니다. 지문 함수 자체는 이런 사용 가능성/이력 오류를 계산하지 않는다.

## 24. Serialization

to_dict는14절 **21개 stored key를 같은 순서로** 새 dict에 반환한다. status는 Enum.value, scope는 기존 to_dict의 새 nested dict, 날짜는 exact date.isoformat(), revokes_acceptance_ref=None은 null이다. None key를 생략하거나 alias/파생 key를 더하지 않는다.

current usability·FULL/VERIFIED·evaluator reasons·현재 날짜·지문 재계산·원문/artifact 내용을 serializer에 넣지 않는다. 새 scope dict를 수정해도 원본은 바뀌지 않는다. 이것은 미래 release JSON loader/schema가 아니며 이번에 loader를 추가하지 않는다.

## 25. Immutability와 equality

frozen/slots/keyword-only 값이며21필드 전부에 대해 equality/hash를 사용한다. 날짜·Scope도 기존 immutable 값을 보존한다. 미래 current 날짜/환경에 따라 equality가 바뀌지 않는다. 동일 입력 반복 serialization은 같은 값이다.

과거 A와 새 B의 구별은 새 ref/version/status·artifact·날짜 값으로 나타나며 A의 setter를 열지 않는다. 개인정보·자동 로그·외부 전송·영구 사용자 입력 보관을 추가하지 않는다.

## 26. Direct constructor 정책

**일반 structural constructor를 허용**한다. CoverageResult처럼 private sentinel/factory-only 생성 제한을 추가하지 않는다. CoverageResult는 계산된 findings와 원본 대응을 공식 실행 경로에서 조립하는 결과이고, Acceptance는 외부에서 검토/발행한 선언적 기록을 구조 값으로 읽어야 한다는 차이가 있다.

factory-only로 만들어도 가짜 검토 진실성이 인증되지는 않는다. 외부 loader/issuance·현재 평가 gate가 따로 필요하다. constructor는21개 필드/로컬 규칙을 검사하며 승인 발급 권한을 주는 API가 아니다. 실제 issuance factory/저장소/서명 workflow는 이번 범위 밖이다.

후속 모델의 직접 의존 후보는 dataclasses/enum/datetime.date/re·기존 PolicyDataError/ApplicabilityScope뿐이다. CoverageResult/BenefitSnapshot/지문 함수/PolicyEnvelope/SourceRegistry/Bridge/Cashflow import가 필요 없다. SourceBinding도 record 필드가 아니므로 새로 import/복제하지 않는다.

## 27. Context/collection과 resolution 후속 필요성

**명시 ref/철회 연결을 검사할 작은 불변 collection 계약은 후속 단계에서 필요하다.** Coverage ReviewContext의 exact tuple·ref 유일성·명시 lookup 철학을 참고하되 다종 review matching 전체를 복제하지 않는다. 단일 record 구현의 선행조건은 아니다.

가장 작은 후보는 한 policy/scope/benefit target의 역사 records와 선택 acceptance_ref(또는 None)를 받는 묶음이다. 후속 설계에서 정확한 필드/API를 확정한다. collection은 같은 target·ref 및 target/version 유일성·명시 선택 ref 존재·REVOKED의 원래 ACCEPTED ref/동일 binding/후행 version·검토일 관계를 검사한다. 같은 artifact를 여러 decision entry가 공유할 수 있으므로 artifact_ref 전역 유일성을 추가하지 않는다.

모든 records의 구조/연결 오류는 선택 대상이 아니거나 선택 ref=None이어도 숨기지 않는다. 역사 version/dataset 차이는 공존할 수 있다. version/date 정렬로 최신을 고르거나 옛 승인 fallback을 하지 않는다. 실제 누락 철회·전역 이력 완전성은 외부 제공 책임이다.

외부 resolution은 exact selected record 또는 None을 future evaluator에 공급한다. M2.41의 pure evaluator가 직접 파일/DB나 record history를 검색하지 않는 경계를 유지한다. Bridge가 context를 resolve하거나 Acceptance를 재판정하지 않는다. Context 구현은 이번에 하지 않는다.

## 28. Evaluation result와 future input

**작은 immutable BenefitAcceptanceEvaluation이 필요하다는 M2.41 결론을 유지**한다. stored decision과 현재 outcome은 다른 역할이다. usable은 typed reasons가 비었을 때 파생하는 방향이며 record status와 별도 USABLE/UNUSABLE Enum을 지금 추가할 필요는 없다.

향후 입력 방향은 current EligibilityCoverageResult, 동일 고정 PolicyEnvelope, current BenefitSnapshot, 외부에서 resolve/선택한 PolicyBenefitAcceptance 또는 None, 명시 SourceRegistry/DatasetManifest/data_use_date다. 기존 M2.41 API 후보의 경계를 유지하며 record model이 이 입력을 받지는 않는다.

최소 정상 사유는 기존 NO_ACCEPTANCE/ACCEPTANCE_REVOKED/ACCEPTANCE_NOT_YET_VALID/ACCEPTANCE_EXPIRED/COVERAGE_NOT_FULL/POLICY_NOT_VERIFIED/BENEFIT_METADATA_NOT_REVIEWED/COVERAGE_SNAPSHOT_CHANGED/BENEFIT_SNAPSHOT_CHANGED 계열이다. Benefit provenance 변경을 별도 reason으로 나눌지와 exact 결과 trace/serialization은 후속 result 설계에서 결정한다. 이번21필드에 reason을 넣거나 Enum을 구현하지 않는다.

개인 PASS·해당 월 적용·중복/병급·cadence/medium·합산은 Bridge/외부 정규화 책임이다. ACCEPTED이거나 평가 usable이어도 quarterly/local currency는 기존 Bridge에서 제외된다.

## 29. Current Ansan

실제 안산001/002는 기존 **DRAFT/CONDITION_SLICE**이며 실제 FULL CoverageResult·검토된 BenefitSnapshot/Acceptance가 없다. source VERIFIED·주민등록/출생일 PASS·generic core 완료로 이를 바꾸지 않는다. 실제 ACCEPTED/REVOKED record·ref·revision·artifact를 생성하지 않는다.

ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 공식 의미와 다른 조건/최종 목록·검토·자료 연결의 미완료를 유지한다. 실제 혜택 Cashflow 반영0원 원칙도 유지하며 없는 Bridge의 실행 결과라고 설명하지 않는다.

## 30. Synthetic examples

**문서상 합성 예시**이며 runtime 객체/승인 파일을 만들지 않는다. 아래 Coverage/Registry 지문은 형식 설명용 자리값이며 실제 계산/검토된 사실을 뜻하지 않는다. Benefit 지문은 기존 합성 BV01 literal을 참조할 수 있고 실제 안산 자료를 사용하지 않는다.

기준 A: acceptance_ref=SYNTH-ACCEPT-A1, acceptance_version=a0001, status=ACCEPTED, policy_id=SYNTH-POLICY, scope=2026/Q3, benefit_id=SYNTH-BENEFIT이다. Coverage binding은 i0001/Inventory fp=`1`64개, rule=r0001/Tree fp=`2`64개, dataset=SYNTH-D1/Registry fp=`3`64개/implementation fp=`4`64개로 가정한다. Benefit은 b0001/BV01 정의 지문/SYNTH-D1/동일 Registry를 가정한다. reviewed_at=2026-01-01, valid_until=2026-12-31, review_artifact_ref=SYNTH-REVIEW-A1, revokes_acceptance_ref=None이다.

이21필드는 구조적으로 유효하다. **가상 검토가 FULL/VERIFIED·fixed monthly cash·원본 binding·claim 검토까지 완료됐다는 추가 전제**가 있을 때만 승인 발급 예시가 된다. placeholder 지문만으로 실제 FULL/검토 성공을 만들지 않는다. 현재 usable은 여전히 future evaluator 책임이다.

B는 A의 target/binding을 그대로 두고 ref=SYNTH-ACCEPT-A2, version=a0002, status=REVOKED, reviewed_at=2026-10-22, valid_until=2026-12-31, artifact=SYNTH-REVIEW-A2, revokes_acceptance_ref=SYNTH-ACCEPT-A1인 새 철회 revision이다. A는 변하지 않는다. B의 metadata horizon 이후에도 A가 자동 복구되지 않는다.

현재 rule이 r0002/새 Tree면 A는 정상 역사 record이며 현재 unusable이다. 같은 r0001/다른 Tree면 Data Error다. 같은 target/b0001/다른 Benefit 지문도 Data Error다. current Coverage/Benefit이 함께 D2로 이동하고 Benefit 정의 지문이 같으면 A는 정상 provenance 변경으로 unusable이다.

## 31. 후속 구현 순서와 완료조건

| 순서 | 최소 작업 | 완료조건/검증 |
|---|---|---|
| M2.46 후보 | **PolicyBenefitAcceptance와 BenefitAcceptanceStatus만 구현** | 정확한21필드·2상태·strict 타입/grammar·날짜·MVP provenance equality·status/ref/self-link·frozen/equality·21key serializer 합성 unit tests |
| 다음 승인 단계 | Context/resolution 최소 계약 설계 | ref/revision 유일성·한 target 범위·철회 edge·명시 선택·이력 완전성 한계 확정 |
| 다음 승인 단계 | 승인한 bounded collection/resolution | 중복·broken ref·잘못된 revoke target/ordering·no latest selection 테스트 |
| 다음 승인 단계 | Acceptance evaluation result 설계/값 구현 | 현재 target/binding/date·typed reasons·trace·usable 파생 최소화 |
| 다음 승인 단계 | pure evaluator | current 구조/독립 guards·FULL/verification·Benefit completeness·provenance·선택/날짜 테스트 |
| 다음 승인 단계 | Bridge 정규화/합산 | 현재 수용 결과 결합·개인/월·유형·중복·무환산·Cashflow 경계 테스트 |

한 번에 다음 단계를 구현하지 않는다. 첫 모델은 Snapshot/지문/Context/result에 의존하지 않아 독립적으로 닫을 수 있다. 실제 발급·서비스 연결은 외부 근거/선택·실제 정책 FULL 등 요건까지 충족해야 한다. 새 generic framework/loader/DB/UI를 선행하지 않는다.

## 32. 수동 시나리오 — AR01~AR112

**112개 문서상 계약 사례이며 실행 테스트가 아니다.** 기본은30절 A다. C는 local constructor, R은 future resolution/이력 준비, E는 future current-usability 평가, B는 future Bridge를 뜻한다. “C 유효”는 검토/승인 진실성을 뜻하지 않는다. 정상 current 변경은 두 subsystem의 같은 release 결합을 함께 유지한다.

| ID | 사례 | 기대 |
|---|---|---|
| AR01 | exact 비공백 acceptance_ref | C 유효, 자동 생성 없음 |
| AR02 | a0001 | C 유효, 명시 revision |
| AR03 | exact ACCEPTED Enum | C 유효, 현재 usable은 별도 |
| AR04 | REVOKED+이전 ref·새 ref | C 유효, R 연결 검증 별도 |
| AR05 | canonical policy_id | C 통과 |
| AR06 | exact Q3 Scope | 원래 immutable 값 보존 |
| AR07 | canonical benefit_id | component target 보존 |
| AR08 | i0001 | Coverage version 문법 통과 |
| AR09 | Inventory fp lowercase hex64 | 형식만 통과 |
| AR10 | coverage_rule_version 비공백 str | C 통과, r grammar 추가 강제 안 함 |
| AR11 | Tree fp hex64 | 형식 통과 |
| AR12 | Coverage dataset=SYNTH-D1 | Benefit도 같은 D1이면 C 통과 |
| AR13 | Coverage Registry fp=G1 | Benefit도 같은 G1이면 C 통과 |
| AR14 | implementation fp 형식값 | C 통과, 실제 artifact 확인 아님 |
| AR15 | b0001 | Benefit version 통과 |
| AR16 | Benefit fp hex64 | 형식만 통과, 계산 없음 |
| AR17 | Benefit dataset=D1 | Coverage D1과 일치 요구 |
| AR18 | Benefit Registry=G1 | Coverage G1과 일치 요구 |
| AR19 | reviewed_at exact date | C 통과, 오늘 기본값 없음 |
| AR20 | valid_until exact date | C 통과, 무기한 기본값 없음 |
| AR21 | reviewed_at==valid_until | C 유효, 같은 날 사용 가능성 별도 |
| AR22 | reviewed_at>valid_until | C Data Error |
| AR23 | 비공백 artifact ref | C 유효, 파일 조회 없음 |
| AR24 | 빈/공백 artifact ref | C Data Error |
| AR25 | ACCEPTED+revokes=None | local invariant 통과 |
| AR26 | REVOKED+이전 승인 ref | local 통과, R에서 실제 A 확인 |
| AR27 | B 생성 후 과거 A | A 값/status 보존 |
| AR28 | 새 ref/a0002의 B | 새 결정 revision, A mutation 금지 |
| AR29 | A의 r0001 대비 current r0002 | A는 유효 역사 기록, E 정상 unusable |
| AR30 | A의 b0001 대비 current b0002 | 정상 정의 변경, 재승인 필요 |
| AR31 | A D1, current 양쪽 D2 | 정상 provenance 변경, fp 같아도 unusable |
| AR32 | current 새 dataset/Registry·정상 근거 갱신 | 정상 unusable, 자동 승계 금지 |
| AR33 | current implementation fp만 정상 교체 | 정상 snapshot 변경·unusable |
| AR34 | 같은 policy/scope/i version, 다른 Inventory fp | E Data Error |
| AR35 | 같은 policy/rule version, 다른 Tree fp | E Data Error |
| AR36 | 같은 policy/scope/benefit/b version, 다른 fp | E Data Error |
| AR37 | A·current exact·모든 gate 통과 | E usable 후보, B/개인 요건 별도 |
| AR38 | A의 valid_until 뒤 | 정상 expired unusable·A.status 유지 |
| AR39 | B가 현재 선택됨 | 정상 revoked unusable |
| AR40 | A/Q3와 current/Q3 | scope binding 통과 |
| AR41 | 정직한 A/Q3를 current/Q4와 비교 | 정상 scope 변경·unusable |
| AR42 | 정직한 A/Q3를 current annual과 비교 | 정상 범위 변경·unusable |
| AR43 | current release D2로 전환한 Coverage leg | Coverage dataset mismatch로 수용 재검토 |
| AR44 | 같은 전환의 Benefit leg, 정의 fp 동일 | Benefit provenance mismatch도 보존 |
| AR45 | 새 dataset에서 current Coverage/Benefit Registry G2 | 정상 재검토, 관련 binding 변화 별도 |
| AR46 | 같은 dataset에서 양쪽 Registry G2로 바뀜 | same-dataset 내용 모순 Data Error |
| AR47 | 구조만 정상인 가짜 ACCEPTED metadata | C 통과 가능, 실제 검토/발급 인증 아님 |
| AR48 | C 실행 | Coverage evaluator 호출 없음 |
| AR49 | C 실행 | Benefit 지문 계산 없음 |
| AR50 | C 실행 | Policy verification 조회 없음 |
| AR51 | C 실행 | Bridge 지원 판정 없음 |
| AR52 | C 실행 | Cashflow 계산/연결 없음 |
| AR53 | to_dict status | canonical ACCEPTED/REVOKED 문자열 |
| AR54 | to_dict scope | 새 edition_id/quarter dict |
| AR55 | to_dict 날짜 | ISO 문자열, datetime 절삭 없음 |
| AR56 | to_dict ACCEPTED revokes | 명시 null key 유지 |
| AR57 | 모든 필드 assignment/deletion 시도 | frozen 값은 거부 |
| AR58 | stored field 값이 같은 별개 record | equality 동일, current 날짜 영향 없음 |
| AR59 | 잘못된 policy ID·raw 숫자 | C Data Error |
| AR60 | 잘못된 benefit ID·자동 uppercase 요구 | C Data Error·보정 없음 |
| AR61 | a0000/b1/i00001 등 잘못된 version | C Data Error |
| AR62 | uppercase/짧은/긴/nonhex 지문 | C Data Error |
| AR63 | raw dict 또는 Scope subclass | C Data Error |
| AR64 | datetime/date subclass/ISO str 날짜 | C Data Error |
| AR65 | 외부 선택 record 없음 | 정상 E NO_ACCEPTANCE, 상태 member 아님 |
| AR66 | 단일 exact A를 명시 선택 | R 통과 가능, E gate 별도 |
| AR67 | 여러 정상 역사 version·자료 기록 | 후속 collection 공존 가능, 자동 선택 없음 |
| AR68 | 선택 ref=A의 정확한 ref | 해당 revision만 resolve |
| AR69 | 더 큰 version/최근 날짜가 함께 있음 | 명시 ref를 자동 대체하지 않음 |
| AR70 | 명시 data_use_date | E 날짜 입력, record 필드 아님 |
| AR71 | 실제 안산 SLICE | 실제 ACCEPTED 발급 금지 |
| AR72 | 실제 안산에 승인 원본 없음 | 가짜 A/B/ref/artifact 생성 금지 |
| AR73 | 실제 안산 Cashflow | 정책 반영0원 원칙 유지 |
| AR74 | 합성 A의21개 값 | 구조 유효, actual record 아님 |
| AR75 | 합성 B와 A를 함께 검토 | R에서 A 상태/target/binding·순서 확인 |
| AR76 | 합성 old rule A | 정상 역사 record·현재 재수용 필요 |
| AR77 | 합성 old Benefit A | 정상 역사 record·현재 재수용 필요 |
| AR78 | 합성 old dataset A | 정상 역사 record·정의 fp 같아도 현재 불가 |
| AR79 | 검토된 월 자유 현금·정확한 수용 | 개인/월 등 B 요건 후에만 합산 가능 |
| AR80 | 검토된 quarterly cash의 수용 | E usable 가능, B 비월 지급 제외0 |
| AR81 | 검토된 local currency의 수용 | E usable 가능, B 제한수단 제외0 |
| AR82 | current FULL | Coverage gate만 통과, 자동 ACCEPTED 없음 |
| AR83 | current 정상 SLICE·과거 A 있음 | E 정상 불가, old baseline 채우지 않음 |
| AR84 | 현재 Policy VERIFIED·근거 사용요건 충족 | verification gate만 통과 |
| AR85 | Policy DRAFT/STALE 또는 freshness 미충족 | E 정상 불가, FULL로 우회 안 함 |
| AR86 | current 유효 VARIABLE Benefit | 초기 발급/사용 차단, C 자체는 판정 안 함 |
| AR87 | current 유효 UNKNOWN Benefit | 초기 발급/사용 차단, 구조 오류와 구별 |
| AR88 | partial Benefit에 valid-looking A를 입력 | E의 completeness/binding guard 필요, 타입이 검토 인증 안 함 |
| AR89 | 같은 record 반복 serialization | 같은 값, 입력 변경 없음 |
| AR90 | 시스템 날짜 변경 | C 결과/equality 불변, E 명시 날짜만 사용 |
| AR91 | artifact가 파일처럼 보이는 ref | C가 filesystem 접근하지 않음 |
| AR92 | artifact가 URL처럼 보이는 ref | C가 network 접근하지 않음 |
| AR93 | 같은 acceptance_ref의 다른 내용 | 외부 이력/collection Data Error |
| AR94 | 같은 target/a version, 다른 ref/내용 | revision collision Data Error |
| AR95 | 재검토·기간 연장·새 승인 | 새 ref/version/artifact, old 불변 |
| AR96 | 다른 Benefit 계보의 record 연결 | wrong target Data Error |
| AR97 | 새로운 Q4 target 승인 필요 | Q3 revision 자동 승계 없음 |
| AR98 | 새 edition=2027 | 새 scope target·명시 재검토 |
| AR99 | FULL이라는 사실 | Acceptance/사용자 PASS/지급 확정과 다름 |
| AR100 | ACCEPTED라는 사실 | Bridge 유형/개인·월 적용 보장 아님 |
| AR101 | ACCEPTED+revokes ref 제공 | C local invariant 오류 |
| AR102 | REVOKED+revokes=None/blank | C local invariant 오류 |
| AR103 | REVOKED가 자기 ref를 지목 | C self-link 오류 |
| AR104 | B가 없는 ref/REVOKED/다른 target A를 지목 | R Data Error, 조용한 no-record로 처리 금지 |
| AR105 | B가 같은 target이나 다른 snapshot A를 지목 | R binding 오류 |
| AR106 | B.version<=A.version 또는 B.reviewed_at<A.reviewed_at | R 이력 오류, C는 상대 조회 안 함 |
| AR107 | B.valid_until이 지남 | 철회 지속, A 자동 복구 없음 |
| AR108 | A 만료 후 B를 검토/발급 | B 자체 날짜 순서 충족 시 가능, 옛 기한 자동 복사 금지 |
| AR109 | record의 Coverage/Benefit dataset 또는 Registry가 다름 | MVP local provenance Data Error |
| AR110 | current 양 subsystem provenance가 서로 다름 | E current 결합 Data Error, 정상 stale 아님 |
| AR111 | 만료/SLICE/REVOKED와 독립 같은-version fp 모순 동시 | 모순은 Data Error, 정상 사유로 은폐 금지 |
| AR112 | artifact에 읽을 수 있는 정의/claim 근거가 없음 | 실제 발급 검토 미완료, ref 문자열만으로 승인 금지 |

## 33. Coverage freeze 영향

영향 없음. EligibilityCoverageResult의8필드·파생 status·공식 evaluator·구조/결합·Review matching·지문 schemas/GV를 그대로 사용한다. Acceptance prefix 필드는 record 쪽의 명확한 snapshot binding 이름이며 Coverage의 필드 rename이 아니다.

현재 baseline과 과거 승인 binding의 비교는 외부 record/evaluator 계층에서 해결할 수 있다. Coverage Result에 추가 필드·승인 상태·날짜·사용자 facts를 넣거나 sentinel 경로를 우회할 이유가 없다. change-control 없이 frozen core를 수정하지 않는다.

## 34. Benefit Snapshot/지문 영향

영향 없음. Snapshot의16필드·4개 Enum·serializer·정의15key payload·BV01~BV16을 그대로 사용한다. dataset/Registry는 지문에서 제외되지만21필드 record의 provenance binding에 남는다. 관련 source bindings는 정의 지문과 불변 원본/artifact로 추적한다.

별도 accepted_terms runtime 모델/BenefitDefinitionReview·Snapshot review 필드/acceptance bool/property를 만들지 않는다. 기존 값/지문은 검토 대상이며 승인 record로 자동 변환하지 않는다.

## 35. 미해결 문제와 Assumptions

**Record의21개 필드·정확한 타입/순서·2개 status·revocation link·로컬 invariant는 이 문서에서 닫는다.** record 전에 별도 identity/revocation/Verification subsystem을 구현할 필요는 없다. 비교 상대/실제 자료가 필요한 검증은 명시적으로 후속 책임이다.

| 후속/한계 | 상태 |
|---|---|
| Context/resolution exact API와 컬렉션 검증 |27절 방향 확정, record 다음 별도 설계/승인 |
| Evaluation result/사유·trace·입력 연결 | M2.41 방향 유지, exact 모델/계산은 미구현 |
| 실제 artifact/Manifest/원문 검토·철회 선택 완전성 | 외부 자료 준비 책임, record가 인증하지 않음 |
| 기존 legacy full 자료 연결/verification freshness 실행·개인 월 적용 | 미구현, 모델 추가로 해소되지 않음 |
| actual Ansan | DRAFT/slice, 공식 거주기간/다른 조건·검토 blocker 유지 |

**Assumption A1:** 명시 선택/불변 이력과 실제 검토는 신뢰된 내부 자료 준비에서 공급한다. 외부 사용자/LLM의 선언으로 record 발급·현재 사용을 허용하지 않는다.

**Assumption A2:** 초기 실제 수용은 기존 fixed-only·유한 지급월 범위다. constructor에 completeness 계산을 넣지 않고 실제 발급/현재 평가가 확인한다.

동일 dataset/Registry 의무는 Assumption이 아니라 승인된 MVP 계약이다. 독립 release 결합은 이번에 허용하지 않는다. accepted_terms 보존 위치와 explicit acceptance_ref/revokes link의 보완은17절에 명시했으며 과거 문서를 조용히 수정하지 않는다.

## 36. 최종 판단과 검증 기록

**READY_TO_IMPLEMENT_BENEFIT_ACCEPTANCE_MODEL**

최소21개 stored fields와 BenefitAcceptanceStatus의2개 member, ref/revision 구분·명시 철회 대상·완전 binding·날짜/동일 provenance local invariant를 확정했다. 모델은 기존 Scope/오류/date만으로 구현할 수 있고 frozen Coverage/Snapshot/지문 변경이 필요 없다. 실제 current usability/검토 진실성은 별도 책임으로 남긴다.

다음 가장 작은 작업 한 개: **PolicyBenefitAcceptance와 BenefitAcceptanceStatus만 합성 unit tests로 구현**한다.21필드 reflection·Enum2개·exact 타입/grammar·날짜 경계·provenance equality·status/link/self-link·frozen/equality·21key mutation-isolated serializer를 검증한다. Context/result/evaluator/Bridge·실제 기록은 포함하지 않는다.

사전 전체 pytest: **6053 passed in 14.97s**. 문서 작성 후 전체 pytest: **6053 passed in 16.24s**. 신규 실행 테스트/기대값은 추가·변경하지 않으며 이 회귀가 아직 없는 Acceptance 구현을 검증한 것은 아니다.

문서36개 절·최종21개 stored fields의 순서/유일성·AR01~AR112의 연속/유일 ID·표 열 수·코드 블록·한국어 표기를 확인했다. 사전 actual releases/pycache 제외 backend/tests/data/docs154개 파일 SHA256 대조에서 **기존154개 전부 동일, 이 문서1개만 추가되어155개**이며 수정/삭제는 없다.

Coverage freeze/source·BenefitSnapshot/지문·GV01~GV15·BV01~BV16 literal 및 실행 테스트·나머지 기존 테스트/기대값·Cashflow·기존 모든 명세·ResidenceHistory 자료를 보존했다. 실제 release6개 파일의 경로/크기/수정시각도 모두 동일하다. 실제 Ansan Snapshot·지문·혜택 금액·Review/Acceptance·철회 기록은 생성하지 않았다.

## 37. M2.46 — IMPLEMENTED: 불변 Acceptance 결정 기록

`backend/policy_engine/policy_data/benefit_acceptance.py`에 **BenefitAcceptanceStatus(str, Enum)**와 **PolicyBenefitAcceptance**만 구현했다. 상태는 ACCEPTED/REVOKED 두 member이며 raw 문자열을 변환하지 않는다. public export에도 두 타입만 추가했다. alias·Context·평가 result·factory/sentinel은 없다.

14절의 정확한21개 필드·타입·순서를 사용한다. nullable revokes_acceptance_ref도 default 없는 keyword-only 필수 인자다. frozen=True/slots=True이며 equality/hash는21개 값 전체에 따른다. 기존 exact ApplicabilityScope 원본과 유효 문자열·날짜를 보존한다.

15절 순서대로 필드 exact 타입/문법을 검사한 뒤 날짜 순서 → dataset equality → Registry equality → status/link 조합 → self-link를 검사한다. canonical ID·i/b 버전·비공백 rule/dataset/ref·hex64는 기존 계약과 같다. 기존 Inventory/Benefit 모델에는 추출된 공용 버전 helper가 없으므로 동결 코드를 수정하지 않고 동일 문법을 작은 private helper로 적용했다. Envelope private validator의 별도 오류에 결합하거나 새 grammar를 만들지 않았다.

reviewed_at/valid_until은 required exact date이며 datetime/subclass/문자열/None을 거부하고 같은 날은 허용한다. Coverage/Benefit dataset과 Registry가 각각 같아야 한다. ACCEPTED에는 revokes=None, REVOKED에는 비공백 다른 ref를 요구한다. REVOKED의 valid_until도 구조 metadata이며 철회 효과 종료일로 계산하지 않는다.

잘못된 구조는 **INVALID_BENEFIT_ACCEPTANCE: field: reason**의 기존 PolicyDataError다. 입력 payload는 오류 문구에 넣지 않는다. 누락/extra/positional 인자 오용은 Python TypeError다. 일반 structural constructor 성공은 실제 검토·발급 권한·현재 사용 가능성의 증명이 아니다.

to_dict는 저장21key를 같은 순서로 반환한다. status.value·새 Scope dict·ISO 날짜·명시 nullable ref만 담는다. 현재 사용/만료/stale·근거 원문·검증 결과·월 환산액을 추가하지 않는다. 기록 간 조회·version 비교·지문 계산·Coverage 평가·verification·파일/네트워크·시스템 시각을 호출하지 않는다. unresolved 철회 ref와 과거 binding도 단일 record 차원에서는 유효할 수 있다.

신규 합성 `tests/test_benefit_acceptance.py` **472개**로 명세21필드 reflection/annotations/slots/필수성·Enum2개·exact 타입/grammar·6개 지문 형식·날짜/동일 provenance·status/link/self-link·오류 순서/비노출·전체 필드 equality·모든 필드 assignment/deletion 거부·명시21key serializer·nested mutation isolation·100회 결정성·외부 계산 부재를 검증했다. 실제 source/Snapshot/Acceptance는 생성하지 않았다.

검증: 사전 전체 **6053 passed in 16.02s**, 신규 **472 passed in 1.22s**, 최종 전체 **6525 passed in 15.91s**. 기존6053개 테스트·fixture·기대값은 수정하지 않았다. 기존 BenefitSnapshot292개·지문74개와 Coverage/GV01~GV15·BV01~BV16·Cashflow 회귀를 포함한다.

**IMPLEMENTED:** BenefitAcceptanceStatus·PolicyBenefitAcceptance·로컬 구조 검증·불변성/equality·21key serializer·합성 모델 tests.

**NOT IMPLEMENTED:** AcceptanceContext·ref resolution·철회 대상 존재/상태/target/binding/선후 검증·current usability·stale/expired 계산·AcceptanceEvaluation/result/evaluator·verification integration·Bridge·Cashflow 연결·실제 Acceptance 발급.

최종 판단: **READY_FOR_ACCEPTANCE_CONTEXT_DESIGN**. 다음 가장 작은 작업 한 개는 **한 target의 작은 불변 Context/명시 ref resolution 계약을 문서로 설계**하는 것이다. ref/revision 유일성·철회 edge·명시 선택·이력 완전성 한계를 확정하며 자동 최신 선택·evaluator 구현으로 진행하지 않는다.

Coverage core는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**, ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 실제 안산001/002는 DRAFT/CONDITION_SLICE와 정책 혜택 반영0원 원칙을 유지한다. 구조적으로 유효한 합성 ACCEPTED를 실제 승인이라고 설명하지 않는다.

### M2.46 최종 변경 범위

사전 actual releases/pycache 제외 backend/tests/data/docs155개 파일 SHA256 대조에서 **기존151개 동일, 수정4개·추가2개·삭제0개, 최종157개**를 확인했다. 수정은 public export와 이 명세·DATA_MODEL.md·ARCHITECTURE.md뿐이다. 기존 모든 테스트/fixture/기대값·BenefitSnapshot/지문 코드와 명세·Coverage frozen source/문서·GV/BV literal·Cashflow·ResidenceHistory 자료는 그대로다. 실제 release6개 파일은 경로/크기/수정시각이 모두 동일하다. 실제 정책 지문·혜택 금액·Acceptance/철회 기록은 만들지 않았다.

문서37개 절, DATA_MODEL34개 절, ARCHITECTURE50개 절의 연속 순서·코드 블록·한국어 표기를 확인했다.14절의21필드 표와 AR01~AR112의 유일/연속 ID를 보존했다. Context/resolution·현재 평가·실제 발급 검증은 이번 합성 모델 테스트가 검증한 기능으로 주장하지 않는다.
