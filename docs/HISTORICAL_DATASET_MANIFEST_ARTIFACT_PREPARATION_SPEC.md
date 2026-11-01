# M2.67 — Historical DatasetManifest Artifact Preparation Contract

상태: **IMPLEMENTED / HISTORICAL_DATASET_MANIFEST_LOADER_COMPLETE**. M2.67 설계 및 M2.68 구현: 2026-10-23.

1~31절은 M2.67 당시 설계·검증 기록이다. 당시 산출물은 문서1개, 수동90사례, 신규 실행0개였다. M2.68의 실제 구현/543개 합성 테스트/검증 이력은32절을 따른다. 아래 raw codec/API/오류 계약은 유지한다.

## 1. 목적

정확히 선택한 AcceptanceReviewEntry.dataset_manifest_ref의 과거 Manifest 원본을 독립 기대 SHA256과 **동일 raw bytes**로 검증·복원하는 순수 loader를 설계한다. 기존 DatasetManifest를 반환하고, 세 입력으로 확인 가능한 Acceptance 및 같은 Entry의 선언 참조 관계까지 대조한다.

성공 범위는 원본 복원과 직접 binding이다. 전체 release 정책/출처 집합의 실제 내용 검증, 공식 원문 검증, ZIP 실행 대응, Review MATCHED, Historical FULL_POLICY, Policy VERIFIED, Acceptance USABLE, Cashflow 사용 승인은 별도 책임이다.

## 2. Source of Truth와 조사 결과

다음 기존 문서를 확인했으며 이번 문서로 개정하지 않는다.

| 기존 문서 | 유지하는 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md | 전체 release 검증, 같은 Entry의 Envelope/Registry artifact 대응, domain fp와 raw SHA 분리 |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | 전체 Manifest 집합 검증, 역사 환경 호환성, 같은 호출 원본의 대응 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md | Entry15필드·원본 Acceptance identity·7참조·ACCEPTED/REVOKED |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC.md | 검토 artifact strict bytes와 원본 record 결합·외부 신뢰 경계 |
| HISTORICAL_BENEFIT_SNAPSHOT_ARTIFACT_PREPARATION_SPEC.md | M2.60 loader의 독립 H/동일 bytes/선택 Entry 패턴 |
| HISTORICAL_ELIGIBILITY_COVERAGE_ARTIFACT_PREPARATION_SPEC.md | M2.62 loader의 과거 Coverage 복원 범위 |
| HISTORICAL_POLICY_ENVELOPE_ARTIFACT_PREPARATION_SPEC.md | M2.64 loader의 Envelope/Rule Tree 복원과 Tree 지문 대응 |
| HISTORICAL_COVERAGE_REVIEW_CONTEXT_ARTIFACT_PREPARATION_SPEC.md | M2.66 Context7필드와 dataset/Registry/implementation baseline |
| POLICY_DATA_ENVELOPE_SPEC.md | M1.14 Manifest11필드·UTC snapshot·domain 지문·순수 validator |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | Generic Coverage Core 동결 및 GV01~GV15 |
| RELEASE_ARTIFACT_EXECUTION_BINDING_SPEC.md | 새 MVP 발급 bundle의 동일 source ZIP 선택, 역사 hash 소급 변경 금지 |
| DATA_MODEL.md | 기존 저장 필드·불변 모델·계층 분리 |
| ARCHITECTURE.md | 구현 완료 경계와 미구현 기능의 구분 |

실제 코드 확인 대상은 backend/policy_engine/policy_data/manifest.py, validation.py, envelope.py, benefit_acceptance.py, benefit_acceptance_review_artifact.py, benefit_acceptance_review_artifact_loader.py, historical_*_loader.py 4개, sources/models.py, sources/registry.py, errors.py 및 기존 Manifest 테스트다. Manifest JSON bytes loader는 존재하지 않는다. validate_dataset_manifest는 메모리 도메인 객체의 전체 집합 검증 함수이며 JSON decoder가 아니다. bootstrap의 Manifest header 읽기도 전체 loader가 아니다.

## 3. 현재 검증 공백

| 구분 | 현재 상태 | 이번 범위 |
|---|---|---|
| A BenefitSnapshot | M2.60 strict historical loader 구현 | 보존 |
| B EligibilityCoverage | M2.62 구현 | 보존 |
| C PolicyEnvelope/Rule Tree | M2.64 구현 | 보존 |
| D CoverageReviewContext | M2.66 구현 | 보존 |
| E DatasetManifest | 모델/validator 존재, historical bytes loader 없음 | 원본 복원 계약 설계 |
| F Historical SourceRegistry | 별도 원본 preparation 필요 | 미완료 |
| G Official Source Originals | 실제 원문 확보/내용 검증 필요 | 미완료 |
| H 실제 Implementation Artifact | production ZIP bytes/실행 대응 별도 | 미완료 |
| I 전체 release contents | 전체 정책·Registry·실행 결합 별도 | 미완료 |

E의 성공으로 F~I가 검증됐다고 기록하지 않는다. 현재 일반 SourceRegistry parser가 있다는 사실은 Acceptance가 참조한 역사 Registry bytes 준비 완료를 뜻하지 않는다.

## 4. DatasetManifest 정확한 저장 필드 — 11개

모든 필드는 아래 **선언 순서**다. frozen=True, slots=True, kw_only=True다. required는 기존 Python constructor 기준이며 raw HM1은 기본값 필드도 항상 명시한다. Manifest와 아래 참조 모델 자체에는 Enum 필드가 없다.

| # | 필드 | 실제 타입 | constructor required/default | validation·의미 | HM1 raw |
|---|---|---|---|---|---|
| 1 | schema_version | str | 필수 | exact str, dataset-manifest-1.0 | 필수 string |
| 2 | dataset_id | str | 필수 | exact nonblank str, dataset 계열 식별; 정책 ID 문법 적용 안 함 | 필수 string |
| 3 | dataset_version | str | 필수 | exact nonblank str, semver/날짜 문법 강제 없음 | 필수 string |
| 4 | created_at | datetime | 필수 | exact datetime, utcoffset() is not None | 필수 UTC ISO string; 9절 |
| 5 | freshness_max_age_days | int | 필수 | exact int >=1, bool 불가; 자동 기본7 없음 | 필수 integer |
| 6 | engine_version | str | 필수 | exact nonblank str; constructor는 현재 ENGINE_VERSION과 비교하지 않음 | 필수 string |
| 7 | engine_artifact_sha256 | str | 필수 | exact 소문자 hex64, 엔진 artifact 원본 bytes 기대 SHA | 필수 string |
| 8 | policy_versions | tuple[PolicyEditionReference, ...] | 필수 | exact nonempty tuple/exact items, policy_id 유일 | 필수 array |
| 9 | source_registry | SourceRegistryReference | 필수 | exact type, Registry artifact 및 domain fp 선언 | 필수 object |
| 10 | source_versions | tuple[SourceBinding, ...] | 필수 | exact nonempty tuple/exact items, source_document_id 유일 | 필수 array |
| 11 | review_manifest | ArtifactReference 또는 None | default None | None 또는 exact ArtifactReference | **필수** object 또는 null |

dataset_id/dataset_version/engine_version은 .strip()으로 공백 여부만 검사하며 저장값을 trim하지 않는다. 한국어와 앞뒤 공백이 있는 nonblank 값도 기존 모델이 허용하면 그대로 보존한다. dataset_version의 null/숫자/빈 문자열/공백 전용 문자열은 거부하지만 임의의 semver 정규식을 추가하지 않는다.

Artifact 경로의 중복도 DatasetManifest constructor가 검사한다. 모든 policy artifact.path + Registry artifact.path + review_manifest.path(있으면) 사이에 같은 경로가 있으면 거부한다. 엔진 경로 필드는 없다. 같은 policy_id를 다른 edition으로 두 번 넣거나 같은 source ID를 다른 d version으로 두 번 넣는 것도 거부한다.

## 5. Nested Policy/Source 참조의 정확한 저장 구조

### 5.1 ArtifactReference — 2개, frozen/slots, positional 허용

| 순서 | 필드 | 타입/default | validation |
|---|---|---|---|
| 1 | path | str, 필수 | 빈 값/앞뒤 공백/역슬래시/콜론/제어문자 금지; slash 구성요소 빈 값·`.`·`..` 금지 |
| 2 | sha256 | str, 필수 | 소문자 [0-9a-f] 정확히64자 |

이 문법만으로 symlink/junction, archive root 이탈, 실제 파일 존재를 검증하지 않는다. filesystem 해석과 안전한 한 번 확보는 외부 preparation 책임이다.

### 5.2 PolicyEditionReference — 7개, frozen/slots/kw_only

| 순서 | 필드 | 타입 | constructor required/default | validation |
|---|---|---|---|---|
| 1 | policy_id | str | 필수 | [A-Z0-9]+(?:-[A-Z0-9]+)* |
| 2 | edition_id | str | 필수 | ASCII 숫자4자리; constructor 자체는 0000도 허용 |
| 3 | rule_version | str | 필수 | r 뒤4자리 이상, 양수 정규형; r0000 금지 |
| 4 | artifact | ArtifactReference | 필수 | exact type |
| 5 | fingerprint | str | 필수 | hex64; **Envelope 전체 domain fp**, Tree fp가 아님 |
| 6 | schema_version | str | policy-data-1.0 | 해당 literal만 허용 |
| 7 | rule_schema_version | str | m1.1 | 해당 literal만 허용 |

rule_version의 실제 regex는 r(?:[0-9]{4}|[1-9][0-9]{4,})이며 r0000을 제외한다. SourceBinding의 d version도 같은 양수 규칙을 쓴다. 이 표의 선언 순서와 constructor 내부 validation 순서는 다르며 후자는 14절에서 유지한다.

### 5.3 SourceRegistryReference — 3개, frozen/slots/kw_only

| 순서 | 필드 | 타입 | constructor required/default | 의미 |
|---|---|---|---|---|
| 1 | artifact | ArtifactReference | 필수 | Registry **파일**의 path/raw SHA |
| 2 | fingerprint | str | 필수 | Registry 전체 **도메인 내용** hex64 |
| 3 | schema_version | str | source-registry-1.0 | 해당 literal만 허용 |

registry_id/registry_version 필드는 없다. 이를 빈 문자열이나 새 가짜 ID로 추가하지 않는다.

### 5.4 SourceBinding — 2개, frozen/slots, positional 허용

| 순서 | 필드 | 타입/default | validation |
|---|---|---|---|
| 1 | source_document_id | str, 필수 | canonical ID 문법 |
| 2 | document_version | str, 필수 | d(?:[0-9]{4}|[1-9][0-9]{4,}), d0000 금지 |

이 값은 문서 ID/version 선언이며 문서 원문 파일 경로나 SHA가 아니다. Manifest raw 배열은 같은 순서의 exact tuple로 복원한다.

### 5.5 참조 바깥의 기존 객체

SourceRegistry 저장 필드는 sources 1개(exact nonempty tuple[SourceDocument, ...])이며 source ID 유일성과 bundle 내부 supersedes cycle 등을 검사한다. schema_version은 to_dict 출력에 있고 저장 필드가 아니다.

SourceDocument 저장 필드는 선언 순서로18개다: source_document_id, document_version, source_type, issuer, title, official_url, publication_date, verified_at, verification_status, status, locators, notice_number, attachment_url, previous_urls, effective_from, effective_to, supersedes, content_sha256. 앞11개는 constructor 필수이며 publication_date/verified_at는 명시적 None이 가능하다. 뒤7개는 각각 None, None, (), None, None, (), None 기본값이다. SourceType/VerificationStatus/SourceStatus Enum과 SourceEvidence 등이 실제 문서 계층에 있다. 이18필드는 HM1에 포함하지 않으며 이번 loader가 복원하지 않는다. content_sha256도 Registry 파일 raw SHA와 다르다.

PolicyEnvelope는15개 저장 필드(schema_version, rule_schema_version, policy, edition_id, jurisdiction, category, dataset_version, evaluation_scope, coverage, source_bindings, verification_status, last_verified_at, lifecycle_status, effective_from, effective_to)를 갖는다. HM1에는 Envelope 본문/Rule Tree를 포함하지 않는다. M2.64가 복원할 원본과 후속에 대조한다.

## 6. dataset_manifest_ref와 독립 기대값

선택한 동일 Entry의 dataset_manifest_ref만 사용한다. path는 원본 위치 식별, sha256은 준비·검토 시 이미 고정한 **Manifest 원본 전체 bytes**의 기대값 H다. 이 H는 함수가 받은 bytes를 검사하기 전에 trusted Review Artifact에 존재해야 한다.

실제 파일 digest를 구해 즉석에서 ref에 채우는 자기 검증, 다른 Entry/revision fallback, 현재 Manifest 대체, dataset_version/Registry fp/engine SHA/Manifest domain fp를 H로 사용하는 것을 금지한다. 합성 자료의 저작 단계에서 fixture bytes의 기대 SHA를 고정하는 일과 소비 단계에서 관찰 digest를 기대값으로 채택하는 일은 구분한다.

SHA는 참조한 bytes와의 동일성을 확인한다. 발급 권한·사람 검토의 진실성·공식 정책 최신성을 인증하는 서명은 아니다.

## 7. Raw schema 후보 비교와 확정

| 후보 | 복원·재사용·버전 감지 | 장점 | 판단 |
|---|---|---|---|
| A 기존 to_dict 직접 | 11필드 복원 가능; dataset-manifest-1.0은 도메인 schema | wrapper 없이 작음; 새 strict raw 규약은 여전히 필요 | 채택하지 않음. 기존 snapshot이 이미 strict raw format이었다고 소급 해석하지 않음 |
| B 명시 wrapper | 기존 값/constructor 그대로, raw codec 버전 별도 | 도메인 snapshot/domain fp와 strict 원본 파일 구분; 타 historical wrapper와 일관 | **채택** |
| C 기존 확정 Manifest loader | 전체 Manifest JSON loader가 현재 없음 | 재사용할 구현 없음 | 채택 불가. validator/header reader를 loader로 간주하지 않음 |

최종 raw profile 이름은 **HM1**, discriminator는 **historical-dataset-manifest-1.0**이다. 새로운 도메인 모델을 만드는 변경이 아니다. 기존 실제 release 파일을 변환·덮어쓰지 않는다. HM1이 아닌 과거 파일의 pretty JSON/다른 codec은 자동 변환하여 같은 원본으로 받아들이지 않는다. 해당 원본에 맞는 별도 향후 계약 또는 명시적인 새 archive 발급이 필요하며 기존 ref/H를 바꾸지 않는다.

## 8. HM1 exact schema

| 경로 | exact key 집합 | nullable/array |
|---|---|---|
| root | schema_version, manifest | null 불가 |
| root.schema_version | literal historical-dataset-manifest-1.0 | string |
| manifest | 4절의11필드 전부 | review_manifest만 null 허용 |
| manifest.schema_version | literal dataset-manifest-1.0 | string |
| policy_versions[i] | 5.2절7필드 전부 | non-null object |
| policy_versions[i].artifact | path, sha256 | non-null object |
| source_registry | 5.3절3필드 전부 | non-null object |
| source_registry.artifact | path, sha256 | non-null object |
| source_versions[i] | source_document_id, document_version | non-null object |
| review_manifest(비-null) | path, sha256 | object |

모든 깊이에서 missing/extra key 거부, null과 missing을 구별한다. constructor default를 가진 policy/reference schema 필드와 review_manifest도 raw에서는 생략할 수 없다. source_versions와 policy_versions는 JSON exact list이며 원소는 위 object다. 빈 배열은 P5 형태 검사 후 P6 기존 constructor가 거부한다. review_manifest:null은 정상이다.

primitive는 exact str/int/list/dict/None만 해당 자리에서 허용한다. freshness_max_age_days는 exact int이므로 true/false/string/null 불가. 나머지 모델 str 필드에 숫자를 문자열로 바꾸지 않는다. 이 schema에는 실수 필드와 Enum 필드가 없다. 모든 숫자 token은 정수만 허용하고 float/exponent/NaN/Infinity를 P4에서 거부한다.

wrapper는 root의 manifest 객체를 그대로 담는다. 새 필드 dataset_family, registry_id, engine_path, quarter, manifest_fingerprint, release_verified, profile_flag 등을 추가하지 않는다. 키의 표 나열 순서는 설명/검사 순서이며 실제 canonical object key 순서는 10절의 사전순이다.

## 9. created_at 원본 표현과 복원 한계

HM1은 기존 DatasetManifest.to_dict가 쓰는 **UTC ISO 표현**을 고정한다. 형식은 ASCII `YYYY-MM-DDTHH:MM:SS[.ffffff]+00:00`이며 초는 항상 있고 microsecond는0이면 생략,0이 아니면6자리다. datetime 유효 범위1~9999년을 적용한다. `Z`, naive, 날짜만, 공백 구분자, 비UTC offset, `.000000`, 가변 소수 자릿수, 비정상 날짜/윤초는 HM1에서 거부한다.

후속 loader는 고정 문법을 확인한 뒤 datetime.fromisoformat으로 exact datetime을 만들고 UTC offset=0 및 `value.isoformat() == raw_string`을 확인한다. 누락 offset을 UTC로 추정하거나 비UTC 문자열을 정규화해 통과시키지 않는다. 이 작업은 JSON canonical 검사 후 P6에서 수행한다. 정상 값은 timezone-aware UTC datetime으로 constructor에 전달한다.

기존 constructor는 비UTC timezone-aware datetime도 허용한다. **HM1은 그 전체 Python 입력 공간과 동일하지 않은 archive codec**이다. 기존 public snapshot과 같은 UTC 시점/마이크로초·to_dict/domain 지문 값을 복원한다. constructor 자체의 허용 범위는 변경하지 않는다.

기존 UTC snapshot에 없는 원래 offset 표기, timezone 객체/이름(예: ZoneInfo), fold 값은 완전히 복원할 수 없다. 이를 새 필드로 발명하지 않는다. 원래 tzinfo/fold의 객체 동일성까지 보존해야 하는 요구는 HM1 범위 밖이며 별도 codec 설계가 필요하다. 이번 계약은 그런 복원을 보장하지 않는다. raw bytes 자체는 H로 보존하되 HM1이 저장하지 않은 정보를 되찾았다고 주장하지 않는다.

## 10. Canonical bytes — HM1 고정

SHA256 대상은 wrapper를 포함한 raw_bytes 전체다. strict UTF-8, BOM 없음, 모든 깊이 duplicate JSON key 거부, Unicode scalar만 허용한다. 고립 surrogate는 escape 상태라도 거부한다. Unicode NFC/NFD 등의 정규화, 문자열 trim, path/버전 보정은 없다.

파싱한 root에 `json.dumps(root, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")`를 적용한 bytes와 받은 raw_bytes가 **정확히 같아야 한다**. object key는 Python str의 사전순, 배열은 원본 순서다. compact, trailing newline/공백 없음, 한국어를 ASCII escape로 바꾸지 않는다. 이 규약은 프로젝트 전용이며 범용 JCS 전체 구현을 주장하지 않는다.

raw `-0`은 정수0 파싱 후 canonical `0`과 달라 P5에서 실패한다. 비표준 수치/실수/exponent는 그보다 앞 P4에서 실패한다. 허용 정수는 Python int 변환 가능 범위이며 runtime의 숫자 변환 제한으로 변환할 수 없는 token도 명시적 NUMBER 오류다. P6에서 freshness 양수 조건을 다시 검사한다.

canonical 재직렬화는 입력 bytes와의 대조용이다. 재직렬화한 bytes를 새로운 원본으로 채택하거나 H를 재고정하지 않는다. policy/source 배열을 정렬·중복 제거하여 통과시키지 않는다.

## 11. 서로 다른 SHA/fingerprint 영역

| 값 | 고정 대상 | 이번 loader 동작 |
|---|---|---|
| entry.dataset_manifest_ref.sha256 | HM1 원본 파일 전체 bytes | P3에서 직접 계산·대조 |
| DatasetManifest.fingerprint() | Manifest.to_dict + 정책/source 배열을 ID 기준 정렬한 도메인 값 | 호출/비교하지 않음; R에 대응 필드 없음 |
| PolicyEditionReference.artifact.sha256 | 개별 Envelope 파일 원본 bytes | 선언 보존/Entry 참조 equality만 검사 |
| PolicyEditionReference.fingerprint | Envelope domain snapshot | 보존; 실제 Envelope 대조는 후속 |
| R.coverage_policy_tree_fingerprint | Coverage Tree 전용 payload | Envelope fp와 직접 비교 금지 |
| source_registry.artifact.sha256 | Registry 파일 원본 bytes | 선언 보존/Entry 참조 equality만 검사 |
| source_registry.fingerprint | Registry 전체 도메인 내용 | R의 coverage/benefit Registry fp와 비교 |
| source_versions의 document_version | 개별 문서 d version | 값·순서 보존; SHA가 아님 |
| engine_artifact_sha256 | 엔진 코드 artifact bytes | 값 보존; 19절 조건부 동일 ZIP 검증은 후속 |

Manifest.to_dict는 created_at을 UTC ISO로 바꾸고 tuple을 list로 내보내며 입력 배열 순서를 보존한다. fingerprint()는 fresh dict의 두 배열을 정렬한다. 따라서 배열 순서를 바꾼 두 Manifest의 domain fp가 같아도 raw H는 다를 수 있다. wrapper 포함 HM1 H와 Manifest domain fp도 서로 다르다.

## 12. 동일 bytes와 외부 preparation

외부 trusted preparation이 선택 Entry의 path를 archive root 안에서 해석·검사하고 파일을 한 번 읽어 exact immutable bytes를 확보한다. 같은 객체/내용의 raw_bytes를 P3 hash, P4 decode/parse, P5 canonical 비교, P6 복원에 사용한다. hash용 파일과 parse용 파일을 따로 열지 않는다. 저장소 변경/원본 보존·파일 접근 통제는 외부 책임이다.

순수 loader에는 path 인자, 파일 조회, URL/network, 현재 DB/Registry, 환경변수, 시계, bootstrap, worker, subprocess, LLM 호출이 없다. Entry path는 I/O 명령으로 해석하지 않는다. raw_bytes를 bytearray/memoryview에서 자동 복사하지 않고 P0 exact bytes만 받는다.

## 13. 최종 pure API와 같은 호출 원본 결합

```python
load_historical_dataset_manifest_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> DatasetManifest
```

세 인자는 모두 필수 keyword-only, default 없음, exact type이다. 새 HistoricalDatasetManifest/Result/설정 모델을 만들지 않는다. Registry/Envelope/ReviewContext/current Manifest/expected_hash/skip_validation/프로파일 bool을 인자로 추가하지 않는다.

R=expected_acceptance, A=artifact로 표기한다. P1은 R.status가 ACCEPTED인지, A.review_artifact_ref가 R.review_artifact_ref와 같은지, R.acceptance_ref로 찾은 Entry가 정확히1개인지, **entry.acceptance is R**인지 순서대로 검사한다. 첫 Entry/latest/policy_id만 같은 revision 선택은 금지한다. 값이 같은 별도 R 객체도 identity 실패다. REVOKED의 원본 참조는 기존 모델상 None이며 이 loader의 복원 대상으로 허용하지 않는다.

P2는 그 Entry.dataset_manifest_ref가 exact ArtifactReference인지 확인한다. 정상 모델에서는 ACCEPTED ref 누락/duplicate acceptance_ref가 constructor에서 이미 거부되지만 후속 API의 방어 경계를 명시한다. frozen 객체를 강제로 변조하는 것을 정상 합성 테스트 입력 방식으로 삼지 않는다.

trusted 호출자는 M2.57 등 외부 preparation에서 확보한 정확한 A/R를 같은 호출 흐름으로 공급한다. exact type/is만으로 M2.57이 실제 실행됐거나 사람 검토가 진실함을 인증하지 않는다. 반환 객체에도 그런 provenance 증명 필드를 추가하지 않는다.

## 14. 기존 constructor/validator 재사용 경계

P5는 raw exact schema/primitive를 검사한다. P6에서 9절 created_at을 변환한 다음 다음 순서로 기존 constructor를 호출한다.

1. policy_versions의 **원본 배열 순서대로** 각 ArtifactReference → PolicyEditionReference.
2. source_registry.artifact의 ArtifactReference → SourceRegistryReference.
3. source_versions의 원본 배열 순서대로 SourceBinding.
4. 비-null review_manifest는 ArtifactReference, null은 그대로 None.
5. 모든11필드를 명시하여 DatasetManifest 1회 구성.

배열→tuple과 UTC timestamp decoding만 표현 변환이며 default 채움·값 보정은 없다. 새 historical 도메인 모델, 정책/source 정렬·dedupe·누락 보완·engine hash 생성·최신 Registry 주입을 하지 않는다. nested schema literal은 P5에서 string 타입을 확인하고 P6 기존 constructor에서 검증한다.

constructor 내부 검증 순서도 유지한다. PolicyEditionReference는 policy_id → rule_version → edition_id → artifact type → fingerprint → schema_version → rule_schema_version, SourceRegistryReference는 artifact → fingerprint → schema_version, SourceBinding은 ID → d version이다. DatasetManifest는 schema → dataset_id/dataset_version/engine_version → timestamp → freshness → engine hash → 정책 tuple/ID유일성 → Registry type → source tuple/ID유일성 → review ref type → artifact 경로유일성 순서다. 해시/ID regex를 느슨하게 재정의하지 않는다.

`validate_dataset_manifest(manifest, envelopes, registry)`는 **호출하지 않는다**. 이 함수에는 전체 Envelope tuple과 실제 Registry가 필요하다. 실제 순서는 타입 → 현재 ENGINE_VERSION 호환성 → 제공 정책 ID유일성/전체 집합 일치 → Registry 전체 source ID/d version 집합 → Registry domain fp → Manifest 참조 순서로 각 Envelope dataset/edition/rule/schema/source/Envelope fp/전역 rule ID유일성이다. 파일 SHA·ZIP 실행·전체 공식 원문·freshness 판정은 이 함수만으로 완료되지 않는다.

이 validator에서 engine 비교만 삭제한 복제품을 만들지 않는다. 다른 historical engine_version을 현재 환경에서 검증할 수 없다면 역사 실행 환경 준비 문제로 남긴다. narrow 복원에서 정상 과거 version을 STALE/UNUSABLE 또는 잘못된 역사 자료로 분류하지 않는다.

## 15. 직접 Acceptance dataset/release identity — P7

복원된 M=DatasetManifest에 대해 다음 **고정 순서**를 사용한다.

| 순서 | 직접 검사 | 근거/범위 |
|---|---|---|
| 1 | M.dataset_version == R.coverage_dataset_version == R.benefit_dataset_version | M2.46 same-release 계약; 두 R 필드의 local equality도 보존 |
| 2 | M.policy_versions에서 policy_id == R.policy_id인 ref가 정확히1개 | 이 선택 policy의 Manifest membership |
| 3 | 선택 ref.edition_id == R.scope.edition_id | edition만 확인 |
| 4 | 선택 ref.rule_version == R.coverage_rule_version | 확인 가능한 rule version 문자열 exact equality |

문자열/버전을 trim·추론하지 않는다. R의 coverage_rule_version은 기존 nonblank 검증을 유지하며 Manifest ref의 더 엄격한 r 문법도 유지한다. R 값이 그 문법과 맞지 않거나 다르면 맞는 값으로 고치지 않는다.

R에는 dataset_id가 없으므로 M.dataset_id는 보존만 하며 직접 equality를 주장하지 않는다. 원본 H/Entry는 그 저장값을 고정하지만 별도 dataset 계열의 외부 인증을 제공하지 않는다. created_at/freshness metadata와 R.reviewed_at/valid_until의 신규 시간 관계도 만들지 않는다.

## 16. PolicyEditionReference membership의 수준

| 수준 | 의미 | 이번 성공 범위 |
|---|---|---|
| A | Manifest와 nested 객체의 구조가 유효 | 포함 |
| B | 선택 R의 policy/edition/rule version이 선언 집합에 존재 | 포함 |
| C | 모든 선언 Envelope 원본이 실제로 대응 | 미포함 |
| D | release 전체 정책·출처·환경 검증 | 미포함 |

다른 policy들의 선언도 각 constructor로 구조 검증하지만 실제 파일을 읽지 않는다. 선택 policy가 첫 번째가 아니어도 ID로 찾으며 배열을 바꾸지 않는다. constructor의 policy ID유일성 때문에 다른 edition의 같은 policy를 여러 개 넣을 수 없다.

edition 2026 일치는 2026/Q3 applicability 증명이 아니다. Manifest ref에는 quarter가 없다. R.scope.quarter를 None으로 지우거나 3으로 추정하지 않는다. 실제 Envelope/Benefit/Coverage/Review scope 의미는 후속 내용 검증에서 다룬다.

## 17. 같은 Entry의 직접 참조 관계 — P8

| 순서 | 직접 검사 | 이 단계에서 확인하지 않는 것 |
|---|---|---|
| 1 | M.source_registry.fingerprint == R.coverage_source_registry_fingerprint == R.benefit_source_registry_fingerprint | 실제 Registry domain fp 재계산 |
| 2 | 선택 policy ref.artifact == entry.policy_envelope_ref | 해당 Envelope 파일의 SHA/내용 |
| 3 | M.source_registry.artifact == entry.source_registry_ref | 해당 Registry 파일의 SHA/내용 |

artifact equality는 path와 sha256 **모두**의 값 equality다. 같은 SHA/다른 path도 실패하며 이름 비슷함으로 통과시키지 않는다. 이 관계는 기존 Content Validator 계약을 이번 입력만으로 직접 검사할 수 있는 범위다. 다른 Entry의 Envelope/Registry ref를 빌려오지 않는다.

M.review_manifest는 과거 정책 검토 자료의 참조로 보존한다. entry.coverage_reviews_ref와 자동 equality를 요구하지 않는다. 반환된 M이 검증한 것은 선언끼리의 대응이며 두 다른 파일 bytes가 실제 확보됐다는 증명이 아니다.

## 18. SourceRegistry/SourceDocument 원본 검증 경계

Manifest는 Registry artifact(path/raw SHA), Registry domain fingerprint, 전체 source ID/d version 선언을 보존한다. 별도 registry_id/version은 없다. 이 세 종류의 식별을 하나의 hash로 합치지 않는다.

후속 F에서 독립 기대 raw SHA/동일 Registry bytes를 검증·복원한 뒤 fingerprint_source_registry와 M.source_registry.fingerprint의 equality 및 전체 source ID/d version 집합을 기존 validator에서 대조해야 한다. 실제 Envelope 전체도 별도 확보한다. SourceDocument의 locator/상태/버전/공식 원문 content SHA·내용 확인은 각각 후속 책임이다.

이번 loader는 SourceRegistry 생성, source version 최신 선택, Registry fp 재계산, SourceDocument 원문 다운로드, 공식 최신성 확인을 하지 않는다. Manifest에 지문이 있음 → 참조 선언 확인 → 실제 원본 확보 → 내용 일치 → 공식 근거 검증은 서로 다른 단계다.

## 19. 엔진 compatibility·artifact와 implementation 지문

engine_version은 nonblank compatibility metadata이며 코드 build identity가 아니다. 현재 상수 ENGINE_VERSION=m1.0을 복원 조건으로 강제하지 않는다. engine_artifact_sha256은 정확한 hex64로 보존하되 실제 ZIP bytes/경로/실행 환경을 이 입력으로 알 수 없다.

M2.52는 **새 MVP bundle 발급**에서 엔진과 Coverage implementation이 실제 같은 source ZIP bytes를 쓰도록 선택했다. 해당 profile의 외부 확인이 있으면 Manifest.engine_artifact_sha256 == R.coverage_implementation_fingerprint 및 ReviewContext.implementation_fingerprint가 **필수**다. 같은 bytes를 고정한다는 근거 없이 과거의 서로 다른 역할 지문을 소급해서 같게 만들지 않는다.

HM1/Manifest/R에는 동일 ZIP profile을 인증하는 필드가 없고 세 인자만으로 그 실제 대응을 확인할 수 없다. 따라서 **이번 narrow loader는 두 hash의 무조건 equality를 적용하지 않는다**. profile flag/skip 인자도 추가하지 않는다. 이 차이는 P6 형식 검사 이후 그대로 보존하여 후속 외부 preparation/Content Validator에 넘긴다. HM1 자체를 코드 bundle profile 인증으로 사용하지 않는다.

후속 순서는 명시 외부 profile/bundle 근거 확인 → 같은 ZIP 계약의 선언 SHA equality → 독립 기대 SHA로 실제 ZIP bytes 검증 → bootstrap/worker의 import 및 실행 대응 검증이다. 새 공유 ZIP bundle인데 값이 다르면 그 후속 계층에서 binding contradiction으로 차단하며 정상 STALE로 낮추지 않는다. 우연히 두 hash가 같아도 실제 ZIP 검증/실행이 완료된 것은 아니다. M2.53의 합성 verify-only를 production 검증으로 확대하지 않는다.

## 20. Historical ReviewContext와의 연결

M2.66의 별도 loader를 같은 A/R에 각각 호출한 후, 후속 Content Validator는 다음을 대조한다. 이번 Manifest API에 Context 인자를 추가하거나 두 loader를 합치지 않는다.

| Context 값 | Manifest 대응 | 조건 |
|---|---|---|
| dataset_version | M.dataset_version | 둘 다 R의 same-release dataset version과 일치 |
| source_registry_fingerprint | M.source_registry.fingerprint | 둘 다 R의 coverage/benefit Registry fp와 일치 |
| implementation_fingerprint | M.engine_artifact_sha256 | 19절의 실제 공유 ZIP profile이 확인된 경우에만 같은 bytes equality |
| policy_id/scope | 선택 ref.policy_id/edition_id | policy/edition까지만 직접 확인; quarter 의미는 별도 |

Context는 coverage_reviews_ref로 복원되며 Manifest.review_manifest로 바꿔 읽지 않는다. Context 내부 Review matching/내용 정당성/FULL은 여전히 별도다.

## 21. Loader 성공의 정확한 의미와 반환

성공 시 exact DatasetManifest 하나를 반환한다. 과거 Manifest 파일의 동일 raw bytes가 선택 Entry의 독립 기대 SHA와 일치했고 HM1/기존 constructor 검증을 통과했으며, 그 Manifest의 dataset version·선택 policy/edition/rule version·Registry fp 및 같은 Entry의 Envelope/Registry 선언 참조가 R와 대응한다는 의미다.

원본 H가 그 bytes의 dataset_id/created_at/metadata/참조 값을 고정하지만 R에 없는 identity까지 직접 비교됐다는 의미는 아니다. source_versions의 실제 전체 문서 대응/모든 Envelope/Registry/ZIP 검증은 완료되지 않는다. 최종 사용 상태, boolean verified, FULL/USABLE, 금액·현금흐름 결과를 생성하지 않는다. 반복 호출은 같은 값의 새 immutable Manifest를 반환할 수 있으며 객체 identity 재사용/캐시는 요구하지 않는다.

## 22. Validation precedence — P0~P9

| phase | 고정 작업 | 실패 시 |
|---|---|---|
| P0 | raw_bytes → artifact → expected_acceptance 순서로 exact 타입 | INPUT |
| P1 | ACCEPTED → root review ref equality → acceptance_ref Entry1개 → entry.acceptance is R | REVIEW_BINDING |
| P2 | 선택 Entry.dataset_manifest_ref exact ArtifactReference | EXPECTED_REF |
| P3 | SHA256(받은 raw_bytes 전체) == ref.sha256 | BYTES |
| P4 | BOM/strict UTF-8 → strict JSON/모든 깊이 duplicate/숫자 token → Unicode scalar | ENCODING/JSON/KEY/NUMBER/UNICODE |
| P5 | exact root/manifest schema·nested shape/primitive → canonical bytes equality | FIELDS/SCHEMA/TYPE/NONCANONICAL |
| P6 | UTC timestamp → 14절 nested constructor 순서 → DatasetManifest constructor | TIMESTAMP/MODEL |
| P7 | 15절 dataset → policy membership → edition → rule version | DATASET/MEMBERSHIP/EDITION/RULE_VERSION |
| P8 | 17절 Registry fp → 선택 Policy artifact equality → Registry artifact equality | REGISTRY_FP/POLICY_REF/REGISTRY_REF |
| P9 | exact immutable DatasetManifest 반환 | 추가 gate 없음 |

P5 상세: root exact dict/두 key → wrapper literal → manifest exact dict/11key → manifest schema literal → 4절 필드 순서로 primitive/nested shape 검사. nested record는 각 표 순서, 배열은 입력 순서로 내려간다. object 검사에서 타입 → 필수 key 누락(표 순서) → extra key를 확인한다. shape 검사를 모두 마친 뒤 canonical을 대조한다. nested schema literal 값은 P6 constructor가 담당한다.

P4 JSON 파싱 중 token/중복 오류는 parser가 처음 만나는 것을 보고한다. key 중복과 malformed token의 모든 조합에 별도 전역 탐색 순서를 만들지 않는다. 두 오류가 다른 phase면 반드시 앞 phase가 우선이다. P5 canonical 전 shape 오류, P6 timestamp 전 모델 오류로 순서를 뒤집지 않는다. JSON recursion/decoder 실패는 명시적 JSON 오류로 전달한다.

## 23. Stable 오류 prefix — 22개

후속 구현은 기존 PolicyDataError를 사용하며 `PREFIX: field: 고정된 설명` 형태로 보고한다. 아래는 줄임말이 아닌 정확한 prefix다. raw bytes/전체 개인정보를 오류 메시지에 넣지 않는다. constructor의 알려진 PolicyDataError는 P6 MODEL로 감싸고 field/원인 범주를 보존한다. timestamp의 예상 파싱 ValueError/OverflowError는 TIMESTAMP로 처리한다. 포괄적 Exception으로 프로그래밍 오류를 정상 데이터 상태로 숨기지 않는다.

| # | phase | 정확한 prefix | 의미 |
|---|---|---|---|
| 1 | P0 | INVALID_HISTORICAL_DATASET_MANIFEST_LOADER_INPUT | exact 필수 입력 타입 |
| 2 | P1 | HISTORICAL_DATASET_MANIFEST_REVIEW_BINDING_MISMATCH | status/root ref/Entry 선택/is |
| 3 | P2 | INVALID_HISTORICAL_DATASET_MANIFEST_EXPECTED_REF | 선택 ref 계약 |
| 4 | P3 | HISTORICAL_DATASET_MANIFEST_BYTES_MISMATCH | raw H 불일치 |
| 5 | P4 | INVALID_HISTORICAL_DATASET_MANIFEST_ENCODING | BOM/UTF-8 |
| 6 | P4 | INVALID_HISTORICAL_DATASET_MANIFEST_JSON | malformed JSON/recursion |
| 7 | P4 | DUPLICATE_HISTORICAL_DATASET_MANIFEST_JSON_KEY | 모든 깊이 중복 key |
| 8 | P4 | INVALID_HISTORICAL_DATASET_MANIFEST_NUMBER | 실수/exponent/비표준/변환불가 정수 |
| 9 | P4 | INVALID_HISTORICAL_DATASET_MANIFEST_UNICODE | 고립 surrogate |
| 10 | P5 | INVALID_HISTORICAL_DATASET_MANIFEST_FIELDS | missing/extra |
| 11 | P5 | UNSUPPORTED_HISTORICAL_DATASET_MANIFEST_SCHEMA | wrapper/Manifest 최상위 schema literal |
| 12 | P5 | INVALID_HISTORICAL_DATASET_MANIFEST_TYPE | raw primitive/nested 타입 |
| 13 | P5 | NONCANONICAL_HISTORICAL_DATASET_MANIFEST_BYTES | exact canonical 불일치 |
| 14 | P6 | INVALID_HISTORICAL_DATASET_MANIFEST_TIMESTAMP | HM1 UTC 날짜·시각 |
| 15 | P6 | INVALID_HISTORICAL_DATASET_MANIFEST_MODEL | 기존 constructor invariant |
| 16 | P7 | HISTORICAL_DATASET_MANIFEST_DATASET_MISMATCH | 두 R dataset version과 불일치 |
| 17 | P7 | HISTORICAL_DATASET_MANIFEST_POLICY_MEMBERSHIP_MISMATCH | 선택 policy ref 없음/비유일 |
| 18 | P7 | HISTORICAL_DATASET_MANIFEST_EDITION_MISMATCH | 선택 edition 불일치 |
| 19 | P7 | HISTORICAL_DATASET_MANIFEST_RULE_VERSION_MISMATCH | rule version 불일치 |
| 20 | P8 | HISTORICAL_DATASET_MANIFEST_REGISTRY_FINGERPRINT_MISMATCH | R Registry domain fp 불일치 |
| 21 | P8 | HISTORICAL_DATASET_MANIFEST_POLICY_REFERENCE_MISMATCH | 같은 Entry policy artifact 불일치 |
| 22 | P8 | HISTORICAL_DATASET_MANIFEST_REGISTRY_REFERENCE_MISMATCH | 같은 Entry Registry artifact 불일치 |

예: H 불일치+BOM은 P3 BYTES, canonical 불일치+잘못된 timestamp는 P5 NONCANONICAL, 빈 policy_versions+dataset 불일치는 P6 MODEL, dataset+Registry fp 불일치는 P7 DATASET이다. 실패를 UNKNOWN/STALE/UNUSABLE/빈 Manifest로 낮추거나 fallback하지 않는다.

## 24. 합성 검증 시나리오 — 수동 설계 90개

각 행은 아직 실행하지 않은 설계 사례다. 기본 자료는 유효 HM1/ACCEPTED 원본 A/R/정확한 독립 H이며 해당 행만 변경한다. P4 이후를 검증하는 **합성 자료 저작 단계**에서는 바꾼 fixture bytes의 H를 독립 고정해 P3를 통과시킨다. 소비 중 실제 digest를 기대값으로 채택하지 않는다. 표의 오류 짧은 이름은22~23절 exact prefix에 대응한다.

후속 열의 `단위`는 M2.68에서 pure loader 테스트 가능, `모델`은 기존 constructor에서 거부하는 입력이므로 정상 모델 단계의 테스트, `통합`은 별도 준비/Content Validator/실행 계층에서 가능하다는 뜻이다. 이번 실행 테스트 개수는 어느 행도 증가시키지 않는다.

### 24.1 정상·보존 — HM01~HM16

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 후속 실행 |
|---|---|---|---|---|---|
| HM01 | 정확한 HM1 bytes/H/원본 A/R | exact DatasetManifest 반환 | P9 | loader | 단위 |
| HM02 | 여러 policy ref, 선택 policy는 마지막 | ID로 선택, 모든 입력 순서 보존 | P7/P9 | loader | 단위 |
| HM03 | 여러 source ID/d version | 원본 순서 tuple 복원 | P6/P9 | loader | 단위 |
| HM04 | 한국어 dataset_id/version | 문자 그대로 보존 | P6/P9 | loader | 단위 |
| HM05 | R 두 dataset version과 M이 과거 값으로 같음 | 현재 버전 조회 없이 통과 | P7 | loader | 단위 |
| HM06 | nonblank engine_version이 현재 m1.0과 다름 | metadata 그대로 복원 | P6/P9 | loader | 단위 |
| HM07 | 모든 SHA/domain fp 유효 | 각 원래 값 보존, 영역 섞지 않음 | P6/P8 | loader | 단위 |
| HM08 | review_manifest:null을 명시 | None 복원 | P6 | loader | 단위 |
| HM09 | 별도 경로 review_manifest object | ArtifactReference 보존, coverage_reviews_ref와 같을 필요 없음 | P6 | loader | 단위 |
| HM10 | UTC 시각 microsecond0 | 소수 생략형 복원 | P6 | loader | 단위 |
| HM11 | UTC 시각 microsecond123000 | .123000으로 exact 복원 | P6 | loader | 단위 |
| HM12 | 같은 입력100회 | to_dict 값/반환 타입 일정, 입력 A/R/bytes 불변 | P9 | loader | 단위 |
| HM13 | 서로 다른 historical dataset version의 각각 맞는 R | 각각 자기 원본만 통과 | P7 | loader | 단위 |
| HM14 | source/policy 배열을 각각 다른 순서로 저작·H 고정 | 두 입력 모두 원래 순서, domain fp 동일 가능/raw H 구별 | P5/P9 | loader·저작 | 단위 |
| HM15 | dataset_id/version이 nonblank 앞뒤 공백 포함 | trim 없이 보존, R version도 exact 일치 필요 | P6/P7 | loader | 단위 |
| HM16 | dataset_version이 semver 아닌 한국어 release명 | 임의 문법 추가 없이 통과 | P6/P7 | loader | 단위 |

### 24.2 bytes/strict schema — HM17~HM38

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 후속 실행 |
|---|---|---|---|---|---|
| HM17 | 받은 raw 한 byte 변경, 기존 H | BYTES | P3 | loader | 단위 |
| HM18 | bytes 정상, 독립 H가 다른 valid hex64 | BYTES | P3 | loader | 단위 |
| HM19 | invalid UTF-8, 저작 시 해당 H 고정 | ENCODING | P4 | loader | 단위 |
| HM20 | BOM 포함, 해당 H 고정 | ENCODING | P4 | loader | 단위 |
| HM21 | malformed JSON, 해당 H 고정 | JSON | P4 | loader | 단위 |
| HM22 | root duplicate schema_version | KEY | P4 | loader | 단위 |
| HM23 | policy artifact 내부 duplicate sha256 | KEY | P4 | loader | 단위 |
| HM24 | 잘못된 object key 순서 | NONCANONICAL | P5 | loader | 단위 |
| HM25 | trailing newline/앞뒤 공백 | NONCANONICAL | P5 | loader | 단위 |
| HM26 | pretty-print 정상 JSON | NONCANONICAL; 재작성하여 통과 금지 | P5 | loader | 단위 |
| HM27 | 한국어를 ASCII escape로 표현 | NONCANONICAL | P5 | loader | 단위 |
| HM28 | escaped lone surrogate | UNICODE | P4 | loader | 단위 |
| HM29 | NaN/Infinity token | NUMBER | P4 | loader | 단위 |
| HM30 | freshness 1.0 또는 1e0 | NUMBER | P4 | loader | 단위 |
| HM31 | freshness -0, 그 외 정상 | NONCANONICAL | P5 | loader | 단위 |
| HM32 | root manifest key 누락 | FIELDS | P5 | loader | 단위 |
| HM33 | root extra key | FIELDS | P5 | loader | 단위 |
| HM34 | wrapper schema 미지원 문자열 | SCHEMA | P5 | loader | 단위 |
| HM35 | manifest.schema_version 미지원 | SCHEMA | P5 | loader | 단위 |
| HM36 | manifest.review_manifest key 생략 | FIELDS; default 보충 금지 | P5 | loader | 단위 |
| HM37 | nested ref default schema key 생략 또는 extra key | FIELDS | P5 | loader | 단위 |
| HM38 | root/manifest가 array 또는 null | TYPE | P5 | loader | 단위 |

### 24.3 구조·constructor — HM39~HM62

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 후속 실행 |
|---|---|---|---|---|---|
| HM39 | dataset_version 숫자/null | TYPE | P5 | loader | 단위 |
| HM40 | dataset_version 빈 문자열/공백 전용 | MODEL | P6 | constructor·loader | 단위 |
| HM41 | dataset_id 빈 문자열 또는 engine_version 공백 | MODEL, 실제 constructor 순서 | P6 | constructor·loader | 단위 |
| HM42 | policy_versions 빈 array | MODEL | P6 | constructor·loader | 단위 |
| HM43 | source_versions 빈 array | MODEL | P6 | constructor·loader | 단위 |
| HM44 | 동일 policy ID ref 두 개 | MODEL, 중복 제거 금지 | P6 | constructor·loader | 단위 |
| HM45 | 동일 policy ID, 서로 다른 edition | MODEL | P6 | constructor·loader | 단위 |
| HM46 | 동일 source ID, 서로 다른 d version | MODEL | P6 | constructor·loader | 단위 |
| HM47 | 중복 source ID/d version | MODEL | P6 | constructor·loader | 단위 |
| HM48 | malformed/대문자 hex fingerprint | MODEL | P6 | constructor·loader | 단위 |
| HM49 | malformed engine_artifact_sha256 | MODEL | P6 | constructor·loader | 단위 |
| HM50 | policy artifact/Registry/review artifact 경로 충돌 | MODEL | P6 | constructor·loader | 단위 |
| HM51 | ArtifactReference에 ../, 역슬래시, 콜론 등 | MODEL | P6 | constructor·loader | 단위 |
| HM52 | policy_versions/source_versions가 object | TYPE | P5 | loader | 단위 |
| HM53 | nested record가 null/string | TYPE | P5 | loader | 단위 |
| HM54 | freshness true/false 또는 string | TYPE | P5 | loader | 단위 |
| HM55 | freshness0/음수 | MODEL | P6 | constructor·loader | 단위 |
| HM56 | policy/reference nested schema literal 미지원 | MODEL, 기존 constructor 재사용 | P6 | constructor·loader | 단위 |
| HM57 | 잘못된 policy/source ID 또는 r0000/d0000 | MODEL | P6 | constructor·loader | 단위 |
| HM58 | created_at naive/날짜만/공백 구분자 | TIMESTAMP | P6 | timestamp codec | 단위 |
| HM59 | created_at Z 또는 +09:00 | TIMESTAMP; 자동 UTC 보정 금지 | P6 | timestamp codec | 단위 |
| HM60 | created_at .000000 또는 소수3자리 | TIMESTAMP | P6 | timestamp codec | 단위 |
| HM61 | created_at 불가능한 날짜/윤초 | TIMESTAMP | P6 | timestamp codec | 단위 |
| HM62 | 정상 비UTC datetime Python 객체를 직접 constructor에 전달 | 기존 모델은 허용, HM1 소비 입력은 별도 UTC raw 규약 | 모델/P6 | 기존 모델·codec | 모델/단위 |

### 24.4 Entry·binding·precedence — HM63~HM80

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 후속 실행 |
|---|---|---|---|---|---|
| HM63 | raw bytearray 또는 입력 모델 subclass | INPUT, 변환 금지 | P0 | loader | 단위 |
| HM64 | REVOKED R/정상 철회 Entry | REVIEW_BINDING | P1 | loader | 단위 |
| HM65 | 다른 acceptance revision 또는 root review ref | REVIEW_BINDING | P1 | loader | 단위 |
| HM66 | 값은 같은 별도 R 객체 | REVIEW_BINDING, is 필수 | P1 | loader | 단위 |
| HM67 | A에 R.acceptance_ref 없음/다른 Entry만 존재 | REVIEW_BINDING; first/fallback 금지 | P1 | loader | 단위 |
| HM68 | ACCEPTED ref None/duplicate Entry를 정상 생성 시도 | 기존 constructor 거부; loader P2 방어 계약 별도 | 모델/P2 | Review 모델 | 모델 |
| HM69 | M.dataset_version이 R와 다름 | DATASET | P7 | loader | 단위 |
| HM70 | R policy ID가 Manifest에 없음 | MEMBERSHIP | P7 | loader | 단위 |
| HM71 | 선택 policy edition 다름 | EDITION | P7 | loader | 단위 |
| HM72 | 선택 ref rule_version 다름 | RULE_VERSION | P7 | loader | 단위 |
| HM73 | Registry fp가 두 R baseline과 다름 | REGISTRY_FP | P8 | loader | 단위 |
| HM74 | 선택 policy artifact의 path 또는 SHA만 다름 | POLICY_REF | P8 | loader | 단위 |
| HM75 | Registry artifact의 path 또는 SHA만 다름 | REGISTRY_REF | P8 | loader | 단위 |
| HM76 | 다른 Entry의 valid Manifest bytes와 선택 Entry H | BYTES 또는 이후 직접 binding 실패; 다른 Entry 사용 금지 | P3/P7/P8 | loader | 단위 |
| HM77 | H 불일치+BOM | BYTES 우선 | P3 | loader | 단위 |
| HM78 | noncanonical+잘못된 created_at | NONCANONICAL 우선 | P5 | loader | 단위 |
| HM79 | 빈 정책 array+dataset 불일치 | MODEL 우선 | P6 | loader | 단위 |
| HM80 | dataset+Registry fp 동시 불일치 | DATASET 우선 | P7 | loader | 단위 |

### 24.5 신뢰 경계 — HM81~HM90

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 후속 실행 |
|---|---|---|---|---|---|
| HM81 | M.dataset_id 변경 후 별도 저작/H/Entry 고정, R에 대응 필드 없음 | 보존; R dataset 계열 인증을 주장하지 않음 | P6/P9 | loader·외부 검토 | 단위/통합 |
| HM82 | 다른 policy의 실제 파일이 누락됐지만 HM1 자체 정상 | narrow 통과 가능; 전체 release 성공 금지 | P9 이후 | 전체 release 준비 | 단위/통합 |
| HM83 | Registry 선언은 같지만 실제 Registry bytes 미확보 | narrow 통과 가능; F/G 미완료 | P9 이후 | Registry/원문 준비 | 단위/통합 |
| HM84 | engine SHA와 R implementation fp 다름, profile 근거 없음 | narrow 값 보존; equality/production 검증 미완료 | P6/P9 이후 | ZIP profile 준비 | 단위/통합 |
| HM85 | 새 공유 ZIP profile이 외부 확인됐고 두 SHA가 다름 | 후속 binding 차단, STALE로 낮추지 않음 | 후속 gate | Content/실행 준비 | 통합 |
| HM86 | engine/implementation SHA 같지만 ZIP bytes/실행 미확보 | narrow 통과 가능; 실행 대응 성공 아님 | P9 이후 | bootstrap/worker | 단위/통합 |
| HM87 | edition2026/quarter3 R와 같은 Manifest edition | edition까지만 대응, Q3 의미·FULL 보장 안 함 | P7/P9 이후 | scope/내용 검증 | 단위/통합 |
| HM88 | D Context와 E Manifest가 각각 같은 R로 복원 | dataset/Registry baseline 대응 가능, Review MATCHED/USABLE 아님 | 후속 gate | Content Validator | 통합 |
| HM89 | 정상 HM1 성공 후 외부 loader/Registry/fingerprint/validator 호출 감시 | loader 자체 외부 호출0, 상태/현금 반영0 | P0~P9 | loader | 단위 |
| HM90 | 원래 ZoneInfo/fold가 UTC snapshot에 없음 | 원 시점/마이크로초 보존, 원 timezone/fold 재현 주장 금지 | P6/문서 | archive codec·외부 기록 | 단위/통합 |

형태/값 구분을 유지한다. 예를 들어 malformed dataset version은 임의 semver 실패가 아니라 잘못된 primitive/blank로 설계한다. 원래 모델에서 생성 불가능한 P2 ref 누락/Entry 중복은 frozen 값 강제 변조 없이 모델 단계에서 검증한다. 후속 구현은 표 외에도 field별 parameterization을 할 수 있으나 기존9,421개의 fixture/기대값을 바꾸지 않는다.

## 25. 전체 release/Registry/실행 후속 책임

외부 preparation은 E만 성공해도 A~I를 완료 처리하지 않는다. 후속 whole-release 경로는 Manifest가 선언한 **모든** PolicyEnvelope와 실제 Registry 전체를 확보해 기존 validate_dataset_manifest를 역사 호환 환경에서 호출하고 각 파일 raw H와 domain fingerprint를 각각 대조해야 한다. 선택 policy 하나의 membership으로 전체 set equality를 대신하지 않는다.

기존 validator의 ENGINE_VERSION gate를 우회하지 않는다. 별도 실행 ZIP 검증/worker import 대응이 필요하며 Review matcher/Coverage evaluator 자동 재실행, 외부 FULL boolean 채택으로 이 검증을 대체하지 않는다. 최종 Acceptance 평가/사용 승인은 후속 별도 계약/구현 단계다.

## 26. 동결 계약 영향

변경 허용은 새 문서 이 파일 한 개다. DatasetManifest/PolicyEditionReference/SourceRegistry/PolicyEnvelope/ArtifactReference/기존 Manifest validator/모델 필드·직렬화·domain fingerprint를 수정하지 않는다. 기존 Historical loader4종, Review Artifact models/loader, Acceptance Record21/Context/Result, BenefitSnapshot16/지문/BV01~BV16, frozen Generic Coverage/schema/GV01~GV15, bootstrap, Cashflow, 기존 tests/fixture/기대값, 기존 docs, actual Ansan release6개를 보존한다.

정책 자격 PASS/FAIL/UNKNOWN 판단을 LLM으로 넘기지 않는다. 실제 안산 DRAFT/CONDITION_SLICE와 실제 정책 혜택 Cashflow 반영0원 상태를 유지한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**이며 공식 답변 없이 의미/조건을 추가하지 않는다.

## 27. Assumptions·확인 한계·미해결 사항

- **Assumption A1:** trusted 호출자가 이미 고정된 Review Artifact와 정확한 원본 R를 같은 호출에 공급한다. is/H 검증만으로 검토자 권한이나 M2.57 실제 실행을 인증하지 않는다.
- **Assumption A2:** archive 준비자가 앞으로 HM1로 저작·고정한 Manifest 원본을 보존한다. 기존 실제 releases가 HM1이라고 가정하거나 자동 변환하지 않는다.
- **Assumption A3:** 이번 보존 단위는 기존 public UTC snapshot 의미다. 원래 tzinfo/offset 표기/fold 객체 재현 요구가 생기면 별도 raw codec 검토가 필요하다.
- **확인 불가:** R의 dataset_id 대응 필드, Manifest quarter, engine artifact path/실제 bundle profile, 실제 Registry/모든 Envelope/공식 원문은 세 입력에 없다. 추정값/빈 값/가짜 SHA를 만들지 않는다.
- **후속 미완료:** Historical SourceRegistry strict bytes 준비, 공식 원문, 실제 production ZIP/역사 실행 환경, 전체 release validation, Content Validator, 최종 Acceptance evaluator/현금흐름 연결. 이 작업들을 E 설계의 차단 사유로 확대하지 않는다.
- **이번 좁은 계약의 미결정 사항:** 없음. Raw HM1·UTC 범위·constructor 순서·직접 비교/유보 비교·22오류·순수 API를 확정했다. 후속 범위 승인과 실제 원본 확보는 별도다.

## 28. 최종 판단

**READY_TO_IMPLEMENT_HISTORICAL_DATASET_MANIFEST_LOADER**

독립 기대 SHA, 같은 bytes, 명시 raw HM1, 기존 모델 복원, 선택 Entry identity, 직접 확인 가능한 dataset/선택 policy/Registry/참조 binding을 확정했다. R에 없는 dataset_id/quarter, 실제 Registry bytes, 동일 ZIP profile/실행, 전체 release 진실성은 성공 의미에 포함하지 않는다. 기존 동결 계약과 충돌하는 필드 추가/validator 변경이 필요하지 않다.

## 29. 다음 최소 작업 하나

**M2.68 — Historical DatasetManifest Strict Bytes Loader 구현**. 승인 후 위3개 필수 keyword-only 입력의 pure API 하나를 기존 DatasetManifest/nested constructor로 구현하고, P0~P9/22오류/HM1/direct binding의 합성 실행 테스트를 추가한다. 기존9,421개 테스트·기대값·실제 release를 유지한다. Registry/전체 release/Content Validator/ZIP 실행은 이 구현에 넣지 않는다.

## 30. 작업 검증 기록

- 사전 전체 pytest: **9,421 passed in 73.59s (0:01:13)**. 최초 실행 통과.
- 사후 전체 pytest: **9421 passed in 49.64s**. 최초 실행 통과.
- 신규 실행 테스트: **0개**. HM01~HM90은 수동 설계 사례이며 통과 실적으로 계산하지 않는다.
- 보호 기준선: 기존191개 파일(backend/tests/data/docs/tools 및 루트4개). 실제 release6개의 SHA256·경로·크기·수정시각 기준선을 별도 확보했다.
- 최종 파일 보존 대조: **기존191개 파일 SHA256 동일, 삭제0개, 새 문서1개만 추가하여 보호 집합192개. 기존 코드/tests/fixture/기대값/기존 문서 변경0개. 실제 release6개 SHA256·경로·크기·수정시각 모두 동일**.
- 최초 실패/timeout/재실행: **사전·사후 pytest 각각 최초 실행 통과, 실패0/timeout0/재실행0/skipped0**.

### 실제 release 기준선/최종 대조

실제 release6개는 아래 SHA256이 사전·사후 모두 같다. 크기·UTC 수정시각도 기준선과 동일하다.

| release 상대 경로 | SHA256(사전=사후) | bytes | LastWriteTimeUtc(동일) |
|---|---|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f | 1563 | 2026-10-20T08:37:35.9680027Z |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b | 3803 | 2026-10-20T08:34:42.4474005Z |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 | 1981 | 2026-10-20T08:34:43.2171427Z |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 | 5620 | 2026-10-20T12:23:31.4656538Z |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 | 5944 | 2026-10-20T12:21:00.2764608Z |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 | 2922 | 2026-10-20T12:21:00.2774706Z |

## 31. 최종 보고 항목 대응

사용자 요청29항목은 각각 본문 1/4/5/6/7~8/10/6/12/14/15/16/25/18/19/20/13/21/22~23/24/26/30/30/26·30/30/26/26/27/28/29절에서 확인할 수 있다. 보고 시 수동90사례와 신규 실행0개, 사전·사후 최초 실행/재실행 및 실제 release 보존을 구분한다.

## 32. M2.68 — IMPLEMENTED: Historical DatasetManifest Strict Bytes Loader

### 32.1 실제 구현과 변경 범위

신규 source: backend/policy_engine/policy_data/historical_dataset_manifest_loader.py. 공개 API는 `load_historical_dataset_manifest_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> DatasetManifest`다. 세 입력 모두 exact type/필수 keyword-only이며 추가 옵션이 없다. policy_data/__init__.py에 import/export를 각각1회 추가했다.

신규 tests/test_historical_dataset_manifest_loader.py는 독립 fixture 저작과 M2.57 실제 반환 A/원본 R을 사용한다. 문서 수정은 이 파일과 ARCHITECTURE.md의 구현 상태만이다. 신규2개/기존 수정3개/삭제0개이며 기존 domain 모델/validator/loader/테스트·fixture·기대값은 수정하지 않는다. 새 generic codec framework/도메인/설정 모델은 없다.

### 32.2 구현 계약

- P0 exact 입력 → P1 ACCEPTED/root ref/acceptance_ref Entry1개/`entry.acceptance is R` → P2 해당 dataset_manifest_ref → P3 전체 raw SHA → P4 strict UTF-8/JSON → P5 schema/canonical → P6 UTC timestamp/기존 constructor → P7 dataset/membership/edition/rule → P8 Registry fp/Policy artifact/Registry artifact → P9 반환.23절의22개 오류 prefix를 그대로 PolicyDataError로 보고한다.
- H는 동일 Entry에 이미 고정된 ref.sha256이다. hash mismatch 뒤 decode/parse/constructor를 실행하지 않는다. 같은 raw bytes로 hash/파싱하며 파일을 열거나 다른 Entry의 digest로 fallback하지 않는다.
- HM1 root2/Manifest11/Policy7/Registry3/Artifact2/Source2 필드를 명시적으로 검사한다. default 필드도 raw 필수이고 null과 missing을 구분한다. 모든 깊이 duplicate key, BOM/UTF-8, float/exponent/NaN/Infinity/정수 변환 한도, bool-as-int, 고립 Unicode surrogate, extra/missing/type 및 canonical 표현을 검사한다. 배열은 정렬·dedupe하지 않고 원래 순서의 tuple로 복원한다.
- created_at은9절 UTC ISO를 datetime으로 변환한다. 현재시각/로컬 시간대 추론, 원래 timezone 이름·offset 표기·fold의 복원은 하지 않는다.
- ArtifactReference/PolicyEditionReference/SourceRegistryReference/SourceBinding/DatasetManifest constructor를14절 순서로 사용한다. 알려진 데이터 오류의 field/원인 범주를 P6 MODEL에 보존하며 예상하지 못한 RuntimeError는 숨기지 않는다.
- M.dataset_version을 R의 coverage_dataset_version과 benefit_dataset_version에 각각 비교한다. 선택 policy_id의 정확한 membership/edition/rule version을 확인한다. R에 없는 dataset_id 대응값을 만들거나 edition으로 quarter 의미를 증명하지 않는다.
- Registry domain fp는 R의 coverage/benefit baseline 양쪽과 각각 비교한다. 선택 Policy artifact/Registry artifact는 **같은 Entry**의 관련 ref와 path+sha 모두 비교한다. review_manifest와 coverage_reviews_ref의 자동 equality는 없다.
- engine_version/hash는 구조 검증 후 보존한다. 현재 ENGINE_VERSION 또는 coverage_implementation_fingerprint와 무조건 같게 강제하지 않는다. 동일 source ZIP profile/실제 bytes/실행 대응은 외부 책임이다.

### 32.3 구현 상태와 성공 한계

**IMPLEMENTED:** HM1 strict bytes loader, immutable DatasetManifest11필드/중첩 참조 복원, selected PolicyEditionReference membership, 직접 확인 가능한 Acceptance dataset/Registry/reference binding, 결정적 오류 우선순위와 합성 실행 테스트543개.

**NOT IMPLEMENTED:** Historical SourceRegistry Loader, 전체 release contents validation, production engine ZIP 실행 검증, quarter applicability verification, Content Validator, Source Gate, Acceptance evaluator, Benefit Bridge/Cashflow 연결, FastAPI/React 연결. ReviewContext 교차검증/Review matching/Coverage FULL도 수행하지 않는다. validate_dataset_manifest를 실행하거나 호환성 gate만 삭제한 복제품을 만들지 않는다.

성공은 선택 Entry 원본 H/같은 bytes에서 복원한 선언과 직접 binding의 일치다. 실제 Registry/전체 Envelope/공식 원문/ZIP 실행/FULL_POLICY/VERIFIED/USABLE/현금 반영 성공은 아니다.

### 32.4 HM01~HM90 실행 대응

표의 `실행`은 이번 pure loader 또는 기존 모델 경계의 합성 검증이다. 수동90개를 parameterized 실행543개에 더하지 않는다. 후속 통합 책임을 이번 통과 실적으로 계산하지 않는다.

| 수동 ID | 대응 테스트/검증 내용 | 실행 범위 |
|---|---|---|
| HM01~HM03, HM07~HM09 | test_hm01_11_field_restoration_and_nullable_review / explicit Entry 선택 | 실행:11필드/복수 참조/nullable/원본 순서/지문 영역 |
| HM04~HM06, HM13, HM15~HM16 | test_nonblank_metadata_is_not_normalized_or_assigned_new_grammar / engine 보존 | 실행: 한국어/non-semver/공백 보존/과거 dataset·engine |
| HM10~HM11 | test_utc_timestamp_valid_boundaries | 실행: 초/microsecond/날짜 경계 |
| HM12 | test_100_repetitions_determinism_immutability_and_no_input_mutation | 실행100회, 입력/nested 불변성 |
| HM14 | test_order_unicode_and_utc_snapshot_domain_boundaries | 실행: 배열 순서/domain fp/raw 구분/NFC·NFD |
| HM17~HM18 | raw byte change/wrong hash domain/SHA 차단 | 실행: 독립 H/한 byte 변경 |
| HM19~HM21 | encoding failures/malformed JSON | 실행: BOM/strict UTF-8/잘못된 JSON |
| HM22~HM23 | test_duplicate_keys_at_every_object_depth | 실행: 모든 object 깊이 |
| HM24~HM27 | test_noncanonical_representations_are_not_rewritten | 실행: 공백/정렬/newline/escape |
| HM28 | test_unicode_surrogates_in_values_or_keys | 실행: key/value 고립 surrogate |
| HM29~HM30 | test_noninteger_or_unconvertible_number_tokens | 실행: float/exponent/비표준 수치/정수 변환 한도 |
| HM31 | negative_zero canonical 사례 | 실행: -0 자동 보정 금지 |
| HM32~HM38 | missing/extra/object/schema parameterization | 실행: default도 필수/null과 missing 구분 |
| HM39~HM41 | primitive/constructor/nonblank metadata | 실행: 타입/blank 거부, 새 version 문법 미추가 |
| HM42~HM43 | constructor invariant 빈 collection 사례 | 실행: nonempty tuple 유지 |
| HM44~HM47 | test_duplicate_ids_and_artifact_paths_are_not_deduplicated | 실행: policy/source ID 중복 금지 |
| HM48~HM51 | constructor invariant fingerprint/hash/path 사례 | 실행: hex/경로 문법/경로 중복 |
| HM52~HM55 | collection/object/string/freshness 타입/경계 | 실행: bool-as-int 등 |
| HM56~HM57 | nested schema/ID/r·d version constructor | 실행: 기존 문법 유지 |
| HM58~HM61 | test_utc_timestamp_rejects_non_hm1_without_correction | 실행: naive/Z/offset/소수/불가능 날짜 |
| HM62 | 비UTC aware constructor와 UTC snapshot 비교 | 실행: 기존 모델 허용 범위와 archive codec 분리 |
| HM63 | API/exact 입력/subclass | 실행: 필수 keyword-only/추가 옵션 거부 |
| HM64~HM67 | test_entry_identity_and_status_fail_before_bytes | 실행: status/root/누락/revision/동일 값 별도 R |
| HM68 | invalid manifest ref/duplicate Entry/cross-leg local constructor 오류 | 실행: 기존 모델이 먼저 거부. 정상 모델로 도달 불가한 P2 방어 분기를 frozen 변조로 실행하지 않음 |
| HM69~HM75 | direct bindings/exact artifact path+SHA/same Entry 참조 | 실행: dataset/member/edition/rule/Registry fp/참조 equality |
| HM76 | test_other_entry_matching_digest_never_falls_back | 실행: 다른 Entry H가 맞아도 대체 금지 |
| HM77~HM80 | SHA 차단/cross·within phase precedence | 실행: 앞 phase 오류 우선 |
| HM81 | dataset_id metadata 보존 | 실행: R에 없는 가짜 비교 없음; 별도 계열 인증 미실시 |
| HM82~HM83 | missing-* 경로 fixture/pure 호출 감시 | 실행: 파일/Registry/전체 validator 호출 없음; 실제 release/원문 검증 미실시 |
| HM84 | engine hash 상이/과거 engine 보존 | 실행: profile 근거를 발명하지 않음 |
| HM85 | 실제 공유 ZIP profile 확인 후 contradiction 차단 | **후속 통합 책임, 이번 실행 검증 아님** |
| HM86 | test_engine_hash_equality_or_difference_does_not_prove_zip_execution | 실행: 같거나 다른 SHA 모두 실제 ZIP 인증 아님 |
| HM87 | test_manifest_does_not_prove_or_overwrite_quarter | 실행: R의 None/1~4 quarter를 덮어쓰지 않음; 내용 검증 미실시 |
| HM88 | ReviewContext/Manifest 원본 교차검증 | **후속 Content Validator 책임, 이번 실행 검증 아님** |
| HM89 | pure 호출 감시/AST import·공개 API·전역 cache 검사 | 실행: I/O/network/env/ZIP/다른 loader/전체 validator/평가/domain fp 호출 없음 |
| HM90 | UTC snapshot과 비UTC 원래 offset/fold 대비 | 실행: UTC 공개 값만 복원, 원 timezone/fold 재현 주장 없음 |

정상 HM1 fixture의 독립 고정 SHA256은 `814826438ac659b85f2eee106a6905e07051156cfc75822c6909020a0be39a33`, 길이는1520 bytes다. fixture 저작 encoder/기대 H와 소비 loader의 helper/domain serializer는 분리했다.

### 32.5 실제 검증 이력

- 사전 actual 프로젝트 전체 최초 실행: **9,421 passed in 71.24s (0:01:11)**.
- 임시 사본 신규 합성 최초 실행: **1 failed, 538 passed in 2.25s**. 깊이2000 배열이 이 CPython3.12 JSON decoder에서 정상 parse되어 P5 root TYPE이 발생했다. 신규 테스트가 기대한 P4 recursion JSON 오류가 발생하지 않았다.
- 신규 합성 두 번째 실행: **1 failed, 538 passed in 2.36s**. Python 함수 재귀 한도+100도 JSON decoder의 별도 C 재귀 한도를 넘지 않았다. 동일 신규 사례의 입력 가정을 재확인했다.
- 실제 decoder에서 깊이20000이 RecursionError를 발생시킴을 확인하여 **신규 테스트 입력만** 변경했다. 기존 테스트/기대값/로더 계약은 변경하지 않았다. 세 번째 실행: **539 passed in 2.08s**.
- 다른 Entry H fallback 차단2개와 engine SHA 동일/상이2개를 추가한 최종 신규 합성: **543 passed in 2.66s**. 수동90사례는 별도다.
- 사후 actual 프로젝트 전체: **9964 passed in 48.93s. 사후 전체 최초 실행 통과, skipped0/failed0/timeout0/재실행0**.
- timeout은 현재까지0회다. 사전 전체는 재실행하지 않았다. 신규 첫 두 실패와 수정 후 통과를 구분하며 최초부터 전부 통과했다고 기록하지 않는다.
- 보존 대조: **기존192개 중189개 SHA256 동일, 수정3개는 export/관련 문서2개뿐. 신규 loader/합성 테스트2개를 추가해 최종194개, 삭제0개. 기존9,421개 tests/fixture/기대값·GV/BV·동결 Coverage·모델·기존 loader4종/Review Artifact Strict Loader/bootstrap/Acceptance/Benefit/Cashflow는 보존. 실제 release6개 SHA256·경로·크기·수정시각 모두 동일**.


M2.68 사전=사후 실제 release SHA256:

| release 상대 경로 | SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

### 32.6 최종 판단과 다음 최소 작업

판단은 **HISTORICAL_DATASET_MANIFEST_LOADER_COMPLETE**이며 완료 검증은32.5의 최종 전체 회귀/보존 기록을 따른다. 전체 release/실제 Registry/공식 원문/production ZIP/서비스 사용 승인은 미완료다.

다음 최소 작업은 **Historical SourceRegistry Artifact Preparation Contract 설계 한 개**다. 같은 Entry.source_registry_ref와 Manifest.source_registry.artifact의 H/동일 bytes, 기존 Registry/SourceDocument의 정확한 저장 필드·Enum/날짜·source ID/version/domain fp 복원부터 설계한다. 그 loader나 Content Validator는 이번에 구현하지 않는다. Coverage freeze/GV/BV/기존 loader4종/Review/Acceptance/Benefit/bootstrap/Cashflow/실제 releases를 보존하며 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.
