# M2.65 — Historical CoverageReviewContext Artifact Preparation Contract

현재 구현·검증 상태는 **30절 M2.66**을 따른다. 1~29절의 미구현/다음 작업/테스트 수는 M2.65 설계 시점의 이력이다. 승인된 raw/오류/복원 계약은 유지한다.

## 1. 목적·이번 범위

선택한 AcceptanceReviewEntry.coverage_reviews_ref의 독립 기대 SHA256과 일치하는 **동일 raw bytes**에서 기존 CoverageReviewContext와 두 종류의 검토 기록 전체를 복원하고, Context의 policy/scope/dataset/Registry/implementation baseline이 당시 Acceptance와 대응하는 계약을 확정한다.

이번에는 이 문서 하나만 추가한다. Historical ReviewContext Loader·Manifest Loader·Content Validator·Source Gate·Acceptance evaluator·Bridge/Cashflow·역사 실행 worker를 구현하지 않는다. 기존 코드/테스트/동결 문서/실제 releases를 변경하거나 실제 안산 ReviewContext/Acceptance/FULL Result를 생성하지 않는다.

**최종 판단: READY_TO_IMPLEMENT_HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER.** 좁은 원본 복원과 Context baseline 대조의 구현 준비 판단이며, Review MATCHED·Historical FULL_POLICY·사람 검토 진실성·현재 Acceptance USABLE의 인증이 아니다.

## 2. 현재 검증 공백·Source of Truth

| 확인 자료 | 유지할 계약·실제 코드 대조 |
|---|---|
| COVERAGE_REVIEW_CONTEXT_SPEC.md34절 | Context7필드·두 종류 tuple·전체 ref 유일성·역사 기록 공존 |
| COVERAGE_REVIEW_MATCHING_SPEC.md41~42절 | 실제 private matcher API·명시 ref resolution·guarded conflict·MISSING/STALE |
| COVERAGE_FINGERPRINT_SPEC.md / coverage_fingerprint.py | 기존 Inventory/Tree/subtree schema와 GV01~GV15·raw SHA와의 구별 |
| COVERAGE_INTEGRATION_GATE_SPEC.md40절 / coverage_integration.py | 구조→composition→Context target→실제 지문→Inventory→Implementation matching |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md36~37절 | Result8저장 필드·공식 evaluator/Gate/factory·derived FULL/SLICE |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | 최신 동결 의미/API/오류/지문·실제 정책 blocker·변경 통제 |
| HISTORICAL_ELIGIBILITY_COVERAGE_ARTIFACT_PREPARATION_SPEC.md30절 | M2.62의 Inventory/Binding 복원·same-call R·독립 H |
| HISTORICAL_POLICY_ENVELOPE_ARTIFACT_PREPARATION_SPEC.md28절 | M2.64의 전체 Policy/Tree 복원·확인 가능한 Acceptance binding |
| HISTORICAL_BENEFIT_SNAPSHOT_ARTIFACT_PREPARATION_SPEC.md26절 | M2.60의3인자 API·strict bytes·기존 모델 재사용 |
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md4~10·13·20절 | L1/L2/L3·historical_reviews·Content의 evaluator 자동 재실행 금지 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md30절 | Entry15·coverage_reviews_ref·REVOKED None·실제 loader와 구조 모델 구별 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md10~12·37절 | 실제 Acceptance21필드·Coverage provenance 원천·MVP equality |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md5~7·12절 | A/C/B 책임·같은 호출 원본·현재 producer와 역사 원본 분리 |
| ARCHITECTURE.md31·37~38·45~47·54~58절 / DATA_MODEL.md27~30·32·34·37절 | 현재 구현 위치/저장 필드·과거 설계 이력과 구별 |

실제 coverage_review_context.py, coverage_review.py, implementation_review.py, eligibility_coverage.py, condition_inventory.py, condition_binding.py, coverage.py, coverage_review_matching.py, coverage_review_resolution.py, coverage_integration.py, eligibility_coverage_result.py, eligibility_coverage_evaluator.py, benefit_acceptance_review_artifact.py, manifest.py, benefit_acceptance.py, errors.py 및 기존 historical loaders를 대조했다. 존재하는 constructor/함수만 아래에서 재사용한다.

현재 CoverageReviewContext.to_dict()는7key domain snapshot이며 schema/독립 file SHA/Entry 대응을 확인하는 raw loader가 아니다. 원본 tuple은 메모리로 구성할 수 있지만 **selected ref→동일 bytes→기존 모델→당시 R baseline**을 닫는 public 함수는 없다.

| 역사 원본 | 소유·복원 내용 | 대신할 수 없는 원본 |
|---|---|---|
| A: Historical EligibilityCoverage, M2.62 | Inventory/conditions/completeness ref + Bindings/implementation refs | Tree와 Review records/baseline |
| B: Historical PolicyEnvelope, M2.64 | 전체 Policy/Rule Tree·rule version·Envelope metadata | Inventory와 Review records |
| C: 이번 Historical CoverageReviewContext | Context baseline·Inventory/Implementation review records | 실제 Inventory/Binding/Tree/원문·실행 ZIP |

A/B/C와 별도의 BenefitSnapshot 원본은 같은 R/Entry에 독립 ref/H로 결합한다. C를 읽었다고 A/B를 생성하거나 FULL을 파생하지 않는다.

## 3. coverage_reviews_ref의 의미

기존 ArtifactReference의 저장 필드는 **path:str, sha256:str** 두 개다. path는 외부 원본 위치, sha256은 원본 파일 bytes 전체의 독립 기대 H다. 기존 생성자가 상대 slash path 문법과 lowercase hex64를 검증한다. 경로 실재·보관 권한·사람의 검토는 인증하지 않는다.

후속 loader는 selected entry.coverage_reviews_ref만 사용한다. coverage_snapshot_ref/policy_envelope_ref/accepted_terms_ref/Manifest/다른 Entry ref로 fallback하지 않는다. file SHA를 Context.source_registry_fingerprint나 implementation_fingerprint, Inventory/Tree/subtree fp로 대체하지 않는다. 파일명·길이·mtime도 H를 대체하지 않는다. path를 이용한 filesystem I/O는 순수 함수 밖의 책임이다.

이 ref는 Context 원본 파일의 참조다. Context 안 각 record.review_artifact_ref와 AcceptanceReviewArtifact.review_artifact_ref는 역할/문법이 별개이며 같은 파일이나 schema라고 강제하지 않는다(17절).

## 4. CoverageReviewContext의 정확한 저장 필드

기존 frozen/slots dataclass의 **7개 필수 필드**다. 기본값·새 stored field·상태를 추가하지 않는다.

| 순서 | 필드 | exact domain 타입·constructor validation |
|---|---|---|
|1|policy_id|str, `[A-Z0-9]+(?:-[A-Z0-9]+)*` |
|2|scope|ApplicabilityScope, 값으로 policy 회차/분기 식별 |
|3|dataset_version|str, 비공백. 임의 strip/version grammar 추가 없음 |
|4|source_registry_fingerprint|str, `[0-9a-f]{64}` |
|5|implementation_fingerprint|str, `[0-9a-f]{64}` |
|6|inventory_reviews|exact tuple, 각 원소 exact InventoryCompletenessReview |
|7|implementation_reviews|exact tuple, 각 원소 exact ImplementationBindingReview |

두 tuple은 각각 비어 있어도 된다. 모든 record의 policy_id/scope **값**은 Context와 같아야 하고, review_ref는 두 tuple 내부/사이를 합쳐 전부 유일해야 한다. 같은 ref의 같은 객체/같은 값/다른 날짜/다른 종류도 중복이면 오류다. 미참조 record도 이 구조 검증에서 제외하지 않는다.

Context constructor는 record의 inventory/rule/dataset version·각 fp·reviewed_at을 Context baseline이나 다른 record와 비교하지 않는다. 같은 policy/scope에서 다른 version 또는 같은 version의 다른 fp가 공존해도 이 collection 자체로는 허용한다. condition/root/version별 유일성을 추가하지 않는다. 원래 tuple 순서와 metadata를 보존한다.

ApplicabilityScope의 저장2필드는 **edition_id: exact str ASCII4자리, quarter: exact int1~4 또는 None**이며 둘 다 필수다. None은 unknown이 아닌 연간이다. 같은 연도의 Q3/annual/Q4는 다르다. 기존 모델이 허용하는 `0000`을 새로 금지하지 않는다. scope_id는 파생 property이며 raw key가 아니다.

## 5. InventoryCompletenessReview의 정확한 저장 필드

기존 frozen/slots dataclass의 **9개 필수 필드**를 모두 복원한다.

| 순서 | 필드 | exact domain 타입·constructor validation |
|---|---|---|
|1|review_ref|str, 비공백 opaque 참조. 공백/대소문자 원문 보존 |
|2|policy_id|str, Context와 같은 canonical ID grammar |
|3|scope|exact ApplicabilityScope |
|4|inventory_version|str, `i(?:[0-9]{4}\|[1-9][0-9]{4,})`, i0000 제외 |
|5|inventory_fingerprint|str, lowercase hex64 |
|6|dataset_version|str, 비공백. Context와 다른 값도 허용 |
|7|source_registry_fingerprint|str, lowercase hex64. Context와 달라도 collection-valid |
|8|reviewed_at|exact date. datetime/str/None을 domain에서 허용하지 않음 |
|9|review_artifact_ref|str, 비공백 opaque 내부 검토 참조 |

constructor 검사 순서는 실제 코드대로 비공백3필드(review_ref/dataset_version/review_artifact_ref)→policy→scope→inventory version→지문2개→날짜다. 로더가 그 의미 검사를 복제하지 않는다.

기록은 조건 목록 전체의 완결성 검토 주장을 표현한다. 이 타입이 source 원문·Inventory 내용·사람 검토 수행 여부를 확인하지 않는다. condition_id/rule_version/implementation_fingerprint는 이 타입에 없으며 추가하지 않는다.

## 6. ImplementationBindingReview의 정확한 저장 필드

기존 frozen/slots dataclass의 **15개 필수 필드**다.

| 순서 | 필드 | exact domain 타입·constructor validation |
|---|---|---|
|1|review_ref|str, 비공백 opaque 참조 |
|2|policy_id|str, canonical policy ID |
|3|scope|exact ApplicabilityScope |
|4|condition_id|str, `[A-Z0-9_]+` |
|5|rule_root_id|str, 비공백 원문. 이 생성자가 root를 조회하지 않음 |
|6|inventory_version|str,5절과 같은 양의 i grammar |
|7|inventory_fingerprint|str, lowercase hex64 |
|8|rule_version|str, 비공백. Envelope의 r#### grammar를 새로 강제하지 않음 |
|9|policy_tree_fingerprint|str, lowercase hex64 |
|10|subtree_fingerprint|str, lowercase hex64 |
|11|dataset_version|str, 비공백 |
|12|source_registry_fingerprint|str, lowercase hex64 |
|13|implementation_fingerprint|str, lowercase hex64 |
|14|reviewed_at|exact date |
|15|review_artifact_ref|str, 비공백 opaque 내부 검토 참조 |

constructor의 실제 순서는 비공백5필드(review_ref/rule_root_id/rule_version/dataset_version/review_artifact_ref)→policy→scope→condition→inventory version→지문5개→date다. 이 모델은 Binding/Policy/Inventory/원문을 저장하거나 lookup·fp 계산·MATCHED를 실행하지 않는다.

같은 condition/root를 여러 ref로 보관할 수 있다. 각 record의 fp 형식 유효성과 실제 tree/subtree/실행물 대응은 다르며, 이 원본 codec이 새로운 target 관계 검사를 발명하지 않는다.

## 7. 확정 Historical raw schema/version

| 후보 | 비교 | 선택 |
|---|---|---|
| A flat root8(schema_version+Context7) | 단순하나 Context snapshot과 파일 envelope 계층이 섞임 | 미선택 |
| B wrapper2(schema_version+review_context) | M2.60/M2.62의 독립 version wrapper와 일관되며 Context7을 그대로 보존 | **선택** |

schema discriminator는 exact str literal **`historical-coverage-review-context-1.0`**이다. 현재 backend/docs/tests의 실제 naming/codec과 충돌하는 기존 사용은 없었다. Context.to_dict()를 그대로 root로 받거나 alias wrapper를 추론하지 않는다. 이 문서의 raw 새 버전은 기존 Coverage fingerprint schema 변경이 아니다.

| object 경로 | exact required keys — 검사 순서 |
|---|---|
|root|schema_version, review_context |
|review_context|policy_id, scope, dataset_version, source_registry_fingerprint, implementation_fingerprint, inventory_reviews, implementation_reviews |
|모든 scope|edition_id, quarter |
|review_context.inventory_reviews[i]|review_ref, policy_id, scope, inventory_version, inventory_fingerprint, dataset_version, source_registry_fingerprint, reviewed_at, review_artifact_ref |
|review_context.implementation_reviews[i]|review_ref, policy_id, scope, condition_id, rule_root_id, inventory_version, inventory_fingerprint, rule_version, policy_tree_fingerprint, subtree_fingerprint, dataset_version, source_registry_fingerprint, implementation_fingerprint, reviewed_at, review_artifact_ref |

전 key는 required이며 optional key는 **0개**다. null은 각 scope.quarter에만 허용한다. quarter=null과 quarter missing은 다르고, reviews=[]와 null/missing도 다르다. root/Context/record/scope는 exact object, 두 reviews는 exact array[object]다. scope.quarter 외 record 값은 모두 string 또는 위 표의 scope object다. reviewed_at은 required string이며 P6에서 exact date로 변환한다. bool은 quarter의 int로 수용하지 않는다.

배열은 원순서 list→tuple로 복원한다. 문자열은 원문 그대로, null→None은 quarter에서만, 날짜는 정확한 ASCII `YYYY-MM-DD`의 유효 달력 날짜만 변환한다. datetime 문자열/숫자 timestamp/자동 strip/기본 날짜는 없다.

빈 Context의 논리적 raw 예시는 다음과 같다. 아래 들여쓰기 표시는 설명용이며 **HRC1 canonical bytes 예시가 아니다**. 실제 archive/Acceptance를 발급하는 자료가 아니다.

```json
{
  "schema_version": "historical-coverage-review-context-1.0",
  "review_context": {
    "policy_id": "SYNTH-POLICY",
    "scope": {"edition_id": "2026", "quarter": 3},
    "dataset_version": "SYNTH-D1",
    "source_registry_fingerprint": "3333333333333333333333333333333333333333333333333333333333333333",
    "implementation_fingerprint": "4444444444444444444444444444444444444444444444444444444444444444",
    "inventory_reviews": [],
    "implementation_reviews": []
  }
}
```

제외 key: status/matched/is_reviewed/is_full/acceptance_usable/verified, Inventory/Binding/Policy/Tree 본문, Result/findings, path/sha256, root-level acceptance/benefit/review_artifact_ref, 준비/검토자 handle. 이 값들은 Context7 또는 기존 두 review 저장 필드가 아니다.

## 8. Canonical bytes — HRC1

HRC1은7절 wrapper 전체의 bytes 규약이다. 다음 recipe를 확정한다.

```python
json.dumps(
    raw_payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8", errors="strict")
```

모든 object key 정렬·compact separators·BOM/끝 newline 없음·strict UTF-8다. 모든 review 배열은 원순서이며 ref/date/version별 정렬·dedupe가 없다. Unicode NFC/NFD·공백·대소문자·문자열 내 줄바꿈을 정규화하지 않는다. 한국어 opaque ref/표현도 기존 모델이 허용하는 문자열 그대로 보존한다. 구조 공백 제거와 문자열 내부 공백 제거를 혼동하지 않는다.

모든 깊이의 decoded key 중복, NaN/Infinity/-Infinity, float/exponent token, 고립 surrogate를 거부한다. 정수 token은 JSON parser에서 int로 읽되 quarter의 exact 타입/범위는 P5/P6에 따른다. parse_int ValueError와 실제 JSON parser RecursionError를 대응하고 전역 제한은 바꾸지 않는다. 유효한 surrogate pair는 scalar로 복원된 뒤에도 원본 escape가 HRC1과 다르면 NONCANONICAL이다.

P5 shape/primitive 검사를 끝낸 **같은 parsed root**를 위 recipe로 인코딩하여 B와 byte equality를 검사한다. missing을 null로 채우거나 defaults/date/배열을 변환한 뒤 canonical 비교하지 않는다. pretty-print/key순서/newline/불필요한 Unicode 또는 slash escape/-0 등 비정규 표현은 거부하며, canonical 사본으로 원본 B/H/ref를 바꿔 통과시키지 않는다. RFC 범용 canonicalization framework는 만들지 않는다.

## 9. 독립 expected SHA256의 원천

유일한 H는 **명시 선택 Entry.coverage_reviews_ref.sha256**이다. 신뢰된 외부 R.review_artifact_ref→같은 호출의 실제 M2.57 Review bytes 검증/원본 대조→selected Entry→Context 기대 H라는 연결을 유지한다.

actual sha256(B)는 오직 H와 비교한다. actual을 expected로 채택하지 않는다. source_registry_fingerprint/implementation_fingerprint/Tree·subtree fp는 서로 다른 대상의 값이며 raw H와 교환할 수 없다. 새 Context domain fingerprint 함수도 필요하지 않다.

record 날짜·ref·배열 순서·unused historical record·baseline을 바꾸면 파일 bytes가 달라지므로 원래 H에 대해 실패한다. 다른 정당한 archive가 별도 H를 고정할 수는 있지만 이전 검토가 새 bytes를 가리켰다고 소급 주장하지 않는다. H의 발급/권한·원본 보관 진실성은 외부 책임이다.

## 10. 동일 bytes와 외부 preparation

외부 preparation이 정확한 ref.path에서 immutable exact bytes B를 한 번 확보한다. 후속 순수 함수는 **B 전체 SHA→바로 그 B의 strict decode→그 내용 JSON parse→그 parsed Context의 기존 모델 복원** 순서다. hash 뒤 path를 다시 열거나 외부에서 만든 Context로 교체하지 않는다.

path containment·symlink/junction·접근 권한·보관소·파일 미확보·최대 파일 크기 같은 실제 I/O 운영 규칙은 외부 preparation 책임이다. 순수 API가 path 실재나 bytes 취득 위치를 인증하지 않는다. 확보 실패를 빈 Context나 Context=None으로 대신해 성공시키지 않는다.

외부는 같은 `(selected ref, B, returned Context)`와 Artifact/R 원본을 호출 지역값으로 보존해 후속 Content에 전달한다. cache key/token/검증 bool로 다음 요청에 승계하지 않는다. 이 문서로 외부 orchestrator나 generic historical codec framework를 구현하지 않는다.

## 11. 기존 모델 복원·constructor 재사용

현재 이 raw의 기존 parser는 없다. 후속 loader는 P5의 명시 raw key/type 확인 뒤 다음 작은 변환만 수행한다. 기존4타입을 수정/복제하거나 HistoricalReviewContext 타입을 만들지 않는다.

1. review_context.scope의 원문 두 값으로 기존 ApplicabilityScope 생성.
2. inventory_reviews를 **입력 순서**로 처리: 각 record 원문 scope로 ApplicabilityScope 생성→reviewed_at을 strict ASCII ISO date로 변환→기존 InventoryCompletenessReview에9개 값 모두 전달.
3. implementation_reviews를 입력 순서로 처리: 각 record scope 생성→date 변환→기존 ImplementationBindingReview에15개 값 모두 전달.
4. 두 record 배열을 exact tuple로 만들고,1의 Scope와 Context 원문 baseline/두 tuple을 기존 CoverageReviewContext7개 인자에 전달.

각 record의 원래 scope를 Context scope로 덮어쓰지 않는다. 별개 Scope 객체라도 값이 같으면 정상이다. 완성된 Context constructor가 다른 policy/scope·두 종류 전체 중복 ref를 최종 검증한다. 빈 두 tuple은 그대로 허용하고 같은 target의 여러 historical record를 남긴다. record가 같은 version의 다른 지문을 가졌다고 collection 단계에서 거부하지 않는다.

date 변환은 exact string shape는 P5, 정확한 ASCII 형식/달력 유효성은 P6 책임이다. constructor의 PolicyDataError만 고정 MODEL prefix와 생성 객체 경로로 좁게 대응한다. 날짜 변환의 ValueError만 DATE로 대응한다. 예상 밖 RuntimeError/시스템 실패를 포괄적으로 덮지 않는다. 리뷰 모델의 의미 검증 순서는 기존 코드를 유지한다.

자동 ref 생성·누락 Review/Binding 생성·stale 제거·dedupe·날짜/condition/root 추론·fp 재작성·latest 선택·현재 Context fallback은 없다. schema_version은 wrapper 식별자이며 Context의8번째 저장 필드로 넣지 않는다. 반환은 기존 frozen/slots CoverageReviewContext 하나다.

## 12. Acceptance identity/provenance 대조

P6의 구조적 복원이 전부 끝난 뒤 P7에서 다음 **5축을 이 순서로** 비교한다.

| 순서 | Context 원천 | 당시 R 원천 | 실패 |
|---|---|---|---|
|1 policy|policy_id|policy_id|IDENTITY_MISMATCH |
|2 scope|scope 전체 값|scope 전체 값|SCOPE_MISMATCH |
|3 dataset|dataset_version|coverage_dataset_version|DATASET_MISMATCH |
|4 Registry|source_registry_fingerprint|coverage_source_registry_fingerprint|REGISTRY_FINGERPRINT_MISMATCH |
|5 implementation|implementation_fingerprint|coverage_implementation_fingerprint|IMPLEMENTATION_FINGERPRINT_MISMATCH |

scope는 edition과 quarter의 정확한 value equality다. M2.64 Envelope의 year-only 한계와 달리 이 Context에는 명시 quarter가 있지만, 값 일치가 공식 정책의 실제 Q3 적용 의미를 인증하지는 않는다. 현재 날짜/이름/URL/birth range로 scope를 추론하지 않는다.

Context top-level에는 inventory_version/fp·rule_version/Tree fp·benefit_id가 없다. R의 그 값을 Context에 추가하거나 임의 record에서 뽑아 baseline으로 채우지 않는다. A의 Inventory와 B의 Policy는 해당 historical loader/후속 Content에서 별도로 대조한다.

개별 historical review의 dataset/Registry/implementation/inventory/rule/fp/date 차이를 R과 일괄 비교하지 않는다. Context baseline은 **복원 대상 당시 R의 기준**이고 각 record는 과거에 검토한 대상의 선언이다. Context baseline 자체와 R의 차이는 원본 binding 모순이므로 loader Data Error이며 정상 STALE/USABLE reason으로 낮추지 않는다. 개별 record 차이는13~16절의 후속 matching 책임이다.

## 13. Inventory/Binding의 명시 review ref 연결

| 관계 | 좁은 loader | 후속 Content/기존 core |
|---|---|---|
|A: Context 자체 구조 유효성|기존 constructor로 검증|완성 객체 사용 |
|B: Inventory.completeness_review_ref의 존재/종류|Inventory가 입력에 없으므로 미검증|기존 _resolve_inventory_review / _match_inventory_review 계약 재사용 |
|C: 선택 review의 Inventory version/fp 대응|실제 Inventory가 없어 미검증|복원 A와 기존 fingerprint_condition_inventory로 대조 |
|D: 해당 slot MATCHED/MISSING/STALE|계산/반환하지 않음|기존 matcher가 정확한 당시 입력을 기준으로 계산 |
|Binding.implementation_review_ref의 존재/종류|Binding이 없어 미검증|기존 _resolve_implementation_review / _match_implementation_review 계약 재사용 |
|condition/root 대상 대응|실제 Binding/Policy가 없어 미검증|기존 구조/대상 검증 및 matcher 책임 |

기존 ConditionInventory는5필드(policy_id/scope/inventory_version/conditions/completeness_review_ref)이고 completeness ref는 None 허용이다. ConditionBinding은 condition_id/rule_root_id/implementation_review_ref의3필드이며 마지막 ref는 필수 비공백 str다. raw codec 설계를 이유로 이를 optional로 바꾸지 않는다. EligibilityCoverage는 Inventory/Bindings만 소유한다.

기존 resolver는 정확한 원문 ref를 지정 종류 tuple에서 찾고 반대 종류에만 있으면 WRONG_REVIEW_TYPE, 양쪽에 없으면 REVIEW_REF_NOT_FOUND를 발생시킨다. Context가 없는 정상 MISSING과, 제공된 Context 안 깨진 명시 ref를 구별한다. empty Context는 생성/복원 가능하지만 선언 ref를 그 Context에서 resolve하면 오류일 수 있다. 이 loader는 어떤 ref가 선택됐는지 알 수 없으므로 empty를 불법으로 만들지 않는다.

후속 Content는 같은 R의 복원 A/C를 결합한다. resolver/matcher의 의미를 복제한 새 review-match 함수는 만들지 않는다. 좁은 loader가 기존 resolver를 미리 호출하거나 ref existence를 확인했다고 주장하지 않는다.

## 14. Policy Tree/Subtree 지문의 책임

Implementation review의 condition_id/rule_root_id/ref·Inventory version/fp·rule version·Tree fp·subtree fp·implementation fp를 원문 그대로 복원한다. 이 타입들에 저장되지 않은 실제 RuleNode를 추론하지 않는다.

같은 R의 복원 A(Inventory/Bindings), B(PolicyEnvelope.policy), C(Context)를 **후속 Content 검증 단계**에서 결합한다. 실제 root 존재/소속/ownership/overlap/unmapped/composition의 기존 core 책임과, 공식 지문 함수로 계산한 실제 Inventory/Tree/subtree 값을 해당 matcher에 공급하는 책임을 유지한다. loader에는 Policy 인자가 없어 actual subtree fp 검증을 할 수 없다.

기존 schemas는 coverage-inventory-1.0 / coverage-policy-tree-1.0 / coverage-subtree-1.0이다. raw file H나 Context 문자열 하나가 이 actual domain fp를 대신하지 않는다. 의미상 같은 Tree를 추정해 reference를 고치거나 unsupported Rule을 제외하지 않는다. frozen matching/구조 순서도 변경하지 않는다.

## 15. implementation fingerprint의 세 경계

| 단계 | 검사 | 이번 계약 |
|---|---|---|
|1 형식|Context/record의 exact lowercase hex64|기존 constructor로 복원 시 검사 |
|2 metadata binding|Context.implementation_fingerprint == R.coverage_implementation_fingerprint|P7에서 비교 |
|3 실제 artifact/실행 대응|선언 ZIP bytes identity·내용/프로파일·실제 평가 실행 코드와의 대응|외부 preparation/별도 검증 책임, 이번 미구현 |

개별 Implementation record의 다른 implementation fp는 정상 historical collection에 포함될 수 있다. baseline과의 비교는 후속 matcher에서 IMPLEMENTATION_CHANGED STALE일 수 있으며, 이 loader가 일괄 거부하지 않는다.

implementation_fingerprint와 coverage_reviews_ref.sha256은 서로 다른 원본의 지문이다. Manifest.engine_artifact_sha256과도 두 hash 영역의 동일 ZIP 프로파일/실제 대응이 확인된 경우의 후속 규칙을 따른다. hex 형식이 같다고 모두 같게 채우지 않는다. M2.53 합성 ZIP verify-only는 당시 production 구현 검증이 아니며 이번 loader에서 bootstrap/ZIP/서브프로세스를 실행하지 않는다.

## 16. Review MATCHED와 Historical FULL의 구별

Raw에는 MATCHED/MISSING/STALE/FULL_POLICY/CONDITION_SLICE를 저장하지 않는다. 기존 ReviewMatchStatus는 MATCHED/MISSING/STALE의3값이며 InventoryReviewMatch/ImplementationReviewMatch는 resolver/matcher의 별도 결과다. 이 loader는 해당 결과나 EligibilityCoverageResult를 생성하지 않는다.

후속 matcher의 동결 규칙은 다음과 같다. 이는 **설명용 책임표이며 이번 loader가 실행하는 비교가 아니다**.

| 선택 record의 비교 | 동결 matcher 결과 |
|---|---|
|Inventory version 다름|INVENTORY_VERSION_CHANGED STALE; 그 쌍의 fp 차이를 모순으로 보지 않음 |
|같은 Inventory version, 실제 Inventory fp 다름|INVENTORY_FINGERPRINT_CONFLICT Data Error |
|Rule version 다름|RULE_VERSION_CHANGED STALE; 해당 Tree/subtree fp 쌍은 version guard |
|같은 Rule version, 실제 Tree/subtree fp 다름|POLICY_TREE_FINGERPRINT_CONFLICT / SUBTREE_FINGERPRINT_CONFLICT |
|record dataset 다름|DATASET_VERSION_CHANGED STALE |
|같은 dataset, Registry fp 다름|SOURCE_REGISTRY_FINGERPRINT_CONFLICT |
|record implementation fp 다름|IMPLEMENTATION_CHANGED STALE |

다른 독립 version/내용의 모순은 STALE 후보가 생겨도 검사한다. 실제 적용 순서는 최신 integration gate와 Inventory slot→canonical Implementation slot 단위의 기존 matcher를 따른다. reviewed_at/artifact ref로 최신 검토를 선택하거나 만료를 추론하지 않는다.

Historical FULL은 당시 정확한 A/B/C/공식 의미 검토/실행 artifact 대응이 준비된 환경에서 기존 **evaluate_eligibility_coverage(coverage, policy, review_context=None) -> EligibilityCoverageResult** 공식 경로가 계산해야 할 결과다. 이 API는 실제 positional/keyword 인자를 허용하고 Context 기본값은 None이다. 임의 Result JSON 복원·private token 우회·현재 engine 결과에 과거 implementation H를 붙이는 경로는 없다.

기존 Result 저장8필드는 policy_id/scope/inventory_version/rule_version/dataset_version/source_registry_fingerprint/implementation_fingerprint/findings다. status는 파생 property다. MATCHED만으로 missing Binding·구조/composition·전체 검토·baseline gate를 건너뛰어 FULL을 만들 수 없다. Generic FULL도 Policy VERIFIED/사용자 eligibility PASS/Acceptance USABLE/현금 지급과 다르다.

M2.58의 Content Validator는 **Coverage evaluator 자동 재실행·외부 FULL bool/Result 입력을 채택하지 않는다**. 기존 resolver/matcher/지문/구조 규약을 재사용한 L1/L2 대조와, 필요할 때의 별도 역사 실행 환경에서 FULL 재현을 구별한다. 이번 설계는 그 결정을 뒤집지 않는다.

## 17. 외부 검토 진실성·두 종류 artifact ref

record.review_artifact_ref는 exact 비공백 opaque str이다. URL/파일 경로/새 prefix/acceptance-review:sha256: 형식을 강제하지 않는다. 예를 들어 한국어 참조나 앞뒤 공백이 있는 비공백 ref도 기존 모델대로 원문을 보존한다. review_ref 역시 opaque이며 빈 문자열/공백뿐인 값만 기존 모델이 거부한다.

AcceptanceReviewArtifact.review_artifact_ref는 M2.54~M2.57의 content-addressed **acceptance-review:sha256:hex64**로 별도 역할이다. record의 내부 검토 자료와 같은 문서/같은 hash domain이라고 가정하지 않는다. CoverageReviewContext 파일의 H는 다시 별도다.

raw H 일치·record constructor 성공·Context baseline 일치·후속 MATCHED 모두 실제 사람이 어떤 근거로 검토했는지, 검토 권한이 정당한지, 원문이 조건 의미를 지지하는지 인증하지 못한다. record가 지목한 검토 원문 확보·대상/검토자/테스트/note·공식 의미 확인은 외부 L3/검토 절차 책임이다. 허위 검토 기록/가짜 reviewer를 생성하거나 LLM에 자격/검토 진실성을 판정시키지 않는다.

## 18. Same-call Entry 선택·ACCEPTED 전용

후속3인자 API는 기존 historical loaders와 같은 R/Artifact 경계를 선택한다.

1. P0 exact bytes / exact AcceptanceReviewArtifact / exact PolicyBenefitAcceptance.
2. P1 R.status는 BenefitAcceptanceStatus.ACCEPTED.
3. Artifact.review_artifact_ref == R.review_artifact_ref.
4. entries에서 entry.acceptance.acceptance_ref == R.acceptance_ref인 Entry가 정확히 하나.
5. **entry.acceptance is R**.
6. P2 바로 그 Entry.coverage_reviews_ref가 nonnull exact ArtifactReference.

같은 값의 R 복사본/다른 revision/같은 benefit의 다른 Entry/first/latest/current fallback은 없다. 다른 revision이 정당하게 같은 ref/bytes를 공유하는 것은 각 R 원본의 위 관계를 충족하면 가능하다. 외부 orchestration은 다른 요청의 A/B/C/Benefit를 섞지 않고 각 selected ref의 동일 bytes를 보존한다.

REVOKED의7참조 None은 유지하며 직접 입력을 P1에서 거부한다. 철회 target A의 역사 자료가 필요하면 M2.58의 외부 target preparation이 A 원본을 명시 공급한다. B의 None 참조를 채우거나 loader가 target을 자동 조회하지 않는다.

정상 Artifact constructor는 duplicate Entry/ref/revision·ACCEPTED None ref를 이미 막는다. 후속 loader에도 방어 검사를 두되, 도달 불가능한 실패를 테스트하려고 frozen 객체를 강제 훼손하지 않는다. 기존 생성 단계의 거부와 loader 단계의 검사를 구별한다.

type/is만으로 실제 M2.57을 실행했다는 인증은 못 한다. 신뢰된 외부 A/C가 같은 호출에서 실제 loader를 실행해 그 반환 root와 외부 R 원본을 직접 넘겨야 한다. 새 VerifiedContext/보안 token/영구 캐시 성공 flag를 만들지 않는다.

## 19. 확정한 후속 Pure API

```python
load_historical_coverage_review_context_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> CoverageReviewContext
```

이 문서의 **후속 구현 계약**이며 현재 구현/export된 함수가 아니다.3개 인자는 모두 필수 keyword-only이고 default/추가 옵션이 없다. artifact는 ArtifactReference가 아닌 실제 AcceptanceReviewArtifact다. subclass/dict/list/str/bytearray/memoryview/raw Context를 자동 변환하지 않는다.

세 입력으로 가능한 것은 selected ref H·원본 복원·Context target/provenance 대조다. 개별 review는 원본 metadata로 복원하고 실제 Inventory/Binding/Tree와 결합하지 않는다. 반환은 기존 CoverageReviewContext 하나이며 flag·tuple[Context,bool]·새 DTO·Result를 만들지 않는다.

force_matched/force_full/skip_reviews/use_current_context/ignore_implementation/skip_hash/allow_stale/fallback_context 옵션은 금지한다. 기존 historical loader들을 공통 framework로 리팩터링하지 않는다. 권장 후속 파일은 `backend/policy_engine/policy_data/historical_coverage_review_context_loader.py`, 합성 테스트는 `tests/test_historical_coverage_review_context_loader.py`다. 이번에는 두 파일과 export를 추가하지 않는다.

## 20. Loader 성공의 정확한 의미

성공은 **선택한 R의 Entry가 지목한 과거 Context 파일의 기대 H와 일치하는 동일 bytes를 strict raw schema/HRC1로 복원했고, 구조적으로 유효한 Context의 policy/scope와 dataset/Registry/implementation baseline이 R과 같음**을 뜻한다.

성공에 포함하지 않는 것: 개별 Review MATCHED·모든 Binding 검토 완료·Inventory 공식 완결성·실제 root/subtree 대응·Historical FULL·실제 사람 검토·ZIP 실행 대응·전체 Manifest/Registry/source·Policy VERIFIED·현재 Acceptance USABLE·사용자 PASS/현금흐름 반영.

빈 Context나 오래된 records가 정상 복원될 수 있어도 당시 Acceptance 발급 적정성이 증명된 것은 아니다. 후속 Content가 요구하는 원본/관계를 충족하지 못하면 전체 검증은 미완료다. 좁은 loader 성공을 전체 validation 성공 token으로 재사용하지 않는다.

| 상황 | 책임·처리 |
|---|---|
|깨진 raw/모델/Context baseline 불일치|loader PolicyDataError, partial 성공 없음 |
|같은 policy/scope의 여러 version/fp/date record|기존 collection대로 복원, 현행/역사 matcher의 별도 비교 |
|명시된 Inventory/Binding review ref가 Context에 없음|A와 C 결합 후 기존 resolver 오류, 이 loader에는 입력이 없어 미판정 |
|원본 bytes/검토 문서/실행 환경 미확보|외부 preparation 실패/검증 미완료, 빈값으로 성공하지 않음 |
|pretty-print 원본|H가 맞더라도 HRC1 실패, 자동 재작성 없음 |

## 21. Error Contract — 후속 prefix20개

기존 PolicyDataError 하나를 사용하며 새 예외 계층/.code 속성/오류 Enum을 만들지 않는다. 오류는 `PREFIX: field: 고정 이유` 형식이며 known field 경로/배열 index만 표시한다. raw 값·unknown key·path/ref·actual/expected H·하위 constructor 원문 오류를 노출하지 않는다. signature 위반은 Python TypeError다.

| phase | exact prefix | 고정 field·의미 |
|---|---|---|
|P0|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER_INPUT|raw_bytes / artifact / expected_acceptance exact 타입 |
|P1|HISTORICAL_COVERAGE_REVIEW_CONTEXT_REVIEW_BINDING_MISMATCH|expected_acceptance.status / artifact.review_artifact_ref / artifact.entries / entry.acceptance |
|P2|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_EXPECTED_REF|entry.coverage_reviews_ref nonnull exact 타입 |
|P3|HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES_MISMATCH|raw_bytes 전체 SHA != selected H |
|P4|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_ENCODING|raw_bytes, BOM/invalid UTF-8 |
|P4|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON|json, JSONDecodeError/실제 parser RecursionError |
|P4|DUPLICATE_HISTORICAL_COVERAGE_REVIEW_CONTEXT_JSON_KEY|json, 모든 깊이 decoded key 중복 |
|P4|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_NUMBER|json, float/exponent/constant/parse_int ValueError |
|P4|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_UNICODE|json, 고립 surrogate |
|P5|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_FIELDS|known object 경로, required missing/unknown extra |
|P5|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_SCHEMA|schema_version, literal 미지원 |
|P5|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_TYPE|known field 경로, primitive/object/array/null 타입 |
|P5|NONCANONICAL_HISTORICAL_COVERAGE_REVIEW_CONTEXT_BYTES|raw_bytes != HRC1 bytes |
|P6|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATE|각 record.reviewed_at, 비ASCII/비ISO/유효 달력 아님 |
|P6|INVALID_HISTORICAL_COVERAGE_REVIEW_CONTEXT_MODEL|생성 대상 scope/record/review_context 경로, 기존 PolicyDataError |
|P7a|HISTORICAL_COVERAGE_REVIEW_CONTEXT_IDENTITY_MISMATCH|review_context.policy_id != R.policy_id |
|P7b|HISTORICAL_COVERAGE_REVIEW_CONTEXT_SCOPE_MISMATCH|review_context.scope != R.scope |
|P7c|HISTORICAL_COVERAGE_REVIEW_CONTEXT_DATASET_MISMATCH|review_context.dataset_version != R.coverage_dataset_version |
|P7d|HISTORICAL_COVERAGE_REVIEW_CONTEXT_REGISTRY_FINGERPRINT_MISMATCH|review_context.source_registry_fingerprint != R의 Coverage Registry fp |
|P7e|HISTORICAL_COVERAGE_REVIEW_CONTEXT_IMPLEMENTATION_FINGERPRINT_MISMATCH|review_context.implementation_fingerprint != R의 Coverage implementation fp |
|P8|오류 없음|기존 CoverageReviewContext 반환 |

P6 MODEL은 예를 들어 `review_context.scope`, `review_context.inventory_reviews[0].scope`, `review_context.inventory_reviews[0]`, `review_context.implementation_reviews[0]`, `review_context`를 사용한다. DATE field는 예를 들어 `review_context.implementation_reviews[0].reviewed_at`다. float quarter는 P4 NUMBER, bool quarter/null date는 P5 TYPE, 범위 밖 int quarter는 P6 MODEL이다.

현재 snapshot의 guarded fp conflict/REVIEW_REF_NOT_FOUND/WRONG_REVIEW_TYPE 등 기존 matcher 오류를 이 loader의 prefix로 재정의하지 않는다. matcher를 실행하지 않는다. 정상 historical record 차이를 STALE로 계산하거나 Data Error를 CONDITION_SLICE/미검토/Acceptance reason으로 낮추지 않는다.

## 22. Validation precedence

1. **P0:** raw_bytes→artifact→expected_acceptance exact 타입. 모든 타입 확인 뒤 P1.
2. **P1:** ACCEPTED→root ref→명시 acceptance_ref 유일 조회→entry.acceptance is R. **P2:** selected coverage_reviews_ref 타입/nonnull. 다른 Entry 자료를 미리 parse하지 않음.
3. **P3:** 동일 B 전체 SHA. mismatch면 decode/JSON/모델 생성 없음.
4. **P4:** BOM→strict UTF-8→JSON→Unicode scalar scan. duplicate/number/syntax가 겹치면 JSON parser에서 실제 먼저 발견한 사건이다. 전역 정수/recursion 제한은 바꾸지 않음.
5. **P5:** root object→required keys7절 순서로 missing 먼저/extra 다음→schema_version type/literal→review_context object/key 집합→Context 필드7절 순. scope는 edition_id→quarter. inventory_reviews 배열을 왼쪽부터 각9필드 순(중첩 scope 포함)으로 검사하고, 다음 implementation_reviews 배열 각15필드를 같은 방식으로 검사. 각 object는 own key set을 primitive보다 먼저 확인. nullable는 quarter만. 의미/날짜/Enum 판정은 하지 않음.
6. **P5 마지막:** 원문 parsed root의 HRC1 bytes == B. noncanonical+invalid 날짜/ref/version이면 NONCANONICAL이 P6보다 먼저. raw를 수정/기본값 주입하지 않음.
7. **P6:** Context scope→입력 순 Inventory records 각각(scope→date→constructor)→입력 순 Implementation records 각각(scope→date→constructor)→최종 Context constructor. 모든 record가 만들어진 뒤 전역 ref 중복/소속을 검사하므로 뒤쪽 record 자체의 날짜/생성 오류가 최종 Context 중복보다 먼저일 수 있음. 모델 내부 검증 순서는 실제 constructor 그대로.
8. **P7:** policy→scope→dataset→Registry→implementation, 각각 독립 비교. 차이를 수집하다 부분 성공/STALE로 반환하지 않음.
9. **P8:** 전부 성공한 기존 Context만 반환. I/O·Inventory/Tree fp·resolver/matcher/Gate/factory/evaluator/bootstrap 호출 없음.

예: 잘못된 input+ref는 P0, 잘못된 H+malformed JSON은 P3, wrong schema+record 오류는 P5 schema, whitespace+invalid date는 P5 canonical, 다른 record policy+R baseline 오류는 P6 Context, Registry+implementation 불일치는 P7d가 먼저다. 특정 phase 합성 테스트는 그 이전 단계가 정상 통과하도록 독립 fixture를 준비한다.

## 23. 합성 검증 시나리오 — HRC01~HRC80

아래 **80개는 수동 설계 사례이며 신규 실행 테스트0개**다. E=실제 M2.57 root/Entry와 외부 R 원본, B=Context raw bytes, H=selected coverage_reviews_ref의 독립 기대 SHA, T=R policy/scope, D/G/X=R의 Coverage dataset/Registry/implementation baseline이다. A/P는 별도 복원 Coverage/Policy 원본이며 V는 검토 원문이다.

정상 fixture의 B/H와 R baseline을 저작 시 고정한다. P4 이후 손상 테스트는 손상 B에 맞는 H를 테스트 실행 전에 고정해 P3를 통과시킨다. 소비 loader의 actual→expected 채택을 허용하는 것이 아니다. 모델 생성 불가능 상태를 frozen 강제 변조로 만들지 않는다.

| ID | 입력·독립 기대값 | 기대 결과 | phase | 담당 계층·후속 실행 테스트 |
|---|---|---|---|---|
|HRC01|빈 두 reviews, E/B/H/T/D/G/X|기존 빈 Context 복원, FULL 주장 없음|P8|loader, 가능 |
|HRC02|Inventory review만1개, 나머지 정상|9필드/Scope/date 복원|P8|loader, 가능 |
|HRC03|Implementation review만1개|15필드 전체 복원|P8|loader, 가능 |
|HRC04|두 종류 모두 존재|Context7+record 전체 값 보존|P8|loader, 가능 |
|HRC05|다수 record, ref 유일|입력 tuple 순서 보존|P8|loader, 가능 |
|HRC06|같은 target의 i0001/i0002 records|둘 다 복원, 최신 선택 없음|P8|loader, 가능 |
|HRC07|같은 condition/root의 다른 rule versions|둘 다 보존|P8|loader, 가능 |
|HRC08|record dataset/Registry가 Context와 다름|historical collection 복원 허용|P8|loader, 가능 |
|HRC09|record implementation fp가 baseline과 다름|복원 허용, STALE 미계산|P8|loader, 가능 |
|HRC10|같은 version의 다른 fp, ref는 다름|collection은 허용, snapshot 비교 별도|P8|loader, 가능 |
|HRC11|같은 T/D/G/X, 서로 다른 reviewed_at|원날짜 보존, 최신/만료 선택 없음|P8|loader, 가능 |
|HRC12|Scope2026/annual, record/R도 annual|quarter=None 복원|P8|loader, 가능 |
|HRC13|Scope2026/Q3, record/R 모두 동일|정확한 scope 값 대조|P8|loader, 가능 |
|HRC14|Scope0000/Q4, 같은 R|기존 scope grammar 유지|P8|loader, 가능 |
|HRC15|한국어 opaque review/artifact refs|UTF-8 원문 복원, 새 prefix 강제 없음|P8|loader, 가능 |
|HRC16|opaque ref/rule_version의 유효 앞뒤 공백·NFC/NFD|trim/normalization 없음|P8|loader, 가능 |
|HRC17|같은 E/B/H100회|결정적 동일 값, 입력 불변/새 반환 객체|P8|loader, 가능 |
|HRC18|다른 R 원본 revision이 정당하게 같은 B/H 공유|각 Entry 원본 binding으로 복원|P8|loader, 가능 |
|HRC19|B1byte 변경, old H|BYTES_MISMATCH|P3|loader, 가능 |
|HRC20|기대 H만 다른 값|BYTES_MISMATCH|P3|loader, 가능 |
|HRC21|같은 파일명, 다른 B|파일명 무관 BYTES_MISMATCH|P3|loader, 가능 |
|HRC22|invalid UTF-8, 손상 B의 H|ENCODING|P4|loader, 가능 |
|HRC23|BOM, 해당 H|ENCODING|P4|loader, 가능 |
|HRC24|malformed/trailing JSON|JSON|P4|loader, 가능 |
|HRC25|root duplicate key|DUPLICATE_JSON_KEY|P4|loader, 가능 |
|HRC26|nested Scope/두 record의 duplicate key|모든 깊이 DUPLICATE_JSON_KEY|P4|loader, 가능 |
|HRC27|escape 후 동일 decoded key|DUPLICATE_JSON_KEY|P4|loader, 가능 |
|HRC28|pretty-print/key순서 변경, H는 맞음|NONCANONICAL|P5|loader, 가능 |
|HRC29|끝 newline/구조 공백|NONCANONICAL|P5|loader, 가능 |
|HRC30|불필요 Unicode/slash escape|NONCANONICAL|P5|loader, 가능 |
|HRC31|quarter=-0 raw표현|NONCANONICAL, 범위 판단보다 먼저|P5|loader, 가능 |
|HRC32|float/exponent/NaN/Infinity|NUMBER|P4|loader, 가능 |
|HRC33|parse_int ValueError/실제 JSON RecursionError|NUMBER/JSON, 전역 설정 불변|P4|loader, 격리 주입/런타임 사례 가능 |
|HRC34|고립 surrogate key/value|UNICODE|P4|loader, 가능 |
|HRC35|root nonobject|TYPE|P5|loader, 가능 |
|HRC36|root required missing/extra|FIELDS, missing 먼저|P5|loader, key별 가능 |
|HRC37|flat Context/alias wrapper/unknown schema|FIELDS/SCHEMA 첫 오류|P5|loader, 가능 |
|HRC38|Context7개 중 required missing/extra|FIELDS|P5|loader, key별 가능 |
|HRC39|두 record9/15개 중 required missing/extra|FIELDS|P5|loader, key별 가능 |
|HRC40|scope.quarter missing vs null|missing FIELDS / null은 annual|P5/P8|loader, 가능 |
|HRC41|reviews null/missing/object|TYPE/FIELDS, 빈 array와 구별|P5|loader, 가능 |
|HRC42|quarter bool/string|TYPE, int coercion 없음|P5|loader, 가능 |
|HRC43|quarter0/5|MODEL, scope 생성 단계|P6|loader+Scope, 가능 |
|HRC44|잘못된 edition ASCII4 grammar|MODEL|P6|loader+Scope, 가능 |
|HRC45|reviewed_at null/int|TYPE, 날짜 추론 없음|P5|loader, 가능 |
|HRC46|비ISO/비ASCII/불가능 달력 date|DATE|P6|loader date 변환, 가능 |
|HRC47|빈/공백 review_ref/artifact ref|MODEL, 새 ref 생성 없음|P6|기존 record, 가능 |
|HRC48|malformed/대문자 fp|MODEL, 소문자 보정 없음|P6|기존 모델, 가능 |
|HRC49|잘못된 inventory version/condition ID|MODEL|P6|기존 record, 가능 |
|HRC50|같은 inventory tuple 안 duplicate ref|MODEL|P6 최종 Context|기존 Context, 가능 |
|HRC51|같은 implementation tuple 안 duplicate ref|MODEL|P6 최종 Context|기존 Context, 가능 |
|HRC52|두 종류 사이 duplicate ref|MODEL|P6 최종 Context|기존 Context, 가능 |
|HRC53|다른 policy record를 Context에 혼합|MODEL, 미참조여도 거부|P6 최종 Context|기존 Context, 가능 |
|HRC54|다른 scope record를 혼합|MODEL, annual/Q3/다른 edition 구별|P6 최종 Context|기존 Context, 가능 |
|HRC55|Implementation shape를 inventory 배열에 공급|FIELDS, 종류 추론/변환 안 함|P5|loader, 가능 |
|HRC56|status=MATCHED/is_full 등 추가|FIELDS, 파생값 신뢰 없음|P5|loader, 가능 |
|HRC57|bytearray/memoryview/bytes subclass|LOADER_INPUT|P0|loader, 가능 |
|HRC58|dict/ref/Context/subclass를 typed 인자 대신 공급|LOADER_INPUT|P0|loader, 가능 |
|HRC59|R 같은 값 복사본/다른 revision|REVIEW_BINDING_MISMATCH|P1|loader, 가능 |
|HRC60|R.acceptance_ref Entry 없음/root ref 불일치|REVIEW_BINDING_MISMATCH|P1|loader, 가능 |
|HRC61|같은 benefit의 다른 Entry bytes|selected R의 H로 BYTES_MISMATCH|P3|loader, 가능 |
|HRC62|duplicate Entry/ACCEPTED None·wrong ref|기존 생성자 단계 거부|진입 전|기존 Artifact/Entry, 강제 훼손 없이 가능 |
|HRC63|잘못된 ArtifactReference path/hash|기존 생성자 거부|진입 전|기존 ArtifactReference, 가능 |
|HRC64|REVOKED 직접 공급|REVIEW_BINDING_MISMATCH, ref None 유지|P1|loader, 가능 |
|HRC65|Context 전체 policy는 내부 일치하나 R과 다름|IDENTITY_MISMATCH|P7a|loader, 가능 |
|HRC66|Context/records scope는 같으나 R과 다름|SCOPE_MISMATCH|P7b|loader, 가능 |
|HRC67|Context dataset baseline만 R과 다름|DATASET_MISMATCH|P7c|loader, 가능 |
|HRC68|Context Registry baseline만 R과 다름|REGISTRY_FINGERPRINT_MISMATCH|P7d|loader, 가능 |
|HRC69|Context implementation baseline만 R과 다름|IMPLEMENTATION_FINGERPRINT_MISMATCH|P7e|loader, 가능 |
|HRC70|타입+ref/H+JSON/schema+record/공백+날짜/두 baseline 오류|22절 첫 phase/축 오류|복합|loader, 조합별 가능 |
|HRC71|A의 completeness ref가 복원 C에 없음|C loader는 성공 가능, 결합 후 REVIEW_REF_NOT_FOUND|후속|Content+기존 resolver, 후속 가능 |
|HRC72|Binding ref가 Inventory review를 가리킴/아예 없음|C loader는 성공 가능, WRONG_REVIEW_TYPE/REF_NOT_FOUND|후속|Content+기존 resolver, 후속 가능 |
|HRC73|명시 Implementation review condition/root가 Binding과 다름|loader에는 Binding 없음, 후속 target Data Error|후속|기존 구조/matcher, 후속 가능 |
|HRC74|actual subtree fp와 선택 review fp가 다름|loader 미판정, 같은 rule version이면 기존 conflict|후속|Content+기존 fp/matcher, 후속 가능 |
|HRC75|Context baseline=R이나 ZIP bytes 없음/다름|좁은 복원과 실제 실행 검증 완료는 별개|외부|preparation/실행, 실제 bytes 없이는 완료 불가 |
|HRC76|C 복원 성공/A 또는 P 미확보|Review MATCHED/FULL 계산 불가|후속|Content/외부, loader 호출 격리 경계만 가능 |
|HRC77|기계 MATCHED이나 실제 사람 검토 문서/권한 미확인|truthfulness 인증 아님|외부 L3|사람/검토 절차, 자동 테스트로 증명 불가 |
|HRC78|현재 engine과 과거 artifact 불일치, M2.53 합성만 성공|Historical FULL 재현 완료 아님|외부 실행|역사 환경 준비, 실제 실행 대응 별도 |
|HRC79|Context dataset/Registry=R, Manifest/Registry 원본 없음|전체 release 검증 완료 아님|후속|Manifest/source 준비, loader 경계만 가능 |
|HRC80|C 복원 또는 별도 Historical FULL 있으나 current/source/철회 미확인|Acceptance USABLE/Policy VERIFIED/Cashflow 승인 아님|후속|Acceptance/Source/Bridge, 이번 미구현 |

후속 단위 테스트는 schema key/type 매개화·같은 B/모델 변환 순서·100회 결정성·입력 불변/serializer 사본 격리·생성자 재사용·예외 원문 비노출·예상 밖 RuntimeError 전달·외부 I/O/지문/matcher/Result/bootstrap 미호출을 확인한다. 테스트 작성 시80개 표를 그대로 실행 테스트 개수로 더하지 않는다. 불가능한 P2/중복 Entry 상태는 기존 생성자 거부와 방어 경계 검수로 구분한다.

## 24. Coverage freeze 영향

동결 core 밖의 bytes codec을 설계했으며 기존 Context/Review/Scope/Inventory/Binding/Coverage/MatchResult/Result·공식 evaluator·resolver/matcher·지문 payload·오류·생성자 불변조건은 바꾸지 않는다. 새 raw version은 transport wrapper만 구별한다. 기존 domain serializer를 raw parser로 오인하지 않는다.

Generic Coverage Core는 ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS의 의미를 유지한다. 실제 안산은 기존 DRAFT/CONDITION_SLICE·정책 혜택 Cashflow 반영0원 상태다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**이며 공식 답변 전 구현/Rule 연결을 진행하지 않는다. 기존 release001/002 여섯 파일도 불변이다.

기존 타입을 그대로 복원할 수 없는 모델 충돌은 발견하지 않았다. 같은 version 다른 지문 records의 collection 허용을 바꾸지 않고 후속 선택 snapshot 검증과 구별했으므로 frozen contract revision은 필요하지 않다. 향후 의미/API/지문 변경이 필요하면 기존 change-control을 별도로 따른다.

## 25. Historical Manifest·release와 분리

| 후속 필요 원본 | 필요한 이유 | 이번 계약의 한계 |
|---|---|---|
|Historical DatasetManifest|당시 dataset/전체 policy/source refs·engine artifact 선언|loader/raw schema까지 여기서 설계하지 않음 |
|당시 SourceRegistry snapshot|Registry fp의 실제 내용·source version/locator|Context의 hex equality로 원본을 대체 못 함 |
|Manifest 전체 PolicyEditionReference/Envelope 집합|전체 release 구성/정책·rule·source 대응|선택 Context/Envelope 하나로 전체 검증 못 함 |
|정확한 Coverage/Policy 원본|review refs·actual Inventory/Tree/subtree 결합|각 기존 historical loader의 별도 ref/B와 결합 필요 |
|개별 검토 원문·공식 source|review_artifact_ref의 실제 주장/권한/내용|opaque 문자열 복원으로 진실성 인증 못 함 |
|당시 implementation ZIP·프로파일·실행 환경|bytes identity와 실제 평가 코드 대응|metadata equality/M2.53 합성 verify-only로 대체 못 함 |

Context.dataset_version=R이어도 Manifest 전체 내용은 검증되지 않는다. Registry/engine 참조의 실제 bytes와 domain fp도 분리한다. Manifest.review_manifest와 Entry.coverage_reviews_ref를 자동으로 같은 원본이라고 강제하지 않는다. 기존 validate_dataset_manifest의 ENGINE_VERSION 호환 검사를 삭제한 새 validator를 만들지 않는다. 역사 환경이 맞지 않으면 외부 준비 부족을 명시한다.

## 26. Assumptions·미해결 사항

| 항목 | 명시 경계·상태 |
|---|---|
|A1 외부 R/root 신뢰|같은 호출의 실제 M2.57 반환값과 신뢰된 R 원본을 공급함. type/is는 발급/검토 진실성 인증이 아님 |
|A2 외부 보관본|선택 ref가 고정한 HRC1 원본 bytes를 확보함. 실제 안산 보관본/Acceptance는 이번에 발급하지 않음 |
|A3 외부 역사 의미/실행|공식 scope·검토 진실성·실행 ZIP 대응은 별도 준비. 충족됐다고 가정해 사용 승인하지 않음 |
|좁은 loader 계약|raw wrapper/version/필드/nullable/H/동일 bytes/constructor/5축 binding/API/20prefix/순서 확정. 추가 모델 변경 blocker 없음 |
|미완료 원본/기능|Historical Manifest/Registry strict 원본 준비·외부 orchestration·Content Validator·Source Gate·Acceptance evaluator/Bridge·역사 실행 환경 |

설계 선택(7절 wrapper B/HRC1,18~19절3인자/ACCEPTED 전용,12절5축 비교)은 이번 승인 범위의 명시 결정이다. 불확실한 공식 의미나 자료 존재를 임의로 PASS/검토 완료로 채운 Assumption과 구별한다. 후속 검토 ref 대응·subtree 검증·FULL 미완료는 이 좁은 loader 구현을 차단하는 모델 충돌이 아니다.

## 27. 최종 판단

**READY_TO_IMPLEMENT_HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER**

기존 Context7/Inventory review9/Implementation review15/Scope2를 정확하게 복원할 raw HRC1과, 독립 기대 H→동일 bytes→기존 constructors→당시 R의 Context baseline 대조가 닫혔다. 기존 frozen 모델/Review 의미를 변경할 이유는 없다. FULL/사람 검토/실제 실행 검증 완료를 선언하지 않는다.

## 28. 다음 최소 작업 하나

승인 후 **M2.66 — Historical CoverageReviewContext Strict Bytes Loader 구현** 한 개다.19절3인자 API·7~11절 raw/HRC1/복원·12/18절 Entry/baseline·21~22절 prefix/순서·23절 해당 합성 사례를 구현/검증한다.

기존 constructor를 사용한 새 bytes loader/합성 테스트와 필요한 최소 export/관련 문서 기록만 다음 구현 범위로 제안한다. 기존 core/loader 리팩터링·Review matching 재구현·Historical FULL/evaluator·Manifest Loader·Content Validator·Source Gate·Acceptance evaluator·Bridge/Cashflow·실제 정책 Artifact 생성은 다음 작업에 포함하지 않는다. 이번 M2.65에서는 구현하지 않는다.

## 29. 검증·보존 기록

- 작업 전 전체 pytest: **8,981 passed in 67.86s / skipped0 / failed0 / timeout0**. 최초 전체 실행이 통과했으며 재실행은 없었다.
- 신규 실행 테스트: **0개**. HRC01~HRC80은 문서 설계 사례80개다.
- 작업 후 전체 pytest: **8,981 passed in 48.00s / skipped0 / failed0 / timeout0**. 최초 작업 후 전체 실행이 통과했으며 재실행은 없었다. 전후 모두 기존8,981개 회귀이며 신규 실행 테스트0개다.
- 사전 보호 파일184개가 모두 SHA256까지 동일하다. 새 문서1개만 추가하여 최종185개이며 기존 파일 수정/삭제0개다. 실제 release6개는 SHA256·경로·크기·수정시각이 모두 같다.
- Python AST로 기존 Context7/Inventory review9/Implementation review15/Scope2 필드와 frozen/slots를 대조했다. 문서29개 절·HRC01~HRC80 연속/유일성·20개 오류 prefix·API 필수 keyword-only3개·논리 JSON 예시·table/fence·UTF-8/한국어를 검수했다. 문서 검수는 신규 테스트 수로 세지 않는다.
- 현재 대화 폴더와 기존 프로젝트 경로가 달라 실행 캐시 생성을 끄고 임시/테스트 산출물은 현재 허용 폴더에 두었다. 테스트 코드·기대값·timeout 설정·기존 프로젝트 설정 파일은 변경하지 않았다.
- 문서만 추가한다. 기존 코드/테스트/fixture/기대값/기존 문서·GV01~GV15/BV01~BV16·Coverage freeze·기존 Historical Loaders·Review Artifact loader·bootstrap/Cashflow·실제 releases는 보존한다.
- 실제 Context/Review/Acceptance/FULL/실행 ZIP을 생성하지 않았다. 문서의 합성 논리 예시는 실제 검토 발급 자료가 아니다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.


전후 동일한 실제 release SHA256(root: data/releases/):

| 기존 상대 경로 | 전후 동일 SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

## 30. M2.66 — IMPLEMENTED: Historical CoverageReviewContext Strict Bytes Loader

### 30.1 실제 API와 변경 파일

```python
load_historical_coverage_review_context_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> CoverageReviewContext
```

세 인자는 필수 keyword-only/exact 타입이다. subclass/dict/str/bytearray/memoryview를 자동 변환하지 않는다. 새 모듈 `backend/policy_engine/policy_data/historical_coverage_review_context_loader.py`, 새 합성 테스트 `tests/test_historical_coverage_review_context_loader.py`를 추가하고 package에 위 함수 하나만 export했다. 기존 모델·Review matcher·fingerprint·historical loaders·테스트·실제 release는 변경하지 않았다. 문서는 이 명세와 ARCHITECTURE만 갱신한다.

### 30.2 실제 P0~P8 경로

```text
exact bytes + 같은 호출의 실제 M2.57 Artifact + 외부 R 원본
  → ACCEPTED / root ref / 명시 유일 Entry / entry.acceptance is R
  → selected coverage_reviews_ref exact ArtifactReference
  → 해당 ref.sha256 대 동일 raw bytes 전체 SHA256
  → BOM / strict UTF-8 / JSON duplicate·number·Unicode scalar
  → wrapper2 / Context7 / Inventory review9 / Implementation review15 / Scope2
  → 같은 parsed root의 HRC1 bytes equality
  → Context scope / 각 Inventory(scope→date→constructor) / 각 Implementation / Context constructor
  → policy / scope / dataset / Registry / implementation baseline 순 대조
  → 기존 불변 CoverageReviewContext만 반환
```

선택 Entry의 독립 H만 기대값으로 사용하며 실제 digest/다른 ref/Registry/implementation fp로 대체하지 않는다. path를 열거나 hash 뒤 bytes를 다시 읽지 않는다. primitive 검사와 HRC1 비교 전에 raw defaults/date/배열을 바꾸지 않는다. wrapper schema는 domain 저장 필드가 아니다.

4/5/6절의 기존 Context7/Review9/Review15와 Scope2 생성자를 그대로 사용한다. 각 record scope는 해당 원문에서 따로 복원하고 Context scope로 덮어쓰지 않는다. exact date 변환 후 기존 constructor를 호출한다. 모든 review는 원문 순서/값으로 tuple에 담고, 최종 Context가 전체 ref 유일성/소속을 검사한다. 역사 version·지문·날짜 차이는 제거/정렬/자동 최신 선택/일괄 거부하지 않는다. 빈 두 tuple도 정상 복원한다.

### 30.3 오류·순수성·경계

21~22절의 **20개 prefix/P0~P8 순서**를 유지했다. 모든 깊이 decoded key 중복·NaN/Infinity·float/exponent·고립 surrogate를 거부한다. parse_int ValueError/발생한 JSON RecursionError는 기존 전역 제한 변경 없이 대응한다. 날짜 문자열의 타입은 P5, ASCII ISO/달력은 P6 DATE, 기존 constructor의 PolicyDataError는 P6 MODEL로 구분한다. MODEL field는 생성한 scope/record/Context의 고정 경로다. RuntimeError 같은 예상 밖 오류는 덮지 않는다.

SHA 실패 뒤 JSON/모델 복원을 하지 않고, missing→extra/형식→HRC1→모델/constructor→baseline 우선순위를 지켰다. 날짜 변환이 record constructor보다 앞서고, 전체 record 복원 뒤 Context의 중복/소속 검사가 수행되는 순서도 검증했다. 오류에 원본 값/unknown key/hash/ref/path/하위 오류를 복사하거나 실패를 MISSING/STALE/SLICE/UNUSABLE로 낮추지 않는다.

외부 filesystem/network/Git/env/current time/random/cache·ZIP/bootstrap·다른 historical loader·resolver/matcher·Inventory/Tree/subtree fp·Coverage Gate/factory/evaluator·Manifest/source validator를 실행하지 않는다. 모델·기존 함수의 복제 구현이나 generic framework도 없다. 반환은 기존 Context 하나다.

개별 review_ref 존재/종류·실제 Inventory/Binding/Tree/subtree·검토 원문 진실성·실제 implementation ZIP 대응은 입력에 없어 검증하지 않는다. Context baseline=R은 metadata 대응이며 실제 Registry/ZIP/Manifest 검증이 아니다. FULL/MATCHED/현재 USABLE/Policy VERIFIED/사용자 PASS/Cashflow를 생성하지 않는다. 기존 generic core의 matcher가 이미 구현돼 있다는 사실과 이 loader가 그 matcher를 실행하지 않는다는 사실은 별개다.

### 30.4 HRC01~HRC80 실행 대응과 합성 검증

신규 실행 테스트는 **440개**다. 문서80개 수동 사례를 이 수에 더하지 않았다. 모든 정상 end-to-end fixture는 실제 M2.57 loader 반환 root와 외부 R 원본을 사용한다. base HRC1은1628bytes, 고정 SHA256은 `fec6b234759aac68ab6ed851b2a81212c944f263cc28cdac40f90f4fbf886fd2`다. fixture 저작 시 고정한 기대 H를 소비하며 actual→expected 채택은 없다. 손상 schema/JSON 사례도 해당 손상 B의 H를 미리 준비해 P3 이후 오류를 검사한다.

| M2.65 수동 사례 | 이번 실행 대응 |
|---|---|
| HRC01~HRC18 | 빈/한 종류/혼합 Context·모든 저장 필드·역사 version/같은 version 다른 fp/날짜 공존·순서·scope·한국어 opaque ref·100회 결정성/불변성·다중 Entry/공유 bytes |
| HRC19~HRC34 |1byte/old H·잘못된 H·같은 path 다른 bytes·UTF-8/BOM/JSON·모든 object 깊이의 duplicate/escape key·HRC1·number/Unicode·격리 parser recursion/int 제한 |
| HRC35~HRC58 | wrapper/Context/두 Review/세 Scope의 required/extra/type/null·schema aliases·date 경계·기존 모델 grammar·두 종류 내부/간 duplicate·다른 소속·wrong record shape·파생 flag 거부·exact 인자/subclass |
| HRC59~HRC70 | Entry 원본 is/ref/revision/REVOKED·기존 생성 단계 ref/중복 Entry 거부·다섯 baseline 축·다중 오류 우선순위 |
| HRC71~HRC80 | 입력에 없는 Inventory/Binding/Tree/검토 원문/ZIP/Manifest/현재 사용 검증을 실행하지 않는 호출 격리 경계. 실제 후속 validation/검토 진실성을 실행 완료로 세지 않음 |

SHA spy는 같은 raw bytes 객체를 정확히 한 번 hash하고 그 bytes 내용의 decoded text를 한 번 parse함을 확인한다. 같은 parsed Context로 기존 constructors를 순서대로 호출하고, 생성된 Review/Scope/Context 객체를 그대로 반환 구조에 보존함도 확인했다. 입력 bytes/Artifact/Entry/R/ref 불변, frozen/slots, serializer snapshot 격리,100회 새 Context의 결정적 equality를 검증했다.

ACCEPTED None/wrong ref·duplicate Entry는 기존 모델이 진입 전에 막는다. 이 거부 테스트를 새 loader P2 방어 prefix의 정상 도달 사례라고 주장하지 않고 frozen 객체 강제 훼손도 하지 않았다. constructor의 PolicyDataError 변환과 RuntimeError 비은폐를 격리 실패 주입으로 확인했다.

### 30.5 구현 상태·남은 의존사항

**IMPLEMENTED:** Historical CoverageReviewContext strict bytes loader·기존 Inventory/Implementation Review와 Context 복원·Acceptance target/baseline 대조·합성 검증·public 함수1개.

**이번 경로에서 구현/실행하지 않음:** Review MATCHED 계산·Historical FULL 재현·Historical Manifest/Registry Loader·Source Gate·Content Validator·Acceptance Evaluator·same-call adapter·Bridge/Cashflow·실제 안산 ReviewContext/Acceptance/FULL/실행 ZIP 생성·검증.

다음 최소 작업은 **Historical DatasetManifest Artifact Preparation Contract 설계 한 개**다. M2.58에서 실제 필요한 dataset_manifest_ref의 당시 전체 release 원본과 기존 DatasetManifest를 대응시킬 strict schema/H/동일 bytes/정확한 저장 필드·engine 호환성/검증 범위부터 설계한다. Registry/source 전체 codec·Content Validator·역사 실행/사용 승인을 동시에 구현하지 않는다.

### 30.6 회귀·보존 기록

- 작업 전 전체 pytest: **8,981 passed in 68.62s / skipped0 / failed0 / timeout0**. 최초 전체 실행이 통과했다.
- 임시 작업 사본의 신규 합성 테스트: **440 passed in 1.99s**. 최초 신규 테스트 실행이 통과했다. 기존 tests/fixture/기대값·timeout 설정은 수정하지 않았다.
- 최종 전체 pytest: **9,421 passed in 51.77s / skipped0 / failed0 / timeout0**. 기존8,981개+신규440개다. 사전/작업 후 최초 전체 실행이 모두 통과했으며 실패/timeout/재실행은 없었다.
- SHA256 기준선189개 중186개는 동일하다. 변경3개는 package export와 이 명세/ARCHITECTURE이며 신규 loader/합성 테스트2개를 더해191개다(루트4개 포함). 기존 파일 삭제0개다. 기존 tests/fixture/기대값·모델·Review/Context/Scope·다른 historical loaders·Coverage 동결 코드/문서·fingerprints·bootstrap/Cashflow는 그대로다.
- 실제 release6개는29절 표의 SHA256과 모두 같고 경로·크기·수정시각도 동일하다. GV01~GV15/BV01~BV16을 보존했고 기존 전체 회귀가 통과했다. 실제 안산 원본/검토 기록/Acceptance/FULL/실행 ZIP을 생성하거나 기존 pretty-print releases를 재작성하지 않았다.
- 코드 AST/API·20개 오류 prefix·기존 저장 필드·문서30개 절/HRC80개·table/fence·UTF-8/한국어·변경 파일5개 범위를 검수했다. 해당 검수는 신규 실행 테스트 수로 세지 않는다. 현재 대화 폴더와 기존 프로젝트 경로가 달라 임시 작업 사본에서 신규 테스트를 먼저 검증한 뒤 위5개 파일만 반영했다. 기존 프로젝트 설정은 바꾸지 않았고 캐시/테스트 임시 산출물은 현재 허용 폴더에서 처리했다.
- 보호 기준선은 기존 backend/tests/data/docs/tools185개와 루트 설정/README4개, 총189개다. 실제 release6개는 SHA256/경로/크기/수정시각으로 별도 보호한다. GV01~GV15/BV01~BV16·Coverage freeze·기존 모델/loader·bootstrap/Cashflow·실제 releases를 유지한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

최종 판단: **HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER_COMPLETE**. 좁은 원본 복원 완료이며 전체 역사 검증/현재 사용 승인이 아니다.
