# 자격조건 Coverage 순수 검증 계약 — M2.10

> EligibilityCoverage 구조와 책임표는 33절 M2.11, 독립 review metadata는 34~35절, Context collection은36절, 공개 Coverage evaluator는37절 M2.39를 따른다. 1~32절은 M2.10 설계 기록이다. 현재 상세 Gate/Result 계약은 COVERAGE_INTEGRATION_GATE_SPEC.md40절과 ELIGIBILITY_COVERAGE_RESULT_SPEC.md36~37절을 우선한다.

M2.10 작성일: **2026-10-21 / Asia/Seoul**. 당시에는 **문서 설계 전용**이었다. 현재 구현 상태는33절 이후의 기록을 따른다.

현재 최종 판단: **ELIGIBILITY_COVERAGE_CORE_COMPLETE** (37절). M2.10 당시 판단은 READY_TO_IMPLEMENT_ELIGIBILITY_COVERAGE였다. 실제 안산 FULL·Acceptance·서비스 연결 승인이 아니다.

## 1. 목적

ConditionInventory가 정의한 필요한 의미상 조건과 ConditionBinding이 지목한 실제 Policy subtree 사이의 참조·소유·결합 논리를 검증한다. 구조적 모순은 Data Error, 정상적인 조건/검토 미완료는 CONDITION_SLICE로 구별한다. FULL_POLICY는 검토된 inventory·tree·구현 대응을 확인한 결과에서만 파생한다.

Source of Truth: POLICY_COVERAGE_SPEC.md 1~30절과31~34절의 현재 구현 기록, POLICY_BENEFIT_ACCEPTANCE_SPEC.md, CASHFLOW_BENEFIT_BRIDGE_SPEC.md, POLICY_RULE_SPEC.md, RULE_ROUTING_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 코드의 ApplicabilityScope/RequiredCondition/ConditionInventory/ConditionBinding, Policy/RuleGroup/RuleNode/walk_nodes/중복 ID 검사와 legacy PolicyCoverage/Envelope의 leaf·source 대조를 다시 확인했다. 저장소의 확인본 검토이며 정책 원문을 새로 조회한 작업은 아니다.

## 2. 입력 객체

필수 입력은 정확한 ConditionInventory, 정확한 tuple[ConditionBinding,...], 정확한 Policy다. 상위 scope override·사용자 profile·PolicyEvaluation·시각·Envelope·SourceRegistry는 받지 않는다. inventory.scope와 policy.rule_version을 그대로 사용한다.

FULL의 검토 대응을 위해 **선택적 CoverageReviewContext**를 keyword-only 입력으로 제안한다. 이를 생략하면 구조 검증은 가능하지만 FULL은 불가다. 참조 존재만 보는 세 인자 API로 FULL을 반환하는 설계는 POLICY_COVERAGE_SPEC.md 10~11·21·24절의 검토 snapshot 의무를 충족하지 못한다.

Context는 파일/DB registry가 아니라 외부에서 검토를 완료한 **불변 메모리 확인 묶음**이다. 최소 값 제안:

| 필드 | 의미 |
|---|---|
| inventory_snapshot | 검토한 ConditionInventory 값. scope/identity/조건 의미·근거·completeness ref 포함 |
| policy_snapshot | 검토한 Policy 값. 전체 root 구조·노드 종류·연산자·자식 순서·기준값·evidence·rule_version 포함 |
| bindings_snapshot | 검토한 ConditionBinding tuple. condition/root/implementation ref별 정확한 대응 |
| dataset_version | 검토한 고정 자료 확인본 ID |
| source_bindings | inventory/구현 검토가 사용한 tuple[SourceBinding,...]. 기존 source ID/document_version 값, ID 유일 |
| implementation_contract_ref | 지원 입력모델/evaluator 구현 확인본·분기/경계 테스트를 묶은 검토 참조 |

실제 reviewer·시각·승인 workflow를 runtime 객체마다 복제하지 않는다. 기존 refs가 가리키는 실제 검토 기록을 외부 준비 계층이 대조한 뒤 이 묶음을 공급한다. Context constructor 성공은 실제 검토가 수행됐다는 인증이 아니다. 임의 사용자/LLM의 snapshot 선언은 신뢰하지 않는다. 이 모델과 발급/대조 코드도 현재 미구현이다.

## 3. Structurally valid vs complete

**STRUCTURALLY VALID:** 존재하는 Binding들의 condition 참조·root·subtree 소유·전체 결합이 서로 모순되지 않는다. R 중2개가 없어도, tree에 구현된2개만 정확히 연결되면 정상이다.

**COVERAGE COMPLETE:** 구조 검증에 더해 모든 REQUIRED/CONDITIONAL 조건이 binding되며, 공식 목록 완결성과 구현 전체 분기·지원 입력/evaluator가 고정 검토 자료로 확인됐다. 같은 사용자에게 PASS가 나오는지는 관계없다.

미검토 구조가 정상이라는 이유로 FULL을 반환하지 않는다. 조건 수가0인 공집합 FULL은 기존 Inventory 모델이 빈 목록을 거부하므로 성립하지 않는다.

## 4. Error vs SLICE

| 정상 미완료 → SLICE | 구조적 모순 → Data Error |
|---|---|
| R의 REQUIRED/CONDITIONAL 일부에 binding 없음 | 존재하지 않는 condition/root 참조 |
| 공식 거주 의미 미확정으로 binding 자체 없음 | 같은 condition 중복 binding, 같은 root/하위 node 중복 소유 |
| completeness_review_ref=None | policy ID·명시적 scope/버전·검토 snapshot 불일치 |
| review_context 생략으로 실제 구현 검토 미확인 | 제공한 검토 묶음에서 명시 ref가 없거나 잘못 연결됨 |
| 모든 ID는 대응해도 목록/구현 검토가 미확인 | 미매핑 leaf/group, 잘못된 전체 결합·미지원 node |

현재 ConditionBinding은 implementation_review_ref가 필수여서 ref=None인 정상 Binding은 없다. 필수 ref 누락은 기존 모델 오류다. **문자열이 존재하는 것**과 **검토가 확인된 것**을 분리한다. 잘못된 자료를 SLICE로 낮춰서 숨기지 않는다.

## 5. Validator responsibility

**C 선택: 작은 domain 객체 + 순수 검증 결과.** EligibilityCoverage는 inventory와 bindings만 보존하고, 별도 evaluate_eligibility_coverage가 Policy·선택적 review_context를 받아 검증 결과를 만든다. domain 객체는 status를 갖지 않는다. BindingSet·동적 rule registry·workflow engine은 만들지 않는다.

모델의 책임은 타입·collection·조건 참조/중복의 로컬 정합성이다. tree/review 대조와 결과 생성은 순수 함수의 책임이다. 함수는 기존 모델 검증을 복제하지 않고, 명시적인 객체 타입과 객체 간 관계를 검사한다. UI·LLM·데이터 수집·개인 eligibility 평가·source 공식성 확인·benefit 금액 계산은 수행하지 않는다.

## 6. Condition-binding 대응

R은 inventory.conditions의 모든 condition_id 집합이다. REQUIRED와 CONDITIONAL을 모두 포함한다. I는 유효한 bindings의 condition_id에서 파생한다. 별도 implemented ID 목록을 입력받거나 저장하지 않는다.

Bindings가 A/C라면 I={A,C}, R={A,B,C}에서는 missing={B}다. 이때 Policy가 A/C만 구현하고 mapping/검토에 모순이 없으면 SLICE다. Binding의 condition_id가 R 밖이면 extra 구현으로 허용하지 않고 오류다.

I는 **구조적으로 매핑된 구현 집합**이다. 실제 검토가 없으면 완전한 의미 구현으로 인증하지 않고 unreviewed 표시를 함께 반환한다. missing과 unreviewed를 합쳐 하나의 수치로 숨기지 않는다.

## 7. Duplicate binding

한 condition_id에 Binding은 정확히 하나만 허용한다. 동일 객체·동일 값·다른 root/ref 모두 중복이면 오류다. dedupe·최신 선택·자동 merge는 없다. 별도 ConditionBindingSet 없이 tuple과 검증으로 충분하다.

서로 다른 condition에 같은 root를 지정한 경우는8~10절 subtree ownership 오류다. 같은 review ref가 여러 Binding의 검토를 가리키는 것은 가능하나, 제공된 검토 묶음에서 각 condition/root 대응이 실제로 확인되어야 한다.

## 8. Rule root lookup

기존 walk_nodes(policy.root)로 node_id→node lookup을 만든다. Binding의 rule_root_id가 없으면 오류다. leaf와 RuleGroup 모두 root로 허용한다. ID 명칭에 GROUP/LEAF가 들어 있는지로 종류를 추측하지 않는다.

Policy의 기존 생성자가 node ID 유일성을 검사한다. 정상 Policy의 유일성 검증을 새 규칙으로 바꾸지 않는다. 별도 객체/손상된 타입을 tree로 받지 않으며 미지원 node를 무시하거나 UNKNOWN으로 만들지 않는다. source evidence 조회나 정책 상태 계산도 호출하지 않는다.

## 9. Subtree ownership

Binding root 자체와 모든 descendant node가 그 condition의 소유다. leaf root는 자기 node 하나, group root는 group·중간 group·모든 leaf를 포함한다. leaf만 집계하여 group 중첩이나 재사용 충돌을 놓치지 않는다.

초기 전체 결합은 **Binding root들의 최상위 ALL**이다. 둘 이상 Binding이면 policy.root는 RuleGroup ALL이어야 하고 그 direct child ID 집합은 Binding root ID 집합과 정확히 같아야 한다. condition 내부의 ANY/ALL/NOT·중첩은 허용하고 전체 subtree 검토에 포함한다.

Binding 하나이면 (a) 그 root가 policy.root 자체인 단일 의미 조건 tree, 또는 (b) 최상위 ALL 아래 그 Binding root 하나인 형태를 허용한다. 단일 root binding이 실제로 여러 별도 의미조건을 숨기는지는 구현 검토에서 차단한다. R의 나머지 조건이 미구현이라 Binding 하나인 정상 slice도 표현할 수 있다. 실제로 다른 condition을 구현한 node가 있다면 별도 binding이 필요하다.

## 10. Overlap/shared rule 정책

서로 다른 Binding subtree의 node 집합 교집합이 비어 있지 않으면 오류다. 같은 root 두 번, 부모 group과 그 자식을 별도 condition으로 binding, nested child 재사용 모두 거부한다. **MVP에서는 공유 구현 예외를 허용하지 않는다.**

정책 전체 root를 한 condition에 binding하면서 다른 Binding도 존재하면 전체 root가 그 subtree를 포함하므로 overlap 오류다. DAG/shared predicate 지원은 필요가 확인된 이후의 별도 설계다. 기존 Rule Engine의 논리나 순회 자체를 바꾸지는 않는다.

## 11. Unbound tree rules

모든 tree node는 condition subtree 소유이거나 허용된 최상위 ALL 조합 root여야 한다. 그 외 eligibility leaf·group·보수적 추가 check가 있으면 **SLICE에서도 Data Error**다. 설명용/실험 rule은 평가 tree 밖에서 다룬다.

**zero bindings 결정:** 현재 Policy는 비어 있지 않은 tree를 요구한다. 따라서 policy가 필수인 이 API에서 bindings=()는 모든 node가 미매핑되어 오류다. Inventory와 빈 bindings의 계획 데이터 자체는 domain 객체에 보관 가능하지만 실행 Policy 검증 결과는 만들 수 없다. 향후 빈 Policy/항상 PASS placeholder를 추가해서 zero-binding SLICE를 만들지 않는다. 이는 기존 POLICY_COVERAGE_SPEC.md 24절과 같다.

Binding을 제거하고 해당 구현 node가 tree에 남아 있으면 drift 오류다. Binding과 해당 node를 모두 제거한 뒤 남은 tree가 다른 조건을 정확히 구현한다면 정상적인 missing SLICE다. 두 상황을 구별한다.

## 12. REQUIRED

REQUIRED에 Binding이 없으면 missing_condition_ids에 넣는다. 조건의 존재·공식 의미가 검토되어도 아직 구현되지 않은 것이므로 구조가 정상인 한 SLICE다. 누락을 사용자 FAIL/UNKNOWN으로 바꾸거나 자동 PASS leaf로 채우지 않는다.

## 13. CONDITIONAL

CONDITIONAL도 R에 포함한다. Binding 없으면 SLICE이며 “일반 사용자에게 비적용”이라는 이유로 제외하지 않는다. coverage는 사용자군마다 바뀌지 않는다.

Binding이 있으면 guard·적용·비적용 경로 전체가 해당 subtree로 대응되어야 한다. 이를 node 수나 root ID만으로 증명할 수 없다. implementation 검토는 분기·기준값·입력모델/evaluator 지원·기존3상태 진리표와 경계 테스트를 포함해야 한다. 자동 semantic proof나 새로운 conditional evaluator는 만들지 않는다.

## 14. Inventory completeness review

completeness_review_ref=None이면 모든 조건에 Binding이 있어도 **SLICE**다. R 자체의 완결성이 아직 확인되지 않았기 때문이다. ref가 있어도 review_context가 없으면 동일하게 검토 미확인이다.

Context가 주어지면 inventory_snapshot의 policy/scope/inventory_version·조건 의미/분류/evidence·completeness ref를 현재 inventory와 대조한다. ref 문자열만 비교하지 않는다. source bindings와 dataset 확인본·실제 검토 기록의 결합은 신뢰된 외부 준비 계층이 확인한 자료를 공급한다. 이 함수는 SourceRegistry에 접속하지 않는다.

명시적으로 제공한 Context가 다른 inventory/ref를 가리키면 오류다. ref=None인 inventory에 임의로 검토 완료를 선언하는 Context도 허용하지 않는다. None은 값으로 그대로 유지하고 검토한 구현의 확인만 제공할 수 있다.

## 15. Implementation reviews

**ref 존재만으로 FULL 불가.** review_context가 없으면 모든 Binding의 implementation refs를 unreviewed_binding_refs에 기록한다. 생성자에서 필수 문자열을 다시 optional로 만들지 않는다.

Context가 제공되면 bindings_snapshot에 현재 Binding들의 정확한 condition/root/ref 대응이 모두 있어야 한다. 부분 registry 공급은 초기 MVP에서 지원하지 않는다. 빠진 명시 참조·다른 root/condition/ref·여분의 Binding 확인본은 Data Error다. policy_snapshot과 현재 Policy 전체 값도 같아야 한다. ANY→ALL, 자식 삭제, 기준값/근거 변경은 ID가 같아도 drift 오류다.

Context는 해당 subtree의 모든 조건부 분기와 전체 조합이 공식 의미에 맞고 지원된 입력/evaluator로 실행된다는 **외부 검토의 완료 확인본**이다. 일부 경로만 검토했으면 이 완료 Context를 공급하지 않고 SLICE로 남긴다. 실제 불완전 subtree로 확인된 구현을 완료 Binding이라고 등록해서는 안 된다. Inventory/구현을 고쳐 재검토해야 한다.

구조적으로 같은 snapshot이라도 사람이 잘못 검토한 의미까지 함수가 자동으로 발견하지는 못한다. snapshot 대응과 실제 공식 완결성 검토의 신뢰를 구분한다. 서명·검토 플랫폼·네트워크 registry·자격판정 LLM을 추가하지 않는다.

## 16. FULL 조건

FULL_POLICY는 다음 모두를 충족한 성공 결과에서만 파생한다.

1. 입력 값 모델과 collection·정책 identity가 유효하다.
2. 모든 Binding은 R 안의 condition과 실제 root를 유일하게 참조한다.
3. subtree overlap·미매핑 node·전체 결합 모순이 없다.
4. R=I이며 REQUIRED/CONDITIONAL 누락이 없다.
5. completeness_review_ref가 있고 실제 제공된 Context의 목록 검토와 대응한다.
6. 모든 구현 ref·전체 Policy snapshot·지원 입력/evaluator 검토가 Context와 대응한다.
7. 고정 scope·inventory/rule/dataset/source 확인본 결합이 외부 검토와 일치한다.

이는 **선택한 scope의 자격조건 구현범위**다. benefit metadata·신청창·행정 지급 승인·사용자 PASS·배포 승인까지 뜻하지 않는다. 단순 constructor나 status=FULL 인자로 만들지 않는다.

## 17. SLICE 조건

구조가 정상이고 다음 중 하나라도 있으면 CONDITION_SLICE다.

- R−I가 비어 있지 않음.
- inventory 완결성 ref가 None이거나 검토 Context가 없어 완결성 미확인.
- 구현 refs는 구조적으로 있지만 Context가 없어 실제 구현 검토 미확인.

별도 BLOCKED/UNKNOWN coverage 상태는 추가하지 않는다. 구조적 오류가 있으면 SLICE 결과 대신 예외이며, 정상 오류와 미완료를 혼합하지 않는다.

## 18. Coverage result 구조

최소 구조 제안은 다음과 같다. 모두 아직 미구현이다.

| 객체 | 입력/보관 책임 |
|---|---|
| EligibilityCoverage | inventory + bindings만 보관. exact 타입/tuple, condition 존재·유일성의 로컬 정합성 검사. status 없음 |
| CoverageReviewContext | 2절의 명시적 검토 snapshot 묶음. 외부 검토 자료이며 자동 승인 아님 |
| EligibilityCoverageResult | coverage:EligibilityCoverage, policy_rule_version:str, review_context:CoverageReviewContext\|None. 순수 함수의 검증 성공 경로에서만 구성 |

Result의 policy_id/scope/inventory_version은 coverage.inventory에서, implemented_condition_ids는 bindings에서, missing_condition_ids는 R−I에서 파생한다. ID 목록과 refs는 정렬한 중복 없는 tuple이다. implemented/missing을 별도 저장하여 서로 어긋나게 하지 않는다. unreviewed_inventory는 ref=None 또는 Context 없음일 때 True, unreviewed_binding_refs는 Context가 없을 때 모든 Binding의 refs이고 검증된 Context가 있으면 빈 tuple인 읽기 전용 파생값이다.

status는 Result의 읽기 전용 파생 property로 둔다. `missing이 비고 unreviewed_inventory=False이고 unreviewed_binding_refs가 비었음`일 때만 FULL_POLICY다. 단 이 Result는 **tree/review 검증 성공 뒤 순수 평가 함수의 내부 factory 경로에서만 생성**하는 공개 계약이다. 일반 constructor에 status를 받지 않는다. 생성 통제가 외부 신뢰/보안 인증을 대신하는 것은 아니다.

review_context는 이미 전달받은 불변 객체를 참조하며 snapshot을 새로 복제하지 않는다. 감사용 to_dict에는 review_context=None 또는 dataset_version/source_bindings/implementation_contract_ref의 작은 metadata dict만 담는다. 원래 completeness/implementation refs는 inventory와 canonical bindings에서 추적한다. 전체 검토 Policy/원문·사용자 결과·외부 파일을 출력에 복제하지 않는다. 검토 미확인 결과도 원래 ref를 보존한다.

to_dict는 policy_id/scope/inventory_version/rule_version, canonical bindings, status, 파생 implemented/missing IDs, 검토 미확인 정보·검토 참조를 새 primitive dict/list로 반환하도록 제안한다. 반환 데이터 수정은 원본에 영향이 없어야 한다. FULL을 직접 지정하는 생성 경로는 공개하지 않는다.

## 19. Status naming

명세 호환성을 위해 **FULL_POLICY / CONDITION_SLICE**를 유지한다. 새 독립 EligibilityCoverageStatus 후보로 두며 현재 Envelope의 EvaluationScope Enum을 변경하지 않는다. “FULL_POLICY for 2026-Q3 eligibility”처럼 scope와 자격축을 함께 표시한다.

FULL_ELIGIBILITY로 이름을 바꾸면 기존 Acceptance/Bridge 설계와 매핑 비용만 생긴다. 명칭의 한계는 축과 scope의 명시로 해결하며 신청/혜택 운영기능 완성을 뜻하지 않도록 한다.

## 20. PolicyCoverage legacy 관계

기존 PolicyCoverage(included_rule_ids, excluded_conditions)와 Envelope.evaluation_scope=CONDITION_SLICE는 그대로 유지한다. 새 EligibilityCoverage/Result는 독립 계층이며 legacy를 삭제·교체하지 않는다. policy-data-1.0에 키/Enum을 슬쩍 추가하지 않는다.

현재 Envelope의 source_bindings는 실제 leaf의 source 집합과 같아야 하고 last_verified_at도 leaf 기준이다. inventory의 추가 조건 근거를 legacy binding에 합치면 기존 검증과 충돌하므로 별도로 검토한다. 새 결과를 실제 Envelope/Manifest/fingerprint/serializer로 연결하는 migration은 후속 승인 작업이다. 첫 합성 구현의 선행조건이 아니다.

## 21. Scope

핵심 API의 scope는 오직 inventory.scope에서 가져온다. Q3/annual override·신청일/현재 날짜 기반 선택은 없다. Policy 자체에는 edition/quarter가 없어 그 객체만으로 scope 진위를 증명할 수 없다.

따라서 FULL에는 Context의 inventory scope와 해당 Policy snapshot의 검토 대응이 필요하다. Q3 확인본을 annual inventory로 바꿔 공급하면 Context 대조 오류다. review_context가 없으면 scope를 보존해 구조 SLICE만 반환할 수 있고 FULL을 만들 수 없다.

실제 연결 단계에서는 별도의 Envelope 경계가 inventory.scope.edition_id와 Envelope.edition_id, 명시한 회차·dataset/rule/source 결합을 확인해야 한다. Envelope의 연도 문자열만으로 Q3를 증명하지 않는다. 이 adapter는 이번에 설계 범위를 넓혀 구현하지 않는다.

## 22. Policy ID

inventory.policy_id == policy.policy_id가 필수다. 불일치는 Data Error이며 자동 교정/다른 정책 lookup은 없다. Context의 inventory/policy snapshot도 같은 대상을 가리켜야 한다. condition_id가 정책 간 우연히 같다고 같은 정책으로 취급하지 않는다.

## 23. Current Ansan example

**문서상 대입**이다. 실제 inventory/Binding/Context 객체나 JSON은 생성하지 않는다. 현재002는 DRAFT/CONDITION_SLICE, edition2026, r0002, 명시적 Q3의 ALL(resident,birth)다. 의미상 구현은 현재 안산 주민등록과 Q3 출생일 두 조건이다.

기존 분석의 최소 후보 목록에는 경기도 거주기간과 국적/등록분류 관련 조건이 미구현이며, 최종 공식 inventory 완결성도 아직 확인되지 않았다. 두 실제 leaf를 두 독립 의미 조건에 대응시킬 수 있지만 나머지 missing과 목록/구현 검토 한계가 남으므로 **SLICE 예상, FULL 불가**다.

이는 기존 actual data에서 새 validator를 실행한 결과가 아니다. 원문 source VERIFIED·두 leaf PASS가 FULL/VERIFIED/ACCEPTED를 만들지 않는다. 현재 현금 반영액0도 유지한다. 001 resident-only snapshot을 수정하거나 새 scope를 자동 부여하지 않는다.

## 24. ResidenceHistory unresolved

OFFICIAL_INQUIRY_REQUIRED 상태인 기간 조건은 필요한 inventory 후보에 남고 Binding은 없다. 구조가 정상인 대응에서는 missing_condition_ids로 설명하면 충분하다. 별도 runtime BLOCKED_BY_OFFICIAL_INQUIRY 상태는 만들지 않는다.

공식 산식·기산·경계가 정해지지 않은 것은 사용자 데이터 부족 UNKNOWN이 아니다. 개발 보류/문의 내용은 기존 문서에서 추적한다. 이를 항상 UNKNOWN을 반환하는 구현으로 등록하지 않는다. Fact/Rule/Evaluator·actual inventory/coverage를 추가하지 않는다.

## 25. Verification 독립성

Coverage FULL + Envelope DRAFT는 구조상 가능하지만 Acceptance 불가다. Coverage SLICE + Envelope VERIFIED도 Acceptance 불가다. FULL + VERIFIED 역시 혜택 정의·검토 수용·개인/월 적용과 Bridge 유형 필터를 대신하지 않는다.

Context의 source 검토 결합은 공식 의미 대응의 확인본이다. source freshness·운영 수용·철회/만료 검증은 별도 외부 경계에서 수행한다. Coverage 함수는 현재시간이나 verification 상태를 조회하지 않는다.

## 26. PolicyEvaluation 독립성

Coverage는 정책 구현과 검토 자료에 대한 결과이므로 같은 inventory/bindings/tree/review_context에서는 사용자 PASS/FAIL/UNKNOWN과 무관하게 동일하다. 사용자의 나이·주소·소득·가구·생년월일·신청일을 받거나 읽지 않는다.

FULL이라도 사용자 사실이 없으면 실제 평가 UNKNOWN이 가능하다. SLICE여도 구현한 조건만 PASS일 수 있다. 두 결과를 섞거나 coverage 이유를 사용자 판정 reason으로 넣지 않는다.

## 27. Determinism

동일 inventory/bindings/Policy/선택적 Context → 동일 결과다. 검토 자료가 달라지면 결과가 달라질 수 있으므로 세 입력만 같다는 이유로 검토 결과까지 같다고 주장하지 않는다.

입력 Inventory의 조건 순서와 tuple은 변경하지 않는다. domain 객체 equality/원래 to_dict는 순서를 보존한다. 평가 결과의 의미상 ID·bindings·검토 이유 목록은 canonical condition/ref 순서로 출력하므로 조건/Binding collection 순서만 달라지면 status·전체 result.to_dict의 의미상 내용은 동일하다.

Context 비교도 inventory 조건은 condition_id별 값, bindings는 condition_id별 세 필드를 비교하여 목록 순서만으로 검토를 무효화하지 않는다. 조건 내부 evidence 순서·Policy tree의 자식 순서/구조·기준값은 검토한 snapshot 그대로 대조한다. source bindings는 ID/version 집합으로 대조하되 중복은 오류다. 오류가 여러 개면 같은 입력 순서에 대한 첫 오류는 결정적이며 모든 오류 수집 framework는 필요 없다.

## 28. Validator API

최종 추천 API 후보는 다음과 같다. **미구현**이다.

```text
evaluate_eligibility_coverage(
    inventory: ConditionInventory,
    bindings: tuple[ConditionBinding, ...],
    policy: Policy,
    *,
    review_context: CoverageReviewContext | None = None,
) -> EligibilityCoverageResult
```

내부에서 작은 EligibilityCoverage domain 값을 구성하고 로컬/교차 검증한 뒤 결과를 생성한다. review_context=None은 “검토 미확인”이며 FULL을 허용하지 않는다. Context가 있으면 해당 객체가 명시적으로 공급한 모든 refs/snapshots를 검증하고 잘못된 것을 생략하거나 정상 미완료로 숨기지 않는다.

오류는 기존 PolicyDataError를 기본으로 사용한다. 메시지에서 field/검증 종류를 식별하고 전체 payload를 복사하지 않는다. 구조 오류에서 정상 결과·부분 합계·UNKNOWN은 반환하지 않는다. 파일 I/O·SourceRegistry 조회·현재 날짜·사용자 profile·정책 재평가·네트워크·LLM은 없다.

## 29. Tree traversal 재사용

기존 models.walk_nodes를 재사용해 전체 lookup 및 각 Binding root의 subtree node 집합을 만든다. RuleGroup에서만 재귀하고 leaf 자체도 yield하는 기존 의미를 유지한다. 별도 재귀 engine이나 문자열 기반 rule_type registry를 추가하지 않는다.

정확한 지원 node 목록은 현재 RuleNode인 PolicyRule/ResidentRegistrationRule/BirthDateRule/RuleGroup과 맞춘다. walk_nodes 자체가 미지원 객체를 명시적으로 거부하는 validator는 아니므로 core 입력은 기존 Policy 모델을 전제로 하고, 방어 검사에서는 미지원 node를 오류로 처리한다. 기존 중복 ID validation·3상태 집계·evaluator/routing은 변경하지 않는다.

## 30. 수동 시나리오

**52개 문서상 사례이며 신규 실행 테스트가 아니다.** C는 서로 다른 합성 의미조건, L은 합성 leaf, G는 합성 group이다. FULL 사례는 유효한 동일 scope의 inventory/구현 검토 Context와 공식 근거·입력/evaluator 지원 검토가 완료됐다고 가정한다. 실제 안산 승인 자료가 아니다.

| ID | 사례 | 기대 |
|---|---|---|
| EC01 | R={A}, A→L, policy.root=L, 검토완료 | FULL_POLICY |
| EC02 | REQUIRED A+CONDITIONAL B, root ALL(LA,GB), 모두 검토완료 | FULL_POLICY |
| EC03 | R={A,B}, A만 binding, tree=LA | SLICE, missing B |
| EC04 | CONDITIONAL B 미구현, tree에는 A만 | SLICE, missing B |
| EC05 | 모두 binding, completeness ref=None | SLICE, unreviewed_inventory |
| EC06 | R4/I1, tree는 그 한 조건만 | SLICE, missing3 |
| EC07 | 비어 있지 않은 Policy, bindings=() | unbound node Data Error; 계획 domain만 보관 가능 |
| EC08 | Binding의 condition X가 inventory에 없음 | Data Error |
| EC09 | 같은 condition Binding 두 개, 내용 동일 | Data Error, dedupe 없음 |
| EC10 | binding root가 tree에 없음 | Data Error |
| EC11 | inventory.policy_id와 policy.policy_id 다름 | Data Error |
| EC12 | A→group, B→그 descendant | overlap Data Error |
| EC13 | A/B가 같은 root | ownership Data Error |
| EC14 | tree LA/LB/LC, bindings A/B만 | LC unbound Data Error |
| EC15 | 미지원 tree node 주장 | Policy 생성 또는 core 타입 검사에서 오류 |
| EC16 | condition→leaf | 허용; 다른 gate도 충족하면 FULL |
| EC17 | condition→ANY group+두 자식 | subtree 전체 ownership, 검토 대응 필요 |
| EC18 | condition→중첩 NOT/ANY/ALL | subtree 전체 검토와 일치하면 허용 |
| EC19 | group binding | group 자체·모든 중간/leaf node가 같은 condition 소유 |
| EC20 | Q3 inventory와 Q3 검토 snapshot | scope gate 통과 |
| EC21 | 독립 ANNUAL inventory와 해당 검토 snapshot | 별도 범위, 모든 조건 검토 시 FULL 가능 |
| EC22 | Q3 검토 snapshot을 ANNUAL inventory에 연결 | scope 검토 불일치 Data Error |
| EC23 | CONDITIONAL 전체 분기 구현/검토 | 완료 조건으로 인정 가능 |
| EC24 | CONDITIONAL Binding 없음 | SLICE |
| EC25 | 일부 분기 검토만 되어 완료 Context 없음 | SLICE; 부분 구현을 완료로 인증하지 않음 |
| EC26 | 현재 안산002 resident+birth 의미상 대입 | missing/목록 검토 한계로 SLICE 예상, 실제 실행 아님 |
| EC27 | residence duration 미구현 | missing, FULL 불가 |
| EC28 | inventory 전체 목록 검토 미확정 | 모든 Binding이 있어도 SLICE |
| EC29 | FULL coverage / DRAFT Envelope | 가능, Acceptance 불가 |
| EC30 | SLICE coverage / VERIFIED Envelope | 가능, Acceptance 불가 |
| EC31 | 같은 tree/reviews, 사용자 PASS | coverage 변화 없음 |
| EC32 | 같은 tree/reviews, 사용자 FAIL | coverage 변화 없음 |
| EC33 | 같은 tree/reviews, 사용자 UNKNOWN | coverage 변화 없음 |
| EC34 | 동일 입력 반복 | 동일 status/결과 값 표현 |
| EC35 | Binding tuple 순서만 변경 | canonical 결과 동일, 원래 입력 불변 |
| EC36 | Inventory condition 순서만 변경 | Inventory 값 순서는 다르지만 coverage 의미/출력 동일 |
| EC37 | completeness ref 및 대응하는 검토 Context 존재 | 목록 검토 gate 통과 |
| EC38 | completeness ref=None | SLICE, 참조 자동 생성 없음 |
| EC39 | Binding ref는 정상 문자열, Context 생략 | SLICE, 해당 ref를 unreviewed로 보존 |
| EC40 | binding 없이 새 leaf 추가 | metadata drift Data Error |
| EC41 | Binding만 제거하고 tree는 유지 | unbound node Data Error |
| EC42 | nested child를 다른 condition에 재사용 | overlap Data Error |
| EC43 | 기존 legacy PolicyCoverage | 필드/validator/serializer/Enum 변경 없음 |
| EC44 | 실제 release001/002 | bytes·schema·DRAFT/slice 불변 |
| EC45 | 이번 작업 범위 | ResidenceHistory 코드/actual inventory 추가 없음 |
| EC46 | Context 제공했는데 특정 Binding ref/snapshot 없음 | broken review correspondence Data Error |
| EC47 | ANY→ALL 변경, root ID 동일 | review snapshot drift Data Error |
| EC48 | 모든 bindings 존재, Context 없음 | SLICE; ID equality만으로 FULL 금지 |
| EC49 | 정책 전체 root binding + 다른 Binding | overlap Data Error |
| EC50 | 여러 Binding인데 최상위 ANY | 최소 전체 결합 계약 위반 Data Error |
| EC51 | missing node와 그 Binding 모두 제거, 다른 조건 tree 유지 | 정상 SLICE |
| EC52 | 같은 refs라도 다른 rule version/기준값/Policy 확인본 | review 결합 불일치 Data Error |

review Context가 없는 구조적으로 정상 상태와 제공된 검토 자료가 모순인 오류를 구별한다. source freshness·benefit·개인 판정·행정 의미의 진위를 이 표가 자동 검증한다고 주장하지 않는다.

## 31. 미해결 문제

**이번 설계에서 확정:** subtree 전체 소유·겹침 금지, top ALL/단일 조건 예외, 미매핑 node는 오류, missing/미검토는 SLICE, 검토 snapshot 없는 FULL 금지, scope는 inventory 소유, legacy 독립 유지다. 첫 합성 구현에 앞서 ownership/legacy migration을 더 결정할 필요는 없다.

**후속 구현의 순서:** EligibilityCoverage 구조 모델 → 구조/tree 검증 → 검토 Context/결과 계층 → FULL 파생을 작은 승인 단위로 구현할 수 있다. Context 및 결과는2·18절의 값 계약을 따른다. Context가 아직 준비되지 않은 중간 구현에서는 FULL을 비활성화하고 SLICE/구조 오류까지만 검증해야 한다. 문서의 READY를 한 번에 전부 구현하라는 지시로 해석하지 않는다.

**외부 연결의 미구현 사항:** 실제 inventory 완결성 검토·조건별 공식 산식·지원 input/evaluator 증명·source/dataset 확인본 공급·검토 기록의 사실성과 철회 관리는 기존 외부 검토 경계에 남는다. Policy만으로 edition/source 진위를 증명할 수 없고 내부 Context도 임의 요청 payload를 신뢰해서는 안 된다. 향후 실제 Envelope adapter에서 정확한 결합을 검증한다. 새 verification/acceptance workflow를 선행 구축하지 않는다.

**Assumption A1:** 초기 모델은 분리된 의미조건 subtree와 최상위 ALL 구조에 한정하며 공유 구현은 없다. **Assumption A2:** 검토 Context는 이미 실제 검토를 마친 신뢰된 내부 자료로 명시적으로 제공한다. 타입 생성이나 문자열 ref만으로 신뢰가 생긴다고 가정하지 않는다. 두 전제 밖의 정책은 자동 수용하지 않고 별도 검토한다.

실제 안산 정책은 거주기간 공식 의미와 목록 완결성이 미확정이다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**이며 현재 FULL은 불가하다. 실제 release migration·새 inventory·Binding·Context를 생성하지 않는다.

## 32. 최종 판단

**READY_TO_IMPLEMENT_ELIGIBILITY_COVERAGE**

이 문서만 추가했다. 모든 기존 모델/코드/테스트/actual releases는 보존한다. 이 판단은 합성 데이터로 구조 모델과 검증 책임을 단계적으로 구현할 준비이며 실제 정책 FULL/수용/현금 적용 승인이 아니다.

다음 가장 작은 작업 한 개: **EligibilityCoverage(inventory, bindings) 불변 구조 모델만 구현**한다. exact 타입·tuple·inventory 안 condition 존재·중복 condition binding을 검사하고 빈 bindings는 계획 값으로 허용한다. Policy/tree를 받거나 status를 만들지 않는다. tree 검증·검토 Context·FULL 파생은 그 다음 별도 단계다.

### 검증 기록

기존 전체 pytest는 **3199 passed in 9.07s**다. 신규 실행 테스트는 추가하지 않았다. 문서의32개 필수 절과 EC01~EC52의 순서·중복·누락 여부 및 한국어 표기를 확인했다. 이 결과는 아직 없는 Coverage validator의 실행 검증을 의미하지 않는다.

작업 전 backend/tests/data/docs의 기존 **106개 파일 SHA256이 모두 동일**하고 수정·삭제는 없다. 추가는 이 문서 한 개다. 기존 coverage 값 모델/Policy/RuleNode/Envelope·평가/loader·Cashflow·actual releases·테스트·기존 명세·ResidenceHistory 관련 자료를 보존했다.

## 33. M2.11 — IMPLEMENTED: EligibilityCoverage 구조 모델

policy_data/coverage.py에 `EligibilityCoverage(inventory: ConditionInventory, bindings: tuple[ConditionBinding,...])` frozen/slots dataclass 하나를 추가했다. 두 인자 모두 필수이며 추가 필드·property·상태·계산 helper는 없다. policy_data 공개 export로 제공한다.

기존 eligibility_coverage.py는 ApplicabilityScope와 그 모듈 경계 테스트가 있으므로 변경하지 않고 같은 패키지의 작은 coverage.py를 사용했다. Scope/RequiredCondition/ConditionInventory/ConditionBinding과 기존 테스트를 수정·재배치하지 않았다.

inventory와 bindings는 exact 타입만 허용하며 원래 객체·tuple·원소를 그대로 보존한다. list/set/dict/generator/None/하위 타입을 변환하지 않는다. 빈 bindings는 유효한 계획 값이다. 일부 REQUIRED/CONDITIONAL의 Binding이 없어도 생성 가능하며 누락 목록이나 상태를 계산하지 않는다.

생성자는 inventory 안 condition 존재와 동일 condition_id의 Binding 중복만 로컬 참조 정합성으로 검사한다. 동일 객체/동일 값/다른 root·review의 중복 모두 오류다. 서로 다른 조건의 같은 rule_root_id는 허용한다. root ID의 존재·동일 subtree 소유·겹침은 후속 Policy validator 책임이다.

completeness_review_ref=None과 아직 조회하지 않은 implementation_review_ref도 보존한다. 검토 참조의 실제 존재·tree와의 대응·검토 완료를 판단하지 않는다. 생성 성공은 **구조 입력의 로컬 정합성**이며 검증 완료/FULL/SLICE/사용자 자격/수용 승인이 아니다.

### Constructor responsibility matrix

| 검증 | Constructor — 이번 구현 | Future Validator — 미구현 |
|---|---|---|
| inventory type | exact ConditionInventory 필수 | 검증된 모델 사용; API 자체 입력 타입은 경계에서 확인 |
| bindings tuple type | exact tuple 필수, 빈 tuple 허용 | 검증된 구조값 사용 |
| binding element type | exact ConditionBinding 필수 | 검증된 구조값 사용 |
| duplicate condition_id | 동일 내용도 PolicyDataError | 로컬 검사를 중복 구현하지 않음 |
| unknown condition_id | inventory에 없으면 PolicyDataError | 로컬 검사를 중복 구현하지 않음 |
| missing condition binding | 허용, 누락 목록 미계산 | 후속 결과에서 누락·완결성 파생 |
| policy ID match | Policy 입력/직접 policy_id 필드 없음 | 명시적 Policy와 inventory.policy_id 대조 |
| root exists | 조회하지 않음 | 실제 tree node 존재 확인 |
| same root / different conditions | 값으로 허용 | ownership 검증에서 거부 |
| subtree overlap | 검사하지 않음 | 전체 subtree 집합 대조 |
| unbound tree rule | 검사하지 않음 | 실제 tree와 mapping 대조 |
| inventory review None | 허용, 완료 여부 미판정 | 목록 검토 gate에서 FULL 불가 사유로 처리 |
| review snapshot | 입력/조회/판정 없음 | 명시적 ReviewContext의 확인본 대조 |
| FULL/SLICE | 필드·property·계산 없음 | 검증 성공 뒤 별도 결과에서 파생 |

생성자 내부의 inventory ID 임시 집합과 중복 탐지용 지역 set은 참조 검사에만 사용하고 저장하지 않는다. implemented/missing/bound/unbound condition IDs의 필드·property를 만들지 않는다. scope/policy_id/inventory_version도 inventory에서만 접근하며 직접 복사/노출 property가 없다.

입력 순서와 기본 dataclass equality를 유지한다. 같은 Inventory에 Binding 순서가 다르면 다른 구조 값이다. semantic 순서 동등성은 후속 결과 책임이다. to_dict는 정확히 inventory/bindings 두 key의 새 중첩 dict/list를 반환하며 기존 하위 to_dict를 재사용한다. evidence·scope·Binding snapshot을 수정해도 원본은 불변이다.

오류는 기존 PolicyDataError다. 필수 인자 누락/정의되지 않은 인자는 Python TypeError다. 하위 모델 validation을 재실행하지 않고 원래 ID/전체 payload를 예외 문장에 넣지 않는다. Policy/RuleNode/순회·ReviewContext·SourceRegistry·시스템 시각·환경·파일·네트워크·Acceptance·Cashflow를 직접 사용하지 않는다.

**빈 Binding과 향후 평가의 구별:** 이번 단계는 bindings=()의 표현 가능성만 확정한다. M2.10 11절처럼 비어 있지 않은 실행 Policy를 필수 입력으로 받는 후속 검증에서는 미매핑 node 오류가 될 수 있다. M2.11 지시문의 ‘향후 SLICE’ 표현을 실제 tree 검증 생략으로 해석하지 않으며, 해당 후속 API의 최종 책임은 구현 전에 기존 명세와 함께 재확인한다. 이번에는 어느 판정 경로도 추가하지 않았다.

IMPLEMENTED: 기존 네 값 모델, EligibilityCoverage 구조·exact 타입·condition 참조/중복 검증·불변성·순서 보존·중첩 snapshot·합성 단위 테스트.

NOT IMPLEMENTED: CoverageReviewContext, CoverageResult, evaluate_eligibility_coverage, tree lookup/ownership/overlap/unbound 검증, FULL/SLICE·missing/implemented 파생, Acceptance, Bridge, actual 안산 coverage. legacy PolicyCoverage/Envelope와 실제001/002는 불변이다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 유지한다.

작업 전: backend/tests/data/docs 107개 파일과 실제 두 release 파일을 SHA256 기준선으로 기록했고, coverage 값 모델은 eligibility_coverage.py/required_condition.py/condition_inventory.py/condition_binding.py였다. 기존 전체 **3199 passed in 8.81s**. 신규 tests/test_eligibility_coverage_structure.py **83 passed in 0.34s**. 빈/부분/전체·조건부·Q3/annual·미검토·같은 root·중복/unknown·exact 타입/하위 타입·순서/equality·불변성·출력 독립성·금지 필드/직접 의존 부재를 확인했다. 실제 정책 자료로 테스트하지 않았다.

최종 판단: **READY_FOR_COVERAGE_REVIEW_CONTEXT**. FULL 파생에는 필수 ref의 존재와 실제 검토 확인본을 구분하는 Context가 필요하므로, 현재 입력 구조에서 바로 validator로 이동하지 않는다. 다음 가장 작은 작업은 CoverageReviewContext의 최소 필드·확인본 결합·구조 검증 책임을 문서로 구체화하는 것이다. Context/Result/tree validator 코드는 포함하지 않는다.

### M2.11 최종 검증 기록

전체 pytest는 **3282 passed in 8.55s**다. 기존3199개와 신규83개가 모두 통과했으며 기존 테스트/기대값은 수정하지 않았다. 기존 네 coverage 값 모델의 코드·직렬화·테스트도 변경하지 않았다. 변경 파일의 한국어 표기와 새 모델의 직접 의존·금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 107개 파일의 SHA256을 대조했다. 기존102개는 동일하고 변경은 policy_data 공개 export 한 파일과 승인된 문서 네 파일이다. 신규 모델·테스트 두 파일만 추가했으며 삭제는 없다. actual release001/002 전체 파일, legacy PolicyCoverage/Envelope, Policy/RuleNode/evaluator/loader, Cashflow, 기존 테스트, Acceptance/Benefit 명세와 ResidenceHistory 관련 자료는 바이트 단위 동일하다.

## 34. M2.13 — IMPLEMENTED: 독립 Inventory review 값

policy_data/coverage_review.py에 InventoryCompletenessReview만 추가했다. COVERAGE_REVIEW_CONTEXT_SPEC.md 6절의 아홉 필수 필드로 검토 대상 policy/scope/inventory·자료 확인본 지문·날짜·참조를 명시적으로 기록한다. 기존 EligibilityCoverage와 다른 값 모델은 변경하지 않았다.

모델은 문자열/ID/version·두 lowercase SHA256 지문 형식·exact Scope/date만 검증한다. 실제 Inventory/Registry 지문 계산·ref resolution·현재 대상과의 일치·stale·사람의 검토 사실은 검사하지 않는다. Record 생성 성공을 Coverage 완료로 해석하지 않는다.

IMPLEMENTED: InventoryCompletenessReview structural model/합성 테스트182개. NOT IMPLEMENTED: ImplementationBindingReview/Context/Result/지문 계산/tree validator/FULL·SLICE 파생/Acceptance/Bridge. actual records/releases와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED 보류는 유지한다. 정확한 필드·검증·전체 회귀 기록은 COVERAGE_REVIEW_CONTEXT_SPEC.md 32절이다.

## 35. M2.14 — IMPLEMENTED: 독립 Implementation review 값

policy_data/implementation_review.py의 ImplementationBindingReview는 최우선 COVERAGE_REVIEW_CONTEXT_SPEC.md 7절의15필드를 명시적으로 받는 불변 record다. Inventory version/지문, rule version, policy_tree_fingerprint/subtree_fingerprint, dataset/source/implementation 확인본을 모두 보존한다. 실제 Binding/Inventory/Policy/tree를 받거나 조회하지 않는다.

생성자는 exact Scope/date·문자열/ID/version·지문5종의 형식만 확인한다. 기존 Policy.rule_version과 같은 비공백 문자열 계약을 유지하며 Envelope의 별도 canonical version 제한을 도입하지 않는다. review 생성 성공은 구현 정답·실제 사람 검토·artifact 존재·현재 snapshot 일치·FULL을 보증하지 않는다.

IMPLEMENTED: InventoryCompletenessReview(변경 없음), ImplementationBindingReview 구조·불변성·새 중첩 직렬화·합성 테스트216개. NOT IMPLEMENTED: fingerprint calculators, CoverageReviewContext, matching/stale, CoverageResult, Coverage validator, FULL/SLICE, Acceptance/Bridge.

기존 Inventory review 모듈/테스트를 변경하지 않고 sibling 파일과 public export를 추가했다. actual releases와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 상세 검증 기록은 COVERAGE_REVIEW_CONTEXT_SPEC.md 33절이다. 다음 collection 모델에서도 현재 Coverage/Policy와의 대조는 후속 validator 책임으로 남긴다.

## 36. M2.15 — IMPLEMENTED: 독립 ReviewContext collection

policy_data/coverage_review_context.py의 CoverageReviewContext는 최우선 COVERAGE_REVIEW_CONTEXT_SPEC.md 13절의 일곱 필수 필드를 가진 frozen/slots 값이다. policy_id/scope/dataset_version/source_registry_fingerprint/implementation_fingerprint와 두 review tuple을 명시적으로 받는다.

생성자는 exact 타입·정확한 종류의 record·policy/scope 값 일치·두 tuple 전체 review_ref 유일성만 검사한다. 빈 tuple은 허용하고 원래 tuple/record/Scope 객체·순서를 보존한다. 다른 버전/dataset/지문의 과거 record도 소속과 ref가 정상이라면 허용한다. 이 허용은 현재 Coverage와 내용이 일치한다는 뜻이 아니다.

Context는 Coverage/Policy를 받지 않는다. lookup helper·지문 계산/대조·version matching·stale/missing·상태 파생은 없다. 미참조 record도 구조 오류이면 전체 Context를 거부하며 자동 필터/dedupe/최신 선택은 하지 않는다. 새 중첩 to_dict만 제공한다.

IMPLEMENTED: 두 review 모델(변경 없음), CoverageReviewContext collection/로컬 참조 유일성/소속/불변성/직렬화/합성 테스트127개. NOT IMPLEMENTED: fingerprint calculators, review matching/stale, CoverageResult, Coverage validator, FULL/SLICE, Acceptance/Bridge. 기존2절 snapshot 제안은 M2.12 이후의 종류별 record와 지문 결합으로 구체화됐고, Context 구현 자체가 기존18절 Result gate를 완성하지는 않는다.

actual releases와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED를 유지한다. 상세 계약·검증 기록·다음 지문 명세 작업은 COVERAGE_REVIEW_CONTEXT_SPEC.md 34절이다.

## 37. M2.39 — IMPLEMENTED: 공개 eligibility coverage 검증 진입점

공식 public API는 policy_data/eligibility_coverage_evaluator.py의 **evaluate_eligibility_coverage(coverage, policy, review_context=None) -> EligibilityCoverageResult**다. coverage/policy는 필수이며 추가 옵션/입력 변환은 없다. policy_data 공개 export에 추가하고 기존 private Gate/factory는 공개하지 않는다.

evaluator는 기존 Integration Gate를1회 호출해 얻은 원본 findings를 기존 Result factory에1회 전달하고 원본 Result를 반환한다. 별도 pre-validation·구조/지문/Review 검사·findings 변형·status 파생·직접 constructor·catch/retry를 추가하지 않는다. Gate 실패면 factory0회, factory 실패면 재시도 없이 원본 예외 전파다.

M2.10의 과거2·18·28절 입력/전체 snapshot/Result/API 후보 대신, 현재 Coverage/Review 모델과 ELIGIBILITY_COVERAGE_RESULT_SPEC.md36~37절의8필드 Result·정확한 condition/root/ref 대응·파생 상태·공개 API를 적용한다. 과거 zero Binding/미매핑 항상 오류·direct-child ALL 제한·Context 존재만으로 FULL이라는 후보는 이미 후속 structure/integration/result 명세가 대체했으며 새 evaluator가 복원하지 않는다. legacy Envelope/JSON 형식은 변경하지 않는다.

실제 합성 current 지문과 두 Review record 타입으로 Gate→factory 전체 경로를 실행해 FULL/정상 SLICE/오류 분리를 검증했다. Context None·missing/미선언/STALE·incomplete U/G는 정상 Result가 될 수 있고, 잘못된 대상/참조/소유·complete U/G·같은 version 지문 모순은 PolicyDataError다. 결과의 FULL은 scope가 고정된 eligibility coverage만 뜻하며 사용자 PASS/VERIFIED/수용/현금 적용으로 확대하지 않는다.

신규 evaluator 테스트67개와 전체5687개가 통과했다. 기존5620개·Result226개·Gate107개·하위 회귀/golden은 변경 없이 유지한다. 상세 호출 횟수·객체 identity·오류·결정성·변경 범위 기록은 ELIGIBILITY_COVERAGE_RESULT_SPEC.md37절이다.

IMPLEMENTED: public pure evaluator 및 기존 Gate→factory 연결. NOT IMPLEMENTED: Verification·Acceptance·Benefit Bridge/Cashflow·actual Ansan FULL. 실제 정책자료는 유지하며 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**는 계속 보류한다. 최종 판단은 **ELIGIBILITY_COVERAGE_CORE_COMPLETE**다.


