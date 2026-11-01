# M2.71 — Historical Six-Artifact Synthetic Integration Validation

작성일: 2026-10-23 / Asia/Seoul. 범위: **합성 통합 테스트와 보고서**.

최종 판단: **SYNTHETIC_HISTORICAL_SIX_ARTIFACT_INTEGRATION_COMPLETE**

이 보고서에서 **A는 원본 PolicyBenefitAcceptance**, **R은 Review Artifact Loader가 반환한 AcceptanceReviewArtifact**다. 과거 명세 일부의 A/R 약어 순서와 구별한다. 성공 범위는 합성 자료의 A~C이며 D의 실제 검토·사용 적격성은 미완료다.

## 1. 생성·수정 파일

- 추가: `tests/test_historical_six_artifact_integration.py`.
- 추가: `docs/HISTORICAL_SIX_ARTIFACT_INTEGRATION_REPORT.md`.
- 기존 파일 수정·삭제: **0개**. 별도 fixture 파일은 추가하지 않고 새 테스트 내부에 합성 저작 helper를 둔다.
- 새 production 모델·Loader·validator·공개 API·설정·의존성은 없다.

대조한 계약은 Historical BenefitSnapshot / EligibilityCoverage / PolicyEnvelope / CoverageReviewContext / DatasetManifest / SourceRegistry의 여섯 Artifact Preparation Spec, BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC, BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC, COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC, ELIGIBILITY_COVERAGE_CORE_FREEZE, ARCHITECTURE와 실제 구현이다. 과거 후보 API보다 현재 구현 및 최신 구현 기록을 따른다.

## 2. 합성 A/R 생성 구조

저작 의존 순서는 다음과 같다.

1. 합성 Source 원본 두 개, 실행 코드가 없는 합성 ZIP, 별도 합성 Review 증거 bytes를 만든다.
2. 원본 content SHA를 가진 SourceRegistry를 만들고 기존 함수로 Registry domain fingerprint를 계산한다.
3. 합성 m1.1 PolicyEnvelope / 두 leaf의 ALL Tree / Inventory / Bindings / BenefitSnapshot을 구성한다. 지문은 기존 함수로 계산한다.
4. 앞의 실제 지문을 담은 ReviewContext를 만든다. i0001의 과거 기록과 i0002/r0002의 선택 기록을 공존시킨다.
5. Envelope와 Registry raw bytes의 H를 고정한 후, 해당 ArtifactReference와 Envelope domain fingerprint가 들어 있는 Manifest를 만든다.
6. 여섯 raw Artifact의 canonical bytes와 H를 저작 단계에서 확정한다.
7. 원본 A의 자기참조 필드가 없는 raw20 내용과 위 ArtifactReference를 가진 raw Review Artifact를 인코딩한다.
8. raw Review Artifact의 SHA로 root ref를 계산한 뒤 최종 A를 **처음 생성**한다. 임시 A나 임시 hash를 만들지 않는다.
9. `load_acceptance_review_artifact_bytes(raw_bytes=..., expected_acceptances=(A,))`로 R을 복원한다.
10. 같은 R과 같은 A를 여섯 Historical Loader에 전달한다. `entry.acceptance is A`를 검사한다.

복수 Entry 시험은 a0001과 a0002를 함께 싣고 Entry 순서를 양방향으로 바꾼다. 선택 revision의 source/Inventory/Tree/Benefit/dataset에 대응하는 여섯 raw를 사용한다. 최신 날짜나 tuple 위치로 revision을 선택하지 않는다.

## 3. 여섯 Artifact의 hash 원천

H는 **저작한 raw bytes 전체의 SHA256**이다. 소비 Loader의 반환값을 다시 직렬화해서 expected H를 만들지 않는다. 기본 합성 fixture의 다음 여섯 H를 새 테스트의 상수로 고정하고 별도 parameterized test로 확인한다. 변조 시험에서는 변경 bytes의 실제 H를 R에 먼저 고정해 raw 무결성 검사 뒤의 domain binding까지 도달시킨다.

| Artifact / Entry ref | 기본 합성 raw SHA256 |
|---|---|
| Benefit / accepted_terms_ref | `ee2dd9425eeaa2f461a20619b293deb0deae6b399961f93e7b54b5c819ab5ea6` |
| Coverage / coverage_snapshot_ref | `555eef751ec54ae40cfd3a9bed52b32d49f77532f12f454f79e664918fec6710` |
| Envelope / policy_envelope_ref | `0efa33b9a64d3efa0109547f3d57e89c310601a81109badbb4c4456cd0b1c7a5` |
| Reviews / coverage_reviews_ref | `1b9d2693d1c850bf5cc104522fbfe7b4401f42fbf4a302ebfb51775c74c0d685` |
| Manifest / dataset_manifest_ref | `7494bfebfed624062b3018c2fb105e15a2d731a0f9a64f0d852b291a11ba76ce` |
| Registry / source_registry_ref | `678c3c241b133eaddf12d67d3ecf07b86de6c9b8d4a749e3f98eea1b0f55e892` |

추가 원본도 실제 bytes의 H를 사용한다.

- Review Artifact H: `a62a90341c403c0837b6b22714c2373c04fd735e91904dc21df98e487bc0732a`.
- 합성 ZIP H: `f93ecf7de8d27a5a495f8f10cfd557b5c9a610839411b50b90d55ab892db3ee0`.
- SYNTH-A 원본 H: `c8a9cb9833f56ab967f3477a0129f8a3409bae5029d99cd3c08f823d9358db8e`.
- SYNTH-B 원본 H: `6316c342183a0676c2795984fc420904d800efdbd3199fd9ccaee5dfce99c998`.

ZIP은 고정 timestamp / create_system / 권한 / ZIP_STORED를 사용하며 TEST_ONLY.txt 한 개만 담는다. 실행 엔진이 아니고 bootstrap으로 실행하지 않는다. raw hash, Inventory/Tree/subtree/Benefit/Envelope/Registry domain fingerprint는 각각 구별한다. domain fingerprint의 payload/정렬/계산 구현은 복제하지 않는다.

## 4. Review Artifact raw20key 자기참조 방지

raw Acceptance는 정확히 20개 key이고 `review_artifact_ref`가 없다. raw Review Artifact bytes의 H를 구한 뒤 그 ref를 결합한 21필드 원본 A를 생성한다. 기존 Strict Review Artifact Loader가 해당 raw20과 **그 A 자체**를 결합한다.

ReviewContext 내부 record의 `review_artifact_ref`는 별도로 먼저 만든 **합성 Review 증거 bytes**를 가리킨다. Acceptance Review Artifact root를 역참조하지 않으므로 Context → R → Context 순환이 생기지 않는다. 이 opaque ref 선택은 합성 저작 가정이며 실제 사람의 검토를 증명하지 않는다. 여섯 Artifact raw 안에 최종 Acceptance root ref가 들어 있지 않음도 검사한다. 순환을 피하기 위한 임의 placeholder hash는 사용하지 않는다.

## 5. 여섯 Loader 호출 결과

다음 기존 API를 실제 호출하며 I/O나 fake return으로 대체하지 않는다.

| 호출 | 정확한 반환 타입 |
|---|---|
| load_historical_benefit_snapshot_bytes | BenefitSnapshot |
| load_historical_eligibility_coverage_bytes | EligibilityCoverage |
| load_historical_policy_envelope_bytes | PolicyEnvelope |
| load_historical_coverage_review_context_bytes | CoverageReviewContext |
| load_historical_dataset_manifest_bytes | DatasetManifest |
| load_historical_source_registry_bytes | SourceRegistry |

모든 호출은 `raw_bytes=해당 원본, artifact=R, expected_acceptance=A`다. 실제 함수를 그대로 호출하는 관찰 wrapper로 같은 두 객체의 전달을 확인한다. 반환값은 해당 합성 저작 모델과 값이 같고 정확한 타입이다. 반환 객체를 재생성하거나 다른 revision의 객체로 바꾸지 않고 후속 비교에 사용한다.

## 6. 각 Loader의 직접 검증 범위

공통으로 exact 입력 타입, ACCEPTED/root ref/유일 Entry/원본 A identity, 선택된 ArtifactReference의 raw H, strict canonical bytes와 기존 모델 복원을 검사한다. strict parsing의 모든 세부 경계를 새로 복제하지 않고 기존 로더 회귀로 보존한다.

| Loader | 직접 domain binding | 직접 수행하지 않는 주요 교차 검증 |
|---|---|---|
| Benefit | policy/scope/benefit ID·version, 계산한 Benefit fp, dataset, Registry fp | 실제 Registry 문서 version/locator/원문·의미 |
| Coverage | policy/scope, inventory version, 계산한 Inventory fp | Binding root 존재·소유/Review 대응, dataset 필드 없음 |
| Envelope | policy/edition/rule version, 계산한 Tree fp, dataset | Manifest의 Envelope domain fp, 실제 Registry 근거, Q3 의미 |
| Reviews | policy/scope/dataset/Registry/implementation baseline | 선택 Review의 현재 Inventory/Tree/subtree matching |
| Manifest | dataset, 정책 membership/edition/rule, Registry fp 양쪽, 같은 Entry의 Policy·Registry path+H | 전체 입력 집합/실제 Envelope domain fp/source_versions/ZIP 실행 |
| Registry | 계산한 실제 Registry domain fp와 Acceptance의 Coverage·Benefit 양쪽 결합 | 다른 복원 객체의 개별 문서 binding/locator 내용·날짜별 사용 |

## 7. 추가 교차원본 검사

- Benefit / Envelope / ReviewContext / Manifest의 실제 dataset과 A의 두 dataset 축.
- Registry를 직접 계산한 fp와 Benefit / Context / Manifest / A의 두 Registry 축.
- Policy ID, scope를 가진 원본들의 정확한 scope, edition/rule version, Manifest membership.
- 실제 Envelope domain fp와 Manifest 정책 선언. Tree fp와 Envelope domain fp를 혼용하지 않음.
- Manifest 정책·Registry ArtifactReference와 선택된 같은 Entry의 path+H.
- 합성 Envelope·Benefit source binding과 Entry의 합집합 및 Manifest 문서 목록의 실제 대응. 이 fixture는 두 목록이 같은 집합인 경우다.
- 실제 Registry의 문서 version, locator 존재, policy 적용 ID, source original content H.
- Coverage의 명시적 Binding과 Tree 원본 node, Inventory/Implementation Review의 명시 ref 선택과 subtree 지문.
- Manifest engine hash / Entry implementation artifact H / Context implementation fp의 이 합성 자료 내 대응.
- 100회 재실행에서 반환값·snapshot 동일, 입력 bytes와 A/R/저작 모델 snapshot 불변.

`validate_dataset_manifest`를 **실제 호출**한다. 입력은 Manifest의 전체 정책 집합인 합성 정책 한 개와 전체 합성 Registry다. 기존 ENGINE_VERSION 검사를 제거하지 않는다. 이 함수의 source version 집합/Registry fp/정책 metadata·근거/Envelope domain fp 검사를 그대로 재사용한다. 실제 release 전체 검증을 실행한 것은 아니다.

## 8. mismatch 처리 결과와 검출 책임

| 합성 재현 | 여섯 Loader의 직접 결과 | 추가 검출 경계 |
|---|---|---|
| 다른 revision / 다른 Entry의 실제 raw 사용 | 해당 Loader의 BYTES_MISMATCH | raw H 단계 |
| 원본 뒤에 공백을 붙여 raw H 변경 | 해당 Loader의 BYTES_MISMATCH | raw H 단계 |
| 값만 같은 별도 A / 다른 호출 R | 원본 identity / root ref binding 오류 | 로더의 Entry 대응 단계 |
| H는 다시 고정했지만 Benefit version·금액·dataset·Registry·scope가 A와 다름 | Benefit identity/fp/dataset/Registry 오류 | domain binding |
| H 재고정 후 Inventory version·의미·scope 변경 | Coverage version/fp/identity 오류 | domain binding |
| H 재고정 후 Tree/rule version·dataset 변경 | Envelope version/Tree fp/dataset 오류 | domain binding |
| H 재고정 후 Context baseline·scope 변경 | Context dataset/Registry/implementation/scope 오류 | domain binding |
| Manifest dataset/member/edition/rule/Registry fp 변경 | Manifest 각 binding 오류 | domain binding |
| Manifest의 Policy·Registry ref에 다른 Entry의 path+H 사용 | Manifest POLICY_REFERENCE / REGISTRY_REFERENCE 오류 | 같은 Entry 대응 |
| Registry의 동일 document version에서 title만 변경 | 실제 Registry fp 불일치 | Registry loader |
| Manifest source_versions가 실제 Registry와 다름 | **여섯 개 모두 성공 가능** | 기존 validate_dataset_manifest의 SOURCE_REFERENCE_SET_MISMATCH |
| Manifest가 같은 Tree의 다른 Envelope domain fp 선언 | **여섯 개 모두 성공 가능** | 기존 validate_dataset_manifest의 POLICY_FINGERPRINT_MISMATCH |
| Manifest engine_version이 이 실행과 다름 | **여섯 개 모두 성공 가능** | 기존 validate_dataset_manifest의 ENGINE_COMPATIBILITY_MISMATCH |
| Manifest engine H가 Entry의 실제 합성 ZIP H와 다름 | **여섯 개 및 기존 집합 validator도 성공 가능** | 테스트 전용 hash 대응 assert |
| Coverage root 또는 명시 Review ref가 실제 집합에 없음 | **여섯 개 모두 성공 가능** | 기존 구조 분석 / ref resolver의 NOT_FOUND |
| 선택 Review의 같은 version 내 Inventory/Tree/subtree/Registry fp 모순 | **여섯 개 모두 성공 가능** | 기존 matcher의 각 FINGERPRINT_CONFLICT |
| 개별 성공한 서로 다른 호출의 Benefit/Manifest 혼합 | 개별 호출은 성공 | 테스트 전용 dataset 대응 assert |
| 같은 Inventory/Tree/dataset 축을 가진 두 호출의 Binding/Review 혼합 | 개별 호출은 성공 | 기존 matcher의 REVIEW_RULE_ROOT_MISMATCH |
| 같은 Tree의 다른 Envelope와 Manifest를 다른 호출에서 혼합 | 개별 호출은 성공 | 기존 validate_dataset_manifest의 POLICY_FINGERPRINT_MISMATCH |
| A의 Benefit fp까지 맞지만 Benefit 문서 version이 실제 Registry와 다름 | **여섯 개 모두 성공 가능** | 테스트 전용 문서 version assert |
| A의 Benefit fp까지 맞지만 문법상 유효한 locator가 실제 Registry에 없음 | **여섯 개 모두 성공 가능** | 기존 validate_evidence_refs의 LOCATOR_NOT_FOUND |
| Entry source original H와 실제 Registry content_sha256가 다름 | **여섯 개 모두 성공 가능** | 테스트 전용 source original assert |

`AssertionError`는 새 production 오류 계약이 아니라 **테스트에서만 수행한 직접 비교**다. 기존 matcher는 모순을 거부하는 음성 시험에 재사용하며 새 matcher를 구현하지 않는다. frozen 객체 강제 변조는 없고, 정상 constructor / replace 또는 유효 raw 저작을 사용한다.

다른 revision이 동일한 Registry bytes를 정당하게 공유하는 것은 자체로 오류가 아니다. 다른 원본을 섞는 음성 fixture에서는 revision 2의 source 원본 bytes도 실제로 바꾸어 서로 다른 Registry H를 갖게 한다. 공통 내용 공유를 금지하는 production 계약은 추가하지 않는다.

## 9. Manifest / Registry 관계

Manifest 선언과 같은 Entry의 raw 참조를 로더가 확인한 뒤, 실제 복원 Registry의 domain fp와 문서 version 집합을 기존 validator로 추가 비교한다. 다른 Registry path 또는 같은 path의 다른 H도 오류 시험에 포함한다. 각 ref는 논리적 합성 경로이며 Loader는 이 경로에서 파일을 새로 열지 않는다.

Manifest의 engine hash가 Context/Entry의 implementation 원본에 대응하는지는 로더의 직접 보장이 아니다. 테스트 전용 대응 비교가 이를 드러낸다. ZIP의 내용 hash 일치는 실제 production ZIP 실행 대응을 증명하지 않는다.

## 10. Rule Tree / Inventory / Review 관계

기존 `_analyze_coverage_structure`로 누락 조건/명시 root/소유/미매핑을 확인하고 반환된 원본 node를 사용한다. Review는 기존 resolver로 completeness_review_ref / implementation_review_ref 하나를 정확히 선택한다. 과거 Review가 tuple 앞·중간에 있어도 최신 선택이나 정렬을 하지 않는다.

선택한 합성 Review metadata의 Inventory/Tree/subtree가 실제 계산 지문과 대응함을 확인한다. 합성 Review 증거 ref도 별도 실제 bytes의 H와 대응한다. 그러나 사람의 의미 검토나 Review MATCHED, Coverage FULL_POLICY를 선언하지 않는다. 동일 version의 모순 시험에서는 기존 matcher의 오류를 재사용한다. private helper 사용은 이번 저장소 내부 테스트의 재사용이며 새 공개 API 약속이 아니다.

Coverage에는 dataset_version이나 Registry binding 필드가 없다. 이 두 provenance를 Coverage에 새로 추가하거나 A 값으로 채우지 않는다. Scope는 실제 존재하는 모델에서만 비교하고 Envelope의 연도 일치만으로 Q3 applicability를 증명하지 않는다.

## 11. 합성 자료와 실제 production 자료의 차이

모든 정책·근거·검토자·수용 기록은 SYNTH / TEST_ONLY 자료다. Enum상 source_type이 OFFICIAL_NOTICE여도 제목/URL/내용은 합성임을 표시하며 실제 공식 자료가 아니다. Source와 Envelope는 DRAFT, Envelope는 CONDITION_SLICE다.

공식 URL 수집·원문 의미·locator 의미·실제 사람의 검토·source 사용일·freshness·quarter 의미·production ZIP 실행을 검증하지 않았다. ACCEPTED는 합성 기록의 저장 상태일 뿐 현재 Acceptance USABLE을 뜻하지 않는다. Eligibility 평가, 실제 Benefit 적용, Cashflow Bridge/서비스 연결을 실행하지 않는다.

## 12. 신규 테스트 수

**81개 parameterized 실행**. 100회 replay의 반복 횟수나 로더 호출 횟수를 테스트 수에 더하지 않는다. fixture/helper는 새 테스트 파일 안에만 존재한다.

## 13. 전체 pytest와 최초 실패 이력

| 단계 | 결과 | 해석 |
|---|---|---|
| 실제 프로젝트 작업 전 전체 | **10,705 passed in 79.59s** | 사용자 기준선 재확인 |
| 신규 통합 테스트 첫 실행 | **46 failed, 24 errors in 4.56s** | 새 fixture가 SourceBinding.to_dict를 잘못 사용. 존재하는 두 필드를 명시 직렬화하도록 새 테스트만 수정 |
| 신규 두 번째 | **6 failed, 64 passed in 2.01s** | 새 오류 prefix 기대값 5개와 같은 Registry bytes 공유를 오류로 가정한 1개. 실제 기존 prefix로 수정하고 음성 fixture의 revision 2를 실제 다른 source bytes로 저작 |
| 신규 세 번째 | **70 passed in 1.32s** | 초기 통합 시나리오 통과 |
| raw H 고정 및 Entry/Manifest 시험 추가 | **81 passed in 1.56s** | 신규 기대 hash 6개 및 추가 binding 시험 |
| ZIP 운영체제 metadata까지 고정 후 최종 신규 | **81 passed in 1.43s** | 재현 가능한 합성 ZIP bytes와 이에 의존한 새 H 확정 |
| 실제 프로젝트 반영 후 전체 | **10786 passed in 63.30s (0:01:03)** | 사후 전체 최초 실행 통과. failed/skipped/timeout 0회, 재실행 0회 |

기존 테스트·fixture·기대값·timeout 설정은 변경하지 않았다. 위 실패는 새 테스트 저작 중의 실패이며 기존 production 결함으로 보고하지 않는다. timeout은 발생하지 않았다.

## 14. 기존 10,705개 회귀 및 파일 보존

기존 보호 파일 **197개 전부 SHA256 동일**, 기존 파일 수정·삭제 0개. 신규 두 파일만 추가되어 해당 범위 최종 **199개**다. 실제 release 6개는 별도 검사에서도 SHA256·크기·mtime_ns 모두 동일하다. 기존 테스트·fixture·기대값의 SHA도 전부 보존했다. 기존 **10,705개 + 신규 81개 = 10,786개**가 전체 회귀에서 모두 통과했다.

사전 snapshot은 기존 backend/tests/data/docs/tools 및 root 설정·안내 파일을 포함한다. 실제 releases는 별도의 SHA256·크기·수정시각(ns) 기준선으로 검사한다. 테스트 캐시/가상환경은 보호 대상 코드·자료 수에 포함하지 않는다. 사후 전체 pytest가 기존 10,705개와 신규 81개를 함께 실행한다.

## 15. GV / BV 상태

GV01~GV15와 BV01~BV16의 기존 값/fixture/테스트는 수정하지 않는다. 기존 Inventory/Tree/subtree/Benefit 지문 함수와 golden 회귀가 전체 pytest에 포함된다. 이번 합성 raw H 상수는 별도의 새 fixture 기준이며 기존 golden의 개정이 아니다. 결과: **기존 값·파일 SHA 보존 및 전체 회귀 통과**.

## 16. Coverage freeze 영향

Generic Eligibility Coverage Core의 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**를 유지한다. 의미·fingerprint payload·precedence·resolver/matcher·Gate/factory/evaluator·공개 API와 freeze 문서는 그대로다. 기존 helper를 테스트에서 호출한 것이 동결 해제나 실제 정책 FULL 승인이 아니다.

## 17. 실제 release 6개 SHA256

아래 경로는 `data/releases/` 기준이다. 실제 파일의 SHA256·크기·수정시각을 사전/사후 대조한다. 결과: **6개 전부 SHA256·크기·mtime_ns 동일**.

| release 파일 | 전후 SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | `4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f` |
| ansan-youth-2026-10-20-001/sources.json | `a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b` |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | `9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025` |
| ansan-youth-2026-10-20-002/README.md | `8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99` |
| ansan-youth-2026-10-20-002/sources.json | `711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620` |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | `d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92` |

## 18. 기존 production 코드 변경 여부

**없음**. Historical Loader 6종 / Review Artifact Strict Loader / 모델 / 지문 / Source parser / Coverage / bootstrap / Acceptance / Benefit / Cashflow를 변경하지 않는다. API/UI/DB/LLM 연결도 추가하지 않는다. 새 테스트와 새 보고서 두 개만 추가한다.

## 19. ResidenceHistory 및 실제 정책 상태

ResidenceHistory: **OFFICIAL_INQUIRY_REQUIRED** 유지. 공식 답변 없는 거주기간 의미를 새로 결정하거나 구현하지 않는다. 실제 안산 정책: **DRAFT / CONDITION_SLICE** 유지. FULL_POLICY, 현재 Acceptance USABLE, 사용자 eligibility PASS, 실제 Benefit 적용을 선언하지 않는다.

## 20. 남은 검증 공백과 단계별 책임

| 단계 | 이번 확인 | 남은 경계 |
|---|---|---|
| A — Raw 무결성 | 같은 Entry의 실제 여섯 raw H와 Review root H | 외부 불변 보관·원본 발급 이력·서명 신뢰 |
| B — Domain 복원 | 기존 일곱 Loader로 원본 A identity와 정확한 domain type 복원 | 현재 모델 밖의 공식 의미를 자동 해석하지 않음 |
| C — 교차 원본 | 직접 비교와 기존 Manifest/구조/ref/지문 검증 함수 재사용 | 여섯 Loader만 호출하는 production 경로가 이 추가 비교를 자동 강제하지 않음 |
| D — 검토·사용 적격성 | **미완료** | 공식 원문/locator 의미·실제 검토·Source Gate·날짜/신선도·Review MATCHED·Verification·Acceptance USABLE·실제 ZIP 실행 대응 |

기존 함수로 이미 가능한 Manifest 집합 검증, 구조 분석, ref 조회, matcher의 guarded conflict 검사는 다시 만들 필요가 없다. 다만 이들을 같은 A/R와 여섯 반환값에 연결하는 production 계약은 아직 없다. 별도 대응이 남은 예는 implementation Artifact H, Benefit 문서 version, source original H이며 각각 테스트로 구체적인 반례를 남겼다.

복원된 domain 값만으로 raw bytes의 SHA나 입력 A/R의 전달 이력을 새롭게 증명할 수 없다. loader의 raw 검증 책임과 후속 값 비교 책임을 다음 계약에서도 분리해야 한다. 이번 테스트 성공을 전체 실제 release/Content/Source 검증 완료로 확대하지 않는다.

## 21. 최종 판단

**SYNTHETIC_HISTORICAL_SIX_ARTIFACT_INTEGRATION_COMPLETE**

같은 A/R에서 여섯 원본을 실제 복원하고 직접 가능한 주요 교차 관계를 확인하는 합성 범위의 완료다. production의 추가 교차 강제와 D 단계가 완료됐다는 판단은 포함하지 않는다. 새 Historical 모델·새 public loader·범용 framework는 필요하지 않았다.

## 22. 다음 최소 작업 한 개

**작은 순수 Cross-Artifact Validation Contract 설계**를 권고한다. 구현은 다음 승인 범위에서 결정한다.

같은 명시 A/R와 여섯 복원 원본을 연결하는 검증 순서·입력 준비 책임·오류 범위·성공 한계를 정한다. 기존 validate_dataset_manifest / 구조·ref·지문·matcher를 재사용하고, 이번에 테스트 전용 비교로 남은 관계만 추가 계약으로 좁힌다. 새 framework나 D 단계·Acceptance evaluator·Cashflow 연결을 기본 범위로 넣지 않는다. 운영 원본의 raw hash 증명은 기존 Loader에 남겨 두고 값 비교 결과만으로 대체하지 않는다.
