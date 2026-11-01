# Benefit Acceptance Evaluator 입력·검증·원본 결합 계약 — M2.51

작성일: **2026-10-22 / Asia/Seoul**. **문서 설계만 수행**한다. 최종 판단: **NEEDS_RELEASE_VALIDATION_CONTRACT**.

이 문서의 함수·호출 경계는 후속 구현 계약이다. 현재 구현된 evaluator/adapter로 보고하지 않는다. 기존 코드·테스트·문서·실제 release는 수정하지 않는다. 새 Context/Result/검증 완료 bool·범용 검토 framework는 도입하지 않는다.

## 1. 목적과 계약 우선순위

평가 질문은 다음과 같다. **명시 선택한 Acceptance revision을, 현재 공급된 Coverage·Policy·Benefit·근거 확인본과 명시 사용일에서 시뮬레이션 사용 근거로 삼을 수 있는가?** 발급·조회·현재 사용 평가·개인별 금액 적용은 별개다.

우선순위는 Coverage 동결 계약 → 구현된 Snapshot/Acceptance/Context/Result 계약 → 이 문서의 호출 경계 구체화 → 과거 미구현 후보 설명이다. 저장21필드 record·4필드 Context·9필드 Result·12개 Reason·기존 지문 payload를 변경하지 않는다.

| 확인 자료 | 적용한 현재 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md 4~21·23·26·29절 | 요청 내부 결과, 명시 선택/철회/기한, 독립 guards, 실제 factory와237개 모델 tests |
| BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md 및 실제 Context/resolver | exact one-target 이력,14phase 구조 검사, 원문 ref 조회·원본 반환, 최대 한 직접 철회 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md 14~23·37절 |21필드, 불변 artifact의 accepted_terms/claim 대응표, 구조와 검토 진실성 분리 |
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md 6~9·15~22절 | FULL 필요조건, 현재 동일 release, Verification/Benefit/Bridge 분리 |
| BENEFIT_SNAPSHOT_SPEC.md 13~22·36~37절 및 실제 지문 함수 |16필드, 중복 evidence 보존/사용 시 거부, 정의15key와 provenance 분리 |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md / CASHFLOW_BENEFIT_BRIDGE_SPEC.md | 실제 발급 검토, 개인·대상 월·병급·유형·중복·합산의 후단 책임 |
| POLICY_DATA_ENVELOPE_SPEC.md 12~18·26·28·30~31절 | 메모리/bytes 지문 구별, 전체 Manifest 집합, source 사용/검토/release 의무, 미구현 freshness |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md 36~37절 / ELIGIBILITY_COVERAGE_CORE_FREEZE.md | 공식 평가1회, 원본 대응,8필드/파생 status, 지문·오류·외부 신뢰 동결 |
| DATA_MODEL.md 33~36절 / ARCHITECTURE.md 49~52절 | 현재 구현과 미구현 경계 |
| 실제 policy_data·sources 코드 | 아래 표의 실제 이름·필드·검사 범위 확인. 후보 함수를 구현된 API로 취급하지 않음 |

사전 전체 pytest는 **6962 passed in 17.75s**다. 기존 파일164개와 실제 release6개의 SHA256 기준선을 확보했다. 문서 수동 사례와 실행 회귀를 구분한다.

## 2. 실제 검증 능력 현황

책임 A=자료 준비·외부 검증, B=순수 Acceptance 계산, C=같은 호출 결합이다. 아래의 미구현은 성공했다고 가정하지 않는다.

| 검증 항목 | 현재 타입·함수 | 실제 보장 | 없는 보장 | 책임 |
|---|---|---|---|---|
| Coverage FULL | evaluate_eligibility_coverage / EligibilityCoverageResult.status | 고정 scope에서 M/U/G·Review matching·baseline 완결성 | 공식 의미·실제 검토 진실성·Policy VERIFIED | 기존 Coverage, A |
| Result 대 현재 Policy | 공식 evaluator와 내부 factory | 같은 호출의 Inventory/Policy/Context/findings 결합 | 다른 호출의 Result를 임의 Policy에 붙인 것을 자동 인증 | C에서 공식 producer 고정 |
| Benefit 정의 지문 | fingerprint_benefit_snapshot | exact Snapshot 정의15key의 결정적 지문 | dataset/전체 Registry·검토·원문 bytes | B, 기존 helper |
| Coverage/Benefit 동일 release | 개별 모델의 provenance 필드 | 각 값의 문법, Acceptance 내부 두 dataset/Registry equality | 현재 Result/Envelope/Benefit/Manifest/Registry 전체 대조 | B/C, 미구현 |
| Envelope Verification | PolicyEnvelope.verification_status / PolicyVerificationStatus | DRAFT/VERIFIED/STALE 선언, VERIFIED 확인일 필수 | 실제 review 수행·FULL·freshness | A, B gate 미구현 |
| source ref/version/locator | parse_evidence_ref, validate_evidence_refs, validate_envelope_sources | 문법·존재·중복·leaf 버전/policy·파생 확인일 | Benefit의 실제 binding/policy 대조·검토·사용일 | 기존 validator + B |
| source 수명 | SourceRegistry.resolve | 사용 source/locator의 ACTIVE, 비참조 상태는 오류 | ACTIVE가 VERIFIED/최신/공식 검토라는 보장 | 기존 Registry, A |
| 확인일/freshness | SourceDocument/SourceEvidence, Manifest N | exact 날짜/구조, N 양의 int 보존 | 사용일 기준 날짜 구간 검사 | B gate 미구현 |
| Manifest 정책 전체 집합 | validate_dataset_manifest | 전체 Envelope/Registry 집합·버전·도메인 지문·rule ID 유일성·ENGINE_VERSION 호환 | 실제 파일 bytes·검토·현재 실행물 | A/C에서 기존 함수1회 |
| 파일 bytes/hash | ArtifactReference, SourceDocument.content_sha256 | hash/path 형식과 선언 보존 | 실제 읽은 bytes와 일치, bytes로부터 현재 객체 생성 | A, 연결 미구현 |
| 실행물/implementation 지문 | CoverageReviewContext.implementation_fingerprint, Manifest.engine_artifact_sha256 | 각각 hex64 보존, Coverage의 supplied baseline 비교 | 두 artifact의 구성·대응 및 실제 실행한 artifact 일치 | **A의 선행 계약 공백** |
| 검토 artifact | PolicyBenefitAcceptance.review_artifact_ref, Manifest.review_manifest | opaque ref 또는 파일 참조의 로컬 구조 | 존재·본문·accepted_terms·claim·snapshot 대응 | A의 준비/내용 대조, 구조화 API 없음 |
| 명시 Acceptance 조회 | _resolve_benefit_acceptance | exact ref로 supplied Context의 원본 반환 | 최신 선택·현재 사용 승인 | 기존 resolver, B가 재사용 |
| 직접 철회 | BenefitAcceptanceContext | 대상 ACCEPTED·동일11 binding·후행 revision/date·최대1개 | 선택 A에 알려진 B를 적용하는 계산·누락 이력 탐지 | B 검색 미구현 / 완전성 A |
| 기한 | record의 reviewed_at/valid_until | 로컬 날짜 순서 | 사용일의 포함 구간 비교 | B 미구현 |
| 과거 대 현재 | record binding + Result.findings/Benefit 지문 | 비교할 값 존재, current baseline all-None 허용 | 독립 same-version guards·정상 변경 사유 계산 | B 미구현 |
| 최종 결과 | _create_benefit_acceptance_evaluation |9필드 구조·사유/선택/철회 조합, 파생 status | 위 검사가 실제 수행됐다는 인증 | 기존 factory, B가 마지막1회 |

Manifest 생성 성공, hex64 문법, ref 문자열, private token은 각각 구조 장치다. 파일·실행물·실제 검토를 인증하는 증거로 승격하지 않는다.

## 3. 세 책임과 서비스 진입 제한

**A 자료 준비:** 명시 release를 선택하고 실제 bytes를 확보한다. 동일 bytes로 로드한 전체 Envelope/Registry, 검토 원본, 실제 실행 artifact, 현재 Acceptance 이력을 고정한다. 공식성·검토자 독립성/권한·검토 수행·이력 누락/overwrite 여부는 외부 검토 책임이다. 사용자의 경제정보나 LLM 선언을 검토 증거로 받지 않는다.

**B 순수 evaluator:** 공급된 불변 현재 값의 target/release·source 사용요건, 명시 선택·알려진 철회·기한, 과거/current guards,12개 사유와 기존 결과를 계산한다. 파일·네트워크·시스템 시각·환경·Git·DB·난수·전역 캐시를 읽지 않는다. Acceptance를 새로 발급하지 않는다.

**C 같은 호출 adapter:** A가 확보한 원본을 고정하고 전체 메모리 검증과 Coverage 공식 producer를 연결한다. B 호출 뒤 같은 Benefit 원본으로 후속 candidate를 구성한다. 외부의 precomputed Result/serialized status를 받는 인자는 없다.

현재 A의 실행물 대응 및 검토 artifact 대조 API, B, C는 **미구현**이다. 아래 내부 API만 먼저 만들어 외부에서 직접 호출하게 열면 A/C를 우회하므로 서비스 연결로 승인하지 않는다. 정상 결과를 만들 수 있다는 사실만으로 이 전제가 집행됐다고 보고하지 않는다.

## 4. 정확한 순수 내부 API와 제외한 입력

후속 B의 **내부 keyword-only 함수** 계약을 다음8개 인자로 고정한다. 모든 인자는 필수이며 nullable도 명시한다. 이름 앞 underscore는 신뢰 경계를 암호학적으로 강제하지 않는다. package public export/외부 endpoint로 제공하지 않는다.

```python
_evaluate_benefit_acceptance(
    *,
    coverage_result: EligibilityCoverageResult,
    envelope: PolicyEnvelope,
    benefit: BenefitSnapshot,
    acceptance_context: BenefitAcceptanceContext | None,
    acceptance_ref: str | None,
    manifest: DatasetManifest,
    registry: SourceRegistry,
    data_use_date: date,
) -> BenefitAcceptanceEvaluation
```

**이8개는 순수 계산 입력의 확정이며, 완성된 서비스 입력 계약이 아니다.** 실제 bytes/검토 사실을8개에서 복원할 수 없다. A/C의 검증을 호출 구조로 집행하기 전에는 안전한 production 진입 API가 성립하지 않는다. 그 공백을 새 verified DTO나 생략된 기본값으로 감추지 않는다.

| 입력 | 타입/필수성 | 원천 | 없으면 못 하는 검사 | 중복 여부·기계/외부 책임 |
|---|---|---|---|---|
| coverage_result | exact EligibilityCoverageResult, 필수 | C가 현재 Coverage·envelope.policy·CoverageReviewContext로 공식 evaluator1회 실행한 원본 | FULL·scope/i/r/Inventory/Tree·현재 baseline | 전체 Coverage 재전달 없음. 생성 경로 C, 대응/사용 B |
| envelope | exact PolicyEnvelope, 필수 | 고정 전체 release의 선택 구성원 원본 | policy/rule/tree 소속·edition/dataset·검토 상태·leaf 근거 | Policy 별도 전달 불필요. bytes/실제 review A |
| benefit | exact BenefitSnapshot, 필수 | 명시 현재 정의 원본, A가 보존한 확인본 | benefit target/정의/근거/provenance | 정의 지문 인자 없음. B가 기존 helper로 계산 |
| acceptance_context | exact Context 또는 None, 필수 | A가 현재 공급한 한 target 이력 | 세 선택 부재 상태·원본 조회·incoming B | None은 정상. supplied 이력 구조는 기존 모델, 완전성 A |
| acceptance_ref | exact 비공백 str 또는 None, 필수 | 호출자가 명시 선택한 원문 | revision 하나 선택 | Context에 저장하지 않음. 자동 latest 없음 |
| manifest | exact DatasetManifest, 필수 | A/C가 선택한 전체 release의 동일 객체 | 현재 dataset/Registry 대응·명시 N | 전체 검증 C, B는 그 선택 구성원 검사 |
| registry | exact SourceRegistry, 필수 | A/C가 동일 bytes에서 로드한 전체 Registry | source/version/locator/policy·수명·검토/확인일 | hash 문자열만 받지 않음. 공식 원문 진실성 A |
| data_use_date | exact datetime.date, 필수 | 명시 호출 기준일 | 선택 기한·freshness | datetime/subclass/str/None 거부. 오늘 기본값 없음 |

별도 policy_id/scope/benefit_id·current hash·status·usable·freshness N·selected record는 받지 않는다. 각각 기존 원본에서 얻거나 실제 helper/명시 resolver로 계산한다. current Inventory와 CoverageReviewContext는 C가 소유하고 B에 다시 넘기지 않는다.

전체 envelopes·파일 bytes·검토 artifact 본문은 A/C 검증의 원재료이지 B의 거대한 추가 인자 목록으로 만들지 않는다. 단, 현재 이 원재료를 받는 완료된 A/C API가 **없다**. 그 연결이 누락된 채8개만 외부에서 공급하는 경로는 금지하며,25절에서 구현 승인을 보류한다.

## 5. Coverage 원본 대응 — A 선택

| 대안 | 실제 필요 입력·보장 | 판단 |
|---|---|---|
| A 같은 상위 호출에서 공식 Coverage 결과 생성 | 원본 EligibilityCoverage·그 inventory.scope·CoverageReviewContext·동일 envelope.policy를 C가 고정. 공식 평가1회가 Inventory/Tree/finding 대응을 보장 | **채택** |
| B 임의 기존 Result를 현재 원본과 재대조 | Result만으로 실제 Inventory/Bindings/Review 원본 전체를 재검증할 수 없음. 별도 원본 전달·지문/대응 검사와 재사용 경계가 추가됨 | 미채택 |

C는 `evaluate_eligibility_coverage(coverage, envelope.policy, coverage_review_context)`를 정확히1회 호출해 그 반환 객체를 B로 보낸다. B는 Coverage evaluator·private Gate/factory/token을 호출하지 않는다. 파일의 예전 Result/JSON을 역직렬화해 끼우는 overload는 없다.

현재 inventory_version/Inventory fp는 각각 현재 Inventory와 공식 결과 findings에서 온다. rule_version/Tree fp는 같은 envelope.policy로 공식 경로가 계산한 값이다. dataset/Registry/implementation은 현재 CoverageReviewContext 또는 모두 None에서 왔음을 producer가 보장한다. C가 다른 Policy로 계산한 Result를 받는 인자 자체를 두지 않는다. B의 값 대조는 여전히 수행한다.

**scope 근거는 current Coverage.inventory.scope이며 Benefit.scope와 value equality를 요구**한다. Envelope에는 edition_id만 있으므로 연도 일치는 Q3 증명이 아니다. 같은 연도라도 inventory.scope가 Q3와 다르면 오류다. 현재 scope 근거/Inventory가 없는 입력은 producer를 실행할 수 없어 준비 미완료이며, policy명·경로·사용일로 추론하지 않는다. Q3 Inventory와 공식 원문의 의미 대응은 실제 Review 책임이다.

legacy Envelope.evaluation_scope=CONDITION_SLICE, 비어 있지 않은 excluded_conditions는 그대로다. 이를 FULL로 고치거나 새 Generic Result를 그 Enum에 캐스팅하지 않는다. Generic FULL과 실제 full release metadata의 수용 연결은 **별도 미완료**다. 합성 연동 설계가 실제 Envelope의 제한을 해소한 것으로 보고하지 않는다.

## 6. 전체 release 검증과 선택 구성원 검사

**전체 메모리 검증은 C에서 release 원본 고정 후, B 호출 전에 한 번 실행**한다.

```text
validate_dataset_manifest(manifest, all_envelopes, registry)
```

all_envelopes는 exact tuple이고 Manifest.policy_versions의 **전체 정책 ID 집합**과 정확히 같아야 한다. 선택 정책 한 개만 추려 전체 검증을 대체하지 않는다. 해당 함수는 현재 ENGINE_VERSION 호환 → 전체 정책 중복/집합 → 전체 source ID/version 집합 → 실제 Registry domain fp → Manifest 순서의 각 Envelope dataset/reference 필드 → validate_envelope_sources → Envelope domain fp → 전역 rule ID 순서로 검사한다. 내부 순서·오류를 바꾸거나 catch하지 않는다.

Registry에는 Benefit 전용 source도 포함될 수 있다. Manifest.source_versions는 Registry **전체**와 같아야 하지만 선택 Envelope.bindings는 그 leaf source만 포함한다. 전체 release가 정책/혜택 근거 합집합보다 더 큰 것은 정상이다.

B의 선택 대상 검사는 아래7절이다. C는 `all_envelopes`에서 명시 policy_id로 찾은 **원본 객체**를 envelope로 전달한다. 동등한 복제품으로 교체·latest 재조회·중간 파일 재로드를 하지 않는다. Manifest 객체/전체 tuple/Registry 고정 뒤 관련 원본 변경 시 처음부터 새 호출이다.

| 범위 | 검사하는 것 | 현재 구현/한계 |
|---|---|---|
| 전체 도메인 | 전체 정책/출처 집합, 버전·내용 지문·기존 ref 무결성 | 기존 함수 있음. 파일 bytes/운영 사용 gate 아님 |
| 전체 bytes | 각 policy artifact, Registry artifact, 선언된 review artifact의 실제 bytes SHA256, 그 bytes에서 현재 객체 생성 | A/C 연결 미구현. Manifest.review_manifest=None은 domain-valid이나 실제 검토 완료가 아님 |
| 원문 bytes | 사용 SourceDocument.content_sha256가 있으면 그 원문 bytes와 대조. 없으면 bytes 확인 완료 주장 불가 | 공식성/원문 보존 A. optional을 임의 가짜 hash로 채우지 않음 |
| 실행 artifact | 실제 사용 엔진/입력·evaluator artifact와 각각 선언 지문의 대응 |25절 선행 계약 공백. ENGINE_VERSION equality가 대체하지 못함 |
| 선택 대상 | 현재 Coverage/Envelope/Benefit가 이 전체 release의 정확한 원본과 결합 | B/C. 과거 Acceptance를 현재 release로 강제 수정하지 않음 |

파일은 한 번 확보한 bytes를 해시하고 **같은 bytes를 parse**해야 한다. hash 후 같은 경로를 다시 열어 다른 내용을 로드하는 방식은 원본 결합을 보장하지 못한다. 상대 경로 형식 검증과 실제 release 경로 밖으로 벗어나지 않는지 확인은 별개다. 파일/parse 실패는 A/C 준비 실패이고 부분 evaluator 결과를 만들지 않는다. Manifest JSON loader·실행물 검사·review loader는 현재 없다.

freshness로 전체 production release를 차단하는 M1.9 운영 preflight와, 선택 대상의 정상 미충족 사유를 계산하는 B는 별도다. 전체 domain validator가 모든 정책의 운영 freshness까지 통과시킨다고 하지 않는다. 이 문서로 기존 전체 release REJECT 정책을 해제하지 않는다.

## 7. 현재 identity·same-release 대조

B에서 필드 순서는 다음 표 순서다. C의 동일 호출 producer가 전제되며, 값만 같은 외부 Result를 허용하는 대체 계약이 아니다.

| 순서/축 | 의무 | 실패 |
|---|---|---|
| policy | coverage_result.policy_id == benefit.policy_id == envelope.policy_id | ACCEPTANCE_CURRENT_INPUT_MISMATCH |
| scope/edition | coverage_result.scope == benefit.scope, envelope.edition_id == benefit.scope.edition_id | 같은 오류. 연도만으로 quarter 검증하지 않음 |
| rule | coverage_result.rule_version == envelope.rule_version | 같은 오류 |
| Context target | 제공되면 policy_id → scope → benefit_id가 현재 Benefit target과 동일 | ACCEPTANCE_CONTEXT_TARGET_MISMATCH. ref=None도 검사 |
| 현재 dataset | benefit.dataset_version == envelope.dataset_version == manifest.dataset_version | ACCEPTANCE_CURRENT_INPUT_MISMATCH |
| 현재 Registry | benefit.source_registry_fingerprint == 검증된 manifest.source_registry.fingerprint | 같은 오류. C에서 실제 Registry fp를 계산해 대조한 원본만 허용 |
| Coverage present baseline | dataset/Registry가 위 current 값과 각각 동일 | 같은 오류. 세 baseline all-None이면 두 축 검사만 생략 |
| 현재 Tree | 같은 C 호출에서 envelope.policy를 producer에 전달하고 그 findings를 그대로 B에 전달 | C 원본 전달 의무. 별도 Tree hash 재계산/임의 Result 반입 없음 |
| source binding | Envelope/Benefit의 같은 source ID는 같은 d version이고 해당 Registry/Manifest와 동일 | 기존 Envelope 오류 또는 Benefit source 오류, 정상 stale 아님 |

same-release 검사는 current 자료끼리의 검사다. 과거 D1의 A와 정상 current D2가 다르면18절 정상 변경을 판단한다. 역사 Context 전체를 D2로 맞추거나 D1 records를 버리지 않는다.

Coverage implementation_fingerprint와 Manifest.engine_artifact_sha256은 **그대로 equality를 강제하지 않는다**. 앞 값은 input/evaluator artifact, 뒤 값은 엔진 배포물/빌드의 bytes 지문이다. 포함 관계/동일 artifact 여부가 명시돼 실제 bytes 및 실행과 대응해야 한다. 둘 다 hex64라는 이유로 같게 채우는 것은 검사 우회다.

## 8. source 구조 검사와 사용 gate

정책 근거는 `walk_nodes(envelope.root)`의 기존 pre-order leaf/evidence 순서, Benefit 근거는 원래 benefit_evidence_refs 순서를 사용한다. source 사용 gate는 **정책 묶음 → 혜택 묶음** 순서다. 모두 같은 Registry/Manifest/data_use_date를 쓴다.

| 항목 | 기계 검사/재사용 | 실패 분류 |
|---|---|---|
| ref 문법 | 기존 parse_evidence_ref, canonical SOURCE-ID#locator | 기존 SourceValidationError, 구조 오류 |
| source/locator 존재·수명 | 기존 validate_evidence_refs → registry.resolve | SOURCE_NOT_FOUND/LOCATOR_NOT_FOUND/SOURCE_NOT_REFERENCEABLE/EVIDENCE_NOT_REFERENCEABLE 그대로 오류 |
| 중복 ref | Benefit 원래 tuple에 validate_evidence_refs1회, dedupe 금지 | DUPLICATE_EVIDENCE_REF. Snapshot 생성/지문 가능과 사용 허용을 구별 |
| 정책 leaf version/policy/확인일 | 전체 validator 안 기존 validate_envelope_sources | SOURCE_VERSION_MISMATCH/POLICY_EVIDENCE_MISMATCH/LAST_VERIFIED_DATE_MISMATCH 등 전파 |
| Benefit binding version | binding tuple 순서로 Registry.get_source 및 전체 Manifest 고정 version 대조 | 후속 Benefit gate의 SOURCE_VERSION_MISMATCH: source_bindings, PolicyDataError |
| Benefit 적용 policy | validate_evidence_refs 반환 순서로 applicable_policy_ids 검사 | 후속 Benefit gate의 POLICY_EVIDENCE_MISMATCH: applicable_policy_ids, PolicyDataError |
| 관련 source 집합 | Envelope leaf 집합은 기존 생성자, Benefit ref 집합은 기존 생성자. 둘의 합집합은 review 원본과 대조 | 구조 오류 또는 artifact 대응 오류. Benefit 전용 source를 Envelope에 추가하지 않음 |
| document/locator 검토 상태 | 각각 VerificationStatus.VERIFIED인지 | ACTIVE지만 DRAFT/STALE이면 정책 reason8 / 혜택 reason9 |
| document/locator 확인일 | 명시 사용일·Manifest N으로 각 날짜 검사 | 유효 구조의 None/미래/기한 밖은 해당 reason8/9 |
| Envelope 검토 | PolicyVerificationStatus.VERIFIED와 last_verified_at 사용요건 | DRAFT/STALE 또는 정상 freshness 실패는 reason8 |
| 공식 원문·실제 검토·이력 누락 | 실제 확보 원문/검토 artifact 및 외부 확인 | 외부 검증 미완료. reason을 지어내어 사용 완료로 낮추지 않음 |

Benefit gate의 두 prefix는 **후속 구현 계약**이며 현재 Benefit validator가 존재한다는 뜻이 아니다. 기존 SourceValidationError/EnvelopeValidationError/ManifestValidationError는 PolicyDataError 하위다. 기존 예외는 원래 객체로 전파하고, 새 hierarchy나 ERROR reason을 추가하지 않는다. 누락/상충 source 집합은 정상 생성자에서 먼저 거부되므로 강제 훼손 fixture를 만들지 않는다.

정책 source refs와 Benefit refs 사이에 같은 ref가 공통으로 쓰이는 것은 정상이다. 중복 제한은 각 leaf의 ref tuple 및 Benefit ref tuple 내부에 적용한다. 전체 정책의 모든 leaf refs를 flatten한 tuple에 중복 검사를 새로 적용해 정상 공통 근거를 거부하지 않는다.

## 9. freshness·날짜·정상 미완료의 의미

N은 **manifest.freshness_max_age_days**다. 과거7일 제안은 자동 default가 아니며 현재 모델은 N을 보존할 뿐 실행하지 않는다. B는 각 필요한 verified_at에 `0 <= (data_use_date - verified_at).days <= N`을 적용한다. 이는 `[verified_at, verified_at+N일]` 포함 구간과 같고 date.max의 덧셈 overflow도 피한다.

문서와 사용 locator를 **각각** 검사한다. 더 최근 문서 확인일로 오래된 locator를 덮지 않는다. Envelope.last_verified_at은 leaf locator 최솟값/None이라는 기존 구조 대조를 먼저 통과해야 한다. source VERIFIED인데 확인일 None, locator 확인일이 문서보다 늦음, Envelope 파생 확인일 모순은 기존 생성자/validator의 Data Error다. 정상 DRAFT/STALE의 None이나 사용일보다 미래인 확인일은 사용 gate 미충족이다.

publication_date=None은 단독 실패가 아니다. lifecycle ACTIVE·검토 VERIFIED·freshness는 별개다. effective_from/to, application period, target_month, 사용자 신청일은 data_use_date와 자동 동일시하지 않는다. ENDED/효력일 metadata로 Acceptance reason을 새로 만들지 않는다. 정책 운영 활성화·효력 범위는 전체 release/정책별 수용 검토가 먼저 다뤄야 하며, B의 USABLE이 현재 접수 중임을 보증하지 않는다.

Benefit 초기 completeness는 **FIXED + cadence/medium/restriction 각각 UNKNOWN 아님 + applicable_months가 알려진 유한 tuple**이다. VARIABLE/UNKNOWN/미완료는 reason9다. 금액0은 정상 고정액이다. QUARTERLY/LOCAL_CURRENCY 자체는 이 gate의 실패가 아니다.

## 10. Verification 저장 위치와 artifact의 세 수준

| 수준 | 저장/입력 위치 | 실제 검사/한계 |
|---|---|---|
| ref 구조 | Acceptance.review_artifact_ref, Manifest.review_manifest | 비공백 ref/ArtifactReference 형식. 파일 존재 보장 없음 |
| 실제 확보 | A가 확보한 immutable review bytes와 ref의 명시 대응 | 존재/bytes hash/동일 bytes parse는 외부 준비. URL/path처럼 보인다고 자동 파일 조회하지 않음 |
| 내용 대응 | artifact의 결정 identity·역사 원본·Coverage/Benefit/claim·provenance | 정확한 대상에 대한 검토인지 별도 대조 필요. 현재 구조화 모델/API 없음 |

PolicyEnvelope.verification_status는 Envelope 도메인 지문에 포함된 확인본 metadata다. Manifest가 그 Envelope 지문을 고정하므로 다른 bytes/상태로 교체하면 전체 대조에 걸려야 한다. source 문서/locator 검토 상태도 Registry domain fp에 포함된다. 그 값들이 실제 사람의 검토 행위를 인증하지는 않는다.

## 11. 검토 artifact의 필수 내용과 구조화 전달 공백

현재21필드 record에는 accepted_terms가 없다. M2.45 17절에 따라 다음은 **불변 artifact 쪽의 의무**다. 별도 BenefitDefinitionReview 모델을 자동 신설하지 않는다.

| 필수 자료 | 원본 대조 | 책임/현재 상태 |
|---|---|---|
| 결정 ref/version/status·target·reviewed_at/valid_until·revokes | 해당 원본 PolicyBenefitAcceptance와 equality | A의 준비/내용 대조. 현재 opaque ref만 있음 |
| 준비자/별도 검토자 handle, 검토일·사유·수동 사례 | 실제 보존 자료, 두 handle 구분·필요 항목 존재 | 구조 검사는 가능해도 실재/권한·충분한 검토는 외부 진실성 |
| Coverage9 binding과 원래 Review refs/자료 | 승인 당시 원본 Inventory/Policy/CoverageReviewContext·결과 참조 | 저장 binding과 실제 역사 원본 대조, 해시 문자열끼리 일치만으로 대체 불가 |
| readable accepted_terms | 정확한 당시16key BenefitSnapshot 또는 그 불변 원본을 복원 | 기존 Snapshot 생성/serializer/지문 재사용. hash만 남기기 금지 |
| claim별 근거 | amount/cadence/medium/restriction/applicable_months 각각 비어 있지 않은 refs 부분목록 | 당시 Snapshot.benefit_evidence_refs에 속하는지·모든5claim 존재 확인, 의미 충족은 검토자 |
| 정책+혜택 source bindings 합집합 | 당시 Envelope.bindings ∪ 당시 Snapshot.bindings, 같은 source ID의 version 모순 거부 | 정확한 당시 Registry/Manifest 및 공식 원문·locator와 대조 |
| 당시 provenance | dataset/Registry·Manifest/Envelope·엔진/구현 artifact 참조 | 원본 확인본 복원, 실제 bytes/실행 대응 A |

**이 표는 필요한 사실의 목록이며 구현된 ArtifactBinding 타입 선언이 아니다.** B가 artifact 파일을 열지 않으므로 A/C에서 실제 내용을 읽고 위 원본들과 대조한 뒤 호출해야 한다. 필요한 구조화 입력은 결정 원본, 당시 Snapshot, Coverage/Review/Manifest/Registry 원본의 불변 참조,5claim 매핑, 준비/검토 metadata다. 어느 것도 현재 record의 ref 문자열로 대체할 수 없다.

현재 이 자료를 strict parse하고 원본과 결합하는 callable이 없다. A/C의 future 준비 단계에 **artifact 확보 → 같은 bytes 해시/parse → 위 내용 대응 → B 진입**을 강제하는 경로가 필요하다. 이를 아직 없는 `ReviewArtifact` 인자가 이미 존재한다고 쓰거나 `verified=True`로 축약하지 않는다. 정확한 구조화 표현/loader 계약은 남은 의존사항이다. 이 미완료 때문에8인자 내부 API만의 구현을 완성된 검증으로 승인하지 않는다.

과거 A의 artifact는 **A의 역사 Snapshot**과 먼저 대조한다. 정상 current B2를 A의 accepted_terms와 직접 비교해 구조 오류로 만들면 정상 새 version 의미를 깨뜨린다. 과거 원본이 A의 저장 지문과 다르면 artifact 대응/불변성 오류, 과거 원본은 정확하고 current version이 바뀌었으면18절 정상 사용 불가다. 철회 B artifact도 B 자신의 결정과 A의 동일 binding 원본을 가리켜야 한다.

실제 artifact가 없거나 아직 확보하지 못한 상태는 **외부 검증 미완료**다. 다른 ref/target/원본을 가리키는 확보 artifact는 **대응 Data Error**다. 검토 중이라 record가 없는 것은 정상 no-selection/Benefit incomplete 경로와 구별한다. artifact 미확보를 기존 reason9 하나로 감추어 “필수 전제 검증이 끝난 정상 결과”를 만들지 않는다. 새 Error prefix/구조화 타입은 이 선행 계약 없이 발명하지 않는다.

## 12. 동일 호출 검증 경계와 재료 소유

C의 외부 입력은 현재 **원본**과 명시 선택뿐이어야 한다. 개념상 필요한 재료는 전체 release 자료, 현재 EligibilityCoverage/ReviewContext, 현재 Benefit, AcceptanceContext/ref, 명시 사용일이다. 별도 Result/current hash/검토 성공 bool은 외부 입력이 아니다. 파일/원문/실행·검토 artifact의 정확한 공급 형식은25절 미완료이며 완성된 public adapter signature를 임의 선언하지 않는다.

```text
한 trusted 호출
  A: 명시 원본 bytes 확보·불변 보존·실행/검토 대응 확인
  C: 같은 bytes의 전체 Envelope/Registry 고정
     → validate_dataset_manifest(manifest, all_envelopes, registry) 1회
     → 명시 current Envelope 원본 선택
     → current Coverage/ReviewContext와 원본 envelope.policy 고정
     → evaluate_eligibility_coverage(...) 1회
     → 내부 B에 그 결과·동일 Envelope/Benefit/Context/ref/Manifest/Registry/date 전달
     → B 정상 반환 뒤 같은 Benefit 원본으로 candidate 구성
  후속 Bridge: 별도 개인·월·중복·유형 검증/합산
```

이 흐름이 실제로 구현/검증되기 전에는 외부 함수가8개 객체를 넣고 USABLE을 얻는 서비스 경로를 제공하지 않는다. C는 검증 완료 플래그를 외부에서 신뢰하는 wrapper가 아니라 필요한 검증 함수를 자기 호출 안에서 실행하는 경계여야 한다. A의 사람 검토·누락 이력 완전성은 C도 로컬 계산만으로 인증할 수 없다는 한계는 남는다.

## 13. selection·resolution의 고정 의미

현재 type/target/release/source 정합성을 통과한 뒤 선택을 처리한다.

| Context / 명시 ref | 실행 | 결과/오류 |
|---|---|---|
| None / None | resolver0회 | NO_ACCEPTANCE_CONTEXT |
| empty / None | resolver0회 | NO_ACCEPTANCE_RECORDS |
| nonempty / None | resolver0회 | ACCEPTANCE_NOT_SELECTED |
| None / exact 비공백 str | 조회 불가능 | ACCEPTANCE_CONTEXT_REQUIRED Data Error |
| empty 또는 nonempty / 없는 ref | 기존 resolver1회 | ACCEPTANCE_REF_NOT_FOUND 그대로 |
| nonempty / 있는 ref | 기존 resolver1회, 원본 반환 | 그 원본 revision만 평가 |
| 다른 target Context / None 포함 | 먼저 Context target 검사 | ACCEPTANCE_CONTEXT_TARGET_MISMATCH |

정규화·strip·자동 최신/최대 a version·마지막 tuple 원소·대안 승인 선택은 없다. current Context가 None/empty인 것은 실제 전역 이력 부재 인증이 아니다. resolver가 반환한 원본을 복제/재생성하지 않는다.

## 14. incoming 철회와 날짜

selected ACCEPTED A이면 공급 Context에서 `status is REVOKED`이고 `revokes_acceptance_ref == A.acceptance_ref`인 B를 한 번 순회로 찾는다. 기존 Context가 최대1개·동일11 binding·후행 revision/date를 보장한다. 새 graph framework나 Context 전체 재검증은 없다.

| 명시 선택 | 철회 근거 | 현재 효과 |
|---|---|---|
| A, 관련 B 없음 | None | 다른 gate 평가 |
| A, B→A 있음 | B.acceptance_ref | selected는 A 유지, ACCEPTANCE_REVOKED |
| 직접 REVOKED B | B.acceptance_ref 자신 | selected=B, ACCEPTANCE_REVOKED, 기한 사유 없음 |
| C, B는 A만 철회 | C에 직접 B가 없으면 None | C 독립 평가, A 자동 대체 아님 |

data_use_date가 B.reviewed_at 전/당일/후여도 알려진 B를 적용한다. B.valid_until 경과는 A 부활 조건이 아니다. 현재 supplied 지식의 보수적 사용 규칙이며 당시 정보를 재구성하는 replay/행정 소급효 판단이 아니다.

날짜 gate는 selected ACCEPTED에만 `reviewed_at <= data_use_date <= valid_until` 양끝 포함이다. 하한 전은 ACCEPTANCE_NOT_YET_VALID, 상한 후는 ACCEPTANCE_EXPIRED다. 철회된 A도 A 자체 기한을 검사하므로 REVOKED+EXPIRED 또는 REVOKED+NOT_YET_VALID 조합이 가능하다. 직접 B에는 둘 다 붙이지 않는다.

## 15. 현재 지문 계산·재사용 표

| 값 | 실제 함수/원천 | 계산 위치·재사용 | 금지 |
|---|---|---|---|
| Inventory/Tree/각 subtree | 기존 coverage_fingerprint helpers, 공식 Coverage 경로 | C의 공식 평가 내부 기존 횟수. B는 findings 값을 읽음 | B에서 Coverage 재실행/동결 payload 복제 |
| Registry domain fp | fingerprint_source_registry | C의 validate_dataset_manifest가 실제 계산·Manifest와 대조. 성공한 같은 호출 B는 그 Manifest fp를 현재 값으로 재사용 | 외부 전달 hex를 검증 없이 current로 신뢰 |
| 각 Envelope domain fp | fingerprint_policy_envelope | 전체 validator가 모든 선언 Envelope에 계산·대조 | 선택 Envelope만 검증하고 전체 성공 주장 |
| Benefit definition fp | fingerprint_benefit_snapshot | B에서 current Benefit에1회, 모든 guards/정상 변경 비교에 재사용 | 별도 to_dict 전체/hash(any)/provenance 추가 |
| Manifest fp | manifest.fingerprint() | A/C가 선택 기록에 필요할 때1회, B의 결과9필드에는 불필요 | bytes SHA나 검토 완료 인증으로 사용 |
| 실제 파일/실행 bytes SHA256 | A의 실제 확보 bytes | 파일 존재/내용·parse/실행 대응에 사용 | domain fp/ENGINE_VERSION/임의 literal로 대체 |
| 역사 Benefit fp | 기존 fingerprint_benefit_snapshot | A의 artifact 대응에서 당시 원본에 계산, current 정의 계산과 다른 대상 | 과거 문자열만으로 원본 보존 주장 |

기존 full validator 내부의 지문 재계산은 유지한다. 이번에 반환값·캐시 인자를 추가하거나 frozen 코드를 최적화하지 않는다. 작은 source 조회의 재사용은 가능하나 추가 persistent Context/cache schema가 필요하지 않다.

## 16. 과거/current guards와 정상 변경

selected가 존재할 때만 다음 비교를 수행한다. REVOKED/만료/SLICE도 비교 가능한 독립 모순을 숨기지 않는다. target은13절까지 동일하다. 각 guard의 version domain은 기존 계약 그대로다.

| 축·domain | current 원천 | 같은 version/identity | 정상 변경·Reason | 비교 불가 |
|---|---|---|---|---|
| Inventory: policy/scope/i | Result.inventory_version, findings.inventory_fingerprint | fp 다르면 INVENTORY_FINGERPRINT_CONFLICT | i 변경→COVERAGE_SNAPSHOT_CHANGED | 정상 Result에는 두 값 존재 |
| Tree: policy/rule version | Result.rule_version, findings.policy_tree_fingerprint | fp 다르면 POLICY_TREE_FINGERPRINT_CONFLICT | rule 변경→COVERAGE_SNAPSHOT_CHANGED | 정상 Result에는 존재 |
| Coverage Registry: dataset | Result.dataset_version/source_registry_fingerprint | 같은 dataset의 다른 G→SOURCE_REGISTRY_FINGERPRINT_CONFLICT | dataset 변경→COVERAGE_SNAPSHOT_CHANGED | current baseline all-None이면 이 축만 생략 |
| Coverage implementation | Result.implementation_fingerprint | 별도 version 없으므로 차이 자체는 conflict 아님 | present 값 변경→COVERAGE_SNAPSHOT_CHANGED | current all-None이면 생략 |
| Benefit: policy/scope/benefit/b | Benefit.benefit_version, B가 계산한 정의 fp | fp 다르면 BENEFIT_FINGERPRINT_CONFLICT | b 변경→BENEFIT_SNAPSHOT_CHANGED | 정상 Snapshot에는 존재 |
| Benefit Registry: dataset | Benefit.dataset_version/source_registry_fingerprint | 같은 dataset의 다른 G→SOURCE_REGISTRY_FINGERPRINT_CONFLICT | dataset 변경→BENEFIT_PROVENANCE_CHANGED | 항상 존재 |

guard 오류 선택 순서는 Inventory → Tree → Coverage Registry → Benefit definition → Benefit Registry다. Implementation 차이는 정상 사유라 이 오류 우선순위에 끼워 넣지 않는다. 첫 Data Error는 그대로 전파하되, 첫 정상 version 변경에서 반환하지 않는다. 예: 새 dataset이어도 같은 b 아래 다른 정의면 오류다. 철회+만료여도 같은 i/Tree 모순은 오류다.

## 17. SLICE와 없는 baseline

현재 all-None baseline은 정상 CONDITION_SLICE다. COVERAGE_NOT_FULL을 남기고 없는 dataset/Registry/implementation 비교만 생략한다. 과거 승인값·빈 문자열·가짜 hash로 채우지 않는다. 비교하지 못한 축에 SNAPSHOT_CHANGED를 추가하지 않는다.

findings의 Inventory/Tree 값, current Benefit provenance는 그대로 존재하므로 guards는 실행한다. missing baseline이라는 이유로 current Benefit 대 Manifest 모순이나 같은 i/Tree/b 모순을 면제하지 않는다. 일부만 None인 Coverage Result는 정상 생성자가 이미 거부하는 이론적 방어 사례다.

## 18. 정상 사유12개와 오류 매핑

아래 순서를 그대로 사용해 중복 없는 exact Enum tuple을 **B가 구성**한다. 모델이 정렬/보정해 주지 않는다. 성공은 reasons=(), 그 밖은 UNUSABLE이며 status를 직접 저장하지 않는다.

| 순서/Reason | 실행 전제·정상 성공 | 정상 사용 불가 | Data Error/전제 실패 | 원천·책임 |
|---|---|---|---|---|
| 1 NO_ACCEPTANCE_CONTEXT | current 검사 성공 | Context=None/ref=None | 명시 ref와 None은 CONTEXT_REQUIRED | Context/ref, B |
| 2 NO_ACCEPTANCE_RECORDS | exact empty Context, ref=None | supplied records 없음 | 없는 명시 ref는 REF_NOT_FOUND | Context/resolver, B |
| 3 ACCEPTANCE_NOT_SELECTED | nonempty Context, ref=None | 선택 의도 없음 | wrong target은 CONTEXT_TARGET_MISMATCH | Context, B |
| 4 ACCEPTANCE_REVOKED | 원본 선택·정상 Context | 직접 B 또는 A의 incoming B | 깨진 edge는 기존 Context 생성 오류 | 원본 records, B |
| 5 ACCEPTANCE_NOT_YET_VALID | selected ACCEPTED | 사용일<reviewed_at | 날짜 구조/타입은 오류 | 선택 원본/date, B |
| 6 ACCEPTANCE_EXPIRED | selected ACCEPTED | 사용일>valid_until | 직접 REVOKED에 붙이면 결과 로컬 오류 | 선택 원본/date, B |
| 7 COVERAGE_NOT_FULL | 공식 producer 정상 Result | status CONDITION_SLICE | Coverage 계산 자체 오류는 전파 | Result, 기존 Coverage/B |
| 8 POLICY_NOT_VERIFIED | 정책 refs 구조 정상 | Envelope DRAFT/STALE 또는 정책 근거 상태/freshness 미충족 | 깨진/비참조 ref·version/policy/date 모순은 오류 | Envelope/Registry/Manifest/date, B |
| 9 BENEFIT_METADATA_NOT_REVIEWED | Snapshot/혜택 refs 구조 정상 | 초기 completeness 또는 혜택 근거 상태/freshness 미충족 | ref/version/중복/policy 모순은 오류. artifact 미확보는 별도 준비 미완료 | Benefit/Registry, B 및 A |
| 10 COVERAGE_SNAPSHOT_CHANGED | selected, 비교 가능한 축 있음 | i/r/dataset/implementation 정상 변경 | 독립 same-version fp conflict는 오류 | 선택 binding/current Result, B |
| 11 BENEFIT_SNAPSHOT_CHANGED | selected, current b/fp 계산 | b version 변경 | 같은 b의 다른 fp는 오류 | 선택 binding/current Benefit, B |
| 12 BENEFIT_PROVENANCE_CHANGED | selected, current provenance | dataset 변경, 정의 fp 같아도 해당 | 같은 dataset의 다른 Registry는 오류 | 선택 binding/current Benefit, B |

1~3은 정확히 하나 또는 선택 시 모두 없음,4~6/10~12는 selected 전용,5/6은 배타적이다.7~9는 선택 유무와 독립이다. REVOKED+EXPIRED+SLICE+정책 미검토처럼 실행 가능한 정상 사유를 모두 남긴다.

현재 target/release 모순은 ACCEPTANCE_CURRENT_INPUT_MISMATCH, Context target 모순은 ACCEPTANCE_CONTEXT_TARGET_MISMATCH다. malformed top-level 인자는 INVALID_ACCEPTANCE_EVALUATION_INPUT이다. 기존 named source/Manifest/guard 오류는 PolicyDataError로 전파한다. 새 메시지는 고정 prefix/field/reason만 사용하고 raw ref/지문/payload/사용자 정보를 노출하지 않는다.

실행 artifact 미확보/검토 artifact 미확보·본문 구조 미정은 위12개에 없는 **외부 준비 미완료/계약 공백**이다. 이를 UNUSABLE 사유로 임의 변환하지 않는다. 해당 A/C 경로를 열지 않고 정상 Result도 발급하지 않는다. 실제 자료가 확보됐으나 대응이 틀린 경우의 준비 오류 형식은 선행 계약에서 닫아야 한다. 오류를 조용히0원/UNKNOWN/정상 SLICE로 낮추지 않는다.

## 19. deterministic 호출·오류 순서

### 전체 호출 순서

1. A에서 명시 자료 확보·bytes/실행/검토 대응 준비. 실패하면 C/B 진입 없음. 현재 미완료 경계다.
2. C에서 전체 release 원본 고정, exact 재료 타입 확인 후 기존 `validate_dataset_manifest`1회. 그 내부 오류 순서는 변경하지 않는다.
3. C에서 명시 선택 Envelope 원본과 current Coverage/ReviewContext 고정, 공식 `evaluate_eligibility_coverage`1회. 기존 오류는 그대로 전파한다. 실패하면 B/factory/candidate0회.
4. B는 아래 phase1~9를 실행한다. 성공한 정상 결과만 C에 반환한다.
5. C는 동일 Benefit/date/Context/ref를 유지해 후속 candidate를 구성한다. 부분 후보/합계는 반환하지 않는다.

전체 검증/공식 Coverage 오류가 B의 no-selection/type/기한 계산보다 먼저 발생할 수 있다. 이는 **M2.49 phase0 외부 준비를 실제 호출로 구체화**한 것으로, 동결 Coverage/Manifest의 내부 오류 순서를 바꾼 것이 아니다. 외부 endpoint 전체의 첫 오류와 B 단독 첫 오류를 혼동하지 않는다.

### B의 내부 순서

| phase | 정확한 검사/호출 | 실패/다음 조건 |
|---|---|---|
| 1 | coverage_result → envelope → benefit → acceptance_context 또는 None → acceptance_ref 또는 None → manifest → registry → data_use_date exact 타입·ref 문법 | INVALID_ACCEPTANCE_EVALUATION_INPUT. exact date라 datetime/subclass 거부 |
| 2 | policy_id → scope/edition → rule identity | ACCEPTANCE_CURRENT_INPUT_MISMATCH |
| 3 | 제공 Context policy_id → scope → benefit_id | ACCEPTANCE_CONTEXT_TARGET_MISMATCH, 미선택도 검사 |
| 4a | 같은 호출 C의 전체 검증/producer 원본 전제. B에서는 policy leaf 순서의 source 구조 resolve, Benefit binding version → validate_evidence_refs → applicable_policy_ids | 기존 source 오류 전파 또는8절 후속 Benefit gate 오류. 정상 검토/freshness 사유는 아직 반환하지 않음 |
| 4b | 현재 dataset → Registry → Coverage present baseline 순서의7절 대조 | ACCEPTANCE_CURRENT_INPUT_MISMATCH. 없는 baseline 축만 생략 |
| 5 | ref=None의 세 분류, 또는 CONTEXT_REQUIRED, 그 외 resolver1회 | REF_NOT_FOUND 전파. 선택 없으면 과거 비교만 생략 |
| 6 | selected ACCEPTED의 incoming B 한 순회 / 직접 B의 자기 근거 | Context 재생성/최신 선택 없음 |
| 7 |16절 순서의 독립 same-version guards. current Benefit 지문은 이 전에 한 번 계산 | 첫 conflict가 정상 사유보다 우선. 선택 없으면 현재 정의/근거 검사는 하되 역사 비교 없음 |
| 8 | 준비한 선택/철회, ACCEPTED 기한, FULL, 정책 검토/freshness, Benefit completeness/근거 freshness, 정상 snapshot 변경을 모두 수집 |18절 Enum 선언 순서로 exact tuple, 독립 gate 조기 반환 없음 |
| 9 | 기존 private Result factory 정확히1회 | 정상9필드 반환. 실패 재시도/부분 Result 없음 |

current Benefit 지문은 phase4b 성공 후 phase5 전에 계산해 로컬 값으로 둔다. 따라서 strict encoding 오류가 ref 조회보다 먼저일 수 있다. **M2.49에서 미정이던 계산 위치를 이 지점으로 고정**한다. 실제 원본 인코딩 문제를 선택 부재/없는 ref로 숨기지 않기 위한 것이다. 기존 helper의 원래 오류를 전파한다.

artifact 본문 검사는 phase4의 암묵적 성공으로 끼워 넣지 않는다. A에서 역사 원본 및 현재 자료의 검토 대응을 준비하는 절차이고 현재 callable이 없다. 실제 연결 구현 전25절의 공백과11절 구조화 계약을 닫아야 한다. 이 순서표는 없는 검사 함수를 실행했다고 주장하지 않는다.

## 20. 기존 factory와9필드 연결

정확한 실제 함수는 `benefit_acceptance_evaluation_result.py`의 **_create_benefit_acceptance_evaluation**이다. B는 모든 구조/참조/guards가 정상 완료된 경우에만 다음9개 keyword를 전달한다.

| 인자 | 전달 원천 |
|---|---|
| policy_id | 현재 benefit.policy_id |
| scope | 현재 benefit.scope 원본 |
| benefit_id | 현재 benefit.benefit_id |
| data_use_date | 명시 인자 원본 |
| selected_acceptance_ref | 선택 없음 None, 있으면 resolver가 반환한 원본.acceptance_ref |
| selected_acceptance_version | 선택 없음 None, 있으면 원본.acceptance_version |
| selected_acceptance_status | 선택 없음 None, 있으면 기존 BenefitAcceptanceStatus 원본 |
| revocation_acceptance_ref |14절 B ref 또는 None |
| reasons | B가 구성한 canonical exact tuple |

factory는 private token과9개 값을 모델 생성자1회에 전달한다. token →필드 →사유 순서/중복 →선택3개 all-None/all-present →선택 사유 →철회 관계 →기한 사유 조합 검사를 우회하지 않는다. factory 오류를 catch/보정하지 않는다. status 저장·usable bool·raw dict 반환·지문 추가·임의 object 생성은 없다. to_dict의10key는 표시용이며 승인 증명서가 아니다.

## 21. 결과 재사용 차단과 후속 candidate

C는 원래 Benefit 객체를 B의 `benefit` 인자와 후속 candidate 조립에 똑같이 사용한다. Result.target/date/ref가 같다는 값 검사만으로 다른 Benefit 정의에 붙일 수 없다. package private API만으로 악성 Python 호출을 막는다고 주장하지 않고, 외부 API shape와 실제 호출/원본 identity tests로 정상 경로를 제한한다.

다음 변경 중 하나라도 있으면 새 호출에서 A/C의 필요한 검증과 B를 다시 실행한다: Benefit version/정의/provenance, Envelope, Manifest/Registry, scope/date, current Coverage/ReviewContext, AcceptanceContext/ref. 특히 A·Benefit·날짜가 같아도 Context에 B가 추가되면 새 평가가 필요하다. Result equality/serialization/cache hit로 생략하지 않는다.

C의 정확한 candidate 타입/adapter signature는 아직 미구현 Bridge 계약 단계에서 닫는다. 이번에 그 모델이나 token/Context fingerprint를 추가하지 않는다. 외부 입력에는 precomputed AcceptanceEvaluation·CoverageResult·status dict·skip_validation/verified/allow_stale 인자를 두지 않는다는 경계는 확정한다.

## 22. Acceptance 끝과 Bridge 시작

Acceptance USABLE은 정의/수용 계층 결과다. 다음은 후단 책임이다.

| 후단 책임 | Acceptance에서 하지 않는 것 |
|---|---|
| 사용자 정책 자격 | 해당 사용자 PASS/FAIL/UNKNOWN 계산 |
| 개인·월 applicability | 실제 대상 월, 병급/선택형 충돌·소득에 이미 포함한 지급 여부 |
| 중복/정책 batch | stable Benefit 중복·여러 후보 metadata 일관성 |
| Bridge 유형 | MONTHLY/UNRESTRICTED_CASH 지원 필터·제외 이유 매핑 |
| 현금흐름 | 월 합계, 새 CashflowInput 매핑, calculate_cashflow |

정확히 검토된 QUARTERLY/LOCAL_CURRENCY 정의는 Acceptance USABLE일 수 있다. 현행 직접 월 현금 Bridge에서는 제외될 수 있고 월할 환산하지 않는다. 이를 BENEFIT_METADATA_NOT_REVIEWED로 바꾸지 않는다. raw Context/history·검토 artifact를 Bridge에 넘겨 Acceptance를 재평가하게 하지 않는다. 외부 Result 하나만 단독 수용 입력으로 노출하지 않는다.

## 23. 기존 사례 재사용과 후속 실행 검증

아래는 **문서 수동 대응표**다. 신규 실행 tests는0개이며 합성 전제의 USABLE을 실제 안산 평가로 해석하지 않는다. S는 실제 current 원본/전체 준비·검토가 충족된 합성 기준이다.

| 기존 사례/검증축 | 실행 전제·변경 | 기대/책임 | 후속 테스트 종류 |
|---|---|---|---|
| AE01~AE06, AC29~AC33/AC74 | S에서 None/empty/nonempty·미선택/명시 없는 ref | 세 사유 구분, CONTEXT_REQUIRED/기존 REF_NOT_FOUND, resolver0/1회·원본 identity | B 단위 |
| AE09~AE10/AE27/AE49 | wrong Context target+ref=None, raw 타입/date, 현재 혼합 | 정상 미선택보다 Data Error 우선 | B 오류 순서 |
| AE07/AE28 | S의 정확한 현재 원본 | 사유 없음, 기존 factory1회 | 준비/producer/B 합성 통합 |
| AE35/AE68 | current 한쪽만 D2 / 다중정책 Manifest에 한 Envelope만 제출 | current mismatch / 전체 validator 집합 오류, 정상 Result 없음 | C 전체/선택 범위 |
| AE37~AE38/AE67 | 정상 SLICE all-None / 같은 i 다른 fp / partial baseline | 비교 없는 축에 변경 사유 없음, 가능한 독립 conflict 유지. partial baseline은 기존 생성자에서 차단 | B + 기존 생성자 회귀 |
| AE28~AE32, scope 근거 | 같은 연도 다른 quarter 또는 Inventory 없이 연도만 제공 | scope mismatch 또는 producer 준비 불가. Q3 추론 금지 | C 원본 생산/B identity |
| AE42/AE44/AE66 | 정상 refs, broken locator/version, ACTIVE DRAFT/STALE, 확인일 경계/초과·미래·None, duplicate Benefit refs | 정상 상태/freshness만8/9, 구조/비참조/중복은 기존 오류. document/locator 각각 검사 | source gate 단위/통합 |
| AE63, artifact 확보 | ref만 있고 본문 없음 / 다른 Snapshot artifact / 해시만 일치 | 준비 미완료 / 대응 오류. hash로 실제 검토 진실성 인증 안 함 | A의 향후 artifact 대응 tests·실제 검토 절차 |
| AE68, 실제 bytes/실행 | domain fp는 맞지만 bytes 다름 / 같은 bytes가 아닌 객체 / 실행 artifact 미확보 | release 준비 실패, B/candidate 호출0회 | A/C 후속 계약 tests |
| AE08/AE11~AE21, AC93/AC108~AC109 | A, A+B, A+B+C의 A/C, 직접 B, B 검토일 전·horizon 후 | A selected 유지+B근거, C 독립, 알려진 B 차단·A 부활 없음, 직접 B 날짜 사유 없음 | B 철회/순열 |
| AE22~AE26 | ACCEPTED 하한 직전/당일·상한 당일/다음날·하한=상한 | 포함 기한,5/6 배타 | B 날짜 경계 |
| AE29~AE36/AE39~AE41/AE48 | 정상 i/r/b/dataset/implementation 변경, 같은 version 모순, 한 축 정상 변경+다른 축 모순, 철회/만료 동시 | 정상 변경 사유 보존, 독립 conflict 우선, 정의 동일+provenance 새 값도12 | B guarded comparisons |
| AE43/AE45/AE64 | 미완료 정의 / 분기 지역화폐 / 사용자 UNKNOWN | incomplete는9, Bridge 비지원/사용자 상태는 Acceptance reason 아님 | B 경계 + 후단 별도 |
| AE46~AE47/AE50~AE59 | 정상 복수 사유 및 결과 로컬 조합 | canonical tuple, Data Error 시 factory0회, factory로 보정 안 함 | B 연결, 기존237개 모델 회귀 |
| AE20/AE59, AC36/AC81~AC82 | 유효 Context 기록 순열·같은 원본 반복 | 같은 selected/B/reasons, 입력 불변. Context 자체 equality 순서 민감성과 구분 | B 결정성 |
| AE60~AE61 | 같은 호출 Benefit identity, 다른 b/date/Context로 재사용, 새 B 추가 | C는 외부 Result 인자 없음, 새 평가1회, 새 Benefit 원본 결합 | C API/호출 스파이 |
| AE62~AE65, AC61/AC120 | 누락 철회·형식상 가짜 검토·과거 사용일·USABLE | 완전성/권한/실제 검토 인증 못함, replay/사용자 PASS/금액 승인 아님 | 운영 검토·의미/경계 tests |

기존 정상 생성자로 불가능한 partial baseline/self-link/역전 record·동일 target에 중복 직접 철회를 B 정상 입력 fixture로 만들지 않는다. 기존 모델 거부 회귀로 확인한다. 강제 object 훼손을 정상 evaluator 지원 범위로 확대하지 않는다.

후속 테스트는 실제 연결 때 필요하다. 전체 validator/공식 Coverage 각각1회, 실패 뒤 B/factory/candidate0회, 같은 원본 인자 identity, 기존 helper 오류 객체 그대로 전파, current Benefit 지문1회·독립 guards·예외 시 정상 결과 없음·source 날짜 양끝·Context 순열을 확인한다. 현 문서의 수동 행 수를 새 실행 테스트 수로 세지 않는다.

## 24. 계약 충돌 검토·Assumptions·실제 안산

Coverage 의미/API/오류/지문·GV01~GV15, Benefit 정의 payload/BV01~BV16, record21/Context4/Result9·12Reason에 변경이 필요한 충돌은 발견하지 않았다. M2.49의 내부 순서는19절에서 현재 caller graph로 구체화했고 Benefit 지문의 오류 발생 위치를 명시했다. 기존 문서를 소급 수정하지 않는다.

| 남은 의존사항 | 분류·영향 |
|---|---|
| 실행 artifact 구성/실행물 대응 | **미정 계약**,25절 다음 한 작업. 형식상 hex로 해결 불가 |
| release bytes 고정·동일 bytes parse/전체 검증 연결 | 알려진 검증 의무의 **미구현 A/C 연결**. actual Manifest/실행 artifact 아직 없음 |
| 검토 artifact 구조화 원본/claim/binding 대조 | 필수 내용은11절 기존 의무, strict 표현/loader/대응 함수 **미정·미구현**. 다음 한 작업에 편의상 함께 구현하지 않음 |
| source freshness/Benefit binding·current consistency | 의미는7~9절에서 구체화, pure gate **미구현** |
| 선택·철회·기한·guards·사유/factory | 이 문서의 B 계약, **미구현** |
| same-call adapter/Bridge | 원본/재사용 금지 경계 확정, 실제 API/구현/tests **미완료** |
| legacy full release/회차·공식 조건/효력 연결 | policy-specific 수용 전 **미완료**. Generic FULL로 자동 해결 안 됨 |

**Assumption A1:** 정상 constructor/public producer를 거친 immutable 원본을 신뢰된 내부 경로가 공급한다. Python private 우회/강제 변조를 막는 보안 인증이 아니다.

**Assumption A2:** 공식성·실제 검토의 충실성/권한·불변 이력 및 현재 철회 이력의 완전성은 팀의 실제 준비/검토 절차가 담당한다. 이를 boolean 성공값으로 바꾸거나 아직 하지 않은 검토를 가정하지 않는다.

**Assumption A3:** 작은 대학 MVP는 요청 단위 계산이다. 결과 cache/요청 간 재사용·역사 as-of replay·다중 독립 source release 병합은 지원하지 않는다. 필요하면 별도 계약 개정부터 한다.

실제 안산001/002는 **DRAFT / CONDITION_SLICE**다. 실제 full Inventory/Review·BenefitSnapshot/Acceptance/Context/평가 결과/혜택 금액을 새로 만들지 않았다. 정책 Cashflow 반영0원 원칙을 유지하며 아직 없는 Bridge 실행 결과로 보고하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, Generic Coverage는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**를 유지한다.

## 25. 최종 판단과 다음 최소 작업 한 개

**NEEDS_RELEASE_VALIDATION_CONTRACT**

현재 existing validator는 전체 **메모리** release 대응을 검사한다. 실제 실행된 엔진과 입력/evaluator artifact가 어떤 bytes인지 식별하고, 이를 Manifest.engine_artifact_sha256와 CoverageReviewContext.implementation_fingerprint에 연결하는 규약은 없다.8개 내부 인자·9필드 결과를 조립해도 이 사실을 증명할 수 없으므로 evaluator 전체 구현 준비 완료로 판단하지 않는다.

**다음 최소 작업은 “엔진 배포 artifact와 Coverage 입력/evaluator artifact의 식별·실행 대응 규약 한 개를 문서로 확정”하는 것이다.** 범용 release platform·새 Context/Result 모델·evaluator/adapter/Bridge 구현은 포함하지 않는다.

| 다음 작업의 범위 | Definition of Done |
|---|---|
| 두 hash의 정확한 대상 | 엔진 배포물과 input/evaluator artifact의 실제 구성·의존 파일/제외 범위를 명시하고, 같은 artifact인지 다른 artifact인지 근거로 결정 |
| 실제 실행 대응 | 확보 bytes로 로드/실행한 것을 어떤 최소 내부 호출 경계에서 확인하는지 정의. 경로/버전 상수/임의 hex로 대체하지 않음 |
| 기존 Manifest/Context 연결 | 기존 필드 재사용 가능성 및 필요한 최소 외부 원재료/API를 확정. schema 변경 필요 시 먼저 영향 보고 |
| 오류와 테스트 | actual bytes 부재·hash mismatch·서로 다른 실행/검토 artifact·정상 새 artifact 교체의 준비 실패/정상 변경을 구분하고 합성 재현 사례 정의 |

이 항목을 먼저 택한 이유는 **현재 baseline 자체를 무엇으로 계산했는지 식별하는 선행 사실**이기 때문이다. artifact hash 입력 문자열만으로 실행/원본 대응을 보장하는 문제가 가장 앞에 남아 있다. 검토 artifact 내용 대조도 별도 미완료이며 다음 작업 하나로 전부 해결된다고 주장하지 않는다. 이미 확정된 선택/철회/12Reason/결과 모델을 다시 설계하거나 새 검토 framework를 계속 늘릴 이유는 없다.

## 26. 검증 기록

사전 전체 pytest: **6962 passed in 17.75s**. 문서 작성 후 전체 pytest: **6962 passed in 15.36s**. 신규 실행 tests/fixture/기대값 변경: **0개**다. 이 회귀는 기존 구현 보존 확인이며 아직 없는 evaluator/준비 gate/adapter의 실행 검증이 아니다.

actual releases/pycache를 제외한 backend/tests/data/docs의 사전164개 파일은 **SHA256 모두 동일**하다. 추가는 이 문서 한 개, 기존 파일 수정/삭제0개, 최종165개다. Coverage freeze 문서/source·기존 모든 tests/fixture/기대값·GV01~GV15/BV01~BV16 literal·Benefit/Acceptance/Context/Result·Cashflow·ResidenceHistory 자료를 보존했다.

실제 release6개 파일도 **SHA256 전부 동일**하며 경로/크기/수정시각이 같다. 실제 정책 도메인 지문·평가/승인/철회 기록·혜택 금액은 생성하지 않았다. 문서26개 절의 연속 순서·표 열 수·코드 블록·한국어 표기를 확인했다. 기존 AE/AC 사례를 재사용한 수동 대응과 실행 테스트 수를 구분한다.
