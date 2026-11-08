# Coverage Structure Orchestration 계약 — M2.31

> 현재 구현은 32절 M2.32를 따른다. 1~31절은 M2.31 설계 기록이다. private 매핑 구조 분석·missing 계산·조건부 미매핑 오류 승격을 구현했으며 전체 결합 gate·지문/Review 통합·CoverageResult/최종 상태는 아직 없다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 설계 전용**이다. 이번 산출물은 이 문서 하나다. 코드·테스트·기존 문서·actual releases를 변경하지 않는다. 아래 API·오류 승격·반환 계약은 후속 구현용이며 현재 실행 경로가 아니다.

최종 판단: **READY_TO_IMPLEMENT_COVERAGE_STRUCTURE_ORCHESTRATION**. 다음 단계는 작은 private 구조 분석 함수와 합성 테스트에 한정한다. CoverageStructureAnalysis 모델·CoverageResult·FULL_POLICY/CONDITION_SLICE Enum·최종 validator·Review/지문 통합은 구현하지 않는다.

## 1. 목적과 Source of Truth

EligibilityCoverage의 condition ↔ 현재 Policy subtree 연결을 정해진 순서로 분석한다. missing Binding은 사실로 보존하고, 존재하는 mapping의 모순은 PolicyDataError로 거부한다. 미매핑 leaf의 오류 승격은 Binding 누락 유무와 결합한다.

이번 M2.31 지시문과 다음 현재 계약을 기준으로 한다. 과거 미매핑 규칙은 COVERAGE_UNMAPPED_RULE_SPEC.md31절의 명시적 대체 범위를 우선 적용한다.

| 확인 자료 | 적용 범위 |
|---|---|
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md3~13·21~29·33절 | 구조와 완결성의 구분, identity, 모델 생성자 책임, 최종 validator와의 경계 |
| POLICY_COVERAGE_SPEC.md8~12·24·35절 | R/I, 모든 조건의 구현 의무, FULL 필요조건, Coverage 구조값 |
| COVERAGE_RULE_ROOT_LOOKUP_SPEC.md15·20·33절 | exact 입력, 전체 tree 방어, 원본 root, 오류 순서 |
| COVERAGE_OWNERSHIP_SPEC.md13~20·25·34절 | group 포함 ownership, 모든 resolve 선행, canonical overlap |
| COVERAGE_UNMAPPED_RULE_SPEC.md2~25·28~31·35절 | 세 leaf target, M/U 분리, 조건부 오류 승격, 구현된 두 분석 helper |
| COVERAGE_REVIEW_MATCHING_SPEC.md6·18·22~24·28~29·41~42절 | 구조 뒤 현재 지문 공급, 단일 matcher 계약, missing Binding과 review missing 분리 |
| COVERAGE_REVIEW_CONTEXT_SPEC.md3~4·9~11·34절 | 검토 metadata의 의미와 신뢰 한계, policy/scope 결합 |
| COVERAGE_FINGERPRINT_SPEC.md7~15·19절 | Inventory 정렬과 tree child 순서의 구별, 원본 root 입력 |
| DATA_MODEL.md24~26절 / ARCHITECTURE.md28·37~41절 | 실제 모델 필드와 독립 helper의 구현 상태 |

코드의 EligibilityCoverage/ConditionInventory/ConditionBinding/RequiredCondition/ConditionRequirement, Policy/RuleNode/RuleGroup/walk_nodes, root resolver·ownership 두 helper·unmapped 두 helper·두 Review matcher를 대조했다. 공식 정책·법령의 새 해석이나 실제 Coverage 생성은 수행하지 않는다.

## 2. Structural orchestration의 역할과 한계

이번 함수의 검사는 policy identity, Binding 누락, 선언 root 존재, subtree ownership 비겹침, 실행 leaf 미매핑과 조건부 오류 승격까지다. 결과는 현재 입력 객체에 대한 **mapping 구조 분석**이다.

Inventory 공식 완결성·Implementation 의미/분기 적합성·review freshness·사용자 PASS/FAIL/UNKNOWN·Benefit Acceptance·Cashflow·LLM·최종 FULL은 다루지 않는다. 이 함수의 성공은 기존 전체 구조 계약의 모든 검사를 끝냈다는 인증이 아니다.

특히 전체 결합 ALL/단일 의미 조건 예외·Binding roots와 composition의 적합성은 별도 gate로 남는다. unowned ANY/NOT group 아래 leaf들이 전부 소유되어도 여기서는 미매핑이 없다고 계산할 수 있다. 해당 결합의 의미를 승인하지 않는다. 이 gate의 구체적인 함수/오류/후속 통합 순서는 별도 설계 대상이며, 이번 함수에 몰래 넣거나 Review MATCHED로 대체하지 않는다. incomplete에서 exhaustive root/child 집합 비교로 M2.29의 오류 보류를 우회해서도 안 된다.

## 3. 입력 API와 exact 타입

후속 최소 private API는 다음으로 확정한다. 후보 위치는 **backend/policy_engine/policy_data/coverage_structure.py**이며 이번에는 파일·placeholder를 만들지 않는다.

```python
_analyze_coverage_structure(
    coverage: EligibilityCoverage,
    policy: Policy,
) -> tuple[
    tuple[str, ...],
    tuple[tuple[ConditionBinding, RuleNode], ...],
    tuple[str, ...],
]
```

두 인자는 필수다. 반환 위치는 순서대로 missing_condition_ids, resolved_bindings, unmapped_rule_ids다. 별도 Inventory/Bindings·scope override·review_context·supplied IDs·complete boolean·지문은 받지 않는다. public 별칭/overload/옵션도 없다.

입력 검사는 coverage → policy 순서다. 각각 exact EligibilityCoverage와 exact Policy만 허용하며 하위 타입·dict·None·fake object를 자동 변환하지 않는다. 오류 메시지 계약은 다음과 같다.

- `INVALID_STRUCTURE_INPUT: coverage: 정확한 EligibilityCoverage가 필요합니다`
- `INVALID_STRUCTURE_INPUT: policy: 정확한 Policy가 필요합니다`

두 타입 검사를 끝내기 전에 내부 속성을 읽지 않는다. 누락/정의되지 않은 인자는 일반 Python TypeError다. 이미 정상 생성된 불변 도메인 객체를 받으며 생성자·__post_init__을 재실행하거나 serializer/parser로 재구성하지 않는다.

## 4. Policy identity

타입 확인 후 첫 의미 검사는 **coverage.inventory.policy_id == policy.policy_id**다. 정확한 원래 문자열로 비교하며 strip/대소문자 보정/다른 Policy 자동 검색은 없다.

불일치면 다음 고정 PolicyDataError를 사용하도록 확정한다.

`COVERAGE_POLICY_MISMATCH: Coverage와 Policy의 policy_id가 일치해야 합니다`

payload·두 ID 전체·개인정보·추가 JSON은 필요하지 않다. mismatch는 missing 계산·root resolution·overlap·unmapped·지문·Review보다 앞선다. 두 정책에 우연히 같은 rule_id가 있어도 통과시키지 않는다. 정책 이름이나 rule_version이 같다는 사실로 identity를 대신하지 않는다.

## 5. Scope 경계와 생성자 invariant

현재 Policy 필드는 policy_id/policy_name/rule_version/root/synthetic/test_only와 생성용 allow_real_data다. ApplicabilityScope·edition·quarter를 직접 갖지 않는다. **Policy와 scope를 비교하거나 생년월일 구간/현재 날짜/rule ID/version에서 추론하지 않는다.** 구조 분석 대상 scope의 유일한 원천은 coverage.inventory.scope다. 새 scope 필드·반환 중복 필드를 만들지 않는다.

**Assumption A1:** 호출자는 같은 선택 자료에 속하는 정상 불변 Coverage/Policy를 전달한다. 이 함수가 policy_id 일치는 검증하지만 실제 edition/quarter/dataset 결합까지 증명하지는 않는다. 실제 연결의 Envelope/release adapter와 Review/Context target 대조는 별도 경계다. legacy Envelope의 source/leaf 집합 계약과 데이터 형식은 유지한다.

EligibilityCoverage 생성자가 정확한 하위 모델 타입과 tuple을 요구하고, Inventory 밖 condition과 중복 Binding condition을 이미 거부한다. ConditionInventory는 nonempty/unique 조건 목록을 보장한다. 이 invariant를 신뢰하고 orchestration에서 별도 중복/unknown-condition 검사·재생성 루프를 추가하지 않는다. 기존 ownership/finder의 private pair 입력 방어는 그대로 실행되며 제거하지 않는다. 객체 훼손·순환 tree 복구는 입력 계약에 포함하지 않는다.

## 6. Missing condition IDs 계산

R은 Inventory의 모든 condition_id, I는 현재 Binding의 모든 condition_id다. M의 집합 의미는 **R−I**다. 구현에서는 I의 호출 지역 membership set을 만들고 inventory.conditions를 순회하여 I에 없는 ID를 tuple로 남긴다.

**반환 순서는 Inventory.conditions 원래 순서를 채택한다.** 예: Inventory=(COND_B,COND_A,COND_C), Binding=COND_A이면 M=(COND_B,COND_C)다. Binding tuple 순서를 바꿔도 M은 같다. set iteration으로 출력하지 않으며 ID를 정규화하거나 요구사항 개수와 leaf 개수로 대응시키지 않는다.

ASCII 정렬은 canonical 최종 보고/지문에 유리하지만 현재 목록의 검토 순서를 잃는다. 이번 private facts 전달에서는 원래 목록 순서를 보존한다. 같은 조건 내용으로 Inventory 순서 자체를 바꾸면 M tuple 순서도 바뀔 수 있다. 이는 Binding 순서 독립성과 다른 계약이다. 기존 최종 CoverageResult의 canonical 정렬 계획·Inventory fingerprint 정렬은 바꾸지 않는다. 정확한 적용 범위는28절에 명시한다.

계산 시점은 identity 확인 직후다. M은 오류나 early-return 조건이 아니며, nonempty여도 존재하는 모든 Binding의 후속 검증을 계속한다. 오류 발생 시 이 지역 M을 부분 성공 결과로 밖에 반환하지 않는다.

## 7. REQUIRED와 CONDITIONAL

둘 다 R에 포함한다. 사용자 applicability/guard의 평가로 조건을 제외하지 않는다. CONDITIONAL은 선택 구현을 뜻하지 않는다. INFORMATIONAL을 새로 추가하지 않으며 사용자 facts/PolicyEvaluation을 읽지 않는다.

condition 누락과 implementation review 누락은 다르다. M의 ID에 가상 Binding·항상 PASS/UNKNOWN rule·ImplementationReviewMatch를 만들지 않는다. 생성자가 불허하는 빈 Inventory로 공집합 완료를 만들지도 않는다.

## 8. Zero Binding

정상 Coverage.bindings=()는 유효한 입력이다. Inventory가 비어 있지 않아 M은 전체 조건 ID tuple이고, resolved pairs는 빈 tuple이다. no-overlap helper를 빈 tuple로 한 번 호출하고 finder도 빈 tuple로 한 번 호출한다. finder가 현재 tree 전체를 검사해 T 전체를 U로 반환한다.

예: Inventory=(COND_A,COND_B), Policy=ALL(RULE_A,RULE_B), Binding=()이면 M=(COND_A,COND_B), resolved=(), U=(RULE_A,RULE_B)다. **정상 incomplete facts를 반환하며 zero Binding/U 전체만을 이유로 오류 승격하지 않는다.**

빈 Binding이라고 Policy tree 검사를 생략하지 않는다. 이 경로에는 root resolver 호출이 없지만 finder의 target collector가 지원 타입과 전체 node ID 유일성을 확인한다. 정상 생성자가 막는 비정상 tree가 도달한다면 해당 tree 오류는 유지한다. 빈 Policy·group·placeholder는 추가하지 않는다.

## 9. Root resolution phase

M을 계산한 뒤 모든 제공 Binding을10절의 지역 순서로 처리한다. 각 Binding마다 기존 **_resolve_rule_root(policy, binding.rule_root_id)**를 정확히 한 번 호출하고 (현재 Binding 원본, 반환 root 원본) pair를 모은다. 별도 dict index·Persistent ResolvedBinding·전역 cache를 만들지 않는다.

**모든 제공 root resolution이 성공한 뒤에만 ownership phase로 이동한다.** 하나가 실패하면 즉시 그 예외를 전파하고 뒤 Binding을 계속 조회하거나 부분 결과를 반환하지 않는다. “모두 먼저 resolve”는 오류 뒤에도 전부 수집하라는 뜻이 아니다. 앞의 두 root가 겹칠 것 같아도 뒤 canonical Binding의 root가 없으면 root 오류가 먼저다.

현재 resolver는 요청 root를 찾아도 전체 Policy를 순회한다. 미지원 node → 전체 타입 확인 후 중복 ID → 요청 root 부재의 방어 순서를 유지한다. root ID가 삭제/rename됐으면 RULE_ROOT_NOT_FOUND이며 M·U·review stale로 낮추지 않는다. resolver의 오류 class/message/객체를 감싸지 않는다.

## 10. Canonical Binding order

coverage.bindings를 **condition_id ASCII lexical 오름차순**으로 본 지역 ordered view를 만든다. 현재 condition ID는 [A-Z0-9_]+이므로 Python 기본 문자열 정렬로 충분하다. COND_10이 COND_2보다 앞선다. locale/자연 정렬/입력 위치/root ID 순서가 아니다.

root resolution·반환 resolved pairs는 이 순서다. 기존 ownership/finder도 내부에서 같은 순서를 사용하므로 첫 root 실패와 첫 overlap 선택이 Binding 입력 순열에 영향받지 않는다. 원래 Coverage.bindings tuple·equality·to_dict 순서는 바꾸지 않는다.

여러 root가 없으면 canonical 첫 실패를 전파한다. 현재 RULE_ROOT_NOT_FOUND 메시지에 condition/root ID를 추가하지 않는다. 후속 테스트는 helper 호출 추적으로 선택 순서를 검증할 수 있다. 이를 위해 resolver 오류 모델을 바꾸지 않는다.

## 11. Ownership phase

모든 원본 pair를 exact tuple로 만든 뒤 **_validate_binding_ownership_no_overlap(resolved_bindings)**를 한 번 호출한다. zero/single pair에도 호출한다. 성공은 None이며 whole-Policy/mapping/FULL 승인으로 해석하지 않는다.

같은 leaf/group root·parent/child·ancestor group·Policy root와 내부 root 중복 소유는 기존 COVERAGE_OWNERSHIP_OVERLAP이다. M이 있어도 즉시 실패한다. existing mappings의 모순을 incomplete로 숨기지 않는다. 소유는 여전히 root와 모든 descendants·중간 group을 포함한다.

기존 helper의 포장/연결 검사·각 entry 수집·canonical pair·Unicode 최소 증거 ID·6필드 compact JSON을 바꾸지 않는다. orchestration에서 ownership collector를 직접 추가 호출하거나 overlap 알고리즘을 복제하지 않는다.

## 12. Unmapped phase

root resolution과 no-overlap 성공 후 **_find_unmapped_rule_ids(policy, resolved_bindings)**를 한 번 호출한다. 동일 pair tuple을 그대로 전달한다. 모든 현재 Binding을 같은 현재 Policy에서 원본 root로 resolve하고 no-overlap을 마쳤다는 M2.30의 전제가 이 경로에서 충족된다. 실제 scope/release의 A1 외부 전제는5절과 별개다.

T는 세 실행 leaf IDs의 pre-order, O는 각 root의 group 포함 ownership union, U는 T 중 O에 없는 ID tuple이다. leaf Policy root·group-root Binding·unowned composition group·원문 ID·child 순서의 기존 의미를 유지한다. finder를 수정하거나 내부에 root 재조회/overlap 재검사를 넣지 않는다.

orchestration이 target collector나 ownership collector를 별도로 호출해 결과를 중복 조립하지 않는다. 기존 no-overlap과 finder 각각의 내부 ownership 수집은 현재 계약상 반복될 수 있다. 작은 tree에서 허용하며 공유 mutable index/cache나 helper 리팩터링은 이번 선행 조건이 아니다.

## 13. Missing와 unmapped의 해석

독립 입력/tree/root/ownership 오류가 없다는 전제에서 다음으로 확정한다. M은 condition IDs, U는 rule IDs로 서로 다른 종류의 사실이다.

| M | U | 이번 구조 분석의 행동 |
|---|---|---|
| nonempty | nonempty | 두 tuple 보존. 미매핑 오류 승격 보류, incomplete |
| nonempty | empty | 두 tuple 보존. 현재 tree에 필요한 구현이 아직 없을 수 있는 정상 incomplete |
| empty | nonempty | COVERAGE_UNMAPPED_RULE PolicyDataError. 정상 반환 없음 |
| empty | empty | mapping 검사 범위의 완료 facts 반환. FULL·전체 composition 적합성은 별도 |

M=(COND_B,), U=(RULE_B,RULE_EXTRA)여도 각각을 어떤 condition의 구현/stray라고 확정하지 않는다. 개수·이름·위치·AI로 자동 귀속시키지 않는다. 진짜 extra처럼 보이는 leaf가 섞여도 M이 남아 있으면 모든 U를 보존하고 승격은 보류한다. 이것은 해당 leaf를 안전하다고 승인하는 뜻이 아니다.

M이 있는데 U가 없는 경우도 오류가 아니다. 예를 들어 Policy가 COND_A만 구현하고 COND_B의 구현이 아직 전혀 없으면 정확히 이 경우다. “미구현 조건마다 기존 tree에 unowned leaf가 있어야 한다”는 새 요구를 만들지 않는다.

## 14. Data Error 승격과 메시지

**M==() AND U!=()인 경우에만**, finder가 정상 반환한 뒤 orchestration이 COVERAGE_UNMAPPED_RULE을 발생시키도록 확정한다. M2.30 finder는 계속 사실 분석만 한다. 독립 _validate_no_unmapped_rules·complete flag·새 exception subclass/.code/.metadata/오류 Enum을 추가하지 않는다.

COVERAGE_UNMAPPED_RULE_SPEC.md24절 그대로 기존 PolicyDataError의 메시지는 prefix + ': ' + JSON이다. 정확히 두 필드 unmapped_count=len(U), first_unmapped_rule_id=U[0]를 담고 **json.dumps(sort_keys=True, ensure_ascii=True, separators=(',', ':'))**로 만든다. 전체 U/Policy/개인정보는 복사하지 않는다.

U=(RULE_Z,RULE_A)이면 메시지 예시는 다음과 같다. 증거는 ASCII 최소값이 아니라 현재 Policy의 첫 미매핑 위치다.

```text
COVERAGE_UNMAPPED_RULE: {"first_unmapped_rule_id":"RULE_Z","unmapped_count":2}
```

이 조건과 메시지는 이번에는 문서만 확정한다. production 오류 발생 코드·상수·placeholder는 없다. 오류가 있으면 3-tuple·부분 진단·정상 상태를 동시에 반환하지 않는다.

## 15. Structural incomplete의 의미

이번 범위의 독립 검사가 성공하고 M이 남으면 **mapping 구조에 모순을 발견하지 않았으나 표현이 미완성**이다. U가 있거나 없어도 성립한다. 추후 CONDITION_SLICE의 사유가 될 수 있지만 여기서 status·Enum·FULL/SLICE 결과를 생성하지 않는다.

root 부재·overlap·policy mismatch 같은 독립 오류는 incomplete와 공존할 수 있고 먼저 실패한다. incomplete는 그 오류의 면제나 검증 중단 조건이 아니다. 미구현 조건/미확정 의미를 사용자 UNKNOWN으로 바꾸지 않는다.

## 16. Structural mapping-complete의 의미

이번 함수의 정상 반환에서 M=()이고 U=()이면 모든 현재 Inventory condition이 실제 disjoint subtree에 연결되고 모든 현재 실행 leaf가 그 소유 union에 포함됐다는 **mapping-complete** 개념을 사용할 수 있다. 별도 STRUCTURALLY_COMPLETE status·boolean 필드를 만들지 않는다.

이것은 공식 Inventory가 모든 조건을 포함한다는 증명·전체 결합 논리 승인·완전한 evaluator 분기 구현·Review MATCHED·FULL_POLICY·정책/현금 수용과 다르다. 빈 U만으로 완료를 선언하지 않으며, 모든 Binding이 있다는 사실만으로도 완료가 아니다. 전체 구성 gate는2절과21절대로 남는다.

## 17. 전체 호출 순서와 오류 우선순위

| 순번 | phase | 실패/행동 |
|---|---|---|
| 1 | coverage exact 타입 → policy exact 타입 | INVALID_STRUCTURE_INPUT; 속성/계산 접근 전 |
| 2 | Inventory.policy_id ↔ Policy.policy_id | COVERAGE_POLICY_MISMATCH |
| 3 | M 계산·Binding 지역 canonical view | 분석 단계. missing 자체는 오류/중단 아님 |
| 4 | canonical 각 root resolve, 모든 성공 필요 | resolver의 UNSUPPORTED_RULE_NODE/DUPLICATE_RULE_NODE_ID/RULE_ROOT_NOT_FOUND 그대로 전파 |
| 5 | 준비한 전체 pair로 no-overlap 한 번 | private 입력/수집 오류 또는 COVERAGE_OWNERSHIP_OVERLAP |
| 6 | 같은 pair로 finder 한 번 | private 입력/tree/수집 오류 전파, 아니면 U |
| 7 | M empty & U nonempty 검사 | COVERAGE_UNMAPPED_RULE 승격 |
| 8 | 성공한 facts 전달 | exact (M,resolved,U) tuple |

policy mismatch + missing root는 mismatch, missing root + overlap은 root, overlap + unmapped는 overlap이 우선한다. M이 있어도 앞의 오류는 유지한다. 여러 root 오류는 canonical 첫 resolver 호출의 내부 전체 tree 방어 순서를 따른다. unsupported가 duplicate보다, duplicate가 NOT_FOUND보다 앞선다는 기존 의미는 불변이다.

zero Binding에서는 phase4의 조회 호출이 없으므로 tree 방어는 phase6에서 실행된다. 이를 보완한다며 별도 선행 tree traversal을 넣지 않는다. 이는 정상 공개 생성자가 막는 방어 상황이며 모든 phase를 무시한 새로운 전역 오류 sort를 의미하지 않는다.

사용한 오류 prefix는 INVALID_STRUCTURE_INPUT/COVERAGE_POLICY_MISMATCH/RULE_ROOT_NOT_FOUND/DUPLICATE_RULE_NODE_ID/UNSUPPORTED_RULE_NODE/COVERAGE_OWNERSHIP_OVERLAP/COVERAGE_UNMAPPED_RULE 일곱 개면 충분하다. 누락 조건 자체의 오류·새 composition 오류 분류는 만들지 않는다. 이미 생성자에서 거부된 입력은 이 함수에 도달하지 않으며 그 생성 오류까지 runtime phase의 순서로 재분류하지 않는다.

## 18. 결정성·순서·무변경

| 대상 | 확정 순서 |
|---|---|
| missing IDs | 현재 Inventory.conditions 입력 순서 |
| root 조회·resolved pairs | condition_id ASCII lexical order |
| overlap 첫 conflict | 기존 canonical condition pair, 교집합 증거는 Unicode 최소 ID |
| unmapped IDs·오류 첫 증거 | Policy target pre-order·U[0] |
| 원본 모델 equality/to_dict | 기존 tuple 순서 그대로 |

Binding 순열만 바꾸면 M·resolved의 condition/root 대응·첫 root 실패·overlap 메시지·U가 동일하다. Policy children 순서를 바꾸면 U 순서/첫 증거는 그 tree를 따른다. Inventory 순서 변경 시 M 순서가 바뀌는 별도 계약을 Binding 순서 독립성과 혼동하지 않는다.

동일 입력100회에서 같은 값·오류·원본 root identity를 보장하도록 테스트한다. Coverage/Inventory/Binding/Policy/root/children/evidence를 변경하지 않는다. 지역 tuple/set/view만 사용하며 filesystem/network/Git/env/현재시각/난수/locale/cache/LLM/평가를 사용하지 않는다.

## 19. Review matching과의 관계

**구조 분석이 예외 없이 성공한 뒤에만** 후속 지문 준비와 Review matching으로 이동한다. M이 남은 정상 incomplete도 다음 단계로 갈 수 있다. Inventory review는 현재 Inventory 한 slot, Implementation review는 **존재하는 Binding들만** 대상으로 한다. missing condition마다 가상의 match 객체를 만들지 않는다. zero Binding이면 Inventory slot은 가능하고 Implementation slot은 없다.

구조 분석 함수는 ReviewContext/ref 내용·두 matcher/Review resolver/MatchResult를 import하거나 호출하지 않는다. MISSING/STALE/MATCHED가 M/U를 바꾸거나 구조 오류를 면제하지 않는다. 존재하는 Binding의 잘못된 명시 review ref는 후속 matcher의 Data Error이며 missing implementation으로 숨기지 않는다.

단일 matcher의 정확한 계약은 COVERAGE_REVIEW_MATCHING_SPEC.md41~42절과 현재 코드 그대로다. Inventory ref=None은 유효한 Context가 있어도 INVENTORY_REVIEW_NOT_DECLARED가 우선이고, Implementation에는 현재 Policy.rule_version을 공급한다.

전체 review slots 간 세부 오류 우선순위를 이번 구조 API에서 새로 정하지 않는다. 같은 문서18절의 전체 phase 계약과41~42절의 단일 slot 실행을 실제 통합하는 문제는 final review orchestration에서 별도 확인해야 한다. 단일 matcher를 순서대로 호출하는 것만으로18절의 모든 slot identity 선행 검사를 이미 구현했다고 주장하지 않는다. 해당 후속 통합 과제는 이번 mapping 함수 구현의 선행조건이 아니다.

## 20. Fingerprint와의 관계

구조 분석 자체는 지문을 받거나 계산하지 않는다. 후속 상위 준비 계층이 구조 성공 후 **현재 Inventory 지문 한 번 → 전체 Policy Tree 지문 한 번 → canonical resolved pair별 subtree 지문 한 번**을 계산한다. 기존 M2.17~M2.19 payload/인코딩/GV01~GV15를 변경하지 않는다.

subtree 입력은 반환된 원본 root다. matcher는 supplied 현재 지문과 현재 Policy.rule_version을 받으며 지문 계산/lookup을 하지 않는다. review의 과거 지문을 현재값으로 대입하지 않는다. Context=None/Inventory ref 미선언에서도 현재 지문 준비의 오류를 숨기지 않는 기존 계약을 유지한다.

구조 실패 때는 이 후속 준비를 호출하지 않는다. 지문 계산의 실패를 review MISSING/STALE로 낮추거나 partial 결과를 만들지 않는다. rule_version 변경만으로 mapping 구조 결과는 바뀌지 않을 수 있지만 Tree 지문과 review freshness는 바뀔 수 있다.

## 21. Final validator와의 경계

책임을 다음처럼 분리한다. 아래는 **후속 계층 배치**이며 이번 실행 구현이 아니다.

```text
정상 생성된 EligibilityCoverage + Policy
  → private mapping 구조 분석 (이번 확정 계약)
     입력/identity → M → 모든 root → no-overlap → U → 조건부 오류 승격
  → 별도 전체 composition 적합성 gate (후속 설계·통합 필요)
  → 현재 Inventory / Tree / subtree 지문 준비
  → Inventory / 존재하는 Binding들의 Review matching
  → 별도 CoverageResult 및 최종 상태 파생
```

가운데 composition gate는 기존 전체 검증 원칙을 유지한다는 경계 표시다. 그 구체 API/실행 순서/오류 계약은 아직 승인되지 않았으며 현재 helper들이 제공하지 않는다. incomplete에서 exhaustive child/root equality와 단일 Binding 전체 tree 모양 제한을 보류하는 M2.29 31절을 지켜야 한다. 이 분석의 정상 반환을 그 gate 통과로 표시하지 않는다.

최종 validator만 외부 검토 Context·지문 준비·match 결과·추후 상태를 결합한다. 구조 함수에는 CoverageResult/Review/status/Acceptance/Bridge를 넣지 않는다. 최종 result 스키마와 발행/실제 release adapter도 이번에는 확정하지 않는다.

## 22. Resolved roots 재사용과 계산 비용

private 함수가 반환한 두 번째 원소는 호출 지역 (Binding, 원본 RuleNode) 쌍이다. 상위 final pipeline이 같은 현재 Coverage/Policy의 분석 결과를 즉시 사용하며 subtree 지문 계산에 root를 재사용한다. Policy/Binding을 바꿨으면 이전 pairs를 재사용하지 말고 분석을 다시 실행한다.

root 객체를 persistent domain metadata·JSON·DB·review record·최종 result에 저장하지 않는다. private return value는 메모리 전달일 뿐 snapshot serialization 계약이 아니다. 최종 결과가 필요로 하는 condition/root IDs는 추후 별도 값 표현으로 다룬다.

정책 node N개/Binding B개에서 현재 root 조회 O(N×B), ownership 및 finder는 기존 subtree 순회·overlap 비용을 그대로 가진다. no-overlap과 finder 안의 ownership 재수집을 줄이기 위해 새 index/result/cache API를 선행하지 않는다. 작은 MVP tree에서 단순한 기존 책임을 유지하고 실제 병목이 확인될 때 별도 검토한다.

## 23. Intermediate result 선택

| 선택 | 평가 | 결정 |
|---|---|---|
| immutable CoverageStructureAnalysis dataclass | 이름 있는 필드는 편하나 현재3개의 지역값에 모델/검증/직렬화 경계가 추가됨 | 지금 불필요 |
| private exact 3-tuple (M,resolved,U) | 기존 원본 pair 계약 재사용, 중복 조회·missing/U 재계산 회피, 상태 모델 없음 | **채택** |
| None 반환 후 상위 재계산 | facts 손실·중복 연산·해석 불일치 위험 | 미채택 |
| final validator 내부에만 직접 조립 | 지금 독립적으로 검증할 작은 경계를 잃고 Review/Result와 작업 범위가 합쳐짐 | 미채택 |

세 원소를 명확한 지역 이름으로 unpack하도록 문서화하고 정상 반환 타입/원소 순서를 테스트한다. 별도 persistent ResolvedBinding/분석 모델·namedtuple·새 status·properties·public serializer는 필요하지 않다. A1과 정상 불변 입력을 신뢰하는 private 인프라로 유지한다. package public export에 추가하지 않는다.

## 24. Current Ansan 개념 예시

기존 문서에 기록된 현재 release002의 개념은 ALL(resident,birth)다. 향후 공식 전체 Inventory 후보가 현재 주민등록/Q3 출생일 외 거주기간·등록분류 등을 포함하고 resident/birth만 정상 Binding되어 있다고 가정한다.

그 가정에서 두 leaf가 모두 소유되면 U는 비어 있을 수 있어도, 나머지 condition은 M에 남아 **mapping incomplete**다. 현재 tree에 거주기간 leaf가 없다는 사실만으로 추가 Data Error를 만들지 않는다. M2.29/M2.30과 일치하며 실제 정책 전체 완료를 주장할 수 없다.

이는 문서상 대입이며 **actual Inventory/Binding/분석 결과·Review·지문을 생성/실행/저장한 것이 아니다.** 공식 inventory의 최종 완결성도 이번에 확정하지 않는다. 기존 DRAFT/CONDITION_SLICE·release/SHA 선언·현금 반영 계약은 유지한다.

## 25. Future Ansan 개념 예시

공식 의미가 확정되고 필요한 모든 조건이 구현·Binding됐다는 가정 아래, 거주기간 의미 조건을 ANY(continuous_3y,cumulative_10y) 전체 root에 연결할 수 있다는 구조 예시다. group 소유에는 두 경로가 모두 포함되어 leaf target이 덮인다.

모든 condition이 bound이고 overlap/미매핑이 없으면 M=()/U=()인 mapping-complete 후보가 된다. 전체 composition 적합성·공식 Inventory/Implementation 검토·freshness가 남으므로 FULL/수급/Acceptance를 선언하지 않는다.

이 문서는 duration 산식/기산/경계·Fact/Rule/Evaluator·실제 mapping을 추가하지 않는다. **ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED**이며 공식 답변 전 구현 보류를 유지한다.

## 26. 후속 구현 테스트 계약

이번에는 신규 테스트를 작성하지 않는다. 다음 구현에서는 정상 합성 Policy/Coverage·기존 helper를 사용하고 actual releases를 계산 입력으로 사용하지 않는다.

| 범위 | 후속 실행 검증 |
|---|---|
| 입력/identity | exact 두 모델·하위 타입 거부, 양쪽 오류 우선순위, 같은 rule IDs인 다른 policy 거부, mismatch 후 호출 없음 |
| missing | zero/일부/전체 Binding·REQUIRED/CONDITIONAL·Inventory 원래 순서·Binding 순열 독립성 |
| phase | canonical root당1회, 모든 성공 뒤 no-overlap1회, 그 뒤 finder1회, 같은 원본 pair tuple 전달 |
| 해석 |13절4가지 조합, zero Binding 정상, M이 있어도 root/overlap 오류 전파, M empty/U positive만 정확한2필드 오류 |
| 오류 순서 | policy mismatch > root > overlap > unmapped promotion, 여러 root의 canonical 선택, helper 원본 예외 identity 전파 |
| 결과 전달 | exact3-tuple, pair canonical 순서, root/Binding 원본 identity, 오류 때 정상/부분 return 없음 |
| 무변경/결정성 |100회·Binding 순열·M inventory order·U pre-order·모든 원본 값/tuple/evidence 유지 |
| 책임 분리 | 지문/Review/평가/시각/env/I/O/cache 부재·private export 부재, helper 의미 불변 |

정상 생성자가 막는 duplicate/unsupported/empty tree는 frozen 객체 훼손·생성자 우회·비정상 traversal 주입으로 테스트하지 않는다. 정상 생성자 거부와 소스/수동 방어 사례를 구별한다. 올바른 입력의 phase 관찰/원본 helper 예외 전파를 검증하는 spy는 가능하다. subtree 지문 재사용·review/FULL의 실행 통합 테스트는 해당 후속 구현 승인 때 추가한다.

테스트 제약은 함수 책임에 한정한다. 같은 모듈에 미래 다른 기능이 없음을 고정하는 구조 테스트·기존 테스트/기대값 수정·Golden 재생성은 하지 않는다. 기존4897개 회귀를 유지한다.

## 27. 수동 시나리오 — SO01~SO92

**92개 문서상 계약 사례이며 신규 실행 테스트가 아니다.** 별도 표시가 없으면 같은 정책 ID의 정상 불변 입력, 세 지원 leaf·정상 Inventory·기타 독립 gate 정상이라는 가정이다. “정상”은 이번 mapping 범위의 facts 반환이며 전체 composition/Review/FULL 통과가 아니다. 오류는 PolicyDataError다.

| ID | 사례 | 기대 |
|---|---|---|
| SO01 | 정상 Coverage/Policy, 모든 roots 존재·비겹침 | M/resolved/U 정상 반환 |
| SO02 | Coverage=None/dict/fake/subclass | INVALID_STRUCTURE_INPUT coverage, 속성 접근 전 |
| SO03 | Policy=None/dict/leaf/subclass | INVALID_STRUCTURE_INPUT policy |
| SO04 | Inventory와 Policy의 ID 불일치 | COVERAGE_POLICY_MISMATCH |
| SO05 | 모든 condition Binding 존재 | M=(), 이후 구조 검사는 계속 |
| SO06 | condition 하나 누락 | 해당 ID를 M에 보존, 자체 오류 아님 |
| SO07 | condition 여러 개 누락 | 모두 Inventory 원래 순서로 보존 |
| SO08 | Binding=() | M=R 전체, resolved=(), U=T 전체, 승격 없음 |
| SO09 | REQUIRED condition 누락 | M에 포함 |
| SO10 | CONDITIONAL condition 누락 | applicability와 무관하게 M에 포함 |
| SO11 | 제공한 roots 모두 존재 | 모든 resolve 성공 후 ownership 진행 |
| SO12 | root 하나 없음 | RULE_ROOT_NOT_FOUND, 이후 phase 호출 없음 |
| SO13 | roots 여러 개 없음 | condition_id순 첫 실패 전파 |
| SO14 | tree duplicate ID | 정상 생성자가 거부, 도달 시 기존 DUPLICATE 방어; 훼손 테스트 없음 |
| SO15 | tree unsupported node | 정상 생성자가 거부, 도달 시 기존 UNSUPPORTED 방어 |
| SO16 | sibling disjoint roots | no-overlap 성공 |
| SO17 | 서로 다른 condition이 같은 root 소유 | COVERAGE_OWNERSHIP_OVERLAP |
| SO18 | parent root와 child root가 별도 Binding | overlap 오류 |
| SO19 | Policy root와 내부 root 동시 Binding | overlap 오류 |
| SO20 | missing condition도 있으나 기존 Binding overlap | incomplete로 숨기지 않고 overlap 오류 |
| SO21 | U=() | 미매핑 승격 없음; M과 다른 검토는 별도 |
| SO22 | U 한 개, M=() | COVERAGE_UNMAPPED_RULE, count=1 |
| SO23 | U 여러 개, M=() | 같은 오류, 전체 count와 U[0] |
| SO24 | zero Binding으로 U=T | M nonempty라 승격 보류 |
| SO25 | M nonempty/U nonempty | 두 facts 보존, incomplete |
| SO26 | M nonempty/U empty | 구현 자체가 아직 없을 수 있는 정상 incomplete |
| SO27 | M empty/U nonempty | 미매핑 Data Error |
| SO28 | M empty/U empty | 이번 범위 mapping-complete 개념, status 없음 |
| SO29 | Binding tuple 전체 순열 | M·resolved 대응·U·오류 선택 동일 |
| SO30 | Inventory=(B,A,C), Binding=A | M=(B,C), ASCII 재정렬 안 함 |
| SO31 | COND_Z/COND_A root 둘 다 부재 | COND_A 조회가 먼저, payload 추가 없음 |
| SO32 | 여러 overlap pair 존재 | 기존 canonical 첫 충돌 pair/JSON 그대로 |
| SO33 | T=(RULE_Z,RULE_A), 둘 다 미매핑 | U=(RULE_Z,RULE_A), sort하지 않음 |
| SO34 | 누락 조건은 있으나 현재 tree leaf 전부 소유 | M 유지/U=(), 정상 incomplete |
| SO35 | 누락 조건처럼 보이는 leaf가 미소유 | 자동 연결 없이 M/U 보존 |
| SO36 | 누락 구현 후보와 진짜 extra처럼 보이는 leaf 혼재 | 둘 다 U 보존, 귀속·승격 보류 |
| SO37 | 모든 condition bound·모든 leaf owned | mapping-complete, FULL 아님 |
| SO38 | 모든 condition bound·extra leaf 하나 | COVERAGE_UNMAPPED_RULE |
| SO39 | Review가 STALE이라는 외부 사정 | 구조 함수 입력 아님, 결과 영향 없음 |
| SO40 | Review/Context가 없음 | 구조 facts 영향 없음 |
| SO41 | 모든 Review가 MATCHED라는 외부 사정 | 구조 오류를 면제하지 않음 |
| SO42 | 과거 Tree 지문 불일치 | 구조 함수는 지문을 읽지 않음 |
| SO43 | 과거 subtree 지문 불일치 | 구조 결과와 분리, 후속 matcher 책임 |
| SO44 | 과거 Inventory 지문 불일치 | 구조 함수 입력 아님 |
| SO45 | 현재 안산 resident/birth만 정상 연결했다고 가정 | 두 leaf 소유 가능, 실제 실행 없음 |
| SO46 | Inventory 후보의 ResidenceHistory condition 미연결 | M에 남는다는 개념, 실제 Inventory 생성 없음 |
| SO47 | 위 현재 tree에서 U=() | M 때문에 mapping incomplete |
| SO48 | 미래 duration ANY group 전체 Binding 가정 | 두 기간 branch 모두 owned, 실제 Rule 추가 없음 |
| SO49 | 미래 모든 공식 condition Binding 가정 | M=(), Review와 별개 |
| SO50 | 미래 모든 target도 소유 가정 | U=(), mapping-complete 후보만 |
| SO51 | Binding 빈 tuple | root 조회0회, overlap1회, finder1회 |
| SO52 | 정상 단일 Binding | 조회1회 후 overlap/finder, 전체 완료는 M/U에 따름 |
| SO53 | 동일 policy_id, 다른 정상 객체 | identity 비교 성공, 원본 전달 |
| SO54 | 다른 policy_id인데 rule IDs는 동일 | mismatch가 먼저, 우연 연결 금지 |
| SO55 | 동일 입력100회 | 동일 facts/오류·root identity |
| SO56 | 입력 Binding 순서만 역전 | canonical 처리·반환 동일 |
| SO57 | 지역 set 내부 iteration 차이 | M/U는 원래 tuple 필터로 결정 |
| SO58 | 호출 전후 Coverage | inventory/bindings 값·identity 유지 |
| SO59 | 호출 전후 Policy | root/metadata 값·identity 유지 |
| SO60 | 호출 전후 Binding | 원래 객체/순서/ref 유지 |
| SO61 | 호출 전후 RuleNode/children/evidence | 값·identity 유지 |
| SO62 | 구조 분석 실행 | Review matcher/resolver 호출 없음 |
| SO63 | 사용자 PolicyEvaluation 결과 변화 | 구조 함수와 무관 |
| SO64 | 나이/주소/소득 등 facts 변화 | 입력 아님, M/U 변화 근거 아님 |
| SO65 | Acceptance 상태가 외부에 존재 | 구조 결과와 분리 |
| SO66 | Cashflow 결과가 외부에 존재 | 읽거나 변경하지 않음 |
| SO67 | policy mismatch + missing root | mismatch 우선 |
| SO68 | missing root + 다른 두 roots overlap | 모든 resolve 선행 원칙으로 root 오류 우선 |
| SO69 | overlap + 미매핑 leaf | overlap 우선, finder 호출 없음 |
| SO70 | incomplete + missing root | root 오류, 정상 incomplete 결과 없음 |
| SO71 | incomplete + overlap | overlap 오류, 부분 facts 반환 없음 |
| SO72 | incomplete + unmapped만 존재 | 정상 facts, 미매핑 승격 보류 |
| SO73 | 상위가 subtree 지문을 준비할 때 | 반환 root 원본 재사용, 재조회 불필요 |
| SO74 | private tuple을 DB/JSON에 저장하려 함 | persistent 계약 없음, RuleNode serialization 추가 금지 |
| SO75 | Policy에서 scope를 얻을 수 없음 | inventory.scope 유지, 추론/비교 안 함 |
| SO76 | rule_version만 바뀌고 구조/ID 동일 | mapping facts 같을 수 있음, stale는 후속 |
| SO77 | unowned top ALL, leaf는 모두 소유 | group 자체는 U에 없음 |
| SO78 | unowned nested ANY, leaf는 모두 소유 | U=() 가능, composition gate 승인 아님 |
| SO79 | 세 타입 leaf targets가 전부 owned | U=(), M·Review·전체 결합은 별도 |
| SO80 | group-root Binding | root+모든 descendants ownership 재사용 |
| SO81 | 두 API 인자 타입 모두 잘못됨 | coverage 입력 오류가 먼저 |
| SO82 | zero Binding·이론상 unsupported tree | resolver0회라도 finder의 tree 오류 유지, 수동 방어 |
| SO83 | U=(Z,A), M=() | first_unmapped_rule_id=Z, count=2, 고정2필드 JSON |
| SO84 | ID에 공백/한글/따옴표/줄바꿈 | 원문 보존, 오류 JSON만 기존 escaping |
| SO85 | Inventory 순서 자체 변경 | M 순서도 새 입력 따름; Binding 순열 독립성과 구별 |
| SO86 | ANY 두 children을 별도 조건으로 전부 연결 | mapping facts만 성공 가능, 전체 ALL 계약 검증은 별도 |
| SO87 | NOT child만 소유한 Binding | group 미소유는 U가 아님, NOT 의미 승인 없음 |
| SO88 | 구조 함수가 helper 예외를 받음 | 같은 예외를 전파, UNKNOWN/STALE로 감싸지 않음 |
| SO89 | missing condition 개수와 U 개수 일치 | 자동 일대일 mapping 금지 |
| SO90 | 구조 성공했으나 후속 지문 인코딩 실패 | 후속 단계 오류, review 정상 결과로 대체 금지 |
| SO91 | zero Binding의 후속 Review 준비 | Inventory slot 가능, Implementation slots 없음 |
| SO92 | 구조 성공했지만 complete composition gate 미검증 | 최종 구조 검증 완료/FULL 주장 금지 |

## 28. 기존 spec 충돌과 명시적 적용 범위

기존 파일은 이번에 수정하지 않는다. 다음 표가 옛 문구와 현재 계약을 연결한다. M2.29가 개정한 내용 외의 기존 모델·helper·Review/지문 계산 의미를 바꾸지 않는다.

| 기존 문구·위치 | M2.31 적용과 해결 |
|---|---|
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md11·33절, POLICY_COVERAGE_SPEC.md24절의 zero Binding이면 unbound 오류 | M2.29 12·31절의 supersede 유지. M=R/U=T 사실 반환, 다른 독립 오류는 유지 |
| 위11절/4절, POLICY_COVERAGE_SPEC.md11·24절의 미매핑이면 SLICE에서도 무조건 Data Error | M2.29 14·31절 유지. target은 세 leaf, M empty일 때만 positive U 승격 |
| COVERAGE_REVIEW_MATCHING_SPEC.md6·24절/RM78의 zero Binding 무조건 오류 | 같은 supersede 유지. zero Binding도 구조 성공 가능하며 후속 Inventory 검토 가능 |
| COVERAGE_OWNERSHIP_SPEC.md19~20·34절/ARCHITECTURE.md40절의 과거 모든 node/허용 ALL 원칙 | unmapped universe/무조건 오류만 M2.29로 대체. group 포함 ownership/overlap 의미 유지 |
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md12~13절, POLICY_COVERAGE_SPEC.md8~10절의 missing은 SLICE 사유 | 의미 유지. 이번 함수에서는 M facts로만 전달하고 SLICE Enum/Result를 만들지 않음 |
| 모든 conditions가 bound여야 FULL이라는 POLICY_COVERAGE_SPEC.md10절 | 필요조건 유지. M=()/U=()만으로 FULL에 충분하다고 바꾸지 않음 |
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md9절의 exhaustive direct children/root equality·단일 Binding 전체 모양 | M2.29 31절대로 incomplete에 exhaustive 적용 보류. 별도 전체 composition 의미 제약은 유지하며 이 mapping 함수 밖의 후속 gate로 남김 |
| 같은 문서3·16·29절의 전체 구조/결합 검증과 새 mapping 함수 이름 | 이번 성공은 제한된 mapping 분석. 전체 구조 유효성·결합 적합성까지 인증한다고 읽지 않음. 기존 최종 gate 생략 금지 |
| POLICY_COVERAGE_SPEC.md24절·ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md27절의 결과 ID canonical 정렬 | 최종 CoverageResult 정렬 계획은 유지. 새 private M tuple은 Inventory 입력 순서로 한정 확정. 최종 adapter가 필요한 canonical view를 별도로 만들 수 있으며 원본 facts를 변경하지 않음 |
| COVERAGE_REVIEW_MATCHING_SPEC.md18절의 Structure→지문→Review | 유지. 이번 mapping 범위만으로 전체 composition gate까지 실행했다고 간주하지 않음. Review slots 전체 phase와 단일 matcher 연결은 별도 후속 설계 |
| DATA_MODEL.md26절·현재 생성자의 빈 Binding/소속/중복 검사 | 그대로 신뢰. orchestration에서 재생성/광범위 invariant 복제 없음 |
| COVERAGE_UNMAPPED_RULE_SPEC.md35절·ARCHITECTURE.md41절의 아직 오류 승격/통합 없음 | 현재 구현 사실 그대로. 이번 문서는 후속 코드 계약일 뿐 구현 완료 기록으로 대체하지 않음 |

Review의 guarded version/fingerprint 오류를 새 구조 오류로 옮기거나 stale로 흡수하지 않는다. GV01~GV15·actual release/SHA·legacy Envelope/Manifest·Cashflow/Acceptance·ResidenceHistory 계약은 변경하지 않는다.

## 29. 미해결 문제·가정·현재 검증 기록

**이번 private mapping orchestration 구현을 막는 미결정은 없다.** API/정확한 입력·policy mismatch·M 순서·원본 root/canonical 처리·ownership→U·조건부 승격/오류 메시지·private3-tuple 전달을 확정했다. 별도 BindingCompleteness/CoverageStructureAnalysis 모델은 필수 선행이 아니다.

후속 최종 validator에는 다음 과제가 남는다. 현재 설계가 그 실행 해결까지 보장하지 않는다.

- 기존 전체 composition 제약의 구체 gate·오류/실행 순서 및 incomplete에서 exhaustive 비교 보류 구현.
- Review slots 전체 phase와 기존 단일 matcher들의 호출을 일관되게 연결하는 후속 review orchestration 계약.
- 최종 CoverageResult/FULL·SLICE 파생 및 실제 Envelope/release의 scope·자료 결합 adapter.
- 공식 거주기간 의미와 ResidenceHistory: OFFICIAL_INQUIRY_REQUIRED 유지.

A1의 정상 불변 입력·신뢰된 외부 자료 선택, 기존 recursive walk_nodes의 현실적인 tree 깊이 한계를 유지한다. 관련 모델/결과의 실제 검토 진실성·공식 목록 완결성을 코드가 자동 인증하지 않는다.

작업 전 actual releases 제외 backend/tests/data/docs **132개 파일 SHA256**과 actual release **6개 파일 경로/길이/수정시각**을 기록했다. 전체 기준 pytest는 **4897 passed in 12.99s**다. 신규 실행 테스트는 없고92개 수동 시나리오를 실행 테스트로 세지 않는다. 이번 변경은 새 Markdown 한 개뿐이므로 같은 실행 기준선이 적용된다. 실제 자료의 새 hash/Binding/target/unmapped/Review 결과를 생성하지 않는다.

최종 파일 대조에서 기존132개는 SHA256까지 모두 동일하고 수정·삭제가 없다. 추가는 이 문서 하나뿐이며 actual release6개 파일의 경로/길이/수정시각도 동일하다. 1~31절과 SO01~SO92가 순서대로 유일하게 존재하고 code fence3쌍이 닫혔음을 확인했다. 한국어 표기도 확인했다. 기존 코드·모델·helper·공개 export·테스트/기대값·Golden·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했다.

## 30. 추천 다음 단계와 완료조건

다음 가장 작은 작업 한 개는 **M2.32: coverage_structure.py의 private _analyze_coverage_structure(coverage, policy)와 합성 unit tests만 구현**하는 것이다. API는3절, 호출/오류 순서는17절, 해석은13~14절, 테스트는26절을 따른다.

완료조건은 exact 입력/identity 선행, Inventory 순서의 M, canonical 모든 root resolve, 원본 resolved tuple, no-overlap1회→finder1회, M empty/U positive의 정확한 오류, zero Binding 정상 facts, 입력/오류 결정성과 무변경·private export·기존4897개 회귀다. 생성자가 막는 방어 분기까지 객체 훼손으로 테스트하지 않는다.

기존 helper/모델/테스트 기대값을 변경하지 않는다. 별도 analysis model·persistent roots·composition validator·지문/Review 연결·CoverageResult/FULL/SLICE·최종 validator·실제 데이터·Acceptance/Bridge를 같이 구현하지 않는다. 최종 기능으로의 확장은 작은 구현·테스트·검증 후 별도 승인 범위로 진행한다.

## 31. 최종 판단

**READY_TO_IMPLEMENT_COVERAGE_STRUCTURE_ORCHESTRATION**

모델 추가 없이 private internal tuple로 세 사실과 원본 roots를 전달할 수 있다. 구조 모순은 phase 순서로 즉시 실패시키고, missing 자체와 incomplete에서의 positive U는 facts로 보존한다. Review/지문/최종 결과와의 경계도 유지한다.

IMPLEMENTED: 기존 Coverage 값 모델·독립 root/ownership/unmapped helpers·Review matcher·지문 utility는 현 상태 그대로다. **M2.31 산출물은 이 설계 문서 한 개다.**

NOT IMPLEMENTED: 새 structural orchestration 코드·오류 승격·missing 파생 코드·새 분석 모델·composition gate·Review/지문 통합·CoverageResult/FULL_POLICY/CONDITION_SLICE·최종 Coverage validator·Acceptance/Benefit Bridge. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 32. M2.32 — IMPLEMENTED: private structural orchestration

### API와 배치

backend/policy_engine/policy_data/coverage_structure.py에 다음 private 함수 하나만 구현했다. 별도 missing helper/분석 dataclass·persistent resolved model·serializer·공개 export는 추가하지 않았다.

```python
_analyze_coverage_structure(
    coverage: EligibilityCoverage,
    policy: Policy,
) -> tuple[
    tuple[str, ...],
    tuple[tuple[ConditionBinding, RuleNode], ...],
    tuple[str, ...],
]
```

반환 순서는 missing_condition_ids, resolved_bindings, unmapped_rule_ids다. 두 인자만 필수로 받으며 추가 옵션/ReviewContext/지문/사용자 facts/시각/상태를 받지 않는다. 원본 Binding과 Policy node를 반환하고 root 객체를 직렬화하거나 영속 저장하지 않는다.

### 실제 실행 순서

1. exact EligibilityCoverage → exact Policy를 확인한다. 다른 타입·하위 타입은3절의 INVALID_STRUCTURE_INPUT 고정 메시지로 거부한다. 타입 확인 전 내부 속성을 읽지 않는다.
2. inventory.policy_id와 policy.policy_id를 정확히 비교한다. 다르면4절의 COVERAGE_POLICY_MISMATCH이며 helper 호출 전 실패한다. ID 정규화/자동 대체·scope 추론은 없다.
3. Binding condition IDs를 지역 set에 모으고 Inventory.conditions 원래 순서로 missing tuple을 만든다. REQUIRED/CONDITIONAL 모두 포함하고 missing 때문에 검증을 중단하지 않는다. 생성자의 condition 소속·중복 invariant를 다시 구현하거나 객체를 재생성하지 않는다.
4. Binding을 condition_id ASCII 오름차순의 지역 view로 정렬하고 각 entry의 _resolve_rule_root를 한 번 호출해 원본 pair tuple을 완성한다. 하나라도 실패하면 기존 예외 그대로 전파한다. 모든 root 성공 전에 ownership을 호출하지 않는다.
5. 같은 resolved tuple로 기존 _validate_binding_ownership_no_overlap을 정확히 한 번 호출한다. zero/single pair도 호출하며 missing이 있어도 overlap은 오류다.
6. no-overlap 성공 후 같은 Policy/같은 resolved tuple로 기존 _find_unmapped_rule_ids를 정확히 한 번 호출한다. 반환 U의 Policy pre-order를 재정렬하지 않는다.
7. missing이 비고 U가 남으면14절의 COVERAGE_UNMAPPED_RULE을 발생시킨다. 그 외에는 exact (missing,resolved,U) tuple을 반환한다.

기존 root/ownership/unmapped 모듈의 의미·검증·예외 메시지는 변경하지 않았다. 모든 helper 예외는 같은 객체로 전파하며 별도 wrapping/UNKNOWN/STALE/부분 성공 반환은 없다. zero Binding에서는 resolve0회 → no-overlap1회 → finder1회로 현재 tree 검사를 유지한다.

### Missing와 미매핑 해석

| missing | unmapped | 구현 결과 |
|---|---|---|
| nonempty | nonempty | 두 tuple 보존, 정상 incomplete facts |
| nonempty | empty | 정상 incomplete facts. 현재 tree에 누락 구현이 없을 수 있음 |
| empty | nonempty | COVERAGE_UNMAPPED_RULE PolicyDataError |
| empty | empty | mapping-complete facts, FULL/전체 구조 완료는 아님 |

승격 오류는 prefix 뒤 compact JSON으로 정확히 unmapped_count/first_unmapped_rule_id만 담는다. first는 U[0]이고 json.dumps(sort_keys=True, ensure_ascii=True, separators=(',', ':'))를 사용한다. ASCII 최소 ID 선택/전체 U·payload 복제·새 exception/code Enum은 없다. 독립 unmapped validator도 만들지 않았다.

### 책임과 합성 테스트

함수의 직접 의존은 json·PolicyDataError·기존 Policy/RuleNode/Binding/Coverage 타입과 세 helper다. Review matcher/Context·지문 utility·사용자 평가·날짜/시각/env/I/O/cache·Acceptance/Cashflow를 사용하지 않는다. Policy.rule_version freshness나 scope를 추정하지 않으며 전체 composition gate를 추가하지 않았다. 정상 facts만으로 공식 목록/구현 의미·전체 결합·Review 확인·FULL을 인증하지 않는다.

작업 전 전체 기준은 **4897 passed in 13.75s**다. 신규 tests/test_coverage_structure.py는 **94 passed in 0.53s**다. 세 leaf·group/Policy-root/nested/disjoint·네 가지 M/U 조합·zero Binding·혼합 REQUIRED/CONDITIONAL·Inventory/canonical/tree 세 순서를 검증했다. 정확한 입력/하위 타입·identity mismatch·canonical missing root·root>overlap>unmapped 오류 순서·helper 호출 횟수와 같은 pair tuple 전달·예외 원본 전파·정확한 JSON/Unicode escaping을 확인했다.

현재 안산의 resident/birth 매핑은 있지만 기간 condition은 missing인 형태를 **합성 데이터로만** 검증했다. 미래 ANY group 모양도 기존 AGE atomic 두 개로만 표현하여 실제 기간 Rule/산식/evaluator를 추가하지 않았다. 두 개념 모두 실제 release를 읽어 Coverage/결과를 생성한 것이 아니다.

100회 정상/오류 반복·Binding 순열·원본 Coverage/Inventory/Binding/Policy/node/children/evidence 무변경·scope/version 무관성·생성자 재실행 부재·함수 단위 의존/공개 export 경계도 확인했다. 훼손된 tree로 방어 분기를 만들거나 기존 테스트/기대값을 수정하지 않았다. 같은 모듈의 미래 기능을 금지하는 구조 테스트는 없다.

IMPLEMENTED: private structural orchestration·missing 계산·조건부 COVERAGE_UNMAPPED_RULE 승격·합성 테스트94개.
NOT IMPLEMENTED: 전체 결합 gate·Review 통합·fingerprint orchestration·CoverageStructureAnalysis/CoverageResult·FULL_POLICY/CONDITION_SLICE·최종 Coverage validator·Acceptance/Benefit Bridge·실제 Coverage 자료.

최종 판단: **READY_FOR_COVERAGE_INTEGRATION_GATE_DESIGN**.
다음 가장 작은 작업 한 개는 **전체 결합 gate와 구조 분석·현재 지문 준비·Review matching의 책임/호출·오류 순서를 통합 gate 문서로 설계**하는 것이다. 특히2·19·21절의 composition 범위와 Review 전체 slot phase의 남은 연결 계약을 확정한 뒤 후속 구현으로 진행한다. CoverageResult로 바로 이동하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

### M2.32 최종 검증 기록

전체 pytest는 **4991 passed in 13.05s**다. 기존4897개와 신규94개가 모두 통과했다. 기존 unmapped112개·ownership93개·root resolver80개·Inventory/Implementation matcher142개/257개·Review resolver63개/결과166개 및 GV01~GV15 literal 회귀를 포함하며 기존 테스트/기대값 변경은 없다.

작업 전 actual releases 제외 backend/tests/data/docs133개 파일 SHA256을 기록했다. 최종 대조에서 기존131개는 동일하고 수정은 이 명세와 ARCHITECTURE.md 두 문서뿐이다. 새 구조 분석 모듈과 합성 테스트 두 파일을 추가했고 삭제는 없다. 기존 모델·root/ownership/unmapped helpers·Review/matcher·지문 utility·공개 export·기존 모든 테스트·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했다. actual release6개 파일의 경로/길이/수정시각도 작업 전과 같다. 실제 Inventory/Binding/구조 결과·새 실제 검토/지문을 생성하지 않았으며 변경 파일의 한국어 표기를 확인했다.
