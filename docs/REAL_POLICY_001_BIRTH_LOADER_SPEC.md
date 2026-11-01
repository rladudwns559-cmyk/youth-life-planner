# BirthDateRule JSON 입력 계약 — M1.16H

> 현재 상태: **M1.16I IMPLEMENTED / READY_FOR_REAL_Q3_BIRTH_INTEGRATION**. 아래 H 본문은 승인 당시 설계 기록이며 현재 구현·검증 결과는 29절을 따른다.

작성일: 2026-10-20 / Asia/Seoul. **문서 설계 전용**. 이 파일 하나만 추가하며 기존 코드·테스트·합성 fixture·실제 자료는 수정하지 않는다.

최종 판단: **READY_TO_IMPLEMENT_BIRTH_LOADER**. 아래 m1.1 확장과 guard 전환은 후속 M1.16I의 구현 계약이다. 현재 loader가 이미 birth를 읽는다는 뜻은 아니다.

## 1. 목적

메모리 mixed tree에서 지원하는 BirthDateRule을 strict JSON 경계로 안전하게 읽기 위한 문법·버전·날짜·도메인·근거·오류 책임을 확정한다. 실제 Q3 값·분기 선택·정책 발행과 parsing을 구별한다.

검토한 문서: REAL_POLICY_001_BIRTH_SLICE_SPEC.md, REAL_POLICY_001_BIRTH_RESULT_CONTRACT.md, REAL_POLICY_001_BIRTH_ROUTING_SPEC.md, POLICY_RULE_SPEC.md, RULE_ROUTING_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 실제 loader.py/models.py/PolicyEnvelope loader/Source loader의 날짜·JSON helper 및 birth 모델과 거부 테스트도 확인했다. 과거 단계 기록과 현재 구현을 구별했다.

## 2. 현재 loader 상태

| 영역 | 현재 구현 |
|---|---|
| 지원 버전 | m1.0 / m1.1 정확한 문자열. validate_schema_version 공유 |
| m1.0 leaf | kind=rule, field/operator/value의 기존 atomic. rule_type 불허 |
| m1.1 leaf | kind=rule, rule_type=atomic 또는 resident_registration |
| group | kind=group, rule_id/operator/children. leaf rule_type 키 없음 |
| _node | explicit kind/rule_type 분기와 재귀. shape inference 없음 |
| parse_policy_set | 버전 확인 → 전체 구조/Policy/PolicySet 생성. 기본 합성, 명시적 allow_real_data 경계 별도 |
| PolicySet | 메모리 birth Policy가 가능해졌어도 schema 지원 전까지 birth를 두 버전에서 차단 |
| 파일 JSON | UTF-8 json.load, 모든 object의 중복 키 hook 사용. parse는 dict 입력 경계 |
| Envelope | embedded Policy 하나를 기존 parse_policy_set으로 읽음. 별도 m1.1 파서 없음 |

현재 birth JSON을 전달하면 미지원 rule_type 오류다. 메모리 모델의 지원과 JSON의 지원을 구별한다. 기존 evaluator/routing/직렬화는 이번 loader 설계에서 바꿀 이유가 없다.

## 3. schema version 결정

**기존 m1.1의 additive extension을 채택한다. m1.2는 도입하지 않는다.**

| 기준 | m1.1 확장 | m1.2 도입 |
|---|---|---|
| 기존 payload 의미 | 기존 atomic/resident/group은 키와 의미 모두 그대로 유지 가능 | 같은 의미인데 지원 버전·분기·Envelope 허용 목록 변경이 늘어남 |
| specialized 구조 | M1.7부터 explicit leaf 종류를 구분하는 mixed specialized 구조 | 별도 구조 변경을 요구하는 근거가 현재 없음 |
| invalid → valid | 정확한 새 birth leaf 및 이를 담는 m1.1 PolicySet만 의도적으로 허용 | 이전 reader와 명목 버전을 구별하기는 쉬움 |
| 구현 규모 | 기존 분기 하나·날짜 helper·guard 조건 변경 | 불필요한 버전/호환 분기를 추가할 가능성 |
| 판단 | **이번 계약에 적합** | 기존 구조/필드 의미를 깨는 변경 때 재검토 |

이 결정은 m1.1이 임의 unknown rule_type을 허용하는 열린 schema라는 뜻이 아니다. 지원 집합은 atomic/resident_registration/**birth_date** 세 값으로 정확히 넓히며 다른 값은 계속 거부한다. 기존 valid payload는 객체/평가/직렬화 의미가 동일해야 한다.

**호환 한계:** 예전 m1.1 reader는 새 birth payload를 거부한다. 같은 schema 문자열이라는 이유로 과거 실행기가 새 leaf를 처리한다고 주장하지 않는다. 새 데이터 사용 시 reader 구현/계산 artifact 버전을 함께 확인해야 한다. 기존 engine_version=m1.0은 호환 표지이며 birth 지원 빌드 식별자 역할을 하지 않는다. 이 문서에서 별도 capability framework나 배포 시스템은 만들지 않는다.

## 4. m1.0 계약

m1.0은 atomic/group만 허용한다. rule_type이 있는 birth 표현은 unknown key/미지원 구조로 실패하고, rule_type을 빼고 birth 날짜 키만 남겨도 atomic 필수 키 누락/추가 키 때문에 실패해야 한다. birth 모양을 보고 추정하지 않는다.

메모리 PolicySet(m1.0)도 resident와 birth를 계속 거부한다. m1.0 fixture·atomic parser·기존 오류 의미는 유지한다. 지원 버전 검증에서 여전히 m1.2·잘못된 타입·오타를 거부한다.

## 5. m1.1 계약

후속 허용 종류는 leaf의 atomic/resident_registration/birth_date와 기존 group이다. birth-only·다른 leaf와 혼합·ALL/ANY/NOT·중첩 group을 읽을 수 있다. PolicySet m1.1의 도메인 guard도 같은 작업에서 birth를 허용하도록 전환해야 한다.

구버전·버전 누락을 m1.1로 자동 추정하지 않는다. m1.1에도 기존 dataset/Policy identity·synthetic/test_only·ID 유일성·배열·strict key 검증을 그대로 적용한다. 실제/합성 flag 수용 경계는 변경하지 않는다.

## 6. birth JSON syntax

아래는 **문서상 합성 예시**이며 아직 저장소의 JSON fixture나 실제 정책 데이터가 아니다.

```json
{
  "kind": "rule",
  "rule_type": "birth_date",
  "rule_id": "SYNTH-BIRTH-001",
  "min_birth_date": "1998-01-10",
  "max_birth_date": "1999-01-09",
  "evidence_refs": ["SYNTH-BIRTH-SOURCE-001#birth-date-range"]
}
```

JSON object → BirthDateRule, JSON array → tuple, 정확한 날짜 문자열 → date라는 경계 변환만 수행한다. Rule.to_dict()는 kind/rule_type이 없는 도메인 snapshot이므로 그 자체를 loader 입력 serializer로 취급하지 않는다. 예시의 synthetic source ref는 현재 Registry에서 resolve됐다는 뜻이 아니다.

## 7. 필수 필드

**정확히 여섯 키가 필수이며 선택 키는 없다.**

| 필드 | JSON 타입 / 계약 |
|---|---|
| kind | 정확한 문자열 rule |
| rule_type | 정확한 문자열 birth_date |
| rule_id | 정확한 str. 기존 모델이 빈 값·공백만 있는 값 거부, 자동 strip/생성 없음 |
| min_birth_date | 정확한 ASCII YYYY-MM-DD 문자열, null 금지 |
| max_birth_date | 같은 날짜 계약 |
| evidence_refs | JSON array, 비어 있지 않은 str 원소. 아래 10절 계약 |

도메인 생성자에서 evidence_refs의 기본값이 ()이더라도 JSON에서는 evidence_refs 누락을 허용하지 않는다. 모든 누락은 전체 load failure다. 사용자 Fact가 없어서 발생하는 평가 UNKNOWN과 다르다.

## 8. date parsing

후속 policy loader에 작은 전용 required-date helper를 추가한다. **정확한 str + `re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)` + date.fromisoformat** 순서로 검증한다. 정규식으로 형태를 제한한 뒤 달력 유효성을 Python date에 맡긴다. fromisoformat만 호출하여 다른 ISO 표기를 추가 허용하지 않는다.

| 입력 | 처리 |
|---|---|
| 1998-01-10, 2000-02-29 | date로 명시적 변환 |
| 2001-02-29, 0000-01-01, 1998-13-01 | 형식이 맞아도 달력 오류로 거부 |
| 1998/01/10, 10-01-1998, 1998-1-10, 19980110 | 거부 |
| T 시각/공백 시각/Z suffix/UTC offset 포함 | 거부. datetime 생성·절삭 안 함 |
| 앞뒤 공백·개행·비ASCII 숫자·주차 ISO 표기 | 거부. strip/locale/별칭 보정 없음 |
| null/bool/int/float/list/dict | 거부 |
| parse_policy_set 직접 호출에서 date/datetime 객체 | JSON 경계 입력이 아니므로 거부. 도메인 constructor의 date 허용과 구별 |

성공 시 **정확한 date**를 만들고 최종 BirthDateRule constructor도 exact date를 검증한다. date subclass를 만들거나 사용자 함수로 변환하지 않는다. 별도 윤년·나이 산식·timestamp parser는 없다.

현재 policy loader에는 날짜 helper가 없다. Source loader의 `_date`는 None 허용과 SourceValidationError 계약을 가지므로 birth에 그대로 가져와 null을 허용하거나 Source 오류가 새는 방식은 채택하지 않는다. 같은 strict 형식 원칙만 따르는 작은 policy-local helper를 둔다. 공통 날짜 framework·SourceRegistry 의존·다른 loader 리팩터링은 하지 않는다.

날짜 오류 메시지는 필드명과 계약만 담고 raw 값/전체 payload를 복사하지 않는다. 정확한 새 오류 문구의 스타일은 기존 PolicyDataError 방식으로 고정하며 새 오류 클래스를 만들지 않는다.

## 9. range validation 책임

loader는 두 문자열을 date로 바꾸고 BirthDateRule을 생성한다. **min ≤ max는 기존 BirthDateRule의 책임**이며 파서에서 중복 비교하지 않는다. 같은 날짜는 유효하다. 문자열 parsing 오류와 역전된 도메인 범위를 구별하되 둘 다 정상 UNKNOWN이 아닌 PolicyDataError다.

양끝 포함은 Rule의 고정 의미다. loader가 inclusive 플래그·나이 기준일·분기를 만들지 않는다. 날짜가 올바른 Q3 범위인지, 사용자가 해당 조건에 맞는지는 이 계층이 판정하지 않는다.

## 10. evidence_refs

기존 resident leaf처럼 `_array`로 정확한 list를 확인한 뒤 tuple로 변환하고 BirthDateRule constructor에 전달한다.

| 입력 | 구조 loader 처리 |
|---|---|
| 비어 있지 않은 문자열 배열 | ACCEPT, 순서 보존 |
| 같은 ref 중복 | **ACCEPT**, 중복 보존. 정렬/deduplicate 금지 |
| 빈 배열 | REJECT, 기존 모델의 필수 근거 검증 |
| 배열 대신 str/dict/tuple/None | REJECT |
| 원소가 None/bool/숫자/빈 문자열/공백만 있는 문자열 | REJECT |
| 비어 있지 않지만 canonical 형식이 아닌 문자열 | 독립 Rule/PolicySet 구조 경계에서는 ACCEPT. 실제 Envelope/Registry 경계에서 canonical 검증 |

Birth loader만 duplicate/canonical 검증을 강화해 기존 specialized Rule 의미와 달라지게 하지 않는다. PolicyEnvelope는 기존대로 leaf 내 중복 ref와 잘못된 canonical ref를 거부할 수 있다. 독립 PolicySet에서 허용됨과 Envelope의 근거 무결성 통과를 구별한다.

## 11. extra field

기존 _object strict 검증을 사용하며 정의되지 않은 키 하나라도 있으면 실패한다. 이름을 보정하거나 조용히 무시하지 않는다.

금지 예: min_birthdate/minimum_birth_date/birth_range, age/target_age/reference_age/calculated_age, quarter/application_date/evaluation_date/reference_date_source, inclusive_min/inclusive_max, birth_source, fact_basis, field/operator/value.

birth_source는 사용자 Fact provenance이며 정책 Rule에 들어갈 수 없다. 반대로 birth 필드를 atomic/resident에 넣는 것도 기존 strict key 오류다. group에 rule_type=birth_date를 넣어도 별도 birth group으로 취급하지 않는다.

## 12. rule_type dispatch

기존 _node의 kind=rule 안에서 schema 확인 후 다음 explicit 분기 하나만 추가한다: **rule_type == birth_date → strict 여섯 키 → 날짜 helper → BirthDateRule**.

atomic의 공통 _atomic과 resident_registration parser는 의미·키·배열 변환·결과를 유지한다. 정확한 문자열 BirthDate/BIRTH_DATE/birth-date/birthdate 등은 모두 거부한다. rule_type 누락/None/숫자도 거부한다. 날짜 키가 존재해도 shape inference를 하지 않는다.

kind=group은 기존 operator/children과 재귀 _node 경로를 그대로 사용한다. reflection·동적 import·registry 기반 dispatch로 전면 변경하지 않는다.

## 13. PolicySet guard

현재 위치: **models.py → PolicySet.__post_init__ → 전체 nodes/중복 ID 검증 다음의 unconditional BirthDateRule 거부**. M1.16G에서 JSON 지원 전 schema 유입을 막기 위해 추가한 임시 경계다. 바로 뒤에는 m1.0의 기존 ResidentRegistrationRule 거부가 있다.

후속 전환: **birth 거부 조건을 schema_version == m1.0인 경우로 좁힌다.** 기존 m1.0 resident guard는 유지한다. 이렇게 하면 m1.1에서 정확한 BirthDateRule을 허용하고 m1.0에서는 계속 거부한다. guard를 삭제하여 모든 버전에 birth를 허용하지 않는다.

Policy/RuleGroup은 이미 유한 노드 목록을 검증하며 미지원 객체를 거부한다. PolicySet의 버전·빈 목록·flags·중복 policy_id·모든 node의 rule_id 유일성 검증도 유지한다. loader의 birth 분기와 guard 전환은 **같은 구현 milestone**에서 완료한다. 파서만 성공하고 컨테이너에서 막히는 불완전 상태로 완료 보고하지 않는다.

m1.1 PolicySet이 birth를 담는다고 legacy evaluate_policies가 specialized batch 평가를 지원하는 것은 아니다. 평가에는 선택한 Policy 하나와 EvaluationFacts를 기존 evaluate_policy_tree로 전달한다. 이번 loader 구현에 새 batch routing을 추가하지 않는다.

## 14. nested group

ALL/ANY는 하나 이상, NOT은 정확히 한 자식이라는 기존 모델 검증을 유지한다. birth는 root 또는 모든 group의 자식·재귀 중첩 leaf로 읽는다. 별도 birth group 문법은 없다.

예시 구조는 ALL(atomic,resident_registration,birth_date), ANY(atomic,birth_date), NOT(birth_date)다. 입력 child 순서를 바꾸지 않고 loaded 결과의 root-first 실행 순서도 hand-built와 같아야 한다. 논리식이 실제 정책의 공식 조건을 의미하는지는 별도 자료 검토 사항이다.

## 15. duplicate rule ID

BirthDateRule 생성 이후 기존 RuleGroup/Policy/PolicySet의 walk_nodes 기반 유일성 검증을 재사용한다. atomic/resident/birth/group 사이, 중첩 다른 가지, 여러 Policy 사이의 동일 ID는 Data Error다. 타입별로 별도의 ID 공간을 만들거나 자동 이름을 붙이지 않는다.

JSON **중복 key**는 별개다. load_policy_set 파일 경계의 기존 object_pairs_hook은 모든 object에서 중복 key를 거부한다. Envelope 파일 경계의 자체 중복 key hook도 유지한다. 이미 dict가 된 parse 입력은 사라진 중복 key를 복원할 수 없으므로 파일 로딩과 pure parse의 보장 범위를 구별한다.

## 16. PolicyEnvelope 영향

현재 Envelope loader는 rule_schema_version=m1.1을 확인하고 embedded Policy 하나를 parse_policy_set으로 전달한다. 따라서 **그 loader 코드를 수정하지 않고** 새 birth 파서와 m1.1 guard 허용이 전파되는 방향을 채택한다.

PolicyEnvelope 모델도 group 이외 leaf를 공통 순회하여 coverage ID·근거·binding을 검증하므로 새 birth용 분기가 필요하지 않다. fixture와 동일한 identity/flags assertion, 날짜/coverage/source binding 검증을 유지한다. 새 leaf가 있으면 coverage에 해당 ID가 정확히 있어야 하며 빠진 상태는 계속 오류다.

후속 I에서 합성 Envelope payload를 메모리에 구성하여 embedded birth strict parsing 성공과 coverage/canonical ref/flag 불일치 거부를 확인한다. 실제 Envelope나 기존 synthetic fixture는 바꾸지 않는다. 추가 Registry 검증이 필요하면 별도 합성 메모리 자료만 사용한다. source resolve 없이 Envelope 구조 load만 성공한 경우 그 범위로 보고한다.

## 17. SourceRegistry 책임 분리

Rule/domain/parser는 최소 근거 구조를 확인한다. Envelope는 canonical ref·중복·coverage/binding ID 집합을 확인한다. Registry와 기존 cross-validator는 source/locator 존재, 참조 수명, 문서 버전, 적용 정책, 확인일을 검증한다. 이 구분을 유지한다.

Birth JSON parsing 중 Registry/파일 URL/공식 사이트를 조회하지 않는다. 실제 source가 없다는 이유를 사용자 조건 UNKNOWN으로 바꾸지 않는다. canonical ref가 형식상 맞아도 공식 구간이 원문과 일치하는지는 자동 검증되지 않는다. 실제 Q3 데이터 acceptance가 별도로 필요하다.

## 18. quarter / edition 분리

loader는 현재 날짜·신청일·평가일을 보지 않으며 이미 주어진 한 날짜 구간을 읽을 뿐이다. 실제 Q3 min/max·정책 canonical ID·공식 locator를 코드에 하드코딩하지 않는다.

edition_id는 현재 ASCII 4자리 연도 계약을 유지한다. 2026-Q3 같은 문법을 추가하지 않는다. 향후 Q3는 현재 2026 edition 안의 **명시적으로 선택된 부분 조건**으로 연결하는 방향이며, 연간 edition의 분기 선택 문제는 미결정 상태다. 실제 Q3 birth를 연간 정책 전체에 일괄 적용하면 안 된다.

I의 loader 지원은 이 미결정을 해결한 것으로 보고하지 않는다. J의 실제 자료 연결 전에는 분기 선택·공식 source 재확인·새 확인본/정책 버전·DRAFT/coverage를 별도로 확정해야 한다.

## 19. synthetic fixture 전략

| 방법 | 영향 | 결정 |
|---|---|---|
| 기존 policies_m11.json 확장 | 기존 정책 구조와 테스트 의미를 바꾸고 원본 회귀 비교가 어려워짐 | 미채택 |
| 별도 policies_m11_birth.json 추가 | 기존 fixture 불변, 새 지원 종류를 독립 검증 가능 | **채택** |

후속 파일 후보는 **data/synthetic/policies_m11_birth.json**이다. 이번에는 만들지 않는다. schema_version=m1.1, dataset/각 Policy flags=True/True, SYNTH-* ID·합성 이름·임의 구간(예: 1998-01-10~1999-01-09)과 합성 ref를 사용한다. 실제 정책 ID/날짜/공식 URL/locator는 넣지 않는다.

최소 파일은 atomic/resident/birth를 가진 단일 mixed Policy로 충분하다. standalone/ANY/NOT/중첩·잘못된 입력은 이를 복사한 메모리 payload로 검증할 수 있다. 사용자 BirthFact/resident Facts와 reference context는 명시적 합성 입력으로 전달하고 영구 저장하지 않는다. 합성 ref가 기존 sources.json에 실제로 존재한다고 주장하지 않으며 기존 source fixture를 억지로 바꾸지 않는다.

## 20. error contract

| 오류 | 처리 / 책임 |
|---|---|
| 잘못된 JSON 문법/파일/인코딩/중복 JSON key | 기존 load_policy_set의 PolicyDataError 경계. 부분 결과 없음 |
| unsupported kind/rule_type/schema | 기존 PolicyDataError. 버전 fallback 없음 |
| missing/unknown key, 잘못된 배열 | 기존 structural helper 오류를 parse_policy_set이 PolicyDataError로 정규화 |
| 날짜 타입/형식/달력 오류 | 새 작은 날짜 helper의 PolicyDataError. 값 자동 보정 없음 |
| min > max | 기존 BirthDateRule PolicyDataError 전파. 모델 비교 복제 없음 |
| ID 중복/flag/container 불일치 | 기존 Policy/PolicySet 검증 |
| 잘못된 Envelope metadata | 기존 EnvelopeValidationError. 내부 rule 오류를 무조건 Envelope 오류로 재포장하지 않음 |
| 형식상 valid하나 없는 실제 evidence ref | parsing과 별개인 source cross-validation 오류 |

새 예외 클래스를 만들거나 Data Error를 정상 UNKNOWN으로 바꾸지 않는다. parse는 입력 dict를 변경하지 않고 I/O를 하지 않는다. load는 기존 JSON 파일 경계를 사용한다. 기존 raw JSON 상수 처리 등 무관한 loader 동작을 이번 작업에서 전면 변경하지 않는다. birth 날짜에 NaN/Infinity처럼 숫자가 전달되면 str 타입 조건에서 거부해야 한다.

## 21. partial load

정책 하나·leaf 하나라도 invalid하면 전체 PolicySet 반환 없이 실패한다. 유효한 앞 정책이 있었다고 먼저 반환하거나 malformed child를 건너뛰지 않는다. Envelope 안의 birth도 실패하면 Envelope 전체가 반환되지 않는다.

중간의 지역 변수로 객체가 만들어지는 것과 외부에 부분 성공값을 제공하는 것은 다르다. 기존 all-or-nothing 반환 계약을 유지하고 에러를 빈 정책/UNKNOWN 상태로 바꾸지 않는다.

## 22. semantic equivalence

후속 I에서 JSON-loaded BirthDateRule과 독립 hand-built Rule의 전체 객체 의미가 같음을 검증한다. rule_id, exact date min/max, evidence tuple 내용·순서·중복, 트리 children과 root 순서를 포함한다.

같은 합성 Fact로 독립 evaluator 결과 객체와 to_dict 전체를 비교한다. PASS/BEFORE/AFTER/Fact 없음/날짜 없음·source variant를 확인한다. JSON 문자열 날짜가 도메인에 그대로 남지 않고 date로 변환됐는지 확인한다. min=max/윤년과 임의 구간으로 실제 Q3 하드코딩이 없음을 검증한다.

기존 m1.0 fixture와 기존 m1.1 atomic/resident fixture의 loaded 객체·평가·직렬화 결과도 그대로여야 한다. additive schema 확장이 기존 의미를 바꾸지 않았다는 근거로 사용한다.

## 23. Loader → Routing integration

합성 파일 load_policy_set → PolicySet.policies에서 단일 Policy 선택 → 명시적 UserProfile/EvaluationContext/EvaluationFacts(birth=...)/필요한 resident reference → 기존 evaluate_policy_tree → 기존 birth evaluator → RuleEvaluation/PolicyEvaluation 직렬화까지 검증한다.

PolicySet.schema_version만 보고 새로운 batch 평가 entrypoint를 만들지 않는다. loaded vs hand-built의 root-first 결과·reason/missing/evidence/details/context/rule_version 전체를 비교한다. parser/loader가 상태를 계산하거나 routing이 JSON을 읽지 않는다. 실제 Q3 출처 데이터는 사용하지 않는다.

## 24. 기존 rejection test 전환 대상

아래 세 함수가 정확한 후속 변경 후보다. **이번 H에서는 그대로 유지한다. I 지시에서 해당 기대값 전환을 명시적으로 승인한 뒤 갱신한다.** 테스트를 삭제하거나 다른 미지원 값 거부를 무력화하지 않는다.

| 현재 함수 | 이전 기대 → I의 새 기대 |
|---|---|
| tests/test_birth_date_rule.py::test_m11_loader_does_not_accept_birth_date_rule | 유효 birth JSON 거부 → 같은 payload가 BirthDateRule로 로드되고 min/max·refs가 동일함 |
| tests/test_birth_routing.py::test_m11_birth_json_still_fails_without_loader_changes | 유효 m1.1 birth 거부 → 로드 후 기존 routing으로 동일 결과 생성 |
| tests/test_birth_routing.py::test_policy_set_birth_is_blocked_until_loader_schema_support | m1.0/m1.1 두 param 모두 거부 → **m1.0 거부 유지**, m1.1 param만 정확한 birth Policy 보존 허용 |

세 함수 중 guard 테스트는 두 실행 사례 중 **m1.1 하나만** 달라진다. m1.0·unknown rule_type·오타·미지원 m1.2·strict 키/타입 거부 기대는 유지한다. 새로운 m1.0 birth JSON 거부 회귀도 추가한다. 기능 추가에 따라 과거 birth 거부가 valid로 바뀌는 것을 숨기지 않는다. 추가 충돌을 발견하면 임의로 테스트를 고치지 않고 먼저 범위를 보고한다.

## 25. 수동 JSON 시나리오

아래 **48개는 설계 기대값**이며 현재 parser에 새 테스트를 실행한 결과가 아니다. 기본은 6절의 합성 leaf를 m1.1 PolicySet에 포함한 입력이다. ACCEPT는 구조 load이며 사용자 자격/공식성 승인이 아니다.

| ID | 입력 변화 / 검증점 | 후속 기대 |
|---|---|---|
| BL01 | 기본 birth leaf | ACCEPT, 정확한 BirthDateRule/date |
| BL02 | min=max=1998-01-10 | ACCEPT, 하루 구간 |
| BL03 | min=max=2000-02-29 | ACCEPT, 윤년 date |
| BL04 | min=2001-02-29 | REJECT, 달력 오류 |
| BL05 | min=1998/01/10 | REJECT, 형식 오류 |
| BL06 | max=1999-1-9 | REJECT, 자리수 오류 |
| BL07 | min에 T 시각 문자열 | REJECT, datetime 문법 |
| BL08 | max에 공백 시각 문자열 | REJECT, datetime 문법 |
| BL09 | min 누락 | REJECT, 필수 key |
| BL10 | max 누락 | REJECT |
| BL11 | evidence_refs 누락 | REJECT |
| BL12 | evidence_refs가 문자열/dict | REJECT, array 필수 |
| BL13 | evidence 원소가 숫자/None/bool | REJECT |
| BL14 | evidence_refs=[] | REJECT, 근거 필수 |
| BL15 | ref 두 개와 같은 ref 중복 | ACCEPT, 순서/중복 보존 |
| BL16 | extra age 또는 quarter | REJECT, 추가 key |
| BL17 | rule_type 누락 | REJECT, 모양 추정 없음 |
| BL18 | rule_type=BIRTH_DATE | REJECT, 자동 case 보정 없음 |
| BL19 | rule_type=unknown | REJECT |
| BL20 | ALL(resident,birth) | ACCEPT, 재귀 타입 보존 |
| BL21 | ANY(atomic,birth) | ACCEPT |
| BL22 | NOT(birth) | ACCEPT |
| BL23 | ALL(atomic,ANY(resident,NOT(birth))) | ACCEPT, 순서 보존 |
| BL24 | atomic/birth 같은 ID | REJECT, 기존 중복 검증 |
| BL25 | resident/birth 같은 ID | REJECT |
| BL26 | birth JSON에 schema_version=m1.0 | REJECT, 구버전 계약 유지 |
| BL27 | birth JSON에 schema_version=m1.1 | ACCEPT, 정확한 새 분기 |
| BL28 | hand-built와 loaded Rule 비교 | 전체 객체 의미 동일 |
| BL29 | loaded Rule + 구간 안 합성 Fact | 기존 router에서 birth leaf PASS |
| BL30 | 유효 정책 뒤 malformed birth 정책 | 전체 load failure, 앞 정책만 반환 금지 |
| BL31 | min > max | REJECT, BirthDateRule 오류 전파 |
| BL32 | min/max의 null/bool/숫자 | REJECT, 필수 date text |
| BL33 | 날짜 앞뒤 공백/Z suffix/주차 ISO/기본형 | REJECT, 정확한 형식만 |
| BL34 | parse 입력에 date/datetime 객체 | REJECT, JSON 경계 문자열 필요 |
| BL35 | min=0000-01-01 | REJECT, Python date 범위 |
| BL36 | 비ASCII 숫자 날짜 | REJECT, ASCII 계약 |
| BL37 | 파일 birth object에 중복 min key | REJECT, 기존 duplicate-key hook |
| BL38 | birth/birth 또는 group/birth ID 충돌 | REJECT |
| BL39 | 다른 Policy와 birth ID 충돌 | REJECT, dataset 전역 검사 |
| BL40 | group에 rule_type=birth_date | REJECT, group 문법 유지 |
| BL41 | birth에 birth_source/inclusive 옵션 | REJECT, Rule 필드 아님 |
| BL42 | valid synthetic Envelope의 embedded birth/맞는 coverage | 구조 load ACCEPT. Registry 존재 검증과 별개 |
| BL43 | BL42에서 coverage에 birth ID 누락 | REJECT, 기존 Envelope 검증 |
| BL44 | 같은 valid ref 중복을 독립 Rule에 사용한 후 Envelope로 감쌈 | Rule load ACCEPT, Envelope에서는 기존 중복 ref 오류 |
| BL45 | 형식상 valid하지만 Registry에 없는 ref | PolicySet parse ACCEPT, 별도 cross-validation REJECT |
| BL46 | loaded Rule + 범위 이전/이후/Fact 없음 | 기존 router에서 BEFORE FAIL/AFTER FAIL/MISSING UNKNOWN |
| BL47 | birth 날짜 키만 있고 kind/rule_type 제거 | REJECT, shape inference 없음 |
| BL48 | 기존 m1.0/m1.1 fixture 재로드·평가 | 기존 결과 전체 동일 |

추가 날짜/배열/키 경계는 parameterized 테스트로 확장할 수 있다. 이는 실제 Q3 데이터·birth locator 발행과 무관하다. UNKNOWN은 유효하게 로드된 Rule에 사용자 Fact가 부족할 때 evaluator가 반환하는 상태다.

## 26. M1.16I 예상 코드 변경

| 영역 | 최소 변경 |
|---|---|
| backend/policy_engine/loader.py | BirthDateRule/date/re import, 작은 필수 날짜 parser, _node의 birth_date 분기 하나 |
| backend/policy_engine/models.py | unconditional birth guard를 m1.0에만 적용. 기존 모든 검증 유지 |
| data/synthetic/policies_m11_birth.json | 별도 합성 fixture 추가. 기존 자료 불변 |
| 신규 loader 테스트 | strict 입력·semantic equivalence·loaded routing·합성 Envelope 전파·기존 회귀 |
| 24절 기존 세 테스트 함수 | 승인된 해당 기대만 새 지원 계약으로 갱신 |
| 문서 | 실제 구현 상태와 미구현 actual Q3 범위 기록 |

변경하지 않을 것: 기존 atomic/resident parser의 의미, SourceRegistry/Source loader, PolicyEnvelope loader, birth evaluator/Rule/Fact/결과 타입, RuleNode/routing/집계, 기존 fixtures, actual sources/Envelope/data/releases, edition 문법·분기 선택·API/UI/LLM. 별도 parser framework·버전 migration 시스템을 만들지 않는다.

## 27. 미해결 문제 / Assumptions

| 항목 | 상태 |
|---|---|
| Assumption A1 | 명시된 m1.1 입력의 birth는 한 구간을 표현. 어떤 지급 분기의 구간인지 외부 자료 선택 책임 |
| Assumption A2 | I는 합성 데이터로 지원을 검증하며 real-data flags의 의미/운영 승인은 바꾸지 않음 |
| 확정 설계 | m1.1 additive, 여섯 필수 key, 정확한 date text, 생성자 range 검증, m1.0 거부, m1.1 guard 허용 |
| 후속 기존 테스트 승인 | 24절 세 함수의 해당 기대 변경을 I 지시에서 명시 승인해야 함. 이번 테스트는 불변 |
| 과거 reader와의 호환 | 예전 m1.1 reader는 birth를 거부함. 새 데이터에 맞는 실행 artifact 확인 필요, 자동 capability 협상은 미구현 |
| 실제 Q3 의미/최신성 | J 전에 공식 자료·새 locator·확인본·정책 버전·coverage를 검토해야 함. loader가 검증하지 않음 |
| 지급 분기/연간 edition | 기존 미결정 유지. Q3를 연간 전체에 적용하지 않도록 실제 데이터 연결 전 결정 필요 |
| source/production acceptance | 구조 parse와 공식 근거·운영 승인·freshness는 구별. 기존 경계 유지 |

독립 JSON loader 구현을 막는 날짜 문법·타입·오류 경계의 미결정은 없다. 실제 자료의 미해결 행정조건을 parser에서 추정하지 않는다.

## 28. 최종 판단

**READY_TO_IMPLEMENT_BIRTH_LOADER**

현재 explicit parser 구조를 유지하며 birth 분기/날짜 경계/PolicySet guard만 최소 확장할 수 있다. 기존 m1.0/m1.1 valid payload 의미를 바꾸거나 새 schema 버전을 도입해야 할 근거는 없다. strict parsing과 실제 공식 정책 검증을 구별하고 후속 테스트 기대 변경 범위까지 특정했다.

**다음 가장 작은 작업 1개:** M1.16I에서 이 계약대로 birth parser·m1.1 guard 전환·별도 합성 fixture와 관련 테스트만 구현한다. 24절의 기존 테스트 세 함수에 대한 해당 기대 갱신 승인 후 진행하고 실제 Q3 자료는 J로 분리한다.

### M1.16H 검증 기록

작업 전 전체 pytest는 **2,160 passed in 7.76s**였다. 이번에 새 실행 테스트나 loader 구현은 없다. 작성 후 기존 backend/tests/data/docs **77개 전부의 SHA256이 동일**함을 확인했다. 추가 파일은 이 문서 하나이며 코드·기존 테스트·fixture·실제 자료·기존 문서는 변경하지 않았다.

필수 28개 절과 BL01~BL48의 순서·중복·누락, JSON 예시의 문법·여섯 key 및 문서 언어를 확인했다. 이는 문서 형식 검증이며 새 parser가 테스트를 통과한 것이 아니다. Git 저장소가 아니므로 파일 해시를 사용했고 적용되는 AGENTS.md는 발견되지 않았다.


## 29. M1.16I — IMPLEMENTED: 합성 Birth JSON → 판정

현재 판단은 **READY_FOR_REAL_Q3_BIRTH_INTEGRATION**이다. 1~28절은 H 당시 설계 기록이며 이 절이 현재 구현 상태다.

loader.py의 명시적 m1.1 dispatch에 birth_date 분기 하나를 추가했다. 필수 key는 kind/rule_type/rule_id/min_birth_date/max_birth_date/evidence_refs 여섯 개이며 선택 필드는 없다. 정확한 str과 ASCII 전체 형식을 검증한 후 date.fromisoformat으로 변환한다. None·date/datetime 객체·기본형/주차형·공백·비ASCII·존재하지 않는 날짜를 거부한다. min ≤ max 검증은 기존 BirthDateRule 생성자에 맡긴다.

evidence_refs는 정확한 JSON list → tuple이며 기존 Rule 생성자가 비어 있지 않은 문자열 근거를 검증한다. 순서·중복을 보존한다. 독립 parser는 canonical ref나 Registry 존재를 검증하지 않는다. 추가 key·잘못된 discriminator·중복 ID/JSON key·잘못된 후속 노드는 전체 로딩 실패이며 UNKNOWN으로 전환하지 않는다.

PolicySet의 birth 금지를 m1.0으로 한정했다. m1.1은 atomic/resident_registration/birth_date/group을 허용한다. m1.0 제한과 미지원 버전 거부는 유지한다. 기존 atomic/resident parser·Rule/Fact/결과·evaluator/router·Envelope loader는 변경하지 않았다. 과거 m1.1 reader는 새 birth 자료를 거부하므로 실행 artifact와 데이터의 지원 기능을 맞춰야 한다. m1.2나 자동 capability 협상은 추가하지 않았다.

### 합성 자료와 검증

새 fixture는 data/synthetic/policies_m11_birth.json 하나다. 합성 서울/종로 지역, 임의 날짜 1998-01-10~1999-01-09, 합성 ID와 true/true flag로 ALL(atomic,resident,birth)을 표현한다. 기존 SYNTH-SOURCE-001 참조를 재사용하며 새 SYNTH-BIRTH-SOURCE-001#birth-date-range는 논리 참조다. 새 birth source는 기존 Registry에 등록되어 있지 않으며 출처 검증 완료를 의미하지 않는다. 기존 sources/fixture는 수정하지 않았다.

작업 전 **2160 passed in 7.04s**, 신규 tests/test_birth_loader.py **156개**, 최종 전체 **2316 passed in 8.56s**다. 날짜/키/버전·ALL/ANY/NOT·복합 중첩·전역 ID 충돌·중복 JSON key·전체 실패·입력 불변성·합성 Envelope 전파를 검증했다. loaded mixed tree와 독립 hand-built 전체 객체 및 PASS/BEFORE FAIL/AFTER FAIL/UNKNOWN 결과·직렬화가 동일하다. 양끝 포함, 날짜 누락 Fact 및 Fact 자체 부재도 검증했다.

승인된 기존 함수 세 개만 갱신했다. 이름은 변경 이력 추적을 위해 유지한다.

| 함수 | 이전 기대 | 현재 기대 / 이유 |
|---|---|---|
| test_m11_loader_does_not_accept_birth_date_rule | 유효 m1.1 birth 거부 | 정확한 BirthDateRule/date 로드. 임시 차단 해제 |
| test_m11_birth_json_still_fails_without_loader_changes | 유효 m1.1 birth 거부 | 로드 후 hand-built와 판정 동일. loader 지원 구현 |
| test_policy_set_birth_is_blocked_until_loader_schema_support | m1.0/m1.1 모두 거부 | m1.0 거부 유지, m1.1 허용. schema 지원 구현 |

기존 2160개 실행 사례에서 위 세 함수의 m1.1 기대만 변경했다. Envelope는 합성 payload 복사본으로 구조 전파·coverage·엄격한 근거 검증을 확인했다. Registry 교차검증이나 실제 정책 통합을 뜻하지 않는다.

### 구현 경계

IMPLEMENTED: m1.1 birth_date strict JSON parser, m1.1 PolicySet birth 지원, 합성 Loader → Routing → 기존 birth evaluator → 결과 경로.

NOT IMPLEMENTED: actual Q3 birth data, actual birth locator, actual PolicyEnvelope 통합, quarter selection, new edition syntax. 실제 정책/source/Envelope/data/releases는 변경하지 않았다. parser는 현재일·평가일·신청일·edition·quarter로 구간을 생성하거나 선택하지 않는다.

최종 판단은 합성 경로의 기술적 준비 상태이며 실제 정책 발행 승인이 아니다. 다음 가장 작은 작업은 실제 데이터 변경 전에 Q3 공식 근거·birth locator 후보·연간 edition과 분기 범위의 의미·coverage를 대조하는 통합 설계 검토 한 건이다. 연간 전체에 Q3 조건을 적용하지 않도록 기존 미결정을 먼저 해결해야 한다.

### M1.16I 변경 격리 확인

작업 전 backend/tests/data/docs 78개 파일과 SHA256을 대조했다. 기존 변경 파일은 loader.py/models.py, 승인된 테스트를 담은 두 파일, 위 네 문서로 총 8개이며 나머지 70개는 바이트 단위 동일하다. 새 파일은 합성 fixture와 신규 테스트 모듈 두 개다. 기존 데이터 파일 10개는 모두 동일하다. 두 테스트 모듈에서 승인된 함수 세 개를 제외한 전체 AST가 작업 전과 동일하다. loader의 새 birth 분기를 제외한 기존 _node AST와 나머지 기존 함수 AST도 동일하다.

실제 release 파일의 작업 전/후 동일 SHA256:

| 파일 (data/releases/ansan-youth-2026-10-20-001 기준) | SHA256 |
|---|---|
| README.md | 4183C73C37D3CB7EC76BAD21656B50A2C41B064E1298C2D4934DB0D4E536A09F |
| sources.json | A47E53DA0B298C93C1AD04480E8C7FED96F2E45144AD4D58991C9EC86AAA9E3B |
| policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9C6E22DDC1C936E365ECB9B3BE355A73F8CFBDC6F02F99D66E2FB843E0187025 |

