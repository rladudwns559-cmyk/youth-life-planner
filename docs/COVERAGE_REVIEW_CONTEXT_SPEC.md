# Coverage 검토 기록·확인본 결합 계약 — M2.12

> 현재 구현 상태는 34~37절을 따른다. 1~31절은 M2.12 설계 기록이다. 두 review 값 모델·Context와 Inventory/전체 Tree/subtree 지문을 구현했으며 lookup·매칭·상태 파생은 없다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 전용**. Record·Context·지문 함수·CoverageResult·validator 코드는 구현하지 않았다.

최종 판단: **READY_TO_IMPLEMENT_COVERAGE_REVIEW_RECORDS**. 합성 값으로 검토 기록 타입을 단계적으로 구현할 준비에 한정한다. 실제 검토 완료·안산 FULL·Acceptance 승인이 아니다.

## 1. 목적

후속 순수 validator가 “이 review_ref가 현재 정책·scope·조건 목록·Rule 구현의 검토 기록인가?”를 명시적인 기록과 지문으로 대조할 수 있게 한다. 단순 문자열 존재로 FULL을 허용하지 않는다.

검토 기준: ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md, POLICY_COVERAGE_SPEC.md, POLICY_BENEFIT_ACCEPTANCE_SPEC.md, CASHFLOW_BENEFIT_BRIDGE_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 현재 Scope/RequiredCondition/Inventory/Binding/EligibilityCoverage, Policy/RuleGroup/RuleNode/walk_nodes, Envelope의 edition/rule/dataset/source binding 및 DatasetManifest의 canonical SHA256·파일 hash 분리 계약을 확인했다. 저장소 확인본을 검토했으며 공식 정책을 새로 조회한 작업이 아니다.

CoverageReviewContext는 외부에서 확인해 전달한 review metadata 묶음이다. 정책조건 평가·tree 실행·FULL/SLICE 결정·인간 검토의 대체·암호학적 진실성 인증을 하지 않는다.

## 2. 현재 review_ref 한계

Inventory.completeness_review_ref는 str|None, Binding.implementation_review_ref는 필수 str다. 현재 생성자는 참조의 타입/비공백만 확인한다. 참조 문자열로는 검토 대상·버전·범위·내용·검토 종류를 알 수 없다.

필수 Binding ref를 임의로 None 허용으로 바꾸지 않는다. 새로운 Context가 명시적 ref를 해석할 기록을 공급한다. 생성자 성공과 review metadata의 실제 진실성은 여전히 별개다.

## 3. Inventory review 의미

InventoryCompletenessReview는 **고정 policy/scope의 해당 Inventory 확인본이 필요한 REQUIRED/CONDITIONAL 조건과 예외를 빠짐없이 정의한다는 검토 완료 기록**이다. 조건별 공식 의미 evidence와 목록 전체의 완결성 검토는 다르다.

미검토·검토 중·미완료 목록에는 이 완료 기록을 발급하지 않는다. Inventory의 ref=None은 정상 미검토다. 실제 원문에서 추가 조건이 없는지 타입/해시만으로 자동 판정하지 않는다.

## 4. Implementation review 의미

ImplementationBindingReview는 **해당 조건의 의미·전체 조건부 분기를 특정 rule_version의 subtree와 전체 tree 결합이 올바르게 구현하고, 지원 입력/evaluator 확인본으로 평가 가능하다는 검토 완료 기록**이다.

condition/root ID만 맞는 것으로 충분하지 않다. 전체 tree와 subtree 지문을 모두 고정해 내부 분기 변경과 외부 결합 변경을 확인한다. 일부 조건부 경로만 구현·검토했다면 완료 기록을 발급하지 않는다. 기록이 있어도 실제 tree 존재/ownership 검사는 후속 validator가 별도로 해야 한다.

## 5. Review record 구조 비교

| 방식 | 장점 | 문제 / 선택 |
|---|---|---|
| A 두 별도 타입 | 필수 필드가 명확하고 wrong type을 구분하기 쉬움 | **채택** |
| B 공통 record + review_type | collection 하나로 보관 가능 | 불필요한 optional 필드와 종류별 검증 증가. 미채택 |
| C base + 두 하위 타입 | 공통 필드 정의 재사용 | 작은 두 값 모델에 상속/기반 타입 비용. 미채택 |

최소 객체는 InventoryCompletenessReview, ImplementationBindingReview, CoverageReviewContext 세 개다. 자유 review_type 문자열·동적 registry·공통 workflow engine을 만들지 않는다. 종류는 정확한 객체 타입으로 구별한다.

## 6. Inventory review 필드

다음은 **후속 구현 계약**이다. 모두 필수이며 자동 생성하지 않는다.

| 필드 | 타입·의미 |
|---|---|
| review_ref | 정확한 비공백 str. 참조 identity |
| policy_id | 현재 Inventory와 같은 canonical 정책 ID |
| scope | 정확한 ApplicabilityScope. edition을 별도 중복 저장하지 않음 |
| inventory_version | 현재 Inventory와 같은 i0001부터의 버전 문법 |
| inventory_fingerprint | 20절 canonical inventory SHA256, 정확한 소문자16진64자리 |
| dataset_version | 검토한 고정 release/snapshot ID, 정확한 비공백 str |
| source_registry_fingerprint | 기존 fingerprint_source_registry의 canonical SHA256 |
| reviewed_at | 정확한 date. datetime/문자열은 거부 |
| review_artifact_ref | 검토자·근거·수동 사례·검토 note가 있는 불변 내부 기록의 비공백 str 참조 |

조건 ID/meaning/evidence 목록을 record에 다시 복사하지 않고 Inventory 지문으로 고정한다. version은 진단과 정상 갱신 구분에, 지문은 같은 version의 내용 재사용 검출에 각각 필요하다. 날짜·artifact 참조는 대상 지문과 분리한다.

## 7. Implementation review 필드

다음 필드도 모두 필수인 독립 불변 값 모델로 제안한다.

| 필드 | 타입·의미 |
|---|---|
| review_ref / policy_id / scope | 참조 identity와 대상 정책/범위 |
| condition_id | RequiredCondition과 동일한 ID 계약 |
| rule_root_id | ConditionBinding과 동일한 exact 비공백 str |
| inventory_version / inventory_fingerprint | 검토한 조건 의미·분기·evidence를 포함한 전체 목록 결합 |
| rule_version | 현재 Policy.rule_version과 같은 exact 비공백 str. Policy가 허용하는 값을 보존 |
| policy_tree_fingerprint | 전체 정책의 자격 tree 지문 |
| subtree_fingerprint | 해당 root 아래 전체 subtree 지문 |
| dataset_version / source_registry_fingerprint | 검토한 release와 근거 확인본 |
| implementation_fingerprint | 실제 지원 입력모델/evaluator 구현 배포물의 SHA256 |
| reviewed_at / review_artifact_ref | 검토 날짜와 내부 검토 기록 참조 |

전체 Inventory 지문을 결합하여 같은 condition ID의 meaning/requirement/evidence 변경도 놓치지 않는다. 따라서 목록의 다른 조건 변경도 재검토 대상이 되는 보수적 선택이다. subtree만 고정하면 정책 전체 결합 변경을 놓칠 수 있어 policy tree 지문도 둔다. 각 지문은 목적이 다르며 하나를 다른 것의 대체값으로 넣지 않는다.

실제 Policy/RuleNode/Condition 객체·원문·사용자 profile을 record에 저장하지 않는다. implemented/full/verified/accepted flags·자동 review version은 추가하지 않는다. record 타입은 완료 검토 metadata를 표현할 뿐 그 주장의 진실성을 보증하지 않는다.

## 8. Review identity

review_ref는 두 종류를 합친 Context 전체에서 유일해야 한다. 동일 객체·동일 내용·다른 종류·다른 내용 모두 중복이면 Data Error다. dedupe·최신 선택·source 우선순위는 없다.

기존 Inventory/Binding의 참조와 호환되게 정확한 비공백 str을 사용한다. 새 prefix/URL/파일 경로 문법을 강제하지 않는다. 자동 strip·대소문자 변환 없이 **정확한 원래 문자열**로 lookup한다. 유효한 앞뒤 공백도 값으로 보존하며 “REV-A”와 “ REV-A ”는 다른 참조다. 운영상 혼동 방지는 외부 기록 작성 규칙이며 도메인에서 보정하지 않는다.

동일 review_ref의 내용을 덮어쓰지 않는다. 다른 snapshot을 검토하거나 검토 metadata를 정정하면 새 ref를 발급하고 이전 참조는 외부 이력에 남긴다. 별도 acceptance와 같은 승인/철회 workflow를 이 Context에 추가하지 않는다.

## 9. Policy/scope binding

Context 하나는 **한 policy_id와 한 ApplicabilityScope**에 제한한다. 모든 내부 record는 Context의 policy/scope와 정확히 같아야 한다. 다른 정책/분기가 섞이면 Context 구성 오류다.

후속 validator는 Context의 policy_id/scope와 Coverage.inventory의 값을 다시 대조한다. 잘못된 정책·Q3/annual·다른 분기·다른 edition으로 연결하면 **Data Error**다. 동일 condition/root 문자열을 다른 정책에서 재사용했다고 승계하지 않는다. 현재 날짜·신청일·birth 구간으로 scope를 추정하지 않는다.

단 같은 policy/scope 안의 과거 version review는 함께 보관 가능하다. validator는 현재 ref가 정확히 가리킨 record만 선택하며 최신 review를 자동 탐색하지 않는다.

## 10. Inventory version/fingerprint

review의 inventory_version이 현재와 다르면 **정상 stale review → FULL 불가/SLICE 사유**다. 이때 지문도 달라지는 것은 정상일 수 있으므로 같은 version 변조로 오진하지 않는다. 새 version에 자동 승계하지 않는다.

**같은 inventory_version인데 fingerprint가 다르면 Data Error**다. 목록 추가·meaning/requirement/evidence를 바꾸면서 확인본 버전을 재사용한 모순이다. 단순히 “review가 오래됨”으로 숨기지 않는다. version 비교 뒤 같은 version일 때 내용 지문을 대조한다.

조건 tuple의 순서만 바뀌면20절의 condition ID 정렬 정규화에 따라 지문은 같다. completeness_review_ref와 검토 날짜/note는 inventory 의미 지문에서 제외한다. 이는 자기참조를 피하고 검토 metadata와 검토 대상 내용을 분리하기 위해서다.

## 11. Rule version/subtree fingerprint

policy의 rule_version과 review가 다르면 **stale rule review → FULL 불가/SLICE 사유**다. tree/subtree 내용도 달라질 수 있으므로 version 변경에 수반된 차이를 즉시 변조 오류로 만들지 않는다.

같은 rule_version인데 policy_tree_fingerprint 또는 subtree_fingerprint가 다르면 **Data Error**다. root ID를 유지하고 ANY→ALL·child 삭제·기준값·evidence를 변경해도 검출한다. root가 실제로 없거나 ownership이 모순이면 review staleness 판단 전 기존 tree 검증에서 오류다.

입력/evaluator 구현이 바뀌어 implementation_fingerprint가 다르면 **stale implementation review**다. 이것은 코드 배포물의 내용 identity 자체가 바뀐 것이며, 별도 mutable 코드 version을 여기서 만들지 않는다. 재검토 전 FULL은 불가다. 실제 배포물 hash 산출은 외부 준비 계층 책임이다.

## 12. reviewed_at/reviewer metadata

reviewed_at은 정확한 Python date다. 시스템 오늘을 기본값으로 넣거나 datetime을 절삭하지 않는다. record의 to_dict에서는 ISO YYYY-MM-DD 값으로 표현한다. 현재 날짜와의 비교·미래 날짜 자동 판정·만료 기간·자동 freshness는 이 모델의 책임이 아니다.

review_artifact_ref에는 외부에서 실제로 확인한 검토 기록 참조를 둔다. 해당 기록이 준비자/검토자·대상 지문·공식 근거·분기/경계 테스트·note를 보유해야 한다. 실명을 모든 runtime record에 반복하지 않고 팀 handle 등을 외부 기록에서 관리한다.

note만 수정해도 기존 review_ref의 record를 덮어쓰지 않고 새 ref로 명시적 정정한다. 대상 내용이 같다면 inventory/tree/subtree 지문은 그대로일 수 있다. 어떤 ref를 사용하도록 선택할지는 외부 orchestration 책임이며 가상 검토자/승인 이력을 만들지 않는다.

## 13. CoverageReviewContext 구조

최종 최소 후보는 다음 일곱 필드다. 모두 명시적으로 받으며 records tuple은 비어 있을 수 있다.

| 필드 | 계약 |
|---|---|
| policy_id | 한 대상의 canonical ID |
| scope | 정확한 ApplicabilityScope |
| dataset_version | 이번 검증에 사용할 명시적 고정 자료 ID |
| source_registry_fingerprint | 이번 자료의 SourceRegistry canonical 지문 |
| implementation_fingerprint | 이번 실행 입력/evaluator 배포물 SHA256 |
| inventory_reviews | 정확한 tuple[InventoryCompletenessReview,...] |
| implementation_reviews | 정확한 tuple[ImplementationBindingReview,...] |

frozen/slots·exact 타입·tuple·새 to_dict를 우선한다. 외부 dict/list를 그대로 저장하거나 자동 변환하지 않는다. 조회는 tuple을 순회하는 순수 helper 또는 validator의 임시 lookup으로 충분하다. mutable mapping/cache/global registry는 저장하지 않는다.

Context는 모든 record의 구조·종류·policy/scope 일치 및 전체 review_ref 유일성을 검사한다. record의 dataset/version이 현재 Context와 다를 수는 있다. 이것은 명시적으로 참조된 과거 review를 stale로 구분하기 위한 표현이다.

같은 policy/scope의 미참조 정상 records는 보관 가능하며 결과에 영향이 없다. 다만 잘못된 타입·중복 ref 등 구조 오류는 미참조라도 Context 전체를 거부한다. 다른 policy/scope records는 섞지 않는다. 이 선택은 M2.10의 전체 snapshot tuple 한 묶음을 **종류별 review records lookup**으로 구체화한 변경이다.

## 14. Duplicate review 처리

두 tuple 안과 두 tuple 사이 모두 review_ref 중복을 검사한다. 같은 ref의 inventory/implementation record가 동시에 존재해도 오류다. 같은 내용 두 개를 idempotent하게 제거하지 않는다.

Context의 입력 순서는 보존하고 기본 value equality/to_dict도 순서를 보존한다. 의미상 lookup 결과와 후속 validator의 audit 목록은 ref 기준 canonical 순서를 사용할 수 있다. 순서 변화가 review 수용 여부를 바꾸지 않는다. 모든 오류 수집 framework는 추가하지 않는다.

## 15. Missing review 처리

| 상황 | 계약 |
|---|---|
| Inventory.completeness_review_ref=None | 정상 미검토. FULL 불가/SLICE 사유 |
| review_context=None | 정상 검토 미확인. FULL 불가/SLICE 사유 |
| Context 제공, 명시된 completeness ref의 record 없음 | broken claimed reference → Data Error |
| Context 제공, Binding의 필수 implementation ref record 없음 | broken claimed reference → Data Error |
| Context의 두 records tuple이 비어 있음 | Context 값 자체는 허용. 명시 ref를 resolve하려면 위 오류가 적용됨 |

Context를 아예 제공하지 않는 것과 “기록 집합을 제공했는데 그 안에 명시 ref가 없음”을 구별한다. 일부 review만 준비됐다면 완료를 주장하는 Context를 불완전하게 전달하지 말고 해당 실행에서는 Context=None으로 미검토 상태를 유지할 수 있다. Inventory ref=None은 Binding review 확인과 독립적으로 남는다.

## 16. Wrong type 처리

ref는 종류를 포함한 정확한 record를 resolve해야 한다. completeness ref가 implementation tuple의 record를 가리키거나 그 반대이면 **Data Error**다. 같은 문자열이라는 이유로 다른 타입을 받아들이지 않는다.

두 tuple에는 각각 정확한 타입만 허용한다. dict·임의 subclass·자유 문자열 review_type·None 원소·list 변환은 없다. 잘못된 ref 문법/빈 값·hash·날짜는 값 모델의 PolicyDataError 계층이다. UNKNOWN으로 바꾸지 않는다.

## 17. Mismatch 처리

후속 순수 검증의 고정 우선순위를 제안한다.

1. Coverage/Policy의 기존 구조·root 존재·ownership 검증. 오류는 즉시 Data Error.
2. Context/record 타입·ref 유일성·존재·종류 검증.
3. policy/scope, implementation의 condition_id/rule_root_id 대상 일치. 틀리면 Data Error.
4. inventory/rule/dataset version 및 implementation 배포물 identity 변경을 확인.
5. **같은 version에서만** 해당 내용 지문 불일치를 immutable snapshot 모순으로 검사.
6. 정상 stale 사유가 있으면 검토를 현재 확인본과 일치한 것으로 인정하지 않음.

잘못된 대상에 연결된 ref를 “단순 오래된 review”로 처리하지 않는다. 같은 policy/scope에서 inventory/rule version이 다른 정상 record는 명시 ref로 조회됐더라도 stale로 분리한다. 자동 새 record 선택·ref 교정은 없다.

이 분류는 M2.12에서 확정한 **정밀화**다. M2.10의 포괄적인 ‘제공한 snapshot/version 불일치는 오류’ 문구와 EC52는 이후 구현에서 이 절의 ‘정상 version 갱신 vs 동일 version 내용 모순’으로 나눠 적용한다. 기존 코드를 바꾸거나 테스트 기대값을 변경한 것이 아니다.

## 18. Stale review 처리

| 변화 | 현재 review 재사용 | 후속 처리 |
|---|---|---|
| inventory_version 변경 | 불가 | stale inventory review, SLICE 사유 |
| 조건 추가/meaning/evidence 변경 + inventory version 갱신 | 불가 | stale inventory 및 그 목록에 묶인 implementation review |
| 같은 inventory version에서 위 내용 변경 | 불가 | Data Error |
| rule_version 변경 | 불가 | stale rule review, SLICE 사유 |
| subtree/전체 결합 변경 + rule version 갱신 | 불가 | stale rule review |
| 같은 rule version, tree/subtree 내용 변경 | 불가 | Data Error |
| dataset_version 변경 | 불가 | stale dataset review, SLICE 사유 |
| 같은 dataset_version, registry fingerprint 변경 | 불가 | immutable release/source snapshot 모순, Data Error |
| implementation 배포물 fingerprint 변경 | 불가 | stale implementation review, SLICE 사유 |
| 조건 순서만 변경 | 가능 | inventory 지문 같음, 다른 gate는 별도 |
| 검토 note/reviewer/date 정정 | 대상 지문은 같을 수 있음 | 새 review_ref의 정정 record를 명시적으로 선택 |

source registry version/내용 변경은 새 dataset snapshot과 재검토로 묶는다. URL/locator 검토일만 달라져도 기존 registry 지문은 변경될 수 있다. 자동 의미 동일 판단이나 예외 승계는 없다. 원래 source 확인본을 같은 dataset ID 아래 덮어쓰지 않는다.

**CoverageResult에 필요한 후속 보완:** Context가 존재해도 stale review이면 FULL은 불가다. 따라서 M2.10 18절의 ‘Context 존재 시 unreviewed refs가 비면 FULL’이라는 단순 식만 사용하면 안 된다. 후속 Result 계약에서 누락·미검토·stale 사유를 구별하고, **모든 요구 review가 CURRENT_MATCH인 경우에만** review gate를 통과시켜야 한다. 여기서는 새 Result/Enum/상태 계산을 구현하지 않는다.

## 19. ReviewContext=None

review_context=None은 정상적인 미검토 실행이다. Coverage의 로컬 정합성과 tree 구조 검증까지 정상이어도 FULL은 허용하지 않는다. completeness/implementation refs는 그대로 audit 대상으로 보존한다.

Context None이 tree 오류를 면제하지 않는다. 예를 들어 존재하지 않는 root나 unbound node는 여전히 오류다. 빈 bindings의 계획 값과 비어 있지 않은 Policy 검증의 구별도 유지한다. 검토 자료가 없다는 이유로 source/정책 상태를 UNKNOWN으로 바꾸지 않는다.

## 20. Fingerprint strategy

**원칙:** 기존 Manifest의 canonical domain fingerprint 철학과 JSON 인코딩을 사용한다. raw 파일 bytes SHA256·PolicyEnvelope 지문·registry 지문·이번 inventory/tree/subtree 지문은 서로 다른 대상이다. 이름이나 64자리 형식이 같다고 교환하지 않는다. 기존 fingerprint 함수를 수정하지 않는다.

모든 새 지문은 다음 절차를 사용한다.

```text
정해진 payload를 새 값으로 구성
→ JSON(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
→ UTF-8 bytes (BOM/추가 newline 없음)
→ SHA256 lowercase hexdigest
```

입력값을 변이하지 않는다. repr·메모리 주소·파일 경로·Python hash·현재시간·임의 Enum repr을 쓰지 않는다. 유효하지 않은 Unicode/JSON 내용은 오류다. 문자열 strip/Unicode 정규화는 하지 않는다. 지문은 정확한 str의 `[0-9a-f]{64}`만 허용하며 uppercase 변환·공백 보정은 없다.

**Inventory payload — coverage-inventory-1.0:**

| key | 값 |
|---|---|
| fingerprint_schema | coverage-inventory-1.0 고정 |
| policy_id | inventory.policy_id |
| scope | scope.to_dict()의 edition_id/quarter |
| inventory_version | 원래 version |
| conditions | condition_id 오름차순으로 나열한 RequiredCondition.to_dict() 전체 |

completeness_review_ref와 review record의 날짜/artifact/ref는 제외한다. condition meaning/requirement/evidence의 값·순서·중복은 보존한다. evidence 순서/중복을 바꾸면 지문도 달라진다. 조건 목록 순서만 바꾸면 지문은 같다. 원래 Inventory.to_dict/equality는 순서를 보존하므로 지문 동등성과 객체 equality를 구별한다.

**Node payload N(node):** 정확한 현재 node 종류를 명시하는 `node_type`과 기존 dataclass의 실제 필드를 합친 새 dict다. node_type은 PolicyRule→atomic, ResidentRegistrationRule→resident_registration, BirthDateRule→birth_date, RuleGroup→group이다. Enum은 value, date는 ISO, tuple은 list, None은 JSON null로 표현한다. Group.children은 원래 순서의 N(child) 목록이다. 모든 기준값·ID·evidence/중복·하위 값 객체 필드를 보존하고 미지원 node는 오류다. Rule 실행은 하지 않는다.

**전체 tree payload — coverage-policy-tree-1.0:** fingerprint_schema, policy_id, rule_version, root=N(policy.root)의 네 key다. 표시명 policy_name과 synthetic/test_only는 자격 tree 지문에서 제외한다. 데이터의 실제/합성 수용은 별도 기존 gate 책임이며 이 지문이 이를 인증하지 않는다.

**Subtree payload — coverage-subtree-1.0:** fingerprint_schema, root=N(명시한 root)의 두 key다. root lookup은 후속 tree validator가 제공하고, 지문 계산은 root 아래 모든 node를 보존한다. group child order·연산자·value·evidence·rule_id가 달라지면 지문이 달라진다. 논리적으로 같은 ANY 자식 순서라도 임의로 정렬하지 않는다.

**Registry:** 기존 fingerprint_source_registry가 고정한 정규화·JSON 계약을 그대로 사용한다. registry 전체 복사나 source 조회는 Coverage validator가 하지 않고 외부가 계산한 현재 지문을 Context로 공급한다. source ID/version뿐 아니라 registry metadata 변경도 지문에 반영된다.

**Implementation 배포물:** 외부가 검토한 입력모델/evaluator 소스 배포물 또는 빌드 artifact의 정확한 bytes SHA256이다. filename·engine_version 문자열을 대체값으로 쓰지 않는다. 어떤 artifact인지 review_artifact_ref에 기록한다. validator는 파일을 열지 않는다.

이는 정해진 정규화의 **확인본 지문**이지 일반적인 논리 동치 증명기가 아니다. 의미가 같아도 원문 공백·evidence 순서·child 순서가 다르면 검토 대상이 달라질 수 있다. 범용 hash framework나 PolicyEnvelope loader를 추가하지 않는다. fingerprint schema 문자열을 바꾸면 별도 계약 변경/재검토로 다룬다.

## 21. Pure validator 경계

외부 orchestration이 고정 Coverage·Policy·현재 dataset/registry/implementation 지문과 review records를 준비해 전달한다. 후속 validator는 메모리 안에서 exact ref lookup·종류·대상·version·지문을 비교한다.

파일 열기·URL 접속·Git 조회·DB·현재 날짜·임의 source 조회·artifact 다운로드는 없다. completeness/implementation ref가 실제 문서를 가리키는지의 외부 확인을 validator 안에 넣지 않는다. 지문 계산은 순수 utility, record 구조 검증은 값 모델, ref/target/staleness 대조는 후속 validator로 분리한다.

Record constructor는 64자리 지문을 구조적으로 검사할 뿐 Inventory/Policy를 받아 재계산하지 않는다. Context constructor도 Coverage/Policy와 대조하거나 FULL을 만들지 않는다. 형식상 정상인 허위 metadata가 만들어질 수 있다는 한계는22절을 따른다.

## 22. External truthfulness 한계

시스템이 검사할 수 있는 것은 **review metadata 구조·명시 ref의 무결성·대상과 확인본 일치**까지다. 실제 사람이 공식 목록과 구현 의미를 충분히 검토했는지 해시나 frozen dataclass가 보증하지 않는다.

review_artifact_ref가 가리키는 실제 기록·준비자/검토자·대상 artifact·source 확인본을 외부 과정이 확인해야 한다. 사용자/LLM이 제출한 Context를 신뢰하는 API는 허용하지 않는다. 동시에 이 한계를 이유로 전자서명·권한 서비스·감사 플랫폼을 선행 구축하지 않는다. 실제 경제 입력/사용자 평가를 검토 기록에 저장할 필요도 없다.

## 23. DatasetManifest 분리

DatasetManifest는 release 선택·버전/파일 bytes·배포물 재현성, ReviewContext는 coverage 검토 metadata의 목표 결합을 담당한다. Manifest 생성 성공이나 review 파일 경로가 있다는 사실로 review를 승인하지 않는다.

dataset_version과 registry/implementation 지문을 결합하는 철학만 재사용한다. Manifest JSON loader·hash 산출 I/O·운영 release 발행을 이번에 추가하지 않는다. Context는 Manifest를 소유하거나 파일 artifact를 해석하지 않는다.

## 24. Acceptance 분리

정확한 review match는 향후 coverage review gate를 충족할 수 있을 뿐, 그 자체로 Coverage FULL을 만들지 않는다. 누락/ownership/tree 구조도 정상이어야 한다. FULL 이후에도 verification·benefit metadata·simulation acceptance·개인/월 적용·현금 유형 gate가 별도로 필요하다.

ReviewContext에 ACCEPTED/REVOKED·혜택 금액·지급수단·납입액·사용자 PASS를 넣지 않는다. PolicyEvaluation·Cashflow·Benefit Bridge를 호출하지 않는다. 실제 수급 승인·배포 승인과도 별개다.

## 25. Current Ansan example

현재002는 2026 Q3 resident+birth만 구현한 DRAFT/CONDITION_SLICE다. 실제 전체 ConditionInventory도 아직 생성 전이며 거주기간 공식 의미·등록분류 관련 구현·전체 목록 완결성은 미확정이다.

ReviewContext를 만든다는 이유로 미구현 조건이 binding되거나 목록이 완결되지 않는다. 현재 FULL은 불가하고 현금 반영0을 유지한다. 실제 review record/ref/hash를 만들거나 release001/002를 수정하지 않는다.

ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 이 문서가 공식 산식·귀화일/기간 경계를 대신하지 않으며 Fact/Rule/Evaluator/actual binding을 구현하지 않는다.

## 26. Synthetic future-full example

**문서상 미래 가정:** policy_id=SYNTH-POLICY, scope=2026/Q3, inventory_version=i0001, 조건 SYNTH_CONDITION_A/B를 각각 SYNTH_RULE_A/B에 binding한다. 전체 tree는 두 root의 ALL이고 모든 분기·입력 계약이 검토됐다고 가정한다.

Inventory의 completeness ref는 SYNTH-INV-REVIEW, 두 Binding refs는 SYNTH-IMPL-A/B다. 첫 record는 현재 Inventory 지문, 두 implementation records는 같은 Inventory 지문·rule_version·전체 tree 지문과 각각의 subtree 지문을 고정한다. Context의 dataset/registry/implementation 값도 records와 같다.

실제로 계산하지 않은 64자리 hash나 사람의 검토 기록은 만들어 적지 않는다. 모든 기록/지문/대상이 맞고 tree·조건 대응까지 검증되면 향후 FULL을 지원할 수 있다. 어느 review만 맞는다고 FULL은 아니며 현재 실행 결과도 아니다.

## 27. 수동 시나리오

**56개 문서상 계약 사례이며 신규 실행 테스트가 아니다.** 아래 ‘검토 gate 통과’는 Context/refs/대상/버전/지문만의 판단이다. FULL은 이후 구조·조건 완결성까지 필요하다. stale은 정상 미완료, Error는 Data Error다.

| ID | 사례 | 기대 |
|---|---|---|
| RC01 | 정상 completeness record와 현재 inventory 일치 | 검토 gate 통과 |
| RC02 | completeness_review_ref=None | 정상 미검토, FULL 불가 |
| RC03 | ref 존재, 제공한 Context에 inventory record 없음 | Error |
| RC04 | completeness ref가 implementation record를 지목 | wrong type Error |
| RC05 | record가 다른 policy_id를 지목 | Error |
| RC06 | Q3 record를 annual inventory에 연결 | scope Error |
| RC07 | 같은 대상, inventory_version 다름 | stale inventory review |
| RC08 | 같은 inventory version, fingerprint 다름 | immutable snapshot Error |
| RC09 | 정상 implementation record의 모든 결합 일치 | 구현 검토 gate 통과 |
| RC10 | Binding ref 존재, 제공 Context에 record 없음 | Error |
| RC11 | implementation record의 condition_id 다름 | Error |
| RC12 | implementation record의 rule_root_id 다름 | Error |
| RC13 | rule_version r0001→r0002 | stale rule review, 자동 승계 없음 |
| RC14 | 같은 rule version, subtree fingerprint 다름 | Error |
| RC15 | 같은 review_ref/같은 내용 두 번 | duplicate Error |
| RC16 | 같은 review_ref/다른 내용 두 번 | duplicate Error |
| RC17 | Context=None | 정상 미검토 실행, FULL 불가 |
| RC18 | 두 record tuple이 빈 Context | 값으로 허용; 명시 ref 조회 시 missing Error |
| RC19 | 같은 policy/scope의 미참조 정상 record | 보관 가능, 참조 결과에 영향 없음 |
| RC20 | 다른 policy reviews 혼합 | Context 구성 Error |
| RC21 | inventory version 갱신 후 기존 review | stale |
| RC22 | condition 추가와 inventory version 갱신 | stale inventory/implementation review |
| RC23 | evidence 변경과 inventory version 갱신 | stale |
| RC24 | rule version 갱신 후 같은 내용 tree | version 결합이 달라 stale |
| RC25 | subtree 수정과 rule version 갱신 | stale; 같은 버전 수정이면 Error |
| RC26 | 형식상 유효한 허위 review metadata | 구조 생성 가능, 실제 검토 진실성 인증 아님 |
| RC27 | artifact 실제 존재/검토자 확인 | 외부 책임, validator의 I/O 없음 |
| RC28 | 현재 안산 Q3 부분 구현 | review만으로 FULL 불가 |
| RC29 | ResidenceHistory 의미 미확정 | 보류·missing 유지 |
| RC30 | review 존재하지만 필요한 Binding 없음 | 누락이 사라지지 않음 |
| RC31 | 합성 inventory 전체 목록 검토 완료 | inventory review gate만 통과 |
| RC32 | 합성 모든 Binding review 완료 | implementation review gate만 통과 |
| RC33 | 모든 지문·version·대상 일치 | 향후 구조 검증도 통과해야 FULL 지원 |
| RC34 | 동일 record/context 반복 | 같은 value/직렬화·lookup 결과 |
| RC35 | Context record 순서만 변경 | 원래 to_dict 순서는 다를 수 있으나 lookup 결과 동일 |
| RC36 | policy_id 잘못된 타입/형식 | 값 모델 Error |
| RC37 | scope=None/dict/하위 타입 | 값 모델 Error |
| RC38 | review_ref 빈/whitespace-only/비str | 값 모델 Error |
| RC39 | 지문 길이/문자 오류·uppercase·비str | 값 모델 Error |
| RC40 | reviewed_at=datetime/str/None | 값 모델 Error, 날짜 자동 변환 없음 |
| RC41 | 사용자 PolicyEvaluation 값 변경 | Context/coverage 검토와 무관 |
| RC42 | review match로 Acceptance 생성 요청 | 자동 생성 없음 |
| RC43 | ref가 파일/URL처럼 보임 | 값만 보존, filesystem/network 조회 없음 |
| RC44 | 실행 날짜가 달라짐 | 자동 현재일/만료 계산 없음 |
| RC45 | 유효 Context 생성만 수행 | FULL 자동 생성 없음 |
| RC46 | 같은 Inventory 조건 순서만 뒤집음 | inventory 지문 동일, 원래 객체 순서 불변 |
| RC47 | 같은 inventory version에서 meaning 변경 | 지문 변경, Error |
| RC48 | completeness ref/date/note만 새 기록으로 변경 | 대상 지문 동일 가능, 새 ref 명시 선택 |
| RC49 | group child 순서·value·evidence·rule ID 변경 | tree/subtree 지문 변경 |
| RC50 | dataset_version 변경 | stale dataset review |
| RC51 | 같은 dataset ID의 registry 지문 변경 | immutable dataset Error |
| RC52 | implementation 배포물 지문만 변경 | stale implementation review |
| RC53 | 같은 review_ref를 두 review 종류에 사용 | Context 전체 duplicate Error |
| RC54 | 앞뒤 공백이 다른 review ref | 다른 identity, 자동 strip lookup 없음 |
| RC55 | 같은 policy/scope의 과거 version record 참조 | 조회는 성공하나 stale, 최신 record 자동 선택 없음 |
| RC56 | Context는 있으나 stale review 포함 | Context 존재만으로 FULL 금지, 후속 Result의 stale 사유 필요 |

## 28. 추천 최소 모델

**InventoryCompletenessReview + ImplementationBindingReview + CoverageReviewContext**를 채택한다. 공통 base/상태 Enum/범용 artifact resolver/ReviewSet는 만들지 않는다. 필드 중복은 대상·결합의 독립 증거를 담는 범위로 한정하며 조건/Rule 객체 전체를 복제하지 않는다.

M2.10 2절의 snapshot 포함 Context는 이 문서의 **종류별 review records와 지문 결합**으로 구체화한다. 전체 Policy/Inventory 복제 대신 정해진 내용 지문을 사용한다. source_bindings 목록은 기존 registry fingerprint로 고정하고, implementation_contract_ref는 검토 배포물 fingerprint와 외부 artifact 참조로 구체화한다. 이전 문서와 코드는 변경하지 않는다.

아직 record 필드 검증·Context lookup·지문 함수·review issue enum·Result·validator는 없다. 향후 값 모델은 frozen/slots·exact 타입·새 JSON 친화 snapshot과 기존 PolicyDataError 계층을 사용한다. review_ref와 artifact_ref는 비공백 exact str을 보존하고 해석/접속하지 않는다.

## 29. 후속 구현 순서

| 순서 | 단일 작업 범위 | 포함하지 않는 것 |
|---|---|---|
| 1 | InventoryCompletenessReview 값 모델·필드 검증·합성 단위 테스트 | 지문 계산·implementation record·Context |
| 2 | ImplementationBindingReview 값 모델·필드 검증·합성 단위 테스트 | Context·tree lookup·검토 판정 |
| 3 | 이 문서의 Inventory/tree/subtree 순수 지문 utility·결정성 테스트 | 파일 artifact hash I/O·validator |
| 4 | CoverageReviewContext collection 모델·타입/중복/policy-scope 검증·순수 lookup | 현재 Coverage/Policy와 대조·상태 파생 |
| 5 | CoverageResult의 미검토/stale audit·파생 gate 계약 재정리 후 결과 타입 | tree validator |
| 6 | tree 구조 검증과 review 참조/결합 검증을 승인된 작은 단계로 구현 | 실제 정책 FULL·Acceptance·Bridge 자동 연결 |

이 순서는 추천이며 이후 milestone에서 각각 승인 범위를 확정한다. 속도를 이유로 record/Context/Result/validator를 한 번에 구현하지 않는다. 새 지문 utility도 기존 Manifest 함수의 의미를 바꾸지 않는다.

## 30. 미해결 문제

이번에 정한 identity·정규화 지문·stale/Error 분류에는 추가 선택을 남기지 않았다. **실제 연결에 남은 문제**는 실제 공식 목록/구현 검토와 artifact 공급, Registry/배포물 확인본의 신뢰된 선택, 오래된 검토의 사용중지 관리, 실제 scope/Envelope/Manifest 결합이다. 이들은 record 타입 구현의 완료와 다르다.

**Assumption A1:** Context는 한 policy/scope만 다루고, record별 조건·구현 의미 검토는 신뢰된 외부 과정에서 수행한다. **Assumption A2:** dataset/inventory/rule 확인본은 불변이며 의미/내용 변경에는 새 version을 사용한다. **Assumption A3:** implementation artifact 지문은 검토한 입력/evaluator 코드 확인본 전체를 가리키며 외부가 실제 bytes를 확인한다. ref/해시 모양만 맞춰 이 전제를 가장하지 않는다.

정상 version 변경을 stale로 구분하도록 했으므로 후속 Result 설계는 M2.10의 단순 Context 존재식을 보완해야 한다. 이 작업은 현재 코드·테스트를 변경하지 않는다. 현재 안산의 공식 거주기간 의미·전체 조건 목록은 여전히 미확정이며 FULL 불가다.

## 31. 최종 판단

**READY_TO_IMPLEMENT_COVERAGE_REVIEW_RECORDS**

두 검토 종류의 대상·버전·지문·참조 identity·시점·외부 진실성 경계를 정했고, Context 유무와 broken ref, 정상 stale과 같은 version 내용 모순을 구별했다. 이 문서만 추가하며 실제 검토 기록/지문/Context/FULL 결과는 만들지 않는다.

다음 가장 작은 작업 한 개: **InventoryCompletenessReview 불변 값 모델만 구현**한다. 6절의 명시적 필드·exact 타입·지문 문자열/날짜/ID 구조·불변성·직렬화를 합성 테스트로 검증한다. Inventory 지문 계산·실제 ref resolution·ImplementationBindingReview·Context·Result·validator는 포함하지 않는다.

### 검증 기록

기존 전체 pytest는 **3282 passed in 9.96s**다. 신규 실행 테스트는 추가하지 않았다. 문서의31개 필수 절과 RC01~RC56의 순서·유일성·누락 여부 및 한국어 표기를 확인했다. 이 결과는 아직 없는 review 모델·지문 함수·validator의 실행 검증을 의미하지 않는다.

작업 전 backend/tests/data/docs의 기존 **109개 파일 SHA256이 모두 동일**하고 수정·삭제는 없다. 추가는 이 문서 한 개다. Coverage/Inventory/Binding/Scope/RequiredCondition, Policy/RuleNode/Envelope/Manifest·기존 지문 함수, Cashflow, actual release001/002, 모든 테스트/기대값·기존 명세·ResidenceHistory 자료를 보존했다.

## 32. M2.13 — IMPLEMENTED: InventoryCompletenessReview metadata

policy_data/coverage_review.py에 InventoryCompletenessReview frozen/slots dataclass 하나를 추가하고 policy_data 공개 export로 제공한다. ImplementationBindingReview placeholder·Context·Result·validator·지문 계산 함수는 만들지 않았다.

정확한 필드 순서는 review_ref, policy_id, scope, inventory_version, inventory_fingerprint, dataset_version, source_registry_fingerprint, reviewed_at, review_artifact_ref이며 **아홉 인자 모두 필수**다. 프롬프트7개 후보보다 최우선 명세6절이 요구하는 dataset_version/source_registry_fingerprint 두 필드가 더 있다. 자료 확인본을 생략하지 않았으며 조건 ID 목록·Inventory 객체·Manifest 객체는 복제하지 않는다.

review_ref/dataset_version/review_artifact_ref는 exact 비공백 str이다. 자동 생성·strip·UUID·시각·path/URL 해석은 없다. 유효한 문자열의 앞뒤 공백은 기존 참조 모델처럼 그대로 보존한다. policy_id는 ConditionInventory의 canonical ID와 같은 식, inventory_version도 같은 i0001부터의 양의 버전 식을 사용한다. 기존 검증이 inline/private에 있어 다른 모델을 변경/추출하거나 전체 Manifest에 의존하지 않고 같은 작은 식을 적용했다.

scope는 exact ApplicabilityScope만 허용하고 원래 객체를 보존한다. dict/문자열/하위 타입에서 자동 생성하지 않는다. quarter/edition 필드를 중복하거나 현재 날짜/신청일로 범위를 추론하지 않는다.

inventory_fingerprint와 source_registry_fingerprint는 exact str의 `[0-9a-f]{64}`만 허용한다. uppercase·접두사·공백·str 하위 타입을 거부하고 보정하지 않는다. 실제 Inventory/Registry를 갖지 않으므로 합성0 지문처럼 형식만 맞는 값도 보존한다. hashlib·JSON canonicalizer·기존 fingerprint 함수는 호출하지 않는다. 현재 내용과의 일치는 후속 검증 책임이다.

reviewed_at은 exact date다. datetime/date 하위 타입/문자열/숫자/bool/None은 거부한다. 유효한 윤일·date.min/max도 그대로 보존하며 자동 today/now·만료·미래일·stale 판정을 하지 않는다. 검토일은 source verified_at 또는 dataset created_at과 다른 metadata다.

잘못된 값은 기존 PolicyDataError다. 새 오류 계층·UNKNOWN·verification/acceptance/coverage 상태는 없다. 필수 인자 누락/정의되지 않은 인자는 Python TypeError다. 오류에 원본 payload를 넣지 않는다. review_ref 유일성·다른 record와의 충돌은 Context의 후속 책임이며 동일 ref의 다른 metadata 객체도 단독 생성 가능하다.

to_dict는 정확한 아홉 key의 새 dict이며 scope는 새 중첩 dict, date는 ISO 문자열, 두 지문은 원래 str을 보존한다. equality/hash는 아홉 필드 전체의 값에 기반한다. 객체 생성과 직렬화는 실제 review artifact·사람의 검토·공식 목록 완결성·Coverage FULL을 보증하지 않는다.

직접 의존은 dataclasses/date/re/PolicyDataError/ApplicabilityScope뿐이다. 실제 Inventory/RequiredCondition/RuleNode/PolicyEvaluation/Cashflow·파일/Git/네트워크를 호출하지 않는다. reviewer 실명·rule version/tree 지문·condition 목록·status flags는 추가하지 않았다.

IMPLEMENTED: InventoryCompletenessReview structural metadata/strict ID·version·두 지문·date·문자열 검증/불변성/결정적 snapshot/합성 단위 테스트.

NOT IMPLEMENTED: Inventory canonicalizer/fingerprint 계산기, ImplementationBindingReview, CoverageReviewContext, CoverageResult, ref lookup/matching/stale 판정, tree validator, FULL/SLICE, Acceptance/Bridge/actual 안산 record. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지.

작업 전 coverage 값 모델 파일은 eligibility_coverage.py/required_condition.py/condition_inventory.py/condition_binding.py/coverage.py였고, backend/tests/data/docs 110개와 actual 두 release 파일을 SHA256 기준선으로 기록했다. 기존 전체 **3282 passed in 10.08s**. 신규 tests/test_inventory_completeness_review.py **182 passed in 0.45s**. 명시9필드·Scope/날짜 경계·정확한 타입·양의 version·두 지문의 형식/미보정·equality·단일 record의 identity 한계·불변성·출력 독립성·hash/I/O/Scope 재생성 부재·금지 필드를 검증했다. 실제 review 데이터는 없다.

최종 판단: **READY_FOR_IMPLEMENTATION_BINDING_REVIEW**. 지문 계산 계약은20절에 이미 정의되어 있고 단순 record 값 모델은 현재 지문과 비교하지 않으므로 계산기를 먼저 구현할 필요가 없다. 다음 가장 작은 작업은 ImplementationBindingReview 값 모델 하나의 필드·형식·불변성·직렬화를 합성 테스트로 구현하는 것이다. 지문 함수·Context·매칭·validator는 포함하지 않는다.

### M2.13 최종 검증 기록

전체 pytest는 **3464 passed in 11.14s**다. 기존3282개와 신규182개 모두 통과했으며 기존 테스트/기대값을 수정하지 않았다. 기존 다섯 coverage 값 모델·지문 함수·직렬화·테스트도 그대로다. 변경 파일의 한국어 표기와 새 모델의 직접 의존·금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 110개 파일의 SHA256을 대조했다. 기존105개는 동일하며 변경은 policy_data 공개 export 한 파일과 승인된 문서 네 파일이다. 신규 모델·테스트 두 파일만 추가했으며 삭제는 없다. actual release001/002 전체 파일, Scope/RequiredCondition/Inventory/Binding/EligibilityCoverage, Policy/RuleNode/Envelope/Manifest/evaluator/loader, Cashflow, 기존 테스트·Acceptance/Benefit 명세·ResidenceHistory 관련 자료를 보존했다.

## 33. M2.14 — IMPLEMENTED: ImplementationBindingReview metadata

policy_data/implementation_review.py에 독립 frozen/slots 값 모델 하나를 추가하고 policy_data 공개 export로 제공한다. 기존 coverage_review.py의 단일 클래스 모듈 경계를 고정한 회귀 테스트와 InventoryCompletenessReview를 그대로 보존하기 위해 같은 패키지의 별도 파일을 사용했다. 공통 base나 기존 모델의 helper 추출은 없다.

### 최종 필드와 검증

7절을 우선하여 다음 **15개 필드를 모두 필수**로 구현했다.

| 필드 | 구조 계약 |
|---|---|
| review_ref | exact 비공백 str, 원래 공백 보존 |
| policy_id | exact str, `[A-Z0-9]+(?:-[A-Z0-9]+)*` |
| scope | exact ApplicabilityScope, 원래 객체 보존 |
| condition_id | exact str, `[A-Z0-9_]+` |
| rule_root_id | exact 비공백 str, leaf/group 여부 조회 없음 |
| inventory_version | 현재 Inventory와 같은 i0001부터의 명시적 버전 |
| inventory_fingerprint | exact lowercase hex64 str |
| rule_version | 현재 Policy.rule_version과 같은 exact 비공백 str |
| policy_tree_fingerprint | exact lowercase hex64 str, 전체 정책 tree 대상 |
| subtree_fingerprint | exact lowercase hex64 str, 해당 root 아래 subtree 대상 |
| dataset_version | exact 비공백 str |
| source_registry_fingerprint | exact lowercase hex64 str |
| implementation_fingerprint | exact lowercase hex64 str, 입력모델/evaluator 배포물 대상 |
| reviewed_at | exact date, datetime/date 하위 타입 거부 |
| review_artifact_ref | exact 비공백 str, 참조 대상 조회 없음 |

프롬프트의 후보명 tree_fingerprint 대신 policy_tree_fingerprint, 구현 배포물은 implementation_fingerprint를 사용한다. 전체 Inventory version/지문도 생략하지 않는다. 지문 다섯 개는 독립 필드이며 다른 지문으로 자동 대체하지 않는다.

기존 ID/version 검증은 inline/private이고 require_text는 전체 models 모듈에 있다. 다른 모델을 리팩터링하거나 Policy/Manifest 의존을 추가하지 않고 동일한 작은 구조 검사를 사용했다. ConditionBinding의 ID 수용/거부, Policy의 require_text, Inventory review의 version과 동등한 수용 결과를 합성 테스트로 확인한다. Policy.rule_version은 r0001 같은 예시만 강제하지 않는 비공백 문자열 계약이다. Envelope의 별도 canonical r 버전 제한을 이 record에 새로 적용하지 않는다. 문자열 자동 strip·대소문자 변환·semver 생성은 없다.

다섯 지문은 `[0-9a-f]{64}` 형식만 확인한다. canonical payload 생성·SHA256 계산·현재 Inventory/Policy/tree와 비교는 수행하지 않는다. 조건/root 존재·Binding 대조·검토 lookup·stale·FULL/SLICE 판정도 없다. 실제 사람이 검토했는지, subtree가 올바른지, artifact가 존재하는지 생성 성공으로 보증하지 않는다.

to_dict는 정확히 위15개 key의 새 dict와 새 scope dict를 반환하고 날짜만 ISO 문자열로 표현한다. equality는15개 실제 필드 전체에 기반한다. 같은 review_ref라도 다른 subtree 지문을 가진 단독 객체를 만들 수 있으며 Context 전체의 중복/충돌 검사는 후속 책임이다. 모든 필드는 frozen/slots이고 nested Scope도 기존 불변 객체 그대로다.

직접 의존은 dataclass/date/re/PolicyDataError/ApplicabilityScope뿐이다. ConditionBinding/Inventory/Policy/RuleNode/Manifest 객체·reviewer 실명·coverage/verification/acceptance flags를 저장하지 않는다. 파일/Git/네트워크/현재 날짜·시각·자동 ID/버전/지문 생성이 없다. 오류는 기존 PolicyDataError이며 누락/추가 인자는 Python TypeError다. 원본 payload를 오류에 노출하지 않는다.

IMPLEMENTED: InventoryCompletenessReview(변경 없음), ImplementationBindingReview 구조·strict 형식·불변성·결정적 snapshot·합성 단위 테스트216개.

NOT IMPLEMENTED: fingerprint calculators, CoverageReviewContext, review lookup/matching, stale detection, CoverageResult, Coverage validator, FULL/SLICE 파생, Acceptance, Benefit Bridge. 실제 안산 record/Inventory/Binding은 만들지 않았다. actual release001/002는 DRAFT/CONDITION_SLICE 그대로이며 ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED를 유지한다.

작업 전 backend/tests/data/docs 112개 파일과 실제 두 release를 SHA256 기준선으로 기록했다. coverage 관련 모델 목록은 ApplicabilityScope, ConditionRequirement/RequiredCondition, ConditionInventory, ConditionBinding, EligibilityCoverage, InventoryCompletenessReview였다. 기존 전체 **3464 passed in 9.49s**, 신규 tests/test_implementation_binding_review.py **216 passed in 0.58s**다. 정상 leaf/group·Q3/annual·명시15필드·ID/version·지문5종·날짜/윤일·exact 타입/하위 타입·equality·assignment/deletion·snapshot 독립성·금지 객체/상태·hash/I/O/재검증 부재를 확인했다.

최종 판단: **READY_FOR_COVERAGE_REVIEW_CONTEXT_MODEL**. 다음 가장 작은 작업은 13~14절의 CoverageReviewContext collection 값 모델만 구현하는 것이다. 종류별 exact tuple/원소·policy/scope 일치·전역 review_ref 유일성·불변성·직렬화를 검사한다. 현재 Coverage/Policy와 매칭하거나 stale/상태를 파생하지 않는 이 collection 모델은 지문 계산기를 선행 요구하지 않는다. 29절의 추천 순서에서 collection 구조만 먼저 검토할 수 있다는 판단이며 계산/매칭까지 승인한 것은 아니다.

### M2.14 최종 검증 기록

전체 pytest는 **3680 passed in 9.88s**다. 기존3464개와 신규216개 모두 통과했으며 기존 테스트/기대값은 수정하지 않았다. InventoryCompletenessReview의182개 테스트도 그대로 통과했다. 변경 파일의 한국어 표기와 새 모델의 직접 의존·금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 112개 파일의 SHA256을 대조했다. 기존107개는 동일하고 변경은 policy_data 공개 export 한 파일과 승인된 문서 네 파일이다. 신규 모델·테스트 두 파일만 추가했으며 삭제는 없다. coverage_review.py 및 기존 모든 테스트, actual release001/002 전체 파일, 기존 coverage 값 모델/Policy/RuleNode/Envelope/Manifest·지문 함수·평가/loader·Cashflow·Acceptance/Benefit 명세·ResidenceHistory 관련 자료는 바이트 단위 동일하다. Git 저장소가 없어 파일 지문으로 변경 범위를 확인했다.

## 34. M2.15 — IMPLEMENTED: CoverageReviewContext collection 값

policy_data/coverage_review_context.py에 독립 frozen/slots CoverageReviewContext 하나를 추가하고 policy_data 공개 export로 제공한다. 두 review 모델의 위치·필드·검증·오류·직렬화와 기존 테스트는 변경하지 않았다. 공통 base·lookup cache·새 상태 타입은 없다.

### 최종 필드

13절을 우선하여 다음 **일곱 인자를 모두 필수**로 받는다. 프롬프트의 네 필드 예시보다 dataset/source/implementation 확인본 세 필드가 더 있다.

| 필드 | 구조 계약 |
|---|---|
| policy_id | exact str, 기존 canonical 정책 ID 형식 |
| scope | exact ApplicabilityScope, 원래 객체 보존 |
| dataset_version | exact 비공백 str, 자동 strip/버전 생성 없음 |
| source_registry_fingerprint | exact lowercase hex64 str, 형식만 검증 |
| implementation_fingerprint | exact lowercase hex64 str, 형식만 검증 |
| inventory_reviews | exact tuple, 모든 원소 exact InventoryCompletenessReview |
| implementation_reviews | exact tuple, 모든 원소 exact ImplementationBindingReview |

모든 record는 Context와 동일한 policy_id 및 scope **값**이어야 한다. 별개로 생성된 동일 Scope 값은 허용하며 원래 객체를 교체하지 않는다. Q3/annual·다른 분기·다른 edition은 다르다. 다른 소속의 record는 미참조 여부와 관계없이 오류이며 자동 필터링하지 않는다.

두 collection과 원소는 exact 타입이다. list/set/dict/generator/tuple 하위 타입·반대 종류의 review·record 하위 타입·None을 변환하거나 받아들이지 않는다. 기존 하위 record/Scope 생성 검증도 다시 실행하지 않는다.

두 tuple 안과 두 tuple 사이의 **모든 review_ref가 유일**해야 한다. 동일 객체·동일 값·다른 metadata·다른 review 종류 모두 참조가 중복이면 PolicyDataError다. 자동 dedupe·merge·최신 선택이 없다. ref의 공백/대소문자는 원래 값 그대로이므로 서로 다른 원문 문자열은 서로 다른 identity다.

### 역사적 확인본과 empty Context

두 tuple이 모두 비어 있어도 유효하다. 명시적 policy/scope와 dataset/source/implementation identity는 여전히 필수다. 이는 Context=None과 구별되는 빈 검토 기록 집합일 뿐, 필요한 review 존재나 FULL을 뜻하지 않는다. 현재 Coverage가 입력이 아니므로 missing 참조를 판단하지 않는다.

같은 policy/scope 아래 여러 Inventory review, 같은 condition/root의 여러 implementation review, 다른 inventory/rule/dataset version·날짜·지문의 공존을 허용한다. review_ref만 달라야 하며 같은 version의 지문이 달라도 이 collection 단계에서는 현재 대상과 대조하지 않는다. 내용 모순·stale·대상 일치 여부는 명시적 Coverage/Policy와 결합하는 후속 validator 책임이다. Context의 dataset/source/implementation 값과 record 값도 여기서 비교하지 않는다.

입력 tuple·record·Scope 객체와 순서를 그대로 보존한다. 기본 equality는 일곱 필드와 tuple 순서에 기반한다. 자동 정렬/비순서 equality가 없다. to_dict는 일곱 key의 새 dict, 새 scope dict, 원래 순서의 새 review lists와 각 record.to_dict의 새 중첩 값을 반환한다. 날짜 표현은 기존 record의 ISO 계약을 그대로 사용한다.

### 책임 경계

이번에는 lookup helper를 추가하지 않았다. 현재 규모에서 후속 validator의 tuple 순회로 충분하고, Context에 Coverage를 받지 않으므로 missing/wrong-target resolution을 선행 구현할 필요가 없다. 임시 중복 확인 set은 생성자 지역값이며 객체에 저장하지 않는다.

직접 의존은 dataclasses/re/PolicyDataError/Scope/두 review 타입뿐이다. EligibilityCoverage/Inventory/Binding/Policy/Rule 객체·사용자 평가·Cashflow·Coverage status·verification/acceptance는 보관하지 않는다. 파일/네트워크/Git·현재시각·자동 지문/버전 생성·지문 계산·version/fingerprint matching·stale·FULL/SLICE 계산도 없다.

생성 성공이 보장하는 것은 collection/원소 타입, policy/scope 소속, 전역 review_ref 유일성, 불변 구조뿐이다. 실제 사람 검토·artifact 존재·현재 자료 일치·모든 검토의 존재·최신성·FULL은 보증하지 않는다. 구조 오류는 기존 PolicyDataError이고 필수 인자 누락/추가 인자는 Python TypeError다. 원본 payload를 오류 문장에 노출하지 않는다.

IMPLEMENTED: InventoryCompletenessReview, ImplementationBindingReview(둘 다 변경 없음), CoverageReviewContext collection·identity/소속/중복 검증·불변성·결정적 중첩 직렬화·합성 테스트127개.

NOT IMPLEMENTED: fingerprint calculators, review lookup/resolution/matching, version matching, stale detection, missing review 판정, CoverageResult, Coverage validator, FULL/SLICE 파생, Acceptance, Benefit Bridge. actual release001/002는 DRAFT/CONDITION_SLICE 그대로이며 실제 안산 review/Inventory/Binding은 생성하지 않았다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지.

작업 전 backend/tests/data/docs **114개 파일**의 SHA256과 actual release001/002 여섯 파일 상태를 기록했다. Inventory review의9필드와 Implementation review의15필드 계약을 확인했고 기존 전체 **3680 passed in 10.17s**다. 신규 테스트는 empty/한 종류/혼합·Q3/annual·exact collection/원소/하위 타입·소속 오류·종류 내/간 참조 중복·공백 identity·역사적 확인본 공존·순서/equality·불변성·새 중첩 snapshot·하위 객체 재검증/hash/I/O 부재를 확인한다.

최종 판단: **READY_FOR_COVERAGE_FINGERPRINT_DESIGN**. 20절의 정규화 전략은 유지한다. 현재 Manifest의 Envelope/Registry 지문은 Inventory/tree/subtree 지문을 대체하지 못하며 세 계산기는 아직 없다. validator의 현재 내용 대조 전에 함수 입력 경계·현재 node 종류별 정확한 payload·오류·고정 검증 벡터를 구현 가능한 명세로 구체화하는 작은 문서 작업을 권장한다. 이번 승인 범위를 넘어 계산기나 Result/validator를 자동 구현하지 않는다.

### M2.15 최종 검증 기록

신규 tests/test_coverage_review_context.py는 **127 passed in 0.49s**, 전체 pytest는 **3807 passed in 10.09s**다. 기존3680개와 신규127개 모두 통과했고 기존 테스트/기대값은 변경하지 않았다. 기존 두 review 모델의182개·216개 테스트도 그대로 통과했다. 신규/변경 파일의 한국어 표기와 직접 의존·금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 114개 파일의 SHA256을 대조했다. 기존109개는 동일하고 변경은 policy_data 공개 export 한 파일과 승인된 문서 네 파일이다. 신규 Context 모델·테스트 두 파일만 추가했으며 삭제는 없다. 기존 두 review 모델·Scope/Inventory/Binding/EligibilityCoverage·Policy/Rule/평가/loader/Manifest·Cashflow·기존 모든 테스트·data 전체(실제 두 release 여섯 파일 포함)·ResidenceHistory 관련 자료는 바이트 단위 동일하다. Git 저장소가 없어 파일 지문으로 변경 범위를 확인했다.

## 35. M2.17 — IMPLEMENTED: 검토 대상 Inventory의 순수 지문

policy_data/coverage_fingerprint.py의 fingerprint_condition_inventory를 공개했다. 20절 및 COVERAGE_FINGERPRINT_SPEC.md의 inventory v1 payload를 그대로 사용한다. review metadata를 hash하거나 두 review 모델/Context를 변경하지 않았다.

함수는 exact ConditionInventory의 policy/scope/inventory version·명시 네 필드의 조건 목록을 선택한다. 조건 ID순 정렬만 수행하고 meaning/근거 순서·중복은 보존한다. completeness_review_ref는 제외한다. canonical JSON/strict UTF-8/SHA256으로 고정64자리 지문을 계산하며 실제 review와 대조하지 않는다.

IMPLEMENTED: 기존 두 review 모델/Context(변경 없음), Inventory 지문 계산 및 GV01~GV06 실행 테스트. NOT IMPLEMENTED: tree/subtree 지문·implementation artifact 계산·review matching/stale·CoverageResult/validator·FULL/SLICE·Acceptance/Bridge. 생성 지문은 공식 완결성·실제 검토·현재 review 일치의 증명이 아니다.

실제 안산 Inventory/review/hash 기록은 생성하지 않았으며 기존 데이터/release SHA 선언은 불변이다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED를 유지한다. 상세 구현/테스트·회귀 기록과 다음 전체 tree 지문 작업은 COVERAGE_FINGERPRINT_SPEC.md 33절이다.

## 36. M2.18 — IMPLEMENTED: 검토 대상 전체 Policy Tree 지문

policy_data/coverage_fingerprint.py에 fingerprint_policy_tree를 추가했다. 20절의 고정 schema와 policy_id/rule_version/전체 N(root)를 계산하며 explicit 네 node·계층·child/근거 순서를 보존한다. policy_name/flags와 review/user metadata는 제외한다. 지문 생성은 실제 review 존재나 구현 정답·현재 review 일치의 보증이 아니다.

Inventory 지문과 공통 private JSON/UTF-8/SHA256 encoder를 사용하고 기존 GV01~GV06 결과는 그대로 유지한다. 기존 구조 제한 테스트1개만 사용자 승인에 따라 갱신했으며 기존 두 review 모델·Context·Policy/Rule·실제 데이터는 변경하지 않았다.

IMPLEMENTED: Inventory 및 전체 Policy Tree 지문, 각 golden 실행 테스트. NOT IMPLEMENTED: subtree/artifact calculator, matching/stale, CoverageResult/validator, FULL/SLICE, Acceptance/Bridge. 실제 안산 review는 생성하지 않았고 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 상세 테스트·회귀/예외 기록과 다음 subtree 작업은 COVERAGE_FINGERPRINT_SPEC.md 34절이다.

## 37. M2.19 — IMPLEMENTED: 검토 대상 subtree 지문

policy_data/coverage_fingerprint.py의 fingerprint_rule_subtree(root)를 공개했다. 20절의 coverage-subtree-1.0 wrapper와 기존 N(root)/공통 encoder를 그대로 사용하며 root·전체 descendant·계층·순서·근거를 보존한다. policy_id/rule_version/parent metadata는 포함하지 않는다.

같은 subtree가 다른 정책·규칙 버전·부모/위치에 있어도 같은 subtree 지문을 가질 수 있고 전체 Tree 지문은 달라질 수 있음을 합성 valid Policy로 확인했다. 이것이 그 subtree를 다른 대상의 검토로 자동 승계할 수 있다는 뜻은 아니다. 현재 utility는 대상/소속/ref/version/지문을 대조하지 않는다.

IMPLEMENTED: Inventory/전체 Tree/subtree 지문 및 현재15개 golden vectors. NOT IMPLEMENTED: root lookup, review matching/stale, CoverageResult/validator, FULL/SLICE, implementation artifact calculator, Acceptance/Bridge. 기존 Review/Context 모델과 실제 데이터는 불변이다.

기존 subtree 부재를 검사하던 구조 테스트2개만 사용자 승인으로 갱신했다. 신규 subtree 테스트58개와 기존 Inventory/Tree119개가 통과했다. ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 상세 회귀 기록과 다음 matching 문서 설계 범위는 COVERAGE_FINGERPRINT_SPEC.md 35절이다.





