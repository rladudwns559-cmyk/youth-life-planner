# Generic Eligibility Coverage Core — Audit & Freeze / M2.40

작성 완료일: **2026-10-22 / Asia/Seoul** (감사 시작: 2026-10-21). 기준 구현: **M2.39**.

**최종 판단: ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**.

Generic core는 **FROZEN**이며 실제 안산 정책은 **FULL_POLICY가 아니다**. 실제 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, 실제 안산 coverage는 **BLOCKED_ON_OFFICIAL_RESIDENCE_SEMANTICS**라는 개발/감사 표기로 구분한다. 이 표기는 새로운 runtime Enum이나 계산 결과가 아니다.

이번 작업은 **문서 한 개 추가**다. 코드·테스트·기존 명세·actual releases를 변경하지 않는다. 새로운 정책 판정/금액/검토 기록·실제 CoverageResult를 생성하지 않는다.

## 1. 목적·감사 방법·기준 문서

동결 대상은 “현재 테스트가 통과한다”는 사실에 더해 **Contract / Implementation / Trust Boundary**가 일치하는 범위다. 앞으로 Acceptance 등 다른 subsystem을 개발하면서 Coverage 의미·오류·지문·공개 API가 조용히 바뀌지 않도록 기준을 확정한다.

감사 방법은 현재 source/export/값 필드/호출 순서/예외 분기/테스트를 읽어 유효 명세와 대조하고, 작업 전후 전체 pytest·기존 파일 SHA256·actual release metadata를 비교하는 것이다. 테스트 통과만으로 공식 완결성·외부 검토 수행·운영 안전성을 인증하지 않는다.

다음 **15개 문서 전부를 재확인**했다. 과거 후보 문구를 현재 계약과 혼합하지 않고 명시된 supersede와 최신 구현 기록을 따른다.

| Source of Truth | 감사에 사용한 현재 계약/범위 |
|---|---|
| POLICY_COVERAGE_SPEC.md | 3~10·13~24절의 자격축/범위/검토/수용 분리, 31~35절 값 모델 |
| ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md | 3~6·18~29절의 과거 후보와37절 공개 진입점 |
| COVERAGE_REVIEW_CONTEXT_SPEC.md | 3~24·32~34절의 검토 의미/정확한 refs/현재 baseline/외부 신뢰 |
| COVERAGE_FINGERPRINT_SPEC.md | 3~19·24~29·33~35절의 payload/bytes/golden/보안 경계 |
| COVERAGE_REVIEW_MATCHING_SPEC.md | 3~6·18~23·29·39~42절의 상태·독립 guarded comparisons·slot API |
| COVERAGE_RULE_ROOT_LOOKUP_SPEC.md | 4~16·20·33절의 exact ID/원본 root/전체 타입·중복 방어 |
| COVERAGE_OWNERSHIP_SPEC.md | 2~18·25·34절의 root+descendants/겹침/고정 오류 |
| COVERAGE_UNMAPPED_RULE_SPEC.md | 3~18·31·35절의 leaf target/M 의존 승격·과거 계약 대체 |
| COVERAGE_STRUCTURE_ORCHESTRATION_SPEC.md | 3~23·28·32절의 canonical pairs/M/U/오류 순서 |
| COVERAGE_INTEGRATION_GATE_SPEC.md | 4~25·30·34·38~40절의 composition/통합 순서/findings |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md | 8~18·23~25·32~33·36~37절의8필드/상태/생성/공개 연결/한계 |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md | 2~11·15~20·26절의 독립 수용/정확한 version/source/외부 검토 |
| CASHFLOW_BENEFIT_BRIDGE_SPEC.md | 2~17·24절의 사용자/월 적용·현금 유형·오류/정상 제외 |
| DATA_MODEL.md | 22~32절 및 상단 현재 안내의 실제 stored fields/구현 상태 |
| ARCHITECTURE.md | 24~47절, 특히45~47절의 Gate→factory→public evaluator |

현재 유효 계약과 코드 사이에 **freeze를 막는 미해결 충돌은 발견하지 못했다**. 과거에 명시적으로 대체된 문구와 실제로 미완료인 정책/외부 과정은 아래에서 따로 기록한다. 모든 역사적 문장이 현재 코드와 글자 그대로 동일하다는 주장은 하지 않는다.

## 2. 완료 범위와 계층별 감사 결과

아래 source는 backend/policy_engine/policy_data/ 기준이다. Policy/RuleNode/walk_nodes는 기존 backend/policy_engine/models.py를 사용한다.

| 계층 | 실제 구현 | 보장 범위 | 감사 판단 |
|---|---|---|---|
| 의미 입력 | eligibility_coverage.py, required_condition.py, condition_inventory.py, condition_binding.py, coverage.py | scope/조건 의미·분류·근거 형식·Binding 소속/유일성 | 계약과 일치 |
| 검토 metadata | coverage_review.py, implementation_review.py, coverage_review_context.py | 두 record의 구조/종류, Context 소속/ref 유일성 | 계약과 일치, 진실성 인증 제외 |
| 현재 지문 | coverage_fingerprint.py | 명시3개 payload와 canonical bytes/SHA256 | 계약/golden과 일치 |
| 검토 비교 | coverage_review_match.py, coverage_review_resolution.py, coverage_review_matching.py | exact ref/target, MISSING/STALE/MATCHED, guarded conflicts | 계약과 일치 |
| root/소유 | rule_root_resolution.py, coverage_ownership.py | 원본 root/지원 타입/ID 유일성/전체 subtree 비겹침 | 계약과 일치 |
| 미매핑 | coverage_unmapped.py | 세 실행 leaf target과 미소유 leaf IDs | 계약과 일치, 완결성 해석 제외 |
| 구조 조립 | coverage_structure.py | policy/M/root/소유/U와 complete U 승격 | 계약과 일치 |
| 결합 | coverage_composition.py | 미소유 ANY/NOT gap 사실 | 계약과 일치, 일반 동치 증명 제외 |
| 통합 | coverage_integration_findings.py, coverage_integration.py | 구조→결합→Context→현재 지문→Review→불변 facts | 계약과 일치 |
| 최종 값 | eligibility_coverage_result.py | 원본 tuple 대응/identity/현재 baseline/derived status/9key 표현 | 계약과 일치 |
| 공식 진입점 | eligibility_coverage_evaluator.py | Gate1회→factory1회→동일 Result 반환 | 계약과 일치 |

이 완료는 generic 메모리 내 계산 경로에 한정한다. 실제 정책의 공식 조건 목록이 참인지, 실제 engine artifact가 준비됐는지, 실제 Review가 수행됐는지는 해당 계층의 보장에 포함하지 않는다.

## 3. 비완료 범위와 계약 우선순위

미구현: 실제 전체 안산 Inventory/Bindings/Reviews/Result, ResidenceHistory Fact/Rule/evaluator, Coverage→legacy Envelope/Manifest 연결, Policy verification의 신규 수용 gate, Benefit Acceptance/Bridge, 정책 혜택 Cashflow 반영, 독립 영속 감사 archive, HTTP/DB/LLM/로그인/사용자 금융정보 저장.

현재 사용자 정책 평가 엔진과 독립 Cashflow calculator가 존재한다는 사실과, 이 Coverage 경로에서 그것들을 연결했다는 주장은 다르다. 이번 freeze는 새 연결을 승인하지 않는다.

| 과거 문구/후보 | 이미 승인된 현재 대체 기준 | 동결 해석 |
|---|---|---|
| zero Binding/모든 미매핑 node는 SLICE에서도 항상 오류 | UNMAPPED31·35, STRUCTURE28·32, INTEGRATION40 | M nonempty이면 U facts 보존, complete U만 오류 |
| top ALL direct-child IDs가 Binding roots와 같아야 함 | INTEGRATION34·38·40 | nested unowned ALL 허용, unowned ANY/NOT gap을 M에 따라 승격 |
| 모든 Review slots의 identity를 먼저 모아서 검사 | INTEGRATION19·34·40 | Inventory 전체 slot 우선, canonical Implementation 전체 slots 순차 검사 |
| Context 존재/ref 미확인 목록 empty면 FULL | CONTEXT18, RESULT14~18·36 | 모든 current MATCHED·baseline·nonempty·정확한 대응 필요 |
| Result가 원본 Coverage/전체 Context를 보관 | RESULT8·12~15·32·36 | 현재8필드+기존 private findings, 외부 원본/record 별도 보존 |
| keyword-only Context/이전 inventory+bindings evaluator 후보 | RESULT25·37, VALIDATION37 | Coverage/Policy/optional Context의 현재 public API |
| init=False만으로 Result 생성 차단 후보 | RESULT36 / M2.38 | private sentinel+keyword-only InitVar, 저장8필드 유지 |
| FULL에 신청/운영/지급 범위가 포함된 듯한 Acceptance/Bridge 과거 표현 | POLICY_COVERAGE3~4, RESULT20~22·32 | FULL은 자격축만. 다른 검토는 독립 수용 요건 |
| scope와 completeness를 derived_scope로 혼용 | RESULT32·36~37 | scope는 ApplicabilityScope, completeness는 status |
| 과거 절의 “아직 미구현” | 각 문서 최신 구현 절/ARCHITECTURE47 | 역사 기록으로 읽으며 현재 공개 연결을 부정하지 않음 |

위의 supersede를 확인했으므로 옛 문구 잔존을 새로운 모순으로 오인하지 않는다. 현재 원본 문서는 이번 작업에서 수정하지 않는다. 이 표를 이유로 기존 실제 데이터나 테스트 기대값을 바꾸지 않는다.

## 4. Public API·타입·private 경계 동결

공식 외부 진입점은 다음 하나다.

```text
evaluate_eligibility_coverage(
    coverage: EligibilityCoverage,
    policy: Policy,
    review_context: CoverageReviewContext | None = None,
) -> EligibilityCoverageResult
```

세 인자는 위치/키워드 전달 가능, coverage/policy 필수, Context만 default None이다. 별도 override/force/strict/skip 옵션·raw 입력 자동 변환이 없다. Policy는 기존 models의 타입이며 policy_data에서 새로 export한 타입이 아니다.

| Public API/값 | Input | Output | Error | Side effect |
|---|---|---|---|---|
| evaluate_eligibility_coverage | exact Coverage/Policy, exact Context 또는 None | exact 불변 EligibilityCoverageResult | 기존 PolicyDataError 원본 전파, API 인자 오용은 TypeError | 없음 |
| fingerprint_condition_inventory | exact ConditionInventory | lowercase hex64 str | PolicyDataError | 없음 |
| fingerprint_policy_tree | exact Policy | lowercase hex64 str | PolicyDataError | 없음 |
| fingerprint_rule_subtree | 현재 지원 exact RuleNode root | lowercase hex64 str | PolicyDataError | 없음 |
| EligibilityCoverageResult.status | 내부 검증된8필드 | EligibilityCoverageStatus | 정상 생성 전제, setter 없음 | 없음 |
| EligibilityCoverageResult.to_dict | 불변 Result | 정확한9개 key의 새 nested snapshot | 입력 parser가 아님 | 원본 변경 없음 |
| 입력/검토 값 모델 | 아래 명시 필드 | frozen/slots 값, 새 to_dict | 기존 모델 오류/형식·참조 parser 오류 | I/O·실제 검토 인증 없음 |

현재 policy_data.__all__에서 확인한 **Coverage 관련 public 이름20개**는 아래와 같다. 기존 Envelope/Manifest/loader 등 package의 다른 공개 기능은 삭제/재정의하지 않는다.

| 그룹 | 실제 공개 이름 |
|---|---|
| 입력6개 | ApplicabilityScope, ConditionRequirement, RequiredCondition, ConditionInventory, ConditionBinding, EligibilityCoverage |
| 검토3개 | InventoryCompletenessReview, ImplementationBindingReview, CoverageReviewContext |
| match5개 | ReviewMatchStatus, ReviewMissingReason, ReviewStaleReason, InventoryReviewMatch, ImplementationReviewMatch |
| 결과2개 | EligibilityCoverageStatus, EligibilityCoverageResult |
| 함수4개 | 세 fingerprint 함수, evaluate_eligibility_coverage |

public Result는 **반환 타입**이며 일반 constructor로 수동 FULL을 만들 수 있는 API가 아니다. caller는 evaluator를 사용한다.

비공개: `_collect_coverage_integration_findings`, `_create_eligibility_coverage_result`, `_analyze_coverage_structure`, `_find_composition_gap_group_ids`, root/review resolvers, ownership/unmapped helpers, matchers, 두 integration findings 모델, payload/digest helpers와 생성 sentinel. package public export가 아니며 외부 caller가 직접 계산/승인 API로 사용할 계약이 없다. 내부 파일명/구현 기법 전체를 영구 public ABI로 승격하지 않되, 아래 의미·오류·순서·결과는 회귀 기준으로 유지한다.

입력 모델 동결 요약:

| 모델 | 실제 stored fields / 로컬 보장 |
|---|---|
| ApplicabilityScope | edition_id, quarter. exact4자리 연도 문자열, exact int1~4 또는 None=annual. 두 인자 필수, 날짜 추론 없음 |
| RequiredCondition | condition_id, meaning, requirement, evidence_refs. REQUIRED/CONDITIONAL 둘 모두 구현 의무, 근거 형식만 검사 |
| ConditionInventory | policy_id, scope, inventory_version, nonempty conditions, optional completeness_review_ref. 조건 ID 유일, i0001 이상 |
| ConditionBinding | condition_id, rule_root_id, implementation_review_ref. exact 원문 문자열, root/ref 비공백 |
| EligibilityCoverage | inventory, bindings. exact tuple, condition 소속/중복 검사, 빈 Binding 허용 |
| InventoryCompletenessReview | ref/policy/scope/inventory version·fp/dataset/source fp/date/artifact ref의9필드 |
| ImplementationBindingReview | ref/policy/scope/condition/root/inventory version·fp/rule/tree·subtree fp/dataset/source·implementation fp/date/artifact ref의15필드 |
| CoverageReviewContext | policy_id, scope, 현재 dataset/source fp/implementation fp, 두 record tuples의7필드. 종류/소속/전체 ref 유일성 |

동일 값의 별개 Scope는 동등하지만 Q3/annual은 다른 값이다. 문자열 자동 strip/대소문자/Unicode 정규화·숫자/Enum 자동 변환·dedupe를 하지 않는다. 기존 허용 tuple/근거 순서와 원문은 보존한다.

Scope의4자리 문자열 검사는 실제 효력연도 인증이 아니며 현재 문법상0000도 허용한다. Result.rule_version은 기존 Policy와 같은 exact 비공백 str로서 r#### 형식을 추가 강제하지 않는다. 근거 refs의 형식 검증과 실제 공식 출처/버전 존재 검증도 구별한다.

## 5. FULL_POLICY / CONDITION_SLICE 의미 동결

정상 public 실행에서 다음을 모두 만족한 **해당 policy_id/scope/Inventory·Rule version/현재 dataset·source·implementation baseline/current 지문**에 한해 FULL_POLICY다.

- M=missing_condition_ids, U=unmapped_rule_ids, G=composition_gap_group_ids가 모두 빈 tuple.
- Inventory Review는 MATCHED.
- Implementation findings는 nonempty이며 모두 MATCHED.
- 원본 Inventory/Bindings와 findings의 condition/root/review_ref가 정확히 대응.
- 현재 baseline3개가 모두 present이며 Result의 로컬 관계 검증 성공.

FULL은 고정 범위의 **eligibility representation/implementation/review coverage** 완료다. 필요한 조건·분기의 실제 공식 의미/검토 진실성은 외부 검토 전제다. 사용자의 PASS·행정 승인·신청 가능·Policy VERIFIED·혜택 수용·금액 반영·배포 승인을 뜻하지 않는다. Q3 FULL을 annual/Q2/다른 연도로 확대하지 않는다.

CONDITION_SLICE는 Gate와 factory가 정상 반환한 **모순 없는 미완료 coverage**다. missing Binding, Context 없음, Inventory/Implementation MISSING 또는 STALE, missing이 있을 때 보존된 U/G가 포함된다. 모두 bound여도 Review 미완료면 SLICE이며 existing reviews 모두 MATCHED여도 missing이 있으면 SLICE다.

Data Error를 catch해 SLICE로 만드는 fallback은 없다. 잘못된 metadata나 누락된 existing finding은 정상 미완료가 아니다. 실제 runtime 정상 status는 FULL_POLICY/CONDITION_SLICE 두 개뿐이다.

## 6. Structural pipeline 감사와 동결

```text
exact Coverage/Policy → policy_id 일치
→ Inventory 순서로 M 계산
→ canonical condition_id순 모든 Binding root resolve
→ 모든 원본 root 준비 후 ownership no-overlap
→ 실행 leaf target 및 U 계산
→ M empty/U positive일 때만 COVERAGE_UNMAPPED_RULE
→ (M, canonical 원본 pairs, U)
```

root는 exact ID로 전체 tree에서 찾으며 찾은 뒤에도 지원 타입/ID 유일성을 확인하고 원본 객체를 반환한다. leaf/group/root 자체/깊은 descendant 모두 대상이다. 타입 방어는 rule_id 접근 전이며 지원 타입 확인을 마친 뒤 중복 ID를 확정한다. missing root보다 duplicate 오류가, 지연된 duplicate보다 발견된 unsupported가 우선한다.

소유는 **root 자체+모든 descendant group/leaf**다. 같은 root·parent/child·ancestor/descendant 공유는 overlap 오류다. 현재 strict tree/MVP에서는 shared predicate 예외가 없다. canonical condition pair의 첫 겹침을 보고하며 payload의 첫 overlap ID는 tree순이 아니라 원문 ID의 Unicode code point 최소값이다.

U의 target은 exact **PolicyRule / ResidentRegistrationRule / BirthDateRule** 세 leaf다. RuleGroup은 소유/타입/중복/결합 탐색에 포함되지만 U target에는 넣지 않는다. U는 현재 Policy pre-order이며 set 순서로 반환하지 않는다.

| M | U | 구조 결과 |
|---|---|---|
| nonempty | empty 또는 nonempty | 정상 facts, Review와 최종 결과까지 계속 진행 |
| empty | empty | mapping-complete facts. 단독 FULL 증명 아님 |
| empty | nonempty | COVERAGE_UNMAPPED_RULE, 정상 결과 없음 |

zero Binding이면 nonempty Inventory의 모든 조건이 M이고 현재 모든 실행 leaf가 U다. root resolve0회 뒤 no-overlap/U 분석은 수행한다. zero Binding 자체를 단독 오류로 만들지 않는다. missing 때문에 깨진 root/overlap 등 독립 오류를 면제하지 않는다.

private ownership/unmapped/composition helper는 같은 Policy에서 준비한 원본 pairs라는 선행조건을 신뢰한다. 이를 공개 검증 우회 경로로 쓰지 않는다. 현재 root resolve는 Binding별 전체 탐색으로 O(N×B)이며 깊은 tree에는 기존 재귀 한계가 있다. 작은 MVP에서 성능 index/일반 DAG를 선제 구현할 근거는 없다.

## 7. Composition rules와 한계 동결

현재 MVP는 **condition 소유 subtree 밖의 결합은 ALL만 허용**한다.

| 현재 group | G 결과 |
|---|---|
| unowned ALL, top/nested와 무관 | gap 아님 |
| unowned ANY | gap |
| unowned NOT | gap |
| owned ANY/NOT | gap 아님 |
| 상위 Binding이 소유한 nested ANY/NOT | gap 아님 |
| ANY/NOT의 children을 별도 Binding들로 모두 소유 | parent group은 여전히 gap |

G는 미소유 ANY/NOT IDs를 root 포함 Policy pre-order로 보존한다. ancestor가 gap이어도 descendant를 임의 생략하지 않는다. helper는 사실만 반환하고 Inventory/missing/status를 해석하지 않는다.

M nonempty/G positive는 정상 incomplete facts, M empty/G positive는 integration의 **COVERAGE_COMPOSITION_GAP**이다. findings 생성자의 로컬 오류에 승격 책임을 떠넘기지 않는다. 전체 구조/결합이 성공하기 전에 Review 지문으로 문제를 덮지 않는다.

이는 **안전한 MVP representation restriction**이며 일반 Boolean equivalence proof가 아니다. owned subtree가 공식 조건의 의미를 정확히 구현하는지는 Implementation Review 책임이다. 더 복잡한 condition 간 관계가 필요하면24절의 명시적 모델 개정이 필요하다.

## 8. Fingerprint payload·bytes 계약 동결

| 지문/API | schema | 포함·순서 | 제외/한계 |
|---|---|---|---|
| Inventory | coverage-inventory-1.0 | policy_id/scope/inventory_version, condition_id ASCII순 조건4필드, evidence 원래 순서/중복 | completeness_review_ref·검토 날짜/ref/artifact·Bindings 제외 |
| Policy Tree | coverage-policy-tree-1.0 | policy_id/rule_version/root 전체 N(node), children 원래 순서·node IDs/값/evidence | policy_name/synthetic/test_only/Envelope verification·benefit·scope 제외 |
| Subtree | coverage-subtree-1.0 | 전달된 root 자체+모든 descendants의 동일 N(node) | parent/Policy/policy_id/rule_version 제외. 소속/존재는 상위 책임 |

N(node)는 현재 exact4타입의 명시 필드 allowlist다. atomic은 field/operator/value/FactBasis/evidence, resident는 요구 지역/기준일 source/evidence, birth는 ISO 날짜 경계/evidence, group은 operator와 순서 있는 N(children)을 포함한다. generic to_dict/dataclass 전체를 자동 hash하지 않는다. 미래 필드가 추가되면 포함/제외를 먼저 승인한다.

canonical recipe는 `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")` 후 SHA256 lowercase hexdigest다. BOM/추가 newline·repr/Python hash·문자열 정규화·시간/경로는 넣지 않는다. 올바르게 표현할 수 없는 JSON/UTF-8는 PolicyDataError이며 replace/ignore하지 않는다. 정수/bool/None/Enum/date 변환도 기존 payload를 유지한다. RFC8785/JCS 전체 구현이나 자연어/논리 동치 정규화는 아니다.

condition collection 순서만 바뀌면 Inventory 지문은 같을 수 있지만 원본 Inventory equality/to_dict는 순서를 보존한다. evidence 순서·group child 순서는 바뀌면 다른 지문이다. 동일 subtree가 다른 parent로 이동하면 subtree 지문은 같아도 Tree 지문은 달라질 수 있다.

source_registry_fingerprint는 기존 Registry 전체 도메인 지문을 **외부가 현재 Context에 공급**한다. implementation_fingerprint는 명시된 input/evaluator artifact의 정확한 bytes SHA256을 **외부가 공급**한다. dataset_version은 hash가 아니라 고정 snapshot ID다. Envelope/Manifest/원문 파일 bytes/domain tree/artifact 지문은 역할이 달라 64자리라는 이유로 교환하지 않는다.

## 9. Review contract·상태·비교 동결

InventoryCompletenessReview는 고정 scope의 공식 조건/예외 목록 완결성을 검토했다는 snapshot 주장이다. ImplementationBindingReview는 특정 condition의 전체 분기·subtree·전체 tree 결합·입력/evaluator 구현의 대응을 검토했다는 snapshot 주장이다. Context는 한 policy/scope에 대한 현재 baseline과 두 종류의 명시 records다.

Context는 두 tuple 전체 ref 유일성과 모든 record의 policy/scope 소속을 검사한다. records의 inventory/rule/dataset version이 현재 baseline과 다를 수 있고, 같은 policy/scope의 미선택 정상 historical records도 허용한다. 현재 ref는 원문 equality로 선택하며 strip/prefix 추론·최신 날짜·가장 큰 version·대체 record 선택이 없다.

| 상태 | 현재 의미 | Coverage 정상 경로 |
|---|---|---|
| MATCHED | 해당 slot의 target·version·지문 조건 일치 | FULL의 Review 필요조건 하나 |
| MISSING | 정상 미선언/Context 미제공 | SLICE 사유 |
| STALE | 올바른 target이나 version/implementation 확인본이 다름 | SLICE 사유 |
| Data Error | 참조·종류·대상·동일 version 내용의 모순 | 예외, 정상 status 아님 |

STALE은 version 숫자/날짜의 “과거”를 판정한 결과가 아니다. 정확한 동일성의 차이이며 더 큰/다른 version도 stale로 표현한다.

| 비교 | 같은 version인데 지문 다름 | version 다름 |
|---|---|---|
| Inventory version / Inventory fp | INVENTORY_FINGERPRINT_CONFLICT | INVENTORY_VERSION_CHANGED |
| Rule version / Tree·subtree fp | POLICY_TREE_FINGERPRINT_CONFLICT 또는 SUBTREE_FINGERPRINT_CONFLICT | RULE_VERSION_CHANGED |
| Dataset version / source registry fp | SOURCE_REGISTRY_FINGERPRINT_CONFLICT | DATASET_VERSION_CHANGED |
| Implementation fp, 별도 version 없음 | 해당 없음: 단순 mismatch는 IMPLEMENTATION_CHANGED | 별도 version 비교 없음 |

한 version 변경은 그 version의 지문 비교만 면제한다. 다른 독립 쌍의 같은 version 모순은 계속 오류다. 첫 STALE에서 반환하지 않으며 stale 이유는 INVENTORY_VERSION_CHANGED → RULE_VERSION_CHANGED → DATASET_VERSION_CHANGED → IMPLEMENTATION_CHANGED 순서의 중복 없는 tuple이다. Inventory에는1·3만 허용한다.

Context=None은 정상이며 Inventory ref가 없으면 INVENTORY_REVIEW_NOT_DECLARED 하나, ref가 있으면 NO_REVIEW_CONTEXT 하나다. existing Implementations는 모두 NO_REVIEW_CONTEXT MISSING이다. Context가 있어도 Inventory ref=None은 미선언 MISSING이지만, 명시된 ref가 Context에 없거나 종류가 다르면 Data Error다. **empty Context≠None**이다.

정상 matcher에서 Implementation MISSING은 Context=None에만 발생한다. 따라서 Inventory STALE+Implementation MISSING 또는 Implementation MISSING/STALE 혼합을 같은 정상 Context의 성공 예시로 만들지 않는다. 값 모델이 더 넓은 조합을 로컬 표현할 수 있어도 최종 Result는 현재 실행 경로에 맞는 조합만 허용한다.

reviewed_at은 exact date metadata이며 현재 시각·자동 만료/최신 선택을 만들지 않는다. 실제 freshness/철회·검토 진실성은 외부 경계다. metadata 정정은 새 review_ref로 남기며 기존 ref 내용을 덮어쓰지 않는다.

## 10. Integration·Result 계약 동결

정확한 순서는 **입력 타입 → 구조 → composition → complete gap 승격 → Context policy/scope → Inventory/Tree/각 subtree 지문 → Inventory matcher → canonical Implementation matchers → 모든 매칭 성공 후 findings → factory → Result**다.

한 공개 호출에서 Gate1회, 성공 뒤 factory1회다. Gate 안에서는 structure/composition 각각1회, Inventory/Tree 지문 각각1회, 각 existing Binding subtree 지문1회, Inventory matcher1회, 각 existing Implementation matcher1회다. 구조 helper 내부의 기존 traversal/ownership 호출까지 “전체 tree를 딱 한 번만 순회한다”는 뜻은 아니다.

private findings는 M/U/G·Inventory/Tree 지문·Inventory match·canonical Implementation findings의7필드다. Implementation finding은 subtree_fingerprint/review_match의2필드다. 조건/root/ref는 match 한 곳에만 있다. runtime RuleNode/Context/Policy는 findings에 저장하지 않는다.

Result는 정확히 **policy_id, scope, inventory_version, rule_version, dataset_version, source_registry_fingerprint, implementation_fingerprint, findings**의8필드다. 앞4개는 현재 Inventory/Policy, baseline3개는 현재 Context 또는 모두 None에서 얻고 원본 scope/findings를 보존한다. partial baseline은 오류다. 과거 Review record의 값으로 현재 baseline을 채우지 않는다.

factory는 모든 정상 FULL/SLICE 생성 전에 다음을 대조한다.

1. exact Coverage/Policy/Context-or-None/findings, Coverage/Policy ID, 제공 Context의 policy/scope.
2. Inventory 원래 순서의 R−Binding IDs와 M의 정확한 tuple equality.
3. canonical Binding의 (condition_id, root_id, implementation_review_ref)와 finding의 (condition_id, root_id, review_ref) tuple 전체 equality.
4. Inventory completeness_review_ref와 Inventory match.ref equality.
5. 로컬8필드 형식/현재 baseline all-or-none/Review 조합/M empty이면 Implementation nonempty.

그 결과 R=B∪M, B∩M=∅, K=B가 보장된다. 단순 len 비교나 count0만으로 FULL을 만들지 않는다. factory는 구조/지문/Review를 다시 계산하지 않으며 public evaluator가 같은 호출의 실제 Gate 반환값만 전달한다.

status는 저장 필드/인자/setter/cache가 없는 derived property다. frozen/slots와 private sentinel+keyword-only InitVar로 일반 생성/replace를 제한한다. token은9번째 저장 필드가 아니다. Python private 우회/강제 객체 변조까지 막는 보안 인증은 아니다.

to_dict는 저장8개+파생 canonical status의 **정확한9개 key**이며 optional3개는 None이어도 key를 보존한다. 새 nested scope/findings 표현을 사용해 snapshot 수정이 원본에 영향을 주지 않는다. 별도 SliceReason·is_full·verification/acceptance/사용자 facts/금액·전체 원문은 없다.

## 11. Stable errors와 우선순위

기본 예외는 기존 **PolicyDataError**다. 아래는 실제 구현에서 확인한 prefix이며 새 .code 필드/ERROR status/예외 계층을 정의하지 않는다.

| 실제 prefix | 계층/발생 조건 |
|---|---|
| INVALID_STRUCTURE_INPUT | Gate/구조/root/소유/U/G의 exact 타입·내부 pair 입력 위반 |
| COVERAGE_POLICY_MISMATCH | 현재 Coverage와 Policy ID 다름 |
| RULE_ROOT_NOT_FOUND | 명시 root가 현재 정상 tree에 없음 |
| DUPLICATE_RULE_NODE_ID | root/소유/target/composition helper의 전체 ID 유일성 방어 |
| UNSUPPORTED_RULE_NODE | 미지원 exact node 또는 composition operator |
| COVERAGE_OWNERSHIP_OVERLAP | 서로 다른 condition subtree의 공유 node |
| COVERAGE_UNMAPPED_RULE | M empty/U positive |
| COVERAGE_COMPOSITION_GAP | M empty/G positive |
| INVALID_MATCH_INPUT | private review resolver/matcher의 입력 형식 위반 |
| REVIEW_REF_NOT_FOUND | 제공 Context에서 명시 ref 부재 |
| WRONG_REVIEW_TYPE | ref가 반대 종류의 record를 가리킴 |
| REVIEW_POLICY_MISMATCH | Context/선택 Review와 현재 policy 불일치 |
| REVIEW_SCOPE_MISMATCH | Context/선택 Review와 현재 scope 불일치 |
| REVIEW_CONDITION_MISMATCH | 선택 Implementation Review의 condition 불일치 |
| REVIEW_RULE_ROOT_MISMATCH | 선택 Implementation Review의 root 불일치 |
| INVENTORY_FINGERPRINT_CONFLICT | 같은 inventory version의 다른 Inventory fp |
| POLICY_TREE_FINGERPRINT_CONFLICT | 같은 rule version의 다른 Tree fp |
| SUBTREE_FINGERPRINT_CONFLICT | 같은 rule version의 다른 subtree fp |
| SOURCE_REGISTRY_FINGERPRINT_CONFLICT | 같은 dataset version의 다른 Registry fp |
| INVALID_INTEGRATION_FINDINGS | private findings의 로컬 형식/중복/정렬/관계 위반 |
| INVALID_COVERAGE_RESULT | factory correspondence 또는 Result 로컬 형식/관계 위반 |

위21개 이름으로 모든 모델 오류를 억지 통일하지 않는다. 입력 모델은 기존 필드별 PolicyDataError, evidence parser는 기존 SourceValidationError를 사용할 수 있다. 지문 utility의 wrong root/type와 strict encoding은 현재 `root:`, `inventory:`, `policy:`, `inventory fingerprint:`/`policy tree fingerprint:`/`subtree fingerprint:` 메시지 계약이다. 일반 Result 생성/인자 오용은 TypeError, 동결 값 변경은 Python의 frozen/attribute 오류다. 새로운 가상 FINGERPRINT_ERROR code를 만들지 않는다.

정상 생성자는 duplicate/unsupported tree를 먼저 거부할 수 있다. 따라서 모든 잘못된 객체가 public evaluator까지 도달해 반드시 위 named 방어 prefix를 낸다고 주장하지 않는다. 강제 훼손 객체/순환 graph 복구는 보장하지 않는다. 현재 도달하지 못하는 방어 분기의 소스/수동 검토와 실제 실행 테스트를 구분한다.

외부 호출의 fail-fast 우선순위는10절과 같다. Inventory slot **전체** 검사 후 canonical Implementation slot **전체** 검사다. Inventory content conflict보다 뒤 Implementation의 identity 오류를 먼저 찾는 옛 global preflight를 복원하지 않는다. 같은 slot에서는 target → Inventory version/fp → Rule version/Tree→subtree → Dataset version/Registry → implementation identity 순서의 현재 코드가 우선한다.

고정 JSON 진단도 동결한다.

- overlap: condition_a/rule_root_a/condition_b/rule_root_b/overlap_count/first_overlap_rule_id의6필드. 첫 ID는 해당 교집합의 code point 최소값.
- U: unmapped_count/first_unmapped_rule_id의2필드. 첫 ID는 U[0], Policy pre-order.
- G: composition_gap_count/first_composition_gap_group_id의2필드. 첫 ID는 G[0], Policy pre-order.

모두 sort_keys=True/ensure_ascii=True/compact separators, prefix 뒤 `: `를 사용한다. JSON 인코딩이 지문 payload의 ensure_ascii=False와 다름을 유지한다. 예외를 catch해 SLICE/STALE/UNKNOWN으로 강등하거나 partial findings/Result를 반환하지 않는다.

## 12. Trust boundary 표와 감사 한계

| 항목 | 시스템이 보장하는 것 | 외부 책임/보장하지 않는 것 |
|---|---|---|
| 공식 policy source truth | 조건/근거 ref의 구조와 공급된 자료의 대응 | 공식성·최신성·행정 의미·추가 예외/누락 여부의 실제 검토 |
| Review truthfulness | 정확한 타입/유일 ref/대상·version·지문 비교 | 사람이 실제로 충분히 검토했는지, 기록/artifact 존재와 진실성 |
| Dataset release identity | 명시 dataset ID를 보존하고 검토 record와 비교 | 같은 label의 파일 덮어쓰기 금지, 실제 Manifest/bytes 확인·선택 |
| Source Registry content | 현재 supplied Registry fp와 같은 dataset의 Review fp 대조 | 실제 Registry/공식 문서/version/locator의 공급·보존·freshness |
| Implementation artifact | supplied engine fp 일치/변경을 비교하고 현재 값 보존 | 정확히 어떤 artifact/의존성을 검토·실행했는지, bytes와 baseline 연결 |
| Policy/scope 대응 | 현재 Inventory/Context policy/scope와 tree ID·Review 결합 | Policy 자체에 scope가 없으므로 공식 회차와 그 tree 의미의 참된 대응 |
| User eligibility facts | 이 경로에서는 입력·평가·저장하지 않음 | 별도 Rule Engine과 신뢰된 사실/개인 적용 검토 |
| Administrative approval | 승인/신청/지급 확정 상태를 만들지 않음 | 행정기관의 자격·접수·지급 결정 |
| Result provenance | public API에서 Gate1회→factory1회 원본 연결 | Python private 강제 우회·임의 sentinel/객체 조작의 악성 위조 방지 |
| 과거 완전 재현 | current identity/fps/선택 refs/outcomes 보존 | 원본 dataset/registry/review records·artifacts/engine artifact의 불변 보존 |

SHA256은 변경 감지·현재 확인본 대조·재현에 사용하며 **전자서명·작성자 인증·위조 불가·사람 검토 증명**이 아니다. 같은 형식의 거짓 baseline/record를 함께 만들면 모델 생성/지문 일치만으로 진실성을 증명할 수 없다. 사용자나 LLM의 직접 승인 선언을 신뢰하는 API는 제공하지 않는다.

Result 하나는 완전한 독립 audit archive가 아니다. 선택된 Review의 과거 versions/날짜/artifact 본문·전체 records나 source_bindings를 모두 저장하지 않는다. 외부 불변 ref와 고정 원본을 함께 보존해야 하며, 그것을 폐기한 환경에서 동일 과거 평가를 재현한다고 주장하지 않는다. 필요한 경우 persistence/record snapshot 계약을 먼저 별도로 설계한다.

## 13. Regression baseline과 현재 검증

작업 전 전체 pytest는 **5687 passed in 14.24s**다. 현재 collect-only 수집도 **5687개**이며 아래 주요 suite 수를 확인했다. 잔존할 수 있는 pytest node cache 개수를 현재 테스트 수로 사용하지 않는다.

| 회귀 대상 | 현재 테스트 수 |
|---|---|
| ApplicabilityScope | 84 |
| RequiredCondition / Inventory / Binding / Coverage 입력 | 104 / 119 / 82 / 83 |
| Inventory Review / Implementation Review / Context | 182 / 216 / 127 |
| ReviewMatch 값 / resolver / Inventory matcher / Implementation matcher | 166 / 63 / 142 / 257 |
| Inventory / Tree / subtree fingerprint | 47 / 72 / 58 |
| root / ownership / unmapped / structure / composition | 80 / 93 / 112 / 94 / 112 |
| findings / integration Gate / Result / public evaluator | 184 / 107 / 226 / 67 |

위는 전체 프로젝트 suite의 부분집합이다. 전체5687개에는 기존 정책 로더/평가/원문·Manifest/Cashflow 등 다른 회귀도 포함된다. 과거 단계별 “신규 테스트 수”를 더하거나 캐시를 합쳐 현재 총수로 쓰지 않는다.

freeze 핵심은 **semantic contracts·정확한 golden bytes/지문·기존 오류/순서/출력·실제 release immutability**다. 숫자가 많다는 사실은 correctness나 실제 정책 자격을 증명하지 않는다. 이번에는 신규 테스트를 작성하거나 기대값을 갱신하지 않는다. 문서 작성 후 전체 pytest를 다시 실행한 결과와 최종 변경 대조를26절에 기록한다.

## 14. Golden vectors 동결

GV01~GV15는 COVERAGE_FINGERPRINT_SPEC.md24절과 기존 테스트의 **literal canonical JSON/UTF-8 길이/SHA256**을 회귀 원본으로 유지한다. 실행 시 같은 현재 구현으로 기대값을 새로 계산해 비교하는 방식으로 바꾸지 않는다.

| Golden | 의미 |
|---|---|
| GV01 | 단일 Inventory 조건 |
| GV02 / GV03 | 입력 조건 순서 반전, 같은 canonical Inventory 지문 |
| GV04 | condition meaning 변경 |
| GV05 | evidence 추가 |
| GV06 | evidence 순서 반전 |

위 GV01~GV06의 원본은 tests/test_inventory_fingerprint.py다.

| Golden | 의미 | 기존 회귀 파일 |
|---|---|---|
| GV07 | 단일 atomic Tree | tests/test_policy_tree_fingerprint.py |
| GV08 / GV09 | ALL child 순서 반전, 다른 Tree 지문 | 같은 파일 |
| GV10 | ResidentRegistrationRule payload | 같은 파일 |
| GV11 | BirthDateRule payload | 같은 파일 |
| GV14 | FactBasis 다섯 필드 | 같은 파일 |
| GV15 | IN value tuple 순서 | 같은 파일 |
| GV12 / GV13 | group/atomic root-only subtree | tests/test_rule_subtree_fingerprint.py |

기존 golden 파일 내용과 literal을 바꾸지 않는다. 이번 감사에서 새로운 actual hash를 발급하지 않으며 golden을 복사해 별도 경쟁하는 기대값 목록을 만들지 않는다.

## 15. Actual Ansan 상태와 generic 완료의 구별

**Generic core complete / frozen, actual Ansan FULL_POLICY 아님.**

읽기 전용으로 현재 release JSON/README를 확인했다. 001은 edition2026/r0001의 주민등록 한 조건, 002는 edition2026/r0002의 ALL(resident,birth) 부분 구현이다. 두 실제 Envelope의 verification_status는 DRAFT, evaluation_scope는 CONDITION_SLICE다.

002에는 현재 안산 주민등록 slice와 Q3 출생일 경계가 구현돼 있으나, ResidenceHistory 공식 의미가 미확정이다. 국적/등록분류 관련 조건 및 최종 공식 조건 목록 완결성 검토도 남아 있다. actual full ConditionInventory/Bindings/Reviews·검증된 FULL Result는 없다. source VERIFIED·일부 leaf PASS·generic evaluator 완성으로 이 공백을 채우지 않는다.

이번 감사에서는 실제 release를 public evaluator에 넣어 새 Result/FULL을 생성하지 않았다. 실제 승인·수용·혜택 metadata·금액 적용을 발급하지 않는다.

## 16. ResidenceHistory와 국민신문고 dependency

개발/감사 상태를 분리한다.

| 대상 | 현재 표기 | 의미 |
|---|---|---|
| Generic Eligibility Coverage Core | FROZEN | 사용자 독립 metadata 계산/공개 경로 동결 |
| M1.18 ResidenceHistory | OFFICIAL_INQUIRY_REQUIRED | 정책별 공식 거주기간 산식/기산/경계 답변 대기 |
| Actual Ansan coverage | BLOCKED_ON_OFFICIAL_RESIDENCE_SEMANTICS | 현재 actual FULL로 진행 불가. runtime status가 아님 |

국민신문고 dependency는 **실제 policy-specific ResidenceHistory semantics**에 있다. generic Coverage core나 합성 Acceptance 계약 연구 전체가 답변을 기다려야 한다는 뜻은 아니다. 1095/3650일·calendar 계산·귀화일 포함을 임의 선택하지 않고 Fact/Rule/evaluator/placeholder를 구현하지 않는다.

답변 도착은 FULL의 충분조건이 아니다. 원문/기산 의미 확정 → 데이터/규칙/입력/경계 테스트 계약 승인 → 구현/검토 → 최종 Inventory와 mapping/reviews 준비가 여전히 필요하다. 등록분류·목록 완결성 등 다른 미완료도 함께 해결해야 한다.

## 17. Immutable release 정책

실제 **ansan-youth-2026-10-20-001 / 002**는 불변으로 유지한다. 이 freeze가 기존 JSON/schema/rule_version/source bindings/Manifest/SHA 선언을 수정하거나 legacy CONDITION_SLICE를 FULL로 덮는 migration은 아니다.

새 공식 의미·정정 자료가 도착하면 영향 분석과 승인 후 **새 release를 추가**한다. 과거 참조/원문/검토 snapshot은 보존하고 새 version/ref와 대응을 명시한다. 같은 dataset label·review_ref에 다른 내용을 덮어쓰지 않는다. 새 자료·새 지문에 과거 FULL/검토/수용을 자동 승계하지 않는다.

실제 release 변경 확인은 파일 경로/크기/수정시각을 작업 전후 비교한다. 이번에 새 실제 fingerprint/승인 record를 만들어 동결 근거로 삼지 않는다.

## 18. Future Rule type 확장 절차

ResidenceHistoryRule 등 새 specialized Rule은 현재 exact4타입 지원 목록에 자동 포함되지 않는다. 최소 다음을 함께 검토한 뒤 별도 승인 단위로 확장한다.

1. 공식 의미/기준일/입력 Fact·Resolver·evaluator·반환 details·경계 테스트.
2. RuleNode union·Policy/RuleGroup 생성자·지원 타입 dispatch·중복/재귀 traversal.
3. root resolver·소유 collector/overlap·target collector의 실행 leaf universe·composition 타입/operator 방어.
4. 명시 N(node) payload와 포함/제외 필드, fingerprint schema/bytes/golden 영향.
5. loader/routing/schema와 legacy m1.0/m1.1 호환성, integration/result/public API 영향.
6. 기존 Review의 implementation artifact/Tree/subtree 지문과 재검토·version/ref 처리.
7. 과거 actual releases 보존·새 release/migration/compatibility 결정.

임의 to_dict가 있다고 generic dispatch하거나 unsupported node를 skip/UNKNOWN으로 처리하지 않는다. 새로운 leaf를 target universe에서 누락하거나 의미 변경을 기존 schema/Review로 숨기지 않는다. 모든 항목을 한꺼번에 대규모 구현하라는 지시는 아니며, 계약 → 작은 구현 → 테스트/검증 순서를 유지한다.

## 19. Fingerprint schema 변경 통제

canonical payload의 **의미/기존 domain projection·정규화 규칙**을 바꾸려면 영향을 받는 schema version을 명시적으로 개정한다. 같은 schema 문자열 아래 payload 의미·기존 golden을 조용히 바꾸지 않는다.

변경안에는 새/구 payload 및 bytes 차이, Review/Manifest/actual releases 영향, golden 추가/보존 계획, 읽기·비교 호환 또는 병행 지원/재발급 전략을 포함한다. 기존 GV literal을 새 구현 출력으로 덮어 통과시키지 않는다. source registry나 artifact bytes 지문은 별도 계약 대상이므로 세 coverage schema 중 하나로 대체하지 않는다.

새 모델 필드가 지문 비대상 metadata라 기존 projection을 유지할 수 있어도 포함/제외 결정을 먼저 기록한다. 새 Rule type의 표현 추가 역시 schema/호환 영향 분석을 생략할 수 없으며, 이번 freeze가 자동 schema 확장을 허용하는 것은 아니다.

## 20. 향후 Composition model의 한계

현재 restriction으로 표현하기 어려운 정책에서는 조건을 잘못 쪼개거나 ANY를 ALL로 바꿔 FULL을 만들지 않는다. condition 간 OR/NOT/예외 관계를 지원할 필요가 확인되면 **ConditionComposition 등 별도 모델 revision**을 먼저 설계한다.

조건 의미 목록·전체 결합·subtree 소유·Review 대상·fingerprint/현재 FULL 식·과거 release/검토 호환에 미치는 영향을 함께 검토한다. 단순 unowned ANY/NOT 허용 옵션이나 force_full 플래그로 MVP restriction을 무력화하지 않는다. 현재 helper는 일반 논리 동치 증명기로 확대하지 않는다.

## 21. Change-control 절차

동결 의미/API/오류/지문을 바꾸기 전에 다음 다섯 항목을 명시하고 별도 승인을 받는다.

1. **Spec revision:** 어떤 frozen invariant/경계가 왜 바뀌는지, 새 의미와 비목표.
2. **Impact analysis:** 입력/값/loader/Rule/structure/Review/Gate/Result/API/후속 Acceptance 영향.
3. **Golden/test impact:** 기존 사례 보존·새 경계/반례, 기대값 변경이 필요한 정확한 이유와 범위.
4. **Old actual releases impact:** 기존 bytes/version/ref 보존, 새 release 필요와 재검토 범위.
5. **Migration/compatibility decision:** 기존 caller/검토 자료의 읽기·비교·재발급·병행 지원/명시적 미지원 결정.

이 과정 없이 다른 subsystem의 편의를 위해 status를 수동 입력으로 바꾸거나, 오류를 정상 제외로 내리거나, source/engine baseline을 추론하거나, 기존 release를 고치지 않는다. 의미를 유지하는 내부 refactor도 관련 회귀·순서·결정성·오류/지문 불변을 확인한다. 테스트 수 변화 자체는 의미 개정의 근거가 아니다.

## 22. Frozen invariants — FI01~FI36

아래 **36개**를 의미 회귀 기준으로 동결한다. 연결은2절 source와 해당 기존 suite를 가리키며 테스트 전체를 그대로 보존한다.

| ID | 동결 계약 | 구현/주요 회귀 |
|---|---|---|
| FI01 | exact domain/tuple/Enum, raw 자동 변환 없음 | 입력 모델·Gate·Result tests |
| FI02 | scope 명시, quarter=None=annual, Q3와 구별 | ApplicabilityScope |
| FI03 | 날짜/사용자 값으로 scope/현재 baseline 추론 없음 | scope/Context/evaluator |
| FI04 | Inventory nonempty·condition ID 유일 | ConditionInventory |
| FI05 | REQUIRED/CONDITIONAL 둘 모두 FULL 구현 의무 | RequiredCondition/Result |
| FI06 | Binding condition 소속·유일성, 별도 implemented IDs 저장 없음 | EligibilityCoverage |
| FI07 | exact root ID·원본 root identity | root resolver |
| FI08 | 지원 node/type·전체 ID 유일성 방어, skip/dedupe 없음 | root/targets/composition |
| FI09 | 소유는 root+전체 group/leaf descendants | ownership collector |
| FI10 | 같은/ancestor/descendant root overlap은 Data Error | no-overlap validator |
| FI11 | U target은 현재3개 exact 실행 leaf만 | unmapped target collector |
| FI12 | missing Binding/zero Binding은 정상 incomplete 가능 | structure/Result/evaluator |
| FI13 | M empty/U positive는 COVERAGE_UNMAPPED_RULE | structure |
| FI14 | M nonempty/U positive는 facts 보존 | structure/integration |
| FI15 | top/nested unowned ALL 허용 | composition |
| FI16 | unowned ANY/NOT gap, 소유/parent-owned이면 gap 아님 | composition |
| FI17 | M empty/G positive만 승격, incomplete G는 보존 | integration |
| FI18 | 세 schema·명시 payload·canonical JSON/strict UTF-8/SHA256 | fingerprint utilities |
| FI19 | M=Inventory순, pairs/K=condition순, U/G=Policy pre-order, child/evidence 원순서 | structure/fp/integration |
| FI20 | GV01~GV15 JSON/bytes 길이/digest literal 보존 | 세 golden suite |
| FI21 | exact explicit ref, 자동 최신/대체/정규화 선택 없음 | Review resolvers |
| FI22 | Context는 한 policy/scope, 두 종류 전체 ref 유일 | ReviewContext |
| FI23 | Review 정상 상태는 MATCHED/MISSING/STALE만 | ReviewMatch 모델/matchers |
| FI24 | version 변경은 그 쌍만 stale 면제, 독립 같은 version conflict는 오류 | 두 matchers |
| FI25 | implementation fp mismatch는 별도 version 없이 STALE | Implementation matcher |
| FI26 | Context=None은 정상 MISSING/baseline None/SLICE | matchers/Result/evaluator |
| FI27 | empty Context≠None, 깨진 명시 ref/wrong type/target은 오류 | resolver/integration |
| FI28 | R=B∪M, B∩M=∅, K=B와 condition/root/ref 정확한 tuple 대응 | Result factory |
| FI29 | Result 저장8필드·derived status·새9key serialization, SliceReason 없음 | Result |
| FI30 | 현재 baseline3개 all-none/all-present, 과거 Review 값에서 추론 금지 | Result/Context |
| FI31 | FULL은 M/U/G empty·K nonempty·모든 current MATCHED·baseline present | Result.status |
| FI32 | 일반 생성/replace 제한, token은 InitVar로 저장 필드 아님 | Result construction |
| FI33 | public Gate1회→factory1회, 실패 원본 전파/재시도·강등·partial 없음 | public evaluator |
| FI34 | pure/deterministic/user-independent/원본 mutation 없음 | subsystem 전반 |
| FI35 | FULL≠사용자 PASS/행정 승인/VERIFIED/Acceptance/현금 적용 | API·Result·경계 문서 |
| FI36 | 외부 원문/Review/artifact 진실성·불변 보존은 별도, 개인정보 저장 없음 | trust/actual release 경계 |

## 23. Explicit non-goals와 알려진 한계

| 한계 | 동결 의미/현재 대응 |
|---|---|
| 공식 의미와 human review 진실성 | 타입/지문/현재 비교가 인증하지 않음. 외부 근거·교차 검토 필요 |
| 일반 Boolean equivalence·condition 관계 모델 | unowned-ALL-only restriction까지만, 필요 시20절 개정 |
| 대규모/순환/DAG/악성 훼손 객체 | 현재 작은 strict recursive tree, O(N×B) 탐색·깊이 한계. 일반 복구/보안 보장 없음 |
| 완전한 과거 감사 재생 | Result 단독 불충분, 불변 원본/records/artifacts 함께 보존 |
| source/engine baseline의 실제 bytes 연결 | Context의 supplied 값을 비교할 뿐 외부 파일/artifact를 검증하지 않음 |
| 오래된 날짜/만료/정정의 자동 탐지 | 현재시간/네트워크 조회 없음, source freshness/철회/외부 자료 선택은 별도 |
| legacy Envelope FULL 표현/연결 | 독립 Result가 기존 slice-only Envelope를 자동 승격하지 않음 |
| actual Ansan FULL | 공식 거주 의미·등록분류·최종 목록/검토/자료 미완료 |

사용자 자격 PASS/FAIL/UNKNOWN·신청일 평가·소득/월세/예산·정책 혜택 금액 계산·Verification/Acceptance/Bridge·실제 가입/신청·계좌 연동·권한/전자서명 platform·영구 사용자 로그는 이 Coverage subsystem의 비목표다. 동결을 이유로 이 기능들을 새로 만들지 않는다.

## 24. 다음 subsystem 추천

Coverage를 더 확장하는 대신 기존 **Benefit Acceptance** 계약 검토로 복귀한다. Generic coverage를 막던 기반은 준비됐지만, 과거 M2.4의 수용 모델이 곧바로 구현 준비 완료라는 뜻은 아니다.

추천 순서:

1. **다음 가장 작은 작업 한 개:** M2.4 Acceptance 계약을 현재 EligibilityCoverageResult와 대조하여 **CoverageResult→Acceptance 연결 계약을 문서로 재검토**한다. 실제 수용 record/코드는 만들지 않는다.
2. scope/inventory/rule/dataset/source/implementation identity·current 결과·verification/benefit metadata·기한/철회/검토 ref의 경계를 확정한다. Result 단독/상태 문자열만으로 ACCEPTED를 만들지 않는다.
3. 별도 승인 후 최소 Benefit Acceptance 모델과 합성 테스트를 구현한다.
4. 이후 Benefit Bridge의 정규화/개인·월 적용·중복/현금 유형 계약을 구현한다.
5. 검증된 결과만 기존 Cashflow calculator에 연결한다.

Acceptance 재검토 시 POLICY_COVERAGE_SPEC.md20절의 accepted_scope/inventory_version 보완, 실제 source_bindings/benefit 근거, implementation artifact와 현재 Result baseline의 결합, legacy Envelope의 slice-only 한계를 먼저 드러내야 한다. 현재 안산의 보류를 우회하지 않으며 generic 합성 모델 검토는 공식 답변과 독립적으로 진행할 수 있다.

## 25. 감사 결론과 freeze 판단

| 감사 축 | 결론 |
|---|---|
| Contract | 최신 승인된 대체 범위를 적용하면 public API/의미/오류/지문/경계가 일관됨 |
| Implementation | 현재 exact 타입/계층 책임/실행 순서/상태 파생이 유효 계약에 대응함 |
| Trust Boundary | 실제 Review/공식 자료/선택 artifact 진실성과 보존은 외부 책임으로 제한됨 |
| Generic core | 공개 pure API까지 완료·FROZEN |
| 실제 안산 정책 | DRAFT/CONDITION_SLICE, 공식 의미/목록/구현·검토 준비가 남음 |

**ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**를 최종 판단으로 선택한다. Generic engine의 미완성을 뜻하지 않으며 실제 안산 정책별 blocker가 남아 있음을 함께 보존한다. 실제 안산 FULL·VERIFIED·신청 가능·Benefit Acceptance·Cashflow 적용을 승인하는 판단이 아니다.

## 26. 최종 검증·변경 범위 기록

작업 전 전체 기준: **5687 passed in 14.24s**. 현재 collect-only: **5687개**. 문서 작성 후 전체 pytest 재실행은 **5687 passed in 14.14s**다. 기존 전체 회귀와 GV01~GV15를 유지했고 신규 테스트/기대값/코드 변경은 없다.

사전 기록은 actual releases/pycache 제외 backend/tests/data/docs의 기존147개 파일 SHA256과 actual release6개 파일 경로/크기/수정시각이다. 최종 대조에서 **기존147개 모두 동일, 이 문서1개만 추가되어148개**, 기존 파일 수정/삭제 없음, 실제 release6개 metadata 동일을 확인했다. 지문 utility나 새 스크립트로 실제 Ansan Result/Review/실제 hash를 생성하지 않았다.

문서26개 절의 연속 순서·FI01~FI36의 유일/연속 ID·표 열 수·code fence·한국어 표기를 확인했다. 원본 source/golden/test 파일은 변경하지 않았으며 기존 명세에 남은 역사적 표현의 적용 순위는3절에 명시했다. 다음 subsystem 코드는 구현하지 않았다.

동결 대상은 M2.39 source와 기존 회귀/지문 계약이다. 새 runtime freeze flag·증명서·승인 record·패키지/데이터 schema version을 발급하는 작업이 아니다.
