# M2.61 — Historical EligibilityCoverage Artifact Preparation Contract

최신 구현 상태는 **30절 M2.62**다. 1~29절은 승인된 M2.61 설계와 당시 검증 기록이며, 문서 전용/미구현 표기는 그 시점의 이력이다. 기존 Coverage 모델·지문·FULL/SLICE 의미는 변경하지 않았다.

## 1. 목적과 범위

`AcceptanceReviewEntry.coverage_snapshot_ref`가 고정한 과거 파일의 **검증된 동일 raw bytes**에서 기존 EligibilityCoverage를 복원하고, 확인 가능한 Inventory identity/version/fingerprint를 명시한 과거 Acceptance와 대조하는 계약이다.

이번 산출물은 이 문서 하나다. loader·파일 preparation·역사 Review/Manifest codec·Content Validator·Source Gate·Acceptance evaluator·Bridge/Cashflow를 구현하지 않는다. 실제 안산 Coverage Artifact/과거 FULL Result/금액/승인을 생성하지 않는다.

**최종 판단: READY_TO_IMPLEMENT_HISTORICAL_ELIGIBILITY_COVERAGE_LOADER.** 준비 완료 범위는 이 문서의 좁은 입력 복원 함수 하나다. Historical FULL 재현·전체 release 검증·전체 Content Validator 구현 준비 완료를 뜻하지 않는다.

## 2. Source of Truth·현재 검증 공백

| 확인 문서 | 유지할 계약 |
|---|---|
| HISTORICAL_BENEFIT_SNAPSHOT_ARTIFACT_PREPARATION_SPEC.md | M2.59의 동일 bytes/독립 hash/same-call 원본 원칙, M2.60의 실제 3인자 loader와 범위 |
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md | L1/L2/L3, Coverage bytes와 별도 typed 객체 혼합 공백, historical FULL/Source/사람 검토 분리 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md | Entry15·7참조의 의미·ACCEPTED/REVOKED·원본 분리 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC.md | M2.57의 Review raw SHA/외부 Acceptance20값 대조·원본 is 보존 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md | Acceptance21, 공유 target와 Coverage7binding, 발급 기준과 현재 사용 분리 |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | 외부 A/순수 B/same-call C, 전체 release와 역사 자료·현재 자료 분리 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS, 기존 모델/evaluator/지문/오류 의미 보호 |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md | Result8·private factory·파생 FULL_POLICY/CONDITION_SLICE |
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md | 로컬 모델 정합성 vs tree/ownership/composition/review 통합 검사 |
| COVERAGE_FINGERPRINT_SPEC.md | inventory/tree/subtree의 서로 다른 payload·조건 정렬·근거 순서·GV01~GV15 |
| COVERAGE_REVIEW_CONTEXT_SPEC.md | 현재 Context7 및 review9/15의 필드·명시 ref·정상 미검토와 broken ref |
| POLICY_DATA_ENVELOPE_SPEC.md | 실제 Envelope/Source/Manifest, 기존 JSON parser와 artifact raw SHA의 차이 |
| DATA_MODEL.md / ARCHITECTURE.md | 최신 구현 절과 과거 후보 구분·현재 실제 타입/공개 경계 |

실제 코드의 EligibilityCoverage/ConditionInventory/RequiredCondition/ConditionRequirement/ConditionBinding/ApplicabilityScope, Result/Status/private factory, ReviewContext와 두 review 타입, Policy/PolicyEnvelope, Inventory/Tree/subtree 지문, 공개 evaluator, Review 모델/loader, ArtifactReference/Acceptance, historical_benefit_snapshot_loader, PolicyDataError를 확인했다. parser/export 검색으로 **현재 Historical EligibilityCoverage strict bytes loader가 없고** Inventory/ReviewContext/Manifest의 역사 strict bytes codec도 없음을 확인했다. 기존 to_dict는 decoder가 아니다.

기존에는 bytes B의 raw SHA와 별도 Coverage C의 Inventory 지문이 각각 맞아도 C가 B에서 만들어졌다는 보장이 없다. 특히 Inventory 지문은 bindings와 completeness_review_ref를 포함하지 않아, 다른 Binding/root/review ref의 Coverage로 바꾸는 문제를 지문만으로 막지 못한다. 이번에는 ref → 동일 B → strict 복원 C → 실제 Inventory 지문 → R 대응을 한 순수 호출로 연결한다.

## 3. Coverage 입력·ReviewContext·Result의 차이

| 객체 | 실제 저장 구조 | 실제 보장/보장하지 않는 것 |
|---|---|---|
| EligibilityCoverage | inventory, bindings의2필드 | 조건 참조/중복의 로컬 정합성. Policy/tree·Review·dataset·상태 없음 |
| ConditionInventory | policy_id, scope, inventory_version, conditions, completeness_review_ref의5필드 | 의미 조건 목록. completeness ref는 nullable이고 실제 검토 여부는 모름 |
| CoverageReviewContext | policy_id, scope, dataset_version, source_registry_fingerprint, implementation_fingerprint, inventory_reviews, implementation_reviews의7필드 | review 타입/소속/ref 유일성. 실제 Coverage/tree와 matching·사람 검토는 별도 |
| EligibilityCoverageResult | policy_id, scope, inventory_version, rule_version, dataset_version, source_registry_fingerprint, implementation_fingerprint, findings의8필드 | 정상 생성은 private factory. 검증 findings로 FULL_POLICY/CONDITION_SLICE를 파생 |

Result의 `_creation_token`은 저장 필드가 아닌 InitVar이며 status도 stored field가 아니다. 최상위 Result에는 inventory_fingerprint/policy_tree_fingerprint라는 저장 필드가 없으나 **내부 findings에는 실제 두 지문이 있다**. 그것만으로 Coverage 입력/Review/공식 원문 파일 전체나 당시 실행 대응을 복원할 수는 없다.

입력 파일을 복원한 결과는 EligibilityCoverage다. Result/Context/FULL bool로 반환 대상을 바꾸지 않는다. 기존 evaluator의 정상 incomplete → CONDITION_SLICE와 데이터 모순 → PolicyDataError 계약은 그대로다.

## 4. coverage_snapshot_ref의 실제 의미

Entry.coverage_snapshot_ref의 실제 타입은 기존 `ArtifactReference | None`이다. ACCEPTED에는 nonnull이며 REVOKED에는 나머지6참조와 함께 None이다.

ArtifactReference는 frozen/slots, 정확히 `path: str`, `sha256: str` 두 필드다. path는 상대 slash 경로로 빈 segment/`.`/`..`/역슬래시/colon/control char/앞뒤 공백을 거부하고, sha256은 소문자 hex64다. version/source ID/content_hash 필드는 없다. 생성자는 파일을 열거나 내용·실재 경로를 검증하지 않는다.

coverage_snapshot_ref는 **이 Entry의 과거 EligibilityCoverage 입력 확인본 위치와 전체 bytes 기대 SHA**다. Policy Tree/ReviewContext/Result/FULL의 파일 참조로 확대하지 않는다. Review root의 문자열 `acceptance-review:sha256:H`와는 별도 타입·역할이다. 다른 Entry의 coverage_snapshot_ref나 accepted_terms_ref를 fallback으로 사용하지 않는다.

## 5. Raw Artifact 범위 — A안 선택

| 후보 | 검토 결과 |
|---|---|
| A: EligibilityCoverage의 Inventory+Bindings | 실제 모델과 정확히 대응하고 기존 policy_envelope_ref/coverage_reviews_ref의 독립 원본 책임을 유지한다. **선택** |
| B: Coverage+Policy Tree+Review metadata 통합 파일 | 기존 별도 참조와 내용을 복제하고 부분 변경/상호 대응 책임을 늘린다. 동결 모델에도 tree/review 필드가 없다. 미선택 |

한 Raw Coverage Artifact는 EligibilityCoverage의 저장 입력 전체를 보존한다. inventory 안 모든 conditions/evidence/completeness ref와 모든 bindings의 condition/root/implementation ref를 포함한다. 단순 Inventory 지문 payload만 저장하는 방식은 채택하지 않는다.

제외: Policy/Rule Tree, ReviewContext/검토 record 내용, status/findings/Result, dataset_version/Registry/implementation 지문, SourceBinding, Acceptance/Benefit identity, 준비/검토자, path/hash. 이들은 EligibilityCoverage 저장 필드가 아니다. wrapper의 schema_version만 외부 파일 형식 discriminator로 둔다. PolicyEnvelope.coverage는 legacy PolicyCoverage이며 여기의 EligibilityCoverage와 다른 타입이다.

## 6. 확정 Raw schema/version

Benefit historical 형식의 버전 wrapper 철학을 재사용하되 별도 Coverage 형식을 확정한다. 기존 실제 파일의 재사용/자동 migration은 없다.

| object 경로 | exact required keys (검사 순서) |
|---|---|
| root | schema_version, coverage |
| coverage | inventory, bindings |
| coverage.inventory | policy_id, scope, inventory_version, conditions, completeness_review_ref |
| coverage.inventory.scope | edition_id, quarter |
| coverage.inventory.conditions[i] | condition_id, meaning, requirement, evidence_refs |
| coverage.bindings[i] | condition_id, rule_root_id, implementation_review_ref |

root.schema_version은 exact str literal **`historical-eligibility-coverage-1.0`**이다. coverage는 exact object다. 전 항목의 key가 필수이며 completeness_review_ref의 constructor 기본값 None도 raw에서는 **명시 null**로 기록한다. missing을 기본값으로 복구하지 않는다. future/alias schema, unknown extra key, root에 coverage 대신 inventory/bindings만 놓는 형식은 거부한다.

| 저장 값 | raw 타입 → 기존 모델 값 | 구조 규칙 |
|---|---|---|
| inventory.policy_id | string → str | canonical `[A-Z0-9]+(?:-[A-Z0-9]+)*` |
| scope.edition_id | string → str | ASCII4자리. 기존 Scope가 허용하는 `0000`을 임의 금지하지 않음 |
| scope.quarter | integer 또는 null → exact int 또는 None |1~4 또는 연간(None). bool 불가 |
| inventory.inventory_version | string → str | i0001 이상 기존 버전 문법 |
| inventory.conditions | array[object] → exact tuple[RequiredCondition,...] | 비어 있지 않음, condition_id 유일, 원순서 |
| inventory.completeness_review_ref | string 또는 null → str 또는 None | 원문 비공백 opaque ref. path/SHA/실제 review 존재로 해석하지 않음 |
| condition.condition_id | string → str | **`[A-Z0-9_]+`**, policy ID 문법과 다름 |
| condition.meaning | string → str | 비공백, 원문 보존 |
| condition.requirement | string → 기존 ConditionRequirement | 정확히 REQUIRED 또는 CONDITIONAL |
| condition.evidence_refs | array[string] → exact tuple[str,...] | nonempty, 기존 source#locator 문법, 순서/중복 보존 |
| coverage.bindings | array[object] → exact tuple[ConditionBinding,...] | **빈 목록 허용**, 원순서 |
| binding.condition_id | string → str | 기존 ID 문법·Inventory에 존재·Binding 안 condition_id 유일 |
| binding.rule_root_id | string → str | 비공백 원문. 이 단계에서 Policy root lookup 없음 |
| binding.implementation_review_ref | string → str | 비공백 원문. **null 불가**, Review 조회 없음 |

날짜/시각 필드는 없다. Scope에서 지급월/정책 분기를 추론하지 않는다. RequiredCondition과 Binding에 없는 source version/검증 status를 추가하지 않는다. 같은 root/review 문자열이 서로 다른 condition에 재사용되는 경우의 의미·소유 검증은 Policy/Review를 받는 후속 evaluator 책임이다.

## 7. Canonical bytes — HC1

HC1은 위 raw 전체에 대한 별도 규약이다. 기존 canonical JSON 철학을 재사용한다.

```python
json.dumps(
    raw_payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8", errors="strict")
```

모든 object key 정렬, compact separators, strict UTF-8, BOM/최종 newline 없음이다. Unicode NFC/NFD/공백/대소문자를 정규화하지 않는다. 한글은 원문 문자로 인코딩하고 escape는 위 recipe의 정확한 결과를 따른다. null은 명시 nullable 항목에만 쓰며 Enum은 value 문자열이다. int는 quarter의 exact int이고 bool을 int로 취급하지 않는다.

모든 배열은 입력 순서와 중복을 보존한다. raw conditions를 ID순 정렬하지 않는다. **Inventory 지문 함수가 자기 projection의 조건만 정렬하는 것과 구별한다.** raw의 bindings/completeness ref/조건 순서 변경은 전체 bytes SHA의 변경 대상이다. JSON 의미가 같아도 구조 공백/key순서/escape/newline/-0 표현이 HC1과 다르면 거부한다.

중복 JSON key·NaN/Infinity·float/exponent number·고립 surrogate는 거부한다. strict parse 후 raw 전체를 HC1로 재인코딩한 bytes와 원래 B를 비교한다. 재작성 bytes로 B를 교체하거나 hash 대상에 사용하지 않는다. RFC 범용 canonicalization framework를 도입하지 않는다.

## 8. 독립 expected SHA256

유일한 기대 raw SHA 원천은 **선택 Entry.coverage_snapshot_ref.sha256**이다. 별도 index/Manifest lookup/새 모델은 필요하지 않다. trusted R.review_artifact_ref → 실제 M2.57의 Review bytes SHA/원본 대조 → selected Entry → Coverage 기대 H라는 연결이다.

actual `sha256(B).hexdigest()`를 H와 비교한다. actual 값을 기대값으로 채택하거나 Inventory/Tree 지문으로 raw H를 대신하지 않는다. ref.path는 외부 원본 위치이며 내용 hash가 아니다. 소비 중 ref/H를 바꾸면 같은 검토 원본을 소비하는 것이 아니다.

같은 Inventory 지문을 가진 다른 bindings/review refs의 Coverage도 raw 전체 H가 독립적으로 고정하므로 old H로 바꿔치기하면 실패한다. 반대로 새로운 독립 검토 원본이 다른 H를 정당하게 고정했다면 그 사실을 Inventory 지문만으로 기존 파일과 동일하다고 주장하지 않는다. 실제 보관본/검토 권한 진실성은 hash가 보장하지 않는다.

## 9. 동일 bytes 복원·strict parsing

외부가 정확한 ref.path에서 immutable exact bytes B를 한 번 확보한다. 순수 loader는 B 전체 hash → 바로 그 B.decode(strict UTF-8) → JSON parse → 기존 모델 복원을 수행한다. 파일 A/B 혼합 또는 같은 경로 이중 읽기를 하지 않는다. 완성된 Coverage를 외부 인자로 받아 교체하지 않는다.

| 검사 | 확정 계약 |
|---|---|
| 입력 | exact bytes만. str/bytearray/memoryview/subclass/file-like/raw dict/tuple 거부 |
| encoding | raw SHA 성공 뒤 BOM 거부 → strict UTF-8 |
| JSON | malformed/trailing garbage 거부, object_pairs_hook 방식으로 모든 깊이의 decoded key 중복 거부 |
| numbers | parse_constant/parse_float 거부; parse_int ValueError도 number 오류. 전역 정수/recursion 제한 변경 없음 |
| Unicode | parse 결과 key/value의 잔류 U+D800~U+DFFF 거부. 유효 scalar도 최종 HC1 bytes를 만족해야 함 |
| schema | root2/coverage2/inventory5/scope2/condition4/binding3 exact key 집합, missing 먼저/extra 다음 |
| primitive | exact dict/list/str/int/nullable 검사. bool-as-int/null-as-missing/문자열 숫자 변환 없음 |
| canonical | raw 전체 HC1 equality. 실패 시 자동 canonical 복구 없음 |
| domain | 기존 constructor invariants 재사용. 의미 검증의 불필요한 중복 구현 없음 |

JSON array를 tuple로 복원하는 것은 명시한 codec 대응이다. JSON 자체에 tuple 타입은 없으며 object로 바뀐 배열이나 Python tuple을 raw API에 직접 공급하는 것은 별도 타입 오류다. `completeness_review_ref=null`은 허용하지만 Binding ref의 null은 거부한다. sort/dedupe/trim/누락 Binding·review ref 생성/현재 Policy의 조건 보충은 없다.

## 10. 기존 모델로 복원하는 순서

후속 구현은 P5에서 모든 shape/primitive/HC1을 검사한 뒤 P6에서 다음 순서를 따른다.

1. scope.edition_id/quarter로 기존 ApplicabilityScope 생성.
2. conditions 원순서로 ConditionRequirement(value) 변환 후 기존 RequiredCondition 생성. evidence array는 원순서 tuple.
3. 기존 ConditionInventory에5개 값 모두 전달. completeness_review_ref도 명시 None/원문 전달.
4. bindings 원순서로 기존 ConditionBinding 생성.
5. 기존 EligibilityCoverage(inventory, tuple(bindings)) 생성.

별도 HistoricalCoverage 모델은 없다. 기존 생성자가 검사하는 중복 condition·빈 Inventory·존재하지 않는 Binding condition·중복 Binding을 재사용한다. bindings 빈 tuple/일부 Binding 없음/completeness ref None은 기존 모델대로 허용한다.

RequiredCondition의 evidence ref 문법은 기존 parse_evidence_ref를 재사용하지만 Registry lookup/ACTIVE/VERIFIED/공식 내용·source version·실제 Review 존재는 조회하지 않는다. evidence 중복을 loader에서 새로 금지하지 않는다. rule_root_id의 실제 존재/ownership/composition은 이 생성 순서로 검증되지 않는다.

## 11. Inventory fingerprint와 전체 파일 SHA의 차이

복원 C의 **실제 C.inventory**에 기존 `fingerprint_condition_inventory(C.inventory)`를 호출한다. schema는 기존 `coverage-inventory-1.0`을 유지하고 GV01~GV15를 변경하지 않는다.

기존 Inventory payload5는 fingerprint_schema, policy_id, scope, inventory_version, conditions다. 각 조건은 condition_id/meaning/requirement/evidence_refs4이며 조건만 ID순 정렬한다. evidence 순서/중복·원문 문자열은 유지한다.

제외 항목은 completeness_review_ref, bindings 전체, Rule Tree/ReviewContext, dataset/Registry/implementation, status다. 따라서 다음을 구별한다.

| 변화 | Inventory 지문 | Historical raw 파일 |
|---|---|---|
| 같은 조건의 순서만 변경 | 동일할 수 있음 (기존 정렬 규칙) | 원순서 보존이므로 bytes/H 변경 |
| completeness review ref만 변경 | 동일 | raw 안 포함되므로 bytes/H 변경 |
| bindings/root/implementation ref/순서 변경 | 동일 | raw 안 포함되므로 bytes/H 변경 |
| 조건 meaning/근거/requirement/version 변경 | 기존 정의 payload에 따라 변경 | raw도 변경 |

독립 H로 검증한 같은 bytes에서 C 전체를 만든 후 Inventory 지문을 대조해야 한다. Inventory 지문만으로 C 전체/공식 조건 목록 완결성/FULL을 보증하지 않는다.

## 12. Rule Tree fingerprint의 별도 책임

EligibilityCoverage에는 Policy가 없다. `coverage_rule_version`/`coverage_policy_tree_fingerprint`를 이 파일만으로 검사할 수 없다. 당시 Policy는 별도 **entry.policy_envelope_ref**의 PolicyEnvelope.policy에서 확보하는 경로를 유지한다.

현재 `parse_policy_envelope(data)`와 `load_policy_envelope(path)`는 실제로 존재한다. 전자는 구조 object parser이며 m1.1의 parse_policy_set을 재사용한다. 후자는 UTF-8 파일 읽기·중복 key/비정상 상수 검사를 제공하지만 expected raw SHA를 인자로 받거나 HC1 canonical 검사를 하는 함수는 아니다. **hash용 읽기 후 load_policy_envelope로 재읽는 것으로 동일 bytes를 증명하지 않는다.** 후속 preparation에서 고정 ref의 동일 bytes 검증/strict JSON → 기존 parse_policy_envelope를 연결하는 별도 경계를 확정해야 한다. 이 문서에서 그 codec을 새로 구현/완료 선언하지 않는다.

그렇게 확보한 당시 Envelope.policy에 기존 `fingerprint_policy_tree(policy)`를 적용하고 policy_id/rule_version/실제 Tree 지문을 R과 대조하는 것은 후속 역사 준비/Content 검증 책임이다. 각 Binding root는 기존 lookup/ownership/구조 검증으로 연결하며 실제 root에 `fingerprint_rule_subtree(root)`를 사용한다. Tree/subtree 지문을 새로 구현하지 않는다.

Policy에는 scope/edition 필드가 없다. Envelope.edition_id와 Inventory.scope.edition_id는 비교할 수 있지만 Envelope에도 quarter는 없어 annual/Q3를 공고일로 추론하지 않는다. legacy Envelope.coverage/evaluation_scope를 generic FULL_POLICY로 바꾸지 않는다.

## 13. ReviewContext와 검토 metadata의 별도 책임

**entry.coverage_reviews_ref**는 당시 CoverageReviewContext와 그 records를 준비해야 할 독립 참조다. Coverage 파일은 completeness_review_ref/implementation_review_ref 문자열만 보존하며 record를 생성하지 않는다. 현재 역사 ReviewContext strict bytes codec은 없다.

실제 InventoryCompletenessReview는9필드로 review_ref/policy/scope/inventory version·fp/dataset/Registry/reviewed_at/review_artifact_ref를 갖는다. ImplementationBindingReview는15필드이며 이에 condition/root, rule version·Tree fp/subtree fp·implementation fp 등의 대응을 기록한다. Context7은 dataset/Registry/implementation baseline과 두 records tuple을 갖지만 그 baseline을 Coverage 입력에 저장하지 않는다.

후속에는 같은 bytes에서 복원한 당시 Context의 policy/scope를 C.inventory와, dataset/Registry/implementation을 R 및 당시 release와 대조한다. 명시 completeness/implementation refs를 기존 resolver/matcher로 연결하고 actual Inventory/Tree/subtree 지문과 condition/root/version을 비교한다. 임의 MATCHED·missing review record·새 최신 ref를 만들지 않는다.

순수 Coverage loader는 Context를 입력받지 않아 그 부재로 좁은 복원을 실패시키지 않는다. 후속 evaluator에서 Context=None은 정상 검토 미확인으로 FULL 불가다. **Context가 제공됐는데 명시 ref가 없거나 종류/대상이 틀린 것**은 기존 broken reference Data Error다. 당시 Content 검증에 필수인 Review 원본 미확보는 외부 준비 미완료이며 정상 미검토를 이유로 전체 역사 검증 성공을 선언하지 않는다.

## 14. Implementation Artifact 경계

R.coverage_implementation_fingerprint, 당시 Context.implementation_fingerprint, ImplementationBindingReview.implementation_fingerprint는 비교할 기대 metadata다. 실제 실행물의 확보·raw SHA·동일 bytes 코드 실행 대응은 별도 외부 책임이다.

entry.implementation_artifact_ref는 기존 path/sha256 참조다. Manifest.engine_artifact_sha256와 implementation fp를 같은 source ZIP에 결합하는 것은 M2.52의 공유 ZIP 프로파일이 해당 역사 자료에 적용되는 경우의 규칙이다. 모든 hash 역할을 무조건 같다고 강제하거나 과거 label을 새 SHA로 수정하지 않는다.

M2.53의 실제 구현은 **합성 ZIP verify-only**다. production artifact 발행·당시 업무 worker 실행·FULL 계산 재현은 완료되지 않았다. 이번 Coverage loader는 ZIP을 읽거나 검증/실행하지 않는다. 같은 hex 문자열의 존재나 값 일치만으로 그 구현에서 평가됐다고 선언하지 않는다.

## 15. dataset/Registry provenance

EligibilityCoverage/ConditionInventory/RequiredCondition/ConditionBinding/Scope에는 dataset_version/source_registry_fingerprint/SourceBinding/implementation_fingerprint가 없다. raw에 새 필드로 끼워 넣거나 현재 release에서 채워 넣지 않는다.

| Acceptance 축 | 필요한 당시 실제 원본/검증 | 이번 loader |
|---|---|---|
| policy_id/scope | C.inventory, 당시 Context/Benefit, Envelope policy/edition | C.inventory와 R의 policy/scope만 검사 |
| coverage_inventory_version/fingerprint | C.inventory와 실제 기존 지문 계산 | 검사 |
| coverage_rule_version/policy_tree_fingerprint | 당시 Envelope.policy와 실제 Tree 지문 | 제외 |
| coverage_dataset_version | 당시 Envelope.dataset_version/Manifest.dataset_version/Context.dataset_version | 제외 |
| coverage_source_registry_fingerprint | 실제 당시 Registry의 fingerprint_source_registry, Manifest의 Registry ref, Context | 제외 |
| coverage_implementation_fingerprint | 당시 Context/record, 실제 artifact·명시 실행 대응 | 제외 |

전체 provenance 검증은 같은 bytes에서 확보한 각 원본을 후속 Content Validator/외부 준비에 공급해야 한다. 전체 Manifest policy 집합과 Registry/SourceBinding/document version을 기존 검증기로 대조한다. Manifest의 engine version이 현재 실행 코드와 비호환이면 당시 검증 환경 준비 문제이며 기존 validator의 ENGINE_VERSION 비교를 삭제하지 않는다.

Entry.source_bindings는 기존 **당시 Envelope∪Benefit** 합집합 계약이다. Inventory refs가 그 밖의 source를 사용한다는 이유만으로 이 모델을 오류로 만들거나 Entry에 source binding을 몰래 추가하지 않는다. Inventory 검토 원문/Registry·문서 version의 확인은 당시 Coverage Review 준비 책임으로 남긴다. 이 때문에 기존 source binding 모델/합집합의 개정을 요구하지 않는다.

## 16. Acceptance Entry identity·ACCEPTED 전용

같은 호출의 실제 M2.57 반환 Artifact와 그때 공급한 외부 R을 사용한다. R.status는 ACCEPTED여야 하며 root.review_artifact_ref == R.review_artifact_ref, R.acceptance_ref로 유일 Entry 조회, **entry.acceptance is R**를 확인한다. 같은 값의 복사본·다른 revision/target·같은 benefit_id의 임의 Entry·first/latest 선택을 허용하지 않는다.

그 Entry.coverage_snapshot_ref만 기대 원본으로 쓴다. 여러 Entry가 같은 파일/정의를 정당하게 공유할 수는 있다. 다른 Entry bytes가 우연히 정확히 같은 bytes라면 물리 파일 출처는 bytes만으로 구별되지 않으며 정확한 path 확보 책임은 외부다.

REVOKED의 None 참조는 그대로다. 직접 입력하면 subject 오류이며 가짜 Coverage를 붙이지 않는다. 철회 대상 A의 원본이 필요하면 기존 Context 관계를 통해 A와 A의 실제 Review Artifact를 별도로 준비하는 후속 경로를 유지한다. 이번 함수가 Context graph를 해석하거나 B를 A로 바꾸지 않는다.

## 17. 확정한 후속 pure loader API

다음 함수는 **아직 구현되지 않았다**. 다음 승인 후 구현할 최소 API다.

```python
load_historical_eligibility_coverage_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> EligibilityCoverage
```

3개 모두 필수 keyword-only, 기본값 없음. 후속 모듈 후보는 `backend/policy_engine/policy_data/historical_eligibility_coverage_loader.py`다. 기존 Benefit historical 사용 패턴을 유지하며, convenience를 위해 tree/Context/Manifest/evaluator/status/skip 옵션을 추가하지 않는다.

| 입력 | 독립 원본/기대값 | 확인 못 하는 가정 |
|---|---|---|
| raw_bytes | actual exact bytes. 선택 ref.sha256이 별도 기대값 | 실제 opened path·보관소 신뢰 |
| artifact | 같은 호출의 실제 M2.57 반환값. selected coverage ref를 공급 | 타입/is만으로 실제 loader 통과를 인증할 수 없음 |
| expected_acceptance | 신뢰된 과거 R 원본. Inventory target/version/fp를 고정 | 실제 발급 권한·사람 검토·누락 없는 이력 |

new VerifiedCoverage/PreparedResult/approval bool은 없다. expected digest/ref를 따로 받지 않아 다른 Entry ref를 섞을 슬롯을 만들지 않는다. 반환은 기존 EligibilityCoverage 하나이며 source/path/hash/status를 저장하지 않는다.

## 18. 성공의 정확한 보장 범위

성공은 **정확한 Entry가 고정한 raw SHA와 일치하는 동일 bytes에서 기존 모델로 구조적으로 유효한 Coverage를 복원했고, 그 Inventory policy/scope/version/실제 지문이 R에 대응한다**는 뜻이다.

R의 비교 축은 다음 순서다: C.inventory.policy_id == R.policy_id, C.inventory.scope == R.scope, C.inventory.inventory_version == R.coverage_inventory_version, fingerprint_condition_inventory(C.inventory) == R.coverage_inventory_fingerprint. 지문이 이 identity를 포함하더라도 개별 비교를 생략하지 않는다.

Coverage에는 benefit_id/acceptance_version이 없다. 그 값을 새로 만들지 않는다. R의 revision/benefit/Coverage7binding/날짜/status는 M2.57의 원본20값 대조와 이번 is 결합으로 특정한다. Coverage 파일 자체가 그 모든 축을 검사한 것으로 보고하지 않는다.

보장하지 않음: 실제 Rule Tree/Review/Manifest/Registry/ZIP 원본 검증, 공식 내용/사람 검토, 과거 FULL, Policy VERIFIED, 현재 Acceptance USABLE, 개인 eligibility/지급/Bridge/Cashflow. 역사 Inventory와 현재 Inventory의 정상 변경 판단은 후속 현재 evaluator 책임이다. R의 과거 원본으로 다른 version을 공급한 것은 정상 stale가 아닌 대응 오류다.

## 19. Data Error·정상 incomplete·준비 실패

| 사례 | 책임·분류 |
|---|---|
| hash/encoding/JSON/key/type/Enum/기존 모델 구조 불량 | loader의 PolicyDataError. 부분 Coverage 반환 없음 |
| R/Entry 원본 대응 실패·다른 policy/scope/version/fp | loader의 대응 Data Error. 정상 상태로 강등하지 않음 |
| Binding 일부/전체 없음·completeness_review_ref None | 기존 모델상 유효하면 정상 Coverage 복원. FULL 생성 없음 |
| Binding condition이 Inventory 밖/같은 condition 중복 | 기존 EligibilityCoverage 생성 오류 |
| root 문자열이 비공백이나 실제 Policy에 없음 | 좁은 loader만으로 검사 불가. 후속 실제 Policy와 구조 검증 시 Data Error |
| Context=None | loader 입력 밖. evaluator에서는 정상 검토 미확인/FULL 불가 |
| 제공 Context에서 명시 ref 부재/다른 종류·대상 | 후속 resolver/matcher의 기존 Data Error |
| 실제 Coverage 파일 미확보·필수 당시 Tree/Review/Manifest 미확보 | 외부 준비 실패/미완료. 확보된 Coverage의 좁은 복원과 전체 검증 성공을 구별 |
| 현재 자료가 정상 변경됨 | 후속 current gate가 별도 판단. 과거 원본으로 자동 교체하지 않음 |

구조적으로 incomplete한 C와 R의 Inventory binding이 맞으면 좁은 loader는 성공할 수 있다. 그것은 FULL 요구 발급 기준이 충족됐다는 승인이 아니다. 후속 역사 검토/FULL 근거가 부족하면 전체 사용 경로는 닫힌 채 유지한다. 독립 모순을 CONDITION_SLICE/UNUSABLE/BENEFIT_METADATA_NOT_REVIEWED로 숨기지 않는다.

## 20. 후속 오류 prefix와 validation precedence

새 예외 계층 없이 기존 PolicyDataError와 안전한 field 경로만 사용한다. raw 데이터/ref/path/actual·expected 값/unknown extra key 내용을 출력하지 않는다. signature 위반·필수 인자 누락은 일반 Python TypeError다. 아래 **19개 prefix**는 후속 구현 계약이며 현재 callable 오류가 아니다.

| phase | exact prefix | 조건 |
|---|---|---|
| P0 | INVALID_HISTORICAL_COVERAGE_LOADER_INPUT | raw_bytes/artifact/expected_acceptance exact 타입 |
| P1 | HISTORICAL_COVERAGE_REVIEW_BINDING_MISMATCH | ACCEPTED/root ref/유일 Entry/is 실패 |
| P2 | INVALID_HISTORICAL_COVERAGE_EXPECTED_REF | selected coverage_snapshot_ref nonnull/exact ArtifactReference 실패 |
| P3 | HISTORICAL_COVERAGE_BYTES_MISMATCH | B 전체 SHA와 독립 ref.sha256 불일치 |
| P4 | INVALID_HISTORICAL_COVERAGE_ENCODING | BOM/invalid UTF-8 |
| P4 | INVALID_HISTORICAL_COVERAGE_JSON | JSONDecodeError/발생한 RecursionError |
| P4 | DUPLICATE_HISTORICAL_COVERAGE_JSON_KEY | decoded key 중복 |
| P4 | INVALID_HISTORICAL_COVERAGE_NUMBER | float/exponent/NaN/Infinity·parse_int ValueError |
| P4 | INVALID_HISTORICAL_COVERAGE_UNICODE | parse 결과의 고립 surrogate |
| P5 | INVALID_HISTORICAL_COVERAGE_FIELDS | missing 또는 extra key |
| P5 | INVALID_HISTORICAL_COVERAGE_SCHEMA | 지원하지 않는 schema literal |
| P5 | INVALID_HISTORICAL_COVERAGE_TYPE | raw primitive/object/list/int/nullable 위반 |
| P5 | NONCANONICAL_HISTORICAL_COVERAGE_BYTES | 원본 B != HC1 bytes |
| P6 | INVALID_HISTORICAL_COVERAGE_VALUE | ConditionRequirement 변환의 ValueError |
| P6 | INVALID_HISTORICAL_COVERAGE_MODEL | 기존 constructor PolicyDataError |
| P7 | INVALID_HISTORICAL_COVERAGE_FINGERPRINT | 기존 Inventory 지문 함수 PolicyDataError의 방어 경계 |
| P8a | HISTORICAL_COVERAGE_IDENTITY_MISMATCH | policy_id → scope 순 첫 불일치 |
| P8b | HISTORICAL_COVERAGE_INVENTORY_VERSION_MISMATCH | inventory_version 불일치 |
| P8c | HISTORICAL_COVERAGE_INVENTORY_FINGERPRINT_MISMATCH | 계산한 실제 Inventory 지문 불일치 |
| P9 | 오류 없음 | 기존 EligibilityCoverage만 반환 |

세부 순서는 다음과 같다.

1. P0 raw_bytes → artifact → expected_acceptance exact 타입.
2. P1 ACCEPTED → root ref → acceptance_ref 유일 조회 → entry.acceptance is R. P2 해당 coverage_snapshot_ref 타입/nonnull. 생성 완료 객체의 원래 invariant를 다시 구현하지 않는다.
3. P3 B 전체 SHA 비교 후에만 decode/parse. 실제 경로는 열지 않는다.
4. P4 BOM → strict UTF-8 → JSON parser → Unicode scalar 순. duplicate/number/syntax 복합 오류는 parser에서 실제 먼저 발견한 사건을 보고한다. 전역 제한 변경/손상 JSON 계속 해석 없음.
5. P5 root object/key 집합 → schema 타입/literal → coverage object/key 집합 → inventory5와 nested scope/conditions의 표6 순 타입/shape → bindings의 원순서 타입/shape → HC1 equality. 각 object는 기대 key 순 missing을 먼저 찾고 extra를 그 다음 본다.
6. P6 scope → 조건 원순서 Enum/RequiredCondition → ConditionInventory → Binding 원순서 → EligibilityCoverage. 기존 constructor 내부 우선순위를 바꾸지 않는다.
7. P7 실제 복원 Inventory에 기존 지문 함수1회. P8 policy_id → scope → inventory_version → 실제 지문 순 대조. 지문에 identity가 포함돼도 먼저 identity 오류를 보고한다.
8. P9 전체 성공 때만 새 C 반환. 상태 문자열/부분 값/기본 Coverage 없음.

예를 들어 H가 틀리면 invalid JSON보다 P3가 먼저다. unknown Enum+공백이면 P5 canonical이 먼저고, canonical raw의 unknown Enum은 P6 VALUE다. ID/version/fp가 모두 틀리면 P8의 identity→version→fp 순서다. constructor와 지문 함수의 PolicyDataError만 좁게 대응하고 예상 밖 모든 Exception을 포괄적으로 데이터 오류로 덮지 않는다.

중복 Entry/ACCEPTED의 None ref는 기존 Review 모델이 정상 생성 단계에서 이미 거부한다. 후속 loader에도 방어 검사는 유지하되 실행 테스트를 위해 frozen 모델을 강제로 훼손하지 않는다. 기존 Review/Benefit loader의 prefix나 Coverage evaluator 오류/정상 상태를 변경하지 않는다.

## 21. 동결 Coverage 보호

후속 codec은 동결 모델 바깥의 새 모듈에 둔다. EligibilityCoverage/Result/Status/공개 evaluator/private factory/Review matching/Integration Gate/Inventory·Tree·subtree schemas·GV를 수정하지 않는다. 새 stored field나 source-binding 개정으로 문제를 우회하지 않는다.

이번 설계의 exact2/5/4/3/2 구조는 기존 constructor로 복원 가능하다. raw wrapper만 새 외부 형식이며 내부 모델 변경이 필요한 충돌은 발견하지 못했다. Generic core의 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS** 상태·실제 정책 blocker를 유지한다.

## 22. Historical FULL 재현 한계

정상 FULL은 기존 `evaluate_eligibility_coverage(coverage, policy, review_context=None)`의 구조/ownership/미매핑/composition/actual 지문/review matching 결과에서 파생된다. ReviewContext 부재 또는 정상 incomplete는 FULL이 아니다. 선언된 ref의 broken relation 같은 독립 모순은 Data Error다.

raw status="FULL_POLICY"를 믿거나 Result constructor/private factory/token을 사용해 강제로 만드는 경로는 없다. 원본 범위 밖 status/findings/Result key는 schema extra 오류다. 현재 Context를 과거 검토 원본 대신 넣지 않는다.

과거 FULL 재현에는 정확한 당시 C/Policy/Context와 검토 대상 implementation·실행 환경의 대응이 필요하다. 현행 구현으로 얻은 FULL에 과거 implementation SHA만 붙이지 않는다. 동일 구현 실행을 확보하지 못하면 역사 재현 환경 미완료라고 보고한다.

M2.58의 결정대로 **Content Validator는 evaluator를 자동 재실행하지 않고 외부 FULL bool/미리 계산한 Result도 받지 않는다.** 당시 trusted producer/검토 근거를 준비하고, 실제 재현이 필요하면 검증한 당시 실행 환경에서 공식 evaluator를 별도로 실행한다. current C의 현재 producer 실행은 별도다. 이 좁은 loader의 READY를 그러한 전체 실행 준비로 확대하지 않는다.

## 23. 합성 시나리오 — HC01~HC72

**72개 문서 사례**, 이번 신규 실행 테스트 **0개**다. 후속 구현에서 해당 순수/경계 사례만 실제 실행 테스트로 전환한다. E=신뢰된 R 원본+실제 M2.57 반환 root/entry, H=그 entry.coverage_snapshot_ref의 고정 raw SHA, I=R의 policy/scope/inventory_version, F=R의 Inventory fp다. T/V/L=각각 별도 당시 Tree/Review/release·실행 원본이다.

H/F는 합성 fixture 저작 시 독립 기대값으로 고정한다. 원본 H를 유지한 byte 변형은 P3 실패를 검증한다. P4 이후 오류는 손상 raw 자체에 맞는 H를 fixture에 미리 고정하여 앞 단계를 통과시킨다. 소비 중 actual hash를 expected로 채택하지 않는다. 정상 API 사례는 실제 M2.57 반환 root/R을 사용한다.

| ID | 입력 | 기대 결과 | phase | 담당 | 독립 기대값 | 후속 실행 테스트 |
|---|---|---|---|---|---|---|
| HC01 | exact wrapper/모델 전체 raw | 기존 Coverage 반환 | P9 | loader | E/H/I/F | 가능 |
| HC02 | 정확한 고정 ref SHA | raw 전체 대응 성공 | P3→P9 | loader | E/H/I/F | 가능, path 인증 별도 |
| HC03 | 명시 Q3/annual 각각 정상 | scope 원값 보존 | P9 | loader | 각 E/H/I/F | 가능 |
| HC04 | 정확한 inventory_version | 버전 대응 성공 | P8b | loader | E/H/I/F | 가능 |
| HC05 | 기존 Inventory fp와 정확히 일치 | 실제 지문 재계산 성공 | P8c | loader | E/H/I/F | 가능, GV 불변 |
| HC06 | 일부 condition Binding 없음 | 정상 구조 복원, FULL 아님 | P9 | loader | E/H/I/F | 가능 |
| HC07 | bindings=[] | 빈 tuple 복원, FULL 없음 | P9 | loader | E/H/I/F | 가능 |
| HC08 | 다수 조건/Binding | 원순서·참조 보존 | P9 | loader | E/H/I/F | 가능 |
| HC09 | 비공백 review refs에 앞뒤 공백 | 원문 그대로, trim 없음 | P9 | loader | E/H/I/F | 가능 |
| HC10 | completeness_review_ref=null | None 복원, 검토 생성 없음 | P9 | loader | E/H/I/F | 가능 |
| HC11 | 같은 조건 순서만 다름 | 원순서 보존·F 동일 가능·H 별도 | P9 | loader | 각각 고정 E/H, 같은 I/F | 가능 |
| HC12 | Binding 순서만 다름 | 원순서 보존·raw identity 구분 | P9 | loader | 각 E/H/I/F | 가능 |
| HC13 | 조건 evidence 중복/순서 | 그대로 보존, Registry 미조회 | P9 | loader | E/H/I/F | 가능 |
| HC14 | 한국어/NFC/NFD meaning | 정규화 없이 보존 | P9 | loader | 각각 고정 E/H/I/F | 가능 |
| HC15 | 동일 입력100회 | 값/지문 결정적·입력 불변 | P9 | loader | 고정 E/H/I/F | 가능, 사례1개 |
| HC16 |1byte 변경, H 유지 | BYTES_MISMATCH | P3 | loader | 원본 E/H | 가능 |
| HC17 | 기대 H만 다른 고정값 | BYTES_MISMATCH | P3 | loader | 독립 E/H | 가능 |
| HC18 | 같은 filename 다른 bytes | BYTES_MISMATCH | P3 | loader/외부 | 원본 E/H | bytes 부분 가능 |
| HC19 | invalid UTF-8, H 대응 | ENCODING | P4 | loader | 손상 bytes 고정 E/H | 가능 |
| HC20 | BOM, H 대응 | ENCODING | P4 | loader | 손상 bytes 고정 E/H | 가능 |
| HC21 | malformed/trailing JSON | JSON | P4 | loader | 손상 bytes 고정 E/H | 가능 |
| HC22 | root 중복 key | DUPLICATE_JSON_KEY | P4 | loader | 손상 bytes 고정 E/H | 가능 |
| HC23 | nested 중복/같은 decoded escape key | DUPLICATE_JSON_KEY | P4 | loader | 손상 bytes 고정 E/H | 깊이별 가능 |
| HC24 | wrapper required key 누락 | FIELDS | P5 | loader | 손상 bytes 고정 E/H | 가능 |
| HC25 | wrapper extra/status/Policy key | FIELDS | P5 | loader | 손상 bytes 고정 E/H | 가능 |
| HC26 | stored field 각 하나 누락 | FIELDS, absent≠null | P5 | loader | 손상 bytes 고정 E/H | 모델/key별 가능 |
| HC27 | nested extra key | FIELDS | P5 | loader | 손상 bytes 고정 E/H | 깊이별 가능 |
| HC28 | 추가 공백, H 대응 | NONCANONICAL | P5 | loader | 비정규 bytes 고정 E/H | 가능 |
| HC29 | key 순서 변경, H 대응 | NONCANONICAL | P5 | loader | 비정규 bytes 고정 E/H | 가능 |
| HC30 | trailing newline, H 대응 | NONCANONICAL | P5 | loader | 비정규 bytes 고정 E/H | 가능 |
| HC31 | 한국어 불필요 Unicode escape | NONCANONICAL | P5 | loader | 비정규 bytes 고정 E/H | 가능 |
| HC32 | quarter float/NaN/Infinity/exponent | NUMBER | P4 | loader | 손상 bytes 고정 E/H | token별 가능 |
| HC33 | 고립 surrogate key/value | UNICODE | P4 | loader | 손상 bytes 고정 E/H | 가능 |
| HC34 | unknown schema literal | SCHEMA | P5 | loader | 손상 bytes 고정 E/H | 가능 |
| HC35 | 잘못된 condition ID | MODEL | P6 | loader | canonical 손상 E/H | 가능 |
| HC36 | 중복 condition | MODEL, dedupe 없음 | P6 | loader | canonical 손상 E/H | 가능 |
| HC37 | 잘못된 policy ID | MODEL | P6 | loader | canonical 손상 E/H | 가능 |
| HC38 | quarter bool/string | TYPE | P5 | loader | 손상 bytes 고정 E/H | 가능 |
| HC39 | scope 범위/edition 형식 오류 | MODEL, 기존 규칙 | P6 | loader | canonical 손상 E/H | 가능,0000 허용 별도 |
| HC40 | array 대신 object/null, API raw tuple | TYPE 또는 INPUT | P5/P0 | loader | E/H 및 정상 나머지 입력 | 가능, JSON tuple은 없음 |
| HC41 | malformed evidence ref | MODEL | P6 | loader | canonical 손상 E/H | 가능 |
| HC42 | i0000/잘못된 Inventory version | MODEL | P6 | loader | canonical 손상 E/H | 가능 |
| HC43 | Inventory에 없는 Binding condition | MODEL | P6 | loader | canonical 손상 E/H | 가능 |
| HC44 | 같은 condition의 중복 Binding | MODEL | P6 | loader | canonical 손상 E/H | 가능 |
| HC45 | 빈 meaning/빈 conditions | MODEL | P6 | loader | canonical 손상 E/H | 가능 |
| HC46 | 잘못된 requirement Enum | VALUE | P6 | loader | canonical 손상 E/H | 가능 |
| HC47 | implementation ref null/빈값 | TYPE/MODEL | P5/P6 | loader | 손상 bytes 고정 E/H | 가능 |
| HC48 | 다른 condition이 같은 root 문자열 | 로컬 복원 가능, ownership 별도 | P9/후속 | loader/evaluator | E/H/I/F, 후속 T | 경계 가능 |
| HC49 | 같은 값의 R 복사본/다른 revision | REVIEW_BINDING_MISMATCH | P1 | loader | 실제 E의 원본 R | 가능 |
| HC50 | 같은 benefit의 다른 Entry bytes | 선택 R의 H로 거부 | P3 | loader | 선택 E/H | 다른 raw로 가능 |
| HC51 | R clone의 policy/scope만 변경 | is 실패, 임의 원본 조립 금지 | P1 | loader | 실제 E의 원본 R | 가능 |
| HC52 | raw Inventory policy만 R과 다름 | IDENTITY_MISMATCH | P8a | loader | E/H, R의 I/F | 가능 |
| HC53 | raw Q3 vs R annual | IDENTITY_MISMATCH | P8a | loader | E/H, R의 I/F | 가능 |
| HC54 | raw Inventory version 다름 | INVENTORY_VERSION_MISMATCH | P8b | loader | E/H, R의 I/F | 가능 |
| HC55 | 같은 version 다른 meaning/근거 | INVENTORY_FINGERPRINT_MISMATCH | P8c | loader | E/H, R의 고정 I/F | 가능 |
| HC56 | current Coverage로 과거 원본 대체 | H 또는 I/F 첫 불일치 | P3/P8 | loader | 원본 E/H/I/F | 가능 |
| HC57 | 같은 Inventory의 bindings/ref 변경, old H | BYTES_MISMATCH, F만으로 통과 안 함 | P3 | loader | 원본 E/H/I/F | 가능 |
| HC58 | completeness ref만 변경, old H | BYTES_MISMATCH | P3 | loader | 원본 E/H/I/F | 가능 |
| HC59 | root ref 불일치/Entry 없음 | REVIEW_BINDING_MISMATCH | P1 | loader | R 원본+다른 정상 root | 가능 |
| HC60 | REVOKED 직접 공급 | subject 오류, None ref 유지 | P1 | loader | 실제 M2.57 B/root | 가능 |
| HC61 | Coverage 복원 성공 | FULL을 반환/저장하지 않음 | P9/후속 | loader/evaluator | E/H/I/F, 별도 T/V | 경계 가능 |
| HC62 | Inventory fp 일치 | Tree 검증 완료 아님 | 후속 | 외부/Content | E/H/I/F와 별도 T | 부재 경계 가능 |
| HC63 | Tree fp만 일치 | Review/검토 완료 아님 | 후속 | Content/Review | 당시 T/V 원본 | matching 부분 후속 가능 |
| HC64 | Review metadata 일치 | 실제 인간 검토 인증 아님 | 외부 | 사람/운영 | 공식 원문/권한/검토 기록 | 진실성 자동 실증 불가 |
| HC65 | loader 정상, release 미확보 | 전체 release 검증 완료 아님 | 외부/후속 | preparation/Content | 실제 L | 경계 가능 |
| HC66 | loader 정상 | Acceptance USABLE/지급/Bridge 아님 | 후속 | evaluator/adapter | 별도 current 원본/gate | 상태 경계만 가능 |
| HC67 | bytearray/subclass/잘못된 artifact/R 타입 | LOADER_INPUT | P0 | loader | 나머지 정상 E | 가능 |
| HC68 | H+JSON 오류/Enum+공백/identity+fp 오류 | P3→P5→P6→P8의 첫 오류 | 복합 | loader | 각 독립 E/H/I/F | 매개화 가능 |
| HC69 | parser RecursionError/int 제한 실패 | JSON/NUMBER, 전역 설정 불변 | P4 | loader | E/H, 격리 실패 주입 | 가능, 고정 깊이 임계값 없음 |
| HC70 | 중복 Entry/ACCEPTED None coverage ref | 기존 모델 생성 오류 | loader 이전 | 기존 Review 모델 | 정상 생성 시도 | 강제 변조 없이 가능 |
| HC71 | 당시 Tree/Review/ZIP 미확보 | 좁은 복원 가능, 전체 준비는 미완료 | 외부/후속 | preparation | E/H/I/F, 필요한 T/V/L | 경계만 가능 |
| HC72 | 같은 Inventory, 없는 root/외부 source | 좁은 복원은 가능, 실제 root/source·실행 검증 별도 | P9/후속 | evaluator/Content/외부 | E/H/I/F, 당시 T/V/L | 기계 부분 후속 가능 |

축약 오류명은20절 exact prefix를 가리킨다. HC61~HC66은 단계 간 보장 한계이며 사람 검토/미구현 evaluator의 실행 완료 실적으로 세지 않는다. 100회 반복·매개화된 case 수는 향후 실제 pytest 수로 별도 보고한다.

## 24. 외부 preparation 책임

신뢰된 A/C는 같은 호출에서 외부 R/전체 expected Acceptance 원본을 확보하고 실제 M2.57을 실행한다. 반환 root에서 R의 Entry를 골라 coverage_snapshot_ref와 명시 artifact root로 정확한 path를 resolve하고, containment/symlink/junction·접근 권한/보관본 확보를 담당한다. 파일 미확보면 외부 준비 실패로 중단한다.

그 파일을 한 번 읽어 immutable B를 얻고17절 API에 B/root/R을 직접 공급한다. 반환 C와 **같은 ref/B/R/root**를 로컬에 보존한다. 기존 tuple `(entry.coverage_snapshot_ref, B, C)` 대응을 보존할 수 있으나 새 인증 DTO/token/verified bool은 아니다. 같은 파일 내용이 다른 path에도 존재할 수 있어 bytes 함수만으로 물리 경로를 인증하지 않는다.

typed Artifact를 직접 만들 수 있으므로 타입/is만으로 실제 M2.57 실행을 증명하지 못한다. 같은 호출의 실제 반환값 공급이 외부 계약이며, 임의 prevalidated 객체를 받는 public 우회 orchestration을 만들지 않는다. Coverage bytes 소비 중 expected H를 교체하지 않는다. filesystem/network/Git/env/시각/random/cache는 pure loader 안에 넣지 않는다.

## 25. 후속 Content Validator 연결

M2.58의11입력 후보에서 `historical_coverage`에는17절 반환 C를, `historical_artifact_bytes`의 해당 항목에는 동일 selected ref/B를 전달하는 방향이다. 다른 객체/current Coverage로 바꾸거나 다른 호출의 성공을 재사용하지 않는다. 같은 R/root와 다른 역사 원본도 그 원본별 동일 bytes 복원으로 결합해야 한다.

그 뒤 당시 Policy/Tree, ReviewContext/명시 refs, 전체 Manifest/Registry/Envelope/source/implementation 대응과 L1/L2를 확인한다. Source/L3/당시 FULL 근거는 기존 외부 책임이다. 이번에 M2.58 API/자동 evaluator 미실행 결정을 변경하지 않는다.

기존 historical Benefit loader는 구현 완료지만 Coverage loader는 이 문서로 설계 완료일 뿐이다. ReviewContext/Manifest 등 남은 원본 준비도 아직 미완료여서 전체 Content Validator의 구현 준비 완료를 주장하지 않는다.

## 26. Assumptions·미해결 의존사항

| 항목 | 경계 |
|---|---|
| A1 | 신뢰된 R/전체 expected originals·실제 M2.57 동일 호출 반환값을 공급함. 타입으로 발급 진실성을 인증하지 못함 |
| A2 | 고정 ref.path의 원본 bytes를 외부에서 확보함. 실제 archive/preparation은 미구현 |
| A3 | 사람의 공식 의미/권한·Source 요건/필요한 당시 실행 대응은 별도 확인. hash만으로 완료 선언 안 함 |
| 좁은 준비 완료 | raw2/2/5/2/4/3, HC1, 독립 H, 기존 모델 복원/Inventory binding/API/오류 순서가 모두 확정. 이 함수 구현의 blocker 없음 |
| 남은 원본 | 당시 PolicyEnvelope 동일 bytes 준비 경계, CoverageReviewContext/Manifest 역사 strict codec, Registry/source/ZIP·실제 실행 대응 |
| 남은 기능 | 이번 Coverage loader 구현/합성 검증, 외부 preparation, 전체 Content Validator, Source Gate, Acceptance evaluator/adapter/Bridge |

그 의존사항이 전체 Historical FULL/Acceptance 사용 경로를 막는 것과, 이번 입력 복원 함수를 독립 구현할 수 있는 것은 구별한다. 없는 provenance 필드나 새로운 SourceBinding을 모델에 추가해서 해결하지 않는다.

## 27. 최종 판단

**READY_TO_IMPLEMENT_HISTORICAL_ELIGIBILITY_COVERAGE_LOADER**

기존 ArtifactReference의 독립 SHA, 정확한 Coverage 입력 raw schema/HC1, 동일 bytes의 기존 모델 복원, selected Entry/R 원본 결합, Inventory4축 비교와 오류 순서를 확정했다. 동결 Coverage와 충돌하지 않는다. Tree/Review/release/실행/FULL은 이번 loader의 보장 범위 밖으로 명시했다.

## 28. 다음 최소 작업 하나

승인 후 **M2.62 — Historical EligibilityCoverage Strict Bytes Loader 구현** 한 개다.17절3인자 API·20절 P0~P9·23절 해당 합성 사례로 입력 복원/Inventory binding만 구현·검증한다. 기존 모델/evaluator/지문/Review matching/freeze/테스트 기대값/실제 releases는 보존한다.

Tree/Review/Manifest codec·파일 preparation·Content Validator·Source Gate·evaluator·Bridge/Cashflow·실제 Coverage/Result 생성까지 확장하지 않는다. 이번 M2.61에서는 구현을 시작하지 않는다.

## 29. 검증·보존 기록

- 작업 전 전체 pytest: **7,967 passed in 73.13s / skipped0 / failed0 / timeout0**.
- 신규 실행 테스트: **0개**. HC01~HC72는 문서 사례72개다.
- 작업 후 전체 pytest: **7,967 passed in 68.82s / skipped0 / failed0 / timeout0**. 전후 최초 실행이 모두 통과했고 실패/timeout 후 재실행은 없었다. 기존 테스트/fixture/기대값·timeout 설정은 변경하지 않았다.
- 사전 backend/tests/data/docs/tools178개(실제 releases·pycache 별도)의 SHA256이 모두 동일하다. 새 문서1개만 추가해 최종179개이며 기존 파일 수정/삭제0개다. GV01~GV15/BV01~BV16 literal/계산, 동결 Coverage 코드/문서, 기존 Benefit/Acceptance/Review 모델·loader·M2.60 loader, bootstrap/Cashflow를 보존했다.
- 실제 release6개는 SHA256·경로·크기·수정시각이 모두 동일하다. 아래는 기존 원본의 전후 동일 SHA이며 새 정책 지문 발급이 아니다. release root는 `data/releases/`다.

| 기존 release 상대 경로 | 전후 동일 SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

- 문서 검수:29개 절·HC01~HC72 연속/유일성·19개 오류 prefix 유일성·API3개 필수 keyword-only 인자·모델5개의 실제 AST 저장 필드와 schema 대응·표 column/fence·UTF-8/한국어를 확인했다. 이 검수는 신규 실행 테스트로 계산하지 않는다.
- 실제 안산 Coverage Artifact/과거 FULL Result/Acceptance/금액·실행 ZIP을 생성하지 않았다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, 실제 안산 DRAFT/CONDITION_SLICE·정책 혜택 Cashflow 반영0원 원칙을 유지한다.

## 30. M2.62 — IMPLEMENTED: Historical EligibilityCoverage Strict Bytes Loader

### 실제 API·파일

`backend/policy_engine/policy_data/historical_eligibility_coverage_loader.py`에 다음 순수 함수 하나를 구현하고 package public export에 추가했다.

```python
load_historical_eligibility_coverage_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> EligibilityCoverage
```

3개 인자는 필수 keyword-only이며 기본값/skip/fallback/force_full/current_review_context 옵션은 없다. 새 domain 모델/저장 필드/예외 계층/범용 codec을 추가하지 않았다. 기존 Historical Benefit loader를 수정하거나 공통 helper로 추출하지 않았다.

### 구현된 P0~P9

```text
exact bytes + 실제 M2.57 반환 Artifact + 외부 Acceptance R 원본
  → ACCEPTED/root ref/명시 acceptance_ref 유일 조회/entry.acceptance is R
  → 그 Entry.coverage_snapshot_ref의 exact ArtifactReference
  → 동일 raw_bytes 전체 SHA256 대 독립 ref.sha256
  → BOM 거부/strict UTF-8/JSON duplicate·number·Unicode scalar
  → wrapper2/coverage2/inventory5/scope2/condition4/binding3 exact schema
  → HC1 canonical bytes와 원본 bytes equality
  → 기존 Scope/Requirement/RequiredCondition/Inventory/Binding/Coverage 복원
  → 기존 fingerprint_condition_inventory(coverage.inventory) 1회
  → policy_id → scope → inventory_version → 실제 Inventory fp와 R 대조
  → 불변 EligibilityCoverage 입력만 반환
```

20절19개 prefix와 우선순위를 그대로 사용한다. P3 SHA 실패 뒤에는 decode/JSON/모델 복원/지문 계산을 진행하지 않는다. missing은 extra보다 먼저, raw schema/type은 canonical보다 먼저, canonical은 domain invariant보다 먼저다. P6 constructor 순서와 P7 계산 후 P8 identity/version/fp 순서를 유지한다. PolicyDataError는 정상 incomplete/CONDITION_SLICE/UNUSABLE/미검토 reason으로 바꾸지 않는다.

raw에는 기존 저장 필드만 있다. ConditionRequirement 문자열→기존 Enum, JSON array→명시 tuple 변환 외에 trim/sort/dedupe/ID·ref 생성/현재 Policy 보충은 없다. conditions/bindings/evidence의 원래 순서를 보존한다. Inventory 지문 함수 내부의 조건 정렬은 지문 projection만의 규칙이며 반환 Coverage 순서를 바꾸지 않는다.

Binding 일부/전체 없음과 completeness_review_ref=None은 기존 모델대로 정상 복원된다. 반대로 중복 condition/Binding·존재하지 않는 Binding condition 등은 기존 constructor의 오류다. 존재하지 않는 Policy root/Review ref를 비공백 문자열로 보존할 수 있으나 그것의 실제 존재/구현/검토를 확인했다고 보고하지 않는다.

### 동일 bytes·Inventory binding의 보장

기대 hash는 selected coverage_snapshot_ref.sha256에서만 얻고 actual digest로 덮어쓰지 않는다. accepted_terms_ref/다른 Entry ref/Inventory fp를 raw SHA 대신 사용하지 않는다. 선택 ref는 함수 내부에서만 결정하며 path를 열지 않는다. 외부에서 이미 만들어진 Coverage를 받거나 다른 파일을 재조회하지 않는다.

raw SHA는 completeness_review_ref와 bindings/root/implementation refs까지 고정한다. 기존 Inventory 지문에서는 이 값들이 계속 제외된다. 따라서 같은 Inventory fp라도 다른 Binding 파일을 old raw SHA로 대체하면 실패한다. 실제 복원 Inventory에 기존 지문 함수1회를 적용한 뒤 R의 policy/scope/inventory_version/fp4축을 독립 대조한다.

R의 rule version/Tree fp/dataset/Registry/implementation 값은 이 Coverage 파일만으로 검증할 수 없어 입력/검사 축에 추가하지 않았다. 그 값들이 다르더라도 이 함수의 좁은 복원 성공은 그 축들의 검증 성공을 뜻하지 않는다. 후속 역사 원본 대조 의존사항으로 유지한다.

### 합성 실행 테스트와 HC 대응

`tests/test_historical_eligibility_coverage_loader.py`의 신규 **267개**는 실제 수집·실행된 pytest 수다. HC01~HC72를 더하지 않는다. 정상 end-to-end fixture는 기존 실제 M2.57 loader를 거쳐 외부 R과 root Entry의 is 관계를 확보한다. 각 phase 손상 fixture는 저작 단계에서 H를 고정하여 앞 단계가 통과하도록 준비한다. 소비 함수에서 expected를 actual로 채택한 것이 아니다.

기본 synthetic raw는478bytes이며 고정 SHA는 `240ec48137b395eb5bdcccda9883c4eefa21b736e959b85f720f0b46cfa7339e`다. 실제 Inventory 기대값은 기존 **GV01** literal `abf20d120e93265b5b2e85851707d255693f833ee2dbdab8cd5741115fdf572a`를 사용한다. 조건 순서 검증에는 기존 GV02/GV03 지문 literal도 재사용했다. 새 GV/실제 정책 지문을 발급한 것이 아니다.

| 문서 사례 | 이번 실제 검증 범위 |
|---|---|
| HC01~HC15 | exact 모델/API·단일/다중 조건·Binding0/1/전체·annual/0000 Scope·명시 refs/None·원순서/evidence 중복·한국어/NFC/NFD·100회 결정성/불변성 |
| HC16~HC34 | 고정 H/1byte/같은 filename·SHA 뒤 단계 미실행·UTF-8/BOM/JSON/전 깊이 중복·schema/모든 required/extra·HC1 공백/순서/newline/escape/숫자/Unicode |
| HC35~HC48 | 기존 ID/버전/meaning/Enum/evidence/Scope invariant·malformed/unknown/duplicate Binding의 정상 incomplete와 오류 구별. 같은 root 재사용의 tree ownership 검사는 구현하지 않음 |
| HC49~HC60 | 실제 Entry/R 원본 is·복사본/revision/target·같은 benefit의 다른 Entry·다중 Entry 순서/공유·policy/scope/version/fp·current 대체·bindings/ref의 raw hash 대응·REVOKED 거부 |
| HC61~HC66 | 반환은 Coverage 입력이며 status/Result 없음. Tree/Review/release/실행/사람 검토/USABLE을 확인하지 않는 기계적 경계. 미구현 전체 검증을 실행했다고 세지 않음 |
| HC67~HC72 | exact 타입/subclass·복합 오류 순서·parser 방어 오류·기존 Entry 중복/None ref 생성 차단·파일/Registry/Tree/Review/Manifest/Result/evaluator 호출 부재. 외부 원본 미확보/실제 역사 실행은 미구현 |

중복 Entry와 ACCEPTED의 None/잘못된 coverage ref는 정상 기존 모델 생성 단계에서 이미 거부된다. 같은 Entry/값 같은 Entry 복사본/같은 ref의 다른 revision 생성 시도를 검증했다. frozen 객체를 강제로 훼손하지 않았다. 새 loader의 유일성/EXPECTED_REF 방어 분기가 정상 생성 객체에서 도달 불가라는 사실을 숨기지 않는다.

parser RecursionError는 격리 failure injection으로 mapping을 검사하며 특정 JSON 깊이를 고정 임계값이라고 주장하지 않는다. 정수 파싱 제한/ValueError와 지문 함수 PolicyDataError mapping도 검사하고, 전역 제한을 변경하지 않았다. 예상 밖 RuntimeError를 포괄 Data Error로 은폐하지 않는 것도 확인했다. parser callback/기존 constructor의 원래 오류 순서는 변경하지 않았다.

### 순수성·검증 한계·다음 의존사항

filesystem/network/Git/env/현재시각/random/cache/ZIP 실행은 없다. Review matching·Tree/subtree 지문·Manifest 검증·Coverage evaluator/Result factory·Acceptance 평가·Benefit loader·Bridge/Cashflow를 실행하지 않는다. 신뢰된 외부가 같은 호출의 실제 M2.57 반환 root/R을 공급해야 하며, 타입/is 자체를 실제 검토·발급 진실성 인증으로 확대하지 않는다.

**IMPLEMENTED:** Historical Coverage strict bytes loader·기존 EligibilityCoverage 복원·기존 Inventory 지문 재계산/비교·Acceptance Inventory binding·합성 실행 테스트·public 함수1개.

**NOT IMPLEMENTED:** Historical Policy Tree/ReviewContext/Manifest loader·Historical FULL replay·외부 file preparation·Content Validator·Source Gate·Acceptance evaluator·same-call adapter·Bridge/Cashflow·실제 안산 Coverage/Acceptance/FULL Result.

**최종 판단: HISTORICAL_ELIGIBILITY_COVERAGE_LOADER_COMPLETE.** 다음 최소 작업은 **Historical PolicyEnvelope / Rule Tree Artifact Preparation Contract 문서 설계 하나**다. policy_envelope_ref의 동일 bytes 검증과 기존 parse_policy_envelope를 연결하고, 그 Policy의 실제 rule_version/Tree 지문 대응을 확정한다. 기존 object parser가 있어 좁은 원본 준비 계약부터 닫을 수 있으며 ReviewContext/Manifest 전체 codec이나 Content Validator 구현으로 확대하지 않는다.

### M2.62 검증·보존 기록

- 작업 전 전체 pytest: **7,967 passed in 66.41s / skipped0 / failed0 / timeout0**.
- 신규 합성 실행 테스트: **267 passed in 1.33s**. 문서72사례/보조 검수를 더하지 않는다.
- 작업 후 전체 pytest: **8,234 passed in 74.89s / skipped0 / failed0 / timeout0**. 기존7,967개와 신규267개를 포함한다. 전후 전체/신규 최초 실행 모두 통과했으며 실패/timeout 후 재실행은 없었다. 기존 테스트/fixture/기대값·timeout/테스트 설정은 변경하지 않았다.
- 사전 backend/tests/data/docs/tools179개(실제 releases·pycache 별도) 중 기존176개 SHA256이 동일하다. 변경3개는 package __init__.py의 함수 export·이 문서·ARCHITECTURE.md다. 새 loader/테스트2개로 최종181개이며 삭제0개다.
- 기존 모든 tests/fixture·GV01~GV15/BV01~BV16·Coverage freeze 코드/문서·기존 지문/evaluator/Review matching·Historical Benefit loader·Review Artifact strict loader·Benefit/Acceptance/Context/Result·bootstrap/Cashflow는 SHA256이 동일하다. DATA_MODEL.md도 변경하지 않았다. 새 stored field가 없어 모델 문서를 추가 갱신할 필요가 없었다.
- 실제 release6개는 SHA256·경로·크기·수정시각이 모두 동일하다. 기존 SHA는29절 표와 같으며 실제 안산 Coverage/Acceptance/FULL Result·금액·실행 ZIP을 생성하지 않았다.
- API·raw exact schema·19prefix·순수성·기존 모델 복원/Inventory 지문 사용은 신규 실행 테스트로 검증했다. 정상 모델에서 도달 불가인 Entry/ref 방어 분기는 생성 단계의 차단 검증과 구별했다. 구문/UTF-8·한국어·문서 table/fence·모델 필드 검수는 신규 pytest 수에 더하지 않는다.
- ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, 실제 안산은 DRAFT/CONDITION_SLICE·정책 혜택 Cashflow 반영0원 원칙을 유지한다.
