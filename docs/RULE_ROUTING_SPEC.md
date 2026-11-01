# 주민등록 leaf의 최소 Rule Routing 계약 — M1.6F

작성일: 2026-10-20. **M1.6F 설계 기록**. 모델은 21절, 단일 Policy routing은 22절, **M1.7 m1.1 Loader는 23절**을 우선한다. 실제 routing entrypoint는 22절이며 초기 인자 후보와 구분한다. 실제 정책 JSON은 미구현이다.

최신 구현 기준은 RESOLVER_RULE_ADAPTER_SPEC.md 20~21절, RESIDENT_REGISTRATION_FACT_SPEC.md 17~18절이다. POLICY_RULE_SPEC/DATA_MODEL/ARCHITECTURE 및 models/evaluator/loader/resolver/adapter/result_types 코드를 다시 확인했다. POLICY_RULE_SPEC 4절의 ‘Adapter도 아직 없다’는 문장은 M1.6D 당시 기록이며 현재 M1.6E Adapter가 구현돼 있다. 이번에는 기존 문서를 수정하지 않고 이 상태 차이를 기록한다.

## 1. 목적

정책 요구를 표현하는 주민등록 leaf 하나를 기존 원자 규칙·그룹 트리에 추가하고, 전용 Resolver → Adapter 결과가 기존 집계에 참여하는 최소 경계를 정한다.

정책 자격 판단은 Python에 둔다. 주민등록 결과는 해당 조건 하나의 충족 여부이며 정책 전체의 신청/수급 확정이 아니다. 정책 원문·소득 기준·개인정보 원칙이나 승인된 Resolver 의미를 변경하지 않는다. 실제 정책 JSON·미래 Fact·UI/API/LLM은 설계 범위에 포함하지 않는다.

## 2. 현재 엔진 구조

| 영역 | 확인한 현재 동작 |
|---|---|
| Python | 3.12.14. frozen/slots dataclass와 tuple 사용 |
| PolicyRule | 등록 Field 및 eq/in/gte/lte만 표현. 기존 원자 클래스의 실제 이름 |
| RuleGroup | children은 정확한 PolicyRule/RuleGroup만 허용. ALL/ANY 최소 1개, NOT 정확히 1개 |
| RuleNode / Policy.root | PolicyRule 또는 RuleGroup만 허용 |
| 노드 검증 | walk_nodes로 그룹을 순회, 정책/데이터셋 rule_id 유일성 검증 |
| evaluator | PolicyRule이면 원자, 그 외에는 그룹이라고 가정. 미지원 타입을 명시적으로 거부하는 분기 필요 |
| aggregation | _aggregate는 Status만 사용. root-first 결과, 모든 자식 평가, 전체 누락/근거 합집합 |
| loader | kind=rule/group으로 구분. 엄격한 키/타입 검증. schema_version=m1.0, synthetic/test_only=True만 허용 |
| Context | EvaluationContext.as_of는 명시적 평가일. application_date 없음 |
| 주민등록 Resolver | 완전한 요구 지역·명시적 평가일/기준일·facts를 받아 판정. 전체 후보의 같은 날짜 충돌을 먼저 거부 |
| Adapter | 기존 Resolution을 상태/사유/근거 손실 없이 RuleEvaluation으로 변환. 재판정·Resolver 호출 없음 |

현재 `_node`, RuleGroup/Policy 생성자, `_evaluate_node`에 새 객체를 그냥 전달하면 작동하지 않는다. 결과 타입과 Adapter가 준비됐다는 사실이 트리 연결 구현을 대신하지 않는다.

## 3. 필요한 확장

1. 정책 요구 전용 ResidentRegistrationRule을 추가한다.
2. RuleNode/RuleGroup.children/Policy.root의 유한 허용 타입 및 재귀 검증을 넓힌다.
3. 프로필 밖 typed facts와 정책별 신청 기준일 context를 전달한다.
4. 노드 타입별 명시적 evaluator dispatch를 추가한다.
5. 주민등록 분기에서 기존 Resolver를 호출한 뒤 기존 Adapter를 호출한다.
6. 그룹 결과와 PolicyEvaluation 조립은 기존 알고리즘을 유지한다.
7. JSON 연결은 별도 승인 단계에서 엄격한 버전별 구분을 추가한다.

순서상 **모델/순회 검증 → 메모리 내 routing → JSON loader**로 나눌 수 있다. 첫 routing 구현이 실제 정책 데이터 로딩을 요구하지 않는다.

## 4. A/B/C 설계 비교

| 설계 | 장점 | 단점 | 판단 |
|---|---|---|---|
| A. PolicyRule 하나에 rule_type과 선택 필드 추가 | 한 클래스로 분기, 표면적 파일 수가 적음 | field/operator/value와 required_region/binding의 잘못된 조합 증가. 기존 생성자/loader 검증이 커지고 미래 종류마다 optional 필드 누적 | 채택하지 않음 |
| B. 별도 specialized 타입 + 유한 union | 타입별 필수 필드 명확. 기존 원자 생성자 유지. 그룹은 결과 Status만 알면 됨 | 허용 타입·순회·loader·dispatch를 함께 갱신해야 함 | **추천** |
| C. 기존 Rule + 외부 registry | 새 매핑 추가가 쉬워 보임 | operator/name 문자열로 숨은 실행 의미가 생김. 데이터 오류가 늦게 드러나고 JSON에서 사실/날짜 의미가 불명확. 동적 확장 프레임워크 비용 | 채택하지 않음 |

B의 loader 변경은 새 종류를 명시적으로 읽는 범위다. 기존 원자 JSON을 전면 변환할 필요가 없다. 내부 dispatch는 문자열 registry나 동적 import 대신 정확한 타입 분기를 쓴다.

## 5. 최종 추천 Rule 타입 구조

문서상 ‘AtomicPolicyRule’은 **기존 PolicyRule을 가리키는 개념명**이다. 기존 클래스명을 바꾸거나 새 중복 원자 클래스를 만들지 않는다. 별도 alias도 필수 사항이 아니다.

```text
RuleNode = PolicyRule | ResidentRegistrationRule | RuleGroup
RuleGroup.children = tuple[RuleNode, ...]
Policy.root = RuleNode
```

Python 3.12와 현재 future annotations를 유지한다. RuleGroup의 children annotation은 전방 RuleNode를 참조하고, 런타임 union은 세 클래스가 정의된 뒤 만들 수 있다. 생성자 허용 타입도 세 종류를 명시한다. annotation만 넓히고 검증을 그대로 두면 안 된다.

ResidentRegistrationRule은 models를 역으로 import하지 않는 작은 specialized 모듈에 둔다. RegionRef·ReferenceDateSource·오류 타입만 의존하고 Status/evaluator/Resolver 결과는 의존하지 않는다. models는 해당 leaf 타입을 import할 수 있다. `walk_nodes`는 RuleGroup에서만 재귀하며 모든 leaf를 yield한다. 주민등록 root도 허용한다. ID 중복 검사는 기존 방식으로 원자·주민등록·그룹 전체에 적용한다.

Birth/History 등 미지원 객체는 아직 union 구성원이 아니다. 미래 규칙을 알아서 UNKNOWN 처리하거나 children에서 생략하지 않는다.

## 6. ResidentRegistrationRule 계약

| 필드 | 타입과 검증 |
|---|---|
| rule_id | 기존 정책 규칙과 동일한 비어 있지 않은 str. 트리/데이터셋 전체 유일 |
| required_region | 완전하고 유효한 RegionRef 필수. None/부분 지역/str/dict 객체는 domain 입력 오류 |
| reference_date_source | 기존 ReferenceDateSource Enum. 현재 APPLICATION_DATE만 허용 |
| evidence_refs | 비어 있지 않은 str의 tuple, 최소 1개. 정책 요구조건의 근거 참조 |

frozen/slots를 사용한다. 추가 필드는 필요하지 않다. rule_type 문자열은 내부 필수 저장값으로 중복하지 않아도 된다. 별도 클래스가 이미 종류를 식별한다. JSON에서는 14절의 discriminator를 쓴다.

사용자 facts, profile, application_date 실제 값, Resolver/Adapter 결과, source, 계산 상태를 Rule에 넣지 않는다. 실제 지역 판정은 하지 않는다. 잘못된 정책 구성은 PolicyDataError다. 직접 생성과 loader 경로 모두 검증해야 하며 하위 RegionRef 오류를 정책 입력 오류로 분류할 때 원인/필드 정보를 유지한다.

Rule은 RegionRef, 결과 Condition은 RegionSnapshot을 사용한다. routing이 요구 지역 두 키를 snapshot으로 옮겨 `ResidentRegistrationCondition`을 구성한다. 이는 자격 비교가 아닌 표현 변환이며 공식 행정코드 변환은 없다.

## 7. reference_date_source 계약

| 후보 | 평가 | 이번 선택 |
|---|---|---|
| FIXED_DATE | 명시적 고정 기준일 정책에 의미가 있으나 날짜 필드와 검증이 추가로 필요 | 현재 미지원 |
| EVALUATION_DATE | 평가 시점 조건에는 가능하나 신청일 요구를 대신할 수 없음 | 현재 미지원 |
| APPLICATION_DATE | 정책별 context의 신청 기준일을 명시적으로 바인딩 | **지원할 유일한 종류** |
| 임의 context key/표현식 | 여러 날짜를 동적으로 선택할 수 있으나 문자열 오타·키 누락·표현식 평가 위험과 과도한 일반화 | 현재 미지원 |

현재 ReferenceDateSource.APPLICATION_DATE를 그대로 사용한다. 미등록 값이나 바인딩 종류 부재는 PolicyDataError다. 과거 설계 이름 APPLICATION_REFERENCE_DATE를 alias로 받아들이지 않는다.

바인딩은 `PolicyReferenceContext.application_date`를 선택하는 명시적 단일 분기다. 시스템 오늘, context.as_of, 신청기간 시작일/종료일에서 값이 없다고 채우지 않는다. reference_date가 평가일 이후인지 여부 등 날짜 판정은 기존 Resolver에만 맡긴다.

## 8. Evaluation Context 계약

### 8.1 기존 평가 context 보존

EvaluationContext의 필드·생성자·의미는 유지한다. `context.as_of → resolver.evaluation_date`로 직접 전달한다. 새로운 evaluation_date 필드를 만들거나 as_of를 신청일로 재해석하지 않는다.

추가할 작은 불변 context 후보는 하나다.

```text
PolicyReferenceContext
  policy_id: 비어 있지 않은 str
  application_date: date | None = None
```

정확한 date만 허용하며 datetime/str/bool/숫자는 ContextValidationError다. 사용자 신청 기준일을 모르면 **유효한 context의 application_date=None**으로 표현한다. 실제 접수 완료를 증명하는 모델은 아니다.

### 8.2 최소 호출 계약 — 미구현 API 제안

기존 세 positional 인자는 유지하고 새 입력만 keyword-only로 추가한다.

```text
evaluate_policy(profile, policy, context, *, facts=None, reference_context=None)
evaluate_policies(profile, policy_set, context, *, facts=None, reference_contexts=())
```

- 기존 원자/그룹만 있는 호출은 새 인자 없이 동일하게 동작한다.
- 주민등록 leaf가 있으면 policy_id가 같은 PolicyReferenceContext를 명시적으로 제공해야 한다.
- 주민등록 평가에서 reference_context 자체가 None이면 **ContextValidationError**다. 호출자가 바인딩 context를 만들지 않은 오류와 사용자 날짜 미입력을 구분한다. context를 자동 생성해 이 오류를 UNKNOWN으로 덮지 않는다.
- 유효한 context에 application_date=None이면 Resolver가 RESIDENT_REFERENCE_DATE_MISSING / UNKNOWN을 반환한다. 같은 요청에 충돌 facts가 있으면 기존 Resolver 순서에 따라 충돌 오류가 먼저다.
- context가 제공됐다면 atomic-only 정책이라도 타입/정책 ID 일치를 검증한다. 유효한 application_date=None은 atomic 조건에 누락 항목을 추가하지 않는다.
- 배치 reference_contexts는 PolicyReferenceContext tuple이다. 각 policy_id는 유일하고 대상 데이터셋에 존재해야 한다. 잘못된 타입/list, 중복/타 정책 ID는 ContextValidationError다. 각 주민등록 정책에는 정확히 하나가 필요하다. atomic-only 정책 context는 선택이다.
- 배치는 먼저 데이터셋 버전과 context 집합의 구조/필수 바인딩을 검증한다. 각 정책에는 자신의 context만 전달한다. 한 정책 날짜를 다른 정책에 전역 재사용하지 않는다. 내부 검색용 dict[str, PolicyReferenceContext]는 가능하나 외부의 임의 context bag을 허용하지 않는다.

반환된 Resolution의 evaluation_date/reference_date가 방금 전달한 두 날짜와 같은지 routing 경계에서 확인한다. 어긋나면 기존 ResultValidationError를 사용하고 code는 각각 RESOLUTION_EVALUATION_DATE_MISMATCH / RESOLUTION_REFERENCE_DATE_MISMATCH, field는 evaluation_date / reference_date로 제안한다. 이 두 코드는 아직 구현에 등록하지 않았다. Adapter를 호출해 덮어쓰지 않는다. 이 검사는 원본의 시간 관점이 결과에서 소실되기 전 연결 정합성 확인이다. 날짜의 충족 여부를 재판정하는 검사가 아니다. 상위 PolicyEvaluation.context에는 동일한 평가 context가 남는다.

**Assumption:** 첫 context는 정책당 신청 기준일 하나만 필요하다. 향후 한 정책에서 서로 다른 실제 신청일을 동시에 요구하면 별도 설계를 해야 한다. 지금 임의 context-key 계층을 만들지 않는다.

## 9. Fact 전달 계약

### 9.1 비교

| 방식 | 타입 안전성·개인정보 | 확장/테스트 | 판단 |
|---|---|---|---|
| A. UserProfile에 specialized facts 추가 | 이미 경제정보를 가진 모델의 역할이 커짐. 오래된 region과 혼동 가능 | profile parser 영향, 단일 leaf 테스트에 불필요한 입력 증가 | 현재 보류 |
| B. 별도 EvaluationFacts | 필요한 종류만 명시적 tuple로 전달. 원본 profile과 분리 | 직접 순수 함수 테스트 가능. 실제 다음 Fact 승인 시 필드 추가 가능 | **추천** |
| C. facts_by_type mapping | 유한 typed mapping이면 가능하나 dict[str, Any]는 키/값 실수와 미등록 종류를 허용하기 쉬움 | registry와 함께 범용 프레임워크로 커질 위험 | 채택하지 않음 |

최소 객체 후보:

```text
EvaluationFacts
  resident_registrations: tuple[ResidentRegistrationFact, ...] = ()
```

frozen/slots. tuple과 정확한 Fact 타입을 검증한다. list/dict/generator/None을 resident_registrations 필드에 직접 넣으면 ProfileValidationError다. 개별 Fact의 날짜/source/지역 오류는 기존 ResidentRegistrationValidationError를 유지한다.

공개 evaluator의 facts=None은 기존 호출과 호환하기 위한 **전체 입력 생략 표기**이며 빈 EvaluationFacts로 정규화한다. 이는 잘못된 필드 값 None을 허용한다는 뜻이 아니다. 주민등록 leaf에 전달할 facts가 없으면 빈 tuple로 Resolver를 호출한다. 날짜 context가 유효하면 정상 UNKNOWN이다. context 오류와 함께 있으면 8절의 호출 오류가 먼저다.

요청의 사실 묶음은 동일 사용자의 자료라는 전제다. 프로필 ID 연결·저장소·계좌·문서 원본을 추가하지 않는다. 주민등록 branch는 UserProfile.region을 읽지 않는다. atomic region 규칙은 기존 str 비교를 계속 사용한다. 서로 다른 두 의미를 자동 동기화하지 않는다.

EvaluationFacts는 전체 후보의 구조만 검증하고 새로운 충돌 해결을 하지 않는다. 같은 날짜 충돌은 주민등록 Resolver 책임이다. 따라서 주민등록 leaf가 없는 atomic-only 평가에서는 이 Resolver를 호출하지 않으며 사용하지 않는 facts의 의미적 충돌 검사를 새로 수행하지 않는다. 주민등록 leaf가 하나라도 있으면 해당 종류의 **전체 tuple**을 그대로 전달해 기준일 밖 충돌도 기존대로 거부한다. 날짜별 사전 필터링이나 출처 순위 선택은 금지한다.

## 10. evaluator routing 흐름

세 가지 정확한 노드 타입으로 분기한다. 현재 ‘원자가 아니면 무조건 그룹’이라는 마지막 else를 제거하고 미지원 타입을 PolicyDataError로 거부해야 한다.

```text
PolicyRule:
  기존 _evaluate_atom(profile, rule)
  → RuleEvaluation 1개

ResidentRegistrationRule:
  해당 policy reference_context 확인
  APPLICATION_DATE → context.application_date
  facts.resident_registrations 전체 tuple
  resolve_resident_registration(
    required_region=rule.required_region,
    reference_date=application_date,
    evaluation_date=evaluation_context.as_of
  )
  → 반환 날짜와 전달 날짜의 연결 정합성 확인
  → 기존 Adapter 호출
  → RuleEvaluation 1개

RuleGroup:
  children을 입력 순서대로 같은 요청 입력과 함께 재귀 평가
  → 기존 root-first flatten + aggregation

그 외:
  PolicyDataError
```

직접 만든 임의 Resolution을 주입받아 정책을 평가하는 별도 공개 경로는 만들지 않는다. routing이 Resolver를 직접 호출하고 바로 Adapter로 전달한다. Resolver나 Adapter를 캐시/우회/재작성하지 않는다. 한 정책 안의 여러 주민등록 leaf는 각자의 요구 지역에 같은 facts와 해당 정책 신청일을 사용한다. 별도 registry·plugin·동적 import·eval은 없다.

구조/context 검증 후 노드를 입력 순서대로 평가하고 오류가 발생하면 즉시 예외를 전파한다. 모든 정상 자식을 평가한다는 뜻은 오류가 난 뒤에도 계속 평가해 오류 목록을 수집한다는 뜻이 아니다. 여러 오류의 전역 수집 체계는 만들지 않는다.

## 11. Adapter 호출 위치

주민등록 branch 내부에서만, Resolver의 정상 반환 뒤 호출한다.

```text
rule_id          ← rule.rule_id
resolution       ← 방금 반환한 ResidentRegistrationResolution
policy_condition ← ResidentRegistrationCondition(
                     RegionSnapshot(rule.required_region의 두 키),
                     rule.reference_date_source)
evidence_refs    ← rule.evidence_refs
```

Adapter는 기존 함수 그대로 쓴다. 관찰값을 재비교하거나 missing_fields를 다시 추론하지 않는다. 상태·사유·선택 evidence 순서를 보존한다. 날짜 의미는 APPLICATION_DATE, 실제 값은 Resolution.reference_date이며 상위 평가일과 구분한다.

Resolver 예외면 Adapter에 전달할 결과가 없다. 오류 객체를 Adapter 입력으로 넘기거나 예외를 잡아 UNKNOWN Resolution을 만들어내지 않는다. Adapter가 내는 ResultValidationError도 정상 leaf 결과로 변환하지 않는다.

## 12. aggregation과의 관계

**_aggregate의 구현과 진리표는 변경하지 않는다.** 입력은 여전히 자식 subtree 첫 결과의 Status tuple이다. 원자/주민등록 구분·날짜·출처를 집계기가 알 필요가 없다.

| 자식 상태 | ALL | ANY |
|---|---|---|
| P,P | P | P |
| P,F | F | P |
| P,U | U | P |
| F,P | F | P |
| F,F | F | F |
| F,U | F | U |
| U,P | U | P |
| U,F | F | U |
| U,U | U | U |

NOT은 P→F, F→P, U→U다. NOT에서 부모 결과만 반전하고 주민등록 leaf의 원래 상태/사유/details를 바꾸지 않는다.

root-first 순서, children 순서, 그룹 reason(ALL_*/ANY_*/NOT_*), 그룹 missing_fields/evidence_refs 합집합, 정책 reason_codes 합집합도 유지한다. leaf details를 그룹에 복사하지 않는다. leaf 결과가 사유/근거의 설명 단위다. 기존 사유와 주민등록 사유가 같은 PolicyEvaluation에 공존하는 것은 이미 M1.6D에서 지원한다.

정상 값에 대한 ANY PASS가 뒤의 데이터 오류를 가리지 않는다. 모든 자식을 평가하므로 ANY(atomic PASS, resident conflict)는 오류다. 마찬가지로 ALL의 선행 FAIL도 뒤 오류를 숨기지 않는다.

## 13. Data Error 계약

| 상황 | 처리 |
|---|---|
| 잘못된 specialized rule, 미지원 노드/바인딩, 정책 요구 지역 오류 | PolicyDataError |
| context 없음(주민등록 평가), 정책 ID 불일치, context 날짜 타입/배치 중복 오류 | ContextValidationError |
| 유효한 context에 application_date=None | 정상 UNKNOWN / RESIDENT_REFERENCE_DATE_MISSING, 단 기존 Resolver 오류 우선순위 유지 |
| facts 생략/빈 tuple | 빈 사실로 정상 Resolver 호출, 조건에 맞는 원인별 UNKNOWN |
| EvaluationFacts 구조 오류 | ProfileValidationError |
| 개별 Fact 오류·충돌 | 기존 ResidentRegistrationValidationError 전파 |
| Resolver 반환 날짜가 전달값과 불일치 | 연결 계약 오류(ResultValidationError 계열), 정상 결과 없음 |
| Adapter 입력/출력 구조 계약 오류 | 기존 ResultValidationError 전파 |

INVALID_REQUIRED_REGION이 Resolver에서 발생해도 UNKNOWN으로 감추지 않는다. 정상 경로에서는 정책 모델이 먼저 유효성을 보장한다. 원문/user fact 값은 오류 문장에 복사하지 않는다.

평가 호출 하나는 정상 PolicyEvaluation(배치는 전체 tuple) 또는 예외 중 하나만 반환한다. 부분 성공과 오류를 혼합한 새 응답 모델을 만들지 않는다. 기존 evaluator에는 오류→UNKNOWN 변환이 없으며 그 성질을 유지한다. 자료 충돌을 UNKNOWN으로 바꿔 group Status에 끼워 넣지 않는다.

기준일 밖 충돌도 거부하는 현재 동작은 유지한다. collection validation과 날짜별 resolution의 책임 분리는 별도 기술부채이며 routing 구현이 이를 승인/해결하지 않는다.

## 14. Loader JSON 계약

### 14.1 현재 문법 보존과 버전 선택

현재 loader는 kind=rule/group을 사용한다. 이번 설계는 이를 삭제하지 않는다. **향후 확장 문법을 schema_version=m1.1로 제안**하고 기존 m1.0을 그대로 지원한다. 실제 지원 버전 상수와 로더는 이번에 변경하지 않는다.

| schema | leaf | group |
|---|---|---|
| m1.0 | 기존 kind=rule, field/operator/value. rule_type 키 없음 | 기존 kind=group |
| m1.1 제안 | kind=rule + 필수 rule_type=atomic 또는 resident_registration | kind=group, rule_type 키 없음 |

m1.0에서 rule_type 키는 계속 미등록 키 오류다. m1.1에서 leaf rule_type 누락/None/미지원 값은 PolicyDataError다. group에 rule_type을 붙이는 것도 오류다. missing type을 operator/field 모양으로 추정하지 않는다. JSON 문자열은 loader의 유한 표로 Enum/타입에 명시적으로 변환하며 알 수 없는 값은 거부한다.

loader는 envelope의 schema_version을 먼저 검증한 뒤 `_node`에 버전을 명시적으로 전달한다. PolicySet은 지원 버전 집합을 검증하고 m1.0에서 specialized node를 직접 넣는 우회도 거부하도록 한다. m1.1에서는 atomic-only 또는 혼합 트리가 가능하다. 원래 합성 fixtures는 m1.0 그대로 남긴다.

**단계 간 검증 우회 방지:** PolicySet의 m1.1 허용과 loader의 envelope/버전별 필수 키 검증은 같은 후속 작업에서 적용한다. 현재 loader는 마지막 PolicySet 생성자에 버전 검증을 의존하므로 모델에 m1.1 허용만 먼저 추가하면 구문 검증 우회가 생긴다. 다음 모델 단계에서는 Policy/RuleGroup의 메모리 내 혼합 트리만 허용하고, PolicySet은 기존 m1.0 제한 및 specialized 포함 거부를 유지하도록 한다. 그다음 단일 Policy routing을 검증할 수 있다. 새 specialized 배치 트리의 PolicySet 생성/평가는 버전/loader 계약을 함께 구현한 단계에서 허용한다. 기존 atomic batch 호출은 계속 지원한다. 이것은 후속 기능의 도입 순서이며 m1.1 검증을 느슨하게 허용하는 과도기 API를 만들자는 뜻이 아니다.

### 14.2 설명용 JSON — 파일 아님

아래 leaf는 향후 m1.1 **합성 테스트** 문법 예시다. 실제 정책 공고를 나타내지 않는다.

```json
{
  "kind": "rule",
  "rule_type": "resident_registration",
  "rule_id": "SYN_RR_001",
  "required_region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
  "reference_date_source": "APPLICATION_DATE",
  "evidence_refs": ["synthetic:resident-requirement"]
}
```

m1.1 atomic leaf는 기존 kind/field/operator/value/evidence_refs와 선택 fact_basis에 `rule_type: atomic`만 추가한다. 주민등록 leaf에는 atomic field/operator/value/fact_basis를 허용하지 않는다. 요구 지역 object는 정확히 sido/sigungu 두 필수 키다. 추가 사용자 facts/date/source/result 키도 거부한다.

group은 기존 kind/rule_id/operator/children 구조를 유지하고 children을 같은 버전으로 재귀 파싱한다. 새 종류가 있어도 JSON 키 중복 거부·unknown key 거부·엄격한 숫자/bool 타입·NOT 자식 수·전역 rule_id 유일성·전체 로딩 성공 원칙은 유지한다. 예외를 PolicyDataError로 분류하는 기존 parse_policy_set 경계를 유지한다.

schema_version은 데이터 형식, dataset_version은 자료 버전, rule_version은 정책 규칙 버전이다. 기존 ENGINE_VERSION/평가 context의 버전 계약을 이번 설계만으로 자동 변경하지 않는다. 이 engine_version을 빌드 전체의 해시라고 주장하지 않으며 향후 배포 버전 추적은 별도다. synthetic/test_only=True 제한도 유지한다. 실제 정책 로딩 허용과 JSON 전송용 사용자 facts/context 파서는 별도 승인 범위다.

## 15. 실제 정책 개념 예시

기존 M1.5/M1.6 분석과 사용자 제공 개념에 주민등록 leaf를 대입하면 다음 관계가 가능하다. 이는 일부 논리 관계이며 정책의 모든 필수조건을 망라한 실행 트리가 아니다. 새로운 공식 정책 사실을 확정하지 않는다.

```text
ALL
├─ 생년월일 조건                  [미구현 개념]
├─ ResidentRegistrationRule        [이번 routing 대상]
│    required_region: 안산 내부 지역 참조
│    reference_date_source: APPLICATION_DATE
└─ ANY
   ├─ 경기도 연속 3년             [미구현 개념]
   └─ 경기도 합산 10년            [미구현 개념]
```

논리적으로 ALL/ANY 재귀 구조는 적합하다. 각 미구현 leaf가 나중에 표준 RuleEvaluation을 반환하면 집계기를 바꾸지 않아도 된다. 그러나 현재 Birth/History 타입은 존재하지 않으므로 이 전체 트리를 로드/실행할 수 없다. 미구현 부분을 삭제하거나 PASS 처리하고 전체 정책 결과를 표시하면 안 된다. UNKNOWN placeholder 구현도 이번에 만들지 않는다.

현재 age를 생년월일 조건의 자동 대체값으로 쓰거나 점 시점 주민등록을 거주기간으로 확장하지 않는다. 지금 구현 가능한 것은 합성 조건으로 검증하는 주민등록 leaf뿐이다. 실제 정책 전체는 원문 커버리지와 미구현 조건 설계가 완료된 별도 단계에서 다룬다.

## 16. 수동 테스트 시나리오

### 공통 가상 입력

평가일=2026-11-10, 해당 정책 신청일=2026-11-10. 정상 PolicyReferenceContext 제공. 요구=GYEONGGI/ANSAN. 정상 주민등록 fact는 같은 날 안산/SELF_REPORTED 하나. A_P/A_F/A_U는 기존 age eq 24 규칙에 age=24/25/None을 넣는 합성 사례다. R_P/R_F/R_U는 주민등록 안산/수원/빈 facts다. 행에 명시한 변경만 적용한다. 모든 예시는 향후 구현의 **수동 기대값이며 실행 테스트가 아니다**.

| ID | 입력/노드 | 기대 결과 |
|---|---|---|
| RT01 | 기존 A_P만, 새 인자 생략 | PASS/CONDITION_MET, 기존 JSON 동일 |
| RT02 | 기존 A_F만 | FAIL/CONDITION_NOT_MET |
| RT03 | 기존 A_U만 | UNKNOWN/MISSING_FIELD, missing=[age] |
| RT04 | R_P root | PASS/RESIDENT_REGION_MATCH, 전체 지역 snapshot·기준일·선택 근거 보존 |
| RT05 | R_F root | FAIL/RESIDENT_REGION_MISMATCH, 관찰=수원/요구=안산 |
| RT06 | 정확한 날짜 fact.region=None | UNKNOWN/RESIDENT_REGION_MISSING, missing=[resident_registration.region], 날짜/source 근거 유지 |
| RT07 | ALL(A_P,R_P) | PASS/ALL_PASS, 두 leaf 사유 보존 |
| RT08 | ALL(A_P,R_F) | FAIL/ALL_FAIL |
| RT09 | ALL(A_P,R_U) | UNKNOWN/ALL_UNKNOWN |
| RT10 | ANY(A_F,R_P) | PASS/ANY_PASS |
| RT11 | ANY(A_P,R_U) | PASS/ANY_PASS, resident 누락 경로는 정책 요약에 남음 |
| RT12 | ANY(A_F,R_F) | FAIL/ANY_FAIL |
| RT13 | ANY(A_F,R_U) | UNKNOWN/ANY_UNKNOWN |
| RT14 | NOT(R_P) | 부모 FAIL/NOT_FAIL, leaf PASS/MATCH·details 그대로 |
| RT15 | NOT(R_F) | 부모 PASS/NOT_PASS, leaf FAIL/MISMATCH 그대로 |
| RT16 | NOT(R_U) | 부모 UNKNOWN/NOT_UNKNOWN, leaf 누락 보존 |
| RT17 | 평가일11/10, 신청일/fact 날짜10/1 | PASS. resolver 평가일=11/10, reference=10/1, detail/fact 날짜=10/1 |
| RT18 | 유효한 정책 context의 application_date=None | UNKNOWN/RESIDENT_REFERENCE_DATE_MISSING, missing=[reference_date]. 평가일 대체 없음 |
| RT19 | facts 인자 생략 또는 빈 EvaluationFacts, 정상 context | UNKNOWN/RESIDENT_REGISTRATION_MISSING, missing=[resident_registration] |
| RT20 | 같은 날짜 안산·수원 facts | CONFLICTING_RESIDENT_REGISTRATION_FACTS. 정상 Rule/PolicyEvaluation 없음 |
| RT21 | m1.1 leaf rule_type=unknown | PolicyDataError. registry fallback 없음 |
| RT22 | JSON required_region 키/타입/유효 쌍 오류 | PolicyDataError. UNKNOWN 아님 |
| RT23 | 주민등록 leaf인데 reference_context 자체 생략 | ContextValidationError. 날짜 미입력 RT18과 구분 |
| RT24 | context.policy_id가 다른 정책 | ContextValidationError. 타 정책 신청일 사용 금지 |
| RT25 | application_date에 str/datetime/bool | ContextValidationError. 자동 파싱 없음 |
| RT26 | UserProfile.region=안산시, 주민등록 facts 없음 | UNKNOWN. atomic region 값 fallback 없음 |
| RT27 | ANY(A_P, 충돌 facts의 resident) | 오류 전파. 선행 PASS로 숨기지 않음 |
| RT28 | ALL(A_F, 충돌 facts의 resident) | 오류 전파. 선행 FAIL로 숨기지 않음 |
| RT29 | 신청일=11/11, 평가일=11/10, 같은 미래 날짜 fact | UNKNOWN/RESIDENT_REFERENCE_DATE_IN_FUTURE, 근거 생성 없음 |
| RT30 | 요청 facts에 기준일 밖 같은 날짜 안산·수원 충돌 | 기존 충돌 오류 유지. 날짜별 사전 필터링 없음 |
| RT31 | 원자와 주민등록 leaf 또는 그룹 간 rule_id 중복 | 모델/로딩 PolicyDataError |
| RT32 | Root=ALL(A_P, ANY(R_P,A_U)) | root-first 입력 순서 유지. 전체 PASS여도 age 누락은 유지. leaf details만 보존 |
| RT33 | 미지원 객체/Birth/History를 현재 트리에 직접 전달 | 모델 검증 또는 dispatch PolicyDataError. UNKNOWN/생략 없음 |
| RT34 | m1.0 합성 fixtures 그대로 로드/평가 | 기존 결과 동일. 새 입력 불필요 |
| RT35 | m1.0 leaf에 rule_type 추가 | 기존 unknown-key PolicyDataError 유지 |
| RT36 | m1.1 leaf rule_type 누락 또는 group에 rule_type 추가 | PolicyDataError. 구조 추측 없음 |
| RT37 | EvaluationFacts.resident_registrations에 list/None/잘못된 원소 | ProfileValidationError. 빈 tuple과 구분 |
| RT38 | batch 정책 A/B에 서로 다른 유효 신청일 context | 각 정책 자신의 날짜로 Resolver 호출. context 교차 없음 |
| RT39 | batch context 중복 policy_id/대상 밖 ID/필수 context 부재 | ContextValidationError. 부분 정상 결과 tuple 반환 없음 |
| RT40 | Resolver가 전달 날짜와 다른 날짜 결과 반환 | 연결 계약 오류, Adapter/집계로 정상 결과 유입 금지 |
| RT41 | Adapter의 ResultValidationError 발생 | 예외 그대로 전파. UNKNOWN 치환 없음 |
| RT42 | 동일 요청 재실행, 동일 fact 중복/순서만 변경 | 결과/JSON 동등. 입력 변경 없음. 선택 evidence는 Resolver canonical 순서 |

각 정상 RT 행의 정책 결과는 context.as_of·rule_version을 보존한다. RT21/22/34~36은 loader 확장 단계, RT40/41은 후속 routing 경계 오류 테스트 기대값이다. 실제 Resolver/Adapter의 기존 단위 테스트와 구분한다.

## 17. 구현 예상 변경 파일

이번에는 아래 파일을 수정하지 않는다. 신규 후보도 아직 존재하지 않는 제안이다.

| 경로 | 후속 변경 역할 |
|---|---|
| backend/policy_engine/specialized_rules/resident_registration.py (신규 후보) | 정책 요구 leaf와 검증 |
| backend/policy_engine/specialized_rules/__init__.py (신규 후보) | 해당 leaf만 공개 |
| backend/policy_engine/evaluation_inputs.py (신규 후보) | 작은 EvaluationFacts/PolicyReferenceContext 모델. 기존 EvaluationContext는 유지 |
| backend/policy_engine/models.py | RuleNode/children/root 허용 타입·재귀 검증, 이후 지원 schema 검증 |
| backend/policy_engine/evaluator.py | keyword-only 입력 및 재귀 전달, 타입별 routing, 명시적 미지원 노드 오류 |
| backend/policy_engine/loader.py | 별도 단계에서 버전별 leaf discriminator 및 지역/바인딩 파싱 |
| backend/policy_engine/__init__.py | 승인한 타입/함수 공개. 기존 import 유지 |
| tests/test_rule_routing_models.py (신규 후보) | leaf/input 모델·ID·불변성 |
| tests/test_rule_routing.py (신규 후보) | 혼합 트리·context·오류 전파·기존 호출 회귀 |
| tests/test_rule_routing_loader.py (신규 후보) | 별도 loader 단계의 m1.0/m1.1 호환/거부 사례 |
| docs/POLICY_RULE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md, 본 문서 | 실제 구현 범위만 갱신 |

_aggregate는 변경 불필요다. `_evaluate_node`에는 인자와 분기가 추가되지만 그룹 조립/순서/합집합 알고리즘은 그대로 둘 수 있다. Resolver/Adapter/Fact/result_types의 의미나 구현을 바꿀 이유가 없다. 기존 합성 데이터 및 테스트 기대값을 새 문법으로 대량 수정하지 않는다.

## 18. 호환성 위험

| 위험 | 방지 계약 |
|---|---|
| AtomicPolicyRule로 클래스 이름 변경 | 기존 PolicyRule 이름/필드/생성자/exports 유지 |
| 새 leaf가 그룹으로 오인됨 | 세 타입의 명시적 분기 + 미지원 오류 |
| union만 바꾸고 모델 검증/순회 누락 | root/children/ID/walk_nodes 함께 검증 |
| context 누락을 신청일 미입력으로 덮음 | 객체 부재 오류 vs 유효 객체의 날짜 None UNKNOWN 구분 |
| batch에서 다른 정책 날짜 재사용 | policy_id별 명시 context와 중복/대상 검증 |
| region fallback/날짜 추정 | UserProfile 자동 승격·평가일 대체·최근 fact 선택 금지 |
| ANY PASS가 오류를 숨김 | 단락 평가 도입 금지, 예외는 정상 집계 밖으로 전파 |
| 새 JSON이 기존 strict loader를 느슨하게 만듦 | 버전별 필수 키·discriminator, m1.0 원형 유지 |
| import 순환/타입 힌트 해석 | specialized/input 모듈은 models/evaluator를 역으로 참조하지 않음. 기존 reason 전방 참조는 필요 시 명시 해석하며 API schema 선제 도입 없음 |
| build 버전과 schema를 혼동 | 기존 버전 의미 유지, 신규 형식 버전은 loader 단계에서만 추가. 빌드 지문 보장으로 과장하지 않음 |
| 부분 정책으로 전체 자격 표시 | 미구현 조건 실행 금지, 실제 자료와 synthetic/test_only 제한 유지 |

설계는 기존 출력과 호출 호환을 목표로 하며 아직 구현 테스트로 입증된 상태는 아니다. 수동 기대표를 후속 회귀 테스트로 옮겨 검증해야 한다.

## 19. 미결정사항

첫 주민등록 routing에 필요한 타입·facts/context 부재 의미·분기·집계·loader 구분은 이 문서에서 선택했다. 다음은 첫 메모리 내 routing을 막지 않는 후속 사항이다.

- 운영 입력에서 신청 기준일/평가일을 누가 확인하고 어떻게 표시할지. 현재는 명시적 date라는 Assumption을 둔다.
- 기준일 밖 충돌의 collection validation 분리. 현행 전체 충돌 오류 유지가 기본이다.
- 실제 정책 원문·전체 조건 커버리지·신청기간·서류/지원금 처리. 주민등록 routing으로 해결하지 않는다.
- 정책당 여러 신청 기준일이 생길 때의 context 확장, 실제 두 번째 specialized 타입. 지금 미리 만들지 않는다.
- build/배포 지문과 엔진 호환 버전의 별도 추적. 현재 engine_version을 전체 배포 식별자로 과장하지 않는다.

권장 schema 버전명 m1.1 및 새 경로는 후속 구현 승인 때 적용할 제안이다. 이번에는 상수/파일/API로 등록하지 않는다. Python 3.12에서 필요한 문법은 이미 사용 가능하며 별도 패키지 도입은 필요 없다.

## 20. 최종 판단

**READY_TO_IMPLEMENT_RULE_ROUTING**

기존 PolicyRule을 보존한 유한 union, 주민등록 요구 leaf, 별도 typed facts와 정책별 reference context를 선택했다. 누락과 호출 오류, Resolver/Adapter 경계 및 날짜 의미를 분리했고 기존 Status 집계 알고리즘을 유지할 수 있다. 범용 프레임워크나 논리 엔진 재작성은 필요 없다.

**다음 가장 작은 작업 1개:** ResidentRegistrationRule과 EvaluationFacts/PolicyReferenceContext 입력 모델 및 혼합 트리의 타입/ID 검증만 구현하고 테스트한다. evaluator routing·loader 변경·실제 JSON은 다음 별도 작업으로 둔다.

### 이번 작업의 검증 기록

작업 전 전체 pytest: **449 passed in 2.19s**, 문서 작성 후 **449 passed in 2.26s**. Git 저장소가 아니므로 기존 backend/tests/data/docs 파일 33개의 SHA256 기준선을 비교했고 모두 동일했다. 이 문서만 추가했다. 필수 20절과 중복 없는 RT01~RT42를 확인했다. 이번 수동 시나리오 42개는 실행된 신규 테스트가 아니며, routing/새 타입/loader의 구현 검증을 완료했다는 뜻은 아니다.

## 21. M1.6G — IMPLEMENTED: specialized leaf와 평가 입력 모델

M1.6F의 모델 준비 단계만 구현했다. 8절 evaluator 인자, 10~11절 routing, 14절 m1.1 loader는 아직 구현하지 않았다. 기존 평가 함수를 혼합 트리 실행에 사용하지 않는다. 모델 생성 성공과 실행 지원을 구분한다.

### 구현 모델 및 배치

| 구현 | 위치/계약 |
|---|---|
| ResidentRegistrationRule | specialized_rules/resident_registration.py. rule_id, required_region: RegionRef, reference_date_source, evidence_refs |
| ReferenceDateSource | 기존 result_types의 APPLICATION_DATE Enum 멤버 재사용. 새 종류/alias 추가 없음. 주민등록 Rule은 해당 멤버만 허용 |
| PolicyReferenceContext | evaluation_inputs.py. policy_id, application_date: date 또는 None(기본값) |
| EvaluationFacts | evaluation_inputs.py. resident_registrations: 정확한 ResidentRegistrationFact의 tuple, 기본 빈 tuple |
| RuleNode | 기존 PolicyRule 또는 ResidentRegistrationRule 또는 RuleGroup |
| RuleGroup / Policy | 혼합 children/주민등록 root를 명시적으로 허용. 정확한 타입·자식 수·전체 ID 유일성 검증 |

새 모델은 frozen/slots다. specialized 모듈은 models/evaluator/Resolver를 역으로 import하지 않는다. root 패키지에서 세 신규 모델을 공개하고 기존 이름·생성자를 유지한다. AtomicPolicyRule이라는 별도 클래스는 만들지 않았다.

### 검증 경계

- ResidentRegistrationRule은 비어 있지 않은 rule_id, 완전한 RegionRef, APPLICATION_DATE 멤버, 최소 한 개의 비어 있지 않은 근거 str로 된 tuple을 요구한다. 잘못된 Rule 입력은 PolicyDataError이며 UNKNOWN을 만들지 않는다. evidence_refs 기본 빈 tuple도 정책 요구 근거가 없으므로 거부한다.
- 부분/미등록 RegionRef는 그 객체 생성 단계에서 기존 ResidentRegistrationValidationError가 먼저 발생한다. Rule 생성자에 None/문자열/dict 등을 넣으면 PolicyDataError다. 기존 지역 검증을 복제하거나 정책 지역을 추론하지 않는다.
- context의 policy_id는 비어 있지 않은 str, application_date는 정확한 date/None이다. datetime/str/bool 자동 변환은 없다. 잘못된 context는 ContextValidationError다. application_date=None은 유효한 미입력 표현일 뿐, 이번 모델이 UNKNOWN을 계산하는 것은 아니다. 실제 Policy와의 ID 일치·context 부재 처리는 미래 routing 책임이다.
- EvaluationFacts의 list/dict/generator/None/잘못된 원소는 ProfileValidationError다. 개별 Fact 생성 오류는 기존 오류를 유지한다. tuple 순서/중복/source 차이/동일 날짜 충돌 주장을 그대로 보존하고 정렬·dedup·선택·충돌 판정을 하지 않는다.
- RuleGroup은 ALL/ANY의 비어 있지 않은 tuple, NOT의 정확히 한 자식을 유지한다. 알 수 없는 child/root를 거부한다. walk_nodes는 그룹에서만 재귀하며 모든 leaf를 순서대로 포함한다. 원자/주민등록/그룹 간 중복 rule_id도 트리 전체에서 거부한다. 기존 데이터셋 전체 ID 검사도 유지한다.
- Policy의 synthetic/test_only=True 제한을 유지한다. PolicySet은 여전히 m1.0만 허용하며 specialized root/하위 leaf가 있는 데이터셋도 거부한다. m1.1 허용은 loader 버전 검증과 함께 적용해야 한다. 모델 단계의 검증 우회를 만들지 않았다.

### 표현과 범위

각 신규 모델에 작은 to_dict()를 제공한다. RegionRef는 두 내부 키, 날짜는 ISO/None, Enum은 value, tuple은 새 list로 표현한다. 반환 dict/list 변경은 불변 입력에 영향을 주지 않는다. 이 표현은 m1.1 JSON 스키마나 사용자 입력 파서가 아니다. 범용 직렬화 계층·DB·프로필 복제·상태 판정은 추가하지 않았다.

기존 PolicyRule/UserProfile/EvaluationContext, evaluator.py/loader.py, Fact/Resolver/Adapter/result_types 및 기존 테스트/합성 데이터의 동작·기대값은 유지한다. UserProfile.region의 주민등록 자동 승격은 없다.

### 검증 기록 및 다음 단계

작업 전 **449 passed in 2.26s**, 최종 전체 pytest는 **542 passed in 2.76s**다. 신규 테스트 파일은 tests/test_rule_routing_models.py이며 신규 사례는 93개다. 정상/오류/불변성/직렬화, 혼합 트리/순회/중복 ID, 기존 세 합성 정책과 m1.0 제한 보존을 검증했다. mixed tree를 평가하거나 Resolver/Adapter를 연결한 테스트는 없다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 파일 34개의 SHA256을 비교했다. models.py/공개 export 및 문서 3개만 수정했고 나머지 29개는 동일하다. 신규 모듈/공개 파일/테스트 4개를 추가했다. evaluator/loader/Fact/Resolver/Adapter/result_types/기존 모든 테스트/합성 데이터는 기존 해시와 동일하며 기존 449개 테스트 기대값을 수정하지 않았다.

NOT IMPLEMENTED: 실제 rule routing, Resolver/Adapter 호출 연결, evaluator의 새 입력 인자, 정책별 context 바인딩, loader m1.1, 실제 정책 JSON 및 미래 Fact/서비스 기능.

최종 판단: **READY_FOR_ROUTING_IMPLEMENTATION**.

다음 가장 작은 작업 1개: 단일 Policy의 메모리 내 routing에 한정해 typed facts/context 전달과 주민등록 branch의 기존 Resolver→Adapter 호출을 연결하고 혼합 트리 회귀 테스트를 추가한다. _aggregate 의미·Loader·PolicySet m1.1 허용은 변경하지 않는다.

## 22. M1.6H — IMPLEMENTED: 단일 Policy의 메모리 내 mixed-tree routing

### entrypoint와 호환성

현재 공개 함수는 다음과 같다. 기존 8절의 evaluate_policy 인자 확장 후보 대신, M1.6H 직접 지시가 우선한 **별도 확장 entrypoint**를 선택했다.

```python
evaluate_policy_tree(
    profile: UserProfile,
    policy: Policy,
    context: EvaluationContext,
    *,
    facts: EvaluationFacts | None = None,
    reference_context: PolicyReferenceContext | None = None,
) -> PolicyEvaluation
```

구현은 backend/policy_engine/routing.py 하나에 둔다. root 패키지에서 공개한다. 별도 evaluation 패키지나 범용 registry는 만들지 않았다. PolicySet을 받는 새 배치 함수는 없으며, 실제 JSON/스키마 버전 로딩 경로와 독립적이다.

기존 evaluate_policy/evaluate_policies의 이름·인자·기본값을 유지한다. 기존 호출은 facts/context 추가 입력을 요구하지 않는다. 기존 경로로 specialized tree를 실행하면 PolicyDataError로 명시적으로 거부한다. 이전의 그룹 오인/AttributeError를 방지하는 guard이며 기존 유효한 m1.0 규칙의 의미는 바꾸지 않는다.

### 실제 routing

| 타입 | 실행 경로 |
|---|---|
| PolicyRule | 기존 evaluator._evaluate_atom을 그대로 호출 |
| ResidentRegistrationRule | 신청일 바인딩 → 기존 Resolver → 반환 날짜 연결 정합성 확인 → 기존 Adapter |
| RuleGroup | 모든 child를 입력 순서대로 재귀 평가 → 공통 그룹 조립 및 기존 _aggregate |
| 그 외 | PolicyDataError |

evaluator.py에서는 그룹/정책 결과 조립 부분만 `_assemble_group_result` / `_assemble_policy_result`로 추출해 두 경로가 공유한다. 기존 atomic 평가와 _aggregate의 구현은 그대로다. 새 evaluator 전체를 복제하지 않았다. root-first 순서, 전체 누락/정책 근거 합집합, 모든 노드 사유 합집합, rule_version/context 보존도 같은 함수를 사용한다.

NOT은 부모 상태만 반전하고 leaf의 상태/reason/details/evidence는 원래대로 남긴다. ANY 앞에 PASS 또는 ALL 앞에 FAIL이 있어도 뒤의 오류를 숨기지 않는다. 오류가 발생하면 정상 결과로 집계하지 않고 예외를 즉시 전파한다.

### 입력·날짜·근거 계약

- 새 entrypoint는 profile/Policy/평가 context/facts/reference context의 타입을 확인한다. 잘못된 호출은 각각 기존 ProfileValidationError/PolicyDataError/ContextValidationError 흐름으로 거부한다.
- facts=None은 빈 EvaluationFacts로 정규화한다. 주민등록 branch는 resident_registrations **전체 tuple**만 전달한다. UserProfile.region fallback·fact 선택·정렬·출처 우선순위는 없다.
- reference context가 제공되면 atomic-only 정책에도 policy_id 일치를 검사한다. 주민등록 leaf가 있는데 context 자체가 없으면 평가 전 ContextValidationError다.
- 유효한 context의 application_date=None은 그대로 Resolver로 보낸다. 정상 상황에서는 RESIDENT_REFERENCE_DATE_MISSING/UNKNOWN이며, 충돌 자료가 함께 있으면 기존 Resolver의 충돌 우선순위를 유지한다.
- Resolver.reference_date는 reference_context.application_date, evaluation_date는 context.as_of다. 시스템 오늘·평가일 자동 대체·신청기간 보간은 없다.
- Resolver 반환 타입 및 반환된 두 날짜가 전달한 값과 같은지만 연결 경계에서 확인한다. 날짜 불일치에는 승인된 RESOLUTION_EVALUATION_DATE_MISMATCH / RESOLUTION_REFERENCE_DATE_MISMATCH를 ResultValidationError로 반환한다. 날짜의 정책 충족 여부를 다시 계산하지 않는다.
- Adapter에는 leaf rule_id/evidence_refs와 원본 Resolution, 명시적 ResidentRegistrationCondition snapshot을 전달한다. 원래 reason/status/missing과 선택한 fact provenance는 보존된다. 정책 근거와 사용자 사실 근거를 합치지 않는다.
- Resolver/Adapter 예외에 대한 catch-all이나 UNKNOWN 변환은 없다. 두 구성요소의 기존 구현·오류·입력 의미를 바꾸지 않았다. 기준일 밖 충돌 거부도 유지한다.

### 합성 mixed tree 실제 실행 예

신규 tests/test_rule_routing.py의 합성 tree를 실제 새 entrypoint로 실행한 요약이다. 실제 정책명이 아니며 실제 정책 전체 판정도 아니다.

```text
ROOT ALL
├─ AGE: age >= 19
├─ RESIDENT: 신청 기준일의 안산 내부 지역
└─ LIFE ANY
   ├─ STUDENT: student_status == True
   └─ UNEMPLOYED: employment_status == unemployed
```

평가일/신청 기준일=2026-11-10, student=True, employment=employed. 아래는 가상 입력이다.

| 시나리오 | age | resident | LIFE | 실제 overall | missing_fields |
|---|---|---|---|---|---|
| A | 24 → PASS | 같은 날 안산 → PASS | PASS | PASS | [] |
| B | 24 → PASS | 같은 날 수원 → FAIL | PASS | FAIL | [] |
| C | 24 → PASS | fact 없음 → UNKNOWN | PASS | UNKNOWN | [resident_registration] |
| D | 18 → FAIL | fact 없음 → UNKNOWN | PASS | FAIL | [resident_registration] |

A의 실제 노드 결과 요약(root-first):

```json
[
  {"rule_id": "ROOT", "status": "PASS"},
  {"rule_id": "AGE", "status": "PASS"},
  {"rule_id": "RESIDENT", "status": "PASS"},
  {"rule_id": "LIFE", "status": "PASS"},
  {"rule_id": "STUDENT", "status": "PASS"},
  {"rule_id": "UNEMPLOYED", "status": "FAIL"}
]
```

JSON은 실행 결과를 발췌한 설명이며 정책 로더 입력 파일을 생성한 것이 아니다. 실제 PolicyEvaluation에는 reason/요구조건/details/정책 근거/평가 context도 포함한다. 전체 FAIL/PASS라도 미확인 항목을 숨기지 않는다.

### 검증과 남은 범위

작업 전 **542 passed in 2.56s**, 최종 전체 pytest는 **607 passed in 3.07s**다. 신규 테스트는 65개다. eq/in/gte/lte 및 원자 PASS/FAIL/UNKNOWN 사례와 중첩 ALL/ANY/NOT 결과를 기존 경로와 비교하고, 기존 세 합성 정책도 결과 객체/JSON의 동일성을 확인했다. mixed 진리표, 주민등록 8개 사유, 세 출처, context 경계, Resolver→Adapter 호출 순서, 오류 전파, 반환 날짜 불일치, 입력 불변성 및 순서/중복 재현성도 검증했다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 파일 38개의 SHA256 기준선을 비교했다. evaluator.py/공개 export 및 문서 2개만 수정했고 나머지 34개는 동일하다. routing.py와 신규 테스트 파일만 추가했다. Loader·모델·입력 타입·Fact·Resolver·Adapter·result_types·기존 모든 테스트·합성 데이터는 기존 해시와 동일하다. AST 비교로 기존 _evaluate_atom/_aggregate 구현과 evaluate_policy/evaluate_policies 인자 구조의 동일성도 확인했다.

IMPLEMENTED: 단일 메모리 내 합성 Policy의 mixed rule routing과 기존 Resolver/Adapter 연결.

NOT IMPLEMENTED: loader m1.1, specialized PolicySet/배치 routing, 실제 정책 JSON·공식 문서 바인딩, Birth/ResidenceHistory/Income/ApplicationWindow, 실제 정책 전체 평가, API/UI/DB/금융/What-if/LLM. PolicySet은 여전히 m1.0만 허용하고 specialized 노드를 거부한다. engine_version은 기존 호환 계약을 유지하며 배포 빌드 지문으로 간주하지 않는다.

최종 판단: **READY_FOR_M11_LOADER**.

다음 가장 작은 작업 1개: 승인된 m1.1 합성 규칙 문법의 loader와 PolicySet 버전 검증을 함께 추가하고, m1.0 fixtures 및 unknown/malformed 입력 거부를 테스트한다. 실제 정책 JSON과 specialized 배치 routing은 그 작업에 자동 포함하지 않는다.

## 23. M1.7 — IMPLEMENTED: 버전별 mixed-rule Loader

### 구현 계약

공개 load_policy_set/parse_policy_set API는 그대로다. loader.py에서 schema_version을 먼저 검증한 뒤 노드 파서에 명시적으로 전달한다. models.py의 validate_schema_version과 PolicySet은 m1.0/m1.1 정확한 문자열만 허용한다. 버전이 잘못됐으면 노드 오류보다 먼저 거부하며 버전 누락·미지원/잘못된 타입을 schema_version 메시지로 구분한다.

14절에서 승인한 문법을 실제 구현했다. m1.0은 기존 kind=rule/group 및 원자 필드를 유지하고 rule_type 키를 거부한다. m1.1 leaf는 kind=rule과 필수 rule_type=atomic/resident_registration을 사용한다. group은 기존 kind=group/operator/children이며 rule_type 키를 받지 않는다. M1.7 예시 후보의 rule_type=group 대신 기존 확정 discriminator를 유지한 선택이며, 자식 모양으로 종류를 추론하지 않는다.

- 원자 파싱은 공통 _atomic 하나다. eq/in/gte/lte 및 FactBasis/엄격한 타입의 의미를 복제/변경하지 않는다.
- 주민등록 leaf는 rule_id, 완전한 canonical required_region, APPLICATION_DATE, evidence_refs를 읽는다. RegionRef/ReferenceDateSource/ResidentRegistrationRule의 기존 검증을 사용한다. 별칭/숫자/오타를 자동 보정하지 않는다.
- JSON 배열은 기존처럼 tuple로 변환한다. group children의 순서와 재귀 구조는 보존한다.
- 허용 키 외 필드, 미등록 kind/rule_type/operator, 필수 키 누락, 빈 그룹/NOT 개수, malformed child, 중복 policy_id와 모든 종류의 rule_id를 거부한다. 중복 JSON 키도 기존 파일 읽기 경계에서 거부한다.
- invalid policy JSON은 PolicyDataError이며 정상 UNKNOWN이 아니다. 로딩 중 오류가 있으면 전체 PolicySet 반환을 중단한다. 일부 정책/규칙을 건너뛰지 않는다.
- PolicySet의 m1.1 허용과 loader의 버전별 검증을 같은 작업에서 추가했다. m1.0에서 specialized 노드를 직접 넣는 domain 경로도 계속 거부한다. m1.1 PolicySet은 원자-only/주민등록-only/혼합 트리를 담을 수 있다.
- synthetic/test_only=True 제한은 dataset/각 Policy에 계속 적용한다. 실제 자료 허용, engine_version 변경, 배치 routing은 추가하지 않았다.

### 합성 fixture와 실행 결과

새 파일은 data/synthetic/policies_m11.json 하나다. schema_version=m1.1, dataset_version=synthetic-routing-1, dataset/Policy 모두 synthetic/test_only=True다. 정책 이름은 ‘합성 혼합 트리’, ID는 SYN_MIX이며 공식 기관/정책/URL/실제 문서 바인딩이 없다. 기존 m1.0 JSON은 수정하지 않았다.

트리는 기존 M1.6H의 ROOT ALL → AGE + RESIDENT + LIFE ANY(STUDENT,UNEMPLOYED)와 동일하다. 기존 tests/test_rule_routing.py의 Python builder와 로드된 Policy 객체가 같은지도 별도로 확인했다. 새 테스트의 독립 hand-built 트리와도 결과 객체 전체 및 to_dict가 일치한다. 상태 외 rule_results/reason/missing/details/evidence_refs/context/rule_version까지 포함한 비교다.

| M1.7 사례 | 주민등록 fact | 신청 기준일 | 실제 결과 | missing_fields |
|---|---|---|---|---|
| A | 같은 날 안산 | 명시 | PASS | [] |
| B | 같은 날 수원 | 명시 | FAIL | [] |
| C | 없음 | 명시 | UNKNOWN | [resident_registration] |
| D | 같은 날 안산 | None인 유효 context | UNKNOWN | [reference_date] |

모두 age=24, student=True, employment=employed, 평가일=2026-11-10인 가상 입력이다. 단일 Policy를 기존 evaluate_policy_tree로 평가하며 새 배치 함수를 만들지 않았다. m1.0 기존 세 샘플 재로딩/평가 결과는 SAMPLE-001 PASS, SAMPLE-002 FAIL, SAMPLE-003 UNKNOWN으로 유지된다.

### 승인된 기존 테스트 1개 갱신

기존 test_m11_not_enabled_by_model_extension은 M1.6G의 임시 ‘m1.1 거부’ 기대값이라 이번 기능과 모순됐다. 작업 중 이를 보고했고 사용자가 **‘해당 테스트 1개만 갱신’**을 명시적으로 승인했다. 해당 함수만 test_m11_enabled_with_versioned_loader_contract로 바꾸어 m1.1 지원을 확인한다. 나머지 기존 테스트/기대값 및 m1.0 fixtures는 유지한다. 이 예외를 숨기고 기존 607개의 기대값이 전부 불변이라고 보고하지 않는다.

### 검증 및 남은 범위

작업 전 전체 pytest는 **607 passed in 2.56s**, 최종 전체 pytest는 **702 passed in 2.70s**다. 신규 tests/test_m11_loader.py는 95개 사례다. 기존 606개 기대값을 유지하고 승인된 1개를 갱신한 상태로 모두 통과했다. 버전 우선 검증·오류/extra field·잘못된 타입·지역 alias·중복 ID·부분 로드 금지·결정성 및 Loader→Routing/트리 동등성을 포함한다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 파일 40개의 SHA256을 비교했다. Loader/models, 승인된 테스트 파일 1개 및 문서 4개만 변경했고 나머지 33개는 동일하다. 신규 테스트와 m1.1 합성 JSON만 추가했다. 기존 테스트 파일은 승인된 함수 부분을 원래 내용으로 치환한 해시가 기준선과 같은지도 확인해 다른 변경이 없음을 검증했다. 기존 m1.0 JSON/나머지 모든 테스트/routing/evaluator/Fact/Resolver/Adapter는 변경하지 않았다.

IMPLEMENTED: m1.1 합성 mixed-rule Loader 및 PolicySet 버전 검증, 기존 단일 Policy routing과의 통합.

NOT IMPLEMENTED: 실제 정책 JSON/공식 문서 바인딩, BirthFact/ResidenceHistoryFact/IncomeFact/ApplicationWindow, 실제 정책 전체 평가, specialized 배치 routing, 금융/API/UI/DB/What-if/LLM.

최종 판단: **READY_FOR_FIRST_REAL_POLICY_SLICE**. 실제 정책 데이터 투입을 자동 승인한다는 뜻은 아니다.

다음 가장 작은 작업 1개: 기존 실제 정책 분석에서 주민등록 조건 한 조각의 원문·기준일·근거 위치·필수조건 커버리지를 다시 확인하는 문서를 작성한다. 합성 제한 해제나 production JSON 생성은 별도 승인으로 둔다.

## 24. M1.16G — IMPLEMENTED: Birth leaf 메모리 routing

현재 메모리 RuleNode는 PolicyRule/ResidentRegistrationRule/BirthDateRule/RuleGroup의 정확한 유한 union이다. Policy root와 RuleGroup child도 이를 허용하며 기존 순회/중복 ID·그룹 자식 수 검증은 유지한다. EvaluationFacts는 기존 resident positional 필드 뒤에 keyword-only birth:BirthFact|None=None을 제공한다. birth=None은 to_dict에서 생략해 기존 출력과 같고, 유효한 Fact는 그대로 보존한다.

evaluate_policy_tree의 공개 API와 기존 atomic/resident/group 분기는 유지한다. 새 birth 분기는 evaluate_birth_date_rule(node,facts.birth)를 호출하고 반환 객체를 tuple로 전달할 뿐이다. age/context 전달·날짜 비교·근거 변경은 없다. facts=None은 기존 빈 묶음 정규화를 통해 birth UNKNOWN이 되고, resident context 요구와 잘못된 명시적 reference context 거부는 그대로다.

기존 _aggregate/그룹·정책 조립/직렬화는 변경하지 않았다. ALL/ANY/NOT와 root-first 순서·누락/근거 합집합·오류 전파를 신규 mixed 테스트로 확인했다. birth 포함 PolicySet은 loader/schema 지원 전까지 m1.0/m1.1에서 거부한다. legacy evaluate_policy는 birth를 평가하지 않는다.

IMPLEMENTED: Birth RuleNode, EvaluationFacts.birth, birth routing dispatch, mixed aggregation support. NOT IMPLEMENTED: JSON loader support·actual Q3 policy data·분기 선택. 승인된 기존 테스트 세 함수만 새 계약에 맞게 갱신했으며 정확한 이름·전후 기대와 전체 회귀 결과는 REAL_POLICY_001_BIRTH_ROUTING_SPEC.md 25절을 따른다.
