# 정책 규칙 명세

## 1. 기획 PDF에서 확정된 요구사항

- PASS: 현재 입력 기준으로 조건을 충족한다.
- FAIL: 현재 입력 기준으로 조건을 충족하지 않는다.
- UNKNOWN: 필요한 정보가 없거나 자동 확인할 수 없다.
- 사용자 표시: PASS=이용 가능성 높음, FAIL=현재 조건과 맞지 않음, UNKNOWN=추가 확인 필요.
- 이는 최종 자격 확정이 아니다. 생성형 AI는 상태를 결정하지 않는다.

## 2. 이번 M1에서 승인한 결정

### 데이터 오류와 UNKNOWN

사용자 필드 누락/None, 정책 소득 기준 부재 또는 불일치는 UNKNOWN이다. 누락을 0/False로 대체하지 않는다.

사용자 타입/값 오류는 ProfileValidationError, 정책 JSON/규칙/타입 오류는 PolicyDataError, 평가 컨텍스트 오류는 ContextValidationError다. 모두 EngineValidationError(ValueError)의 하위 예외다. 오류를 판정 상태로 변환하지 않는다.

### 원자 연산자

| 연산자 | 정의 | 타입 |
|---|---|---|
| eq | 같은 타입의 값 일치 | 등록 필드의 타입 |
| in | 비어 있지 않은 같은 타입 후보 중 포함 | JSON 배열, 내부 tuple |
| gte | 값 >= 기준 | 정수 필드만 |
| lte | 값 <= 기준 | 정수 필드만 |

M1 등록 필드: age, region, student_status, employment_status, household_income. 소득 규칙은 FactBasis를 필수로 갖는다. 생활비 monthly_income을 규칙 필드로 사용하면 데이터 오류다.

규칙 기준값 None, 잘못된 타입, 혼합 타입 in 배열, 정의되지 않은 필드/연산자, 알 수 없는 JSON 키, 중복 JSON 키, 빈 파일/잘못된 JSON을 거부한다. JSON 숫자 0과 bool false는 다르다. 문자열 숫자를 자동 변환하지 않는다. 가구소득의 단위·기간·주체·연도·소득 정의는 모두 같아야 비교한다.

### ALL / ANY 진리표

P=PASS, F=FAIL, U=UNKNOWN. 2개 자식에 대한 모든 조합:

| 자식 A | 자식 B | ALL | ANY |
|---|---|---|---|
| P | P | P | P |
| P | F | F | P |
| P | U | U | P |
| F | P | F | P |
| F | F | F | F |
| F | U | F | U |
| U | P | U | P |
| U | F | F | U |
| U | U | U | U |

ALL: 하나라도 F이면 F, 모두 P이면 P, 그 외 U.
ANY: 하나라도 P이면 P, 모두 F이면 F, 그 외 U.
NOT: P→F, F→P, U→U. NOT은 정확히 자식 1개여야 한다.

ALL/ANY는 자식이 최소 1개여야 한다. 빈 그룹이나 NOT의 잘못된 자식 수는 로딩 시 거부한다. 중복 rule_id는 원자·그룹을 포함해 전체 데이터셋에서 거부한다. 각 그룹은 데이터가 정한 논리대로 집계하며 optional/required 별도 플래그는 M1에 없다.

### 결과 집계와 사유

모든 자식을 평가한다. 단락 평가로 미확인 조건을 숨기지 않는다. 최상위 root 결과가 overall_status다. rule_results는 그룹을 포함한 전위 순서(root-first)이며 각 노드에 아래 코드 중 하나가 있다.

| reason_code | 의미 |
|---|---|
| CONDITION_MET | 원자 조건 충족 |
| CONDITION_NOT_MET | 원자 조건 불충족 |
| MISSING_FIELD | 필드 누락 또는 None |
| FACT_BASIS_MISSING | 정책 사실 값은 있지만 소득 기준 누락 |
| FACT_BASIS_MISMATCH | 정책 사실과 규칙 소득 기준 불일치 |
| ALL_PASS / ALL_FAIL / ALL_UNKNOWN | ALL 그룹 집계 |
| ANY_PASS / ANY_FAIL / ANY_UNKNOWN | ANY 그룹 집계 |
| NOT_PASS / NOT_FAIL / NOT_UNKNOWN | NOT 그룹 집계 |

사유 코드에는 사용자 값이나 이름을 삽입하지 않는다. 실제 비교값은 evaluated_value, 요구 조건은 expected_condition에 둔다. 그룹의 evaluated_value는 None이다. evidence_refs는 원자의 합성 규칙 근거 및 그룹 하위 근거의 정렬된 합집합이다.

missing_fields는 미입력 시 해당 필드명이다. 소득 기준 누락/불일치도 재확인이 필요한 household_income을 반환한다. 그룹/정책은 하위 missing_fields의 정렬된 합집합이다. reason_codes는 모든 노드 사유의 정렬된 합집합이다.

### 입력·재현성·버전

프로필과 규칙은 불변 모델이며 내부 컬렉션은 tuple이다. 평가 중 입력을 바꾸지 않는다. 컨텍스트에 date 타입 as_of와 dataset_version을 명시한다. datetime/문자열 자동 변환은 하지 않는다. evaluate_policies는 데이터 버전 불일치를 거부한다. 현재시각·난수·네트워크·eval을 사용하지 않는다.

## 3. 향후 결정해야 할 사항

실제 정책의 원문 근거, 수동 확인 전용 조건, 신청기간, 필수조건 커버리지 검증, 소득 기준표와 날짜 기반 나이 판정, 문자열/지역 정규화, 더 많은 연산자는 후속 작업이다. M1 합성 결과를 실제 신청 자격에 사용하면 안 된다.

## 4. M1.6D — IMPLEMENTED: 결과 계약만 확장

RuleEvaluation은 선택 details(기본 None), 지역 snapshot 관찰값, 주민등록 expected condition, 주민등록 전용 reason Enum을 표현한다. PolicyEvaluation도 전용 reason을 담을 수 있다. 등록 machine path tuple은 유지하며 정책 evidence_refs와 details.evidence의 사용자 사실 근거를 구분한다.

기존 ReasonCode 이름과 주민등록 8개 reason 이름은 바꾸지 않았다. 자유 문자열 사유·오류 상태는 거부한다. 주민등록 사유/정상 상태 조합 검증만 수행하며 실제 지역 판정과 ALL/ANY/NOT 진리표는 변경하지 않는다. ResultValidationError는 정상 판정과 별도 예외 경로다.

expected condition의 APPLICATION_DATE는 결과가 설명하는 기준일 의미다. 새 PolicyRule/RuleNode/연산자/실행 바인딩이 등록됐다는 뜻은 아니다. 주민등록 결과를 자동 생성하는 Adapter도 아직 없다. 현재 엔진은 기존 합성 규칙만 실행한다. 전체 계약과 구현/제안의 경계는 RESOLVER_RULE_ADAPTER_SPEC.md 20절을 따른다.

## 5. M1.7 — IMPLEMENTED: m1.1 합성 mixed-rule Loader

앞의 4절은 M1.6D 당시 기록이다. 현재는 주민등록 모델·Resolver·Adapter·단일 Policy routing과 아래 버전별 Loader가 구현돼 있다. 실제 정책 전체의 실행은 지원하지 않는다.

| 버전 | 원자 leaf | 주민등록 leaf | 그룹 |
|---|---|---|---|
| m1.0 | 기존 kind=rule. rule_type 불허 | 불허 | 기존 kind=group |
| m1.1 | kind=rule, rule_type=atomic 필수 | kind=rule, rule_type=resident_registration 필수 | 기존 kind=group. rule_type 불허 |

M1.7 지시문의 rule_type=group은 예시 후보이므로, 승인된 RULE_ROUTING_SPEC 14절의 명시적 kind discriminator를 유지했다. group은 kind로, leaf 세부 종류는 rule_type으로 구분한다. shape 기반 추론이나 두 문법의 자동 혼용은 없다.

parse_policy_set은 schema_version의 존재/정확한 str 타입/지원 값을 **노드 파싱 전에** 검증한다. m1.0/m1.1만 허용하고 누락·None·숫자·미지원 버전은 schema_version을 명시한 PolicyDataError다. 버전 fallback/최신 추정은 없다.

두 버전의 원자 파싱은 공통 _atomic을 사용한다. field/operator/value/fact_basis/evidence_refs 의미와 엄격한 타입은 그대로다. 주민등록은 정확한 sido/sigungu object를 RegionRef로 검증하고 APPLICATION_DATE Enum으로 변환한다. evidence_refs는 JSON list에서 tuple로 바꾼다. 지역 alias/문자열 숫자/출처 보정은 없다.

envelope/policy/group/leaf/region 모두 허용 키 외 필드를 거부한다. 필수 키·자식 수·중복 JSON 키·정책/전역 rule_id 유일성도 유지한다. 잘못된 정책 하나라도 있으면 PolicySet 반환 없이 전체 로드가 실패한다. invalid JSON은 UNKNOWN이 아니며, 유효 정책에 사용자 fact가 없는 평가 UNKNOWN과 구분한다.

PolicySet도 같은 지원 버전 검증을 사용하고 m1.0의 specialized 금지는 유지한다. 기존 ENGINE_VERSION은 변경하지 않는다. 합성/test_only=True 제한은 두 버전에 동일하게 적용한다. 실제 정책 JSON·Birth/History/Income/ApplicationWindow는 미구현이다. 최신 Loader 계약과 검증 기록은 RULE_ROUTING_SPEC.md 23절이다.


## 6. M1.16I — IMPLEMENTED: m1.1 Birth JSON

앞 절의 birth loader 미구현 표시는 각 단계 당시 기록이다. 현재 m1.1 leaf는 atomic/resident_registration/birth_date를 명시적 rule_type으로 구분한다. group은 기존 kind=group이며 rule_type을 허용하지 않는다. m1.0은 atomic/group만 지원하고 birth/resident를 거부한다. m1.2는 지원하지 않는다.

birth는 kind/rule_type/rule_id/min_birth_date/max_birth_date/evidence_refs 여섯 필수 key만 받는다. 날짜는 정확한 ASCII YYYY-MM-DD 문자열과 실제 달력 유효성을 검증하여 date로 변환한다. 범위 순서는 기존 Rule 생성자가 검증하며 양끝 포함이다. 근거는 JSON list에서 tuple로 변환하고 순서·중복을 보존한다. 독립 parser의 근거 존재 검증과 Envelope의 canonical/중복 검증은 별개다.

중첩 ALL/ANY/NOT·ID 유일성·중복 JSON key·전체 실패 계약을 유지한다. 잘못된 자료는 PolicyDataError이며 사용자 사실 누락의 UNKNOWN과 구별한다. IMPLEMENTED: m1.1 birth_date JSON parser, PolicySet m1.1 birth support, synthetic Loader → Routing. NOT IMPLEMENTED: actual Q3 birth data/locator/Envelope 통합, quarter selection. 상세 검증과 승인된 기존 테스트 세 함수는 REAL_POLICY_001_BIRTH_LOADER_SPEC.md 29절을 따른다.

