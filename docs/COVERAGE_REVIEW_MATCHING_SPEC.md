# Coverage Review matching 계약 — M2.20

> 현재 구현 상태는 42절 M2.24를 따른다. 결과 값 모델·private ref resolver·Inventory/Implementation private matcher를 구현했다. subtree lookup·전체 Coverage 구조 검증·최종 결과는 없다. M2.24 승인으로 Implementation matcher는 Policy 객체 대신 상위에서 공급한 current_rule_version을 받는다. M2.23의 Inventory 미선언 사유 우선순위와 기존 결과 값 모델 계약은 유지한다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 설계 전용**. 추가 산출물은 이 파일 하나다. lookup/matcher/상태 Enum/결과 모델/CoverageResult/validator 코드는 작성하지 않았다.

최종 판단: **READY_TO_IMPLEMENT_REVIEW_MATCH_RESULT_MODELS**. 실제 검토 승인·전체 정책 FULL·운영 수용을 뜻하지 않는다.

## 1. 목적

명시적 review_ref가 가리키는 검토 기록을 현재 Coverage/Policy/자료/실행 구현 확인본에 사용할 수 있는지 판별하는 계약을 정한다. 정상 버전 갱신과 같은 버전 내용 모순을 분리하고, 어떤 stale 사유도 다른 구조 오류를 숨기지 못하게 한다.

최우선 기준은 COVERAGE_REVIEW_CONTEXT_SPEC.md 8~19·20~24절이다. COVERAGE_FINGERPRINT_SPEC.md 6~23·33~35절, ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md, POLICY_COVERAGE_SPEC.md, POLICY_BENEFIT_ACCEPTANCE_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md와 현재 모델/함수를 대조했다. 이전 포괄적 snapshot 불일치 문구보다 M2.12의 version별 stale/error 정밀화가 우선한다.

현재 InventoryCompletenessReview9필드, ImplementationBindingReview15필드, CoverageReviewContext7필드 및 EligibilityCoverage/Inventory/Binding/Policy/walk_nodes를 확인했다. 세 지문 함수와 기존 Manifest/Registry canonical hash·version 계약도 확인했다. 현재 facts·사용자 평가·공식 정책 원문을 새로 조회하지 않았다.

## 2. Matching 정의

matching은 **검토 metadata와 현재 대상 확인본의 일치성 판단**이다. 공식 조건 목록의 실제 완결성, subtree의 행정적 정답, 사람이 검토했다는 진실성, 원본 artifact의 존재를 새로 인증하지 않는다.

입력 구조·대상 결합을 검증한 뒤 MATCHED/MISSING/STALE 중 하나를 기록별로 설명한다. Coverage FULL/SLICE·사용자 PASS/FAIL/UNKNOWN·verification·Benefit Acceptance·현금 적용을 계산하지 않는다. 지금은 이 계약을 문서화할 뿐이다.

## 3. MATCHED / MISSING / STALE / ERROR

| 의미 | 최종 naming | 정상 결과인지 |
|---|---|---|
| 현재 대상·모든 필요한 version/지문 결합이 정확함 | MATCHED | 예 |
| 정상적인 검토 미확인/미선언 | MISSING | 예 |
| 대상은 맞으나 version 또는 구현 artifact 확인본이 달라짐 | STALE | 예 |
| 잘못된 참조/종류/대상 또는 같은 version의 내용 모순 | Data Error | 아니오. PolicyDataError 예외 |

MATCHED/MISSING/STALE를 후속 ReviewMatchStatus의 세 값으로 채택한다. ERROR를 정상 result status로 넣지 않고 UNKNOWN/BLOCKED/PARTIAL을 추가하지 않는다. M2.12의 CURRENT_MATCH 표현은 이번 MATCHED와 같은 의미이며 별도 네 번째 상태나 문자열 alias를 구현하지 않는다.

후속 최소 결과 모델은 다음 **두 별도 불변 값**으로 제안하며 이번에는 구현하지 않는다.

| 모델 | 모두 명시적으로 받을 필드 |
|---|---|
| InventoryReviewMatch | review_ref:str 또는 None, status:ReviewMatchStatus, stale_reasons:tuple[ReviewStaleReason,...], missing_reasons:tuple[ReviewMissingReason,...] |
| ImplementationReviewMatch | condition_id:str, rule_root_id:str, review_ref:str, status, stale_reasons, missing_reasons |

공통 base나 서로 맞지 않는 optional condition/root 필드를 가진 범용 result는 만들지 않는다. Inventory result의 ref는 원래 completeness_review_ref, Implementation result의 ref는 원래 필수 Binding ref다. Context=None이어도 원래 ref를 보존한다. Policy/Inventory/Review/Context 객체·전체 지문·reviewer·사용자 입력·FULL 상태를 결과에 복제하지 않는다.

후속 구조 검증 규칙: MATCHED는 두 reasons tuple이 비어 있고 ref가 있어야 한다. STALE은 ref가 있고 stale_reasons가 하나 이상, missing_reasons는 비어야 한다. MISSING은 stale_reasons가 비고 missing_reasons가 하나 이상이어야 한다. Inventory ref=None은 MISSING 및 INVENTORY_REVIEW_NOT_DECLARED 사유를 요구한다. Implementation ref는 항상 필수다. exact 타입·frozen/slots·순서/중복 없는 reasons·새 to_dict를 적용할 계획이다. to_dict는 실제 필드만 출력하고 status/reason Enum은 value, tuple은 새 list로 표현한다.

구체적인 값 모델 경계도 고정한다. 표의 모든 필드는 기본값 없이 필수다. ref는 기존 exact 비공백 str 계약을 따르고 Inventory에서만 None을 허용한다. Implementation condition_id/root는 기존 ConditionBinding 구조 계약과 같다. status와 reason 원소는 각각의 정확한 Enum, reasons는 정확한 tuple이어야 한다. 자동 문자열→Enum/리스트→tuple 변환·중복 제거·정렬은 하지 않고 잘못된 종류/순서/중복을 PolicyDataError로 거부한다.

Inventory ref가 있으면 INVENTORY_REVIEW_NOT_DECLARED를 넣을 수 없으며, 이때 MISSING은 (NO_REVIEW_CONTEXT,)만 가능하다. ref=None이면 MISSING으로 고정하고 (INVENTORY_REVIEW_NOT_DECLARED,) 또는 (NO_REVIEW_CONTEXT, INVENTORY_REVIEW_NOT_DECLARED)만 가능하다. Implementation MISSING은 정확히 (NO_REVIEW_CONTEXT,)다. STALE/MATCHED에는 missing reason이 없고, Inventory STALE에는 RULE_VERSION_CHANGED/IMPLEMENTATION_CHANGED를 넣지 않는다. 값 모델은 원인을 계산하지 않고 명시 결과의 로컬 정합성만 검사한다.

이 값의 수동 생성이 실제 비교 성공을 인증하지는 않는다. 결과 값 모델과 matcher의 올바른 계산/외부 검토 신뢰는 별개다. 결과 모델의 구체적인 validation 구현은 다음 승인 milestone에 한정한다.

## 4. Missing vs stale

MISSING은 현재 사용할 검토가 선언되지 않았거나 Context 자체가 제공되지 않은 정상 상태다. STALE은 명시 ref로 올바른 종류/대상의 record를 찾았지만 현재 version/구현 확인본이 다른 상태다.

과거 review가 실제로 참이었다는 역사적 진실성까지 STALE이 증명하지는 않는다. 이번 비교에서는 올바른 대상을 가리키는 과거/다른 확인본을 재사용할 수 없음을 뜻한다. version 숫자의 크기나 날짜로 “진짜 과거”를 추론하지 않고 정확한 동일성만 비교한다. 둘 다 검토 gate를 통과시키지 못하지만 이유는 별도로 보존한다.

## 5. Stale vs error 원칙

독립 비교 단위는 아래 세 version/내용 쌍과 별도 artifact identity다.

| 기준 version | 연결 지문 | version 같음 + 지문 다름 | version 다름 |
|---|---|---|---|
| inventory_version | inventory_fingerprint | Data Error | INVENTORY_VERSION_CHANGED |
| rule_version | policy_tree_fingerprint 및 subtree_fingerprint | 어느 하나라도 다르면 Data Error | RULE_VERSION_CHANGED |
| dataset_version | source_registry_fingerprint | Data Error | DATASET_VERSION_CHANGED |
| 별도 version 없음 | implementation_fingerprint | 단순 불일치는 IMPLEMENTATION_CHANGED | 해당 없음 |

**version 불일치는 그 version에 속한 지문 비교만 면제**한다. 예를 들어 rule version이 바뀌어 tree/subtree 지문 차이를 허용해도, inventory version이 같고 inventory 지문이 다르면 오류다. dataset 변경도 같은 rule version의 tree 모순을 면제하지 않는다. 모든 해당 비교를 끝내기 전에 첫 stale에서 반환하지 않는다.

같은 version의 evidence 순서/meaning/tree 내용 변경도 기존 지문 계약상 모순을 일으킬 수 있다. source만 고쳤으므로 rule version을 유지할 수 있다는 발행 계약과, 과거 review를 그대로 재사용할 수 있다는 주장은 다르다. COVERAGE_FINGERPRINT_SPEC.md 12절의 보수적인 review 재발급 경계를 유지한다.

## 6. Context=None 및 empty Context

| 상황 | Inventory 결과 | 존재하는 Binding별 Implementation 결과 |
|---|---|---|
| Context=None, inventory ref=None | MISSING, INVENTORY_REVIEW_NOT_DECLARED (M2.23 승인 우선순위) | MISSING, NO_REVIEW_CONTEXT |
| Context=None, inventory ref 있음 | MISSING, NO_REVIEW_CONTEXT | MISSING, NO_REVIEW_CONTEXT |
| Context 제공, inventory ref=None | MISSING, INVENTORY_REVIEW_NOT_DECLARED | 각 필수 ref를 정상 resolve·비교 |
| Context 제공, 명시 ref record 없음 | Data Error | Data Error |

Empty Context는 **collection 생성 자체는 정상**이다. 그러나 ref가 있는 Inventory/Binding을 함께 검증할 때 record가 없으면 broken reference 오류다. empty Context를 Context=None으로 취급하지 않는다. Context 제공 + inventory ref=None만 단독으로 보면 Inventory MISSING이지만, 다른 Binding ref가 없으면 전체 호출은 오류다.

Context가 없거나 ref=None이라는 이유로 현재 Coverage/tree의 구조 오류를 면제하지 않는다. 특히 비어 있지 않은 Policy와 zero bindings는 기존 unbound node 오류이며 empty Context를 붙여 정상 결과를 만들지 않는다. 누락된 condition binding은 review MISSING과 다른 Coverage completeness 문제이고, 가상의 Binding/ImplementationReviewMatch를 생성하지 않는다.

## 7. Inventory review resolution

Inventory.completeness_review_ref=None이면 lookup하지 않고 미선언으로 기록한다. Context=None이면 명시 ref가 있어도 lookup할 자료가 없으므로 MISSING이다.

Context가 있으면 선언한 **정확한 원문 ref**를 두 종류의 collection에서 찾는다. inventory_reviews에서 찾으면 사용하고 implementation_reviews에서만 찾으면 WRONG_REVIEW_TYPE이다. 어디에도 없으면 REVIEW_REF_NOT_FOUND다. strip·대소문자 변환·prefix 추론·대체 ref 선택을 하지 않는다.

Context constructor가 종류/유일성을 이미 검증한다. 잘못된 하위 타입·중복·소속 모델을 matcher에서 정상화하지 않는다. refs가 공백만 다르면 다른 identity다. 사용하지 않는 정상 historical record가 있다는 이유로 target ref를 자동 대체하지 않는다.

## 8. Inventory identity matching

비교 대상은 coverage.inventory다. Context가 있으면 우선 Context.policy_id/scope와 Inventory의 값을 대조한다. 다른 policy/quarter/annual/edition이면 Data Error다. Policy.policy_id와 Inventory.policy_id도 기존 구조 검증에서 같아야 한다.

선택한 Inventory record의 policy_id/scope도 현재 Inventory와 정확히 같아야 한다. record와 Context 간 소속은 constructor가 보장하지만 Context 자체가 현재 Coverage에 잘못 연결될 수 있으므로 외부 target 대조가 여전히 필요하다. 다른 정책/회차를 stale로 낮추지 않는다. 같은 값을 가진 별개 Scope 객체는 정상이다.

## 9. Inventory version/fingerprint

current inventory_version과 current fingerprint는 현재 Inventory에서 가져온다. 동일 version이면 지문을 정확히 대조하고 차이는 INVENTORY_FINGERPRINT_CONFLICT다.

version이 다르면 INVENTORY_VERSION_CHANGED를 모으며, 지문이 같든 다르든 이 쌍만으로 오류를 만들지 않는다. i0001/i0002의 숫자 우선순위나 최신 선택은 없다. 이 규칙은 Inventory review와 Implementation review의 inventory_version/fingerprint 모두에 적용한다. 같은 condition ID여도 의미/분류/evidence가 바뀌면 전체 Inventory 지문 결합으로 검출한다.

## 10. Dataset/source matching

current dataset_version/source_registry_fingerprint는 Context의 현재 baseline 필드다. 두 record 종류에 같은 비교 규칙을 적용한다.

dataset version이 다르면 DATASET_VERSION_CHANGED다. 이 경우 Registry 지문도 같거나 달라질 수 있으며 SOURCE_CHANGED 같은 중복 stale reason을 추가하지 않는다. dataset version이 같고 Registry 지문이 다르면 SOURCE_REGISTRY_FINGERPRINT_CONFLICT다.

이 비교가 Registry/Manifest/파일의 실제 존재와 현재 내용을 인증하지는 않는다. Context의 baseline을 검증된 자료에서 공급하고 동일 dataset label의 과거 덮어쓰기를 탐지하는 것은 외부 orchestration/발행 이력 책임이다. Matcher가 Registry를 재조회하거나 원문을 열지 않는다.

## 11. Implementation review resolution

ConditionBinding.implementation_review_ref는 기존대로 필수 str이다. 이를 optional로 바꾸지 않는다.

Context=None이면 각 기존 Binding은 MISSING/NO_REVIEW_CONTEXT다. Context가 있으면 정확한 ref로 implementation_reviews를 찾는다. inventory review를 가리키면 WRONG_REVIEW_TYPE, 어느 종류에도 없으면 REVIEW_REF_NOT_FOUND다. 여러 Binding이 같은 ref를 가리켜도 한 record는 condition/root 한 쌍만 선언하므로 다른 target이면 다음12절에서 오류다. 공유 review라는 이유로 대상 대조를 생략하지 않는다.

## 12. Condition/root matching

선택한 Implementation record는 현재 Inventory의 policy/scope, 현재 Binding의 condition_id/rule_root_id와 모두 정확히 같아야 한다. 하나라도 다르면 Data Error다. version 갱신·같은 subtree 지문·같은 표시명으로 이 오류를 덮지 않는다.

Binding root가 현재 Policy에 실제로 있는지, 다른 condition과 subtree가 겹치거나 중복 소유되는지는 **review matching 이전 구조 검증** 책임이다. 없는 root는 STALE review가 아니라 잘못된 Coverage mapping이다. 과거 ref를 새 condition/root에 연결하고 matcher가 자동 remap하도록 하지 않는다.

## 13. Rule version

current rule_version의 유일 원천은 Policy.rule_version이다. Context에 version을 중복 추가하지 않는다.

record와 다르면 RULE_VERSION_CHANGED다. 내용이 그대로여도 재검토가 필요하며 자동 승계하지 않는다. 이때 tree/subtree 지문 차이는 이 rule-version 쌍의 정상 갱신으로 처리한다. 같은 rule version이라면 다음14~15절의 두 지문 모두를 대조한다.

## 14. Policy tree fingerprint

current 값은 기존 fingerprint_policy_tree(policy)로 계산한다. 같은 rule_version에 다른 지문이면 POLICY_TREE_FINGERPRINT_CONFLICT다. 동일 root/subtree가 다른 상위 결합에 놓여 정책 의미가 바뀌는 것도 전체 tree 지문이 식별한다.

rule_version이 다르면 지문 차이를 별도 오류/stale reason으로 만들지 않는다. 그러나 다른 inventory/dataset 쌍의 모순 검사는 계속한다. 계산 함수가 PolicyDataError를 내면 그대로 실패하며 STALE/UNKNOWN으로 바꾸지 않는다.

## 15. Subtree fingerprint

구조 검증으로 찾은 현재 Binding root를 기존 fingerprint_rule_subtree(root)에 전달한다. 같은 rule_version에 다른 subtree 지문이면 SUBTREE_FINGERPRINT_CONFLICT다. rule_version이 다르면 이 차이는 RULE_VERSION_CHANGED에 포함한다.

root ID만 같은 것으로 충분하지 않고 root 자체·descendant·연산자·순서·값·근거까지 고정한 지문을 대조한다. 같은 subtree가 다른 부모에 있어 subtree 지문이 같아도, 같은 rule version의 전체 tree가 다르면14절 오류다. root lookup/unsupported node/인코딩 실패는 정상 match state가 아닌 Data Error다.

## 16. Implementation fingerprint

current 값은 Context.implementation_fingerprint다. 별도 implementation_version이 없으므로 불일치는 **항상 IMPLEMENTATION_CHANGED라는 stale 사유**다. dataset/rule label이 같아도 이 불일치만으로 Data Error라고 단정하지 않는다. 새 실행 artifact일 수 있기 때문이다.

같은 호출에 condition/root 오류나 같은 version의 tree/Inventory/Registry 모순이 있으면 예외가 우선한다. implementation 지문이 같다는 사실도 코드의 정답·실행 환경 전체 재현·실제 artifact bytes 진위를 인증하지 않는다. 외부가 실제 검토한 artifact와 baseline을 공급해야 한다. Inventory completeness record에는 implementation 지문 필드가 없으므로 이 gate를 억지로 적용하지 않는다.

## 17. reviewed_at / artifact 처리

reviewed_at은 matching·최신 선택·만료의 기준으로 사용하지 않는다. 오래된 날짜여도 모든 대상/확인본이 같으면 MATCHED일 수 있고 새 날짜여도 같은 version 내용 모순은 오류다. 현재 날짜/자동 expiry/source freshness 정책을 추가하지 않는다.

review_artifact_ref는 기존 값 모델이 검증한 참조로만 보존한다. 실제 문서·Git·파일·URL을 열거나 내용을 hash하지 않는다. 어떤 reviewer가 실제로 무엇을 검토했는지 확인하는 외부 과정은 별도다.

## 18. Matching phase/order

아래 순서는 **한 Coverage 실행 전체**의 고정 순서다. record 하나에서 STALE을 발견했다고 다음 record의 오류 검사를 생략하지 않는다.

| 단계 | 책임·고정 순서 |
|---|---|
| 0 현재 입력/구조·자료 준비 | 정확한 Coverage/Policy/Context 타입, 현재 policy 일치, 기존 tree 구조·root/소유/겹침/unbound/전체 결합 검증. 성공 뒤 current Inventory 지문 → 전체 Tree 지문 → condition_id순 각 Binding subtree 지문 계산 |
| 1 reference/type/target integrity | Context와 현재 policy/scope 대조. Inventory slot → condition_id순 Binding slots. 각 slot에서 ref resolve → review 종류 → policy → scope → implementation이면 condition → root |
| 2 version flags | 선택 record별 inventory version → rule version(implementation만) → dataset version → implementation identity(implementation만). 독립 stale flags를 지역값으로 모으되 결과 반환 금지 |
| 3 guarded content consistency | Inventory slot → condition_id순 Binding slots. 각 record에서 같은 inventory version의 Inventory 지문 → 같은 rule version의 tree → subtree → 같은 dataset version의 Registry 지문. 모순은 즉시 예외 |
| 4 정상 결과 구성 | 어느 단계에도 오류가 없을 때만 slot별 MATCHED/MISSING/STALE과 canonical reasons 반환 |

전제 구조 검증은 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md의 기존 설계이며 아직 구현되지 않았다. matching 설계가 그 gate를 구현 완료로 간주하지 않는다. current 지문 계산도 Context=None의 정상 미검토 처리를 이용해 구조/인코딩 오류를 숨기지 않도록 현재 자료 준비 경로에서 수행한다. 단 이 문서가 새 standalone preflight API를 만들라는 뜻은 아니다.

**fail-fast Data Error, stale 이유는 전체 수집**을 채택한다. 모든 오류를 모으는 framework는 만들지 않는다. 한 record의 Phase1 identity 오류는 그 record의 stale보다 먼저 거부하고, 다른 record에서 발견된 guarded conflict도 앞서 모은 stale보다 우선한다. Phase3에서 같은 record에 tree/subtree 모순이 둘 다 있으면 표 순서상 tree 오류를 먼저 보고한다. 부분 성공/STALE 결과를 예외와 함께 반환하지 않는다.

## 19. Stale reasons

후속 ReviewStaleReason은 다음 네 값과 이 **고정 순서**만 사용한다.

1. INVENTORY_VERSION_CHANGED
2. RULE_VERSION_CHANGED
3. DATASET_VERSION_CHANGED
4. IMPLEMENTATION_CHANGED

InventoryReviewMatch에서는1·3만 허용한다. ImplementationReviewMatch에서는1~4 모두 가능하다. 여러 독립 사유는 중복 없이 canonical 순서의 tuple로 보존한다. “첫 stale 하나” 방식은 감사 정보가 부족해 미채택이다. M2.3의 독립 제외 사유를 함께 보존하는 철학을 재사용하되 Bridge 모델이나 코드에 의존하지 않는다.

SOURCE_SNAPSHOT_CHANGED/TREE_CHANGED/SUBTREE_CHANGED를 stale reason으로 추가하지 않는다. 해당 version이 바뀌었다면 이미 version reason에 포함되고, 같은 version의 내용 차이라면 Data Error다. 숫자 비교·오래된 날짜라는 별도 사유도 없다.

## 20. Missing reasons

후속 ReviewMissingReason은 다음 두 값과 순서만 사용한다.

1. NO_REVIEW_CONTEXT
2. INVENTORY_REVIEW_NOT_DECLARED

M2.23 승인에 따라 Inventory에서 ref=None이면 Context 유무와 무관하게2만 반환한다. Context=None이고 ref가 있으면1만이다. M2.20의 두 사유 동시 반환 설계는 이 matcher 우선순위로 대체한다. 기존 M2.21 값 모델은 두 사유 조합도 허용하지만 matcher는 생성하지 않는다. Implementation은 ref가 필수이므로1만 가능하다.

REVIEW_RECORD_NOT_AVAILABLE/IMPLEMENTATION_REVIEW_UNAVAILABLE은 MISSING reason으로 만들지 않는다. Context가 제공됐는데 명시 ref가 없으면 정상 미검토가 아니라 broken reference 오류이기 때문이다. 그래서 missing_reasons가 있다고 다른 slot의 오류를 무시해서는 안 된다.

## 21. Error contract

기존 PolicyDataError는 code 인자를 받거나 .code를 보장하는 클래스가 아니다. 이번에는 새 오류 클래스/Enum/속성을 구현하지 않는다. 후속 matcher는 다음 안정 식별자를 **메시지 prefix**로 사용할 수 있도록 명세화하고, field/조건 ID 등 최소 target을 알려준다. 원본 profile·meaning·전체 payload는 넣지 않는다.

| prefix | 의미 |
|---|---|
| INVALID_MATCH_INPUT | 정확한 입력 타입/현재값 공급 계약 위반 |
| CONTEXT_POLICY_MISMATCH / CONTEXT_SCOPE_MISMATCH | 정상 Context를 다른 현재 대상에 연결 |
| REVIEW_REF_NOT_FOUND | Context 제공 + 명시 ref가 두 collection에 없음 |
| WRONG_REVIEW_TYPE | ref가 다른 종류 record를 가리킴 |
| REVIEW_POLICY_MISMATCH / REVIEW_SCOPE_MISMATCH | 선택 record의 대상이 현재와 다름 |
| REVIEW_CONDITION_MISMATCH / REVIEW_RULE_ROOT_MISMATCH | implementation ref의 잘못된 Binding 대상 |
| INVENTORY_FINGERPRINT_CONFLICT | 같은 inventory version의 지문 모순 |
| POLICY_TREE_FINGERPRINT_CONFLICT | 같은 rule version의 전체 tree 모순 |
| SUBTREE_FINGERPRINT_CONFLICT | 같은 rule version의 subtree 모순 |
| SOURCE_REGISTRY_FINGERPRINT_CONFLICT | 같은 dataset version의 Registry 모순 |

이미 발생한 모델/지문/후속 구조 validator의 PolicyDataError는 원래 계층으로 전파하고 matcher reason으로 감싸 UNKNOWN/STALE을 만들지 않는다. Context constructor가 막는 잘못된 collection/중복 ref/record 소속 문제를 matcher에서 재구성하거나 필터링하지 않는다. raw dict를 Context로 자동 변환하지 않는다.

## 22. Current snapshot Source of Truth

| current value | 유일한 원천 |
|---|---|
| policy_id/scope/inventory_version | coverage.inventory |
| condition_id/rule_root_id/명시 implementation ref | 현재 ConditionBinding |
| rule_version | 현재 Policy.rule_version |
| inventory_fingerprint | fingerprint_condition_inventory(coverage.inventory) |
| policy_tree_fingerprint | fingerprint_policy_tree(policy) |
| subtree_fingerprint | 구조 검증으로 찾은 Binding root의 fingerprint_rule_subtree(root) |
| dataset_version | 제공된 CoverageReviewContext.dataset_version |
| source_registry_fingerprint | 제공된 Context.source_registry_fingerprint |
| implementation_fingerprint | 제공된 Context.implementation_fingerprint |

**C 선택: 상위 validator/orchestration의 호출 지역값**을 채택한다. 별도 CoverageCurrentSnapshot 모델이나 Context 중복 version을 만들지 않는다. record의 과거 값에서 current baseline을 역으로 채우지 않는다.

Context=None이면 dataset/source/implementation baseline은 얻을 수 없다. 추론하지 않고 해당 review 비교를 하지 않으며 MISSING이다. 현재 Inventory/Policy/root 자체의 구조·지문 유효성 검사는 별도로 유지한다. Context baseline이 실제 선택 release/artifact와 같은지는 신뢰된 외부 준비 계층 책임이다. 사용자/LLM이 제출한 current hash 선언을 신뢰하는 API를 만들지 않는다.

## 23. Fingerprint calculation 위치

A 각 matcher가 실제 객체 지문을 반복 계산하는 방식은 단순하지만 여러 Binding에서 같은 Inventory/전체 Tree를 재계산한다. B 별도 immutable CurrentSnapshot은 모델/중복 상태가 늘어난다. **C 상위 검증 호출에서 한 번 계산하고 private matcher에 공급**을 채택한다.

Inventory 지문과 전체 Tree 지문은 호출당 각각1회, 선택 subtree 지문은 Binding root마다1회 계산한다. 값은 함수 지역값으로 보관하고 전역 cache·DB·환경·최신 release 재조회는 없다. 두 private matcher는 supplied current 지문을 exact lowercase hex64 구조로 받아 대조하며 외부 사용자에게 raw hash를 직접 제출받는 public API가 아니다.

현재 Scope/모델/세 utility의 type/JSON/UTF-8 규칙과 GV01~GV15 계약은 그대로다. 어느 utility가 실패해도 match 결과를 만들지 않는다. 현재 지문 공급을 검토 대상 review의 값으로 대신하면 자기검증이 되므로 금지한다.

## 24. Subtree lookup 위치

후속 Coverage structural validator가 정확한 Policy와 기존 walk_nodes를 사용해 호출 지역 node_id→node lookup을 준비한다. 모든 root의 존재·소유·겹침·최상위 결합을 검증한 뒤 root를 지문 함수에 전달한다.

review matcher와 fingerprint_rule_subtree는 lookup을 하지 않는다. 현재 Policy 생성자는 중복 ID를 거부하며, 구조 검증 실패/미지원 node를 정상 stale로 바꾸지 않는다. zero Binding/비어 있지 않은 Policy의 unbound 오류도 기존 설계 그대로다.

이 문서는 lookup helper나 structural validator를 구현하지 않는다. 현재 Policy만 정상 생성됐다는 사실이 Coverage mapping까지 검증됐다는 뜻은 아니다.

## 25. Review lookup 방식

Context public API는 확장하지 않는다. 후속 matching 모듈의 작은 private resolver가 tuple을 정확한 review_ref로 순회하면 현재 규모에 충분하다. 두 종류 전체의 ref 유일성은 기존 Context가 보장한다. mutable lookup cache/global registry/최신 선택은 없다.

반대 collection에만 같은 ref가 있으면 wrong type, 둘 다 없으면 not found다. lookup 함수는 파일/URL을 해석하지 않으며 같은 문자열 prefix·strip 결과·유사 condition으로 대체하지 않는다. resolver의 오류 선택이 tuple 입력 순서에 의존하지 않는다.

## 26. Matcher API 후보 — 채택 범위

공개 aggregate matcher를 새로 늘리기보다 **후속 validator가 조합하는 private 두 함수**를 채택한다. 아래는 M2.23/M2.24에서 구현한 시그니처다. M2.24 승인에 따라 Implementation matcher의 Policy 인자를 current_rule_version 공급 방식으로 변경했다.

```text
_match_inventory_review(
    inventory: ConditionInventory,
    review_context: CoverageReviewContext | None,
    *,
    current_inventory_fingerprint: str,
) -> InventoryReviewMatch

_match_implementation_review(
    inventory: ConditionInventory,
    binding: ConditionBinding,
    review_context: CoverageReviewContext | None,
    *,
    current_inventory_fingerprint: str,
    current_rule_version: str,
    current_policy_tree_fingerprint: str,
    current_subtree_fingerprint: str,
) -> ImplementationReviewMatch
```

Inventory에서 current inventory version을 얻고 current_rule_version은 상위 호출자가 현재 Policy.rule_version에서 공급한다. matcher는 Policy를 받거나 지문 계산/순회하지 않는다. Context에서 current dataset/source/implementation 값을 얻고 선택 ref record만 비교한다. binding은 상위 coverage.bindings의 현재 원소이며 root와 지문은 사전 구조 검증으로 연결됐다는 내부 호출 계약이다. 그 상위 구조 검증은 아직 미구현이다. private API가 악의적 caller의 거짓 hash/다른 Binding을 인증한다고 주장하지 않는다.

전제조건과 공통 Phase1~3 처리는 상위 호출이 조합한다. 각 helper에서도 해당 ref/type/target·모든 독립 guarded conflict를 검사하고, 호출자는 하나라도 실패하면 전체 정상 반환을 만들지 않는다. Inventory 결과 한 개와 condition_id순 Implementation 결과 tuple은 상위의 지역 결과로 사용할 수 있지만, 새 CoverageResult/aggregate class를 이 단계에서 설계·구현하지 않는다.

다음 값 모델 단계에는 이 두 matcher/resolver나 lookup을 포함하지 않는다. 공개 evaluate_eligibility_coverage의 기존 설계는 여기서 시그니처를 바꾸거나 구현하지 않는다.

## 27. Historical reviews

같은 policy/scope의 여러 version·같은 condition/root의 여러 review는 기존 Context에 공존 가능하다. 실제 대상은 현재 Inventory/Binding의 정확한 ref로만 선택한다. 미참조 정상 record의 version/fingerprint가 오래됐다는 이유로 현재 결과를 바꾸거나 오류를 만들지 않는다.

단 Context의 구조·종류·ref 유일성·policy/scope는 미참조 record에도 적용하는 기존 constructor 계약이다. “미참조이므로 잘못된 타입은 무시”하지 않는다. reviewed_at/숫자 version/tuple 첫 항목/가장 가까운 fingerprint를 기준으로 최신 review를 자동 선택하지 않는다.

## 28. Determinism

동일 Coverage/Policy/Context는 동일 결과·reasons·오류 우선순위를 가져야 한다. Inventory review slot을 먼저, Implementation slots는 condition_id ASCII 오름차순으로 처리한다. binding tuple 순서·Context review tuple 순서가 달라도 동일 ref 내용이면 semantic matching 결과는 같다. 기존 원래 모델 equality/to_dict의 순서는 그대로다.

오류는18절 phase와 slot/field 순서대로 fail-fast다. stale/missing reasons는19~20절의 canonical order이며 중복을 넣지 않는다. 현재시간·난수·locale·환경·네트워크는 없다. 외부 artifact가 거짓이면 동일한 거짓 선언에 대한 비교만 재현된다는 신뢰 한계도 유지한다.

## 29. CoverageResult와 책임 분리

MATCHED는 **그 review slot의 gate 통과**일 뿐 Coverage FULL이 아니다. missing condition binding·inventory 공식 완결성·구조 오류·미지원 입력/evaluator·별도 검증 gate가 남을 수 있다.

미래 전체 흐름은 현재 구조 검증 + review matching → 별도 CoverageResult다. Context가 존재하고 refs가 비지 않았다는 이유만으로 FULL을 파생하지 않는다. M2.12의 “모든 필요한 review가 현재 확인본과 일치해야 함”을 지킨다. MISSING/STALE을 합쳐 존재하는 것처럼 처리하지 않는다.

이번에는 CoverageResult의 필드·status property·factory를 확정하거나 구현하지 않는다. Acceptance/verification/사용자 PolicyEvaluation/Cashflow/Benefit Bridge도 연결하지 않는다.

## 30. Current Ansan example

현재 실제 Q3 release002는 resident/birth 일부만 구현한 DRAFT/CONDITION_SLICE다. real ConditionInventory/실제 completeness·implementation review는 없고 ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED다.

실제 Inventory/ref/지문을 만들어 matching을 통과시켰다고 주장하지 않는다. 이 문서의 일치 규칙으로 거주기간·등록분류의 누락이나 공식 의미 미확정을 해결할 수 없다. FULL/Acceptance 불가·현금 자동 반영 없음이라는 기존 경계는 유지한다. release001/002와 기존 SHA 선언은 수정하지 않는다.

## 31. Synthetic MATCHED example

문서상 기호 예시이며 실제 기록이나 hash를 발급한 것이 아니다. P=SYNTH-POLICY, S=2026/Q3, Inventory i0001과 조건 COND_A, Policy r0001, Binding COND_A→RULE_A를 가정한다.

I/T/U/R/E는 각각 현재 Inventory/전체 Tree/subtree/Registry/implementation의 **서로 다른 대상 지문을 나타내는 기호**다. 임의 AAA 문자열을 실제 hex64 입력이라고 사용하지 않는다. Context는 dataset SYNTH-DATA-1, source=R, implementation=E다.

Inventory ref INV-1과 implementation ref IMPL-A가 정확한 종류/대상의 records를 가리키고, 각각 필요한 version·I/T/U·dataset·R/E가 모두 같으면 두 slot은 MATCHED이며 두 reasons tuple은 비어 있다. 조건 목록의 실제 완결성/구현 정답은 외부 검토 전제다. 여기서 FULL 결과를 생성하지 않는다.

## 32. Synthetic STALE example

동일 target의 IMPL-A가 r0001을 기록하고 현재 Policy가 r0002이며 다른 모든 비교 단위는 같다고 가정하면 STALE, reasons=(RULE_VERSION_CHANGED,)다. 이 경우 T/U가 바뀌어도 같은 reason이고 같아도 자동 승계하지 않는다.

추가로 inventory i0001→i0002, dataset SYNTH-DATA-1→SYNTH-DATA-2, implementation E1→E2까지 바뀌고 어떤 같은-version conflict도 없다면 reasons는 (INVENTORY_VERSION_CHANGED, RULE_VERSION_CHANGED, DATASET_VERSION_CHANGED, IMPLEMENTATION_CHANGED)다. Registry 차이는 dataset reason에 포함한다.

## 33. Synthetic ERROR example

현재 Binding이 COND_A→RULE_A인데 명시 IMPL-A record가 COND_B→RULE_A이면 REVIEW_CONDITION_MISMATCH다. rule_version/dataset이 달라도 STALE로 낮추지 않는다.

또 Inventory version이 양쪽 i0001인데 I가 다르면 INVENTORY_FINGERPRINT_CONFLICT다. 이와 동시에 rule_version이 r0001→r0002로 바뀌었더라도 오류다. dataset이 같고 Registry만 다른 경우도 다른 version stale와 독립적으로 SOURCE_REGISTRY_FINGERPRINT_CONFLICT다.

## 34. Synthetic MISSING example

Context=None이고 completeness ref가 INV-1이면 Inventory 결과는 MISSING/(NO_REVIEW_CONTEXT,), 기존 각 Binding도 같은 missing reason을 가진다. completeness ref까지 None이면 M2.23 승인에 따라 Inventory는 MISSING/(INVENTORY_REVIEW_NOT_DECLARED,)만 반환한다.

Context가 제공되고 completeness ref=None이면 Inventory MISSING/(INVENTORY_REVIEW_NOT_DECLARED,)다. 그러나 Context가 empty인데 명시 INV-1 또는 IMPL-A가 없다면 MISSING 예시가 아니라 REVIEW_REF_NOT_FOUND다. 이 차이를 변경하지 않는다.

## 35. 수동 시나리오

아래 **80개 문서상 계약 사례**는 신규 실행 테스트가 아니다. I/T/U/R/E는31절과 같은 기호다. 다른 명시가 없으면 current 구조와 나머지 독립 gate는 정상이라고 가정한다. “Error”는 정상 결과를 반환하지 않는 Data Error다.

| ID | 사례 | 기대 |
|---|---|---|
| RM01 | Context=None, inventory ref=None | Inventory MISSING, INVENTORY_REVIEW_NOT_DECLARED 단독 (M2.23 승인) |
| RM02 | Context=None, inventory ref 있음 | Inventory MISSING, NO_REVIEW_CONTEXT |
| RM03 | Context=None, Binding ref 있음 | Implementation MISSING, NO_REVIEW_CONTEXT |
| RM04 | exact Inventory ref/모든 현재 값 동일 | MATCHED |
| RM05 | Context 제공, 명시 Inventory ref 없음 | REVIEW_REF_NOT_FOUND Error |
| RM06 | Inventory ref가 implementation record 지목 | WRONG_REVIEW_TYPE Error |
| RM07 | 현재 Coverage와 Context policy 다름 | CONTEXT_POLICY_MISMATCH Error |
| RM08 | 현재 Q3와 Context Q2/annual 다름 | CONTEXT_SCOPE_MISMATCH Error |
| RM09 | Inventory version/I 모두 동일 | 해당 pair 통과 |
| RM10 | Inventory version 다름, I도 다름 | STALE, INVENTORY_VERSION_CHANGED |
| RM11 | 같은 Inventory version, I 다름 | INVENTORY_FINGERPRINT_CONFLICT Error |
| RM12 | Inventory review dataset 변경 | STALE, DATASET_VERSION_CHANGED |
| RM13 | 같은 dataset, R 다름 | SOURCE_REGISTRY_FINGERPRINT_CONFLICT Error |
| RM14 | Context 있음, inventory ref=None | Inventory MISSING, INVENTORY_REVIEW_NOT_DECLARED |
| RM15 | implementation condition 정확히 일치 | identity gate 통과 |
| RM16 | implementation condition 다름 | REVIEW_CONDITION_MISMATCH Error |
| RM17 | implementation root 정확히 일치 | identity gate 통과 |
| RM18 | implementation root 다른 명시 record | REVIEW_RULE_ROOT_MISMATCH Error |
| RM19 | 선택 implementation record의 policy가 현재와 다름 | Context target 대조 또는 record identity Error |
| RM20 | 선택 implementation record의 scope가 현재와 다름 | Context target 대조 또는 record identity Error |
| RM21 | rule version/T/U 모두 같음 | rule pair 통과 |
| RM22 | rule version 다름 | STALE, RULE_VERSION_CHANGED |
| RM23 | 같은 rule version, T 다름 | POLICY_TREE_FINGERPRINT_CONFLICT Error |
| RM24 | 같은 rule version, U 다름 | SUBTREE_FINGERPRINT_CONFLICT Error |
| RM25 | implementation review dataset 변경 | STALE, DATASET_VERSION_CHANGED |
| RM26 | implementation review와 같은 dataset, R 다름 | SOURCE_REGISTRY_FINGERPRINT_CONFLICT Error |
| RM27 | implementation E 다름, 나머지 동일 | STALE, IMPLEMENTATION_CHANGED |
| RM28 | rule + dataset 변경 | 두 stale reasons 고정 순서 |
| RM29 | inventory + rule 변경 | 두 stale reasons 고정 순서 |
| RM30 | rule + E 변경 | RULE_VERSION_CHANGED, IMPLEMENTATION_CHANGED |
| RM31 | inventory/rule/dataset/E 모두 변경, 모순 없음 | 네 stale reasons 고정 순서 |
| RM32 | 현재 Binding root가 정상 tree에 있음 | 구조 gate 이후 U 계산 |
| RM33 | 현재 Binding root가 tree에 없음 | matching 전 구조 Error |
| RM34 | 현재 unsupported node가 지문 계산에 들어옴 | PolicyDataError 전파 |
| RM35 | 같은 condition의 과거/현재 record 여러 개 | 명시 ref만 선택 |
| RM36 | 명시 ref가 과거 다른 version record | STALE, 최신 record로 대체 금지 |
| RM37 | 명시 ref가 현재 record, 과거 record 공존 | MATCHED 가능 |
| RM38 | tuple 첫 항목/날짜가 더 새롭지만 다른 ref | 선택하지 않음 |
| RM39 | implementation record의 같은 Inventory version/I 다름 | INVENTORY_FINGERPRINT_CONFLICT Error |
| RM40 | 같은 rule version/T와 U 모두 다름 | Phase3 순서상 T conflict 먼저 Error |
| RM41 | target condition 다름 + rule version 다름 | target Error, STALE 아님 |
| RM42 | Binding ref가 Inventory record를 지목 | WRONG_REVIEW_TYPE Error |
| RM43 | 다른 policy record를 Context 안에 직접 넣음 | 기존 Context constructor Error |
| RM44 | 다른 scope record를 Context 안에 직접 넣음 | 기존 Context constructor Error |
| RM45 | 동일 입력 반복 | 동일 결과·reasons·오류 순서 |
| RM46 | Context review tuple 순서 변경, 명시 refs/내용 동일 | matching 의미 동일 |
| RM47 | 필요한 review 모두 MATCHED, 다른 condition Binding 누락 | matching이 FULL을 만들지 않음 |
| RM48 | 사용자 PolicyEvaluation PASS→FAIL | matching 입력/결과에 영향 없음 |
| RM49 | 사용자 BirthFact/소득 변경 | matching 입력/결과에 영향 없음 |
| RM50 | 시스템 날짜 변경 | matching 결과 영향 없음 |
| RM51 | 현재 안산 real Inventory 없음 | 실제 matching/FULL 실행 주장 금지 |
| RM52 | ResidenceHistory 의미 미확정 | 보류·미구현 유지 |
| RM53 | 현재 안산 actual reviews 없음 | 실제 완료 record 생성 금지 |
| RM54 | E 동일 + 나머지 정확 | implementation MATCHED 가능 |
| RM55 | 같은 dataset/rule version, E만 다름 | STALE, Error 아님 |
| RM56 | review_artifact_ref가 URL/파일처럼 보임 | 열지 않고 값 모델 계약 유지 |
| RM57 | reviewed_at 오래됐으나 확인본 모두 같음 | MATCHED 가능 |
| RM58 | reviewed_at만 더 최근이고 같은-version conflict 있음 | 날짜로 덮지 않고 Error |
| RM59 | 날짜 기반 expiry를 외부에서 요청하지 않음 | 새 시간 stale gate 없음 |
| RM60 | 동일 Inventory 반복/조건 순서만 변경 | 기존 지문 결정성 유지, 대상 내용 같음 |
| RM61 | 동일 전체 Policy Tree 반복 | 기존 T 지문 결정성 유지 |
| RM62 | 동일 subtree 반복 | 기존 U 지문 결정성 유지 |
| RM63 | empty Context + inventory 명시 ref 있음 | REVIEW_REF_NOT_FOUND Error |
| RM64 | empty Context + inventory ref=None + Binding ref 있음 | Inventory 미선언이어도 Binding broken ref Error |
| RM65 | empty Context를 Inventory slot만 보며 ref=None | MISSING, Context=None과 audit 사유 구별 |
| RM66 | inventory version 다름 + 같은 dataset/R 모순 | source conflict Error가 stale보다 우선 |
| RM67 | dataset 다름 + 같은 Inventory version/I 모순 | Inventory conflict Error |
| RM68 | rule version 다름 + 같은 Inventory version/I 모순 | Inventory conflict Error |
| RM69 | Inventory version 다름 + 같은 rule version/T 모순 | tree conflict Error |
| RM70 | dataset 다름 + 같은 rule version/U 모순 | subtree conflict Error |
| RM71 | E 다름 + condition/root identity 틀림 | identity Error |
| RM72 | 첫 Binding은 STALE, 뒤 Binding 같은-version conflict | 전체 Error, 부분 정상 반환 없음 |
| RM73 | 첫 Binding은 MATCHED, 뒤 명시 ref 없음 | 전체 Error |
| RM74 | version이 다르나 content 지문은 같음 | 여전히 해당 version stale |
| RM75 | 검토 version 숫자가 current보다 커 보임 | 숫자 최신 판단 없이 CHANGED stale |
| RM76 | policy/scope 같고 미참조 정상 historical record의 I/T/U 다름 | 그 record를 대조하지 않아 결과 영향 없음 |
| RM77 | ref 원문 앞뒤 공백만 다름 | 다른 ref, 자동 strip lookup 금지 |
| RM78 | Context=None이나 현재 mapping 구조 오류 | 구조 Error, MISSING으로 덮지 않음 |
| RM79 | Context=None이나 현재 지문 JSON/UTF-8 계산 실패 | Data Error 전파 |
| RM80 | Binding 순서 변경, 여러 독립 오류 존재 | condition_id순/phase순의 동일 첫 오류 |

## 36. 미해결 문제와 검증 기록

**기존 stale/error 계약과 충돌하는 미결정은 없다.** empty Context·broken explicit ref는 기존 M2.12대로 오류이고, 각 version/지문 쌍의 독립 guarded conflict가 다른 stale보다 우선한다. implementation hash 변경만 stale인 경계도 유지한다. 별도 CurrentSnapshot 모델은 필요하지 않다.

다음에 먼저 구현할 대상은 matching 결과의 타입/상태·사유 표현이다. 이후 구조 validator와 matching을 연결하려면 현재 root/ownership/unbound 검증의 구현이 필요하다. 이 의존관계를 건너뛰어 현재 모델만으로 구조가 검증됐다고 주장하지 않는다. CoverageResult의 stale audit와 gate는 별도 설계가 남아 있으며 이번에 완성하지 않는다.

실제 engine artifact의 준비/증빙, 신뢰된 Context baseline 공급·발행 이력/동일 version 덮어쓰기 검토·source freshness·외부 검토 진실성은 계속 외부 책임이다. 이 한계를 새로운 인증/서명/DB 플랫폼으로 선행 확대하지 않는다.

작업 전 actual releases를 제외한 backend/tests/data/docs **115개 파일**의 SHA256, 실제 두 release 여섯 파일의 경로/길이/수정시각을 기록했다. 전체 pytest는 **3984 passed in 10.37s**다. Inventory6개/Tree7개/subtree2개, 총 GV01~GV15가 기존 suite에서 통과했다. canonical payload/JSON/UTF-8 길이/literal digest 계약은 변경하지 않았다. 신규 실행 테스트는 없다. 80개 수동 사례는 아직 없는 matcher의 실행 테스트가 아니다.

최종 대조에서 기존115개 파일의 SHA256은 모두 동일하고 수정·삭제는 없다. 추가는 이 명세 한 개뿐이다. 실제 release 여섯 파일의 경로·길이·수정시각도 기준선과 동일하다. actual releases를 새 hash/Review 대상으로 계산하거나 기존 데이터/SHA 선언을 변경하지 않았다.

문서의38개 절과 RM01~RM80이 순서대로 유일하게 존재함을 확인했다. 기존 fingerprint 명세의15개 golden JSON·byte 길이·digest와 세 기존 테스트 파일의 literal을 직접 대조해 모두 동일함을 확인했다. 한국어 표기와 금지 구현 부재도 확인했다. 이는 아직 없는 matching 함수/결과 모델의 실행 검증을 뜻하지 않는다.

## 37. 추천 후속 구현 순서

| 순서 | 단일 승인 작업 범위 | 포함하지 않을 것 |
|---|---|---|
| 1 | ReviewMatchStatus/ReviewStaleReason/ReviewMissingReason의 값 계약과 두 ReviewMatch 불변 결과 모델·합성 구조 테스트 | 실제 비교·lookup·지문 재계산·CoverageResult |
| 2 | 현재 Coverage/tree의 root/소유/겹침/unbound/전체 결합 검증을 기존 명세대로 작은 단계로 구현 | review matching/FULL·실제 정책 승격 |
| 3 | private ref resolver와 target identity 확인 | version/지문 비교·결과 gate |
| 4 | 두 private matcher의 독립 version/guarded fingerprint 비교·canonical reasons | FULL·Acceptance/Bridge |
| 5 | 별도 CoverageResult의 missing/stale audit와 생성 gate를 설계 | 즉시 실제 정책 수용 |

구조 검증과 matcher의 구체적인 분할은 각각 승인 단계에서 확정한다. 이 표가 여러 단계를 이번에 한꺼번에 구현하라는 승인은 아니다. 특히 바로 matcher나 Coverage validator 전체로 이동하지 않는다.

## 38. 최종 판단

**READY_TO_IMPLEMENT_REVIEW_MATCH_RESULT_MODELS**

다음 가장 작은 작업 한 개: **matching 결과 값 모델 계층만 구현**한다. 3·19~20절의 세 Enum과 InventoryReviewMatch/ImplementationReviewMatch의 명시 필드·상태별 reasons 불변조건·exact 타입·불변성·새 직렬화를 합성 테스트로 확인한다. 실제 ref resolution·version/지문 대조·stale 계산·CurrentSnapshot·CoverageResult·validator는 만들지 않는다.

IMPLEMENTED: 기존 Coverage/Review/Context와 세 지문 utility는 현 상태 유지. 이번에는 matching 명세 한 개만 추가한다.

NOT IMPLEMENTED: 결과 모델/Enum, review lookup/matcher/stale evaluator, 구조 validator, CoverageResult, evaluate_eligibility_coverage, FULL/SLICE, Acceptance/Bridge, actual 안산 review records. M1.18 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지.

## 39. M2.21 — IMPLEMENTED: Review match 결과 값 모델

policy_data/coverage_review_match.py에 ReviewMatchStatus, ReviewMissingReason, ReviewStaleReason, InventoryReviewMatch, ImplementationReviewMatch 다섯 타입만 추가했다. policy_data 공개 export로 제공하며 실제 lookup/matcher·version/지문 비교·stale 계산·Coverage validator는 없다.

### 최종 필드와 Enum

ReviewMatchStatus는 MATCHED/MISSING/STALE 세 값뿐이다. Data Error/UNKNOWN/REVIEWED/PARTIAL을 추가하지 않는다. Missing은 NO_REVIEW_CONTEXT, INVENTORY_REVIEW_NOT_DECLARED 두 값이고, Stale은 INVENTORY_VERSION_CHANGED → RULE_VERSION_CHANGED → DATASET_VERSION_CHANGED → IMPLEMENTATION_CHANGED 네 값이다. Enum 선언 순서를 canonical order로 사용한다.

InventoryReviewMatch 필드는 review_ref:str|None, status, stale_reasons:tuple[ReviewStaleReason,...], missing_reasons:tuple[ReviewMissingReason,...] 네 개다. ImplementationReviewMatch는 condition_id/rule_root_id/review_ref:str와 같은 세 결과 필드, 총 여섯 개다. 모두 기본값 없이 필수이며3절 계약을 그대로 구현했다. 프롬프트 후보의 단일 missing_reason 대신 확정된 **missing_reasons tuple**을 사용한다.

review_ref는 존재하면 exact 비공백 str이며 원래 앞뒤 공백을 보존한다. None은 Inventory의 정상 미선언 MISSING에서만 허용한다. condition_id/root는 기존 Binding과 같은 ID/비공백 문자열 계약이며 실제 Binding 객체·root 존재를 조회하지 않는다. 기존 검증이 inline이라 작은 같은 구조 검사를 사용하고 기존 모델/helper를 변경하거나 import하지 않았다.

### 상태 공간과 사유 검증

| 상태 | 공통 불변조건 | Inventory 추가 제약 | Implementation 추가 제약 |
|---|---|---|---|
| MATCHED | ref 필수, stale/missing 모두 빈 tuple | 없음 | condition/root/ref 필수 |
| MISSING | stale 빈 tuple, missing 하나 이상 | ref 있음: NO_REVIEW_CONTEXT만. ref=None: NOT_DECLARED 단독 또는 NO_CONTEXT+NOT_DECLARED | NO_REVIEW_CONTEXT만 |
| STALE | ref 필수, stale 하나 이상, missing 빈 tuple | inventory/dataset version 사유만 | 네 stale 사유의 canonical subset 허용 |

status와 reason은 정확한 각각의 Enum만 허용한다. raw str/bool/다른 Enum을 변환하지 않는다. 두 사유 collection 모두 exact tuple이며 list/generator/tuple 하위 타입을 자동 변환하지 않는다. duplicate 또는 canonical 상대 순서를 어긴 tuple은 PolicyDataError다. 정렬/dedupe하지 않고 원래 tuple 객체를 보존한다.

작은 private validation helper는 타입·순서·상태/사유의 로컬 조합만 검사한다. 버전 label/지문/date/record를 입력받거나 비교하지 않는다. 기존 PolicyDataError를 사용하고 원본 payload를 오류 문장에 넣지 않는다. 필수 인자 누락·추가 인자는 Python TypeError다. 오류를 result.status에 저장하지 않는다.

### 불변성·표현·보증 한계

두 dataclass는 frozen/slots다. equality는 실제 모든 필드를 반영하며 잘못된 사유 순서는 생성 단계에서 거부한다. to_dict는 실제 네/여섯 key만 새 dict로 반환하고 Enum→value, tuple→새 list로 표현한다. 반복 결과와 원본 독립성을 보존한다.

Policy/Inventory/Coverage/Binding/Review/Context 전체 객체·실제/예상 fingerprint·reviewed_at·FULL/SLICE·사용자 PolicyEvaluation·Acceptance/Cashflow는 넣지 않는다. 생성 성공은 명시 결과 조합의 유효성일 뿐 실제 matching/사람 검토/현재 지문 일치의 인증이 아니다. 직접 의존은 dataclasses/Enum/re/PolicyDataError뿐이고 시간·파일/네트워크/Git·지문 계산이 없다.

IMPLEMENTED: 세 Enum 및 두 ReviewMatch 값 모델·조합 검증·불변성·결정적 직렬화·합성 단위 테스트166개.

NOT IMPLEMENTED: review resolution, 두 private matcher, version/지문 비교, stale calculation, root lookup, CoverageResult, Coverage validator/evaluate_eligibility_coverage, FULL/SLICE, Acceptance/Benefit Bridge. actual 안산 review ref/데이터는 생성하지 않았다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지다.

작업 전 actual releases를 제외한 backend/tests/data/docs 116개 파일 SHA256과 actual 여섯 파일의 경로/길이/수정시각을 기록했다. 기존 전체 **3984 passed in 11.24s**다. 신규 tests/test_coverage_review_match.py는 **166 passed in 0.57s**다. Inventory7개 정상 조합과 Implementation17개 정상 조합(15개 stale subset 포함), raw/wrong 타입·조합 오류·순서/중복·ref/ID·불변성/equality·새 serialization·금지 의존/I/O 부재를 검증했다. 기존 테스트/기대값은 수정하지 않았다.

최종 판단: **READY_TO_IMPLEMENT_REVIEW_RESOLUTION**. 다음 가장 작은 작업은 제공된 Context 안에서 **명시 review_ref의 존재와 정확한 review 종류만 확인하는 private resolver**를 별도 구현하는 것이다. Context=None의 MISSING 결과 계산·현재 target/version/지문 대조·stale·tree 검증·CoverageResult는 포함하지 않는다. 이 순서가 아직 없는 구조 validator나 matching 전체를 완료한 것으로 취급하지 않도록 한다.

### M2.21 최종 검증 기록

전체 pytest는 **4150 passed in 9.40s**다. 기존3984개와 신규166개 모두 통과했고 기존 테스트/기대값은 수정하지 않았다. 기존15개 golden vectors의 canonical JSON/byte 길이/literal digest도 명세와 그대로 일치한다. 변경 파일의 한국어 표기와 새 모델의 직접 의존/금지 기능 부재를 확인했다.

작업 전 기준선116개(actual releases 제외) 중112개가 동일하다. 변경은 policy_data 공개 export1개와 승인된 문서3개뿐이며 신규 결과 모듈·테스트2개만 추가했고 삭제는 없다. 기존 Review/Context/EligibilityCoverage·세 지문 utility·모델/serializer·평가/loader·Cashflow·기존 모든 테스트·데이터/SHA 선언·ResidenceHistory 자료는 유지했다. actual release 여섯 파일의 경로/길이/수정시각도 기준선과 같다.

## 40. M2.22 — IMPLEMENTED: 제공된 Context의 private review ref resolution

### API와 책임

policy_data/coverage_review_resolution.py에 다음 두 private 함수를 추가했다. package 공개 export는 변경하지 않았다.

```python
_resolve_inventory_review(
    context: CoverageReviewContext, review_ref: str,
) -> InventoryCompletenessReview

_resolve_implementation_review(
    context: CoverageReviewContext, review_ref: str,
) -> ImplementationBindingReview
```

작은 공통 private 입력 검사는 exact CoverageReviewContext와 exact 비공백 str만 허용한다. None/유사 객체/하위 타입은 자동 변환하지 않는다. review_ref의 strip은 공백 여부 검사에만 사용하며 원본 앞뒤 공백과 대소문자를 보존해 정확한 문자열로 비교한다. 기존 Review 모델의 검사가 inline이므로 기존 모델/helper를 리팩터링하지 않았다.

요청한 종류의 tuple을 선형 검색하여 원래 record를 직접 반환한다. 반환값은 Context에 있던 객체와 is가 같으며 새 객체/직렬화/검증을 만들지 않는다. 요청 종류에 없으면 반대 collection을 조회해 잘못된 종류와 없는 ref를 구별한다. exact Context 생성자의 record 종류·policy/scope 일치·두 collection 전체 ref 유일성 불변조건을 전제로 하며 이를 재검증하지 않는다. tuple 순서·날짜·버전 크기로 record를 선택하지 않는다.

### 오류 계약

| 경우 | 결과 |
|---|---|
| Context None 또는 exact Context가 아님 | PolicyDataError, INVALID_MATCH_INPUT prefix |
| ref가 exact 비공백 str가 아님 | PolicyDataError, INVALID_MATCH_INPUT prefix |
| 반대 종류 collection에만 ref 존재 | PolicyDataError, WRONG_REVIEW_TYPE prefix |
| 두 collection 모두 ref 없음 | PolicyDataError, REVIEW_REF_NOT_FOUND prefix |

기존 PolicyDataError는 별도 code 속성이 없는 ValueError 하위 타입이다. 새 오류 계층/code 속성을 만들지 않고 M2.20의 안정된 message prefix를 사용한다. 지시문의 REF_NOT_FOUND 의미는 명세의 **REVIEW_REF_NOT_FOUND**로 구현했다. 오류에 원본 ref/payload/시각을 넣지 않아 collection 순서와 현재시각에 무관한 메시지를 유지한다.

resolver는 None을 MISSING으로 변환하지 않는다. Context=None과 Inventory ref 미선언의 정상 MISSING 처리 및 NO_REVIEW_CONTEXT/INVENTORY_REVIEW_NOT_DECLARED 사유는 후속 matcher 책임이다. 제공된 Context의 깨진 명시 참조를 MISSING으로 숨기지 않는다.

### 의존과 구현 경계

직접 의존은 PolicyDataError, 두 Review 타입, CoverageReviewContext뿐이다. record의 review_ref와 Context의 두 collection만 읽는다. policy/scope·condition/root·inventory/rule/dataset version·모든 지문·reviewed_at을 읽거나 현재 대상과 비교하지 않는다. 최신 검토 자동 선택, stale 계산, MatchResult 생성, fingerprint import, Coverage/Binding/Policy import, cache, 외부 I/O·파일/네트워크/Git·시각·환경변수는 없다.

IMPLEMENTED: 두 private typed resolver와 공통 입력 검사, 합성 단위 테스트63개.
NOT IMPLEMENTED: Inventory/Implementation matcher, target identity 확인, version/지문 비교, stale 계산, root lookup, tree 구조 validator, CoverageResult/evaluate_eligibility_coverage, FULL/SLICE, Acceptance/Benefit Bridge. 이 구현은 검토 승인이나 정책 수용을 뜻하지 않는다.

### 검증과 다음 단계

작업 전 actual releases 제외 backend/tests/data/docs118개 파일의 SHA256 및 actual release6개 파일의 경로/길이/수정시각을 기록했다. 기존 전체 테스트 **4150 passed in 11.51s**, 신규 resolver 테스트 **63 passed in 0.32s**다. 합성 Review/Context만 사용했다.

테스트는 단일/혼합/historical old·new exact ref, 원본 identity, 빈/편측/혼합 collection의 없는 ref, 반대 종류, Context/ref exact 타입·하위 타입 거부, 공백·대소문자 보존, 순서 무관 결정성,100회 반복·무변경을 검증한다. 속성 접근 가드로 ref와 두 collection 외의 target/version/지문/date 읽기를 차단하고도 정상/오류 resolution이 동작함을 확인했다. signature·직접 의존·공개 export 부재와 재생성/재검증/직렬화/외부 I/O 부재도 확인했다.

최종 판단: **READY_TO_IMPLEMENT_INVENTORY_REVIEW_MATCHING**.
다음 가장 작은 작업 한 개는 M2.20에 따른 **Inventory private matcher만** 구현하는 것이다. Context=None/미선언 MISSING, resolver 호출, Inventory 대상 확인, 독립 version/guarded fingerprint 대조와 사유 결정을 맡긴다. Implementation matcher와 별도 tree 구조 검증·Coverage validator 전체를 함께 구현하거나 완료한 것으로 취급하지 않는다.

실제 안산 review record·실제 지문은 생성하지 않는다. actual releases와 기존 Context/Review/MatchResult 모델·지문 utility·기존 테스트/기대값은 유지한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

### M2.22 최종 검증 기록

전체 pytest는 **4213 passed in 12.38s**다. 기존4150개와 신규63개 모두 통과했으며 기존 테스트/기대값 수정은 없다. M2.21 결과 모델 테스트166개 및 기존 GV01~GV15의 literal digest 검증도 그대로 통과했다.

작업 전 기준선118개(actual releases 제외) 중116개가 SHA256까지 동일하다. 변경은 이 문서와 ARCHITECTURE.md 두 개뿐이고 새 resolver/테스트 두 파일을 추가했다. 삭제는 없다. package 공개 export, 기존 Review/Context/결과 모델·지문 utility·평가/loader·Cashflow·기존 모든 테스트·데이터와 SHA 선언은 변경하지 않았다. actual release6개 파일의 경로/길이/수정시각이 기준선과 같고 실제 review record·실제 지문을 생성하지 않았다. 변경 파일의 한국어 표기도 확인했다.

## 41. M2.23 — IMPLEMENTED: Inventory completeness review matcher

### API와 입력 계약

policy_data/coverage_review_matching.py에 private 함수 하나를 추가했다. 결과 모델·resolver를 옮기거나 package 공개 export를 변경하지 않았다.

```python
_match_inventory_review(
    inventory: ConditionInventory,
    review_context: CoverageReviewContext | None,
    *,
    current_inventory_fingerprint: str,
) -> InventoryReviewMatch
```

입력은 exact ConditionInventory, exact CoverageReviewContext 또는 None, exact 소문자16진64자리 str이다. 누락/추가/잘못된 위치 인자는 Python TypeError, 전달된 잘못된 값은 INVALID_MATCH_INPUT PolicyDataError다. 자동 변환·정규화·지문 계산은 없다. Review 계층의 hash 검사가 inline이고 기존 Manifest의 _hash는 Manifest 전용 오류/의존을 가지므로 같은 최소 형식 검사를 이 함수에 두었다. 기존 모델/helper는 변경하지 않았다.

입력 타입과 current 지문 형식은 모든 정상 분기보다 먼저 검증한다. ref 미선언/Context 없음도 malformed 현재 지문이나 Context 타입을 숨기지 않는다. 현재 지문의 내용 진실성은 형식 검사로 증명되지 않으며, 상위의 신뢰된 호출자가 **실제 현재 Inventory에서 계산한 지문**을 공급해야 한다. private 함수이며 사용자/LLM이 raw hash를 제출하는 public 경로는 만들지 않는다.

### MISSING 분기와 승인된 우선순위

M2.23 지시문7절이 M2.20의 두 missing 사유 동시 반환보다 우선한다. 이 승인을 6·20·34절과 RM01에도 반영했다. M2.21 결과 모델/기존 테스트의 허용 조합은 그대로다.

| 입력 | 정확한 결과 |
|---|---|
| ref=None, Context None 또는 존재 | ref=None, MISSING, stale=(), missing=(INVENTORY_REVIEW_NOT_DECLARED,) |
| ref 존재, Context=None | 원래 ref, MISSING, stale=(), missing=(NO_REVIEW_CONTEXT,) |
| ref 존재, Context 존재 | 기존 _resolve_inventory_review로 조회 후 대상/확인본 대조 |

미선언/Context 없음에서는 resolver를 호출하지 않는다. 미선언 분기는 유효한 Context의 현재 policy/scope와도 비교하지 않는다. 전체 Coverage 구조 검증을 생략하는 근거는 아니며 그 상위 경로는 아직 없다.

### Resolution과 대상 확인

명시 ref가 있으면 M2.22 resolver를 정확히 한 번 사용한다. matcher에서 collection을 순회하거나 최신 review를 선택하지 않는다. REVIEW_REF_NOT_FOUND/WRONG_REVIEW_TYPE 예외는 같은 객체 그대로 전파한다.

선택 record의 policy_id → scope 순서로 현재 Inventory와 정확히 비교한다. 다르면 REVIEW_POLICY_MISMATCH 또는 REVIEW_SCOPE_MISMATCH다. Context 생성자는 모든 record와 Context의 policy/scope 일치를 보장하므로 이 대조로 잘못 연결한 Context도 검출한다. Context target 대조를 중복 수행하지 않으며, 명시 ref 오류는 resolver에서 먼저 발생한다. Scope는 값 동등성을 사용하고 Q2/Q3·annual/quarter·edition 차이를 거부한다. 서로 같은 값을 가진 별개 Scope 객체는 허용한다.

### 독립 version/guarded fingerprint 비교

| 비교 쌍 | version 같음 | version 다름 |
|---|---|---|
| review.inventory_version ↔ inventory.inventory_version / review.inventory_fingerprint ↔ supplied current 지문 | 지문 차이는 INVENTORY_FINGERPRINT_CONFLICT | INVENTORY_VERSION_CHANGED, 이 쌍의 지문 차이로 오류를 만들지 않음 |
| review.dataset_version ↔ Context.dataset_version / review.source_registry_fingerprint ↔ Context.source_registry_fingerprint | 지문 차이는 SOURCE_REGISTRY_FINGERPRINT_CONFLICT | DATASET_VERSION_CHANGED, 이 쌍의 지문 차이로 오류를 만들지 않음 |

version은 정확한 동일성만 보며 숫자 크기/날짜/과거 여부를 추론하지 않는다. version이 다르고 지문이 같아도 stale다. Registry 차이의 별도 stale reason은 추가하지 않는다.

먼저 Inventory 쌍, 다음 Dataset 쌍을 검사한다. stale 후보가 있어도 독립된 다른 쌍의 동일 version 내용 모순을 계속 검사한다. Inventory stale + 동일 Dataset/source 모순은 오류, Dataset stale + 동일 Inventory/지문 모순도 오류다. 둘 다 모순이면 Inventory 오류가 먼저다. fail-fast 오류를 정상 결과로 감싸지 않는다.

모순이 없으면 canonical stale tuple은 (INVENTORY_VERSION_CHANGED, DATASET_VERSION_CHANGED)의 해당 subset이다. tuple이 비면 MATCHED, 하나 이상이면 STALE이며 두 경우 missing=()와 원래 ref를 보존한다. 결과는 기존 InventoryReviewMatch를 사용한다.

### 의존·보증 경계

직접 의존은 re, PolicyDataError, ConditionInventory, CoverageReviewContext, InventoryReviewMatch 및 세 Enum, _resolve_inventory_review다. 날짜/외부 artifact 조회·구현 지문·Policy/RuleNode/ConditionBinding·rule/tree/subtree 지문은 사용하지 않는다. supplied 지문을 재계산하거나 Context의 baseline을 record의 과거 값으로 대체하지 않는다. 파일/네트워크/Git·현재시각·환경변수·전역 cache·입력 변경도 없다.

MATCHED는 선언된 현재 확인본과 검토 metadata의 일치성이다. 검토가 실제로 수행됐다는 진실성·공식 조건 목록 완결성·artifact 존재·공식성·FULL/Acceptance를 새로 인증하지 않는다. 상위 지문 준비/전달과 별도 tree 구조 validator는 아직 없으며 이 함수는 이들을 완료한 것으로 주장하지 않는다. 현재 세 인자 및 keyword-only 지문 공급 계약으로 독립 구현 가능하며 새 CurrentSnapshot 모델은 필요하지 않다.

IMPLEMENTED: Inventory private matcher의 MISSING/MATCHED/STALE·대상 및 guarded conflict 판정.
NOT IMPLEMENTED: Implementation matcher/placeholder, ConditionBinding matching, subtree lookup, Policy Tree/rule version/implementation 지문 matching, CoverageResult, 최종 Coverage validator, FULL_POLICY/CONDITION_SLICE 파생, Acceptance/Benefit Bridge.

### 합성 테스트와 검증

작업 전 actual releases 제외 backend/tests/data/docs120개 파일 SHA256과 actual release6개 파일 경로/길이/수정시각을 기록했다. 기존 전체 **4213 passed in 11.58s**다. 신규 tests/test_inventory_review_matching.py는 첫 수집 단계에서 합성 fake 객체가 pytest의 속성 조사까지 거부하는 문제를 테스트 fixture에서 수정한 뒤 **142 passed in 0.45s**다. matcher 코드 변경 없이 해결했으며 기존 테스트는 수정하지 않았다.

142개는 annual/quarter/한국어 exact match, 우선순위가 고정된 MISSING, ref 원문 보존·resolver1회 호출·예외 identity 전파, 없는 ref/잘못된 종류, policy·edition·quarter·annual 대상 오류, version/지문 동일 여부16조합, 실제 합성 의미/근거/분류 변경의 지문 모순과 version 갱신, 숫자 최신 선택 없음, canonical 다중 stale와 독립 오류 우선, 날짜/artifact/구현 지문 무관성, historical ref·tuple 순서, exact 입력/하위 타입/잘못된 지문 형식,100회 결정성·무변경을 검증한다. 속성 접근 가드로 책임 밖 필드 읽기를 막았고 지문 계산·모델 재검증/직렬화·외부 I/O를 차단한 상태에서도 정상 matching을 확인했다.

함수 단위의 의존/책임 테스트는 Inventory matcher 자체만 제한한다. 후속 별도 matcher가 같은 모듈에 추가된다는 이유로 기존 테스트가 충돌하도록 모듈 전체의 미래 확장을 금지하지 않는다.

최종 판단: **READY_TO_IMPLEMENT_IMPLEMENTATION_REVIEW_MATCHING**.
다음 가장 작은 작업 하나는 기존 resolver/결과 모델을 재사용하는 **Implementation private matcher**다. 상위에서 공급한 현재 Inventory/Tree/subtree 지문과 명시 Binding/Policy를 대조하는 M2.20 계약에 한정하며 lookup·최종 Coverage validator·CoverageResult를 함께 구현하지 않는다.

실제 ConditionInventory/review/지문을 생성하거나 releases를 변경하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

### M2.23 최종 검증 기록

전체 pytest는 **4355 passed in 11.09s**다. 기존4213개와 신규142개가 모두 통과했다. M2.22 resolver63개, M2.21 결과 모델166개 및 GV01~GV15 literal digest 검증을 포함하며 기존 테스트/기대값 수정은 없다.

작업 전 기준선120개(actual releases 제외) 중118개가 SHA256까지 동일하다. 변경은 이 문서와 ARCHITECTURE.md 두 개이며, 새 matcher 모듈/테스트 두 파일을 추가했다. 삭제는 없다. 기존 공개 export·Context/Review/Inventory/결과 모델·resolver·지문 utility·기존 모든 테스트·데이터/SHA 선언·ResidenceHistory 자료는 변경하지 않았다. actual release6개 파일의 경로/길이/수정시각도 작업 전과 같다. 실제 review/Inventory/지문을 생성하지 않았으며 변경 파일의 한국어 표기를 확인했다.

## 42. M2.24 — IMPLEMENTED: ImplementationBindingReview matcher

### API와 현재값 공급 계약

기존 policy_data/coverage_review_matching.py에 private 함수 하나를 추가했다. Inventory matcher 함수 본문은 그대로 유지했고 기존 Result/Resolver/모델·지문 utility·package 공개 export는 변경하지 않았다.

```python
_match_implementation_review(
    inventory: ConditionInventory,
    binding: ConditionBinding,
    review_context: CoverageReviewContext | None,
    *,
    current_inventory_fingerprint: str,
    current_rule_version: str,
    current_policy_tree_fingerprint: str,
    current_subtree_fingerprint: str,
) -> ImplementationReviewMatch
```

M2.24 승인으로 26절의 Policy 객체 인자를 제거하고 current_rule_version을 keyword-only로 공급하는 형태를 확정했다. 현재 version의 원천은 계속 **현재 Policy.rule_version**이며 record의 과거 rule_version에서 역으로 채우지 않는다. Policy 객체를 받거나 root를 조회하지 않는다.

정확한 ConditionInventory/ConditionBinding, 정확한 CoverageReviewContext 또는 None만 받는다. 세 지문은 각각 exact lowercase hex64 str, rule version은 exact 비공백 str이다. 자동 strip/소문자화/Enum 변환/Envelope r#### 제한은 없다. 앞뒤 공백도 version identity에 포함한다. 현재 Policy의 require_text는 models.py에 있으며, 그 모듈에 결합해 가져오거나 오류를 감싸는 대신 동일한 작은 검사를 적용해 INVALID_MATCH_INPUT prefix를 유지했다. 지문 validation은 기존 Review 계층의 inline 형식과 같다. Inventory matcher를 공통 helper로 리팩터링하지 않았다.

입력 검사는 Inventory → Binding → Context → current_rule_version → current Inventory 지문 → Tree 지문 → subtree 지문 순서다. Context=None이어도 모든 현재값의 형식을 먼저 검사한다. 잘못된 값은 INVALID_MATCH_INPUT PolicyDataError, 누락/추가/잘못된 위치 인자는 Python TypeError다.

### MISSING과 명시 ref resolution

ConditionBinding.implementation_review_ref는 필수다. 미선언 상태/INVENTORY_REVIEW_NOT_DECLARED 사유를 새로 만들지 않는다.

Context=None이면 Binding의 원래 condition_id/rule_root_id/implementation_review_ref를 보존하고 MISSING, stale=(), missing=(NO_REVIEW_CONTEXT,)를 반환한다. resolver를 호출하지 않는다.

Context가 있으면 기존 _resolve_implementation_review를 정확히 한 번 호출한다. 직접 collection search·latest 선택·대체 ref를 구현하지 않는다. REVIEW_REF_NOT_FOUND/WRONG_REVIEW_TYPE은 원래 PolicyDataError 객체 그대로 전파한다. 존재하는 Context의 깨진 ref를 MISSING/STALE로 낮추지 않는다.

### 대상 결합과 오류 순서

resolve 성공 후 review의 policy_id → scope → condition_id → rule_root_id 순서로 현재 Inventory/Binding과 정확히 비교한다. 순서대로 REVIEW_POLICY_MISMATCH / REVIEW_SCOPE_MISMATCH / REVIEW_CONDITION_MISMATCH / REVIEW_RULE_ROOT_MISMATCH다. 모두 stale보다 우선하는 Data Error다.

Context가 모든 record와 자신의 policy/scope 일치를 보장하므로 선택 record와 Inventory 대조로 Context의 잘못된 연결도 검출한다. 중복 Context target 검사나 record 재검증을 하지 않는다. quarter/annual/edition의 차이, root/ref의 원래 공백과 대소문자를 보정하지 않는다.

### 독립 version/내용 비교

| 기준 | 기준이 같을 때 | 기준이 다를 때 |
|---|---|---|
| inventory_version | 공급된 현재 Inventory 지문과 다르면 INVENTORY_FINGERPRINT_CONFLICT | INVENTORY_VERSION_CHANGED, 해당 지문 차이는 오류가 아님 |
| rule_version | 먼저 전체 Tree 지문, 다음 subtree 지문을 대조. 각각 POLICY_TREE_FINGERPRINT_CONFLICT / SUBTREE_FINGERPRINT_CONFLICT | RULE_VERSION_CHANGED, Tree/subtree 차이는 여기에 흡수 |
| dataset_version | Registry 지문이 다르면 SOURCE_REGISTRY_FINGERPRINT_CONFLICT | DATASET_VERSION_CHANGED, Registry 차이는 여기에 흡수 |
| implementation artifact에는 별도 version 없음 | Context와 review 지문이 같으면 사유 없음 | 지문 불일치만으로 IMPLEMENTATION_CHANGED STALE |

각 version의 숫자 크기/날짜를 추론하지 않는다. version이 다르고 지문은 같아도 stale다. implementation 변경은 같은 rule/dataset label이어도 오류가 아닌 stale이며 별도 implementation_version을 추가하지 않는다. Registry와 실행 artifact 지문을 서로 대체하지 않는다.

대상 검사를 모두 마친 다음 Inventory → Tree → subtree → Registry 순서의 guarded conflict를 검사한다. stale 후보가 생겨도 다른 독립 쌍의 모순을 검사하며 첫 stale에서 반환하지 않는다. fail-fast 오류가 정상 결과보다 우선한다. Tree와 subtree가 동시에 충돌하면 Tree 오류가 먼저다.

오류가 없을 때 canonical stale tuple은 INVENTORY_VERSION_CHANGED → RULE_VERSION_CHANGED → DATASET_VERSION_CHANGED → IMPLEMENTATION_CHANGED의 해당 subset이다. 네 사유가 모두 생겨도 보존한다. tuple이 비면 MATCHED, 하나 이상이면 STALE이며 missing=()다. 결과는 기존 ImplementationReviewMatch만 사용하고 condition/root/ref는 현재 Binding에서 가져온다.

### 책임과 보증 한계

추가 직접 의존은 ConditionBinding, ImplementationReviewMatch, _resolve_implementation_review다. 세 현재 지문과 현재 rule version은 이미 준비된 호출 지역값이라는 내부 계약이다. **Assumption:** 신뢰된 상위 준비 계층이 정확한 현재 Policy.rule_version과 Inventory/Tree/선택 root의 지문을 공급한다. 그 준비 계층은 아직 미구현이다. 형식 검사만으로 공급값이 실제 현재 tree에서 계산됐는지 인증하지 않는다.

matcher는 Policy/RuleNode 입력·walk_nodes·root lookup·tree traversal·조건 소속/ownership·overlap/unbound 검증을 수행하지 않는다. 따라서 MATCHED가 root 실존이나 전체 구조 유효성을 뜻하지 않는다. Binding의 조건이 Inventory에 있는지와 선택 root의 실제 소속/존재는 상위 구조 검증의 별도 책임이다. 거짓 선언값을 public 입력으로 신뢰하는 경로/새 snapshot 모델은 만들지 않는다.

reviewed_at과 review_artifact_ref를 읽지 않는다. 날짜 기반 만료/최신 선택·artifact 파일/URL 열기·현재시각·환경·Git·네트워크·파일 I/O·cache·입력 변경은 없다. matcher 내부 지문 계산, Inventory matcher 실행, 기존 모델 재생성/재검증도 없다. 결과 일치는 실제 사람이 완료한 검토의 진실성·공식 목록 완결성·행정 수용을 새로 인증하지 않는다.

IMPLEMENTED: Inventory matcher 및 단일 Binding의 Implementation matcher.
NOT IMPLEMENTED: subtree/root lookup, Coverage structural validator, ownership/overlap/unbound 검사, CoverageResult, FULL_POLICY/CONDITION_SLICE 파생, 최종 Coverage validator, Acceptance/Benefit Bridge.

### 합성 테스트와 검증

작업 전 actual releases 제외 backend/tests/data/docs122개 파일 SHA256과 actual release6개 파일의 경로/길이/수정시각을 기록했다. 기존 전체 **4355 passed in 12.07s**다. 신규 tests/test_implementation_review_matching.py는 **257 passed in 0.71s**다. 합성 Policy/leaf/group을 테스트 준비 과정에서만 구성하고 기존 지문 함수로 현재값을 계산해 명시적으로 전달했다.

신규 검증 범위는 leaf/group·annual/quarter exact match, Context=None의 세 identity 보존, resolver1회 사용·없는/다른 종류 ref·원래 예외 전파, 모든 target 오류·오류 순서,16개 stale subset을 지문 같음/다름 두 경우로 검증한32조합, 각 동일 version conflict·독립 stale+오류, Tree/subtree 동시 conflict 우선순위, rule version 원문/숫자 최신 판단 없음, 검토 날짜/artifact 무관성·historical ref 순서·100회 결정성/무변경, exact 입력·하위 타입·현재값 형식이다.

속성 접근 가드로 현재 조건/Policy/root 구조·날짜/artifact 읽기가 없음을 확인했고 지문 계산기·walk_nodes·Inventory matcher·모델 재검증/직렬화·외부 I/O를 차단해도 matching이 동작했다. private signature와 함수 단위 금지 의존도 확인했다. 테스트는 같은 모듈의 미래 별도 기능 확장을 금지하지 않는다.

### 최종 판단과 다음 최소 단계

**READY_FOR_COVERAGE_STRUCTURE_VALIDATION_DESIGN**

두 matcher의 독립 비교는 안정화됐지만 아직 실제 root 존재/소유/겹침/미매핑 rule/전체 결합을 확인하는 실행 경로가 없다. 기존 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md8~11·29절은 의미 원칙과 walk_nodes 재사용을 정한다. 다음 가장 작은 작업은 이를 재설계하는 것이 아니라 **첫 root lookup 단계의 입력·반환·오류 순서와 테스트 계약을 구체화하는 구조 검증 설계 하나**다. 사전 원칙을 유지하며 단계별 경계를 확정한 후 구현한다. 이번에 lookup helper나 전체 validator/Result placeholder를 추가하지 않는다.

현재 scalar snapshot 공급 계약 자체가 불안정해서 진행을 막는 문제는 발견되지 않았다. 공급값과 실제 tree 연결 보증은 상위 구조 검증/준비 계층이 맡는 명시적 한계로 유지한다. 실제 안산 Binding/Inventory/review/지문은 생성하지 않으며 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

### M2.24 최종 검증 기록

전체 pytest는 **4612 passed in 11.07s**다. 기존4355개와 신규257개가 모두 통과했다. 기존 Inventory matcher142개, resolver63개, 결과 모델166개와 GV01~GV15 literal digest 검증을 포함하며 기존 테스트/기대값 수정은 없다.

작업 전 기준선122개(actual releases 제외) 중119개가 SHA256까지 동일하다. 변경은 기존 matching 모듈의 import/docstring/Implementation 함수 추가와 이 문서/ARCHITECTURE.md 두 개다. 신규 Implementation 테스트 파일 하나를 추가했고 삭제는 없다. Inventory matcher 함수의 원래 소스 본문이 그대로임을 직접 대조했다. 기존 공개 export·모델·resolver·지문 utility·평가/loader·Cashflow·모든 기존 테스트·데이터/SHA 선언·ResidenceHistory 자료는 유지했다. actual release6개 파일의 경로/길이/수정시각도 작업 전과 같다. 실제 검토/Binding/Inventory/지문은 생성하지 않았고 변경 파일의 한국어 표기를 확인했다.





