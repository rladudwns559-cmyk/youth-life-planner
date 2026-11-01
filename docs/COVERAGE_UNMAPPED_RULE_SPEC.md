# Coverage Unmapped Rule 계약 — M2.29

> 현재 구현은 35절 M2.30을 따른다. 1~34절은 M2.29 설계 기록이며, 두 private 분석 helper만 구현됐다. 오류 승격·통합 구조 검증·상태 파생은 아직 없다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 설계 전용**이다. 추가 산출물은 이 문서 하나이며 코드·테스트·기존 문서·실제 release는 변경하지 않는다. 후속 helper/API·오류 승격은 아직 구현하지 않았다.

최종 판단: **READY_TO_IMPLEMENT_UNMAPPED_RULE_ANALYSIS**. 다음 구현은 target collector와 unmapped finder의 사실 계산에 한정한다. CoverageResult/FULL_POLICY/CONDITION_SLICE 모델·통합 structural validator·독립 unmapped validator는 이번에 만들지 않는다.

## 1. 목적과 기준

현재 Policy의 실행 leaf 중 어떤 Binding의 현재 ownership에도 포함되지 않은 ID를 계산하고, 이 사실과 Binding의 미완성을 구별한다. leaf가 미매핑이라는 사실만으로 그 leaf가 특정 누락 condition의 구현인지 stray rule인지 추론하지 않는다.

Source of Truth는 이번 M2.29 지시문과 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md3~13·29·33절, POLICY_COVERAGE_SPEC.md8~12·24절, COVERAGE_OWNERSHIP_SPEC.md18~25·34절, COVERAGE_RULE_ROOT_LOOKUP_SPEC.md20·33절, COVERAGE_REVIEW_MATCHING_SPEC.md6·18·24절, COVERAGE_FINGERPRINT_SPEC.md11~15절, DATA_MODEL.md26절, ARCHITECTURE.md39~40절이다. 현재 Policy/RuleNode/세 leaf·RuleGroup/walk_nodes·ID 유일성, Inventory/Binding/Coverage, root resolver/ownership 두 helper를 확인했다.

기존 엄격한 미매핑 규칙은 “Binding 누락만 있고 tree에는 연결한 구현만 있음”을 허용해 자체로 모순되지는 않았다. 이번 지시문은 **미매핑 leaf가 남는 미완성 연결도 오류 확정 전 진단 상태로 다룰 것**을 요구하므로 계약을 명시적으로 개정한다. 대체할 기존 문장과 유지할 경계는31절에 기록한다. 조용히 예전 규칙과 새 규칙을 동시에 적용하지 않는다.

## 2. Unmapped 정의

다음 집합/tuple을 구별한다.

| 기호 | 정의 |
|---|---|
| T | 현재 Policy의 실행 leaf ID를 Policy pre-order로 모은 tuple |
| O_i | resolve된 각 Binding root의 root+전체 descendant ID 집합. group 포함 |
| O | 모든 O_i의 합집합. 호출 지역 set |
| U | T를 순회하며 O에 없는 ID만 남긴 tuple |
| R | 현재 Inventory의 REQUIRED/CONDITIONAL condition_id 집합 |
| I | 현재 Coverage의 Binding.condition_id 집합 |
| M | R−I, 즉 Binding이 없는 condition ID 집합 |

unmapped = coverage_targets − owned_all이라는 집합 의미를 유지하되 실제 반환 U의 순서는 T를 따른다. R/I/M은 leaf ID가 아닌 **condition ID**다. M과 U를 동일 집합/동일 오류로 취급하거나 서로 개수만 맞춰 자동 연결하지 않는다.

## 3. Coverage target universe

**현재 실행 predicate를 수행하는 세 exact leaf 타입의 모든 ID**를 coverage target으로 채택한다. 타입은 PolicyRule/ResidentRegistrationRule/BirthDateRule이다. 사용자 평가 결과에 따라 leaf를 제외하지 않는다. operational/설명 metadata·과거 tree·다른 Policy는 target이 아니다.

RuleGroup은 탐색을 계속해야 하는 지원 node지만 target tuple에는 넣지 않는다. predicate leaf인지 node_type 문자열로 추측하지 않고 현재 정확한 타입 목록을 사용한다. future specialized rule 지원은 별도 명시적 확장이 필요하다.

## 4. Leaf vs all-node 결정

| 후보 | 결과/문제 | 결정 |
|---|---|---|
| 모든 RuleNode를 target으로 요구 | unowned composition group이 미매핑으로 잡힘. 과거의 최상위 ALL 예외를 넘어 wrapper마다 예외가 필요 | 미채택 |
| 세 실행 leaf만 target | leaf의 mapping 사실과 group의 논리/구조 검증을 분리할 수 있음 | **채택** |

이는 M2.28 ownership의 group 포함 원칙을 바꾸는 것이 아니다. Ownership은 계속 group+descendants 전체이며, unmapped의 target universe만 leaf로 한정한다. tree/지문/평가/Review에서 group을 제거하거나 무의미하다고 선언하지 않는다.

## 5. Composition group 처리

ROOT_ALL(RESIDENT,BIRTH)에서 두 leaf를 각각 binding하면 ROOT_ALL이 unowned여도 U는 빈 tuple이다. nested ANY/NOT/ALL group도 unowned라는 이유만으로 unmapped 오류를 만들지 않는다.

group operator/전체 결합의 적합성은 별도 구조 계약과 구현 검토 책임이다. 이 변경만으로 기존 MVP의 “분리된 조건들의 전체 결합은 ALL” 제약을 폐기하지 않는다. 예를 들어 ANY(A,B)의 두 leaf를 별도 조건으로 binding하면 **leaf 미매핑 분석은 통과**할 수 있지만, 전체 결합 검사 또는 의미 검토에서 거부될 수 있다. Review만 있으면 기존 구조 제약도 자동 면제된다고 해석하지 않는다.

NOT(A)의 child만 binding해도 detector는 U=()를 계산한다. condition이 NOT 전체 의미를 책임져야 하는지, 해당 Binding과 전체 결합이 적합한지는 이 detector가 추론하지 않는다. 새 composition validator를 이번에 설계·구현하지 않는다.

## 6. Leaf Policy root·empty Policy

Policy.root 자체가 세 leaf 중 하나이면 그 ID가 T의 유일한 원소다. 그 root를 소유한 Binding이 있으면 U=(), 없으면 U=(root ID,)다. root 포함 검색/ownership과 같은 원칙이다.

현재 Policy는 exact RuleNode root를 요구하고 모든 RuleGroup은 비어 있지 않은 children을 요구한다. 정상 유한 tree에는 실행 leaf가 최소 하나 있어 **빈 Policy/빈 target tree는 현재 공개 생성자로 만들 수 없다.** 빈 Inventory도 기존 모델이 거부한다. 빈 Policy·항상 PASS leaf·빈 group placeholder를 새로 추가하지 않는다.

## 7. Group-root와 leaf Binding

Binding이 group root를 가리키면 ownership에 group과 모든 descendant가 들어가므로 그 아래 leaf targets는 모두 O에 포함된다. nested group도 같다. leaf Binding은 자기 leaf 하나를 O에 추가한다. Policy root Binding은 전체 tree의 모든 leaf를 덮는다.

bound group에 새 child가 추가되면 현재 ownership에서 자동 포함되어 그 child는 U에 남지 않을 수 있다. 이는 정책 의미가 올바르다는 인증이 아니다. tree/subtree 변화와 재검토는 기존 matcher·지문 계약의 독립 책임이다. 삭제된 child는 현재 T에 없으며, 과거 child Binding이 남아 있으면 먼저 root lookup 오류다.

## 8. Owned union 계산

M2.28에서 채택한 exact (ConditionBinding, 원본 RuleNode) 쌍의 tuple을 사용한다. 각 root의 _collect_owned_rule_ids(root) 결과를 호출 지역 set에 합집합한다. 반환 tuple/Binding/원본 tree를 변경하지 않는다. group IDs가 O에 들어가도 T에 없으므로 집합 차이에 문제를 만들지 않는다.

collector를 임의 leaf-only 버전으로 바꾸거나 supplied owned ID 문자열을 신뢰하는 새 API를 만들지 않는다. root당/entry당 한 번 수집하고 target마다 반복 수집하지 않는다. derived union을 Policy/Binding/Coverage 필드·global cache·새 persistent model로 저장하지 않는다.

## 9. Target ordering

T는 **root 포함 기존 walk_nodes(policy.root)의 pre-order 중 leaf만 선택한 순서**다. group은 tuple에서 제외하되 descendants 탐색을 생략하지 않는다. children의 원래 tuple 순서를 보존한다.

예: ROOT→[RULE_Z,GROUP→[RULE_A]]이면 T=(RULE_Z,RULE_A)다. ASCII 정렬은 ID 검색에는 편하지만 실제 tree 위치 순서를 잃으므로 채택하지 않는다. root/group도 포함해 전체 tree의 타입·ID 유일성 방어를 확인한 뒤 target tuple을 반환한다.

## 10. Unmapped ordering

U는 T에서 O에 속하지 않는 ID만 남긴 tuple이다. 출력 순서를 set 차집합의 iteration에 맡기지 않는다. 모두 미매핑이면 U=T, 모두 소유되면 U=()다.

현재 구조의 첫 미매핑 위치를 추적하기 위해 pre-order를 채택한다. Binding tuple 순서를 바꿔도 O가 같으므로 U는 같다. Policy children 순서가 바뀌면 T/U 순서는 그 새 tree 순서대로 달라질 수 있다. 이것은 외부 상태에 따른 비결정성이 아니다.

## 11. Missing Binding + unmapped

M≠∅이고 U≠()이면 **두 사실을 모두 유지하되 U를 즉시 구조 오류로 승격하지 않는다.** 어떤 U가 missing condition의 구현인지 추가 stray rule인지 현재 Mapping 정보로 확정할 수 없다. ID 유사성·개수·LLM으로 귀속시키지 않는다.

이는 실행 node를 안전한 구현으로 승인하거나 미매핑 진단을 삭제하는 뜻이 아니다. Mapping 미완성으로 해석을 보류하며 전체 검증 통과/정책 완료를 주장하지 않는다. 잘못된 입력·알 수 없는 condition·깨진 root·overlap·미지원 node 같은 독립 오류는 그대로 실패한다. incomplete를 모든 구조 오류의 면제 사유로 사용하지 않는다.

예: R={A,B}, tree leaf={LA,LB}, Binding={A→LA}이면 M={B}, U=(LB,)다. 기존처럼 LB를 자동 drift 오류로 확정하지 않고 연결 미완성 사실과 미매핑 사실을 함께 남긴다.

## 12. Zero Binding

현재 R은 비어 있지 않으므로 I=∅이면 M=R≠∅다. 정상 Policy의 T도 비어 있지 않아 O=∅, U=T가 된다. detector는 이 tuple을 정상 반환하며 **zero Binding 자체 또는 이 U만을 이유로 즉시 unmapped Data Error를 만들지 않는다.**

“nonempty Policy + zero bindings는 무조건 unbound 오류”라는 과거 규칙은 이번 계약에서 대체한다. 무조건 성공/완료로 바꾸는 것이 아니라 미완성 해석을 보류한다. 추가 Policy/Review 입력 오류는 면제하지 않는다. R=∅/I=∅라서 complete라는 경우는 현재 Inventory 생성자가 막으므로 공집합 완료 경로를 만들지 않는다.

## 13. All-bindings-complete 의미

정상 EligibilityCoverage에서 **M=∅, 즉 R=I**이면 Binding 표현이 complete다. REQUIRED와 CONDITIONAL을 모두 포함하며 같은 condition 중복/Inventory 밖 condition은 기존 생성자가 거부한다.

이 completeness는 condition별 root 연결이 존재한다는 구조적 표현에 한정한다. inventory 목록의 공식 완결성·implementation 의미 검토·Review MATCHED·행정 수용과 같지 않다. completeness를 외부 boolean 파라미터로 제출받거나 review 상태에서 역산하지 않는다.

## 14. Data Error 승격 조건

사실 계산과 이후 해석을 아래처럼 분리한다. 독립 입력/tree/root/ownership 오류가 없다는 전제다.

| 경우 | M | U | unmapped 관점의 확정 해석 |
|---|---|---|---|
| A. missing Binding과 미매핑 leaf가 함께 있음 | 비어 있지 않음 | 비어 있지 않음 | 즉시 오류 승격 보류. 두 사실 유지, 전체 완료 아님 |
| B. 모든 condition bound, 미매핑 leaf 남음 | 비어 있음 | 비어 있지 않음 | **COVERAGE_UNMAPPED_RULE Data Error** |
| C. 모든 condition bound, 미매핑 없음 | 비어 있음 | 빈 tuple | unmapped 검사만 통과. 다른 검증은 별도 |
| D. missing Binding 있으나 현재 tree의 미매핑 없음 | 비어 있지 않음 | 빈 tuple | Binding 표현 미완성. unmapped 오류 아님 |
| E. zero Binding + 현재 nonempty Inventory/Policy | R 전체 | T 전체 | A와 같은 보류. zero Binding 단독 오류 금지 |
| F. zero Binding인데 모든 Inventory condition bound | 성립 불가 | 해당 없음 | 빈 Inventory가 금지되어 현재 모델로 구성 불가 |

정확한 승격 조건은 **M=∅ AND len(U)>0**이다. U가 nonempty라는 한 조건만으로 오류를 내는 standalone validator는 만들지 않는다. Review가 없어도/오래돼도 M=∅에서 남는 leaf는 이 규칙대로 구조 오류 후보이며 Review 미확인이 이를 면제하지 않는다.

## 15. CONDITION_SLICE와 관계

M≠∅은 기존의 정상적인 구현 표현 미완성 사유다. U가 함께 있다는 사실만으로 이를 같은 오류로 처리하지 않는다. 향후 미완성 결과의 근거가 될 수 있으나 **이번에는 상태 Enum·CoverageResult·FULL/SLICE 계산/반환을 설계하거나 구현하지 않는다.**

U=() 역시 전체 정책 완료를 의미하지 않는다. 공식 condition 누락·Review 미확인·구현 의미 오류가 별도로 남을 수 있다. 특히 현재 partial Policy tree만으로 미매핑이 없다고 실제 정책 전체 구현을 주장하지 않는다.

## 16. REQUIRED/CONDITIONAL

두 종류 모두 R에 포함한다. 조건부 조건이 현재 사용자에게 적용되지 않는다고 Binding 의무에서 빼지 않는다. RequiredCondition에는 INFORMATIONAL이 없으며 unmapped를 위해 새 예외 종류를 만들지 않는다.

M은 Inventory condition IDs−Binding condition IDs로 상위에서 계산한다. detector는 Inventory·요구사항 종류·사용자 facts를 입력받지 않고 completeness까지 계산하지 않는다. runtime guard/evaluation을 실행해 target이나 condition을 줄이지 않는다.

## 17. Ownership precondition

상위 호출 순서는 root resolution → ownership no-overlap → unmapped analysis다. M2.28의 _validate_binding_ownership_no_overlap을 통과한 동일 resolved pair를 detector에 전달한다. overlap이 있으면 그 기존 Data Error가 먼저며 union으로 겹침을 감추지 않는다.

집합 union 자체는 겹친 범위에도 수학적으로 가능하지만, 그것이 overlap 검증을 대체하지는 않는다. finder의 내부 입력 전제를 어긴 계산 결과를 유효한 Coverage 진단으로 인증하지 않는다. 이번 문서가 미구현된 상위 순서를 실행 완료로 주장하지 않는다.

## 18. Root lookup·identity precondition

모든 Binding의 명시 root는 같은 현재 Policy에서 _resolve_rule_root로 먼저 resolve한다. missing/renamed root는 RULE_ROOT_NOT_FOUND이며 U의 항목으로 변환하지 않는다. 원본 root identity를 보존한 pair를 사용하고 finder 내부에서 lookup을 복제하지 않는다.

**Assumption A1:** resolved_bindings는 정상 EligibilityCoverage의 모든 현재 Binding을 빠짐없이 같은 정상 Policy에서 resolve한 후 non-overlap 검사를 마친 호출 지역값이다. Policy/Coverage policy_id·scope/외부 edition 연결도 상위 책임이다. private finder만으로 동일 ID를 가진 외부 node의 실제 소속을 재인증하지 않는다. 새 RuleTreeIndex/ResolvedBinding·public raw ID API는 필요하지 않다.

## 19. Review 분리

InventoryCompletenessReview는 공식 condition 목록의 완결성 주장, ImplementationBindingReview는 Binding 구현 의미·확인본 대응의 검토 metadata다. 현재 matcher는 version/지문·대상 일치성을 비교할 뿐 자동으로 의미의 정답을 증명하지 않는다.

Review MISSING/STALE/MATCHED를 detector 입력/분기 조건으로 쓰지 않는다. 미매핑 없음은 검토 완료를 인증하지 않는다. root와 ownership의 구조 오류는 Review보다 먼저 처리하며, 정상 version 변경도 깨진 현재 root를 stale로 숨기지 않는다.

## 20. Fingerprint 분리

tree/subtree 지문은 group의 operator/child 순서/기준값/근거까지 보존한다. leaf-only target은 그 지문 payload를 바꾸지 않는다. detector는 지문을 import/계산/비교하거나 같은 digest의 root를 자동 연결하지 않는다.

bound group의 child 추가/삭제 또는 subtree 이동으로 U가 그대로일 수 있어도 검토 확인본은 달라질 수 있다. 같은 version의 지문 모순/버전 변경 stale 규칙은 기존 matcher가 처리한다. tree fingerprint가 모든 semantic correctness를 대신한다는 주장도 하지 않는다.

## 21. Target collector API

후속 최소 private API는 다음과 같다. 권장 모듈은 **backend/policy_engine/policy_data/coverage_unmapped.py**다. 이번에는 파일/placeholder를 만들지 않는다.

```python
_collect_policy_coverage_target_rule_ids(policy: Policy) -> tuple[str, ...]
```

exact Policy만 허용하고 None/dict/RuleNode/하위 타입은 INVALID_STRUCTURE_INPUT PolicyDataError다. 기존 walk_nodes(policy.root)로 root 포함 전체를 순회한다. 방문 node의 exact 네 타입을 ID 접근 전에 확인하고, 세 leaf의 ID만 원래 순서로 선택한다. RuleGroup은 순회·ID 방어에는 포함하고 반환 target에는 제외한다.

전체 node IDs의 중복을 조용히 dedupe하지 않는다. UNSUPPORTED_RULE_NODE는 순회 중 타입 확인에서, DUPLICATE_RULE_NODE_ID는 전체 타입 확인 후 확정하는 기존 순서를 유지한다. group ID 중복도 leaf-only 출력이라는 이유로 무시하지 않는다. 기존 Policy/ID 생성자를 재검증/변경하거나 새 재귀 engine을 추가하지 않는다. 정상 생성자가 막는 방어 경로는 객체 훼손 테스트 없이 소스·수동 사례로 남긴다.

## 22. Unmapped finder API

```python
_find_unmapped_rule_ids(
    policy: Policy,
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> tuple[str, ...]
```

M2.28의 원본 root pair 입력을 재사용한다. 별도 caller-supplied target tuple을 받는 방식은 임의 target 누락·중복 공급 계약을 늘리므로 지금 채택하지 않는다. finder가 target collector를 한 번 호출하고 각 root의 ownership을 한 번씩 모은 뒤 O를 만들어 T에서 필터한다. 현재 작은 tree에서는 중복 traversal 최적화보다 단순한 입력 계약을 우선한다.

정확한 Policy·exact outer tuple/길이2 exact entry tuple/exact Binding·exact 네 root 타입을 받는다. 잘못된 포장·중복 condition·Binding.root ID와 supplied root ID 불일치는 INVALID_STRUCTURE_INPUT이다. 로컬 검증은 Policy 타입 → 전체 pair 포장/타입 → 중복 condition → condition_id순 root 연결 → target collector → condition_id순 ownership collector → T 필터 순서로 제안한다. 오류는 기존 PolicyDataError를 그대로 전파하고 미매핑 반환으로 덮지 않는다.

finder가 직접 overlap 검사·root lookup·policy_id/scope 대조·M 계산을 하지 않는다. A1을 전제로 하며 그 전제를 증명하는 상위 경로는 아직 없다. 반환 U는 항상 exact tuple이며 빈 resolved tuple이면 정상 Policy의 T 전체다. positive U도 사실 반환이며 **그 존재를 이유로 COVERAGE_UNMAPPED_RULE을 던지지 않는다.**

## 23. Validator API 필요성

| 선택 | 위험/장점 | 결정 |
|---|---|---|
| finder만 구현하고 completeness-aware 해석은 상위에 둠 | 사실과 판단의 경계가 명확하며 incomplete 오판을 줄임 | **채택** |
| _validate_no_unmapped_rules만 구현 | M을 모르면 incomplete도 즉시 오류로 만들 위험 | 미채택 |
| 둘 다 구현하고 complete boolean/precondition을 받음 | 잘못된 호출·boolean 선언으로 오류 승격 조건을 우회할 수 있음 | 현 단계 미채택 |

다음 구현은21~22절 두 분석 helper뿐이다. 나중의 상위 구조 검증이 정상 Coverage에서 R/I/M을 직접 파생하고14절을 적용한다. 지금 독립 validator/complete flag/상태 모델을 추가하지 않는다. 그 상위 API/최종 Result 스키마는 이번에 정하지 않는다.

## 24. Future error contract

후속 completeness-aware 해석에서 M=∅이고 U가 비어 있지 않을 때만 **COVERAGE_UNMAPPED_RULE PolicyDataError**를 사용한다. 메시지는 prefix + ': ' + **unmapped_count / first_unmapped_rule_id** 두 필드의 JSON이다. json.dumps의 sort_keys=True, ensure_ascii=True, separators=(',', ':')를 사용하도록 확정한다. 새 exception class/.code/.metadata/오류 Enum은 없다.

unmapped_count=len(U), first_unmapped_rule_id=U[0]이다. 전체 ID 목록·사용자 facts·Policy 전체 payload는 메시지에 넣지 않는다. policy_id는 오류가 발생한 상위 호출의 대상이므로 최소 메시지에 중복 추가하지 않는다. 둘 이상의 미매핑에도 같은 prefix를 사용한다.

이 오류는 아직 구현하지 않으며 다음 두 분석 helper도 발생시키지 않는다. 잘못된 입력/tree/root/ownership의 기존 오류는 completeness와 무관하게 유지한다.

## 25. Determinism·무변경·오류 순서

동일 Policy와 동일 resolved Binding 의미는 동일 T/U를 반환한다. Binding 입력 순서는 union을 바꾸지 않으므로 최종 U는 같고, 오류 전 검증/수집은 condition_id ASCII 순서로 고정한다. tree child 순서가 바뀌면 T/U는 그 새 pre-order를 반영한다.

ownership overlap은 여러 root에 걸친 unordered 교집합에서 증거를 고르므로 Unicode 최소값을 사용한다. unmapped는 하나의 Policy의 순서 있는 T에서 빠진 위치를 찾으므로 U[0]를 증거로 사용한다. 두 규칙은 목적이 다르며 동일한 sort를 억지로 적용하지 않는다.

Policy/Binding/root/children/evidence/Coverage를 변경하지 않고100회 반복해도 같은 값/오류가 나와야 한다. 현재시각/신청일·환경·파일/network/Git·사용자 평가·LLM·지문·cache에 의존하지 않는다. 모든 root/overlap 검사가 정상이라는 상위 전제를 U가 비었다는 이유로 생략하지 않는다.

## 26. Current Ansan example

로컬 release002의 기존 ID/종류만 읽어 개념적으로 참고했다. 실제 Inventory/Binding/unmapped 결과·검토 기록·지문은 생성하거나 실행/저장하지 않았다.

현재 ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE ALL 아래 resident ID ANSAN_YBI_2026_RESIDENT_AT_APPLICATION와 birth ID ANSAN_YBI_2026_Q3_BIRTH_RANGE가 있다. 향후 두 leaf를 각각 정상 Binding root로 연결하면 T=(resident,birth), O에 두 leaf가 들어가 U=()다. ROOT_ALL 자체가 owned되지 않아도 이 분석은 미매핑 오류를 만들지 않는다.

공식 정책의 전체 condition inventory·거주기간/등록분류 등의 구현/검토는 별개다. 현재 partial tree의 U=()를 실제 정책 전체 완료로 표시하지 않는다. 기존 release DRAFT/CONDITION_SLICE·SHA 선언은 변경하지 않는다.

## 27. Future ResidenceHistory example

가상 tree ROOT_ALL(CURRENT_RESIDENCE,BIRTH,DURATION_ANY(CONTINUOUS_3Y,CUMULATIVE_10Y))에서 COND_DURATION→DURATION_ANY이면 두 duration leaf가 ownership에 포함되어 U에 남지 않는다. group ID 자체는 target이 아니다.

이는 미래 구조 설명일 뿐, 기산일·기간 경계·등록상태·귀화 예외나 실제 Rule/evaluator를 구현·확정하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. placeholder·실제 Binding을 만들지 않는다.

## 28. Semantic limitations와 독립 구조 검사

U는 현재 tree의 leaf mapping 사실만 나타낸다. 어느 unbound condition이 어느 leaf에 해당하는지, group이 올바른 의미 조건인지, 공식 목록에 조건이 빠졌는지 자동 추론하지 않는다. ALL/ANY/NOT를 평가하거나 leaf들을 의미상 조건으로 재분류하지 않는다.

leaf-only 통과가 기존 전체 결합 규칙의 통과를 뜻하지 않는다. 완전한 Binding 집합의 top-level ALL/단일 의미 조건 예외 등 **별도 composition 계약은 유지**한다. 다만 미완성 Binding 집합을 전체 구현과 동일시하는 exhaustive child-set 비교는31절대로 범위를 조정해야 한다. 이 문서가 모든 새로운 group 분해를 허용하는 것은 아니다.

M≠∅에서 U를 오류로 승격하지 않는 것은 명시적 해석 보류다. stray rule이 안전하거나 missing condition 구현이 충분하다고 보증하지 않는다. Review·구조 검증·정책 수용의 다른 오류는 별개이며 결과 모델/배포 승인 흐름을 새로 추가하지 않는다.

## 29. 후속 구현 테스트 계약

이번에는 새 테스트/기대값을 작성하지 않는다. 다음에는 합성 정상 Policy/Coverage, 기존 root resolver/ownership helper로 준비한 pair를 사용한다.

| 범위 | 다음 분석 구현에서 검증할 계약 |
|---|---|
| Targets | 세 leaf 포함, ALL/ANY/NOT 제외하지만 descendant 탐색, leaf-root 포함, nested/복수 leaf pre-order |
| Finder | leaf/group/Policy-root Binding, nested 소유 union, 빈 resolved tuple→T, 단일/다수 disjoint pairs |
| Unmapped | extra sibling/deep/multiple leaf 전부 반환, 그룹 미소유만으로 반환 항목 만들지 않음 |
| Ordering | Binding 모든 순열에서 U 동일, tree child 순서 반영, set iteration 무관 |
| Current changes | bound group 새 child는 owned, 삭제 leaf는 T에서 사라짐, 이동은 현재 소속 기준, rename은 사전 lookup 오류 |
| Inputs | exact Policy/tuple/pair/Binding/root·하위 타입/잘못된 arity/중복 condition/root 연결 거부 |
| Separation | positive U도 오류 승격 없음, M·Review·facts·지문·policy_id/scope 판정 없음, lookup/overlap 중복 실행 없음 |
| Integrity |100회 결정성, 원본 Policy/Binding/tuple/node 무변경, private export/I/O/cache 부재 |

미완성/complete별 Data Error 승격과 고정 JSON은 이후 상위 해석 코드가 승인되어 구현될 때 실행 테스트한다. 이번에 미구현인 orchestration/오류 승격을 다음 detector의 테스트 통과로 주장하지 않는다. 정상 생성자가 막는 duplicate/unsupported/empty tree는 immutable hacking 없이 생성자 경계·수동 방어 시나리오로 유지한다.

## 30. 수동 시나리오 — UM01~UM84

**84개 문서상 사례이며 신규 실행 테스트가 아니다.** 별도 표시가 없으면 같은 정상 Policy/Coverage에서 root resolution과 no-overlap이 끝났다는 A1을 전제한다. “보류”는 unmapped만으로 오류를 확정하지 않는다는 뜻이며 다른 구조 검증의 성공을 뜻하지 않는다.

| ID | 사례 | 기대 |
|---|---|---|
| UM01 | atomic leaf | target 포함 |
| UM02 | resident leaf | target 포함 |
| UM03 | birth leaf | target 포함 |
| UM04 | top-level ALL | group ID는 target 제외, children 탐색 |
| UM05 | nested ANY | group 제외, 모든 branch leaf 포함 |
| UM06 | NOT group | group 제외, child leaf 포함 |
| UM07 | Policy.root가 leaf | 해당 ID가 유일 target |
| UM08 | direct leaf Binding | 그 leaf는 U에 없음 |
| UM09 | group-root Binding | 모든 subtree leaf는 U에 없음 |
| UM10 | nested group Binding | nested 소유 범위의 모든 leaf covered |
| UM11 | multiple sibling Bindings | owned union으로 각 leaf covered |
| UM12 | Policy-root Binding | 전체 target covered, 다른 검증 별도 |
| UM13 | extra sibling leaf | U에 포함; 승격은 M에 따름 |
| UM14 | deep extra leaf | 깊이와 무관하게 U에 포함 |
| UM15 | 여러 미매핑 leaf | 전체 tuple을 Policy pre-order로 반환 |
| UM16 | Binding 없음 | U=T, detector는 오류 승격 안 함 |
| UM17 | missing condition 하나와 U 하나 | 두 사실 유지, 즉시 오류 보류 |
| UM18 | 여러 missing conditions와 U 여러 개 | 개수로 자동 귀속하지 않고 보류 |
| UM19 | missing Binding 있으나 U=() | 표현 미완성, unmapped 오류 없음 |
| UM20 | zero Binding+nonempty Inventory | M=R/U=T, unmapped 오류 보류 |
| UM21 | R=I/U=() | unmapped 검사만 통과 |
| UM22 | R=I/U에 leaf 하나 | 후속 해석의 COVERAGE_UNMAPPED_RULE |
| UM23 | R=I/U에 여러 leaf | 같은 오류, count 전체·first U[0] |
| UM24 | unowned ROOT_ALL, leaf는 모두 owned | group 자체 unmapped 오류 없음 |
| UM25 | unowned nested group, leaf는 owned | 이 detector의 U=(), composition 별도 |
| UM26 | ANY child leaf들을 별도 Binding | leaf 미매핑 없음; 전체 ALL 제약/의미 검토 통과 주장 금지 |
| UM27 | NOT child leaf만 Binding | leaf 미매핑 없음; NOT 의미/전체 결합 적합성 별도 |
| UM28 | bound group에 child 추가 | 새 child도 ownership에 포함되어 U에 없을 수 있음 |
| UM29 | bound group의 child 삭제 | 현재 target에서 제외, 과거 child Binding은 먼저 lookup 확인 |
| UM30 | leaf가 다른 group으로 이동, leaf Binding 유지 | 현재 ID가 존재하면 mapped, Review 별도 |
| UM31 | Binding root rename | U 계산 전에 RULE_ROOT_NOT_FOUND |
| UM32 | declared root가 없음 | root resolver 오류가 먼저 |
| UM33 | ownership overlap 존재 | 기존 overlap 오류가 먼저, union으로 덮지 않음 |
| UM34 | tree ID 중복 | 생성자/구조 방어 오류, U로 바꾸지 않음 |
| UM35 | ROOT→[Z,GROUP→[A]], 둘 다 미매핑 | U=(Z,A), ASCII 정렬 안 함 |
| UM36 | Binding tuple 순열 변경 | U 동일 |
| UM37 | 같은 tree에 복수 미매핑100회 | 같은 전체 U와 첫 ID |
| UM38 | Review 없음 | T/U 영향 없음 |
| UM39 | Review STALE | T/U 영향 없음 |
| UM40 | Review MATCHED | T/U 영향 없음, 완료 인증 아님 |
| UM41 | 과거 tree 지문 불일치 | 지문은 detector 입력 아님 |
| UM42 | 과거 subtree 지문 불일치 | 검토 freshness는 별도 |
| UM43 | REQUIRED condition Binding 없음 | M에 포함 |
| UM44 | CONDITIONAL condition Binding 없음 | M에 똑같이 포함 |
| UM45 | 현재 사용자에게 conditional branch 비적용 | Binding 의무 면제 없음 |
| UM46 | UserProfile 변경 | T/U 변화 없음 |
| UM47 | 사용자 평가 PASS/FAIL/UNKNOWN 변화 | T/U 변화 없음 |
| UM48 | 안산 resident/birth를 각각 Binding하는 개념 예시 | T에 두 leaf, U=() 가능, 실제 결과 생성 없음 |
| UM49 | 위 예시의 ROOT_ALL 미소유 | target이 아니므로 미매핑 항목 없음 |
| UM50 | 현재 partial tree의 U=() | 공식 정책 전체 완료 주장 금지 |
| UM51 | 미래 기간 ANY group Binding | group은 target 제외, 두 leaf covered |
| UM52 | 미래 기간 children의 ownership | group Binding의 descendants로 포함; 실제 Rule 구현 없음 |
| UM53 | 모든 condition bound + RULE_EXTRA 미소유 | 후속 해석에서 Data Error |
| UM54 | complete 상태 U 길이3 | unmapped_count=3 |
| UM55 | U=(RULE_Z,RULE_A) | first_unmapped_rule_id=RULE_Z |
| UM56 | 동일 Policy/pairs100회 | 동일 T/U |
| UM57 | set iteration 순서 변화 | T 필터이므로 U 순서 동일 |
| UM58 | 호출 전후 Policy 비교 | 값/identity 유지 |
| UM59 | 호출 전후 Binding tuple 비교 | 원래 순서/객체 유지 |
| UM60 | 호출 전후 node/children/evidence 비교 | 변경 없음 |
| UM61 | target collector에 None/dict/Policy subclass | INVALID_STRUCTURE_INPUT |
| UM62 | finder의 잘못된 pair/list/root 타입 | INVALID_STRUCTURE_INPUT |
| UM63 | 빈 resolved tuple | 정상 T 전체 반환 |
| UM64 | 단일 leaf pair | 나머지 targets만 U |
| UM65 | 다수 정상 disjoint pairs | 합집합으로 U 계산 |
| UM66 | unsupported specialized node | fail-closed, 공개 생성자가 막으면 수동 방어 |
| UM67 | 미래 ResidenceHistory leaf 지원 | 명시적 타입 계약 확장 전 자동 지원 없음 |
| UM68 | ANY 아래 모든 leaf가 separately bound | leaf coverage 사실만 확인 |
| UM69 | semantic condition이 group 전체여야 하는지 | inventory/implementation 의미 검토와 독립 composition 책임 |
| UM70 | unmapped empty | FULL/수급/정책 수용의 충분조건 아님 |
| UM71 | zero Binding인데 R도 공집합이라고 주장 | 현재 Inventory 생성자가 거부, 완료 경로 없음 |
| UM72 | 빈 Policy/빈 RuleGroup 주장 | 현재 생성자로 구성 불가, placeholder 금지 |
| UM73 | 미매핑 group ID만 있고 모든 leaf owned | U=(), group 구조 검증 별도 |
| UM74 | incomplete 상태에서 leaf Binding 제거, 구현 leaf 남음 | M/U 함께 보존, 과거의 무조건 drift 오류는 대체 |
| UM75 | Binding과 해당 구현을 함께 제거, 다른 정상 tree 남음 | M≠∅/U=() 가능, 표현 미완성 |
| UM76 | missing condition 개수와 unmapped leaf 개수가 같음 | 자동 일대일 mapping 금지 |
| UM77 | 한 condition이 복수 leaf를 담당할 수 있음 | M/U 개수 동등성은 의미상 근거 아님 |
| UM78 | 현재 Policy와 Coverage policy_id가 다름 | 상위 identity 검사 책임, finder가 인증하지 않음 |
| UM79 | 외부 Policy의 같은 ID root를 supplied | A1 위반, private finder가 실제 소속 증명 안 함 |
| UM80 | 일부 resolved pair를 누락해 전달 | A1 위반, missing Binding 해석의 근거로 사용 금지 |
| UM81 | malformed tree + zero Binding | 기존 입력/tree 오류, completeness 보류로 면제 안 함 |
| UM82 | incomplete이나 overlap도 존재 | overlap은 독립 오류로 유지 |
| UM83 | 모든 Bindings 존재하나 Review 미확인+U 존재 | Review 미확인이 unmapped 구조 오류를 면제하지 않음 |
| UM84 | source/기준값 변경으로 target IDs는 그대로 | ID mapping 사실과 snapshot 검토의 결과가 다를 수 있음 |

## 31. 기존 명세 충돌·대체 범위

**이번 M2.29 지시문을 따른 명시적 개정이다.** 이번에 기존 파일을 직접 수정하지 않으므로 아래의 특정 문장/사례는 후속 설계·구현에서 이 문서가 우선한다. 이 표는 미구현 해석 계약을 대체하며 기존 실행 코드/테스트 기대값을 바꾸는 것이 아니다.

| 기존 문서·위치/문장 | 유지/대체 결론과 이유 |
|---|---|
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md11절 “모든 tree node는 ... 소유이거나 허용된 최상위 ALL 조합 root” | **unmapped target 정의로는 대체**. T는 세 실행 leaf만. 미소유 group의 구조/연산자는 독립 composition 검증·Review에서 다룸 |
| 같은11절 “그 외 ... leaf·group ... SLICE에서도 Data Error” 및4절 표의 무조건 미매핑 오류 | **대체**. group 미소유만으로 오류 없음. leaf U는 M=∅일 때만 승격하고 M≠∅이면 보류 |
| 같은11절 “bindings=()는 모든 node가 미매핑되어 오류”와33절의 빈 Binding 후속 오류 가능성 | **zero Binding만으로 무조건 오류라는 해석을 대체**. 현재 R≠∅여서 M≠∅이며 U=T 사실만 계산. 다른 구조 오류는 유지 |
| 같은11절 “Binding을 제거하고 해당 구현 node가 tree에 남아 있으면 drift 오류” | **조건부로 대체**. M≠∅이면 즉시 drift로 확정하지 않음. M=∅인데 U가 남으면 기존의 extra 구현 오류 취지 유지 |
| 같은9절의 direct child ID 집합=Binding root ID 집합, 단일 Binding의 전체 tree 모양 제한 | **전체 매핑을 판정하는 exhaustive 적용은 Binding-complete 상태로 한정**. incomplete에서 추가 미소유 leaf가 있다는 사실을 같은 결합 오류로 다시 포장해 보류 원칙을 무효화하지 않음. ALL/단일 의미 조건의 별도 operator·논리 제약 자체는 유지 |
| 같은30절 EC07(nonempty Policy+zero Binding 오류) | **대체**.14절 E의 보류로 변경. 실행 테스트가 아닌 과거 문서 사례임 |
| 같은30절 EC14(tree LA/LB/LC, Binding A/B만, LC 오류) | **분기 구체화**. R={A,B}여서 complete면 오류 유지. R에 unbound C가 있으면 U=(LC,)와 M을 보존하고 승격 보류 |
| 같은31절 요약의 무조건 미매핑 node 오류 및16절의 관련 표현 | **unmapped 부분만 새 leaf/M 경계로 해석**. 나머지 root/ownership/Review/완결성 요구는 유지하며 새 결과 모델을 정의하지 않음 |
| POLICY_COVERAGE_SPEC.md11절 “전체 조합 ALL root 외 임의 group/leaf가 없어야 ... extra rule은 SLICE에서도 Data Error” 및24절 zero Binding/unbound 원칙 | **unmapped 판정 부분을 대체**. leaf-only 탐지, complete일 때 extra leaf 오류. incomplete의 미소유 영역은 보류. 공유 구현 금지/전체 결합 의미/공식 검토 의무는 유지 |
| COVERAGE_REVIEW_MATCHING_SPEC.md6·24절의 nonempty Policy+zero bindings unbound 오류 및 관련 RM78 구조 오류 예시 | **zero Binding을 단독 오류로 보는 부분만 대체**. 실제 깨진 root/overlap/unsupported/identity 오류는 여전히 Review 전에 실패. matcher 코드·MISSING/STALE 규칙 불변 |
| COVERAGE_RULE_ROOT_LOOKUP_SPEC.md20절의 미매핑 node→후속 구조 오류와 zero Binding 관련 문장 | **후속 unmapped 해석만 본 문서로 대체**. root lookup의 존재/타입/중복/identity 책임은 불변 |
| COVERAGE_OWNERSHIP_SPEC.md19~20·34절의 기존 모든 node/ALL 예외 보존·unmapped 후속 설명 | **보존 대상으로 언급했던 unmapped universe/무조건 오류를 이번 명시적 개정으로 대체**. group 포함 ownership, overlap 금지, canonical 오류·실제 구현은 전부 유지 |
| ARCHITECTURE.md40절·M2.28 최종 보고의 “기존 모든 node/허용 조합 root 원칙 유지” 후속 제안 | **이번 분석 결론으로 supersede**. 이전 제안이 이번 target universe 검토 결과보다 우선하지 않음 |
| DATA_MODEL.md26절·실제 Coverage/Inventory/Binding 모델 | **유지**. 빈 Binding 보관, nonempty Inventory, 조건 소속/중복 검사와 모든 실제 필드 변경 없음 |

즉 과거에 “정상 incomplete는 tree도 연결한 구현만 남아 있어야 한다”고 제한했던 부분을 이번에는 완화한다. U/M이라는 사실은 남겨 두고 최종 해석을 completeness-aware 상위 단계로 옮긴다. 이 개정을 숨겨서 기존 명세와 모순된 두 규칙을 병행하지 않는다.

## 32. 미해결 문제·가정·검증 기록

**unmapped 분석 구현을 막는 미결정은 없다.** leaf targets/pre-order·owned union/정확한 root pair·M/U 분리·zero Binding·승격 경계·기존 규칙 대체를 확정했다. A1의 같은 현재 Policy·모든 pairs·no-overlap 준비는 신뢰된 내부 호출 전제이며 그 orchestration은 아직 미구현이다.

complete 상태의 독립 composition 검증, incomplete에서 exhaustive 비교를 보류하는 상위 구현 분할, 결과/진단의 영속 표현은 후속 승인 과제다. 새 group 의미를 추론하거나 Review만으로 구조 제약을 대체하는 미결정은 남기지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**로 별도 보류한다.

작업 전 actual releases 제외 backend/tests/data/docs129개 파일 SHA256과 actual release6개 파일의 경로/길이/수정시각을 기록했다. 전체 기준 pytest는 **4785 passed in 13.26s**다. 기존 코드·테스트/기대값은 변경하지 않는다. 신규 실행 테스트는 없으며 수동84개 사례를 실행 검증으로 세지 않는다. 실제 release는 기존 ID/종류 설명만 참고했고 새 분석/Binding/검토/지문을 생성하지 않았다.

최종 대조에서 기존129개 파일의 SHA256이 모두 동일하며 수정·삭제는 없다. 추가는 이 문서 하나뿐이다. actual release6개 파일의 경로/길이/수정시각도 기준선과 같다. 1~34절과 UM01~UM84가 각각 순서대로 유일하게 존재하고 code fence가 닫혀 있음을 확인했다. 코드/helper placeholder·기존 테스트/기대값·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했으며 한국어 표기도 확인했다. 문서만 추가했으므로 기존4785개 실행 테스트의 기준선은 그대로다.

## 33. 후속 구현 추천

다음 가장 작은 승인 작업은 **coverage_unmapped.py의 target collector와 finder 두 private 분석 helper 및 합성 unit tests만 구현**하는 것이다. Policy/원본 resolved pair에서 T/O/U를 계산하고 U가 존재해도 그 이유로 오류 승격하지 않는 경계를 고정한다.

_validate_no_unmapped_rules·complete boolean·M 계산·CoverageResult/상태·root lookup/overlap orchestration·최종 구조 validator는 함께 구현하지 않는다. 두 분석 helper를 검증한 후 상위에서 실제 Coverage로 completeness를 파생하고31절 개정을 적용할 호출 계약을 별도 작업으로 다룬다. RuleTreeIndex/ResolvedBinding/새 오류 모델은 필수 선행이 아니다.

## 34. 최종 판단

**READY_TO_IMPLEMENT_UNMAPPED_RULE_ANALYSIS**

이번에는 이 문서만 추가했다. 기존 root resolver·ownership collector/no-overlap validator·모델·walk_nodes·Review matcher·지문 utility·공개 export·테스트/기대값·actual releases·Cashflow·ResidenceHistory는 그대로 유지한다.

NOT IMPLEMENTED: target collector/unmapped finder 코드, completeness-aware 오류 승격·standalone validator·통합 structural orchestration, CoverageResult/FULL/SLICE 새 모델·파생, 최종 Coverage validator, Acceptance/Benefit Bridge. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 35. M2.30 — IMPLEMENTED: leaf target 수집과 unmapped 사실 분석

### API와 입력

backend/policy_engine/policy_data/coverage_unmapped.py에 다음 두 private 함수만 추가했다. 공개 export·기존 모델·root resolver·ownership 구현은 변경하지 않았다.

```python
_collect_policy_coverage_target_rule_ids(policy: Policy) -> tuple[str, ...]

_find_unmapped_rule_ids(
    policy: Policy,
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> tuple[str, ...]
```

두 함수 모두 exact Policy만 허용한다. finder의 resolved_bindings는 exact tuple, 각 entry는 길이2 exact tuple이고 exact ConditionBinding과 현재 지원 exact RuleNode를 담아야 한다. list/generator/dict/하위 타입을 자동 변환하지 않는다. 잘못된 입력은 INVALID_STRUCTURE_INPUT PolicyDataError다.

M2.29 22절에 명시된 중복 condition 검사도 적용했다. 검사 순서는 Policy 타입 → 전체 pair 포장/타입 → 중복 condition → condition_id순 Binding/root ID 연결 → target collector → condition_id순 ownership collector → target 순서 필터다. root.rule_id와 binding.rule_root_id가 다르면 입력 오류이며 정규화/재연결하지 않는다.

### Target과 소유 union

collector는 기존 walk_nodes(policy.root)를 한 번 사용해 전체 tree를 원래 pre-order로 순회한다. 각 node의 exact 네 지원 타입을 ID 접근 전에 확인한다. PolicyRule/ResidentRegistrationRule/BirthDateRule의 ID만 target tuple에 넣고 RuleGroup은 탐색·ID 중복 검사에만 포함한다. ALL/ANY/NOT 모두 descendants 탐색을 계속하며 leaf Policy root도 유일 target으로 포함한다.

전체 node의 ID를 지역 set으로 확인하고 중복은 순회 후 DUPLICATE_RULE_NODE_ID로 거부한다. 중간에 미지원 타입이 있으면 UNSUPPORTED_RULE_NODE가 먼저다. 중복을 조용히 제거하지 않는다. 현재 정상 공개 생성자가 duplicate/unsupported/빈 tree를 막으므로 해당 방어 분기를 실행하려고 immutable 객체를 훼손하거나 traversal에 비정상 node를 주입하지 않았다. 생성자 거부는 실행 검증했고, 도달 불가능한 방어 경로는 소스 검토와 기존 UM34·66·72·81 수동 사례로 유지한다.

finder는 target collector를 한 번 호출한 뒤 각 entry의 원본 root에 기존 _collect_owned_rule_ids를 한 번씩 호출한다. group을 포함한 소유 ID tuple들을 지역 set으로 합치고 target tuple 중 그 set에 없는 ID만 반환한다. set iteration·ASCII 정렬로 출력 순서를 만들지 않는다. ID의 공백·대소문자·Unicode 정규형을 보존한다. 기존 collector의 오류는 같은 예외 객체로 전파한다.

### 사실과 해석의 경계

빈 Binding은 targets 전체, 일부 Binding은 나머지 leaf IDs, 모든 target 소유는 빈 tuple을 반환한다. group-root Binding은 그 아래 모든 leaf를 소유한다. 최상위 ALL·nested ANY·NOT group 자체가 소유되지 않아도 모든 leaf가 소유되면 unmapped는 빈 tuple이다. 이 결과는 composition 적합성·목록 완결성·Review 확인·FULL을 인증하지 않는다.

**Assumption A1 유지:** 상위 caller가 같은 현재 Policy의 모든 Binding을 기존 resolver로 원본 root에 연결하고 no-overlap 검사를 완료한 pair를 전달한다. finder는 root lookup/실제 Policy 소속 identity/overlap 검사를 다시 하지 않는다. 이 전제를 입증하는 통합 orchestration은 아직 없다. helper 단독 결과를 전체 구조 검증 결과로 사용하지 않는다.

Inventory/REQUIRED/CONDITIONAL·missing condition IDs/Binding completeness를 읽거나 계산하지 않는다. positive unmapped도 ID tuple로 반환하며 COVERAGE_UNMAPPED_RULE 오류·상수·standalone validator를 추가하지 않았다. Review/matcher/지문/사용자 평가·시각/환경·파일/network/Git·cache·LLM을 사용하지 않고 입력을 변경하지 않는다. 실제 안산 데이터로 target/미매핑/Binding/검토 결과를 생성하거나 저장하지 않는다.

### 검증과 다음 단계

작업 전 기준선은 **4785 passed in 14.75s**다. 신규 tests/test_coverage_unmapped.py는 **112 passed in 0.50s**다. 합성 정상 Policy/Coverage를 만들고 기존 resolver·no-overlap helper로 준비한 pair를 사용했다.

세 leaf root, ALL/ANY/NOT·중간 group 제외·5/12/30단계 탐색, zero/single/many·leaf/group/Policy-root/nested Binding, extra/deep/multiple leaf, 미소유 composition group, ID 원문/Policy pre-order·Binding 순열 독립성, exact 입력/하위 타입·중복 condition·root 연결 오류·검증 선행을 확인했다. target 수집1회/entry당 기존 ownership 수집1회·오류 원본 전파, 현재 child 추가/삭제·leaf 이동·rename 선행 lookup 오류, 100회 결정성·값/객체/children 무변경·private API와 함수 단위 의존 경계도 확인했다. overlap이 있는 pair를 finder가 승인한다는 테스트는 없다.

IMPLEMENTED: policy coverage target collector / unmapped rule finder, 합성 테스트112개.
NOT IMPLEMENTED: missing Binding 계산·오류 승격·독립 unmapped validator·구조 orchestration·CoverageResult/FULL_POLICY/CONDITION_SLICE·전체 결합 검증·최종 Coverage validator·Acceptance/Benefit Bridge.

최종 판단: **READY_FOR_COVERAGE_STRUCTURE_ORCHESTRATION_DESIGN**.
다음 가장 작은 작업 한 개는 **기존 root resolution → no-overlap → unmapped 분석과 Inventory의 missing condition IDs를 결합하는 구조 orchestration의 입력·실행/오류 순서·해석 경계를 문서로 설계**하는 것이다. R−I와 승격 조건 M=∅ AND U≠()는 기존13~14절에 이미 있으므로 별도 completeness 모델 구현은 선행 조건이 아니다. 31절의 incomplete에서 exhaustive composition 비교 보류도 이 설계에서 명시해야 한다. 아직 validator/Result/상태 코드는 만들지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

### M2.30 최종 검증 기록

전체 pytest는 **4897 passed in 13.94s**다. 기존4785개와 신규112개가 모두 통과했다. 기존 ownership93개·root resolver80개·Inventory/Implementation matcher142개/257개·Review resolver63개/결과166개 및 fingerprint GV01~GV15 literal 검증이 포함된다. 기존 테스트·기대값 수정은 없다.

작업 전 actual releases 제외 backend/tests/data/docs130개 파일의 SHA256을 기록했다. 최종 대조에서 기존128개가 동일하고 변경은 이 명세와 ARCHITECTURE.md 두 문서뿐이다. 분석 모듈과 신규 합성 테스트 두 파일을 추가했고 삭제는 없다. 기존 엔진/모델/walk_nodes·ownership/root resolver·Review/matcher·지문 utility·공개 export·기존 테스트·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했다. actual release6개 파일의 경로/길이/수정시각도 작업 전과 같으며 실제 데이터의 새 분석/Binding/검토/지문 결과를 생성하지 않았다. 정상 생성자가 차단하는 tree의 방어 분기는 수동/소스 확인으로 명시했고, 변경 파일의 한국어 표기도 확인했다.
