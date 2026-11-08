# Coverage Integration Gate 계약 — M2.33

> 현재 composition 사실 분석 구현은 38절 M2.34, private findings 값 모델은 39절 M2.35, 실제 findings 수집 gate와 composition 오류 승격은 40절 M2.36을 따른다. 1~37절은 M2.33 설계 기록이다. 최신 API의 필수 인자 3개는 40절을 우선한다. CoverageResult·최종 Coverage 상태는 아직 없다.

M2.33 작성일: **2026-10-21 / Asia/Seoul**. 당시에는 **문서 설계 전용**으로 이 문서 하나만 작성했다. 아래 1~37절의 후속 구현 계획에 대한 진행 기록은 38절 이후를 따른다.

현재 최종 판단: **READY_FOR_COVERAGE_RESULT_DESIGN** (40절). M2.33 당시 판단은 READY_TO_IMPLEMENT_COVERAGE_COMPOSITION_ANALYSIS였으며 composition → findings 값 모델 → integration 순으로 구현했다. CoverageResult/FULL_POLICY/CONDITION_SLICE는 아직 만들지 않는다.

## 1. 목적과 Source of Truth

현재 leaf mapping 검사에 남아 있는 condition 경계 밖 ANY/NOT를 탐지할 최소 계약을 정하고, structure → composition → 현재 지문 → Review matching의 순서와 결과 전달을 확정한다. 실제 정책 자격·공식 조건 의미·수급·혜택 반영을 판정하지 않는다.

이번 M2.33 지시문을 우선하며 다음 문서와 현재 코드를 대조했다.

| 자료 | 확인한 계약 |
|---|---|
| COVERAGE_STRUCTURE_ORCHESTRATION_SPEC.md2·17~23·28·32절 | 현재 매핑 보장/한계, private tuple, 남은 composition/Review 순서 |
| COVERAGE_UNMAPPED_RULE_SPEC.md3~5·11~18·24·31·35절 | leaf targets, missing 시 승격 보류, 기존 문구 대체 범위 |
| COVERAGE_OWNERSHIP_SPEC.md2~6·17~19·34절 | root+전체 descendants, 원본 pair, 비겹침/기존 helper |
| COVERAGE_RULE_ROOT_LOOKUP_SPEC.md15·33절 | exact 타입·전체 tree 방어·원본 root·오류 순서 |
| COVERAGE_REVIEW_MATCHING_SPEC.md6·18·22~29·41~42절 | 현재 matcher API/분기·지문 공급·과거 전체 slot phase 순서 |
| COVERAGE_REVIEW_CONTEXT_SPEC.md3~4·9~11·34절 | 검토 주장과 machine validation의 구분, Context target |
| COVERAGE_FINGERPRINT_SPEC.md7~15·19절 | Inventory 정렬, tree/근거 순서, 지문 대상·인코딩 |
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md3·9~13·21·27·33절 | 전체 ALL 제약·과거 tree 모양 제한·생성자/validator 책임 |
| POLICY_COVERAGE_SPEC.md8~12·24절 | 의미 조건·FULL 필요조건·소속/전체 결합 |
| DATA_MODEL.md23~30절 / ARCHITECTURE.md37~42절 | 실제 값 모델/Review/구조 경로의 구현 상태 |

EligibilityCoverage/RequiredCondition/ConditionRequirement/ConditionBinding, Policy/RuleGroup/GroupOperator/세 leaf, _analyze_coverage_structure/_collect_owned_rule_ids, 세 지문 함수, 두 matcher, CoverageReviewContext/두 match 결과의 필드와 실행 책임을 확인했다. 이번에는 반례를 실제 데이터로 실행하거나 새 지문/Review/Binding을 생성하지 않는다.

## 2. Integration gate의 정확한 역할

후속 integration gate는 같은 현재 Coverage/Policy에 대해 mapping 구조·MVP 전체 결합 제한·Context target·현재 지문과 명시 Review의 대응을 확인하고, 정상적인 미완료 사실과 match outcomes를 함께 전달한다.

구조 모순/잘못된 target/깨진 명시 ref/guarded fingerprint conflict는 Data Error다. missing Binding·보류된 unmapped/composition gaps·MISSING/STALE은 사실로 보존한다. 어떤 정상 outcome도 다른 독립 오류를 숨기지 않는다.

일반 논리 동치 증명·공식 Inventory 완결성의 자동 인증·human review 진실성 검증·사용자 평가·혜택 수용·현금 계산·최종 Coverage status는 수행하지 않는다. 모든 검토가 일치해도 아직 FULL/VERIFIED/ACCEPTED를 반환하는 API가 아니다.

## 3. 현재 structure가 보장하는 것과 보장하지 않는 것

M2.32는 exact 입력, Coverage/Policy policy_id 일치, M=Inventory IDs−Binding IDs, 모든 제공 root 실존·원본 대응, ownership 비겹침을 확인한다. M이 없는데 leaf가 미매핑이면 COVERAGE_UNMAPPED_RULE이며, M이 남으면 U도 facts로 보존한다.

M=()/U=()라는 정상 반환은 **leaf mapping-complete**다. Group operator를 condition 간 관계로 검증하지 않으므로 global composition 완료와 다르다. 현재 별도 composition validator는 없다. Policy/RuleGroup 생성자는 타입·children·NOT arity·ID 유일성만, Coverage 생성자는 소속/중복 Binding만 확인한다.

fingerprint는 확인본 동일성, matcher는 선언한 검토와 현재 확인본 대응을 비교한다. 어느 현재 실행 계층도 새로운 ANY/NOT boundary split을 자체적으로 금지하지 않는다. 이 공백을 Review 상태나 leaf 수로 덮지 않는다.

## 4. Global composition gap과 소유 경계

현재 Policy tree에서 각 Binding의 root+전체 descendants를 소유 범위로 둔다. 그 밖의 RuleGroup은 condition 구현들 사이 또는 아직 미연결 영역의 composition node다. group을 따로 Binding해야 한다고 요구하지 않는다.

MVP는 **condition 경계 밖에서는 ALL만 허용**한다. ANY/NOT는 하나의 의미 조건의 소유 subtree 안에 포함되어야 한다. leaf가 모두 매핑되어도 이 제약을 독립 검사한다. ANY/NOT 아래 leaf를 이름/개수로 자동 합치거나 tree를 ALL로 바꾸지 않는다.

incomplete에서는 unowned group이 누락 조건의 예정 subtree인지 boundary 오류인지 확정할 수 없다. gap은 진단 사실이며10절의 조건부 승격을 적용한다.

## 5. ANY 분해 반례

Policy=ANY(RULE_A,RULE_B), Inventory=(COND_A,COND_B), Bindings=(A→RULE_A,B→RULE_B)이면 현재 M2.32는 M=()/U=()를 반환할 수 있다. roots는 실존하고 소유가 겹치지 않기 때문이다.

Policy의 A OR B를 상위가 condition 결과들의 A AND B로 해석하면 의미가 달라진다. 기존 evaluator는 원래 tree를 그대로 평가하므로 evaluator 자체가 OR를 AND로 바꾸는 버그라는 뜻은 아니다. **이 분해를 독립 필수 condition의 완전한 구현으로 수용하는 것이 문제**다.

이 반례에서는 ANY group이 소유 union 밖에 남아 composition gap이다. 모든 conditions가 bound이면 새 gate가 거부한다. 한 의미 조건 COND_ANY가 ANY root 전체를 소유하면 gap이 아니다. 그것이 공식 의미와 맞는지는 여전히 Inventory/Implementation 검토 책임이다.

## 6. NOT 분해 반례

Policy=NOT(RULE_A), Binding=COND_A→RULE_A이면 leaf mapping은 완료지만 negation이 condition boundary 밖에 남는다. condition의 구현을 RULE_A 자체로 설명하면 원래 NOT A를 잃는다.

unowned NOT를 gap으로 계산하고 M=()일 때 거부한다. COND_A가 NOT root 또는 그 NOT를 포함한 상위 subtree 전체를 소유하면 gap이 아니다. NOT가 두 번 중첩되어 논리적으로 상쇄돼 보이더라도 unowned NOT를 임의 생략하지 않는다. 이 gate는 동치 최적화기가 아니다.

## 7. ALL 허용 근거와 한계

ALL(RESIDENT,BIRTH)의 두 leaf를 독립 conditions에 연결하는 것은 현재 모델의 conjunctive 정책 표현과 일치한다. unowned ALL 및 **중첩 unowned ALL**은 모두 허용한다. owned ALL 내부에는 현재 허용된 어떤 ALL/ANY/NOT도 들어갈 수 있다.

정상 유한 strict tree에서 disjoint Binding subtrees를 각각 하나의 opaque condition으로 보고, 모든 leaf가 소유되며 boundary 밖 group이 전부 ALL이면 남은 연결은 그 condition들의 conjunction이다. ALL 중첩을 허용하는 이유다. 현재 3상태 ALL의 결과 결합 의미를 바꾸지 않으며 원본 tree/순서/trace/지문을 flatten하지 않는다.

이 근거는 **현재 tree의 condition 경계 형태**에 한정한다. 공식 정책이 정말 이 conjunction인지, 한 Binding이 다른 의미 조건을 부당하게 숨겼는지, 조건 내부 predicate가 정확한지는 증명하지 않는다. REQUIRED/CONDITIONAL은 구현 의무 metadata이며 Boolean AND/OR 관계를 재구성하는 연산자가 아니다.

## 8. Composition gap의 정확한 정의

O는 모든 resolved root의 기존 _collect_owned_rule_ids 결과를 합친 지역 ID set이다. G는 다음을 만족하는 RuleGroup.rule_id의 tuple이다.

1. 현재 같은 Policy의 지원 tree에 존재한다.
2. node.rule_id가 O에 없다.
3. operator가 현재 지원 **ANY 또는 NOT**다.

G는 Policy pre-order다. leaf는 대상이 아니고 ALL은 gap이 아니다. owned ANY/NOT·parent-owned nested ANY/NOT는 제외한다. 여러 gap은 전부 보존하고 ancestor가 gap이라는 이유로 descendant gap을 생략하지 않는다. ID를 정규화·ASCII sort·자동 dedupe하지 않는다.

새 node/group operator는 자동 허용하지 않는다. 현재 지원은 exact PolicyRule/ResidentRegistrationRule/BirthDateRule/RuleGroup 및 exact ALL/ANY/NOT다. 미래 지원은 명시적인 계약 확장이 필요하다. ResidenceHistory placeholder는 만들지 않는다.

## 9. Missing과 composition gap

M은 M2.32가 반환한 missing condition IDs다. integration은 이를 다시 계산하거나 외부 complete boolean으로 대체하지 않는다.

| M | G | 행동 |
|---|---|---|
| nonempty | nonempty | G와 M 보존, composition 오류 승격 보류 |
| nonempty | empty | 정상 incomplete findings, 구현이 현재 tree에 없을 수 있음 |
| empty | nonempty | COVERAGE_COMPOSITION_GAP Data Error |
| empty | empty | 이 composition 제한을 통과. Review/FULL은 별도 |

zero Binding + ANY(A,B) + Inventory=(COND_ANY)이면 M 전체·U 전체·G=(ANY root ID,)를 보존한다. ANY가 나중에 그 누락 조건의 root가 될 수 있으므로 즉시 오류가 아니다. 반대로 M이 있어도 root 부재/overlap/unsupported/잘못된 Context·Review는 기존대로 실패한다.

## 10. Composition 오류 승격

integration은 composition analysis가 정상 반환한 뒤 **M==() AND G!=()**일 때만 기존 PolicyDataError로 새 prefix **COVERAGE_COMPOSITION_GAP**을 발생시킨다. helper 자체는 M을 모르므로 승격하지 않는다. 새 exception class/Enum/.code 속성은 필요하지 않다.

메시지는 prefix + ': ' + compact JSON이며 정확히 composition_gap_count=len(G), first_composition_gap_group_id=G[0] 두 필드다. json.dumps(sort_keys=True, ensure_ascii=True, separators=(',', ':'))를 사용한다. 예:

```text
COVERAGE_COMPOSITION_GAP: {"composition_gap_count":2,"first_composition_gap_group_id":"GROUP_Z"}
```

증거는 pre-order 첫 group이며 ASCII 최소값이 아니다. 전체 gap/Policy/사용자 payload를 넣지 않는다. 실패 시 정상 findings/부분 matches를 함께 반환하지 않는다.

M2.32가 먼저 실행되므로 M=()/U positive/G positive이면 COVERAGE_UNMAPPED_RULE이 먼저다. 이 우선순위를 바꾸려고 기존 structure 함수의 승격을 분리하거나 끄지 않는다.

## 11. ConditionComposition 모델 필요성 판단

| 안 | 장점과 한계 | 결정 |
|---|---|---|
| 현재 모델 + unowned ALL만 허용 | 조건 내부 ANY/NOT를 기존 subtree로 보존하고 경계 밖 비논리적 분해를 보수적으로 제한 | **현재 MVP에 채택** |
| 별도 ConditionComposition/coverage graph | 조건 간 OR/NOT를 직접 표현할 수 있으나 두 expression tree의 정합성·평가/직렬화 비용이 증가 | 현재 필수 아님 |
| Implementation review만으로 승인 | 사람이 전체 결합을 검토할 수 있으나 matcher는 metadata/지문 대응만 검사 | 단독 대체 불가 |

ImplementationBindingReview는 실제로 subtree뿐 아니라 **전체 tree 결합도 올바르다는 검토 주장**과 전체 Tree 지문을 가진다. 이를 단순 local review라고 축소하지 않는다. 다만 현재 matcher가 그 주장의 의미적 진실성을 자동 검증하지는 않는다. InventoryCompletenessReview도 조건/예외 목록의 완결성 주장이지 machine-readable Boolean condition AST가 아니다.

condition 간 disjunction을 하나의 의미 조건으로 묶는 것이 공식 의미상 부적절한 실제 정책이 등장하면 MVP 제약 밖으로 보고 새 composition 모델을 별도 설계한다. 현재 gate를 느슨하게 하거나 ALWAYS PASS·AI 추론·임의 합병으로 처리하지 않는다.

## 12. Composition 분석 helper API

후속 최소 API와 위치를 다음으로 확정한다. **아직 미구현**이다. 권장 파일은 backend/policy_engine/policy_data/coverage_composition.py다.

```python
_find_composition_gap_group_ids(
    policy: Policy,
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> tuple[str, ...]
```

추가 옵션·Inventory/M·Context·status·지문을 받지 않는다. 모든 unowned group이 아닌 **ANY/NOT gap만** 반환한다는 이름을 사용한다. public export·별도 persistent root 모델·standalone validator는 추가하지 않는다.

입력은 exact Policy, exact outer tuple, 길이2 exact entry tuple, exact ConditionBinding과 지원 exact RuleNode다. 자동 변환/하위 타입은 거부한다. 검증 순서는 Policy → 전체 pair 포장/타입 → 중복 condition → condition_id순 Binding/root ID 연결이다. 오류 prefix/필드별 메시지는 기존 unmapped helper의 INVALID_STRUCTURE_INPUT과 동일하게 한다.

이후 walk_nodes(policy.root) **한 번**으로 전체 지원 타입·모든 node ID 유일성을 방어하고 group 후보를 pre-order로 모은다. node 타입은 ID 접근 전 확인한다. 미지원은 UNSUPPORTED_RULE_NODE, 중복은 전체 타입 확인 뒤 DUPLICATE_RULE_NODE_ID다. 정상 생성자가 차단하는 훼손/빈/중복/미지원 tree는 강제로 만들지 않는다. 미래 미지원 group operator 역시 skip하지 않고 UNSUPPORTED_RULE_NODE 계열로 fail closed하며 새 지원 때 명시적으로 확장한다.

각 root의 ownership은 canonical condition_id순으로 기존 _collect_owned_rule_ids를 entry당 한 번 호출해 지역 set에 합친다. 새 ownership traversal을 복제하지 않는다. 그 뒤 group 후보 중 O 밖 ANY/NOT의 ID만 원래 순서로 반환한다. zero pair도 현재 tree를 확인하고 모든 현재 ANY/NOT IDs를 사실로 반환한다. leaf-root Policy의 G는 빈 tuple이다.

**Assumption A1:** 같은 현재 Coverage/Policy에서 M2.32가 성공해 준 원본 resolved pairs다. helper가 root lookup/Policy 소속 identity/overlap을 다시 증명하지 않는다. composition 분석 단독 성공은 그 선행 검증 완료나 의미 적합성 인증이 아니다. 오류를 감싸지 않고 I/O/시각/평가/Review/지문/cache/입력 변경을 사용하지 않는다.

## 13. 전체 integration pipeline과 API

후속 private API 후보를 다음으로 확정한다. 이름은 최종 evaluate/validator와 구별한다. review_context는 keyword-only 필수 인자이며 None을 명시할 수 있다.

```python
_collect_coverage_integration_findings(
    coverage: EligibilityCoverage,
    policy: Policy,
    *,
    review_context: CoverageReviewContext | None,
) -> _CoverageIntegrationFindings
```

| phase | 책임 |
|---|---|
| 0 | coverage → policy → review_context exact 타입만 검사 |
| 1 | _analyze_coverage_structure 한 번: identity/M/roots/overlap/U/기존 승격 |
| 2 | _find_composition_gap_group_ids 한 번, M empty/G positive만 승격 |
| 3 | Context가 있으면 현재 Inventory와 policy_id → scope target 확인 |
| 4 | 현재 Inventory → 전체 Tree → canonical pair별 subtree 지문 준비 |
| 5 | Inventory matcher 한 번, 정상 outcome이면 계속 |
| 6 | 존재하는 canonical Binding별 Implementation matcher 한 번씩, 정상 outcome이면 계속 |
| 7 | 모든 phase 성공 시 immutable private findings 구성 |
| 이후 별도 | CoverageResult/최종 상태 설계·파생 |

phase1에서 identity를 이미 검사하므로 integration이 같은 비교/root 조회/M 계산을 별도 복제하지 않는다. 모든 인자 누락/추가 인자는 Python TypeError다. 구조 성공은 composition 통과와 다르고, 이 둘의 성공도 review-complete와 다르다.

## 14. ReviewContext 입력과 target identity

coverage/Policy는 정확한 기존 타입, review_context는 **None 또는 exact CoverageReviewContext**만 허용한다. phase0의 잘못된 값은 기존 INVALID_STRUCTURE_INPUT prefix로 거부한다. Coverage/Policy 메시지는 M2.31과 같고 Context는 `INVALID_STRUCTURE_INPUT: review_context: 정확한 CoverageReviewContext 또는 None이 필요합니다`다. 새 input 오류 종류를 늘리지 않는다.

None은 정상 미검토 입력이다. 제공된 Context는 record가 비거나 ref가 전혀 선택되지 않아도 target을 검사한다. context.policy_id == coverage.inventory.policy_id, 이어서 context.scope == inventory.scope를 정확히 비교한다. scope는 값 동등성이고 Q3/annual·edition·quarter 자동 재사용/추론은 없다.

prefix는 기존 **REVIEW_POLICY_MISMATCH / REVIEW_SCOPE_MISMATCH**를 재사용한다. integration의 고정 메시지는 각각 `REVIEW_POLICY_MISMATCH: Context와 현재 Inventory의 policy_id가 다릅니다`, `REVIEW_SCOPE_MISMATCH: Context와 현재 Inventory의 scope가 다릅니다`로 한다. record matcher의 기존 메시지는 변경하지 않는다. Context가 자신의 record 소속을 보장하는 것과 현재 Inventory에 연결되는 것은 다르다.

검사 시점은 **structure/composition 뒤, 지문/Review 앞**이다. 잘못된 input type은 phase0에서 먼저지만, 정상 타입의 Context target 오류는 root/overlap/unmapped/composition 오류보다 뒤다. 따라서 구조 모순을 review 연결 문제로 가리지 않는다. 단순 identity 비교 전에 지문을 계산하는 불필요한 비용도 피한다.

Inventory ref=None + zero Binding + 다른 대상의 empty Context가 기존 matchers만으로 조용히 통과하는 공백을 이 gate가 막는다. Context 내부 타입/record 소속/ref 유일성 생성자는 신뢰하며 재생성하거나 미참조 historical records를 삭제하지 않는다.

## 15. Current fingerprint preparation

phase1~3 성공 뒤 기존 함수로 inventory_fp=fingerprint_condition_inventory(coverage.inventory), tree_fp=fingerprint_policy_tree(policy)를 차례로 각 한 번 계산한다. 이어 canonical resolved pair마다 fingerprint_rule_subtree(root)를 한 번씩 계산한다. 모든 현재 지문 준비를 끝낸 뒤에만 matcher를 실행한다.

지역 tuple `(binding, original_root, subtree_fp)`를 같은 canonical pair 순서로 준비한다. Binding/root를 재조회하거나 root ID 문자열만으로 새 객체를 찾지 않는다. 대응 정보는 하나의 row에 묶어 별개 병렬 목록의 index 혼동을 피한다. 전역/영속 mutable dict·cache는 없다.

Context=None·Inventory ref 미선언·zero Binding에서도 Inventory/Tree 지문은 계산한다. zero Binding의 subtree 지문 호출은0회다. matcher에 형식상 hash가 필요하며 Context 부재로 현재 snapshot의 인코딩 오류를 숨기지 않는 기존 계약을 지킨다. record의 과거 지문을 현재값으로 복사하지 않는다.

지문 계산 오류는 기존 PolicyDataError 그대로 전파한다. snapshot 준비 중 실패하면 어떠한 matcher/정상 findings도 실행·반환하지 않는다. GV01~GV15·JSON/UTF-8 recipe·Inventory condition 정렬·tree children/evidence 순서·rule_version 포함 여부는 변경하지 않는다.

## 16. Inventory review matching

지문 전체가 준비되면 기존 _match_inventory_review(inventory, review_context, current_inventory_fingerprint=inventory_fp)를 정확히 한 번 호출한다. MATCHED/MISSING/STALE 모두 정상 outcome이고 뒤 Implementation slots를 계속 검사한다.

현재 matcher의 우선순위를 유지한다. ref=None은 Context 유무와 무관하게 MISSING + INVENTORY_REVIEW_NOT_DECLARED 하나다. ref가 선언되어 있고 Context=None이면 MISSING + NO_REVIEW_CONTEXT다. Context가 제공됐는데 명시 ref가 없거나 종류/대상이 잘못되면 Data Error이며 미검토로 낮추지 않는다.

integration의 phase3 target 검사는 이 matcher가 ref=None에서 target을 읽지 않는 분기를 보완한다. matcher 내부의 검증 순서/정상 사유를 바꾸는 작업은 아니다.

## 17. Implementation review matching

Inventory slot이 정상 반환하면 canonical `(binding,root,subtree_fp)` rows 순서로 기존 _match_implementation_review를 Binding당 한 번 호출한다. current_inventory_fingerprint=inventory_fp, current_rule_version=policy.rule_version, current_policy_tree_fingerprint=tree_fp, current_subtree_fingerprint=그 row의 지문을 공급한다.

현재 Inventory/Binding 원본을 전달하고 record의 과거 version/지문으로 현재값을 역산하지 않는다. policy_id/scope/condition/root·guarded version/지문 비교는 기존 matcher 그대로다. Context=None이면 존재하는 Binding의 원래 IDs/ref를 보존한 MISSING + NO_REVIEW_CONTEXT다.

Binding이 없는 condition에는 가상의 ImplementationReviewMatch를 만들지 않는다. 해당 사실은 M에만 남는다. zero Binding이면 Implementation finding tuple은 빈 tuple이다. 선택되지 않은 historical Context 기록을 최신 순서로 대체 선택하지 않는다.

## 18. 정상 Review outcomes와 수집

MATCHED/MISSING/STALE은 모두 정상 findings다. 한 slot이 MISSING/STALE이어도 다음 slot을 계속 검사하고 각 canonical reason tuple을 그대로 보존한다. Inventory missing + 여러 Implementation stale도 함께 남길 수 있다.

정상 review outcome은 mapping missing·unmapped·composition gap과 독립이다. existing reviews가 전부 MATCHED여도 missing condition이 있으면 전체 구현이 끝난 것이 아니다. Context=None이면 integration은 정상 완료할 수 있으나 후속 FULL 후보가 되지는 않는다. 여기서는 그 status를 계산하지 않는다.

## 19. Review Data Error와 slot 오류 우선순위

**한 slot을 끝까지 검사하는 기존 matcher를 순서대로 호출**한다. Inventory slot 전체 → condition_id순 각 Implementation slot 전체다. 최초 Data Error에서 fail-fast하며 이전에 모은 정상 matches/partial findings를 반환하지 않는다. 한 slot 내부의 identity → version/guarded conflict 순서는 기존 코드 그대로다.

이는 COVERAGE_REVIEW_MATCHING_SPEC.md18절의 “모든 slots의 ref/identity를 먼저 확인한 뒤 모든 slots의 content conflict 검사”와 다르므로 **이번 integration 계약에서 그 전체 slot phase 순서를 명시적으로 대체**한다. 단일 matcher 코드/테스트는 유지한다. 중복 ref preflight·matcher 내부 로직 복제·matcher 분할은 추가하지 않는다.

예: Inventory의 동일 version 지문 conflict와 Implementation의 broken ref가 함께 있으면 이제 Inventory conflict가 먼저다. 기존 전역 identity-first 문구를 적용하면 Implementation ref 오류가 먼저였을 수 있다. 또 canonical 첫 Implementation slot의 guarded conflict는 뒤 slot의 ref 오류보다 먼저다. stale/missing은 오류가 아니므로 뒤 오류 검사를 생략하지 않는 원칙은 그대로다. 이 개정은 아직 존재하지 않는 integration 경로의 우선순위만 확정한다.

## 20. Canonical ordering

| 대상 | 순서 |
|---|---|
| M | Inventory.conditions 입력 순서, 기존 structure 결과 그대로 |
| U | Policy executable leaf pre-order |
| G·composition 첫 증거 | Policy RuleGroup pre-order 중 gap 순서·G[0] |
| root/소유 수집/subtree 지문/Implementation slots·findings | condition_id ASCII lexical 오름차순 |
| Inventory/Tree 지문 준비 | Inventory 먼저, Tree 다음 |
| Review slot 오류 | Inventory 전체 먼저, canonical Implementation 전체 |

Binding 순열만 바꾸면 모든 facts·대응·오류 선택이 동일하다. Inventory 순서 자체를 바꾸면 M 순서가 달라질 수 있고, tree child 순서를 바꾸면 U/G 순서 및 tree 지문이 달라질 수 있다. 기존 모델 equality/to_dict·지문 정렬과 이 세 순서를 섞지 않는다. set iteration으로 반환/오류 증거를 고르지 않는다.

## 21. Integration findings 항목

정상 완료 시 다음을 잃지 않고 운반한다. 아래는 **후속 private 값 모델 계약**이며 이번 파일에 class를 구현하지 않는다.

| _CoverageIntegrationFindings 필드 | 타입/의미 |
|---|---|
| missing_condition_ids | tuple[str,...], M |
| unmapped_rule_ids | tuple[str,...], U |
| composition_gap_group_ids | tuple[str,...], G |
| inventory_fingerprint | str, 현재 Inventory 지문 |
| policy_tree_fingerprint | str, 현재 Tree 지문 |
| inventory_review_match | 정확한 기존 InventoryReviewMatch |
| implementation_findings | tuple[_ImplementationIntegrationFinding,...], canonical order |

_ImplementationIntegrationFinding은 **subtree_fingerprint:str / review_match:ImplementationReviewMatch** 두 필드만 제안한다. condition_id/rule_root_id/review_ref는 기존 review_match에 이미 있으므로 복제하지 않는다. 준비한 같은 row의 subtree_fp와 match 결과를 묶어 correlation을 보존한다. 별도 raw Implementation matches 목록/평행 fingerprint 목록은 저장하지 않는다.

incomplete에서 M/U/G를 모두 유지해야 현재 연결 부족과 boundary 위험을 진단할 수 있다. G가 비어 있다고 M을 없애거나 review 상태로 U/G를 덮지 않는다. 실제 Policy/Binding/Inventory/Context/SourceRegistry·raw review/사용자 profile은 fields에 넣지 않는다.

## 22. Intermediate model 필요성 판단

| 선택 | 평가 | 결정 |
|---|---|---|
| 중첩 private tuple 하나 | 이전 structure3-tuple과 달리7개 fields와 per-binding 지문/결과 대응을 index로 관리해야 함 | 통합 출력에는 미채택 |
| 두 최소 private immutable findings 값 | 이름 있는 fields·per-binding correlation, status derivation 없음, 중복 IDs 회피 | **통합 코드 전에 채택** |
| CoverageResult에 바로 저장 | 최종 상태/대외 표현이 아직 미확정이며 기반과 최종 판단이 합쳐짐 | 미채택 |

후속 findings 모델은 frozen/slots, 필수 fields, exact tuple/문자열/결과 타입, lowercase hex64 지문을 요구한다. M은 canonical condition ID 문법, U/G는 기존 exact 비공백 자유 rule ID 문법과 중복 거부를 따른다. 입력 순서를 자동 sort/dedupe하지 않는다. Implementation findings는 review_match.condition_id strict 오름차순·유일성을 검증한다.

로컬 invariant로 M이 비면 U/G도 비어야 하고, M과 existing Implementation condition IDs는 겹치지 않아야 한다. 하위 MatchResult는 정상 생성자를 신뢰하며 재실행하지 않는다. 원래 Inventory/tree가 없으므로 missing의 실제 완결성·모든 Binding 대응·지문 내용 진실성은 모델 생성자가 새로 증명하지 않는다. 그 보증은 pipeline이 제공한다. 모델을 수동 구성한 것이 integration 실행 증명은 아니다.

scope/policy/dataset version을 매번 복제한 범용 Snapshot 모델·serializer·persistence·public export는 만들지 않는다. 이 최소 모델의 구현은 composition 분석 이후 **별도 milestone**로 분리한다. 현재 다음 작업은 준비되지 않은 통합 모델이 아니라 독립 검증 가능한 composition helper다.

## 23. RuleNode runtime 처리와 baseline 경계

resolved roots는 M2.32에서 얻어 phase2/4까지 같은 호출 안에서만 재사용한다. 지문 준비 row의 root가 Binding과 같은 현재 Policy에서 온 원본이라는 A1을 유지한다. 다른 Policy/Binding으로 바뀌면 이전 rows를 재사용하지 않는다.

findings 모델·JSON·DB·review record에 RuleNode를 저장하지 않는다. findings는 현재 caller가 가진 입력들과 함께 쓰는 private 중간값이며, 그 자체로 완전한 영속 감사 archive가 아니다. Context의 dataset/source/implementation baseline 진실성과 실제 선택 release의 일치는 신뢰된 외부 준비 계층 책임이다. 최종 결과에 어떤 identity/baseline을 공개·영속 보존할지는 별도 CoverageResult 설계 범위다.

## 24. CoverageResult와의 경계

integration은 facts/current 지문/정상 Review matches만 반환한다. 정상 완료는 “구조적/target/현재 snapshot/명시 ref 비교 과정에서 Data Error가 없었다”는 범위다. 실정책의 조건 누락이나 잘못된 인간 review까지 자동 탐지했다는 의미가 아니다.

후속 CoverageResult가 M/U/G·Review 사유를 어떻게 노출할지는 별도 설계한다. 구현 완료 전 facts를 버리면 진단을 복구하기 어렵기 때문에 중간 findings에서 보존한다. 실제 Envelope/Manifest/legacy Coverage format에 새 fields를 넣거나 release migration을 지금 수행하지 않는다.

## 25. FULL/SLICE·Verification·Acceptance 경계

M=()/U=()/G=()는 현재 MVP mapping/composition 제한의 완료 후보다. Inventory review MATCHED와 필요한 모든 existing Implementation review MATCHED가 더해져야 후속 FULL 후보를 논의할 수 있다. 공식 Inventory/입력/evaluator 의미 검토와 외부 신뢰 경계도 유지한다.

여기서 FULL_POLICY/CONDITION_SLICE·VERIFIED/ACCEPTED·사용자 PASS/FAIL/UNKNOWN·Benefit Acceptance/Cashflow를 계산하거나 새 Enum으로 반환하지 않는다. Context=None은 review 미확인 상태를 남길 뿐 integration 실패는 아니다. 정상 MISSING/STALE과 구조적 모순을 동일 상태로 합치지 않는다.

## 26. Current Ansan 개념 예시

기존 문서의 ALL(resident,birth)와, 향후 전체 Inventory 후보에 RESIDENCE_DURATION도 포함된다는 가정이다. resident/birth만 Binding되면 M에 기간 condition이 남고 U=()일 수 있다. unowned top-level ALL은 허용되어 G=()다.

이 incomplete도 유효한 Context target과 현재 지문을 준비한 뒤 Inventory 및 두 existing Binding의 review matching을 진행할 수 있다. 기간 condition의 가상 Implementation match는 만들지 않는다. 모든 existing reviews가 MATCHED여도 missing은 그대로 남는다.

문서상 가정이며 실제 안산 Inventory/Binding/Review/지문/findings를 생성·실행·저장하지 않았다. 실제 공식 조건 전체 목록을 이번에 확정하지 않는다. release001/002의 DRAFT/CONDITION_SLICE·SHA 선언·혜택 반영 계약은 유지한다.

## 27. Future Ansan 개념 예시

공식 의미가 확정되고 필요한 모든 조건이 구현됐다는 가정에서 ALL(resident,birth,DURATION_ANY(path3y,path10y))와 COND_DURATION→DURATION_ANY 전체 Binding은 정상 구조 후보다. top ALL은 unowned이나 허용되고, duration ANY는 owned이므로 G에 없다. M/U/G 모두 비어 있을 수 있다.

Review/공식 의미/입력모델 지원은 별도다. 3년/10년 기산·날짜 경계·등록분류/예외 산식은 여기서 정하지 않는다. 실제 ResidenceHistory Fact/Rule/Evaluator나 mock production placeholder를 추가하지 않는다. **OFFICIAL_INQUIRY_REQUIRED** 유지다.

## 28. 잘못된 ANY 예시와 내부 ANY의 구별

기간 ANY 아래 path3y/path10y를 COND_CONTINUOUS와 COND_CUMULATIVE라는 두 conditions로 각각 Binding하고 그 Inventory가 모두 bound라고 주장하면, M2.32는 U=()로 통과할 수 있다. ANY root는 unowned여서 G=(DURATION_ANY,)이며 composition gate는 거부한다.

COND_PARENT가 그 ANY를 포함한 상위 subtree 전체를 소유하면 ANY 자체에 별도 Binding이 없어도 G가 아니다. 부모를 소유하면서 자식 condition을 또 Binding하면 먼저 ownership overlap이 실패한다. 공식 의미와 무관하게 group 이름/기간 단어로 예외를 만들지 않는다.

## 29. NOT와 ALL 추가 예시

NOT(A)를 COND_A→A로만 연결하면 M=()/U=()여도 G=(NOT root,)이므로 실패한다. COND_NEG→NOT root 전체면 gap이 없다. unowned NOT(NOT(A))도 두 gap을 모두 기록하며 이중부정을 임의 제거하지 않는다.

ALL(ALL(A,B),C)를 세 disjoint condition leaf에 연결하면 unowned 두 ALL 모두 허용한다. ALL(A,ANY(B,C))에서 ANY 전체를 한 condition이 소유하면 정상 후보, B/C를 독립 conditions로 분해하면 complete에서 gap이다. ANY가 하나의 child만 갖는 등 논리적으로 단순화 가능한 경우에도 현재 MVP는 unowned ANY를 보수적으로 거부한다.

## 30. 전체 오류 우선순위

| 순위 | 실패 지점 |
|---|---|
| 0 | 입력 타입: coverage → policy → review_context. bad Context 타입도 의미 검사 전에 거부 |
| 1 | 기존 structure: Coverage/Policy mismatch → root/tree 방어 → overlap → complete+unmapped 승격 |
| 2 | composition 분석의 입력/tree/수집 방어 → complete+G 승격 |
| 3 | 제공 Context의 policy → scope target mismatch |
| 4 | Inventory → Tree → canonical subtree 지문 계산 실패 |
| 5 | Inventory matcher 한 slot 내부의 기존 fail-fast 오류 |
| 6 | canonical Implementation slot별 기존 fail-fast 오류 |
| 7 | 정상 immutable findings 구성 |

structure 내부의 타입/unsupported/duplicate/root 순서는 M2.32와 기존 helper 그대로다. error list를 새로 정렬하지 않는다. overlap+broken review는 overlap, U+G complete는 unmapped, G complete+stale review는 composition, 지문 오류+broken review는 지문, Inventory slot 오류+Implementation slot 오류는 Inventory가 먼저다.

정확한 타입의 wrong-target Context와 structure 오류가 함께 있으면 structure가 먼저다. 반면 Context 값이 dict/subclass처럼 타입부터 잘못됐으면 phase0이 먼저다. 객체 생성자가 이미 거부한 record/type/ref 중복 오류까지 이 runtime 순서로 재분류하지 않는다. 모든 오류는 원래 PolicyDataError를 전파하고 부분 findings와 함께 반환하지 않는다.

## 31. 결정성·무변경·운영 경계

동일 입력에서100회 같은 G·지문·match outcomes·오류를 반환해야 한다. Binding/Context record tuple 순열에 무관한 explicit ref/canonical 처리, 원본 free ID/Unicode/공백 보존을 유지한다. 검토일/현재시각/version 숫자 크기/tuple 첫 record로 latest review를 선택하지 않는다.

Coverage/Policy/Context/Binding/root/children/evidence를 변경하지 않는다. filesystem/network/Git/env·사용자 facts·정책 재평가·LLM·Acceptance·Cashflow·global cache는 없다. 지문 계산만 현재 메모리 도메인 값에서 수행하며 실제 파일 hash나 외부 artifact 진실성 조회를 맡지 않는다.

## 32. 후속 테스트 계약

이번에는 실행 테스트를 추가하지 않는다. 단계별 구현 때 다음을 합성 자료로 검증한다.

| 단계 | 실행 검증 계약 |
|---|---|
| Composition helper | exact 입력·pair/condition/root 연결·leaf root·ALL/ANY/NOT owned/unowned/nested·pre-order·zero Binding·원본 ownership 재사용·100회/무변경·예외 전파 |
| Findings 모델 | strict 필드/tuple/지문/결과 타입·canonical per-binding order·중복 IDs·M empty의 U/G 금지·M/existing condition disjoint·동결·no roots/serializer/status |
| Integration phase | structure1회→composition1회→Context target→Inventory/Tree 각1회·root당 subtree1회→Inventory matcher1회→Binding당 Implementation1회 |
| Error precedence |30절 전체 및19절 slot별 변경 counterexample, no partial results, same exception identity |
| Normal incomplete | M/U/G 모두 보존·zero Binding/None Context·모든 정상 matches 수집·missing 조건에 가짜 match 없음 |
| Separation | 기존94/112/93/80·matcher142/257·resolver63/result166·GV01~GV15 불변, actual 자료로 새 계산 없음 |

정상 공개 생성자가 막는 duplicate/unsupported/empty/cyclic tree는 frozen 객체 훼손·생성자 우회·비정상 traversal 주입으로 테스트하지 않는다. 정상 생성자 경계와 소스/수동 방어 사례를 구분한다. 미래 node/operator는 명시적 지원 전 fail closed다. 함수 책임만 제한하고 같은 모듈의 미래 별도 기능을 막는 테스트를 만들지 않는다.

## 33. 수동 시나리오 — IG01~IG116

**116개 문서상 계약 사례이며 실행 테스트가 아니다.** 다른 표시가 없으면 정상 finite tree/exact 생성 모델/같은 policy/유효한 다른 독립 gates를 전제한다. “통과”는 해당 gate의 성공이며 FULL을 뜻하지 않는다. M/U/G는 missing/unmapped/composition gap facts다.

| ID | 사례 | 기대 |
|---|---|---|
| IG01 | unowned top ALL | G에 없음 |
| IG02 | unowned nested ALL | 모두 허용 |
| IG03 | owned ALL | 내부 condition 구현 범위 |
| IG04 | owned ANY | G에 없음 |
| IG05 | unowned ANY, M=() | composition Data Error |
| IG06 | unowned ANY, M nonempty | G 보존, 승격 보류 |
| IG07 | owned NOT | G에 없음 |
| IG08 | unowned NOT, M=() | composition Data Error |
| IG09 | unowned NOT, M nonempty | G 보존, 승격 보류 |
| IG10 | parent-owned nested ANY | 소유 union에 포함, gap 아님 |
| IG11 | parent-owned nested NOT | gap 아님 |
| IG12 | M/U/G empty인 정상 mapping | 구조/composition 통과, 후속 계속 |
| IG13 | missing condition | 정상 incomplete facts |
| IG14 | complete+unmapped leaf | M2.32 오류, composition 전 실패 |
| IG15 | ownership overlap | 구조 오류, 뒤 단계 없음 |
| IG16 | missing root | resolver 오류 그대로 |
| IG17 | Context=None | 정상 입력, 현재 지문 후 Review MISSING |
| IG18 | 같은 policy/scope Context | target 통과 |
| IG19 | Context policy 다름 | REVIEW_POLICY_MISMATCH |
| IG20 | Context scope 다름 | REVIEW_SCOPE_MISMATCH |
| IG21 | 같은 target의 empty Context | target 통과, 명시 ref가 있으면 후속 ref 오류 |
| IG22 | 현재 Inventory 지문 준비 | 기존 함수1회 |
| IG23 | 현재 Tree 지문 준비 | Inventory 다음1회 |
| IG24 | 현재 subtree 지문 준비 | 원본 root당1회 |
| IG25 | zero Binding | subtree 호출0회, Inventory/Tree 각1회 |
| IG26 | 여러 Binding의 지문 | condition_id순 원본 row와 대응 |
| IG27 | fingerprint 인코딩 실패 | matcher 호출 전 Data Error |
| IG28 | Inventory review MATCHED | 정상 보존, 다음 slot 계속 |
| IG29 | Inventory review MISSING | 정상 보존, 다음 slot 계속 |
| IG30 | Inventory review STALE | 정상 보존, 다음 slot 계속 |
| IG31 | Inventory review Data Error | Implementation 호출 없음 |
| IG32 | 모든 Implementation MATCHED | 모든 결과 보존, FULL 파생 없음 |
| IG33 | Implementation 하나 STALE | 나머지 정상/오류 계속 검사 |
| IG34 | Context=None로 Implementation MISSING | existing IDs/ref 보존 |
| IG35 | 여러 Implementation STALE | 각 canonical reasons 모두 보존 |
| IG36 | Implementation 하나 Data Error | pipeline 실패, partial 반환 없음 |
| IG37 | Binding=() | Implementation finding tuple=() |
| IG38 | missing condition + existing reviews MATCHED | M 유지, 전체 완료 아님 |
| IG39 | M/U nonempty | 둘 다 보존 |
| IG40 | M/G nonempty | 둘 다 보존 |
| IG41 | missing + Context=None | M·정상 MISSING outcomes 보존 |
| IG42 | 구조/composition complete + reviews MATCHED | integration 정상 findings, FULL 미계산 |
| IG43 | 구조 complete + Inventory STALE | 정상 findings |
| IG44 | 구조 complete + Implementation STALE | 정상 findings |
| IG45 | 구조 complete + Context=None | 정상 미검토 findings |
| IG46 | Coverage/Policy mismatch + root 오류 | policy mismatch 우선 |
| IG47 | structure 오류 + 정상 타입 wrong-target Context | structure 우선 |
| IG48 | overlap + broken review ref | overlap 우선 |
| IG49 | complete G + review stale | composition 오류 우선 |
| IG50 | 지문 오류 + review ref 오류 | 지문 오류 우선 |
| IG51 | Inventory slot 오류 + Implementation 오류 | Inventory 오류 우선 |
| IG52 | Implementation 여러 오류 | condition_id순 첫 slot 오류 |
| IG53 | Binding tuple 순열 | facts·대응·오류 동일 |
| IG54 | Implementation findings 출력 | canonical condition_id순 |
| IG55 | 여러 composition gaps | Policy pre-order |
| IG56 | subtree 지문 출력 대응 | canonical same-row correlation |
| IG57 | duration ANY 전체를 한 condition에 연결 | ANY owned, gap 없음 |
| IG58 | duration ANY children을 두 conditions로 split | complete면 ANY gap 오류 |
| IG59 | ANY를 포함한 상위 root Binding | ANY gap 없음 |
| IG60 | NOT 전체를 하나의 condition에 연결 | NOT owned |
| IG61 | NOT child만 연결 | complete면 NOT gap 오류 |
| IG62 | resident/birth를 ALL 아래 별도 연결 | unowned ALL 허용 |
| IG63 | 세 독립 조건을 중첩 ALL로 연결 | 허용 |
| IG64 | 현재 안산 모양의 문서상 incomplete | 실제 결과 생성 없이 M 남음 |
| IG65 | Residence duration condition missing | 가짜 match/Rule 없음 |
| IG66 | 현재 모양의 top ALL | gap 아님 |
| IG67 | 미래 duration ANY owned 가정 | gap 아님, 기간 의미 확정 아님 |
| IG68 | 미래 모든 condition/target 연결 가정 | M/U/G empty 가능, Review 별도 |
| IG69 | Context.policy_id exact 일치 | 통과, strip/보정 없음 |
| IG70 | 같은 scope 값인 별개 객체 | 값 동등성으로 통과 |
| IG71 | Q3 vs annual | target mismatch |
| IG72 | user facts 변화 | integration 입력 아님 |
| IG73 | 사용자 eligibility 변화 | gate와 무관 |
| IG74 | Acceptance 외부 상태 | 읽거나 파생하지 않음 |
| IG75 | Cashflow 외부 결과 | 읽거나 변경하지 않음 |
| IG76 | 동일 입력100회 | 동일 결과/오류 |
| IG77 | Context record tuple 순열 | explicit ref 의미 동일 |
| IG78 | Coverage 호출 전후 | 원본 값/identity 유지 |
| IG79 | Policy/tree/children 호출 전후 | 유지 |
| IG80 | Context/reviews 호출 전후 | 유지 |
| IG81 | incomplete의 M | findings에 보존 |
| IG82 | incomplete의 U | findings에 보존 |
| IG83 | incomplete의 G | findings에 보존 |
| IG84 | Inventory match | 기존 결과 원본 보존 |
| IG85 | Implementation matches | subtree 지문과 묶어 보존 |
| IG86 | leaf mapping만 완료 | global completion 주장 금지 |
| IG87 | composition gate 통과 | formal equivalence/공식 의미 증명 아님 |
| IG88 | 실제 condition 간 OR 표현이 필수인 새 정책 | richer model 별도 설계, gate 우회 금지 |
| IG89 | 모든 facts 정상 | FULL Enum/상태 없음 |
| IG90 | incomplete facts | SLICE Enum/상태 없음 |
| IG91 | 정상 MISSING | Data Error 아님 |
| IG92 | 정상 STALE | Data Error 아님 |
| IG93 | zero Binding + ANY root | M/U/G 보존, 정상 incomplete |
| IG94 | zero reviews + ref 미선언 + zero Binding | target 통과 후 Inventory 미선언 MISSING |
| IG95 | 여러 unowned ALL | 전부 허용 |
| IG96 | unowned ALL + owned ANY | G empty 가능 |
| IG97 | unowned ALL + unowned ANY | ANY만 G, M에 따라 승격 |
| IG98 | nested unowned ANY/NOT 여러 개 | 모두 pre-order로 기록 |
| IG99 | 미래 미지원 node/group operator | 명시 지원 전 fail closed |
| IG100 | 미래 ResidenceHistory 지원 | 공식 답변·별도 모델/Rule 승인 전 추가 없음 |
| IG101 | ref=None/zero Binding + 다른 policy empty Context | integration target gate가 거부 |
| IG102 | ref=None/zero Binding + 다른 scope empty Context | integration target gate가 거부 |
| IG103 | Context=dict/subclass + structure 오류 | input type 오류 먼저 |
| IG104 | complete U positive + G positive | COVERAGE_UNMAPPED_RULE 우선 |
| IG105 | Inventory 동일 version conflict + Implementation broken ref | slot 개정으로 Inventory conflict 우선 |
| IG106 | canonical 첫 Implementation conflict + 뒤 broken ref | 첫 slot conflict 우선 |
| IG107 | Inventory STALE + 뒤 Implementation broken ref | 정상 STALE에서 중단 안 하므로 뒤 Data Error |
| IG108 | 부모 group와 child 둘 다 Binding | ownership 오류로 composition 전에 실패 |
| IG109 | unowned unary ANY의 leaf만 Binding | 동치 단순화 없이 complete에서 gap |
| IG110 | unowned 이중 NOT 아래 leaf Binding | NOT 둘 다 G, complete에서 오류 |
| IG111 | 한국어/공백/따옴표/줄바꿈 gap ID | 원문 보존, 오류 JSON만 escaping |
| IG112 | Inventory 순서 자체만 변경 | M 순서는 변경 가능, inventory 지문은 canonical |
| IG113 | tree child 순서 변경 | U/G 순서·Tree 지문은 현재 tree 반영 |
| IG114 | findings에 runtime RuleNode를 넣으려 함 | 모델 fields에 없음, persistent 저장 금지 |
| IG115 | 현재값을 과거 review hash로 채움 | 신뢰된 준비 경계 위반, 금지 |
| IG116 | 현재 snapshot 준비 후 입력 Policy/Binding을 교체 | 이전 rows/findings를 새 입력에 재사용 금지 |

## 34. 기존 계약 충돌과 명시적 대체 범위

이번에는 옛 파일을 직접 수정하지 않는다. 다음은 **후속 미구현 integration/composition 계약의 명시적 개정**이며 기존 실행 코드/Golden/테스트 의미를 바꾸는 것이 아니다.

| 기존 문구·위치 | 유지/대체 결론 |
|---|---|
| M2.31 16절·M2.32 32절 및 ARCHITECTURE.md42절의 mapping-complete | 한정 표현 유지. global composition·Review·FULL까지 보장한다고 읽지 않음 |
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md9절의 top ALL direct children IDs=Binding roots IDs·단일 Binding의 제한된 wrapper 형태 | **현재 MVP composition의 형태 조건으로 대체**. nested unowned ALL도 허용하고 unowned ANY/NOT는 M에 따라 승격. complete에서도 direct-child equality는 새 필수 검사가 아님 |
| POLICY_COVERAGE_SPEC.md11·24절의 top ALL만 예외라는 tree 모양 | 같은 대체. 독립 conditions 사이 conjunction 원칙·disjoint 소유는 유지하며 ALL의 계층 배치는 일반화 |
| COVERAGE_UNMAPPED_RULE_SPEC.md31절의 complete에서 exhaustive 모양 검사 가능성 | 이 문서가 미구현 composition 부분을 구체화. nested ALL까지 허용하므로 옛 direct-child equality를 다시 추가하지 않음 |
| zero Binding/미매핑이면 무조건 오류라는 옛 문구 | M2.29 개정 그대로. M/U 보존, M empty/U positive만 기존 오류 |
| ImplementationBindingReview가 전체 결합도 검토한다는 CONTEXT_SPEC.md4절 | 검토 주장의 의미 유지. matcher가 Boolean 정당성을 machine proof한다는 해석은 배제. composition gate 독립 필요 |
| InventoryCompletenessReview의 조건/예외 완결성 | human review 주장 유지. 구조화된 condition Boolean expression model이 있다는 뜻 아님 |
| COVERAGE_REVIEW_MATCHING_SPEC.md18절의 모든 slots identity→모든 slots content 순서 | **19절대로 slot 전체 순차 처리로 대체**. Inventory 전체 우선, Implementation canonical 전체 순서. 동일 slot guarded conflict·정상 outcome 수집·fail-fast 원칙은 유지 |
| 같은 문서41~42절·현재 두 matcher의 단일 slot API/오류 | 그대로 재사용. 코드 분할/중복 preflight/기대값 변경 없음 |
| Inventory ref 미선언 때 Context target을 읽지 않는 현재 분기 | 분기 유지. integration phase3에서 제공 Context의 target을 항상 검사하여 공백 보완 |
| M2.31의 private structure tuple 채택 | 유지. structure3-tuple은 변경하지 않고, 더 많은 integration facts의 전달만 별도 typed 값으로 분리 |
| DATA_MODEL/ARCHITECTURE의 현재 구현 상태 | 유지. 이 문서가 새 helper/gate/model을 구현 완료로 바꾸지 않음 |

ALL 중첩 허용은 논리 AND 관계를 OR/NOT로 확장하는 변경이 아니다. 새 gap gate가 조건 내부의 의미 오류를 review 없이 인증한다는 주장도 아니다. 공식 조건·source/release·GV01~GV15·기존 domain flags/원문/개인정보 원칙은 그대로다.

## 35. 미해결 문제·가정·검증 기록

**다음 composition 분석 helper를 막는 미결정은 없다.** G 정의/입력/순서/방어·ownership 재사용·사실/승격 분리·MVP 안전 제한을 확정했다. 새로운 ConditionComposition 모델은 현재 필수 선행이 아니다.

통합 실행 전 필요한 기반은 구현 과제로 명확히 남긴다. composition helper, 두 최소 findings 값 타입, 제공 Context의 target gate, 현재 snapshot 준비와 기존 matcher의 slot 조립이 아직 없다. 13·14·19·21~22·30절의 계약을 별도 승인 단계로 구현해야 한다. 이를 현재 구현된 최종 gate라고 주장하지 않는다.

이번 범위의 phase/반환 선택은 확정했으므로 Review 전역 phase 충돌을 미정 상태로 방치하지 않는다. 추가 정책에서 condition 간 OR/NOT 모델이 실제로 필요해지는 상황·최종 CoverageResult의 대외/영속 스키마·release/scope adapter는 후속 별도 범위다. ResidenceHistory 공식 의미는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

Assumption A1은 정상 생성된 유한 불변 strict tree와 동일 현재 자료에서 온 원본 pairs·신뢰된 Context baseline 공급이다. helper/모델 생성 성공이 인간 검토·공식 목록·외부 artifact 진실성을 증명하지 않는다. 무한 깊이/순환/훼손 객체 복구·악의적 hash 제출을 인증하는 기능은 추가하지 않는다.

작업 전 actual releases 제외 backend/tests/data/docs **135개 파일 SHA256**과 release **6개 파일 경로/길이/수정시각**을 기록했다. 전체 기준 pytest는 **4991 passed in 13.35s**다. 신규 실행 테스트는 없으며116개 사례는 수동 문서 계약이다. 새 actual Inventory/Binding/gap/지문/Review/findings를 생성하거나 실행하지 않는다.

최종 대조에서 기존135개 파일은 SHA256까지 동일하고 수정·삭제는 없다. 추가는 이 문서 하나뿐이다. actual release6개 파일의 경로/길이/수정시각도 같다. 1~37절과 IG01~IG116이 순서대로 유일하게 존재하고 code fence3쌍이 닫혀 있음을 확인했다. 한국어 표기도 확인했다. 기존 전체4991개 실행 테스트의 코드·기대값·Golden·모델/helper·공개 export·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 그대로다.

## 36. 후속 단계 추천

| 순서 | 작은 승인 작업 | 포함하지 않는 것 |
|---|---|---|
| 바로 다음 M2.34 | _find_composition_gap_group_ids 한 private 분석 helper와 합성 테스트 | M/G 승격·integration·findings 모델·Review/지문 실행 |
| 그 다음 별도 |21~22절의 최소 private immutable findings 타입 두 개 | integration 계산·CoverageResult·roots 직렬화 |
| 이후 별도 |13~20·30절의 integration 조립: 조건부 gap 승격·Context target·현재 지문·기존 matcher 호출 | FULL/SLICE/최종 CoverageResult·실제 데이터 migration |
| 검증 후 별도 | 필요한 사실을 근거로 CoverageResult/최종 상태 설계 | 지금 선행 구현하지 않음 |

다음 helper의 완료조건은 G의 exact pre-order tuple, owned ANY/NOT 제외·unowned ALL 허용·zero pair facts, 현재 타입/ID 방어, 기존 ownership collector entry당1회, 입력/예외 결정성·무변경·금지 의존 부재·기존4991개 회귀다. 아직 승격하지 않는 분석 함수라는 경계를 고정한다.

## 37. 최종 판단

**READY_TO_IMPLEMENT_COVERAGE_COMPOSITION_ANALYSIS**

현재 Coverage 모델에 별도 condition expression tree를 도입하지 않고도, disjoint subtree 소유·leaf mapping과 unowned ALL-only 제한으로 안전한 MVP 경계를 둘 수 있다. ANY/NOT gap 사실을 먼저 독립 구현하고 검증하는 것이 다음 최소 단계다.

통합 facts는 많아져 typed immutable 중간값이 필요하므로 composition 다음 별도 모델 단계도 계획했다. 이 사실을 이유로 지금 CoverageResult나 integration 전체를 구현하지 않는다.

IMPLEMENTED: 기존 structure94·unmapped112·ownership93·root80 및 Review/지문 코드와 테스트는 현 상태 그대로다. **이번 산출물은 이 문서 하나**다.

NOT IMPLEMENTED: composition 분석/gate·findings 타입·Context target integration·현재 지문/Review orchestration·CoverageResult/FULL_POLICY/CONDITION_SLICE·최종 Coverage validator·Acceptance/Benefit Bridge·actual Coverage 자료. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 38. M2.34 — IMPLEMENTED: private composition gap analysis

### API와 입력 방어

backend/policy_engine/policy_data/coverage_composition.py에 private 함수 하나만 추가했다. 공개 export·별도 helper/모델·설정 옵션은 없다.

```python
_find_composition_gap_group_ids(
    policy: Policy,
    resolved_bindings: tuple[tuple[ConditionBinding, RuleNode], ...],
) -> tuple[str, ...]
```

12절의 exact Policy → exact outer tuple → 전체 길이2 exact entry/Binding/지원 root 타입 → 중복 condition → canonical condition_id순 Binding/root ID 연결 순서를 적용했다. 잘못된 입력은 기존 unmapped helper와 같은 INVALID_STRUCTURE_INPUT 필드별 메시지다. 중복 condition 거부는 명세에 이미 명시된 계약이며 새 책임을 임의 추가한 것이 아니다.

root의 현재 Policy 소속·원본 identity·no-overlap은 A1의 선행조건이다. helper 내부에서 root lookup/overlap/unmapped/structure 함수를 다시 호출하지 않는다. 원본 pair와 ID를 자동 변환·정규화·재연결하지 않는다.

### 순회와 gap 사실 계산

기존 walk_nodes(policy.root)를 한 번 사용해 root 포함 pre-order로 전체 tree를 확인한다. 네 exact node 타입을 rule_id 접근 전에 확인하고, 전체 node ID의 중복을 지역 set/flag로 추적한다. 세 leaf는 ID 방어에만 포함하며 gap 대상이 아니다. RuleGroup의 operator는 exact GroupOperator의 ALL/ANY/NOT만 허용한다.

미지원 node/operator는 UNSUPPORTED_RULE_NODE로 거부한다. operator 방어의 고정 메시지는 `UNSUPPORTED_RULE_NODE: 지원하는 정확한 RuleGroup operator가 필요합니다`다. 전체 지원 타입/operator 검사가 끝난 뒤 중복 flag가 있으면 DUPLICATE_RULE_NODE_ID로 거부한다. 조용히 skip/dedupe하지 않는다. 정상 생성자가 막는 duplicate/미지원 node/operator/빈 tree를 만들려고 불변 객체나 생성자를 우회하지 않았다. 해당 방어 경로는 소스/수동 시나리오로 유지하고 정상 생성자의 거부를 실행 검증했다.

순회에서 ANY/NOT group 후보 IDs를 원래 순서대로 모은 뒤 condition_id순 각 entry에 기존 _collect_owned_rule_ids를 한 번씩 호출한다. 그 소유 tuple들을 지역 set으로 union하고 소유되지 않은 후보만 tuple로 반환한다. ownership traversal을 복제하거나 set iteration으로 출력하지 않는다. 전체 tree 확인 뒤에만 ownership을 수집하며 collector 예외는 같은 객체로 전파한다.

owned ALL/ANY/NOT·parent-owned nested groups는 gap이 아니다. unowned ALL은 계층과 무관하게 gap에서 제외한다. unowned ANY/NOT는 모두 Policy pre-order로 반환하며 ancestor가 gap이어도 descendant를 생략하지 않는다. child 일부/전부가 따로 소유되어도 parent ANY/NOT는 여전히 gap이다. zero Binding이면 현재 모든 ANY/NOT IDs를 반환하고, only-ALL/leaf-root Policy이면 빈 tuple을 반환한다.

### 분석과 해석의 경계

이 helper는 Policy와 원본 pair만 받는다. Inventory/Coverage/missing condition을 읽거나 M을 계산하지 않는다. positive G도 정상 tuple이며 COVERAGE_COMPOSITION_GAP 오류/상수·승격 validator를 구현하지 않았다. M2.32 structure 함수와 기존 helpers의 의미/오류/테스트는 변경하지 않았다.

Review/Context/MatchResult·지문·사용자 평가/PASS/FAIL/UNKNOWN·FULL/SLICE·Integration Findings·시간/env/파일/network/Git/cache/LLM은 사용하지 않는다. 현재 실제 정책이 일반 논리/공식 의미와 동일한지 인증하지 않는다. 원본 Policy/Binding/node/children/evidence/tuple도 변경하지 않는다.

### 합성 테스트와 다음 단계

작업 전 전체 기준은 **4991 passed in 13.48s**다. 신규 tests/test_coverage_composition.py는 **112 passed in 0.46s**다. 정상 합성 Coverage/Policy에서 M2.32 구조 분석이 성공한 원본 pairs를 준비한 뒤 helper를 검증했다. standalone 잘못된 입력 검증도 포함하며 실제 release는 fixture로 사용하지 않았다.

owned/unowned ALL/ANY/NOT 조합·top/nested/multiple ALL·ancestor/descendant gap·parent-owned groups·partial/all child Binding·zero/single/many pairs·leaf3종·5/12/30단계 탐색, pre-order/자유 ID/Unicode·Binding 순열·100회 결정성을 확인했다. exact 입력/하위 타입·중복 condition·root 연결·검증 우선순위, 전체 walk1회/수집 전 완료·canonical entry당 ownership1회·예외 원본 전파·원본 값/identity 유지·private export/함수 단위 의존 경계도 검증했다. overlap 입력을 helper가 승인한다는 테스트는 없다.

현재 resident/birth ALL 모양은 합성으로 gap 없음, 미래 duration ANY 모양은 통째 Binding하면 gap 없음, children을 별도 조건으로 분해하면 DURATION_ANY를 정상 facts로 반환함을 검증했다. 기간 branch는 기존 AGE atomic으로 tree 경계만 표현했으며 실제 거주기간 산식/Fact/Rule/Evaluator를 구현하지 않았다. NOT child만 Binding한 경우도 NOT_X gap을 반환한다.

IMPLEMENTED: private global composition gap 사실 분석·합성 테스트112개.
NOT IMPLEMENTED: composition Data Error 승격·findings 타입·전체 integration gate/Context target·지문/Review orchestration·CoverageResult/FULL_POLICY/CONDITION_SLICE·최종 Coverage validator·Acceptance/Bridge·actual Coverage 자료.

최종 판단: **READY_FOR_COVERAGE_INTEGRATION_FINDINGS_MODEL**.
다음 가장 작은 작업 한 개는 **21~22절의 _ImplementationIntegrationFinding과 _CoverageIntegrationFindings 두 최소 private immutable 값 모델과 합성 테스트만 구현**하는 것이다. IDs는 기존 match 결과에서 가져와 중복 저장하지 않고 runtime RuleNode/serializer/최종 상태를 넣지 않는다. composition 탐지가 안정화돼도 아직 integration gate/승격/Review·지문 연결을 같이 구현하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

### M2.34 최종 검증 기록

전체 pytest는 **5103 passed in 14.07s**다. 기존4991개와 신규112개가 모두 통과했다. 기존 structure94개·unmapped112개·ownership93개·root resolver80개·Inventory/Implementation matcher142개/257개·Review resolver63개/결과166개 및 GV01~GV15 literal 회귀를 포함하며 기존 테스트/기대값 변경은 없다.

작업 전 actual releases 제외 backend/tests/data/docs136개 파일 SHA256을 기록했다. 최종 대조에서 기존134개는 동일하고 수정은 이 명세와 ARCHITECTURE.md 두 문서뿐이다. composition 모듈과 합성 테스트 두 파일을 추가했고 삭제는 없다. 기존 모델·structure/root/ownership/unmapped helpers·Review/matcher·지문 utility·공개 export·기존 모든 테스트·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했다. actual release6개 파일의 경로/길이/수정시각도 같다. 실제 Inventory/Binding/composition/Coverage 결과·새 실제 검토/지문은 생성하지 않았다. 문서의 기존 IG01~IG116과 절 순서·code fence·변경 파일의 한국어 표기도 확인했다.

## 39. M2.35 — IMPLEMENTED: private immutable integration findings 값

### 최종 클래스/필드와 후보 비교

backend/policy_engine/policy_data/coverage_integration_findings.py에 frozen=True/slots=True인 두 private dataclass만 추가했다. 모든 필드는 필수이며 별도 계산/통합 함수·public export·persistent 모델은 없다. M2.35 지시문의 후보보다21~22절 최종 필드를 우선했다.

| 클래스 | 정확한 저장 필드 |
|---|---|
| _ImplementationIntegrationFinding | subtree_fingerprint:str, review_match:ImplementationReviewMatch |
| _CoverageIntegrationFindings | missing_condition_ids:tuple[str,...], unmapped_rule_ids:tuple[str,...], composition_gap_group_ids:tuple[str,...], inventory_fingerprint:str, policy_tree_fingerprint:str, inventory_review_match:InventoryReviewMatch, implementation_findings:tuple[_ImplementationIntegrationFinding,...] |

Binding의 condition_id/rule_root_id/review_ref는 review_match 하나에만 있다. flat fields/property로 복제하지 않아 finding과 match가 다른 ID를 갖는 모순 자체를 표현할 수 없다. 기존 ImplementationReviewMatch 생성자가 ID의 canonical/비공백 형식을 검증한다. Findings는 exact MatchResult를 요구하고 그 생성자를 재실행하지 않는다. 서로 다른 ID를 추가 인자로 전달하면 정의되지 않은 인자로 TypeError다.

policy_id/scope/rule_version/dataset_version/source_registry_fingerprint/implementation_fingerprint·원본 Coverage/Binding/Policy/RuleNode/Context는 fields에 추가하지 않았다.21~23절의 private 중간값 경계를 유지한다. 해당 metadata의 사실성과 최종 영속 audit identity는 원래 caller/Context·후속 CoverageResult 설계 책임이며, findings 하나가 독립적인 완전 감사 archive라고 주장하지 않는다.

### 입력과 로컬 정합성

세 지문은 exact str·소문자 hex64 형식만 검증한다. 기존 Manifest._hash는 ManifestValidationError와 지문 계산 모듈 의존을 가져오므로 재사용하지 않고 Review 값 모델과 같은 작은 inline 검사를 사용했다. 실제 digest를 계산하거나 내용/기준 자료와 비교하지 않는다. policy_id/rule_version 검증 계약도 확인했으나 해당 필드가 없으므로 가상의 검사를 추가하지 않았다.

M/U/G는 exact tuple, 원소는 exact str이며 내부 중복을 거부한다. M은 [A-Z0-9_]+ condition ID, U/G는 기존 exact 비공백 자유 rule ID다. 앞뒤 공백·Unicode·원래 순서는 유지한다. 자동 변환/sort/dedupe는 없다.

inventory_review_match는 exact InventoryReviewMatch, review_match는 exact ImplementationReviewMatch, implementation_findings는 exact tuple의 exact _ImplementationIntegrationFinding이다. MATCHED/MISSING/STALE을 모두 받아 원본 객체를 보존한다. 원본 결과의 상태/사유를 재검증·재계산하거나 해석하지 않는다.

implementation_findings의 review_match.condition_id는 중복 없이 ASCII 오름차순이어야 한다. M과 existing condition IDs의 교집합은 오류다.22절대로 M이 비었는데 U 또는 G가 남은 구성도 로컬 정합성 오류로 거부한다. 이는 computed facts container의 형태 계약이며 COVERAGE_UNMAPPED_RULE/COVERAGE_COMPOSITION_GAP 승격·상태 파생이 아니다.

M/U/G 각각의 중복과 implementation condition 중복만 검사한다. duplicate root/실제 subtree ownership·U/G가 소유 범위 밖인지·Inventory의 실제 완결성·모든 Bindings가 전달됐는지는 upstream 책임이다. 새 tree 참조/검색/overlap 검사를 만들지 않는다. 빈 implementation tuple과 모든 facts가 빈 최소 값은 로컬 표현상 허용한다. Inventory를 입력받지 않으므로 이 값이 실제 공집합 정책 완료라는 결론을 내리지 않는다.

잘못된 형식·로컬 관계는 기존 PolicyDataError에 단일 stable prefix **INVALID_INTEGRATION_FINDINGS: field: reason**을 사용한다. payload/ID 전체·새 예외 계층/.code·상태 Enum은 추가하지 않았다. 입력의 ID tuple/지문/Inventory result/Implementation collection 타입을 확인한 뒤 canonical order → M/existing 교집합 → M empty의 U/G invariant를 검사한다.

### 값 표현·불변성·현재 지시 우선

M2.33 22절과 M2.34 후속 설명의 serializer 비추가보다 **이번 M2.35 지시의 to_dict() 요구를 우선**하여 두 모델에 값 표현만 추가했다. 실제 저장 필드와 같은2개/7개 key를 쓰며 하위 MatchResult.to_dict()를 재사용한다. 매 호출 새 중첩 dict/list를 반환하고 ID tuple 순서는 그대로다. flat identity 키·상태·계산값·parser·JSON loader·파일 저장 기능은 없다.

모든 필드는 frozen/slots이고 기본 dataclass equality/hash를 유지한다. 저장 tuple 순서도 equality에 반영된다. 반환된 nested lists/dicts를 바꿔도 원본 findings/MatchResult에 영향이 없다. 외부 I/O/시각/env/Git·지문 계산·review lookup/matching·structure/composition 분석·user evaluation·CoverageResult/FULL/SLICE·Acceptance/Cashflow는 사용하지 않는다.

### 합성 테스트와 다음 단계

작업 전 전체 기준은 **5103 passed in 13.03s**다. 신규 tests/test_coverage_integration_findings.py는 **184 passed in 0.57s**다. 첫 실행에서 하위 생성자 재실행을 막은 뒤 fixture가 불필요한 새 MatchResult를 만들던 테스트 준비 부분1개를 수정했고, production 모델은 변경 없이 통과했다. 기존 테스트/기대값은 변경하지 않았다.

모든 Review 정상 상태 조합·complete-like/incomplete/zero facts·strict 지문/tuple/ID/하위 타입·중복·canonical order·M/existing 충돌·M empty/U/G 관계·원본 identity·동결/slots/equality/hash·정확한2/7필드 직렬화·중첩 mutation isolation·100회 결정성·하위 생성자 재실행 없음·계산/금지 객체/공개 export 부재를 검증했다. hash는 합성 literal 형식만 사용하고 실제 자료·지문 utility를 호출하지 않았다.

IMPLEMENTED: 두 private immutable findings 값 모델·로컬 정합성·to_dict·합성 테스트184개.
NOT IMPLEMENTED: integration gate·Context target 연결·composition 오류 승격·fingerprint/Review orchestration·CoverageResult/FULL_POLICY/CONDITION_SLICE·최종 Coverage validator·Acceptance/Bridge·actual Integration Findings.

최종 판단: **READY_TO_IMPLEMENT_COVERAGE_INTEGRATION_GATE**.
다음 가장 작은 작업 한 개는 **13~20·30절 계약의 private _collect_coverage_integration_findings와 합성 통합 테스트만 구현**하는 것이다. 기존 structure/composition·현재 지문·두 matcher의 조립과 Context target·조건부 gap 승격·정상 findings 생성에 한정한다. CoverageResult/최종 상태·실제 데이터 발행으로 바로 확장하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

### M2.35 최종 검증 기록

전체 pytest는 **5287 passed in 13.43s**다. 기존5103개와 신규184개가 모두 통과했다. 기존 composition112개·structure94개·unmapped112개·ownership93개·root resolver80개·Inventory/Implementation matcher142개/257개·Review resolver63개/결과166개 및 GV01~GV15 literal 회귀를 포함하며 기존 테스트/기대값 변경은 없다.

작업 전 actual releases 제외 backend/tests/data/docs138개 파일 SHA256을 기록했다. 최종 대조에서 기존135개는 동일하고 수정은 이 명세·DATA_MODEL.md·ARCHITECTURE.md 세 문서뿐이다. findings 모듈과 신규 테스트 두 파일을 추가했고 삭제는 없다. 기존 모델·structure/composition/root/ownership/unmapped helpers·Review/matcher·지문 utility·공개 export·기존 모든 테스트·데이터/SHA 선언·Cashflow·ResidenceHistory 자료는 유지했다. actual release6개 파일의 경로/길이/수정시각도 같다. 실제 Integration Findings/검토/지문/정책자료는 생성하거나 저장하지 않았다. 문서 절/기존 IG01~IG116·code fence·변경 파일의 한국어 표기도 확인했다.

## 40. M2.36 — IMPLEMENTED: Integration findings collection gate

### 정확한 private API와 입력 계약

backend/policy_engine/policy_data/coverage_integration.py에 orchestration 함수 하나를 추가했다.

```python
_collect_coverage_integration_findings(
    coverage: EligibilityCoverage,
    policy: Policy,
    review_context: CoverageReviewContext | None,
) -> _CoverageIntegrationFindings
```

**이번 M2.36의 정확한 API 지시를 우선하여 13절의 keyword-only Context 후보를 대체한다.** 세 인자는 모두 필수이며 위치/키워드 전달이 가능하다. Context의 None도 명시해야 한다. 옵션·기본값·공개 export·새 persistent 모델은 추가하지 않았다.

exact EligibilityCoverage → exact Policy → None 또는 exact CoverageReviewContext 순으로 확인한다. raw dict/list/string·subclass를 자동 변환하지 않는다. 모든 입력 타입 확인이 끝난 뒤에만 구조 분석을 시작한다. 오류는 M2.33의 INVALID_STRUCTURE_INPUT 필드별 고정 메시지다.

### 실행과 오류 우선순위

| Phase | 실행 | 성공 이후 보장 |
|---|---|---|
| 1 | 세 입력 타입 확인 | 잘못된 Context 타입도 structure보다 먼저 거부 |
| 2 | _analyze_coverage_structure(coverage, policy) 정확히 1회 | M, 원본 canonical resolved pairs, U 재사용 |
| 3 | _find_composition_gap_group_ids(policy, resolved_bindings) 정확히 1회 | 같은 pairs tuple로 G 계산 |
| 4 | M이 비었고 G가 남았을 때만 오류 승격 | findings 로컬 오류 전에 의미 오류 발생 |
| 5 | Context policy_id → scope 확인 | review ref 미사용/zero Binding도 target 검사 |
| 6 | Inventory → 전체 Tree → canonical 각 subtree 지문 | 모든 현재 지문을 matcher 전에 준비 |
| 7 | Inventory matcher 정확히 1회 | 정상 MATCHED/MISSING/STALE 모두 다음 단계 진행 |
| 8 | canonical 각 existing Binding의 Implementation matcher | 정상 결과 수집, Data Error 즉시 전파 |
| 9 | 모든 매칭 성공 후 Binding findings 생성 | 원래 subtree 지문과 같은 row의 match 연결 |
| 10 | Coverage findings 생성/반환 | 기존 불변 모델의 로컬 검증 적용 |

구조/결합/지문/matcher의 기존 PolicyDataError는 wrapping 없이 같은 예외 객체로 전파한다. partial findings를 반환하지 않는다. structure 실패 시 composition 미호출, composition 승격 시 Context/지문 미실행, Context 오류 시 지문 미실행, 지문 오류 시 matcher 미호출이다. Inventory matcher 오류는 모든 Implementation matcher보다 먼저이며 Implementation 오류는 condition_id canonical 순서에서 첫 실패가 우선한다. 실패 이전의 정상 매칭 결과도 findings constructor에 전달하지 않는다.

19·34절이 명시한 Inventory slot 전체 검사 → canonical Implementation slot 전체 검사 계약을 유지했다. 과거 COVERAGE_REVIEW_MATCHING_SPEC.md18절의 모든 slot identity 선검사를 새로 도입하지 않았다.

M이 있으면 U/G가 함께 남아도 정상 facts로 보존한다. M이 없고 U가 남는 오류는 기존 structure가 COVERAGE_UNMAPPED_RULE로 처리한다. Integration에서 이를 복제하지 않는다. M이 없고 G가 남는 경우만 다음 고정 payload로 COVERAGE_COMPOSITION_GAP을 발생시킨다.

```text
COVERAGE_COMPOSITION_GAP: {"composition_gap_count":2,"first_composition_gap_group_id":"GROUP_Z"}
```

정확히 두 필드, sort_keys=True/ensure_ascii=True/separators=(",", ":") JSON이다. 첫 ID는 G tuple의 첫 값, 즉 Policy pre-order이며 사전순 최소 ID가 아니다. findings constructor를 이용해 승격 오류를 대신 발생시키지 않는다.

Context가 존재하면 coverage.inventory의 policy_id/scope와 각각 대조한다. 명시 ref를 조회할지와 무관하다. policy mismatch의 고정 메시지는 `REVIEW_POLICY_MISMATCH: Context와 현재 Inventory의 policy_id가 다릅니다`, scope mismatch는 `REVIEW_SCOPE_MISMATCH: Context와 현재 Inventory의 scope가 다릅니다`다. 두 모순이 함께 있으면 policy가 먼저다. 2026/Q3와 2026/annual은 서로 다른 범위다.

### 지문과 Review의 대응

한 호출에서 Inventory 지문 1회, Tree 지문 1회, existing Binding마다 원본 root의 subtree 지문 1회다. structure가 이미 돌려준 canonical pairs 순서를 그대로 사용하며 다시 sort/resolve하지 않는다. local row는 (원본 Binding, 원본 root, subtree fingerprint)다. root/소유 범위/미매핑/ANY·NOT 탐지를 통합 함수가 복제하지 않는다.

모든 subtree 지문이 준비된 뒤 Inventory matcher를 실행한다. 이어 current Inventory 지문·현재 Policy.rule_version·Tree 지문·해당 row의 subtree 지문을 Implementation matcher에 공급한다. matcher가 지문을 다시 계산하지 않는다. 새 _ImplementationIntegrationFinding에는 subtree_fingerprint와 같은 row의 review_match만 전달한다. condition/root/ref는 기존 match 하나에만 있으며 중복 필드가 없다. RuleNode는 함수 지역에만 머무르고 findings에 저장하지 않는다.

Context=None은 정상이다. Inventory ref 미선언이면 INVENTORY_REVIEW_NOT_DECLARED, 선언됐으면 NO_REVIEW_CONTEXT라는 기존 정상 MISSING 사유를 유지한다. existing Implementation들은 NO_REVIEW_CONTEXT로 정상 MISSING이다. Context가 있어도 Inventory ref가 미선언이면 Inventory MISSING과 Implementation MATCHED/STALE이 공존할 수 있다. identity가 맞는 빈 Context에 explicit ref가 있으면 기존 REVIEW_REF_NOT_FOUND 오류이고, ref 미선언/zero Binding이면 정상 findings가 가능하다.

zero Binding에서는 subtree 지문·Implementation matcher·Binding findings가 모두 0개다. Inventory/Tree 지문과 Inventory matcher는 그대로 실행한다. 누락 condition은 Binding이 없으므로 가짜 Implementation MISSING이나 지문을 만들지 않는다.

### 상태와 사실의 경계

MATCHED/MISSING/STALE은 상태/사유를 바꾸지 않고 보존한다. STALE이 있어도 다른 slot의 오류를 숨기지 않는다. reviewed_at/현재 날짜/최신 기록 선택 없이 기존 explicit review_ref를 사용한다. 모든 facts가 비고 모든 Review가 MATCHED여도 이 함수가 FULL_POLICY/VERIFIED/ACCEPTED를 생성하지 않는다.

**IMPLEMENTED:** Integration findings collection gate·Context target 검증·조건부 composition 오류 승격·현재 지문/Review 조립·기존 불변 findings 반환.

**NOT IMPLEMENTED:** CoverageResult·FULL_POLICY·CONDITION_SLICE·Policy verification·최종 Coverage validator·Acceptance/Bridge·Cashflow 연결·사용자 facts/PASS·FAIL·UNKNOWN 평가·actual Integration Findings. 외부 I/O/환경/시간/Git/cache/LLM을 참조하지 않는다.

### 합성 검증

작업 전 전체 기준은 **5287 passed in 15.10s**다. 신규 tests/test_coverage_integration.py는 **107 passed in 0.53s**다. 첫 실행의 annual scope fixture에서 필수 quarter=None이 누락된 부분과 strict UTF-8 오류의 기존 영문 prefix에 대한 신규 테스트 기대값을 바로잡았다. production integration 함수와 기존 코드·테스트는 이 수정에 포함하지 않았다.

실제 helpers를 연결해 complete-like all MATCHED·Context None·미선언 Inventory·empty Context·zero Binding·M/U/G 동시 보존·top/nested ALL·ANY/NOT root 소유/child 분해·complete gap 승격을 검증했다. 현재 resident/birth와 missing duration, 미래 duration ANY 전체 소유/잘못된 분해는 합성 tree만 사용한다. 기간 branch는 기존 AGE atomic으로 경계만 표현하며 ResidenceHistory 산식/Rule/Fact를 만들지 않는다.

스파이로 structure/composition 각 1회·원본 pairs identity·현재 지문 순서/횟수·원본 root identity·각 subtree와 condition/root/match 대응·matcher 순서/횟수·모든 매칭 후에만 findings 생성하는 순서를 확인했다. exact 타입/subclass·입력 우선순위·실제 구조 오류·Context policy/scope·합성 helper 예외의 동일 객체 전파·실제 strict UTF-8 지문 실패·Inventory conflict 우선·Implementation 중간 실패/partial 부재도 확인했다.

정상 생성자가 막는 duplicate/미지원 node를 불변 객체 우회로 만들지 않았다. 해당 선행 helper 오류의 wrapping 없는 전달은 명시적 합성 예외 주입으로 검증한다. Implementation MISSING은 기존 matcher 계약상 Context=None에만 발생하므로 하나의 정상 Context에서 Implementation MISSING/STALE 혼합은 직접 구성되지 않는다. 실제 Context 경로와 별도로 matcher의 정상 반환값 주입 테스트에서 orchestration이 세 상태를 해석하지 않고 보존함을 확인했다.

100회 동일 입력·Binding 순열·Context 기록 순서/더 최신인 미선택 기록·원본 Coverage/Inventory/Bindings/Policy/nodes/Context/records의 값과 identity 유지·반환 snapshot 독립성을 검증했다. private export와 함수 단위 의존 경계를 검사하며 같은 모듈에 미래 기능을 추가하지 못하게 하는 테스트는 없다.

최종 판단: **READY_FOR_COVERAGE_RESULT_DESIGN**.

다음 가장 작은 작업 한 개는 **CoverageResult의 최소 불변 필드·identity 보존 범위·findings에서 FULL_POLICY/CONDITION_SLICE를 파생하는 필요조건·오류/정상 상태 구분을 문서로 설계**하는 것이다. 아직 status 코드를 구현하지 않는다. actual releases는 유지하며 M1.18 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 상태로 계속 보류한다.

### M2.36 최종 검증 기록

전체 pytest는 **5394 passed in 14.24s**다. 기존5287개와 신규107개가 모두 통과했다. findings184개·composition112개·structure94개·unmapped112개·ownership93개·root resolver80개·Inventory/Implementation matcher142개/257개·Review resolver63개/결과166개 및 GV01~GV15 literal 회귀를 포함한다. 기존 테스트/기대값 수정은 없다.

작업 전 actual releases 제외 backend/tests/data/docs140개 파일의 SHA256을 기록했다. 최종 대조에서 기존138개가 동일하고 수정은 이 명세와 ARCHITECTURE.md 두 문서뿐이다. integration 모듈과 합성 테스트 두 파일을 추가했고 삭제는 없다. 기존 findings 모델·structure/composition/root/ownership/unmapped helpers·Review/matcher·지문 utility·공개 export·기존 테스트·정책자료·Cashflow·ResidenceHistory는 유지했다. actual release6개 파일의 경로/길이/수정시각이 동일하다. 새 실제 정책 지문·Review·Binding·Integration Findings는 생성/저장하지 않았다.
