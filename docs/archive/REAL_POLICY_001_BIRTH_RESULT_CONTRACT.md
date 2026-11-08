# 생년월일 leaf 결과 계약 — M1.16C

현재 결과 모델은 24절 M1.16D, 독립 evaluator는 25절 M1.16E 기록을 따른다. 1~23절의 문서 전용 작업과 NEEDS_RULE_EVALUATION_EXTENSION 판단은 M1.16C 당시 기록이다.

작성일: 2026-10-20 / Asia/Seoul. **설계 문서이며 구현이 아니다.** 기존 파일은 변경하지 않고 이 문서 하나만 추가한다.

최종 판단: **NEEDS_RULE_EVALUATION_EXTENSION**. BirthFact/BirthDateRule의 구조 모델은 존재하지만 현재 공통 결과 모델은 birth 결과를 거부한다. 후속 최소 결과 모델 확장 이후에 evaluator를 구현한다.

## 1. 목적

BirthDateRule과 단일 BirthFact를 비교한 결과를 기존 RuleEvaluation과 동일한 수준으로 설명·추적·직렬화할 계약을 정의한다. 범위·관찰 날짜·이유·사용자 provenance·정책 근거의 책임을 분리한다. birth leaf PASS는 전체 정책 자격·신청/수급 확정이 아니다.

검토한 문서: REAL_POLICY_001_BIRTH_SLICE_SPEC.md(특히 7~12절 및 19~20절), POLICY_RULE_SPEC.md, RULE_ROUTING_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 실제 models.py/result_types.py, 주민등록 reason/Resolver/Adapter, evaluator의 집계/결과 조립과 _jsonable도 확인했다.

이 문서의 날짜 예시는 M1.16에서 확인한 Q3 구간을 사용한다. 이번에는 공식 자료 최신성을 다시 검증하는 작업이나 실제 데이터 발행을 수행하지 않는다. 새 source locator·정책 JSON·Envelope·schema는 생성하지 않는다.

## 2. 기존 RuleEvaluation 분석

현재 클래스 필드는 rule_id/status/reason_code/evaluated_value/expected_condition/missing_fields/evidence_refs/details다. 실제 상태 Enum의 이름은 **Status**이며 값은 PASS/FAIL/UNKNOWN이다. EvaluationStatus라는 별도 타입은 없다. 이번에 새 상태 Enum을 제안하지 않는다.

| 영역 | 현재 구현 | birth 수용에 필요한 최소 변경 |
|---|---|---|
| evaluated_value | str/int/bool/RegionSnapshot/None만 허용 | BirthDateCondition 분기에서 정확한 date/None 추가 |
| expected_condition | ExpectedCondition/GroupCondition/ResidentRegistrationCondition만 허용 | BirthDateCondition 추가 |
| reason_code | ReasonCode와 주민등록 전용 Enum만 허용 | BirthDateReasonCode 유한 목록 추가 |
| details | EvaluationDetails는 ResidentRegistrationDetails 단일 클래스이며 exact type 검사 | BirthDateDetails를 유한 union에 추가하고 실제 타입 검사를 명시적 허용 목록으로 변경 |
| condition별 결과 검사 | resident 분기 이외의 specialized 값·details·reason 거부 | birth 전용 정합성 분기 추가. 기존 atomic/resident 조건은 유지 |
| PolicyEvaluation.reason_codes | 공통 _validate_result_reason을 호출 | 같은 birth Enum을 허용해야 정책 결과 조립 가능 |
| missing_fields | dotted lower_snake_case 경로 tuple 허용 | 새 문법 불필요. birth.birth_date를 계약으로 지정 |
| _jsonable | date는 ISO, Enum은 value, tuple은 list, dataclass는 필드 순회 | 기존 재귀 직렬화를 재사용 가능 |

**결론:** 새 top-level birth 전용 필드를 추가할 필요는 없다. 그러나 typed details만 추가해도 나머지 exact 타입/분기 검증이 거부하므로 **RuleEvaluation의 허용 타입과 검증 확장은 필수**다. generic dict로 우회하거나 date를 문자열/int로 위장하지 않는다. RuleNode/Policy/routing 확장은 별개다.

### 표현 배치 비교와 결정

| 배치 | 장단점 | 판단 |
|---|---|---|
| 기존 필드에 범위/관찰값, typed details에는 provenance만 | 기존 POLICY_RULE_SPEC의 관찰값= evaluated_value, 요구조건=expected_condition 의미를 유지. 날짜 중복 없음 | **채택** |
| details에 condition/observed/source 모두 넣고 기존 값 필드 None | date 허용 확장은 피하지만 이미 아는 관찰값을 공통 필드에서 누락하고 요구조건 위치가 달라짐. condition 허용 확장도 여전히 필요 | 미채택 |
| 기존 필드와 details에 같은 범위/관찰값을 모두 저장 | 중복 검증과 개인정보 복제가 늘어남 | 미채택 |

사용자 지시문의 BirthDateDetails 세 필드는 후보로 검토했다. 이번 추천은 중복을 피하는 더 작은 구조다. 실제 비교 정보는 **RuleEvaluation 전체**에서 완전하게 추적된다.

## 3. BirthDateCondition

추천: frozen/slots 결과 전용 값 객체.

| 필드 | 계약 |
|---|---|
| min_birth_date | 필수, 정확한 date |
| max_birth_date | 필수, 정확한 date. min ≤ max |

양끝 포함은 고정 의미다. age/calculated_age/application_date/evaluation_date/quarter/inclusive 플래그를 넣지 않는다. 같은 날짜 구간은 유효하다. datetime/date 하위 타입/문자열/None/숫자는 거부한다.

RuleEvaluation.expected_condition에 둔다. BirthDateRule 자체를 보관하지 않고 필요한 날짜 값만 복사하며 Rule/Fact/프로필의 참조를 갖지 않는다. 결과 모델의 날짜 오류·역전 범위는 기존 ResultValidationError 계열로 거부하는 후속 계약이다.

## 4. BirthDateDetails

추천: frozen/slots 결과 전용 `BirthDateDetails(birth_source: BirthSource | None)`.

- source는 정확한 BirthSource 또는 None. None은 **BirthFact 자체가 없을 때**의 provenance 부재다.
- Fact가 존재하고 birth_date만 None이면 입력 BirthSource를 보존한다.
- 관찰 출생일은 RuleEvaluation.evaluated_value에만 둔다.
- 조건은 RuleEvaluation.expected_condition에만 둔다.
- condition/observed_birth_date를 details에 다시 넣지 않는다. age·분기·현재 날짜도 넣지 않는다.
- birth 결과에는 BirthDateDetails 객체가 필수다. details=None, resident details, generic dict는 birth 결과 계약 오류다.

### typed details 방식 비교

| 방식 | 안전성 / 기존 구조와의 관계 | 판단 |
|---|---|---|
| A. 새 BirthDateDetails | 유한 타입·provenance 검증이 명확. resident details의 책임을 그대로 보존 | **채택** |
| B. generic dict | 키 오타·다른 Enum·날짜 타입·입력 전체 유출을 모델이 막기 어려움 | 미채택 |
| C. atomic details 재사용 | 현재 atomic 전용 details 클래스 자체가 없고 atomic 결과의 details는 None. 재사용할 구조 없음 | 불가 |

현재 `type(details) is EvaluationDetails` 검사는 alias를 union으로 바꾸는 것만으로 작동하지 않는다. 후속 구현은 정확한 concrete 타입 목록을 검사해야 한다. 주민등록의 조건·값·details 조합은 기존대로 유지한다.

## 5. reason codes

독립 `BirthDateReasonCode(str, Enum)` 후보 네 개를 고정한다. 자유 문자열이나 기존 atomic reason을 빌려 쓰지 않는다. Enum은 result_types 등 models를 역참조하지 않는 결과 값 계층에 두는 방식을 추천한다. 정확한 모듈 export는 후속 결과 모델 작업에서 정하되 순환 import를 피한다.

| 코드 | 상태 | 의미 |
|---|---|---|
| BIRTH_DATE_WITHIN_RANGE | PASS | 양끝 포함 범위 안 |
| BIRTH_DATE_BEFORE_RANGE | FAIL | 최소 출생일보다 이전 |
| BIRTH_DATE_AFTER_RANGE | FAIL | 최대 출생일보다 이후 |
| BIRTH_DATE_MISSING | UNKNOWN | 출생일을 알 수 없음 |

FAIL 하나(OUTSIDE/OUT_OF_RANGE)는 단순하지만 설명자가 방향을 다시 계산해야 한다. 두 개로 나누면 두 비교 분기와 직접 대응하고 “대상 범위보다 이른/늦은 출생일”을 재판정 없이 설명할 수 있다. 추가 비용이 작으므로 **BEFORE/AFTER 분리를 채택**한다.

M1.16의 BIRTH_DATE_IN_RANGE/OUT_OF_RANGE/BIRTH_FACT_MISSING 및 두 종류의 missing 경로는 당시 제안이었다. **이번 직접 지시를 반영한 후속 결과 계약은 위 네 코드와 단일 경로를 우선한다.** 기존 코드/Enum에는 아직 birth reason이 없으므로 기존 실행 계약 변경은 없다. 역사적 문서는 이번에 수정하지 않는다.

## 6. PASS 계약

조건: 유효한 Fact의 정확한 date에 대해 `min ≤ birth_date ≤ max`.

| 결과 필드 | 값 |
|---|---|
| status / reason_code | PASS / BIRTH_DATE_WITHIN_RANGE |
| evaluated_value | 관찰 출생일 date |
| expected_condition | BirthDateCondition의 공식 요구 구간 |
| details.birth_source | 입력 BirthSource 그대로 |
| missing_fields | 빈 tuple |
| evidence_refs | Rule의 tuple 그대로 |

source는 반드시 존재해야 한다. 출생일만 있고 source가 None인 정상 PASS를 만들지 않는다. “전체 정책 대상자”라는 결과 문구·별도 boolean은 추가하지 않는다.

## 7. FAIL 계약

정상 date가 min보다 작으면 BIRTH_DATE_BEFORE_RANGE, max보다 크면 BIRTH_DATE_AFTER_RANGE다. evaluated_value/expected_condition/details.birth_source/evidence_refs는 PASS와 같은 수준으로 보존하고 missing_fields는 빈 tuple이다.

FAIL은 잘못된 입력이라는 뜻이 아니다. 달력상 유효한 입력이 요구 구간 밖이라는 뜻이다. min=max이면 그 날짜만 PASS가 될 수 있으며 앞/뒤는 각각 다른 FAIL 사유다. 존재하지 않는 날짜·타입 오류·거꾸로 된 Rule은 이 경로로 보내지 않는다.

## 8. UNKNOWN 계약

두 미입력을 제품의 추가 확인 요구로 동일하게 처리한다.

| 입력 | status / reason | evaluated_value | details.birth_source | missing_fields |
|---|---|---|---|---|
| birth_fact=None | UNKNOWN / BIRTH_DATE_MISSING | None | None | (birth.birth_date,) |
| BirthFact(birth_date=None, source=유효 Enum) | UNKNOWN / BIRTH_DATE_MISSING | None | 입력 source | (birth.birth_date,) |

범위와 정책 근거는 UNKNOWN에서도 존재해야 한다. 두 경우의 reason/missing_fields는 같지만 실제 받은 provenance는 보존하므로 JSON 전체가 반드시 같지는 않다. source=None과 OFFICIAL_DATA 등을 임의로 통일하지 않는다.

BirthFact가 잘못된 타입이거나 birth_date=None에 잘못된 source를 넣은 경우는 UNKNOWN이 아니다. Rule 구조 검증을 우선하고 미입력 때문에 잘못된 Rule을 정상 결과로 만들지 않는다.

## 9. Data Error와 결과 정합성

| 오류 | 후속 처리 계약 |
|---|---|
| rule이 정확한 BirthDateRule이 아님 / min > max / 규칙 날짜·근거 구조 오류 | PolicyDataError 계열 |
| birth_fact가 정확한 BirthFact 또는 None이 아님 / 잘못된 source·날짜 타입 | 기존 ProfileValidationError/BirthFactValidationError 계열 |
| list/tuple의 복수 Fact 전달 | 단일 입력 계약 오류. 병합·source 우선 선택 없음 |
| 결과 condition/details/reason/status 조합 오류 | ResultValidationError 계열 |
| source/locator/버전/적용 정책 불일치 | 기존 근거 검증 계층의 오류. leaf 함수의 조회 책임은 아님 |

모든 오류는 정상 RuleEvaluation 없이 예외로 전파한다. Status에 DATA_ERROR를 추가하거나 UNKNOWN으로 치환하지 않는다. None 인자와 계약과 다른 객체를 구별한다. 실제 값이나 프로필 전체를 오류 메시지에 넣지 않는다.

### 후속 결과 모델의 최소 정합성 검증

- BirthDateCondition이면 BirthDateReasonCode와 정확한 BirthDateDetails가 필요하다.
- birth의 evaluated_value는 정확한 date 또는 None만 허용한다. atomic 결과에 date를 넣는 것은 계속 거부한다.
- WITHIN은 PASS, BEFORE/AFTER는 FAIL, MISSING은 UNKNOWN으로 고정한다.
- PASS/FAIL은 관찰 date·유효한 BirthSource·빈 missing_fields를 요구한다.
- UNKNOWN은 관찰값 None과 정확히 (birth.birth_date,)를 요구한다. birth_source는 None 또는 유효 Enum이다.
- 다른 condition에 birth reason/details를 섞거나 birth condition에 resident reason/details를 섞으면 거부한다.
- birth 결과에는 Rule에서 전달받은 비어 있지 않은 근거 문자열 tuple을 요구한다. 독립 구조 모델처럼 순서/중복을 보존하며 자동 출처 조회는 하지 않는다.

범위의 실제 대소 비교와 before/within/after 선택은 **향후 evaluator 한 곳**에서 수행한다. 결과 생성자는 타입·상태/사유·누락 조합을 검사하며 별도 두 번째 정책 비교 엔진을 만들지 않는다. 그러므로 수동으로 만든 결과 객체의 구조 검증 성공만으로 실제 비교가 올바르다는 뜻은 아니다. 후속 evaluator의 경계 테스트로 그 의미를 검증한다.

## 10. missing_fields

canonical path는 **birth.birth_date** 하나로 확정한다. 현재 regex가 허용하는 dotted lower_snake_case 규칙과 일치한다. 이 경로는 논리적인 사실 필드명이며 현재 API/JSON Loader에 birth 필드가 이미 구현됐다는 뜻이 아니다.

PASS/FAIL은 `()`, 두 UNKNOWN은 `("birth.birth_date",)`다. JSON에서는 각각 `[]`, `["birth.birth_date"]`다. age·source·정책 날짜·전체 BirthFact 경로를 추가하지 않는다. source가 잘못됐으면 missing이 아닌 오류다. 미래 그룹/정책 집계는 기존 정렬된 중복 제거 합집합을 사용한다.

## 11. User Fact evidence

사용자 근거는 **evaluated_value의 날짜 + details.birth_source**라는 최소 값 snapshot이다. BirthFact 객체·UserProfile 전체·원본 증빙·사용자 ID를 보관하지 않는다. fact가 없으면 두 값 모두 None이다.

현재 EvaluationEvidence는 RegistrationSource, fact_as_of_date, RegionSnapshot, RESIDENT_REGISTRATION 및 고정 field_path만 허용하는 **주민등록 전용 구조**다. 이름이 일반적이라는 이유로 재사용하지 않는다. 출생일에 임의 as_of_date/region을 만들거나 정책 ref를 그 객체에 넣지 않는다.

이번 단일 사실은 선택된 여러 Fact 목록이 없어 별도 BirthEvidence collection도 필요 없다. 향후 복수 provenance가 실제로 필요해질 때 별도로 검토한다. dates/source를 보존하는 원칙은 resident와 같고 필드 구조는 의미에 맞게 작게 유지한다.

## 12. Policy evidence

RuleEvaluation.evidence_refs는 **정책 원문 근거**다. User Fact provenance와 섞지 않는다. PASS/FAIL/UNKNOWN 모두 입력 Rule의 ref 순서·내용을 그대로 보존한다. 그룹은 기존 규칙에 따라 정렬된 합집합을 만들 수 있으나 leaf 결과는 임의 정렬·중복 제거하지 않는다.

독립 evaluator는 SourceRegistry/파일/URL을 받거나 조회하지 않는다. 잘못된 tuple/빈 ref 등 구조 오류는 규칙/결과 경계에서 거부한다. 구조적으로 유효한 canonical ref의 존재·문서 확인본·locator 수명·적용 정책 검증은 향후 호출자가 명시적으로 수행하는 기존 envelope/source 경계 책임이다. 검증하지 않은 ref가 evaluator를 통과했다고 공식 근거를 확인한 것으로 표현하지 않는다.

현재 실제 registry에는 birth locator가 없다. M1.16에서 제안한 Q3 locator는 아직 미발행이다. 아래 JSON의 SYNTH-SOURCE-001#birth-date-range도 **설명용 합성 문자열**이며 현재 registry에서 resolve됐다는 뜻이 아니다. 실제 Q3 range와 근거 내용의 일치 검토는 후속 실제 데이터 acceptance에 남는다.

## 13. BirthSource 의미

SELF_REPORTED / MANUALLY_VERIFIED / OFFICIAL_DATA는 기존 별도 BirthSource Enum 그대로다. 동일 Rule/출생일이면 source 변경은 provenance만 바꾸며 status/reason/missing_fields는 바꾸지 않는다. 전체 JSON에는 source 차이가 남는 것이 맞다.

RegistrationSource나 임의 문자열은 결과의 BirthSource로 자동 변환하지 않는다. 알려진 출생일과 source=None은 모순 결과다. source 표식은 행정기관 인증·생년월일 진위·production 승인·정책 적용 우선순위를 자동 입증하지 않는다.

## 14. Evaluation / Application Date 독립성

고정된 같은 Rule/Fact의 **leaf JSON은 평가일·신청일 변경과 무관**하다. evaluator는 이 날짜를 인자로 받지 않고 나이를 재계산하지 않는다. 신청일이 None이거나 미래여도 birth 비교 자체는 바뀌지 않는다. resident leaf의 기준일 UNKNOWN과 구별한다.

상위 PolicyEvaluation.context.as_of는 명시적인 재현 정보이므로 평가일을 바꾸면 **정책 결과 JSON 전체는 달라진다**. “결과 동일”은 birth leaf만의 계약이다. 선택된 지급 분기가 바뀌어 다른 Rule을 사용하면 입력 Rule이 달라진 것이므로 동일성 전제가 성립하지 않는다.

## 15. UserProfile.age 독립성

evaluator는 UserProfile을 받지 않는다. age=23/25여도 출생일이 공식 구간 안이면 leaf PASS이고 age=24라도 Fact가 없으면 UNKNOWN이다. 유효한 범위 밖 출생일은 age=24라는 이유로 PASS로 바꾸지 않는다. 두 필드의 기준일을 모르므로 birth 함수가 임의의 불일치 오류도 만들지 않는다.

## 16. evaluator API 후보

추천 후속 함수: `evaluate_birth_date_rule(rule: BirthDateRule, birth_fact: BirthFact | None) -> RuleEvaluation`.

두 인자를 명시적으로 받고 BirthFact 부재는 None으로 전달한다. M1.16의 fact=None 기본값 후보보다 호출자의 미입력을 분명히 드러내는 계약으로 정리한다. profile/context/registry/application_date/evaluation_date/quarter는 받지 않는다.

| 후보 | 판단 |
|---|---|
| 최소 Rule/Fact 인자만 | **채택**. 실제 의존성과 일치, 시각 비의존성 테스트가 명확함 |
| routing과 모양을 맞추기 위해 context를 추가 | 사용하지 않는 인자와 기준일 혼동이 늘어남. 향후 router가 상위 context를 보유하고 leaf에는 필요한 입력만 전달하면 됨 |

순수 typed 입력 검증 → 미입력 분기 → 한 번의 날짜 범위 비교 → 직접 RuleEvaluation 조립 순서다. 현재 constructor가 이미 구조 검증한 값이라도 함수 경계에서 정확한 객체 타입을 검증한다. 문자열 파싱·미래 날짜 보정·복수 Fact 병합·실시간 조회를 하지 않는다. 실제 함수는 이번에 구현하지 않는다.

## 17. Resolver 필요 여부

**없음.** 단일 BirthFact에는 주민등록처럼 날짜별 사실 선택이나 신청 기준일 바인딩이 없다. Rule과 Fact를 비교하는 작은 함수로 충분하다. 주민등록 Resolver를 일반화하거나 BirthResolution 중간 모델을 만들지 않는다.

## 18. Adapter 필요 여부

| 방식 | 판단 |
|---|---|
| A. evaluator가 직접 RuleEvaluation 생성 | **채택**. 비교와 값 snapshot 변환이 작고 중간 상태가 필요 없음 |
| B. 별도 birth result → Adapter → RuleEvaluation | 이미 독립 Resolver가 있는 resident와 달리 새 중간 모델/복제 필드/변환 계약만 늘어남 |

현 ResidentRegistration Adapter는 그대로 둔다. birth에서 별도 Adapter가 없다는 이유로 기존 주민등록 구조를 수정하지 않는다.

## 19. RuleNode / aggregation 영향

현재 RuleNode/Policy/RuleGroup은 birth 타입을 거부하며 이번에 변경하지 않는다. 미래 연결에서는 유한 RuleNode/root/children 허용 목록과 routing 분기를 명시적으로 확장해야 한다. JSON loader 지원은 그 다음 별도 작업이다.

기존 _aggregate는 Status만으로 ALL/ANY/NOT을 계산하므로 **변경 불필요**다. _assemble_group_result의 전위 순서·근거/누락 합집합, _assemble_policy_result의 reason.value 정렬도 유지할 수 있다. birth reason 문자열은 기존 reason과 충돌하지 않는 네 이름을 사용한다.

다만 공통 reason validator와 PolicyEvaluation이 새 Enum을 허용해야 하며 details/condition 타입 검증도 준비해야 한다. “집계 알고리즘을 바꿀 필요 없음”과 “현재 전체 엔진에 연결 가능”은 다르다. 기존 mixed 결과와 missing_fields를 숨기지 않는 집계 의미도 유지한다.

## 20. serialization

기존 _jsonable 재귀 계약을 따른다. date는 YYYY-MM-DD, Enum은 canonical 문자열, tuple은 list, dataclass는 필드별 새 값으로 표현한다. date를 저장하는 허용 타입만 확장하면 현재 serializer 구현은 재사용할 수 있다. birth 결과는 필수 details가 있으므로 details 생략 규칙의 영향을 받지 않는다. None 값은 null로 보존한다.

### PASS 전체 leaf JSON 예시 — 아직 실행된 출력이 아님

```json
{
  "rule_id": "SYNTH-BIRTH",
  "status": "PASS",
  "reason_code": "BIRTH_DATE_WITHIN_RANGE",
  "evaluated_value": "2001-10-10",
  "expected_condition": {
    "min_birth_date": "2001-07-02",
    "max_birth_date": "2002-07-01"
  },
  "missing_fields": [],
  "evidence_refs": ["SYNTH-SOURCE-001#birth-date-range"],
  "details": {"birth_source": "SELF_REPORTED"}
}
```

### UNKNOWN 전체 leaf JSON 예시 — Fact 없음

```json
{
  "rule_id": "SYNTH-BIRTH",
  "status": "UNKNOWN",
  "reason_code": "BIRTH_DATE_MISSING",
  "evaluated_value": null,
  "expected_condition": {
    "min_birth_date": "2001-07-02",
    "max_birth_date": "2002-07-01"
  },
  "missing_fields": ["birth.birth_date"],
  "evidence_refs": ["SYNTH-SOURCE-001#birth-date-range"],
  "details": {"birth_source": null}
}
```

Fact가 있고 날짜만 None이면 위 UNKNOWN에서 details.birth_source만 실제 입력 Enum으로 바뀐다. FAIL은 같은 전체 구조에서 status=FAIL, reason_code=BEFORE/AFTER의 canonical 코드, evaluated_value=실제 범위 밖 날짜, source=실제 source, missing_fields=[]다.

JSON만으로 범위·관찰값·상태/사유·provenance·정책 ref를 추적할 수 있다. 날짜/조건은 중복 저장하지 않는다. leaf to_dict에는 kind/rule_type/result_type 같은 새 discriminator를 추가하지 않는다. expected_condition의 유한 구조로 내부 결과를 구별하고 미래 외부 API의 식별 schema는 별도 계약으로 남긴다. 이 JSON은 loader 입력이나 공식 source 검증 결과가 아니다.

동일 Rule/동일 Fact 입력이면 동일 값의 dict/JSON을 만들어야 한다. 자동 현재시각/ID/난수는 없다. bytes 수준의 JSON 공백·키 정렬은 호출자의 encoding 옵션에 달렸으므로 해시 프로토콜이 확정됐다고 주장하지 않는다. 기존 dataclass 필드 순서와 고정 encoding 옵션을 사용하면 결정적인 문자열을 만들 수 있다. 입력 객체를 보유하거나 반환 dict 변경으로 원본을 바꿀 수 없어야 한다.

날짜가 결과에 포함되는 것은 이번 추적 계약상 필요한 요청 단위 값 표현이다. 영구 저장·전체 결과 로그·LLM 전송을 허용하는 뜻은 아니다. 사용자 사실은 provenance와 함께 필요한 곳에 한 번만 표현한다.

## 21. 수동 시나리오

아래 **32개는 설계상 기대값이며 신규 실행 테스트가 아니다.** 기본 Rule은 Q3 예시 구간, 근거는 위 합성 ref, 기본 source는 SELF_REPORTED다. WITHIN/BEFORE/AFTER/MISSING은 5절 코드의 접미어 약칭이다. 판정 오류 행과 결과 모델 오류 행을 구별한다.

| ID | 입력 / 확인점 | 기대 상태·reason / 결과 계약 |
|---|---|---|
| BR01 | 2001-07-01 (lower − 1일) | FAIL / BEFORE, 관찰 날짜·source 보존 |
| BR02 | 2001-07-02 (lower) | PASS / WITHIN, 양끝 포함 |
| BR03 | 2001-10-10 (중간) | PASS / WITHIN |
| BR04 | 2002-07-01 (upper) | PASS / WITHIN |
| BR05 | 2002-07-02 (upper + 1일) | FAIL / AFTER |
| BR06 | Fact=None | UNKNOWN / MISSING, 관찰값/source=None |
| BR07 | Fact 날짜=None, SELF_REPORTED | UNKNOWN / MISSING, source는 보존 |
| BR08 | 구간 안 날짜, SELF_REPORTED | PASS / WITHIN |
| BR09 | BR08 날짜, MANUALLY_VERIFIED | PASS / WITHIN, provenance만 변경 |
| BR10 | BR08 날짜, OFFICIAL_DATA | PASS / WITHIN, provenance만 변경 |
| BR11 | age=24, Fact=None | UNKNOWN / MISSING, age fallback 없음 |
| BR12 | age=23, 구간 안 Fact | PASS / WITHIN |
| BR13 | age=25, 구간 안 Fact | PASS / WITHIN |
| BR14 | 고정 Rule/Fact에 평가일 변경 | birth leaf JSON 동일. 상위 context JSON은 달라질 수 있음 |
| BR15 | 고정 Rule/Fact에 신청일 변경/None | birth leaf JSON 동일 |
| BR16 | 합성 min=max=2000-01-10, 같은 날짜 Fact | PASS / WITHIN |
| BR17 | BR16 Rule, Fact=2000-01-09 | FAIL / BEFORE |
| BR18 | BR16 Rule, Fact=2000-01-11 | FAIL / AFTER |
| BR19 | 합성 min=max=2000-02-29, 같은 윤년 Fact | PASS / WITHIN, 나이 산식 없음 |
| BR20 | BR01에서 reason 확인 | BIRTH_DATE_BEFORE_RANGE. FAIL 하나로 합치지 않음 |
| BR21 | BR05에서 reason 확인 | BIRTH_DATE_AFTER_RANGE |
| BR22 | BR06/BR07의 missing_fields | 두 경우 모두 정확히 (birth.birth_date,) |
| BR23 | 모든 정상 상태에 ref 두 개 입력 | 입력 순서·내용 그대로 보존 |
| BR24 | BR03에서 관찰값 확인 | evaluated_value에 date, details에는 날짜 복제 없음 |
| BR25 | 동일 Rule/Fact 두 번 직렬화 | dict/고정 옵션 JSON 동등, 자동 생성값 없음 |
| BR26 | 유효한 범위 밖 Fact, age=24 | FAIL / BEFORE 또는 AFTER, age 영향 없음 |
| BR27 | Rule min > max | DATA ERROR, 정상 결과 없음 |
| BR28 | Fact 대신 dict/복수 Fact list | DATA ERROR, 자동 변환/선택 없음 |
| BR29 | birth_date가 문자열/datetime 또는 source가 다른 Enum | DATA ERROR. 기존 입력 모델이 먼저 거부 |
| BR30 | evidence_refs 빈 tuple/잘못된 원소 | DATA ERROR. source 부재를 UNKNOWN으로 표현하지 않음 |
| BR31 | 수동 birth 결과가 PASS+MISSING 또는 UNKNOWN+관찰 date | ResultValidationError, 상태·사유·값 모순 |
| BR32 | 수동 birth 결과에 resident details 또는 generic dict | ResultValidationError, typed details 불일치 |

관찰 날짜와 before/within/after의 실제 정답은 evaluator 경계 테스트에서 검증할 항목이다. BR31/32는 후속 결과 모델의 수동 생성 테스트로 분리 가능하다. 실제 Q3 데이터가 발행됐거나 현재 RuleEvaluation이 위 예시를 생성할 수 있다고 보고하지 않는다.

## 22. 미해결 질문 / Assumptions

| 항목 | 상태 |
|---|---|
| Assumption A1 | 한 호출은 동일 사용자 한 명의 명시적 Rule/단일 Fact를 받음. provenance 인증과 신원 연결은 범위 밖 |
| Assumption A2 | 지급 분기/대상 Rule은 이미 명시적으로 선택됨. evaluator는 Q3·분기·신청 회차를 선택하지 않음 |
| 확정할 추천 결과 | BirthDateCondition, provenance-only BirthDateDetails, date evaluated_value, 네 reason, 단일 missing 경로. 구현 전 승인 대상인 이 문서의 설계 계약 |
| 결과 모델 구현 | exact 허용 목록/condition별 검증/_validate_result_reason/PolicyEvaluation을 함께 확장해야 함. 기존 타입 검증을 generic하게 느슨하게 하면 안 됨 |
| 후속 모듈 배치 | 새 condition/details/reason은 기존 result_types 계층을 우선 추천. 기존 resident import와의 순환 여부는 구현 시 확인 |
| RuleNode/routing/입력 묶음 | 현재 미지원. 결과 모델/evaluator 구현 이후 별도 연결 계약 필요 |
| JSON loader/version | 현재 m1.1에 birth 문법 없음. 다음 실제 로딩 단계 전 별도 결정 |
| 연도 edition의 분기 선택 | 기존 미결정 유지. 실제 Q3를 연간 정책 전체에 적용하지 않음 |
| 실제 source/정책 버전 | birth locator·확인본·rule_version·coverage·공식 의미 검증은 후속 실제 데이터 단계 |
| 외부 결과 API | 현재 Python 결과 snapshot 계약. OpenAPI/Pydantic/외부 discriminator/version은 이번에 설계·구현하지 않음 |

관찰값·reason·provenance·missing 경로의 추천은 이 문서에서 일관되게 정리했다. 남은 런타임 차단 원인은 현재 결과 모델의 미지원이며, 분기/loader 미결정을 birth 함수 내부 추정으로 채우지 않는다.

## 23. 최종 판단

**NEEDS_RULE_EVALUATION_EXTENSION**

현재 constructor가 date, BirthDateCondition, BirthDateDetails, BirthDateReasonCode를 거부한다. typed details만으로 기존 결과 계약을 우회할 수 없으므로 먼저 유한 결과 타입/검증을 확장해야 한다. 설계 방향을 다시 처음부터 만드는 NEEDS_BIRTH_RESULT_REDESIGN은 아니며 현재 상태에서 evaluator 구현 준비가 모두 완료됐다고 보고하지 않는다.

**다음 가장 작은 작업 1개:** 결과 계층에 BirthDateCondition/BirthDateDetails/BirthDateReasonCode를 추가하고 RuleEvaluation/PolicyEvaluation의 최소 허용 타입·정합성 검증 및 수동 생성/직렬화 테스트만 구현한다. evaluator·RuleNode·routing·loader·실제 자료는 그 작업에 포함하지 않는다.

### 이번 작업 검증 기록

작업 시작 시 전체 pytest는 **1,939 passed in 6.88s**였다. 문서 전용 작업이며 새 실행 테스트나 birth 판정 구현은 없다. 작성 후 backend/tests/data/docs 기존 파일 **71개 전부의 SHA256이 동일**함을 확인했다. 추가 파일은 이 문서 하나다. 기존 코드·테스트 기대값·실제/합성 데이터·기존 문서는 변경하지 않았다.

필수 23개 절, BR01~BR32의 순서·중복·누락, JSON 예시 2개의 문법/필드 구성을 확인했다. 이는 문서 예시 형식 확인이며 새 결과 모델이나 evaluator 테스트 통과가 아니다. Git 저장소가 아니므로 git diff 대신 파일 해시를 사용했고 적용되는 AGENTS.md는 발견되지 않았다.

## 24. M1.16D — IMPLEMENTED: Birth 결과 타입과 조합 검증

result_types.py에 불변 BirthDateCondition/BirthDateDetails 및 BirthDateReasonCode를 추가하고 기존 root 패키지에서 공개했다. RuleEvaluation의 필드·인자 순서는 유지하고 허용 타입/조건별 검증만 확장했다. PolicyEvaluation은 기존 공통 reason 검증의 확장을 통해 birth 결과를 그대로 보관·직렬화한다.

| 항목 | 현재 구현 |
|---|---|
| BirthDateCondition | 정확한 date 두 개, min ≤ max. 양끝 포함의 고정 의미. 동일 날짜 허용 |
| BirthDateDetails | birth_source:BirthSource\|None 하나. 날짜·정책 근거 복제 없음 |
| BirthDateReasonCode | WITHIN_RANGE / BEFORE_RANGE / AFTER_RANGE / MISSING의 5절 canonical 네 코드 |
| 평가 관찰값 | birth condition에서만 정확한 date/None. atomic/resident의 date 거부는 유지 |
| details 타입 | ResidentRegistrationDetails\|BirthDateDetails 유한 union. birth는 BirthDateDetails 필수. resident에 birth details 혼입 거부 |
| PASS | WITHIN, date 관찰값, 유효한 source, missing_fields=() |
| FAIL | BEFORE 또는 AFTER, date 관찰값, 유효한 source, missing_fields=() |
| UNKNOWN | MISSING, 관찰값 None, missing_fields=(birth.birth_date,), source=None 또는 BirthSource |
| 정책 근거 | birth 결과의 비어 있지 않은 문자열 tuple 필수. 순서·중복 보존, Registry 조회 없음 |
| 직렬화 | 기존 _jsonable 재사용. date→ISO, Enum→value, tuple→새 list, None→null. PolicyEvaluation 중첩 포함 |

M1.16D 지시의 의미 비교 검토는 **9절의 최우선 승인 계약**에 따라 처리했다. 결과 생성자는 before/after 날짜 관계를 다시 계산하지 않는다. 현재 resident 결과 생성자도 상태·사유·snapshot 정합성을 확인하며 정책 요구 지역 비교를 다시 수행하지 않는다. 이번 birth도 같은 책임 경계를 유지한다.

따라서 수동으로 BEFORE에 구간 이후 날짜를 넣거나 AFTER에 구간 이전 날짜를 넣은 결과, WITHIN에 구간 밖 날짜를 넣은 결과는 **구조가 맞으면 생성될 수 있다**. 이것은 실제 비교의 정답을 검증했다는 뜻이 아니다. 해당 허용 정책을 신규 테스트 3개로 명시했고, 실제 범위 비교의 정답은 후속 evaluator에서 경계 테스트해야 한다. 이 한계를 숨기고 의미상 모든 모순을 차단했다고 보고하지 않는다. 반면 status/reason·date 유무·source·missing_fields·condition/details의 혼합 오류는 현재 거부한다.

구조 오류는 기존 ResultValidationError 계열이며 입력 전체나 관찰 날짜를 오류 메시지에 넣지 않는다. condition 날짜 타입 오류는 INVALID_RESULT_DATE, 역전은 INVALID_BIRTH_DATE_RANGE, source 오류는 INVALID_BIRTH_SOURCE다. 나머지는 기존 INVALID_RESULT_VALUE/INVALID_RESULT_DETAILS/RESULT_REASON_STATUS_MISMATCH/INVALID_MISSING_FIELDS 등의 code를 재사용한다.

새 결과 객체는 frozen/slots이며 출력 dict/list를 변경해도 원본은 변하지 않는다. 새 condition/details를 Any나 generic dict로 받지 않고 datetime/date 하위 타입도 거부한다. 주민등록 EvaluationEvidence 및 Condition/Details의 구조·날짜 선택·의미는 변경하지 않았다.

IMPLEMENTED: Birth 결과 typed contract, RuleEvaluation birth support, PolicyEvaluation의 birth reason 수용 및 중첩 직렬화, 수동 생성·구조 검증 테스트.

NOT IMPLEMENTED: evaluate_birth_date_rule, BirthFact 비교·상태 계산, Resolver/Adapter, RuleNode/Policy/RuleGroup 타입 확장, routing, loader/schema, actual Q3 policy/source/locator/Envelope, 분기 선택.

최종 판단: **READY_TO_IMPLEMENT_BIRTH_EVALUATOR**. 다음 가장 작은 작업 1개는 **독립 evaluate_birth_date_rule(rule, birth_fact) 순수 함수와 경계·누락·방향 reason 테스트만 구현**하는 것이다. 이번에 준비한 RuleEvaluation을 직접 반환하고 routing/loader/실제 데이터는 연결하지 않는다.

### M1.16D 검증 기록

- 작업 전 전체 pytest: **1,939 passed in 5.42s**. 신규 tests/test_birth_result_types.py는 **106개**이며 최종 전체는 **2,045 passed in 5.74s**다. 기존 테스트 기대값을 변경하지 않았다.
- 신규 검증은 condition/date 타입, 역전·동일 날짜, typed details/source, 정상 PASS/FAIL/UNKNOWN 수동 생성, status/reason/missing_fields/관찰값 조합 오류, birth/atomic/resident 혼입 거부, 불변성, golden JSON·결정성·새 출력 값, PolicyEvaluation 중첩 보존을 포함한다. 날짜 방향을 결과 생성자가 다시 비교하지 않는 계약도 3개 사례로 고정했다.
- 기존 backend/tests/data/docs **72개**의 SHA256을 비교했다. result_types.py/models.py/root __init__.py 및 문서 3개만 변경했고 나머지 **66개는 동일**하다. 기존 테스트 전체·BirthFact/BirthDateRule·주민등록 값 타입/Resolver/Adapter·aggregation/evaluator·RuleNode/routing/loader·실제/합성 데이터는 보존했다. result_types.py의 기존 주민등록 클래스는 그대로이며 같은 파일에 새 birth 타입만 추가했다.
- 신규 파일은 tests/test_birth_result_types.py 하나다. Git 저장소가 아니므로 파일 해시를 사용했고 적용되는 AGENTS.md는 발견되지 않았다.

## 25. M1.16E — IMPLEMENTED: 독립 birth evaluator

`backend/policy_engine/birth_evaluator.py`의 `evaluate_birth_date_rule(rule: BirthDateRule, birth_fact: BirthFact | None) -> RuleEvaluation`을 root 패키지에서 공개했다. 두 인자는 필수이며 Fact 부재는 None으로 명시한다. RuleNode/정책 트리 입력과는 아직 연결하지 않는다.

모델 파일에 함수를 넣으면 models.py → specialized_rules → evaluator → models.py 순환이 생길 수 있어, 기존 evaluator.py/routing.py와 같은 계층의 별도 작은 모듈을 사용했다. 새 패키지·Resolver·Adapter·중간 결과 모델은 만들지 않았다.

| 입력 | 실제 계산 / 결과 |
|---|---|
| Fact 자체 없음 | UNKNOWN / BIRTH_DATE_MISSING, 관찰값 None, source None |
| Fact 날짜 없음 | 같은 UNKNOWN/관찰값, 입력 BirthSource 보존 |
| 출생일 < min | FAIL / BIRTH_DATE_BEFORE_RANGE |
| 출생일 > max | FAIL / BIRTH_DATE_AFTER_RANGE |
| 그 외 | PASS / BIRTH_DATE_WITHIN_RANGE. 양끝과 동일 날짜 구간 포함 |

UNKNOWN의 missing_fields는 정확히 (birth.birth_date,), PASS/FAIL은 빈 tuple이다. 결과의 rule_id/evidence_refs는 Rule에서 그대로 전달하며 ref 순서·중복을 보존한다. expected_condition은 Rule 날짜로 새 BirthDateCondition을 구성하고, evaluated_value는 date/None을 유지하며 BirthDateDetails에는 사용자 source만 넣는다. 기존 결과 생성자의 검증과 serializer를 그대로 사용한다.

입력 경계는 정확한 BirthDateRule인지, BirthFact 또는 None인지만 확인한다. 잘못된 rule은 PolicyDataError, 잘못된 fact 객체는 ProfileValidationError다. 모델 내부 날짜/범위/source/근거 구조를 수동으로 재검증하지 않는다. 결과 Condition/Details/RuleEvaluation을 구성할 때 기존 생성자가 자신의 불변 조건을 확인하는 것은 유지한다. 새 예외 클래스는 없다.

비교는 Rule의 날짜만 사용한다. 실제 Q3 값·정책 ID·분기·age·현재 날짜·신청일·평가일을 읽거나 하드코딩하지 않는다. 파일/네트워크/DB/전역 변경·캐시는 없다. 같은 Rule/Fact는 같은 결과 객체 의미와 직렬화 값을 만든다. source 차이는 details에만 반영하며 상태/사유를 바꾸지 않는다.

M1.16D의 수동 결과 생성자가 범위 방향을 재계산하지 않는 책임 경계는 유지한다. 이제 **이 함수가 실제 before/within/after 선택을 수행하는 단일 비교 지점**이며 경계 테스트로 방향을 검증했다. 기존 수동 결과 생성 테스트의 허용 기대값은 바꾸지 않았다.

테스트 입력은 합성 날짜/근거 문자열이며 실제 정책 데이터와 출처를 인코딩한 것이 아니다. evaluator가 근거 문자열을 보존한다고 source 존재·공식성·최신성을 검증한 것은 아니다. birth leaf PASS를 전체 정책 자격으로 해석하지 않는다.

IMPLEMENTED: evaluate_birth_date_rule, 실제 inclusive 비교에 따른 PASS/BEFORE FAIL/AFTER FAIL/UNKNOWN 계산, provenance/근거 보존, 결정적 결과와 직렬화.

NOT IMPLEMENTED: RuleNode/Policy/RuleGroup birth 연결, routing, loader/schema, 실제 Q3 JSON/source locator/PolicyEnvelope, 분기 선택. 기존 resident/atomic evaluator와 결과 모델은 이번에 수정하지 않았다.

최종 판단: **READY_FOR_BIRTH_RULE_ROUTING**. 다음 가장 작은 작업 1개는 **birth를 RuleNode와 기존 routing에 연결하는 최소 입력·dispatch 계약을 설계**하는 것이다. 기존 ALL/ANY/NOT 의미를 유지하고 loader/실제 데이터 연결은 별도 범위로 둔다.

### M1.16E 검증 기록

- 작업 전 전체: **2,045 passed in 7.39s**. 신규 tests/test_birth_evaluator.py: **48 passed in 0.26s**. 최종 전체: **2,093 passed in 6.68s**. 기존 테스트 파일·기대값은 수정하지 않았다.
- 신규 검증은 양끝/중간/먼 범위 밖/단일 날짜/윤년, 세 source의 PASS/FAIL 동일성, 두 누락 형태의 provenance, 값/조건/ID/근거 보존, 잘못된 객체 타입, 실제 반환 객체의 golden JSON·반복 결정성·입력 불변성·프로필/context 인자 부재·외부 I/O 미호출을 포함한다.
- 코드 확인 및 AST 점검으로 시스템 현재시각 조회·외부 I/O·전역 변경 호출이 없음을 확인했다. 실제 Q3 날짜를 함수에 하드코딩하지 않았다.
- 기존 backend/tests/data/docs **73개**의 SHA256과 비교했다. root __init__.py와 이 결과 계약/Birth slice 명세/ARCHITECTURE 문서만 변경됐고 나머지 **69개는 동일**하다. 신규 파일은 birth_evaluator.py와 tests/test_birth_evaluator.py 두 개다. 기존 Rule/Fact/결과 모델·atomic/resident evaluator·집계·RuleNode/routing/loader·실제/합성 자료는 보존했다.
- Git 저장소가 아니므로 파일 해시를 사용했다. 적용되는 AGENTS.md는 발견되지 않았다.
