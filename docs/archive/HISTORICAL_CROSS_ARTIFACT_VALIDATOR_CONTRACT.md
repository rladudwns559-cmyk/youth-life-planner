# M2.72 — Historical Cross-Artifact Validator Contract

> 현재 상태 안내 — **M2.73: IMPLEMENTED / HISTORICAL_CROSS_ARTIFACT_VALIDATOR_COMPLETE**. 최신 구현·실행 검증·한계는 **24절**이다. 기존 1~23절과 부록은 M2.72 설계 및 당시 감사 기록으로 보존한다. 여덟 입력·여덟 새 prefix·P0~P8·36개 관계의 책임은 변경하지 않았다. Production same-call orchestration과 Content/Source/전체 release 연결은 미구현이다.

작성일: 2026-10-23 / Asia/Seoul. **설계 문서 한 개만 추가한다.**

최종 판단: **READY_TO_IMPLEMENT_CROSS_ARTIFACT_VALIDATOR**.

이 문서의 함수·prefix·연결 순서는 **후속 구현 계약**이다. 현재 운영 코드나 새 실행 테스트가 생겼다는 뜻이 아니다. 신규 실행 테스트 **0개**, 수동 합성 시나리오 **56개**다. A=원본 PolicyBenefitAcceptance, R=실제 Review Artifact Loader의 반환 객체, E=R에서 A를 명시 선택한 원본 Entry로 표기한다.

## 1. 목적과 실제 검증 공백

M2.71은 여섯 Historical Loader의 실제 반환값을 같은 A/R에 연결했으며, 로더가 모두 성공해도 Manifest source version 집합, 선택 Envelope domain fingerprint, Binding/Review 및 원문 hash 선언이 서로 모순일 수 있음을 재현했다. 테스트의 직접 assert는 운영 검증기가 아니다.

이번 결정은 **여섯 복원 원본의 관계를 순수 함수 한 개로 연결**하는 것이다. 이미 구현된 raw decoder·지문·Review matcher·Coverage 구조 분석을 다시 만들지 않는다. 전체 release/Source 사용/claim 의미/실행 ZIP 검증은 별도 계층으로 남긴다. 함수 하나의 None을 모든 원본의 내용 검토 완료로 해석하지 않는다.

확인 자료:

- HISTORICAL_SIX_ARTIFACT_INTEGRATION_REPORT 2~10·20절 및 해당 테스트의 definitions / prepare / restore / 26개 test 함수, 81개 실행 사례.
- BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC 5~20절, BENEFIT_ACCEPTANCE_EVALUATOR_SPEC 5~12·15~22절.
- ELIGIBILITY_COVERAGE_CORE_FREEZE 2~7절, ARCHITECTURE의 현재 Historical Loader 여섯 구현 기록.
- 여섯 HISTORICAL_*_ARTIFACT_PREPARATION_SPEC의 raw·binding·성공 한계와 최신 구현 절, 실제 여섯 loader의 schema/parser/constructor/binding/call 경로.
- 실제 validation.py / manifest.py / coverage_structure.py / coverage_review_resolution.py / coverage_review_matching.py / coverage_fingerprint.py / sources/registry.py.
- RELEASE_ARTIFACT_EXECUTION_BINDING_SPEC 3~6·9·15~18절. M2.52의 공유 ZIP 규약은 새 bundle에 대한 규약이며 모든 과거 hash의 전역 equality가 아니다.

과거 문서의 “loader 미구현”은 최신 구현 기록과 M2.71의 실제 호출로 해소됐다. Content Validator·Source Gate·전체 운영 orchestration·Acceptance evaluator가 완성됐다는 의미는 아니다. 이번 문서로 기존 명세를 소급 수정하지 않는다.

## 2. M2.71 발견 사항 전체 목록과 A/B/C/D 분류

분류는 **A 기존 Loader**, **B 기존 순수 함수 재사용**, **C 새 함수의 최소 관계 비교**, **D 다른 계층**이다. B+C는 기존 함수가 계산/구조 검사를 담당하고 새 함수가 원본들을 연결한다는 뜻이다. raw 무결성의 단계 A와 이 표의 분류 A는 모두 로더 책임을 가리키며, ReviewContext의 검토 상태를 뜻하지 않는다.

| ID / 관계 | 관련 원본 | 기존 보장 | 남은 공백 | 책임 계층 |
|---|---|---|---|---|
| R01 Review root H·raw20·원본 identity | A/R/Review raw | Strict Loader가 같은 bytes·raw20·원본 is 결합 | typed R만으로 실제 loader 실행 이력 인증 불가 | A / 운영 orchestration |
| R02 다른 revision·Entry raw, 손상된 raw H | 여섯 raw/E refs | 각 loader의 BYTES_MISMATCH | 새 함수에서 raw 재해시할 재료 없음 | A |
| R03 값만 같은 A 복제·다른 R | A/R/E | 기존 Entry binding이 거부 | 새 호출 경계에서도 정확한 E를 선택해야 함 | A / B: 기존 _selected_entry 재사용 |
| R04 Benefit ID/version·같은 b의 금액/fp·dataset/Registry/scope | Benefit/A | Benefit loader가 각 축 거부 | 기존 _bind/정의 payload를 복제할 필요 없음 | A |
| R05 Inventory version·같은 i의 의미/fp·scope | Coverage/A | Coverage loader가 거부 | Binding과 Review는 Inventory fp 밖 | A, R18~R24로 연결 |
| R06 Rule version·같은 r의 Tree·dataset | Envelope/A | Envelope loader가 거부 | Envelope 전체 domain fp는 Tree fp와 다름 | A / R14 |
| R07 Context dataset/Registry/implementation/scope | Context/A | Context loader의 baseline binding | 개별 record의 Review matching은 별도 | A / R19~R24 |
| R08 Manifest dataset/member/edition/rule/Registry fp | Manifest/A | Manifest loader가 거부 | 선택된 실제 Envelope·Registry와의 대응 | A / B+C |
| R09 동일 source d version의 다른 title | Registry/A | Registry loader가 실제 domain fp로 거부 | Registry의 별도 ID/version을 추가할 이유 없음 | A |
| R10 Policy ID·scope·edition의 실제 교차 대응 | A/Benefit/Coverage/Envelope/Context | 같은 A로 로드하면 추이적으로 일치 | 서로 다른 반환값을 부분 혼합한 호출 방어 | C: P1 |
| R11 Benefit/Manifest 혼합 등 dataset 관계 | Benefit/Envelope/Context/Manifest/A | 같은 A에 대한 loader binding | 실제 전달된 원본끼리의 대응 확인 | C: P2 |
| R12 실제 Registry fp와 provenance baseline | Registry/Benefit/Context/Manifest/A | 각 loader가 A와 결합 | 서로 다른 반환값 사이 fp 대응 | B+C: P4 |
| R13 Manifest source_versions 대 Registry 전체 문서 집합 | Manifest/Registry | 전체 validate_dataset_manifest는 검사함 | 여섯 loader만으로는 미검사 | C: P4, 정확한 두 필드 집합 비교 |
| R14 선택 Envelope의 metadata·domain fp | Manifest/Envelope | 전체 validator와 기존 Envelope fp 함수 | 같은 Tree의 다른 Envelope, 잘못 선언한 domain fp | B+C: P3 |
| R15 Manifest Policy/Registry path·H와 같은 E | Manifest/E | Manifest loader가 양쪽 참조의 path+sha 비교 | 다른 호출 Manifest를 새 함수에 섞지 않도록 연결 | B: 기존 Manifest _bind 재사용, P3 |
| R16 Manifest engine_version 대 실행 환경 | Manifest/역사 환경 | 기존 전체 validator의 ENGINE_COMPATIBILITY_MISMATCH | 현재 코드와 다른 과거 환경일 수 있음 | D: 호환되는 역사 환경 준비/전체 release 검증 |
| R17 Manifest engine H 대 합성 ZIP H | Manifest/ZIP/Context/E | M2.71의 테스트 전용 assert | 공유 profile 여부와 실제 ZIP이 여덟 객체에 없음 | D: 배포 준비/Content, 11·18절 |
| R18 Binding root·소유·미매핑 | Coverage/Envelope.policy | 기존 _analyze_coverage_structure | raw Coverage loader는 Tree를 조회하지 않음 | B: P6, 기존 구조 분석 그대로 |
| R19 completeness_review_ref와 원본 record | Inventory/Context | 기존 Inventory resolver/matcher | 명시 ref 없음/다른 종류/같은 i의 fp 모순 | B: P7 |
| R20 implementation_review_ref·condition/root | Binding/Context/Tree | 기존 Implementation resolver/matcher | 없는 ref·다른 condition/root | B: P7 |
| R21 Review Inventory version/fp | Inventory/Review | 기존 matcher의 guarded comparison | 같은 version 모순을 미검토로 숨기지 않아야 함 | B: P7 |
| R22 Review Tree/subtree version/fp | Policy/선택 root/Review | 기존 지문·matcher | 같은 r의 Tree/subtree 모순 | B: P7 |
| R23 Review dataset/Registry guard | Review/Context | 기존 matcher | 같은 dataset의 Registry fp 모순 | B: P7 |
| R24 Review implementation fp | Review/Context | 차이는 기존 matcher의 정상 STALE 후보 | baseline 자체와 실제 구현 참조의 대응은 미검사 | B: P7 / C: Context 대 E의 동일 역할 hash, P5 |
| R25 historical Review 공존·명시 선택 | Context/Bindings/Inventory | Context가 원래 record와 순서 보존, resolver가 exact ref 선택 | 최신/tuple 위치 선택 금지; opaque review evidence 원문은 입력 밖 | B: P7 / D: 별도 Review 증거 bytes |
| R26 Benefit/Envelope/Entry 문서 version | source_bindings/Registry | get_source는 원본 조회, 전체 validator는 Envelope 버전 검사 | Benefit의 d version 모순 등 미연결 | B+C: P4 |
| R27 Entry의 정책+Benefit source 합집합 | E/Envelope/Benefit | Entry 내부 정렬·source_documents 대응 | 실제 두 목록의 정확한 합집합 여부 | D: Content Validator의 기존 source 합집합 계약 |
| R28 locator 존재·policy 적용·tuple 내부 중복 | Benefit/leaf/조건/Registry | validate_evidence_refs·validate_envelope_sources가 검사하며 ACTIVE도 요구 | M2.71의 합법적이지만 없는 Benefit locator | B/D: Content·Source 계층. 새 함수가 resolve를 대체하지 않음 |
| R29 Registry content_sha256 대 Entry 원문 hash 선언 | SourceDocument/E.source_documents | 두 선언의 형식만 보존 | 값이 있으면 서로 같은 원문을 선언하는지 | B+C: get_source + P5 비교 |
| R30 실제 source original raw H | 원문 bytes/E/Registry | M2.71은 실제 합성 bytes를 해시함 | 새 API에는 원문 bytes가 없음 | D: Content·원문 preparation |
| R31 실제 ZIP profile/실행 대응 | ZIP/환경/Manifest/Context | M2.53은 합성 verify-only | 실제 계산 코드 실행·공유 profile 증명 | D: 기존 배포/실행 계약 |
| R32 다수 Evidence refs·5claim·의미 | Benefit/Inventory/leaf/E/Registry | ref 형식/저장 순서와 Entry 5행 구조 | claim membership·policy 적용·공식 의미·사람 검토 | A(구조) / D(Content·Source·실제 검토) |
| R33 100회 결정성·입력 불변 | A/R/여섯 원본 | M2.71은 반복·snapshot 비교 | 새 함수에서도 보존해야 함 | C의 구현·테스트 계약, 실행 반복을 새 검사 phase로 만들지 않음 |
| R34 source status/date·DRAFT/SLICE | Registry/Envelope/Context | loader는 당시 metadata 보존 | 현재 사용 요건은 다른 질문 | D: Source Gate·FULL/Verification/Acceptance |
| R35 같은 i/r/dataset의 Binding/Review 교차 혼합 | 서로 다른 호출의 Coverage/Context | 개별 로더는 모두 성공 가능 | REVIEW_RULE_ROOT_MISMATCH | B: P6~P7, R18/R20의 실제 반례 |
| R36 같은 Tree의 다른 Envelope/Manifest 혼합 | 서로 다른 호출의 Envelope/Manifest | 개별 로더는 모두 성공 가능 | POLICY_FINGERPRINT_MISMATCH | B+C: P3, R14의 실제 반례 |

M2.71 보고서 8절의 22개 mismatch 행과 7·10절의 정상 교차 비교를 위에 모두 대응시켰다. 단순 raw SHA 실패만으로 C/D를 검증했다고 세지 않는다. R16/R17/R28/R30/R31을 C의 성공으로 해소됐다고 보고하지 않는다.

## 3. 기존 Loader가 보장하는 범위

여섯 API는 모두 필수 keyword-only `raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance`를 받는다. Review Artifact는 기존 `load_acceptance_review_artifact_bytes(*, raw_bytes, expected_acceptances)`가 복원한다. 실제 함수·원래 prefix를 변경하지 않는다.

| 반환 원본 | 직접 binding |
|---|---|
| BenefitSnapshot | policy/scope/benefit ID·b version, 실제 Benefit 정의 fp, dataset, Registry fp |
| EligibilityCoverage | inventory의 policy/scope/i version과 실제 Inventory fp |
| PolicyEnvelope | policy/edition/r version, 실제 Policy Tree fp, dataset |
| CoverageReviewContext | policy/scope/dataset/Registry/implementation baseline |
| DatasetManifest | 두 Acceptance dataset 축, 선택 policy membership/edition/rule, Registry fp 양쪽, 같은 E의 Policy·Registry path+sha |
| SourceRegistry | 실제 Registry domain fp와 A의 Coverage·Benefit 양쪽 Registry binding |

공통 raw 단계의 H/canonical/schema/Enum/constructor·원본 A identity를 새 함수에 복제하지 않는다. Benefit/Inventory/Tree 대 A의 지문 binding도 새 로더처럼 다시 구현하지 않는다. 새 함수는 **같은 호출에서 이 단계를 실제 통과한 결과**를 받는 내부 후속 검사다.

## 4. 기존 validator 재사용 가능성

아래 모든 함수는 외부 I/O와 현재 날짜 조회가 없다. 저장된 날짜를 지문에 포함하는 것은 시스템 시각 의존과 다르다. 재사용은 함수 호출과 기존 예외 보존이며 구현 코드를 복사하는 뜻이 아니다.

| 실제 함수 | 정확한 입력/자료 | 검사 범위·실패 | 이번 결정 / 동결 영향 |
|---|---|---|---|
| historical_dataset_manifest_loader._selected_entry | R, A; exact type은 상위에서 확인 | ACCEPTED/root ref/유일 entry/is/Manifest ref; 기존 PolicyDataError | P0에서 1회 재사용, 새 선택 helper 없음 |
| historical_dataset_manifest_loader._bind | Manifest, A, 원본 E | dataset→membership→edition→rule→Registry fp→Policy ref→Registry ref, 기존 named 오류 | P3에서 1회 재사용. 이미 있는 비교를 복제하지 않음 |
| validate_dataset_manifest | exact Manifest, **전체** Envelope tuple, Registry | 현재 ENGINE_VERSION→전체 정책 집합→source 집합→Registry fp→각 Envelope/근거/fp→전역 rule IDs | 이 여덟 입력 함수에서는 호출하지 않음. 전체 자료·역사 환경을 갖춘 D가 그대로 호출 |
| validate_envelope_sources | exact Envelope, Registry | 문서 version, leaf ref resolve/ACTIVE/policy, 파생 확인일 | D의 기존 source/release 검사에 유지. C가 전체 source gate를 흡수하지 않음 |
| fingerprint_policy_envelope | exact PolicyEnvelope | 실제 전체 Envelope domain fp; ManifestValidationError 전파 | P3에서 1회. Tree fp로 대체하지 않음 |
| fingerprint_source_registry | exact SourceRegistry | 전체 Registry domain fp; ManifestValidationError 전파 | P4에서 1회. raw H와 혼용하지 않음 |
| SourceRegistry.get_source | canonical 문서 ID와 해당 Registry | status와 무관한 원본 조회, SOURCE_NOT_FOUND | P4~P5 문서 version/hash 선언 비교에 사용 |
| _analyze_coverage_structure | exact Coverage, exact Policy | M/root/소유/U, 원본 (Binding, node) tuple; 기존 PolicyDataError | P6 1회. 구조·소유 알고리즘 복제 없음 |
| _resolve_inventory_review / _resolve_implementation_review | exact Context와 명시 exact ref | 원본 record 반환, WRONG_REVIEW_TYPE / REVIEW_REF_NOT_FOUND | P7 matcher 내부 호출을 재사용. 같은 ref를 먼저 별도 조회해 우선순위를 바꾸지 않음 |
| _match_inventory_review | exact Inventory, Context 또는 None, current_inventory_fingerprint | target·i/fp·dataset/Registry guards, InventoryReviewMatch 또는 기존 오류 | P7 1회. MATCHED 강제·STALE/MISSING 오류화 없음 |
| _match_implementation_review | exact Inventory/Binding, Context 또는 None, i/r/Tree/subtree의 실제 값 | ref/target/root·독립 version guards, ImplementationReviewMatch 또는 기존 오류 | P7 Binding마다 1회, canonical condition 순서 |
| fingerprint_condition_inventory / fingerprint_policy_tree / fingerprint_rule_subtree | exact Inventory / Policy / 지원 root | 기존 결정적 payload·지문, PolicyDataError | P7에서 Inventory·Tree 각1회, 원본 root마다1회 |
| validate_evidence_refs / registry.resolve | 원래 ref tuple와 Registry / ref | 문법·tuple 내부 중복·존재·ACTIVE, SourceValidationError | D에서 재사용. C가 has_evidence로 바꿔 사용 검증 완료로 취급하지 않음 |

`validate_dataset_manifest`는 필요한 **모든 Envelope**를 받지 못하고, current engine 호환 및 ACTIVE 참조 검사도 포함한다. 이를 선택 Envelope 하나로 호출하거나 임시 Manifest를 만들어 정책 목록·engine_version을 수정하지 않는다. 함수의 엔진 검사만 제거한 사본도 만들지 않는다. P3/P4의 선정된 원본·실제 Registry 비교는 아래의 한정된 관계 검사이며 전체 정책 순회/전역 rule ID/상태·날짜 검사를 구현하지 않는다.

기존 matcher는 CoverageResult를 만들지 않는다. 새 함수는 `_collect_coverage_integration_findings`, Gate/factory, `evaluate_eligibility_coverage`를 호출하지 않는다. 전체 Coverage 판정이나 composition/FULL 평가를 불필요하게 추가하지 않는다.

## 5. 여섯 원본의 정확한 관계

| 입력 | 실제 저장 관계 / 새 필드가 아닌 것 |
|---|---|
| BenefitSnapshot | scope·b/version/정의·source_bindings·dataset/Registry fp |
| EligibilityCoverage | Inventory와 Bindings. **dataset_version/Registry/implementation 필드 없음** |
| PolicyEnvelope | policy/rule/edition·dataset·source_bindings·legacy coverage/상태. quarter 없음 |
| CoverageReviewContext | policy/scope·dataset/Registry/implementation baseline, 두 Review record tuple |
| DatasetManifest | dataset·engine 선언, 전체 policy refs/source_versions, Registry 참조. 선택 정책 외 Envelope 실체는 보관하지 않음 |
| SourceRegistry | sources tuple. 별도 registry_id/registry_version/dataset_version 저장 필드 없음 |
| A / R / E | A의 독립 Coverage/Benefit binding과 R의 원본 Entry/ArtifactReference. R은 실제 companion bytes를 자동 확보하지 않음 |

별도 scope ID·Registry version·Coverage dataset 필드를 만들지 않는다. UserProfile/생성형 AI/사용자 자격·금액은 이 계약의 입력이 아니다.

## 6. Same-call A/R identity 계약

운영 호출 경계는 원본 A와 R을 고정한다. A는 명시 선택된 ACCEPTED 원본이다. 새 함수의 P0는 `_selected_entry(R, A)`를 호출해 root ref → 유일한 acceptance_ref Entry → `E.acceptance is A`를 기존 순서로 확인한다. raw20 재대조나 새 A 생성은 없다.

모든 Historical Loader에는 **그 A와 그 R 자체**를 전달한다. 각 ref는 그 유일한 E에서 정해진다. 날짜·revision 최대값·tuple 위치·이름이 비슷한 다른 정책으로 fallback하지 않는다. 같은 Registry bytes를 여러 revision이 정당하게 공유하는 것은 허용한다.

REVOKED B의 None 참조를 A의 참조로 덮어쓰지 않는다. 여섯 Loader와 이 내부 함수의 직접 대상은 ACCEPTED A다. 철회 경로의 effective target A 확보와 B/Context/target Artifact 결합은 기존 Content 계약의 별도 준비 책임이다.

## 7. 객체 출처 신뢰 경계

**계층 A:** 한 번 확보한 각 raw bytes를 기존 Loader가 독립 H와 비교하고, 그 동일 bytes를 복원한다. **계층 B:** 그 반환 원본 여섯 개를 새 함수가 비교한다.

계층 B의 타입/is/지문/equality만으로 계층 A의 실제 실행·입력 bytes·ZIP 실행 이력을 재증명할 수 없다. 다음 순서를 운영 코드의 호출 구조와 후속 identity/call-count 시험으로 강제해야 한다.

1. 실제 Review Loader → 원본 R, 외부에서 이미 고정한 원본 A의 명시 선택.
2. 같은 A/R로 여섯 Loader를 실제 호출하고 각 반환값을 로컬에 고정.
3. 여섯 성공 직후, 그 반환 객체를 그대로 새 함수의 여섯 인자에 전달.
4. 어느 Loader나 관계 검사가 실패하면 downstream Content/evaluator/Bridge 호출 0회.

외부 endpoint가 typed 객체·precomputed fp·검증 완료 bool·이전 호출의 None 성공을 받지 않는다. 새 capability token/서명/인증 모델도 없다. 새 함수는 raw decoder가 아니므로 임의 객체를 주입한 단독 호출에 여섯 로더 전체의 보장을 부여하지 않는다. 특히 값과 참조가 같은 다른 객체의 출처는 여덟 인자만으로 구분 불가능하다. 부분 혼합에서 **실제 비교 값이 다른 경우**는 P1~P7이 차단하지만 모든 주입을 막는 보안 증명은 아니다.

## 8. Dataset 관계

P2는 다음 **실제로 전달된 원본**의 값만 비교한다.

1. Benefit.dataset_version 대 A.benefit_dataset_version.
2. Envelope.dataset_version → Context.dataset_version → Manifest.dataset_version 각각 대 Benefit.dataset_version.

A.coverage_dataset_version과 A.benefit_dataset_version의 동일성은 기존 Acceptance 생성자 불변조건이며 다시 재구현하지 않는다. Manifest `_bind`도 두 A 축을 기존 순서로 대조한다. Coverage 관련 dataset은 Context와 A의 Coverage binding에서 확인하며 Coverage에 없는 필드를 읽지 않는다.

기존 loader를 바꾸지 않고 actual 반환값 혼합을 방어하는 짧은 교차 비교다. P1/P2와 같은 호출의 Entry guard가 일부 scalar를 다시 비교해도, 로더의 parser·전체 _bind·지문 구현을 복사하는 것은 아니다. 정상 historical D1과 별도의 current D2 비교/정상 변경 판정은 이 함수 밖이다.

## 9. Policy / Rule 관계

P1에서 Benefit.policy_id → Coverage.inventory.policy_id → Envelope.policy_id → Context.policy_id 각각을 A.policy_id와 비교한다. 그다음 Benefit.scope → Inventory.scope → Context.scope 각각을 A.scope와 비교하고, 마지막에 Envelope.edition_id를 A.scope.edition_id와 비교한다. scope equality는 quarter까지 exact value equality다.

P3에서 기존 Manifest `_bind`로 A/E 대응을 검사한 뒤 선택 PolicyEditionReference와 **실제 Envelope**의 edition_id → rule_version → schema_version → rule_schema_version → `fingerprint_policy_envelope`를 순서대로 대조한다. Manifest membership은 A.policy_id로 명시 선택하며 기존 _bind의 유일 membership 검사를 재사용한다.

Tree fp는 Inventory/Implementation Review matching의 현재 지문으로 기존 helper가 계산한다. 같은 Tree라도 policy_name/검토 metadata 등 Envelope domain이 다를 수 있다. raw Envelope H·Envelope domain fp·Tree fp·subtree fp를 서로 대체하지 않는다. 2026 edition 일치만으로 2026/Q3의 공식 적용 조건을 증명하지 않는다.

## 10. Registry 관계

P4에서 실제 `fingerprint_source_registry(source_registry)`를 한 번 계산한다. 이를 Benefit.source_registry_fingerprint → Context.source_registry_fingerprint → Manifest.source_registry.fingerprint 순서로 대조한다. Manifest의 fp와 A의 두 Registry 축은 P3의 기존 _bind가 이미 연결한다.

이후 다음 두 집합의 exact equality를 확인한다.

- Manifest.source_versions의 `(source_document_id, document_version)` 전체 집합.
- 공급된 Registry.sources의 같은 두 필드 전체 집합.

Registry는 이 입력에서 전체 원본이므로 이 비교는 가능하다. 다른 정책 Envelope를 모두 확보했다는 뜻은 아니다. 기존 생성자가 검사한 중복/형식은 재구현하지 않는다. 집합 equality만 비교하고 원래 tuple을 정렬/수정하지 않는다.

그다음 Envelope.source_bindings → Benefit.source_bindings → E.source_documents.binding의 원래 tuple 순서로 get_source를 호출하고 d version을 비교한다. source가 없으면 기존 SOURCE_NOT_FOUND, version이 다르면 새 고정 관계 오류다. Entry의 정확한 source **합집합** 판단은 Content 책임으로 남긴다.

get_source는 ACTIVE 여부를 검사하지 않는다. 당시 status·검증일을 변경하지 않고 metadata 관계만 검사한다. Source Gate의 resolve/검토/freshness를 통과했다고 말하지 않는다. Registry raw H는 E.source_registry_ref.sha256이며 domain fp와 별개다. Registry ID/version을 경로·파일명에서 만들지 않는다.

## 11. ArtifactReference 관계

P3의 기존 Manifest _bind가 선택 PolicyEditionReference.artifact와 E.policy_envelope_ref, Manifest.source_registry.artifact와 E.source_registry_ref를 비교한다. ArtifactReference의 두 필드 **path와 sha256 모두 exact equality**다. 각각 path만 바꾼 시험과 sha만 바꾼 시험을 둔다. 경로 대소문자/alias/파일명만으로 같은 원본 처리하거나 파일을 다시 열지 않는다.

P5a의 새 비교는 **동일한 Coverage 구현 역할**인 Context.implementation_fingerprint와 E.implementation_artifact_ref.sha256의 대응이다. 이 참조의 실제 ZIP bytes H 검증·실행은 새 함수의 입력 밖이다.

**Manifest.engine_artifact_sha256와 위 두 값의 전역 equality는 추가하지 않는다.** M2.52 공유 source ZIP profile이 실제 확인된 자료에서는 세 값이 같은 H여야 하지만, 그 profile과 실제 bytes/실행 증거는 여덟 객체에 없다. M2.71의 합성 ZIP은 두 역할을 공유한 한 fixture다. 이 사례를 모든 역사 자료의 hash 규칙으로 승격하지 않는다. 해당 mismatch는 D의 배포/Content 준비가 실제 profile을 확인한 뒤 차단해야 한다. 정보가 없으면 준비 미완료로 중단하고 가짜 hash나 자동 fallback으로 채우지 않는다.

P5b에서는 E.source_documents 순서대로 Registry의 동일 문서 content_sha256가 **None이 아닐 때만** 그 값과 ReviewSourceOriginal.artifact.sha256를 비교한다. None은 정상 optional 부재이며 fake H로 채우지 않는다. 이 비교는 두 hash **선언**의 일치일 뿐 실제 공식 원문 bytes를 해시한 결과가 아니다. None인 행이 있어도 다음 행의 알려진 모순을 검사한다. Registry에는 원문 artifact path가 없으므로 경로 equality를 만들어내지 않는다.

Manifest.review_manifest와 E.coverage_reviews_ref, Review record의 opaque review_artifact_ref는 자동으로 같은 자료가 아니다. 원본들에 없는 hash/경로를 추론하지 않는다.

## 12. Review 관계

P6은 `_analyze_coverage_structure(coverage, envelope.policy)`를 한 번 호출해 원본 Binding/root 쌍을 받는다. 조건 순서/명시 root/소유/미매핑의 기존 오류와 정상 missing facts를 그대로 따른다. M이 남은 합법적인 부분 Coverage를 새 오류로 만들지 않는다. complete coverage의 U 오류는 기존 helper가 그대로 낸다.

P7은 다음 순서다.

1. 기존 Inventory fp → Tree fp → P6의 canonical condition 순서에 따른 각 원본 root의 subtree fp를 계산한다. Inventory·Tree 각1회, subtree 각1회다.
2. `_match_inventory_review`를 1회 호출한다. resolver는 그 내부에서 명시 completeness_review_ref를 선택한다.
3. P6 순서의 각 Binding에 `_match_implementation_review`를 1회씩 호출한다. 그 내부 resolver가 implementation_review_ref를 선택한다.

ref 전체를 먼저 조회하는 별도 pre-pass, 최신 record 선택, matcher 비교 로직 복제는 없다. record 존재를 MATCHED로 간주하지 않는다. 기존 matcher는 condition/root identity와 같은 i/r/dataset 아래의 지문 모순을 Data Error로 거부한다. implementation 기록과 baseline의 차이는 기존 정상 STALE 의미를 유지한다.

**새 함수는 MATCHED를 요구하는 gate가 아니다.** completeness_review_ref=None의 정상 MISSING이나 합법적인 과거 version 선택의 STALE만으로 새 Data Error를 만들지 않는다. 명시된 ref가 실제로 없거나 종류/condition/root가 틀린 경우는 기존 Data Error다. STALE/MISSING이어도 다른 Binding의 독립 모순 검사를 끝까지 진행하며 Data Error를 숨기지 않는다.

matcher가 반환한 정상 결과는 로컬 검사 결과로만 사용하고 새 상태로 재포장하지 않는다. None 성공은 현재 자료의 Review 완결성이나 당시 ACCEPTED 발급 기준 재현 성공이 아니다. 그 기준을 요구하는 Content/역사 FULL 준비는 별도다. M2.58의 “원본/검토 재현이 부족하면 Content 전체 성공 없음”을 완화하지 않는다.

## 13. 최소 Pure API

다음 **여덟 개 필수 keyword-only 인자**, 기본값 없음, nullable 없음으로 확정한다.

```python
def _validate_historical_artifact_relationships(
    *,
    expected_acceptance: PolicyBenefitAcceptance,
    artifact: AcceptanceReviewArtifact,
    benefit_snapshot: BenefitSnapshot,
    eligibility_coverage: EligibilityCoverage,
    policy_envelope: PolicyEnvelope,
    coverage_review_context: CoverageReviewContext,
    dataset_manifest: DatasetManifest,
    source_registry: SourceRegistry,
) -> None:
    ...
```

| 인자 | 필요한 이유 |
|---|---|
| expected_acceptance | 명시 target/revision, 원본 E identity의 기준 |
| artifact | 같은 E의 Policy/Registry/implementation/원문 참조 확보 |
| benefit_snapshot | actual dataset·Registry·혜택 source version |
| eligibility_coverage | 실제 Inventory/Bindings·명시 Review refs |
| policy_envelope | 선택 metadata/domain fp와 실제 Policy/root |
| coverage_review_context | 당시 baseline과 Review records |
| dataset_manifest | 선택 정책/Registry 선언과 source version 집합 |
| source_registry | 실제 Registry fp/문서 version/content hash 선언 |

모든 domain 입력은 exact type이며 dict/serialized status/subclass/None을 coercion하지 않는다. Python 인자 개수/위치/이름 오용은 일반 TypeError, 전달된 값의 타입 오류는 P0 PolicyDataError다.

raw bytes/all_envelopes/현재일자/사용자 입력/FULL bool/profile bool/별도 기대 지문/검증 토큰을 추가하지 않는다. 각 목적은 Loader·전체 release·Source·실행 준비의 다른 경계다. 성공은 None, 기계적 모순은 PolicyDataError다. 새 결과 모델·FULL/VERIFIED/USABLE 상태·공개 export/endpoint는 없다. 후보 구현 위치는 `backend/policy_engine/policy_data/historical_artifact_relationships.py`이며 이번에는 생성하지 않는다.

## 14. Error Contract

새 오류는 모두 기존 **PolicyDataError**다. 새 hierarchy/Reason Enum은 없다. 메시지는 정확히 `PREFIX: field: 계약을 확인하세요` 형태의 고정 prefix/field로 제한한다. 배열 field는 원래 index를 사용할 수 있으나 raw payload/ref/hash/사용자 값은 넣지 않는다.

| 새 prefix | phase | field / 발생 조건 |
|---|---|---|
| INVALID_HISTORICAL_ARTIFACT_RELATIONSHIP_INPUT | P0 | API 선언 순서의 인자 이름; exact type 아님 |
| HISTORICAL_ARTIFACT_IDENTITY_MISMATCH | P1 | 해당 policy_id / scope / policy_envelope.edition_id |
| HISTORICAL_ARTIFACT_DATASET_MISMATCH | P2 | 해당 원본의 dataset_version |
| HISTORICAL_ARTIFACT_POLICY_MISMATCH | P3 | selected_policy.edition_id → rule_version → schema_version → rule_schema_version → fingerprint |
| HISTORICAL_ARTIFACT_REGISTRY_MISMATCH | P4 | benefit_snapshot.source_registry_fingerprint → coverage_review_context.source_registry_fingerprint → dataset_manifest.source_registry.fingerprint |
| HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH | P4 | dataset_manifest.source_versions, 또는 해당 binding의 document_version |
| HISTORICAL_ARTIFACT_IMPLEMENTATION_MISMATCH | P5 | coverage_review_context.implementation_fingerprint; 동일 역할의 E implementation H와 다름 |
| HISTORICAL_ARTIFACT_SOURCE_CONTENT_MISMATCH | P5 | entry.source_documents[index].artifact.sha256; 알려진 Registry 원문 hash 선언과 다름 |

기존 helper 예외는 **같은 객체로 그대로 전파**한다. 기존 이름을 새 prefix로 감싸지 않는다.

- P0: `_selected_entry`의 HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH, INVALID_HISTORICAL_DATASET_MANIFEST_EXPECTED_REF.
- P3: Manifest `_bind`의 HISTORICAL_DATASET_MANIFEST_DATASET_MISMATCH / POLICY_MEMBERSHIP_MISMATCH / EDITION_MISMATCH / RULE_VERSION_MISMATCH / REGISTRY_FINGERPRINT_MISMATCH / POLICY_REFERENCE_MISMATCH / REGISTRY_REFERENCE_MISMATCH. 뒤 여섯 이름도 같은 HISTORICAL_DATASET_MANIFEST_ prefix를 가진다.
- P3/P4 지문: 기존 ManifestValidationError, 특히 INVALID_FINGERPRINT_CONTENT 등 원래 오류.
- P4/P5 get_source: 기존 SourceValidationError의 SOURCE_NOT_FOUND.
- P6: INVALID_STRUCTURE_INPUT / COVERAGE_POLICY_MISMATCH / UNSUPPORTED_RULE_NODE / DUPLICATE_RULE_NODE_ID / RULE_ROOT_NOT_FOUND / COVERAGE_OWNERSHIP_OVERLAP / COVERAGE_UNMAPPED_RULE.
- P7: 기존 fingerprint PolicyDataError, INVALID_MATCH_INPUT / WRONG_REVIEW_TYPE / REVIEW_REF_NOT_FOUND / REVIEW_POLICY_MISMATCH / REVIEW_SCOPE_MISMATCH / REVIEW_CONDITION_MISMATCH / REVIEW_RULE_ROOT_MISMATCH / INVENTORY_FINGERPRINT_CONFLICT / POLICY_TREE_FINGERPRINT_CONFLICT / SUBTREE_FINGERPRINT_CONFLICT / SOURCE_REGISTRY_FINGERPRINT_CONFLICT.

Data Error를 STALE/MISSING/SLICE/UNUSABLE/UNKNOWN/0원으로 바꾸지 않는다. 반대로 기존 matcher의 정상 STALE/MISSING을 새 오류로 바꾸지도 않는다. 지원하지 않는 profile/미확보 raw/역사 환경 부재는 외부 준비 미완료이며 이 여덟 인자에서 알아냈다고 가짜 prefix를 내지 않는다. 예상 밖 RuntimeError/TypeError 등 개발 오류를 catch-all로 숨기지 않는다.

## 15. Validation Precedence

아래 순서를 고정한다. 후보 P0~P8 중 ArtifactReference 검사의 일부는 기존 Manifest _bind의 순서를 보존하기 위해 **P3에 포함**한다. P5가 그 비교를 반복하지 않는다.

| phase | 결정적 실행 순서 | 실패 시 |
|---|---|---|
| P0 | 여덟 인자 exact type을 API 순서로 전부 확인 → `_selected_entry(R,A)` 1회 | 첫 타입 오류 또는 기존 Entry 오류. 후속 helper 0회 |
| P1 | 9절 policy ID 순서 → scope 순서 → Envelope edition | 첫 새 identity 오류 |
| P2 | 8절 Benefit 대 A → Envelope → Context → Manifest | 첫 새 dataset 오류 |
| P3a | 기존 Manifest `_bind(M,A,E)` 1회. 내부 dataset 두 축→member→edition→rule→Registry fp 두 축→Policy ref→Registry ref 그대로 | 첫 기존 Manifest 오류 |
| P3b | 선택 Policy ref 대 actual Envelope의 edition→rule→schema→rule schema → Envelope domain fp 계산/비교 | 첫 새 Policy 오류 또는 기존 지문 오류 |
| P4a | 실제 Registry fp 계산1회 → Benefit→Context→Manifest baseline 대조 | 첫 새 Registry 오류 또는 기존 지문 오류 |
| P4b | Manifest/Registry source 두 필드 집합 equality → Envelope bindings→Benefit bindings→Entry source_documents binding의 원래 순서 | 새 version 오류 또는 기존 SOURCE_NOT_FOUND |
| P5 | Context 대 E implementation H → 원래 source_documents 순서의 알려진 content H | 첫 implementation/source content 오류 |
| P6 | 기존 Coverage 구조 분석1회, 그 내부 우선순위 유지 | 기존 구조 오류 |
| P7a | Inventory fp→Tree fp→canonical 각 원본 subtree fp | 기존 지문 오류 |
| P7b | Inventory matcher 전체 slot1회 → canonical Binding별 Implementation matcher 전체 slot | 첫 기존 ref/target/guard 오류. 정상 STALE/MISSING은 조기 반환하지 않음 |
| P8 | 모든 해당 비교 완료 | None |

오류는 수집/정렬하지 않고 첫 예외에서 중단한다. partial report/status를 반환하지 않는다. P3a에서 참조 오류가 P4의 실제 Registry 오류보다 먼저 나타날 수 있는 것은 위 계약의 의도된 순서다. helper 내부의 matcher guarded 비교·root/소유 오류 순서는 그대로다. 정상 version 변경 하나가 독립 same-version conflict를 면제하지 않는다.

## 16. 정상 합성 시나리오 — HXV01~HXV12

아래 56개 ID는 **수동 설계**이며 신규 실행 테스트가 아니다. 다음 구현에서 M2.71의 definitions / prepare / restore를 우선 재사용한다. 원본을 바꾸는 fixture는 저작 단계에서 관련 domain 지문·독립 raw H·최종 A/R를 정확히 재작성하며 frozen 강제 훼손이나 runtime 자동 보정을 사용하지 않는다.

| ID | 입력 / M2.71 재사용 | 기대 / 책임 |
|---|---|---|
| HXV01 | 기본 합성 A/R, 실제 여섯 loader 반환 원본 | 새 함수 None, domain type/입력 identity 보존. FULL/사용 승인은 아님 |
| HXV02 | 서로 다른 정상 a revision의 multi-entry, Entry 순서 양방향 | 각 명시 revision의 원본으로 None, 최신 선택 없음 |
| HXV03 | 과거/선택 Inventory·Implementation Review 공존 | 명시 ref만 선택. 다른 record가 있다는 이유로 오류 없음 |
| HXV04 | Source/Envelope DRAFT·확인일 None의 일관된 역사 자료 | 관계 None. Source Gate가 통과했다는 의미 없음 |
| HXV05 | SUPERSEDED/WITHDRAWN인 문서·locator 상태까지 고정한 일관된 역사 자료 | 상태 그대로 보존, C에서 resolve/현재 ACTIVE 강제 안 함. 사용 검사는 D |
| HXV06 | completeness_review_ref=None, 나머지 구조 일관 | matcher 정상 MISSING만으로 오류화 안 함; 뒤 검사 계속 |
| HXV07 | 선택 ref가 합법적인 과거 version/implementation의 Review를 가리킴 | 기존 STALE 의미 보존. Content 전체 성공은 별도 |
| HXV08 | 다중 정책 Manifest, 선택 Envelope 한 개, 전체 해당 Registry | 선택 관계만 None. 전체 release 검증 완료 주장 없음 |
| HXV09 | 일관된 historical engine_version이 현재 ENGINE_VERSION과 다름 | C는 보존. D는 호환 역사 환경 없이 전체 검증 성공 불가 |
| HXV10 | SourceDocument.content_sha256=None | 해당 hash 선언 비교만 없음, 다른 행/후속 검사 계속. 실제 원문 SHA 증명 없음 |
| HXV11 | 여러 Evidence refs/claim 간 공유·정상 source 공유 | 순서/중복 보존, C에서 새 dedupe/flatten 검증 없음. claim/source 의미는 D |
| HXV12 | 같은 A/R/여섯 원본 100회, 전후 to_dict snapshot·참조 비교 | 결정적 None/동일 오류, 입력 불변·전역 cache 없음. 반복을 테스트 수에 더하지 않음 |

## 17. 모순·경계 합성 시나리오 — HXV13~HXV56

L=기존 Loader에서 차단, V=새 관계 함수에서 차단, D=다른 계층, U=객체만으로 출처 증명 불가능. L에서 실패하면 정상 운영 V 호출은 0회다. V 단독 혼합 시험은 정상 constructor로 만든 자료 또는 다른 성공 호출의 원본을 사용하며 Loader provenance까지 증명한 시험으로 세지 않는다.

| ID | 입력 / 실제 발견 관계 | Loader와 새 함수의 기대 | 책임 |
|---|---|---|---|
| HXV13 | 다른 revision/Entry의 raw 6종 섞기 | 해당 BYTES_MISMATCH, V 0회 | L / R02 |
| HXV14 | raw bytes 손상·공백으로 H 불일치 | 해당 BYTES_MISMATCH, V 0회 | L / R02 |
| HXV15 | 값만 같은 A 복제본으로 loader 호출 | 원본 Entry identity 오류, V 0회 | L / R03 |
| HXV16 | 다른 호출 R과 A를 loader에 결합 | root binding 오류, V 0회 | L / R03 |
| HXV17 | H 재고정 후 Benefit b/금액/fp/dataset/Registry/scope만 A와 모순 | M2.71 기존 Benefit binding 오류들, V 0회 | L / R04 |
| HXV18 | H 재고정 후 Coverage i/의미/fp/scope 모순 | 기존 Coverage binding 오류들 | L / R05 |
| HXV19 | H 재고정 후 Policy r/Tree/dataset 모순 | 기존 Envelope binding 오류들 | L / R06 |
| HXV20 | Context baseline/scope 모순, nested scope는 내부적으로 합법 | 기존 Context binding 오류들 | L / R07 |
| HXV21 | Manifest dataset/member/edition/rule/Registry/ref 모순 | 기존 Manifest binding 오류들 | L / R08/R15 |
| HXV22 | 같은 Registry d version의 title 변경, A fp 유지 | Registry fp 오류 | L / R09 |
| HXV23 | V에 동일 값의 별도 A를 전달 | P0 기존 _selected_entry의 is 오류 | V(B) |
| HXV24 | V에 다른 R과 원본 A 전달 | P0 기존 root binding 오류 | V(B) |
| HXV25 | 다른 성공 호출의 policy/scope/edition을 부분 혼합 | 비교 값이 다르면 P1 identity 오류. 연도만으로 quarter 추론 안 함 | V(C) |
| HXV26 | revision 2 Benefit과 revision 1 Manifest 등 혼합 | P2 dataset 오류 | V(C) / R11 |
| HXV27 | 모든 loader 성공, Manifest source_versions가 실제 Registry와 다름 | P4 source version 집합 오류 | V(C) / R13 |
| HXV28 | 모든 loader 성공, 선택 ref의 Envelope domain fp 선언이 다름 | P3 Policy fp 관계 오류 | V(B+C) / R14 |
| HXV29 | 다른 Entry Policy/Registry path 또는 sha를 Manifest에 사용 | 정상 경로는 L; 직접 다른 반환 Manifest 혼합은 P3 기존 _bind 오류 | L / V(B) |
| HXV30 | 실제 Registry와 Context/Benefit/Manifest의 fp 교차 모순 | 정상 경로 해당 loader가 거부; 단독 혼합은 P4 실제 fp 관계 오류 | L / V(B+C) |
| HXV31 | 모든 loader 성공, Binding root가 실제 Policy에 없음 | P6 RULE_ROOT_NOT_FOUND | V(B) / R18 |
| HXV32 | 명시 completeness_review_ref가 Context에 없음 | P7 REVIEW_REF_NOT_FOUND. None인 정상 미선언과 구별 | V(B) / R19 |
| HXV33 | 명시 implementation_review_ref가 없거나 다른 종류 | P7 REVIEW_REF_NOT_FOUND / WRONG_REVIEW_TYPE | V(B) / R20 |
| HXV34 | 선택 Implementation Review의 같은 i / 다른 Inventory fp | P7 INVENTORY_FINGERPRINT_CONFLICT | V(B) / R21 |
| HXV35 | 같은 r / 다른 Tree fp | P7 POLICY_TREE_FINGERPRINT_CONFLICT | V(B) / R22 |
| HXV36 | 같은 r / 다른 subtree fp | P7 SUBTREE_FINGERPRINT_CONFLICT | V(B) / R22 |
| HXV37 | 선택 Review의 같은 dataset / 다른 Registry fp | P7 SOURCE_REGISTRY_FINGERPRINT_CONFLICT | V(B) / R23 |
| HXV38 | Inventory completeness Review의 같은 i / 다른 fp | P7 INVENTORY_FINGERPRINT_CONFLICT | V(B) / R21 |
| HXV39 | 같은 i/r/dataset의 두 성공 호출에서 Binding과 Review 혼합 | P7 REVIEW_RULE_ROOT_MISMATCH, condition도 기존 matcher 의미대로 | V(B) / R35 |
| HXV40 | 같은 Tree의 다른 Envelope와 Manifest를 혼합 | P3 Envelope domain fp 관계 오류 | V(B+C) / R36 |
| HXV41 | A의 Benefit fp까지 맞지만 Benefit d version이 Registry와 다름 | 여섯 loader 성공 가능, P4 source version 오류 | V(C) / R26 |
| HXV42 | Entry source original H와 Registry의 알려진 content_sha256 모순 | 여섯 loader 성공 가능, P5 source content 선언 오류 | V(C) / R29 |
| HXV43 | 동일 Coverage 구현 역할의 Context baseline과 E implementation H 모순 | P5 implementation 관계 오류. 실제 ZIP 실행 증명은 없음 | V(C) / R24 |
| HXV44 | M2.71의 Manifest engine H만 공유 합성 ZIP H와 다름 | C의 동일 역할 값은 맞으면 None 가능; 공유 profile 확인한 D가 차단 | D / R17 |
| HXV45 | A fp까지 맞지만 Benefit의 문법상 유효한 locator가 없음 | C는 locator 검사를 하지 않아 None 가능. 기존 source resolve가 LOCATOR_NOT_FOUND로 차단 | D(B 재사용) / R28 |
| HXV46 | refs/metadata가 있어도 claim 의미·실제 검토·source 사용 적격성 미확인 | C None을 D 성공으로 사용 금지, 운영 경로 중단 | D / R27/R28/R32/R34 |
| HXV47 | 올바른 source/ZIP 선언만 있고 실제 bytes/profile/실행 대응 없음 | 여덟 객체로 증명 못함, preparation 미완료. fake 성공 인자 없음 | D/U / R17/R30/R31 |
| HXV48 | 값·참조가 같은 다른 객체 출처 또는 이전 호출의 None 성공 반입 | 객체 값만으로 실제 decoder 실행 이력 탐지 불가, 운영 입력 경계에서 금지 | U / R01/R33 |
| HXV49 | 뒤 인자의 타입 오류와 A/R root 오류 동시 | 여덟 exact type 검사가 먼저, P0 타입 오류. Entry helper 0회 | V precedence |
| HXV50 | dataset 교차 모순과 missing root 동시 | P2 먼저, P6 호출0회 | V precedence |
| HXV51 | Envelope domain fp 모순과 source_versions 모순 동시 | P3 먼저, P4 호출0회 | V precedence |
| HXV52 | source_versions 모순과 implementation/source hash 모순 동시 | P4 먼저, P5 후속 비교0회 | V precedence |
| HXV53 | missing root와 missing Review ref 동시 | P6 먼저, P7 matcher0회 | V precedence |
| HXV54 | Inventory Review conflict와 Implementation root conflict 동시 | Inventory 전체 slot 오류 우선, Implementation matcher0회 | V / 기존 slot 순서 |
| HXV55 | 먼저 처리한 정상 STALE 또는 MISSING과 뒤 Binding의 same-version conflict | 정상 결과에서 조기 반환하지 않고 뒤 conflict를 그대로 전파 | V / guarded comparison |
| HXV56 | 첫 source content_sha256=None, 뒤 문서의 알려진 H 모순 | P5 뒤 행의 모순을 차단, None 행으로 전체 검사 생략 금지 | V precedence |

기존 모델 생성자가 이미 금지한 중복 Entry·부분 scope·불가능한 ref None 조합을 frozen 강제 변조로 만들지 않는다. 실제 값이 다르더라도 기존 Loader 단계에서 이미 거부되는 사례와, 모든 Loader가 성공한 뒤에 남는 C/D 사례를 분리해 기록한다.

## 18. Content Validator / Source Gate와 책임 분리

새 함수가 맡는 범위는 실제 공급 원본 간의 **관계**다. 아래 D를 우회하는 대체 gate가 아니다.

| 다른 책임 | 유지할 검사 / C가 하지 않는 것 |
|---|---|
| Content Validator | E의 정책+Benefit source 정확한 합집합, 5claim refs의 Snapshot membership/공식 대응, 역사 ACCEPTED 정의·검토 재현 요구, REVOKED effective target, 필요한 원문/Artifact bytes 전체 결합 |
| Source 구조·사용 | 원래 단위별 validate_evidence_refs/validate_envelope_sources/resolve, 존재·중복·policy 적용·ACTIVE, 문서/locator 각각 VERIFIED·명시 기준일/freshness |
| 전체 release | 모든 Envelope와 Registry·Manifest, engine 호환 역사 환경, 전역 rule ID 및 해당 raw 참조들. 선택 Envelope 검증으로 대체하지 않음 |
| 배포/실행 preparation | 공유 profile인지 실제 확인, Manifest 엔진 H/구현 H 대응, 실제 ZIP H 및 실행/import/환경. M2.53 합성 verify-only를 업무 실행 완료로 승격하지 않음 |
| 원문·실제 검토 | 실제 공식 bytes와 locator의 문장 의미·claim 지지·사람 수행/권한·불변 보관·이력 완전성 |
| Coverage/FULL 및 현재 Acceptance | 공식 producer·현 current 자료·명시 사용일·독립 same-version guards·기한·철회/정상 reason/factory |
| 사용자/Bridge/Cashflow | 개인 eligibility, 대상 월/병급/중복·수단·현금흐름 |

R17/R28/R30/R31의 C 이후 잔여 실패를 정상 검증 완료로 숨기지 않는다. 특히 has_evidence의 존재 확인을 source resolve 대신 쓰거나, source status를 ACTIVE로 바꿔 C/전체 validator를 통과시키지 않는다. D 미구현/자료 미확보이면 서비스/evaluator 진입은 계속 닫혀 있다.

향후 Content 구현은 같은 호출의 C를 한 번 연결해 이 문서의 관계 검사를 재사용할 수 있다. Content의 전체 자료/claim/검토 재현·Source 의무를 C의 None으로 면제하는 skip 옵션은 만들지 않는다. 이번 설계는 기존 Content의 11입력 후보나 evaluator의 8입력 계약을 수정하지 않는다.

## 19. 운영 orchestration 연결 계획

아래는 후속 연결 계획이다. 구현된 public 서비스 흐름으로 보고하지 않는다.

1. 신뢰된 준비자가 독립 기대 record 원본들과 immutable Review/companion raw bytes를 확보한다. metadata·지문을 LLM/사용자 선언으로 발급하지 않는다.
2. 기존 Review Artifact Loader로 R을 실제 복원한다. 원본 A를 명시 선택한다. 같은 호출에서 R/A/E를 고정한다.
3. 같은 A/R로 Benefit → Coverage → Envelope → ReviewContext → Manifest → Registry Loader를 실행한다. 실패 시 후속 호출은 없다.
4. **바로 그 여섯 반환 원본**으로 새 관계 함수를 1회 호출한다. 성공 None을 요청 간 보관/재사용하지 않는다.
5. 역사 Content Validator의 나머지 의무를 검증한다. 전체 역사 Manifest 비교가 필요하면 모든 Envelope와 호환 역사 환경을 확보한 D 경로에서 기존 validate_dataset_manifest를 호출한다. 누락을 한 정책/engine 상수 수정으로 우회하지 않는다.
6. 역사 Source 사용·실제 L3/권한·필요한 당시 FULL/ZIP 실행 근거를 확인한다. 기준일은 기존 Content 계약의 A.reviewed_at이며, 현재 사용 gate와 혼동하지 않는다. Source 구조 resolve의 ACTIVE 오류는 Content/source 단계에서 기존 의미대로 유지한다.
7. **현재 자료는 별도로** 확보·고정한다. M2.51에 따라 전체 current Manifest 검증 → 같은 current Coverage/Policy/Context의 공식 evaluate_eligibility_coverage 1회 → 같은 결과/Benefit/Envelope/Context/ref/Manifest/Registry/명시 data_use_date로 내부 Acceptance evaluator를 호출한다. 현재 source 구조/사용 gate는 기존 evaluator/source 계약 순서를 따른다.
8. 정상 Acceptance 결과 뒤에만 같은 current Benefit 원본으로 후속 candidate를 구성하고, 별도 개인/월/중복/유형 검증을 거쳐 Benefit Bridge/Cashflow로 진행한다.

즉 Content의 역사 전체 검증은 5단계 내부에 있고, 현재 전체 검증·공식 Coverage producer는 7단계에서 evaluator보다 앞선다. Source Gate와 release 검증을 일괄 “C가 수행했다”고 합치지 않는다. 역사 원본을 current version으로 덮어쓰지 않는다. Source Gate/Content/evaluator/adapter/Bridge의 미구현은 이번 작은 관계 함수의 구현 승인과 구별하며, 전체 운영 서비스 완료 조건으로는 계속 남긴다.

## 20. Coverage freeze 영향

Generic Coverage는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**를 유지한다. 새로운 CoverageResult/상태/필드·factory·public export·오류 의미·지문 payload를 만들지 않는다. 기존 root/소유/M/U와 matcher guarded 비교, Inventory 전체 slot→canonical Implementation slot 순서를 호출로 재사용한다.

정상 incomplete/STALE/MISSING을 모두 동일 오류로 승격하거나 M nonempty의 U facts를 새 Data Error로 바꾸지 않는다. C의 None은 Coverage FULL 판정이 아니다. 이미 구현된 official evaluator의 호출 계약이나 current adapter의 producer 1회 원칙은 바뀌지 않는다.

GV01~GV15 / BV01~BV16, Source parser/fingerprint, Historical Loader 여섯 종, Review Artifact Strict Loader, ZIP bootstrap, Acceptance/Benefit/Cashflow와 기존 M2.71 테스트·fixtures·hash 상수는 수정하지 않는다.

## 21. 미해결 사항과 Assumptions

**Assumption A1:** trusted 내부 orchestration이 실제 여섯 Loader를 같은 A/R로 실행하고 반환 객체를 그대로 연결한다. 이는 객체 타입이나 private 함수 이름이 제공하는 인증이 아니다.

**Assumption A2:** 입력은 정상 constructor/기존 strict loader를 거친 불변 원본이다. frozen 우회/악성 Python process/호스트 통제까지 방어하는 경계는 아니다.

**Assumption A3:** supplied Registry는 그 historical_source_registry_ref의 전체 원본이고 Manifest source_versions는 그 전체 문서 집합을 뜻한다. Envelope는 명시 선택한 정책 하나다. 이 두 범위는 서로 다르다.

작은 함수의 입력·순서·오류·None 의미에 남은 미정 사항은 없다. 다만 실제 raw 출처/원문/공식 의미·역사 환경/공유 profile·전체 release·Content/Source gate·운영 호출 결합은 별도 준비/구현 의무다. 여덟 객체에 없는 profile/bytes 증명을 요구하려고 bool·인자를 계속 늘리지 않는다. 해당 기능이 필요하면 D가 원재료를 확보하고 기존 계약에 따라 검사한다.

직접 private loader helper에 의존하는 것은 선택한 **내부 재사용**이다. public API로 승격하지 않고 기존 함수 변경 없이 호출한다. 다음 구현에서 실제 기존 함수와 계약이 달라진 증거가 나오면 그 차이를 보고하며 동결 코드를 즉시 수정하지 않는다. 지금 확인한 코드와의 충돌은 발견하지 않았다.

실제 Ansan은 **DRAFT / CONDITION_SLICE**, ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**를 유지한다. 새 실제 정책 지문·금액·Acceptance·Review·FULL/VERIFIED/USABLE·사용자 eligibility PASS·Cashflow 반영 결과를 만들지 않는다.

## 22. 최종 판단

**READY_TO_IMPLEMENT_CROSS_ARTIFACT_VALIDATOR**

기존 함수만 각각 호출하는 현재 운영 경로는 없고, 그 함수들만으로 구현 참조·원문 hash **선언**·선택 원본 관계가 모두 자동 연결되지는 않는다. 따라서 EXISTING_VALIDATORS_SUFFICIENT가 아니다. 필요한 것은 새 framework가 아니라 기존 `_selected_entry`/Manifest `_bind`/지문/구조/matcher와 여덟 입력의 최소 비교를 잇는 private 함수 한 개다.

Manifest engine H/profile 및 locator 의미·사용 적격성 등을 D로 명시했으므로 그 재료를 C 입력에서 추론하는 input contract 충돌도 없다. READY는 **이 제한된 관계 함수**의 구현 준비에만 적용된다. 전체 Content/Source/release/Acceptance/서비스 구현 준비 완료 판정이 아니다.

## 23. 다음 최소 작업 한 개

**M2.73 — Historical Cross-Artifact Validator 구현**을 권고한다. 승인 후 이 문서의 여덟 입력 private 함수 한 개와 신규 단위/연결 테스트를 추가한다. 기존 M2.71 definitions/prepare/restore를 우선 재사용하고 기존 테스트/fixture/기대값은 수정하지 않는다.

Definition of Done: 실제 helper를 호출하는 P0~P8, 여덟 새 prefix와 기존 예외 객체 전파, 같은 원본 인자·helper 횟수·경계별 미호출, HXV01~HXV56의 해당 L/V/D/U 구분, 100회 결정성·불변성, 기존 10,786개/GV/BV/freeze 및 release 보존을 검증한다. 시나리오를 실제 실행 가능 사례/운영 경계 사례로 나누고 D/U를 C의 통과 실적으로 계산하지 않는다.

Content Validator·Source Gate·전체 release/실행물·evaluator·Bridge/Cashflow를 이 작업에 함께 구현하지 않는다. 새로운 Historical 모델·capability token·범용 validation framework도 추가하지 않는다.

## 부록 A. 작업 검증·보존 기록

- 사전 actual 전체 pytest: **10,786 passed in 90.31s**. 실패/skip/timeout 0회.
- 사후 actual 전체 pytest: **10786 passed in 62.12s (0:01:02)**. 사후 전체 최초 실행 통과. failed/skipped/timeout 0회, 재실행 0회
- 신규 실행 테스트: **0개**. 56개 수동 시나리오와 문서 검수를 실행 테스트 수에 더하지 않는다. 기존 테스트·fixture·기대값·timeout 설정 변경 0개.
- 기존 보호 파일 **199개 전부 SHA256 동일**. 코드·테스트·fixture·기대값·기존 명세 수정/삭제 **0개**. 새 문서 **1개**만 추가하여 최종 **200개**다. 실제 release 6개는 별도 기준선으로 SHA256·크기·mtime_ns 모두 동일하다.
- GV01~GV15 / BV01~BV16 / Coverage freeze / 여섯 Historical Loader / Review Artifact Loader / ZIP bootstrap / Acceptance/Benefit/Cashflow: **기존 파일 SHA·기대값 보존, 기존 10,786개 전체 회귀 통과**.
- 실제 release 6개 SHA256·크기·mtime_ns: **6개 전부 SHA256·크기·mtime_ns 동일**.

| data/releases/ 기준 파일 | 전후 SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | `4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f` |
| ansan-youth-2026-10-20-001/sources.json | `a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b` |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | `9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025` |
| ansan-youth-2026-10-20-002/README.md | `8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99` |
| ansan-youth-2026-10-20-002/sources.json | `711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620` |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | `d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92` |

문서 검수: 23개 본문 절, R01~R36 분류 및 HXV01~HXV56의 연속/유일성, 표 열 수·코드 fence·API 인자8개·8개 새 prefix·한국어/UTF-8을 확인한다. 이 검수는 미구현 함수를 실행했다는 증거가 아니다.

## 부록 B. 최종 보고 24항목 요약

| 항목 | 결과 |
|---|---|
| 1 새 문서 | docs/HISTORICAL_CROSS_ARTIFACT_VALIDATOR_CONTRACT.md 한 개 |
| 2 M2.71 모순 | 2절 R01~R36, 특히 source 집합/Envelope domain/Binding·Review/source version·hash 선언 |
| 3 Loader 차단 관계 | 3절 raw H·A binding. 변경 없음 |
| 4 운영 누락 관계 | 8~12절의 실제 원본 관계와 기존 함수 호출 결합 |
| 5 재사용 | 4절 기존 selector/Manifest bind/지문/구조/Review matcher·resolver/get_source |
| 6 새 함수 필요 | 최소 private 조립 함수 한 개 필요, framework 불필요 |
| 7 Pure API | 13절 필수 keyword-only8개, None / PolicyDataError |
| 8 Same-call | 6~7절: 기존 loader 실제 실행과 반환 원본 직접 연결 필수 |
| 9 Dataset | 8절 actual 객체 및 A 축. Coverage의 가상 dataset 필드 없음 |
| 10 Policy/Rule | 9절 selected Envelope domain + P6/P7 기존 구조/지문 |
| 11 Registry | 10절 실제 domain fp/전체 source ID·d version, 별도 Registry ID/version 없음 |
| 12 ArtifactReference | 11절 path+sha 기존 bind, 같은 구현 역할 및 원문 hash 선언 비교 |
| 13 Review | 12절 기존 guards, 정상 STALE/MISSING 보존, FULL 판정 없음 |
| 14 Error/precedence | 14~15절 새 prefix8개 + 기존 예외 원본, P0~P8 |
| 15 수동 합성 | 56개, 신규 실행0개 |
| 16 코드/테스트 변경 | 0개. 기존 명세 수정0개 |
| 17 전체 pytest | 사전 10,786 passed / 사후 10786 passed in 62.12s (0:01:02) |
| 18 회귀/GV/BV | 기존 파일 SHA·기대값 보존, 기존 10,786개 전체 회귀 통과 |
| 19 실제 releases | 6개 전부 SHA256·크기·mtime_ns 동일; 부록 A에 여섯 H 기록 |
| 20 Coverage freeze | 기존 동결 유지, 상태·payload·API·오류 의미 변경 없음 |
| 21 ResidenceHistory | OFFICIAL_INQUIRY_REQUIRED 유지 |
| 22 남은 책임 | Content·Source·전체 release·원문/ZIP 실행/실제 검토·current evaluator·Bridge |
| 23 최종 판단 | READY_TO_IMPLEMENT_CROSS_ARTIFACT_VALIDATOR, 제한된 함수 구현 준비 |
| 24 다음 작업 | M2.73 private 함수 한 개 및 신규 검증 구현, 그 외 계층은 제외 |

## 24. M2.73 — IMPLEMENTED: Historical Cross-Artifact Validator

### 24.1 파일·실제 API

추가한 운영 모듈은 `backend/policy_engine/policy_data/historical_cross_artifact_validator.py`, 신규 테스트는 `tests/test_historical_cross_artifact_validator.py`다. 기존 문서 수정은 이 문서의 현재 상태 안내/24절과 ARCHITECTURE의 구현 기록뿐이다. 13절의 파일 경로는 후보였으며 이번 구현 지시의 권장 파일명을 택했다. 함수명·인자·계약은 그대로다.

실제 함수 `_validate_historical_artifact_relationships`는 13절과 동일한 **필수 keyword-only8개**, exact domain type, nullable/default/override 없음, 성공 `None`, 불일치 `PolicyDataError`다. 모듈에 신규 함수는 이 내부 함수 한 개뿐이다. 공개 export·새 모델·service class·HTTP·새 Loader·새 오류 타입은 없다.

### 24.2 구현한 P0~P8과 기존 helper

- P0: API 순서로 exact type8개 전부 확인 후 기존 Manifest `_selected_entry`1회. ACCEPTED/root/명시 ref/유일 Entry/`entry.acceptance is A`를 재사용한다.
- P1: policy ID4개 → scope3개 → Envelope edition. P2: Benefit 대 A → Envelope → Context → Manifest dataset 순서다. Coverage에 없는 dataset/Registry 필드를 추가하지 않는다.
- P3: 기존 Manifest `_bind`1회로 membership/edition/rule/Registry 및 Policy·Registry의 **path+sha** 검사를 원래 순서대로 호출한다. 그 뒤 실제 선택 Envelope metadata와 기존 `fingerprint_policy_envelope`1회를 비교한다.
- P4: 기존 Registry fp1회, Benefit→Context→Manifest baseline, 전체 source ID/d version 집합, Envelope→Benefit→Entry 원문 binding 순서다. get_source는 status를 바꾸거나 ACTIVE를 강제하지 않는다.
- P5: Context의 Coverage 구현 fp 대 같은 E의 implementation 참조 H, 이어 알려진 원문 content H 선언을 비교한다. P4에서 조회한 Entry의 원본 SourceDocument를 로컬에 보존해 P5에서 재사용한다. global cache는 없다. content_sha256=None인 행이 뒤 오류를 숨기지 않는다.
- P6: 기존 `_analyze_coverage_structure`1회. P7: Inventory fp→Tree fp→canonical 원본 subtree fp 전부 계산 후 Inventory matcher1회→canonical Binding별 Implementation matcher1회다. resolver는 matcher 내부에서 호출하며 별도 ref pre-pass가 없다.
- P8: 모든 해당 비교 뒤 정확히 None. 기존 helper 예외 객체는 그대로 전파하며 RuntimeError 같은 예상 밖 오류도 삼키지 않는다. 정상 MISSING/STALE을 Data Error로 승격하지 않는다.

새 prefix는 14절의 **8개만**이다. 표기/field/message와 P0~P8을 테스트에서 고정했다. P3의 ArtifactReference 비교가 P4보다 먼저인 기존 binding 순서도 유지한다. schema/edition 일부 방어 분기는 exact 생성자와 P1/P3a를 통과한 정상 객체에서는 독립적으로 도달할 수 없으므로, 해당 분기를 위해 frozen 값을 강제 훼손하지 않았다.

### 24.3 36개 관계의 구현 추적

아래 문자열은 **테스트 문서화용 분류**다. 운영 Enum/인증 모델이 아니다. 신규 테스트의 RELATION_CLASSIFICATION과 같은 기본 분류이며, 하나의 관계에 있는 provenance/외부 의미 경계는 2절과 아래 주석을 함께 따른다.

| 관계 | 분류 | 이번 실행·책임 대응 |
|---|---|---|
| R01 | ALREADY_GUARDED | 실제 Review Loader와 M2.71 raw20/root 회귀. typed 객체 출처 인증은 별도 NOT_OBSERVABLE |
| R02 | ALREADY_GUARDED | 기존 M2.71의 다른 Entry/revision·손상 bytes 거부 회귀 유지 |
| R03 | CROSS_VALIDATED | 원본 A 복제/다른 R를 P0 기존 Entry helper로 거부 |
| R04 | ALREADY_GUARDED | 기존 Benefit Loader binding 회귀 유지 |
| R05 | ALREADY_GUARDED | 기존 Inventory binding 회귀 유지, Binding은 별도 P6/P7 |
| R06 | ALREADY_GUARDED | 기존 Envelope Tree binding 회귀 유지 |
| R07 | ALREADY_GUARDED | 기존 Context baseline binding 회귀 유지 |
| R08 | ALREADY_GUARDED | 기존 Manifest Loader 회귀와 같은 _bind 재사용 |
| R09 | ALREADY_GUARDED | 기존 Registry Loader fp 회귀 유지 |
| R10 | CROSS_VALIDATED | P1 각 identity와 다중 오류 순서 |
| R11 | CROSS_VALIDATED | P2 필드별·다중 dataset/다른 실제 revision 혼합 |
| R12 | CROSS_VALIDATED | 실제 Registry fp 대 세 baseline의 순서 |
| R13 | CROSS_VALIDATED | source 집합 누락·추가·다른 version 거부, 원래 순서 보존 |
| R14 | CROSS_VALIDATED | 같은 Tree의 다른 Envelope/잘못된 Manifest domain fp 거부 |
| R15 | CROSS_VALIDATED | Policy/Registry의 path만·sha만 변경한 네 조합을 기존 prefix로 거부 |
| R16 | DEFERRED | 과거 engine_version 보존. 전체 validator의 호환 역사 환경은 D |
| R17 | DEFERRED | Manifest engine H와 Coverage 구현 H의 전역 equality 없음 |
| R18 | CROSS_VALIDATED | missing root 거부·원본 node 전달, 정상 partial Coverage 보존 |
| R19 | CROSS_VALIDATED | 명시 Inventory ref 없음/종류 오류와 정상 미선언 구별 |
| R20 | CROSS_VALIDATED | Implementation ref 없음/종류/condition/root 오류 |
| R21 | CROSS_VALIDATED | Inventory/Implementation Review의 같은 i 지문 모순 |
| R22 | CROSS_VALIDATED | 같은 r의 Tree/subtree 모순과 canonical 순서 |
| R23 | CROSS_VALIDATED | 같은 dataset의 Registry 지문 모순 |
| R24 | CROSS_VALIDATED | 정상 과거 implementation STALE 보존, Context 대 E의 같은 구현 역할 H 비교 |
| R25 | CROSS_VALIDATED | 역사 record 공존·명시 선택. 별도 opaque Review 증거 bytes는 D |
| R26 | CROSS_VALIDATED | Envelope/Benefit/Entry 각각의 실제 문서 version |
| R27 | DEFERRED | source 정확한 합집합·claim 대응은 Content 책임 |
| R28 | DEFERRED | locator 존재·ACTIVE/policy/중복은 source/Content 책임 |
| R29 | CROSS_VALIDATED | 알려진 원문 H 선언 거부, None 보존·뒤 행 검사 |
| R30 | DEFERRED | 실제 공식 원문 bytes 해시/내용 검증은 미구현 |
| R31 | DEFERRED | 실제 production ZIP profile/실행 대응은 미구현 |
| R32 | DEFERRED | Evidence/5claim 의미·실제 사람 검토 인증 없음 |
| R33 | CROSS_VALIDATED | 정상/오류 각각100회 결정성·입력 snapshot/identity 불변 |
| R34 | DEFERRED | 역사 DRAFT/SUPERSEDED/WITHDRAWN 보존만 확인, 사용 승인 없음 |
| R35 | CROSS_VALIDATED | 두 성공 호출의 같은 i/r/dataset Binding·Review 혼합 거부 |
| R36 | CROSS_VALIDATED | 같은 Tree의 다른 Envelope/Manifest 혼합 거부 |

기본 분류 합계는 ALREADY_GUARDED8 / CROSS_VALIDATED20 / DEFERRED8이다. 별도 NOT_OBSERVABLE 시험은 값이 같지만 다른 여섯 객체를 주입해 None이 가능함을 확인하며, 이를 raw decoder 실행 증명으로 세지 않는다.

### 24.4 HXV01~HXV56 실행 대응

M2.71의 definitions/prepare/restore를 **테스트에서만 import해 재사용**한다. fixture 저작 중 Registry metadata를 바꿀 때 실제 기존 parser/fp와 종속 A/Context/Manifest/H를 다시 작성하며, 소비 함수의 보정이나 가짜 hash 우회가 아니다. 새 함수는 실제 여섯 Loader의 반환 원본을 받는다.

| 수동 ID | 대응 / 실행 범위 |
|---|---|
| HXV01~03 | exact API/None·원본 helper 인자/호출 순서·multi-entry 양방향/명시 revision·역사 record 공존 |
| HXV04~05 | 일관되게 저작한 ACTIVE/SUPERSEDED/WITHDRAWN, DRAFT/확인일 None 보존. Source Gate 완료 아님 |
| HXV06~07 | 실제 matcher MISSING/STALE 반환을 관찰하고 새 함수가 None으로 끝남. FULL/사용 승인이 아님 |
| HXV08 | 다중정책 Manifest에서 첫 원소가 아닌 선택 정책만 검사. 다른 Envelope/전체 release 검증 없음 |
| HXV09~11 | historical engine version/optional 원문 H/여러 근거·공유 source·source tuple 순서 보존. 미사용 Source가 포함된 전체 Registry의 정상 집합도 확인 |
| HXV12 | 정상/오류 각각100회 입력 snapshot·is·결정성. 반복 횟수는 테스트 수에 합산하지 않음 |
| HXV13~22 | 변경 없는 M2.71의 기존 raw/domain binding 거부 사례를 ALREADY_GUARDED로 재사용. 새 함수의 raw 검증 실적으로 중복 계상하지 않음 |
| HXV23~24 | 값만 같은 원본 A 복제/다른 R를 실제 기존 Entry helper 오류로 거부 |
| HXV25~26 | 정상 constructor로 만든 단독 혼합 객체 및 실제 다른 revision의 반환값. P1/P2 필드·비교 순서 확인 |
| HXV27~28 | **여섯 loader 모두 성공** 후 source 집합/Envelope domain fp 모순 거부 |
| HXV29~30 | 기존 Manifest 참조 path/sha 각각 거부 및 actual Registry fp baseline별 모순. 단독 주입 시험을 raw 출처 시험과 구별 |
| HXV31~38 | **여섯 loader 모두 성공** 후 missing root/ref·wrong review type·같은 i/r/dataset의 Inventory/Tree/subtree/Registry 모순 거부 |
| HXV39~40 | 두 실제 성공 호출의 Binding/Review 및 같은 Tree의 다른 Envelope를 혼합해 거부 |
| HXV41~43 | **여섯 loader 모두 성공** 후 Envelope/Benefit/Entry 문서 version, 원문 H 선언, 구현 참조 H 모순 거부 |
| HXV44 | Manifest 엔진 H만 다른 경우 C None 가능함을 실행. 실제 profile/ZIP 대조는 DEFERRED이며 실패를 사용 승인으로 낮추지 않음 |
| HXV45 | 없는 Benefit locator에서 C None 뒤 기존 validate_evidence_refs가 LOCATOR_NOT_FOUND. source 검증 책임이 남아 있음을 실행 |
| HXV46~47 | Content/Source/실제 원문·ZIP 의미·실행은 DEFERRED. purity/dependency 경계와 합성 None만 확인하며 실제 외부 검토를 실행했다고 세지 않음 |
| HXV48 | 동등하지만 별도 여섯 모델 주입 시 None 가능. raw 출처는 NOT_OBSERVABLE |
| HXV49~54 | 실제 다중 오류의 P0~P7 우선순위·뒤 helper 미호출 및 Inventory slot 우선 |
| HXV55~56 | 정상 MISSING/STALE 뒤 다른 Binding conflict 및 content_sha256=None 뒤 알려진 H conflict가 숨겨지지 않음 |

신규 **157개 parameterized 실행**이며 56개 수동 ID/36개 분류/반복 횟수를 더하지 않는다. 기존 M2.71의 81개 및 raw/모델 거부는 기존 회귀 수에 포함한다.

### 24.5 순수성·신뢰 경계·남은 구현

실제 helper를 관찰해 선택 Entry1 / Manifest bind1 / Envelope fp1 / Registry fp1 / 구조 분석1 / Inventory fp1 / Tree fp1 / root당 subtree fp1 / Inventory matcher1 / Binding당 Implementation matcher1을 확인했다. 원본 Binding/node/Context/A/R 인자를 그대로 전달한다. source 조회는 Envelope→Benefit→Entry 각2개인 기본 fixture에서6회이며 P5는 조회한 원본 문서를 재사용한다. sentinel PolicyDataError/RuntimeError와 실제 source 예외의 객체 identity도 보존한다.

filesystem·환경변수·시각·난수·network·subprocess를 차단한 실제 호출, source AST의 단일 private 함수/새 runtime 모델·금지 import·전체 validator/evaluator 호출 부재를 확인했다. 새 함수는 raw bytes·ZIP·공식 원문을 읽지 않는다. 입력 원본을 수정하거나 전역 mutable cache를 두지 않는다.

**IMPLEMENTED:** 순수 관계 함수 / 직접 가능한 여섯 원본 교차 비교 / 기존 helper 재사용 / 실제 loader 성공 뒤 모순 차단 / 정상 MISSING·STALE 및 역사 metadata 보존 / 결정성·불변성 테스트.

**NOT IMPLEMENTED:** Production same-call orchestration / 전체 release contents verification / Official Source 원문 검증 / Source Gate / Review Content Validator 전체 구현 / production ZIP 실행 검증 / Historical FULL_POLICY / Acceptance evaluator 연결 / Benefit Bridge·Cashflow 연결 / API/UI.

테스트의 restore_specs는 합성 저작·연결 helper일 뿐 새 운영 orchestration이 아니다. 여섯 원본의 실제 source bytes 검증을 typed 객체만으로 재증명하지 못한다. Same-call 운영 진입 경계가 연결되기 전 외부 API에서 이 함수의 None을 승인 증거로 받아서는 안 된다.

### 24.6 실행·보존 기록

- 사전 actual 전체: **10,786 passed in 76.36s**.
- 신규 첫 실행: **147 passed in 2.40s**. 실패/timeout0회.
- 비교 순서/정상 Registry 집합 경계10개 추가 후 신규 최종: **157 passed in 2.29s**. 실패/timeout0회. 기존 테스트·fixture·기대값 수정0개.
- 사후 actual 전체: **10943 passed in 64.04s (0:01:04)**. 사후 전체 최초 실행 통과. failed/skipped/timeout 0회, 재실행 0회
- 기존 보호 파일200개 중 **198개 SHA256 동일**, 수정2개는 승인된 계약/Architecture 문서뿐이다. 신규 운영 모듈/테스트2개를 추가해 최종 **202개**, 삭제0개다. 기존 코드·테스트·fixture·기대값·export·설정은 모두 보존했다. 기존 **10,786개 + 신규 157개 = 10,943개**가 전체 회귀에서 모두 통과했다.
- GV01~GV15 / BV01~BV16 / Coverage freeze / Historical Loader6 / M2.71 통합81 / Review Artifact Loader / ZIP bootstrap / Acceptance/Benefit/Cashflow: **기존 파일 SHA·기대값 보존, 기존 10,786개 전체 회귀 통과**.
- 실제 release6개 SHA256·경로·크기·mtime_ns: **6개 전부 SHA256·경로·크기·mtime_ns 동일**. 여섯 hash 값은 부록 A에 보존된 값과 동일하다. 실제 source·정책·금액·Review·Acceptance 자료는 생성/변경하지 않았다.

### 24.7 최종 판단과 다음 최소 작업

**HISTORICAL_CROSS_ARTIFACT_VALIDATOR_COMPLETE**.

M2.72에서 확정한 원본 간 모순을 내부 운영 모듈의 순수 함수로 차단하며, 이미 보장되는 raw codec/모델/동결 Coverage를 변경하지 않았다. 구현 완료는 이 함수의 한정된 책임에만 적용된다. 실제 정책 검증·현재 사용 승인·Cashflow 연결 완료가 아니다.

다음 최소 작업은 **실제 same-call orchestration의 선행 조건 계약 설계 한 개**다. 독립 기대 원본/raw6종의 확보 → 실제 Review/여섯 Loader → 원본 직접 전달 → 관계 함수 → Content/Source/전체 release 준비로 이어지는 진입·실패·미확보 경계를 정한다. 새 인증 token/도메인 모델/범용 framework나 다른 운영 기능을 함께 구현하지 않는다.

ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, 실제 안산 **DRAFT / CONDITION_SLICE**, Generic Coverage **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**를 유지한다.

### 24.8 최종 보고 28항목 요약

| 항목 | 결과 |
|---|---|
| 1 구현 요약 | 내부 순수 관계 검증 함수 한 개 |
| 2 파일 | 운영 모듈/테스트2개 신규, 승인된 계약/Architecture 문서2개 수정 |
| 3 API | 13절의 exact type·필수 keyword-only8개, None / PolicyDataError |
| 4 A/R identity | 기존 selector1회, E.acceptance is A |
| 5 36개 관계 | 24.3절 ALREADY_GUARDED8/CROSS_VALIDATED20/DEFERRED8 및 별도 NOT_OBSERVABLE 경계 |
| 6 helper | selector/Manifest bind/기존 지문/구조/Review matcher·내부 resolver/get_source |
| 7 Dataset | Benefit/A→Envelope→Context→Manifest, Coverage 가상 필드 없음 |
| 8 Policy/Rule | P1 target/scope/edition 및 P6/P7 기존 구조·원본 roots |
| 9 Manifest/Policy | 기존 binding 후 선택 Envelope metadata/domain fp |
| 10 Registry | 실제 fp·전체 문서 ID/d version 집합, binding 순서 |
| 11 ArtifactReference | 기존 path+sha, 같은 Coverage 구현 역할 및 알려진 원문 H 선언 |
| 12 Review | 명시 ref·condition/root·독립 same-version guards 재사용 |
| 13 MISSING/STALE | 기존 정상 의미 유지, 뒤 모순은 계속 거부 |
| 14 오류/순서 | 8개 새 prefix·P0~P8, 기존 예외 객체 전파 |
| 15 합성 테스트 | 정상·오류·경계·다중 오류·helper identity/count·순수성 |
| 16 M2.71 모순 | 24.4절: loader6 성공 후 C 모순 거부와 D 경계 분리 |
| 17 provenance | 객체만으로 raw 출처 인증 불가, 운영 orchestration 미구현 |
| 18 신규 테스트 | 157개, 수동56·반복 횟수와 구별 |
| 19 전체 pytest | 사전 10,786 passed / 사후 10943 passed in 64.04s (0:01:04) |
| 20 기존 회귀 | 기존 파일 SHA·기대값 보존, 기존 10,786개 전체 회귀 통과 |
| 21 GV/BV | 기존 값/파일 SHA 보존 및 전체 회귀 통과 |
| 22 releases | 6개 전부 SHA256·경로·크기·mtime_ns 동일, 부록 A의 실제 H 유지 |
| 23 Coverage freeze | 기존 API·상태·지문·오류·helper semantics 보존 |
| 24 ResidenceHistory | OFFICIAL_INQUIRY_REQUIRED |
| 25 실제 정책 | DRAFT / CONDITION_SLICE |
| 26 남은 책임 | Content/Source/전체 release/원문/실제 ZIP 실행/FULL/evaluator·Bridge·Cashflow |
| 27 최종 판단 | HISTORICAL_CROSS_ARTIFACT_VALIDATOR_COMPLETE |
| 28 다음 최소 작업 | same-call orchestration 선행 조건 계약 설계 한 개 |
