# M2.56 — Strict Acceptance Review Artifact Loader Contract

## 1. 목적·범위·현재 상태

Loader의 역할은 **외부에서 명시한 Acceptance 원본들의 기대 ref와 실제 입력 bytes가 일치하고, 정해진 raw JSON을 기존 불변 모델로 복원할 수 있는지** 확인하는 것이다. bytes integrity·strict parsing·로컬 구조 복원·외부 record 대응까지만 담당한다. 공식 내용 검토·검토자의 진실성/권한·Coverage FULL·Policy VERIFIED·현재 Acceptance USABLE·지급·Bridge/Cashflow는 판단하지 않는다.

이번 산출물은 이 문서1개다. loader/parser/파일 읽기·새 validator·실제 Artifact bytes·발급 기록·정책 금액을 구현/생성하지 않는다. 이하 API·phase·helper·오류는 **후속 구현 계약**이며 현재 callable이 아니다.

현재 구현: Review Artifact Enum+4개 value 모델, 기존 Acceptance21/Context4/Result9·BenefitSnapshot16/지문, frozen Coverage, 합성 ZIP verify-only. 미구현: Review Artifact loader/content validator·전체 Source Gate·Acceptance evaluator·same-call adapter·Benefit Bridge. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED다.

## 2. Source of Truth·실제 코드 확인

| 확인 문서 | 적용 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md 4~15·20~23·30절 | ref·raw20key·동일 bytes·4개 구현 모델·원본 객체 보존·여러 entry·구조와 내용 구분 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md | 기존21필드·same-release·ACCEPTED/REVOKED·날짜/버전·opaque ref |
| BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md | 한 target Context·명시 선택·철회 edge·여러 revision의 artifact 공유 |
| BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md | 결과9필드·파생 status·12 reason |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | A 외부 준비/C 동일 호출/B 순수8입력·역사 원본과 current 비교 분리 |
| BENEFIT_SNAPSHOT_SPEC.md / COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md | Snapshot16/정의 지문·초기 FIXED·accepted terms 원본·provenance·개인/월 경계 |
| RELEASE_ARTIFACT_EXECUTION_BINDING_SPEC.md | 실행 ZIP의 별도 identity/실행 검증·합성 범위 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | frozen source/schema/GV·로컬 해시와 실제 검토 진실성 구분 |
| DATA_MODEL.md / ARCHITECTURE.md | M2.55 value 구현·public5개·미구현 계층 |

실제 AcceptanceReviewArtifact/AcceptanceReviewEntry/ClaimEvidenceMapping/ReviewSourceOriginal/BenefitReviewClaim, PolicyBenefitAcceptance/BenefitAcceptanceStatus, ArtifactReference/SourceBinding/ApplicabilityScope/BenefitSnapshot/PolicyDataError를 확인했다. 기존 source/envelope JSON loader·PolicySet loader·Coverage/Benefit/Manifest 지문 helper·bootstrap의 strict JSON도 확인했다.

| 기존 기능 | 차이/재사용 판단 |
|---|---|
| sources.loader의 _object/_array | exact dict/list와 missing/extra 검사는 참고 가능하나 SOURCE 오류와 optional/default 의미가 있음. 기존 의미를 수정하지 않고 새 loader의 최소 private helper로 경계를 표현 |
| _date/_enum | ASCII ISO 날짜·정확한 Enum 해석 원칙은 같음. 기존 _date는 None도 허용하므로 required 날짜에 그대로 적용하지 않음 |
| _unique_keys/_invalid_constant | duplicate/NaN 거부 원칙 참고. 새 loader 고정 오류가 필요하므로 기존 SOURCE prefix를 바꾸지 않음 |
| load_source_registry/load_policy_envelope | 경로 I/O와 parsing 결합, 기대 raw SHA·canonical 비교·Acceptance 대응 없음. 이 함수들을 새 bytes API의 대체물로 사용하지 않음 |
| 기존 fingerprint JSON 설정 | sort_keys/separators/ensure_ascii/allow_nan 설정만 맞춤. payload/domain/schema·지문 함수는 재사용하지 않음 |
| bootstrap strict JSON | ZIP/runtime profile 전용. 수정/import/업무 parser 전용으로 확장하지 않음 |

새 domain model·예외 hierarchy·공용 parsing framework는 필요 없다.

## 3. 확정 pure API — 후보 C 선택

```python
load_acceptance_review_artifact_bytes(
    *,
    raw_bytes: bytes,
    expected_acceptances: tuple[PolicyBenefitAcceptance, ...],
) -> AcceptanceReviewArtifact
```

두 인자 모두 required·keyword-only다. bytes subclass/bytearray/memoryview/str/경로/dict는 raw_bytes로 받지 않는다. expected_acceptances도 nonempty exact tuple이며 모든 원소는 exact PolicyBenefitAcceptance다. 이 함수는 파일·네트워크·시각·Git을 조회하지 않는다. 동일 입력의 정상 반환/오류가 결정적이며 raw bytes SHA256 계산은 순수 계산이다.

| 후보 | 기대값/record 대응 | multiple entry/최소성 | 결정 |
|---|---|---|---|
| A bytes+expected_ref | digest는 공급되나 외부20값 원본 대응이 별도 필요 | 여러 entry 구조는 가능, 원본 보존까지 닫지 못함 | 제외 |
| B bytes+expected_acceptance 하나 | 그1개 원본/ref를 정확히 결합 가능 | 다른 entry의 외부 원본이 없어 전부 대조/원본 보존 못함 | 제외 |
| C bytes+expected_acceptances tuple | 모든 실제 entry의 신뢰된 원본과 ref를 공급 | 중복 모델 없이 여러 target/revision 지원 | 선택 |

이는 아직 없던 loader 입력을 확정하는 것이며 기존 모델/API 변경이 아니다. 예상 record tuple은 Context 복제 모델이 아니다. Context는 한 target이지만 raw Artifact는 여러 target을 담을 수 있어 Context 타입을 대신 받지 않는다.

## 4. 기대값 원천·공급 목록 계약

외부 발급/자료 준비자가 **이미 존재하는 신뢰된 불변 Acceptance 원본**을 공급한다. body에서 record를 발급한 뒤 그것을 expected로 되넣지 않는다. 실제 bytes로 H를 계산한 뒤 expected ref를 자동 갱신하지 않는다.

expected tuple은 해당 Artifact 전체 entries와 정확히 일대일로 대응해야 한다. 모든 원본 review_artifact_ref가 같은 exact content-addressed 문자열이어야 한다. acceptance_ref 및 `(policy_id, scope, benefit_id, acceptance_version)`은 각각 유일해야 한다. 다른 Artifact의 원본/불필요 추가/누락은 허용하지 않는다. tuple 순서는 raw entries 순서와 달라도 된다. 유효한 순열에서 최종 출력의 entry 순서는 raw 순서이고 각 acceptance는 대응하는 **공급 원본 객체 자체**다.

같은 Artifact에 다른 target의 entry가 있다면 그 thin Acceptance 원본들도 명시 공급한다. 관련 없는 역사 Snapshot/Registry/원문까지 일괄 로드하거나 새 index/DB를 만드는 의무는 아니다. 이미 읽은 body를 근거로 부족한 expected record를 자동 생성하지 않는다. 공급되지 않으면 실패하고 caller가 원본을 확보해야 한다. 후속 준비자가 이 목록을 보존·명시하는 책임은 남는다.

위 조건을 모두 확인한 뒤 expected_acceptances[0].review_artifact_ref를 공통 expected ref로 읽는다. 첫 원소/마지막 원소가 selected/latest인 것은 아니다. 별도 중복 expected_hash/ref 인자·기본값·skip_hash 옵션은 두지 않는다. supplied 원본의 진실성/전역 이력 완전성·악성 강제 객체 조작은 로컬 loader가 인증할 수 없다.

## 5. Content-addressed identity·hash 순서

정확한 ref 문법은 `acceptance-review:sha256:[0-9a-f]{64}` fullmatch다. prefix/hex는 ASCII·case sensitive이고 strip/대소문자 변환/URL 해석/legacy fallback을 하지 않는다. 기존 record의 opaque ref constructor 계약은 그대로지만 opaque ref를 이 loader의 expected로 쓰면 거부한다.

입력/expected 검사 → 공통 ref의 suffix H 확보 → **받은 raw_bytes 전체의 SHA256** 계산 → H와 비교 → 일치할 때만 UTF-8/JSON 해석 순서다. 해시 불일치 bytes는 구조상 정상인지와 무관하게 반환하지 않는다. 실제 digest를 기대값으로 채택하거나 diagnostic to_dict/Benefit fingerprint를 대신 hash하지 않는다.

동일 경로 아래 다른 내용,1byte 변화,공백/개행/key 순서 변화는 이전 expected ref와 hash 불일치다. 공격자가 record와 bytes를 함께 새로 만든 경우까지 SHA256이 원본 발급 권한을 증명하는 것은 아니다.

## 6. Raw·중간 표현·domain 분리

| 단계 | 표현 | 자기 ref/record 처리 |
|---|---|---|
| A raw 파일 | UTF-8 canonical JSON bytes | root에 schema_version/entries만 존재. entry.acceptance는20key |
| B JSON 중간 표현 | 새 dict/list/str/int/None; 외부 노출/새 DTO 없음 | duplicate·primitive/type·schema·canonical 검사, 원래 배열 순서 유지 |
| C 구조 검증 후보 | 기존 모델로 만든 메모리상 임시 값 | 공통 expected ref를21번째 필드로 주입, 기존 constructor 검증 |
| D 최종 반환 | 기존 AcceptanceReviewArtifact | 모든20값 대조 후 각 acceptance를 supplied 원본으로 결합 |

후보 생성은 실제 Acceptance 발급/저장/승인 행위가 아니다. 빈 문자열·자리 ref·아직 모르는 hash를 주입하지 않는다. input bytes로부터 유효하다고 주장하는 record를 authoritative 원본으로 승격하지 않는다. 최종 원본 보존과21필드 constructor 검증을 모두 만족시키는 절차는14절이다.

## 7. Root와 raw entry schema

Root는 정확히2key: `schema_version: str` 값 `benefit-acceptance-review-1.0`, `entries: list[raw entry]`. 빈 entries는 기존 root 모델에서 거부한다. root.review_artifact_ref/hash/status/verified/accepted_terms 등의 추가 key는 없다.

모든 raw entry는 아래 정확한15key를 **항상 포함**한다. nullable/빈 배열도 생략하지 않는다. 표 순서는 schema walk/진단 순서이며 실제 파일의 object key 순서는10절 canonical 정렬을 따른다.

| # | key | JSON 타입 / 복원 |
|---|---|---|
| 1 | acceptance | 8절의 정확한20key object → 기존21필드 객체 |
| 2 | accepted_terms_ref | ArtifactReference object 또는 null |
| 3 | coverage_snapshot_ref | ArtifactReference object 또는 null |
| 4 | policy_envelope_ref | ArtifactReference object 또는 null |
| 5 | coverage_reviews_ref | ArtifactReference object 또는 null |
| 6 | dataset_manifest_ref | ArtifactReference object 또는 null |
| 7 | source_registry_ref | ArtifactReference object 또는 null |
| 8 | implementation_artifact_ref | ArtifactReference object 또는 null |
| 9 | claim_evidence | ClaimEvidenceMapping object array |
| 10 | source_bindings | SourceBinding object array |
| 11 | source_documents | ReviewSourceOriginal object array |
| 12 | prepared_by | string |
| 13 | reviewed_by | string |
| 14 | review_note | string |
| 15 | manual_scenario_ids | string array |

ACCEPTED는 참조7개 non-null·정확한5claim·nonempty source 목록, REVOKED는 참조7개 null·3개 검토/source 목록 empty를 요구한다. 별도 raw boolean을 신설하지 않고 기존 Entry constructor가 검사한다.

## 8. Acceptance raw20key — exact allowlist

기존21필드 중 **review_artifact_ref만 제외**한다. 나머지20개는 required다. 표의 순서는 기존 record 필드 순서/대조 순서다. reflected 미래 필드를 자동 포함하는 serializer 계약이 아니다.

| # | key | JSON 타입 / 기존 값 규약 |
|---|---|---|
| 1 | acceptance_ref | string, exact 비공백 opaque identity |
| 2 | acceptance_version | string, 기존 a 양의 버전 |
| 3 | status | string, ACCEPTED 또는 REVOKED |
| 4 | policy_id | string, 기존 canonical ID |
| 5 | scope | edition_id/quarter 정확한2key object |
| 6 | benefit_id | string, 기존 canonical ID |
| 7 | coverage_inventory_version | string, 기존 i 양의 버전 |
| 8 | coverage_inventory_fingerprint | string, lowercase64hex |
| 9 | coverage_rule_version | string, 기존 record의 비공백 규약; 임의 r 버전 제약 추가 없음 |
| 10 | coverage_policy_tree_fingerprint | string, lowercase64hex |
| 11 | coverage_dataset_version | string, 비공백 |
| 12 | coverage_source_registry_fingerprint | string, lowercase64hex |
| 13 | coverage_implementation_fingerprint | string, lowercase64hex |
| 14 | benefit_version | string, 기존 b 양의 버전 |
| 15 | benefit_fingerprint | string, lowercase64hex |
| 16 | benefit_dataset_version | string, 비공백 |
| 17 | benefit_source_registry_fingerprint | string, lowercase64hex |
| 18 | reviewed_at | required ISO date string, null 불가 |
| 19 | valid_until | required ISO date string, null 불가 |
| 20 | revokes_acceptance_ref | string 또는 명시 null; status 조합은 기존 모델 |

여섯 fingerprint의 문법과 i/a/b 버전·policy/benefit ID는 기존 constructor를 사용한다. ID는 `[A-Z0-9]+(?:-[A-Z0-9]+)*`, i/a/b는 각각 기존 prefix의 양의4자리 이상 규약이며0000 금지다. version 문자열을 숫자로 바꾸거나 새 해시를 계산하지 않는다.

## 9. Nested raw schema와 primitive 타입

| 위치/타입 | exact key 집합 | JSON 값·기존 복원 |
|---|---|---|
| ApplicabilityScope | edition_id, quarter | edition_id string; quarter integer 또는 null → 기존 Scope |
| ArtifactReference | path, sha256 | 둘 다 string → 기존 path/64hex constructor; 파일 조회 없음 |
| SourceBinding | source_document_id, document_version | 둘 다 string → 기존 ID/d 버전 constructor |
| ClaimEvidenceMapping | claim, evidence_refs | claim string; evidence_refs string array → Enum+기존 모델 |
| ReviewSourceOriginal | binding, artifact | 위 두 object → 기존 모델 |

Scope.edition_id는 ASCII4자리이며 기존대로0000도 구조적으로 허용한다. quarter는 `type(value) is int` 또는 None이어야 한다. bool은 int로 받지 않으며 기존 constructor가1~4 범위를 검사한다. null은 미입력이 아니라 연간 범위다. 날짜나 ref에서 scope를 추정하지 않는다.

date는 정확한 ASCII `[0-9]{4}-[0-9]{2}-[0-9]{2}`와 실제 calendar date를 함께 만족해야 한다. compact/week date·datetime·timezone·공백·잘못된 윤일은 거부한다. exact date를 만들고 기존 record의 reviewed_at<=valid_until을 검사한다.

모든 JSON string은 그대로 보존한다. `"100000"`을 int로, int를 string으로, null을 빈 배열로, list를 객체로 보정하지 않는다. JSON array→새 tuple, canonical string→해당 Enum, ISO string→date는 **명시된 parsing 변환**이다. domain constructor에 raw Enum string/list를 넘겨 자동 변환하게 하지 않는다.

## 10. Canonical bytes — 프로젝트 전용 C1 규약 확정

이번에 **canonical 형식인 raw body만 loader가 수용**하도록 확정한다. M2.54의 raw hash 규칙에 형식 제약을 구체화하는 것이며 기존 domain to_dict/지문 함수·schema 이름을 바꾸지 않는다. 아직 실제 발급 bytes가 없으므로 migration0개다. 임의 JSON도 hash만 맞으면 수용된다는 계약은 아니다.

설계식 C(P)는 strict schema에 맞는 **raw JSON payload P**를 다음 설정으로 인코딩한 bytes다. 구현 코드를 이번에 만들지 않는다.

```text
C(P) = json.dumps(P, sort_keys=True, separators=(",", ":"),
                  ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")
```

| 항목 | 확정 규칙 |
|---|---|
| encoding/BOM | strict UTF-8, BOM 금지, 다른 encoding 추정 금지 |
| key ordering | 모든 object에서 sort_keys=True. 허용 key는 ASCII이며 schema 표 순서와 구별 |
| separators/indent | 쉼표와 콜론 사이 공백 없음, indent 없음 |
| newline | 파일 앞/뒤 개행·공백 없음. 문자열 안 개행은 JSON escape로 보존 |
| Unicode | ensure_ascii=False; NFC/NFD normalization 없음. scalar 값 보존, unpaired surrogate 금지 |
| escape | 위 encoder의 quote/backslash/control escaping 사용. 임의 slash/Unicode escape 대체 없음 |
| 숫자 | 이 schema의 정수 위치는 quarter뿐. float/exponent/-Infinity/NaN 금지. bool은 int 아님 |
| null | JSON null을 그대로 보존. key 생략/"null" 문자열과 다름 |
| 배열 | entry/evidence/scenario 순서 그대로. canonical화하려고 정렬/dedupe하지 않음 |
| duplicate key | 어느 깊이에서도 거부. last-wins dict 생성 금지 |

JSON 파싱·전체 shape/type 검사 뒤 raw_bytes와 **C(P)의 bytes equality**를 확인한다. 이는 형식 검사다. 지문은 항상 입력 raw_bytes에서 먼저 계산하며 C(P)의 hash로 expected를 교체하지 않는다. pretty JSON·다른 key 순서·Korean \u escape는 새 expected hash를 갖더라도 NONCANONICAL 오류다. 같은 변형을 이전 expected ref로 넣으면 더 앞선 raw hash 오류다.

C1은 이 제한된 string/int/null schema의 프로젝트 규약이며 RFC8785/JCS 전체 구현을 주장하지 않는다. 기존 Benefit/Coverage fingerprint의 payload·schema·정렬 목록·literal은 별개다. 전역 Unicode 정규화·16필드 Snapshot payload의 재사용도 없다.

## 11. Strict JSON 처리

UTF-8을 성공적으로 decode한 동일 bytes의 문자열만 해석한다. duplicate 감지용 object-pairs hook이 key/value pairs를 덮어쓰기 전에 확인한다. parse_constant로 NaN/Infinity/-Infinity를 거부하고 parse_float로 모든 decimal/exponent 토큰(1.0/1e0 포함)을 거부한다. parse_int는 정확한 int를 만들며 Python의 정수 parsing 제한 초과도 NUMBER 오류로 변환한다. bool은 JSON에서 bool로 남겨 타입 검사에서 거부한다.

JSONDecodeError/잘못된 문법/여러 top-level value/decoder RecursionError는 JSON 오류다. decode된 JSON의 모든 key/문자열 값에 unpaired surrogate가 없는지 확인한다. 유효한 surrogate escape pair는 scalar로 복원될 수 있으나 파일 canonical 비교에서 UTF-8 직접 표현과 다르면 거부한다. 원문 값/파서 traceback/사용자 문자열을 오류 메시지에 출력하지 않는다.

JSON object는 exact dict, array는 exact list여야 한다. schema상 모든 key가 required이므로 missing을 먼저, extra를 다음으로 검사한다. missing은 정의된 key 순서의 첫 key, extra는 해당 object 경로만 보고하고 임의 unknown key 이름을 출력하지 않는다. nullable도 missing과 구분한다. tuple/subclass/Enum/date 같은 Python 객체는 외부 JSON 입력이 아니며 별도 public object parser를 제공하지 않는다.

## 12. 자기참조·writer/loader 구분

raw root에는 자기 ref가 없고 raw entry.acceptance에도 review_artifact_ref가 없다. 관련 철회 target은 원래 revokes_acceptance_ref만 사용한다. 같은 Artifact 안의 A/B entry가 서로를 지목해도 본문의 자기 content hash를 필요로 하지 않는다.

발급 측의 순서는 raw20값/원본 참조/검토 metadata 확정 → C(P) 고정 → H(raw bytes) 계산 → 해당 ref의21필드 record 발급이다. 이는 향후 writer/발급 책임이며 이번에는 구현하지 않는다.

Loader는 이미 발급된 외부 원본과 기대 ref를 입력받는다. diagnostic root.to_dict의 review_artifact_ref와 entry.acceptance.to_dict의21key는 raw format이 아니므로 그대로 입력하면 schema 오류다. to_dict 의미를 바꾸거나 schema_version을 domain stored field에 추가하지 않는다.

## 13. 동일 bytes와 외부 파일 준비

향후 로컬 preparation의 입력은 trusted absolute archive root와 expected_acceptances 원본 tuple이다. 출력은 이 loader가 반환한 Artifact 또는 명시 실패다. 경로는 기존 규약대로 `<archive_root>/acceptance-reviews/<H>.json`이다. root/H는 외부 신뢰된 설정/원본에서 얻으며 body·사용자 업로드·LLM 선언에서 얻지 않는다.

외부 단계는 해석된 경로가 archive root 안인지·부적절한 우회 경로인지 확인하고 실제 파일을 **한번 열어 immutable bytes로 확보**한다. 같은 bytes를 pure loader에 넘긴다. hash용 open 후 parse용 재open을 하지 않는다. 파일을 확보한 뒤 디스크가 바뀌어도 파싱하는 bytes는 이미 확보한 snapshot이며 원본 저장소 불변성·후속 재사용은 외부 보존 책임이다. 실행 ZIP의 handle 수명/프로세스 검증을 이 데이터 파일에 그대로 복제하지 않는다.

M2.54의 외부 preparation에 부여한 bytes 검증 책임은 유지한다. 실제 SHA 계산·비교는 preparation이 이 순수 loader를 직접 호출하여 수행하게 된다. 외부에서 검증 완료 bool을 받거나 같은 bytes를 loader 밖에서 다시 해시해야 한다는 계약이 아니다. 파일 확보와 순수 bytes 계산을 분리한 책임 구체화다.

OSError/파일 미확보는 향후 preparation의 PolicyDataError `REVIEW_ARTIFACT_FILE_UNAVAILABLE: artifact_file: unavailable`로 보고한다. raw path/payload를 오류에 출력하지 않고 loader/후속 evaluator 정상 Result를 발급하지 않는다. 별도 파일 API·네트워크/클라우드/감시/비동기/DB/업로드 서비스를 이번 다음 loader 작업에도 추가하지 않는다.

이 bytes API는 공격자에게 공개한 무제한 업로드 endpoint가 아니다. 새 arbitrary 크기/entry 수 제한을 승인된 모델에 추가하지 않는다. decoder recursion/정수 parsing 실패는 아래 stable 오류로 처리하고, MemoryError/SystemExit/KeyboardInterrupt를 정상 데이터 오류로 삼켜 성공 결과를 만들지 않는다. 실제 운영의 자원 제한은 파일 준비/서비스 경계의 별도 책임이다.

## 14. 기존 모델 복원·원본 record 결합

모든 shape/type 검사와 canonical 검사가 끝난 다음, raw entry 순서대로 아래 순서를 적용한다. private parser helper만 사용하고 새 중복 domain 모델은 만들지 않는다.

1. acceptance.status를 BenefitAcceptanceStatus로 명시 해석한다. scope2key로 ApplicabilityScope를 만들고 reviewed_at, valid_until 순으로 exact ISO date를 만든다.
2. raw20값에 **공통 외부 expected ref**를21번째 값으로 결합하여 임시 PolicyBenefitAcceptance를 만든다. 기존 ID/version/fingerprint/date 순서·same-release dataset/Registry equality·status/revokes/self-revoke invariant가 그대로 실행된다. constructor 의미/순서는 수정하지 않는다.
3. entry의 참조7개를 필드 순서로 ArtifactReference 또는 None으로 복원한다.
4. claim_evidence 순서대로 claim Enum → evidence list의 tuple → ClaimEvidenceMapping을 만든다. 이어 source_bindings를 SourceBinding으로 복원한다.
5. source_documents 순서대로 SourceBinding → ArtifactReference → ReviewSourceOriginal을 만든다. 새 metadata string/scenario tuple과 함께 AcceptanceReviewEntry를 생성한다.
6. 모든 후보 entry로 AcceptanceReviewArtifact를 생성하여 root 유일성·외부 ref equality를 검사한다. rootref는 외부 값이며 body에서 얻지 않는다.
7. 15절의 전체 record binding을 확인한다. 성공 후 각 entry의 acceptance를 **대응 supplied 원본 객체**로 결합하여 최종 Entry/Root를 기존 constructor로 생성한다. 후보의 다른 nested 객체/tuple 순서는 그대로 보존한다. 새 전용 모델/상태/token은 없다.

후보21필드는 로컬 검증용 일시 값이며 발급 기록으로 보존/반환하지 않는다. 마지막 원본 결합은 값이 같아 로컬 invariant를 바꾸지 않는다. 어느 단계라도 실패하면 부분 Artifact/list/일부 entry를 반환하지 않는다. 정상 반환의 모든 entry.acceptance는 supplied record와 `is`도 같아야 한다.

## 15. 외부 record와 raw20key 정확한 대응

root 구조가 유효한 뒤 raw 순서의 각 entry에 대해 acceptance_ref로 supplied 유일 원본을 찾는다. unlisted body entry를 먼저 거부한 뒤 expected tuple 순서로 빠진 expected entry를 거부한다. 그 다음 raw 순서·8절20필드 순서로 값 equality를 확인한다. 같은 ref라도 a version/status/target/scope/날짜/link/어느 binding 하나라도 다르면 오류다.21번째 ref도 외부 원본에서 동일한 값임이 이미 확인돼 있다.

정확한 전체 대응을 요구하므로 한 expected만 제시해 여러 entry를 묵시 승인하지 않는다. expected tuple 순열은 정상 결과를 바꾸지 않으며 raw entries 순서는 결과 값의 일부다. invalid 입력 순열에서 첫 오류의 index까지 같아야 한다는 계약은 아니다.

이 검사는 **record↔raw 결정 값**의 대응이다. record.benefit_fingerprint와 실제 BenefitSnapshot 지문 대조, Coverage snapshot 원본 재계산, source 합집합·locator·원문 의미·사람 권한 검사는 후속이다. canonical bytes+원본 record equality도 실제 검토의 충분성을 증명하지 않는다.

## 16. Multiple entry·철회·순서

entries는 nonempty, 여러 revision·서로 다른 policy/scope/benefit 혼합을 허용한다. 각 acceptance_ref와 target/version key는 유일해야 한다. 모든 entry의 review_artifact_ref는 같은 외부 H의 ref로 복원한다. 배열 순서를 보존하고 자동 sort·dedupe·최신 선택을 하지 않는다. 같은 a0001을 다른 target에 쓰는 것은 허용한다.

REVOKED raw는 기존 record의 nonblank revokes_acceptance_ref와 사유 metadata를 요구한다. None/자기 ref 등 **record 로컬 오류**는 거부한다. target이 실제 Context에 존재하는지·ACCEPTED인지·11binding이 맞는지·후행 revision/date인지·incoming edge가 하나인지는 기존 Context/후속 validator 책임이다. 단독 REVOKED entry도 구조적으로 가능하며 여기서 새 철회 그래프를 만들지 않는다.

누락 entry는 record binding 실패이며 정상 미검토 reason으로 바꾸지 않는다. 실제로 철회된 A의 B를 supplied 이력에서 감춘 누락까지 loader가 발견할 수는 없다. 원본 공급/선택 완전성은 외부 책임이다.

## 17. Accepted terms·source originals·claim 경계

accepted_terms_ref는 path/SHA256 구조만 복원한다. 당시 Snapshot 파일 존재·16값/FIXED completeness·실제 Benefit fingerprint·current version 변경은 검사하지 않는다. historical b0001과 current b0002를 혼동하지 않는다.

ReviewSourceOriginal의 binding/artifact2key 및 Entry의 source 목록 대응은 기존 모델로 검사한다. SourceBinding은 ID/d version2필드뿐이고 locator/status/verified_at를 새로 붙이지 않는다. ArtifactReference에 sha256이 있어도 실제 공식 source bytes 확보·무결성 검증을 완료한 것은 아니다.

Claim의 raw canonical string을 정확한 BenefitReviewClaim으로 해석한다. ACCEPTED는 AMOUNT/CADENCE/MEDIUM/RESTRICTION/APPLICABLE_MONTHS 고정 순서이며 unknown claim·누락·중복·행 내부 duplicate ref는 기존 모델이 거부한다. 한 ref의 claim 간 재사용과 행 내부 evidence 순서는 보존한다. Snapshot refs 부분목록·실제 source/locator 존재·policy applicability·ACTIVE/VERIFIED/freshness·내용이 claim을 지지하는지 검사는 loader 역할이 아니다.

## 18. 고정 validation phases

| phase | 처리·순서 | 성공 후 허용되는 다음 단계 |
|---|---|---|
| P0 | raw_bytes exact bytes → expected tuple exact/nonempty → 전체 원소 exact record 타입 | 외부 record 내용 조회 |
| P1 | 전체 expected ref 문법(입력 순서) → 공통 ref equality → acceptance_ref 유일성 → target/version key 유일성 | 공통 expected H 확보 |
| P2 | 입력 raw bytes SHA256과 H 비교 | UTF-8 해석 시작 |
| P3 | BOM 검사 → strict UTF-8 decode | JSON 파싱 |
| P4 | strict JSON+hooks → 문자열/key Unicode scalar 검사 | raw primitive 트리 |
| P5 | root exact shape/keys → schema_version exact 값 →7~9절 schema 순서의 전체 nested shape/primitive 검사 | 의미 변환 없는 typed JSON |
| P6 | C(P) 인코딩 → raw_bytes와 exact equality | canonical raw body |
| P7 | 14절 순서의 Enum/date·기존 nested/record/Entry/Root 생성 | 로컬 구조 유효한 후보 |
| P8 | 15절 전체 entry 집합 →20필드 대응 → supplied 원본 결합 | 전체 원본 대응 완료 |
| P9 | 최종 기존 모델 반환 | 후속 source/content validator의 입력 재료 |

P5는 object마다 exact dict → missing keys → extra keys → 선언된 field 순서의 값/자식 검사다. array는 index 순서다. nullable 분기를 제외하고 어느 missing/null/default도 자동 생성하지 않는다. 모든 entry의 P5 검사가 P7 의미 검사보다 먼저다.

P4 내부는 Python 표준 json decoder의 **callback 실행 순서**를 따른다. 숫자 hook은 토큰 해석 때, duplicate hook은 해당 object의 pairs가 완성될 때 실행된다. 따라서 malformed JSON·duplicate·NaN이 섞인 문서에서 오류 종류별 임의 전역 우선순위를 다시 부여하지 않는다. decoder가 먼저 발생시킨 오류가 우선이며 동일 bytes/명시 런타임에서 결정적이다. Unicode scalar 순회는 파싱 완료 후다.

P7에서 Enum/date 변환이 record constructor보다 앞서는 것은18절의 확정 parsing 순서다. 기존 constructor 내부의 오류 순서를 raw JSON key 순서나 reflected fields로 바꾸지 않는다. P7 구조 오류는 P8 binding 모순보다 우선한다. 어떤 오류도 BENEFIT_METADATA_NOT_REVIEWED/UNKNOWN/정상0원으로 낮추지 않는다.

## 19. Stable 오류 계약

모든 아래 loader 실패는 **기존 PolicyDataError**를 사용한다. 새 exception Enum/class hierarchy는 없다. 메시지는 `<PREFIX>: <field>: <고정 reason>`이며 원문·실제 ref/hash/path·임의 JSON key/value·traceback을 노출하지 않는다. field는 schema의 고정 key와 array index만 사용한다.

| prefix | phase / field 방향 | 범주 |
|---|---|---|
| INVALID_REVIEW_ARTIFACT_LOADER_INPUT | P0 raw_bytes/expected_acceptances, P1 expected_acceptances | 타입·empty·expected 중복/공통 ref 모순 |
| INVALID_REVIEW_ARTIFACT_EXPECTED_REF | P1 expected_acceptances[i].review_artifact_ref | malformed/opaque/uppercase ref |
| REVIEW_ARTIFACT_BYTES_MISMATCH | P2 raw_bytes | 기대 raw SHA 불일치 |
| INVALID_REVIEW_ARTIFACT_ENCODING | P3 raw_bytes | BOM/strict UTF-8 오류 |
| INVALID_REVIEW_ARTIFACT_JSON | P4 json | 문법·trailing document·RecursionError |
| DUPLICATE_REVIEW_ARTIFACT_JSON_KEY | P4 json | 깊이에 관계없는 duplicate key |
| INVALID_REVIEW_ARTIFACT_NUMBER | P4 json | float/exponent/NaN/Infinity/정수 parsing 실패 |
| INVALID_REVIEW_ARTIFACT_UNICODE | P4 json | key/문자열의 unpaired surrogate |
| INVALID_REVIEW_ARTIFACT_FIELDS | P5 object 경로 | missing 또는 extra key; 고정 reason으로 구분 |
| INVALID_REVIEW_ARTIFACT_SCHEMA | P5 schema_version | 지원하지 않는 exact string 값 |
| INVALID_REVIEW_ARTIFACT_TYPE | P5 값 경로 | 잘못된 primitive/object/array·bool vs int·금지 null |
| NONCANONICAL_REVIEW_ARTIFACT_BYTES | P6 raw_bytes | C(P)와 다른 bytes |
| INVALID_REVIEW_ARTIFACT_VALUE | P7 해당 enum/date 경로 | unknown Enum 또는 정확한 ISO date가 아님 |
| INVALID_REVIEW_ARTIFACT_MODEL | P7/P8 현재 생성 object 경로 | 기존 constructor PolicyDataError |
| REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH | P8 entries 또는 entries[i].acceptance.<known field> | unlisted/missing entry·20값 모순 |

기존 constructor PolicyDataError는 loader 경계에서 MODEL prefix로 변환한다. cause의 메시지를 파싱하여 코드나 field를 추정하지 않고 현재 생성 중인 object 경로를 사용한다. 기존 생성자의 오류/의미 자체는 변경하지 않는다. object 예: entries[0].acceptance.scope, entries[0].source_bindings[0], root. Enum/date의 VALUE 변환 오류와 구분한다.

M2.54 18절의 ACCEPTANCE_REVIEW_INTEGRITY_MISMATCH/ACCEPTANCE_REVIEW_BINDING_MISMATCH는 당시 미구현 외부/내용 검증의 prefix 방향이었다. 이번 bytes loader의 raw SHA 오류와 raw20↔record 오류는 위 BYTES_MISMATCH/ACCEPTANCE_BINDING_MISMATCH로 명시 구체화한다. companion/역사 Snapshot 내용 검증 오류까지 loader prefix로 재분류하지 않는다. 실제 구현된 모델의 INVALID_ACCEPTANCE_REVIEW_ARTIFACT prefix는 그대로이며 loader 안에서 포착한 경우만 고정 MODEL 경계로 감싼다. 기존 함수/예외 동작 변경은 없다.

signature의 missing/extra/positional 인자 오용은 Python TypeError이고, 함수에 정상 전달된 인자 값의 타입 오류는 P0 PolicyDataError다. 파일 오류는13절의 외부 FILE_UNAVAILABLE이며 pure loader에 파일 I/O exception 처리를 넣지 않는다. 알고리즘 버그·메모리 고갈을 포괄 except Exception으로 정상 미검토 결과로 삼키지 않는다.

## 20. 순수성과 신뢰 상승 방지

정상 반환의 의미는 **기대 ref에 맞는 bytes + canonical strict schema + 기존 로컬 구조 + supplied record 대응**이다. raw 지문과 C(P) equality는 확인하지만 정의/원문 해시를 재계산하지 않는다. 검토자 handle이 비공백/서로 다르다는 검사로 실제 사람 독립성·권한을 인증하지 않는다.

reviewed/policy_verified/source_verified/usable/bridge_supported/cashflow_applicable boolean·검증 token·평가 결과를 생성하지 않는다. loader 결과를 받아 다시 같은 bytes를 열었다고 주장하거나 별도 호출의 승인 token으로 캐시하지 않는다. 불변 객체는 검토 자료의 값이며 생산 서비스의 검증 완료 증명서는 아니다.

## 21. 역사·Source Gate·content validator·evaluator 연결

역사 Artifact를 로드해 record와 대조해도 당시 Snapshot/Registry/공식 원문을 대조한 것은 아니다. 후속 외부 preparation은 companion bytes를 확보하고, pure content validator는 그 당시 원본과 Coverage/Benefit 지문·source 합집합·claim mapping을 비교해야 한다. 현재 Benefit과 역사 원본의 정상 version 차이는 후속 Acceptance evaluator 책임이다.

Source Gate의 ACTIVE/VERIFIED·문서/locator 적용·날짜·freshness, Policy VERIFIED, Coverage FULL은 모두 별도다. 실행 ZIP verify-only도 이 loader 성공으로 대체하지 않는다. 실제 원문 내용과 검토 권한은 외부 governance다.

M2.51의8-input B는 유지한다. trusted A/C가 같은 호출에서 이 loader와 후속 내용/원본 검증을 실제 실행하고, current 원본의 공식 Coverage producer 결과와 동일 객체로 B를 호출해야 한다. 이 loader 결과를9번째 B 인자/외부 verified bool로 추가하지 않는다. 현재 이 callable과 Source Gate/content validator/B/C는 모두 미구현이므로 production USABLE 경로를 열지 않는다.

## 22. 합성 검증 계획 — 64개 수동 사례

아래는 **문서 설계 사례64개**이며 실행 테스트0개다. 전제 표기 P=canonical raw20 payload, C(P)=10절 bytes, R=그 bytes와 독립적으로 공급된 exact Acceptance 원본 목록, H=R의 공통 expected digest다. 향후 합성 테스트 authoring에서만 기대값·body 대응을 명시 생성하며 실제 정책 자료는 쓰지 않는다. S=후속 순수 loader 테스트 가능, X=외부 preparation 테스트 필요, B=경계/후속 계층 테스트다. 정상 표의 '-'는 오류 없음이다.

| ID | 입력·전제 | 기대 결과 | phase | 오류 prefix | 후속 실행 가능 여부 |
|---|---|---|---|---|---|
| RL01 | valid ACCEPTED C(P), R 정확 | 원본 결합 Artifact 반환 | P0~P9 | - | S |
| RL02 | valid 단독 REVOKED, R 정확 | target 조회 없이 구조 복원 | P7~P9 | - | S |
| RL03 | A/B 여러 entry·정확한 전체 R | raw 순서/공통 ref 보존 | P7~P9 | - | S |
| RL04 | 다른 policy/scope/benefit entry 혼합 | 각 원본에 정확히 결합 | P7~P9 | - | S |
| RL05 | 한국어 검토 사유/handle canonical UTF-8 | scalar 문자열 값 보존 | P3~P9 | - | S |
| RL06 | annual null/분기 int·ISO date·Enum | 정확한 기존 타입 복원 | P5~P9 | - | S, 변형별 |
| RL07 | 한 claim 여러 evidence, claim 간 공유 | 입력 순서·공유 허용 | P7 | - | S |
| RL08 | 동일 bytes/R 100회 | 동등한 값·동일 진단 출력 | P0~P9 | - | S |
| RL09 | R 순열·raw entries 고정 | 결과 순서 동일·acceptance는 supplied 원본 is | P8~P9 | - | S |
| RL10 | expected가 list/subclass/None | 타입 오류 | P0 | INVALID_REVIEW_ARTIFACT_LOADER_INPUT | S |
| RL11 | raw가 str/dict/bytearray/bytes subclass | 타입 오류·decode 없음 | P0 | INVALID_REVIEW_ARTIFACT_LOADER_INPUT | S |
| RL12 | empty R 또는 wrong record element | 공급 입력 오류 | P0 | INVALID_REVIEW_ARTIFACT_LOADER_INPUT | S |
| RL13 | R ref/revision key 중복 | hash 전 거부 | P1 | INVALID_REVIEW_ARTIFACT_LOADER_INPUT | S |
| RL14 | R의 외부 refs가 서로 다름 | hash 전 거부 | P1 | INVALID_REVIEW_ARTIFACT_LOADER_INPUT | S |
| RL15 | uppercase expected digest | normalization 없이 거부 | P1 | INVALID_REVIEW_ARTIFACT_EXPECTED_REF | S |
| RL16 | opaque/잘못된 prefix/길이/공백 | ref 문법 오류 | P1 | INVALID_REVIEW_ARTIFACT_EXPECTED_REF | S |
| RL17 | 한 byte 변조, 이전 R 유지 | JSON 검사 전 hash 거부 | P2 | REVIEW_ARTIFACT_BYTES_MISMATCH | S |
| RL18 | 같은 filename의 다른 bytes | 확보한 bytes hash 불일치 | P2 | REVIEW_ARTIFACT_BYTES_MISMATCH | X+S, pure는 filename 미입력 |
| RL19 | 공백/개행만 변경, 이전 R | hash 불일치 | P2 | REVIEW_ARTIFACT_BYTES_MISMATCH | S |
| RL20 | JSON key 순서만 변경, 이전 R | hash 불일치 | P2 | REVIEW_ARTIFACT_BYTES_MISMATCH | S |
| RL21 | 다른 데이터에서 얻은 expected H | hash 불일치 | P2 | REVIEW_ARTIFACT_BYTES_MISMATCH | S |
| RL22 | caller가 bytes와 R을 함께 조작해 H 재발급 | 권한 위조 탐지 보장 없음, 발급 신뢰 위반 | 경계 | - | B, 로컬 인증 불가를 명시 |
| RL23 | hash는 맞지만 malformed UTF-8 | encoding 오류 | P3 | INVALID_REVIEW_ARTIFACT_ENCODING | S |
| RL24 | BOM 포함 bytes와 그 H를 가진 R | BOM 오류 | P3 | INVALID_REVIEW_ARTIFACT_ENCODING | S |
| RL25 | hash 일치 malformed JSON/두 document | JSON 오류 | P4 | INVALID_REVIEW_ARTIFACT_JSON | S |
| RL26 | root duplicate key | 덮어쓰기 전 거부 | P4 | DUPLICATE_REVIEW_ARTIFACT_JSON_KEY | S |
| RL27 | 중첩 acceptance/Scope duplicate key | 깊이 무관 거부 | P4 | DUPLICATE_REVIEW_ARTIFACT_JSON_KEY | S |
| RL28 | NaN/Infinity/-Infinity | 숫자 오류 | P4 | INVALID_REVIEW_ARTIFACT_NUMBER | S |
| RL29 | quarter 1.0/1e0 또는 다른 곳 float | 숫자 토큰 거부 | P4 | INVALID_REVIEW_ARTIFACT_NUMBER | S |
| RL30 | escaped unpaired surrogate | Unicode scalar 위반 | P4 | INVALID_REVIEW_ARTIFACT_UNICODE | S |
| RL31 | top-level list/null/string | root 타입 오류 | P5 | INVALID_REVIEW_ARTIFACT_TYPE | S |
| RL32 | schema_version 다른 string | 지원 schema 오류 | P5 | INVALID_REVIEW_ARTIFACT_SCHEMA | S |
| RL33 | root required key 누락 | missing 오류 | P5 | INVALID_REVIEW_ARTIFACT_FIELDS | S |
| RL34 | root에 review_artifact_ref 추가 | 진단/raw 혼동 거부 | P5 | INVALID_REVIEW_ARTIFACT_FIELDS | S |
| RL35 | nested object 대신 array/null | exact schema 타입 오류 | P5 | INVALID_REVIEW_ARTIFACT_TYPE | S |
| RL36 | nullable ref=null vs key 생략 | null은 후속 status 검사, 생략은 오류 | P5/P7 | INVALID_REVIEW_ARTIFACT_FIELDS 또는 INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL37 | quarter=true 또는 string | bool/int 구별·변환 없음 | P5 | INVALID_REVIEW_ARTIFACT_TYPE | S |
| RL38 | evidence/entries/scenarios가 array 아님 | exact array 타입 오류 | P5 | INVALID_REVIEW_ARTIFACT_TYPE | S |
| RL39 | acceptance20key 정확·R와 일치 | ref 결합 후21필드 원본 보존 | P7~P9 | - | S |
| RL40 | raw20key 한 개 누락 | required 오류 | P5 | INVALID_REVIEW_ARTIFACT_FIELDS | S |
| RL41 | raw acceptance에 review_artifact_ref 추가 | 자기참조 raw21key 거부 | P5 | INVALID_REVIEW_ARTIFACT_FIELDS | S |
| RL42 | 유효한 다른 acceptance_ref의 body | unlisted entry 거부 | P8 | REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH | S |
| RL43 | 같은 ref, 유효한 다른 a version | 원본 revision 모순 | P8 | REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH | S |
| RL44 | malformed Coverage/Benefit fp | 기존 record 문법 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL45 | Coverage/Benefit dataset 다름 | 기존 same-release 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL46 | Coverage/Benefit Registry fp 다름 | 기존 same-release 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL47 | compact/week/datetime/잘못된 calendar date | required ISO date 오류 | P7 | INVALID_REVIEW_ARTIFACT_VALUE | S |
| RL48 | unknown status/claim string | 정확한 Enum 해석 실패 | P7 | INVALID_REVIEW_ARTIFACT_VALUE | S |
| RL49 | malformed evidence ref | 기존 Mapping 문법 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL50 | ArtifactReference path/sha256 한 key 누락 | nested missing 오류 | P5 | INVALID_REVIEW_ARTIFACT_FIELDS | S |
| RL51 | missing/reordered/duplicate claim·행 내부 duplicate | 기존 Entry/Mapping 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL52 | source original binding 순서/값 모순 | 기존 Entry 대응 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL53 | root duplicate ref/revision 또는 empty entries | 기존 root invariant 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL54 | body에 없는 expected 또는 공급 안 된 body entry | 전체 집합 대응 거부 | P8 | REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH | S |
| RL55 | 유효하지만 원본과 다른 날짜/target/20값 중 하나 | 정확한20값 대조 실패 | P8 | REVIEW_ARTIFACT_ACCEPTANCE_BINDING_MISMATCH | S, 필드별 변형 |
| RL56 | pretty/key순서/개행 변형과 맞는 새 expected H | hash 성공 후 canonical 거부 | P6 | NONCANONICAL_REVIEW_ARTIFACT_BYTES | S |
| RL57 | Korean Unicode escape·새 expected H | scalar valid여도 canonical 거부 | P6 | NONCANONICAL_REVIEW_ARTIFACT_BYTES | S |
| RL58 | REVOKED null/blank/self target | 기존 record invariant 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL59 | 문법상 target은 있으나 실제 Context에 없음/11binding 다름 | loader는 Context 미조회 | 경계 | - | B, 후속 Context/validator |
| RL60 | ACCEPTED ref=null 또는 REVOKED에5claim | 기존 Entry status 조합 오류 | P7 | INVALID_REVIEW_ARTIFACT_MODEL | S |
| RL61 | 정상 loader, 사람/claim 내용 검토 미수행 | 검토 완료 선언 없음 | P9 경계 | - | S+B, 실제 진실성 로컬 증명 불가 |
| RL62 | 정상 loader, Policy DRAFT/Coverage SLICE/current 미수용 | VERIFIED/FULL/USABLE 반환 없음 | P9 경계 | - | S+B |
| RL63 | 정상 refs이나 source/locator/원본 파일 미확보 | Source Gate 통과 아님 | P9 경계 | - | S+B |
| RL64 | 정상 loader, 월 현금 Bridge 지원 안 됨 | 금액/적용 결과 생성 없음 | P9 경계 | - | S+B |

모든 비정상 JSON/변형 사례는 해당 실패 phase까지 도달하도록 **그 변형 bytes와 맞는 외부 합성 expected H를 별도 공급**한다. 단 RL17~21은 의도적으로 이전/다른 H를 유지하여 P2를 검증한다. expected가 테스트 authoring에서 만들어졌다는 사실을 실제 발급 신뢰의 증명이라고 설명하지 않는다.

추가 조합 테스트 방향: 잘못된 raw 타입+bad ref는 P0, bad ref+bad hash는 P1, bad hash+malformed JSON은 P2, 뒤 entry의 shape 오류+앞 entry의 domain 오류는 P5, root duplicate+record mismatch는 P7이 우선이다. 각 성공 사례는 원본 record `is`/raw 순서·출력 수정 격리·no I/O도 확인한다. 문서의 사례/변형 수는 실제 pytest 수와 다르다.

## 23. 기존 계약 영향·미해결 범위

기존 Review Artifact4개 모델·Enum·to_dict, Acceptance21/Context4/Evaluation9, BenefitSnapshot16/benefit-snapshot-1.0·BV01~BV16, frozen Coverage schema/GV01~GV15·동결 문서/source, bootstrap·Cashflow를 변경하지 않는다. 신규 raw schema는 이미 선택한 benefit-acceptance-review-1.0 외부 파일에 한정한다.

확정된 사항: API C/전체 expected 원본 대응, 자기참조 없는 raw20/15/2key schema, C1 canonical bytes, 동일 raw bytes SHA 우선, strict UTF-8/JSON·기존 모델 복원·원본 보존, stable phases/errors·외부 준비 경계. loader 구현을 막는 형식/identity 미결정은 없다.

미구현: strict loader 자체·writer/발급·실제 파일 준비/경로 안전 검사, companion/historical 원본 확보와 content validator·Source Gate·evaluator/adapter/Bridge·실제 안산 FULL/VERIFIED·검토 원본/실행 ZIP 확보. 실제 archive 위치/보존 담당자/공식 원문·권한 확인은 외부 운영 책임이다. 이것을 loader 형식 미확정과 혼동하지 않는다.

Assumption A1: trusted 내부 호출자가 이미 발급된 정확한 원본 tuple과 관련 이력을 공급한다. Assumption A2: 실제 공식 근거/사람 검토·권한은 별도 절차에서 확인한다. SHA와 canonical JSON만으로 두 가정을 인증하지 않는다. 실제 정책 혜택 Cashflow 반영0원 원칙과 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED를 유지한다.

## 24. 다음 가장 작은 작업 한 개

**위 bytes loader 하나만 합성 테스트로 구현한다.** 후보 새 모듈은 backend/policy_engine/policy_data/benefit_acceptance_review_artifact_loader.py다. 공개 callable은3절의 load_acceptance_review_artifact_bytes 하나, 최소 private helpers만 허용한다. 별도 public object parser/canonical writer/file loader·검증 생략 인자는 없다.

완료조건: exact2인자·expected 전체 대응·hash-before-parse·동일 bytes·strict JSON/Unicode/C1·기존 모델 constructor/원본 보존·P0~P9/오류 우선순위·다중 entry·합성 성공/오류/경계 테스트·기존7,341개 회귀 보존이다. file I/O/source/content validator/evaluator/adapter/실제 데이터는 제외한다. 이번 문서는 그 구현을 대신하지 않는다.

## 25. 최종 판단

**READY_TO_IMPLEMENT_STRICT_REVIEW_ARTIFACT_LOADER**

정확한 raw payload·순환 없는 hash 대상·기대 원본/ref 공급·strict parsing·복원·오류 순서·외부 preparation 경계가 닫혔다. loader 성공은 record/bytes 구조 대응까지만 의미하며 정책 내용/사람 검토/현재 경제적 적용 승인이 아니다.

## 26. 검증 기록

- 작업 전 전체 pytest: **7,341 passed in 69.79s / skipped0 / failed0 / timeout0**.
- 신규 실행 테스트: **0개**. 수동64개 및 보조 문서 검수는 실행 테스트 수에 포함하지 않는다.
- 작업 후 전체 pytest: **7,341 passed in 69.05s / skipped0 / failed0 / timeout0**. 기존 bootstrap106개와 M2.55 값 모델273개를 포함한다. M2.54 timeout2건은 이번 작업 전/후에서 재발하지 않았고 기존 테스트·timeout 설정을 바꾸지 않았다.
- 사전 backend/tests/data/docs/tools의171개(실제 releases·pycache 별도)는 SHA256이 모두 동일하다. 추가는 이 문서1개뿐, 기존 파일 수정/삭제0개, 최종172개다.
- 실제 release6개 파일의 SHA256·경로·크기·수정시각이 모두 동일하다. GV01~GV15/BV01~BV16 literal/fixture·기존 모든 tests·Coverage freeze·bootstrap·Acceptance/Benefit/Cashflow source·기존 명세를 보존했다.
- 문서 검수:27개 절과 RL01~RL64 연속/유일성, 표 column/fence·UTF-8을 확인했다. raw20표가 실제 Acceptance21필드에서 자기 ref만 제외한 정확한 순서이며 raw entry15표가 실제 Entry15필드와 일치함을 AST로 대조했다. 실제 artifact bytes/정책 지문/발급 기록·금액은 만들지 않았다.

## 27. 최종 보고 항목 대응

보고1=1절,2~3=3절,4~5=4~5절,6~7=7~8·12절,8=10절,9~10=5절,11~14=9~11절,15~16=14~15절,17=16절,18~19=9·14·17절,20=13절,21=18·20절,22~23=18~19절,24=22절,25=20절,26~28=21절,29~32=26절,33~34=23절,35=25절,36=24절. 구현 완료와 설계 확정을 구별한다.

## 28. M2.57 — IMPLEMENTED: Strict Review Artifact Bytes Loader

3절의 exact API를 `backend/policy_engine/policy_data/benefit_acceptance_review_artifact_loader.py`에 구현하고 package public export는 `load_acceptance_review_artifact_bytes` 한 개만 추가했다. 새 저장 모델/예외 hierarchy/공용 JSON framework·public object parser/writer/file preparation은 없다. 기존 모델/serializer는 변경하지 않았다.

### 실제 구현 경로

P0 exact bytes·nonempty exact tuple·전체 exact record 타입 → P1 모든 ref 문법/공통성·ref/revision 유일성 → P2 공급 bytes 전체 SHA256 → P3 BOM·strict UTF-8 → P4 duplicate/number hooks·Unicode scalar → P5 root2/entry15/acceptance20/nested 전체 schema → P6 C1 bytes equality → P7 기존 생성자 복원 → P8 전체 원본 대응/원본 객체 결합 → P9 반환 순서다.

P2가 실패하면 UTF-8/JSON으로 진행하지 않는다. 실제 digest로 기대값을 교체하지 않고 canonical 재직렬화본을 대신 hash하지 않는다. P5는 모든 entry의 shape 검사를 마친 뒤 P7로 진행한다. missing은 고정 allowlist의 첫 key를 고정 reason에 표기하고 extra는 object 경로만 표기한다. raw20key에 자기 review_artifact_ref가 있거나 root 진단 ref가 있으면 거부한다.

P7에서 status → Scope → reviewed_at/valid_until → 기존21필드 Acceptance 순서로 복원한다. 임시 객체는 발급/반환 원본이 아니다.7개 ArtifactReference·claim Enum/Mapping·SourceBinding·ReviewSourceOriginal·Entry/Root의 기존 검증을 재사용한다. P8은 unlisted entry → missing expected → raw 순서/20필드 순서의 값 비교를 수행한다. 성공 후 각 entry.acceptance에는 **외부 원본 객체 자체**를 결합한다. expected tuple 순열은 raw entry 순서/최종 값을 바꾸지 않는다.

기존15개 loader 오류 prefix/phase와 MODEL wrapper 경로를 유지한다. 기존 생성자 오류 메시지를 파싱하지 않고 고정 object 경로로 감싼다. 검증 오류는 부분 Artifact/정상 미검토 reason/금액0원으로 변환하지 않는다.

### 합성 실행 테스트와 수동 사례의 경계

`tests/test_benefit_acceptance_review_artifact_loader.py`에 신규 합성 **332개**를 추가했다. raw fixture는 production to_dict·private parser/canonical helper로 생성하지 않는다. 외부의 명시 metadata로 expected record를 만들고 hash mismatch 사례는 원래 expected를 유지한다. JSON/schema/model 오류는 그 bytes에 맞는 독립 합성 expected digest를 공급하여 실제 목표 phase까지 도달시킨다.

기준 합성 bytes는3002bytes이며 독립적으로 확보해 테스트에 고정한 SHA256은 `809f208a6cdcd6d7dcbf5d2f913bc175ecd1761af07ec6ec5d6a8c0bfbbea197`다. 이는 실제 안산/혜택 정의/실행 artifact 지문이 아니다. 기존 GV/BV도 아니다. fixture authoring의 계산과 실제 loader의 계산을 분리하고 해시 대상이 원본 bytes 자체·1회임을 확인했다.

실행 범위: signature/ref·exact input/subclass·expected 관계, 단일 ACCEPTED/REVOKED·여러 target/역사 version·원본 is 보존, 한국어/NFD/emoji/문자열 개행 보존, 모든 선언 object 위치의 missing/extra/wrong type, UTF-8/BOM/duplicate/숫자/surrogate, canonical 공백/key순서/개행/escape 차이, Enum/날짜/기존 모델·same-release/철회 local invariant,20값/전체 집합 대응, 다중 오류 우선순위, 출력 수정 격리/100회 결정성, no I/O/Registry/계산 경계다.

수동 RL01~RL64는 신규 실행 테스트 수에 더하지 않는다. 파일명이 같은 다른 bytes(RL18)의 **파일 준비 부분**은 미구현이며 bytes mismatch만 검증했다. 실제 Context edge/역사 Snapshot/Source Gate/원문/검토자 권한/현재 usable/Bridge는 실행 성공으로 계산하지 않는다. syscall·환경변수·네트워크·시각·전역 mutable cache를 읽거나 생성하지 않는다.

신규 테스트 초회에는 깊이2000의 JSON이 이 런타임에서 반드시 RecursionError를 낸다는 테스트 가정1건이 실패했다. 실제로는 decode가 성공하여 root TYPE 오류가 맞았다. 구현/명세를 바꾸지 않고 그 새 테스트를 decoder가 실제 RecursionError를 발생시킨 경우의 안정적 오류 변환 검사로 수정했다. Python recursion/timeout 설정을 변경하지 않았다. 기존 테스트/기대값은 수정하지 않았다.

### 상태·검증 기록

**IMPLEMENTED:** strict bytes loader·content-addressed ref 대조·C1/strict schema·raw20→21 검증·기존4개 모델 복원·original Acceptance correspondence·합성332개.

**NOT IMPLEMENTED:** 외부 파일 preparation·historical Snapshot/원문 content validator·Source Gate·검토자 진실성/권한 인증·Acceptance evaluator·same-call adapter·Benefit Bridge/Cashflow 연결. loader 성공은 bytes/구조/공급 record 대응이며 실제 내용 검토나 현재 수용 승인이 아니다.

사전 전체 **7,341 passed in 70.11s**, skip/fail0·timeout0. 신규332개 **passed in 1.39s**. 사후 전체 **7,673 passed in 68.49s / skipped0 / failed0 / timeout0**이다. 기존7,341개와 bootstrap106개·Review value273개를 모두 포함한다. M2.54 timeout2건은 재발하지 않았으며 bootstrap·테스트 timeout·Python recursion 설정을 수정하지 않았다.

보존 대조: 사전 backend/tests/data/docs/tools172개 중 기존169개 SHA256 동일, 변경3개는 package __init__.py·이 loader 명세·ARCHITECTURE.md다. 새 loader/테스트2개를 추가해 최종174개, 삭제0개다. 기존 tests/fixture/기대값·Review 모델4개/Acceptance/Context/Result·Benefit16/지문·Coverage freeze source/schema/GV01~GV15/BV01~BV16 literal·bootstrap·Cashflow·DATA_MODEL.md는 동일하다. 실제 release6개의 SHA256·경로·크기·수정시각도 모두 동일하다.

보조 검수: 구문·UTF-8·Markdown 표/fence, 승인 raw20/entry15 allowlist와15개 loader error prefix의 일치를 확인했다. 새 stored model·실제 production Review Artifact/Acceptance/혜택 금액·정책 지문·실행 ZIP은 생성하지 않았다. 이 검수와 수동64개는 신규 pytest 수에 포함하지 않는다.

최종 판단은 **STRICT_REVIEW_ARTIFACT_BYTES_LOADER_COMPLETE**다. 다음 가장 작은 작업은 **당시 BenefitSnapshot·Coverage snapshot·공식 근거와 Review Artifact를 대조하는 content validator 계약 설계 한 개**다. Source Gate/evaluator를 이번 단계에 포함하지 않는다. 기존21/16/9/4필드와 Review 모델4개·frozen Coverage·실제 releases·ResidenceHistory OFFICIAL_INQUIRY_REQUIRED를 유지한다.
