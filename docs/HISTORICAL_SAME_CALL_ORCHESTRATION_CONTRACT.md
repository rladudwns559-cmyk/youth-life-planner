# M2.74 — Historical Same-Call Orchestration Prerequisite Contract

**현재 구현 상태 — M2.75:** 이 계약의 내부 순수 orchestrator와 합성 테스트를 구현했다. 실제 API·호출·검증 결과와 남은 경계는 **23절**이다. 1~22절 및 부록A/B의 설계 당시 상태·검증 기록은 M2.74 이력으로 보존한다. 현재 구현 상태는23절이 우선한다.

작성일: 2026-10-24 / Asia/Seoul. **설계 문서만 추가**한다. 아래 함수는 아직 구현하지 않았다.

최종 판단: **READY_TO_IMPLEMENT_HISTORICAL_SAME_CALL_ORCHESTRATOR**. 합성 입력을 받는 작은 순수 연결 함수의 구현 준비 판단이다. 실제 파일 준비·전체 release·공식 원문·production ZIP 실행·Content 전체·현재 사용 판정의 완료를 뜻하지 않는다.

## 1. 목표와 확인 근거

한 번의 내부 호출에서 Review Artifact strict 복원 → 선택 Acceptance 결합 → Historical Loader 6종 → 기존 교차 검증을 순서대로 반드시 실행하고, 모두 성공한 원본만 함께 반환하는 계약을 정한다. 새 검증 알고리즘·도메인 모델·상태·인증 토큰은 만들지 않는다.

이 문서에서 **A**는 명시 선택한 원본 `PolicyBenefitAcceptance`, **R**은 이번 호출의 Review Loader 반환 원본, **E**는 R에서 A에 대응하는 원본 Entry다. `expected_acceptances`는 R 전체에 대응하는 외부 원본 기록들의 tuple이며 현재 한 target의 Context와 다르다.

| Source of Truth / 실제 확인 파일 | 적용 사항 |
|---|---|
| HISTORICAL_CROSS_ARTIFACT_VALIDATOR_CONTRACT.md 13~24절, historical_cross_artifact_validator.py 및 해당 tests | 구현된 필수8입력·None·기존 helper·P0~P8·오류 전파·36관계·raw 출처 한계 |
| HISTORICAL_SIX_ARTIFACT_INTEGRATION_REPORT.md, test_historical_six_artifact_integration.py | 합성 저작/원본 보존·raw20/root·실제 로더6·독립 H·TEST_ONLY ZIP 한계 |
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md 5~6·17~20절 | 후속11입력 후보·전체 envelopes/원문 필요·같은 R/A·Content None과 사용 판단 분리 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md 4~7·15~17·30절 | content-addressed ref·외부21필드 원본과 raw20·Entry/Artifact 불변성 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md 14~23·37절 | ACCEPTED/REVOKED·binding·날짜·외부 발급/이력 신뢰 |
| BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md 12~19·24~27·35절, 실제 Context/resolver | 명시 ref·원본 is·직접 철회·완전성 한계 |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md 2~4절 | 준비 A/순수 계산 B/같은 호출 C·현재8입력 후보·현재 사용일 분리 |
| RELEASE_ARTIFACT_EXECUTION_BINDING_SPEC.md 6~13절 | import 전 ZIP/환경 검증·실제 실행 대응·새 공유 profile 한계 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md, ARCHITECTURE.md 62절 | frozen core·actual slice/공식 문의·운영 same-call 미구현 |
| benefit_acceptance_review_artifact_loader.py 및 test_benefit_acceptance_review_artifact_loader.py | 실제 함수명·정확한2입력·전체 records 집합·원본 결합·내부 오류 순서 |
| historical_benefit_snapshot_loader.py / historical_eligibility_coverage_loader.py / historical_policy_envelope_loader.py / historical_coverage_review_context_loader.py / historical_dataset_manifest_loader.py / historical_source_registry_loader.py 및 각 tests | 실제6함수 정의·exact3입력·선택 참조 SHA·strict 복원·직접 binding·순수성 |

문서 이름은 지시된 실제 경로와 일치한다. Review 로더의 실제 모듈명은 **benefit_acceptance_review_artifact_loader.py**다. `acceptance_review_artifact_loader.py`라는 별도 파일은 없다. Historical 모듈은 backend/policy_engine/policy_data 아래, 테스트는 tests 아래다.

## 2. M2.73 이후의 운영 연결 공백

이미 구현된 것은 Review strict bytes 복원, Historical 6종의 원본 SHA/직접 binding/strict 복원, 여섯 typed 원본 사이의 교차 관계 검증과 합성 통합 회귀다. M2.73은 값이 같은 별도 여섯 객체를 받아도 관계가 맞으면 None일 수 있음을 시험했다. typed 인자만으로 로더 실행 이력을 관찰할 수 없기 때문이다.

따라서 외부 typed 객체·과거 None 성공·일부 로더 결과를 받는 adapter로 연결하면 검증 생략과 revision 혼합이 가능하다. 이번에는 **허용 입력과 고정 실행 경로**로 그 정상 호출 경로를 닫는다. 같은 테스트 함수 안에서 순서대로 호출한 것만으로 운영 진입 경계가 구현됐다고 보고하지 않는다.

실제 파일 확보·전체 release·공식 Source 원문·production 실행 ZIP·Content 전체·Source Gate·Acceptance evaluator·Benefit Bridge/Cashflow 연결은 여전히 미구현이다. 이번 문서도 orchestration의 구현 자체는 아니다.

## 3. Same-call 정의와 최종 최소 API

Same-call은 **아래 함수 한 번의 동기 호출**이다. 그 호출에 공급된 원본 A, R 전체의 독립 expected 기록 tuple, Review raw bytes와 역할별 raw6, 그 bytes에서 실제 로더가 반환한 R/객체6, 그 A/R/객체6를 검사한 기존 교차 validator가 하나의 로컬 실행 흐름에 묶인다. 다른 요청의 객체·검증 결과를 끼워 넣는 입력은 없다.

후속 위치는 `backend/policy_engine/policy_data/historical_artifact_orchestration.py`, private 함수명은 아래로 정한다. **이번에는 파일/함수/export를 생성하지 않는다.** 정확히9개 필수 keyword-only 인자이며 default·nullable·추가 옵션이 없다.

```python
def _orchestrate_historical_artifact_validation(
    *,
    expected_acceptance: PolicyBenefitAcceptance,
    expected_acceptances: tuple[PolicyBenefitAcceptance, ...],
    review_artifact_raw_bytes: bytes,
    benefit_raw_bytes: bytes,
    coverage_raw_bytes: bytes,
    policy_envelope_raw_bytes: bytes,
    coverage_reviews_raw_bytes: bytes,
    dataset_manifest_raw_bytes: bytes,
    source_registry_raw_bytes: bytes,
) -> tuple[
    AcceptanceReviewArtifact,
    tuple[
        BenefitSnapshot,
        EligibilityCoverage,
        PolicyEnvelope,
        CoverageReviewContext,
        DatasetManifest,
        SourceRegistry,
    ],
]: ...
```

위 표기는 계약상 서명이며 실행 구현은 아니다.

`expected_acceptance`는 선택 원본 A를 명확히 지정하고, 복수 Entry R에 필요한 `expected_acceptances`는 전체 원본들을 제공하므로 중복 인자가 아니다. A를 tuple 위치·최대 version·날짜로 추론하지 않는다. A가 그 tuple 안의 **동일 객체**여야 한다는 조건은 P0c에서 기존 Entry helper로 확인한다.

skip_validation/trust_preloaded_objects/allow_partial/ignore_mismatch/force_verified/force_usable/use_latest/fallback_revision·callback·loader 주입·preloaded 결과·별도 expected SHA 입력은 없다. 누락/extra/positional 인자는 Python의 기본 TypeError이며 함수 본문은 실행되지 않는다.

## 4. Review Artifact 선행 조건과 A/B 진입점 비교

실제 기존 API는 다음2개 필수 keyword-only 인자다.

```python
load_acceptance_review_artifact_bytes(
    *, raw_bytes: bytes,
    expected_acceptances: tuple[PolicyBenefitAcceptance, ...],
) -> AcceptanceReviewArtifact
```

- raw는 exact bytes, records는 exact 비어 있지 않은 tuple, 각 원소는 exact PolicyBenefitAcceptance다. subtype/dict/list/coercion은 거부한다.
- 모든 외부 record의 review_artifact_ref는 정확한 `acceptance-review:sha256:<lowercase hex64>`이고 같아야 한다. acceptance_ref 및 target/scope/benefit/a-version은 각각 유일해야 한다.
- 기대 root H는 외부 원본 record ref에서 온다. 같은 raw 전체 SHA → BOM/UTF-8 → strict JSON/수치/중복/Unicode → schema → canonical bytes → 기존 모델 → 전체 expected 결합 순서다.
- raw root는 schema_version/entries의2key, Entry acceptance는 **review_artifact_ref 없는20key**다. 외부 A는 최종 ref를 포함한21필드 원본이다. 전체 raw20 비교 후 Entry.acceptance를 해당 expected 원본으로 결합한다.
- R에 있는 ref 집합과 expected 전체 ref 집합이 같아야 한다. unlisted → missing → raw20값 불일치 순서도 기존 로더가 담당한다. selected A만 보내서 나머지 Entry를 무시할 수 없다. expected tuple 순서와 R.entries 순서는 같을 필요가 없고 원래 Entry 순서를 보존한다.
- 여러 target/revision 및 구조적으로 유효한 REVOKED Entry도 R 안에서 복원 가능하다. 이 사실이 선택 A의 ACCEPTED 요구나 현재 사용 판정을 없애지 않는다.

| 진입점 | 실제 가능성·이점 | 신뢰 한계·결정 |
|---|---|---|
| A: 외부에서 복원한 A/R + raw6 | 후보8입력, 외부가 같은 Review 로더를 올바르게 썼다면 가능 | 동일 값의 직접 생성 R도 API로 들어오므로 R raw 복원 이력을 강제하지 못한다. 별도 wrapper 선행 조건이 필요해 이번 단일 경계의 최종안으로 선택하지 않음 |
| B: 원본 A/전체 expected + Review raw + raw6 | 실제 기존 Review 로더가 I/O 없이 이 입력만으로 R을 복원한다.9입력, Review까지 실제 호출 강제 가능 | 원본 records의 발급/보관 신뢰는 외부에 남는다. R 반환 보존 문제는11절의 기존 tuple 조합으로 해결. **선택** |

새 Context/index/Record decoder가 B의 선행 필수는 아니다. 그러나 **신뢰된 기존 expected 원본이 없다면** 이 프로파일의 입력 준비 실패다. raw20을 읽어 A를 새로 발급하거나 review_artifact_ref를 관찰 hash로 갈아 끼워 진행하지 않는다. 합성 fixture 저작에서 body 고정→H 확정→최종 A 최초 생성 순서를 쓰는 것과 소비 중 기대값을 자기 채택하는 것은 다르다.

## 5. A/R/Entry 객체 identity

P0a에서 A exact type을 확인한다. P0b에서 Review raw와 **입력 expected tuple 자체**를 기존 로더에 넘겨 R을 얻는다. P0c는 기존 historical_dataset_manifest_loader의 `_selected_entry(R, A)`를 한 번 직접 호출한다. 이 helper는 ACCEPTED → root equality → 명시 acceptance_ref의 유일 Entry → `E.acceptance is A` → Manifest ref exact type 순서다.

따라서 값이 같아도 tuple 원본과 별개인 A clone은 identity 오류다. 같은 policy의 다른 revision도 자동 선택하지 않는다. A가 tuple/Entry에 없으면 유일 선택 실패다. helper에서 반환한 E도 복제하지 않으며 다른 Entry의 참조로 교체하지 않는다.

각 Historical 로더에는 정확히 같은 **A is / R is / 해당 raw bytes is**를 전달한다. 교차 함수의 A/R도 동일하고, 각 객체 인자는 해당 로더가 반환한 바로 그 객체다. dataclasses.replace·to_dict→재구성·현재 객체 교체·상태 수정·캐시 복사는 없다. 로더 내부의 Entry 재확인과 교차 함수 내부의 기존 selector 호출은 원래대로 실행하며 이를 최적화해 건너뛰지 않는다.

원본 expected records를 선택하는 resolver/Context는 함수 외부 책임이다. 함수는 선택을 받은 뒤 대응만 확인한다. Python의 private 이름·is·frozen 타입은 악의적인 같은 프로세스의 monkeypatch/강제 변조를 보안상 격리하지 못한다.

## 6. 역할별 여섯 Raw Bytes 입력

| 고정 순서 | exact bytes 인자 | E의 기대 ArtifactReference | 기존 로더 반환 타입 |
|---|---|---|---|
| 1 | benefit_raw_bytes | accepted_terms_ref | BenefitSnapshot |
| 2 | coverage_raw_bytes | coverage_snapshot_ref | EligibilityCoverage |
| 3 | policy_envelope_raw_bytes | policy_envelope_ref | PolicyEnvelope |
| 4 | coverage_reviews_raw_bytes | coverage_reviews_ref | CoverageReviewContext |
| 5 | dataset_manifest_raw_bytes | dataset_manifest_ref | DatasetManifest |
| 6 | source_registry_raw_bytes | source_registry_ref | SourceRegistry |

각 역할은 독립된 필수 인자이며 exact immutable bytes여야 한다. bytearray/memoryview/None/str/subclass/domain object를 bytes로 변환하지 않는다. 역할 간 Python `id` 유일성이나 raw 값이 모두 달라야 한다는 새 제약은 없다. 서로 다른 artifact의 기대 참조·schema/binding 검증이 독립이라는 뜻이며 bytes interning을 판정 기준으로 쓰지 않는다.

P0d에서 여섯 exact 타입을 위 순서대로 모두 검사한 뒤 P1로 간다. b""도 exact bytes이므로 임의로 보완하지 않고 해당 로더의 SHA/strict 검사를 받는다. 인자 누락은 기본 TypeError다. 경로를 받거나 파일을 열거나 현재 release에서 읽지 않는다. Review raw까지 합하면 이번 호출에 독립 bytes 입력은 **7개**다.

## 7. 독립 expected SHA와 자기참조 방지

신뢰 사슬은 **외부 원본 A.ref의 root H → Review raw 전체 SHA/strict/raw20 결합 → R의 선택 E.ref6 → 각 raw 전체 SHA/strict 복원 → domain binding/교차 검증**이다. 별도 expected H 인자는 필요 없다. 선택 E의 path+sha는 기존 모델대로 보존하고, 함수는 path를 실행하거나 현재 경로로 resolve하지 않는다.

orchestrator는 SHA를 직접 계산/선언/수정하지 않는다. 실제 여섯 기존 로더가 자신의 기대 ref를 선택하고 supplied raw 전체를 해시한다. 실제 raw hash를 기대값으로 자동 채택하거나 반환 객체를 직렬화해 기대 H로 만들거나, 같은 domain fingerprint를 raw SHA 대신 사용하지 않는다.

R/refs와 원본 bytes를 함께 일관되게 새로 저작한 합성 부정 사례는 내부 binding 단계에 도달시키는 **시험 저작**이다. 운영 소비자가 독립 expected A/E 없이 관찰한 bytes로 전체 기대값을 생성해도 된다는 규약이 아니다. SHA는 기대 bytes와의 대응이며 실제 발급 권한·공식성·의미 검토를 인증하지 않는다.

## 8. 고정 실행 순서

아래가 전체 전역 순서다. 내부 로더/교차 함수의 P 번호와 구별해 읽는다. P0도 완료 전 외부 출력은 없다.

| Phase | 실제 수행 | 성공 시 보존 / 실패 시 이후 호출 |
|---|---|---|
| P0a | A exact PolicyBenefitAcceptance 검사 | 잘못되면 새 입력 오류, Review 포함 모든 로더0회 |
| P0b | load_acceptance_review_artifact_bytes(raw_bytes=review_artifact_raw_bytes, expected_acceptances=expected_acceptances) 정확히1회 | 원본 R; 실패 시 selector/로더6/교차0회 |
| P0c | 기존 `_selected_entry(R, A)` 직접1회 | 원본 E; 실패 시 로더6/교차0회 |
| P0d | raw6 exact bytes 전부 순서대로 검사 | 실패 시 로더6/교차0회 |
| P1 | load_historical_benefit_snapshot_bytes | 원본 benefit; 실패 시 P2 이후0회 |
| P2 | load_historical_eligibility_coverage_bytes | 원본 coverage; 실패 시 P3 이후0회 |
| P3 | load_historical_policy_envelope_bytes | 원본 envelope; 실패 시 P4 이후0회 |
| P4 | load_historical_coverage_review_context_bytes | 원본 reviews; 실패 시 P5 이후0회 |
| P5 | load_historical_dataset_manifest_bytes | 원본 manifest; 실패 시 P6 이후0회 |
| P6 | load_historical_source_registry_bytes | 원본 registry; 실패 시 교차0회 |
| P7 | `_validate_historical_artifact_relationships` 정확히1회 | 원래 성공 반환 None; 실패 시 반환/후속 처리 없음 |
| P8 | `(R, (benefit, coverage, envelope, reviews, manifest, registry))` 반환 | 완전한 한 번의 정상 반환 |

P1~P6 모두 기존 `raw_bytes=<해당 입력>, artifact=R, expected_acceptance=A`의3개 keyword-only 인자를 그대로 사용한다. 병렬 실행·부정 사례에서 계속 수집·파일 재읽기·실패 재시도·선택 변경·early success는 없다.

P0c 직접 selector1회와 P7 자체 내부 selector1회는 다른 필수 호출이다. 각 로더가 내부에서 수행하는 자체 Entry 선택/직접 binding도 유지한다. 테스트에서 selector의 전체 호출을 무조건1회로 고정하는 잘못된 최적화 요구를 만들지 않는다.

## 9. Cross-Artifact Validator 연결

P7의 정확한 매핑은 다음과 같다. 이 표의 변수들은 모두 이번 호출에서 앞서 얻은 원본이다.

| 기존 교차 함수 필수 인자 | 연결 원본 |
|---|---|
| expected_acceptance | 입력 A |
| artifact | P0b R |
| benefit_snapshot | P1 benefit |
| eligibility_coverage | P2 coverage |
| policy_envelope | P3 envelope |
| coverage_review_context | P4 reviews |
| dataset_manifest | P5 manifest |
| source_registry | P6 registry |

기존8인자/None 계약을 바꾸지 않는다. `_bind_manifest`, Envelope/Registry 지문, source 집합/version, Coverage 구현 역할 H/알려진 원문 H 선언, 구조·지문·Review matcher를 다시 작성하지 않는다. 교차 함수 내부 P0~P8의 순서·원본 node·canonical 순서·예외를 그대로 사용한다.

정상 MISSING/STALE/partial Coverage도 교차 함수가 허용한 대로 보존한다. 내부 matcher가 MATCHED를 반환할 수 있지만 orchestrator는 MATCHED를 새로 결정/외부 상태로 발행하지 않는다. 교차 검증 None은 원본 관계 검사 성공이고 FULL/VERIFIED/USABLE이 아니다. 이 단계 뒤에 아직 승인되지 않은 Content/evaluator/Bridge를 자동 호출하지 않는다.

## 10. Fail-Closed와 부분 반환 금지

처음 발생한 예외로 즉시 종료한다. 앞서 복원한 R/객체들은 로컬 변수에만 남으며 부분 tuple/generator/yield/callback/전역 cache/실패 결과 객체로 내보내지 않는다. try/finally의 return, 성공 bool, 오류 무시·STALE/MISSING 변환·현재 release fallback도 없다.

PolicyDataError 및 예상 밖 RuntimeError 등의 **발생한 예외 객체 그대로** 전파한다. 상위 연결 함수가 category/메시지를 래핑하거나 정상 상태로 바꾸지 않는다. 기존 로더 내부가 자신의 하위 예외를 명세대로 변환하는 행동은 그대로다. 외부 로깅/오류 표시를 붙여도 원본 bytes·소득·ref/path/hash·본문을 새 오류에 출력하지 않는다.

이는 정상 코드의 반환 계약이다. debugger/traceback이 로컬 변수에 접근하는 것까지 보안상 차단하는 약속은 아니다. 실패한 호출의 로컬 값을 다른 요청의 성공 증거로 사용하는 내부 호출 코드는 지원 경로가 아니다.

## 11. 반환 계약 비교와 최종 선택

| 대안 | 장점 | 적용 결과 |
|---|---|---|
| A 성공 None | 가장 작음 | R/객체6를 후속 Content에 넘기려면 재복원 또는 외부 상태가 필요해 제외 |
| B 여섯 원본의 고정 tuple만 반환 | 새 모델 없이 로더6 중복 방지 | A 진입점에는 충분하지만, 선택한 B 진입점은 내부 R까지 후속에 필요하므로 이것만으로 부족 |
| B 보완: `(R, 고정 tuple6)` | 기존 tuple만 사용, R과 객체6 원본을 모두 보존, 여섯 순서 명확 | **최종 선택**. 새 결과 모델/상태/인증 필드 없음 |
| C 전용 result model | 필드명 명시 가능 | 승인/완료 모델·factory·직렬화·migration을 늘려 이번 최소 경계에 불필요 |

정확한 외부 tuple 길이는2, 첫 원소는 P0b의 **R is**, 둘째는 exact tuple 길이6이며 순서는 BenefitSnapshot → EligibilityCoverage → PolicyEnvelope → CoverageReviewContext → DatasetManifest → SourceRegistry다. 각 slot은 해당 로더 반환 원본과 `is`가 같다. 평탄화한7tuple·dict·namedtuple·None·검증 상태 Enum을 반환하지 않는다.

기존 모델들은 frozen/slots이며 collection은 기존 tuple 규약을 따른다. 상위 tuple 추가가 악의적 강제 변조까지 막는 것은 아니다. 호출자에게는 입력 A/expected tuple/raw7이 이미 있으므로 A/bytes를 반환에 중복하지 않는다. R을 숨기거나 같은 Review bytes를 다시 로딩해 R2로 교체하지 않는다.

후속 신뢰된 연결 함수는 **같은 상위 요청 안에서** 반환 R/객체6를 직접 Content 준비에 전달한다. 선택 envelope 하나를 전체 Manifest envelopes 집합이라고 간주하지 않으며, 다른 정책 원본/공식 Source/구현 ZIP 등은 별도 준비가 필요하다. 후속 Content11입력 후보를 이번에 수정하지 않는다.

tuple은 검증 receipt·capability·지속 provenance 증명서가 아니다. 다른 곳에서 같은 타입/값의 tuple을 만들 수 있다. 이번 함수에는 tuple/preloaded 결과를 입력받는 경로가 없으므로 이전 결과로 실제 로더/교차 호출을 생략할 수 없다. **동일 raw와 A를 새 호출에 다시 공급하는 것은 허용**되지만 그때도 Review1+로더6+교차1을 새로 실행한다. 상위 서비스가 임의 tuple을 직접 승인 증거로 받지 않아야 한다는 책임은 남는다.

## 12. Same-call provenance의 보장 범위와 한계

| 층 | 확인 가능한 것 | 책임·미확인 |
|---|---|---|
| 1 raw/expected 준비 | 원본 A 및 expected 전체 tuple, 명시 bytes 확보 | 외부 신뢰된 준비. 발급/원본 보관/누락 이력/공식성은 이번 함수가 관찰 못함 |
| 2 root/선택 결합 | Review SHA/strict/raw20·R.entries 전체 대응·E.acceptance is A | 기존 Review 로더 + P0c, B 진입점으로 같은 호출에서 강제 |
| 3 raw6 strict 복원 | 각 E.ref의 기대 SHA·schema·domain binding·동일 raw 입력 | 실제 기존 로더6를 이번 호출에 각각1회 실행 |
| 4 교차 일관성 | 같은 A/R 및 방금 복원한 객체6의 기존 관계 비교 | P7 실제 함수1회. 전체 원문/사용성 제외 |
| 5 실행 코드 신뢰 | 실제 검토 artifact의 코드/환경/import/호출 target 대응 | 별도 production 실행 경계. Python private 함수명/반환 tuple로 증명 못함 |

합성 trusted test process에서 2~4를 검증하는 구현은 가능하다. 1/5의 운영 완성이 아직 없다는 이유로 순수 합성 구현을 자동 차단하지 않는다. 반대로 이 함수 성공을 운영 1~5 전체 증명으로 확대하지 않는다. 공격자가 A/R/bytes/코드까지 모두 일관되게 바꿀 수 있다면 hash equality만으로 공식성·발급 신뢰를 얻지 못한다.

## 13. 외부 Raw Bytes Preparation 책임

pure 함수는 파일/네트워크/Git/환경/현재 시각/난수/DB/ZIP을 읽지 않고 입력 bytes만 다룬다. preparation은 Review 포함7종 원본과 필요한 Source/ZIP을 확보한다. **구체적인 파일 준비·실행 계약/구현은 미완료**다.

| 외부 검토 항목 | 후속 실제 파일 계층의 책임 |
|---|---|
| 허용 root/경로 | 신뢰된 명시 archive root; Review content-addressed 위치와 E.path의 허용 상대 경로; 사용자의 임의 경로/LLM 선언 배제 |
| 같은 파일 객체 읽기 | 안전하게 확보한 handle의 같은 bytes를 고정하고 그 불변값을 전달; hash 후 경로를 다시 열어 parse 금지 |
| 교체/원본 보존 | 읽기 중 교체·수정 방지/검출, immutable archive·revision 보존, 획득 실패 시 준비 중단 |
| symlink/reparse/경로 이탈 | 실제 해석 대상·허용 경로·재지정 위험 확인. 문자열 startswith만으로 안전 주장 금지 |
| TOCTOU | 확보/검증/사용 수명과 변경 감지·실패 시 폐기 규약 명시 |
| 독립 expected | 신뢰된 기존 A/전체 records → Review 기대 H → 선택 E.ref6. 관찰 파일 hash를 기대값으로 발급하지 않음 |
| raw 수명 | 같은 상위 요청에서 bytes7과 반환 원본을 유지; 누락 자료를 현재값·빈값·다른 revision으로 보완하지 않음 |

이번 pure 함수가 파일을 열지 않으므로 파일 잠금·reparse 방어·안전한 파일 I/O를 수행했다고 주장하지 않는다. 아직 없는 파일 시스템 보장 때문에 raw 입력에 prepared=True/검증 토큰을 추가하지 않는다.

**Assumption A1:** 후속 합성 구현의 원본 A/expected tuple 및 bytes는 신뢰된 합성 저작 단계가 공급한다. **Assumption A2:** 운영 적용 전 준비 계층이 expected 발급/보관 신뢰와 파일 취득 규약을 별도로 충족해야 한다. 이번 문서가 그 구현을 완료했다는 가정은 하지 않는다.

## 14. Production implementation artifact 경계

M2.52의 신규 공유 ZIP profile은 실제 같은 bundle이 engine/Coverage 구현 역할을 담당한다고 검증한 경우 Manifest.engine_artifact_sha256·Coverage 구현 H의 대응을 요구한다. 이를 과거 모든 manifest/record의 전역 equality로 소급하지 않는다. 이번 함수도 M2.73처럼 Context의 Coverage 구현 fp와 E.implementation_artifact_ref.sha256 대응만 기존 교차 단계에 맡긴다.

**backend의 이 orchestrator를 import하기 전** 별도 신뢰된 launcher가 승인 Python/격리 옵션/설치 및 명시 Manifest 기대 H를 확보하고, 같은 handle의 실제 ZIP SHA/profile/배치 bootstrap bytes를 확인해야 한다. 검증한 ZIP과 허용 stdlib로 import 경로를 고정한 뒤 backend 모듈을 eager import하고 각 origin/loader/archive 및 실제 호출 target 출처를 대조한다. 시작 전후 같은 ZIP·모듈 집합·변경 방지 수명 검증도 필요하다. 검증 전 checkout backend를 import한 process를 성공 worker로 재사용하지 않는다.

외부 bootstrap은 최초 실행 Python/배치 절차 자체를 신뢰한다. 자기 파일 equality나 버전 문자열로 interpreter/OS/악의적인 호스트까지 암호학적으로 인증하지 않는다. 준비된 실제 Manifest bytes를 나중에 backend 전체 검증에도 그대로 사용해야 하며 header-only H 읽기가 전체 release 검증은 아니다.

M2.53의 합성 ZIP verify-only 및 M2.71의 TEST_ONLY.txt ZIP은 production 업무 엔진 실행/전체 import 대응 완료가 아니다. 이번에 새 bootstrap·ZIP·실행 로더·manifest header parser·프로세스 검증을 만들지 않는다. **Assumption A3:** 후속 순수 합성 구현은 trusted test code에서 실행하며, 운영 실행 대응은 별도 미완료 경계다.

## 15. Acceptance status·revocation·유효기간 분리

입력 A는 기존 ACCEPTED 원본이어야 한다. 기존 selector의 요구이며 새로운 상태 판정이 아니다. R 전체 expected tuple에 다른 REVOKED 기록이 포함되는 것은 Review 로더의 기존 구조 계약상 가능하나, **선택 REVOKED 기록 자체를 raw6 복원 대상으로 사용하지 않는다**. REVOKED E의 ref7은 None이며 이 부재를 과거 A 원본으로 fallback하지 않는다.

현재 Context에 A를 직접 철회한 B가 있어도 A 자체는 ACCEPTED 역사 원본으로 남는다. 감사용으로 A와 A에 대응하는 당시 R/raw6를 복원할 수 있으며 결과가 현재 usable을 뜻하지 않는다. B를 선택해 당시 승인 원본을 검토해야 하는 후속 Content 흐름은 신뢰된 Context의 명시 revokes_acceptance_ref로 원본 A/해당 R을 별도 준비하고 그 A를 이 함수에 전달해야 한다. B/RB를 몰래 A/RA로 바꾸는 옵션은 없다.

이번 함수는 Context/data_use_date를 입력받지 않고 revocation/만료/현재 재수용/NO_ACCEPTANCE 이유를 계산하지 않는다. 현재 Context의 이력 완전성·권한은 외부, 알려진 철회 효과·명시 사용일·current snapshot 판정은 후속 evaluator다. 철회 기록의 valid_until 이후 A를 자동 복구하지 않는 기존 방침을 유지한다.

## 16. Content Validator와 책임 분리

이번 연결은 Content 명세의 원본 결합 선행 공백 중 **선택 A에 대응하는 R/자료6의 strict 복원과 기존 교차 관계**를 닫는다. 전체 Content 검증 성공을 대체하지 않는다.

| 남은 기능 | 이번 호출이 제공/하지 않는 것 |
|---|---|
| 전체 release | 선택 Envelope 하나와 Manifest 복원은 제공. 전체 policy envelopes 집합/각 원본·호환 역사 환경의 validate_dataset_manifest는 별도 |
| Source 원문/locator | Registry와 알려진 content H 선언 대조는 기존 교차에 포함. 실제 공식 원문 bytes SHA·locator 존재/ACTIVE/policy·중복·claim 소속/합집합·의미 지지는 미포함 |
| 검토 내용 | 정상 matcher 상태를 유지. 실제 검토 증거 원문·준비/검토 권한·L3 수행 진실성은 외부 |
| FULL/verification | partial/MISSING/STALE도 원본으로 복원 가능. Historical FULL_POLICY 재현·Policy VERIFIED·freshness·Source Gate를 승인하지 않음 |
| 현재 Acceptance | 사용일/철회/현재9축 guard/평가 결과 생성 없음 |
| 후속 제품 | Benefit Bridge·Cashflow·금액 반영·FastAPI·React 연결 없음 |

현재 validate_dataset_manifest는 전체 envelopes 집합 및 ENGINE_VERSION 호환을 확인한다. 선택 정책만 넘기거나 과거 자료가 최신 engine과 다르다는 이유로 기존 검증을 약화하지 않는다. SourceRegistry.get_source와 resolve의 status 차이, optional content_sha256=None도 유지한다. 없는 원문 H를 생성해 채우지 않는다.

후속 Content11입력 후보의 R/A/자료를 이 반환에서 직접 연결할 수 있다. 그러나 source originals/bytes 쌍/다른 envelopes/철회 target 및 실행 대응을 추가로 준비해야 하므로 이번에 전체 후보 구현을 승인하지 않는다. Content의 None 반환과 이 함수의 tuple 반환은 책임이 달라 충돌하지 않는다.

## 17. 오류 prefix·전역 및 내부 우선순위

새 prefix는 **INVALID_HISTORICAL_ORCHESTRATION_INPUT** 한 개만 정한다. 사용 필드는 expected_acceptance 및 raw6의 정확한 인자명7개이고 형태는 `PREFIX: fixed.field: 계약을 확인하세요`다. 실제 payload/ref/hash/path를 넣지 않는다. 새 정상 상태/오류 class는 없다.

| 오류 위치 | 전파/우선순위 |
|---|---|
| Python 호출 형식 | 누락/extra/positional은 기본 TypeError, 본문0회 |
| P0a | 잘못된 A exact type은 새 prefix expected_acceptance |
| P0b | Review 입력/expected 관계 → SHA → encoding/strict/schema/canonical/models → originals binding. 기존 prefix·field·예외 객체 그대로 |
| P0c | `_selected_entry`의 status → root → 유일 Entry → 원본 is → Manifest ref. 기존 HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH / INVALID_HISTORICAL_DATASET_MANIFEST_EXPECTED_REF 그대로 |
| P0d | raw6 exact 타입을6절 순서대로 검사; 첫 잘못된 필드에 새 prefix |
| P1~P6 | 단계 순서대로 기존 로더의 최초 오류 그대로. 각 내부 type/Entry/SHA/strict/domain/binding 순서는 기존 구현 유지 |
| P7 | M2.73 내부 P0~P8 및 원본 helper 순서·기존8prefix/하위 예외 그대로 |
| P8 | 위 단계 모두 성공한 경우에만 반환 |

오류 우선순위는 **전역 단계 → 호출된 함수의 기존 내부 순서**다. 새 함수가 하위 함수의 기존 오류를 사전 재구현하지 않는다. 다만 새 wrapper의 P0 경계에 따른 명시적 전역 선행 검사가 있다. 예: A 타입+Review raw 타입 오류면 P0a; Review raw 타입+raw6 타입 오류면 P0b; A clone+raw6 타입 오류면 P0c; Benefit SHA 오류+Registry raw 타입 오류면 P0d Registry 타입이 먼저다. raw6 타입이 모두 맞고 Benefit SHA와 Registry SHA가 틀리면 P1 Benefit만 실패한다.

P0c의 Manifest 이름 prefix는 기존 helper를 그대로 재사용한 결과다. 새 orchestrator용 identity prefix를 추가해 의미를 바꾸지 않는다. bytes 형식/내용 오류를 STALE/MISSING/UNKNOWN으로 내리지 않는다. 정상 historical MISSING/STALE이면 이후 필수 검사까지 계속하고 모순이 있으면 그 오류를 전파한다.

## 18. 후속 합성 시나리오 — HSO01~HSO64

**64개 수동 설계 사례이며 이번 신규 실행 테스트는0개다.** 후속 실제 테스트 수와 같다고 미리 주장하지 않는다. 기본 원본은 기존 M2.71/73 합성 저작 helper를 시험에서만 재사용할 수 있다. 운영 코드가 tests를 import하지 않는다.

정상 시험은 실제 Review/로더6/교차를 실행한다. 관찰 wrapper는 실제 함수를 호출하고 원본 결과·인자 is/순서를 기록한다. 성공 경로를 fake tuple/가짜 None으로 대체하지 않는다. sentinel 예외 주입은 별도 오류 전파/이후 호출0회 시험에서만 사용한다. schema/domain 부정 사례는 독립 저작 단계에서 matching H를 고정해 목표 단계에 도달시키며 소비 코드는 기대값을 보정하지 않는다.

| ID | 사례 | 기대 phase/결과·담당 |
|---|---|---|
| HSO01 | 원본 A/전체 expected/Review raw/raw6 정상 | P0~P8, Review1+로더6 각1+교차1, exact `(R, tuple6)` |
| HSO02 | 모든 전달 인자와 반환 slot의 is 관찰 | P0b/ P1~7/ P8에서 입력 raw/R/A/반환 원본 연결, 새 함수 책임 |
| HSO03 | 같은 입력100회 정상 | 호출마다 필수8함수 재실행, 값/오류 결정성; 실행 테스트100개로 계상하지 않음 |
| HSO04 | expected records/raw7/반환 객체 불변성 | 전체 호출 전후 값/identity 보존, serializer 결과 변형이 원본을 바꾸지 않음 |
| HSO05 | 복수 정상 historical revision 공존·명시 A 선택 | P0b 전체 binding 후 선택 A의 raw6만 복원, 최신 선택 없음 |
| HSO06 | expected tuple/Review Entry 순서가 다름 | 정상, 원본 A is와 R 원래 순서 유지 |
| HSO07 | 일관된 historical DRAFT/SUPERSEDED/WITHDRAWN·과거 engine | P8 가능, Source/engine 전체 사용 검증은 외부 미완료 |
| HSO08 | 정상 partial Coverage/MISSING/STALE | P7 이후도 필수 검사 수행하고 P8 가능; FULL/USABLE 생성 없음 |
| HSO09 | A=None/dict/subtype | P0a 새 입력 prefix, 모든 로더0회 |
| HSO10 | Review raw=str/bytearray/memoryview/domain 객체 | P0b 기존 INVALID_REVIEW_ARTIFACT_LOADER_INPUT |
| HSO11 | expected list/빈 tuple/잘못된 record exact type | P0b 기존 Review 입력 오류, raw6 로더0회 |
| HSO12 | 기대 root ref가 opaque 또는 records 간 다름 | P0b 기존 expected/ref 오류, 관찰 H로 수정 없음 |
| HSO13 | expected 중복 ref/revision | P0b 기존 오류와 ref 중복 우선 보존 |
| HSO14 | Review raw 변조, 독립 expected root 그대로 | P0b REVIEW_ARTIFACT_BYTES_MISMATCH, selector0회 |
| HSO15 | matching H이나 invalid JSON/canonical/model | P0b 기존 strict 오류, 내부 오류 순서 보존 |
| HSO16 | R body의 미목록/expected 누락/raw20 값 불일치 | P0b 기존 binding 순서·오류, 선택 외 Entry도 검사 |
| HSO17 | A와 tuple 원본이 값만 같은 clone | P0b 성공 후 P0c entry.acceptance is 오류 |
| HSO18 | A ref가 R/expected에 없거나 다른 root | P0c root/유일 Entry의 기존 순서 오류 |
| HSO19 | 선택 A가 REVOKED, 해당 R 자체는 유효 | P0c status 오류, None refs fallback 없음 |
| HSO20 | 만료되었거나 현재 철회된 과거 ACCEPTED A | P8 역사 복원 가능, current 사용 판정은 외부 evaluator |
| HSO21 | raw6 각각 None/subtype/domain 객체 | P0d 해당 필드 새 입력 오류, 로더6 전부0회;6역할 parameterize |
| HSO22 | raw6 중 하나 생략/임의 artifact 또는 skip 옵션 전달 | 본문 전 TypeError, 모두0회 |
| HSO23 | Benefit raw SHA mismatch | P1 기존 HISTORICAL_BENEFIT_BYTES_MISMATCH; P2 이후0회 |
| HSO24 | Coverage raw SHA mismatch | P2 기존 HISTORICAL_COVERAGE_BYTES_MISMATCH; P3 이후0회 |
| HSO25 | Envelope raw SHA mismatch | P3 기존 HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH; P4 이후0회 |
| HSO26 | ReviewContext raw SHA mismatch | P4 기존 HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH; P5 이후0회 |
| HSO27 | Manifest raw SHA mismatch | P5 기존 HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH; P6 이후0회 |
| HSO28 | Registry raw SHA mismatch | P6 기존 HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH; 교차0회 |
| HSO29 | 다른 revision/Entry raw6의 일부 또는 전체 혼합 | 일치하지 않는 첫 역할의 P1~6 SHA 또는 직접 binding 오류, fallback 없음 |
| HSO30 | raw6 각 역할 invalid JSON, matching E H로 독립 저작 | 해당 P1~6 strict 오류·이후0회;6역할 parameterize |
| HSO31 | Benefit/Inventory/Tree/Registry domain fp 모순 | 해당 P1/P2/P3/P6 기존 binding/fp 오류, 관찰 fp 채택 없음 |
| HSO32 | Context baseline/Manifest membership·Registry binding 모순 | P4/P5 기존 직접 binding 오류; 정해진 로더 순서 |
| HSO33 | exact b"" raw 입력 | P0d 통과 후 해당 로더 SHA/strict 오류, 빈값 보정 없음 |
| HSO34 | 로더6 모두 성공하지만 Registry 문서 집합 모순 | P7 기존 HISTORICAL_ARTIFACT_SOURCE_VERSION_MISMATCH |
| HSO35 | 로더6 모두 성공하지만 선택 Manifest Envelope domain fp 모순 | P7 기존 HISTORICAL_ARTIFACT_POLICY_MISMATCH |
| HSO36 | 로더6 모두 성공하지만 Binding root 없음/ownership 모순 | P7 기존 구조 helper 오류, 원본 전파 |
| HSO37 | 로더6 모두 성공하지만 Review ref 없음/종류/condition/root 오류 | P7 기존 resolver/matcher 오류, 정상 MISSING으로 낮추지 않음 |
| HSO38 | 로더6 모두 성공하지만 같은 i/r/dataset Review fp 모순 | P7 기존 matcher 오류, 모든 canonical 순서 유지 |
| HSO39 | 로더6 모두 성공하지만 알려진 Source content H 선언 모순 | P7 기존 HISTORICAL_ARTIFACT_SOURCE_CONTENT_MISMATCH |
| HSO40 | 로더6 모두 성공하지만 Context와 E 구현 역할 H 모순 | P7 기존 HISTORICAL_ARTIFACT_IMPLEMENTATION_MISMATCH |
| HSO41 | 각 raw 검사를 통과하도록 저작했으나 Manifest의 선택 Policy/Registry ref path만 또는 H만 E와 모순 | 기존 직접 Manifest binding P5에서 차단; 로더6 모두 성공 사례로 꾸미지 않음 |
| HSO42 | 사전 생성 객체6를 raw 인자 대신 전달 | P0d, typed 원본 우회 입력 없음 |
| HSO43 | 이전 반환 tuple 또는 그 slot을 입력으로 재사용 시도 | 미지원 keyword면 본문 전 TypeError, raw 역할 주입이면 P0b/P0d 타입 오류 |
| HSO44 | 같은 raw/A를 다시 정상 호출 | 이전 tuple/None 재사용 없이 전체 필수 경로 새 실행, 새 R/복원 원본 |
| HSO45 | P1~6 어느 로더든 PolicyDataError sentinel | 해당 phase의 같은 예외 객체, 이후 호출0회, 부분 반환 없음 |
| HSO46 | P7 PolicyDataError sentinel | 같은 예외 객체 그대로, P8/후속0회 |
| HSO47 | Review/selector/로더6/교차의 예상 밖 RuntimeError | 발생 phase 그대로 전파; 성공/정상 미검토로 변환 없음 |
| HSO48 | A 타입 오류+Review raw 오류 | P0a 먼저, Review0회 |
| HSO49 | Review raw 오류+raw6 타입 오류 | P0b 먼저, selector/로더6/교차0회 |
| HSO50 | A clone+Registry raw 타입 오류 | P0c identity 먼저, 로더6/교차0회 |
| HSO51 | Benefit SHA 오류+Registry raw 타입 오류 | P0d Registry 타입 먼저, P1도0회 |
| HSO52 | raw 타입 정상·Benefit/Coverage/Registry 다중 SHA 오류 | P1 Benefit만 발생, 후속0회 |
| HSO53 | P7 여러 관계 모순 | M2.73 기존 내부 phase/helper 우선순위 그대로 |
| HSO54 | P7 정상 MISSING/STALE과 뒤 독립 오류 | 독립 오류 전파, 정상 상태가 검사를 중단하지 않음 |
| HSO55 | 실패 단계 앞의 부분 값 사용 시도 | 정상 API 반환 없음; debugger/악의 caller 격리는 보장 밖 |
| HSO56 | `(R, tuple6)`의 순서/길이/identity 및 frozen 원본 | P8 구조 고정; 새 모델·bool·USABLE/VERIFIED 필드 없음 |
| HSO57 | 임의 R 객체 또는 과거 R를 직접 입력하려는 호출 | artifact 인자는 없어 TypeError; Review raw 자리에 넣으면 P0b 타입 오류 |
| HSO58 | 신뢰된 A 없이 raw20에서 expected를 자기 발급 | 외부 준비 계약 위반; 내부가 발급/권한 신뢰까지 탐지한다고 주장 안 함 |
| HSO59 | 원본 기록/bytes는 일관되나 실제 파일 취득 미검증 | 합성 P8 가능; 파일 잠금/reparse/TOCTOU 완료는 외부 preparation 미완료 |
| HSO60 | production ZIP identity/import 실행 미검증 | 합성 P8 가능; production 시작 승인은 별도 실행 경계에서 차단 |
| HSO61 | 전체 Manifest의 다른 Policy Envelope 미제공 | 선택 raw6 성공 가능; 전체 release/Content 완료 아님 |
| HSO62 | locator 없음/Source DRAFT 또는 실제 원문 미확보 | 선택 raw6/교차 성공 가능; Content/Source Gate/외부 원문 검토 미완료 |
| HSO63 | 파일·네트워크·환경·시각·난수·외부 evaluator 접근 차단 | 정상 합성 경로 성공, 허용 로더/교차 외 I/O·평가 호출 없음 |
| HSO64 | API/export/기존 source·tests·release 변경 없음 점검 | 이번은 문서만. 후속 구현도 별도 승인 범위/회귀·동결 준수 |

100회 오류 결정성도 HSO03/45~54의 해당 실패 입력에서 확인하도록 설계한다. 다중 입력이 같으면 최초 prefix/field/phase·이후 호출0회가 같아야 한다. 정상 호출 사이 R/객체6의 값 equality와 **각 호출 내부 원본 is**를 구분한다. 서로 다른 호출의 모든 객체가 같은 is여야 한다는 cache 요구는 없다.

## 19. 기존 동결 계약·변경 범위 영향

**이번 추가는 이 문서1개다. 운영 코드·테스트·fixture·기대값·export·설정·기존 문서 수정/삭제0개, 신규 실행 테스트0개다.** 기존 Historical6/Review 로더/교차 validator·SourceRegistry parser/fingerprint·DatasetManifest validator·Review matcher·ZIP bootstrap·Acceptance/Benefit/Cashflow를 변경하지 않는다.

Coverage core는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**, GV01~GV15/BV01~BV16의 기존 literal/계산/회귀를 유지한다. 새 상태/지문 schema/Record·Context·Evaluation 필드·강제 H equality·Review matching 규칙 변경이 없다. 동일 호출 wrapper는 기존 frozen 함수의 호출자이며 core 수정 사유가 아니다.

ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 실제 안산001/002는 **DRAFT / CONDITION_SLICE**, 공식 거주기간 의미·다른 조건/완결성 검토 blocker 및 정책 혜택 Cashflow 반영0원 원칙을 유지한다. 새 실제 정책 지문·금액·Acceptance/철회/검토 기록·ZIP 실행 결과를 만들지 않는다.

## 20. 미해결 사항과 Assumptions

| 항목 | 이번 확정 / 남은 것 |
|---|---|
| 입력/Review 진입점 | B안9필수입력, 실제 Review 로더 호출, 원본 expected tuple. 해결 |
| A/R 및 raw6/교차 결합 | P0~P8·is·독립 기대 ref·실제 필수 호출·fail-closed. 해결 |
| 반환 | 같은 R+고정 tuple6를 기존 tuple 조합으로 반환. 해결; 영구 provenance 인증은 아님 |
| 오류/우선순위 | 새1prefix와 기존 예외/함수 내부 순서 보존. 해결 |
| 구현/합성 실행 증거 | 아직 미구현. 다음 한 단계의 대상 |
| 실제 raw preparation | 파일 root/동일 handle/교체·reparse·TOCTOU·archive·expected 발급/보관 신뢰. 별도 계약/구현 필요 |
| production 코드 실행 | 실제 ZIP/profile/환경/import 출처·worker 수명 검증. 별도 미완료 |
| Content/Source/release/current 사용 |16절의 원문·전체 집합/역사 환경·검토·Gate·evaluator/Bridge 미완료 |

Assumptions A1~A3는 신뢰된 합성 자료와 운영 외부 책임을 명시한 것이다. 실제 자료/권한/파일/ZIP이 검증됐다고 가정해 내부 성공을 생산하지 않는다. 외부 자료가 없으면 해당 운영 흐름은 준비 실패/미완료이며 가짜 ref/hash/empty bytes로 진행하지 않는다. 이 좁은 순수 합성 계약과 기존 구현 사이에 모델 변경이 필요한 충돌은 확인되지 않았다.

## 21. 최종 판단과 M2.74 검증 기록

**READY_TO_IMPLEMENT_HISTORICAL_SAME_CALL_ORCHESTRATOR**

B 진입점·원본 A/전체 expected/R 결합·raw6·호출 순서·기존 교차 실행·반환·오류를 이 문서에서 확정했다. 새 도메인 모델/검증 알고리즘 없이 기존 순수 함수의 내부 연결로 구현할 수 있다. 운영 파일 준비와 production 실행 검증 미완료는 별도 제한으로 남기며 이 판단을 production 전체 승인으로 사용하지 않는다.

사전 전체 pytest: **10943 passed in 99.13s (0:01:39)**. 사후 전체 pytest: **10943 passed in 61.33s (0:01:01)**. 사전/사후 전체 각각 최초 실행 통과, failed/skipped/timeout/재실행0회.

이번 신규 실행 테스트 **0개**. 기존10,943개 회귀 결과와64개 문서 사례를 구분한다. 위 함수의 실제 same-call 구현이 아직 없으므로 이번 회귀가 새 함수를 실행 검증했다고 보고하지 않는다.

보호 범위는 backend/tests/data/docs/tools의 일반 파일 및 .gitignore/pyproject.toml/README.md/requirements-dev.txt다. 생성 임시물·venv·pycache·pytest cache는 제외하고 실제 data/releases는 별도6개로 전수 기록한다. 사전 기존 보호 파일 **202개 + 실제 release6개**의 SHA256/크기/mtime_ns 기준선을 확보했다. 사후 비교에서 기존 **202개 전부 SHA256·크기·mtime_ns 동일**, 수정/삭제0개다. 이 문서1개를 추가해 보호 범위는 **203개**가 됐다. 파일 목록 차이도 이 새 문서 하나뿐이다.

release6의 개별 기준선은 부록A에 보존한다. 실제 release6개 전부 SHA256·경로·크기·mtime_ns 동일. 기존10,943개 테스트·GV01~GV15/BV01~BV16·모든 freeze/로더/교차/Acceptance/Benefit/bootstrap/Cashflow·기존 문서는 그대로다.

## 22. 다음 최소 작업 하나

**별도 구현 승인 후, 이 문서의 private 순수 orchestrator 한 함수와 합성 unit/integration tests만 구현한다.** B안9입력, Review1+기존 selector 직접1+로더6+교차1, `(R, tuple6)` 원본 반환, 신규1prefix, 전역/내부 오류 순서·최초 실패 이후0회·100회 결정성·불변성·우회 인자 부재를 검증한다.

HSO01~HSO64를 실행 가능한 내부 사례/외부 한계 관찰로 구분해 대응 기록을 남긴다. 기존 함수·tests·golden 값·real release·frozen core를 변경할 필요는 없다. 필요한 새 문서 구현 기록 변경도 다음 지시의 명시 승인 범위에 한정한다. 이번에는 후속 코드 구현을 시작하지 않는다.

파일 preparation·실제 실행 ZIP·Content 전체·Source Gate·Acceptance evaluator·Bridge/Cashflow/API/UI를 이 작업에 함께 넣지 않는다. 추가 generic framework나 선행 모델 설계를 다음 단계로 자동 확장하지 않는다.

## 부록 A. 실제 release6 SHA256·크기·수정시각 보존

다음은 실제 파일의 작업 전 SHA256이다. 정책 JSON 파일명은 두 release 모두 `policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json`이다. 경로는 프로젝트 root 기준이며 실제 경로·크기·mtime_ns는 사전/사후 전수 비교한다.

| 실제 파일 | SHA256 |
|---|---|
| data/releases/ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| data/releases/ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| data/releases/ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| data/releases/ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| data/releases/ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| data/releases/ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

작업 전 기준선의 파일 크기와 수정시각은 다음과 같다. mtime_ns는 파일 시스템의 Unix epoch 기준 정수값이다.

| release / 파일 | 크기(bytes) | mtime_ns |
|---|---|---|
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 1981 | 1792485283217142700 |
| ansan-youth-2026-10-20-001/README.md | 1563 | 1792485455968002700 |
| ansan-youth-2026-10-20-001/sources.json | 3803 | 1792485282447400500 |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 2922 | 1792498860277470600 |
| ansan-youth-2026-10-20-002/README.md | 5620 | 1792499011465653800 |
| ansan-youth-2026-10-20-002/sources.json | 5944 | 1792498860276460800 |

## 부록 B. 요청한 최종 보고29항목 대응

| 번호 | 항목 | 확정·검증 |
|---|---|---|
| 1 | 생성 문서 | docs/HISTORICAL_SAME_CALL_ORCHESTRATION_CONTRACT.md 하나 |
| 2 | Same-call |3절, 한 함수 호출의 A/expected/raw7→실제 R/객체6→교차→완전 반환 |
| 3 | Review 선행 조건 |4절, exact2입력·전체 원본 집합·독립 root H/raw20 |
| 4 | A/R identity |5절, E.acceptance is A, 이후 R/A/객체 원본 보존 |
| 5 | raw6 |6절, 독립 역할의 exact bytes 필수, 변환/대체 없음 |
| 6 | 독립 기대 SHA |7절, 외부 A.ref→R/E.ref6, 자기 채택 금지 |
| 7 | A/B 진입점 |4절, A는 R raw provenance 외부 의존, B 선택 |
| 8 | 최종 API |3절, private9필수 keyword-only, 새 모델/옵션 없음 |
| 9 | 로더6 순서 |8절, Benefit→Coverage→Envelope→Reviews→Manifest→Registry |
| 10 | 교차 연결 |9절, 같은 A/R/각 로더 반환 원본의8인자1회 |
| 11 | 반환 |11절, `(R, (benefit, coverage, envelope, reviews, manifest, registry))` |
| 12 | Fail-Closed |10절, 최초 예외 즉시 중단·후속0회·부분 반환 없음 |
| 13 | 오류/순서 |17절, 새 입력 prefix1·기존 예외 객체·P0a~P8 |
| 14 | provenance |12절, root/strict 복원/교차2~4 연결, 외부 준비·코드 신뢰1/5 미완료 |
| 15 | 외부 파일 준비 |13절, 경로/동일 handle/교체·reparse·TOCTOU/원본 보관 별도 |
| 16 | production ZIP |14절, backend import 전 실행 artifact/환경 검증 별도; 합성 verify-only 한계 |
| 17 | status/revocation |15절, 역사 ACCEPTED A 복원과 현재 usable 구별; REVOKED ref fallback 없음 |
| 18 | 합성 시나리오 | HSO01~HSO64 수동64개, 이번 신규 실행0개 |
| 19 | 코드 변경 | 기존/신규 운영 코드·tests·fixture·export 변경0개, 신규 문서1개 |
| 20 | 전체 pytest | 사전10943 passed in99.13s; 사후 10943 passed in 61.33s (0:01:01) |
| 21 | 기존10,943개 | 기존10,943개 전부 사전/사후 통과. 기존 tests/fixture/기대값 변경 없음 |
| 22 | GV/BV | GV01~15/BV01~16 기존 literal·계산·회귀 보존 |
| 23 | release SHA | 실제 release6개 전부 SHA256·경로·크기·mtime_ns 동일. |
| 24 | Coverage freeze | ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS 유지 |
| 25 | ResidenceHistory | OFFICIAL_INQUIRY_REQUIRED 유지 |
| 26 | 실제 정책 | DRAFT / CONDITION_SLICE 유지, 실제 승인/금액 생성 없음 |
| 27 | Content/Source/Release |16·20절 별도 미완료, ZIP/evaluator/Bridge 포함 자동 승인 없음 |
| 28 | 최종 판단 | READY_TO_IMPLEMENT_HISTORICAL_SAME_CALL_ORCHESTRATOR |
| 29 | 다음 최소 작업 | 이 계약의 private 순수 연결 함수+합성 tests 구현 한 단계, 별도 승인 후 |

## 23. M2.75 — IMPLEMENTED: Historical Same-Call Orchestrator

### 23.1 실제 파일·API·구현 범위

추가 운영 파일은 `backend/policy_engine/policy_data/historical_artifact_orchestration.py`, 신규 테스트는 `tests/test_historical_same_call_orchestrator.py`다. 지시문의 historical_same_call_orchestrator.py는 권장 경로이며, **M2.74 최종 계약을 우선한다는 지시**에 따라3절의 파일명을 사용했다. alias 모듈은 추가하지 않았다.

실제 private 함수는 `_orchestrate_historical_artifact_validation` 한 개다.3절 서명과 동일한 필수 keyword-only9개·annotation·중첩 tuple 반환 타입을 reflection으로 확인했다. default/optional/nullable/추가 kwargs·이미 복원한 R/객체6 입력·public export·새 모델·상태·parser·hash 구현·공통 framework·endpoint가 없다.

정확한 입력 순서는 expected_acceptance, expected_acceptances, review_artifact_raw_bytes, benefit_raw_bytes, coverage_raw_bytes, policy_envelope_raw_bytes, coverage_reviews_raw_bytes, dataset_manifest_raw_bytes, source_registry_raw_bytes다. 모든 raw는 exact bytes이며 bytes-like/문자열/list를 자동 변환하지 않는다.

### 23.2 실제 P0a~P8·원본 전달

- **P0a:** A exact PolicyBenefitAcceptance만 검사한다. 잘못되면 새 `INVALID_HISTORICAL_ORCHESTRATION_INPUT: expected_acceptance: 계약을 확인하세요`다.
- **P0b:** 기존 load_acceptance_review_artifact_bytes를 정확히1회 호출한다. 입력 Review raw와 **전체 expected tuple 자체**를 그대로 전달한다. expected 타입/비어 있음/원소 exact 타입/ref·revision 집합/SHA/raw20/canonical/원본 binding은 기존 로더가 담당한다. selected A만 남기도록 축소하지 않는다.
- **P0c:** 기존 Manifest `_selected_entry(R, A)`를 직접1회 호출한다. status/root/유일 명시 ref/entry.acceptance is A/Manifest ref의 기존 의미와 prefix를 유지한다. 값이 같은 A clone·없거나 다른 revision/root·선택 REVOKED를 차단한다.
- **P0d:** raw6 exact bytes를6절 순서대로 전부 검사한다. 잘못된 필드는 같은 신규 입력 prefix다. 입력 타입이 모두 맞기 전 Historical 로더를 실행하지 않는다.
- **P1~P6:** Benefit → Coverage → Envelope → ReviewContext → Manifest → Registry의 기존 로더를 각각 정확히1회 호출한다. 각 로더의 raw_bytes는 해당 **입력 bytes is**, artifact는 **P0b R is**, expected_acceptance는 **입력 A is**다. 기대 SHA는 기존 로더가 선택 E의 ArtifactReference에서 가져오며 소비 중 기대값을 갱신하지 않는다.
- **P7:** 기존 `_validate_historical_artifact_relationships`를 정확히1회 호출한다. A/R과 각 로더의 실제 반환 원본6개를 기존8개 키워드에 직접 연결한다. 관계 비교/지문/구조/matcher를 재구현하거나 내부 순서를 변경하지 않는다.
- **P8:** `(R, (benefit_snapshot, eligibility_coverage, policy_envelope, coverage_review_context, dataset_manifest, source_registry))`만 반환한다. outer exact tuple2/inner exact tuple6, slot별 반환 원본 is를 보존한다.

직접 selector1회는 로더/교차 함수 내부의 기존 Entry 재확인과 별개다. 테스트는 orchestrator가 직접 부른 경계9개(Review·selector·로더6·교차)를 관찰하며 하위 selector 전체 호출을1회로 잘못 제한하지 않는다.

try/catch·재시도·fallback·cache·callback·부분 반환·generator·오류를 정상 STALE/MISSING으로 내리는 경로가 없다. 기존 함수가 발생시킨 PolicyDataError와 RuntimeError 객체는 새 wrapper 없이 그대로 전파한다. 원본 함수 내부의 기존 오류 변환은 유지한다. 신규 prefix는17절의1개뿐이다.

### 23.3 합성 실행 검증과 최초 실행 기록

정상 **실제 통합 시험**은 M2.71의 definitions/prepare를 시험 저작에 재사용하고, 운영 함수 안에서 실제 Review/로더6/교차를 실행한다. spy wrapper는 실제 함수를 실행하며 인자·반환·발생한 예외를 관찰한다. 별도의 **단위 연결 spy 시험**은 미리 준비한 원본과 None을 test monkeypatch로 반환해 고정 호출 경계만 확인하며, 이 단위 시험을 실제 raw 검증 실적으로 주장하지 않는다.

기본 합성 raw6의 고정 H를 기존 독립 상수와 대조한다. SHA 변조 시험은 기대 참조를 유지하고 bytes만 바꾼다. strict/domain 부정 사례는 **합성 저작 단계**에서 bytes와 기대 참조를 먼저 고정해 목표 단계까지 도달시키며, Registry의 경우 앞선 Manifest ref binding까지 일관되게 저작한다. 운영 소비 함수에는 자동 hash 채택·ref 갱신이 없다.

M2.73의 CROSS_CASES20개와 negative_spec을 시험에서 재사용해 **Review+로더6 성공 후** 실제 교차 오류를 확인한다. Manifest Policy/Registry의 path 또는 H만 E와 모순인4사례는 실제 Manifest 로더 P5가 먼저 차단하며 교차 실패로 중복 계상하지 않는다. 다른 Entry/revision의 raw6 각 역할도 독립 SHA에서 차단한다.

100회 정상 반복은 매번 Review1+로더6+교차1을 실행하고 원본 A/tuple/raw7을 보존하며, 각 호출의 새 R/복원 객체와 값 equality를 구분한다. Review/Benefit/Registry/교차의4개 실패 입력도 각각100회 최초 phase·오류 문자열·후속0회·불변성을 확인한다. 반복 횟수를 테스트 개수에 더하지 않는다.

신규 최초 실행: **199 passed in 4.64s**. 실패/timeout0회다. 이후 선택하지 않은 두 번째 Review Entry의 값 모순과 SUPERSEDED 역사 Source 보존2사례를 추가하고, 오류100회 시험에서 각 회차의 필수 호출/중단 기록까지 관찰하도록 보강했다. 신규 최종 실행: **201 passed in 4.32s**. 신규 시험은 총2회 실행했고 추가 후 재실행1회이며, 실패를 수정하기 위한 재실행은0회다. 기존 tests/fixture/기대값을 수정하지 않았다.

### 23.4 HSO01~HSO64 실행 대응 및 외부 한계

아래는64개 **문서 시나리오의 대응 기록**이다. 신규 pytest 수201개와 다르다. REAL은 실제 이번 함수/기존 로더/교차 호출, UNIT은 별도 연결·sentinel 시험, BOUNDARY는 제한된 정상 성공과 API 제한 관찰, EXTERNAL은 이번 함수가 관찰할 수 없는 외부 책임이다. 이 표의 분류는 문서 표기이며 새 운영 상태/Enum이 아니다.

| 수동 ID | 신규 실행 대응 / 정확한 한계 |
|---|---|
| HSO01 | REAL: 단일 정상 입력·실제 Review/로더6/교차·완전 tuple 반환 |
| HSO02 | REAL: raw/전체 expected/A/R/로더 반환 slot의 is와 정확한 호출 순서·횟수 |
| HSO03 | REAL: 정상100회 및 오류4종 각각100회, 매번 재실행/최초 실패·후속0회 |
| HSO04 | REAL: 입력 raw7/A/expected tuple 및 진단 serializer 변형의 원본 불변성 |
| HSO05 | REAL: 다중 revision의 양방향 명시 선택, latest/첫 원소 추론 없음 |
| HSO06 | REAL: expected tuple 순서를 바꿔도 전체 전달·Entry 원래 순서·원본 A 유지 |
| HSO07 | REAL/BOUNDARY: DRAFT·SUPERSEDED·WITHDRAWN·과거 engine 보존, Source 사용/engine 전체 검증 제외 |
| HSO08 | REAL: 정상 partial/MISSING/STALE에서도 교차 검사·반환, FULL/USABLE 생성 없음 |
| HSO09 | REAL: A None/dict/str/bool/정상 생성 subtype의 P0a 오류·전체 호출0회 |
| HSO10 | REAL: Review raw의6가지 잘못된 exact type은 기존 Review 입력 오류 |
| HSO11 | REAL: expected None/list/empty/잘못된 원소/tuple·record subtype, 기존 로더 거부 |
| HSO12 | REAL: opaque root·records 사이 다른 root, SHA 전에 기존 기대 ref 오류 |
| HSO13 | REAL: expected 중복 ref/revision, 기존 오류 유지 |
| HSO14 | REAL: 독립 root 유지한 Review raw 변조, 기존 SHA 오류·이후0회 |
| HSO15 | REAL: matching root의 invalid JSON/중복 key/비canonical/필수 field 누락 |
| HSO16 | REAL: unlisted/missing/raw20 값 모순 및 선택하지 않은 뒤 Entry까지 검증 |
| HSO17 | REAL: 값이 같은 별도 A clone은 P0c entry.acceptance identity 오류 |
| HSO18 | REAL: A ref 부재/다른 revision/root의 기존 selector 오류 |
| HSO19 | REAL: 유효 REVOKED Review 복원 뒤 선택 status 오류, ref None fallback 없음 |
| HSO20 | REAL/EXTERNAL: 기한 지난 ACCEPTED 역사 복원, 현재 철회 이력/사용일 판정은 외부 |
| HSO21 | REAL: raw6 각 역할별6가지 잘못된 type, P0d·Historical6 전부0회 |
| HSO22 | REAL: 필수9입력 누락/positional/우회 옵션은 본문 전 TypeError |
| HSO23 | REAL: Benefit SHA 불일치, P1 이후0회 |
| HSO24 | REAL: Coverage SHA 불일치, P2 이후0회 |
| HSO25 | REAL: Envelope SHA 불일치, P3 이후0회 |
| HSO26 | REAL: ReviewContext SHA 불일치, P4 이후0회 |
| HSO27 | REAL: Manifest SHA 불일치, P5 이후0회 |
| HSO28 | REAL: Registry SHA 불일치, P6 뒤 교차0회 |
| HSO29 | REAL: 복수 Entry에서 다른 revision의 raw를 역할별 주입, 첫 해당 로더 거부 |
| HSO30 | REAL: raw6 각 역할 matching 기대 H의 invalid JSON, 해당 단계 중단 |
| HSO31 | REAL: Benefit/Inventory/Tree/Registry 실제 domain fp 모순, 기존 오류 |
| HSO32 | REAL: Context 구현 baseline·Manifest membership 직접 binding 오류 |
| HSO33 | REAL: exact b"" 역할별 SHA/strict 거부, 보정 없음 |
| HSO34 | REAL: 로더6 모두 성공 뒤 source 문서 집합 다른 version/누락/추가 오류 |
| HSO35 | REAL: 로더6 모두 성공 뒤 선택 Envelope domain fp 모순 |
| HSO36 | REAL: 로더6 모두 성공 뒤 Binding root 부재, 기존 구조 오류 |
| HSO37 | REAL: 로더6 모두 성공 뒤 Review ref 부재/종류/condition/root 모순 |
| HSO38 | REAL: 로더6 모두 성공 뒤 동일 i/r/dataset의 Review fp 모순 |
| HSO39 | REAL: 로더6 모두 성공 뒤 알려진 원문 content H 선언 모순 |
| HSO40 | REAL: 로더6 모두 성공 뒤 같은 Coverage 구현 역할 H 모순 |
| HSO41 | REAL: Policy/Registry path/H4조합은 P5 기존 Manifest 직접 결합 오류 |
| HSO42 | REAL: domain 객체를 raw 대신 공급하면 P0d 거부 |
| HSO43 | REAL: 과거 tuple/slot을 raw에 넣으면 P0d, 별도 결과 인자는 TypeError |
| HSO44 | REAL: 같은 raw 재호출·다른 정상 revision 재호출 모두 새 검증·새 원본 |
| HSO45 | UNIT: 각 로더 단계의 PolicyDataError sentinel 객체 원본 전파·후속0회 |
| HSO46 | UNIT: 교차 sentinel 원본 전파·반환 없음; REAL 교차 오류도 원본 is 확인 |
| HSO47 | UNIT: Review/selector/로더6/교차9경계별 RuntimeError 원본 전파 |
| HSO48 | REAL: A+Review 타입 다중 오류는 P0a, 전체 호출0회 |
| HSO49 | REAL: Review raw+raw6 타입 다중 오류는 P0b |
| HSO50 | REAL: A clone+raw6 타입 오류는 P0c |
| HSO51 | REAL: Benefit SHA+Registry raw 타입 오류는 P0d |
| HSO52 | REAL: raw6 타입의 앞 필드 우선 및 여러 SHA 오류 중 P1 우선 |
| HSO53 | REAL: 교차 P3 Envelope fp 모순이 뒤 source 집합 모순보다 먼저 |
| HSO54 | REAL: 정상 MISSING Inventory 이후 독립 Implementation subtree fp 모순 차단 |
| HSO55 | REAL/UNIT: 예외 호출에는 정상 반환 없음·이후0회; debugger/악의 caller 격리 제외 |
| HSO56 | REAL: tuple2/tuple6의 길이·순서·타입·원본 is·frozen/tuple 변경 거부 |
| HSO57 | REAL: 외부 R 입력 인자 없음·Review raw 대신 domain 주입 거부 |
| HSO58 | EXTERNAL: raw20에서 expected를 자기 발급한 권한/발급 신뢰는 내부에서 판별 불가. 독립 발급 검증 완료로 계상하지 않음 |
| HSO59 | EXTERNAL: 파일 취득/잠금/reparse/TOCTOU는 미실행. 순수 합성 bytes 성공으로 준비 완료 주장 없음 |
| HSO60 | BOUNDARY/EXTERNAL: Manifest 엔진 H 변경에도 좁은 tuple 가능함을 관찰. 실제 production ZIP profile/import/실행은 미검증 |
| HSO61 | BOUNDARY: 다중정책 Manifest에 선택 외 Envelope 미제공이어도 좁은 복원 가능, 전체 release 완료 아님 |
| HSO62 | BOUNDARY/EXTERNAL: locator 부재/DRAFT·WITHDRAWN 정상 복원 가능. 실제 원문/claim/Source Gate 미검증 |
| HSO63 | REAL: 외부 파일/네트워크/환경 조회/시각/난수/프로세스/Source resolve/공식 Coverage 평가 차단 상태의 정상 경로 |
| HSO64 | 실제 전후 파일 감사·신규 모듈 AST/정확한 API/export·회귀. 보존 결과는23.6절 |

이번 함수의 직접 source lookup 추가는 없다. 기존 교차 함수가 메모리 Registry.get_source로 선언을 비교하는 것은 유지하며, 실제 Source 파일/사이트를 재조회하지 않는다. 외부 expected 발급 신뢰·코드 monkeypatch/강제 변조/호스트 격리·서명/공식 원문 의미는 이번 unit/integration 시험이 인증하는 대상이 아니다.

### 23.5 남은 의존성과 다음 최소 작업

| 남은 경계 | 선행/연결 관계 |
|---|---|
| Raw Bytes Preparation | 이번 함수는 exact bytes만 받는다. 실제 명시 archive에서 Review/raw6를 안전하게 확보·고정해야 운영 Content의 L2 원본 연결을 시작할 수 있음 |
| production ZIP | backend import 전에 별도 신뢰된 실행물/환경 검증이 필요. 이 함수가 실행한 검증 코드와 역사 E의 업무 구현 원본 역할을 구분하며, 역사 ZIP을 실제 실행했다고 주장하지 않음 |
| 전체 release | 전체 Envelope 원본 및 호환 역사 환경이 필요. 선택 Envelope 하나/Manifest 복원을 전체 validator 성공으로 대체하지 않음 |
| Content/Source Gate | 공식 Source 원문 bytes·locator/claim/합집합·검토/L3·날짜 사용요건이 필요. Raw7 strict 복원 성공만으로 완성되지 않음 |

**다음 최소 작업 하나는 Review+Historical 원본7종의 Raw Bytes Preparation 계약 설계**다. 허용 archive root/명시 참조·동일 파일 객체 읽기/교체·reparse·TOCTOU/immutable bytes 수명/독립 기대 H/실패 경계를 정하고, 이번 순수 함수에 전달하는 책임까지만 확정한다. 새 History 모델·연결 함수를 자동 추가하거나 production 파일 I/O/ZIP/전체 Content를 동시에 구현하지 않는다.

이 설계 순서는 production ZIP 검증을 뒤로 미뤄도 실제 운영 실행이 안전하다는 뜻이 아니다. 파일 준비 계약은 trusted 합성/검토 환경에서 독립적으로 정할 수 있으며, 실제 운영 진입은 실행 artifact 선행 검증까지 충족하기 전 닫아 둔다. Source/전체 release/원문 준비가 추가로 남는 점도 함께 기록한다.

### 23.6 전체 회귀·변경 범위·최종 판단

사전 actual 전체: **10943 passed in 90.21s (0:01:30)**. 신규 최초199개/최종201개는23.3절과 같다. 사후 actual 전체: **11144 passed in 64.49s (0:01:04)**. 사전/사후 전체는 각각 최초 실행 통과, failed/skipped/timeout0회. 신규 시험은 최초 통과 후 경계2개 추가에 따른 재실행1회이며 실패 수정 재실행0회다.

기존 보호 파일203개 중 **201개 SHA256·크기·mtime_ns 동일**, 변경2개는 승인된 이 계약/Architecture 문서뿐이다. 신규 운영/테스트2개를 추가해 최종 보호 파일205개, 삭제0개다. 기존 운영 코드/테스트/fixture/기대값/export/설정은 전부 보존했다. 실제 release6개는 **SHA256·경로·크기·mtime_ns 전부 동일**. M2.74 부록A의 개별 SHA256/크기/mtime_ns를 이번에도 전수 대조했다. GV01~GV15/BV01~BV16·Coverage freeze·Historical6·M2.71·M2.73·Review 로더·ZIP bootstrap·Acceptance/Benefit/Cashflow·모든 기존 tests/fixture/기대값·export·설정은 보존했다.

**IMPLEMENTED:** 내부 순수 orchestrator 한 함수, B 진입점/전체 expected/원본 A/R/raw6/기존 로더6/교차1 강제, 완전 tuple 원본 반환, fail-closed/기존 오류·순서, 신규 합성201개 및64문서 사례의 범위별 대응.

**NOT IMPLEMENTED:** 실제 파일 preparation·허용 경로/handle/TOCTOU, production ZIP/환경/import 실행 대응, 공식 Source 원문·locator 의미/claim·L3/Source Gate, 전체 release validation·Historical FULL_POLICY·Policy VERIFIED·현재 Acceptance evaluator·Benefit Bridge/Cashflow/API/UI 연결. 반환 tuple은 승인 객체나 영구 provenance 증명서가 아니다.

Coverage core **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, 실제 Ansan **DRAFT / CONDITION_SLICE**와 정책 혜택 Cashflow 반영0원 원칙을 유지한다. 실제 검토/Acceptance/철회·정책 금액·지문·운영 실행 ZIP을 새로 만들지 않았다.

최종 판단: **HISTORICAL_SAME_CALL_ORCHESTRATOR_COMPLETE**. 좁은 raw 입력 기반의 순수 연결 구현/합성 검증 범위에서 완료이며 전체 제품 사용 승인이 아니다.

### 23.7 최종 보고29항목 대응

| 번호 | 항목 | 구현/검증 결과 |
|---|---|---|
| 1 | 구현 요약 | 내부 순수 함수 한 개로 Review→로더6→교차→완전 반환 |
| 2 | 생성·수정 파일 | 신규 운영/테스트2개, 수정은 이 계약/Architecture2개 |
| 3 | 실제 API |23.1절, M2.74와 동일한 private9필수 keyword-only/annotation |
| 4 | expected 전체 | 기존 Review 로더 exact tuple/집합 검사, 원본 tuple 자체 전달 |
| 5 | Review 로더 | B 진입점에서 실제1회 |
| 6 | A/R identity | 기존 selector의 E.acceptance is A 및 이후 원본 보존 |
| 7 | raw6 | 필수 exact bytes, 변환/대체/캐시 없음 |
| 8 | 로더6 순서 | Benefit/Coverage/Envelope/Reviews/Manifest/Registry |
| 9 | 독립 SHA | 기존 E.ref6 기대값·기존 로더 계산, 관찰값 채택 없음 |
| 10 | 교차 강제 | 실제 반환 원본6과 같은 A/R의 기존8입력1회 |
| 11 | 반환 | outer2/inner6 고정 tuple·각 원본 is |
| 12 | Fail-Closed | 모든 단계 첫 예외 종료, 부분 반환 없음 |
| 13 | 후속 미호출 | 실제 오류 및9경계 sentinel·반복 오류에서 이후0회 |
| 14 | prefix/우선순위 | 신규1prefix·기존 내부 오류 유지·P0a~P8 |
| 15 | 예외 객체 | PolicyDataError/RuntimeError 원본 is 전파 |
| 16 | provenance | 같은 호출의 실제 raw 복원/교차 연결, 영구 인증 아님 |
| 17 | I/O/ZIP 한계 | 직접 I/O 없음, 준비/발급 신뢰·운영 실행 검증 미완료 |
| 18 | 수동64 대응 |23.4절, REAL/UNIT/BOUNDARY/EXTERNAL로 구별 |
| 19 | 신규 tests | 최초199 통과→경계2개 추가→최종201 통과, 최초 실패0회 |
| 20 | 전체 pytest | 사전10943 / 사후 11144 passed in 64.49s (0:01:04) |
| 21 | 기존10943 | 기존10,943개 + 신규201개 = 11,144개 전체 회귀 통과, 기존 파일/기대값 보존 |
| 22 | GV/BV | 기존 값·파일 및 전체 회귀 보존 |
| 23 | releases | SHA256·경로·크기·mtime_ns 전부 동일 |
| 24 | freeze | 동결 source/API/상태/지문/Review/오류 계약 변경 없음 |
| 25 | ResidenceHistory | OFFICIAL_INQUIRY_REQUIRED |
| 26 | 실제 Ansan | DRAFT / CONDITION_SLICE, 실제 승인/금액 생성 없음 |
| 27 | 미완료 | 원문/Content/Source/전체 release/운영 ZIP/evaluator/Bridge |
| 28 | 최종 판단 | HISTORICAL_SAME_CALL_ORCHESTRATOR_COMPLETE |
| 29 | 다음 최소 작업 | 원본7종 Raw Bytes Preparation 계약 설계 한 개 |
