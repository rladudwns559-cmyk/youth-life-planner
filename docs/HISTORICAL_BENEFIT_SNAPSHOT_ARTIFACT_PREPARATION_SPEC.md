# M2.59 — Historical BenefitSnapshot Artifact Preparation Contract

최신 구현 상태는 **26절 M2.60**이다. 1~25절은 승인된 M2.59 설계·당시 검증 기록이며, 아래의 미구현/문서 전용 표기는 그 시점의 이력이다. 기존16필드/지문/오류 순서는 변경하지 않았다.

## 1. 목적과 이번 결정

`AcceptanceReviewEntry.accepted_terms_ref`가 고정한 **동일 raw bytes**를 검증·복원하여, 그 결과가 명시한 과거 `PolicyBenefitAcceptance`의 Benefit 정의와 provenance에 대응하도록 한다. 파일 SHA 검사와 별도 객체의 지문 검사가 각각 성공하는 것만으로 두 원본이 연결되지는 않는다는 M2.58의 공백 중 Benefit 한 경로를 닫는다.

**최종 판단: READY_TO_IMPLEMENT_HISTORICAL_BENEFIT_SNAPSHOT_LOADER.** 이는 아래 순수 loader 하나의 구현 준비 판단이다. 현재 구현 완료·전체 Content Validator 준비 완료·실제 역사 자료 확보를 뜻하지 않는다.

이번 변경은 이 문서 하나다. 기존 코드·모델·loader·테스트·동결 문서·실제 releases는 수정하지 않는다. 새 모델/Artifact index/범용 역사 복원 framework, 파일 읽기, Source Gate, Coverage/Review/Manifest 복원, evaluator/Bridge/Cashflow, 실제 안산 Snapshot/Acceptance/금액은 만들지 않는다.

## 2. Source of Truth와 현재 구현의 경계

| 확인 문서 | 적용 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md | L1/L2/L3, 동일 bytes 복원 공백, 당시 원본/현재 자료 분리, 11입력 후보와 미구현 경계 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md | Entry15/Root2, ACCEPTED 7참조와 REVOKED None, 원본 참조와 검토 기록 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC.md | 실제 M2.57 API, raw SHA/C1/strict parsing, 외부 Acceptance 원본 is 보존 |
| BENEFIT_SNAPSHOT_SPEC.md | 기존 16필드/4 Enum, definition payload15, BV01~BV16, 구조와 검토 분리 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md | 21필드, target/revision, Benefit 4binding과 공유 identity, 발급 기준 |
| BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md | Context4, 명시 ref 조회, REVOKED target A의 연결과 11binding |
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md | Coverage/Benefit 수용과 개인 지급·월 현금흐름 적용 분리 |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | A/C/B, 동일 호출, 역사 내용 검증과 현재 usability gate 분리 |
| POLICY_DATA_ENVELOPE_SPEC.md | 실제 ArtifactReference/SourceBinding/Registry/Manifest와 기존 parser의 책임 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | Generic Coverage 동결, FULL/SLICE 및 실제 정책 연결 blocker |
| DATA_MODEL.md / ARCHITECTURE.md | 구현된 값 타입·공개 함수와 미구현 orchestration 구분 |

직접 확인한 코드는 `benefit_snapshot.py`, `benefit_fingerprint.py`, `benefit_acceptance.py`, `benefit_acceptance_review_artifact.py`, `benefit_acceptance_review_artifact_loader.py`, `eligibility_coverage.py`, `envelope.py`, `manifest.py`, `sources/models.py` 및 기존 source/loader/validation 경계다. `PolicyDataError`는 기존 `EngineValidationError` 하위다.

| 현재 구현됨 | 아직 구현되지 않음 |
|---|---|
| BenefitSnapshot16와 4 Enum, 기존 지문 함수 | 이 문서의 Historical Benefit raw format을 읽는 loader |
| Scope2, SourceBinding2, ArtifactReference2 | 실제 accepted_terms 파일의 외부 확보·같은 호출 orchestration |
| Acceptance21, Context4, Evaluation9 값 타입 | Acceptance evaluator·Content Validator·Source Usage Gate |
| Review 모델4개와 M2.57 strict bytes loader | Coverage/ReviewContext/Manifest의 역사 strict bytes 복원 |
| SourceRegistry/Manifest 모델 및 기존 제한된 검증 함수 | 과거 공식 내용/검토 권한 인증·실제 정책 혜택 수용 |

일반 `to_dict()` 존재는 raw loader 존재를 뜻하지 않는다. 기존 진단 serializer의 의미는 변경하지 않는다. 이 문서에서 wrapper 안 `snapshot`에 한해 기존 16필드 표현을 새 외부 raw 계약으로 채택한다.

## 3. 기존 검증 공백과 닫는 연결

기존에는 파일 X의 SHA가 일치하고 공급 객체 Y의 Benefit 지문도 일치할 수 있다. Y를 X에서 실제 복원하지 않았다면 X와 Y의 대응을 보장하지 못한다. `artifact_verified=True` 같은 선언이나 Y에 hash 필드를 추가해도 이 연결은 생기지 않는다.

확정한 흐름은 다음과 같다.

```text
신뢰된 과거 Acceptance R 원본 + Review Artifact raw bytes
  → 실제 M2.57 loader → artifact의 entry.acceptance is R
  → 그 entry.accepted_terms_ref의 path/독립 sha256
  → 외부가 한 번 확보한 exact immutable bytes B
  → B의 SHA 비교 → 바로 같은 B를 strict decode/parse
  → 기존 constructor들로 BenefitSnapshot S 복원
  → S의 실제 정의 지문 + identity/version + dataset/Registry를 R과 대조
  → 그 S와 같은 B/ref/R/artifact를 같은 호출의 후속 검증에 전달
```

검증 직후 파일을 다시 읽어 복원하지 않는다. 이미 만들어진 Snapshot을 외부 인자로 받지 않는다. 성공 반환값은 함수가 해당 bytes에서 직접 만든 기존 Snapshot 하나다.

## 4. accepted_terms_ref와 실제 ArtifactReference

`ArtifactReference`는 `manifest.py`의 기존 frozen/slots dataclass이며 저장 필드는 정확히 두 개다.

| 필드 | 실제 타입·문법 | 의미 |
|---|---|---|
| path | exact str, 상대 slash 경로, 빈 segment/`.`/`..`/역슬래시/colon/control char/앞뒤 공백 거부 | 외부가 찾아야 할 명시 원본 위치 |
| sha256 | exact str, 소문자 `[0-9a-f]{64}` | 그 원본의 전체 raw bytes에 대한 독립 기대 SHA256 |

별도 version/source ID/content_hash 필드는 없다. 생성자는 파일 존재·내용·경로 resolve·공식성·검토를 확인하지 않는다. 문자열 `acceptance-review:sha256:H`인 Review Artifact root ref와 다른 타입이다. ArtifactReference 자체가 그 문자열 형식의 content-addressed ref인 것은 아니지만 기대 내용 hash를 직접 보유한다.

`accepted_terms_ref`는 **이 Entry의 과거 승인 정의를 보존한 Raw Benefit Artifact 위치와 bytes hash**다. 현재 Benefit, Benefit definition fingerprint, 공식 공고 원문, Coverage 원본의 ref가 아니다. `(path, sha256)` 참조 equality와 내용 SHA equality는 구별한다. 같은 bytes가 다른 path에 있을 수 있고 같은 path라도 bytes가 바뀌면 hash가 달라진다.

순수 함수는 bytes만으로 실제 어느 디스크 경로를 열었는지 증명할 수 없다. 명시 root 안 정확한 path에서 확보했다는 책임은 외부 준비 계층에 남는다. 두 ref가 동일 bytes를 공유하는 정상 재검토/독립 재승인은 허용하며 path가 다르다는 이유로 동일 정의를 다른 정의로 만들지 않는다.

## 5. 독립 기대 hash의 원천

**기존 Entry의 `accepted_terms_ref.sha256`을 선택한다.** 추가 Manifest entry/immutable index는 필요하지 않다. M2.57이 외부 R의 `review_artifact_ref`로 검증한 Review raw body 안의 참조이므로, trusted R → Review raw SHA → 선택 Entry → accepted terms SHA로 연결된다.

새로 읽은 Benefit bytes의 digest를 기대값으로 채택하지 않는다. loader는 공급 bytes의 actual digest를 계산해 이미 Entry에 고정된 기대값과 비교한다. 기록을 처음 준비할 때 원본 SHA를 계산하여 독립 검토 후 Review Artifact에 보존하는 것과, 소비 시 actual 값을 expected로 덮어쓰는 것은 다르다. 이번에는 실제 기록을 발급하지 않는다.

Benefit definition fingerprint는 decode 후 정의 내용의 별도 identity다. raw SHA와 교환하지 않으며 R.benefit_fingerprint를 raw SHA 대신 쓰지 않는다. SHA는 R 자체의 신뢰성·서명·검토 권한을 인증하지 않는다. trusted 원본 공급이라는 외부 가정은 22절에 명시한다.

## 6. Raw schema 후보 비교와 단일 선택

| 후보 | 장점 | 한계·결정 |
|---|---|---|
| A: 기존 to_dict의 exact16 root | 복제 없음, 가장 짧음, 기존 모델 복원 가능 | 외부 schema discriminator가 없어 동일 필드 이름의 미래 의미 변경을 명시 구분하기 어렵다. 미선택 |
| B: 최소 버전 wrapper + exact16 snapshot | 원래 16값/provenance 보존, 명시 형식 버전, 미래 schema를 즉시 거부, 구현 부담 작음 | root2 검사가 추가된다. **선택** |
| C: 기존 Benefit data loader format | 기존 확정 codec이 있다면 재사용 가능 | 현재 그런 codec은 없다. definition payload/진단 dict를 기존 loader로 오인하지 않는다. 미선택 |

선택 B의 root는 정확히 다음 두 key이며 둘 다 필수다.

| key | raw 타입·값 |
|---|---|
| schema_version | exact str literal `historical-benefit-snapshot-1.0` |
| snapshot | 아래 16필드의 exact JSON object |

이는 **새 파일 format의 버전**이며 `benefit_version`이나 `fingerprint_schema`와 다르다. wrapper key를 Snapshot에 저장하지 않는다. 1.0 이외 버전/미래 extra key/별칭을 거부한다. root16만, 지문용15key만, root에 acceptance/path/hash가 추가된 형식은 받지 않는다. 기존 실제 release의 파일 형식을 바꾸거나 자동 migration하지 않는다.

## 7. snapshot의 정확한 16필드

모든 필드가 필수다. nullable도 생략하지 않는다. 표 순서는 구조 검사/복원/오류 경로의 순서이며 raw object key 순서는 8절의 canonical 정렬을 따른다.

| 순서 | key | raw JSON 타입 | 기존 constructor에 전달할 값 |
|---|---|---|---|
| 1 | policy_id | string | 원문 exact str |
| 2 | scope | object, exact edition_id/quarter | 기존 ApplicabilityScope |
| 3 | benefit_id | string | 원문 exact str |
| 4 | benefit_version | string | 원문 exact str |
| 5 | amount_type | string | 기존 BenefitAmountType(value) |
| 6 | amount_krw | integer 또는 null | exact int 또는 None |
| 7 | amount_description | string 또는 null | exact str 또는 None |
| 8 | payment_cadence | string | 기존 BenefitPaymentCadence(value) |
| 9 | benefit_medium | string | 기존 BenefitMedium(value) |
| 10 | restriction | string | 기존 BenefitRestriction(value) |
| 11 | restriction_details | string 또는 null | exact str 또는 None |
| 12 | applicable_months | array[string] 또는 null | 원순서 tuple[str, ...] 또는 None |
| 13 | benefit_evidence_refs | array[string] | 원순서 tuple[str, ...] |
| 14 | source_bindings | array[object] | 원순서 tuple[기존 SourceBinding, ...] |
| 15 | dataset_version | string | 원문 exact str |
| 16 | source_registry_fingerprint | string | 원문 exact str |

scope는 정확히 `edition_id: string`, `quarter: integer|null`이다. null quarter는 **연간**이며 미확인 분기나 생략이 아니다. 각 binding은 정확히 `source_document_id: string`, `document_version: string`이다. scope_id/locator/status/date를 추가하지 않는다.

Snapshot에는 date/datetime 필드가 없다. scope edition은 ASCII4자리 문자열이고 기존 Scope는 `0000`도 구조상 허용한다. applicable_months는 기존 모델이 허용하는 `YYYY-MM`이며 year0000은 거부한다. 두 규칙을 임의 통일하거나 quarter에서 지급월을 추론하지 않는다. reviewed_at 등은 이미 R/M2.57의 계약이며 이 raw에 복제하지 않는다.

## 8. Canonical bytes 계약 HB1

HB1은 이 Historical raw 형식에 새로 명시하는 canonical 규약이다. M2.57 및 기존 지문의 JSON 철학을 재사용하되 payload/hash 영역은 별개다.

```python
json.dumps(
    raw_payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8", errors="strict")
```

- 모든 object key를 위 recipe로 정렬한다. compact separators이며 indent/추가 공백/최종 newline은 없다.
- exact UTF-8, BOM 없음, strict Unicode scalar 문자열이다. 한국어는 원래 문자로 직렬화한다. ASCII/제어문자 escape 등은 위 recipe 결과와 정확히 같아야 한다.
- Unicode NFC/NFD 정규화를 하지 않는다. 서로 다른 문자열은 원래 형태로 보존한다. 양쪽 surrogate escape가 올바른 scalar로 decode되는 것은 가능하지만 canonical bytes equality는 별도로 만족해야 한다. 홀로 남은 surrogate는 거부한다.
- null은 JSON null, Enum은 기존 Enum.value와 정확히 같은 대문자 문자열이다. bool은 int로 보지 않는다. 정수는 recipe의 10진 표현이다. `-0`처럼 decode 값은 같아도 재직렬화 bytes가 다른 표현은 거부한다.
- 배열 순서를 보존한다. 월/binding이 정렬되어야 하는지는 기존 모델 invariant이며 자동 정렬하지 않는다. evidence 중복은 Snapshot 계약대로 보존한다.
- 중복 object key는 어느 깊이든 거부한다. NaN/Infinity/float/exponent number는 거부한다. unknown schema/key를 조용히 무시하지 않는다.

입력 B의 SHA 검사가 먼저다. strict parse한 raw 전체를 위 recipe로 재인코딩한 결과와 **B 자체**를 비교한다. canonical 결과로 B를 교체한 뒤 hash를 검사하지 않는다. raw SHA는 wrapper와 provenance까지 포함한 B 전체에 적용하며, Benefit 지문은 기존15key projection에 적용한다. 두 digest의 같음/다름 자체를 유효성 조건으로 삼지 않는다.

## 9. Strict parsing과 자동 복구 금지

| 항목 | 확정한 처리·담당 |
|---|---|
| exact bytes | bytes subclass/bytearray/memoryview/str/file-like 거부. 외부에서 읽은 exact bytes 하나만 받음 |
| encoding | BOM을 명시 거부한 뒤 strict UTF-8 decode. invalid sequence 거부 |
| JSON syntax | json parser 사용, trailing garbage/malformed JSON 거부. 발생한 RecursionError도 JSON 오류로 분류 |
| duplicate keys | object_pairs_hook 계열 검사로 root/nested/같은 이름의 escape 표현까지 decode된 key 기준 중복 거부 |
| number | parse_constant와 parse_float 거부; parse_int의 ValueError도 number 오류. int 자릿수 전역 제한/recursion 설정을 변경하지 않음 |
| Unicode | parse 후 key와 value 모두 순회하여 U+D800~U+DFFF 잔류 scalar 거부 |
| shape | root2/snapshot16/scope2/binding2 exact key 집합. 누락 먼저, extra 다음. null은 명시 nullable 항목만 허용 |
| primitive | string/array/object/int를 exact 타입으로 검사. bool-as-int, 숫자/문자열 변환, null→기본값 금지 |
| canonical | raw payload 전체의 HB1 bytes equality. 공백/key순서/newline/escape 차이를 자동 교정하지 않음 |
| domain | 기존 Scope/Enum/SourceBinding/Snapshot constructor가 원문 값으로 검사. 새 semantic 검증을 중복 구현하지 않음 |

raw 문자열의 strip/대소문자 변환/alias/금액 반올림/월 생성/배열 sort/dedupe는 없다. `amount_description`·`restriction_details`·dataset_version은 기존 모델의 비공백 검사 외에 임의 정규화하지 않는다. 값이 맞지 않으면 해당 단계 오류이며 UNKNOWN/default Snapshot/부분 성공을 반환하지 않는다.

## 10. 동일 bytes 원칙과 외부 준비 책임

외부의 신뢰된 A/C가 실제 M2.57 반환 artifact와 R을 같은 호출에서 보존한다. artifact에서 R의 entry를 선택하고 accepted_terms_ref를 얻는다. 명시된 artifact root와 ref.path를 사용하여 원본을 **한 번** 읽고 immutable bytes B를 유지한다.

외부 준비의 호출 슬롯은 다음으로 한정한다. 새 실행 helper를 구현하거나 기존 파일 helper가 있다고 가정하지 않는다.

| 외부 경계 | 입력·출력·책임 |
|---|---|
| 입력 | 같은 호출의 실제 loader 반환 artifact, 신뢰된 R 원본, 명시 artifact root/원본 확보 수단 |
| 선택 | acceptance_ref exact 조회, entry.acceptance is R, root ref 일치, ACCEPTED 및 nonnull ref 확인. first/latest/현재 version 선택 없음 |
| 확보 | 정확한 ref.path의 파일, 명시 root containment/실제 resolve·symlink/junction 탈출 방지 등 I/O 책임. 파일/권한/보관본 미확보면 중단 |
| 공급 | 읽은 B 하나와 artifact/R을 18절의 순수 loader에 직접 전달. hash와 parse를 위한 이중 읽기 없음 |
| 보존 출력 | 기존 타입의 `(entry.accepted_terms_ref, B, returned_snapshot)` 대응을 로컬에 유지. artifact/R/entry도 같은 호출 원본으로 유지 |
| 후속 | 같은 S를 Content Validator의 historical_benefit에, 같은 ref/B를 historical_artifact_bytes의 해당 쌍에 공급. 다른 객체/새 파일 읽기로 교체하지 않음 |

이 tuple은 새 인증 DTO나 다른 요청에서 재사용할 token이 아니다. 외부 helper 이름/API 구현은 이번 범위 밖이다. 실제 파일이 없을 때 None/빈 bytes를 공급하거나 현재 Snapshot으로 대체하지 않는다. 실제 조회 오류는 외부 준비 실패이고 순수 loader의 Data Error와 별개다.

read 도중 불완전/변경된 bytes가 확보되면 expected SHA 불일치로 성공을 막는다. 외부가 실수로 다른 파일에서 읽었어도 내용이 완전히 같은 경우, bytes 함수는 디스크 출처를 판별하지 못한다. 정확한 path/open 수단은 외부 책임이며 성공을 경로 인증으로 확대하지 않는다.

## 11. 기존 BenefitSnapshot constructor로 복원

P4에서 검사한 raw snapshot만 사용한다. 기존 ApplicabilityScope 생성 → amount_type/payment_cadence/benefit_medium/restriction 순서로 기존 Enum 생성 → 원순서 SourceBinding 생성 → nullable/list를 명시 tuple/None으로 대응 → 기존 BenefitSnapshot에 16개 keyword를 모두 전달한다. 별도 HistoricalBenefitSnapshot은 만들지 않는다.

기존 constructor가 검사하는 규칙을 재사용한다.

- canonical ID, b0001 이상/d0001 이상 버전 문법, source ID의 유일·오름차순과 evidence source 집합의 정확한 대응.
- FIXED는 exact int≥0와 description=None, VARIABLE은 amount=None와 비공백 설명, UNKNOWN은 amount/description 모두 None. 0원 FIXED도 허용한다.
- RESTRICTED는 details 필수, UNRESTRICTED/UNKNOWN은 details=None. 두 명확한 cash medium/restriction 모순 거부.
- months는 None 또는 비어 있지 않은 유효 연월·유일·오름차순 tuple. ONE_TIME의 알려진 월은 하나.
- dataset 비공백, Registry 소문자 hex64. evidence ref 문법은 기존 parse_evidence_ref를 Snapshot이 사용한다.

Snapshot은 duplicate evidence를 보존한다. loader에서 validate_evidence_refs를 호출하여 중복/Registry 존재를 새로 강제하지 않는다. 후속 사용 단계의 기존 evidence validator/Registry 검증이 그 역할을 맡는다. Registry lookup·문서 ACTIVE/VERIFIED·공식 의미는 constructor 보장이 아니다.

구조적으로 유효한 VARIABLE/UNKNOWN도 복원·R의 구조적 binding 대조까지 성공할 수 있다. **이는 그 R의 실제 발급 적정성을 승인하는 성공이 아니다.** 기존 R constructor는 구조만 검사한다. M2.58 Content Validator의 역사 승인 완전성 검사에서는 VARIABLE/UNKNOWN·불완전 metadata를 발급 기준 모순으로 거부한다. 이 후속 gate를 생략하거나 loader 성공으로 우회하지 않는다.

## 12. Benefit definition fingerprint 재계산

복원 S에 기존 `fingerprint_benefit_snapshot(S)`를 그대로 호출한다. 새 지문 함수/일반 to_dict hash/inline projection 대체는 없다.

기존 payload는 **15key**다. 저장16에서 dataset_version/source_registry_fingerprint를 빼고 `fingerprint_schema="benefit-snapshot-1.0"`을 넣는다. Scope/Enum/배열/근거·관련 SourceBinding의 원값과 순서·중복/null을 유지하며, canonical JSON/strict UTF-8/SHA256으로 계산한다. BV01~BV16을 바꾸지 않는다.

P6에서 지문을 계산하고, P7의 identity 검사 후 그 실제 지문을 R.benefit_fingerprint와 비교한다. definition에 포함된 identity가 틀릴 때 identity 오류를 먼저 보고하기 위한 순서다. raw의 임의 `fingerprint` 필드를 믿거나 R의 지문을 실제 계산 결과로 채택하지 않는다.

## 13. 당시 Acceptance identity와 version 대응

R은 신뢰된 외부 원본이다. M2.57이 raw Acceptance20값과 대조한 뒤 최종 entry.acceptance에 **그 원본 객체**를 넣었다. acceptance_ref/acceptance_version/status/review 날짜/Coverage binding은 그 연결에 포함되며, Historical raw에서 다시 복제하거나 재발급하지 않는다. a revision과 b version은 서로 추론하지 않는다.

| 독립 축 | 순수 loader가 실제 비교하는 값 |
|---|---|
| policy identity | S.policy_id == R.policy_id |
| scope | S.scope == R.scope (edition/quarter exact; annual≠Q3) |
| benefit identity | S.benefit_id == R.benefit_id |
| benefit version | S.benefit_version == R.benefit_version |
| definition | fingerprint_benefit_snapshot(S) == R.benefit_fingerprint |
| dataset | S.dataset_version == R.benefit_dataset_version |
| Registry | S.source_registry_fingerprint == R.benefit_source_registry_fingerprint |

같은 b version의 다른 정의 지문은 모순 오류다. R이 b0001인데 과거 원본으로 b0002를 공급한 것도 원본 대응 오류다. 현재 자료가 별도로 b0002가 된 것은 정상 변경일 수 있으나 이 함수의 입력/평가 대상이 아니다. historical b0001 복원 후 현재 b0002의 USABLE을 선언하지 않는다.

## 14. dataset/Registry provenance 대조의 한계

definition 지문이 같아도 dataset이 다르면 DATASET_MISMATCH, Registry만 다르면 REGISTRY_MISMATCH다. 이 두 값은 raw16에 실제로 포함되고 raw SHA로 고정되지만 definition 지문에서는 제외되므로 별도 비교를 생략할 수 없다.

이 함수는 R의 Benefit provenance와의 **값 대응**을 확인한다. 실제 당시 Manifest.dataset_version 및 실제 SourceRegistry의 `fingerprint_source_registry`와도 같다는 검사는 후속 Content Validator 책임이다. Registry/Manifest를 이 최소 API에 추가하지 않는다. string equality를 실제 Registry 복원/검증이라고 보고하지 않는다.

R constructor가 Coverage/Benefit의 같은 dataset/Registry를 이미 검사한다. 이를 새 규칙으로 중복 구현하지 않는다. 전체 Manifest 검증·ENGINE_VERSION 호환/역사 실행 환경·공식 source bytes와 문서 d version·locator 검증은 이 loader로 닫히지 않는다.

## 15. ReviewEntry와 same-call 결합

외부에 임의 `expected_artifact_ref`만 받는 3인자 예시를 그대로 택하면, R1과 Entry2의 참조를 잘못 조립할 수 있다. **artifact/R/bytes의 3인자 API**를 선택해 loader가 root에서 대상 entry를 직접 찾고 ref를 내부에서 추출한다. caller가 다른 Entry의 ref를 별도 인자로 바꾸는 슬롯이 없다.

P1에서 root.review_artifact_ref == R.review_artifact_ref를 검사한다. R.acceptance_ref exact equality로 유일 entry를 조회하고 entry.acceptance **is R**를 검사한다. 값이 같은 record 복사본도 같은 호출 원본으로 인정하지 않는다. lookup은 latest 선택이나 Context resolution이 아니다. 이 결합 뒤에만 selected entry.accepted_terms_ref.sha256을 사용한다.

외부는 10절에서 미리 선택한 바로 그 root/R 관계로 파일을 읽고, 순수 loader는 같은 불변 root/R에서 다시 유일 entry를 선택한다. 다른 Entry bytes를 읽었다면 expected SHA 또는 정의/identity 대응이 실패한다. 두 Entry가 정확히 같은 ref/bytes/정의를 공유하고 R에도 정확히 대응한다면 정상 공유이며 인위적으로 거부하지 않는다.

타입·is·ref 검사만으로 artifact가 실제 M2.57을 통과했다는 사실을 인증하지 못한다. 직접 만든 Artifact도 구조상 생성 가능하다. 따라서 **신뢰된 A/C가 같은 호출에서 실제 M2.57을 호출하고 반환값을 그대로 전달**하는 입력 계약이 필수다. prevalidated 객체/성공 bool을 받는 public orchestration 우회 경로는 허용하지 않는다. 같은 process의 악의적 강제 조작을 방어하는 보안 경계라고 주장하지 않는다.

## 16. ACCEPTED와 REVOKED

이 함수의 expected_acceptance는 **ACCEPTED**만 허용한다. 기존 Entry가 accepted_terms_ref를 실제로 갖는다. REVOKED를 공급하면 P1에서 subject 오류이며 현재 Benefit/target 원본을 임의로 붙이지 않는다.

기존 REVOKED Entry의 7참조는 모두 None, claim/source 목록은 빈 tuple이다. 이를 수정하지 않는다. 철회 B의 대상 A 원본이 필요하다면 기존 검증된 Context/resolver로 A를 명시 확보하고, A를 포함한 실제 loader 반환 Artifact와 A의 accepted_terms_ref로 이 함수를 **별도 A 대상**으로 호출하는 방향을 유지한다.

B의 ref 대신 A를 자동 선택하거나 B를 A로 반환하지 않는다. Context edge/11binding/철회 효과·기한/current gate의 구현은 이번 범위 밖이다. 역사 A 복원으로 B의 철회가 취소되거나 A가 현재 usable해지지 않는다.

## 17. External Preparation과 Pure Loader 경계

| 역할 | 맡는 일 | 맡지 않는 일 |
|---|---|---|
| 외부 trusted A/C | 원본 R/전체 Review expected records 확보, 실제 M2.57 실행, 정확한 file path/bytes 확보, 동일 호출 원본 보존 | actual hash를 expected로 덮어쓰기, 현재 Benefit 대체, 준비 미완료를 성공 취급 |
| 이번 후속 pure loader | root/R 연결, 내부 ref 선택, 같은 bytes SHA/strict parse/HB1, 기존16필드 복원, 실제 지문 및 R binding | filesystem/network/Git/current time/env, 사람 검토, source 조회, 현재 평가 |
| 향후 Content Validator | 동일 S/ref/B와 나머지 당시 원본의 L1/L2 비교·발급 정의 완전성·claim 대응 | loader 성공을 L3/현재 USABLE로 승격 |
| 외부 Source/L3/역사 검증 책임 | 공식 원문 내용·검토 권한/독립성·사용요건·필요한 당시 실행 환경 | hash/evidence metadata만으로 의미 인증 |

순수 함수는 전역 mutable cache나 다른 호출의 검증 결과를 사용하지 않는다. 입력을 수정하지 않고 새 Snapshot만 반환한다. same-call tuple/None 성공/모델에 새 상태를 추가하지 않는다.

## 18. 확정한 후속 pure API

아래 함수는 **아직 없다**. 다음 승인 후 이 한 함수만 구현하는 계약이다.

```python
load_historical_benefit_snapshot_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> BenefitSnapshot
```

필수 keyword-only3개, 기본값/optional 인자 없음. 후속 모듈 후보는 `backend/policy_engine/policy_data/historical_benefit_snapshot_loader.py`다. 현재 public export를 변경하지 않는다. 기존 M2.57 명명/호출 패턴을 따른다.

| 입력 | 독립 기대값·원본성 | 이 함수가 검사하는 것 | 검사하지 못하는 가정 |
|---|---|---|---|
| raw_bytes | 실제 확보한 bytes이며 기대값 자체는 아님 | exact bytes, 내부 ref의 독립 SHA, 동일 bytes의 strict 복원 | 실제 열린 path/보관소·I/O 획득 방식 |
| artifact | 같은 호출의 M2.57 실제 반환값. 그 내부 ref가 독립 기대 SHA 원천 | exact 타입, root ref/entry 조회/is/ref binding | 직접 만든 구조 객체가 실제 loader 반환인지 타입만으로 증명 불가 |
| expected_acceptance | 같은 호출의 신뢰된 R 원본, raw와 별도 확보 | exact 타입, ACCEPTED, root/entry 원본성, definition/identity/provenance 대응 | 실제 발급 권한·누락 없는 이력·원문 진실성 |

다른 Entry/ArtifactReference/expected digest/완성된 Snapshot/현재 Benefit/verified flag/시간/Registry/Manifest/Context를 별도로 받지 않는다. 선택 ref는 내부 entry에서만 얻는다. 성공은 그 ref의 bytes에서 복원해 R과 대조한 기존 BenefitSnapshot이며 `artifact_verified/accepted/reviewed/is_complete/current_usable/raw_file_path/loaded_from_hash`를 저장하지 않는다.

## 19. 오류 prefix와 검증 우선순위

모든 아래 신규 오류는 기존 PolicyDataError와 고정 prefix/안전한 field 경로로 표현한다. 새 예외 계층은 없다. raw payload·actual/expected 값·원문·사용자 데이터·실제 path/ref 내용을 오류에 출력하지 않는다. 잘못된 Python 호출 문법/인자 누락은 일반 TypeError이며 loader 내부 malformed value와 구별한다.

| phase | 고정 prefix | 조건 |
|---|---|---|
| P0 | INVALID_HISTORICAL_BENEFIT_LOADER_INPUT | raw_bytes/artifact/expected_acceptance exact 타입 위반 |
| P1 | HISTORICAL_BENEFIT_REVIEW_BINDING_MISMATCH | REVOKED subject, root ref 불일치, entry 부재/유일성 또는 is 불일치 |
| P1 | INVALID_HISTORICAL_BENEFIT_EXPECTED_REF | selected accepted_terms_ref 없음/타입 위반, 기대 무결성 binding 부재 |
| P2 | HISTORICAL_BENEFIT_BYTES_MISMATCH | supplied B 전체 SHA != selected ref.sha256 |
| P3 | INVALID_HISTORICAL_BENEFIT_ENCODING | BOM/invalid UTF-8 |
| P3 | INVALID_HISTORICAL_BENEFIT_JSON | JSONDecodeError/발생한 RecursionError |
| P3 | DUPLICATE_HISTORICAL_BENEFIT_JSON_KEY | 어느 깊이든 decoded object key 중복 |
| P3 | INVALID_HISTORICAL_BENEFIT_NUMBER | float/exponent/NaN/Infinity, parse_int ValueError |
| P3 | INVALID_HISTORICAL_BENEFIT_UNICODE | parse 결과의 고립 surrogate |
| P4 | INVALID_HISTORICAL_BENEFIT_FIELDS | 필수 key 누락 또는 extra key |
| P4 | INVALID_HISTORICAL_BENEFIT_SCHEMA | 지원하지 않는 schema_version literal |
| P4 | INVALID_HISTORICAL_BENEFIT_TYPE | object/list/str/int/nullable raw 타입 위반, bool-as-int |
| P4 | NONCANONICAL_HISTORICAL_BENEFIT_BYTES | strict raw payload의 HB1 재인코딩 bytes와 B 불일치 |
| P5 | INVALID_HISTORICAL_BENEFIT_VALUE | 기존 Enum의 ValueError |
| P5 | INVALID_HISTORICAL_BENEFIT_MODEL | 기존 Scope/SourceBinding/Snapshot constructor의 PolicyDataError |
| P6 | INVALID_HISTORICAL_BENEFIT_FINGERPRINT | 기존 지문 함수가 던진 PolicyDataError. 정상 strict 복원 입력에서는 보통 도달하지 않는 방어 경계 |
| P7a | HISTORICAL_BENEFIT_IDENTITY_MISMATCH | policy_id/scope/benefit_id/benefit_version 중 첫 불일치 |
| P7b | HISTORICAL_BENEFIT_FINGERPRINT_MISMATCH | 실제 계산 definition fp와 R 불일치 |
| P7c | HISTORICAL_BENEFIT_DATASET_MISMATCH | dataset 불일치 |
| P7d | HISTORICAL_BENEFIT_REGISTRY_MISMATCH | Registry fp 불일치 |
| P8 | 오류 없음 | 기존 BenefitSnapshot만 반환 |

총20개 prefix다. 기존 strict Review loader15개 prefix/기존 Acceptance12reason을 변경하지 않는다. constructor 호출만 좁게 PolicyDataError를 잡아 MODEL로 대응하고, Enum ValueError는 VALUE로 구별한다. 오류 메시지에 constructor 원문 예외 값을 붙이지 않는다. 예상하지 못한 모든 Exception을 데이터 오류로 덮는 포괄 catch는 하지 않는다.

정확한 실행 순서는 다음과 같다.

1. **P0:** raw_bytes → artifact → expected_acceptance exact 타입.
2. **P1:** R.status ACCEPTED → root ref 일치 → acceptance_ref 유일 entry 조회 → entry.acceptance is R → accepted_terms_ref exact 타입/nonnull. 기존 생성 완료 객체의 내부 invariant는 재구축하지 않는다. 정상 exact ArtifactReference의 hash/path 문법은 이미 생성자가 검사했다. 강제 object 조작 방어를 위해 기존 모델을 변경하지 않는다.
3. **P2:** 같은 B 전체 SHA 비교. decode/parse 전에 실패한다.
4. **P3:** BOM → strict UTF-8 → JSON parser → Unicode scalar 검사. parser 중 duplicate/number/syntax의 복합 오류는 문서 순회 중 실제 먼저 발견한 사건을 보고한다. 뒤의 오류를 찾기 위해 손상 JSON을 계속 해석하지 않는다.
5. **P4:** root object/key 집합 → schema_version 타입/literal → snapshot object/key 집합 → 표7 필드 순 raw 타입/중첩 shape → HB1 equality. 각 object는 기대 key 순 누락을 먼저 찾고 그 다음 extra를 보고한다. 배열은 원순서다. 중첩 scope/binding도 그 위치에서 같은 규칙이다.
6. **P5:** Scope → amount/cadence/medium/restriction Enum 순 → bindings 원순서 → Snapshot. 필드 의미/invariant 우선순위는 기존 constructor 그대로다.
7. **P6:** 기존 함수로 actual definition fp 계산.
8. **P7:** identity4축을 표13 순서로 검사 → actual fp → dataset → Registry. 같은 b version/다른 내용과 다른 b version을 구별해 보고한다.
9. **P8:** 전체 성공 때만 S 반환. 상태/부분 결과/기본 Snapshot 없음.

P4의 schema/key/type 위반은 canonical 오류보다 먼저다. model invariant 위반은 HB1 equality 뒤다. 예를 들어 잘못된 Enum과 추가 공백이 함께 있으면 canonical 오류이며, 잘못된 Enum의 canonical bytes는 VALUE 오류다. hash까지 틀리면 모두 P2가 먼저다.

자료 미확보·reader 미구현·file permission/보관소 문제는 외부 준비 실패다. 공급된 자료의 hash/정의/provenance 모순은 Data Error다. 둘 다 정상 STALE/UNUSABLE/UNKNOWN이나 BENEFIT_METADATA_NOT_REVIEWED로 강등하지 않는다. current version 변경 판단은 후속 evaluator의 별도 책임이다.

## 20. 합성 테스트 설계 — HB01~HB72

아래 **72개는 문서 사례**이며 이번 신규 실행 테스트는 **0개**다. 향후 loader 구현 테스트의 입력/기대 결과를 정의한다. 실제 정책/금액/지문/원본 발급은 없다.

공통 독립 기대값 약어: **E**=외부 신뢰된 합성 R 원본과 그것으로 실제 M2.57이 복원한 root/entry의 고정 accepted_terms_ref. **H**=그 ref.sha256, **D**=R의 실제 기대 정의 지문, **I**=R의 identity/version, **P**=R의 dataset/Registry. 정상 합성 fixture의 bytes와 H/D literal은 검토 후 고정하며, 검증 대상 actual digest를 기대값으로 즉석 채택해 통과시켰다고 보고하지 않는다.

malformed parse/schema fixture는 해당 손상 bytes 자체가 명시 ref에 고정된 경우를 별도로 구성해 P2를 통과시킨 뒤 해당 오류를 검사한다. 깨끗한 원본 H를 그대로 유지한 byte mutation은 P2 실패를 검사한다. 형식 오류 테스트의 hash 준비와 신뢰된 실제 기록 소비 절차를 혼동하지 않는다. 전체 API 테스트는 실제 M2.57 반환 root/R을 사용하고, unreachable defensive 입력만 명시된 격리 단위 검사로 구별한다.

| ID | 입력/변경 | 예상 결과 | phase | 필요한 독립 기대값 | 후속 실행 테스트 |
|---|---|---|---|---|---|
| HB01 | wrapper2/snapshot16, 올바른 원본 | Snapshot16 반환 | P8 | E/H/D/I/P | 가능 |
| HB02 | matching path/H의 고정 원본 | 전체 raw SHA 대응 | P2→P8 | E/H/D/I/P | 가능, path 자체는 외부 |
| HB03 | FIXED 0원/description null | 정상 구조·binding 성공 | P8 | E/H/D/I/P | 가능 |
| HB04 | VARIABLE/한국어 description | 복원·binding 성공, 승인 적정성 아님 | P8 | E/H/D/I/P | 가능, CV는 별도 거부 |
| HB05 | UNKNOWN amount/description null | 복원·binding 성공, 승인 적정성 아님 | P8 | E/H/D/I/P | 가능, CV는 별도 거부 |
| HB06 | 여러 evidence refs/관련 bindings | 순서 그대로 반환 | P8 | E/H/D/I/P | 가능 |
| HB07 | applicable_months null | None 유지, 월 추론 없음 | P8 | E/H/D/I/P | 가능, 완전성 CV 별도 |
| HB08 | 명시 정렬 월 array | exact tuple 복원 | P8 | E/H/D/I/P | 가능 |
| HB09 | 같은 입력100회 | 값/지문/출력 결정적, 입력 불변 | P8 | 고정 E/H/D/I/P | 가능, 100회는 사례1개 |
| HB10 | duplicate evidence 원순서 | 중복 유지, loader 성공 | P8 | E/H/D/I/P | 가능, 사용 gate 별도 |
| HB11 | 서로 다른 NFC/NFD 문자열 | 정규화 없이 각각 보존 | P8 | 각 E/H/D/I/P | 가능 |
| HB12 | QUARTERLY/LOCAL_CURRENCY와 유효 제한 | 복원 성공, 월 현금 변환 없음 | P8 | E/H/D/I/P | 가능 |
| HB13 | 한 byte 변경, H 유지 | BYTES_MISMATCH | P2 | 원본 E/H | 가능 |
| HB14 | 같은 파일명에 다른 bytes | BYTES_MISMATCH | P2 | 원본 E/H | loader+외부 reader 경계 가능 |
| HB15 | canonical bytes이나 expected H 다름 | BYTES_MISMATCH | P2 | 독립 다른 H/E | 가능 |
| HB16 | 추가 공백, 그 bytes로 고정된 H | NONCANONICAL | P4 | 손상 bytes 고정 E/H | 가능 |
| HB17 | object key 순서만 다름, H 대응 | NONCANONICAL | P4 | 손상 bytes 고정 E/H | 가능 |
| HB18 | 최종 newline, H 대응 | NONCANONICAL | P4 | 손상 bytes 고정 E/H | 가능 |
| HB19 | invalid UTF-8, H 대응 | ENCODING | P3 | 손상 bytes 고정 E/H | 가능 |
| HB20 | BOM, H 대응 | ENCODING | P3 | 손상 bytes 고정 E/H | 가능 |
| HB21 | root duplicate key | DUPLICATE_JSON_KEY | P3 | 손상 bytes 고정 E/H | 가능 |
| HB22 | scope/binding 내부 duplicate key | DUPLICATE_JSON_KEY | P3 | 손상 bytes 고정 E/H | 가능, 깊이별 매개화 |
| HB23 | malformed JSON/trailing garbage | JSON | P3 | 손상 bytes 고정 E/H | 가능 |
| HB24 | NaN/Infinity/-Infinity | NUMBER | P3 | 손상 bytes 고정 E/H | 가능, token별 매개화 |
| HB25 | 고립 surrogate escape | UNICODE | P3 | 손상 bytes 고정 E/H | 가능 |
| HB26 | 한국어를 불필요한 \u escape로 표현 | NONCANONICAL | P4 | 비정규 bytes 고정 E/H | 가능 |
| HB27 | amount -0의 비정규 표현 | NONCANONICAL | P4 | 비정규 bytes 고정 E/H | 가능 |
| HB28 | parser RecursionError/정수 제한 ValueError | JSON/NUMBER로 대응, 전역 설정 불변 | P3 | E/H 및 격리 parser 실패 | 가능, 깊이 임계값 고정 안 함 |
| HB29 | 16필드 중 하나 누락 | FIELDS, absent≠null | P4 | 손상 bytes 고정 E/H | 가능,16필드 매개화 |
| HB30 | snapshot extra field | FIELDS | P4 | 손상 bytes 고정 E/H | 가능 |
| HB31 | wrapper 없음/root16만 | FIELDS | P4 | 손상 bytes 고정 E/H | 가능 |
| HB32 | schema_version 다른 literal | SCHEMA | P4 | 손상 bytes 고정 E/H | 가능 |
| HB33 | root/snapshot object 대신 list/null | TYPE | P4 | 손상 bytes 고정 E/H | 가능 |
| HB34 | 4 Enum 중 잘못된 문자열 | VALUE | P5 | canonical 손상 bytes 고정 E/H | 가능,4종 매개화 |
| HB35 | amount true | TYPE, bool-int 금지 | P4 | 손상 bytes 고정 E/H | 가능 |
| HB36 | amount 1.0/1e3 | NUMBER | P3 | 손상 bytes 고정 E/H | 가능 |
| HB37 | amount 음수 | MODEL | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB38 | SourceBinding key 누락/extra | FIELDS | P4 | 손상 bytes 고정 E/H | 가능 |
| HB39 | binding ID/d0000/잘못된 version | MODEL | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB40 | malformed evidence ref | MODEL, 기존 문법 재사용 | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB41 | months 역순/중복 | MODEL, 자동 sort/dedupe 없음 | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB42 | 잘못된 month/0000-01/빈 array | MODEL | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB43 | quarter bool/문자열 | TYPE | P4 | 손상 bytes 고정 E/H | 가능 |
| HB44 | quarter 범위 밖/edition malformed | MODEL | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB45 | scope edition0000 + annual | 기존 Scope 규칙상 허용 | P8 | 이에 맞는 E/H/D/I/P | 가능, 실제 연도 승인 아님 |
| HB46 | b0000/잘못된 b version | MODEL | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB47 | FIXED null/VARIABLE 금액 있음/UNKNOWN 설명 있음 | MODEL, 기존 조합 invariant | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB48 | RESTRICTED details 없음/현금 medium 모순 | MODEL | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB49 | binding 역순/중복/evidence source 집합 다름 | MODEL | P5 | canonical 손상 bytes 고정 E/H | 가능 |
| HB50 | 잘못된 dataset/Registry primitive·문법 | TYPE 또는 MODEL | P4/P5 | 손상 bytes 고정 E/H | 가능, primitive별 분리 |
| HB51 | 원본 policy_id만 R과 다름 | IDENTITY_MISMATCH | P7a | E/H, R의 I | 가능 |
| HB52 | 원본 benefit_id만 R과 다름 | IDENTITY_MISMATCH | P7a | E/H, R의 I | 가능 |
| HB53 | Q3 원본과 annual R | IDENTITY_MISMATCH | P7a | E/H, R의 I | 가능 |
| HB54 | R b0001, 원본 b0002 | IDENTITY_MISMATCH, stale 아님 | P7a | E/H, R의 I | 가능 |
| HB55 | 같은 b version 다른 definition | FINGERPRINT_MISMATCH | P7b | E/H, R의 고정 D/I | 가능 |
| HB56 | 정의 지문 동일 + dataset만 변경 | DATASET_MISMATCH | P7c | E/H/D/I, R의 P | 가능 |
| HB57 | Registry-only 변경 | REGISTRY_MISMATCH | P7d | E/H/D/I, R의 P | 가능 |
| HB58 | 다른 Entry2 bytes를 R1용으로 공급 | R1 ref의 SHA 불일치 | P2 | R1의 E/H | 가능, 서로 다른 고정 bytes |
| HB59 | 올바른 원본이나 다른 R 대상 | identity 또는 fp/provenance 첫 불일치 | P7 | 다른 R의 E/H/D/I/P | 가능, H는 같은 원본으로 고정 |
| HB60 | root ref 다름/entry 부재 | REVIEW_BINDING_MISMATCH | P1 | R 원본, 다른 root | 가능 |
| HB61 | 값 같은 R 복사본 공급 | REVIEW_BINDING_MISMATCH, is 실패 | P1 | M2.57에 공급했던 원본 R | 가능 |
| HB62 | selected accepted_terms_ref None/잘못된 타입 | INVALID_EXPECTED_REF | P1 | E의 격리 비정상 상태 | 정상 constructor로 불가, 방어 단위 검사 |
| HB63 | REVOKED B 공급 | REVIEW_BINDING_MISMATCH | P1 | 실제 M2.57 B/root | 가능, 가짜 ref 붙이지 않음 |
| HB64 | 정확한 과거 b0001, 현재 b0002 별도 | 역사 복원 성공, 현재 평가는 안 함 | P8/외부 | E/H/D/I/P와 별도 current | 가능, evaluator 미구현 경계 |
| HB65 | bytearray/bytes subclass/잘못된 root/R 타입 | LOADER_INPUT | P0 | 나머지 정상 E | 가능, 타입별 매개화 |
| HB66 | hash·JSON 모두 잘못됨 | BYTES_MISMATCH 우선 | P2 | 원본 E/H | 가능 |
| HB67 | Enum 잘못됨 + 추가 공백, H 대응 | NONCANONICAL 우선 | P4 | 손상 bytes 고정 E/H | 가능 |
| HB68 | identity/fp/dataset/Registry 동시 불일치 | identity 먼저, 이후 fp→dataset→Registry | P7 | E/H, 독립 R binding | 가능, 단계별 수정 비교 |
| HB69 | 서로 다른 Entry가 같은 ref/정의 공유 | 각 R 원본 binding 맞으면 정상 | P8 | 두 R을 실제 결합한 E/H/D/I/P | 가능, 공유 허용 |
| HB70 | 구조·SHA·fp 대응이나 공식 원문 미검토 | loader 성공 가능, L3/사람 검토/지급 승인 아님 | P8/외부 | E/H/D/I/P, 외부 검토 부재 | 기계 경계 가능, 진실성 실증 불가 |
| HB71 | 역사 복원 성공, current USABLE/Bridge 미확인 | 성공을 current/Bridge/Cashflow로 확대 안 함 | P8/후속 | E/H/D/I/P, 별도 current gate | 경계 가능, 실제 후속 기능 아님 |
| HB72 | 과거 파일 미확보/다른 path에서 동일 bytes | 미확보면 외부 중단, path 출처는 loader 인증 불가 | 외부/P8 | E/H 및 명시 root/path | 외부 모의 경계 가능 |

위 표의 축약 오류명은 19절의 exact prefix suffix를 가리킨다. `MODEL`은 기존 constructor invariant 실패이고 `TYPE`은 raw primitive/shape 실패다. compound 사례의 세부 매개화는 향후 테스트 개수이며 지금 72개를 실행했다고 세지 않는다.

## 21. 신뢰 한계와 Content Validator 사용 경계

이 loader의 성공은 **선택 Entry에 고정된 bytes → 같은 bytes의 구조적 Snapshot → R의 정의/identity/provenance**라는 연결만 뜻한다.

- 구조 유효성은 공식 내용의 진실성이 아니다. hash 일치는 실제 사람 검토·권한·독립성의 증명이 아니다.
- 정의 fp 일치는 지급 승인·개인 정책 자격·수급 확정이 아니다. 동일 지문의 다른 provenance도 자동 허용하지 않는다.
- 당시 Snapshot 복원은 FULL_POLICY/VERIFIED/current Acceptance USABLE/Bridge 지원/현금흐름 반영을 뜻하지 않는다.
- 후속 Content Validator는 이 반환 S와 같은 ref/B/R/artifact를 사용하고 나머지 역사 원본/실제 Registry/Manifest/claim 대응을 검사해야 한다. VARIABLE/UNKNOWN 등 역사 발급 기준 모순도 그곳에서 차단한다.
- 현재 B evaluator/8입력 계약, Generic Coverage freeze, 실제 안산 DRAFT/CONDITION_SLICE·혜택 반영0원 원칙을 바꾸지 않는다. LLM은 이 검증을 판정하거나 값을 생성하지 않는다.

M2.58의 전체 Content Validator 11입력 후보/API/None 의미는 그대로다. 이번 결론을 그 전체의 READY 또는 구현 완료로 확대하지 않는다. 나머지 역사 codec/L3/Source/당시 환경 책임이 남는다.

## 22. Assumptions와 미해결 사항

| 항목 | 명시 가정/경계 |
|---|---|
| A1 | 신뢰된 외부가 R과 전체 expected Acceptance 원본을 정확히 확보하며 실제 M2.57을 같은 호출에서 실행한다. 타입/is만으로 발급 진실성은 증명하지 못함 |
| A2 | ref.path가 명시 root의 보관본으로 resolve되고 독립 H가 고정된 원본이 확보된다. 파일 I/O/운영 archive는 미구현 |
| A3 | 사람이 공식 원문 내용·검토 권한/독립성·Source 요건을 별도로 확인한다. loader는 그 성공을 가정해 선언하지 않음 |
| 제한된 준비 완료 | 필요한 독립 H와 raw schema/HB1/복원/binding/API는 이 문서에서 모두 확정. 순수 loader 설계의 추가 blocker 없음 |
| 남은 후속 작업 | loader 구현·실행 합성 검증, 외부 file preparation/orchestration, Coverage/Review/Manifest 역사 codec·실제 Registry/공식 source 대조, 전체 Content Validator/Source Gate/evaluator |
| 역사 환경 | 과거 engine version/FULL 실행 대응은 별도. 현행 Manifest validator의 ENGINE_VERSION 비교를 삭제해 역사 검증을 우회하지 않음 |
| 실제 자료 | 실제 accepted_terms 파일/Acceptance/금액을 확보·발급했다고 주장하지 않음. 파일이 없으면 외부 준비 실패로 중단 |

이는 무결성 기대값 공백을 새 필드/verified bool로 덮는 가정이 아니다. 독립 기대값은 이미 기존 모델에 있다. 실제 자료 공급·신뢰·운영 책임과 문법/복원 규약의 미확정을 구분한다. canonical recipe는 기존 Python JSON recipe이며 범용 RFC canonicalization/다른 언어 직렬화 표준을 도입하지 않는다.

## 23. 최종 판단

**READY_TO_IMPLEMENT_HISTORICAL_BENEFIT_SNAPSHOT_LOADER**

기존 ArtifactReference의 실제 path/sha256을 재사용해 독립 무결성 기대값을 확보했다. 버전 wrapper2+snapshot16/HB1/strict parsing/기존 constructor/기존 지문/7축 binding/ReviewEntry same-call·오류 우선순위를 확정했다. Snapshot16·definition15·Acceptance21·Review 모델/loader·동결 core와 충돌하지 않는다.

준비 완료 대상은 18절 순수 loader 하나다. 전체 역사 자료 준비/Content Validator/Source Gate/정책 지급의 완료 판단은 아니다.

## 24. 다음 최소 작업 하나

승인 후 **M2.60 — Historical BenefitSnapshot Strict Bytes Loader 구현**만 진행한다. 18절 API와19절 검증 순서로 새 loader 하나 및 합성 실행 테스트를 만들고 HB01~HB72 중 해당 순수/경계 사례를 검증한다. 기존 constructor/지문/값 타입/Review loader/freeze/실제 releases는 보존한다.

파일 읽기·범용 store·Coverage/Review/Manifest 복원·Content Validator·evaluator·Source Gate·Bridge/Cashflow·실제 정책 자료는 이 다음 한 작업에 포함하지 않는다. 이번 M2.59에서는 그 구현을 시작하지 않는다.

## 25. 검증·보존 기록

- 작업 전 전체 pytest: **7,673 passed in 62.51s / skipped0 / failed0 / timeout0**.
- 신규 실행 테스트: **0개**. HB01~HB72는 문서 사례72개이며 실행 테스트 수에 더하지 않는다.
- 작업 후 전체 pytest: **7,673 passed in 61.76s / skipped0 / failed0 / timeout0**. 전후 모두 timeout 재발이 없으며 테스트/timeout/환경 격리 설정·bootstrap 코드는 변경하지 않았다.
- 사전 backend/tests/data/docs/tools의 기존175개 파일(실제 releases·pycache 별도)은 SHA256이 모두 동일하다. 새 문서1개만 추가하여 최종176개이며 기존 파일 수정/삭제0개다. 기존 테스트/fixture/기대값·동결 문서·모델·loader·지문·Cashflow를 보존했다.
- GV01~GV15/BV01~BV16 literal/계산 코드를 변경하지 않았고 전후 전체 테스트가 통과했다. 문서의 정상/오류 사례를 실행 검증 실적으로 세지 않는다.
- 실제 release6개는 SHA256·경로·크기·수정시각이 모두 동일하다. 아래 SHA는 보존 확인값이며 새 지문 발급이 아니다. release root는 `data/releases/`다.

| 기존 release 상대 경로 | 전후 동일 SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

- 문서 검수:25개 절, HB01~HB72 연속/유일성, 오류20prefix 유일성, API3개 필수 keyword-only 인자, 표 column/fence·UTF-8·한국어 본문, 실제 모델 AST의16필드와 raw 표의 exact 일치를 확인했다. 이는 문서 검수이며 신규 실행 테스트가 아니다.
- 실제 안산 BenefitSnapshot/Acceptance/지급액·새 정책 지문·실행 ZIP을 생성하지 않았다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, actual Ansan DRAFT/CONDITION_SLICE·정책 혜택 Cashflow 반영0원 원칙을 유지한다.

## 26. M2.60 — IMPLEMENTED: Historical BenefitSnapshot Strict Bytes Loader

### 실제 API와 모듈

`backend/policy_engine/policy_data/historical_benefit_snapshot_loader.py`에 다음 함수 하나를 구현하고 package public export에 추가했다.

```python
load_historical_benefit_snapshot_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> BenefitSnapshot
```

세 인자 모두 필수 keyword-only이며 기본값/우회 옵션은 없다. artifact는 실제 기존 AcceptanceReviewArtifact 타입이고 ArtifactReference가 아니다. 새 저장 필드/모델/예외 계층/일반 Artifact framework는 없다. 기존 constructor/serializer/지문 함수는 변경하지 않았다.

### 구현된 P0~P8 경로

```text
exact bytes / Review Artifact / 외부 Acceptance R
  → ACCEPTED / root ref / 명시 acceptance_ref 유일 조회 / entry.acceptance is R
  → 그 Entry의 실제 ArtifactReference만 선택
  → 동일 raw_bytes 전체 SHA256 == selected accepted_terms_ref.sha256
  → BOM 거부 / strict UTF-8 / JSON duplicate·number·Unicode scalar
  → wrapper2(schema_version=historical-benefit-snapshot-1.0) / snapshot16 / scope2 / binding2
  → 원본 bytes와 HB1 canonical equality
  → 기존 Scope·4 Enum·SourceBinding·BenefitSnapshot16 복원
  → 기존 fingerprint_benefit_snapshot 실제 호출
  → policy/scope/benefit/version → 실제 정의 fp → dataset → Registry 독립 대조
  → 새 불변 BenefitSnapshot만 반환
```

19절20개 오류 prefix와 세부 순서를 유지한다. P2 실패 시 JSON parser를 실행하지 않는다. missing key는 extra보다 먼저, schema/type은 canonical보다 먼저, canonical은 model invariant보다 먼저 검사한다. P6 계산 후 P7 identity4축/fp/provenance 순서로 비교한다. malformed data를 UNKNOWN/STALE/UNUSABLE/메타데이터 미검토로 바꾸거나 부분 Snapshot을 반환하지 않는다.

기존 Snapshot constructor의 evidence 문법·source 집합·binding 순서·금액/제한/월 조합 규칙을 그대로 사용한다. evidence 중복은 원래대로 보존한다. structurally valid VARIABLE/UNKNOWN·months=None·Bridge 비지원 정의도 구조적 복원과 R binding은 가능하다. 이 성공은 역사 발급 적정성·metadata review completeness의 승인이 아니다. M2.58의 후속 Content Validator 완전성 책임을 유지한다.

### 원본 결합·순수성의 한계

기대 hash는 actual bytes에서 채택하지 않고 선택 Entry의 독립 고정 ref에서 가져온다. hash·UTF-8·JSON·복원은 입력받은 동일 bytes에서 수행한다. 외부 Snapshot/다른 Entry ref/현재 Benefit fallback을 받지 않는다. 기존 지문 함수는 복원 후 반환할 바로 그 Snapshot에 한 번 적용한다. dataset/Registry 전체 지문은 definition15에서 여전히 제외되지만 R binding에서는 각각 필수 비교다.

파일/path 조회·network/Git/env/시각/random/cache·Registry resolve·Coverage 계산·Review loader 재실행은 없다. same-call 신뢰된 외부 A/C가 실제 M2.57 반환 root와 외부 원본 R을 직접 공급해야 한다. 타입/is 검사 자체를 실제 M2.57 통과 인증으로 확대하지 않는다. 파일 경로의 실재/공식성/내용 검토/사람 권한은 이 함수로 인증하지 않는다.

REVOKED 직접 입력은 P1에서 거부한다. 기존 None 참조·Context/철회 graph를 변경하거나 target A를 자동 복원하지 않는다. 다중 Entry에서는 명시 ref의 원본만 고르고 first/latest 선택을 하지 않는다. 정확한 동일 ref/정의를 공유하는 독립 revision은 허용한다.

### 합성 시나리오와 실행 테스트 대응

`tests/test_historical_benefit_snapshot_loader.py`의 신규 **294개**는 실제 수집·실행된 pytest 수다. 문서 HB01~HB72를 더하지 않는다. 모든 정상 end-to-end fixture는 기존 실제 M2.57 loader를 거쳐 root/R의 is 관계를 확보한다. parsing 오류 fixture의 H는 fixture 저작 단계에서 손상 bytes에 고정해 앞 단계가 정상 통과한 뒤 해당 오류를 검사한다. 소비 loader의 actual→expected 덮어쓰기를 허용한 것이 아니다.

기본 합성 historical 원본은681bytes이며 고정 raw SHA는 `14af199097a6b4e9e20e9c7b1e805604dbbc0001a676d370ee497525dfc58e46`이다. 독립 definition 기대값은 기존 BV01 literal `46c9a388b359c3e782e0a1d0d484ce8d19afe92e37080b20adda7000bcd45cd3`을 사용한다. 이는 synthetic/test-only이며 새 GV/BV/실제 정책 지문이 아니다.

| 문서 사례 | 이번 실제 검증 범위 |
|---|---|
| HB01~HB12 |16필드·정확한 타입/Enum/Scope/binding·FIXED0/VARIABLE/UNKNOWN·한국어/NFC/NFD·월 None/tuple·근거 순서/중복·다중 source·100회 불변/결정성 |
| HB13~HB28 | byte 변경/같은 filename/다른 기대 H·SHA 전 parser 미실행·공백/key순서/newline/escape/-0·UTF-8/BOM/JSON/중복/number/surrogate·parser 오류 대응 |
| HB29~HB50 | root2/snapshot16/scope2/binding2의 모든 required key·extra/type/null·schema/Enum·버전/월/SourceBinding/evidence/모델 조합 invariant |
| HB51~HB61 | identity4축·정의 fp·동일 정의의 dataset-only/Registry-only·다른 대상·다른 Entry bytes·root/entry 부재·원본 복사본/revision/target is 거부 |
| HB62 | ACCEPTED None/잘못된 ref는 기존 Entry constructor가 거부함을 검증. 정상 객체로 새 loader의 INVALID_EXPECTED_REF 분기에 도달하지 않으며 강제 변조하지 않음 |
| HB63~HB69 | REVOKED 거부·과거/현재 version 분리·exact 타입/subclass·복합 오류 우선순위·다중 Entry/공유 원본 허용 |
| HB70~HB72 | 반환 객체에 승인/현재 상태/Bridge 필드 없음·원문/Registry/파일을 열지 않음·현재 Snapshot 대체 없음이라는 기계적 경계. 실제 L3/외부 파일 미확보 처리·경로 인증은 실행 구현하지 않음 |

**중복 Entry 검증:** 기존 Root constructor가 중복 ref/revision을 생성 시 거부한다. 같은 Entry/값 같은 복사본/같은 ref의 다른 revision으로 정상 생성 시도를 하여 기존 오류를 확인했다. frozen 모델을 강제로 훼손하여 loader 분기에 도달시키지 않았다. loader에도 유일 entry count 검사를 유지하지만 정상 생성 객체에서 중복 count 실패는 상위 모델이 이미 차단한다.

**방어 오류 검증:** 실제 parser RecursionError mapping은 격리 failure injection으로 검사하며 특정 JSON 깊이를 고정 임계값이라고 주장하지 않는다. int 파싱은 현재 런타임 제한 초과/ValueError를 확인하고 전역 제한을 바꾸지 않았다. 지문 함수의 PolicyDataError 대응·예상 밖 RuntimeError 비은폐도 격리 검사했다. 존재할 수 없는 모델 상태를 만들기 위한 object 강제 변조는 없다.

### 완료 범위·미구현 의존사항

**IMPLEMENTED:** Historical BenefitSnapshot bytes loader·strict 동일 bytes 복원·기존 정의 지문 재계산/비교·Acceptance identity/version/provenance binding·합성 실행 테스트·public 함수1개.

**NOT IMPLEMENTED:** 외부 file preparation/orchestration·Historical Coverage/ReviewContext/Manifest codecs·Content Validator·Source Gate·Acceptance evaluator·same-call adapter·Benefit Bridge/Cashflow 연결·실제 안산 Snapshot/Acceptance/지급액.

**최종 판단: HISTORICAL_BENEFIT_SNAPSHOT_LOADER_COMPLETE.** 전체 Content Validator의 구현 준비 완료를 뜻하지 않는다. 다음 가장 작은 작업은 **Historical EligibilityCoverage Artifact Preparation Contract 문서 설계 하나**다. coverage_snapshot_ref의 동일 bytes에서 inventory뿐 아니라 bindings/review refs까지 포함한 정확한 기존 EligibilityCoverage를 복원하는 형식/기대 hash/동일 호출 대응을 먼저 확정한다. 다른 역사 codec 전체나 validator 구현으로 확대하지 않는다.

Coverage freeze/GV01~GV15/BV01~BV16·기존 Acceptance/Benefit/Review loader·bootstrap/Cashflow·실제 release6개는 보존한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, 실제 안산은 DRAFT/CONDITION_SLICE·정책 혜택 Cashflow 반영0원 원칙을 유지한다.

### M2.60 검증·보존 기록

- 작업 전 전체 pytest: **7,673 passed in 62.77s / skipped0 / failed0 / timeout0**.
- 신규 합성 실행: **294 passed in 1.52s**. 기본 raw SHA literal 고정 후 최종 전체 실행으로 함께 검증한다.
- 작업 후 전체 pytest: **7,967 passed in 70.55s / skipped0 / failed0 / timeout0**. 기존7,673개와 신규294개를 포함하며, 기본 raw SHA literal 고정 후의 최종 테스트다. 기존 테스트/fixture/기대값·timeout/테스트 설정은 변경하지 않았다.
- 사전 backend/tests/data/docs/tools176개(실제 releases·pycache 별도) 중 기존173개 SHA256이 동일하다. 변경3개는 package __init__.py의 public export 추가·이 문서·ARCHITECTURE.md이며, 새 loader/테스트2개를 더해 최종178개다. 기존 파일 삭제0개다.
- 기존 모든 tests/fixture·GV01~GV15/BV01~BV16·BenefitSnapshot/지문·Acceptance/Context/Evaluation·Review 모델/strict loader·Coverage freeze source/문서·bootstrap/Cashflow는 SHA256이 동일하다. DATA_MODEL.md도 변경하지 않았다. 새 stored field가 없으므로 별도 모델 문서 변경이 필요하지 않았다.
- 실제 release6개는 SHA256·경로·크기·수정시각이 모두 동일하다. 구체적인 기존 SHA는25절 표와 같으며 새 정책/Benefit/Acceptance/지급액·실행 artifact를 발급하지 않았다.
- API/타입·16필드·HB1/20prefix·순수성/직접 의존은 신규 실행 테스트로 검증했다. 새 코드 구문·UTF-8/한국어와 문서 table/fence 검수는 실행 테스트 수에 더하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.
