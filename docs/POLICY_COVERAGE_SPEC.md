# 정책 자격조건 구현범위 계약 — M2.5

> 현재 구현 상태는 35절 M2.11을 따른다. 1~30절은 승인된 M2.5 설계 기록, 31~34절은 이전 구현 기록이다. EligibilityCoverage 구조 모델까지 구현되었으며 tree/review 대조·FULL 판정은 없다.

작성일: **2026-10-21 / Asia/Seoul**. **문서 전용**. Coverage/Acceptance/Bridge 코드·실제 정책 자료를 변경하지 않았다.

최종 판단: **READY_TO_IMPLEMENT_POLICY_COVERAGE_MODELS**. 이는 독립 값 모델을 합성 자료로 구현할 설계 준비에 한정된다. 실제 안산 조건 inventory의 최종 확정·FULL 승격·운영 연결 승인이 아니다.

## 1. 목적

공식 정책의 필요한 자격조건 목록과 실제 프로그램의 판정 트리를 연결하여, 선택한 범위의 누락·추가·분기 손실·metadata drift를 검출한다. FULL_POLICY 문자열이나 현재 사용자 PASS만으로 전체 구현을 주장하지 않는다.

검토 기준: POLICY_BENEFIT_ACCEPTANCE_SPEC.md, CASHFLOW_BENEFIT_BRIDGE_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, REAL_POLICY_001_IMPLEMENTATION.md, REAL_POLICY_001_Q3_BIRTH_IMPLEMENTATION.md, REAL_POLICY_001_RESIDENCE_HISTORY_SPEC.md, POLICY_RULE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 실제 policy_data/envelope.py의 coverage/leaf 대조, validation.py의 source/Manifest 대조, loader.py의 엄격한 키·타입 경계와 releases 001/002를 확인했다. 기존 공식 근거 확인본을 해석한 설계이며 정책 원문을 새로 조회하거나 행정 의미를 확정한 작업은 아니다.

## 2. Coverage 정의

**이 PolicyEnvelope가 실제 정책의 어떤 판정 범위를 프로그램으로 구현하는가**다. 같은 정책이라도 edition·회차 scope·규칙 버전이 다르면 다른 coverage다. 어떤 입력을 받으면 PASS가 되는지를 나타내는 사용자 평가 결과가 아니다.

source verification, benefit 정의 검토, simulation acceptance, production deployment approval와 독립된 축이다. 소스가 VERIFIED여도 일부 구현이면 SLICE다. 모든 구조가 있어도 검토 미완료이면 DRAFT일 수 있다.

## 3. FULL_POLICY 정의

**해당 policy_id / edition_id / applicability_scope에서 사용자 자격을 결정하는 데 필요한 모든 REQUIRED 및 CONDITIONAL eligibility condition과 그 전체 분기가, 공식 의미에 대응하는 현재 입력 모델·Rule/evaluator·트리로 표현되고 평가 가능함.**

이 문서에서 FULL_POLICY는 **eligibility completeness**만 뜻한다. 실제 지급 승인·신청 절차·제출서류·혜택 금액/수단/지급월·현재 신청창 열림을 포함하지 않는다. 조건의 행정 의미나 필요한 입력 표현이 미확정인 상태는 구현 완료로 계산하지 않는다. 구현이 있어도 사용자가 사실을 입력하지 않으면 평가 UNKNOWN일 수 있다. FULL은 모든 사용자에게 PASS가 나온다는 뜻이 아니다.

M2.4의 “필요한 효력/신청/지급 관련 범위 검토”는 수용 시 필요한 독립 검토로 유지한다. 이를 모두 FULL_POLICY에 합치지 않는다. FULL만으로 M2.4 acceptance를 발급할 수 없다.

## 4. Eligibility / benefit / operational coverage 분리

| 축 | 내용 | FULL_POLICY와 관계 |
|---|---|---|
| Eligibility | 연령/출생일·지역·기간·국적/등록분류·개인별 조건·예외 등 자격조건 | 이 문서가 정의하는 FULL의 대상 |
| Benefit metadata | 금액·주기·수단/제한·적용 지급월·근거 | 별도 검토. M2.4 수용에도 필요 |
| Application/operational | 접수창·서류·대리/자동/소급 신청·신청 방법 | 별도 범위. “지금 신청” 표시의 선행조건 |

신청일을 기준으로 거주 여부를 확인하는 eligibility rule과 신청창이 열렸는지를 확인하는 operational rule은 다르다. 실제 혜택 적용에 제출/신청 사실 등이 필요한 경우 외부 개인 적용 확인에서 미확인을 제외한다. operational 미구현을 FULL이라는 이름으로 충족 처리하지 않는다. 이번에 세 축용 범용 모델을 모두 만들지 않는다.

## 5. Required condition inventory

구현 트리에서 조건 목록을 역으로 만들어 전체라고 부르지 않는다. 공식 자료를 먼저 검토해 **ConditionInventory**를 만든다. 최소 후보 구조는 다음과 같다.

| 구성 | 후보 필드·의미 |
|---|---|
| Inventory identity | policy_id, edition_id, scope, inventory_version(예: i0001) |
| conditions | RequiredCondition의 불변 tuple, 비어 있지 않음 |
| completeness_review_ref | str 또는 None. 해당 scope의 공식 필수조건 목록·조합을 빠짐없이 검토한 불변 기록 참조 |
| RequiredCondition | condition_id, meaning, requirement(REQUIRED/CONDITIONAL), evidence_refs |

INFORMATIONAL·operational·benefit 설명은 자격 inventory에 넣지 않고 별도 검토 문서에 둔다. 각 condition에 동일 scope를 반복하지 않고 inventory가 scope를 소유한다. condition meaning은 전체 조합·조건부 적용 대상과 예외를 식별할 수 있어야 한다. COMPLETENESS 검토가 없는 임시 inventory도 DRAFT 분석용으로 보관할 수 있으나 FULL 근거가 되지 않는다.

completeness_review_ref는 공식 source 버전, 검토한 조건 목록·논리, scope, 준비자/검토자와 수동 사례를 묶는다. 그것이 비어 있지 않은 문자열이라는 사실만으로 검토가 완료됐다고 인증하지 않는다. 신뢰된 외부 검토가 실제 기록·고정 snapshot을 명시적으로 공급해야 한다.

## 6. Condition identity

정책 안의 안정적인 **condition_id**를 사용한다. 기존 rule_id의 대문자·숫자·밑줄 스타일을 따르는 후보: ANSAN_YBI_CURRENT_RESIDENCE, ANSAN_YBI_BIRTH_DATE, ANSAN_YBI_GG_RESIDENCE_DURATION, ANSAN_YBI_REGISTRATION_ELIGIBILITY. 표시 문장·금액·해당 사용자 값은 ID가 아니다.

condition identity는 (policy_id, condition_id)이고, 의미 확인본은 edition/scope/inventory_version으로 구별한다. birth라는 의미는 안정 ID로 유지하면서 Q3 구간은 scope와 규칙 버전으로 고정할 수 있다. 현행 ANSAN_YBI_2026_Q3_BIRTH_RANGE rule_id를 바꾸거나 condition_id와 같게 만들 필요는 없다. 조건을 분리/통합하면 기존 ID에 다른 의미를 덮어쓰지 않고 새 inventory 확인본으로 검토한다.

## 7. Required / conditional / informational

REQUIRED와 CONDITIONAL은 모두 **구현 의무가 있는 집합 R**에 포함한다. CONDITIONAL은 사용자군에 따라 적용되는 정책 조건이며 “선택 구현”이 아니다. INFORMATIONAL은 eligibility inventory 밖에서 설명한다. required_for_eligibility bool을 requirement와 중복 저장하지 않는다.

조건부 항목을 “일반 사용자에게 필요 없음”이라며 R에서 제거하지 않는다. 관련 사용자군을 인위적으로 scope에서 제외해 전체라고 부르지 않는다. 예외 처리가 단일 기간 조건 내부의 인정기산 규칙이라면 독립 필수조건으로 이중 계수하지 않고 그 조건의 의미·구현 검토에 포함한다.

예: 귀화 이후 기간 인정은 거주기간 조건의 조건부 내부 분기이며, 등록분류에 따른 대상 여부는 별도 자격조건이다. 후속 공식 검토에서 독립 조건이 필요하다고 확인되면 inventory를 개정할 수 있지만 이 문서가 귀화 기간을 새로운 임의 계산식으로 확정하지 않는다.

## 8. Implemented conditions

**ConditionBinding** 한 개가 조건 의미 한 개를 실제 트리의 한 완전한 하위 트리에 연결한다. I는 bindings의 condition_id에서 **파생**하며 따로 implemented_condition_ids를 중복 저장하지 않는다. 빠진 조건은 R−I다.

binding이 존재하는 것만으로 구현 증명이 끝나지는 않는다. 하위 트리가 기대된 전체 분기·연산자·기준값·입력/evaluator 계약과 일치하는지 버전 고정된 구현 검토가 필요하다. 의미 불확정·미지원 evaluator·항상 PASS placeholder·미상 분기를 생략한 함수는 구현 완료가 아니다.

조건의 일부 분기만 실험 구현한 것은 완전한 binding으로 등록하지 않는다. 초기 coverage 모델은 조건 단위 완결성만 지원한다. 그런 실험 트리는 별도 합성 검토에서 유지하며, 실제 eligibility Envelope에 넣으려면 먼저 더 세분한 inventory/부분 구현 계약을 별도 승인해야 한다. 현재 resident/birth leaf는 각각 독립된 완전 조건이므로 이 제약과 충돌하지 않는다.

## 9. CONDITION_SLICE

고정 scope의 R 중 일부만 완전히 구현했거나, inventory 자체의 공식 완결성 검토가 아직 없는 상태다. 어떤 조건이 구현됐는지 I, 누락은 R−I, 범위는 scope로 표시한다. 추가로 completeness_review_ref 미확인이면 “목록 자체도 검토 중”이라고 설명한다.

구조적으로 모순된 coverage는 SLICE로 낮춰 허용하지 않고 Data Error다. I가 R과 같아도 공식 조건 목록/구현 대응 검토가 없다면 FULL이 아니다. R은 비어 있지 않아야 하며 빈 목록의 공집합 equality로 FULL을 만들지 않는다.

## 10. FULL invariants

고정 policy/edition/scope에서 다음이 모두 필요하다.

1. 유효하고 비어 있지 않은 inventory, condition ID 유일, 공식 근거 참조 존재.
2. **검토된 R = 완전하게 구현된 I**. 모든 CONDITIONAL 분기도 포함.
3. 각 조건에 정확히 하나의 binding, 대상은 실제 tree의 완전한 subtree.
4. tree에 mapping되지 않은 eligibility leaf·부가 check가 없고 조건 subtree 간 겹침이 없음.
5. 정책 전체의 결합 논리와 조건 내부의 논리·기준값·예외가 검토한 구현 계약과 일치.
6. scope·inventory·rule/dataset/source 확인본·입력 모델/evaluator 구현의 검토 결합이 정확함.
7. 공식 조건 의미가 모두 해석 가능하고 runtime evaluator가 전 사용자 분기를 지원함.
8. inventory 완결성 및 조건별 구현 검토가 실제로 확인됨.

집합 equality는 필요조건이며 충분조건이 아니다. Python 구조 검증이 공식 원문에 조건이 더 없는지나 모든 프로그램 의미를 자동 증명할 수는 없다. **프로그램이 보장하는 것은 검토·고정한 inventory/구현 계약과 현재 tree의 완전한 대응**이다. 공식 완결성과 코드의 의미 일치는 근거·교차검토·단위/진리표 테스트가 보완한다. LLM이나 문자열 라벨이 이 검토를 대신하지 않는다.

## 11. Rule tree binding

최소 binding: `condition_id`, `rule_root_id`, `implementation_review_ref`. rule_ids 전체를 수동 나열하지 않고 walk_nodes로 root 아래 subtree node/leaf 집합을 파생한다. leaf 하나면 subtree도 하나다. group 조건이면 root부터 모든 자식/손자까지 포함한다.

각 condition subtree는 서로 겹치지 않는다. 정책의 최상위 조합은 초기 최소 계약에서 **조건 root들의 ALL**로 제한한다. 조건이 하나인 실제 slice는 그 condition root 자체를 Policy.root로 허용한다. OR/NOT/중첩 논리는 하나의 의미상 조건 내부 subtree에 둔다. 서로 대안인 두 경로를 모두 필수 조건으로 쪼개 root ANY를 무심코 ALL로 바꾸지 않는다.

따라서 조건별 subtree 바깥에는 전체 조합 ALL root 외 임의 group/leaf가 없어야 한다. 기존 source validation의 leaf-ID 집합 대조와 새 조건 mapping은 서로 다른 검사다. 추가 설명/실험/보수적 check는 평가 tree 밖에 두며, 평가 결과를 바꾸는 근거 없는 extra rule은 SLICE에서도 Data Error다.

**결합 논리 drift 방지:** implementation_review_ref의 고정 검토 자료는 condition별 전체 subtree snapshot(노드 종류·연산자·자식 순서·모든 기준값·evidence)과 policy 전체 조합, rule_version 및 지원 evaluator/입력 계약을 묶는다. 후속 pure validator는 외부에서 명시적으로 전달받은 검토 snapshot과 현재 tree를 대조한다. ref만 보고 신뢰하거나 네트워크로 조회하지 않는다. ANY를 ALL로 바꾸거나 child를 지우고 ID만 유지해도 불일치다. 단위 테스트로 분기와 경계의 의미도 검증해야 한다.

## 12. Group conditions

경기도 최근 연속3년 OR 합산10년은 **하나의 REQUIRED condition: ANSAN_YBI_GG_RESIDENCE_DURATION**이다. 구현 후보는 ANY(continuous,cumulative)의 subtree다. binding은 ANY root를 가리켜 두 자식 전체를 포함한다. 둘 중 하나만 구현했거나 ALL로 바꾸면 완료 binding으로 인정하지 않는다.

CONDITIONAL은 적용 guard·비적용 경로·해당 조건 평가 전체가 필요하다. 예컨대 정책 의미가 논리적 함의일 때 기존 NOT/ANY로 guard의 부정 OR 조건을 표현할 수 있지만 모든 정책에 이 형식을 강제하지 않는다. guard UNKNOWN을 False로 채우지 않고 기존 3상태 진리표를 유지한다. 비적용 분기의 PASS는 **그 조건을 면제한 결과**이지 전체 사용자 자격 PASS가 아니다.

지금의 rule/input 종류가 실제 guard나 기간을 표현하지 못하면 FULL 불가다. conditional engine·신규 guard evaluator·거주기간 Rule은 이번에 만들지 않는다. 의미상 여러 조건을 묶는 기존 그룹도 검토된 한 condition의 subtree로 매핑할 수 있어 현재 트리를 전면 재작성할 필요는 없다.

## 13. Applicability scope

독립 **ApplicabilityScope 후보**는 edition_id, quarter:int|None이다. quarter는 정확한 1~4 int 또는 None, bool 불가다. quarter=None은 해당 edition의 연간 범위를 뜻하며 “분기 미입력”이 아니다. scope_id는 `2026-Q3` 또는 `2026-ANNUAL`처럼 파생한다. 임의 자유 문자열 scope를 받지 않는다.

연도 edition 문법은 기존 4자리 문자열 그대로다. 이 작은 value는 적용 회차 식별이며 효력일·신청일·지급월을 생성하지 않는다. 향후 연도/분기 이외 제도는 별도 승인 전 미지원으로 거부한다. **Assumption A1:** 이번 최소 모델은 현재 프로젝트의 연도 edition·명시적 분기/연간 구분에 한정한다.

inventory/coverage의 scope가 일치하고 외부 PolicyEnvelope의 edition과 같아야 한다. 별도 검토로 연결된 실제 rule/input 기준도 그 scope와 일치해야 한다. 날짜가 Q3라는 이유로 scope를 추정하거나 다른 분기의 사실/규칙으로 자동 교체하지 않는다.

## 14. Quarter 문제

**A 선택: 2026-Q3 범위에서 FULL_POLICY 가능.** 현행처럼 특정 Q3 release를 외부가 명시 선택하는 구조와 맞는다. 제품/문서에는 항상 `FULL_POLICY for 2026-Q3 eligibility`처럼 범위를 함께 표시한다. 이는 “2026년 모든 분기 FULL”과 다르다.

**B의 연간 FULL**은 별도 ANNUAL inventory에서 모든 해당 회차의 조건·예외·선택 논리가 구현되고 검토됐을 때만 가능하다. Q1~Q4 결과 수를 더하거나 Q3를 annual로 이름만 바꿔 인정하지 않는다. 현재 모델 구현 첫 단계에서는 annual value를 식별할 수 있어도 annual 실제 정책 평가기를 구현하지 않는다. Q3 전용 구현 snapshot을 annual inventory에 연결하면 scope mismatch로 오류다.

현재002는 edition=2026, Q3 birth라는 저장 자료의 명시 범위를 외부에서 Q3 scope로 대응시킬 수 있다. 001은 주민등록 하나이고 그 자체만으로 Q3/연간 scope를 자동 추론하지 않는다. 새 sidecar로 001에 scope를 붙이려면 별도 명시적 검토가 필요하다.

## 15. Application window 분리

자격충족 여부와 지금 신청 가능한지는 다르므로 ApplicationWindow open/closed는 operational 축으로 둔다. 자격 FULL만으로 현재 접수 가능 문구를 표시하지 않는다. 접수창 미구현이면 “신청기간 별도 확인”을 함께 안내한다.

신청일의 주소·기간처럼 **자격 기준일을 사용하는 조건**은 eligibility에 포함한다. 신청일 자체가 미입력이면 기존 평가 UNKNOWN/입력 context 계약을 따르며 coverage를 변경하지 않는다. 특정 날짜/신청 사실이 지급 적용의 선행조건이라면 외부 개인·월 적용 검토에서도 확인해야 한다. 제출서류·자동/소급·대리 신청의 미해결 절차를 구조상 eligibility가 아니라고 해서 해결된 것으로 보지 않는다.

## 16. Nationality / residence conditions

기존 REAL_POLICY_001_RESIDENCE_HISTORY_SPEC.md 25절은 공식 확인본의 등록분류·귀화 의미를 기록한다. 거주자/재외국민 포함과 거주불명자/외국인 제외의 대상 분류는 **ANSAN_YBI_REGISTRATION_ELIGIBILITY**의 REQUIRED 후보로 둔다. 외국인등록·실거주를 주민등록으로 바꾸지 않는다. 재외국민과 외국인을 같은 범주로 취급하지 않는다.

귀화자의 국적취득 후 인정기간은 **ANSAN_YBI_GG_RESIDENCE_DURATION** 내부의 조건부 기산 처리로 포함한다. 취득일 포함·등록상태 변화 경계는 미확정이다. 귀화하지 않은 사용자에게 취득일을 강제하지 않되 적용 분기를 미구현한 채 FULL로 인정하지 않는다.

현재 Q3 **임시 eligibility inventory 후보**:

| condition_id | 분류 | 의미 / 현재002 |
|---|---|---|
| ANSAN_YBI_CURRENT_RESIDENCE | REQUIRED | 신청일 안산 주민등록 / 구현 |
| ANSAN_YBI_BIRTH_DATE | REQUIRED | 2026 Q3 출생일 구간 / 구현 |
| ANSAN_YBI_GG_RESIDENCE_DURATION | REQUIRED | 경기도 최근3년 OR 합산10년, 인정기산 분기 포함 / 보류·미구현 |
| ANSAN_YBI_REGISTRATION_ELIGIBILITY | REQUIRED | 국적/등록분류 관련 대상 조건 / 미구현 |

근거 위치는 주민등록·출생일 구현 문서와 거주이력 명세 2~4·25절에 있다. 이 네 항목은 **기존 분석에서 식별한 최소 후보 목록**이며 정책의 최종 전체 목록으로 인증한 것이 아니다. 그 밖의 eligibility 예외가 있는지 공식 목록 완결성 검토가 필요하다. 신청절차/서류/지급 계산을 이 목록에서 뺐다는 이유로 실제 acceptance를 발급하지 않는다.

## 17. Unresolved semantics

정책 의미 미확정은 **정책 개발/검토 차단**이며 해당 사용자의 정보 부족 UNKNOWN과 다르다. 거주기간 condition은 inventory에 남기되 binding을 만들지 않는다. 구현된 것처럼 항상 UNKNOWN을 반환하는 placeholder를 등록하지 않는다.

별도 runtime BLOCKED_BY_UNRESOLVED_SEMANTICS Enum은 추가하지 않는다. 누락 R−I를 프로그램이 파생하고, 보류 이유/문의 reference는 개발 문서·검토 기록에서 추적한다. 공식 답변 뒤 검토·구현·테스트가 완료되면 새 inventory/규칙 확인본으로 연결한다. 단순 미개발과 의미미확정은 개발 기록에서 구분하지만 둘 다 FULL을 막는다.

**M1.18 ResidenceHistory = OFFICIAL_INQUIRY_REQUIRED**. 1095/3650일·calendar 방식·귀화일 포함을 임의로 결정하지 않으며 관련 Fact/Rule/Evaluator를 구현하지 않는다.

## 18. Evidence coverage

모든 RequiredCondition의 의미는 비어 있지 않은 공식 evidence_refs에 연결되어야 한다. inventory는 구현되지 않은 조건도 근거를 가져야 한다. refs는 source_document_id#locator와 고정 document_version의 조합으로 검토한다. 조건 ID·근거 locator·rule ID는 서로 다른 identity다.

구조 모델은 잘못된 ref 형식·빈 목록 등을 거부하고, 별도 pure source 검증은 주어진 registry/bindings에서 존재·대상 정책·버전을 확인한다. 같은 locator가 여러 조건에 관련될 수 있다. 기존 registry에 필요한 locator가 아직 없으면 임의 locator를 만들어 “검증 완료”로 적지 않고 실제 inventory 발급을 보류한다.

공식성·최신성·목록 완결성은 구조 타입 검증만으로 확인되지 않는다. 전체 목록과 예외를 검토한 기록이 필요하며 사람의 검토를 free-form 문자열 하나로 대체하지 않는다. 새 실제 locator·source/release를 이번에 생성하지 않는다.

## 19. Verification과 독립성

FULL/DRAFT, FULL/VERIFIED, FULL/STALE, SLICE/VERIFIED 모두 다른 상태다. FULL은 공식 의미의 정의·구현 대응이 검토된 것을 요구하되, Envelope의 source freshness·현재 수용 검증과 동일하지 않다. 과거 완결한 구현도 지금 source가 STALE이면 acceptance에 사용할 수 없다.

구현 inventory/트리를 바꾸거나 해당 공식 의미가 정정되면 검토 fingerprint/version 결합을 재확인해야 한다. 과거 FULL 라벨을 새 자료로 자동 승계하지 않는다. DRAFT라는 이유로 구조 오류를 허용하거나 FULL이라는 이유로 VERIFIED로 승격하지 않는다.

## 20. Acceptance gate

향후 M2.4 발급 시 확인할 coverage 조건:

```text
검토 inventory/implementation 자료와 tree의 pure validation 성공
AND validated coverage.derived_scope == FULL_POLICY
AND policy_id / edition / scope / inventory_version / rule / dataset / sources 일치
AND Envelope verification == VERIFIED 및 필요한 source 검토 유효
AND benefit metadata 검토 완료
```

사용 시에도 사용자 FULL_POLICY PASS·개인 적용·target_month·acceptance 버전/기한·Bridge cadence/medium 조건을 별도로 검사한다. Q3 수용 기록을 다른 분기/annual 후보에 재사용하지 않는다.

M2.4 record는 scope/inventory 결합이 명시되지 않았으므로 후속 모델 구현 전에 **accepted_scope와 inventory_version을 결합 값에 추가**해야 한다. Candidate/context에도 동일 scope를 명시해 대조한다. 이는 문서 설계의 필요한 보완이며 기존 코드 변경이 아니다. FULL은 운영/혜택 metadata 검토를 대체하지 않는다.

## 21. Stored vs derived status

**B: 파생 추천.** inventory·bindings·실제 tree·검토 확인본의 검증 결과에서 FULL_POLICY/CONDITION_SLICE를 산출한다. 새 모델에 수동 status와 implemented IDs를 이중 저장하지 않는다. 오류가 있는 구조는 status를 산출하지 않는다.

검토 없는 I=R은 아직 SLICE다. R−I가 비어 있어도 “inventory/구현 검토 미확인”을 별도 설명할 수 있어야 한다. 이 한계를 누락 조건 수0으로 감추지 않는다. 새 순수 모델 생성자만으로 FULL을 얻는 API는 제공하지 않고, 이후 명시적 tree/review 검증이 만든 결과에서만 FULL을 사용한다.

현행 Envelope.evaluation_scope는 legacy의 저장된 CONDITION_SLICE이므로 그대로 둔다. 향후 연결 시에도 legacy 값을 FULL로 변경하는 자동 경로는 없다. 새 결과를 Envelope에 저장하게 되는 별도 형식에서는 파생값과 일치하는지 경계에서 검증해야 한다.

## 22. PolicyCoverage 후보

**additive 선택:** 기존 PolicyCoverage(included_rule_ids, excluded_conditions)는 그대로 보존하고, 별도의 **EligibilityCoverage 후보**를 추가한다. 같은 클래스에 optional 필드를 다수 넣거나 기존 생성자·직렬화·해시·JSON 형식을 즉시 바꾸지 않는다.

| 후보 모델 | 최소 값 |
|---|---|
| ApplicabilityScope | edition_id, quarter |
| RequiredCondition | condition_id, meaning, requirement, evidence_refs |
| ConditionInventory | policy_id, scope, inventory_version, conditions, completeness_review_ref |
| EligibilityCoverage | inventory, bindings:tuple[ConditionBinding,...] |

scope/edition은 inventory로부터 파생하며 coverage에 중복 저장하지 않는다. R/I/missing/status는 계산 결과다. value 모델은 frozen/slots·exact 타입·tuple·작은 to_dict를 우선한다. 사람용 미구현 설명은 기존 excluded_conditions와 개발 문서에 보존한다. 기존 문자열 목록을 파싱해 ID 목록으로 자동 이관하지 않는다.

최초 승인 후 구현 범위는 독립 모델/구조 오류/합성 단위 테스트만이다. tree/review/source validator·Envelope 연결·JSON schema 변경은 후속 별도 작업이다. 새 모델 파일 후보는 policy_data/eligibility_coverage.py 한 개이며 범용 coverage framework는 만들지 않는다.

## 23. ConditionBinding 후보

`condition_id: str`, `rule_root_id: str`, `implementation_review_ref: str`. 셋 모두 비어 있지 않은 안정 참조이며 의미/값 자동 변환은 없다. condition ID는 inventory 안에서 한 번만 binding할 수 있다. root ID는 기존 rule tree ID를 그대로 참조한다.

한 조건의 여러 leaf/group은 root subtree로 묶는다. leaf 전체 목록은 tree에서 파생하며 중복 수동 저장하지 않는다. review ref는 검토한 subtree·전체 조합·rule/입력/evaluator 확인본을 가리킨다. ref만으로 구현 검증이 완료됐다고 판정하지 않는다. 다른 조건이 같은 root나 하위 subtree를 공유하면 중복/충돌 오류다. shared predicate가 필요하면 현재 최소 모델 밖에서 별도 분해 검토해야 한다.

## 24. Validation

후속 검증 책임을 분리한다. 모든 검증은 명시적 값만 받고 시스템 시각·I/O·LLM·입력 변경을 사용하지 않는다.

| 층 | 검증 |
|---|---|
| 값 생성 | exact 타입·ID 문법/공백·빈 inventory·중복 condition/binding·scope edition/quarter·ref 구조 |
| inventory/source | 모든 근거 존재·대상 정책·확인본 일치·명시적 완결성 검토 자료 대조 |
| coverage/tree/review | I⊆R, 각 구현조건 binding 존재, root 존재, subtree 겹침 없음, 실제 leaf 집합 완전 대응, 전체 ALL/조건 내부 연산·분기·기준값과 검토 snapshot 일치, evaluator/입력 지원 |
| 파생 결과 | 누락 집합·검토 부족 여부 → SLICE/FULL, 고정 scope 포함 |

상세 규칙: 조건 ID/구현 ID/binding root 유일; 미등록 condition 구현 금지; 실제 subtree 없는 mapping 금지; mapping 밖 leaf 금지; root ALL의 direct child가 condition roots와 정확히 일치; 단일 condition root 예외; nested subtree 전체 포함. required condition인데 binding이 없는 것은 **정상 SLICE**이며, 구현했다고 선언했는데 binding/노드가 없으면 Data Error다. 별도 implemented 목록을 저장하지 않으므로 그 drift는 기본적으로 차단한다.

I=0은 inventory/계획 값 모델에서 표현 가능하다. 다만 기존 Policy는 빈 tree를 허용하지 않으므로 이 coverage를 실제 비어 있지 않은 트리에 연결하면 미매핑 leaf 오류다. 계획용 coverage와 실행 가능한 Envelope를 혼동하지 않는다.

검토 자료 미확인은 정상 SLICE, 잘못된 명시적 검토 참조·틀린 scope/버전·내용 모순은 Data Error다. 같은 policy의 다른 분기/연간 inventory를 잘못 연결해도 오류다. 모든 구조 오류는 전체 실패이고 UNKNOWN이나 PARTIAL 성공으로 감추지 않는다. 결과의 condition/missing 목록은 condition_id 정렬, tree 의미상 자식 순서는 유지하며 동일 정상 입력/collection 순서 변경에 동일 파생 결과를 보장한다.

**현행 source 검증 연결 GAP:** envelope.py는 source_bindings가 실제 leaf의 source ID 집합과 정확히 같도록 요구하고, validation.py는 그 leaf 근거로 last_verified_at을 계산한다. 미구현 inventory 조건의 추가 source를 그 Envelope에 그냥 넣으면 기존 검증과 충돌한다. 따라서 inventory/review는 별도 source binding 묶음으로 검토하고 legacy Envelope bindings를 확장하지 않는다. 나중에 full 연결 시 source/freshness/serializer/fingerprint 경계를 함께 설계해야 한다.

## 25. Current Ansan example

실제002는 policy_id=KR-GG-ANSAN-YOUTH-BASIC-INCOME, edition=2026, dataset=ansan-youth-2026-10-20-002, rule=r0002다. 명시적 **2026-Q3** 임시 inventory에 대한 mapping 예시는 다음과 같다. 신규 JSON/객체를 만든 것이 아니다.

| condition 후보 | 실제 binding 대상 |
|---|---|
| ANSAN_YBI_CURRENT_RESIDENCE | ANSAN_YBI_2026_RESIDENT_AT_APPLICATION |
| ANSAN_YBI_BIRTH_DATE | ANSAN_YBI_2026_Q3_BIRTH_RANGE |
| ANSAN_YBI_GG_RESIDENCE_DURATION | 없음. 공식 산식 보류 |
| ANSAN_YBI_REGISTRATION_ELIGIBILITY | 없음. 미구현 |

실제 root ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE는 ALL(resident,birth)라서 구현된 두 조건의 결합은 최소 mapping과 대응한다. 기존 included_rule_ids의 두 leaf 집합도 유지할 수 있다. R 후보4/I2 → SLICE다. 최종 공식 inventory 완결성 검토도 아직 없으므로 이 네 개만 채우면 즉시 FULL이라고 하지 않는다.

002 excluded_conditions의 다른 분기/연간 범위·절차·지원금 계산은 새 eligibility 누락 ID로 기계적으로 복사하지 않는다. 회차 경계·operational·benefit 축으로 각각 추적한다. 이를 분리해도 거주기간·등록분류 누락과 공식 의미 미해결은 그대로 남는다. source VERIFIED와 slice PASS를 전체 자격/수용으로 바꾸지 않는다. 현재 결과는 **DRAFT / CONDITION_SLICE, ACCEPTED 불가, 현금 반영0**이다. 001 resident-only 확인본도 불변으로 유지한다.

## 26. Future full Q3 example

**가상:** 공식 목록·모든 조건부 분기가 검토 완료되고 Q3의 모든 R이 지원 입력/evaluator로 구현되며 tree/review 대응이 검증되면 **FULL_POLICY for 2026-Q3 eligibility**가 가능하다. 연간 FULL은 아니다.

그때 Envelope DRAFT라면 수용 불가다. VERIFIED이고 benefit metadata/수용 기록·개인 PASS·월 적용이 확인돼도 LOCAL_CURRENCY/QUARTERLY이면 현재 direct Cashflow 반영은0이다. Coverage, verification, acceptance, 사용자 status, 현금 유형 gate를 각각 유지한다. 현재 안산 거주기간을 완성했다는 예시가 아니다.

## 27. User-facing meaning

FULL: “2026년 3분기 기준 지원 자격조건의 구현범위를 검토했습니다.” 사용자 상태 PASS/FAIL/UNKNOWN은 별도로 표시한다. SLICE: “일부 자격조건만 확인했습니다”와 구현/누락 조건·목록 검토 한계를 함께 표시한다.

“지원 자격 있음”, “지금 신청 가능”, “실제 지급 승인”으로 확정하지 않는다. 신청창 미확인·혜택 미반영은 별도 설명한다. 기존 display_status를 scope 없이 단독 표시하여 slice PASS를 전체 이용 가능성으로 해석하지 않는다. UI/LLM은 구조화한 scope·상태·근거만 설명하고 coverage를 스스로 결정하지 않는다.

## 28. 수동 시나리오

**46개 문서상 사례이며 신규 실행 테스트가 아니다.** 기준은 합성 R={C1,C2,C3,C4}, 같은 policy/edition의 Q3 scope, 공식 inventory와 구현 snapshot 검토 완료다. FULL 사례는 각 조건 subtree와 최상위 ALL 대응이 모두 맞는다고 가정한다. 실제 안산 정책을 승인한 값이 아니다.

| ID | 사례 | 기대 |
|---|---|---|
| PC01 | R4/I2, 실제 tree는 두 binding만 | SLICE, 누락2 |
| PC02 | R4/I4, 모든 검토/트리 대응 | FULL for Q3 |
| PC03 | R4/I0 | 계획 값은 SLICE; 비어 있지 않은 실제 tree에 연결하면 drift 오류 |
| PC04 | required condition ID 중복 | Data Error |
| PC05 | implemented condition 중복 | 중복 binding Data Error |
| PC06 | I에 inventory 밖 CX | Data Error |
| PC07 | required C4에 binding 없음 | 정상 SLICE; C4 구현 완료 주장 금지 |
| PC08 | binding root가 실제 tree에 없음 | Data Error |
| PC09 | tree leaf 존재, mapping 없음 | Data Error |
| PC10 | coverage root 존재 주장, tree에 없음 | Data Error |
| PC11 | 거주기간 ANY root와 두 자식 전체 binding | 구조 대응 가능; 산식 미확정이면 구현 완료 불가 |
| PC12 | 중첩 group subtree 전체를 한 condition에 연결 | 검토 snapshot과 같으면 허용 |
| PC13 | Q3 R/I 모두 완전 | FULL for Q3; annual 아님 |
| PC14 | Q3 검토 트리를 ANNUAL로 라벨 변경 | scope/검토 불일치 Data Error |
| PC15 | inventory scope와 요청 scope 다름 | Data Error |
| PC16 | Q3 inventory에 Q2 전용 구현 snapshot 연결 | Data Error |
| PC17 | FULL + DRAFT | 구조상 가능, acceptance 불가 |
| PC18 | FULL + VERIFIED | coverage/verification 통과; 다른 수용 gate 별도 |
| PC19 | SLICE + VERIFIED | 가능, acceptance 불가 |
| PC20 | FULL + STALE | 가능, 현재 acceptance 적용 불가 |
| PC21 | 현재002 resident+birth | Q3 SLICE |
| PC22 | 거주기간 누락 | FULL 불가 |
| PC23 | 공식 거주 산식 미확정 | binding 등록 금지, SLICE·보류 기록 |
| PC24 | FULL VERIFIED 사용자 PASS | 자격 gate 통과, benefit/수용/개인·월 gate 별도 |
| PC25 | FULL VERIFIED 사용자 FAIL | coverage FULL 유지, 혜택 반영 불가 |
| PC26 | FULL VERIFIED 사용자 UNKNOWN | coverage FULL 유지, 혜택 반영 불가 |
| PC27 | SLICE VERIFIED 사용자 PASS | FULL 승격 없음, 혜택 수용 불가 |
| PC28 | FULL DRAFT 사용자 PASS | verification gate에서 불가 |
| PC29 | conditional guard·적용/비적용 분기 모두 구현 | 해당 condition 완료 가능 |
| PC30 | 일반 사용자 경로만 있고 귀화 분기 없음 | 완료 binding 불가, FULL 불가 |
| PC31 | 비적용 branch를 기존 진리표로 처리 | 그 condition 면제 가능, 전체 PASS 자동 부여 없음 |
| PC32 | required condition에 evidence 없음 | 유효 inventory 생성 불가 |
| PC33 | 모든 required에 유효 공식 refs | evidence gate 통과, 완결성 검토는 별도 |
| PC34 | inventory/binding collection 순서만 변경 | 동일 정렬 결과·누락·파생 status |
| PC35 | 동일 입력 반복 검증 | 동일 결과, 입력 변경 없음 |
| PC36 | condition_id 빈 문자열/공백 | Data Error |
| PC37 | condition_id 숫자/bool | Data Error, 자동 변환 없음 |
| PC38 | 알 수 없는 scope 형태/quarter5 | Data Error |
| PC39 | 같은 condition에 binding 두 개 | Data Error |
| PC40 | 두 condition이 같은 root/subtree 공유 | 충돌 Data Error |
| PC41 | R=I지만 공식 완결성 검토 없음 | SLICE, “목록 검토 중” 표시 |
| PC42 | ANY를 ALL로 교체, node ID는 유지 | 구현 snapshot 불일치 Data Error |
| PC43 | group 자식 삭제, root ID는 유지 | 전체 subtree 검토 불일치, 완료 인정 불가 |
| PC44 | R/I 모두 빈 집합 | 빈 inventory 오류, FULL 금지 |
| PC45 | 근거 없는 보수적 check 추가 | extra eligibility leaf Data Error |
| PC46 | FULL Q3, 접수창/금액 미구현 | 자격 구현 FULL은 가능; 현재 신청/혜택 수용 보장 없음 |

각 오류/미완료를 현재 실제 parser/evaluator가 이미 처리한다고 주장하지 않는다. 향후 순수 모델·tree validator·source/review 연결 검증에 나눠 테스트한다. 코드 의미·공식 완결성은 수동 근거·경계/3상태 테스트와 결합하여 검토한다.

## 29. 미해결 문제

**실제 정책에 남은 항목:** 안산 Q3 inventory의 공식 최종 완결성, 아직 registry에 없는 필수 조건 locator, 거주기간 공식 산식·기산·등록분류 경계, 전체 입력/evaluator 구현, source freshness/교차검토 및 acceptance 연결이다. 새 generic coverage 값 모델의 합성 검증은 가능하지만 실제 FULL은 여전히 불가다.

**후속 통합 항목:** legacy PolicyCoverage/Envelope/loader/serializer/Manifest fingerprint와 독립 EligibilityCoverage를 어떤 명시적 버전 형식으로 연결할지는 별도 설계한다. 기존 policy-data-1.0에 unknown JSON 키를 넣어 우회하지 않는다. 모델만 추가하는 최초 단계에는 이 변경이 필요하지 않다. 실제 I=R이나 새 Enum만으로 acceptance를 발급하는 경로도 만들지 않는다.

**Assumption A2:** 초기 mapping은 의미상 조건별 분리된 subtree와 최상위 ALL로 제한한다. 공유 subtree/DAG·조건 간 임의 논리·복잡한 회차 선택은 필요가 확인된 후 별도 검토한다. 현재 실제 resident-only/ALL(resident,birth) 트리는 매핑 가능하다. 이 제한 때문에 기존 rule engine의 ALL/ANY/NOT 자체를 축소하거나 전면 재작성하지 않는다.

**Assumption A3:** 공식 목록과 구현 검토는 팀의 명시적 근거 검토가 제공한다. 단순 ref나 집합 equality로 원문 의미를 자동 인증할 수 없다. review 수집 플랫폼·정리되지 않은 실제 조건 자동 생성·LLM 자격판정은 만들지 않는다.

ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 공식 semantics 해결 전 실제 안산 FULL은 불가능하며 문서 단계와 독립 모델 준비를 그 보류 해제로 해석하지 않는다.

## 30. 최종 판단

**READY_TO_IMPLEMENT_POLICY_COVERAGE_MODELS**

전체 의미와 scope, inventory/condition identity, subtree binding, 파생 status, 집합 equality의 한계 및 검토 대응 의무를 정의했다. 기존 실제 트리를 additive한 독립 coverage 모델에 연결하는 방향은 표현 가능하다. 실제 inventory 완결성·거주기간·full 연결은 승인되지 않았다.

다음 가장 작은 작업 한 개: **ApplicabilityScope 불변 값 모델만 합성 단위 테스트와 함께 구현**한다. edition/quarter의 정확한 타입·범위·scope_id·불변성만 검증한다. 현재 Envelope의 edition/evaluation_scope/coverage/loader를 변경하거나 다음 coverage 모델을 한 번에 구현하지 않는다.

### 검증 기록

기존 전체 pytest는 **2810 passed in 7.79s**다. 신규 실행 테스트는 없다. 이 문서의 30개 필수 절과 PC01~PC46의 순서·유일성·누락 여부 및 한국어 표기를 확인했다. 이 결과는 아직 없는 coverage 모델/validator의 실행 검증을 의미하지 않는다.

Git 저장소가 없어 git status를 조회할 수 없었다. 작업 전 backend/tests/data/docs의 기존 **97개 파일 SHA256이 모두 동일**하며 수정·삭제는 없다. 추가는 이 문서 한 개다. PolicyEnvelope/기존 Coverage/Policy Engine/Cashflow/actual releases/tests/기존 문서/ResidenceHistory를 변경하지 않았다.

## 31. M2.6 — IMPLEMENTED: 독립 ApplicabilityScope

backend/policy_engine/policy_data/eligibility_coverage.py에 frozen/slots dataclass 하나를 추가했다. policy_data의 공개 export는 ApplicabilityScope만 additive하게 추가했다. 기존 모델·validator·loader·평가 로직·실제 releases는 변경하지 않았다.

생성자 계약은 `ApplicabilityScope(edition_id: str, quarter: int | None)`이며 **두 인자 모두 필수**다. 명세13절의 정확한 타입이 M2.6 지시문의 Enum 후보보다 우선하므로 PolicyQuarter는 추가하지 않았다. quarter는 정확한 int 1~4 또는 None만 허용하며 문자열 Q3/3·bool·float·IntEnum·int 하위 타입은 거부한다. None은 미입력 아닌 연간 범위다.

edition_id는 기존 PolicyEnvelope와 같은 `type(value) is str` 및 `re.fullmatch(r"[0-9]{4}", value)`를 사용한다. 기존 검증은 __post_init__ 안의 inline 식이어서 Envelope를 수정하거나 private 모델 검증에 결합하지 않고 동일한 작은 식을 사용했다. 공백/Unicode 숫자/문자열 하위 타입/숫자 변환은 허용하지 않는다. 0000도 기존 계약상 유효한 네 자리이므로 거부하지 않는다. 실제 사업연도·달력 유효성 검증이나 최대연도 제약을 새로 추가하지 않았다.

잘못된 값은 기존 PolicyDataError(EngineValidationError/ValueError 계층)다. 메시지에서 edition_id/quarter 필드를 식별하며 원본 값을 넣지 않는다. 새 오류 계층·UNKNOWN 상태는 없다. 필수 인자 누락/정의되지 않은 추가 인자는 Python TypeError다.

to_dict는 새 dict로 `{"edition_id": "2026", "quarter": 3}` 또는 `{"edition_id": "2026", "quarter": None}`을 반환한다. 분기 문자열/Enum 값으로 변환하지 않으며 JSON에서 annual은 null이다. scope_id property는 2026-Q3 / 2026-ANNUAL을 파생하는 표시값이며 identity 저장 필드가 아니다. equality/hash는 두 원본 필드를 사용한다. 순서·포함관계·문자열 parser는 구현하지 않았다.

모듈의 직접 의존은 dataclasses/re/기존 PolicyDataError뿐이다. 기존 policy_engine/policy_data 패키지의 eager import는 유지했으므로 import된 패키지 전체에 정책 모델이 없다는 보장은 하지 않는다. 새 value object 자체는 PolicyEvaluation/Cashflow/Acceptance·시스템 시각·신청일·I/O에 의존하지 않는다. 날짜/프로필/context·policy_id 필드는 없다.

IMPLEMENTED: ApplicabilityScope, 명시적 edition/quarter/annual, strict 검증, frozen/slots, value equality, 새 snapshot·scope_id, 합성 단위 테스트.

NOT IMPLEMENTED: PolicyQuarter(불필요), RequiredCondition, ConditionInventory, ConditionBinding, EligibilityCoverage, FULL/SLICE 파생, tree/source/review validator, Acceptance, Benefit Bridge, 실제 scope/release 연결. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 보류하고 실제 안산 정책을 FULL로 승격하지 않는다.

검증: 작업 전 전체 **2810 passed in 8.30s**, 신규 tests/test_applicability_scope.py **84 passed in 0.37s**. 네 분기/annual·다른 edition·exact 타입·ASCII·경계값·equality·불변성·명시적 두 인자·새 snapshot·자동 날짜 선택/다른 domain 직접 의존 부재를 검증했다.

최종 판단: **READY_FOR_CONDITION_INVENTORY_MODELS**. 다음 가장 작은 작업은 RequiredCondition 값 모델 하나의 필드·검증·불변성을 합성 테스트와 함께 구현하는 것이다. Inventory/Binding/coverage 계산·실제 정책 연결은 별도 단계다.

### M2.6 최종 검증 기록

전체 pytest는 **2894 passed in 8.54s**다. 기존2810개와 신규84개 모두 통과했고 기존 테스트/기대값은 수정하지 않았다. 변경 파일의 한국어 표기와 새 모델의 직접 의존·금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 98개 파일의 SHA256과 대조했다. 기존94개는 동일하며 변경은 policy_data 공개 export 한 파일과 승인된 문서 세 파일뿐이다. 신규 파일은 모델/테스트 두 개, 삭제는 없다. 기존 PolicyEnvelope/PolicyCoverage/평가·loader·Cashflow·actual releases·모든 기존 테스트·Acceptance/Benefit 명세·ResidenceHistory 관련 자료는 바이트 단위 동일하다. Git 저장소가 없어 git status는 사용할 수 없었다.

## 32. M2.7 — IMPLEMENTED: RequiredCondition 의미 값

policy_data/required_condition.py에 ConditionRequirement(str, Enum)와 RequiredCondition(frozen/slots)을 추가했다. policy_data 패키지의 공개 export로 두 이름을 추가했다. 같은 eligibility_coverage.py에 추가하는 방안은 기존 Scope 테스트가 모듈의 클래스/의존 목록까지 고정하므로 채택하지 않았다. 기존 Scope·84개 테스트와 기대값을 변경하지 않고 같은 패키지의 작은 파일 하나로 분리했다. 새 package hierarchy는 없다.

정확한 생성자 필드는 `condition_id: str`, `meaning: str`, `requirement: ConditionRequirement`, `evidence_refs: tuple[str, ...]`이며 모두 필수다. requirement는 정확한 REQUIRED/CONDITIONAL Enum member만 허용한다. INFORMATIONAL은 명세대로 eligibility inventory 밖이므로 추가하지 않았다. 두 분류 모두 향후 구현 의무 대상이며 조건부 분기/evaluator를 이 모델에서 계산하지 않는다.

condition_id는 정확한 비어 있지 않은 str에 대해 명세6절의 대문자·숫자·밑줄 문자 범위만 검사한다(`[A-Z0-9_]+`). 실제 정책 prefix·최대 길이·접두 문자·숫자 순번 형태 같은 제약을 추가하지 않는다. 공백/표시문장·소문자·비ASCII 문자·str 하위 타입을 거부하고 자동 생성/strip/str 변환은 없다. 정책 안에서의 identity·중복 ID 충돌은 향후 Inventory 책임이다.

meaning은 정확한 비어 있지 않은 str이며 whitespace-only는 거부한다. 유효한 문장의 앞뒤 공백은 그대로 보존한다. 의미 문장을 ID로 쓰지 않고 서로 다른 metadata의 같은 ID 객체는 모델 단독으로 생성할 수 있다. equality는 네 필드 전체의 값 비교다.

evidence_refs는 빈 tuple을 **생성 단계부터 거부**한다. 명세5·18절이 조건 의미에 대한 근거를 필수로 요구하므로 FULL 검증까지 미루지 않았다. 정확한 tuple만 받고 요소는 기존 순수 parse_evidence_ref로 canonical source_document_id#locator 형식을 검사한다. 문자열/목록 자동 변환·공백 보정·대소문자 변환은 없다. 기존 specialized rule의 tuple 관례를 따르되 명세의 ref 형식 요구에 맞춰 기존 canonical parser를 재사용한다.

중복 refs는 제거/정렬하지 않고 순서와 함께 보존한다. 값 모델의 structural 검사와 실제 inventory/source의 중복·존재·버전 검토를 분리한다. SourceRegistry를 입력/보관/조회하지 않으며 canonical 형식이 맞는 합성 미등록 ref도 표현할 수 있다. 실제 정책 원문·공식성·최신성·근거 검증 완료를 인증하지 않는다. Rule evidence와 자동 동기화하지 않는다.

오류는 기존 PolicyDataError를 사용하며, canonical ref 오류는 기존 SourceValidationError(PolicyDataError 하위)를 그대로 전달한다. 새 오류 계층·판정 상태는 없다. 필수 인자 누락/정의되지 않은 인자는 Python TypeError다. 원본 payload를 오류 문구에 넣지 않는다.

to_dict는 정확한 네 key를 새 dict로 반환한다. requirement는 REQUIRED/CONDITIONAL 문자열, evidence_refs는 새 list다. snapshot과 내부 tuple은 독립이다. scope/policy_id/rule_id/implementation_review_ref/implemented/coverage·verification·acceptance 상태/benefit 필드는 없다. 실제 정책 ID·금액·분기를 기본값으로 넣지 않았다.

IMPLEMENTED: ApplicabilityScope(기존 유지), ConditionRequirement, RequiredCondition, strict 구조·canonical ref 검증, 불변성·equality·결정적 값 표현, 합성 테스트.

NOT IMPLEMENTED: ConditionInventory, ConditionBinding, EligibilityCoverage, FULL/SLICE 파생, rule 연결·tree/source cross-validation, Acceptance, Benefit Bridge, 실제 inventory/release 연결. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 보류하며 실제 거주기간 condition을 추가·확정하지 않는다.

검증: 작업 전 전체 **2894 passed in 8.32s**. 신규 tests/test_required_condition.py **104 passed in 0.35s**. 두 분류·필수 네 필드·strict ID/meaning/Enum·refs 타입/빈 목록/형식·중복/순서·불변성·동일 ID의 metadata 차이·snapshot 독립성·출처 조회 부재·금지 필드/직접 의존 부재를 확인했다. 모든 ID/refs는 합성 자료이며 실제 정책 의미 검증은 아니다.

최종 판단: **READY_FOR_CONDITION_INVENTORY**. 다음 가장 작은 작업 한 개는 ConditionInventory의 불변 값 모델과 ID 유일성·scope 소유·review_ref 선택 계약을 합성 단위 테스트로 구현하는 것이다. Binding/tree/FULL 판정·실제 inventory 인코딩은 포함하지 않는다.

### M2.7 최종 검증 기록

전체 pytest는 **2998 passed in 8.33s**다. 기존2894개와 신규104개 모두 통과했고 기존 테스트/기대값은 변경하지 않았다. ApplicabilityScope 코드와 그 테스트84개도 그대로다. 변경 파일의 한국어 표기 및 새 모델의 직접 의존·금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 100개 파일의 SHA256을 대조해 기존96개가 동일함을 확인했다. 변경은 policy_data 공개 export 한 파일과 승인된 문서 세 파일이며, 신규 모델·테스트 두 파일 외 추가/삭제는 없다. 기존 Scope/PolicyEnvelope/PolicyCoverage/평가·loader·source parser·Cashflow·actual releases·모든 기존 테스트·Acceptance/Benefit 명세·ResidenceHistory 자료를 보존했다.

## 33. M2.8 — IMPLEMENTED: scope 소유 ConditionInventory

policy_data/condition_inventory.py에 frozen/slots ConditionInventory만 추가하고 policy_data 공개 export로 제공한다. 기존 Scope/RequiredCondition 모듈은 각각의 기존 모듈 경계와 테스트를 유지하도록 변경하지 않았다. 같은 패키지에 작은 파일 하나를 추가했으며 모델 재배치나 새 package는 없다.

정확한 필드 순서는 다음과 같다.

| 필드 | 계약 |
|---|---|
| policy_id:str | 필수. 기존 Envelope와 같은 대문자·숫자·하이픈 canonical ID |
| scope:ApplicabilityScope | 필수. 정확한 타입만 허용, 원래 객체 보존 |
| inventory_version:str | 필수. i0001부터의 명시적 양의 확인본 버전 |
| conditions:tuple[RequiredCondition,...] | 필수. 최소1개, 정확한 tuple과 정확한 요소 타입 |
| completeness_review_ref:str\|None | 기본 None. 값이 있으면 정확한 비공백 문자열 |

최종 최소 구조인22절을 따라 edition은 scope.edition_id에만 보존한다. 5절 초기 후보 identity 표의 edition_id를 별도 저장 필드로 복제하지 않았다. 서로 다른 정책의 같은 scope를 구별하기 위해 policy_id는 유지한다. policy ID 검증은 기존 inline canonical 식과 동일하며 공백·문자열 하위 타입·자동 변환을 거부한다.

inventory_version은 기존 r/d 버전 형태와 같은 양의 버전 구조에 i 접두사를 적용한다: i0001~i9999, i10000 이상을 허용하고 i0000·축약·대문자 alias·불필요한 선행0·공백·잘못된 타입은 거부한다. 자동 생성/증가/최신 선택은 없다. 이 버전 값만으로 실제 immutable 파일이나 검토 사실을 인증하지 않는다.

빈 inventory는 명세5·10절대로 생성 단계부터 거부한다. 같은 condition_id는 동일 객체·동일 값·meaning/requirement/evidence가 다른 경우 모두 오류이며 전체 생성이 실패한다. 조용한 dedupe나 승자 선택은 없다. 다른 ID의 같은 meaning은 자연어로 비교하지 않고 허용한다. REQUIRED/CONDITIONAL 혼합도 정상이며 사용자별 적용은 계산하지 않는다.

scope와 conditions tuple 및 각 RequiredCondition을 **그대로 보존**한다. 입력 순서·개별 evidence의 순서/중복을 유지하며 정렬·합산·근거 재검증·합집합 필드 추가는 없다. object equality는 다섯 필드와 tuple 순서에 기반한다. 향후 coverage set 비교와 구분하며 custom unordered equality를 만들지 않았다.

completeness_review_ref=None은 목록의 완결성 검토를 아직 확인하지 못한 임시 정의를 표현한다. 생략 시 None으로 보존하며, 빈/whitespace-only·str 하위 타입·다른 타입은 오류다. 유효한 참조 문자열의 앞뒤 공백은 자동 제거하지 않고 보존한다. 원문 ref 형식으로 파싱하거나 파일/registry 존재를 조회하지 않는다. 문자열만으로 공식 검토·목록 완결성·FULL·acceptance를 승인하지 않는다. review_ref와 개별 evidence_refs는 다른 책임이다.

오류는 기존 PolicyDataError를 사용한다. 입력 오류는 UNKNOWN이 아니며 오류 문구에 원본 payload를 넣지 않는다. 필수 네 인자 누락/정의되지 않은 추가 인자는 Python TypeError다. 기존 하위 값 모델 검증을 복제하지 않고 exact 객체 타입을 전제로 한다.

to_dict는 policy_id, scope, inventory_version, conditions, completeness_review_ref의 새 중첩 dict/list를 반환한다. scope/condition의 기존 to_dict를 사용하며 refs list까지 원본과 독립적이다. 조건 수/정렬·상태·review 조회값을 추가하지 않는다. 현재시간·random·I/O·정책 평가·Rule 연결은 없다.

IMPLEMENTED: ApplicabilityScope·RequiredCondition(기존 유지), ConditionInventory, policy/scope/version 소유, strict tuple·요소 검증, ID 유일성, 선택적 검토 참조, 불변성·equality·결정적 중첩 snapshot, 합성 단위 테스트.

NOT IMPLEMENTED: ConditionBinding, rule_id 연결, tree 검증, implemented set, EligibilityCoverage, FULL/SLICE 파생, Acceptance, Benefit Bridge, 실제 안산 inventory. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 계속 보류하고 관련 actual condition을 추가·확정하지 않는다.

검증: 작업 전 전체 **2998 passed in 8.51s**, 신규 tests/test_condition_inventory.py **119 passed in 0.33s**. 단일/복수·혼합 조건·annual/Q3·policy/version·중복/충돌·정확한 타입/하위 타입 거부·review None/문자열·순서/equality·중첩 불변성/snapshot 독립성·하위 모델/근거 재검증 및 조회 부재·금지 필드를 확인했다. 모든 입력은 합성 객체다.

최종 판단: **READY_FOR_CONDITION_BINDING_MODEL**. 다음 가장 작은 작업 한 개는 ConditionBinding의 condition_id/rule_root_id/implementation_review_ref 불변 값 모델과 구조 검증을 합성 단위 테스트로 구현하는 것이다. tree 대조·Binding 간 중복·FULL 파생·실제 정책 연결은 포함하지 않는다.

### M2.8 최종 검증 기록

전체 pytest는 **3117 passed in 8.75s**다. 기존2998개와 신규119개가 모두 통과했으며 기존 테스트/기대값은 수정하지 않았다. 기존 Scope/RequiredCondition 코드·직렬화·테스트도 그대로다. 신규 소스·문서의 한국어 표기와 직접 의존/금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 102개 파일의 SHA256을 대조했다. 기존98개는 동일하고 변경은 policy_data 공개 export 한 파일과 승인된 문서 세 파일이다. 신규 모델·테스트 두 파일만 추가했으며 삭제는 없다. 기존 Scope/RequiredCondition/PolicyEnvelope/PolicyCoverage/평가·loader·Cashflow·actual releases·모든 기존 테스트·Acceptance/Benefit 명세·ResidenceHistory 자료를 보존했다.

## 34. M2.9 — IMPLEMENTED: ConditionBinding 참조 값

policy_data/condition_binding.py에 frozen/slots ConditionBinding 하나를 추가하고 policy_data 공개 export로 제공한다. 정확한 필드는 `condition_id:str`, `rule_root_id:str`, `implementation_review_ref:str` 세 개이며 모두 필수다. 명세23절은 검토 참조를 optional로 정의하지 않았으므로 None을 허용하지 않는다.

condition_id는 RequiredCondition과 같은 exact str 및 `[A-Z0-9_]+` 계약이다. 기존 검증은 해당 모델의 inline 식이고 공유 helper가 없다. 기존 모델 변경 금지와 독립 참조 모델 경계를 지키기 위해 같은 작은 식을 사용했으며, 신규 테스트에서 두 생성자의 유효/무효 ID 결과를 직접 비교했다. 자동 생성·strip·uppercase는 없다.

rule_root_id는 기존 PolicyRule/RuleGroup의 require_text와 동일한 exact str·비공백 계약이다. 그 helper가 전체 models.py 안에 있어 Policy/RuleNode 등에 결합하지 않도록 같은 작은 검사를 독립적으로 적용했다. 기존 node ID에 없는 대문자/regex 제한을 추가하지 않는다. 앞뒤 공백을 가진 유효한 문자열도 기존 규칙처럼 보존하며 자동 정리하지 않는다. 신규 테스트에서 Binding/PolicyRule/RuleGroup의 정상·오류 수용 결과를 비교했다.

condition_id와 rule_root_id는 서로 다른 역할이며 같은 문자열이어도 생성 가능하다. leaf/group을 식별하거나 한 값으로 다른 값을 만들지 않는다. 의미상 조건 한 개에 subtree root 한 개만 연결하므로 rule_ids 목록은 없다. 여러 Binding의 같은 조건/같은 root 충돌도 이번 단일 객체 생성자가 판단하지 않는다.

implementation_review_ref는 정확한 비공백 str이고 유효한 문자열의 앞뒤 공백은 그대로 보존한다. RequiredCondition의 공식 의미 evidence 및 Inventory의 전체 목록 검토 ref와 다르다. 실제 검토 기록·구현 snapshot·외부 파일을 조회하지 않는다. 이 ref가 있다는 사실만으로 구현 검토 완료·FULL·VERIFIED·ACCEPTED를 뜻하지 않는다.

scope/edition/quarter/policy_id/RequiredCondition/RuleNode 객체·evidence_refs·implemented/full/verification/acceptance flags·benefit metadata는 없다. 직접 의존은 dataclasses/re/기존 PolicyDataError뿐이다. 기존 Scope/RequiredCondition/Inventory를 import하거나 재생성하지 않는다. 실제 tree·입력모델·현재시각·신청일·I/O도 사용하지 않는다.

잘못된 값은 기존 PolicyDataError이며 UNKNOWN으로 변환하지 않는다. 원본 값은 오류 문구에 넣지 않는다. 필수 인자 누락/정의되지 않은 추가 인자는 Python TypeError다. to_dict는 세 원래 문자열의 새 dict이며 equality/hash는 세 필드 전체에 기반한다. 문자열 비교용 순서·포함관계·파서는 추가하지 않았다.

IMPLEMENTED: 기존 ApplicabilityScope·RequiredCondition·ConditionInventory(변경 없음), ConditionBinding의 세 참조·strict 검증·불변성·equality·결정적 snapshot·합성 단위 테스트.

NOT IMPLEMENTED: Inventory 대조, 실제 root 존재/노드 종류·subtree 검증, binding collection 중복/겹침 검사, EligibilityCoverage, FULL/SLICE 파생, Acceptance, Benefit Bridge, actual 안산 mapping/coverage. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 보류한다.

검증: 작업 전 전체 **3117 passed in 9.07s**, 신규 tests/test_condition_binding.py **82 passed in 0.31s**. leaf/group 참조·조건부형 합성 ID·독립 ID 역할·두 기존 ID 계약과의 수용 결과 동등성·필수 ref·strict 타입/공백·불변성/equality/snapshot·실제 tree/검토 조회 부재·금지 필드/직접 의존 부재를 검증했다. 모든 입력은 합성 ID이며 실제 정책 연결을 승인하지 않는다.

최종 판단: **READY_FOR_ELIGIBILITY_COVERAGE_DESIGN**. 다음 가장 작은 작업 한 개는 EligibilityCoverage의 입력 구성과 구조 오류/미완료 구분을 문서로 설계하는 것이다. 특히 Inventory/Binding과 tree 검증의 책임·파생 상태의 생성 경계를 정리하며 새 모델·tree validator·FULL 파생을 자동 구현하지 않는다.

### M2.9 최종 검증 기록

전체 pytest는 **3199 passed in 8.59s**다. 기존3117개와 신규82개 모두 통과했으며 기존 테스트/기대값은 수정하지 않았다. 변경 파일의 한국어 표기와 새 모델의 직접 의존·금지 기능 부재를 확인했다.

작업 전 backend/tests/data/docs 104개 파일의 SHA256을 대조했다. 기존100개는 동일하고 변경은 policy_data 공개 export 한 파일과 승인된 문서 세 파일이다. 신규 모델·테스트 두 파일만 추가했으며 삭제는 없다. Scope/RequiredCondition/Inventory/PolicyEnvelope/PolicyCoverage/평가·loader·Cashflow·actual releases·기존 테스트·Acceptance/Benefit 명세·ResidenceHistory 자료를 보존했다.

## 35. M2.11 — IMPLEMENTED: Coverage 구조 입력

policy_data/coverage.py의 EligibilityCoverage는 inventory와 bindings 두 필수 필드만 갖는 frozen/slots 모델이다. 기존 Scope/조건/Inventory/Binding 파일은 변경하지 않고 public export만 추가했다. Inventory와 Binding tuple/요소는 exact 타입이며 원래 객체·순서를 보존한다. 빈 tuple·부분 mapping·검토 참조 미확인·다른 condition의 동일 root는 표현 가능하다.

constructor는 중복 condition_id와 inventory 밖 condition 참조를 PolicyDataError로 거부한다. scope/policy_id/version 직접 필드·status·missing/implemented 집합·Policy/ReviewContext는 없다. 하위 객체를 다시 검증하거나 tree/root/소유/검토 완료를 판단하지 않는다. 생성 성공은 입력의 로컬 정합성일 뿐 FULL/SLICE 판정이 아니다.

to_dict는 inventory/bindings 두 key의 새 중첩 snapshot만 반환한다. 입력 순서와 구조 equality를 유지한다. legacy Coverage/Envelope·실제 releases·ResidenceHistory를 변경하지 않았다.

IMPLEMENTED: 기존 네 값 모델, EligibilityCoverage structural model/strict tuple·참조/중복 검증/불변성/직렬화/신규83개 테스트. NOT IMPLEMENTED: ReviewContext/CoverageResult/tree validator/FULL·SLICE 파생/Acceptance/Bridge/actual mapping. 생성자와 후속 validator의 정확한 책임표·검증 기록은 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md 33절이다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 최종 판단은 READY_FOR_COVERAGE_REVIEW_CONTEXT다.
