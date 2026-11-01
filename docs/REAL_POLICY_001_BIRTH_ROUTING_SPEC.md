# BirthDateRule의 mixed tree 연결 계약 — M1.16F

현재 구현 상태는 25절 M1.16G 기록을 따른다. 아래 1~24절의 문서 전용 작업과 미래형 변경안은 M1.16F 당시 설계 기록이다.

작성일: 2026-10-20 / Asia/Seoul. **문서 설계 전용**이며 이 파일 하나만 추가한다. 아래 변경안·시나리오는 현재 구현이 아니다.

최종 판단: **READY_TO_IMPLEMENT_BIRTH_ROUTING**. 독립 evaluator를 메모리 내 단일 Policy mixed tree에 연결하는 후속 계약이다. JSON 로딩·실제 정책 발행·분기 선택은 포함하지 않는다.

## 1. 목적

이미 구현된 BirthDateRule/BirthFact/evaluate_birth_date_rule/RuleEvaluation을 기존 유한 타입 기반 routing에 연결할 최소 모델·입력·dispatch 계약을 확정한다. 날짜 비교는 기존 birth evaluator에 남기고, 집계·정책 근거 검증·시점/분기 선택 책임을 섞지 않는다.

Source of Truth 검토: REAL_POLICY_001_BIRTH_SLICE_SPEC.md, REAL_POLICY_001_BIRTH_RESULT_CONTRACT.md(25절 현재 evaluator), RULE_ROUTING_SPEC.md, POLICY_RULE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 실제 models.py/evaluation_inputs.py/routing.py/birth_evaluator.py/evaluator.py 및 관련 테스트를 확인했다. 역사적 문서의 초기 모델 상태와 현재 실행 계약을 구별했다.

## 2. 현재 routing 구조

| 영역 | 현재 구현 |
|---|---|
| RuleNode | PolicyRule / ResidentRegistrationRule / RuleGroup의 유한 union |
| Policy.root / RuleGroup.children | 같은 정확한 타입만 허용. BirthDateRule은 아직 거부 |
| 순회/중복 검사 | walk_nodes가 모든 노드를 방문하고 RuleGroup에서만 재귀. ID를 타입 구분 없이 수집 |
| EvaluationFacts | resident_registrations의 불변 typed tuple만 보유 |
| public routing | evaluate_policy_tree(profile,policy,context,*,facts=None,reference_context=None) |
| atomic 분기 | 기존 _evaluate_atom(profile,node) |
| resident 분기 | 기존 Resolver → 반환 날짜 정합성 확인 → 기존 Adapter |
| group 분기 | 자식 전체 재귀 → _assemble_group_result |
| birth evaluator | 별도 함수로 완성. Rule/단일 Fact만 받아 RuleEvaluation 반환 |
| 미지원 노드 | 명시적 PolicyDataError. UNKNOWN fallback 없음 |

dispatch는 isinstance가 아니라 **type(node) is ...**다. 독립 dataclass를 자동 상속/duck typing으로 받아들이지 않는다. 현재 public 함수는 profile/policy/context/facts와 전달된 reference_context의 정확한 타입을 검증한다.

## 3. RuleNode 확장안

후속 유한 union: `PolicyRule | ResidentRegistrationRule | BirthDateRule | RuleGroup`.

Policy.root와 RuleGroup.children의 런타임 exact 타입 허용 목록에도 BirthDateRule을 함께 추가한다. PolicyRule 상속·동적 registry·generic dict·기존 클래스명 변경은 없다. 독립 BirthDateRule 자체의 min/max·근거 검증은 그대로 사용한다.

walk_nodes는 RuleGroup만 재귀하고 나머지는 leaf로 방문하므로 알고리즘을 바꿀 필요가 없다. 타입 주석과 생성자 허용 목록을 일치시키되 그 외 객체·하위 타입을 무조건 허용하지 않는다.

### 기존 PolicySet / legacy 평가 경계

이번 연결 대상은 **단일 메모리 Policy → evaluate_policy_tree**다. legacy evaluate_policy/evaluate_policies는 facts 인자가 없고 기존 _evaluate_node가 atomic/group만 받으므로 birth도 계속 명시적으로 거부해야 한다. 해당 evaluator를 새 dispatch로 자동 전환하지 않는다.

PolicySet은 schema_version이 붙는 별도 컨테이너다. 현재 m1.0에서 resident를 거부하는 guard가 있으므로, union 확장으로 birth가 우연히 m1.0에 들어가지 않게 해야 한다. **M1.16G에서는 BirthDateRule을 가진 PolicySet을 m1.0/m1.1 모두 명시적으로 거부**하는 최소 guard를 권장한다. m1.1 JSON loader가 birth를 지원하지 않는 상태에서 메모리 PolicySet만 schema 지원을 먼저 주장하지 않는다. m1.1의 기존 atomic/resident 컨테이너는 그대로 유지한다. 이 guard는 schema/version을 새로 도입하는 기능이 아니다.

PolicyEnvelope·dataset/배포 발행을 추가하는 작업은 이번 계약 밖이다. 위 guard가 모든 메모리 Envelope의 의미를 자동 검증하는 gate라고 주장하지 않는다.

## 4. EvaluationFacts 확장안

기존 첫 필드/인자 `resident_registrations: tuple[ResidentRegistrationFact,...] = ()`를 유지하고 **keyword-only** `birth: BirthFact | None = None`을 추가하는 방식을 채택한다.

| 생성 형태 | 후속 계약 |
|---|---|
| EvaluationFacts() | resident 빈 tuple, birth None |
| EvaluationFacts(existing_resident_tuple) | 기존 첫 positional 인자 의미 유지, birth None |
| EvaluationFacts(resident_registrations=..., birth=fact) | 기존 주민등록 사실과 단일 출생일 사실 전달 |
| EvaluationFacts(birth=fact) | 주민등록 사실 없이 단일 birth 전달 |
| birth=None | 유효한 미입력 |
| birth가 list/tuple/dict/str/UserProfile 등 | 생성 단계 ProfileValidationError |

BirthFact 내부 날짜/source는 기존 생성자 책임이며 입력 묶음은 정확한 BirthFact/None 타입만 추가 검증한다. source 우선순위·Fact 병합·나이 역산을 하지 않는다. frozen/slots 전략과 resident tuple의 순서·중복·모순 보존은 그대로다.

### to_dict 호환성

birth가 None이면 **새 birth 키를 생략**하고 기존 `{resident_registrations:[...]}` 출력을 정확히 유지한다. Fact가 존재할 때만 birth 키에 기존 BirthFact.to_dict() 값을 둔다. 날짜만 None인 Fact는 birth를 생략하지 않고 `{birth_date:null,source:...}`를 보존한다.

따라서 `EvaluationFacts()`와 명시적 birth=None은 같은 값/출력이다. 모델 필드 자체는 실제로 추가되므로 dataclasses.fields/asdict의 새 필드는 숨기지 않는다. 공개 to_dict의 호환성과 reflection 필드 수의 변화를 구별한다. 반환 타입 주석은 새 중첩 값을 표현하도록 dict[str,object] 등 최소 범위로 갱신한다. 새 JSON 입력 schema나 generic serializer는 만들지 않는다.

## 5. BirthFact 입력 계약

router는 검증된 `EvaluationFacts.birth`를 **그대로** evaluator의 두 번째 인자로 전달한다. Fact가 없으면 None을 전달한다. BirthFact 자체·source·date를 복제/보정/선택하지 않는다.

Fact 없음과 Fact 날짜 없음의 정상 UNKNOWN은 evaluator가 생성한다. router는 UNKNOWN 결과 객체나 reason/missing_fields를 직접 만들지 않는다. birth_source는 결과 details에, 정책 refs는 결과 evidence_refs에 남는 기존 계약을 유지한다.

## 6. dispatch 계약

기존 exact 타입 방식으로 atomic → resident → **birth** → group 순서의 명시적 분기를 둔다. 네 클래스는 서로 독립이므로 상속에 따른 가로채기 문제는 없다. catch-all은 마지막의 기존 미지원 타입 오류로 유지한다.

birth 분기 의미: **`(evaluate_birth_date_rule(node, facts.birth),)`**를 반환한다. _route_node가 요구하는 tuple[RuleEvaluation,...] 모양만 맞추고 내부 RuleEvaluation은 그대로 전달한다. 새로운 birth 전용 list/중간 Resolution/Adapter는 없다.

노드 ID·근거·상태·reason·condition·관찰값·details를 router에서 재조립하거나 비교하지 않는다. 현행 evaluator가 반환 타입/값을 구성·검증하는 책임을 가지며 router는 날짜 판정이나 source 우선순위를 추가하지 않는다. 함수 호출 경계 테스트는 동일 node/fact 인자와 반환 객체 보존을 확인한다.

atomic/resident 분기 본문의 의미·호출 인자·날짜 정합성 검사는 그대로 유지 가능하다. 필요한 변경은 import와 birth 분기, 입력 모델 및 타입 허용 목록이다.

## 7. UserProfile.age 금지

새 분기는 profile을 evaluator에 전달하지 않는다. `facts.birth is None`이고 age=24여도 UNKNOWN이다. 출생일이 범위 안이면 age=23/25여도 birth leaf PASS다. UserProfile에서 BirthFact 생성·날짜 역산·기준일 불명 age와의 교차검증을 하지 않는다.

다른 atomic age leaf가 같은 트리에 있으면 그 leaf는 기존 방식으로 profile.age를 평가할 수 있다. 두 leaf 결과가 다른 것은 데이터 오류라고 자동 해석하지 않는다. 각 조건의 요구 의미를 유지한다.

## 8. EvaluationContext 영향

public evaluate_policy_tree의 context는 필수이고 기존 exact 타입/engine_version 검증을 유지한다. birth 분기가 그 context를 사용하지 않는 것은 atomic leaf가 필요한 프로필만 읽는 것처럼 자연스러운 최소 의존성이다.

고정 Rule/Fact의 **birth leaf**는 context.as_of 변경에 불변이다. PolicyEvaluation.context 자체는 전달받은 값을 보존하므로 정책 JSON 전체는 달라질 수 있다. 같은 mixed tree의 resident leaf는 평가일에 영향을 받을 수 있어 전체 정책 상태가 바뀔 수도 있다. 현재 날짜 조회는 어떤 계층에도 새로 추가하지 않는다.

## 9. PolicyReferenceContext 영향

birth-only 트리는 reference_context=None이어도 실행 가능하게 한다. birth evaluator에 신청일/context를 전달하지 않는다. 올바른 policy_id의 유효한 context에서 application_date가 None이거나 바뀌어도 birth leaf는 같다.

**공통 public 검증은 유지한다.** reference_context를 전달했는데 타입이 잘못됐거나 policy_id가 다르면 birth-only 트리여도 기존 ContextValidationError다. birth 분기에서 날짜를 읽지 않는 것과 잘못된 명시적 context를 무시하는 것은 다르다.

트리 어디든 ResidentRegistrationRule이 있으면 기존 preflight대로 reference_context 자체가 필수다. 이를 ANY/NOT로 감싸도 요구가 사라지지 않는다. 유효한 context의 application_date=None은 resident UNKNOWN이며 birth는 독립 실행된다. birth가 PASS라는 이유로 resident의 context 누락 오류를 건너뛰지 않는다.

## 10. facts=None 처리

현재 public 함수의 `facts=None → EvaluationFacts()` 정규화를 그대로 유지한다. 추가된 기본 birth=None이 evaluator에 전달되어 birth leaf UNKNOWN이 된다. 명시적 EvaluationFacts(birth=None), Fact 날짜=None도 동일한 상태/사유/누락 경로이며 provenance 차이는 보존된다.

기존 resident의 빈 tuple 미입력도 그대로다. 단 resident context 자체가 없으면 기존 구조 오류가 먼저 발생한다. 잘못된 facts 객체를 빈 값으로 보정하거나 UserProfile로 대체하지 않는다.

## 11. duplicate rule ID

기존 _validate_unique_nodes는 walk_nodes의 모든 rule_id를 타입과 관계없이 비교한다. birth를 허용 목록에 넣으면 별도 중복 알고리즘 없이 다음 충돌도 거부할 수 있다.

- atomic ↔ birth, resident ↔ birth, birth ↔ birth.
- group ↔ birth 및 중첩 다른 가지의 birth ID 충돌.
- 동일 birth 객체를 같은 트리의 두 위치에 사용해 동일 ID가 두 번 등장한 경우.

ID를 자동 재생성하거나 타입 prefix로 바꾸지 않는다. Policy/RuleGroup 생성 시 PolicyDataError이며 실행 UNKNOWN이 아니다. 현재 컨테이너의 기존 전역 중복 검사도 보존한다. PolicySet의 birth 지원 자체는 3절 경계대로 아직 금지한다.

## 12. RuleGroup validation

children의 정확한 허용 타입 목록에 BirthDateRule만 추가한다. tuple/비어 있지 않음/NOT의 정확히 한 자식/ID 유일성 검증은 유지한다. child list 자동 변환·None child·미등록 타입 허용은 없다.

birth는 root 단독, ALL/ANY/NOT의 자식, 재귀 중첩 그룹 어디에나 구조적으로 놓일 수 있다. 실제 정책에서 어떤 논리로 결합하는지는 공식 조건과 coverage 검토의 책임이다. generic 모델이 birth를 특정 연산자에만 묶지 않는다.

## 13. ALL

기존 진리표 그대로다. 하나라도 FAIL이면 FAIL, 모두 PASS면 PASS, 그 외 UNKNOWN이다.

| resident | birth | ALL |
|---|---|---|
| PASS | PASS | PASS |
| PASS | FAIL | FAIL |
| PASS | UNKNOWN | UNKNOWN |
| FAIL | PASS | FAIL |
| UNKNOWN | PASS | UNKNOWN |

모든 자식을 평가하므로 최종 FAIL/PASS와 별개로 다른 leaf의 UNKNOWN/missing_fields를 보존한다. 오류는 정상 FAIL과 달라 전체 평가를 중단한다. 집계는 상태만 읽고 birth reason을 다시 계산하지 않는다.

## 14. ANY

birth 자식을 구조적으로 허용한다. 하나라도 PASS이면 PASS, 모두 FAIL이면 FAIL, 그 외 UNKNOWN이다. birth 전용 예외는 없다.

예: ANY(atomic FAIL,birth PASS)=PASS, ANY(atomic FAIL,birth FAIL)=FAIL, ANY(atomic FAIL,birth UNKNOWN)=UNKNOWN. 다른 child가 PASS여도 birth UNKNOWN leaf와 누락 경로는 결과에 남는다. 실제 청년기본소득의 출생일 조건을 ANY로 처리하라는 뜻은 아니다.

## 15. NOT

birth 한 자식을 가진 NOT도 허용한다. 기존 PASS→FAIL, FAIL→PASS, UNKNOWN→UNKNOWN을 그대로 사용한다. birth leaf의 실제 상태/사유/근거/details는 바꾸지 않고 group의 상태만 뒤집는다. 두 자식 이상인 NOT은 기존 생성자 오류다. birth 전용 부정 판정 함수를 만들지 않는다.

## 16. error propagation

잘못된 EvaluationFacts.birth는 입력 묶음 생성 단계에서 ProfileValidationError다. profile/policy/context/facts의 잘못된 public 인자, 미지원 node, 중복 ID, 잘못된 reference context는 기존 오류 계층을 따른다.

birth evaluator에서 PolicyDataError/ProfileValidationError/ResultValidationError 등이 발생하면 router가 그대로 전파한다. UNKNOWN으로 감싸거나 해당 leaf를 생략하지 않는다. 참조·근거·다른 child의 오류도 기존 경로를 유지한다. 오류 전파 테스트는 router가 실제 생성하는 유효 입력과 별도로, evaluator를 테스트 대역으로 치환하여 같은 예외 객체가 전파되는지 확인할 수 있다.

정상 미입력 UNKNOWN은 evaluator의 출력이다. router의 미지원 타입/모순 입력/예외 경로와 구별한다. 새 Status나 catch-all fallback은 추가하지 않는다.

## 17. evidence 처리

leaf evidence_refs는 evaluator에서 Rule 그대로 옮기고 router가 수정하지 않는다. 새 SourceRegistry 조회·URL 접근·locator resolve·검증일 갱신은 없다. 정책 evidence_refs와 BirthDateDetails.birth_source의 사용자 provenance 분리를 유지한다.

group/정책 근거는 기존 정렬된 합집합이며 leaf ref 순서·중복은 그대로 보존된다. router 통과는 공식 출처의 존재·최신성·Q3 의미 일치 검증이 아니다. 실제 자료 연결 전에 기존 별도 source/envelope 검증을 수행해야 한다.

## 18. PolicyEvaluation 영향

birth evaluator의 RuleEvaluation은 M1.16D에서 이미 지원하는 형태다. _assemble_policy_result를 그대로 사용해 root 상태, root-first rule_results, 정렬된 reason/missing 합집합, rule_version/context를 보존한다.

별도 birth top-level metadata·serializer·결과 버전을 만들지 않는다. leaf date는 기존 to_dict에서 ISO로 직렬화되고 typed details는 provenance만 담는다. 공개 routing 시그니처와 기존 evaluate_policy/evaluate_policies도 변경하지 않는다. 새로운 public birth_fact= keyword는 없다.

PolicyEvaluation.overall_status는 선택된 현재 부분 트리의 결과다. birth/resident 둘이 PASS여도 미구현 거주이력·등록분류·신청절차까지 통과한 것으로 표시하지 않는다.

## 19. loader와 책임 분리

이번 계약은 메모리에 검증된 객체가 이미 존재하는 경우만 다룬다. router는 JSON key/schema/discriminator/날짜 파싱을 모른다. M1.16G에서 m1.1 parser·PolicyEnvelope loader·자료 파일을 수정하지 않는다.

현재 birth JSON 거부 테스트는 G에서도 그대로 통과해야 한다. H에서 명시적 birth 문법/버전을 결정하고 strict 파싱을 별도 승인한다. PolicySet의 임시 birth 거부 guard도 그때 schema 계약과 함께 재검토한다. 메모리 Policy 지원이 JSON 지원을 암시해서는 안 된다.

## 20. 실제 정책 트리 향후 형태

M1.15 실제 데이터의 root는 주민등록 leaf 하나다. 이번 F와 후속 G에서는 실제 JSON·sources·Envelope를 바꾸지 않는다.

향후 **명시적으로 Q3 대상 Rule을 선택한 뒤**의 부분 트리 후보:

```text
ALL
├─ ResidentRegistrationRule (신청일의 GYEONGGI/ANSAN)
└─ BirthDateRule (선택된 지급 분기의 공식 출생일 구간)
```

더 뒤에는 경기도 연속/합산 거주기간 ANY 등 실제 조건이 추가될 수 있으나 이번에 새로운 ResidenceHistoryRule을 설계·구현하지 않는다.

M1.16I에서 위 구조를 만들 기술적 연결은 가능하지만, 실제 적용 전 **연도 edition 내부의 지급 분기 선택**, 공식 birth locator/문서 확인본, 정책·dataset 버전, coverage를 확정해야 한다. 현재 연간 resident-only 데이터에 Q3 값을 덮어써 연도 전체에 적용하지 않는다. 순수 routing 준비가 실제 분기 모델 문제를 해결했다는 뜻은 아니다.

## 21. 수동 시나리오

아래 **36개는 미래 연결의 수동 기대값이며 신규 실행 테스트가 아니다.** B_P/B_F/B_U는 기존 독립 birth evaluator가 만드는 PASS/FAIL/UNKNOWN, R_P/R_F/R_U는 유효한 resident context 아래의 해당 상태다. atomic도 동일한 A_* 표기를 사용한다. 기본적으로 각 node ID는 유일하다.

| ID | 입력 / 구조 | 예상 결과와 이유 |
|---|---|---|
| BRT01 | root=B_P | PASS, 단일 birth leaf 결과 그대로 |
| BRT02 | root=B_F | FAIL, BEFORE/AFTER 사유 보존 |
| BRT03 | root=B_U | UNKNOWN / BIRTH_DATE_MISSING |
| BRT04 | birth root, facts=None | 빈 EvaluationFacts로 정규화되어 UNKNOWN |
| BRT05 | birth root, EvaluationFacts(birth=None) | UNKNOWN, 명시적 미입력도 동일 |
| BRT06 | age=24, birth 없음 | UNKNOWN, fallback 금지 |
| BRT07 | age=23 또는 25, B_P 사실 | PASS, age 교차검증 없음 |
| BRT08 | ALL(R_P,B_P) | PASS |
| BRT09 | ALL(R_P,B_F) | FAIL |
| BRT10 | ALL(R_P,B_U) | UNKNOWN, birth.birth_date 누락 보존 |
| BRT11 | ALL(R_F,B_P) | FAIL |
| BRT12 | ALL(R_U,B_P) | UNKNOWN, resident 누락 보존 |
| BRT13 | ANY(A_F,B_P) | PASS |
| BRT14 | ANY(A_F,B_F) | FAIL |
| BRT15 | ANY(A_F,B_U) | UNKNOWN |
| BRT16 | NOT(B_P) | group FAIL, leaf PASS/사유는 그대로 |
| BRT17 | NOT(B_F) | group PASS, leaf FAIL/사유는 그대로 |
| BRT18 | NOT(B_U) | group UNKNOWN, 누락 경로 유지 |
| BRT19 | atomic와 birth의 같은 rule_id | 생성 시 Data Error, 타입이 달라도 중복 |
| BRT20 | resident와 birth의 같은 rule_id | 생성 시 Data Error |
| BRT21 | ALL(A_P,ANY(B_U,R_P)) | root PASS지만 birth UNKNOWN/missing_fields는 보존. root-first 순서 유지 |
| BRT22 | birth에 ref 여러 개/중복/순서 지정 | leaf 결과가 그대로 보존. group만 기존 합집합 규칙 사용 |
| BRT23 | birth-only, reference_context=None | 정상 birth 평가. 필수 신청일 없음 |
| BRT24 | 고정 birth Rule/Fact, 평가일 변경 | birth leaf 동일, 상위 context 표현은 달라질 수 있음 |
| BRT25 | 미지원 node 객체 | 생성자 또는 최종 dispatch Data Error. UNKNOWN 금지 |
| BRT26 | birth evaluator 테스트 대역이 오류 발생 | 동일 오류 전파. 정상 상태로 대체 안 함 |
| BRT27 | EvaluationFacts.birth에 dict/list/tuple/str | 생성 시 ProfileValidationError |
| BRT28 | birth 날짜=None, OFFICIAL_DATA | UNKNOWN이지만 details에 source 보존 |
| BRT29 | ALL(resident,birth), reference_context=None | 공통 preflight ContextValidationError. birth PASS로 우회 안 함 |
| BRT30 | ALL(resident,birth), 유효 context의 application_date=None, B_P | resident UNKNOWN + birth PASS → ALL UNKNOWN |
| BRT31 | birth-only에 다른 policy_id의 reference_context 전달 | ContextValidationError. 불필요한 context라도 잘못된 명시값은 거부 |
| BRT32 | group와 birth 또는 두 birth의 ID 충돌 | 기존 전체 순회 중복 검증 Data Error |
| BRT33 | EvaluationFacts() / resident-only 기존 생성·to_dict | 생성 의미와 기존 출력 유지. birth None은 키 생략 |
| BRT34 | birth 객체를 기존 evaluate_policy 경로로 평가 | 기존 specialized 미지원 PolicyDataError 유지 |
| BRT35 | birth 포함 PolicySet(m1.0 또는 m1.1) | G에서는 명시적 Data Error. JSON/컨테이너 지원은 H에서 별도 결정 |
| BRT36 | birth JSON을 기존 m1.1 parser에 전달 | 기존 미지원 rule_type Data Error 유지 |

신청일이 유효한 다른 값으로 바뀌어도 고정 birth leaf는 동일하다. mixed tree의 resident/전체 상태 변화와 혼동하지 않는다. 순수 객체·반복 결과/직렬화의 동등성과 기존 주민등록/atomic golden 결과 회귀도 후속 구현 테스트에서 확인한다.

## 22. 구현 변경 예상 목록

후속 **M1.16G**의 최소 범위이며 이번에는 모두 미구현이다.

| 파일 / 영역 | 필요한 변경 |
|---|---|
| models.py | BirthDateRule import, RuleNode/root/children 허용 타입 추가. 기존 walk/중복 알고리즘 유지. PolicySet의 birth 조기 유입 guard |
| evaluation_inputs.py | 기존 resident 뒤에 keyword-only birth=None, exact 타입 검증, None 생략 to_dict 호환 |
| routing.py | evaluator/타입 import, birth 분기 하나. 기존 atomic/resident/group 본문·공통 validation 유지 |
| root 공개 export | 필요 시 BirthDateRule 공개만 추가. 기존 evaluator export 유지 |
| 신규 모델/routing 테스트 | 21절 기대값, 입력 불변성, 호출 인자/반환 객체, 오류 전파, 기존 결과 회귀 |
| 기존 테스트 중 의도적 확장 기대 3개 | 아래 항목의 정확한 범위만 후속 승인하에 갱신 |
| 문서 | 실제 구현 범위·테스트 예외·미구현 loader/actual 자료 상태 기록 |

### 후속 기존 테스트 기대값의 명시적 변경 필요

현 테스트를 그대로 유지하면서 타입/필드를 실제 추가하는 것은 아래 세 assertion과 충돌한다. **F에서는 수정하지 않는다. G 구현 지시에서 이 세 테스트의 해당 기대값 갱신을 명시적으로 승인받아야 한다.** 타입을 숨기는 편법이나 별도 opt-in 모델을 만들지 않는다.

| 기존 테스트 함수 | 후속으로 바꿔야 할 기대 범위 |
|---|---|
| tests/test_birth_date_rule.py::test_birth_rule_is_not_registered_as_rule_node_or_policy_root | 임시 미편입 거부를 BirthDateRule union/root/child 허용으로 갱신 |
| tests/test_rule_routing_models.py::test_union_and_recursive_annotations_match_runtime_types | 유한 union의 정확한 타입 집합에 BirthDateRule 추가. 재귀 주석 일치 검증은 유지 |
| tests/test_rule_routing_models.py::test_empty_evaluation_facts_has_no_region_fallback | reflection의 정확한 필드 집합에 birth 추가. 기본값 None·기존 출력·region fallback 없음은 유지 |

다른 기존 기대값/합성 fixture는 유지한다. 특히 현재 m1.1 birth JSON 거부 테스트는 변경하지 않는다. 후속 구현에서 추가 충돌이 발견되면 해당 범위를 먼저 보고한다. 이번 문서 승인이 기존 테스트를 이미 변경했다는 뜻은 아니다.

G에서 하지 않을 것: loader/schema/JSON 예시 파일, 실제 sources/PolicyEnvelope/정책 데이터, evaluator/결과 모델/집계 알고리즘 재작성, birth Resolver/Adapter, 분기 선택·거주이력·API/UI/금융/AI. **H는 loader 지원 검토**, **실제 Q3 자료는 그 이후 별도 단계**로 유지한다.

## 23. 미해결 문제 / Assumptions

| 항목 | 상태 / 경계 |
|---|---|
| Assumption A1 | 한 EvaluationFacts는 동일 사용자 한 명의 요청 단위 값. 여러 사용자의 Fact를 혼합하지 않음 |
| Assumption A2 | BirthDateRule의 지급 분기/공식 범위는 호출 전에 명시적으로 선택됨. router가 추정하지 않음 |
| Assumption A3 | generic ANY/NOT 구조 테스트는 실제 청년기본소득의 자격 논리를 새로 정하는 행위가 아님 |
| 확정 추천 | 유한 exact 타입 편입, 단일 keyword-only birth=None, evaluator 직접 dispatch, 기존 API/집계 유지 |
| 다음 구현의 테스트 예외 | 22절 세 함수의 해당 확장 기대값 갱신 승인 필요. 이번 2,093개 기대값은 불변 |
| JSON 버전 | m1.1 확장 또는 새 버전 선택은 H에서 별도 결정. G에서는 parser 무변경·기존 PolicySet birth 차단 |
| 연간 edition의 분기 선택 | 실제 Q3 자료 등록 전에 해결해야 함. 순수 메모리 routing 구현 자체는 가능 |
| 실제 근거 / 버전 / coverage | 새 locator와 확인본/정책 버전 및 제외 조건을 별도 발행해야 함. 현재 자료 덮어쓰기 금지 |
| 외부 provenance 인증 | 단일 BirthSource는 표식이며 신원 인증·행정자료 진위 보증이 아님 |

위 미결정 사항을 숨긴 자동 분기·나이 fallback·schema 추정은 없다. 현재 routing 구조와 충돌하는 설계는 발견하지 않았다. 필요한 모델 확장은 여기서 특정했으며 별도 framework가 필요하지 않다.

## 24. 최종 판단

**READY_TO_IMPLEMENT_BIRTH_ROUTING**

RuleNode/입력 묶음/정확한 dispatch/시점 독립성/기존 preflight/미입력과 오류/집계/근거/호환성/후속 테스트 변경 범위를 정의했다. 결과 모델과 evaluator는 이미 구현돼 있으므로 새 판정 로직을 만들 필요가 없다. 이번 문서가 routing 구현 완료나 실제 정책 전체 판정 준비를 뜻하지는 않는다.

**다음 가장 작은 작업 1개:** M1.16G에서 이 계약의 메모리 모델·EvaluationFacts.birth·birth dispatch·관련 테스트만 구현한다. 22절의 기존 테스트 세 함수에 대한 확장 기대값 갱신을 명시적으로 승인한 뒤 진행하며, loader/실제 데이터는 포함하지 않는다.

### 이번 M1.16F 검증 기록

작업 전 전체 pytest: **2,093 passed in 6.64s**. 신규 실행 테스트는 없으며 21절은 수동 기대표다. 작성 후 기존 backend/tests/data/docs **75개 전부의 SHA256이 동일**함을 확인했다. 추가 파일은 이 문서 하나이며 기존 코드·테스트·실제/합성 자료·기존 문서는 변경하지 않았다.

필수 24개 절과 BRT01~BRT36의 순서·중복·누락 및 문서 언어를 확인했다. Git 저장소가 아니므로 git diff 대신 파일 해시를 사용했다. 적용되는 AGENTS.md는 발견되지 않았다. 이 검증은 routing 구현이나 신규 동작 테스트의 완료를 뜻하지 않는다.

## 25. M1.16G — IMPLEMENTED: 메모리 mixed tree의 birth 연결

RuleNode/root/children에 정확한 BirthDateRule을 추가하고 EvaluationFacts에 keyword-only birth=None을 추가했다. 기존 router의 atomic/resident/group 본문은 유지하고 다음 분기만 추가했다.

```text
BirthDateRule → evaluate_birth_date_rule(node, facts.birth) → 반환 객체 그대로 tuple에 보존
```

공개 evaluate_policy_tree API는 그대로다. birth 전용 추가 인자·비교·reason 선택·context 전달·age fallback·source 조회는 없다. birth evaluator와 결과 모델도 수정하지 않았다. 기존 walk_nodes/_validate_unique_nodes가 새 leaf도 방문하므로 별도 ID 알고리즘 없이 atomic/resident/birth/group 간 중복을 거부한다.

EvaluationFacts는 기존 resident positional 인자와 frozen/slots 전략을 유지한다. birth에는 정확한 BirthFact 또는 None만 허용하고 다른 객체는 ProfileValidationError다. to_dict는 birth=None일 때 기존 형태를 유지하며 Fact가 있으면 날짜 None 여부와 무관하게 birth 키로 provenance를 보존한다. 입력 dict 자동 변환이나 collection 수용은 없다.

birth-only는 reference_context 없이 실행된다. 기존 공통 profile/context/facts/reference 타입·policy_id 검증은 유지하며 resident가 포함되면 기존 reference context preflight도 유지된다. 평가일·신청일은 birth에 전달하지 않고 상위 PolicyEvaluation의 context는 그대로 기록한다.

ALL/ANY/NOT과 결과 조립·serializer는 수정하지 않았다. root-first 순서와 정렬된 reason/missing/근거 합집합, 각 leaf의 원본 evidence 순서/중복을 유지한다. ANY의 다른 child가 PASS여도 evaluator 오류를 UNKNOWN으로 바꾸지 않고 전파한다.

3절 계약에 따라 birth 포함 PolicySet은 m1.0/m1.1 모두 명시적으로 거부한다. 기존 legacy evaluate_policy도 specialized birth를 거부한다. m1.1 parser 및 모든 loader는 그대로이며 birth JSON은 계속 미지원이다. PolicyEnvelope 모델·실제 resident slice·sources/data/releases도 수정하지 않았다. 메모리 Policy 지원을 실제 Q3 정책 발행으로 표현하지 않는다.

### 승인된 기존 테스트 세 함수의 갱신

사용자가 이번 M1.16G 지시에서 아래 정확한 세 함수의 확장 기대값 갱신을 승인했다. 테스트를 삭제하지 않았고 기존 atomic/resident/group 및 loader 거부 기대는 유지했다. 첫 함수의 역사적 이름은 변경 범위 추적을 위해 유지하고 본문에 승인 이유를 명시했다.

| 함수 | 이전 기대 | 새로운 기대 / 이유 |
|---|---|---|
| test_birth_rule_is_not_registered_as_rule_node_or_policy_root | birth는 union/root/child 모두 거부 | union 포함, Policy root와 RuleGroup child에 같은 객체 보존. M1.16B의 임시 미편입 상태가 이번 기능으로 종료 |
| test_union_and_recursive_annotations_match_runtime_types | 정확한 union은 atomic/resident/group 세 종류 | birth를 추가한 네 종류. 재귀 annotation 일치 검사와 기존 세 종류는 유지 |
| test_empty_evaluation_facts_has_no_region_fallback | dataclasses.fields는 resident 필드 하나 | birth 필드 추가 및 기본 None 확인. 기존 region fallback 없음·빈 resident·to_dict 기대는 유지 |

세 함수는 22절 표의 기존 파일에 있다. 두 테스트 파일을 AST로 비교하여 **이 세 함수 외의 코드가 모두 동일**함을 확인했다. m1.1 birth JSON 거부 테스트는 그대로이며 신규 회귀 사례로도 확인했다. 따라서 기존 2,093개 기대값이 전부 불변이라고 보고하지 않는다. 기존 2,090개 기대를 유지하고 승인된 3개를 갱신한 것이다.

### 실행 검증

신규 tests/test_birth_routing.py는 **67개** 사례다. 합성 hand-built 객체만 사용하며 JSON fixture를 추가하지 않았다.

- birth PASS/BEFORE FAIL/AFTER FAIL/두 UNKNOWN, age fallback 없음, 평가일·신청일 비의존성.
- resident/birth ALL의 PP→P, PF→F, PU→U, FP→F, UP→U 및 atomic/birth ALL/ANY 18개 상태 조합.
- birth의 NOT P→F/F→P/U→U, 중첩 mixed tree의 전위 순서·누락·근거 합집합·직렬화·결정성·입력 불변성.
- ID 중복 5종, facts 생성·잘못된 birth 타입·keyword-only·기존 positional/to_dict·불변성.
- 잘못된 reference context/기존 resident preflight, 실제 evaluator의 node/fact 전달과 반환 객체 identity 보존.
- 예외 세 종류의 동일 객체 전파, 미지원 node/legacy 경로/PolicySet 차단, m1.1 birth JSON 계속 거부.

작업 전 전체 pytest: **2,093 passed in 7.51s**. 최종 전체: **2,160 passed in 8.69s**. 기존 resident exact-date/future/no-fact/conflict/evidence와 atomic golden 테스트도 함께 통과했다.

IMPLEMENTED: Birth RuleNode/Policy root/RuleGroup child, EvaluationFacts.birth, birth dispatch, 기존 mixed aggregation 경로 실행.

NOT IMPLEMENTED: JSON loader support, birth JSON syntax, actual Q3 policy/source/locator/Envelope, quarter selection, 거주이력. 원문 근거·분기·coverage 문제를 임의로 해결하지 않았다.

최종 판단: **READY_FOR_BIRTH_RULE_LOADER**. 다음 가장 작은 작업 1개는 **BirthDateRule의 strict JSON 입력 문법/버전 및 PolicySet guard 전환 계약을 문서로 확정**하는 것이다. 기존 m1.0/m1.1 호환성·미지원 값 거부를 먼저 정하고 실제 Q3 데이터는 별도로 둔다.

### 파일 무결성 확인

기존 backend/tests/data/docs **76개**의 SHA256 기준선과 비교했다. 모델/평가 입력/router/root export 4개, 승인된 테스트 두 파일, 문서 4개만 변경됐고 나머지 **66개는 동일**하다. 신규 파일은 tests/test_birth_routing.py 하나다. 기존 테스트 두 파일은 승인된 세 함수만 제외한 AST의 해시가 각각 기준선과 동일하다. 기존 evaluator/결과 타입/Resolver/Adapter/loader/실제·합성 데이터는 그대로다. Git 저장소가 아니므로 파일 해시를 사용했으며 적용되는 AGENTS.md는 발견되지 않았다.
