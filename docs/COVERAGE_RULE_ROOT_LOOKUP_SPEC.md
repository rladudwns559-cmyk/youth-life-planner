# Coverage Rule Root Lookup 계약 — M2.25

> 현재 구현 상태는 33절 M2.26을 따른다. 1~32절은 M2.25 설계 및 당시 검증 기록이다. private root resolver와 합성 테스트를 구현했으며 ownership/overlap/unmapped·CoverageResult·최종 Coverage validator는 없다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 설계 전용**이다. 이번 산출물은 이 파일 하나이며 코드·모델·공개 export·기존 문서·테스트·실제 release를 변경하지 않는다. 아래 API와 오류 prefix는 후속 구현 계약이며 아직 구현되지 않았다.

최종 판단: **READY_TO_IMPLEMENT_RULE_ROOT_LOOKUP**. root 존재 확인만의 구현 준비이며 ownership/overlap/unmapped 검증·CoverageResult·FULL/SLICE·실제 정책 수용 준비 완료를 뜻하지 않는다.

## 1. 목적

ConditionBinding.rule_root_id의 정확한 문자열을 현재 Policy의 executable eligibility tree 안에 있는 원래 RuleNode 하나에 연결한다. 문자열·날짜·지문으로 추측하거나 오래된 node로 대체하지 않고, 이후 단계가 같은 node 객체를 전달받을 수 있게 계약을 고정한다.

Source of Truth는 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md8~11·29·33절, POLICY_COVERAGE_SPEC.md8~12·24·34절, COVERAGE_REVIEW_MATCHING_SPEC.md24·26·42절, COVERAGE_FINGERPRINT_SPEC.md14~15절, DATA_MODEL.md25~26절, ARCHITECTURE.md38절이다. 현재 코드의 Policy/RuleNode/네 node 타입/ConditionBinding/EligibilityCoverage/walk_nodes/ID 검증/PolicyDataError/fingerprint_rule_subtree/_match_implementation_review를 확인했다. 이전에 확정한 구조 원칙과 matcher의 책임은 유지한다.

## 2. 역할과 비역할

| 담당 | 담당하지 않음 |
|---|---|
| Policy/ref 입력 타입과 ref의 비공백 형식 | Binding.condition_id의 Inventory 소속 |
| 현재 tree 전체에서 exact rule_id 검색 | semantic condition을 올바르게 구현했는지 |
| 방문 node의 현재 지원 타입 확인 | Binding ownership·parent/child overlap·공유 구현 |
| 전체 tree의 중복 rule_id 방어 | unmapped node·전체 ALL 결합 검증 |
| 원래 node 반환 또는 명시적 Data Error | 지문 계산·review resolution/matching·stale |
| root 존재 확인 | CoverageResult/FULL_POLICY/CONDITION_SLICE·Acceptance/Benefit Bridge |

전체 tree의 타입/ID 중복 방어는 조회 결과를 모호하게 만들지 않기 위한 최소 경계다. 이를 Coverage structure validation 전체와 혼동하지 않는다. lookup 성공은 해당 subtree의 유효한 소유나 의미 구현의 인증이 아니다.

## 3. 확정할 최소 private API

```python
_resolve_rule_root(
    policy: Policy,
    rule_root_id: str,
) -> RuleNode
```

두 인자는 필수이며 기본값·선택적 Context·Binding·Inventory·별도 status 인자는 없다. 성공은 RuleNode 직접 반환, 실패는 기존 PolicyDataError다. 별도 RuleRootResolutionResult/Enum/base class를 만들지 않는다. 인자 누락/추가 인자는 Python TypeError다.

후속 모듈은 **backend/policy_engine/policy_data/rule_root_resolution.py**를 권장한다. 기존 review resolver/matcher와 분리하고 파일 이동은 하지 않는다. policy_data의 public export에는 추가하지 않는다. 이번에는 파일이나 placeholder를 만들지 않았다.

## 4. Policy 입력 계약

type(policy) is Policy인 정확한 객체만 받는다. None/dict/list/tuple/RuleGroup/leaf RuleNode/속성이 비슷한 fake/Policy 하위 타입은 INVALID_STRUCTURE_INPUT PolicyDataError다. isinstance로 하위 타입을 자동 수용하거나 raw dict를 parse하지 않는다. 잘못된 Policy 타입이면 policy.root를 읽기 전에 실패한다.

정상 공개 생성자를 거친 Policy를 전제한다. Policy 생성자는 root exact 타입과 전체 ID 유일성을 확인한다. RuleGroup 생성자는 exact children tuple·현재 지원 child 타입·operator/NOT 자식 수·해당 subtree ID 유일성을 검사한다. leaf는 각자의 ID·필드 계약을 검사한다. lookup은 이를 재생성하거나 __post_init__을 재호출하지 않는다.

**Assumption A1:** frozen/slots 객체의 내부를 우회 변경하지 않은, 유한한 현재 tree다. object.__setattr__·비정상 역직렬화·순환 구조 주입을 지원 입력 경로로 삼지 않는다. 문서상 타입/중복 방어를 두더라도 모든 손상된 Python 객체나 임의의 순환/재귀 깊이를 복구하는 validator라고 주장하지 않는다.

## 5. rule_root_id 입력 계약

ConditionBinding.rule_root_id와 같은 **exact str, non-empty, non-whitespace** 계약이다. None/int/bool/bytes/list/dict/str 하위 타입/빈 문자열/공백만 있는 문자열은 INVALID_STRUCTURE_INPUT이다.

strip은 비공백 여부 검사에만 사용할 수 있다. 실제 저장/비교 문자열을 바꾸지 않는다. 대문자·밑줄만 허용하는 새 정규식을 만들지 않는다. 현재 Rule ID는 Condition ID와 달리 비공백 문자열이며 한국어·숫자처럼 보이는 문자열·내부 공백·유효한 앞뒤 공백을 그대로 허용한다. 입력 문자열 길이나 prefix 규칙을 새로 강제하지 않는다.

## 6. Exact ID matching

비교는 **node.rule_id == rule_root_id**다. RuleNode의 실제 식별자 필드는 id가 아닌 rule_id다. 전체 문자열이 정확히 같아야 한다.

| 저장 ID | 요청 ID | 정상 tree에서 결과 |
|---|---|---|
| RULE_A | RULE_A | 해당 원본 node |
| RULE_A | rule_a | RULE_ROOT_NOT_FOUND |
| RULE_A | RULE_A 뒤 공백 | RULE_ROOT_NOT_FOUND |
| 앞뒤 공백이 있는 RULE_A | 같은 앞뒤 공백의 RULE_A | 해당 원본 node |
| RULE_A | RULE | RULE_ROOT_NOT_FOUND |
| RULE_A | A | RULE_ROOT_NOT_FOUND |

case folding/strip/prefix·suffix·부분 문자열/fuzzy match/Unicode NFC·NFD 정규화·지문 유사성 검색은 없다. 같은 표시명/의미/지문이어도 다른 ID는 연결하지 않는다. 유효한 비공백 요청 문자열이지만 정확한 node가 없으면 입력 오류가 아닌 NOT_FOUND다.

## 7. Traversal scope

검색 시작점은 **policy.root**이고 현재 executable eligibility tree 전체를 대상으로 한다. root 자체, 모든 RuleGroup, 모든 descendant leaf, 여러 단계 nested group의 모든 node를 포함한다. source/Envelope metadata·과거 Policy·다른 release·다른 Policy 객체는 검색하지 않는다.

현재 대상 node를 일찍 찾더라도 tree 끝까지 방문한 뒤 반환한다. 요청 node의 subtree만 검사하거나 root 아래 descendant만 검색하는 방식은 채택하지 않는다. 조건이 UNKNOWN/FAIL로 평가될 수 있는 branch나 ANY/NOT 내부도 실행 결과와 관계없이 모두 검색한다. 정책을 평가해 탐색 branch를 줄이지 않는다.

## 8. Supported nodes

| 정확한 타입 | lookup에서의 역할 |
|---|---|
| PolicyRule | atomic leaf |
| ResidentRegistrationRule | 주민등록 요구 leaf |
| BirthDateRule | 생년월일 요구 leaf |
| RuleGroup | ALL/ANY/NOT group |

네 타입의 exact type만 허용하며 그 하위 타입·미래 specialized rule·raw dict를 자동 지원하지 않는다. RuleNode는 이 네 타입의 union alias이며 런타임 discriminator 문자열이 아니다. node_type/rule_type 문자열 기반 동적 registry를 추가하지 않는다.

ResidenceHistory Rule은 현재 없다. 미래 지원은 Policy/RuleNode/생성자·lookup·지문·평가의 명시적 확장과 함께 별도 승인한다. 지금 placeholder leaf/group을 만들지 않는다.

## 9. Root·group·leaf 처리

policy.root.rule_id가 요청과 같으면 **policy.root 자체**를 반환한다. Policy.root가 leaf인 정상 Policy도 허용한다. 각 세 leaf 타입과 root/nested RuleGroup 모두 Binding root 후보가 된다.

ALL/ANY/NOT라는 operator만으로 lookup 허용 여부를 바꾸지 않는다. group root를 찾았을 때 그 subtree를 leaf 하나로 축약하거나 복제하지 않는다. ANY(기간 경로 A, 기간 경로 B)는 group 전체를 가리킬 수 있다는 구조 예시일 뿐, 미확정 거주기간 의미/Rule 구현을 승인하지 않는다.

## 10. Traversal order

기존 walk_nodes와 같은 **root 포함 pre-order DFS, children tuple의 원래 왼쪽부터** 방문하는 순서를 고정한다. 정렬·condition 순서·ID 숫자 크기·표시명·오늘 날짜로 순서를 바꾸지 않는다.

정상 유일 ID tree에서는 child 순서가 달라도 같은 ID의 node를 찾는 의미가 같다. 각 Policy가 가진 실제 target 객체를 반환한다. tree 자식 순서 자체는 지문 계약상 의미 있는 값이므로 lookup이 tuple을 재배열해서는 안 된다. 복수 손상 지점의 최초 방문 위치와 duplicate 탐지의 재현성에는 이 고정 순서를 사용한다.

## 11. Original object identity

반환값은 tree에 있던 원래 immutable 객체이며 **resolved is expected_node**를 만족한다. reconstruct/replace/asdict/to_dict 후 재파싱/clone/새 wrapper는 없다. parent pointer나 소유 condition metadata를 node에 추가하지 않는다.

동일 Policy와 ID를100회 조회하면 매번 동일 객체를 반환한다. 서로 다른 Policy에서 같은 ID를 조회하면 각 tree 안의 객체를 반환하며 전역 ID registry로 합치지 않는다. 조회 전후 Policy/root/모든 node/children tuple identity와 값이 유지돼야 한다.

## 12. Missing root

정상 입력과 지원 타입·유일 ID 검사를 통과한 전체 tree에서 요청 ID를 찾지 못하면 **RULE_ROOT_NOT_FOUND PolicyDataError**다. None·가상 leaf·MISSING/STALE/UNKNOWN/FULL/SLICE 결과를 반환하지 않는다.

현재 tree에서 제거된 ID나 RULE_A→RULE_B로 이름이 바뀐 뒤 남은 과거 Binding도 같은 오류다. rule version 변경이 이를 stale로 낮추지 않는다. 현재 Coverage와 현재 tree의 구조 연결 문제이기 때문이다. 동일 지문의 다른 node·과거 release·비슷한 이름으로 자동 remap하지 않는다.

## 13. Duplicate ID — 대안 비교와 결정

현재 Policy와 RuleGroup의 _validate_unique_nodes는 walk_nodes의 모든 rule_id를 비교하며 중복이면 PolicyDataError("중복 rule_id가 있습니다")를 낸다. 동일 객체 재사용·같은 내용 두 객체·다른 내용 두 객체를 구별해 허용하지 않는다. 정상 공개 생성자로 중복 ID Policy를 만들 수 없고 이 기존 오류를 바꾸지 않는다.

| 방안 | 장점 | 한계 | 결정 |
|---|---|---|---|
| A. constructor invariant를 신뢰하고 첫 exact node에서 반환 | 조기 성공, 추가 상태 최소 | 뒤쪽 unsupported node/같은 ID를 확인하지 않고 첫 항목을 선택하는 의미가 됨 | 미채택 |
| B. 한 번의 전체 순회로 지원 타입·모든 ID 유일성과 target을 확인 | 뒤쪽 모순을 놓치지 않고 원본 객체 하나만 반환 | constructor와 일부 중복 검사, O(N) 지역 ID 집합 필요 | **채택** |

후속 구현에서는 호출 지역 seen ID 집합, 최초 duplicate 여부, target 후보만 보관한다. **요청 ID 외의 중복도 전체 tree 모순**으로 거부한다. 첫 후보를 기억해도 끝나기 전 반환하지 않는다. 중복을 dedupe하거나 내용이 같다는 이유로 정상 처리하지 않는다. 이는 Coverage ownership 검사가 아닌 tree identity 방어다.

순회 완료 후 duplicate가 있었다면 **DUPLICATE_RULE_NODE_ID PolicyDataError**다. target이 존재하거나 존재하지 않더라도 duplicate가 우선한다. 작은 tree에서 한 번의 추가 ID 검사는 허용 가능한 비용이며 범용 tree index/model은 필요하지 않다.

## 14. Unsupported node

walk_nodes는 시작 객체를 바로 yield하고 **type(node) is RuleGroup**인 경우에만 자식으로 내려간다. 따라서 임의 객체를 주면 자동으로 오류를 내는 validator가 아니며, 그것만 호출하고 ID를 읽는 방식은 충분하지 않다.

lookup은 방문한 각 node의 exact 지원 타입을 **rule_id를 읽기 전에** 확인한다. 미지원/하위 타입이면 **UNSUPPORTED_RULE_NODE PolicyDataError**다. skip하거나 하위 타입의 자식을 추측해 순회하지 않는다. 미래 node에서 requested ID가 맞아 보여도 반환하지 않는다. 정상 공개 Policy/RuleGroup 생성자가 앞서 거부하는 경우에는 그 생성자 오류가 먼저이며 lookup이 이를 새 오류로 변환하지 않는다.

이 방어가 모든 node의 operator/value/evidence/FactBasis/date/children 형식을 재검증하는 뜻은 아니다. 해당 로컬 불변조건은 공개 생성자 책임이다. 임의 객체 손상을 일부러 만들어 전체 semantic validator로 확장하지 않는다.

## 15. Error contract와 deterministic order

기존 PolicyDataError를 사용하며 새 예외 계층/code Enum/.code 속성은 추가하지 않는다. 아래 prefix는 이번 문서에서 확정하는 **후속 resolver의 메시지 계약**이다. 기존 코드/명세에서 이 네 prefix를 사용하는 별도 구현은 확인되지 않았다. review의 INVALID_MATCH_INPUT과 구조 조회 입력 오류를 구별한다.

| prefix | 고정 메시지 의미 |
|---|---|
| INVALID_STRUCTURE_INPUT | policy: 정확한 Policy가 필요합니다 / rule_root_id: 정확한 비공백 문자열이 필요합니다 |
| UNSUPPORTED_RULE_NODE | 현재 지원하는 정확한 RuleNode가 필요합니다 |
| DUPLICATE_RULE_NODE_ID | Policy tree의 rule_id는 유일해야 합니다 |
| RULE_ROOT_NOT_FOUND | 현재 Policy tree에 명시적 rule_root_id가 없습니다 |

동일 오류 class/prefix/message는 tree 입력 순서 외의 상태에 의존하지 않는다. 원본 Policy payload·개인정보·근거/meaning·임의 요청 ID 전체를 메시지에 복사하지 않는다. 필드 구분은 위의 policy/rule_root_id만으로 충분하다.

**우선순위:**

1. Policy exact 타입. 잘못되면 다른 속성에 접근하지 않는다.
2. 요청 rule_root_id 구조. 잘못되면 traversal하지 않는다.
3. pre-order 전체 traversal 중 지원 타입 확인. 첫 unsupported를 즉시 오류로 처리한다.
4. 모든 방문 node의 타입이 지원될 때, 기록해 둔 duplicate가 있으면 오류다.
5. duplicate도 없고 target도 없으면 NOT_FOUND다.
6. 그렇지 않으면 기억한 원본 target을 반환한다.

**중복 탐지는 순회 중 수행하되 오류 확정은 지원 타입 검사를 끝낸 뒤**로 한다. 앞에서 duplicate 후보를 보았어도 뒤에 unsupported가 있으면 UNSUPPORTED_RULE_NODE가 우선한다. target을 먼저 찾았어도 뒤쪽 unsupported/duplicate가 성공을 막는다. duplicate와 target 부재가 함께 있으면 DUPLICATE가 우선한다. 이 순서로 한 traversal과 전역 타입 우선순위를 동시에 만족한다. 모든 오류 수집 framework·부분 성공 반환은 없다.

## 16. walk_nodes 관계

**기존 walk_nodes 재사용을 채택**한다. root 포함·nested group 전체 방문·children 순서·pre-order가 요구와 맞는다. 새 재귀 engine/traversal helper나 기존 walk_nodes의 의미 변경은 필요하지 않다. lookup이 yield된 각 node의 exact 타입과 ID 유일성을 확인하는 작은 방어 계층을 맡는다.

기존 순회는 recursive다. 정상 유한 MVP tree와 합리적인 깊이의 nested group을 대상으로 한다. 임의 깊이 지원·재귀 제한 우회·cycle 복구를 새로 보장하지 않으며 RecursionError 등을 NOT_FOUND/UNKNOWN으로 감추지 않는다. 실제 깊이 문제가 확인되면 기존 traversal 계약과 함께 별도 검토한다. 지금은 blocker가 아니다.

의존 후보는 Policy/RuleNode/현재 네 node 타입/walk_nodes/PolicyDataError뿐이다. 각 타입은 기존 선언 위치를 사용하며 specialized rule 모델을 새로 복사하지 않는다. 순회 전체를 list/asdict/JSON으로 직렬화할 필요는 없다.

## 17. Fingerprint 분리

lookup은 **ID → node**, fingerprint_rule_subtree는 **명시 node → digest**다. lookup에서 지문 utility를 import/호출하지 않고 digest를 반환하지 않는다. 현재 지문을 캐시하거나 지문이 같은 다른 root를 탐색하지 않는다.

후속 orchestration은 root 존재/나머지 구조 정합성을 확인한 후 원본 root를 fingerprint_rule_subtree에 전달할 수 있다. 현재 Inventory/전체 Tree 지문은 호출당 한 번, subtree 지문은 선택 root별 한 번 준비한다는 기존 matching 계약을 유지한다. 이번에 orchestration을 구현하지 않는다. GV01~GV15와 지문 payload/serializer는 변경하지 않는다.

## 18. Review matching 분리

lookup은 CoverageReviewContext/Review record/ReviewMatchStatus/ImplementationReviewMatch/review resolver·matcher를 import하거나 실행하지 않는다. Review None/STALE/MATCHED 여부, reviewed_at, artifact 참조가 root 존재를 바꾸지 않는다.

_match_implementation_review는 이미 준비된 current_rule_version/Tree·subtree 지문을 받는다. lookup이 matcher를 호출하거나 matcher가 lookup을 호출하도록 결합하지 않는다. 상위 단계가 순서와 입력을 연결한다. 실제 root가 없으면 구조 오류이며, 과거 review를 stale로 반환해 그 오류를 가릴 수 없다.

## 19. Ownership 책임

root가 존재한다는 사실과 그 condition이 subtree를 유효하게 독점 소유한다는 사실은 별개다. 후속 structural validator가 Binding root 자체와 모든 descendant node의 소유 집합을 확인한다. shared predicate 예외를 허용하지 않는 기존 MVP 원칙을 유지한다.

lookup은 Binding/condition을 모르므로 소유자 목록·겹침 목록·부모 pointer·condition별 node 집합을 만들지 않는다. 허용된 전체 결합 ALL인지, 단일 의미 조건이 복수 의미를 숨기는지도 판단하지 않는다. 해당 검증이 끝나기 전에 root 조회만으로 FULL을 주장하지 않는다.

## 20. Unmapped rule·missing binding·unknown condition 분리

| 상황 | 책임 |
|---|---|
| Binding은 있으나 root ID가 현재 tree에 없음 | lookup의 RULE_ROOT_NOT_FOUND |
| Inventory 조건에 Binding 자체가 없음 | 상위 completeness/missing binding 처리. 호출할 ref가 없으며 NOT_FOUND가 아님 |
| Binding.condition_id가 Inventory에 없음 | 기존 EligibilityCoverage 생성자의 로컬 참조 오류 |
| 모든 Binding root는 존재하나 tree의 일부 node가 미매핑 | 후속 unmapped-rule 구조 오류 |
| bindings=()인 계획 모델 | 기존 모델은 보관 가능. 비어 있지 않은 실행 Policy와의 unbound 검사는 후속 책임 |

lookup은 inventory 조건을 tree에서 역추론하지 않는다. 현재 Policy의 모든 node가 소유되었는지, 허용된 최상위 ALL 결합 root인지도 계산하지 않는다. lookup 결과만으로 zero-binding SLICE나 공집합 FULL을 만들지 않는다.

## 21. Same-root multiple bindings

서로 다른 condition의 Binding이 같은 rule_root_id를 갖는 것은 현재 EligibilityCoverage 생성자가 허용한다. 같은 **tree node ID 중복**과 다른 문제다. Policy tree의 node는 하나이고 동일 ID를 두 번 조회하면 같은 node 객체를 정상 반환한다.

두 Binding의 충돌은 후속 ownership validator가 거부한다. lookup이 외부 호출 횟수를 기억하거나 “이미 조회한 root”라는 이유로 두 번째 조회를 거부해서는 안 된다. condition_id 중복 Binding은 별도로 기존 EligibilityCoverage 생성자가 거부한다.

## 22. Parent/child roots

COND_A→GROUP_X, COND_B→그 안의 CHILD_Y이면 두 ID 모두 존재할 때 각각의 원본 node를 반환한다. 조회 자체는 정상이다. 후속 ownership/overlap 단계는 부모 subtree와 자식 subtree가 겹친다는 이유로 기존 MVP 계약에 따라 거부한다.

sibling roots도 각각 조회 가능하며 이 사실만으로 나머지 구조가 유효한 것은 아니다. Policy 전체 root를 한 condition에 매핑하고 다른 자식 Binding도 둔 경우 역시 두 lookup은 성공하지만 ownership 검증 대상이다.

## 23. Performance와 cache

단일 조회는 전체 N개 node에 대해 **O(N) 시간**, 중복 방어용 지역 ID 집합은 **O(N) 공간**, 기존 recursive traversal stack은 깊이 H에 비례한다. target 후보/duplicate flag는 상수 크기다. 모든 Binding B개를 독립 조회하면 O(N×B)다.

현재 작은 tree에서는 허용할 수 있다. mutable/global cache·Context 필드·Policy 저장 index·DB/파일·환경변수·현재시각은 사용하지 않는다. 호출 지역 set/후보는 일시적 계산 상태이며 캐시가 아니다. node_id→node 전체 mapping이나 공개 성능 설정을 이번 최소 resolver에 추가하지 않는다.

## 24. RuleTreeIndex 필요성

향후 한 Coverage 실행의 여러 Binding을 검증할 때 한 번의 traversal로 지역 index를 준비하면 재사용할 수 있다. 그때 지원 타입·중복 방어·동일 Policy 소속·수명/불변성 계약을 유지해야 한다. 임의 caller의 mutable mapping을 신뢰하는 public index는 만들지 않는다.

**결론: 지금 RuleTreeIndex 모델/설계를 선행할 필요는 없다.** 단일 resolver의 의미를 합성 테스트로 고정한 뒤 전체 ownership/unmapped 단계에서 실제 공유 lookup 필요성을 확인한다. 그 단계에서 기존 의미와 오류 순서를 보존하는 지역 index 설계를 별도 승인할 수 있다. 현재 root 하나 반환 계약은 index 내부 표현을 노출하지 않아 이후 변경 여지가 있다.

## 25. ResolvedBinding 필요성

ResolvedConditionBinding은 Binding+원본 node를 함께 보관해 후속 재사용을 쉽게 할 수 있지만 객체 수·중복 identity·coverage data model의 executable node 결합이 늘어난다.

**결론: 지금 필수 모델은 아니다.** resolver는 원본 node 하나를 반환하고 호출자가 Binding과 root를 지역값으로 함께 유지하면 된다. ownership 단계가 요구하는 데이터가 확정되기 전에 value model/public serialization을 추가하지 않는다. 이번 문서와 다음 최소 구현 범위에 해당 모델/placeholder를 넣지 않는다.

## 26. Synthetic structure example

아래는 설명용 합성 tree이며 실제 정책·거주기간 구현이 아니다.

```text
ROOT_ALL [RuleGroup ALL]
├── RULE_RESIDENT [ResidentRegistrationRule]
└── GROUP_AGE [RuleGroup ANY]
    ├── RULE_A [PolicyRule]
    └── GROUP_NEGATE [RuleGroup NOT]
        └── RULE_B [BirthDateRule]
```

pre-order는 ROOT_ALL → RULE_RESIDENT → GROUP_AGE → RULE_A → GROUP_NEGATE → RULE_B다. 각 group/leaf의 로컬 필드는 현재 생성자 규칙에 맞게 구성한다. RULE_B 조회는 원래 BirthDateRule, GROUP_AGE는 원래 ANY group, ROOT_ALL은 policy.root다. UNKNOWN 요청은 전체 확인 후 RULE_ROOT_NOT_FOUND다.

조건 C1이 GROUP_AGE, C2가 RULE_B를 가리키면 두 조회는 성공하지만 overlap은 후속 오류다. C1만 RULE_A를 가리키면 RULE_RESIDENT 등이 미매핑인지 여부는 lookup이 다루지 않는다. 구조 예시의 ANY/NOT를 전체 조건 조합 ALL로 변경하지 않는다.

## 27. Current Ansan example

로컬 release ansan-youth-2026-10-20-002의 기존 JSON에서 식별자만 읽어 설명에 참고했다. lookup을 실제 실행하거나 새 Binding/결과/검토 기록을 저장하지 않았다.

| 기존 ID | 기존 node 종류 | 후속 조회의 개념 |
|---|---|---|
| ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE | RuleGroup ALL | 현재 Policy.root 자체 |
| ANSAN_YBI_2026_RESIDENT_AT_APPLICATION | ResidentRegistrationRule | 현재 resident leaf |
| ANSAN_YBI_2026_Q3_BIRTH_RANGE | BirthDateRule | 현재 Q3 birth leaf |

이는 정식 loader로 준비한 해당 Policy가 있을 때의 개념적 대응이다. 실제 lookup 실행 결과나 Coverage 승인 기록이 아니다. release의 기존 DRAFT/CONDITION_SLICE 선언을 바꾸지 않으며 actual Inventory/Binding/review/지문을 만들지 않는다. 누락된 거주기간 의미를 node 존재 여부로 보완하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 28. 후속 구현 테스트 계약

이번에는 테스트 파일을 추가하거나 기존 기대값을 수정하지 않는다. 다음 구현은 합성 자료로 다음을 검증한다.

| 구분 | 반드시 확인할 계약 |
|---|---|
| 정상 조회 | policy root 자체, leaf Policy, nested atomic/resident/birth, nested ALL/ANY/NOT group, 여러 단계 descendant |
| 정확 문자열 | 저장된 공백/대소문자 보존, case/공백/prefix/suffix 불일치 NOT_FOUND, 한글 ID·비공백 자유 문자열 |
| 잘못된 입력 | None/dict/list/fake/group/leaf/Policy subclass, None/int/bool/bytes/list/빈·공백 ref/str subclass |
| 오류 순서 | 잘못된 Policy 우선, ref 형식 오류는 traversal 전, missing ref는 정상 tree 전체 확인 후 |
| identity·결정성 | 원본 is,100회 동일 객체, 두 Policy의 같은 ID는 각자의 원본, child 순서 변경 후 각 target 의미 유지 |
| 무변경 | Policy/root/node/children tuple 원본 유지. 기존 모델 직렬화 가능 범위에서 snapshot도 동일 |
| 책임 경계 | Binding/Review/지문 utility·Policy 평가·I/O·시간·환경·cache를 사용하지 않음. private export 유지 |
| constructor 경계 | 중복 ID·미지원 node는 정상 공개 생성자로 거부되는 기존 계약을 유지 |

Policy/PolicyRule/RuleGroup에 없는 public to_dict를 새로 만들지 않는다. 무변경 검증은 tree 객체/tuple identity·dataclass 구조 비교와 이미 있는 표현 수단으로 가능하다. 새 generic serializer를 구현하지 않는다. 깊은 group은 정상 생성 가능한 합리적인 깊이에서 검증한다.

**duplicate/unsupported 실행 가능성 결정:** 정상 공개 생성자로 duplicate/unsupported Policy를 만들 수 없다. lookup 방어 경로를 때리기 위해 frozen 객체를 깨뜨리거나 생성자를 우회하지 않는다. constructor 거부는 정상 합성 입력으로 테스트할 수 있고, resolver 내 unreachable 방어 분기는 소스/의존 검토 및 아래 수동 시나리오로 남긴다. 기존 테스트가 이미 검증한 생성자 의미는 변경하지 않는다. 미래에 정상 구성 가능한 경로가 생기면 그때 별도 실행 테스트를 추가한다.

후속 테스트는 lookup 함수의 책임만 고정한다. 같은 모듈에 아직 없는 index/ownership 기능이 절대 추가될 수 없다는 식으로 미래 확장을 막는 구조 테스트를 만들지 않는다. 기존 matcher142/257개·resolver63개·결과166개·GV01~GV15는 그대로 회귀한다.

## 29. 수동 시나리오 — RL01~RL60

**60개 문서상 사례이며 신규 실행 테스트가 아니다.** 별도 표시가 없으면 공개 생성자로 구성한 정상 유일 ID Policy와 유효 ref를 전제한다. “후속 실행”은 다음 구현에서 합성 단위 테스트로 옮길 수 있다는 뜻이다. “수동/경계”는 lookup이 담당하지 않거나 공개 생성자 뒤에 도달할 수 없는 방어 상황이다.

| ID | 사례 | 기대와 검증 경로 |
|---|---|---|
| RL01 | 요청이 Policy.root의 ID | root 원본 is, 후속 실행 |
| RL02 | nested PolicyRule ID | atomic 원본, 후속 실행 |
| RL03 | nested ResidentRegistrationRule ID | resident 원본, 후속 실행 |
| RL04 | nested BirthDateRule ID | birth 원본, 후속 실행 |
| RL05 | nested RuleGroup ID | group 원본, 후속 실행 |
| RL06 | 여러 단계 안쪽 leaf ID | exact descendant 원본, 후속 실행 |
| RL07 | 저장 RULE_A, 요청 rule_a | NOT_FOUND, 후속 실행 |
| RL08 | 저장 RULE_A, 요청 RULE_A 뒤 공백 | NOT_FOUND, 후속 실행 |
| RL09 | 저장 RULE_A, 요청 RULE | NOT_FOUND, 후속 실행 |
| RL10 | 저장 RULE_A, 요청 A | NOT_FOUND, 후속 실행 |
| RL11 | tree에 없는 정상 ID | RULE_ROOT_NOT_FOUND, 후속 실행 |
| RL12 | 과거 ID가 현재 tree에서 제거됨 | NOT_FOUND, 과거 검색 없음, 후속 실행 |
| RL13 | RULE_A를 RULE_B로 rename 후 RULE_A 요청 | NOT_FOUND, 의미/지문 remap 없음, 후속 실행 |
| RL14 | Policy 자리에 dict/list/fake | INVALID_STRUCTURE_INPUT, 후속 실행 |
| RL15 | Policy=None | Policy 입력 오류 우선, 후속 실행 |
| RL16 | ID=None/int/bool/bytes/list/dict | INVALID_STRUCTURE_INPUT, 후속 실행 |
| RL17 | ID가 빈 문자열 | INVALID_STRUCTURE_INPUT, 후속 실행 |
| RL18 | ID가 공백/tab/newline뿐 | INVALID_STRUCTURE_INPUT, 후속 실행 |
| RL19 | 생성 시 보관한 leaf 참조와 결과 비교 | resolved is original, 후속 실행 |
| RL20 | 동일 Policy/ref100회 | 동일 객체와 오류 의미, 후속 실행 |
| RL21 | ALL root/nested group ID | operator와 관계없이 조회, 후속 실행 |
| RL22 | ANY root/nested group ID | 조회 성공, 전체 결합 적합성 판단 없음, 후속 실행 |
| RL23 | NOT group 및 그 유일 자식 각각 조회 | 각각 원본, 후속 실행 |
| RL24 | nested ALL/ANY/NOT 안쪽 요청 | 모든 group/leaf 검색, 후속 실행 |
| RL25 | Policy.root가 leaf | root leaf 원본, 후속 실행 |
| RL26 | 서로 다른 두 condition이 같은 root ID 요청 | 두 조회 모두 동일 node, ownership은 후속, 수동/경계 |
| RL27 | condition A는 parent group, B는 그 child | 두 조회 성공, overlap은 후속 오류, 수동/경계 |
| RL28 | 두 Binding이 sibling roots | 각각 조회 성공, 전체 구조 인증 아님, 수동/경계 |
| RL29 | root 조회는 성공하나 후속 소유 집합이 겹침 | lookup 성공을 뒤집어 ownership까지 수행하지 않음, 수동/경계 |
| RL30 | Policy에 unbound leaf가 따로 있음 | 요청 root 조회 성공, 미매핑은 후속, 수동/경계 |
| RL31 | 모든 선언 root가 존재해도 unbound group 남음 | lookup은 성공 가능, 최종 구조는 별도, 수동/경계 |
| RL32 | review_context가 없음 | lookup 입력이 아니며 영향 없음, 수동/경계 |
| RL33 | 연결 review가 STALE | root 존재에는 영향 없음, 수동/경계 |
| RL34 | 과거 review의 subtree 지문이 다름 | 지문을 읽지 않아 조회 결과 영향 없음, 수동/경계 |
| RL35 | 전체 tree 지문이 바뀌었으나 target ID 존재 | 조회 성공, matching은 별도, 수동/경계 |
| RL36 | rule_version만 바뀌고 ID 존재 | 현재 node 조회 성공, version 비교 없음, 후속 실행 |
| RL37 | policy_id만 바뀌고 ID 존재 | 각 Policy의 node 조회 성공, Coverage policy 대조는 후속, 후속 실행 |
| RL38 | 이론적 duplicate ID tree | 생성자에서 거부. 도달한다면 DUPLICATE, 수동/경계 |
| RL39 | 두 Binding의 target ID만 같고 tree는 유일 | duplicate tree 아님, 두 조회 성공, 수동/경계 |
| RL40 |100회 전후 root/children/node 비교 | 입력 값·identity 변경 없음, 후속 실행 |
| RL41 | children 순서를 바꾼 별개 정상 Policy | 각각 같은 ID 의미의 원본, 원래 tuple 보존, 후속 실행 |
| RL42 | 미래 specialized node/지원 타입 subclass | 공개 생성자가 거부. 도달한다면 UNSUPPORTED, 수동/경계 |
| RL43 | 미래 ResidenceHistory node | 현재 자동 지원 없음. placeholder 금지, 수동/경계 |
| RL44 | 현재 안산002 resident/birth/ALL ID |27절의 개념적 대응만 기록, 실제 lookup/저장 없음, 수동/경계 |
| RL45 | 거주기간 의미 미확정 | 현재 네 타입 lookup 계약에 영향 없음, 수동/경계 |
| RL46 | 서로 다른 두 node의 ID가 RULE_A와 공백 있는 RULE_A | 정확히 구별, 각각 원본, 후속 실행 |
| RL47 | str subclass ID 또는 Policy subclass 입력 | exact-type 오류, 후속 실행 |
| RL48 | Policy 대신 정상 RuleGroup/leaf 입력 | Policy 입력 오류, 후속 실행 |
| RL49 | 잘못된 Policy와 잘못된 ID 동시 전달 | Policy 입력 오류 먼저, 후속 실행 |
| RL50 | 정상 Policy와 잘못된 ID | traversal 전에 ID 입력 오류, 후속 실행 |
| RL51 | target을 먼저 찾고 뒤쪽에서 unsupported 발견 | 성공 금지, UNSUPPORTED, 공개 구성 불가인 수동 방어 사례 |
| RL52 | target을 먼저 찾고 뒤쪽에서 같은 ID 재발견 | 성공 금지, DUPLICATE, 공개 구성 불가인 수동 방어 사례 |
| RL53 | target 외 다른 ID가 중복이고 target은 존재 | 전체 ID 모순으로 DUPLICATE, 수동 방어 사례 |
| RL54 | target은 없고 다른 ID 중복 | DUPLICATE가 NOT_FOUND보다 우선, 수동 방어 사례 |
| RL55 | 앞쪽 duplicate 후보와 뒤쪽 unsupported | 타입 유효성 우선이므로 UNSUPPORTED, 수동 방어 사례 |
| RL56 | tree에는 서로 다른 ID의 같은 의미 node 둘 | exact ID만 선택, 후속 실행 |
| RL57 | 한국어 ID·서로 다른 Unicode 정규형 ID | 원문 문자열대로 구분, 후속 실행 |
| RL58 | 서로 다른 Policy가 같은 rule_id를 사용 | 각 Policy의 원본 반환, 전역 캐시 없음, 후속 실행 |
| RL59 | Inventory에 조건은 있으나 Binding 없음 | lookup 대상 없음, NOT_FOUND를 합성하지 않음, 수동/경계 |
| RL60 | Binding.condition_id가 Inventory에 없음 | EligibilityCoverage 로컬 오류, lookup 책임 아님, 수동/경계 |

## 30. 미해결 문제·가정·검증 기록

**root lookup 계약 자체의 미결정은 없다.** 정확한 입력/문자열, 네 지원 타입, 기존 순회 재사용, 전체 순회 방어 B, 타입→중복→존재 순서, 원본 객체 반환, private 경계를 확정했다. 기존 tree/ID 계약과 충돌하지 않는다.

가정 A1의 정상 불변 유한 tree를 유지한다. ownership/overlap/unmapped·전체 결합의 구체적인 실행 API/오류 순서, 여러 Binding의 지역 index 최적화, 구조 검증 뒤 지문 공급을 연결할 orchestration은 후속 과제다. 기존 의미 원칙을 바꾸는 미해결 사항은 아니며 root 하나의 resolver를 막지 않는다. 공식 거주기간 의미/ResidenceHistory는 별도로 **OFFICIAL_INQUIRY_REQUIRED**다.

작업 전 actual releases를 제외한 backend/tests/data/docs 파일의 SHA256과 actual release6개 파일의 경로/길이/수정시각을 기록했다. 기준 전체 pytest는 **4612 passed in 12.36s**다. 신규 실행 테스트·기대값 변경·실제 root lookup 실행은 없다. 수동60개 사례는 실행 검증으로 세지 않는다. 실제 자료는 기존 JSON의 ID/종류만 읽어 설명했으며 새 지문/검토 대상으로 계산하지 않았다.

최종 대조에서 기존123개 파일은 SHA256까지 모두 동일하다. 기존 파일 수정·삭제 없이 이 문서 하나만 추가했다. 실제 release6개 파일의 경로/길이/수정시각도 기준선과 같다. 1~32절과 RL01~RL60이 각각 순서대로 유일하게 존재하고 문서의 code fence가 닫혀 있음을 확인했다. 한국어 표기와 코드·테스트·lookup placeholder 추가 부재도 확인했다. 문서만 추가했으므로 실행 코드와 기존4612개 테스트의 기준선은 그대로다.

## 31. 후속 단계 추천

| 순서 | 다음 승인에서 다룰 작업 | 해당 단계 밖 |
|---|---|---|
| A, 바로 다음 | 위 단일 private _resolve_rule_root 구현과 합성 unit tests | index/ResolvedBinding/ownership/unmapped/지문/matching 연결 |
| B | 원본 root를 이용한 ownership/overlap 계약 구체화 | FULL/최종 Result를 먼저 생성하는 것 |
| C | unmapped node·허용 전체 결합의 실행 계약 구체화 | 사용자 eligibility/행정 수용 |
| D | 필요성이 확인되면 호출 지역 index/구조 검증 결과·orchestration 설계 | 근거 없이 새 범용 model/cache 도입 |
| E | 구조 검증·현재 지문 준비·기존 matcher 연결과 최종 CoverageResult 계약을 별도 승인 | 이번 root lookup 성공만으로 FULL 결정 |

이번에 B~E를 구현하라는 승인은 없다. ResolvedBinding과 RuleTreeIndex는 필요할 때 별도 검토하는 선택지이며 지금의 필수 선행 단계가 아니다. 작게 구현→합성 테스트→검증 후 다음 책임으로 확장한다.

## 32. 최종 판단

**READY_TO_IMPLEMENT_RULE_ROOT_LOOKUP**

다음 가장 작은 작업 한 개는 **rule_root_resolution.py의 private _resolve_rule_root(policy, rule_root_id)만 구현**하는 것이다. 현재32개 절의 입력·순회·타입/중복/부재 오류 순서·identity 계약을 합성 테스트로 검증한다. 기존 Policy/RuleNode/walk_nodes/Binding/Coverage/review matcher·지문 utility·기존 테스트/기대값·actual releases·Cashflow·ResidenceHistory를 변경하지 않는다.

IMPLEMENTED: 기존 모델·두 review resolver·두 matcher·세 지문 utility는 현 상태 유지. 이번에는 이 설계 문서 한 개만 추가했다.

NOT IMPLEMENTED: root lookup 코드, RuleTreeIndex/ResolvedBinding, ownership/overlap/unmapped·Coverage structural validator, CoverageResult, FULL_POLICY/CONDITION_SLICE 파생, 최종 Coverage validator, Acceptance/Benefit Bridge. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

## 33. M2.26 — IMPLEMENTED: private Rule Root Resolver

### API와 배치

M2.25의 권장 배치대로 backend/policy_engine/policy_data/rule_root_resolution.py에 다음 함수 하나를 추가했다. review matcher/resolver와 분리했고 기존 파일을 이동하거나 package public export를 변경하지 않았다.

```python
_resolve_rule_root(policy: Policy, rule_root_id: str) -> RuleNode
```

기본값·검색 옵션·추가 인자는 없다. 정확한 Policy와 exact 비공백 str만 허용하고 다른 값/하위 타입은 INVALID_STRUCTURE_INPUT PolicyDataError다. Policy 타입 → ID 형식 순서이며 두 검사를 마치기 전에 tree를 읽거나 순회하지 않는다. require_text와 같은 비공백 검사를 작은 inline 조건으로 두어 기존 helper/모델을 바꾸지 않고 명세의 prefix를 유지했다. strip은 공백 여부 검사에만 사용하며 검색 ID는 보정하지 않는다.

### 구현한 조회와 오류 우선순위

기존 walk_nodes(policy.root)를 한 번 호출해 root 포함 pre-order DFS/children 원래 순서를 그대로 사용한다. 각 node가 exact PolicyRule/ResidentRegistrationRule/BirthDateRule/RuleGroup인지 먼저 확인한 뒤 rule_id를 읽는다. ID는 원문 문자열 equality로만 비교한다. leaf/group/깊은 descendant와 root 자체 모두 정상 후보다.

호출 지역 seen ID set, found 원본 객체, duplicate flag만 사용한다. target을 찾은 뒤에도 정상 tree 끝까지 순회하며 요청 ID 외의 중복도 기록한다. 첫 target을 복제하거나 node를 재생성하지 않는다. 전역/가변 cache나 RuleTreeIndex는 없다.

오류/반환 순서는15절과 같다.

1. 잘못된 Policy → INVALID_STRUCTURE_INPUT.
2. 잘못된 ID → INVALID_STRUCTURE_INPUT.
3. 방문 node 타입이 미지원이면 rule_id 접근 전 UNSUPPORTED_RULE_NODE.
4. 전체 타입 확인이 끝난 뒤 duplicate flag가 있으면 DUPLICATE_RULE_NODE_ID.
5. 정상 유일 ID tree에 target이 없으면 RULE_ROOT_NOT_FOUND.
6. 나머지는 원래 target 객체 직접 반환.

PolicyDataError에 새 code 속성/오류 계층을 추가하지 않았다.15절의 고정 prefix/메시지를 사용하며 원본 ID·payload·현재시각을 오류에 넣지 않는다. 앞쪽 duplicate 후보보다 뒤쪽 unsupported가 우선하고, target 부재보다 duplicate가 우선하도록 duplicate 오류는 순회 후로 미뤘다. 현재 없는/제거된/renamed ID는 정상 상태나 stale로 낮추지 않는다.

### 책임과 방어 경계

직접 의존은 PolicyDataError 및 기존 models의 Policy/RuleNode/네 node 타입/walk_nodes뿐이다. Binding/Inventory/Coverage/review를 입력받거나 조회하지 않는다. 같은 root 반복 조회·parent/child·sibling 각각의 조회는 독립적으로 성공하며 “이미 사용한 root” 상태는 없다. policy_id/rule_version/operator/정책 평가 결과·근거의 의미도 조회 조건으로 사용하지 않는다.

ownership/overlap/unmapped·전체 결합·FULL/SLICE·CoverageResult·최종 validator·Acceptance/Benefit Bridge는 없다. 지문 계산기/Review 모델·resolver·matcher를 import하거나 호출하지 않는다. 외부 I/O·파일/네트워크/Git·현재시각·환경·입력 변경도 없다. ResidenceHistory placeholder를 추가하지 않았다.

가정 A1과 기존 recursive walk_nodes의 깊이 한계는 유지한다. 모든 훼손된 Python 객체/순환 tree 복구를 보장하지 않는다. 정상 생성자는 duplicate/unsupported Policy를 만들지 못하게 하므로 resolver의 해당 방어 분기를 실행하려고 frozen 객체·생성자를 우회하거나 walk_nodes에 비정상 tree를 주입하지 않았다. 기존 RL38·42·43·51~55 수동 방어 시나리오는 그대로 유지하고 production 분기의 타입 검사 위치·duplicate 지연 오류 순서를 소스로 확인했다. 실행 경로가 없는 부분까지 unit test로 검증했다고 주장하지 않는다.

### 테스트와 기존 회귀

작업 전 actual releases 제외 backend/tests/data/docs124개 파일 SHA256과 actual release6개 파일 경로/길이/수정시각을 기록했다. 기존 전체 **4612 passed in 12.27s**다. 신규 tests/test_rule_root_resolution.py는 **80 passed in 0.34s**다.

합성 테스트는 root 자체의 네 타입, nested 세 leaf·ALL/ANY/NOT,5/12단계 중첩, case/공백/prefix/suffix/rename/미존재 ID, 한국어·정규형·비공백 자유 ID, exact Policy/ref 타입·하위 타입·오류 순서, 원본 identity·100회 결정성·구조/children/evidence tuple 무변경을 확인했다. 기존 walk_nodes를 감싼 관찰용 generator가 실제 정상 tree만 전달하며 첫 target/중간/마지막/부재 요청 모두 끝까지 소비됐음을 확인했다.

서로 다른 Policy의 같은 ID, parent/child/sibling/반복 root 조회, metadata 무관성·오류 메시지 결정성·공개 export 부재도 확인했다. 공개 생성자로 중복 ID/미지원 node가 거부되는 경계를 합성 입력으로 확인했으며 immutable object hacking은 없다. 속성 접근 가드로 Policy.root·node.rule_id·group.children 외 필드 읽기를 막았고, 지문 계산/Review 호출/재검증/외부 I/O를 차단한 상태에서도 조회가 성공했다. 테스트의 책임 제약은 resolver 함수에 한정해 미래 별도 ownership/index 구현을 막지 않는다.

IMPLEMENTED: 단일 private Rule Root Resolver·합성 테스트80개.
NOT IMPLEMENTED: ownership/overlap/unmapped·RuleTreeIndex/ResolvedConditionBinding·지문 계산/orchestration·CoverageResult·FULL/SLICE·최종 Coverage validator·Acceptance/Bridge.

최종 판단: **READY_FOR_COVERAGE_OWNERSHIP_DESIGN**.
다음 가장 작은 작업 한 개는 **Binding root와 모든 descendant의 소유 집합 및 parent/child·동일 root 충돌을 판별하는 ownership/overlap 계약 설계**다. 아직 unmapped/전체 결합/Result를 함께 구현하지 않는다. 현재 작은 tree에서는 독립 resolver의 O(N×B) 호출이 blocker가 아니므로 index 모델을 선행할 근거는 없다. 공유 순회가 필요해지면 같은 타입/ID 계약을 유지하며 별도 검토한다.

실제 release/Binding/root 조회 결과·새 실제 검토 기록/지문은 생성하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

### M2.26 최종 검증 기록

전체 pytest는 **4692 passed in 14.11s**다. 기존4612개와 신규80개 모두 통과했다. 기존 Inventory/Implementation matcher142개/257개, Review resolver63개, 결과 모델166개와 GV01~GV15 literal digest 검증도 그대로 통과했으며 기존 테스트/기대값 수정은 없다.

작업 전 기준선124개(actual releases 제외) 중122개는 SHA256까지 동일하다. 변경은 이 명세와 ARCHITECTURE.md 두 문서뿐이고 resolver/합성 테스트 두 파일을 추가했다. 삭제는 없다. 기존 Policy/네 node 모델/ID 검증/walk_nodes/Binding/Coverage·matcher/Review resolver·지문 utility·공개 export·기존 모든 테스트·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했다. actual release6개 파일의 경로/길이/수정시각도 기준선과 같다. 실제 자료에 대한 root lookup 실행/저장·새 검토/지문 생성은 없으며 변경 파일의 한국어 표기도 확인했다.

