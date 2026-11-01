# Coverage Ownership / Overlap 계약 — M2.27

> 현재 구현 상태는 34절 M2.28을 따른다. 1~33절은 승인된 M2.27 설계와 당시 검증 기록이다. collector와 root pair 기반 no-overlap validator를 구현했으며 unmapped/structural orchestration/최종 Coverage 결과는 없다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 설계 전용**이다. 산출물은 이 문서 한 개이며 코드·테스트·기존 문서·실제 release를 변경하지 않는다. 아래 helper/API와 오류 메시지는 후속 구현 계약이며 아직 구현되지 않았다.

최종 판단: **READY_TO_IMPLEMENT_COVERAGE_OWNERSHIP**. 구현 범위의 겹침 확인 준비에 한정한다. unmapped·전체 결합 검증, CoverageResult/FULL_POLICY/CONDITION_SLICE의 설계·구현으로 확장하지 않는다.

## 1. 목적과 Source of Truth

현재 EligibilityCoverage.bindings가 선언한 각 조건의 구현 범위를 실제 Policy subtree에서 파생하고, 서로 다른 조건이 같은 node 구현을 중복 담당하는 모순을 결정적으로 식별할 계약을 확정한다.

기준은 COVERAGE_RULE_ROOT_LOOKUP_SPEC.md13~25·33절, ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md6~11·29·33절, POLICY_COVERAGE_SPEC.md8~12·34절, COVERAGE_REVIEW_MATCHING_SPEC.md18·24·42절, COVERAGE_FINGERPRINT_SPEC.md11~15절, DATA_MODEL.md25~26절, ARCHITECTURE.md39절이다. 현재 EligibilityCoverage/Inventory/Binding·Policy/네 RuleNode·walk_nodes·ID 유일성·_resolve_rule_root를 확인했다. 기존 소유·전체 결합·미매핑 원칙을 바꾸지 않고 이번에 소유/겹침 책임만 구체화한다.

## 2. Ownership 정의

Ownership은 **ConditionBinding 하나가 해당 condition의 구현으로 선언한 subtree 범위**다. 법적·행정적 소유·사용자 자격·실제 구현 의미의 정답을 뜻하지 않는다.

binding=(COND_A, GROUP_X, review_ref)이면 COND_A가 GROUP_X와 그 아래 모든 node를 구현 범위로 선언한다. condition_id가 소유 선언의 주체이고 rule_root_id는 그 범위의 시작점이다. review_ref는 별도 검토 참조이며 소유 범위 계산에 사용하지 않는다. Binding이 존재한다는 사실만으로 구현의 의미 검토가 완료되지는 않는다.

## 3. Root + descendants 원칙

소유 집합은 **root 자체 + 그 root의 모든 descendants**로 확정한다. 식으로는 owned(binding) = {node.rule_id | node in walk_nodes(resolved_root)}다. root를 빼거나 leaf만 모으지 않는다.

이 집합은 현재 tree 구조에서 파생한다. ConditionBinding에 owned_rule_ids 필드를 추가하지 않고 EligibilityCoverage에도 ownership_map/overlaps를 저장하지 않는다. tree의 child가 추가·삭제되면 같은 root ID여도 파생 범위가 달라진다. 과거 소유 목록을 그대로 재사용하지 않는다.

## 4. Leaf ownership

PolicyRule/ResidentRegistrationRule/BirthDateRule은 모두 **자기 rule_id 하나**를 소유한다. leaf의 field/value/date/지역/근거·사용자 PASS/FAIL/UNKNOWN이 범위를 바꾸지 않는다.

leaf A와 별개 leaf B가 논리적으로 같은 조건을 계산해도 ID가 다르고 subtree가 분리되어 있으면 소유 겹침은 아니다. 논리적 중복성/등가성은 이 detector의 판정 대상이 아니다.

## 5. Group ownership

RuleGroup은 group 자체와 모든 자손 group/leaf를 소유한다. ALL/ANY/NOT 모두 같은 구조 규칙이다. ANY branch가 사용자에 따라 선택되지 않거나 NOT 아래에 있다고 소유 범위에서 제외하지 않는다.

group 하나가 여러 leaf로 구성된 하나의 의미상 조건을 구현할 수 있다. 그 group root Binding과 하위 leaf Binding을 동시에 두는 것은 서로 다른 condition의 구현 범위가 겹치는지 검증해야 할 대상이다. group 종류를 보고 자동으로 분할·병합하지 않는다.

## 6. Nested ownership와 strict tree

GROUP_A → [RULE_1, GROUP_B → [RULE_2, RULE_3]]에서 GROUP_A의 범위는 GROUP_A/RULE_1/GROUP_B/RULE_2/RULE_3 전체다. 중간 group을 없애거나 원본 tree를 flatten하지 않는다. 뒤의 tuple은 모든 node를 보존한 조회 표현일 뿐 tree 변경이 아니다.

현재 공개 RuleGroup/Policy 생성자는 walk_nodes에 나타난 ID의 전체 유일성을 확인한다. 같은 객체를 두 parent에 재사용해도 방문 때 같은 ID가 반복되어 거부되고, 서로 다른 객체의 같은 ID도 거부된다. **MVP는 유한 strict tree, 공유 subtree DAG 미지원**을 유지한다.

정상 strict tree에서 sibling subtrees는 disjoint다. 진짜 sibling인데 ID 교집합이 생겼다고 주장하는 입력은 duplicate/shared 구조 또는 현재 Policy에서 resolve하지 않은 입력을 먼저 의심해야 한다. 객체를 깨뜨려 DAG 예외를 새로 만들지 않는다. 정상 객체를 훼손하지 않는 M2.25 가정 A1과 M2.26 방어 한계를 유지한다.

## 7. Ownership 표현 타입

| 선택 | 장점 | 한계 | 결정 |
|---|---|---|---|
| pre-order tuple[str, ...] | tree 순서·root/중간 group을 감사하기 쉽고 결과 표현이 결정적 | 교집합에 지역 set 변환 필요 | **canonical 파생 표현으로 채택** |
| frozenset[str] | 불변성과 교집합 직접 사용 | 출력 순서가 없고 별도 감사 표현 필요 | 기본 반환값으로 미채택 |
| tuple와 frozenset을 모델 필드로 모두 저장 | 양쪽 사용 편의 | 같은 파생 정보 중복 저장 | 미채택 |

collector는 root 포함 pre-order tuple을 반환한다. 내부 overlap 검증에서 tuple을 지역 set으로 한 번 변환할 수 있다. tuple·set 두 표현을 영속 모델/공개 결과 필드로 저장하지 않는다. 입력/반환 ID 문자열을 정규화·정렬·dedupe하지 않는다. 중복 ID는 tree 오류이지 자동 중복 제거 대상이 아니다.

## 8. rule_id 기준과 원본 node 역할

**같은 현재 Policy 안의 유일한 rule_id**를 소유 교집합 비교 단위로 사용한다. Python 객체 주소·dataclass의 전체 값 equality·표시명·condition 의미 문장·지문은 비교 기준이 아니다. 서로 다른 Policy의 같은 ID를 한 소유 검증에 섞지 않는다.

root 원본 객체는 subtree 순회·후속 지문 계산에 필요하므로 별도로 지역값에 보존한다. ID tuple이 원본 node 객체를 대체하지 않는다. 실제 root 존재·같은 Policy 소속은 _resolve_rule_root를 호출하는 상위 준비 단계의 책임이다. ID 문자열이 같다는 사실만으로 외부 객체를 그 Policy의 node로 인증하지 않는다.

## 9. Same-root overlap

COND_A→ROOT_X, COND_B→ROOT_X는 현재 EligibilityCoverage 생성자가 허용하고 두 root lookup도 성공한다. 그러나 서로 다른 condition의 owned 집합이 ROOT_X 자체부터 겹치므로 **COVERAGE_OWNERSHIP_OVERLAP Data Error**다.

이는 tree 안의 중복 rule_id 오류와 다르다. 정상 tree에는 ROOT_X가 하나이고 두 Binding이 같은 node를 참조한 것이다. M2.26의 DUPLICATE_RULE_NODE_ID로 바꾸거나 두 번째 lookup을 거부하지 않는다. 같은 condition_id의 중복 Binding은 별도로 기존 Coverage 생성자가 거부한다.

## 10. Parent/child·ancestor/descendant overlap

COND_A→GROUP_X, COND_B→그 아래 RULE_A이면 두 범위의 교집합에 RULE_A가 들어가므로 오류다. 직접 자식뿐 아니라 여러 단계 떨어진 leaf/group도 동일하다.

GROUP_A 아래 GROUP_B 아래 RULE_C가 있고 서로 다른 condition이 GROUP_A/GROUP_B를 가리키면 교집합은 GROUP_B와 RULE_C다. group 자체도 겹침에 포함한다. leaf만 검사해 nested group 충돌을 놓치지 않는다. ancestor map/parent pointer/depth 필드는 필요하지 않다. 집합 교집합만으로 same-root와 조상/자손 충돌을 모두 검출할 수 있다.

## 11. Siblings/disjoint

서로 다른 sibling leaves, sibling groups, 깊은 분리 subtrees의 소유 집합이 서로소이면 overlap 오류는 없다. 세 개 이상 Binding도 모든 쌍의 교집합이 비어 있으면 이 검사에 한해 통과한다.

이는 소유 범위 비겹침만 의미한다. 전체 결합이 올바른지, tree에 미매핑 node가 남는지, 필요한 조건을 모두 구현했는지까지 보장하지 않는다. 비겹침 성공을 전체 구조/정책 완료로 표시하지 않는다.

## 12. Policy-root ownership

Binding 하나가 Policy.root를 가리키면 전체 tree가 그 condition의 범위다. 하나의 의미상 조건을 실제로 전체 tree가 구현하는 단일 Binding 형태는 이 검사에서 통과할 수 있다. 목록 완결성/의미 검토는 별도다.

Policy root Binding 외에 같은 tree의 node를 가리키는 Binding이 더 있으면 반드시 겹친다. 서로 다른 root ID여도 예외가 아니다. Policy.root가 leaf면 자기 ID 하나, group이면 전체 descendants를 소유한다. 전체 조합용 root의 허용 형태를 이 문서에서 새로 정의하거나 변경하지 않는다.

## 13. Overlap 정의와 알고리즘 경계

서로 다른 condition A/B에 대해 **owned(A) ∩ owned(B) ≠ ∅**이면 overlap이다. 같은 root인지/조상 관계인지 별도 논리 해석 없이 판정한다. 사용자 사실/분기 활성 여부/Review 상태/rule version이 교집합을 면제하지 않는다.

동일 semantic Coverage에서 Binding tuple 순서만 달라져도 판정이 같아야 한다. canonical Binding 순서로 각 root의 tuple과 지역 ID set을 준비한 후 canonical pair 순서로 교집합을 확인한다. pair별 매번 tree를 재순회하지 않는다. 모든 root/owned tuple 준비가 성공한 뒤에만 pair 검사를 시작한다.

## 14. Overlap error contract

| 선택 | 감사 가능성/복잡도 | 결정 |
|---|---|---|
| same-root와 parent/child에 다른 오류 prefix | 분류는 구체적이나 예외 종류·우선순위가 늘어남 | 미채택 |
| 모든 교집합에 COVERAGE_OWNERSHIP_OVERLAP | 동일한 구조 모순을 단순하게 유지. 두 root 값으로 same-root도 식별 가능 | **채택** |

기존 PolicyDataError와 안정된 메시지 prefix를 사용한다. 새 exception class/Enum/.code/.metadata 속성·OverlapResult 모델은 없다. 구조 모순을 STALE/UNKNOWN/부분 정상 결과로 감싸지 않는다.

오류에 포함할 최소 정보는 **condition_a, rule_root_a, condition_b, rule_root_b, overlap_count, first_overlap_rule_id** 여섯 필드다. a/b는15절의 canonical pair 순서를 보존하며 condition과 root의 관계를 분리해 정렬하지 않는다. overlap_count는 해당 첫 충돌 쌍의 전체 교집합 ID 수다. first_overlap_rule_id는16절의 최소 ID 한 개다.

메시지 형식은 prefix + ': ' + 이 여섯 필드의 JSON 객체다. 후속 구현은 json.dumps의 sort_keys=True, ensure_ascii=True, separators=(',', ':')로 결정적으로 표현한다. JSON escaping으로 공백/따옴표/줄바꿈/비ASCII root ID를 손실 없이 구분한다. 이는 작은 오류 표현이며 fingerprint 계산이나 새 generic serializer가 아니다. canonical pair 두 root/condition와 교집합 증거 하나만 포함하고 전체 node·Review·사용자 payload는 넣지 않는다.

전체 overlap ID 목록/모든 충돌 쌍을 오류에 복사하지 않아 subtree 규모에 따른 문자열 증폭을 줄인다. 기존 자유 ID에 길이 제한을 새로 강제하거나 ID를 자르지 않는다. 전체 교집합은 같은 정상 입력에서 다시 계산할 수 있다. 임의 display 메시지를 별도 영속 audit model로 저장하지 않는다.

입력 포장 오류는 기존 **INVALID_STRUCTURE_INPUT**을 사용한다. collector의 미지원 descendant/중복 방어는 **UNSUPPORTED_RULE_NODE / DUPLICATE_RULE_NODE_ID**를 유지한다. root 없음은 기존 resolver의 **RULE_ROOT_NOT_FOUND**이며 ownership 오류로 감싸지 않는다.

## 15. Deterministic Binding pair ordering

| 선택 | 문제/장점 | 결정 |
|---|---|---|
| Coverage.bindings 원래 순서 | tuple 재배열에 따라 첫 오류가 달라짐 | 미채택 |
| root의 tree 방문 순서 | tree의 child 순서가 첫 충돌 주체를 바꿈 | 미채택 |
| condition_id ASCII 오름차순 | 안정적인 condition identity로 입력 순서와 독립적 | **채택** |

condition_id는 현재 [A-Z0-9_]+이므로 Python 문자열 오름차순이 ASCII 순서와 같다. 순서가 c1<c2<c3이면 pair 검사 순서는 **(c1,c2) → (c1,c3) → (c2,c3)**다. 일반적으로 (min condition, max condition) 쌍의 사전순이다. 자연 숫자 정렬을 하지 않으므로 COND_10은 COND_2보다 앞선다.

condition 하나당 Binding 하나라는 기존 Coverage invariant를 전제한다. a/b에 대응하는 root는 각각의 Binding에서 유지한다. 예를 들어 parent condition이 사전순으로 뒤에 있어도 parent를 a로 바꾸지 않는다. 원래 Coverage/Binding tuple은 정렬 결과로 교체하지 않는다.

## 16. Overlap ID ordering

소유 tuple의 **pre-order 표현**과 **오류 증거 ID 순서**를 분리한다. pre-order 오류 목록은 tree 감사에는 편하지만 child 순서만 바뀌어도 증거 순서가 달라진다. ID 정렬은 그 변화와 독립적이다.

오류의 개념적 ID 순서는 **원문 문자열 Unicode code point 오름차순**으로 확정한다. ASCII ID에는 ASCII 순서와 같고, 기존 root/node ID가 한국어·공백을 포함할 수 있어 ASCII-only를 새로 강제하지 않는다. locale/NFC·NFD/대소문자 변환은 없다.

실제 오류에는 정렬상 첫 ID 한 개와 전체 교집합 수만 넣는다. 구현은 교집합의 min을 선택해도 되며 전체 정렬 목록을 저장할 필요는 없다. set iteration의 첫 원소를 증거로 선택하지 않는다. child 순서 변경으로 owned tuple은 달라질 수 있지만 집합·첫 증거·충돌 pair는 같아야 한다. 지문은 child 순서에 민감하다는 기존 계약도 그대로다.

## 17. Fail-fast와 오류 우선순위

**모든 충돌 수집 대신 첫 canonical conflict에서 PolicyDataError**를 채택한다. 기존 프로젝트의 fail-fast 철학과 맞추고 giant error/report 모델을 피한다. fail-fast는 첫 Binding에서 곧바로 overlap을 확정한다는 뜻이 아니다.

후속 상위 호출의 준비 순서는 다음과 같다.

1. 기존 EligibilityCoverage/Policy 입력 및 해당 구조 계층의 사전조건을 확인한다.
2. condition_id순으로 **모든 Binding root를 _resolve_rule_root로 먼저 resolve**한다. 하나라도 없거나 tree가 잘못되면 그 resolver 오류를 전파한다.
3. resolved pair collection의 로컬 포장/연결을 확인한다.
4. condition_id순으로 모든 owned ID tuple을 수집한다. 이 단계 오류가 있다면 overlap보다 먼저 실패한다.
5.15절의 canonical pair 순서로 교집합을 확인해 첫 충돌만 보고한다.
6. 충돌이 없으면 이 validator는 None을 반환한다.

앞의 두 root가 겹쳐도 뒤쪽 Binding root가 없으면 **root resolution 오류가 우선**이다. ownership collector가 subtree 범위를 모은다는 이유로 M2.26 resolver의 전체 Policy 검사·오류 순서를 생략하거나 바꾸지 않는다. 현재 tree 구조 모순을 Review stale나 미완성 상태로 낮추지 않는다. CoverageResult 상태를 이번에 정의하지 않는다.

## 18. Root lookup 관계와 신뢰 경계

_resolve_rule_root는 Policy+ID → 원본 node를 담당하며 condition을 모른다. 두 Binding이 같은 root 또는 parent/child를 가리킬 때 조회는 각각 정상일 수 있다. 이 문서의 overlap 검사는 그 뒤의 독립 책임이다. 기존 resolver의 입력/오류/반환 identity/전체 순회는 변경하지 않는다.

**Assumption A1:** resolved pairs는 하나의 정상 현재 Policy와 하나의 정상 EligibilityCoverage에서, 모든 Binding을 빠짐없이 exact ref로 resolve한 내부 호출 지역값이다. 외부에서 node/owned ID 목록을 받아 사실로 신뢰하는 public API가 아니다. 미래 구현 테스트에서도 같은 합성 Policy에서 root를 준비한다.

아래 최소 validator는 Policy를 입력받지 않으므로 같은 ID의 외부 객체가 실제 그 Policy에 속하는지 새로 증명하지 않는다. 그 연결은 위의 resolver 호출이 보장한다. bare node의 원래 Policy를 추측하거나 parent pointer/전역 registry를 추가하지 않는다. 이 한계를 새 ResolvedBinding 인증 모델로 해결했다고 주장하지 않는다.

## 19. Missing Binding·unknown condition 관계

Inventory의 조건 중 Binding 자체가 없는 것은 completeness 문제이며 소유 겹침이 아니다. 존재하는 Binding들만 disjoint하면 이 검사에 한해 통과한다. 가상의 root/Binding/소유 집합을 만들어 빠진 조건을 채우지 않는다.

Binding.condition_id의 Inventory 소속과 동일 condition 중복은 기존 EligibilityCoverage 생성자가 검증한다. ownership은 이를 주된 업무로 다시 구현하지 않는다. validator의 내부 pair 포장에서 같은 condition을 중복 전달하는 것은 정상 Coverage에서 파생하지 않은 **입력 계약 오류**이며 INVALID_STRUCTURE_INPUT으로 거부한다. 같은 root를 가진 서로 다른 condition은 입력 오류가 아니라 실제 overlap 검사 대상이다.

빈 resolved tuple은 소유 충돌 pair가 없으므로 이 helper에서는 None 반환이 가능하다. 이는 비어 있지 않은 Policy의 zero-binding 구조를 유효하다고 승인하는 것이 아니다. 기존 unbound 원칙은 별도 단계에 남는다.

## 20. Unmapped validation 관계

owned_all = 모든 owned 집합의 union은 후속 unmapped 검증에 재사용할 수 있는 **개념적 파생값**이다. 그러나 non-overlap은 tree 전체가 매핑됐다는 뜻이 아니다. unowned sibling/group이나 전체 조합 root를 이번 단계에서 판정하지 않는다.

후속 unmapped 단계에 필요한 입력은 같은 Policy의 전체 node ID, 동일 Binding별 owned tuple/집합 및 전체 결합 구조다. 이 문서는 예외 목록·unmapped 알고리즘·오류 API·결과 모델을 새로 정하지 않는다. 기존 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md11절의 모든 node/허용 전체 조합 root 원칙을 폐기하거나 leaf-only로 변경하지 않는다. 실제 구현 경계와 오류 순서는 해당 후속 설계에서 다룬다.

최소 overlap validator는 None만 반환하므로 소유 union을 새 결과 필드로 공개하지 않는다. 후속 orchestration이 지역 수집값을 공유할 필요가 확인되면 별도 승인으로 helper 내부 분할/재사용을 검토한다. 이를 이유로 지금 OwnershipResult/CoverageResult를 선행 설계하지 않는다.

## 21. Review matching·사용자 평가 관계

ownership은 ReviewContext/record/MatchResult를 읽지 않는다. review가 MISSING/STALE/MATCHED인지는 같은 tree와 Binding의 겹침을 바꾸지 않는다. 구조 모순이 있으면 review 검사 전에 오류이며 stale에 흡수하지 않는다.

사용자 facts·소득·생년월일·주소·PolicyEvaluation PASS/FAIL/UNKNOWN도 입력이 아니다. ALL/ANY/NOT의 논리 결과·의미 동치·충족 여부를 계산하지 않는다. 비겹침이 공식 의미의 완결성·정책 수용을 인증한다고 주장하지 않는다. FULL/SLICE의 새 계약을 작성하지 않는다.

## 22. Fingerprint 관계

ownership은 실제 resolved root의 구조/ID를 사용하며 tree/subtree 지문을 계산·비교하지 않는다. 지문이 같다는 이유로 ID가 다른 subtree를 공유 처리하거나, 지문이 다르다는 이유로 겹침을 면제하지 않는다.

현재 source/dataset/rule/implementation version·근거 metadata가 바뀌어도 실제 tree ID 관계가 같으면 소유 교집합은 같다. 그 변화의 review freshness는 matcher 책임이다. node 이동/child 추가·삭제는 현재 subtree에서 다시 범위를 파생하고, 과거 owned tuple/지문으로 덮지 않는다.

## 23. RuleTreeIndex 필요성

현재 tree N개 node, Binding B개에서 root resolution은 O(N×B)다. 소유 tuple 수집은 각 subtree 크기의 합 S, set 준비도 O(S)다. 쌍별 교집합은 set 크기에 비례하는 비용이 있으며 호출 지역 계산으로 충분하다. index를 만들어도 모든 overlap pair 의미/진단 순서는 별도로 필요하다.

**현재 RuleTreeIndex는 필수 선행이 아니다.** tree가 작고 기존 resolver가 있으므로 반복 traversal을 이유로 새 기반 모델을 만들지 않는다. pair마다 수집을 반복하지 않고 각 root당 한 번 모은다. 실제 규모 문제가 확인되거나 후속 전체 validator에서 공유 준비가 필요하면 같은 identity/오류 계약을 보존하는 지역 index를 별도 검토한다. cache/global mutable mapping은 없다.

## 24. ResolvedBinding 필요성

**지속 모델 ResolvedConditionBinding도 필수가 아니다.** 호출 지역의 (binding, root), 수집 후 (binding, root, owned_ids) tuple로 충분하다. root는 원본 객체, owned_ids는 파생 pre-order tuple이다. 별도 dataclass/serializer/저장 필드·서명/검토 metadata를 추가하지 않는다.

임시 set·ID tuple과 노드를 같이 지역에 두는 것은 같은 정보를 영속 모델 필드로 중복 저장하는 것과 다르다. 호출이 끝나면 해제되며 Policy/Coverage/Binding/children/evidence를 변경하지 않는다. filesystem/network/Git/시각/환경변수·지문·LLM 호출은 없다.

## 25. 후속 최소 helper API와 입력 계약

후속 구현은 **backend/policy_engine/policy_data/coverage_ownership.py**의 private 두 함수로 제안한다. 기존 root resolver 모듈은 유지하며 public export를 추가하지 않는다. 이번에는 파일/placeholder를 만들지 않는다.

```python
_collect_owned_rule_ids(root: RuleNode) -> tuple[str, ...]

_validate_binding_ownership_no_overlap(
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> None
```

### Collector

exact 네 RuleNode 중 하나인 root를 받는다. root 입력 자체가 None/dict/하위 타입 등이면 INVALID_STRUCTURE_INPUT이다. walk_nodes(root)는 Policy 없이 subtree에도 동작하므로 그대로 재사용한다. root부터 모든 descendants의 rule_id를 원래 pre-order로 수집한다. 네 exact 타입 확인은 각 node의 ID 접근보다 먼저이며 미지원 descendant는 UNSUPPORTED_RULE_NODE다. ID 중복을 자동 dedupe하지 않고 M2.26과 같은 타입 우선/순회 후 DUPLICATE_RULE_NODE_ID 방어를 적용한다.

이미 resolver가 전체 Policy를 확인했지만 collector의 standalone private 입력도 지원 타입을 명확히 유지한다. 별도 recursive engine·operator 해석·원본 모델 __post_init__ 재호출은 없다. 정상 공개 생성자가 duplicate/unsupported tree를 막는 한 불변 객체 훼손 테스트는 작성하지 않고 기존 수동 방어 사례를 유지한다.

### No-overlap validator

정확한 tuple, 각 원소는 길이2의 정확한 tuple이고 첫 원소는 exact ConditionBinding, 두 번째는 exact 현재 RuleNode다. list/raw dict/하위 타입을 변환하지 않는다. A1을 전제로 하며 처음에 포장/타입을 모두 확인한다. 이후 condition 중복과 **root.rule_id == binding.rule_root_id** 연결을 검사한다. 포장·중복 condition·잘못 연결된 pair는 INVALID_STRUCTURE_INPUT이다. 같은 root라도 다른 condition이면 정상 입력이다.

포장/타입 오류는 payload 없는 고정 필드 메시지로 먼저 거부한다. 타입이 모두 유효하면 중복 condition 유무를 확인하고, condition 순서로 root ID 연결을 확인한다. 모든 입력 연결이 정상인 뒤 condition_id순으로 collector를 호출해 모든 tuple을 준비하고,15절의 pair 순서로 검사한다. collector 오류를 그대로 전파한다. supplied owned ID tuple을 받아 검증 없이 재사용하는 인자는 만들지 않는다.

성공은 None, overlap은14절 오류다. 빈 tuple/단일 pair는 교집합 pair가 없으나 존재하는 pair의 입력/수집 검사는 수행한다. root lookup을 내부에서 복제하거나 호출하지 않고 이미 resolve된 원본을 받는다. 이 두 helper만의 성공은 A1의 외부 소속/누락 부재를 재인증하지 않는다. 상위에서 모든 Binding의 resolve를 먼저 마치는 단계는 아직 미구현이다.

## 26. Synthetic examples

```text
ROOT_ALL
├── GROUP_A [ALL]
│   ├── RULE_A1
│   └── RULE_A2
└── GROUP_B [ANY]
    └── RULE_B1
```

GROUP_A tuple은 (GROUP_A,RULE_A1,RULE_A2), GROUP_B tuple은 (GROUP_B,RULE_B1)이다. ROOT_ALL은 각 sibling Binding의 소유에 들어가지 않지만 이 문서에서 그 node의 unmapped 판정을 하지 않는다.

| Bindings | 이 검사에서의 결과 |
|---|---|
| COND_A→GROUP_A, COND_B→GROUP_B | disjoint, None |
| COND_A→GROUP_A, COND_B→GROUP_A | overlap_count=3, 첫 ID=GROUP_A |
| COND_A→GROUP_A, COND_B→RULE_A1 | overlap_count=1, 첫 ID=RULE_A1 |
| COND_ALL→ROOT_ALL, COND_B→GROUP_B | overlap_count=2, 첫 ID=GROUP_B |
| COND_A→RULE_A1, COND_B→RULE_A2 | disjoint, 다른 node의 미매핑은 별도 |

다중 충돌의 예로 COND_A→RULE_A1, COND_B→GROUP_A, COND_C→RULE_A2라면 A/B와 B/C가 겹치고 A/C는 겹치지 않는다. 첫 오류는 (COND_A,COND_B)다. 세 조건이 모두 GROUP_A를 가리키면 모든 pair가 겹치지만 같은 첫 pair만 반환한다. parent가 반드시 오류의 a인 것은 아니다.

nested sibling 예: GROUP_X 안의 GROUP_X1과 GROUP_X2가 각각 분리 leaf를 갖고 있으면 두 subtree 범위는 서로소다. 중간 group 자체도 각자의 owned tuple에 포함하며 tree를 재구성하지 않는다.

## 27. Current Ansan example

로컬 release002의 기존 tree ID만 읽어 개념적으로 참고했다. 실제 새 Inventory/Binding/ownership 결과·검토 기록·지문은 만들거나 실행하지 않았다.

현재 ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE는 ALL이고 resident leaf ANSAN_YBI_2026_RESIDENT_AT_APPLICATION와 birth leaf ANSAN_YBI_2026_Q3_BIRTH_RANGE를 가진다. 향후 공식 검토된 inventory에서 각각을 서로 다른 condition으로 binding한다면 두 leaf의 owned 집합은 disjoint일 수 있다.

두 leaf가 disjoint라는 예시만으로 전체 tree mapping/목록 완결성·정책 구현 완료를 주장하지 않는다. 전체 ALL root를 별도 condition에 추가하면 기존 두 leaf와 겹친다. 현재 release의 DRAFT/CONDITION_SLICE와 SHA 선언은 그대로 두며 actual 데이터를 이 설계에 맞춰 수정하지 않는다.

## 28. Future ResidenceHistory example

설명용 가상 구조 RESIDENCE_DURATION_GROUP = ANY(CONTINUOUS_3Y,CUMULATIVE_10Y)가 하나의 의미 조건에 대응한다면 그 Binding은 group과 두 경로를 함께 소유한다. 어느 child를 다른 condition에 다시 binding하면 parent/child overlap이다.

이는 group 소유 원칙의 예시일 뿐, 연속/합산 기간의 기산·날짜·등록상태·귀화 예외를 확정하지 않는다. 실제 specialized Rule/입력모델/placeholder/정책 Binding을 추가하지 않는다. M1.18 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지이며 공식 답변 전 구현하지 않는다.

## 29. 후속 구현 테스트 계약

신규 실행 테스트는 이번에 작성하지 않는다. 다음 구현에서 합성 Policy/정상 Coverage/기존 resolver로 얻은 root를 사용한다.

| 범위 | 실행 검증 계약 |
|---|---|
| 수집 | 세 leaf self, ALL/ANY/NOT root·전체 descendant, nested 중간 group 포함, pre-order·원문 ID 보존 |
| 소유 겹침 | same leaf/group, parent/leaf·parent/group·deep descendant, Policy root+다른 root 오류 |
| 비겹침 | sibling leaves/groups·deep disjoint·세 개 disjoint, missing Binding만으로 오류 없음 |
| 결정성 | 모든 Binding 입력 순열에서 같은 첫 canonical pair·root 관계, 교집합 수·최소 ID; child 순서 변화는 tuple만 변경 |
| 오류 표현 | 단일 COVERAGE_OWNERSHIP_OVERLAP prefix·여섯 JSON 필드·control/Unicode ID escaping·same-root/조상 충돌 공통 처리 |
| 준비 순서 | 정상 pair 포장·같은 condition 중복 거부·Binding/root ID 연결 확인; 모든 collection 준비 후 overlap 검사 |
| 분리 | missing root는 resolver 오류, review/fingerprint/facts 무관, unknown condition은 Coverage 생성자 오류 |
| 무변경 |100회 반복의 값/오류 동일, Policy/Coverage/Binding/root/children tuple 원본 유지 |
| 경계 | exact 타입·하위 타입·빈/단일 resolved tuple·private export·I/O/cache 부재, collector의 기존 tree 방어 한계 |

M2.26 resolver/walk_nodes·기존 모든 모델·matcher·지문 utility/고정값을 바꾸지 않는다. 공개 생성자로 만들 수 없는 DAG/duplicate/unsupported tree를 object hacking으로 테스트하지 않는다. 정상 생성자의 거부는 실행 가능한 경계이고, 그 뒤의 unreachable 방어는 소스 검토/수동 시나리오로 남긴다.

collector/validator 함수 자체의 책임만 제한하고 같은 모듈의 미래 unmapped/index 기능이 절대 추가될 수 없다는 구조 테스트를 만들지 않는다. 모든 root resolution이 overlap보다 먼저라는 통합 호출 검증은 해당 상위 orchestration이 구현될 때 추가한다. 이번 설계가 그 미구현 경로의 실행 통과를 뜻하지 않는다.

## 30. 수동 시나리오 — OW01~OW72

**72개 문서상 사례이며 신규 실행 테스트가 아니다.** 별도 표시가 없으면 같은 정상 현재 Policy/정상 Coverage에서 모든 root가 resolve된 내부 입력을 전제한다. 성공은 비겹침 또는 수집 성공만 뜻한다. Error는 PolicyDataError다.

| ID | 사례 | 기대 |
|---|---|---|
| OW01 | atomic leaf root | tuple에 자기 ID 하나 |
| OW02 | resident leaf root | 자기 ID 하나 |
| OW03 | birth leaf root | 자기 ID 하나 |
| OW04 | ALL group root | group 자체+모든 descendant |
| OW05 | ANY group root | 모든 branch 포함, 평가하지 않음 |
| OW06 | NOT group root | group과 유일 child 전체 포함 |
| OW07 | nested group | 모든 중간 group/leaf 포함 |
| OW08 | Policy.root를 Binding root로 선택 | 전체 현재 tree 범위 |
| OW09 | sibling leaves | 교집합 없음 |
| OW10 | sibling groups | 교집합 없음 |
| OW11 | 깊은 분리 sibling subtrees | 교집합 없음 |
| OW12 | 세 condition이 분리된 subtrees | 모든 pair 비겹침 |
| OW13 | 두 condition이 같은 leaf | OVERLAP, count=1 |
| OW14 | 두 condition이 같은 group | group+descendant 전체 교집합 |
| OW15 | 세 condition이 같은 root | 첫 canonical pair 오류만 |
| OW16 | group과 직접 leaf를 다른 condition에 binding | leaf ID overlap |
| OW17 | group과 내부 nested group | 내부 group+descendant overlap |
| OW18 | Policy root와 deep leaf | deep leaf overlap |
| OW19 | grandparent와 descendant group | descendant group 전체 overlap |
| OW20 | A leaf / B 그 parent group | A/B 충돌 |
| OW21 | 같은 B group / C 다른 내부 leaf | B/C도 충돌 |
| OW22 | OW20~21의 A/C는 sibling leaves | A/C는 비겹침; 첫 오류는 A/B |
| OW23 | A/B/C가 모두 ancestor chain | 모든 pair 충돌, 첫 A/B |
| OW24 | bindings tuple 순서를 역전 | 첫 pair/메시지 동일 |
| OW25 | group children 순서를 바꿈 | owned tuple은 바뀔 수 있고 집합/증거는 동일 |
| OW26 | COND_10과 COND_2가 충돌 | ASCII로 COND_10이 a |
| OW27 | 교집합 IDs를 여러 번 계산 | count/min ID 항상 동일 |
| OW28 | Inventory B에 Binding 없음, A만 정상 | A 소유 계산 가능, missing을 overlap으로 만들지 않음 |
| OW29 | Binding root 하나가 없음 | ownership 전에 RULE_ROOT_NOT_FOUND |
| OW30 | review가 STALE | 소유 범위/충돌 결과 영향 없음 |
| OW31 | ReviewContext가 없음 | 소유 범위/충돌 결과 영향 없음 |
| OW32 | 같은 tree에 과거 Tree 지문 불일치 | ownership은 지문을 읽지 않음 |
| OW33 | 사용자 평가 PASS→FAIL/UNKNOWN | ownership 변화 없음 |
| OW34 | 현재 안산 resident/birth siblings 개념 | leaf 집합 disjoint 가능, 실제 결과 생성 없음 |
| OW35 | 미래 기간 ANY group을 한 condition에 binding | 설명상 group+양쪽 branch 소유 |
| OW36 | OW35의 child를 다른 condition에 재binding | parent/child overlap, 실제 Rule 구현 없음 |
| OW37 | tree에 duplicate rule_id | 생성자/기존 root resolver 경계 오류, overlap으로 감추지 않음 |
| OW38 | 같은 node 객체를 두 parent에 공유하는 DAG | 현재 공개 생성자의 ID 유일성이 거부, 수동 방어 사례 |
| OW39 | 미래 unsupported node | 현재 생성자/resolver/collector fail-closed, placeholder 없음 |
| OW40 | Policy root Binding 하나만 있음 | 다른 pair 없으므로 소유 겹침 없음 |
| OW41 | Policy root Binding+다른 내부 root Binding | 반드시 overlap |
| OW42 | leaf의 field/value/근거 변경, ID/구조 동일 | owned tuple은 self 그대로, 검토 의미는 별도 |
| OW43 | 빈 RuleGroup | 공개 생성자가 거부, collector로 우회하지 않음 |
| OW44 | NOT group에 child Binding도 별도로 존재 | child overlap, 부정 의미로 면제 안 함 |
| OW45 | 정상 입력100회 반복 | 동일 tuple/오류 pair·정보 |
| OW46 | set 내부 iteration 순서가 달라짐 | 명시 min 선택으로 오류 증거 동일 |
| OW47 | 호출 전후 Policy/children 비교 | 값·원본 identity 유지 |
| OW48 | 호출 전후 Coverage/bindings 비교 | 입력 순서와 원본 유지 |
| OW49 | 호출 전후 ConditionBinding 비교 | 새 파생 필드/변경 없음 |
| OW50 | canonical 첫 pair는 비겹침, 두 번째는 충돌 | 첫 실제 충돌 pair 오류 |
| OW51 | 여러 pair가 충돌 | 전체 수집 없이 첫 canonical conflict만 |
| OW52 | 소유되지 않은 sibling rule 남음 | non-overlap 통과 가능, unmapped는 후속 |
| OW53 | owned 집합의 union을 개념적으로 구성 | 후속 unmapped 입력 후보, 현재 결과 필드 아님 |
| OW54 | overlap-free이나 일부 mapping 부족 | 전체 구조/완료 승인으로 승격하지 않음 |
| OW55 | 의미상 조건 하나가 여러 leaf의 group을 담당 | group 전체 한 소유 범위 허용 |
| OW56 | 서로 다른 IDs의 동등한 논리 subtree | disjoint면 overlap 없음, 의미 동치 추론 없음 |
| OW57 | subtree가 이동했으나 내부 ID 범위 동일 | 해당 소유 집합 유지 가능, 전체 결합/지문은 별도 |
| OW58 | root rename 후 Binding은 과거 ID | 기존 root resolver의 NOT_FOUND |
| OW59 | bound group 아래 새 child 추가 | 새 현재 owned tuple에 child 포함; 다른 Binding과 새 겹침 가능 |
| OW60 | bound group의 child 제거 | 현재 tuple에서 제외; 제거 child Binding은 lookup 실패 |
| OW61 | root ID/교집합 ID가 한국어·공백 포함 | 원문 보존, Unicode code point 최소 증거 |
| OW62 | pre-order 첫 ID와 문자열 최소 ID가 다름 | tuple은 pre-order, 오류 증거는 문자열 최소 |
| OW63 | root ID에 따옴표/줄바꿈이 있음 | 오류 JSON escaping, 정규화 없음 |
| OW64 | 같은 root ID처럼 보여도 공백/정규형이 다른 별개 node | exact ID로 구분, 유일 tree에서 다르면 다른 identity |
| OW65 | 빈 resolved tuple | 이 helper는 None, zero-binding 전체 유효성 주장 없음 |
| OW66 | 정상 단일 pair | 수집/입력 검사는 수행, overlap pair 없음 |
| OW67 | resolved list 또는 잘못된 pair 길이/타입 | INVALID_STRUCTURE_INPUT, 자동 변환 없음 |
| OW68 | 같은 condition을 resolved pair에 두 번 전달 | 정상 Coverage 파생 계약 위반, INVALID_STRUCTURE_INPUT |
| OW69 | Binding.root ID와 supplied root.rule_id가 다름 | INVALID_STRUCTURE_INPUT, remap 없음 |
| OW70 | 앞 pair 충돌 가능, 뒤 root 부재 | 모든 resolve 우선 원칙으로 NOT_FOUND가 먼저 |
| OW71 | 앞 pair 충돌 가능, 뒤 owned 수집 오류 | 수집 준비 단계 오류가 overlap보다 먼저 |
| OW72 | 다른 Policy의 같은 ID root를 외부에서 supplied | A1 위반. 이 private helper가 소속 진실성을 인증하지 않음 |

## 31. 미해결 문제·가정·검증 기록

**ownership/overlap 자체를 막는 미결정은 없다.** root+전체 descendant, pre-order tuple/지역 set, ID 기준 교집합, 하나의 overlap prefix, canonical pair·최소 ID 증거, fail-fast와 all-roots-first, private API/A1 경계를 확정했다. RuleTreeIndex/ResolvedBinding/전용 오류 모델은 필수가 아니다.

후속 과제는 unmapped/전체 결합의 실행 API·오류 순서, 구조 검증을 지문 준비/기존 matching과 연결할 orchestration이다. 새 CoverageResult/FULL/SLICE 계약은 이번에 설계하지 않는다. 공식 ResidenceHistory 의미는 **OFFICIAL_INQUIRY_REQUIRED**로 별도 보류한다.

작업 전 actual releases 제외 backend/tests/data/docs126개 파일 SHA256과 actual release6개 파일의 경로/길이/수정시각을 기록했다. 기준 전체 pytest는 **4692 passed in 12.27s**다. 신규 실행 테스트·기대값 변경은 없으며 수동72개 사례를 실행 검증으로 세지 않는다. 실제 release의 기존 ID만 설명에 참고했고 새 실제 ownership/Binding/검토/지문을 생성하지 않았다.

최종 대조에서 기존126개 파일의 SHA256이 모두 동일하며 수정·삭제는 없다. 추가는 이 문서 하나뿐이다. actual release6개 파일의 경로/길이/수정시각도 기준선과 같다. 코드/helper placeholder·기존 테스트/기대값·실제 데이터·SHA 선언은 변경하지 않았다. 문서의1~33절과 OW01~OW72가 각각 순서대로 유일하게 존재하고 code fence가 닫혀 있음을 확인했다. 한국어 표기와 기존 root resolver/모델/ID 유일성/matcher/지문·Cashflow·ResidenceHistory 자료 유지도 확인했다. 문서만 추가했으므로 기존4692개 실행 테스트의 기준선은 그대로다.

## 32. 후속 단계 추천

| 단계 | 단일 승인 작업 | 포함하지 않을 것 |
|---|---|---|
| 바로 다음 | collector + resolved pair no-overlap validator 두 private helper와 합성 테스트 | 실제 release/모델 변경, lookup orchestration, unmapped/Result |
| 다음 설계 | unmapped/전체 결합의 기존 의미를 실행 계약으로 구체화 | 소유 non-overlap만으로 완료 상태 생성 |
| 이후 구현 | 승인된 unmapped/결합 검사만 구현 | review gate/최종 결과까지 일괄 확장 |
| 이후 별도 설계 | root resolution→ownership→나머지 구조→지문 준비→기존 matcher의 호출 연결 | 이번 helper 성공을 전체 구조 실행으로 주장 |

지역 수집값 재사용이 실제로 필요할 때만 index/내부 helper 분할을 다시 검토한다. CoverageResult 설계는 필요한 구조 기반을 검증한 이후 별도 승인 작업으로 남긴다. 이 표는 여러 단계를 이번에 구현하라는 승인이 아니다.

## 33. 최종 판단

**READY_TO_IMPLEMENT_COVERAGE_OWNERSHIP**

다음 가장 작은 작업 한 개는 **coverage_ownership.py의 _collect_owned_rule_ids와 _validate_binding_ownership_no_overlap을 합성 테스트와 함께 구현**하는 것이다. root+descendants와 교집합/고정 오류 계약까지만 구현한다. 외부에서 준비한 resolved pair의 정확한 내부 호출 계약을 유지하며 상위 lookup/orchestration·unmapped·CoverageResult를 함께 구현하지 않는다.

IMPLEMENTED: 기존 모델/Rule Root Resolver/Review resolver·matcher/지문 utility는 현 상태 유지. 이번에는 이 설계 문서 하나만 추가했다.

NOT IMPLEMENTED: ownership collector/overlap validator 코드, RuleTreeIndex/ResolvedBinding, unmapped·전체 결합/통합 structural validator, CoverageResult/FULL/SLICE 새 계약·파생, 최종 Coverage validator, Acceptance/Benefit Bridge. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

## 34. M2.28 — IMPLEMENTED: ownership collection / no-overlap validation

### API와 Source of Truth 적용

backend/policy_engine/policy_data/coverage_ownership.py에 두 private 함수만 추가했다. package public export와 기존 root resolver/모델/ID 검증/walk_nodes/matcher/지문 utility는 변경하지 않았다.

```python
_collect_owned_rule_ids(root: RuleNode) -> tuple[str, ...]
_validate_binding_ownership_no_overlap(
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> None
```

M2.28 지시문17절은 후보의 ID tuple 입력보다 명세의 다른 최종 입력 계약을 우선하도록 한다. 따라서 **승인된25절의 (Binding, 원본 RuleNode) 쌍**을 그대로 사용했다. ID tuple을 받는 병렬 API나 overload를 만들지 않았다. validator가 collector를 통해 소유 tuple을 수집하며, fabricated owned IDs를 그대로 신뢰하는 입력 경로는 없다.

### Collector

root는 exact PolicyRule/ResidentRegistrationRule/BirthDateRule/RuleGroup만 허용한다. 다른 객체/하위 타입은 INVALID_STRUCTURE_INPUT이다. 기존 walk_nodes(root)를 재사용해 root 첫 번째, children 원래 순서의 pre-order DFS로 모든 중간 group/leaf ID를 수집한다. 반환은 tuple[str,...]이고 정렬/정규화/자동 dedupe하지 않는다.

방문 node의 exact 타입을 ID 읽기 전에 확인한다. 미지원 descendant는 UNSUPPORTED_RULE_NODE, 중복 ID는 순회 중 기록한 뒤 전체 타입 검사를 끝내고 DUPLICATE_RULE_NODE_ID다. 생성자가 막는 invalid tree를 만들려고 immutable 객체/생성자를 우회하지 않았다. 이 unreachable 방어 분기는 M2.27의 수동 시나리오와 소스 검토로 확인하며 실행 테스트 통과로 주장하지 않는다.

### Validator 입력·준비 순서

1. resolved_bindings는 exact tuple, 각 entry는 exact 길이2 tuple인지 확인한다.
2. 각 entry의 Binding exact 타입, root의 exact 현재 네 타입을 **전체 검사**한다.
3. 중복 condition_id를 INVALID_STRUCTURE_INPUT으로 거부한다.
4. condition_id ASCII 오름차순으로 원본을 변경하지 않고 지역 정렬한다. root.rule_id와 Binding.rule_root_id가 다르면 INVALID_STRUCTURE_INPUT이다.
5. 정렬한 각 entry마다 collector를 한 번 호출해 tuple을 수집하고 지역 ID set으로 바꾼다. 모든 수집이 성공한 뒤 pair 검사를 시작한다.
6. canonical pair 순서로 교집합을 확인한다. 첫 실제 충돌이면 오류, 끝까지 충돌이 없으면 None이다.

ID tuple의 nonempty/exact str/비공백/root-first/내부 ID 유일성은 입력 tuple을 별도로 받지 않고 **정상 원본 node 모델과 collector 경로**로 보장한다. ID tuple/list/빈 tuple을 entry의 root 자리에 전달하면 INVALID_STRUCTURE_INPUT이다. 첫 ID가 Binding root와 같은 성질은 연결 검사와 collector의 root-first를 통해 유지한다. 기존 모델의 ID 형식 검사를 재호출하거나 임의의 ID 목록을 모델로 변환하지 않는다.

same root의 서로 다른 condition은 정상 포장이고 overlap 검사 대상이다. 같은 condition 중복/잘못된 root 연결은 포장 무결성 오류가 우선한다. 빈 resolved tuple은 None이다. 단일 entry도 타입/연결/수집 검사를 수행한 뒤 None이며 전체 구조/완료 상태를 만들지 않는다.

### Canonical 오류와 겹침

판정은 서로 다른 condition의 ID 집합 교집합이다. same root/parent-leaf/nested group/Policy-root overlap은 모두 **COVERAGE_OWNERSHIP_OVERLAP** 하나로 거부한다. siblings/deep disjoint는 이 검사에 한해 통과한다.

pair는 condition_id순의 (a,b)를 사전순으로 방문한다. (A,B)→(A,C)→(B,C)이며 입력 tuple 순서·parent 위치·tree child 순서를 첫 오류 기준으로 쓰지 않는다. 모든 충돌을 모으는 결과 모델을 만들지 않고 canonical 순서의 첫 실제 conflict에서 fail-fast한다.

JSON 메시지는14절 그대로 condition_a/rule_root_a/condition_b/rule_root_b/overlap_count/first_overlap_rule_id의 여섯 필드만 담는다. count는 해당 pair 교집합 전체 크기이고 증거는 min(overlap), 즉 원문 Unicode code point 최소 ID다. set iteration의 첫 원소를 사용하지 않는다. json.dumps(sort_keys=True, ensure_ascii=True, separators=(',', ':'))로 출력하고 prefix 뒤 ': '로 연결한다. 공백/따옴표/줄바꿈/한글 ID는 escaping하되 원래 문자열 의미를 보존한다.

PolicyDataError에 .code/.metadata나 새 subclass/Enum을 추가하지 않았다. collector 오류는 같은 예외 객체로 전파한다. 앞 pair가 겹쳐도 뒤 entry의 형식/연결/수집 오류가 있으면 준비 단계 오류가 우선하며 overlap으로 감추지 않는다.

### 책임과 신뢰 한계

직접 의존은 json/PolicyDataError/현재 RuleNode 타입·walk_nodes/ConditionBinding뿐이다. root resolver/Policy/Inventory/Coverage/Review 모델·matcher·지문 함수는 직접 import하거나 호출하지 않는다. root lookup orchestration·missing Binding·Policy/Coverage policy_id matching·unmapped·전체 결합 검증을 구현하지 않았다.

A1의 같은 현재 Policy에서 준비한 원본 root 쌍을 받는 내부 계약은 그대로다. helper만으로 root 실제 소속·모든 Binding의 누락 부재를 새로 인증하지 않는다. root lookup 전에 unknown root가 실패해야 한다는 상위 순서는 아직 미구현이며 해당 실행 검증은 후속 orchestration 단계다. ID union/OwnershipResult/CoverageResult/FULL·SLICE를 만들지 않는다.

RuleTreeIndex/ResolvedConditionBinding·영속 owned IDs·cache·I/O/시각/환경·사용자 평가/LLM은 없다. 모든 상태는 호출 지역값이고 원본 Binding/root/children/evidence refs를 변경하지 않는다. implementation_review_ref도 계산에 사용하지 않는다.

### 합성 테스트와 검증

작업 전 actual releases 제외 backend/tests/data/docs127개 파일 SHA256 및 actual release6개 파일 경로/길이/수정시각을 기록했다. 기존 전체 **4692 passed in 12.56s**다. 신규 tests/test_coverage_ownership.py는 **93 passed in 0.48s**다.

테스트는 합성 Policy와 정상 Coverage를 준비하고 기존 resolver로 얻은 root를 helper에 전달한다. leaf3종·ALL/ANY/NOT·전체 pre-order·5/12단계 nested·중간 group·root-first·원문 ID, 빈/단일/sibling/deep/3개 disjoint, same-root/ancestor/Policy-root overlap, 충돌 그래프별 모든3개 Binding 순열, ASCII pair 순서·부모/자식 root 관계·교집합 count/Unicode 최소 ID·고정 JSON/escaping을 검증했다.

또한 exact outer/entry/Binding/root·하위 타입·잘못된 arity·ID tuple 거부·중복 condition·root 연결 오류, 전체 포장/수집 우선·collector 오류 원본 전파, collector당 정상 walk1회·entry당 canonical 수집1회,100회 반복/무변경·Review ref 무관성·미매핑/빠진 condition 미검사를 검증했다. 속성 접근 가드와 외부 호출 차단으로 lookup/review/fingerprint/재검증/I/O 부재를 확인했다. 생성자가 막는 duplicate/unsupported tree 방어는 정상 생성자 거부와 소스로 확인하며 object hacking은 없다.

IMPLEMENTED: ownership collector와 root pair no-overlap validator.
NOT IMPLEMENTED: lookup/구조 orchestration, unmapped/missing Binding/전체 결합·Policy identity 검증, RuleTreeIndex/ResolvedBinding, Coverage structural result/CoverageResult/FULL·SLICE, 최종 Coverage validator, Acceptance/Benefit Bridge.

최종 판단: **READY_FOR_UNMAPPED_RULE_DESIGN**.
다음 가장 작은 작업 한 개는 **기존 모든 node/허용 전체 조합 root 원칙을 보존하며 unmapped-rule 검증의 입력·예외·오류 순서·테스트 계약을 문서화**하는 것이다. 통합 구조 orchestration/Result를 먼저 구현하지 않는다. 현재 작은 tree와 소유 교집합 계산에 index 선행이 필요할 문제는 발견되지 않았다.

실제 안산 ownership/Binding/조회 결과·검토/지문은 생성하거나 저장하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

### M2.28 최종 검증 기록

전체 pytest는 **4785 passed in 12.44s**다. 기존4692개와 신규93개가 모두 통과했다. 기존 root resolver80개, Inventory/Implementation matcher142개/257개, Review resolver63개, 결과 모델166개 및 GV01~GV15 literal digest 검증을 포함하며 기존 테스트/기대값 변경은 없다.

작업 전 기준선127개(actual releases 제외) 중125개가 SHA256까지 동일하다. 변경은 이 명세와 ARCHITECTURE.md 두 문서뿐이고 ownership 모듈/합성 테스트 두 파일을 추가했다. 삭제는 없다. 기존 root resolver/walk_nodes·Policy/Rule/Binding/Coverage·matcher/Review resolver·지문 utility·공개 export·기존 모든 테스트·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했다. actual release6개 파일의 경로/길이/수정시각도 작업 전과 같다. 실제 ownership 실행/결과 저장·새 실제 검토/지문 생성은 없으며 변경 파일의 한국어 표기를 확인했다.

