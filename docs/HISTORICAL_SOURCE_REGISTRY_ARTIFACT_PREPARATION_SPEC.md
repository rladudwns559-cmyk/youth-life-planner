# M2.69 — Historical SourceRegistry Artifact Preparation Contract

상태: **IMPLEMENTED / HISTORICAL_SOURCE_REGISTRY_LOADER_COMPLETE**. M2.69 설계 및 M2.70 구현: 2026-10-23.

1~30절은 M2.69 당시 설계/검증 기록으로 당시 신규 실행 테스트는0개였다. M2.70의 실제 구현/741개 합성 실행 테스트/연결 검증 전환 평가는31절을 따른다. 기존 HSR1/API/오류/수동96사례 계약은 유지한다.

## 1. 목적과 세 가지 무결성 수준

정확한 AcceptanceReviewEntry.source_registry_ref가 가리키는 과거 Registry의 검증된 **동일 raw bytes**에서 기존 SourceRegistry를 복원하고, 실제 `fingerprint_source_registry` 결과를 당시 Acceptance의 두 Registry fingerprint와 대조하는 순수 loader를 설계한다.

| 수준 | 질문 | 이번 범위 |
|---|---|---|
| Raw bytes integrity | 선택 Entry가 고정한 원본 파일 bytes인가? | 독립 raw SHA/동일 bytes/strict canonical 검사 |
| Registry domain integrity | 기존 모델로 유효하며 전체 domain 내용이 당시 확인본과 같은가? | 기존 parser/constructor 및 실제 domain fp 대조 |
| Source usage validity | 특정 정책·사용일·검토 목적에 이 근거를 써도 되는가? | 후속 Content Validator/Source Gate·공식 원문 검토 |

Registry 구조 유효성은 공식 원문의 진실성·선택 근거의 사용 승인·전체 release 검증·서비스 사용 가능 상태를 인증하지 않는다.

## 2. Source of Truth와 실제 코드 조사

| 기존 문서 | 이번 설계에서 유지한 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md | 실제 Registry fp/Manifest 전체 집합/Entry ref/원문·locator·claim 대응 분리 |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | 같은 호출 원본, 전체 release와 source 사용 gate, 현재 사용 승인 분리 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md | 원본 Acceptance와 Entry15필드/7참조/source bindings/원문 참조 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC.md | M2.57 strict bytes와 trusted 원본 record identity |
| HISTORICAL_DATASET_MANIFEST_ARTIFACT_PREPARATION_SPEC.md | M2.68 Manifest 복원 및 같은 Entry Registry 선언 대응 |
| HISTORICAL_BENEFIT_SNAPSHOT_ARTIFACT_PREPARATION_SPEC.md | M2.60 동일 bytes/definition과 provenance 분리 |
| HISTORICAL_ELIGIBILITY_COVERAGE_ARTIFACT_PREPARATION_SPEC.md | M2.62 과거 Coverage 복원과 FULL 구분 |
| HISTORICAL_POLICY_ENVELOPE_ARTIFACT_PREPARATION_SPEC.md | M2.64 기존 raw schema/parser 재사용 및 전체 source 대조 분리 |
| HISTORICAL_COVERAGE_REVIEW_CONTEXT_ARTIFACT_PREPARATION_SPEC.md | M2.66 Context의 Registry baseline 보존 |
| POLICY_DATA_ENVELOPE_SPEC.md | M1.10/11/14 실제 구현 기록의 Source 모델/parser/Registry fp/Manifest 계약 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | Generic Coverage 동결, 실제 정책별 blocker 유지 |
| DATA_MODEL.md | SourceRegistry/Document/Evidence/참조·불변 모델의 실제 저장 구조 |
| ARCHITECTURE.md | 구현된 Historical loader5종 및 아직 없는 Content Validator/Source Gate |

실제 조사: backend/policy_engine/sources/models.py·registry.py·loader.py·__init__.py, policy_data/envelope.py·manifest.py·validation.py·benefit_acceptance.py·benefit_acceptance_review_artifact.py 및 그 strict loader, historical_*_loader.py5종, errors.py, 기존 Source/Manifest/Registry loader 테스트다. `SourceValidationError`와 `ManifestValidationError`는 기존 `PolicyDataError`의 하위형이다.

POLICY_DATA_ENVELOPE_SPEC.md의 초기 전체 검증 목표와 후속 M1.10/11 구현 기록을 구별한다. 현재 constructor의 supersedes 검증은 bundle 안의 정확한 확인본 순환까지이며, 과거 release 대상의 존재/공식 대체 의미/상태 동기화는 완료됐다고 하지 않는다는 후속 기록을 따른다. 새 역사 검증을 이유로 모델을 바꾸지 않는다.

## 3. 현재 구현 범위와 남은 공백

Historical BenefitSnapshot(M2.60), EligibilityCoverage(M2.62), PolicyEnvelope/Rule Tree(M2.64), CoverageReviewContext(M2.66), DatasetManifest(M2.68) strict loader는 구현 완료다. 이번에는 **Historical SourceRegistry 원본 preparation 계약**을 설계한다.

일반 `load_source_registry`/`parse_source_registry`와 Registry domain fingerprint helper는 이미 있다. 그러나 선택 Acceptance Entry의 독립 raw SHA와 같은 bytes에 결합해 Registry를 복원·대조하는 historical loader는 아직 없다. 일반 파일 loader가 있다는 사실로 이 공백이 닫혔다고 하지 않는다.

공식 SourceDocument 원문 bytes, 실제 locator 위치/claim 의미, 특정 날짜 사용요건, 전체 release, production implementation ZIP, Review Content Validator/Source Gate/Acceptance evaluator/Benefit Bridge는 별도다.

## 4. SourceRegistry 정확한 저장 필드 — 1개

frozen=True, slots=True이며 positional constructor도 허용한다.

| 순서 | stored field | 실제 타입 | 필수/default | nullable | 검증·의미 |
|---|---|---|---|---|---|
| 1 | sources | tuple[SourceDocument, ...] | 필수, 기본값 없음 | 불가 | exact nonempty tuple/exact SourceDocument; source_document_id 유일; 같은 bundle의 정확한 ID/version 노드 간 supersedes cycle 거부 |

registry_id, registry_version, dataset_version, created_at, status, verification_status, fingerprint는 Registry 저장 필드가 아니다. JSON schema_version도 저장 필드가 아니라 `to_dict()`가 출력하는 고정 문법 discriminator다. 없는 ID/version/date를 추가하거나 빈 값으로 채우지 않는다.

`to_dict()`는 `schema_version: source-registry-1.0`과 sources 배열의2key dict를 새로 만든다. 문서/locator/정책 ID/URL/대체 pair의 **객체 저장 순서**는 보존한다. domain fingerprint는 별도 helper의 fresh snapshot 정렬을 사용한다.

## 5. SourceDocument 정확한 저장 필드 — 18개

frozen=True, slots=True, kw_only=True. 다음은 **실제 선언 순서**다. raw 필수/선택은 기존 parser와 같은 HSR1 계약이다. null 가능성과 raw 생략 가능성은 별개다.

| # | 필드 | 실제 타입 | constructor 필수/default | HSR1 raw | validation·의미 |
|---|---|---|---|---|---|
| 1 | source_document_id | str | 필수 | 필수 string | canonical 내부 문서 ID |
| 2 | document_version | str | 필수 | 필수 string | d0001부터의 양수 정규형 |
| 3 | source_type | SourceType | 필수 | 필수 canonical string | 7절3개 값 |
| 4 | issuer | str | 필수 | 필수 string | exact nonblank, trim하지 않음 |
| 5 | title | str | 필수 | 필수 string | exact nonblank |
| 6 | official_url | str | 필수 | 필수 string | HTTPS URL 문법; 공식성은 미인증 |
| 7 | publication_date | date 또는 None | 필수 | **필수** ISO string 또는 null | null 가능, 생략 불가 |
| 8 | verified_at | date 또는 None | 필수 | **필수** ISO string 또는 null | VERIFIED이면 date 필수 |
| 9 | verification_status | VerificationStatus | 필수 | 필수 canonical string | DRAFT/VERIFIED/STALE |
| 10 | status | SourceStatus | 필수 | 필수 canonical string | ACTIVE/SUPERSEDED/WITHDRAWN |
| 11 | locators | tuple[SourceEvidence, ...] | 필수 | 필수 array | exact nonempty/exact items; locator_id 유일 |
| 12 | notice_number | str 또는 None | None | 선택 string 또는 null | 비-null이면 nonblank |
| 13 | attachment_url | str 또는 None | None | 선택 string 또는 null | 비-null이면 HTTPS URL |
| 14 | previous_urls | tuple[str, ...] | () | 선택 array | URL들, 중복 금지, 빈 tuple 허용 |
| 15 | effective_from | date 또는 None | None | 선택 ISO string 또는 null | 명시 효력 시작일 |
| 16 | effective_to | date 또는 None | None | 선택 ISO string 또는 null | 양쪽 있으면 from <= to |
| 17 | supersedes | tuple[tuple[str, str], ...] | () | 선택 pair object array | ID/d version/중복/정확한 자기 pair 금지 |
| 18 | content_sha256 | str 또는 None | None | 선택 string 또는 null | 비-null이면 소문자 hex64; 공식 원문 bytes 지문 선언 |

Registry는 문서 ID당 하나의 선택 확인본만 담는다. 서로 다른 ID의 d0001/d0002 문서는 공존할 수 있지만, **같은 ID의 서로 다른 d version 두 개는** DUPLICATE_SOURCE_ID다. 과거 version의 공존은 여러 immutable release 또는 supersedes pair 표현으로 구분한다.

문서의 verified_at이 None인데 locator verified_at이 있거나, locator 확인일이 문서보다 이후이면 EVIDENCE_DATE_MISMATCH다. publication_date와 verified_at 사이의 추가 날짜 순서, 현재 날짜 비교, status 간 자동 동기화는 기존 constructor에 없으므로 새로 추가하지 않는다.

## 6. SourceEvidence 정확한 저장 필드 — 9개

frozen=True, slots=True, kw_only=True. 소속 source_document_id는 부모 SourceDocument.locators의 포함 관계로 결정되며 이 객체 안에 중복 저장하지 않는다.

| # | 필드 | 실제 타입 | constructor 필수/default | HSR1 raw | 검증 |
|---|---|---|---|---|---|
| 1 | locator_id | str | 필수 | 필수 string | [a-z][a-z0-9]*(?:-[a-z0-9]+)* |
| 2 | section | str | 필수 | 필수 string | exact nonblank |
| 3 | meaning_summary | str | 필수 | 필수 string | exact nonblank; 의미 검토의 결과 선언 |
| 4 | applicable_policy_ids | tuple[str, ...] | 필수 | 필수 array of strings | exact nonempty, canonical ID, 중복 금지 |
| 5 | verified_at | date 또는 None | 필수 | **필수** ISO string 또는 null | VERIFIED이면 date 필수 |
| 6 | verification_status | VerificationStatus | 필수 | 필수 canonical string | DRAFT/VERIFIED/STALE |
| 7 | status | SourceStatus | 필수 | 필수 canonical string | ACTIVE/SUPERSEDED/WITHDRAWN |
| 8 | page | int 또는 None | None | 선택 integer 또는 null | 비-null이면 exact int>=1, bool 불가 |
| 9 | table_position | str 또는 None | None | 선택 string 또는 null | 비-null이면 nonblank |

to_dict는9필드 전부를 내보내되 page/table_position을 section 다음에 두므로 **serializer key 나열 순서와 저장 선언 순서는 다르다**. HSR1 canonical key 정렬은 이 차이와 별개다. page는 보조 metadata이고 locator는 semantic ID이며 URL fragment/DOM selector가 아니다.

## 7. Enum·기본 문법·참조 모델

| 실제 Enum | 정확한 member/value 순서 |
|---|---|
| SourceType | OFFICIAL_NOTICE, OFFICIAL_POLICY_PAGE, OFFICIAL_QUARTER_GUIDE |
| SourceStatus | ACTIVE, SUPERSEDED, WITHDRAWN |
| VerificationStatus | DRAFT, VERIFIED, STALE |

raw Enum은 exact str의 canonical value만 허용하며 alias/대소문자/공백 보정을 하지 않는다. Python domain constructor에는 exact Enum instance가 필요하고, 그 변환은 기존 parser의 책임이다. 사용자 RegistrationSource/FactBasis와 통합하지 않는다.

ID 문법은 `[A-Z0-9]+(?:-[A-Z0-9]+)*`, d version은 `d(?:[0-9]{4}|[1-9][0-9]{4,})`에서 d0000을 제외한다. 날짜는 null 또는 ASCII YYYY-MM-DD의 실제 유효 date(1~9999년)다. datetime/시간대/날짜 절삭·추정은 없다.

URL은 정확한 HTTPS prefix, hostname, userinfo 없음, 유효 port, 공백/제어문자 없음 등을 기존 모델로 검사한다. 공식 도메인 allowlist·접속 성공·redirect·원문 존재·기관 공식성은 검사하지 않는다. URL을 따라가거나 현재 URL로 교체하지 않는다.

| 기존 참조 모델 | 실제 stored fields/의미 |
|---|---|
| SourceBinding | source_document_id, document_version의2필드; ID/d version. Registry 객체/파일/locator 본문이 아님 |
| ArtifactReference | path, sha256의2필드; 안전 상대 경로 문법과 hex64. 파일 존재/경로 해석은 외부 책임 |
| SourceRegistryReference | artifact, fingerprint, schema_version의3필드; schema 기본값 source-registry-1.0. registry_id/version 없음 |

근거 ref 문자열은 `source_document_id#locator_id`이고 `parse_evidence_ref`가 정확한 str/#1개/양쪽 문법을 검사한다. SourceEvidence 안에 별도 evidence_ref 저장 필드를 만들지 않는다.

## 8. 정확한 ReviewEntry 선택과 source_registry_ref

R=expected_acceptance, A=artifact, E=선택 Entry라 한다. P1 순서는 R.status가 ACCEPTED → A.review_artifact_ref == R.review_artifact_ref → R.acceptance_ref로 찾은 Entry가 정확히1개 → **E.acceptance is R**다. 첫 Entry/같은 policy의 다른 revision/latest 자동 선택, 같은 값인 별도 R, 다른 Entry로 fallback을 허용하지 않는다.

P2에서 E.source_registry_ref가 exact ArtifactReference인지 확인한다. 정상 모델의 ACCEPTED ref 누락/duplicate Entry는 기존 constructor가 먼저 거부한다. 이 방어 분기를 테스트하기 위해 frozen 모델을 강제로 훼손하지 않는다. REVOKED는 참조 None 계약을 유지하며 이 loader의 원본 복원 대상이 아니다.

E.source_registry_ref.path는 외부 위치 식별이고 sha256은 Registry 원본 파일 bytes 전체의 독립 기대 H다. 같은 Acceptance revision의 참조만 사용한다. 현재 Registry를 대체 공급하거나 filename/size/mtime로 H를 대신하지 않는다.

## 9. 독립 raw SHA와 domain fingerprint의 분리

| 값 | 실제 대상 | 기대값 원천 | 계산·비교 |
|---|---|---|---|
| H_raw | Registry 파일 전체 raw bytes | E.source_registry_ref.sha256 | P3 SHA256(raw_bytes) |
| F_registry | 기존 Registry 전체 구조화 snapshot | R.coverage_source_registry_fingerprint 및 R.benefit_source_registry_fingerprint | P7 기존 helper 실제 계산 → P8 각각 비교 |
| F_manifest | 당시 Manifest의 Registry domain 선언 | M.source_registry.fingerprint | 17절 같은 호출/후속 결합 |
| 공식 원문 SHA | 개별 PDF/HWP/HTML 등 원문 bytes | SourceDocument.content_sha256/ReviewSourceOriginal.artifact | 이번 원문 bytes 검증 범위 밖 |

H_raw와 F_registry의 equality를 요구하지 않는다. domain fp를 파일 hash로, raw hash를 domain fp로 대체하지 않는다. 실제 digest를 관찰한 뒤 기대 H 또는 R fp에 자동 채택하지 않는다. 합성 저작 단계의 독립 fixture H/F 고정과 소비 시 actual 계산은 별도다.

H_raw는 보존된 참조와의 동일성을 검증한다. 검토자의 실재/권한·공식성·검토 충분성·과거 version 덮어쓰기 부재를 인증하는 서명은 아니다.

## 10. Raw schema 후보와 최종 선택

| 후보 | 기존 parser 재사용/복원/버전 감지 | 비용·한계 | 판단 |
|---|---|---|---|
| A source-registry-1.0 직접 | 공개 pure parse_source_registry에 같은 parsed root 전달 가능; 기존 discriminator 존재 | strict bytes/canonical 검사를 앞단에 추가해야 함 | **채택** |
| B historical wrapper | 내부 Registry parser 재사용 가능 | 기존 schema 외 wrapper/shape 증가; 현재 추가 정보 필요 없음 | 미채택 |
| C 파일 load_source_registry 직접 또는 다른 최소 전달 | 파일 loader는 path를 열고 JSON 읽음; 메모리 parser는 A와 동일 | 재open은 동일 bytes 원칙 위반, text/path 우회는 불필요 | 파일 loader 미채택; pure 경계는 A로 사용 |

최종 raw profile은 **HSR1**, root discriminator는 기존 **source-registry-1.0**이다. 새 historical schema wrapper/도메인 모델을 만들지 않는다. 기존 Registry schema 자체와 충돌하는 JSON 의미 변경은 없다. 기존 일반 loader가 canonical bytes를 요구했다는 주장은 하지 않는다. HSR1은 historical 소비 경계의 추가 bytes 규약이다.

기존 실제 release pretty JSON은 수정하지 않는다. 해당 bytes의 H가 일치해도 HSR1 canonical이 아니면 거부하며 파일을 자동 재작성하지 않는다. canonical archive를 새로 발급하려면 독립된 새 원본/ref/H 검토가 필요하며 기존 참조를 조용히 덮어쓰지 않는다.

## 11. HSR1 exact raw schema와 선택 필드

| raw 객체 | 필수 key | 선택 key |
|---|---|---|
| root | schema_version, sources | 없음 |
| sources[i] | 5절1~11번 전부 | 5절12~18번7개 |
| sources[i].locators[j] | 6절1~7번 전부 | page, table_position |
| sources[i].supersedes[k] | source_document_id, document_version | 없음 |

root.schema_version은 exact str literal source-registry-1.0이다. sources/locators/applicable_policy_ids는 필수 exact JSON list다. previous_urls/supersedes는 있으면 exact list이고 null 불가다. list 원소는 각각 Document/Evidence/정책 ID string/HTTPS URL string/정확한2key supersedes object다.

모든 record는 허용 key 집합을 넘는 extra를 거부하고 **필수** key missing을 거부한다. 선택 key 생략은 기존 parser 계약대로 허용한다. SourceDocument.publication_date/verified_at 및 SourceEvidence.verified_at는 null이어도 **key 자체가 필수**다.

nullable optional인 notice_number/attachment_url/effective_from/effective_to/content_sha256/page/table_position은 생략과 명시 null이 모두 허용되고 기존 constructor 기본 None으로 복원된다. previous_urls/supersedes는 생략 또는 []만 같은 빈 tuple 의미이며 명시 null은 오류다. 선택값의 이 기존 default 복원은 허용된 표현 변환이다. 소득/정책 날짜/현재 source/새 version을 보충하는 자동 보정과 구별한다.

원본이 optional을 생략했는지는 **raw H와 보존 bytes**에 남는다. 모델 자체에는 생략 표시가 없어 `to_dict()`는 기본값까지 전부 출력한다. 따라서 생략형과 명시 기본값형은 model/domain fp가 같고 raw H는 다를 수 있다. 소비 과정에서 빠진 raw key를 채워 canonical 대조하지 않는다. 모델만으로 생략형 원본 bytes를 재현했다고 하지 않는다.

primitive는 해당 자리의 exact str/int/list/dict/None만 허용한다. page의 bool/string은 P5 TYPE, float/exponent는 P4 NUMBER다. null 가능성을 제외한 다른 str 자리의 null은 P5 TYPE이다. Enum 문자열/날짜의 **값** 검증은 기존 parser가 P6에서 수행한다. 빈 sources/locators/applicable_policy_ids는 P5 shape 이후 P6 기존 nonempty constructor가 거부한다.

## 12. Canonical bytes — HSR1

받은 전체 bytes를 SHA 대상으로 한다. strict UTF-8, BOM 없음, 모든 깊이 duplicate key 거부, malformed JSON/비표준 수치 거부, key와 value의 고립 surrogate 거부를 적용한다. 숫자 token은 정수만 허용하며 float/exponent/NaN/Infinity와 runtime에서 변환 불가한 정수는 NUMBER다.

파싱한 **원래 raw root**에 `json.dumps(root, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")`를 적용한 결과와 받은 raw_bytes가 정확히 같아야 한다. object key는 Python str 사전순, arrays는 원본 순서다. trailing newline/공백/pretty/key 순서/불필요한 escape 차이는 거부한다. -0은 parse 후 canonical0과 달라 NONCANONICAL이다.

canonical 대조 대상은 Registry.to_dict나 정렬한 fingerprint payload가 아니다. optional 생략과 배열 순서를 보존한 raw object다. 재직렬화는 비교용이며 출력 bytes로 원본을 바꾸거나 기대 H를 갱신하지 않는다. JCS 전체 구현을 주장하지 않는다.

Unicode 정규화는 없다. NFC/NFD의 실제 문자열은 각각 허용·보존되고 값/H/domain fp가 달라질 수 있다. 이를 비정규라는 이유로 NFC로 보정하지 않는다. 같은 한국어 값을 ASCII escape로 표현한 경우는 ensure_ascii=False canonical과 달라 거부한다. escape/인코딩의 비정규 표현과 실제 Unicode normalization form을 혼동하지 않는다.

## 13. 동일 bytes 확보와 순수 경계

외부 preparation이 archive root/경로 우회/symlink·junction 등을 확인하고 원본 파일에서 immutable exact bytes를 한 번 확보한다. 이 동일 raw_bytes로 P3 SHA → P4 strict decode/JSON parse → P5 canonical 대조 → P6 parse_source_registry → P7 actual domain fp를 수행한다.

H 검사 후 파일 재open, 현재 Registry 조회, URL 따라가기, 다른 parsed 객체/Registry.to_dict로 대체, 외부에서 만든 Registry를 원본으로 채택하지 않는다. 같은 parsed root를 existing pure parser에 직접 전달한다. 정렬·default 삽입·filter·subset 생성으로 parsed root를 바꾸지 않는다.

filesystem/network/Git/env/현재 시각/random/global mutable cache/ZIP/서브프로세스/LLM 호출은 loader에 없다. Entry path는 loader에서 열지 않는다. 저장소 보존·접근 통제·사람 검토/원본 공식성은 외부 책임이다.

## 14. 기존 loader/parser 재사용의 정확한 경계

| 실제 함수 | 입력/반환 | I/O·사용 판단 | 이번 결정 |
|---|---|---|---|
| load_source_registry(path: str 또는 Path) | 파일 경로 → SourceRegistry | Path.open + json.load, duplicate key/constant 처리 | 호출하지 않음; 재open 금지 |
| parse_source_registry(data: object) | 실제로 exact dict/source-registry-1.0 및 nested JSON 값 → exact SourceRegistry | 파일/시각 조회 없음; 배열/날짜/Enum 변환 후 기존 constructor | **P6에 정확히1회 재사용** |
| fingerprint_source_registry(registry: SourceRegistry) | exact Registry → 소문자 SHA hex64 | 메모리 snapshot만 사용 | **P7에 정확히1회 재사용** |

파일 loader에는 H/canonical/선택 Acceptance binding이 없으며 pure parser에는 decode 시점 duplicate key 정보가 없다. HSR1 앞단이 이 경계를 닫는다. 기존 loader/parser/fingerprint를 수정하거나 파일 API를 BytesIO/임시파일로 우회하지 않는다. private `_document`/`_evidence` 등을 복제해 새 parser를 만들지 않는다.

P6의 실제 변환은 JSON list→tuple, canonical Enum string→기존 Enum, null/ASCII ISO date→None/exact date, supersedes object→(ID, version) tuple뿐이다. optional 기본값은11절 그대로다. source/locator/URL/대체 pair를 sort/dedupe하지 않는다.

같은 source list 순서로 `_document`를 구성한 후 전체 SourceRegistry constructor를 호출한다. `_document`는 supersedes pair를 먼저 준비하고, Python keyword 인자 평가 순서로 source_type Enum → publication_date → verified_at → verification_status → status → locators 각각의 `_evidence` → previous_urls 배열 → effective_from/to 날짜를 평가한 뒤 SourceDocument constructor를 호출한다. Evidence는 정책 ID 배열 → verified_at 날짜 → verification/status Enum 변환 후 constructor를 호출한다.

따라서 source ID가 잘못됐어도 같은 문서의 source_type Enum 변환 실패가 먼저일 수 있다. P6의 우선순위는 이 **기존 parser/constructor 실행 순서**를 유지하며 신규 field 검사로 앞질러 재정의하지 않는다. Document 생성 이후에야 Registry의 ID 중복/순환 검사가 실행된다. P5는 형태/primitive만 검사하여 이 의미 검증 순서를 보존한다.

기존 parser의 알려진 PolicyDataError는 P6 MODEL로 감싸고 기존 code/field를 보존한다. 기존 field가 sources/locators처럼 거친 경로라면 없는 배열 index를 발명하지 않는다. 예상 밖 프로그래밍 예외는 포괄적 Exception으로 숨기지 않는다.

## 15. Registry domain fingerprint의 정확한 계산

기존 policy_data/manifest.py의 `fingerprint_source_registry`를 그대로 사용한다. **Registry 전체**의 to_dict에 기반하며 선택 policy/Entry.source_bindings로 부분 필터하지 않는다.

1. exact SourceRegistry 입력을 확인한다.
2. 새 `registry.to_dict()` snapshot을 만든다. root schema_version + 모든 Document18필드 + Evidence9필드가 포함된다. Enum.value/date ISO/null/default/URL/status/확인일/내용 SHA 선언까지 포함하며 Benefit definition fp처럼 provenance를 제외하지 않는다.
3. fresh snapshot의 sources를 source_document_id로 정렬한다.
4. 각 문서의 locators를 locator_id로, supersedes를 (source_document_id, document_version)으로 정렬한다.
5. 각 locator의 applicable_policy_ids를 정렬한다.
6. 기존 `_digest`가 sort_keys=True, compact separators, ensure_ascii=False, allow_nan=False의 JSON을 UTF-8로 인코딩해 SHA256을 반환한다.

**previous_urls는 정렬하지 않는다.** 그 순서 변화는 기존 domain fp를 바꿀 수 있다. sources/locators/supersedes/applicable_policy_ids의 나열 순서는 domain fp에 정렬 반영되지만 반환 객체/원래 raw 배열은 바꾸지 않는다. 일반 raw canonical 검사는 어떤 array도 정렬하지 않는다.

기존 fp payload에 historical wrapper/prefix/새 필드/사용일/현재 Registry 정보를 추가하지 않는다. domain fp 생성 실패의 기존 PolicyDataError는 P7 FINGERPRINT 오류다. 실제 F를 한 번 계산해 R의 두 expected fp와 비교하며 expected를 actual로 교체하지 않는다.

## 16. 직접 Acceptance binding — P8

P7에서 계산한 F를 다음 **순서로 각각** 비교한다.

1. F == R.coverage_source_registry_fingerprint.
2. F == R.benefit_source_registry_fingerprint.

R의 same-release local invariant가 두 값의 equality를 이미 요구하더라도 어느 한 비교를 생략하지 않는다. 불일치는 원본 binding contradiction으로 보고하며 STALE/UNUSABLE/메타데이터 미검토 상태로 낮추지 않는다.

Registry에는 registry_id/version/dataset_version/policy_id 저장 필드가 없다. 비교용 가짜 ID/version/dataset을 만들지 않는다. source-registry-1.0은 raw schema, 각 문서 d version은 SourceDocument 확인본 버전이다. source IDs/versions/locators 등은 전체 fp 안에 들어가 실제 확인본을 고정한다.

**범위 결정:** 이 narrow API에는 Entry.source_bindings/claim evidence의 개별 사용 대상 검증을 추가하지 않는다. Entry의 ID/d version 부분 membership은 세 입력으로 일부 계산할 수 있지만, Envelope+Benefit source 합집합/정확한 locator/claim 원문 대응을 대신할 수 없다. 그 기존 Content Validator 책임을17/19절에 유지한다. 이 선택을 계산 불가능하다는 주장으로 설명하지 않는다.

## 17. Historical DatasetManifest 연결과 실제 가능한 비교

M2.68로 복원한 M에는 source_registry.artifact/fingerprint/schema_version과 source_versions가 있다. 새 Registry S에는 Registry ID/version이 없다.

| 관계 | 실제 필드/검증 | 담당 |
|---|---|---|
| Registry ID/version | 해당 Registry 저장 필드 없음; 생성/가짜 equality 없음 | 해당 없음 |
| raw schema | S의 입력 source-registry-1.0과 M.source_registry.schema_version의 고정 literal | 각 loader에서 검사; 후속 원본 결합 |
| artifact | M.source_registry.artifact == E.source_registry_ref (path+sha) | M2.68이 직접 검사 |
| 실제 Registry raw H | SHA256(S 원본 bytes) == E.source_registry_ref.sha256 | 새 loader P3 |
| domain fp | fingerprint_source_registry(S) == M.source_registry.fingerprint | 같은 호출의 검증 결과 결합/후속 Content Validator |
| 전체 문서 집합 | {(doc.ID, doc.d version)} == {(binding.ID, binding.d version) in M.source_versions} | 실제 M/S를 받는 기존 전체 validator |
| 선택 source 사용 집합 | Entry.bindings == Envelope.bindings ∪ Benefit.bindings, 각 ID/version/locator/claim 대응 | 후속 Content Validator/사용 gate |

새3입력 API에는 M이 없으므로 **M 직접 대조를 실행했다고 하지 않는다**. 대신 같은 trusted 호출 흐름에서 아래 두 loader를 **실제로** 같은 A/R로 호출한 경우의 연결은 증명할 수 있다.

- M2.68 성공: M.source_registry.artifact == E.source_registry_ref, M.source_registry.fingerprint == R.coverage fp == R.benefit fp.
- 새 Registry loader 성공: H(raw S) == E.source_registry_ref.sha256, F(S) == R.coverage fp == R.benefit fp.
- 그러므로 그 실제 두 결과의 F(S) == M.source_registry.fingerprint 및 동일 Entry artifact 선언 대응이 성립한다.

이 추이 관계는 동일 원본 A/R에 대한 실제 실행을 소유하는 외부 preparation/후속 검증 경계의 책임이다. 외부에서 임의로 만든 M, 전달된 성공 bool, hash 문자열만으로 실제 M2.68 실행을 인증하지 않는다. Manifest를 새 필수 인자로 넣거나 loader5종을 합치지 않는다.

source_versions 전체 set equality는 위 fp의 추이 관계만으로 증명되지 않는다. 전체 Envelope 집합/역사 호환 환경이 필요한 validate_dataset_manifest를 이번 loader에서 실행·복제하지 않는다. Content Validator의 명시 대조 단계도 제거하지 않는다.

## 18. Historical status와 supersedes

SourceStatus와 VerificationStatus는 서로 독립이다. 기존 모델이 허용하는 ACTIVE/SUPERSEDED/WITHDRAWN 및 DRAFT/VERIFIED/STALE을 원본대로 복원한다. 과거 비활성 문서/locator가 들어 있다는 사실만으로 Registry 전체를 거부하지 않는다. VERIFIED는 해당 verified_at이 필요하고 locator 확인일과 문서 확인일의 관계도 그대로 검사한다.

SourceRegistry.resolve는 문서/locator ACTIVE를 요구하지만 **복원 중 호출하지 않는다**. Registry에 다른 정책/역사 자료가 함께 있어도 전체 domain fp의 일부로 보존한다. 현재 날짜를 보고 status를 바꾸거나 모든 source를 ACTIVE/VERIFIED로 만드는 일은 없다.

supersedes는 exact pair의 중복/정확한 자기 pair를 거부하며, bundle에 정확한 대상 ID/version이 존재하는 간선만 순환 검사한다. 같은 ID의 이전 d version 또는 외부 과거 release pair는 보존할 수 있다. 외부 대상의 존재·전체 archive 순환·대체의 공식 의미·status 동기화를 모두 확인했다고 하지 않는다. 새 대상 생성/최신 version 선택/URL 조회는 없다.

## 19. SourceEvidence/locator의 네 수준과 기존 조회 API

| 수준 | 검사 내용 | 실제 능력/이번 책임 |
|---|---|---|
| 1 | locator/ref 문자열 문법·문서 내부 locator ID 유일성 | SourceEvidence constructor 및 parse_evidence_ref; 이번 Registry 본문 구조는 constructor 재사용 |
| 2 | 특정 외부 ref의 source/locator가 Registry에 등록됐는가 | has_source/get_source/has_evidence/resolve; 선택 ref 검증은 후속 |
| 3 | 실제 공식 원문에 그 절/쪽/위치가 있는가 | 원문 bytes/사람 확인 필요; 이번 미검증 |
| 4 | 그 위치가 조건·Benefit claim을 뒷받침하는가 | Snapshot/Envelope/claim/공식 의미 검토; 이번 미검증 |

get_source는 source status와 관계없이 metadata를 가져오며 has_evidence는 문법과 존재만 조회한다. resolve는 ACTIVE 문서/locator만 반환하고 없는 ID/locator를 구별하지만 VERIFIED/검증일/freshness/정책 적용 범위/공식 의미는 인증하지 않는다. validate_evidence_refs는 exact nonempty tuple/문법/중복을 확인한 뒤 ref 순서대로 resolve하며 부분 결과를 반환하지 않는다.

이번 loader는 Registry 안의 모든 선언 locator를 복원할 뿐 특정 claim refs를 resolve하지 않는다. 해당 정책이 applicable_policy_ids에 있는지, Entry/Envelope/Benefit source version과 일치하는지, 원문 위치와 meaning_summary가 맞는지는 후속 Content Validator/Source Gate·검토자가 실제 사용 ref를 대상으로 확인한다.

SourceDocument.content_sha256의 형식/저장값을 복원하고 domain fp에 포함하는 일과, 실제 공식 원문 bytes를 확보해 그 hash를 계산하는 일은 별개다. None이면 원문 hash를 만들어 채우지 않는다. 공식 URL 또는 meaning_summary 문자열의 존재만으로 원문 검증을 완료하지 않는다.

## 20. Freshness·사용일·Source Gate의 분리

이번 API에는 data_use_date/신청일/현재 시각/Manifest freshness 설정이 없다. 자동7일 기본값·현재 날짜 비교·DRAFT/STALE의 일괄 사용 차단·정책 자격 PASS/FAIL을 새로 만들지 않는다. 오래됐거나 미래인 verified_at이라도 기존 모델의 내부 날짜 관계를 만족하면 역사 값으로 보존한다.

특정 사용일의 freshness, 검토일/VERIFIED/ACTIVE/정책별 효력 범위·출처 변경 여부는 후속 gate다. Manifest.freshness_max_age_days는 Manifest가 명시하는 값이며 Registry에 복사하지 않는다. 과거 snapshot 복원과 현재 사용 적격성을 구분한다. 현재 접근 실패만으로 역사 status나 정책 조건 FAIL을 만들지 않는다.

## 21. 최종 pure Loader API

```python
load_historical_source_registry_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> SourceRegistry
```

세 인자 모두 exact type/필수 keyword-only/default 없음이다. 외부 Registry/Manifest/현재 source/expected_hash/expected_fingerprint/skip 옵션/verified bool/사용일 인자를 추가하지 않는다. 기존 SourceRegistry 하나를 반환하며 새 HistoricalSourceRegistry/Result/설정 모델은 없다.

정확한 A/R는 trusted 외부 preparation에서 공급한다. type/is/H 검사만으로 M2.57 실제 실행·검토자의 권한/공식성을 인증한다고 하지 않는다. I/O/환경/시각·전역 cache 없이 같은 입력에 같은 값/오류를 반환하며 입력 bytes/A/R/parsed root/반환 객체의 collection 순서를 바꾸지 않는다.

## 22. 성공 의미

성공은 “정확한 선택 Entry의 독립 raw H로 검증한 동일 HSR1 bytes에서 기존 구조상 유효한 SourceRegistry를 복원했고, 실제 전체 Registry domain fp가 R의 coverage/benefit 확인본과 일치한다”는 의미다.

Manifest와의 실제 관계는17절 외부 실행 결합 범위로 한정한다. 공식 원문 bytes, locator 의미/정책 적용·날짜별 사용, 모든 supersedes의 외부 존재, 전체 release/production ZIP, Historical FULL_POLICY, Review MATCHED, Policy VERIFIED, Acceptance USABLE, Cashflow 적용을 반환 성공으로 인증하지 않는다. 기존 객체에 그런 상태/flag 필드를 추가하지 않는다.

## 23. Validation precedence — P0~P9

| phase | 고정 순서 | 실패 범주 |
|---|---|---|
| P0 | raw_bytes → artifact → expected_acceptance exact 타입 | INPUT |
| P1 | ACCEPTED → root review ref equality → acceptance_ref Entry1개 → E.acceptance is R | REVIEW_BINDING |
| P2 | 선택 E.source_registry_ref exact ArtifactReference | EXPECTED_REF |
| P3 | SHA256(전체 raw_bytes) == E.source_registry_ref.sha256 | BYTES |
| P4 | BOM/strict UTF-8 → strict JSON/모든 깊이 duplicate·숫자 token → Unicode scalar | ENCODING/JSON/KEY/NUMBER/UNICODE |
| P5 | exact raw shape/primitive → canonical bytes equality | FIELDS/SCHEMA/TYPE/NONCANONICAL |
| P6 | 같은 parsed root로 parse_source_registry1회 → 모든 기존 constructor | MODEL |
| P7 | fingerprint_source_registry1회로 실제 전체 fp 계산 | FINGERPRINT |
| P8 | 실제 F 대 R.coverage fp → R.benefit fp 각각 비교 | FINGERPRINT_MISMATCH |
| P9 | 기존 exact immutable SourceRegistry 반환 | 추가 사용 gate 없음 |

P5는 root exact dict → 필수 key 누락(표 순서)/extra → schema exact str/literal → sources exact list → 문서 입력 순서로 각 record 필수 key/extra/필드 primitive를 검사한다. 문서는5절 선언 순서, Evidence는6절 선언 순서, supersedes pair는ID→version 순서다. 선택 필드는 존재할 때만 검사한다. null 허용 규칙은11절을 따른다. Enum/날짜/URL/ID/version/hash **값**은 P6 existing parser/constructor에 맡긴다. shape 전부 성공 후 raw canonical을 대조한다.

P4 token/duplicate 오류는 parser가 처음 보고한 오류를 유지하며 malformed/RecursionError는 JSON이다. P6는14절 실제 parser의 argument evaluation/constructor 순서를 유지한다. 여러 phase 오류가 겹치면 반드시 앞 phase가 우선이다. 예: H mismatch+BOM은 P3, missing+noncanonical은 P5 FIELDS, noncanonical+invalid date는 P5 NONCANONICAL, invalid source_type+domain fp mismatch는 P6 MODEL이다.

## 24. Stable 오류 prefix — 16개

기존 PolicyDataError를 사용하며 `PREFIX: field: 고정된 원인 범주` 형태다. 원본 bytes/URL 전체/개인정보/비밀 값을 메시지에 넣지 않는다. SourceValidationError/ManifestValidationError 등 알려진 PolicyDataError의 code/field는 해당 P6/P7 wrapper에 보존한다. 예상 밖 RuntimeError 등은 포괄적으로 삼키지 않는다.

| # | phase | 정확한 prefix | 의미 |
|---|---|---|---|
| 1 | P0 | INVALID_HISTORICAL_SOURCE_REGISTRY_LOADER_INPUT | exact 필수 입력 타입 |
| 2 | P1 | HISTORICAL_SOURCE_REGISTRY_REVIEW_BINDING_MISMATCH | status/root/선택 cardinality/원본 is |
| 3 | P2 | INVALID_HISTORICAL_SOURCE_REGISTRY_EXPECTED_REF | 선택 ref 타입/누락 |
| 4 | P3 | HISTORICAL_SOURCE_REGISTRY_BYTES_MISMATCH | raw SHA 불일치 |
| 5 | P4 | INVALID_HISTORICAL_SOURCE_REGISTRY_ENCODING | BOM/strict UTF-8 |
| 6 | P4 | INVALID_HISTORICAL_SOURCE_REGISTRY_JSON | malformed/decoder RecursionError |
| 7 | P4 | DUPLICATE_HISTORICAL_SOURCE_REGISTRY_JSON_KEY | 모든 깊이 duplicate |
| 8 | P4 | INVALID_HISTORICAL_SOURCE_REGISTRY_NUMBER | 실수/exponent/비표준/변환불가 정수 |
| 9 | P4 | INVALID_HISTORICAL_SOURCE_REGISTRY_UNICODE | 고립 surrogate |
| 10 | P5 | INVALID_HISTORICAL_SOURCE_REGISTRY_FIELDS | 필수 missing/허용 밖 extra |
| 11 | P5 | UNSUPPORTED_HISTORICAL_SOURCE_REGISTRY_SCHEMA | source-registry-1.0 이외 literal |
| 12 | P5 | INVALID_HISTORICAL_SOURCE_REGISTRY_TYPE | raw primitive/nested 타입 |
| 13 | P5 | NONCANONICAL_HISTORICAL_SOURCE_REGISTRY_BYTES | 원본과 canonical bytes 불일치 |
| 14 | P6 | INVALID_HISTORICAL_SOURCE_REGISTRY_MODEL | 기존 parser/constructor validation |
| 15 | P7 | INVALID_HISTORICAL_SOURCE_REGISTRY_FINGERPRINT | 기존 domain fp 계산의 알려진 오류 |
| 16 | P8 | HISTORICAL_SOURCE_REGISTRY_FINGERPRINT_MISMATCH | 실제 F와 R의 두 baseline 불일치 |

원본 불일치를 BENEFIT_METADATA_NOT_REVIEWED/UNUSABLE/STALE/빈 Registry로 바꾸지 않는다. 정상 모델에서 P2 방어 분기나 P7 계산 오류를 직접 유발하기 어려우면 constructor 경계/명시적 합성 fault injection을 구분한다. frozen 모델 훼손을 정상 fixture로 사용하지 않는다.

## 25. 합성 검증 시나리오 — 수동96개

H=선택 Entry의 독립 raw SHA, Fc/Fb=R의 두 Registry expected domain fp, Fm=역사 Manifest 선언 fp다. `H/F 고정`은 합성 저작 단계에서 별도로 준비·보존한 값이며 소비 loader가 actual을 기대값으로 채택한다는 뜻이 아니다. P4 이후 오류 fixture는 그 잘못된 raw 자체의 H를 저작 단계에서 고정해 P3를 통과시킨다. P8 모순은 actual Registry가 아닌 당시 R의 독립 fp를 유지해 만든다.

후속 열의 `단위`는 미래 pure loader 테스트, `모델`은 이미 생성 단계에서 거부되는 입력, `통합`은 Manifest/Content/Source Gate/원문/실행 계층의 책임이다. 이번에는 어느 행도 신규 실행 테스트로 계산하지 않는다.

### 25.1 정상·보존 — HS01~HS16

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 독립 기대값 | 후속 실행 |
|---|---|---|---|---|---|---|
| HS01 | 정확한 HSR1 raw/A/원본 R | exact Registry 반환 | P9 | loader | H/Fc/Fb | 단위 |
| HS02 | 여러 source ID, 각기 d0001/d0002 | 모두 원래 순서 복원 | P6/P9 | parser/loader | H/Fc/Fb | 단위 |
| HS03 | 여러 locator/정책 ID | tuple/의미/적용 ID 순서 보존 | P6/P9 | parser/loader | H/Fc/Fb | 단위 |
| HS04 | 문서7개/evidence2개 optional 생략 | 기존 None/빈 tuple 복원 | P6 | parser | H/Fc/Fb | 단위 |
| HS05 | optional None/빈 배열 명시 | 허용 조합 복원, HS04와 같은 domain 가능 | P6/P7 | parser/helper | 각 raw H, 같은 Fc/Fb | 단위 |
| HS06 | publication_date/verified_at 명시 null, DRAFT | null 보존, 날짜 생성 없음 | P6 | parser | H/Fc/Fb | 단위 |
| HS07 | 한국어 issuer/title/section/summary | 그대로 보존 | P6 | parser | H/Fc/Fb | 단위 |
| HS08 | 정상 VERIFIED 및 문서>=locator 확인일 | 상태/date 보존 | P6 | parser/모델 | H/Fc/Fb | 단위 |
| HS09 | SUPERSEDED 문서/locator 포함 | 역사 값 복원, resolve 안 함 | P6/P9 | loader | H/Fc/Fb | 단위 |
| HS10 | WITHDRAWN 문서/locator 포함 | 역사 값 복원, 사용 승인 없음 | P6/P9 | loader | H/Fc/Fb | 단위 |
| HS11 | ACTIVE이지만 verification STALE/DRAFT | 독립 Enum 상태 유지 | P6 | parser | H/Fc/Fb | 단위 |
| HS12 | 이전 release의 supersedes pair | 보존, 외부 대상 자동 조회 없음 | P6 | Registry 모델 | H/Fc/Fb | 단위 |
| HS13 | 선택 Entry가 첫/마지막이 아님 | acceptance_ref/is로 선택 | P1/P9 | loader | 선택 H/Fc/Fb | 단위 |
| HS14 | 같은 입력100회 | 값/오류 결정적, A/R/bytes 불변 | P9 | loader | H/Fc/Fb | 단위 |
| HS15 | source/locator/policy ID/supersedes 배열 순서 변경 | 각각 원본 순서, domain fp 동일 가능/H 다름 | P5/P7 | loader/helper | 각 H, 같은 Fc/Fb | 단위 |
| HS16 | 정상 page/table_position/URL/history/content SHA | 모든 저장값 복원 | P6/P7 | parser/helper | H/Fc/Fb | 단위 |

### 25.2 bytes/canonical — HS17~HS36

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 독립 기대값 | 후속 실행 |
|---|---|---|---|---|---|---|
| HS17 | raw1byte 변경, 기존 H 유지 | BYTES, parse 금지 | P3 | loader | 기존 H | 단위 |
| HS18 | 정상 raw, 다른 valid hex H | BYTES | P3 | loader | 다른 고정 H | 단위 |
| HS19 | invalid UTF-8 | ENCODING | P4 | loader | 해당 raw H | 단위 |
| HS20 | BOM 포함 | ENCODING | P4 | loader | 해당 raw H | 단위 |
| HS21 | malformed JSON | JSON | P4 | loader | 해당 raw H | 단위 |
| HS22 | root duplicate key | KEY | P4 | loader | 해당 raw H | 단위 |
| HS23 | Document/Evidence/supersedes duplicate key | KEY | P4 | loader | 해당 raw H | 단위 |
| HS24 | object key 순서 변경 | NONCANONICAL | P5 | loader | 해당 raw H | 단위 |
| HS25 | pretty/추가 공백 | NONCANONICAL | P5 | loader | 해당 raw H | 단위 |
| HS26 | trailing newline | NONCANONICAL | P5 | loader | 해당 raw H | 단위 |
| HS27 | 한국어 ASCII escape/불필요한 slash escape | NONCANONICAL | P5 | loader | 해당 raw H | 단위 |
| HS28 | 실제 NFC/NFD 문자열 각기 저작 | 둘 다 원형 보존, 값/F/H 차이 가능 | P4~P8 | loader/helper | 각 H/Fc/Fb | 단위 |
| HS29 | 고립 surrogate key/value | UNICODE | P4 | loader | 해당 raw H | 단위 |
| HS30 | NaN/Infinity | NUMBER | P4 | loader | 해당 raw H | 단위 |
| HS31 | page1.0/1e0 | NUMBER | P4 | loader | 해당 raw H | 단위 |
| HS32 | page -0 | NONCANONICAL 우선, 양수 검사는 나중 | P5 | loader | 해당 raw H | 단위 |
| HS33 | 변환 한도 넘는 정수 token | NUMBER | P4 | loader | 해당 raw H | 단위 |
| HS34 | decoder가 RecursionError 발생하는 raw | JSON, 깊이는 실제 decoder 기준으로 준비 | P4 | loader/decoder | 해당 raw H | 단위 |
| HS35 | root missing schema 또는 sources | FIELDS | P5 | loader | 해당 raw H | 단위 |
| HS36 | root extra historical wrapper/Registry ID/version | FIELDS | P5 | loader | 해당 raw H | 단위 |

### 25.3 shape/domain — HS37~HS64

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 독립 기대값 | 후속 실행 |
|---|---|---|---|---|---|---|
| HS37 | source-registry-2.0/오타 | SCHEMA; Registry version 추정 없음 | P5 | loader | 해당 raw H | 단위 |
| HS38 | root/source/locator/pair가 null/array/string | TYPE(허용 nullable 자리 제외) | P5 | loader | 해당 raw H | 단위 |
| HS39 | Document 필수 key 누락 | FIELDS | P5 | loader | 해당 raw H | 단위 |
| HS40 | Evidence 필수 key 누락 | FIELDS | P5 | loader | 해당 raw H | 단위 |
| HS41 | Document/Evidence/pair extra key | FIELDS | P5 | loader | 해당 raw H | 단위 |
| HS42 | publication_date 또는 verified_at key 생략 | FIELDS, null 자동 추가 없음 | P5 | loader | 해당 raw H | 단위 |
| HS43 | previous_urls/supersedes 명시 null | TYPE, 빈 배열 보정 금지 | P5 | loader | 해당 raw H | 단위 |
| HS44 | page true/false/string | TYPE | P5 | loader | 해당 raw H | 단위 |
| HS45 | page0/음수 | MODEL | P6 | 기존 모델 | 해당 raw H | 단위 |
| HS46 | sources 빈 배열 | MODEL | P6 | Registry 모델 | 해당 raw H | 단위 |
| HS47 | locators/applicable_policy_ids 빈 배열 | MODEL | P6 | 기존 모델 | 해당 raw H | 단위 |
| HS48 | 잘못된 source/policy ID 또는 locator 문법 | MODEL | P6 | 기존 모델 | 해당 raw H | 단위 |
| HS49 | d0000/d1/비정규 document version | MODEL | P6 | 기존 모델 | 해당 raw H | 단위 |
| HS50 | 동일 Source ID 두 번, version 같음/다름 | MODEL, 자동 제거 없음 | P6 | Registry 모델 | 해당 raw H | 단위 |
| HS51 | 문서 안 duplicate locator ID | MODEL | P6 | Document 모델 | 해당 raw H | 단위 |
| HS52 | duplicate applicable policy ID/previous URL | MODEL | P6 | 기존 모델 | 해당 raw H | 단위 |
| HS53 | 잘못된 날짜/시간 포함 문자열/비윤년2월29일 | MODEL의 기존 date code | P6 | 기존 parser | 해당 raw H | 단위 |
| HS54 | effective_from > effective_to | MODEL | P6 | Document 모델 | 해당 raw H | 단위 |
| HS55 | VERIFIED인데 verified_at null | MODEL | P6 | 기존 모델 | 해당 raw H | 단위 |
| HS56 | locator 확인일이 문서보다 늦거나 문서일 null | MODEL | P6 | Document 모델 | 해당 raw H | 단위 |
| HS57 | unsupported source_type/status/verification Enum | MODEL, alias 보정 금지 | P6 | 기존 parser | 해당 raw H | 단위 |
| HS58 | HTTP/credentials/잘못된 port URL | MODEL | P6 | 기존 모델 | 해당 raw H | 단위 |
| HS59 | malformed content_sha256 | MODEL, 실제 원문 hash 계산 안 함 | P6 | Document 모델 | 해당 raw H | 단위 |
| HS60 | supersedes pair의 missing/extra/잘못된 primitive | FIELDS/TYPE | P5 | loader | 해당 raw H | 단위 |
| HS61 | supersedes 정확한 자기 pair/duplicate pair | MODEL | P6 | Document 모델 | 해당 raw H | 단위 |
| HS62 | bundle 안 exact ID/version supersedes cycle | MODEL | P6 | Registry 모델 | 해당 raw H | 단위 |
| HS63 | parser가 알려진 PolicyDataError 보고 | MODEL/code·field 보존, 부분 Registry 없음 | P6 | loader/parser | 해당 raw H | 단위 |
| HS64 | 기존 fp helper가 PolicyDataError 보고(합성 fault injection) | FINGERPRINT, 새 hash 규약으로 우회 금지 | P7 | loader/helper | H/Fc/Fb | 단위 |

### 25.4 binding/precedence — HS65~HS80

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 독립 기대값 | 후속 실행 |
|---|---|---|---|---|---|---|
| HS65 | bytearray/subclass/잘못된 A/R 타입 | INPUT | P0 | loader | 정상 A/R 또는 타입 오류 | 단위 |
| HS66 | 다른 revision/root ref/Entry 없음 | REVIEW_BINDING | P1 | loader | 원본 A/R | 단위 |
| HS67 | 값이 같은 별도 R 객체 | REVIEW_BINDING, is 필수 | P1 | loader | 원본 R | 단위 |
| HS68 | REVOKED Entry | REVIEW_BINDING | P1 | loader | 정상 철회 A/R | 단위 |
| HS69 | ACCEPTED ref 누락/잘못된 ref/Entry 중복 생성 | 기존 constructor 거부; P2는 방어 계약 | 모델/P2 | Review 모델 | 기존 구조 계약 | 모델 |
| HS70 | 다른 Entry H만 raw와 일치 | 선택 H로 BYTES, fallback 금지 | P3 | loader | 선택 H/다른 H | 단위 |
| HS71 | actual domain F가 R 확인본과 다름 | FINGERPRINT_MISMATCH | P8 | loader | H와 기존 Fc/Fb | 단위 |
| HS72 | R의 두 fp 자체가 서로 다름 | 기존 Acceptance constructor 거부 | 모델 | Acceptance 모델 | same-release invariant | 모델 |
| HS73 | raw H를 R의 domain expected로 잘못 사용 | 실제 F와 달라 P8 거부, hash 영역 혼용 금지 | P8 | loader | H, 잘못된 Fc/Fb | 단위 |
| HS74 | URL/title/날짜/status/d version metadata만 변경 | 기존 actual F 변화, old Fc/Fb면 거부 | P8 | helper/loader | 새 raw H, old Fc/Fb | 단위 |
| HS75 | previous_urls 순서만 반대로 저작 | 기존 domain F가 달라질 수 있음, old fp면 거부 | P7/P8 | helper/loader | 각 H, old Fc/Fb | 단위 |
| HS76 | H mismatch + malformed/BOM | BYTES 우선, parse0회 | P3 | loader | 기존 H | 단위 |
| HS77 | missing field + noncanonical | FIELDS 우선 | P5 | loader | 해당 raw H | 단위 |
| HS78 | noncanonical + invalid date | NONCANONICAL 우선 | P5 | loader | 해당 raw H | 단위 |
| HS79 | invalid source_type + invalid source ID + fp mismatch | P6 MODEL의 기존 Enum 변환 오류 우선 | P6 | 기존 parser | 해당 raw H, old fp | 단위 |
| HS80 | 정상 parser 반환 후 실제 F 계산/두 R 비교 순서 감시 | parser1회→helper1회→coverage→benefit 순서 유지 | P6~P8 | loader | H/Fc/Fb | 단위 |

### 25.5 신뢰 경계 — HS81~HS96

| ID | 입력 | 기대 결과 | phase | 담당 계층 | 독립 기대값 | 후속 실행 |
|---|---|---|---|---|---|---|
| HS81 | SourceBinding ID/version이 Registry와 불일치 | narrow 성공 가능, 후속 사용 선언 대응에서 거부 | 후속 | Content Validator | Entry/Envelope/Benefit bindings·S | 통합 |
| HS82 | M Registry fp가 actual S와 다름 | Registry 단독은 M 못 봄, 후속 모순 거부 | 후속 | Content/Manifest 결합 | 실제 M의 Fm | 통합 |
| HS83 | M Registry artifact path/SHA가 E와 다름 | M2.68 거부, 새 loader의 성공으로 대체 금지 | M2.68 P8 | Manifest loader | M/E exact artifact | 통합 |
| HS84 | M.source_versions 집합이 Registry와 다름 | 전체 validator에서 거부, 부분 subset로 대체 금지 | 후속 | release validator | 실제 M/S 전체집합 | 통합 |
| HS85 | 같은 A/R로 M2.68과 새 loader를 실제 실행 | F(S)=R fp=M fp 추이 성립, source set/전체 release는 별도 | 후속 결합 | 외부 preparation | 같은 A/R, 각 원본 H | 통합 |
| HS86 | 외부에서 만든 M/성공 bool만 공급 | 실제 두 loader 수행 증명으로 신뢰 금지 | 후속 경계 | 외부 orchestration | 검증 원본 실행 흐름 | 통합 |
| HS87 | 문서·locator가 등록됐지만 공식 원문 미확보 | 복원 가능, 원문 bytes 검증 미완료 | P9 이후 | 원문 preparation | Review 원문 artifact H | 통합 |
| HS88 | locator 존재하지만 claim 의미 불충족 | 등록 존재와 의미 분리, 후속 검토 거부 | 후속 | Content/사람 검토 | 원문/claim/당시 Snapshot | 통합 |
| HS89 | source ACTIVE지만 대상 policy가 applicable IDs에 없음 | narrow 복원 가능, 실제 사용 ref 검증에서 거부 | 후속 | Content/Source Gate | 대상 policy/정확한 ref | 통합 |
| HS90 | 오래되거나 미래 verified_at, 내부 날짜 관계 유효 | 역사 원형 보존, freshness 판단 안 함 | P6/P9 | loader/후속 Gate | H/Fc/Fb, 사용일은 후속 | 단위/통합 |
| HS91 | 외부 과거 supersedes 대상 미확보 | pair 보존, 존재/공식 대체 검증 완료 아님 | P6 이후 | 과거 archive/review | 정확한 과거 ID/version 원본 | 단위/통합 |
| HS92 | content_sha256가 있지만 공식 원문 bytes 없음 | 선언 보존, 원문 hash 실제 대조 미완료 | P6/P9 이후 | 원문 preparation | 실제 원문 H | 단위/통합 |
| HS93 | 순수 호출 중 파일/network/env/시계/ZIP/다른 loader 감시 | I/O·사용 gate0회, 기존 parser/helper만 각1회 | P0~P9 | loader | H/Fc/Fb | 단위 |
| HS94 | parser/helper가 예상 밖 RuntimeError 보고 | 프로그램 오류 전파, UNUSABLE/빈값으로 낮추지 않음 | P6/P7 | loader | 정상 H/Fc/Fb+fault injection | 단위 |
| HS95 | 정상 Registry 복원 후 FULL/MATCHED/VERIFIED/USABLE 요청 | 그런 결과/flag 반환 없음, 상태 선언과 인증 분리 | P9 이후 | 후속 evaluator/사용 gate | 각 실제 원본/검토·실행 | 단위/통합 |
| HS96 | Registry 정상이나 전체 release/production ZIP 미검증 | 좁은 성공만 기록, 현금 반영0원 원칙 유지 | P9 이후 | 전체 release/실행/Bridge | 전체 원본/ZIP H/사용 전제 | 통합 |

위96행은 미래 parameterization 실행 개수와 같지 않다. raw 손상으로 P3만 실패한 것을 P4/P5 검증 실적으로 계산하지 않는다. scope 밖/기존 모델상 불가능한 사례는 표의 계층에서 검증하고 frozen 값 변조나 외부 FULL/usable bool을 만들지 않는다.

## 26. 전체 release/원문/사용 승인과의 분리

후속 전체 경로는 실제 Manifest/모든 Envelope/Registry 원본을 확보하고 각 raw H와 domain fp를 구별해 비교한다. validate_dataset_manifest의 역사 환경 ENGINE_VERSION 호환성/전체 policy·source set/Registry fp/Envelope source·fp·전역 rule ID 검증을 유지한다. 엔진 비교만 삭제한 복제품이나 선택 policy 하나의 검증으로 전체 release를 대체하지 않는다.

공식 원문 raw H/content_sha256, Entry source 합집합·locator의 등록/정책 적용·상태/날짜/claim 의미, 사용일 freshness, 실제 source ZIP bytes/worker 실행 대응은 후속이다. 이 Registry codec의 성공으로 Content Validator/Source Gate/Acceptance evaluator/Benefit Bridge가 완료됐다고 하지 않는다.

## 27. 동결 영향·Assumptions·미해결 사항

이번 변경은 새 문서1개뿐이다. SourceRegistry/Document/Evidence/Enum/parser/fingerprint/참조 모델, DatasetManifest/기존 validator/Historical loader5종, Review Artifact 모델·strict loader, Acceptance Record/Context/Evaluation, BenefitSnapshot16/definition fp/BV01~BV16, frozen Coverage/schema/GV01~GV15, ZIP bootstrap/Cashflow, 기존 tests/fixture/기대값/기존 docs/실제 release6개를 수정하지 않는다.

**Assumption A1:** trusted 외부 preparation이 독립 기대 H/F를 이미 고정한 A와 원본 R를 같은 호출에 공급한다. type/is/H로 사람 검토·공식성·실제 M2.57 실행을 인증하지 않는다.

**Assumption A2:** HSR1로 소비할 원본은 그 canonical bytes로 별도 보존돼 있다. 기존 pretty release가 이미 HSR1이라고 가정하지 않는다. 기존 원본/ref를 수정하지 않는다.

**Assumption A3:** Manifest와의 연결은17절 같은 원본 A/R를 사용하는 실제 두 loader 실행 흐름에서 확인한다. 임의 객체나 완료 flag를 증거로 삼지 않는다.

기존 optional 생략 표시/원문 파일 bytes/다른 release의 supersedes 대상/공식 URL 진위·의미/현재 사용요건은 Registry 모델만으로 복원·인증할 수 없다. 불가능한 정보를 새 필드로 채우지 않는다. 원본 bytes는 H와 외부 archive로 보존한다.

좁은 loader의 raw schema/parser/fp/binding/오류/API에 미결정 사항은 없다. 공식 원문 preparation, 실제 locator/claim 의미, 전체 release·historical 실행 환경/ZIP, Content Validator/Source Gate/evaluator/Bridge는 미구현 의존사항이다. 이 별도 작업 때문에 본 설계를 차단하지 않는다. 현재 정책 DRAFT/CONDITION_SLICE·실제 정책 혜택 Cashflow 반영0원과 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 28. 최종 판단

**READY_TO_IMPLEMENT_HISTORICAL_SOURCE_REGISTRY_LOADER**

독립 raw H/같은 bytes/HSR1/기존 pure parser/불변 모델/기존 전체 Registry domain fp/직접 Acceptance binding을 확정했다. Manifest 직접 입력 없는 범위와 같은 호출 추이 관계/전체 source set 별도 검증도 명시했다. 기존 모델 의미나 지문 정의를 우회·변경할 필요가 없다.

## 29. 다음 최소 작업 하나

**M2.70 — Historical SourceRegistry Strict Bytes Loader 구현**. 승인 후21절3입력 pure API 한 개에서 기존 parse_source_registry1회/fingerprint_source_registry1회를 연결하고 HSR1/P0~P9/16오류/합성 정상·오류·순수성 테스트를 구현한다. 기존9,964개 회귀·기대값·실제 releases를 보존한다. Manifest/Content Validator/Source Gate/원문 다운로드/전체 release/ZIP 실행을 이 구현에 넣지 않는다.

## 30. 작업 검증·보존 기록

- 사전 전체 pytest 최초 실행: **9,964 passed in 72.92s (0:01:12)**.
- 사후 전체 pytest: **9964 passed in 53.97s; 최초 실행 통과/skipped0/failed0/timeout0**.
- 신규 실행 테스트: **0개**. HS01~HS96은 수동 설계이며 통과 실적으로 계산하지 않는다.
- 보호 기준선: 기존194개 파일(backend/tests/data/docs/tools 및 루트4개), 실제 release6개 SHA256·경로·크기·수정시각을 확보했다.
- 최종 보존 대조: **기존194개 파일 SHA256 모두 동일, 삭제0개. 새 문서1개만 추가하여 보호 집합195개. 코드/tests/fixture/기대값/기존 문서·동결 계약 변경0개. 실제 release6개 SHA256·경로·크기·수정시각 모두 동일**.
- 최초 실패/timeout/재실행: 사전·사후 전체 모두 최초 실행 통과, 실패0/timeout0/재실행0/skipped0. 과거 M2.68 신규 테스트 실패 이력은 기존 문서대로 보존한다.

### 실제 release6개 SHA256

사전=사후 SHA256·크기·수정시각 대조 결과다. 실제 release에는 쓰지 않았다.

| release 상대 경로 | SHA256(동일) | bytes(동일) | LastWriteTimeUtc(동일) |
|---|---|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f | 1563 | 2026-10-20T08:37:35.968002700Z |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b | 3803 | 2026-10-20T08:34:42.447400500Z |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 | 5620 | 2026-10-20T12:23:31.465653800Z |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 | 5944 | 2026-10-20T12:21:00.276460800Z |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 | 1981 | 2026-10-20T08:34:43.217142700Z |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 | 2922 | 2026-10-20T12:21:00.277470600Z |

## 31. M2.70 — IMPLEMENTED: Historical SourceRegistry Strict Bytes Loader

### 31.1 실제 API·파일·구현 범위

신규 backend/policy_engine/policy_data/historical_source_registry_loader.py의 공개 함수는 `load_historical_source_registry_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> SourceRegistry` 한 개다. 입력3개 모두 exact type/필수 keyword-only/default 없음이다. 외부 Registry/Manifest/expected_hash/skip 옵션으로 복원을 우회하는 경로는 없다. policy_data/__init__.py에 import/export를 각각1회 추가했다.

신규 tests/test_historical_source_registry_loader.py에서 합성 실행 테스트741개를 추가했다. 기존 파일 수정은 public export와 이 문서/ARCHITECTURE.md3개, 신규 파일2개, 삭제0개다. 기존 Source 모델/parser/fingerprint/validator/Historical loader5종·tests/fixture/기대값은 변경하지 않는다. 새 domain model/History model/generic artifact framework는 없다.

### 31.2 실행 순서와 원본 보존

P0 exact 입력 → P1 ACCEPTED/root review ref/acceptance_ref Entry1개/`entry.acceptance is R` → P2 선택 source_registry_ref → P3 전체 raw SHA → P4 strict UTF-8/JSON → P5 HSR1 shape/canonical → P6 기존 parse_source_registry1회 → P7 기존 fingerprint_source_registry1회 → P8 Coverage/Benefit Registry fp 각각 비교 → P9 parser가 만든 동일 SourceRegistry 반환을 구현했다.24절16개 prefix와23절 순서를 그대로 유지한다.

SHA mismatch 이후 JSON decode/두 helper 호출은0회다. parser 실패 뒤 fp helper도0회다. 정상 경로에서 같은 JSON root를 parser에 전달하며, parser가 만든 exact 객체를 helper와 반환값에 그대로 사용한다. 별도 SourceDocument/Evidence parser나 Enum/date/URL/ID/version 의미 검증을 복제하지 않았다. private schema helper는 raw key/primitive만 확인한다.

HSR1은 기존 source-registry-1.0 직접 표현이다. optional 생략을 허용하고 원래 parsed root로 canonical 대조한다. 생략을 null/빈 배열로 채워 원본 bytes를 변경하지 않는다. 기존 parser가 생성하는 default None/tuple은 그 이후의 domain 복원이다. 반환 객체는 SourceRegistry1/SourceDocument18/SourceEvidence9 저장 필드와 tuple 순서를 보존한다.

기존 fp helper의 전체 metadata 포함 범위와 sources/locators/supersedes/applicable_policy_ids 정렬을 그대로 사용한다. previous_urls는 정렬하지 않는다. raw SHA와 domain fp는 별도 계산이며 실제 fp는 R.coverage_source_registry_fingerprint → R.benefit_source_registry_fingerprint 순서로 각각 읽어 비교한다.

원래 R의 한쪽 fp만 다르게 만드는 상태는 기존 same-release constructor가 거부한다. 그 부정 사례는 모델 경계에서 검사했다. 정상 public 경로의 두 비교는 원래 attribute 값을 그대로 반환하는 읽기 spy로 순서를 확인했으며 frozen R 값을 변조하지 않았다. ref 누락/잘못된 SHA 형식/중복 Entry도 기존 constructor에서 먼저 거부하는 경계를 분리했다.

### 31.3 Historical 상태와 신뢰 경계

ACTIVE/SUPERSEDED/WITHDRAWN과 DRAFT/VERIFIED/STALE의 정상 조합을 복원한다. 현재시각·로컬 환경·자동7일 freshness·현재 Registry를 사용하지 않는다. 오래된2000년 및 미래2099년 확인일도 기존 내부 날짜 관계를 만족하면 보존한다. SourceRegistry.resolve/has_evidence 등 사용 대상 조회를 loader에서 실행하지 않는다.

**IMPLEMENTED:** Historical SourceRegistry strict bytes, 공개 pure parser 재사용, 실제 Registry domain fingerprint 대조, Acceptance Registry binding, 불변성/결정성/오류 순서/합성 검증.

**NOT IMPLEMENTED:** 공식 Source 원문 bytes/내용 검증, locator 위치·claim 의미, Source Gate/날짜별 사용 승인, Historical Manifest 전체 source 집합 대조, 전체 release validation, production ZIP 실행, Review Content Validator, Acceptance evaluator, same-call adapter, Benefit Bridge/Cashflow 연결, FastAPI/React 연결.

Registry 단독 성공으로17절 Manifest 직접 대조/전체집합 검증을 완료했다고 하지 않는다. 실제 같은 A/R를 사용하는 두 loader의 추이 관계는 후속 연결 경계가 실제 실행을 소유해야 한다. FULL/MATCHED/VERIFIED/USABLE/현금 반영 flag를 새로 반환하지 않는다.

### 31.4 HS01~HS96 실행 대응

96개는 M2.69 수동 시나리오 수이며 신규 parameterized 실행741개와 별도다. 다음의 실행은 pure loader 또는 기존 모델 경계이며 후속 통합 책임의 성공을 포함하지 않는다.

| 수동 ID | 대응 실행 테스트/내용 | 검증 범위 |
|---|---|---|
| HS01~HS03, HS07~HS08, HS16 | test_fixed_raw_and_domain_vectors_and_full_restoration | 실행:2문서/3locator/서로 다른 d version/18·9필드/한국어/정확한 타입 |
| HS04~HS06 | optional omission/explicit defaults/nullable dates/개별 optional 테스트 | 실행: 합법적 생략·null·빈 tuple/원본 raw 구분 |
| HS09~HS11 | lifecycle3x3 및 verification3x3, source_type3개 | 실행: 수명/검토 Enum·역사 값 보존 |
| HS12 | 정상 fixture의 외부 supersedes pair와 pure 호출 감시 | 실행: pair 보존, 외부 원본 존재/공식 대체 의미는 미검증 |
| HS13 | test_exact_revision_selection_and_no_other_entry_hash_fallback | 실행: 첫/마지막 위치와 무관한 revision 선택 |
| HS14 | test_100_repetitions_immutability_and_input_isolation | 실행100회, nested frozen·입력 불변성 |
| HS15 | test_array_order_is_preserved_while_existing_domain_order_rules_apply | 실행: raw/반환 배열 순서와 domain 정렬 분리 |
| HS17~HS18 | SHA 차단/byte change/wrong hash domain | 실행: parse 및 두 helper0회, 독립 H |
| HS19~HS21 | encoding/malformed JSON | 실행: BOM/strict UTF-8/잘못된 JSON |
| HS22~HS23 | test_duplicate_keys_at_every_object_depth | 실행: root/Document/Evidence/supersedes |
| HS24~HS27 | test_noncanonical_representations | 실행: 공백/key 순서/newline/ASCII·slash escape |
| HS28~HS29 | Unicode normalization 및 invalid scalar 테스트 | 실행: NFC/NFD 보존, 고립 surrogate 거부 |
| HS30~HS34 | 숫자 token/negative_zero/decoder recursion | 실행: NUMBER와 canonical/JSON phase 분리 |
| HS35~HS37 | root missing/extra 및 schema version | 실행: wrapper/가짜 Registry ID/version 거부 |
| HS38~HS44 | object/string/array/required/extra/page primitive parameterization | 실행: nullable와 missing/optional 구분, bool-as-int 거부 |
| HS45~HS49 | MODEL_BAD_VALUES의 page/nonempty/ID/locator/d version | 실행: 기존 parser/constructor 유지, parser 실패 후 fp0회 |
| HS50~HS52 | duplicate source/version/locator/policy ID/URL | 실행: dedupe 없음 |
| HS53~HS59 | 날짜/효력일/검토일/Enum/URL/content SHA 값 오류 | 실행: P6 MODEL, 기존 code/field 보존 |
| HS60~HS62 | supersedes shape/자기 pair/duplicate/exact in-bundle cycle | 실행: 기존 pair/Registry 제약 |
| HS63~HS64 | helper 오류 합성 fault injection | 실행: P6/P7 알려진 데이터 오류 wrapper, 정상 입력의 원본 변조 아님 |
| HS65~HS68 | exact/subclass/원본 is/root/revision/REVOKED | 실행: P0/P1 우선 |
| HS69 | ref/ArtifactReference SHA/중복 Entry constructor 경계 | 실행: 생성 단계 거부. P2 방어 분기를 frozen 훼손으로 강제하지 않음 |
| HS70 | 다른 Entry digest fallback 부정 사례 | 실행: 다른 H가 일치해도 선택 H를 사용 |
| HS71~HS73 | real domain mismatch/wrong hash domain/same-release model | 실행: 두 leg 읽기 순서 확인. 한쪽만 다른 R/잘못된 fp는 기존 모델에서 거부 |
| HS74~HS75 | metadata/evidence 변경 및 previous_urls 순서 | 실행: 새 raw H로 P3 통과 후 실제 domain 차이를 P8에서 검출 |
| HS76~HS79 | hash/schema/canonical/parser precedence | 실행: 이전 phase 및 기존 parser의 Enum/날짜 평가 순서 유지 |
| HS80 | test_parser_and_fp_called_once_same_root_same_result_then_both_bindings | 실행: parser1→fp1→coverage→benefit, 같은 root/반환 객체 |
| HS81~HS86 | source binding/Manifest/ref/전체 set/실제 두 loader 실행 결합 | **후속 연결/Content/release 검증 책임, 이번 통과 실적 아님** |
| HS87~HS89 | 원문 확보/locator 의미/대상 policy 사용 | **후속 원문·Content·Source Gate 책임, 이번 미검증** |
| HS90 | test_hs90_old_and_future_verification_dates_do_not_trigger_usage_gate | 실행:2000/2099년 날짜 보존, 사용 적격성 미평가 |
| HS91~HS92 | 정상 supersedes/content_sha256 복원·pure 호출 감시 | 선언 보존만 실행, 과거 대상/공식 원문 bytes 실제 대조 미실시 |
| HS93~HS94 | pure guard/AST imports/cache/예상 밖 RuntimeError | 실행: 외부 호출 금지 및 프로그램 오류 전파 |
| HS95~HS96 | 반환 타입/상태 flag 부재/pure guard | 좁은 반환 의미만 실행. FULL/USABLE/전체 release/ZIP/현금 승인은 미검증 |

독립 정상 raw golden은2509 bytes, SHA256=`97978d60ef2d3f48bf3e675f3f93eb3c58a5f4d2673fa2c0a102dfd28586b7d2`다. 기존 참조 parser/helper로 fixture 저작 시 고정한 domain literal은 `005f78470af9289e31b0b6bd46bb2bcc34861944c0670e276e8d4c5ecb37fc35`, minimal optional 생략 확인본은 `bf0143340dec9898a7c99a1baeadef5d21d01ac5fb3c8fb4cca729e8093f5f7d`다. 소비 함수가 actual을 expected로 채택하는 경로는 없다. variant의 expected fp도 소비 호출/spy 설치 전 별도 fixture 발급 단계에서 준비한다.

### 31.5 실제 검증 이력

- 사전 actual 전체 최초 실행: **9,964 passed in 83.16s (0:01:23)**.
- 임시 작업 사본 신규 최초 실행: **739 passed in 3.03s**.
- HS90의 오래된/미래 확인일2개를 추가한 최종 신규: **741 passed in 3.30s**. 기존 테스트·fixture·기대값은 변경하지 않았다.
- 최초 실패/timeout: 현재까지0회. 신규 첫 실행과 범위 보완 후 실행을 구분했으며 수동96개를 실행 수에 더하지 않았다.
- 사후 actual 전체: **10705 passed in 48.52s; 사후 전체 최초 실행 통과/skipped0/failed0/timeout0/재실행0**.
- 최종 보존 대조: **기존195개 중192개 SHA256 동일, 수정3개는 export와 관련 문서2개뿐. 신규 loader/테스트2개를 추가해 최종197개, 삭제0개. 기존9,964개 tests/fixture/기대값·GV/BV·Coverage freeze·Source 모델/parser/fingerprint·기존 Historical loader5종·Review Artifact Strict Loader·Acceptance/Benefit/bootstrap/Cashflow를 보존. 실제 release6개 SHA256·경로·크기·수정시각 모두 동일**.


M2.70 사전=사후 실제 release SHA256(크기·수정시각도 동일):

| release 상대 경로 | SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

### 31.6 연결 검증으로의 전환 평가와 다음 최소 작업

Benefit/Coverage/Policy/ReviewContext/Manifest/Registry의 strict 복원6종이 모두 구현됐으므로 **새 History 모델 없이 합성 원본의 실제 연결 검증으로 전환할 수 있다**. 기존 Content Validator 계약을 재사용해 같은 A/R에 대한 실제 loader 호출·artifact 참조·dataset/Registry fp·Inventory/Tree/Benefit binding 등의 관계를 먼저 확인할 수 있다.

다음 가장 작은 작업은 **M2.71 — 6종 Historical Artifact 합성 연결 검증** 한 개다. 일관된 합성 raw6종과 독립 기대값/정확한 Review Artifact·원본 R를 준비해 기존6 loader를 실제 호출하고, 성공 조합과 원본 혼합·참조·지문 모순을 통합 테스트로 대조한다. 이 검증을 runtime same-call adapter/Review Content Validator/Source Gate 구현이나 공식 원문·production ZIP·FULL/USABLE 증명으로 확대하지 않는다. 기존 계약에서 연결에 필요한 미해결 사항이 드러나면 그 지점만 보고하고 추가 generic infrastructure를 자동 생성하지 않는다.

최종 판단은 **HISTORICAL_SOURCE_REGISTRY_LOADER_COMPLETE**다. 전체 release/실제 정책 자격·혜택 사용 승인은 미완료다. Generic Coverage freeze/GV/BV/기존 loader5종·Review Artifact Strict Loader/Acceptance/Benefit/bootstrap/Cashflow/실제 release6개를 보존하며 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.
