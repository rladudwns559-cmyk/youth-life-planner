# M2.63 — Historical PolicyEnvelope / Rule Tree Artifact Preparation Contract

현재 구현·검증 상태는 **28절 M2.64**를 따른다. 1~27절의 미구현/다음 작업/테스트 수는 M2.63 설계 시점의 이력이다. 기존 계약은 유지한다.

## 1. 목적·이번 범위

`AcceptanceReviewEntry.policy_envelope_ref`가 지목한 과거 파일의 **독립 기대 SHA와 일치하는 동일 raw bytes**에서 기존 PolicyEnvelope/Policy/Rule Tree 전체를 복원하고, 확인 가능한 당시 Acceptance binding을 대조하는 계약이다.

이번에는 이 문서 하나만 추가한다. Historical PolicyEnvelope/ReviewContext/Manifest loader·Content Validator·Source Gate·evaluator·Bridge/Cashflow·실제 안산 역사 Artifact/Acceptance/FULL Result를 구현하거나 생성하지 않는다. 기존 코드/테스트/동결 계약/실제 releases는 수정하지 않는다.

**최종 판단: READY_TO_IMPLEMENT_HISTORICAL_POLICY_ENVELOPE_LOADER.** 이는 아래 좁은 순수 loader의 구현 준비 판단이다. quarter 적용 증명·당시 FULL·전체 release/실행 검증·현재 Acceptance USABLE은 포함하지 않는다.

## 2. Source of Truth와 현재 검증 공백

| 확인 문서 | 적용할 현재 계약 |
|---|---|
| HISTORICAL_ELIGIBILITY_COVERAGE_ARTIFACT_PREPARATION_SPEC.md | M2.61 exact Coverage 입력/Inventory 경계와 M2.62 구현 완료. Tree/Review/Manifest 분리 |
| HISTORICAL_BENEFIT_SNAPSHOT_ARTIFACT_PREPARATION_SPEC.md | M2.60의 실제 same-call 3인자/동일 bytes/독립 H 원칙 |
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md | L1/L2/L3·당시 Policy 전체 원본·Content의 evaluator 자동 재실행 금지 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md | Entry15/원본7참조·ACCEPTED/REVOKED·원본 참조와 검토 진실성 분리 |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md | Acceptance21·Coverage binding·정확한 revision/target |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | A/C/B, 역사 자료와 current 자료 분리, 전체 release/실행 책임 |
| POLICY_DATA_ENVELOPE_SPEC.md | 최신 M1.13/M1.15의 실제 raw format/parser/flags·domain serializer 차이 |
| COVERAGE_FINGERPRINT_SPEC.md | coverage-policy-tree-1.0·전체 node projection/순서·GV01~GV15 |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md / ELIGIBILITY_COVERAGE_CORE_FREEZE.md | Result/factory/FULL·SLICE·generic core 동결·정책 blocker |
| DATA_MODEL.md / ARCHITECTURE.md | 실제 필드/포함 관계/구현 상태와 과거 후보 구분 |

실제 `policy_data/envelope.py`, `policy_data/loader.py`, `loader.py`, `models.py`, specialized_rules의 resident_registration/birth_date, facts의 RegionRef, `coverage_fingerprint.py`, 기존 Review/Acceptance/ArtifactReference, M2.60/M2.62 loader를 확인했다. `parse_policy_envelope(data)`는 이미 전체 Policy를 복원할 수 있다. 다만 expected ArtifactReference와 **동일 bytes SHA/strict decode/canonical/Acceptance Tree binding까지 결합한 public loader는 없다**.

기존 `load_policy_envelope(path)`로 파일을 읽을 수 있다는 사실만으로, 별도 hash 검사에서 읽은 bytes와 그 객체가 연결되지는 않는다. M2.62 Coverage에는 Tree가 없으므로 그 성공으로 이 공백을 대신할 수도 없다. 이번에는 고정 ref → 한 bytes → 기존 parser → 실제 Tree 지문 → R 대조를 닫는다.

## 3. 실제 PolicyEnvelope·Policy·Rule Tree 구조

### PolicyEnvelope 저장15필드

| 필드 | exact domain 타입·의미 |
|---|---|
| schema_version | str, policy-data-1.0 |
| rule_schema_version | str, m1.1 |
| policy | 기존 Policy 전체 |
| edition_id | str, ASCII4자리 edition 연도 표기. quarter 없음 |
| jurisdiction | 기존 RegionRef(sido, sigungu), 둘 다 완전한 str |
| category | PolicyCategory (현재 YOUTH_SUPPORT) |
| dataset_version | 비공백 str |
| evaluation_scope | EvaluationScope (현재 CONDITION_SLICE만 존재) |
| coverage | legacy PolicyCoverage(included_rule_ids, excluded_conditions), 각 tuple[str,...] |
| source_bindings | nonempty tuple[SourceBinding(source_document_id, document_version),...] |
| verification_status | PolicyVerificationStatus: DRAFT/VERIFIED/STALE |
| last_verified_at | exact date 또는 None |
| lifecycle_status | PolicyLifecycleStatus: ACTIVE/ENDED |
| effective_from | exact date 또는 None (생성자 기본 None) |
| effective_to | exact date 또는 None (생성자 기본 None) |

Envelope.policy_id/policy_name/rule_version/root/synthetic/test_only는 **policy로 위임하는 읽기 전용 property**다. source_document_ids도 bindings에서 파생한다. 별도 저장 필드로 만들지 않는다.

Policy의 저장6필드는 policy_id:str, policy_name:str, rule_version:str, root:RuleNode, synthetic:bool, test_only:bool이다. allow_real_data는 생성자 InitVar이며 저장 값/raw JSON key가 아니다. 실제 root는 **envelope.policy.root**이며 그룹 아래의 전체 트리를 소유한다. Policy 자체에는 edition_id/scope/quarter/source_bindings가 없다.

RuleNode는 정확히 **PolicyRule | ResidentRegistrationRule | BirthDateRule | RuleGroup**이다. 새 HistoricalPolicy/Rule 타입이나 공통 동적 registry를 추가하지 않는다.

## 4. policy_envelope_ref·Entry 원본 결합

실제 ref 타입은 기존 ArtifactReference(path:str, sha256:str)다. 상대 slash path와 소문자 hex64의 로컬 문법은 기존 생성자가 검사한다. path는 외부 원본 위치이고 sha256은 전체 raw bytes의 독립 기대값이다. 파일 존재/정식 검토/권한은 그 타입이 확인하지 않는다.

같은 호출의 실제 M2.57 반환 root와 외부 원본 R을 사용한다. R.status는 ACCEPTED여야 한다. root.review_artifact_ref == R.review_artifact_ref → R.acceptance_ref의 유일 Entry 조회 → **entry.acceptance is R** → 그 Entry.policy_envelope_ref exact 타입/nonnull 순으로 연결한다.

first/latest 선택·같은 benefit_id의 다른 revision·같은 값의 R 복사본·다른 Entry ref/현재 Envelope fallback은 없다. REVOKED의7참조 None을 유지하고 직접 입력은 거부한다. A의 역사 원본이 필요하면 Context의 철회 대상 A를 별도 준비하는 후속 경계를 유지한다.

타입/is만으로 실제 M2.57을 통과했음을 인증하지 못한다. 신뢰된 외부 A/C가 같은 호출에서 실제 loader를 실행해 반환 원본을 직접 전달해야 한다. 같은 process의 강제 조작을 막는 보안 token이라고 주장하지 않는다.

## 5. Raw format 비교·단일 선택

| 후보 | 비교 | 결정 |
|---|---|---|
| A: 기존 PolicyEnvelope JSON 그대로 | 이미 policy-data-1.0/m1.1 두 discriminator와 전체 embedded Policy가 있고 object parser 재사용 가능. 기존 자료의 구조와 호환 | **선택** |
| B: 새 version wrapper + 기존 payload | 별도 profile 이름은 명시되나 이미 존재하는 버전 계층을 복제하고 기존 release 파일을 그대로 소비하지 못함 | 미선택 |

새 Historical wrapper/schema_version을 발명하지 않는다. **root.schema_version=policy-data-1.0**, **root.rule_schema_version=m1.1**의 기존 파일 문법을 사용하고 bytes 수준에는 아래 HP1 canonical profile을 명시한다. 향후 다른 schema/version은 별도 계약 전 거부한다.

기존 `Envelope.to_dict()`는 domain snapshot으로 외부 raw serializer가 아니다. `kind/rule_type`과 외부 ID/flags assertion이 필요한 실제 loader JSON을 사용한다. fingerprint의 node_type projection이나 PolicySet JSON을 root에 대신 놓지 않는다.

**호환성 한계:** 현재 실제 release 파일은 들여쓰기/newline이 있어 HP1 bytes가 아니다. 구조 parser로 읽을 수 있어도 이 후속 strict historical 함수에서는 원래 H가 맞은 뒤 NONCANONICAL로 거부된다. 이번에는 그 파일/참조/hash를 수정하지 않는다. 검증 중 canonical화한 사본으로 원래 B를 바꿔 성공시키지 않는다. 나중에 canonical 보관본이 필요하면 외부의 별도 보존·검토 절차로 새 bytes/ref를 독립 고정해야 하며, 과거 검토가 그 사본을 가리켰다고 소급 주장하지 않는다. 실제 역사 Acceptance/보관본은 이번에 발급하지 않는다.

## 6. 정확한 기존 raw schema

아래 순서는 후속 shape 검사 순서다. JSON key 출력 순서는 HP1 정렬을 따른다. required/optional을 구분한 **기존 문법을 그대로 유지**한다.

| object | required keys | optional keys |
|---|---|---|
| root | schema_version, rule_schema_version, policy_id, policy, edition_id, jurisdiction, category, dataset_version, evaluation_scope, coverage, source_bindings, verification_status, last_verified_at, lifecycle_status, synthetic, test_only | effective_from, effective_to |
| root.policy | policy_id, policy_name, rule_version, synthetic, test_only, root | 없음 |
| jurisdiction / resident.required_region | sido, sigungu | 없음 |
| coverage (legacy) | included_rule_ids, excluded_conditions | 없음 |
| source_bindings[i] | source_document_id, document_version | 없음 |
| group node | kind, rule_id, operator, children | 없음 |
| atomic node | kind, rule_type, rule_id, field, operator, value, evidence_refs | fact_basis |
| resident_registration node | kind, rule_type, rule_id, required_region, reference_date_source, evidence_refs | 없음 |
| birth_date node | kind, rule_type, rule_id, min_birth_date, max_birth_date, evidence_refs | 없음 |
| nonnull fact_basis | basis, subject, period, reference_year, unit | 없음 |

group.kind는 `group`이다. 세 leaf의 kind는 `rule`, rule_type은 각각 `atomic`/`resident_registration`/`birth_date`다. group에는 rule_type을 추가하지 않는다. raw에 node_type/root-level rule_version/root-level policy_name/source_document_ids/quarter/status=FULL_POLICY/Manifest/Review/Artifact path/hash를 추가하지 않는다.

모든 required key는 nullable여도 존재해야 한다. last_verified_at는 string|null이며 누락은 오류다. effective_from/to는 기존 문법대로 생략 또는 string|null이고 두 경우 None으로 복원된다. atomic.fact_basis도 생략/null이면 None이며 nonnull이면 exact5key다. **이 세 optional 필드만** 기존 parser의 명시 기본 동작을 허용한다. raw에서는 missing과 null의 bytes/H가 다르며 서로 바꿔 쓰지 않는다. household_income의 fact_basis 필수성 등 의미 조합은 기존 모델이 검사한다.

root/policy synthetic/test_only는 exact bool이고 두 계층이 정확히 같아야 한다. 현재 parser는 True/True 합성 및 False/False 실자료의 기존 명시 경로를 지원한다. False/False일 때 내부 adapter가 기존 parse_policy_set(..., allow_real_data=True)를 사용한다. 새 raw allow_real_data 옵션·강제 True·실자료의 합성 위장은 없다. 혼합/정수 플래그는 기존 parser/모델대로 거부한다. 이 수용은 production 승인이나 VERIFIED를 뜻하지 않는다.

배열 source_bindings/included_rule_ids/excluded_conditions/evidence_refs/children 및 `in` 후보값은 원순서다. required_region/jurisdiction은 기존 완전한 RegionRef의 두 str이며 null/별칭을 자동 수용하지 않는다.

## 7. 기대 SHA·동일 bytes·외부 준비

독립 기대값은 **selected entry.policy_envelope_ref.sha256**이다. trusted R.review_artifact_ref → 실제 Review bytes SHA/외부20값 대조 → selected Entry → Envelope 기대 H라는 연결을 사용한다. actual digest를 기대값으로 채택하지 않는다. Tree fp/파일명/크기/mtime/Registry fp로 대체하지 않는다.

외부가 정확한 ref.path에서 immutable exact bytes B를 한 번 확보한다. 순수 loader는 B 전체 SHA → B의 strict UTF-8 decode → 같은 내용의 JSON parse → 그 parsed object를 기존 parser에 전달한다. hash 뒤 load_policy_envelope(path)로 다시 읽거나 외부에서 만든 Policy 객체로 바꾸지 않는다.

외부의 명시 root/path containment·symlink/junction·권한/보관소·파일 미확보 처리는 준비 책임이다. bytes 함수는 물리 path 실재를 인증하지 못한다. 같은 bytes가 다른 path에 있을 수 있으며 정상 공유 자료를 중복 실패로 만들지 않는다. 같은 `(ref, B, returned_envelope)`와 root/R을 같은 호출에서 보존하고 후속 Content에 직접 공급한다. 새 VerifiedEnvelope DTO/flag/cache token은 없다.

## 8. Canonical JSON·strict parsing — HP1

```python
json.dumps(
    raw_payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8", errors="strict")
```

root는6절의 기존 Envelope JSON 그대로다. 모든 object key 정렬·compact separators·strict UTF-8, BOM/최종 newline 없음이다. Unicode NFC/NFD·문자열 공백/대소문자·날짜·배열을 정규화하지 않는다. 한국어는 원문 문자로, escape는 위 recipe대로다. Optional missing을 null로 채워 canonical 비교하지 않는다.

exact bytes만 받는다. raw SHA가 맞아야 BOM→strict UTF-8→JSON 순으로 진행한다. 모든 깊이의 decoded key 중복·malformed/trailing JSON·NaN/Infinity·float/exponent token을 거부한다. parse_int ValueError와 발생한 JSON parser RecursionError도 각각 number/JSON 오류로 대응하며 전역 제한을 바꾸지 않는다. parse 후 key/value의 고립 surrogate를 거부한다.

P5에서는 exact required+optional key set/primitive를 검사하고 그 **같은 parsed root**의 HP1 bytes와 B가 같은지 비교한다. noncanonical이면 자동 재작성하지 않는다. primitive bool은 flags/atomic bool value에 합법이고 int로 대체하지 않는다. quarter는 이 파일에 없다. FactBasis.reference_year는 exact int, bool은 타입 오류다. atomic.value는 raw scalar(str/int/bool) 또는 array[그 scalar]만 허용하고 operator/field별 타입·nonempty·범위 조합은 기존 parser/model이 최종 검사한다. 예를 들어 student_status의 bool은 유효하지만 age의 bool은 모델 오류다.

dates는 last_verified_at/effective_from/to에서 string|null, birth bounds에서는 required string이다. 날짜의 정확한 ASCII ISO/유효 달력·순서는 기존 parser/constructor가 검사한다. 숫자 timestamp/date를 문자열로 바꾸지 않는다. date 범위나 reference_year를 edition/scope로 추론하지 않는다.

## 9. 지원 Rule 전체 보존·기존 parser 재사용

| domain 타입 | 실제 stored fields | raw→domain 및 지문 보존 |
|---|---|---|
| PolicyRule | rule_id, field, operator, value, fact_basis, evidence_refs | Field/Operator Enum, in array→원순서 tuple, optional basis→FactBasis/None, refs→원순서 tuple |
| RuleGroup | rule_id, operator, children | GroupOperator ALL/ANY/NOT, 자식 전체를 원순서 재귀 복원. NOT 자식1개·모든 그룹 nonempty |
| ResidentRegistrationRule | rule_id, required_region, reference_date_source, evidence_refs | 기존 RegionRef, ReferenceDateSource.APPLICATION_DATE, refs 원순서 |
| BirthDateRule | rule_id, min_birth_date, max_birth_date, evidence_refs | exact date 두 개, 양끝 포함 구간/순서, refs 원순서 |
| FactBasis | basis, subject, period, reference_year, unit | 비공백 str4개·양의 exact int1개, 원문 보존 |

현재 Field는 age/region/student_status/employment_status/household_income, Operator는 eq/in/gte/lte다. int·bool·문자열 및 employment 값·FactBasis 결합 규칙은 기존 모델 그대로다. resident에 별도 value를 만들거나 birth를 atomic으로 축소하지 않는다. 모든 group/root/leaf·ID/operator/기준값/FactBasis/근거/자식 순서/specialized metadata가 그대로 복원돼야 한다.

P6에서 **기존 공개 `parse_policy_envelope(data: object) -> PolicyEnvelope`를1회 호출**한다. 그 내부는 기존 `parse_policy_set`에 m1.1 single PolicySet adapter를 전달하여 네 RuleNode를 복원한다. 새 rule parser·직접 Policy 생성·중복 지문 구현은 없다. filesystem I/O인 load_policy_envelope/load_policy_set은 호출하지 않는다.

기존 Envelope는 ID/r 버전/schema·외부/내부 ID·flags·모든 rule ID 유일성·leaf ID 집합과 legacy included_rule_ids 일치·source ID 유일성/leaf evidence source 집합·날짜/VERIFIED 선언의 날짜 필요 등을 검사한다. 이 로컬 검증은 재사용한다. 모델을 넓히거나 검증을 생략하지 않는다.

**중복 근거 주의:** 개별 Rule은 근거 순서/중복을 담을 수 있어도 기존 PolicyEnvelope 생성자는 한 leaf 안 duplicate evidence를 거부한다. 이를 dedupe해 통과시키지 않고 기존 모델 오류로 처리한다. 서로 다른 leaf가 같은 ref를 공유하는 것은 별개로 허용한다. included_rule_ids/source_bindings는 기존 유일성, excluded_conditions는 기존 규칙대로 원문/중복을 유지한다. 전체 flatten으로 정상 공유 refs를 duplicate로 거부하지 않는다.

## 10. 기존 Tree fingerprint

복원 E의 **실제 E.policy**에 `fingerprint_policy_tree(policy: Policy) -> str`를1회 적용한다. 기존 `coverage-policy-tree-1.0`과 GV01~GV15를 유지한다. payload는 fingerprint_schema/policy_id/rule_version/root4key이며 root는 네 node 타입의 기존 명시 projection이다.

PolicyRule의 value/FactBasis/evidence, resident의 region/reference date source, birth bounds, group operator/모든 descendant/자식 순서를 포함한다. raw kind/rule_type과 fingerprint node_type 표현은 서로 다른 문법이다. raw에서 node_type을 읽거나 fingerprint payload를 원본 파일로 대체하지 않는다.

policy_name/flags·Envelope metadata/source_bindings document version/dataset/edition/verification/coverage는 Tree 지문에서 제외된다. 따라서 raw SHA와 Tree fp는 교환할 수 없다. metadata 변경은 raw H가 고정하며 확인 가능한 dataset/edition은 R과 추가로 대조한다. 동일 Tree fp가 전체 release/사람 검토를 보장하지 않는다.

## 11. Acceptance binding·version·정상 역사 자료

P7에서 actual Tree fp를 계산하고 P8에서 아래 순서대로 독립 비교한다.

| 순서 | 비교 |
|---|---|
|1 identity | E.policy_id (= E.policy.policy_id) == R.policy_id |
|2 edition | E.edition_id == R.scope.edition_id |
|3 rule version | E.rule_version (= E.policy.rule_version) == R.coverage_rule_version |
|4 실제 Tree | fingerprint_policy_tree(E.policy) == R.coverage_policy_tree_fingerprint |
|5 dataset | E.dataset_version == R.coverage_dataset_version |

dataset은 실제 Envelope 필드이므로 이 최소3인자 API에서도 비교하기로 **선택**했다. Registry 전체 지문·implementation은 없다. policy/edition/version이 지문에 일부 포함돼도 개별 비교를 생략하지 않는다. R의 benefit_id/acceptance_version을 Policy에 추가하지 않는다. 그 revision/target은 M2.57의 원본20값 대조와 is로 특정한다.

정확한 과거 edition/rule_version/DRAFT·현재와 다른 Tree는 정상 역사 자료일 수 있다. current Policy를 함수 인자로 받거나 비교/자동 선택하지 않는다. **R이 고정한 과거 원본**과 다른 version 또는 같은 version의 다른 fp는 binding 모순이다. 이를 현재 정상 변경/만료/UNUSABLE reason으로 바꾸지 않는다.

## 12. Edition과 ApplicabilityScope

edition_id는 기존 ASCII4자리 문자열로 연도 단위 edition 식별에 쓰지만 Policy/Envelope에 quarter는 없다. 기존 모델은 `0000`도 문법상 허용하므로 loader가 임의로 달력 연도 제한을 추가하지 않는다. `2026-Q3`를 분해해 수용하지 않는다.

R.scope와 M2.62 C.inventory.scope에는 edition/quarter가 명시돼 있다. 이번 함수는 **edition 일치만** 검사할 수 있다. E.edition_id=2026, R.scope=(2026,Q3)로 성공해도 Q3 적용의 공식 근거가 증명된 것은 아니다. 같은 연도의 annual/Q1/Q3가 같은 Tree 원본을 참조할 수도 있으며 이 함수가 quarter를 만들거나 구분했다고 보고하지 않는다.

후속 Content/역사 Review/공식 source·명시 release 검토에서 C.scope/R.scope와 해당 Tree가 그 분기에 적용된다는 관계를 연결해야 한다. 날짜/효력기간/Rule ID에 Q3가 들어 있다는 사실로 범위를 역추론하지 않는다. 이 한계는 좁은 복원을 막는 모델 충돌이 아니며 이번에 Scope/Policy 필드를 개정하지 않는다.

## 13. M2.62 Historical Coverage와 연결

같은 호출의 같은 R/root에서 C는 coverage_snapshot_ref, E는 policy_envelope_ref의 각각 동일 bytes로 복원한다. 각 함수가 R.policy_id에 대응하므로 후속에도 C.inventory.policy_id == E.policy_id와 scope edition/R 연결을 보존한다.

C.bindings의 rule_root_id가 E.policy.root에 실제 존재하고 올바른 subtree를 소유하는지, 중첩·미매핑·composition이 맞는지는 기존 Coverage structure/Integration/evaluator 계약의 별도 검증이다. 이번 loader는 그 helper/evaluator를 실행하거나 중복 구현하지 않는다. legacy E.coverage는 generic C가 아니며 FULL을 나타내지 않는다.

## 14. Historical ReviewContext 분리

InventoryCompletenessReview/ImplementationBindingReview/Context/Review matching 상태는 이 raw에 없다. 기존 entry.coverage_reviews_ref에서 당시 기록을 독립 준비한다. 이번 함수가 Context·MATCHED·STALE·FULL을 생성하지 않는다.

후속은 실제 C/Policy의 Inventory/Tree/subtree 지문과 명시 Review의 policy/scope/version/condition/root·baseline을 기존 resolver/matcher로 대조해야 한다. Tree fp 일치는 그러한 Review 일치 또는 실제 사람 검토를 뜻하지 않는다. 현재 Context로 과거 원본을 대신하지 않는다.

## 15. Implementation Artifact 분리

R.coverage_implementation_fingerprint와 Tree fp는 각각 실행 코드 bytes와 정책 구현 정의라는 다른 대상이다. ZIP hash·검토 Context baseline·실제 동일 코드 실행 대응은 외부 역사 준비 책임이다.

M2.53은 합성 ZIP verify-only 구현이며 production/당시 업무 worker/FULL replay 완료가 아니다. 이번 함수는 ZIP/bootstrap/Git/환경/현재 프로세스 artifact를 조회하거나 실행하지 않는다. M2.52의 공유 ZIP 규칙도 적용 가능한 역사 프로파일에서만 연결하며 모든 hash를 무조건 같다고 강제하지 않는다.

## 16. dataset/Registry/Manifest provenance

Envelope는 dataset_version과 SourceBinding의 source_document_id/document_version을 실제로 보존한다. dataset은11절에서 R과 비교하고 source versions는 기존 생성자의 문법·유일성·leaf source 집합 대응까지만 확인한다.

Envelope에는 **source_registry_fingerprint가 없다**. Registry 지문을 source ID/d version이나 Tree fp로 계산·대체하지 않는다. 실제 당시 SourceRegistry에 기존 fingerprint_source_registry를 적용하고 R.coverage_source_registry_fingerprint 및 Context/Manifest.source_registry.fingerprint와 대조하는 것은 후속 검증이다.

DatasetManifest/PolicyEditionReference는 전체 release의 policy/edition/rule/schema/Envelope domain fingerprint·독립 artifact ref를 연결한다. E.policy_envelope_ref 자체를 Manifest가 검증됐다는 증거로 쓰지 않는다. 후속에는 Entry.policy_envelope_ref와 해당 Manifest reference.artifact, 실제 E에 대한 기존 fingerprint_policy_envelope도 대조해야 한다. 그 domain fp와 raw file H/Tree fp는 서로 다르다.

Manifest 전체 Envelope 집합·Registry/source version·ENGINE_VERSION 검증을 유지한다. 과거 엔진과 현재 코드가 비호환이면 역사 환경 준비 부족이며 기존 validator의 engine 비교를 삭제하지 않는다. 이번에 Manifest/Registry/Context를 API에 추가하지 않는다.

## 17. VERIFIED 선언과 gate

E.verification_status/last_verified_at/effective dates/lifecycle/evaluation_scope를 원문대로 복원한다. DRAFT를 VERIFIED로 바꾸지 않는다. VERIFIED와 날짜 필수성 등의 기존 constructor 관계만 구조 검증하며 실제 검토·공식성·권한/최신성/사용일 적합성은 Source/verification gate 책임이다.

현재 실제 안산 DRAFT/CONDITION_SLICE와 정책별 blocker·ResidenceHistory OFFICIAL_INQUIRY_REQUIRED를 유지한다. parser의 실자료 flags 수용이나 이 함수 성공을 production acceptance로 확대하지 않는다.

## 18. 확정한 후속 pure API

다음 함수는 **아직 구현되지 않았다**. 기존 사용 패턴과 일치하는 이 API 하나를 선택한다.

```python
load_historical_policy_envelope_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> PolicyEnvelope
```

필수 keyword-only3개, 기본값/우회 옵션 없음. 후속 모듈 후보는 `backend/policy_engine/policy_data/historical_policy_envelope_loader.py`다. 입력은 exact bytes/기존 exact 타입만 받는다. expected digest/ref/현재 Policy/Registry/Context/verified flag/FULL Result를 별도 입력받지 않는다.

반환은 같은 B에서 기존 parser가 만든 **전체 PolicyEnvelope 하나**이며 Policy만 먼저 반환하거나 status/provenance field를 추가하지 않는다. Tree 계산/비교가 가능한 원본을 반환하므로 별도 HistoricalTree 타입이 필요하지 않다. filesystem/network/Git/env/시간/random/cache는 사용하지 않는다.

## 19. 성공의 보장 범위·실패 경계

성공은 selected ref의 H와 맞는 동일 bytes를 HP1/기존 raw schema/기존 parser로 전체 복원했고, policy/edition/rule version/실제 Tree fp/dataset이 R과 대응한다는 뜻이다. **quarter proof, generic FULL, Review MATCHED, Manifest/Registry/실제 implementation 검증, VERIFIED 진실성, Acceptance USABLE, 사용자 PASS/지급/Cashflow 적용은 아니다.**

| 상황 | 처리 |
|---|---|
| 잘못된 bytes/JSON/schema/Rule/ID·ref/Acceptance binding | loader PolicyDataError. 부분 성공 없음 |
| 정확한 과거 Tree·edition/version, 현재만 변경됨 | 정상 과거 원본. current 자료를 대체/비교하지 않음 |
| 같은 과거 version/다른 실제 Tree fp | 불변 확인본 모순. 정상 stale로 숨기지 않음 |
| DRAFT/ENDED/과거 효력기간 | 모델상 유효하면 원문 복원. 사용 가능성은 별도 |
| actual 파일/필수 당시 Review/Manifest/실행 환경 미확보 | 외부 준비 미완료. 좁은 E 복원과 전체 역사 검증 완료를 구별 |
| 기존 비정규 들여쓰기 파일 | H가 맞더라도 HP1 실패. 이번에 수정/자동 변환하지 않음 |

## 20. Error Contract — 후속 prefix21개

기존 PolicyDataError를 사용하며 새 예외 계층은 없다. raw/actual·expected 값/원문/path/ref/unknown key/기존 parser 원문 오류를 출력하지 않고 고정 field 경로만 보고한다. signature 위반은 일반 TypeError다.

| phase | exact prefix | 조건 |
|---|---|---|
| P0 | INVALID_HISTORICAL_POLICY_ENVELOPE_LOADER_INPUT |3입력 exact 타입 |
| P1 | HISTORICAL_POLICY_ENVELOPE_REVIEW_BINDING_MISMATCH | ACCEPTED/root ref/Entry 유일성/is |
| P2 | INVALID_HISTORICAL_POLICY_ENVELOPE_EXPECTED_REF | selected policy_envelope_ref 타입/nonnull |
| P3 | HISTORICAL_POLICY_ENVELOPE_BYTES_MISMATCH | B 전체 SHA 불일치 |
| P4 | INVALID_HISTORICAL_POLICY_ENVELOPE_ENCODING | BOM/invalid UTF-8 |
| P4 | INVALID_HISTORICAL_POLICY_ENVELOPE_JSON | JSONDecodeError/발생한 parser RecursionError |
| P4 | DUPLICATE_HISTORICAL_POLICY_ENVELOPE_JSON_KEY | 모든 깊이의 decoded key 중복 |
| P4 | INVALID_HISTORICAL_POLICY_ENVELOPE_NUMBER | float/exponent/NaN/Infinity·parse_int ValueError |
| P4 | INVALID_HISTORICAL_POLICY_ENVELOPE_UNICODE | 고립 surrogate |
| P5 | INVALID_HISTORICAL_POLICY_ENVELOPE_FIELDS | required 누락/unknown extra |
| P5 | INVALID_HISTORICAL_POLICY_ENVELOPE_SCHEMA | top2 schema literal 미지원 |
| P5 | INVALID_HISTORICAL_POLICY_ENVELOPE_TYPE | raw primitive/object/array/nullable 타입 |
| P5 | INVALID_HISTORICAL_POLICY_ENVELOPE_NODE | unsupported kind/rule_type |
| P5 | NONCANONICAL_HISTORICAL_POLICY_ENVELOPE_BYTES | 원본 B != HP1 bytes |
| P6 | INVALID_HISTORICAL_POLICY_ENVELOPE_MODEL | 기존 parse_policy_envelope의 PolicyDataError 및 하위 예외 |
| P7 | INVALID_HISTORICAL_POLICY_ENVELOPE_FINGERPRINT | 기존 Tree 지문 함수 PolicyDataError의 방어 경계 |
| P8a | HISTORICAL_POLICY_ENVELOPE_IDENTITY_MISMATCH | policy_id 불일치 |
| P8b | HISTORICAL_POLICY_ENVELOPE_EDITION_MISMATCH | scope.edition_id 불일치 |
| P8c | HISTORICAL_POLICY_ENVELOPE_RULE_VERSION_MISMATCH | rule version 불일치 |
| P8d | HISTORICAL_POLICY_ENVELOPE_TREE_FINGERPRINT_MISMATCH | 실제 Tree fp 불일치 |
| P8e | HISTORICAL_POLICY_ENVELOPE_DATASET_MISMATCH | 실제 dataset 불일치 |
| P9 | 오류 없음 | 전체 기존 PolicyEnvelope 반환 |

P6는 기존 공개 parser에1회 위임하고 **PolicyDataError 계층만 좁게** 새 고정 MODEL prefix/field=root로 대응한다. P7 지문 함수의 PolicyDataError는 FINGERPRINT/field=policy로 대응한다. 그 내부에서 기존 parse_policy_set은 Field/Operator/Group/FactBasis/Rule 오류를 기존 정책 오류로 변환한다. 기존 parser가 외부/내부 ID·flags·Envelope cross-field를 검사하는 순서를 보존한다. 새 loader에서 그 모델 의미 검사를 중복 구현하지 않는다. 예상 밖 모든 Exception을 포괄적으로 데이터 오류로 덮지 않는다.

정상 모델로 만들 수 없는 중복 Review Entry/ACCEPTED None ref는 기존 생성 단계 거부를 검증하고 frozen 객체를 강제 훼손하지 않는다. 기존 Review/Benefit/Coverage loader prefix·Coverage/evaluator 상태를 변경하지 않는다.

## 21. Validation precedence

1. P0 raw_bytes → artifact → expected_acceptance exact 타입.
2. P1 ACCEPTED → root ref → acceptance_ref 유일 조회 → entry.acceptance is R. P2 해당 policy_envelope_ref exact 타입/nonnull.
3. P3 같은 B 전체 SHA. 실패 뒤 decode/JSON/parser/Tree 지문 호출 없음.
4. P4 BOM → strict UTF-8 → JSON → Unicode scalar. duplicate/number/syntax 복합 오류는 parser에서 실제 먼저 발견한 사건을 보고한다. 전역 제한/수정 파싱 없음.
5. P5 root object/key 집합 → schema_version/rule_schema_version 타입/literal → 나머지6절 root 필드 순 raw shape/primitive. policy.root는 왼쪽 자식부터 depth-first pre-order로 각 node discriminator 타입/지원 종류 → exact key 집합 → primitive/하위 값을 검사한다. shape 순회는 iterative stack으로 표현 가능하며 새로운 node 모델은 없다. 각 object는 표의 required 순 missing 먼저/extra 다음, optional은 명시된 순서로 존재할 때만 검사한다. 마지막에 HP1 equality.
6. P6 바로 그 parsed root를 기존 parse_policy_envelope에1회 전달. 새로운 파일 읽기나 raw 수정을 하지 않는다. parser의 metadata → 내부 Policy/트리 → Envelope 기존 로컬 검증 순서를 그대로 따른다. parser가 감싼 RecursionError는 이 단계 MODEL이며 P4 JSON parser 실패와 구별한다.
7. P7 반환 E.policy의 actual Tree fp1회. P8 policy → edition → rule version → actual Tree fp → dataset 순으로 R과 비교.
8. P9 전체 성공 때만 E 반환. 상태/partial Policy/기본값 fallback 없음.

kind/rule_type 누락은 FIELDS, 그 key가 비문자열이면 TYPE, 지원하지 않는 문자열이면 NODE다. 분기 shape를 고르기 위해 leaf는 kind/rule_type required 여부를 먼저 확인하고, 지원 branch의 required key 순으로 나머지를 검사한다. P5는 Enum/date/연산자 의미·필드별 값 조합을 검사하지 않는다. canonical 형식의 잘못된 operator/date/age bool은 P6 MODEL이다. 같은 자료에 공백도 있으면 P5 NONCANONICAL이 먼저다. 잘못된 H는 이 모두보다 먼저다.

## 22. 합성 시나리오 — HP01~HP80

이번 **80개는 문서 사례이며 신규 실행 테스트는0개**다. E=실제 M2.57 반환 root/Entry와 외부 R 원본, H=그 policy_envelope_ref 고정 raw SHA, I=R의 policy/edition/rule version, F=R의 Tree fp, D=R의 coverage_dataset_version이다. C/V/L/X는 각각 별도 당시 Coverage/Review/release/실행 원본이다.

H/F 기대값은 fixture 저작 시 고정하고 base golden은 기존 GV literal을 재사용한다. 손상 raw의 P4 이후 오류는 그 bytes 자체에 맞게 미리 고정한 H로 이전 단계를 통과시킨다. old H를 유지한 mutation은 P3 실패를 확인한다. actual digest를 소비 중 expected로 채택하지 않는다. frozen 모델 강제 변조는 없다.

| ID | 입력 | 기대 결과 | phase | 독립 기대값 | 담당 | 후속 실행 테스트 |
|---|---|---|---|---|---|---|
| HP01 | 단일 atomic Policy | 기존 Envelope/Tree 전체 복원 | P9 | E/H/I/F/D | loader | 가능 |
| HP02 | Group+여러 leaf | 모든 node/ID/자식 순서 보존 | P9 | E/H/I/F/D | loader | 가능 |
| HP03 | 중첩 ALL/ANY/NOT | 전체 재귀 구조 보존 | P9 | E/H/I/F/D | loader | 가능 |
| HP04 | resident_registration leaf | region/date source/ref 보존 | P9 | E/H/I/F/D | loader | 가능 |
| HP05 | birth_date leaf | exact bounds/date/ref 보존 | P9 | E/H/I/F/D | loader | 가능 |
| HP06 | atomic+두 specialized 혼합 | supported4타입 누락 없음 | P9 | E/H/I/F/D | loader | 가능 |
| HP07 | household_income+FactBasis |5값/비교값 보존 | P9 | E/H/I/F/D | loader | 가능 |
| HP08 | in 후보 순서/중복 | tuple 원문 보존 | P9 | E/H/I/F/D | loader | 가능 |
| HP09 | 한국어 policy_name/excluded 설명 | 원문 UTF-8 보존 | P9 | E/H/I/F/D | loader | 가능 |
| HP10 | 같은 ref를 다른 leaf가 공유 | 허용, flatten dedupe 없음 | P9 | E/H/I/F/D | loader | 가능 |
| HP11 | 과거 edition/rule version | R에 맞으면 정상 역사 복원 | P9 | 과거 E/H/I/F/D | loader | 가능 |
| HP12 | DRAFT/ENDED·과거 기간 | 원값 유지, 사용 승인 없음 | P9 | E/H/I/F/D | loader | 가능 |
| HP13 | TT 합성/FF 실자료 flags | 기존 parser 경로 그대로 | P9 | 각 E/H/I/F/D | loader | 합성 JSON으로 가능 |
| HP14 | effective 날짜 omitted/null | 각 bytes/H 구별, None 복원 | P9 | 각 고정 E/H/I/F/D | loader | 가능 |
| HP15 | atomic basis omitted/null | 기존 허용 field에서 None | P9 | 각 E/H/I/F/D | loader | 가능 |
| HP16 | NFC/NFD·문자열 공백 차이 | 정규화 없이 보존 | P9 | 각각 고정 E/H/I/F/D | loader | 가능 |
| HP17 | 동일 입력100회 | 결정성/입력 불변/새 반환값 | P9 | 고정 E/H/I/F/D | loader | 가능, 사례1개 |
| HP18 |1byte 변경, old H | BYTES_MISMATCH | P3 | 원본 E/H | loader | 가능 |
| HP19 | 기대 H만 다른 값 | BYTES_MISMATCH | P3 | 독립 E/H | loader | 가능 |
| HP20 | 같은 filename 다른 bytes | BYTES_MISMATCH | P3 | 원본 E/H | loader/외부 | bytes 부분 가능 |
| HP21 | invalid UTF-8 | ENCODING | P4 | 손상 bytes 고정 E/H | loader | 가능 |
| HP22 | BOM | ENCODING | P4 | 손상 bytes 고정 E/H | loader | 가능 |
| HP23 | malformed/trailing JSON | JSON | P4 | 손상 bytes 고정 E/H | loader | 가능 |
| HP24 | root duplicate key | DUPLICATE_JSON_KEY | P4 | 손상 bytes 고정 E/H | loader | 가능 |
| HP25 | nested node/basis/region duplicate | DUPLICATE_JSON_KEY | P4 | 손상 bytes 고정 E/H | loader | 깊이별 가능 |
| HP26 | escape 후 같은 이름의 key duplicate | DUPLICATE_JSON_KEY | P4 | 손상 bytes 고정 E/H | loader | 가능 |
| HP27 | 추가 공백/key순서/newline | NONCANONICAL | P5 | 비정규 bytes 고정 E/H | loader | 가능 |
| HP28 | 한글 불필요 escape/-0 표현 | NONCANONICAL | P5 | 비정규 bytes 고정 E/H | loader | 가능 |
| HP29 | float/exponent/NaN/Infinity | NUMBER | P4 | 손상 bytes 고정 E/H | loader | token별 가능 |
| HP30 | 고립 surrogate key/value | UNICODE | P4 | 손상 bytes 고정 E/H | loader | 가능 |
| HP31 | root required key 누락 | FIELDS | P5 | 손상 bytes 고정 E/H | loader |16key 매개화 가능 |
| HP32 | root extra/새 wrapper/quarter | FIELDS | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP33 | schema 또는 rule schema 미지원 | SCHEMA | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP34 | root/policy/list/object 타입 오류 | TYPE | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP35 | leaf kind/rule_type 누락 | FIELDS, m1.0 추정 안 함 | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP36 | unknown kind/rule_type | NODE | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP37 | fingerprint node_type payload 입력 | FIELDS/NODE 첫 오류 | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP38 | Rule/group required field 누락 | FIELDS | P5 | 손상 bytes 고정 E/H | loader | 타입/key별 가능 |
| HP39 | specialized metadata 누락 | FIELDS | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP40 | 잘못된 operator/Field Enum | MODEL, 기존 parser | P6 | canonical 손상 E/H | loader/parser | 가능 |
| HP41 | children object/primitive | TYPE | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP42 | 빈 group/NOT 자식2 | MODEL | P6 | canonical 손상 E/H | parser | 가능 |
| HP43 | 중복 rule ID (group/leaf 포함) | MODEL | P6 | canonical 손상 E/H | parser | 가능 |
| HP44 | age bool/student_status 정수 | MODEL, bool-int coercion 없음 | P6 | canonical 손상 E/H | parser | 가능 |
| HP45 | FactBasis reference_year bool | TYPE | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP46 | FactBasis0/소득 basis 미제공/다른 field basis | MODEL | P6 | canonical 손상 E/H | parser | 가능 |
| HP47 | invalid date/뒤집힌 birth bounds | MODEL | P6 | canonical 손상 E/H | parser | 가능 |
| HP48 | RegionRef alias/부분 null/잘못된 pair | TYPE/MODEL 첫 오류 | P5/P6 | 손상 bytes 고정 E/H | loader/parser | 가능 |
| HP49 | 외부/내부 policy ID 불일치 | MODEL | P6 | canonical 손상 E/H | parser | 가능 |
| HP50 | 외부/내부 flags 불일치/혼합 | MODEL | P6 | canonical 손상 E/H | parser | 가능 |
| HP51 | flags 정수 | TYPE | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP52 | included leaf 집합 불일치 | MODEL | P6 | canonical 손상 E/H | Envelope | 가능 |
| HP53 | source binding ID 중복/집합 불일치 | MODEL | P6 | canonical 손상 E/H | Envelope | 가능 |
| HP54 | 한 leaf duplicate/malformed evidence | MODEL, dedupe 없음 | P6 | canonical 손상 E/H | Envelope | 가능 |
| HP55 | 한글을 canonical evidence ref로 공급 | 기존 source#locator 문법 오류 | P6 | canonical 손상 E/H | Envelope | 가능, 한국어 설명과 구별 |
| HP56 | last_verified_at missing | FIELDS | P5 | 손상 bytes 고정 E/H | loader | 가능 |
| HP57 | VERIFIED+last_verified_at null | MODEL | P6 | canonical 손상 E/H | Envelope | 가능 |
| HP58 | effective_from>effective_to | MODEL | P6 | canonical 손상 E/H | Envelope | 가능 |
| HP59 | 다른 revision/같은 값 R 복사본 | REVIEW_BINDING_MISMATCH | P1 | 실제 E의 원본 R | loader | 가능 |
| HP60 | 같은 benefit의 다른 Entry bytes | selected R의 H로 거부 | P3 | 선택 E/H | loader | 가능 |
| HP61 | Entry 없음/root ref 불일치 | REVIEW_BINDING_MISMATCH | P1 | R 원본+다른 정상 root | loader | 가능 |
| HP62 | 중복 Entry/ACCEPTED None ref | 기존 모델 생성 단계 거부 | 진입 전 | 정상 생성 시도 | Review 모델 | 강제 훼손 없이 가능 |
| HP63 | REVOKED 직접 공급 | subject 오류, ref None 유지 | P1 | 실제 M2.57 B/root | loader | 가능 |
| HP64 | raw Policy와 R policy 불일치 | IDENTITY_MISMATCH | P8a | E/H, R의 I/F/D | loader | 가능 |
| HP65 | 다른 edition_id | EDITION_MISMATCH | P8b | E/H, R의 I/F/D | loader | 가능 |
| HP66 | 다른 rule_version | RULE_VERSION_MISMATCH | P8c | E/H, R의 I/F/D | loader | 가능 |
| HP67 | 같은 version 다른 값/자식 순서/근거/FactBasis | TREE_FINGERPRINT_MISMATCH | P8d | E/H, R의 고정 F/I/D | loader | 가능 |
| HP68 | Tree fp 동일+dataset만 다름 | DATASET_MISMATCH | P8e | E/H/I/F, R의 D | loader | 가능 |
| HP69 | 동일 연도 Q3/annual R 각각 | year만 일치, quarter 증명 아님 | P9/후속 | 각 E/H/I/F/D 및 C/V | loader/Content | 경계 가능 |
| HP70 | 정확한 과거 Tree, 현재 Tree만 변경 | 과거 원문 유지, 자동선택 없음 | P9/후속 | 과거 E/H/I/F/D | loader | 가능 |
| HP71 | SHA+JSON/Enum+공백/다중binding 오류 | 명시 phase/축의 첫 오류 | 복합 | 각각 독립 E/H/I/F/D | loader | 가능 |
| HP72 | JSON recursion/int 제한·기존 parser recursion | P4 JSON/NUMBER 또는 P6 MODEL | P4/P6 | E/H·격리 실패 주입 | loader/parser | 전역 설정 불변으로 가능 |
| HP73 | Envelope 성공/C 미확인 | generic FULL 아님 | 후속 | 별도 C/V | evaluator/외부 | 경계 가능 |
| HP74 | Tree fp 일치/Review 미확보 | Review MATCHED 아님 | 후속 | 당시 V | Content/Review | 경계 가능 |
| HP75 | Tree fp와 같은/다른 implementation hex | 실제 코드 검증 아님 | 외부 | 실제 X | 실행 준비 | 진실성은 bytes+실행 필요 |
| HP76 | VERIFIED 선언+날짜만 정상 | 실제 검토/권한 인증 아님 | 후속 | 공식 source/검토 원문 | Source/L3 | 기계 경계만 가능 |
| HP77 | Registry 지문/Manifest 원본 없음 | 전체 provenance 완료 아님 | 후속 | 당시 L/V | Content/외부 | 경계 가능 |
| HP78 | bytearray/subclass/잘못된 typed 인자 | LOADER_INPUT | P0 | 나머지 정상 E | loader | 가능 |
| HP79 | 기존 pretty-print 파일의 H 정확 | HP1 실패, 실제 release 수정 없음 | P5 | 고정 E/H | loader/외부 | 합성 동형 bytes로 가능 |
| HP80 | 정확한 E/Tree이나 사용일/개인 정보 없음 | USABLE/PASS/현금흐름 승인 아님 | 후속 | 별도 current/context/gate | evaluator/Bridge | 경계만 가능 |

위 축약 오류명은20절 exact prefix를 뜻한다. HP73~HP80 등의 신뢰 경계는 미구현 기능/실제 사람 검토를 실행 완료로 세지 않는다. 후속 fixture의 전체 Envelope는 legacy coverage/source/flags invariant까지 맞춰야 하며, Tree 지문 함수 단독으로 허용되던 leaf duplicate를 Envelope 정상 사례로 옮기지 않는다.

## 23. 후속 Content Validator 연결

같은 R/root의 policy_envelope_ref에서 얻은 E와 동일 ref/B를 보존한다. M2.58의 historical_envelopes에는 당시 **전체 Manifest 집합**의 Envelope 원본을 공급해야 하므로 이 한 선택 E만으로 전체 release를 대체하지 않는다. 다른 Envelope도 각 명시 원본에서 준비해야 한다. historical_artifact_bytes에도 같은 ref/B를 쓴다.

그 다음 실제 C/ReviewContext/Registry/Manifest/source/implementation을 원본별로 결합하고 L1/L2·별도 L3/Source/FULL 근거를 확인한다. M2.58의 Content Validator는 evaluator를 자동 재실행하거나 외부 FULL bool/Result를 받지 않는 결정을 유지한다. 정확한 당시 실행으로 FULL 재현이 필요하면 별도 준비 환경에서 기존 공식 evaluator를 사용한다.

이번 후속 loader는 Coverage structure/Review/Manifest 검사·FULL을 실행하지 않는다. 기존8입력 Acceptance evaluator나 current C의 producer 경로를 변경하지 않는다. 같은 입력/사용일이 바뀌면 새로운 평가 호출이며 과거 성공을 cache/token으로 재사용하지 않는다.

## 24. Assumptions·미해결 의존사항

| 항목 | 명시 경계 |
|---|---|
| A1 | 신뢰된 외부 R/expected records·실제 M2.57 반환값을 같은 호출에서 공급함. 로컬 타입으로 발급 진실성을 인증하지 못함 |
| A2 | 고정 path의 HP1에 맞는 당시 보관본 bytes를 확보함. 기존 pretty 파일을 몰래 바꾸지 않으며 실제 보관/발급은 이번에 없음 |
| A3 | quarter 적용·공식 의미/사람 권한·Source 사용요건·실제 실행 대응은 별도 확인. 이 함수가 충족됐다고 가정해 승인하지 않음 |
| 좁은 준비 완료 | 기존 raw schema/HP1/기대 H/같은 parsed object→기존 parser/Tree fp/확인 가능한 binding/API/오류 순서를 확정. 추가 모델 변경 blocker 없음 |
| 남은 원본 | Historical ReviewContext/Manifest strict codec, 실제 Registry/source/ZIP·역사 실행 대응, quarter 적용 검토 근거 |
| 남은 기능 | 이번 loader 구현/합성 검증, 외부 preparation, 전체 Content Validator/Source Gate/Acceptance evaluator/adapter/Bridge |

엄격한 canonical profile의 적용 범위와 기존 archive bytes 미수용은5절의 알려진 제한이다. 실제 bytes/ref가 이 profile에 맞지 않으면 외부 준비/이 함수가 실패하며 성공을 꾸미지 않는다. 그 제한을 없애려고 기존 release/loader/지문/동결 모델을 변경하지 않는다.

## 25. 최종 판단

**READY_TO_IMPLEMENT_HISTORICAL_POLICY_ENVELOPE_LOADER**

기존 object parser가 네 타입의 전체 Tree와 Envelope metadata를 복원하고, 독립 H와 동일 bytes를 결합한 뒤 실제 Tree fp 및 policy/edition/version/dataset을 대조할 수 있다. quarter는 없는 필드이므로 확인 가능한 year와 분리했다. 동결 Coverage와 충돌하지 않는다. Review/Manifest 미구현을 이유로 이 좁은 함수까지 차단하지 않으며 전체 역사 FULL/사용 승인을 선언하지 않는다.

## 26. 다음 최소 작업 하나

승인 후 **M2.64 — Historical PolicyEnvelope Strict Bytes Loader 구현** 한 개다.18절3인자 API·기존 parse_policy_envelope1회·Tree fp1회·20~21절 오류 순서·22절 해당 합성 사례만 구현/검증한다.

새 Rule parser/자동 canonical 파일 변환·실제 archive 발급·Review/Manifest codec·Source Gate·Content Validator·evaluator·Bridge/Cashflow·실제 정책 원본 생성으로 확대하지 않는다. 이번 M2.63에서는 구현하지 않는다.

## 27. 검증·보존 기록

- 작업 전 전체 pytest: **8,234 passed in 68.26s / skipped0 / failed0 / timeout0**.
- 신규 실행 테스트: **0개**. HP01~HP80은 문서 사례80개다.
- 작업 후 전체 pytest: **8,234 passed in 72.41s / skipped0 / failed0 / timeout0**. 전후 최초 전체 실행이 모두 통과했고 실패/timeout 후 재실행은 없었다. 기존 테스트/fixture/기대값·timeout/테스트 설정은 변경하지 않았다.
- 사전 backend/tests/data/docs/tools181개(실제 releases·pycache 별도)의 SHA256이 모두 동일하다. 새 문서1개만 추가하여 최종182개이며 기존 파일 수정/삭제0개다. 기존 모델/Policy parser·Coverage core/freeze 문서·지문·M2.60/M2.62/Review loader·Acceptance/Context/Result·bootstrap/Cashflow를 보존했다.
- GV01~GV15/BV01~BV16 literal/계산 코드를 보존했고 기존8,234개 회귀가 모두 통과했다. 신규 실행 테스트0개와 문서80사례는 구분한다.
- 실제 release6개는 SHA256·경로·크기·수정시각이 모두 동일하다. 다음은 기존 원본의 전후 동일 SHA이며 새 정책/Artifact 지문 발급이 아니다. root는 `data/releases/`다.

| 기존 release 상대 경로 | 전후 동일 SHA256 |
|---|---|
| ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |
| ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

- 문서 검수:27개 절·HP01~HP80 연속/유일성·21개 오류 prefix 유일성·API3개 필수 keyword-only 인자·실제 Envelope15필드와 raw root required16/optional2의 AST 대조·table/fence·UTF-8/한국어를 확인했다. 검수는 신규 실행 테스트 수에 더하지 않는다.
- 실제 안산 PolicyEnvelope/Acceptance/FULL Result·실행 ZIP을 생성하지 않았다. 기존 pretty-print releases를 canonical로 재작성하거나 hash/ref를 갱신하지 않았다.
- GV01~GV15/BV01~BV16·Coverage freeze·기존 모델/loader/지문·bootstrap/Cashflow·실제 release6개를 보존한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 28. M2.64 — IMPLEMENTED: Historical PolicyEnvelope Strict Bytes Loader

### 28.1 구현 API와 파일

```python
load_historical_policy_envelope_bytes(
    *,
    raw_bytes: bytes,
    artifact: AcceptanceReviewArtifact,
    expected_acceptance: PolicyBenefitAcceptance,
) -> PolicyEnvelope
```

세 인자는 필수 keyword-only/exact 타입이다. subclass·bytearray·dict·ref 문자열을 자동 변환하지 않는다. 새 loader는 `backend/policy_engine/policy_data/historical_policy_envelope_loader.py`, 합성 테스트는 `tests/test_historical_policy_envelope_loader.py`다. package에서 위 함수 하나만 추가 export했다. 기존 모델/저장 필드/parser/지문/다른 historical loader/실제 자료를 변경하지 않았다.

### 28.2 P0~P9 실제 경로

```text
exact bytes + 같은 호출의 Artifact + 외부 Acceptance R 원본
  → ACCEPTED / root ref / acceptance_ref 유일 Entry / entry.acceptance is R
  → selected policy_envelope_ref exact ArtifactReference
  → selected ref.sha256 대 동일 bytes 전체 SHA256
  → BOM / strict UTF-8 / strict JSON / Unicode scalar
  → 기존 raw A의 key set·primitive / HP1 원본 bytes equality
  → 같은 parsed root로 기존 parse_policy_envelope 1회
  → 반환된 E.policy로 기존 fingerprint_policy_tree 1회
  → policy / edition year / rule version / 실제 Tree fp / dataset 독립 비교
  → 기존 불변 PolicyEnvelope E 그대로 반환
```

기대 H는 선택 Entry의 독립 ref.sha256이며 실제 계산값으로 대체하지 않는다. 다른 Entry/ref/Tree/Registry/implementation 지문으로 fallback하지 않는다. path는 위치 식별자로만 남고 loader가 파일을 열지 않는다. 원본 bytes를 다시 읽거나 파싱 결과를 수정하지 않는다. 반환 객체는 기존 parser가 반환한 바로 그 객체다.

P5 private helper는 raw shape만 검사한다. RuleNode 모델·Enum/date/operator 의미·cross-field invariant는 기존 parser/생성자에 위임한다. 네 타입 PolicyRule/RuleGroup/ResidentRegistrationRule/BirthDateRule, FactBasis와 전체 자식 계층/순서/원문 근거/비교값을 보존한다. optional effective_from/to와 atomic fact_basis는 생략/null의 기존 의미를 유지하며 HP1 비교 전에 값을 채우지 않는다. 한 leaf의 중복 근거와 한글 근거 ref는 기존 Envelope 문법대로 거부한다. 다른 leaf가 같은 근거를 공유하는 것은 허용한다.

### 28.3 HP1·오류·순수성

8절 HP1과20~21절 **21개 prefix/P0~P9 우선순위**를 그대로 구현했다. decoded key 중복은 모든 깊이에서 거부한다. BOM/invalid UTF-8/malformed JSON/float·exponent·NaN·Infinity/고립 surrogate를 구별한다. 실제 JSON parser RecursionError와 parse_int ValueError를 대응하며 전역 제한을 바꾸지 않는다. schema shape는 명시 required 순서와 왼쪽 depth-first preorder로 검사한 뒤 HP1을 비교한다.

기존 parser의 PolicyDataError만 MODEL/field=root, 기존 지문의 PolicyDataError만 FINGERPRINT/field=policy로 좁게 대응한다. 예상 밖 RuntimeError를 덮지 않는다. signature 위반은 TypeError다. unknown key/value·bytes·ref/path·하위 오류 내용은 오류 메시지에 복사하지 않는다. 실패 시 partial Envelope나 STALE/FULL/사용 상태로 변환하지 않는다.

Entry 중복/ACCEPTED None ref는 기존 생성자가 정상 입력 단계에서 차단한다. 이 불가능한 상태를 만들려고 frozen 모델을 훼손하지 않았다. P2의 방어 검사와21개 prefix 존재를 검수한 것과 모든 prefix를 정상 domain 객체로 발생시켰다는 주장은 구분한다.

외부 I/O/network/Git/env/current time/random/cache/bootstrap/evaluator/Review matching/Result factory/Manifest 검증을 실행하지 않는다. 기존 파일 loader·다른 historical loader·SourceRegistry를 호출하지 않는다. 새 generic framework나 기존 helper 공통화를 추가하지 않았다.

### 28.4 합성 테스트와 HP01~HP80 대응

신규 실행 테스트는 **747개**다. 문서80개 사례와 pytest parameterized case 수는 다르다. 실제 M2.57 loader로 Artifact와 외부 R 원본을 준비한 뒤 새 loader를 호출한다. 손상 JSON/schema 사례도 미리 해당 bytes의 H를 준비해 P3를 통과시킨다. 원래 H를 고정한1byte mutation은 P3 실패를 별도로 검사한다. base HP1은810bytes/SHA256 `df9d56456db5fb2c5a20ba3b9783e7f5be2574acdf43466eb1970a382c0a7bd7`로 고정했다. Tree base는 기존 GV07 literal을 사용하며 GV08/09/10/11/14/15도 실제 복원 객체로 대조했다.

| 문서 사례 | 실행 검증 또는 경계 |
|---|---|
| HP01~HP10 | atomic/group/중첩 ALL·ANY·NOT/두 specialized/FactBasis/in/한국어 설명/leaf 간 공유 근거 |
| HP11~HP17 | 과거 metadata·TT/FF·optional omitted/null·NFD 원문·100회 결정성/입력 불변 |
| HP18~HP30 | 기존 H mutation·선택 H·encoding/JSON/duplicate/HP1/number/Unicode |
| HP31~HP58 | required/extra/exact nested type/discriminator·기존 모델 의미/ID·flags·source/evidence·날짜 조합 |
| HP59~HP68 | Entry 원본 identity/다른 revision/REVOKED/기존 생성자 거부·다섯 Acceptance 축 |
| HP69~HP72 | 연도만 비교/current 미대체/다중 오류 우선순위·격리 recursion 실패 주입 |
| HP73~HP80 | 반환값/호출 격리로 FULL·Review·실행·Manifest·USABLE을 만들지 않음. pretty-print는 합성 동형 bytes로 HP1 거부 |

P6/P7 spy는 기존 parser가 같은 parsed root를1회 받고 Tree fp는 실제 반환 E.policy로1회 계산됨을 확인한다. 원문 파싱 결과·Artifact/Entry/R/ref/bytes의 불변성, 기존 frozen/slots·직렬화 사본 격리도 확인했다. 불가능한 ref/Entry 오류는 기존 생성자 거부 테스트이며 실제 검토/실행 진실성을 테스트 완료로 세지 않는다.

### 28.5 성공 범위와 미구현

**IMPLEMENTED:** Historical PolicyEnvelope strict bytes loader·기존 전체 Rule Tree parser 재사용·실제 Tree fingerprint 재계산/비교·Acceptance Policy/edition year/rule/dataset binding·합성 실행 테스트.

**NOT IMPLEMENTED:** Historical ReviewContext/Manifest loader·quarter scope verification·외부 파일 확보·Source Gate·Review Content Validator·Acceptance Evaluator·Benefit Bridge/Cashflow 연결·실제 안산 역사 원본/Acceptance/FULL 생성·implementation ZIP 실행 검증.

2026 edition과2026/Q3 R은 연도만 확인한다. 이름/URL/birth range/현재 날짜로 분기를 추론하지 않는다. VERIFIED 선언과 날짜가 복원돼도 현재 검토 gate 인증이 아니다. coverage-policy-tree-1.0은 실행 ZIP 지문이 아니며 당시 FULL/Review MATCHED/현재 USABLE/사용자 PASS를 증명하지 않는다.

기존 실제 pretty-print release는 H가 일치해도 HP1에서 실패하는 알려진 경계다. 합성 성공을 실제 release 호환성으로 확대하지 않고 기존 파일/bytes/hash/ref를 자동 정규화하거나 재작성하지 않았다. 한국어 정책명/설명은 원문 그대로 보존하지만 canonical source#locator의 ASCII 식별자 규칙은 바꾸지 않는다(HP55).

### 28.6 회귀·보존 기록

- 사전 전체 pytest: **8,234 passed in 73.76s**.
- 신규 합성 테스트: **747 passed in 2.97s**.
- 최종 전체 pytest: **8,981 passed in 64.76s / skipped0 / failed0 / timeout0**. 기존8,234개+신규747개다. 사전/최종 전체 실행은 각각1회 통과했으며 기존 테스트/fixture/기대값·설정은 수정하지 않았다.
- SHA256 기준선182개 중179개 동일, 변경3개는 package export와 이 문서/ARCHITECTURE뿐이다. 신규 loader/합성 테스트2개를 더해184개다. 기존 파일 삭제0개이며 기존 모델/parser/지문·Coverage 동결 core/문서·Historical Benefit/Coverage/Review loaders·Acceptance/Context/Result·bootstrap/Cashflow는 그대로다.
- GV01~GV15/BV01~BV16의 literal/계산 코드·기존 회귀를 보존했다. 실제 release6개는27절 표의 SHA256과 모두 같고 경로·크기·수정시각도 동일하다. pretty-print를 HP1로 재작성하거나 새 실제 Artifact/Acceptance를 발급하지 않았다.
- Python AST/API·21개 prefix·문서 구조/UTF-8·HP01~HP80 사례 대응을 검수했다. 문서 검수와 방어 경계 검토를 신규 실행 테스트 수에 더하지 않는다.

### 28.7 최종 판단과 다음 최소 작업

최종 판단은 **HISTORICAL_POLICY_ENVELOPE_LOADER_COMPLETE**다. 다음 최소 작업은 **Historical CoverageReviewContext Artifact Preparation Contract 설계 한 개**다. 별도 coverage_reviews_ref에서 복원할 ReviewContext/검토 기록의 raw schema·기대 H·same-call 결합·오류/순서를 먼저 확정하며 이번에 그 loader를 구현하지 않는다.

Generic Coverage freeze와 실제 정책 blocker를 유지한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.
