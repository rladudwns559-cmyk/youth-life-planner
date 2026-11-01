# Coverage 지문 canonical payload 계약 — M2.16

> 현재 구현 상태는 35절 M2.19를 따른다. 1~32절은 M2.16 설계 기록이다. Inventory/전체 Tree/subtree 지문을 구현했고 lookup·matching·validator는 없다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 설계 전용**. 추가 산출물은 이 파일 하나다. 계산 함수·모델·테스트·기존 문서는 변경하지 않았다.

최종 판단: **READY_TO_IMPLEMENT_COVERAGE_FINGERPRINT_UTILS**. 이 판단은 아래 세 순수 함수의 합성 구현 준비에 한정한다. 실제 정책 지문 발급·검토 승인·Coverage FULL·배포 승인이 아니다.

## 1. 목적

Coverage 검토가 의도한 정책 조건 목록, 전체 실행 tree, 조건별 subtree, 입력모델/evaluator 배포물의 확인본을 수개월 뒤에도 같은 규칙으로 식별한다. SHA256 알고리즘만 정하는 대신 입력 경계·명시 필드·순서·문자 인코딩·오류·고정 벡터를 계약으로 고정한다.

최우선 기준은 COVERAGE_REVIEW_CONTEXT_SPEC.md 20절이다. ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md, POLICY_COVERAGE_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md와 현재 코드를 대조했다. 특히 M2.12의 세 schema 이름·Inventory 정렬·evidence 순서·tree 자식 순서·rule_version 포함·artifact bytes 분리를 유지한다. 새 이름이나 hash 형식으로 바꾸지 않는다.

작업 전 확인한 현재 값 모델은 RequiredCondition/ConditionInventory/ConditionBinding/EligibilityCoverage, 두 review record, CoverageReviewContext다. Policy/RuleGroup/RuleNode와 네 노드의 실제 필드, RegionRef/FactBasis, 기존 _jsonable 및 Manifest/Registry 지문 구현도 확인했다. 정책 원문을 새로 조회하거나 행정 의미를 확정한 작업이 아니다.

## 2. Fingerprint 역할

| 지문 | 대상 | A 표현 확인본 / B 의미 정규화 선택 |
|---|---|---|
| inventory_fingerprint | policy/scope/version에 고정된 조건 의미·근거 목록 | **제한된 B**: 조건 집합 순서만 ID순 정규화. 나머지는 정확한 표현 보존 |
| policy_tree_fingerprint | 정책 ID·rule version 및 executable eligibility tree | **A**: 선언한 구현 구조·값·근거·순서의 확인본 |
| subtree_fingerprint | 명시 root 자체와 그 아래 전체 구현 | **A**: 부모/정책 metadata 없는 구현 확인본 |
| implementation_fingerprint | 검토한 입력모델/evaluator 소스 배포물 또는 빌드 artifact의 정확한 bytes | **A**: 원본 bytes identity |

여기서 A는 원본 JSON 파일의 공백까지 hash한다는 뜻이 아니다. 도메인에서 명시한 payload의 표현을 고정한다는 뜻이다. 원본 파일 bytes hash는 별도다. B도 자연어 의미 이해·논리 동치·조건 병합·집합 연산 정규화가 아니다. ALL(A,B)와 ALL(B,A), 동의어 meaning, 근거 순서가 다른 두 확인본을 자동 동치로 처리하지 않는다.

이하 “변경 시 지문이 다르다”는 SHA256 충돌을 무시할 수 있다는 통상적인 변경 감지 전제에서의 계약이다. 수학적인 무충돌·진실성 증명이 아니다.

## 3. 공통 SHA256 계약

Inventory/tree/subtree는 명시 payload → canonical JSON 문자열 → strict UTF-8 bytes → SHA256 → lowercase hexdigest 순서다.

- 결과는 정확한 str의 소문자 16진수64자리이며 접두사·공백·newline이 없다.
- BOM과 문자열 말미의 newline을 bytes에 추가하지 않는다.
- 입력 객체, tuple, 하위 값, 원래 직렬화 결과를 변이하지 않는다.
- Python hash(), repr, str(dataclass), 주소·경로·파일명·set 순회·현재시간을 지문 입력으로 삼지 않는다.
- implementation artifact만 JSON 변환 없이 **원래 artifact bytes 전체**를 hash한다. 그 bytes에 원래 있던 BOM/newline도 제거하지 않는다.

## 4. Canonical JSON

기존 manifest._digest와 동일한 다음 인코딩 recipe를 사용한다. 아래는 명세식이며 이번에 함수로 구현하지 않았다.

```python
json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8", errors="strict")
```

| 항목 | 계약 |
|---|---|
| object keys | 명세에 열거한 문자열 key만 사용, 모든 깊이에서 사전순 정렬 |
| 구조 공백 | indent 없음, 구분자 뒤 공백 없음, 마지막 newline 없음 |
| 문자열 | exact 원문. strip/대소문자 변경/NFC·NFD 정규화/줄바꿈 치환 없음 |
| escaping | 표준 json.dumps 규칙. 한글은 실제 UTF-8, 따옴표·역슬래시·제어문자는 JSON escape |
| int | 기존 모델이 허용한 exact int, 10진 정수. float/Decimal/NaN/Infinity로 대체 금지 |
| bool | true/false. bool을 int로 보거나 문자열로 바꾸지 않음 |
| None | 허용된 nullable 필드에서는 null. key 자체를 생략하지 않음 |
| enum | 해당 필드의 정확한 기존 Enum만 .value의 canonical 문자열로 변환 |
| date | exact date의 isoformat(), YYYY-MM-DD. datetime 절삭/지역시각 변환 없음 |
| tuple | 모델 입력에서 exact tuple. payload에서는 같은 순서의 새 list |
| list/set/raw dict 입력 | public domain 함수의 자동 입력 변환 없음. payload dict/list는 함수 내부에서만 구성 |

동일 payload는 같은 bytes를 내야 한다. 이 계약은 float를 받지 않는 명시적인 Python JSON recipe이며 RFC 8785/JCS 전체 구현을 뜻하지 않는다. 다른 언어 구현도 이 recipe의 문자열 escaping·정수·UTF-8와 golden bytes를 맞춰야 한다. 고립 surrogate 등 strict UTF-8 불가 문자열은 오류이며 replace/ignore하지 않는다. 모델 문자열 안의 공백은 보존하므로 구조 공백 제거와 구별한다.

## 5. Inventory fingerprint 의미

한 ConditionInventory가 특정 policy_id/scope/inventory_version에서 어떤 REQUIRED/CONDITIONAL 의미·근거 목록을 갖는지 고정한다. completeness_review_ref가 있거나 없다는 검토 metadata와 조건 목록 자체의 의미를 분리한다.

ConditionInventory 생성자는 비어 있지 않은 정확한 RequiredCondition tuple과 유일 condition_id를 이미 요구한다. 지문 함수는 빈/중복 조건을 정상화해 새로운 목록을 만들지 않는다. 현재 사용자에게 조건이 비적용이라는 이유로 목록에서 제거하지 않는다.

## 6. Inventory payload

최상위 key는 정확히 다음 다섯 개다.

| key | 값 |
|---|---|
| fingerprint_schema | "coverage-inventory-1.0" |
| policy_id | inventory.policy_id 원래 문자열 |
| scope | edition_id/quarter 두 key. quarter=None이면 null |
| inventory_version | inventory.inventory_version 원래 문자열 |
| conditions | condition_id 오름차순의 C(condition) 목록 |

C(condition)의 정확한 네 key는 condition_id, meaning, requirement, evidence_refs다. requirement는 "REQUIRED" 또는 "CONDITIONAL", refs는 원래 순서/중복의 새 list다. 현재 RequiredCondition.to_dict()와 같은 값이지만 **명시적 필드 선택** 계약이다. 미래 to_dict 필드가 늘었다고 자동 포함하지 않는다.

제외: completeness_review_ref, review_ref, reviewed_at, review_artifact_ref, 준비자/검토자, ConditionBinding, Rule 객체, dataset/source/implementation 지문, 사용자 입력/평가 결과, Coverage status. review가 대상 지문을 참조하고 대상이 다시 review identity를 참조하는 자기참조와 검토 metadata 변경의 불필요한 전파를 피한다.

## 7. Inventory ordering

condition_id는 현재 [A-Z0-9_]+ exact str이다. Python 문자열 오름차순과 동일한 **ASCII code point 오름차순**을 사용한다. locale/자연 정렬/숫자 부분 분리/대소문자 보정이 아니다. 예: COND_10은 COND_2보다 앞선다.

입력 A=(COND_B,COND_A), 입력 B=(COND_A,COND_B)이고 각 조건 내용이 같으면 동일 payload·inventory_fingerprint다. 원래 Inventory equality/to_dict의 tuple 순서는 변경하지 않는다. duplicate condition_id는 기존 모델 오류이며 sort 뒤 dedupe하지 않는다. GV02/GV03이 고정 벡터다.

## 8. Tree fingerprint 의미

Policy의 전체 executable eligibility tree를 정책 ID·rule_version과 함께 고정한다. 판정값만 아니라 근거·node ID·자식 순서·nullable 필드까지 포함한 **검토된 구현 확인본**이다. 계산을 실행하거나 “동일한 truth table”을 증명하지 않는다.

Policy 자체에는 edition/scope가 없다. 그러므로 tree 지문이 Q3/annual 진위를 증명한다고 해석하지 않는다. scope는 Inventory 및 Review/Context의 독립 결합 책임이다.

## 9. Tree payload

최상위 key는 정확히 다음 네 개다.

| key | 값 |
|---|---|
| fingerprint_schema | "coverage-policy-tree-1.0" |
| policy_id | policy.policy_id 원래 문자열 |
| rule_version | policy.rule_version 원래 문자열 |
| root | N(policy.root) |

policy_name, synthetic, test_only, allow_real_data InitVar는 제외한다. category/jurisdiction/edition/verification/benefit 등 Envelope metadata도 포함하지 않는다. 실제 Policy에는 category 필드가 없으므로 가상 key를 만들지 않는다. flags 제외는 실제/합성 수용 gate를 없앤다는 뜻이 아니다.

현재 Policy/PolicyRule/RuleGroup은 자체 public to_dict가 없다. _jsonable은 dataclass 실제 필드를 자동 변환하며 node_type을 넣지 않는다. 따라서 _jsonable(policy)나 Envelope.to_dict 전체를 바로 hash하지 않고 위 명시 projection을 만든다.

## 10. Node별 payload

N은 정확한 네 타입만 explicit dispatch한다. node_type은 loader의 kind/rule_type alias가 아닌 아래 고정 문자열이다. 모든 표의 key를 항상 포함하고 optional key를 임의 생략하지 않는다.

### PolicyRule → atomic

| key | 값 |
|---|---|
| node_type | "atomic" |
| rule_id | 원래 str |
| field | Field.value: age/region/student_status/employment_status/household_income |
| operator | Operator.value: eq/in/gte/lte |
| value | 기존 검증된 exact str/int/bool 또는 in 연산의 ordered tuple→새 list |
| fact_basis | None→null 또는 아래 B(basis) |
| evidence_refs | 원래 순서·중복의 새 list |

실제 필드는 expected_value가 아닌 **value**다. fact_basis도 판정에 영향을 주므로 빠뜨리지 않는다. B는 basis, subject, period, reference_year, unit 다섯 key이며 네 문자열과 exact int를 그대로 보존한다. household_income은 기존 모델대로 정확한 FactBasis가 필수이고 다른 field에는 None이다.

### ResidentRegistrationRule → resident_registration

| key | 값 |
|---|---|
| node_type | "resident_registration" |
| rule_id | 원래 str |
| required_region | 정확히 sido/sigungu 두 문자열 key |
| reference_date_source | 현재 유일 지원 값 "APPLICATION_DATE" |
| evidence_refs | 원래 순서·중복의 새 list |

RegionRef의 namespace를 가상 필드로 추가하지 않는다. 사용자 resident facts·실제 application_date·evaluation_date는 넣지 않는다. 현재 지원되지 않는 reference source 변경은 “다른 유효 지문”이 아니라 모델/utility 오류다.

### BirthDateRule → birth_date

| key | 값 |
|---|---|
| node_type | "birth_date" |
| rule_id | 원래 str |
| min_birth_date | exact date의 ISO 문자열 |
| max_birth_date | exact date의 ISO 문자열 |
| evidence_refs | 원래 순서·중복의 새 list |

양끝 포함 의미는 현재 rule 타입의 고정 계약이다. 생일을 사용자 age로 역산하거나 입력 BirthFact를 넣지 않는다.

### RuleGroup → group

| key | 값 |
|---|---|
| node_type | "group" |
| rule_id | 원래 str |
| operator | GroupOperator.value: "ALL"/"ANY"/"NOT" |
| children | 원래 순서의 N(child) 목록, 중첩 group 전체 포함 |

group에 없는 evidence_refs/fact_basis를 가상으로 넣지 않는다. 현재 nonempty children·NOT 한 자식·node ID 유일성 계약을 유지한다.

지원 타입의 subclass, raw dict, to_dict가 있는 임의 객체, 미래 specialized node는 거부한다. Enum과 하위 RegionRef/FactBasis/date도 현재 정확한 타입 계약을 따른다. getattr/fields/asdict로 알 수 없는 새 필드까지 자동 수집하지 않는다.

## 11. Child ordering

ALL(A,B)와 ALL(B,A)는 일반적인 논리 결과가 같을 수 있어도 **다른 tree 지문**이다. 실제 evaluator의 결과/감사 trace와 직렬화 순서를 포함한 구현 확인본을 보존하기 때문이다. Group.children과 atomic IN.value tuple 모두 자동 sort/dedupe하지 않는다.

같은 child ID가 재사용되거나 서로 다른 node의 ID가 중복되면 기존 Policy/RuleGroup 구조 오류다. 이를 정렬이나 hash로 은폐하지 않는다. GV08/GV09가 순서 민감도를 고정한다.

## 12. Evidence 처리

**Inventory·tree·subtree 모두 evidence_refs를 포함하고 순서·중복을 그대로 보존한다.** [SRC1,SRC2]와 [SRC2,SRC1], [SRC1]과 [SRC1,SRC1]은 다른 확인본이다. 의미상 같은 근거 집합이라고 추측하여 정렬하지 않는다.

condition evidence는 공식 조건 의미와 연결되고 rule evidence는 구현 node와 연결된다. source_registry_fingerprint는 Registry 전체 확인본이다. Registry가 같아도 특정 node가 어느 locator를 어떤 순서로 참조하는지는 달라질 수 있어 역할이 중복되지 않는다. 반대로 Registry의 URL/검증일만 바뀌고 refs가 그대로면 tree/subtree는 같고 Registry 지문은 달라질 수 있다.

POLICY_DATA_ENVELOPE_SPEC.md 10~11절은 근거만 바뀔 때 rule_version 유지가 가능하다고 한다. 이 문서는 그 발행 버전 원칙을 변경하지 않는다. 다만 M2.12의 더 엄격한 **동일 rule_version + tree/subtree 지문 불일치 → review 대조 Data Error**도 유지한다. 따라서 근거가 바뀐 새 자료에 과거 implementation review를 그대로 재사용하지 않는다. 현재 내용으로 새 ref의 review를 준비해야 하며, 새 dataset만 붙이면 과거 review가 자동 수용된다고 해석하지 않는다. 지문 utility는 이 매칭/오류/stale gate를 실행하지 않는다.

## 13. Rule version 처리

M2.12대로 전체 tree payload에 rule_version을 **포함**한다. 내용이 같아도 r0001→r0002이면 전체 tree 지문은 달라진다. review의 별도 rule_version 필드는 정상 버전 갱신과 같은 버전 내용 모순을 구별하는 진단/gate용이므로 중복이 아니다.

subtree에는 rule_version을 넣지 않는다. 같은 subtree가 여러 정책/규칙 버전에서 동일하게 존재할 수 있다. 검토 재사용 가능 여부는 전체 tree 지문·version·대상 결합도 따로 확인해야 한다. rule_version은 현재 Policy와 같은 exact 비공백 str을 보존하며 utility에서 Envelope의 r#### 제한을 추가하지 않는다.

## 14. Subtree fingerprint와 입력 선택

비교한 두 API:

| 선택 | 장점 | 문제 / 결정 |
|---|---|---|
| Policy + rule_root_id | 호출 한 번에 대상 찾기 가능 | lookup/소유 검증과 계산 책임 혼합. 미채택 |
| 정확한 RuleNode root | 순수 계산 경계가 작고 전체 tree와 N을 재사용 | 소속/존재는 외부 검증 필요. **채택** |

후속 validator가 Policy에서 root를 찾아 소속·유일성을 확인한 뒤 명시 root를 전달한다. utility는 부모, Policy, Binding을 받거나 검색하지 않는다. root만으로 어떤 정책에 속했는지 인증하지 않는다.

## 15. Subtree payload

정확한 두 key: fingerprint_schema="coverage-subtree-1.0", root=N(root). root 자체의 type·ID·operator·모든 필드와 descendant 전체가 들어간다. leaf만 hash하거나 group operator를 빠뜨리지 않는다.

동일한 root subtree가 다른 부모/정책 위치로 이동하면 subtree 지문은 같고 전체 tree 지문은 달라질 수 있다. GV12는 GV08의 group을 동일 N으로 사용하지만 schema와 최상위 key가 달라 전체 tree 지문과 다르다.

존재하지 않는 rule_root_id는 **후속 root lookup의 PolicyDataError**다. 채택한 root-only 함수에는 문자열 ID를 검색하는 “not found” 경로가 없다. None/문자열/raw dict를 root로 넘기면 wrong node type 오류다. 중복 ID는 기존 Policy/RuleGroup에서 거부하며 malformed subtree도 정상 결과로 hash하지 않는다.

## 16. Implementation fingerprint 의미·계산 범위

외부에서 검토한 **입력모델/evaluator 소스 배포물 또는 빌드 artifact 전체의 정확한 bytes SHA256**이다. Tree는 정책 데이터이고 artifact는 그 데이터를 처리하는 실행 구현이므로 서로 대체할 수 없다. engine_version 문자열·Git SHA·파일명·선택 파일 목록의 임의 이어붙이기도 대체값이 아니다.

이번 및 후속 Coverage 순수 utility의 세 함수에서는 implementation_fingerprint를 계산하지 않는다. 외부가 준비한 lowercase hex64 값을 기존 Review/Context에 명시적으로 공급한다. 정확한 artifact bytes에 SHA256을 적용하는 의미만 고정하며 어떤 패키지/빌드/파일 범위를 artifact로 발행할지는 별도 작업이다.

**Assumption A1:** 외부 준비 계층이 실제로 검토한 입력모델/evaluator와 필요한 실행 의존성을 식별할 수 있는 고정 artifact 및 그 증빙을 제공한다. 파일별 경로·순서·환경을 추론하지 않는다. artifact가 아직 없으면 실제 engine hash나 review 승인 기록을 만들어내지 않는다. 실제 Manifest를 이 이유로 생략했던 기존 이력과 일치한다.

## 17. Source Registry 및 DatasetManifest와의 관계

기존 policy_data/manifest.py의 fingerprint_source_registry를 그대로 재사용한다. 이는 Registry.to_dict 전체에서 sources를 source_document_id순, locators를 locator_id순, supersedes를 (source_document_id,document_version)순, applicable_policy_ids를 문자열순으로 정렬한 canonical domain SHA256이다. 나머지 배열/값은 기존 함수대로 유지한다. 예를 들어 previous_urls를 새 규칙으로 정렬하지 않는다. 새 source 지문 함수나 schema label을 기존 payload에 소급 추가하지 않는다.

| 기존 값 | 의미 / Coverage 지문과 차이 |
|---|---|
| fingerprint_policy_envelope | Envelope 전체 확인본. source_bindings/included_rule_ids 정렬. metadata도 포함하므로 tree 지문의 대체가 아님 |
| fingerprint_source_registry | 위 Registry 전체 확인본. review의 source_registry_fingerprint와 같은 의미 |
| DatasetManifest.fingerprint() | 선언 metadata·artifact refs·domain 지문을 묶은 선택 목록. policy/source version 목록 정렬·시각 UTC 표현 포함 |
| ArtifactReference.sha256 | 원본 파일 bytes. JSON 공백/개행 변경도 감지 |
| engine_artifact_sha256 | 정확한 엔진 artifact bytes. 동일한 artifact 정의일 때 implementation_fingerprint와 같은 digest일 수 있음 |
| SourceDocument.content_sha256 | 공식 원문 bytes의 선택적 선언. Registry 전체나 engine bytes 지문이 아님 |

같은 64자리 형식이라도 대상이 달라 자동 복사하지 않는다. 같은 실제 bytes artifact를 가리킨다는 외부 증빙 없이 Manifest engine hash와 implementation_fingerprint를 같다고 가정하지 않는다. 기존 _digest/_hash/Manifest/source loader를 수정하지 않는다.

## 18. Dataset version 관계

dataset_version은 고정 release ID 문자열이며 hash가 아니다. 새 세 payload에는 넣지 않는다. 동일 Inventory/tree가 다른 dataset에 포함돼도 도메인 지문은 같을 수 있다. Review/Context의 dataset_version은 별도 결합으로 유지한다.

같은 dataset_version으로 내용을 바꾸면 관련 내용 지문이나 파일 bytes hash가 변경되어 후속 검증에서 모순을 드러낼 수 있다. 단 하나의 tree 지문이 release 안의 모든 파일 변경을 감지하지는 않는다. Manifest/Registry/실제 파일 확인과 발행 이력 검증이 독립적으로 필요하다. utility는 dataset version을 생성·증가·비교하지 않는다.

## 19. Function API 후보 — 채택할 최소 계약

미래 위치는 같은 policy_data 패키지의 coverage_fingerprint.py를 권장한다. 이번에는 파일·public export를 만들지 않는다.

```text
fingerprint_condition_inventory(inventory: ConditionInventory) -> str
fingerprint_policy_tree(policy: Policy) -> str
fingerprint_rule_subtree(root: RuleNode) -> str
```

위 세 public 함수만 채택한다. 정확한 모델 객체를 받고 dict/list/하위 타입에서 변환하지 않는다. 두 번째는 정확한 Policy, 세 번째는 정확한 현재 네 node 중 하나다. canonical payload를 입력으로 받는 public API, policy+ID lookup overload, fingerprint(anything), artifact 경로 인자는 추가하지 않는다.

이 함수들은 PolicyDataError 또는 성공 digest만 반환한다. 상태·matched/stale 결과·None·빈 문자열을 정상 반환하지 않는다. registry 지문은 기존 public 함수를 사용한다.

## 20. Helper 구조

A 각 함수가 모든 변환을 반복하는 방식보다 **B 작은 private payload helpers + private JSON/SHA256 인코딩 helper**를 채택한다.

- _build_inventory_payload: 6절 명시 projection과 조건 ID 정렬.
- _build_rule_node_payload: 네 exact node explicit dispatch, RegionRef/FactBasis의 명시 projection, 재귀 children.
- private digest helper: 위 통제된 payload를 canonical JSON/UTF-8/SHA256으로 인코딩.
- 전체 tree/subtree public 함수는 각각 고정 schema wrapper를 구성해 같은 node helper를 호출.

이는 설계상의 이름이며 공개 계약은19절 세 함수뿐이다. 기존 Manifest private _digest를 import해 오류 타입/내부 모듈 경계에 결합하지 않고 인코딩 recipe를 동일하게 유지한다. 작은 같은 인코딩 절차를 위해 기존 코드를 리팩터링하지 않는다.

public build_payload API·범용 dataclass serializer·Any 기반 hash registry를 만들지 않는다. 감사에는 이 문서의 payload와 golden bytes가 충분하다. 후속 테스트는 public digest 및 필요한 private projection을 golden 벡터와 대조할 수 있다.

## 21. Error contract

새 오류 계층 없이 기존 **PolicyDataError**를 사용한다. field/오류 종류를 식별하고 원본 meaning·프로필·전체 payload를 오류에 복사하지 않는다. 아래는 미래 함수의 계약이며 현재 구현된 검증기가 아니다.

| 상황 | 책임 / 결과 |
|---|---|
| Inventory/Policy의 wrong exact type, subclass, raw dict | 해당 public utility의 PolicyDataError |
| root의 unknown node/subclass/None, 미래 Rule | node dispatch PolicyDataError, generic to_dict fallback 금지 |
| 잘못된 field/operator/Enum/date/RegionRef/FactBasis/value type | 기존 생성 단계 오류 또는 utility 경계의 PolicyDataError, 자동 변환 금지 |
| 중복 node ID·빈 group·NOT 자식 수 모순·잘못된 tuple | 기존 모델에서 거부. utility 입력으로 손상된 구조가 들어와도 정상 hash로 허용하지 않음 |
| malformed Inventory/중복 condition ID | 기존 모델에서 거부, dedupe하여 계산 금지 |
| root ID 미존재 | 채택 utility 범위 밖. 후속 validator의 lookup PolicyDataError |
| canonical JSON 구성/인코딩 실패, invalid Unicode/지원 불가 숫자 | PolicyDataError. replace·None·빈 digest fallback 없음 |
| version/fingerprint 다름·review ref 없음 | utility가 비교하지 않음. 후속 matching 책임 |

정상 생성된 frozen 모델이 전제이며 object.__new__/object.__setattr__로 고의 손상한 객체의 보안 인증은 아니다. 기존 도메인 검증을 새 범용 validator로 재작성하지 않는다. exact 입력/노드 종류와 payload 형태를 확인하고 기존 검증을 재사용할 수 있는 부분은 유지한다. 예상되는 구조·인코딩 실패는 PolicyDataError로 전달하되 MemoryError/KeyboardInterrupt 같은 시스템 실패까지 광범위하게 정상 데이터 오류로 숨기지 않는다.

중복 ID와 구조 오류를 확인하는 것은 hash 입력의 유효성 검사일 뿐 Coverage ownership/overlap/top ALL/FULL 검증이 아니다. 유효한 ANY/NOT tree도 지문 계산 대상이다.

## 22. No external I/O

세 utility는 외부 파일·네트워크·Git·DB·환경변수·현재시간·난수·캐시를 사용하지 않는다. source ref의 실제 존재를 조회하거나 정책을 재평가하지 않는다. artifact hash 산출은 별도 외부 준비 계층이며 이번에 그 계층을 구현하지 않는다.

이번 문서의 golden 값은 코드베이스에 함수를 추가하지 않고, 합성 literal payload에 표준 json/hashlib를 적용한 일회성 계산으로 산출했다. actual release를 대상으로 새 Coverage/implementation 지문을 계산하거나 파일 hash를 발급하지 않았다.

## 23. Fingerprint schema version

M2.12의 다음 고정 식별자를 **그대로** 사용한다.

| 대상 | fingerprint_schema |
|---|---|
| Inventory | coverage-inventory-1.0 |
| 전체 tree | coverage-policy-tree-1.0 |
| subtree | coverage-subtree-1.0 |

서로 payload 의미가 다르므로 별도 식별자다. 동일 root라도 tree/subtree wrapper가 다르면 지문이 다르다. 기존 Registry/Manifest payload에 새 label을 넣지 않으며 raw bytes artifact에도 JSON wrapper를 씌우지 않는다.

이름·포함 필드·의미·정렬·정규화 규칙을 바꾸면 의도적 schema 변경과 재검토가 필요하다. 현재 review record에는 별도 fingerprint_schema 필드가 없으므로 v1은 이 계약/실행 utility 버전/외부 artifact 기록으로 고정한다. 미래 v2를 만들 때 v1/v2 digest를 설명 없이 섞거나 자동 비교하지 않는다. 명시적 review schema 식별·migration 방식과 새 review 발급을 별도 승인해야 하며 이번 모델 필드에 소급 추가하지 않는다.

## 24. Golden vectors 전략 및 고정값

아래 **15개 합성 벡터**를 literal canonical JSON, UTF-8 byte 길이, SHA256으로 고정한다. JSON fence의 내용 한 줄만 hash 대상이며 Markdown fence와 화면상 마지막 줄바꿈은 제외한다. 삽입된 한글의 원래 code point를 보존한다.

입력은 각 JSON에 대응하는 현재 유효한 모델이다. Inventory의 conditions는 exact tuple, refs는 exact tuple, enum은 정확한 모델 Enum, birth 날짜는 exact date다. GV02는 원래 조건 순서 B,A, GV03은 A,B라는 차이가 있지만 canonical payload는 같아야 한다. tree 벡터의 policy_name은 SYNTHETIC, flags는 True/True라고 가정하며 payload에는 없다. 모든 source ref는 합성 형식 값이며 실제 출처 존재를 주장하지 않는다. GV10의 현재 지원 지역 키는 모델 유효성을 위한 합성 요구값이며 실제 정책 자료가 아니다.

향후 테스트는 문서의 기대 digest를 literal로 옮겨 고정한다. 테스트 실행 시 구현으로 기대값을 다시 만들어 덮어쓰지 않는다. payload projection과 digest/bytes를 함께 검증해야 “우연히 같은 입력을 다시 hash”하는 순환 테스트를 피할 수 있다. JSON key 입력 순서만 바꿔 같은 canonical bytes가 되는 사례도 포함한다.

### GV01 — 단일 조건 Inventory

UTF-8 bytes: **282**. SHA256: `abf20d120e93265b5b2e85851707d255693f833ee2dbdab8cd5741115fdf572a`.

```json
{"conditions":[{"condition_id":"COND_A","evidence_refs":["SYNTH-SRC#a","SYNTH-SRC#b"],"meaning":"소득 조건","requirement":"REQUIRED"}],"fingerprint_schema":"coverage-inventory-1.0","inventory_version":"i0001","policy_id":"SYNTH-POLICY","scope":{"edition_id":"2026","quarter":3}}
```

### GV02 — 입력 conditions=(COND_B,COND_A), ID순 정렬 후

UTF-8 bytes: **394**. SHA256: `3d0d97fc12200929459413e8bee59d9126a47749e34826a520529c80c6269946`.

```json
{"conditions":[{"condition_id":"COND_A","evidence_refs":["SYNTH-SRC#a","SYNTH-SRC#b"],"meaning":"소득 조건","requirement":"REQUIRED"},{"condition_id":"COND_B","evidence_refs":["SYNTH-SRC#c"],"meaning":"학생 조건","requirement":"CONDITIONAL"}],"fingerprint_schema":"coverage-inventory-1.0","inventory_version":"i0001","policy_id":"SYNTH-POLICY","scope":{"edition_id":"2026","quarter":3}}
```

### GV03 — 입력 conditions=(COND_A,COND_B), GV02와 동일

UTF-8 bytes: **394**. SHA256: `3d0d97fc12200929459413e8bee59d9126a47749e34826a520529c80c6269946`.

```json
{"conditions":[{"condition_id":"COND_A","evidence_refs":["SYNTH-SRC#a","SYNTH-SRC#b"],"meaning":"소득 조건","requirement":"REQUIRED"},{"condition_id":"COND_B","evidence_refs":["SYNTH-SRC#c"],"meaning":"학생 조건","requirement":"CONDITIONAL"}],"fingerprint_schema":"coverage-inventory-1.0","inventory_version":"i0001","policy_id":"SYNTH-POLICY","scope":{"edition_id":"2026","quarter":3}}
```

### GV04 — GV01의 meaning만 변경

UTF-8 bytes: **292**. SHA256: `36ccede8c75d342508a07e73109d71dd74cda11486e7672a8aa4a30daef69f42`.

```json
{"conditions":[{"condition_id":"COND_A","evidence_refs":["SYNTH-SRC#a","SYNTH-SRC#b"],"meaning":"변경된 소득 조건","requirement":"REQUIRED"}],"fingerprint_schema":"coverage-inventory-1.0","inventory_version":"i0001","policy_id":"SYNTH-POLICY","scope":{"edition_id":"2026","quarter":3}}
```

### GV05 — GV01의 evidence_refs에 c 추가

UTF-8 bytes: **296**. SHA256: `1e1e90ee0677437b84a0dc20ab23615a1ca98754f049dcbe7a2dafddb2f3e170`.

```json
{"conditions":[{"condition_id":"COND_A","evidence_refs":["SYNTH-SRC#a","SYNTH-SRC#b","SYNTH-SRC#c"],"meaning":"소득 조건","requirement":"REQUIRED"}],"fingerprint_schema":"coverage-inventory-1.0","inventory_version":"i0001","policy_id":"SYNTH-POLICY","scope":{"edition_id":"2026","quarter":3}}
```

### GV06 — GV01의 evidence_refs 순서 반전

UTF-8 bytes: **282**. SHA256: `da0e87aea7d09b34afc088b1682de6b2ebd87939bf54c6249846512969f40344`.

```json
{"conditions":[{"condition_id":"COND_A","evidence_refs":["SYNTH-SRC#b","SYNTH-SRC#a"],"meaning":"소득 조건","requirement":"REQUIRED"}],"fingerprint_schema":"coverage-inventory-1.0","inventory_version":"i0001","policy_id":"SYNTH-POLICY","scope":{"edition_id":"2026","quarter":3}}
```

### GV07 — 단일 atomic Policy tree, fact_basis=null

UTF-8 bytes: **240**. SHA256: `e887c0978fdc6e5d652e6982c23913d7d1a2b5570f4d983edd77c953240a63c0`.

```json
{"fingerprint_schema":"coverage-policy-tree-1.0","policy_id":"SYNTH-POLICY","root":{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"age","node_type":"atomic","operator":"gte","rule_id":"RULE_A","value":19},"rule_version":"r0001"}
```

### GV08 — ALL(A,B), B.value=false

UTF-8 bytes: **460**. SHA256: `d95f5a2328666f69f7eb72a3e270b6f3ea39c2303197e522123ffdfe81a23a37`.

```json
{"fingerprint_schema":"coverage-policy-tree-1.0","policy_id":"SYNTH-POLICY","root":{"children":[{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"age","node_type":"atomic","operator":"gte","rule_id":"RULE_A","value":19},{"evidence_refs":["SYNTH-SRC#b"],"fact_basis":null,"field":"student_status","node_type":"atomic","operator":"eq","rule_id":"RULE_B","value":false}],"node_type":"group","operator":"ALL","rule_id":"GROUP_AB"},"rule_version":"r0001"}
```

### GV09 — ALL(B,A)

UTF-8 bytes: **460**. SHA256: `56dc91d1f5ee476f2b7068194dc4dbeb33f1faf77c75ecedaa464f2b63193161`.

```json
{"fingerprint_schema":"coverage-policy-tree-1.0","policy_id":"SYNTH-POLICY","root":{"children":[{"evidence_refs":["SYNTH-SRC#b"],"fact_basis":null,"field":"student_status","node_type":"atomic","operator":"eq","rule_id":"RULE_B","value":false},{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"age","node_type":"atomic","operator":"gte","rule_id":"RULE_A","value":19}],"node_type":"group","operator":"ALL","rule_id":"GROUP_AB"},"rule_version":"r0001"}
```

### GV10 — 합성 resident rule, 현재 지원 지역 키 사용

UTF-8 bytes: **296**. SHA256: `cac2f242577922304c63f28bdac4c5c9712d54b2e6948d2cb74206aa5528658d`.

```json
{"fingerprint_schema":"coverage-policy-tree-1.0","policy_id":"SYNTH-POLICY","root":{"evidence_refs":["SYNTH-SRC#a"],"node_type":"resident_registration","reference_date_source":"APPLICATION_DATE","required_region":{"sido":"SEOUL","sigungu":"JONGNO"},"rule_id":"RESIDENT_A"},"rule_version":"r0001"}
```

### GV11 — 합성 birth rule의 날짜 구간

UTF-8 bytes: **245**. SHA256: `3a08146cbe12770cd371868c11d2d6c1e0b8622f48ff044e2826116833bfdf04`.

```json
{"fingerprint_schema":"coverage-policy-tree-1.0","policy_id":"SYNTH-POLICY","root":{"evidence_refs":["SYNTH-SRC#a"],"max_birth_date":"2001-01-01","min_birth_date":"2000-01-01","node_type":"birth_date","rule_id":"BIRTH_A"},"rule_version":"r0001"}
```

### GV12 — GV08의 root 자체를 subtree로 전달

UTF-8 bytes: **406**. SHA256: `6f7467494db11ce6391444c0e54127706a8ee62eb13e2937726638d92351da17`.

```json
{"fingerprint_schema":"coverage-subtree-1.0","root":{"children":[{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"age","node_type":"atomic","operator":"gte","rule_id":"RULE_A","value":19},{"evidence_refs":["SYNTH-SRC#b"],"fact_basis":null,"field":"student_status","node_type":"atomic","operator":"eq","rule_id":"RULE_B","value":false}],"node_type":"group","operator":"ALL","rule_id":"GROUP_AB"}}
```

### GV13 — GV07의 atomic root를 subtree로 전달

UTF-8 bytes: **186**. SHA256: `7c4088644283ad50806d182d288587bdfad0aa9e08192ad2755594f46f8add69`.

```json
{"fingerprint_schema":"coverage-subtree-1.0","root":{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"age","node_type":"atomic","operator":"gte","rule_id":"RULE_A","value":19}}
```

### GV14 — household_income와 다섯 FactBasis 필드

UTF-8 bytes: **353**. SHA256: `63221aca921c1e31080e1845e4c40c2c4a09671df3bc2276a357aada739ecdbe`.

```json
{"fingerprint_schema":"coverage-policy-tree-1.0","policy_id":"SYNTH-POLICY","root":{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":{"basis":"SYNTH-BASIS","period":"month","reference_year":2026,"subject":"household","unit":"KRW"},"field":"household_income","node_type":"atomic","operator":"lte","rule_id":"INCOME_A","value":2000000},"rule_version":"r0001"}
```

### GV15 — in 연산의 ordered value tuple

UTF-8 bytes: **262**. SHA256: `4c971d7417a4b86448c979b54ae8116645a126061d9c3695d69ad567cf9feea4`.

```json
{"fingerprint_schema":"coverage-policy-tree-1.0","policy_id":"SYNTH-POLICY","root":{"evidence_refs":["SYNTH-SRC#a"],"fact_basis":null,"field":"region","node_type":"atomic","operator":"in","rule_id":"REGION_A","value":["SEOUL","GYEONGGI"]},"rule_version":"r0001"}
```

## 25. Fingerprint change matrix

“변경”은 해당 payload에 반영되면 지문이 달라짐, “동일”은 그 필드/위치가 payload에 없거나 정규화됨을 뜻한다. 아래는 한 항목만 바꾼 합성 비교다. 정책 identity 변경 행은 Inventory와 Policy identity를 함께 변경하는 경우다. subtree 열은 변경 노드를 포함하는 선택 root 기준이며 외부 변경은 별도 행으로 구별한다.

| 변경 | Inventory | 전체 tree | 선택 subtree |
|---|---|---|---|
| Inventory condition tuple 순서만 변경 | 동일 | 해당 없음 | 해당 없음 |
| condition meaning 변경 | 변경 | 해당 없음 | 해당 없음 |
| condition requirement 변경 | 변경 | 해당 없음 | 해당 없음 |
| condition evidence 추가/재배열/중복 변경 | 변경 | 해당 없음 | 해당 없음 |
| completeness_review_ref 변경 | 동일 | 해당 없음 | 해당 없음 |
| inventory_version 변경 | 변경 | 해당 없음 | 해당 없음 |
| scope edition/quarter 변경, tree 자체 동일 | 변경 | 동일 | 동일 |
| policy_id 변경, node 자체 동일 | 변경 | 변경 | 동일 |
| group child 순서/연산자/자식 추가·삭제 | 해당 없음 | 변경 | 내부이면 변경 |
| rule_id 변경 | 해당 없음 | 변경 | 내부이면 변경 |
| atomic value/IN 후보 순서/FactBasis 변경 | 해당 없음 | 변경 | 내부이면 변경 |
| resident region 변경 | 해당 없음 | 변경 | 내부이면 변경 |
| resident reference source를 미지원 값으로 변경 | 해당 없음 | 오류 | 오류 |
| birth 양끝 날짜 변경, 유효 구간 유지 | 해당 없음 | 변경 | 내부이면 변경 |
| rule evidence 추가/재배열/중복 변경 | 해당 없음 | 변경 | 내부이면 변경 |
| rule_version만 변경 | 동일 | 변경 | 동일 |
| policy_name/유효한 synthetic/test_only 조합 변경 | 동일 | 동일 | 동일 |
| 같은 subtree의 외부 부모/형제만 변경 | 해당 없음 | 변경 | 동일 |
| source Registry URL/확인일만 변경, refs/조건/tree 고정 | 동일 | 동일 | 동일 |
| dataset_version만 변경 | 동일 | 동일 | 동일 |
| review ref/date/artifact ref만 변경 | 동일 | 동일 | 동일 |
| fingerprint_schema 변경 | 해당 대상 변경 | 해당 대상 변경 | 해당 대상 변경 |

Registry 내용 변경은 별도 source 지문을, evaluator artifact bytes 변경은 별도 implementation 지문을 바꾼다. model-invalid 변경은 지문 변화가 아닌 오류다. 표가 utility에서 version/검토 정합성을 판단하라는 뜻은 아니다.

## 26. Serialization과의 차이

| 현재 표현 | fingerprint projection과의 차이 |
|---|---|
| RequiredCondition.to_dict | 현재 네 key 값은 동일, 미래 확장은 자동 승계하지 않음 |
| ConditionInventory.to_dict | review ref 포함·입력 조건 순서 유지. 지문은 ref 제외·조건 ID 정렬·schema 추가 |
| ConditionBinding.to_dict | condition/root/review ref의 참조 표현. 세 지문 payload에 넣지 않음 |
| EligibilityCoverage.to_dict | Inventory와 Binding 구조 전체. 그 전체를 Inventory 지문이라고 hash하지 않음 |
| Policy/RuleGroup/PolicyRule의 _jsonable 표현 | 자동 dataclass 필드·flags 포함 가능, node_type 없음. 새 명시 N/wrapper 필요 |
| specialized node.to_dict | 실제 네 필드 값은 사용하되 node_type 추가. 미래 자동 확장 금지 |
| Review record/Context.to_dict | 검토 metadata·지문 선언 집합. 지문 대상 자체와 다름 |

public 저장/UI 직렬화를 변경하지 않는다. 기존 to_dict 호출 후 pop/sort하는 방식은 현재 가능한 구현 기법이어도 계약의 기준은 명시 field allowlist다. 자동으로 미래 필드가 지문에 들어가는 구현은 허용하지 않는다.

## 27. Future extension

새 RequiredCondition 필드·Rule 타입·판정 기준이 추가되면 먼저 의미 필드인지 검토한다. 포함/제외와 schema 영향·golden 벡터·기존 review 재검토를 명시적으로 승인해야 한다. 필드가 늘었다는 이유로 generic serializer가 자동 포함하거나 조용히 무시하여 새 의미를 기존 지문으로 인증하지 않는다.

특히 ResidenceHistory는 현재 지원 네 node에 없다. 임의 to_dict가 있어도 generic dispatch하지 않는다. Fact/Rule/evaluator와 공식 의미가 승인된 뒤 payload 확장과 fingerprint schema 전략을 별도로 검토한다. 단순 model metadata 추가라면 기존 projection을 유지할 수 있지만 그 제외 결정도 문서로 남긴다.

## 28. Security scope

목적은 변경 감지·재현·고정 review 대상 대조다. SHA256은 전자서명·검토자 인증·악성 위조 방지·정책 의미의 정답 증명이 아니다. 공격자/LLM이 내용과 일치하는 지문을 직접 써도 형식이나 내용 일치만으로 실제 검토가 증명되지는 않는다.

신뢰된 외부 검토 자료를 사용해야 한다는 기존 경계를 유지한다. 서명 서비스/권한 플랫폼/보안 workflow를 이번 선행조건으로 만들지 않는다. 실제 수급·행정 자격 확정 표현도 추가하지 않는다.

## 29. Privacy / user data exclusion

어떤 Coverage payload에도 UserProfile, BirthFact, ResidentRegistrationFact, 실제 사용자 birth_date·소득·주소·지출·정책 평가 결과·계정 ID를 넣지 않는다. BirthDateRule의 정책 날짜 경계와 BirthFact의 사용자 생일은 구별한다. FactBasis도 정책의 소득기준 설명이며 사용자의 실제 household_income이 아니다.

ReviewContext/Acceptance/Cashflow를 hash하거나 장기 사용자 저장 기능을 추가하지 않는다. Coverage는 user-independent다. 의미 문장/근거에 사용자 개인정보를 복사해 넣지 않는 외부 데이터 작성 원칙도 유지한다.

## 30. 수동 시나리오

아래 **60개 문서상 계약 사례**이며 새 실행 단위 테스트가 아니다. “오류”는 모델 생성 또는 후속 utility의 PolicyDataError 경계를 뜻한다. 소속/lookup/검토 대조의 경우 책임을 명시한다.

| ID | 사례 | 기대 계약 |
|---|---|---|
| FP01 | 동일 Inventory 반복 | 동일 payload/digest |
| FP02 | 조건 순서 B,A → A,B | 동일 Inventory digest, GV02=GV03 |
| FP03 | meaning 변경 | Inventory 변경 |
| FP04 | REQUIRED → CONDITIONAL | Inventory 변경 |
| FP05 | condition evidence 추가 | Inventory 변경, GV01≠GV05 |
| FP06 | condition evidence 순서 교환 | Inventory 변경, GV01≠GV06 |
| FP07 | completeness_review_ref만 변경 | Inventory 동일 |
| FP08 | inventory_version 변경 | Inventory 변경 |
| FP09 | Q3 → annual | Inventory 변경, quarter null 보존 |
| FP10 | policy_id 변경 | Inventory/전체 tree 변경, node만 같은 subtree는 동일 |
| FP11 | 동일 전체 tree 반복 | 동일 digest |
| FP12 | ALL(A,B) → ALL(B,A) | 전체 tree 변경, GV08≠GV09 |
| FP13 | ALL → ANY, 자식 동일 | tree/subtree 변경 |
| FP14 | rule_id 변경 | 해당 node 포함 tree/subtree 변경 |
| FP15 | atomic value 19 → 20 | tree/subtree 변경 |
| FP16 | resident region의 유효 pair 변경 | tree/subtree 변경 |
| FP17 | resident reference source를 미지원 값으로 변경 | 모델/utility 오류, 가상 지원값 hash 금지 |
| FP18 | birth lower 변경, valid interval 유지 | tree/subtree 변경 |
| FP19 | birth upper 변경, valid interval 유지 | tree/subtree 변경 |
| FP20 | rule evidence만 변경 | tree/subtree 변경, source 지문과 별도 |
| FP21 | rule_version만 변경 | 전체 tree 변경, subtree 동일 |
| FP22 | 동일 subtree를 다른 부모 아래 배치 | subtree 동일, 전체 tree 변경 가능 |
| FP23 | 선택 subtree의 child 순서 변경 | subtree 변경 |
| FP24 | 선택 subtree leaf value 변경 | subtree 변경 |
| FP25 | 선택 root ID 변경 | subtree 변경 |
| FP26 | Policy에서 binding root ID 미존재 | 후속 lookup 오류, root-only 함수가 탐색하지 않음 |
| FP27 | root가 지원 불가 임의 객체 | utility 오류 |
| FP28 | 미래 specialized Rule이 to_dict를 제공 | explicit node 지원 전 오류 |
| FP29 | fingerprint_schema 변경 | 대상 digest 변경, 명시 migration 필요 |
| FP30 | 같은 입력 100회 계산 | 동일 bytes/digest, 원본 불변 |
| FP31 | 다른 프로세스/OS에서 동일 payload | 같은 UTF-8 bytes/digest가 요구됨, 아직 교차 프로세스 실행 검증은 아님 |
| FP32 | dict key 삽입 순서만 변경 | sort_keys로 동일 bytes |
| FP33 | 원본 JSON 파일의 구조 공백/indent만 변경 | 같은 도메인 값이면 새 세 지문 동일, raw file hash는 변경 |
| FP34 | ensure_ascii=True로 한글을 escape | 이번 canonical recipe 위반. 그런 bytes는 golden과 불일치 |
| FP35 | meaning에 한글 포함 | UTF-8 원문 보존, GV01 |
| FP36 | birth date를 exact date로 전달 | ISO 변환, GV11 |
| FP37 | 정확한 Field/Operator/GroupOperator Enum | .value canonical 문자열 |
| FP38 | 모델 tuple을 raw list로 대체 | 모델/utility 오류, payload 내부 list와 구별 |
| FP39 | atomic fact_basis=None | null key 포함, GV07 |
| FP40 | UserProfile을 public 지문 함수에 전달 | wrong input 오류 |
| FP41 | BirthFact를 subtree root로 전달 | wrong node 오류 |
| FP42 | PolicyEvaluation을 전달 | wrong input 오류 |
| FP43 | ReviewContext를 Inventory 대신 전달 | wrong input 오류 |
| FP44 | Acceptance 객체를 전달 | wrong input 오류 |
| FP45 | 외부 artifact의 유효 implementation 지문 제공 | 기존 record의 형식 보존, bytes 진위 보증 없음 |
| FP46 | tree 지문을 artifact 지문으로 복사 | 서로 다른 대상. 역할 대체 금지, 형식만으로 오용 탐지는 못 함 |
| FP47 | digest가 일치하므로 사람 검토 완료 주장 | 성립하지 않음, 전자서명 아님 |
| FP48 | 사람이 허위 metadata와 일치 digest를 직접 작성 | 내용 대응만 가능, 검토 진실성 인증 불가 |
| FP49 | 미래 v2 utility에 v1 review를 schema 정보 없이 비교 | 자동 승계 금지, 외부 계약/이력 확인 및 명시 migration 필요 |
| FP50 | 새 schema를 발행하면서 기존 review 덮어쓰기 | 금지, 별도 승인·새 review ref 필요 |
| FP51 | evidence 같은 ref를 한 번 더 중복 | Inventory 또는 해당 tree/subtree 변경 |
| FP52 | atomic IN tuple의 후보 순서 교환 | tree/subtree 변경, 집합 정렬 없음 |
| FP53 | FactBasis.reference_year/unit/basis 변경 | tree/subtree 변경, GV14의 다섯 필드 모두 포함 |
| FP54 | 의미 문자열의 앞뒤 공백/NFC·NFD 변경 | 원래 code point 보존에 따라 Inventory 변경 |
| FP55 | 유효 bool false를 정수0으로 대체 | field exact 타입 오류, JSON 자동 숫자 변환 금지 |
| FP56 | float/NaN/Infinity/custom Enum 입력 | 지원 타입 오류, 문자열 fallback 없음 |
| FP57 | 고립 surrogate 또는 strict UTF-8 인코딩 불가 | PolicyDataError, replace/ignore 금지 |
| FP58 | Policy 표시명과 유효 flags만 변경 | tree/subtree 동일, 승인 상태를 인증하지 않음 |
| FP59 | tree+subtree 내용 고정, dataset/Registry URL/구현 artifact 변경 | 새 세 지문은 해당 내용 기준 동일, 별도 결합 필드·Registry/implementation hash로 검토 |
| FP60 | current ResidenceHistory가 미구현 | 지원목록/실제 자료 그대로, OFFICIAL_INQUIRY_REQUIRED 유지 |

## 31. 미해결 문제와 검증 기록

**새 세 순수 utility 구현을 막는 canonicalization 미결정은 없다.** 기존 세 schema와 필드·순서·타입·UTF-8 계약을 유지하고 explicit public API/노드 payload/오류·15개 golden 벡터를 구체화했다.

외부 engine artifact의 패키징/범위/실제 bytes 공급, 미래 schema migration의 review 식별 방식, review 진실성·stale gate·CoverageResult는 계속 별도 미구현 사항이다. 이들은 합성 Inventory/tree/subtree utility의 선행 구현 범위가 아니다. 구현이 되었다고 실제 review를 발행하지 않는다.

작업 전 전체 pytest는 **3807 passed in 10.05s**다. 신규 실행 테스트는 추가하지 않았다. Golden digest 계산은 literal synthetic payload의 인코딩 확인이며 아직 없는 utility의 실행 테스트 통과가 아니다. Python json/hashlib로15개 기대값을 계산하고, 저장한 문서의 canonical JSON 한 줄을 독립적인 .NET UTF-8/SHA256으로 다시 읽어 **15개 모두 byte 길이와 digest 일치**를 확인했다. 32개 절과 FP01~FP60의 순서·유일성·누락 여부 및 한국어 표기도 확인했다.

기존 파일 상태는 actual releases를 제외한 backend/tests/data/docs **110개 파일**의 SHA256 기준선으로 기록했다. 실제 release 두 개의 여섯 파일은 경로·길이·수정시각만 기록하며 이번 문서 작업을 위해 새 파일 hash나 Coverage 지문을 계산하지 않는다. 기존 테스트 내부의 종전 동작은 변경하지 않는다. 코드·기존 테스트/기대값·기존 문서·Cashflow·Acceptance·실제 자료·ResidenceHistory를 수정하지 않는다.

최종 대조에서 기존110개 파일은 모두 동일하고 수정·삭제는 없다. 추가 파일은 이 명세 한 개뿐이다. 실제 release 여섯 파일도 경로·길이·수정시각이 기준선과 동일하다. 이 상태 확인을 실제 정책 지문 발급이나 배포 검증으로 해석하지 않는다.

## 32. 최종 판단

**READY_TO_IMPLEMENT_COVERAGE_FINGERPRINT_UTILS**

다음 가장 작은 작업 한 개: **fingerprint_condition_inventory만 구현**한다. 이 문서의 Inventory v1 payload, 정확한 입력 타입·명시 필드·조건 ID 정렬·근거 순서 보존·검토 ref 제외·canonical UTF-8/SHA256과 GV01~GV06을 합성 테스트로 검증한다. tree/subtree utility·external artifact 계산·matching·Result·validator는 그다음 별도 승인 단계다.

IMPLEMENTED: 기존 Scope/Inventory/Binding/EligibilityCoverage/두 review 모델/ReviewContext는 현 상태 유지. 이번에는 **지문 명세만 작성**했다.

NOT IMPLEMENTED: 세 fingerprint utility, implementation artifact 준비/계산 계층, review matching/stale, CoverageResult/validator, FULL·SLICE 파생, Acceptance/Benefit Bridge. M1.18 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지. 실제 안산 release의 상태·지문·검토 기록은 생성하거나 변경하지 않는다.

## 33. M2.17 — IMPLEMENTED: Inventory 지문만 계산

policy_data/coverage_fingerprint.py의 public API는 **fingerprint_condition_inventory(inventory: ConditionInventory) -> str** 하나다. 옵션·추가 인자·public payload helper·generic fingerprint API가 없다. policy_data 패키지에서 이 함수만 추가 export한다.

정확한 ConditionInventory만 허용하고 None/dict/list/tuple/str/fake/subclass는 기존 PolicyDataError로 거부한다. 정상 생성된 불변 모델을 전제로 하위 Scope/Condition 생성 검증을 재실행하지 않는다. 기존 모델/serializer와 Manifest/Registry 지문 함수는 변경하지 않았다.

private _build_inventory_payload는 명시 다섯 key인 fingerprint_schema="coverage-inventory-1.0", policy_id, scope(edition_id/quarter), inventory_version, conditions만 구성한다. 각 조건은 condition_id/meaning/requirement.value/evidence_refs 네 key다. completeness_review_ref를 읽거나 포함하지 않는다. 모델의 to_dict 전체를 hash하지 않고 미래 필드 자동 수집도 하지 않는다.

conditions는 새 sorted sequence로 condition_id ASCII 오름차순 정렬한다. 원래 tuple/하위 객체·순서는 유지한다. refs는 원래 순서/중복의 새 list이며 meaning의 공백·한글·원래 code point를 보존한다. 자동 strip/NFC·NFD/dedupe가 없다. Annual scope의 quarter는 None→JSON null이다.

canonical JSON 설정은 sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False다. strict UTF-8로 encode하여 BOM/마지막 newline을 추가하지 않고 표준 hashlib.sha256(...).hexdigest()를 반환한다. 기존 Manifest의 private helper를 import하지 않고 동일 recipe를 작은 함수 안에서 적용했다. 다음 tree/subtree를 위한 추상화·helper·placeholder는 만들지 않았다.

JSON/UTF-8의 TypeError/ValueError/UnicodeError는 원본 payload를 노출하지 않는 PolicyDataError로 변환하며 None/빈 문자열/placeholder를 반환하지 않는다. MemoryError 같은 시스템 실패는 숨기지 않는다. invalid Unicode를 replace/ignore하지 않는다.

### Golden 및 의미 검증

GV01~GV06의 canonical JSON·UTF-8 byte 길이·expected digest는 문서24절에서 literal로 복사했다. 테스트 실행 중 expected digest를 새로 계산하지 않는다. 실제 함수가 SHA256에 전달한 bytes를 고정 JSON bytes와 직접 대조했다.

| 벡터 | 기대 UTF-8 길이 | 결과 |
|---|---:|---|
| GV01 | 282 | payload/JSON/bytes/SHA256 모두 일치 |
| GV02 | 394 | B,A 입력을 A,B로 정렬, 모두 일치 |
| GV03 | 394 | A,B 입력, GV02와 같은 digest |
| GV04 | 292 | meaning 변경 고정값 일치 |
| GV05 | 296 | evidence 추가 고정값 일치 |
| GV06 | 282 | evidence 재배열 고정값 일치 |

추가로 requirement/condition ID/근거 중복·version/scope/policy 변경, review ref 제외, ASCII 자연정렬과의 구별, 한글/NFC·NFD/공백 보존, 100회 반복·원본/출력 독립성, exact 입력 타입·추가 옵션 거부, JSON 오류·시스템 실패 전달, 하위 serializer/재검증/I/O 부재를 확인한다.

IMPLEMENTED: fingerprint_condition_inventory 및 GV01~GV06 executable golden tests. NOT IMPLEMENTED: fingerprint_policy_tree, fingerprint_rule_subtree, implementation_fingerprint calculator, review matching/stale, CoverageResult/validator, FULL/SLICE 파생, 실제 안산 Inventory 생성, Acceptance/Benefit Bridge.

작업 전 actual releases를 제외한 backend/tests/data/docs 111개 파일의 SHA256을 기준선으로 기록했고 기존 전체 **3807 passed in 9.43s**다. 신규 tests/test_inventory_fingerprint.py는 **47 passed in 0.33s**다. 기존 데이터/release SHA 선언은 수정하거나 새로 발급하지 않았다. M1.18 ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지다.

최종 판단: **READY_FOR_POLICY_TREE_FINGERPRINT**. 다음 가장 작은 작업 한 개는 M2.16의 explicit N(node) 및 전체 wrapper 계약으로 fingerprint_policy_tree만 구현하고 해당 tree golden 벡터로 검증하는 것이다. subtree public API·artifact 계산·review matching·Result/validator는 자동 구현하지 않는다.

### M2.17 최종 검증 기록

전체 pytest는 **3854 passed in 9.96s**다. 기존3807개와 신규47개 모두 통과했으며 기존 테스트/기대값을 수정하지 않았다. GV01~GV06의 payload/JSON/UTF-8 길이/고정 digest가 모두 일치한다. 신규/변경 파일의 한국어 표기와 utility의 직접 의존·금지 기능 부재를 확인했다.

작업 전 기준선111개(actual releases 제외) 중107개는 SHA256이 동일하다. 변경은 policy_data 공개 export 하나와 승인된 문서 세 개뿐이고, 신규 utility·테스트 두 파일을 추가했으며 삭제는 없다. 기존 Inventory/RequiredCondition/Scope/Review/Context·Policy/평가/loader·Manifest/Registry helper·Cashflow·기존 모든 테스트/기대값·데이터/SHA 선언·ResidenceHistory 자료를 유지했다. actual release 여섯 파일의 경로/길이/수정시각도 기존 기록과 같으며 실제 Inventory나 새 release 지문을 만들지 않았다.

## 34. M2.18 — IMPLEMENTED: 전체 Policy Tree 지문

기존 policy_data/coverage_fingerprint.py에 **fingerprint_policy_tree(policy: Policy) -> str** 하나를 추가하고 policy_data 공개 export에 반영했다. 옵션·subtree public API·artifact calculator·matching/Result/validator는 없다.

### 명시 payload와 공통 인코딩

전체 wrapper는 fingerprint_schema="coverage-policy-tree-1.0", policy_id, rule_version, root 네 key뿐이다. policy_name/synthetic/test_only/allow_real_data 및 review/user metadata는 제외한다. Policy의 비공백 ID/version 문자열은 원래 값을 보존하고 Envelope의 별도 canonical 문법으로 제한하지 않는다.

private _build_rule_node_payload는 type(node) is ...로 정확한 현재 네 타입만 처리한다.

| node_type | 명시 key / 표현 |
|---|---|
| atomic | rule_id/field.value/operator.value/value/fact_basis/evidence_refs. value는 scalar 타입 유지, tuple만 같은 순서의 새 list |
| resident_registration | rule_id/required_region(sido,sigungu)/reference_date_source.value/evidence_refs |
| birth_date | rule_id/min_birth_date.isoformat()/max_birth_date.isoformat()/evidence_refs |
| group | rule_id/operator.value/원래 순서의 재귀 children |

모든 node에는 node_type도 포함한다. fact_basis는 None이면 null이며, 있으면 basis/subject/period/reference_year/unit 다섯 필드를 명시한다. group을 flatten하거나 walk_nodes의 평면 목록으로 hash하지 않는다. children·IN 후보·근거의 순서와 중복을 보존한다. 각 모델의 유효성 검증은 기존 constructor 책임이고 utility는 재생성/재평가하지 않는다. generic to_dict/asdict/repr fallback은 없다. 미지원 객체·node subclass는 PolicyDataError로 거부하며 미래 specialized node를 자동 지원하지 않는다.

M2.17에 독립 private encoder는 없었으므로 기존 인코딩 본문만 _digest_payload(payload,label)로 추출했다. 두 public 함수가 같은 sort_keys=True / separators=(",",":") / ensure_ascii=False / allow_nan=False / strict UTF-8 / SHA256 hexdigest 경로를 사용한다. Inventory payload helper는 그대로다. Inventory 오류 문구와 GV01~GV06 bytes/digest도 유지한다. private tree wrapper/node helpers는 public export하지 않는다.

### Golden vector 식별·검증

문서24절의 payload schema를 직접 확인하여 **GV07/GV08/GV09/GV10/GV11/GV14/GV15**만 전체 Policy Tree golden으로 식별했다. GV01~GV06은 Inventory, GV12/GV13은 subtree이므로 새 Tree golden 범위에 넣지 않았다. 아래 일곱 vector의 expected JSON/길이/digest는 literal이며 테스트 중 재계산한 expected가 아니다.

| 벡터 | 내용 | UTF-8 bytes | 결과 |
|---|---|---:|---|
| GV07 | 단일 atomic / fact_basis null | 240 | payload/JSON/bytes/digest 일치 |
| GV08 | ALL(A,B) / bool false | 460 | 모두 일치 |
| GV09 | ALL(B,A) | 460 | 모두 일치, GV08과 다른 digest |
| GV10 | resident / 구조화 RegionRef / APPLICATION_DATE | 296 | 모두 일치 |
| GV11 | birth / ISO 날짜 경계 | 245 | 모두 일치 |
| GV14 | household_income / FactBasis5필드 | 353 | 모두 일치 |
| GV15 | in 후보 tuple | 262 | 모두 일치 |

추가 합성 테스트는 nested ALL/ANY/NOT 계층, child/group op/rule ID/atomic 의미/FactBasis5필드/유효 resident 지역/birth 양끝 변경, evidence 추가·재배열·중복, rule_version/policy_id 변경을 확인한다. 현재 ReferenceDateSource는 APPLICATION_DATE 하나뿐이므로 다른 지원값을 발명하거나 손상된 객체를 만들어 변경 사례로 삼지 않았다.

제외한 표시명과 유효한 flags만 바꾸면 지문은 같다. flags 비교는 실제 정책 자료 없는 합성 메모리 객체로 수행하며 운영 승인과 관계없다. 한글/원래 code point/NFC·NFD 구별, exact Policy/node 타입·subclass 거부, JSON/UTF-8 오류, 100회 반복·원본/출력 독립성, generic serializer/재검증/외부 상태 부재도 확인한다.

### 승인된 기존 테스트 예외

작업 전 기존 tests/test_inventory_fingerprint.py의 test_direct_dependencies_and_exports_do_not_include_future_features가 모듈 내 Policy/RuleNode import와 Tree public 함수 존재를 금지하여, 같은 모듈 확장 지시와 충돌했다. 사용자에게 예외를 요청했고 **해당 구조 제한 테스트1개만 갱신**을 명시적으로 승인받았다. 그 함수만 새 import/public 함수 계약으로 갱신했다. GV01~GV06, 나머지 기존 테스트·데이터 기대값은 유지했다. 이번 승인 없이 기존 기대값을 일괄 바꾼 것이 아니다.

IMPLEMENTED: fingerprint_condition_inventory(기존 결과 유지), fingerprint_policy_tree, 공통 private encoder, explicit node/wrapper payload, Inventory 및 Tree executable golden tests.

NOT IMPLEMENTED: fingerprint_rule_subtree, implementation artifact 계산, review matching/stale, CoverageResult, evaluate_eligibility_coverage, FULL/SLICE, actual 안산 review, Acceptance/Bridge. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED이며 placeholder node/Rule은 없다.

작업 전 actual releases를 제외한 backend/tests/data/docs 113개 파일의 SHA256과 actual 여섯 파일의 경로/길이/수정시각을 기록했다. 기존 전체 **3854 passed in 10.13s**. 신규 Tree72개 + 기존 Inventory47개는 **119 passed in 0.68s**다. 실제 release는 수정하거나 새 지문 필드를 추가하지 않았다.

최종 판단: **READY_FOR_RULE_SUBTREE_FINGERPRINT**. 다음 가장 작은 작업은 같은 private node payload와 encoder를 재사용해 fingerprint_rule_subtree(root) 하나만 구현하고 GV12/GV13으로 검증하는 것이다. lookup·소속 검증·matching·Coverage 결과는 별도 단계다.

### M2.18 최종 검증 기록

전체 pytest는 **3926 passed in 10.38s**다. 기존3854개와 신규72개 모두 통과했다. 기존 Inventory47개도 통과하며 GV01~GV06 literal payload/JSON/bytes/digest를 유지했다. 승인된 구조 제한 테스트1개의 편집을 역으로 되돌린 메모리상 내용의 SHA256이 작업 전 파일과 같아, 해당 수정 외 기존 테스트 파일의 변경이 없음을 확인했다. 나머지 기존 테스트는 파일 지문이 동일하다.

작업 전 기준선113개(actual releases 제외) 중107개가 동일하다. 변경은 utility·public export·승인된 기존 테스트 파일 각1개와 문서3개이며, 신규 Tree 테스트 파일1개만 추가했고 삭제는 없다. 모델/기존 serializer·평가/loader·Manifest/Registry 지문 함수·Cashflow·데이터/SHA 선언·ResidenceHistory 자료는 유지한다. actual release 여섯 파일도 경로/길이/수정시각이 기준선과 같다. 신규/변경 파일의 한국어 표기와 금지 기능 부재도 확인했다.

## 35. M2.19 — IMPLEMENTED: Rule subtree 지문

기존 policy_data/coverage_fingerprint.py에 **fingerprint_rule_subtree(root: RuleNode) -> str** 하나를 추가하고 policy_data 공개 export에 반영했다. 추가 옵션·Policy/ID lookup overload·새 package는 없다. 기존 Inventory/Tree 함수와 node payload/encoder 본문은 변경하지 않았다.

함수는 정확한 두 key인 fingerprint_schema="coverage-subtree-1.0", root=_build_rule_node_payload(root)를 구성하여 기존 _digest_payload에 전달한다. root 자체와 전체 descendant의 ID·타입·operator·값·FactBasis·지역·ISO 날짜·근거·계층·순서를 고정한다. Policy metadata/policy_id/rule_version/parent context는 포함하지 않으며 null placeholder key도 만들지 않는다.

원자/주민등록/출생일/group 네 exact 타입과 subclass 거부는 기존 explicit node helper 그대로다. atomic/resident/birth 변환을 복제하거나 RuleNode union을 위한 새 runtime validator를 만들지 않는다. 미지원 root는 기존 PolicyDataError다. generic to_dict/repr fallback과 UNKNOWN/placeholder digest는 없다.

공통 JSON 설정(sort_keys=True/separators=(",",":")/ensure_ascii=False/allow_nan=False), strict UTF-8, no BOM/final newline, SHA256 lowercase hex64도 기존 helper 그대로다. 한글·원래 code point와 근거 순서/중복을 유지한다. 새 encoder나 지문 schema는 없다.

### Golden 및 독립성 검증

| 벡터 | 내용 | UTF-8 bytes | 고정 SHA256 / 결과 |
|---|---|---:|---|
| GV12 | root group 자체와 두 children | 406 | 6f7467494db11ce6391444c0e54127706a8ee62eb13e2937726638d92351da17 — 모두 일치 |
| GV13 | 단일 atomic root | 186 | 7c4088644283ad50806d182d288587bdfad0aa9e08192ad2755594f46f8add69 — 모두 일치 |

두 벡터의 expected canonical JSON·길이·digest는 문서24절의 literal이다. 실제 wrapper payload/JSON/UTF-8 bytes/digest를 각각 대조했고 기대 digest를 구현 함수로 다시 계산하지 않는다. 같은 node는 전체 Tree 안과 subtree root에서 동일 payload를 사용하고 wrapper만 다르다는 것도 확인한다.

합성 valid Policy에서 같은 값의 독립 subtree를 서로 다른 ALL/ANY 부모·위치에 배치하면 subtree 지문은 같고 전체 Tree 지문은 다르다. 같은 subtree를 다른 rule_version 또는 policy_id에 연결한 경우도 같다. 이 테스트는 메모리에서 root를 직접 전달하며 검색/소속 검증 기능을 만들지 않는다.

추가 검증은 모든 node 종류·중첩 ALL/ANY/NOT 100회 반복·원본 객체/순서 유지, root ID/group operator/child 순서·atomic 의미/FactBasis5필드·유효 resident 지역/birth 양끝·근거 추가/재배열/중복 변경을 포함한다. 잘못된 입력·node subclass·추가 옵션·Unicode/JSON 오류와 외부 I/O/lookup/재검증/generic serializer 부재도 확인한다. 미지원 resident enum 값을 발명하거나 ResidenceHistory placeholder를 추가하지 않았다.

### 승인된 구조 테스트 예외

기존 Inventory의 test_direct_dependencies_and_exports_do_not_include_future_features와 Tree의 test_no_user_review_subtree_api_or_time_dependencies가 subtree API 부재를 요구했다. 사용자가 **구조 제한 테스트2개만 갱신**을 명시적으로 승인했다. Inventory 테스트의 public 함수 집합과 두 함수의 subtree 부재 확인만 새 지원에 맞게 갱신했다. 기존 golden literal/계산 검증·나머지 기대값은 유지했다.

IMPLEMENTED: inventory fingerprint, policy tree fingerprint, rule subtree fingerprint 및 현재15개 golden vectors 실행 테스트.

NOT IMPLEMENTED: implementation artifact calculator, Policy+rule_root_id/root lookup, ConditionBinding/ImplementationBindingReview matching, stale detection, CoverageResult, evaluate_eligibility_coverage, FULL/SLICE, 실제 안산 review, Acceptance/Benefit Bridge.

작업 전 actual releases를 제외한 backend/tests/data/docs 114개 파일의 SHA256과 actual 여섯 파일의 경로/길이/수정시각을 기록했다. 기존 전체 **3926 passed in 11.75s**다. 신규 subtree58개 + 기존 Inventory47개/Tree72개는 **177 passed in 0.78s**다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED를 유지한다.

최종 판단: **READY_FOR_COVERAGE_REVIEW_MATCHING_DESIGN**. 다음 가장 작은 작업은 Review records와 current Inventory/Policy tree/subtree/Context의 대상·참조·version·지문을 어떤 순서로 대조할지, 정상 stale과 구조 오류를 어떻게 구분할지 **문서로 설계**하는 것이다. 기존 M2.12 결정과 현재 세 utility를 연결하는 책임/API/시나리오를 명확히 하며 matching/lookup/Result/validator 코드는 구현하지 않는다.

### M2.19 최종 검증 기록

전체 pytest는 **3984 passed in 10.23s**다. 기존3926개와 신규58개 모두 통과했다. Inventory/Tree 기존119개와15개 golden vectors의 고정 JSON/bytes/digest도 모두 유지한다. 기존 테스트 두 파일에서 승인된 구조 변경만 역으로 되돌린 메모리상 내용의 SHA256이 작업 전과 일치해 다른 기존 기대값을 바꾸지 않았음을 확인했다.

작업 전 기준선114개(actual releases 제외) 중107개가 동일하다. 변경은 utility/public export 각1개, 승인된 기존 테스트 파일2개, 문서3개이며 신규 subtree 테스트 파일1개만 추가했고 삭제는 없다. 기존 모델/Review/Context·serializer·평가/loader·Manifest/Registry helper·Cashflow·데이터/SHA 선언·ResidenceHistory 자료를 유지했다. actual release 여섯 파일의 경로/길이/수정시각도 기준선과 같다. 신규/변경 파일의 한국어 표기와 금지 기능 부재를 확인했다.




