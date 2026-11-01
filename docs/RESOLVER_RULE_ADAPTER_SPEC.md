# Resolver와 Rule Engine 최소 연결 계약 — M1.6C

작성일: 2026-10-20. M1.6C 설계 기록이며, **M1.6D 결과 표현은 20절, M1.6E 독립 Adapter는 21절을 우선**한다. evaluator routing은 미구현이다.

이번 산출물은 이 문서 하나다. M1.6B까지 승인된 동작과 이번 후속 제안을 구분한다. 아래 타입명과 규칙 예시는 구현 후보이며 production schema가 아니다. 기존 M1 논리 엔진, 합성 데이터 제한, M1.6A/B 모델·resolver 계약을 변경하지 않는다.

## 1. 목적

독립 `ResidentRegistrationResolution`을 정책 엔진의 조건 결과로 손실 없이 표현하고, 기존 ALL/ANY/NOT 집계에 연결하기 위한 최소 계약을 정한다. 상태를 다시 판정하거나 resolver가 끝낸 지역 비교를 어댑터에서 반복하지 않는다.

다시 확인한 기준 자료는 `RESIDENT_REGISTRATION_FACT_SPEC.md` 전체(현재 구현은 17~18절 우선), `POLICY_RULE_SPEC.md`, `DATA_MODEL.md`, `ARCHITECTURE.md`, `models.py`, `evaluator.py`, `resolvers/resident_registration.py`다. 오류 분류 확인을 위해 `errors.py`도 읽었다. 정책의 신청일 의미는 기존 M1.5/M1.6 분석을 따른다. 새로운 정책 조사·정책 조건 확정은 하지 않았다.

## 2. 현재 두 시스템 구조

### 2.1 구현된 M1

`PolicyRule → _evaluate_atom → RuleEvaluation → RuleGroup 집계 → PolicyEvaluation` 구조다.

| 대상 | 현재 계약 |
|---|---|
| PolicyRule | rule_id, 등록 Field, eq/in/gte/lte Operator, Scalar 또는 Scalar tuple, 선택 FactBasis, evidence_refs |
| RuleNode / RuleGroup / Policy | 정확한 PolicyRule 또는 RuleGroup 타입만 허용. 새로운 노드를 그냥 전달할 수 없음 |
| RuleEvaluation.reason_code | M1 ReasonCode Enum만 선언 |
| evaluated_value | str/int/bool 또는 None |
| expected_condition | ExpectedCondition(원자) 또는 GroupCondition |
| missing_fields | 필드 경로 tuple. 그룹·정책은 모든 자식의 정렬된 합집합 |
| evidence_refs | 정책 규칙의 합성 근거 참조. 사용한 사용자 fact를 담는 구조가 아님 |
| PolicyEvaluation.reason_codes | M1 ReasonCode tuple. 결과는 root-first, 최상위 상태가 overall_status |
| EvaluationContext | as_of: date, dataset_version, engine_version. evaluation_date라는 필드는 없음 |

evaluator는 `type(node) is PolicyRule`이면 원자로 처리하고 나머지를 그룹으로 처리한다. 따라서 모델 union만 넓히고 dispatch를 그대로 두면 안전하지 않다. 모든 자식을 평가하며 오류를 UNKNOWN으로 바꾸는 로직은 없다.

### 2.2 구현된 M1.6B

`facts + required_region + reference_date + evaluation_date → resolve_resident_registration → ResidentRegistrationResolution`이다. 엔진·프로필·JSON 로더와 연결되지 않았다.

결과는 status, 전용 reason_code, required_region, reference_date, evaluation_date, resolved_region, fact_as_of_date, missing_fields, used_facts를 갖는다. sources는 선택한 used_facts에서 계산한다. 날짜·지역·출처를 구조화해 보존하며 입력 전체를 복사하지 않는다.

현재 resolver는 모든 후보의 타입을 검증하고, 선택 날짜 밖을 포함해 같은 알려진 날짜의 지역 충돌을 먼저 거부한다. 그 뒤 기준일 누락/미래 여부와 정확한 날짜의 사실을 판정한다.

## 3. 연결에서 발생하는 문제

1. Status는 이미 같은 Enum이라 그대로 쓸 수 있지만, 주민등록 8개 사유는 M1 ReasonCode에 없다.
2. RegionRef를 Scalar나 기존 ExpectedCondition에 담을 수 없다. 지역 이름 문자열이나 sigungu 한 개로 바꾸면 지역 계층과 날짜 조건의 의미가 사라진다.
3. 신청 기준일·사실 날짜·평가일은 서로 다르다. 기존 결과에는 이를 구별할 provenance 공간이 없다.
4. evidence_refs에 fact JSON을 문자열로 넣으면 정책 원문 근거와 개인 사실이 혼합된다.
5. 현재 RuleNode의 허용 타입, 생성자 검증, 순회, dispatch가 모두 M1 원자/그룹만 가정한다. 단순 어댑터 추가만으로 자동 실행되지는 않는다.
6. 누락 경로는 UI 질문 이름과 다르다. reference_date라는 원시 경로만 보면 신청 기준일인지 평가일인지 알 수 없다.
7. 전역 충돌 검사가 단일 날짜 결과까지 막는다. 기존 계약과 후속 책임 분리 제안을 구분해야 한다.

결론: dataclass 생성 시 결과 필드의 타입 검사가 없다는 점을 이용해 다른 Enum/객체를 억지로 넣는 것은 계약 준수가 아니다. 무제한 dict/Any/str로 넓혀 문제를 덮지 않는다.

## 4. 설계안 A/B/C 비교

| 방식 | 장점 | 단점·위험 | 확장성 / MVP 평가 |
|---|---|---|---|
| A. 결과 Adapter | 이미 검증한 resolver를 재사용. 변환과 판정을 분리하고 독립 테스트 가능 | 현재 RuleEvaluation의 표현력 확장이 선행. 실행할 규칙 종류와 인자 출처는 별도 필요 | **가장 작은 첫 연결 단위**. 타입별 작은 변환 함수를 추가할 수 있음 |
| B. Specialized Rule | 주민등록 요구 지역·날짜 바인딩을 규칙에 명시. 명확한 dispatch 가능 | 기존 PolicyRule에 모든 종류의 optional 필드를 추가하면 잘못된 조합이 증가. 결과 표현 문제도 별도로 남음 | 기존 원자는 보존하고 별도 주민등록 leaf를 추가하는 좁은 형태가 적합 |
| C. Fact Resolver Layer | 결과 경계를 명시하고 사실 해석·집계를 분리. 공통 상태/사유/누락/근거 계약 가능 | 미구현 사실까지 범용 Resolution, 동적 registry, 의존성 주입 체계를 만들면 과도함 | 지금은 **계약 원칙만 채택**. 모든 도메인 payload를 공통 평면 모델로 강제하지 않음 |

A는 결과 변환, B는 규칙의 표현/실행 경로, C는 계층 경계에 관한 선택이다. 서로 완전히 배타적이지 않다. 추천은 A를 먼저 만들 수 있도록 결과 타입을 최소 확장하고, 엔진 연결 시 B의 명시적인 주민등록 leaf 하나만 추가하는 것이다. C는 그 사이의 작고 타입이 정해진 결과 계약으로 적용한다.

## 5. 추천 구조

### 5.1 책임 흐름 — 후속 구현 제안

```text
기존 PolicyRule ─────────────────────→ 기존 원자 evaluator ──┐
                                                          │
ResidentRegistrationRule + 명시적 facts/reference context  │
  → 주민등록 전용 evaluator                              │
  → 기존 resolve_resident_registration                    │
  → ResidentRegistrationResolution                        │
  → 작은 결과 adapter ────────────────────────────────────┤
                                                          ↓
                                     확장한 RuleEvaluation
                                          ↓ 기존 3상태 집계
                                           PolicyEvaluation
```

기존 PolicyRule 클래스는 원자 규칙으로 유지한다. 새 주민등록 leaf를 별도로 두고 RuleNode의 유한한 union으로 연결하는 것이 조건별 optional 필드를 한 클래스에 누적하는 것보다 안전하다. 주민등록 evaluator는 인자 바인딩과 기존 resolver 호출만 담당하고 adapter는 변환만 한다. 새로운 범용 비교 연산자는 필요 없다.

### 5.2 최소 결과 타입 변화 후보

아래는 문서상 타입 계약이다. 현재 파일에는 적용하지 않았다.

| 필드/타입 | 제안 |
|---|---|
| EvaluationReasonCode | 기존 ReasonCode 또는 ResidentRegistrationReasonCode의 명시적 union |
| RuleEvaluation.reason_code | 위 union. PolicyEvaluation.reason_codes도 같은 union |
| RuleEvaluation.evaluated_value | 기존 Scalar/None에 RegionRef만 추가 |
| RuleEvaluation.expected_condition | 기존 두 타입에 ResidentRegistrationCondition 추가 |
| ResidentRegistrationCondition | required_region: RegionRef, reference_date_source: 고정 바인딩 Enum |
| RuleEvaluation.provenance | 선택 필드. 기본 None. 주민등록 결과에는 ResidentRegistrationProvenance |
| ResidentRegistrationProvenance | reference_date_source와 원본 ResidentRegistrationResolution을 불변으로 참조 |

원본 Resolution은 이미 선택된 근거와 최소 판정 메타데이터만 갖는다. 이를 provenance에 보존하면 각 필드를 또 다른 복제 모델로 옮기며 빠뜨릴 위험이 작다. evaluated_value는 resolved_region, expected_condition은 규칙 요구를 나타낸다. provenance 내부와 공통 필드의 중복은 adapter가 동일성 검증으로 일치시킨다.

일반 원자/그룹에는 provenance=None을 기본값으로 둔다. 기존 M1 출력의 호환성을 위해 None인 새 필드는 기존 `PolicyEvaluation.to_dict()` 결과에서 생략하는 방안을 추천한다. 주민등록 결과만 새 표현을 갖는다. 기존 공통 `_jsonable`에 필드를 추가하기만 하면 None도 출력되므로 이 직렬화 호환성 처리를 별도 테스트해야 한다.

미래의 payload union은 실제 resolver 승인 때 한 종류씩 확장한다. 지금 Birth/History/Income 타입이나 범용 FactContext를 만들지 않는다.

### 5.3 adapter 입력/출력 계약 후보

입력: 검증된 rule_id·ResidentRegistrationCondition·정책 evidence_refs, ResidentRegistrationResolution, 명시적으로 바인딩한 기준일과 평가일. 출력: 확장된 RuleEvaluation 한 개. 외부 I/O·현재시각·상태 재계산 없음.

규칙 요구 지역, 바인딩 날짜, 평가일이 Resolution과 일치하는지 확인한다. 다른 정책/날짜의 결과를 재사용한 경우 정상 결과를 만들지 않고 연결 계약 오류로 거부한다. 그룹 노드, 정책 전체 결과, UI 질문 문장은 adapter가 만들지 않는다.

## 6. 상태 매핑

| Resolution.status | RuleEvaluation.status |
|---|---|
| Status.PASS | 같은 Status.PASS |
| Status.FAIL | 같은 Status.FAIL |
| Status.UNKNOWN | 같은 Status.UNKNOWN |

동일 Enum이므로 변환 추론이 없다. PASS를 CONDITION_MET로 재판정하거나 출처에 따라 UNKNOWN으로 내리지 않는다. 잘못된 결과 객체/사유-상태 조합은 adapter 입력 계약 오류다. Resolution dataclass도 직접 만들 수 있으므로 생성자를 호출했다는 사실만으로 의미적 정합성을 보장한다고 가정하지 않는다.

ALL/ANY/NOT 진리표는 그대로다. 주민등록 leaf의 PASS는 그 조건 하나의 결과다. 전체 정책 PASS를 임의로 생성하지 않는다. NOT 그룹에서는 부모 결과만 반전하고 leaf의 원래 상태·사유·근거는 보존한다.

## 7. reason code 매핑

전용 Enum 멤버를 손실 없이 그대로 옮긴다. 기존 CONDITION_MET/CONDITION_NOT_MET/MISSING_FIELD로 축약하지 않는다.

| 원본 및 변환 후 reason_code | 대응 상태 |
|---|---|
| RESIDENT_REGION_MATCH | PASS |
| RESIDENT_REGION_MISMATCH | FAIL |
| RESIDENT_REGISTRATION_MISSING | UNKNOWN |
| RESIDENT_REGION_MISSING | UNKNOWN |
| RESIDENT_REGISTRATION_DATE_MISSING | UNKNOWN |
| RESIDENT_REGISTRATION_DATE_UNPROVEN | UNKNOWN |
| RESIDENT_REFERENCE_DATE_MISSING | UNKNOWN |
| RESIDENT_REFERENCE_DATE_IN_FUTURE | UNKNOWN |

위 8개 이름은 기존 구현의 고정 값이다. 임의 문자열 생성·UI 문장·지역/날짜 삽입은 금지한다. 직렬화는 Enum.value를 사용한다. 정책 reason_codes는 기존 그룹 사유와 주민등록 사유 모두를 값 기준 정렬·중복 제거한다. 현재 두 Enum의 값은 충돌하지 않는다. 다음 종류를 추가할 때도 코드 값 충돌을 검증해야 한다.

그룹 사유는 기존 ALL_*/ANY_*/NOT_*를 유지한다. 예를 들어 ALL_PASS와 RESIDENT_REGION_MATCH가 정책 사유에 함께 남는다. 그룹 provenance에는 모든 fact를 다시 복제하지 않고 leaf의 rule_id를 통해 확인한다.

## 8. missing_fields 계약

adapter는 원본 missing_fields를 그대로 보존한다. 이 값은 **도메인 정보 부족 경로**이며 UserProfile 필드명이나 UI 질문 ID가 아니다. rule_id 및 provenance의 바인딩과 함께 해석한다.

| 원본 경로 | RuleEvaluation.missing_fields | 향후 입력 연결 후보 | UI 질문 의미 |
|---|---|---|---|
| resident_registration | 동일 | 요청의 주민등록 facts | 해당 기준일의 주민등록 사실 입력 |
| resident_registration.region | 동일 | 해당 기준일 fact.region | 주민등록 시·군·구 확인 |
| resident_registration.as_of_date | 동일 | fact.as_of_date | 사실이 주장하는 날짜 확인 |
| reference_date | 동일 | 해당 정책의 reference_context.application_date | 신청 기준일 확인 |

UI는 `(rule_id, reference_date_source, missing_path)`를 이용한 별도 유한 매핑으로 질문을 만들 수 있다. 문구를 엔진에 저장하지 않는다. 여러 정책의 reference_date를 하나의 전역 입력으로 합치지 않는다. PolicyEvaluation의 합집합은 요약이며, 정확한 추가 질문은 rule_results에서 가져온다.

DATE_UNPROVEN과 REFERENCE_DATE_IN_FUTURE는 missing_fields가 빈 tuple이다. 빈 배열을 완전한 정보의 증거로 해석하지 않는다. 전자는 reason과 요구 기준일을 이용해 해당 날짜의 사실을 다시 확인하고, 후자는 미래 기준일이라는 설명을 제공한다. 새로운 가짜 누락 필드를 만들지 않는다. 부분 RegionRef는 누락 질문이 아니라 검증 오류다.

## 9. evidence / provenance 계약

정책의 요구조건 근거와 사용자 사실 근거를 분리한다.

| 구분 | 담는 내용 | 보존 위치 |
|---|---|---|
| 정책 근거 | 해당 규칙의 원문/문서 참조 | 기존 evidence_refs |
| 정책 요구 | required_region, reference_date_source | ResidentRegistrationCondition |
| 실행 관점 | 실제 reference_date, evaluation_date | provenance.resolution |
| 실제 비교값 | resolved_region, fact_as_of_date | evaluated_value 및 provenance.resolution |
| 사용 근거 | resolver가 선택한 used_facts(region/as_of_date/source), 파생 sources | provenance.resolution |

원본 Resolution 전체는 이 조건에 필요한 작은 데이터이므로 보존 대상으로 선택한다. 선택하지 않은 후보·소득·월세·사용자 ID·전체 프로필·주소·주민번호·초본 원문을 추가하지 않는다. source는 수집 경로 메타데이터이며 사실의 진위를 인증하지 않는다.

exact-date fact의 region만 없는 경우에는 날짜 근거와 해당 source가 남을 수 있다. DATE_UNPROVEN/미래 기준일 등 원본 used_facts가 비어 있으면 adapter도 빈 근거를 유지한다. 요구 지역이나 기존 UserProfile.region을 사용 사실로 둔갑시키지 않는다. sources는 used_facts에서만 계산한다.

현재 evidence_refs는 합성 자료 참조다. 실제 정책을 넣는 후속 단계에서 공식 URL·원문 위치를 연결하되, 이번에는 공식 데이터 로딩 허용이나 실제 정책 스키마를 변경하지 않는다. leaf 근거는 요청 중 결과 설명에만 쓰고 기본 로그·파일·DB에 저장하지 않는다. 실행/규칙 버전은 기존 PolicyEvaluation.context 및 rule_version과 함께 해석한다.

## 10. reference_date 계약

### 10.1 후보 비교

| 후보 | 판단 |
|---|---|
| A. EvaluationContext의 평가일 | 기존 필드는 as_of다. resolver.evaluation_date로 명시적으로 전달할 수 있으나 신청일을 대신하지 못함 |
| B. Rule에 날짜 상수 | 고정 공고 기준일 조건에는 가능하나 사용자별 신청일을 규칙에 박으면 재사용·버전 관리가 틀어짐 |
| C. Policy/ApplicationPeriod 계산 | 신청기간은 허용 구간이며 실제/가정 신청일 하나를 결정하지 못함. 시작일·종료일 자동 선택 금지 |
| D. 별도 정책 기준일 context | **추천**. 규칙은 날짜의 의미를 바인딩하고 호출자가 그 의미에 맞는 값을 명시적으로 제공 |

### 10.2 최소 제안

문서상 `PolicyReferenceContext(policy_id, application_date: date | None)` 하나를 후보로 둔다. rule의 `reference_date_source=APPLICATION_DATE`가 해당 정책 context.application_date를 선택한다. 정책별로 별도 context를 전달하며 policy_id가 다른 context는 거부한다. 여러 기준일을 위한 임의 dict/표현식/날짜 계산 DSL은 만들지 않는다.

기존 M1.6 문서의 APPLICATION_REFERENCE_DATE는 설계상 바인딩 이름이었다. 이 문서는 **새 후보 명칭 APPLICATION_DATE**를 사용한다. 아직 실행 Enum/스키마가 없으므로 기존 코드를 바꾼 것이 아니며, 후속 모델 승인 시 하나로 확정한다. 두 이름을 묵시적 alias로 허용하지 않는다.

명시적 전달:

```text
resolver.evaluation_date ← EvaluationContext.as_of
resolver.reference_date  ← 해당 policy reference context.application_date
resolver.required_region ← 해당 주민등록 rule.required_region
resolver.facts           ← 명시적 주민등록 fact 묶음
```

바인딩 종류 누락/미지원 값은 PolicyDataError다. 바인딩은 유효하나 application_date=None이면 기존 RESIDENT_REFERENCE_DATE_MISSING / UNKNOWN이다. context 객체 자체 누락·다른 정책 context·잘못된 날짜 타입은 호출 계약 오류다. 사용자 미입력은 정상 context의 None으로 명시한다. 평가일을 자동 복사하거나 신청기간에서 보간하지 않는다.

**Assumption:** 신청일은 실제 접수 검증값이 아니라 요청자가 명시한 검토 기준일일 수도 있다. UI가 이를 실제 접수 완료로 표시하지 않는다. 평가일 2026-11-10, 신청 기준일 2026-10-01이면 10월 1일 fact로 평가하며 11월 fact로 과거를 역추론하지 않는다. 미래 신청 기준일이면 기존 UNKNOWN을 그대로 유지한다.

## 11. Data Error 계약

오류는 정상 3상태와 다른 제어 경로다. Data Error라는 네 번째 Status는 만들지 않는다.

| 상황 | 처리 |
|---|---|
| 유효한 context에서 신청 기준일 None, 빈 facts, fact의 None | resolver가 반환한 원인별 UNKNOWN 유지 |
| 필수 요구 지역, rule 종류/바인딩/근거/구조 오류 | 규칙 검증 단계 PolicyDataError. resolver를 호출해 UNKNOWN으로 대체하지 않음 |
| 잘못된 사용자 fact·날짜·source, 상충 fact | 기존 ResidentRegistrationValidationError의 code/field 및 예외를 보존 |
| 평가 context 누락·정책 불일치·잘못된 평가일 | ContextValidationError 계열의 명시적 오류. 하위 resolver 호출 시 발생한 기존 오류도 숨기지 않음 |
| 규칙/날짜와 Resolution의 요구값 불일치, 잘못된 결과 상태/사유 | adapter 계약 오류. 사용자 정보 부족으로 분류하지 않음 |

후속 adapter 계약 오류의 구체적인 예외 클래스명·코드는 모델 확정 단계에서 정한다. 지금 임의 reason 문자열을 만들지 않는다. 기존 오류를 포장하더라도 원래 code/field와 정책 설정/사용자 입력/호출 계약의 구분을 잃으면 안 된다. 오류 메시지에 사용자 원본값을 넣지 않는다.

이번 최소 연결에서는 오류가 발생한 평가 호출을 실패시키고 정상 PolicyEvaluation을 반환하지 않는 방식을 추천한다. ANY에 다른 PASS 자식이 있어도 오류를 감추지 않는다. 여러 정책을 부분 성공으로 반환하는 서비스 응답은 별도 설계 사항이다. 예상한 검증 오류만 처리하며 광범위한 예외 catch로 프로그래밍 오류를 UNKNOWN으로 바꾸지 않는다.

## 12. Fact conflict validation 책임

### 12.1 현행 A와 분리안 B

예: 평가일/신청 기준일 2026-11-10에 안산 fact, 별도로 2026-01-01 안산·수원 fact가 함께 있는 가상 입력.

| 방식 | 단일 조건 결과 | 장점 | 단점 |
|---|---|---|---|
| A. 현행 전체 resolver 오류 | CONFLICTING_RESIDENT_REGISTRATION_FACTS, 정상 상태 없음 | 입력 묶음의 정합성을 강하게 보장. 기존 코드·계약·테스트와 일치 | 무관한 과거 모순이 현재 날짜 조건까지 차단 |
| B. collection 검증과 날짜 resolution 분리 | 해당 날짜 조건은 PASS 가능, 1월 충돌은 별도 검증 보고 | 충돌이 어느 판단에 영향을 주는지 명확. 이력/복수 조건 확장에 유리 | 보고서 전달·검사 범위·서비스 표시 정책을 함께 설계해야 함. 그냥 필터링하면 오류 은폐 |

### 12.2 추천과 현재 효력

장기 추천은 B다. collection validation은 전체 후보 구조·날짜별 충돌을 검사하고 별도 명시적 보고를 만든다. reference-date resolution은 자신의 날짜에 필요한 유효 사실과 해당 날짜의 충돌을 책임진다. selected date의 충돌은 여전히 Data Error다. 모든 후보의 타입/구조 오류도 선택 여부와 무관하게 거부하는 것을 제안한다.

무관한 날짜의 충돌만으로 leaf 상태를 재해석하지 않되 collection 오류는 별도 입력 오류 보고에 남겨야 한다. 해당 조건 PASS와 전체 입력 정합성 문제를 함께 전달할 구조가 승인되기 전에는 이를 정상 정책 전체 결과로 노출하지 않는다. ‘전체 입력 문제를 어떻게 표시/차단할지’는 후속 결정이며 이 문서가 조용한 정상 처리를 승인하지 않는다.

**이번과 다음 최소 adapter의 기준은 현행 A다.** resolver를 변경하지 않고 예외를 그대로 전파한다. adapter가 입력을 미리 날짜로 잘라 전달하거나 예외를 잡아 PASS를 재구성하는 우회는 금지한다. B는 별도 계약 변경 승인·resolver/테스트/명세 변경이 필요한 제안이다. 이 쟁점은 손실 없는 adapter 작성 자체를 막는 필수 선행 조건은 아니다.

## 13. 주민등록 rule 예시

아래는 설명용 표현이며 로더에 넣을 수 있는 정책 JSON이 아니다. 실제 정책 전체도 아니다.

```text
ResidentRegistrationRule
  rule_id: EXAMPLE_RESIDENT_001
  rule_type: RESIDENT_REGISTRATION
  required_region: RegionRef(GYEONGGI, ANSAN)
  reference_date_source: APPLICATION_DATE
  evidence_refs: (기존 분석의 E02를 가리키는 문서 참조,)
```

문서상 rule_type은 명시적 종류 표식이다. 내부에서는 별도 dataclass 타입 자체로 dispatch해도 된다. 현재 PolicyRule에 field=region, operator=eq를 붙이고 날짜 규칙을 evidence 문자열에 숨기는 표현은 선택하지 않는다.

후속 엔진 연결 시에만 `RuleNode = PolicyRule | ResidentRegistrationRule | RuleGroup`로 확장하고 Policy.root/RuleGroup.children의 검증·순회·유일 ID 검사·evaluator의 명시적 dispatch를 함께 검토한다. 지원하지 않는 타입은 오류다. 기존 원자/그룹 동작·논리표는 유지한다. 실제 JSON 로더와 schema_version 확정은 별도 승인까지 미룬다. 현재 synthetic/test_only=True 제한을 해제하지 않는다.

## 14. 향후 Fact 확장성 검토

| 향후 조건 | 재사용 가능한 계약 | 그대로 강제하면 안 되는 부분 |
|---|---|---|
| BirthFact: 생년월일 범위 | 상태, 고정 reason, 명시적 요구조건, 선택 근거와 adapter 경계 | RegionRef·주민등록 기준일을 범용 값으로 재사용할 수 없음. 날짜/구간 조건은 별도 승인 필요 |
| ResidenceHistoryFact: 연속 3년 또는 합산 10년 | 공통 3상태 집계, 정책 요구와 실제 근거 분리 | 여러 구간·중복·공백 처리가 필요. 점 시점 주민등록으로 거주기간을 추론하면 안 됨 |
| IncomeFact: 특정 가구소득 기준 이하 | 고정 사유, missing, 요구 기준과 비교 사실의 provenance | 주체·소득 정의·기간·연도·단위가 맞아야 함. monthly_income 대체/자동 환산 금지 |

따라서 **상태·결과 접근 형태는 공통화하고 의미·payload는 유한한 구체 타입으로 분리**하는 방향은 확장 가능하다. 미래 resolver에 현재 ResidentRegistrationResolution의 필드를 그대로 요구하지 않는다. 실제 두 번째 resolver가 생긴 뒤 필요한 공통 부분만 다시 추출한다.

M1에는 이미 household_income용 PolicyFact/FactBasis가 있다. 이것이 미래 IncomeFact/IncomeResolver가 구현됐다는 뜻은 아니다. 이번 단계에서 해당 세 모델의 필드·계산식·파일을 만들지 않는다.

## 15. 결정사항

다음은 M1.6C의 **추천 계약**이다. 구현 승인으로 간주하지 않는다.

1. 기존 M1 원자 규칙과 3상태 논리 엔진은 유지한다.
2. 상태는 동일 Enum을 그대로 옮기며 주민등록 reason 8개를 보존한다.
3. 결과 타입에 구체적인 지역/조건/provenance 표현을 추가한 뒤 작은 adapter를 만든다.
4. 기존 PolicyRule에 주민등록 optional 필드를 누적하지 않고 별도 leaf를 연결 후보로 둔다.
5. 날짜의 의미는 rule에, 실제 신청 기준일 값은 정책별 context에 둔다. 평가일은 context.as_of에서 별도 전달한다.
6. missing_fields는 도메인 경로로 유지하고 UI 질문과 분리한다.
7. 정책 evidence_refs와 선택 fact provenance를 분리한다. 출처로 상태를 바꾸지 않는다.
8. 오류를 UNKNOWN으로 변환하지 않는다. 현행 전역 충돌 오류도 보존한다.
9. collection validation 분리는 후속 제안이며 이번 코드·현재 기대값에 소급 적용하지 않는다.
10. 실제 정책 로딩·다른 Fact·API/UI/금융/시뮬레이션/LLM은 이번 산출물에 포함하지 않는다.

## 16. 미결정사항

| 항목 | 현재 제안 / 필요한 결정 | 최소 작업의 차단 여부 |
|---|---|---|
| 결과 타입의 최종 선언·불변성·직렬화 | 5절의 명시적 union과 provenance 기본 None을 확정하고 검증 테스트 필요 | **결과 adapter 구현 전 필요** |
| Rule 표현/기준일 바인딩 이름 | 별도 ResidentRegistrationRule, APPLICATION_DATE 권장. 이전 문서 명칭과 하나로 확정 | **엔진 연결 전 필요** |
| adapter 불일치 오류 클래스·고정 code | 기존 입력 오류와 구분하되 중복 범용 오류 체계는 만들지 않음 | **adapter 구현 전 필요** |
| Fact/context 전달 경로 | 프로필 밖 명시적 인자 권장. 기존 UserProfile 통합은 보류 | 실제 evaluator 연결 전 확정 |
| 충돌 책임 분리 | 현행 A 유지. B는 별도 검증 보고와 서비스 처리 계약 필요 | 최소 adapter는 A로 진행 가능 |
| 운영상 신청 기준일/평가일의 입력 권한·표시 | 사용자가 명시한 검토일과 실제 접수 검증을 구분 | 현재 순수 결과 모델에는 비차단 |
| 출처 생성 권한·검증 기록 | 공식 연결 미구현. 임의 OFFICIAL_DATA 표시는 인증 아님 | 현재 모델에는 비차단 |
| 실제 정책 JSON·스키마 버전·원문 관리 | 별도 단계, 현재 합성 데이터 제한 유지 | 이번 작업 대상 아님 |

Assumption: 현재 주민등록 facts는 동일 사용자의 한 요청 입력이다. 장기 저장소나 사용자 ID 연결을 전제하지 않는다. 내부 지역 namespace는 MVP_INTERNAL_REGION_V1이며 공식 행정코드로 취급하지 않는다.

## 17. 구현 시 예상 변경 파일

아래는 **미래 작업 후보**이며 이번 변경 목록이 아니다. 존재하지 않는 파일은 생성 후보로 표시한다.

| 파일 | 예상 역할 / 시점 |
|---|---|
| backend/policy_engine/models.py | 결과 사유/값/조건 union, 선택 provenance 및 직렬화 호환성. 나중에 RuleNode 관련 허용 타입 |
| backend/policy_engine/resident_registration_contracts.py (신규 후보) | 주민등록 조건/규칙/provenance/정책별 기준일 context. import 순환을 피하는 구체 타입 위치 검토 |
| backend/policy_engine/adapters/resident_registration.py (신규 후보) | 검증된 Resolution을 결과로 옮기는 작은 순수 함수 |
| backend/policy_engine/adapters/__init__.py (신규 후보) | 승인한 adapter만 공개 |
| backend/policy_engine/errors.py | adapter 계약 오류의 분류가 승인되면 추가 |
| backend/policy_engine/evaluator.py | 후속 엔진 연결 시 명시적 leaf dispatch와 facts/context 전달. 논리표 보존 |
| backend/policy_engine/__init__.py | 승인된 공개 인터페이스만 추가 |
| tests/test_resolver_rule_contracts.py (신규 후보) | 결과 타입·정합성·직렬화·기존 출력 호환성 |
| tests/test_resident_registration_adapter.py (신규 후보) | 상태/사유/누락/근거/날짜/오류 변환 계약 |
| tests/test_evaluation.py 등 | 연결 승인 이후 혼합 트리·NOT·오류 전파의 회귀 사례 추가. 기존 기대값 수정 금지 |
| docs/DATA_MODEL.md, POLICY_RULE_SPEC.md, ARCHITECTURE.md 및 본 문서 | 승인/구현 상태와 후속 변경 기록 |

기존 resolver/facts 및 해당 테스트는 최소 adapter 단계에서 수정할 필요가 없다. 충돌 B를 승인하는 후속 작업에서만 resolver·관련 테스트·RESIDENT_REGISTRATION_FACT_SPEC을 함께 변경한다. loader.py/실제 정책 JSON/새 Fact 파일은 지금 제안한 첫 작업의 변경 대상이 아니다.

타입 의존 방향은 공통 Status/기존 모델 → 독립 resolver → 주민등록 연결 계약 → adapter 순으로 검토한다. models.py가 연결 계약을 import하면서 연결 계약이 다시 models.py의 런타임 타입에 의존하는 순환은 피해야 한다. 필요한 경우 TYPE_CHECKING/전방 타입 참조와 명시적 직렬화를 이용한다. 이를 이유로 공통 도메인 전체를 재배치하지 않는다.

## 18. 수동 테스트 시나리오

### 공통 전제

가상 평가일=context.as_of=2026-11-10, 신청 기준일=2026-11-10, 요구 지역=GYEONGGI/ANSAN, fact는 같은 날 안산/SELF_REPORTED 하나다. 명시한 변경 외에는 이 기본값을 사용한다. 이는 실제 현재/미래 행정상태의 증명이 아니다.

아래 **24개는 후속 구현의 수동 기대값**이며 실행 테스트 통과를 주장하지 않는다. C23은 미래 구조 검토다. C12의 분리안은 미승인 제안이다.

| ID | 입력/상황 | 기대 결과 |
|---|---|---|
| C01 | 기본 resolver PASS | adapter PASS, RESIDENT_REGION_MATCH, evaluated_value 전체 RegionRef, missing=[] |
| C02 | 같은 날 수원 fact | FAIL, RESIDENT_REGION_MISMATCH 그대로 |
| C03 | 같은 날 fact.region=None | UNKNOWN, RESIDENT_REGION_MISSING, [resident_registration.region], 날짜 근거 보존 |
| C04 | facts=빈 tuple | UNKNOWN, RESIDENT_REGISTRATION_MISSING, [resident_registration], used_facts=[] |
| C05 | fact.as_of_date=None | UNKNOWN, RESIDENT_REGISTRATION_DATE_MISSING, [resident_registration.as_of_date] |
| C06 | fact 날짜만 2026-10-01 | UNKNOWN, RESIDENT_REGISTRATION_DATE_UNPROVEN, missing=[], 사용 근거 생성 금지 |
| C07 | 유효한 context.application_date=None | UNKNOWN, RESIDENT_REFERENCE_DATE_MISSING, [reference_date]; 평가일 대체 금지 |
| C08 | 평가일=2026-10-20, 신청 기준일/fact 날짜=2026-11-10 | UNKNOWN, RESIDENT_REFERENCE_DATE_IN_FUTURE, missing=[], used_facts=[] |
| C09 | 기준일에 안산·수원 fact | 기존 CONFLICTING_RESIDENT_REGISTRATION_FACTS 전파. Rule/PolicyEvaluation 없음 |
| C10 | rule의 reference_date_source 누락/미지원 | PolicyDataError. 사용자 정보 누락으로 취급하지 않음 |
| C11 | rule.required_region=None 또는 잘못된 타입 | 정책 검증 오류. resolver까지 전달됐다면 기존 INVALID_REQUIRED_REGION도 숨기지 않음 |
| C12 | 11/10 안산 + 1/1 안산·수원 충돌 | **현행/최소 adapter: 충돌 오류**. 별도 승인된 B에서만 11/10 leaf PASS와 1/1 collection 오류 보고 가능 |
| C13 | 같은 날 같은 지역, source만 두 종류 | 상태/사유 동일, 두 used_facts/source 보존. 신뢰도 순위 없음 |
| C14 | 같은 입력 재실행·순서 변경·완전 동일 fact 중복 | 결과/직렬화 동등. 현재시각/난수 추가 없음 |
| C15 | 평가일11/10, 신청 기준일/fact 날짜10/1 | PASS, provenance에 서로 다른 두 날짜 보존 |
| C16 | Rule 요구=안산인데 수원 요구로 만든 Resolution을 adapter에 전달 | 연결 계약 오류. 결과 덮어쓰기/재판정 금지 |
| C17 | 예상 신청 기준일 또는 평가일과 Resolution 날짜 불일치 | 연결 계약 오류. 다른 실행 결과 혼용 방지 |
| C18 | ALL(주민등록 PASS, 기존 원자 UNKNOWN) | overall UNKNOWN, ALL_UNKNOWN 및 주민등록 사유 보존. 기존 missing 합집합 유지 |
| C19 | ANY(기존 PASS, 주민등록 fact 충돌 오류) | 정상 ANY_PASS 반환 금지. 오류 전파 |
| C20 | NOT(주민등록 PASS) | 그룹 FAIL/NOT_FAIL, leaf PASS/MATCH와 근거 그대로 |
| C21 | 기존 원자/그룹만 평가 | 기존 결과 의미/JSON 키·값 유지. 새 provenance=None 직렬화 누출 없음 |
| C22 | 정책 A에 정책 B reference context 전달 또는 잘못된 날짜 타입 | 명시적 context/입력 오류. UNKNOWN 아님 |
| C23 | 미래 Birth/History/Income 결과를 같은 경계에 대입 | 상태/사유/누락/근거 접근 계약은 재사용 가능. 주민등록 payload를 강제하지 않음. 실제 타입 없이는 실행 불가 |
| C24 | 원본 evidence_refs와 used_facts, 출처 확인 | 정책 근거는 evidence_refs, 선택 fact는 provenance에 분리. 전체 프로필·선택 밖 fact 없음 |

### 이번 작업의 검증 기록

작업 기준선의 전체 pytest는 **313 passed in 1.79s**였다. 문서 작업이므로 새 테스트나 adapter 테스트를 작성·실행한 것으로 보고하지 않는다. 기존 backend/tests/data/docs 파일 27개의 SHA256을 비교한 결과 모두 동일했고, 이 문서 하나만 추가됐다. 필수 19개 절과 중복 없는 수동 사례 C01~C24도 확인했다. 검증 대상은 구현된 M1~M1.6B의 보존이며 이 문서의 미래 설계가 실행 검증됐다는 뜻은 아니다.

## 19. 최종 판단

**NEEDS_RULE_MODEL_CHANGE**

현재 모델 그대로는 주민등록 사유 Enum, RegionRef, semantic condition, provenance를 손실 없이 담을 수 없다. RuleGroup/Policy의 허용 노드와 evaluator dispatch도 새 leaf를 수용하지 않는다. 따라서 ‘어댑터 함수만 추가하면 바로 연결 가능’이라고 판단하지 않는다.

필요한 변화는 기존 PolicyRule 자체의 전면 확장이 아니라 **결과 타입의 좁은 확장과 별도 주민등록 leaf의 추가**다. 기존 원자/그룹 논리 엔진은 유지한다. 기존 resolver는 현재 계약대로 어댑터에 연결할 수 있으므로 전면 재설계가 선행 조건은 아니다. 전역 충돌 책임 분리는 별도 개선 제안으로 남긴다.

**다음 가장 작은 작업 1개:** M1.6D에서 주민등록 결과 표현용 Condition/Provenance 및 명시적 reason/value/condition union만 확정·구현하고 타입 검증·기존 JSON 출력 호환성 테스트를 추가한다. 구체적인 adapter 불일치 오류도 이때 확정한다. resolver 실행·adapter 함수·새 rule dispatch·실제 정책 JSON은 아직 연결하지 않는다. 이 결과 모델 작업의 승인은 별도로 받는다.

## 20. M1.6D — IMPLEMENTED: 결과 표현 타입만 확장

이 절은 승인된 M1.6D 직접 지시에 따른 구현 계약이다. 앞의 2절은 M1.6C 당시 상태이고 5절은 초기 후보다. 최신 구현은 아래를 따른다. 기존 PolicyRule/RuleNode/로더/evaluator/Resolver 동작은 변경하지 않았다.

### 구현 전 비교와 선택

| 접근 | 장점 | 단점 | 선택 |
|---|---|---|---|
| A. 결과 최상위에 여러 선택 필드 추가 | 접근이 단순 | reference_date/observed/evidence 등 종류별 필드가 계속 증가하고 상충 표현이 생김 | 채택하지 않음 |
| B. typed detail 객체 하나 추가 | 기존 생성자 유지, 날짜·근거를 구체 타입 안에 한정, 미래 종류는 승인 시 유한 union 확장 | detail/공통 값의 정합성 검증 필요 | **채택: details=None** |
| C. 별도 Evidence/Trace 연결 | 여러 조건에 공통 추적 체계를 적용하기 좋음 | 지금은 독립 Trace 식별·참조·수명 구조까지 필요 없음 | 작은 evidence 값만 B 내부에 사용 |

### M1.6C 후보에서 구체화한 차이

최신 지시가 원본 Fact 전체 결합과 평가일 중복을 재검토하도록 요구했다. 이에 따라 5절 후보의 `provenance.resolution` 대신 **결과 전용 스냅샷**을 선택했다. RegionRef 자체를 참조하는 것도 frozen이므로 안전하지만, RegionSnapshot은 Fact 계층 객체를 결과에 저장하지 않는 경계를 명확히 한다. 내부 허용 지역 쌍과 RegistrationSource Enum만 재사용한다. 공식 지역 코드가 아니다.

| 실제 타입/필드 | 구현 계약 |
|---|---|
| RegionSnapshot | sido/sigungu, 완전하고 유효한 내부 지역 쌍. frozen/slots |
| ReferenceDateSource | APPLICATION_DATE 하나만 등록. APPLICATION_REFERENCE_DATE alias 없음 |
| ResidentRegistrationCondition | required_region: RegionSnapshot, reference_date_source: Enum. 규칙 실행 타입은 아님 |
| EvaluationEvidence | source, fact_as_of_date, region snapshot 또는 None, fact_type=RESIDENT_REGISTRATION, field_path=resident_registration.region |
| ResidentRegistrationDetails | reference_date: date 또는 None, evidence: tuple. 평가일 없음 |
| EvaluationDetails | 현재 ResidentRegistrationDetails만 허용하는 결과 타입 별칭. 미래 타입은 아직 없음 |
| RuleEvaluation | 기존 7개 인자 순서 유지. evaluated_value에 RegionSnapshot, expected_condition에 주민등록 Condition, reason_code에 기존 주민등록 Enum을 추가. details=None 한 필드 추가 |
| PolicyEvaluation | reason_codes에 두 Enum 허용. 집계 알고리즘은 변경하지 않음 |
| ResultValidationError | EngineValidationError 하위 예외. code/field만 갖는 결과 계약 오류. 정상 UNKNOWN이 아님 |

결과 계층에는 ResidentRegistrationFact/ResidentRegistrationResolution/UserProfile을 저장하지 않는다. 원본 resolver의 used_facts 각 항목은 향후 adapter에서 region/as_of_date/source 스냅샷으로 옮길 수 있다. resolved_region은 evaluated_value에, required_region은 expected_condition에, 실제 reference_date와 선택 fact 날짜는 details에 남긴다. 평가일은 PolicyEvaluation.context.as_of를 사용한다. sources는 evidence.source에서 확인할 수 있으므로 중복 목록을 저장하지 않는다.

### 검증 및 호환성

- 현재 Resolver reason 8개를 같은 Enum 멤버로 허용한다. 문자열 자유입력과 오류 코드는 reason으로 거부한다. 주민등록 조건에서는 MATCH/PASS, MISMATCH/FAIL, 나머지/UNKNOWN 조합을 검사한다. 지역 비교나 정책 판정을 재실행하지 않는다.
- 공통 missing_fields는 machine path tuple로 유지한다. reference_date 경로도 허용하며 한국어 질문·mutable list는 거부한다.
- 선택 evidence는 tuple이며 등록된 출처·fact_type·field_path·snapshot·정확한 date 타입만 허용한다. 날짜 문자열/datetime/bool 자동 변환은 없다. 선택 근거가 있다면 정책 기준일과 날짜가 같아야 하고, 서로 상충하는 지역이나 관찰값과 다른 지역은 결과 계약 오류다.
- 정보 없는 details/reference_date/evidence는 표현 가능하다. details=None은 기존 atomic 결과의 기본이다. 결과 모델은 추적 정보가 없는 주민등록 결과도 표현할 수 있으므로 **향후 adapter는 원본에서 제공된 근거가 모두 전달됐는지 별도로 검사해야 한다**. 불완전한 수동 결과를 adapter 검증 완료로 취급하지 않는다.
- 기존 positional/keyword 생성자·객체 동등성·repr·PolicyEvaluation.to_dict의 기존 키와 값은 유지한다. details=None은 repr 및 JSON에서 생략한다. dataclasses.fields/asdict에는 새 필드가 나타나는 additive 변화가 있다. 기존 evaluator/CLI/로더/테스트 호출부는 수정하지 않았다.
- RuleEvaluation.to_dict()를 추가했다. Enum.value/date ISO/스냅샷 dict/tuple list/None을 직렬화하고 반환된 dict 변경은 내부 객체에 영향을 주지 않는다. FastAPI/Pydantic/OpenAPI는 없다.
- Resolver가 Status를 models에서 import하므로 결과 모델은 Resolver를 모듈 로딩 시 역으로 import하지 않는다. reason union은 TYPE_CHECKING 전방 참조이며 실제 Enum 검증은 생성 시 국소 import로 수행한다. 향후 런타임 타입 힌트 reflection을 쓰는 API schema를 도입할 때 해당 전방 참조의 명시적 해석을 검토한다.

### 미래 확장성 및 제한

Birth의 관찰 날짜/범위, ResidenceHistory의 기간/OR 조건, Income의 금액·주체·기간·연도·단위는 각각 새로운 typed value/condition/detail 후보가 된다. 날짜의 ISO 표현과 정수 scalar 표현은 이미 가능하지만, **현재 RuleEvaluation의 관찰값에 date나 임의 income dict를 허용한 것은 아니다**. 이번에는 future Birth/History/Income 결과 종류를 만들거나 동작한다고 주장하지 않는다. 다음 실제 resolver 승인 시 좁은 union을 확장한다. EvidenceFactType도 현재 주민등록 하나만 등록했다.

### 검증 기록·남은 범위

작업 전 **313 passed in 2.25s**, 최종 구현 후 **401 passed in 2.81s**. 신규 결과 모델 테스트는 88개다. 기존 313개 테스트의 파일/기대값을 수정하지 않았다. Git 저장소가 아니므로 SHA256 기준선 28개 파일을 비교했다. 기존 파일 중 models.py/공개 export와 문서 4개만 변경했고, 결과 타입 모듈과 테스트 파일만 추가했다. evaluator/loader/resolver/facts/기존 테스트/데이터는 모두 기존 해시와 동일하다.

Adapter 변환 함수, evaluator routing, specialized PolicyRule/PolicyReferenceContext, 실제 정책 JSON, 다른 Fact, API/UI/금융/What-if/LLM은 미구현이다. 기준일 밖 충돌까지 거부하는 M1.6B 동작은 그대로이며 책임 분리 제안은 기술부채로 유지한다.

최종 판단: **READY_FOR_ADAPTER**. 이는 결과 표현 모델의 준비 상태이며 전체 Policy Engine 연결이나 실제 정책 실행 준비를 뜻하지 않는다.

다음 가장 작은 작업: 독립 ResidentRegistrationResolution을 위 결과 타입으로 옮기는 순수 adapter 하나와 상태·사유·누락·선택 근거·날짜 및 불일치 오류 테스트만 추가한다. evaluator/정책 Rule/JSON 연결은 계속 별도 단계다. adapter의 바인딩 불일치는 ResultValidationError 흐름을 사용하되 구체 입력 검증과 고정 오류 코드는 adapter 계약에서 확정한다.

## 21. M1.6E — IMPLEMENTED: 독립 주민등록 Adapter

### 인터페이스와 배치

위치: `backend/policy_engine/adapters/resident_registration.py`. `adapters/__init__.py`에서 함수 하나만 공개한다. 루트 공개 인터페이스나 기존 호출부는 변경하지 않았다.

```python
adapt_resident_registration_resolution(
    *,
    rule_id: str,
    resolution: ResidentRegistrationResolution,
    policy_condition: ResidentRegistrationCondition,
    evidence_refs: tuple[str, ...] = (),
) -> RuleEvaluation
```

rule_id는 기존과 동일하게 비어 있지 않은 문자열이며 별도 ID 정규식은 도입하지 않았다. policy_condition은 결과가 설명할 요구와 APPLICATION_DATE 바인딩을 명시한다. 요구 지역/날짜를 또 별도 인자로 받지 않는다. Resolution에는 날짜 바인딩의 종류가 없으므로 condition이 그 의미를 제공한다. 실제 신청 접수나 사실 진위가 검증됐다는 뜻은 아니다.

### 필드별 변환

| Resolver 또는 호출 입력 | RuleEvaluation 위치 | 처리 |
|---|---|---|
| rule_id | rule_id | 그대로 |
| status | status | 같은 Status 객체. PASS/FAIL/UNKNOWN 재판정 없음 |
| reason_code | reason_code | 같은 ResidentRegistrationReasonCode 멤버. generic 사유로 축약하지 않음 |
| missing_fields | missing_fields | 원본 tuple 그대로. 새 누락 추론·질문 생성 없음 |
| resolved_region | evaluated_value | RegionSnapshot 또는 None |
| policy_condition | expected_condition | 원본 불변 Condition 그대로 |
| required_region | expected_condition.required_region | 입력 condition의 요구와 일치하는지만 확인 |
| reference_date | details.reference_date | 원본 date/None |
| used_facts | details.evidence | 각 항목의 지역 snapshot/사실 날짜/source를 전부, 같은 순서로 변환 |
| fact_as_of_date | 각 evidence.fact_as_of_date | 중복 메타데이터가 선택 근거와 동일한지 확인해 누락 없이 표현 |
| sources | 각 evidence.source | 파생 목록이므로 별도 복제하지 않음. 출처 종류는 그대로 보존 |
| evidence_refs | evidence_refs | 정책 근거 tuple 그대로. 사용자 사실 근거와 섞지 않음 |

evaluation_date는 M1.6D 계약대로 leaf detail에 중복 저장하지 않는다. 향후 상위 정책 평가 context와의 연결에서 사용해야 하며 이번 함수는 PolicyEvaluation/context를 만들지 않는다. 위 ‘손실 없음’은 조건 결과와 선택 근거 표현에 대한 계약이다. 독립 RuleEvaluation만으로 원본 평가일을 복원할 수 있다고 주장하지 않는다.

관찰값과 요구조건은 현재 M1.6D의 정해진 필드에 둔다. details에 임의 observed/expected dict를 추가하거나 평가값을 문자열로 바꾸지 않았다. selected fact가 없으면 evidence는 빈 tuple이며 관찰값은 None이다. 정확한 날짜의 region=None 근거가 있다면 날짜/source를 보존하고 지역은 None으로 남긴다. 전체 입력 fact 묶음이나 UserProfile/경제정보는 받지도 저장하지도 않는다.

### 변환 계약 검증과 재판정의 경계

새 예외 클래스 없이 기존 `ResultValidationError(code, field)`를 재사용한다.

| 신규 고정 code | 의미 |
|---|---|
| INVALID_RESOLUTION | Resolution 객체 타입 오류 |
| INVALID_POLICY_CONDITION | Condition 타입 오류 |
| INVALID_RESOLUTION_REGION | 스냅샷으로 변환할 지역의 타입 오류 |
| RESOLUTION_CONDITION_MISMATCH | condition과 resolution이 서로 다른 요구 지역을 설명 |
| INVALID_RESOLUTION_EVIDENCE | used_facts가 불변 tuple/등록 Fact 구조가 아님 |
| RESOLUTION_EVIDENCE_MISMATCH | 공통 관찰값/사실 날짜와 사용 근거의 중복 메타데이터 불일치, 또는 근거 없이 해당 메타데이터만 존재 |

rule_id, status/reason, machine path, date 표현, source 및 결과 detail 정합성은 **기존 M1.6D 결과 모델 생성자의 검증**을 사용한다. 결과 타입/Resolver 검증 체계를 복제하지 않는다. 정상 상태로 바꾸는 catch 구문은 없다.

Resolution은 frozen이지만 생성자에 의미 검증이 없는 공개 dataclass라 `replace`로 구조가 맞지 않는 객체를 실제로 만들 수 있다. 위 검사는 변환 과정에서 정보를 버리거나 다른 요구를 연결하지 않기 위한 구조 검증이다. 선택 근거의 날짜와 중복 fact_as_of_date를 확인하는 것이며, 신청 기준일 선택·과거/미래 비교를 새로 하지 않는다. 관찰 지역과 **요구 지역**의 일치 여부도 판정하지 않는다.

Adapter는 Resolver 결과를 신뢰하는 표현 경계다. 직접 수작업한 Resolution의 자격 의미를 인증하는 검증기가 아니다. 동일한 상태/사유 조합을 가진 수작업 UNKNOWN에 관찰 지역이 존재해도 PASS로 올리지 않는다. 수작업 PASS의 관찰값이 요구와 다르더라도 상태를 다시 계산하지 않는다. 실제 서비스의 정상 입력은 Resolver에서 생성한 결과여야 한다.

Resolver가 오류를 내면 Resolution 자체가 생성되지 않아 Adapter는 호출되지 않는다. Fact→Resolver→Adapter 호출 흐름에서 원래 ResidentRegistrationValidationError가 그대로 전파되는 테스트로 확인했다. 오류 객체를 Resolution 인자로 넘기는 것은 별도의 입력 타입 오류이며 ‘Resolver 오류의 정상 결과 변환’ 경로가 아니다.

### 순수성·범위·검증

시계·외부 API·DB·파일 I/O·변경 가능한 전역상태를 사용하지 않는다. 입력 fact를 선택/삭제/정렬하지 않고 Resolver의 선택 순서를 보존한다. 같은 입력은 같은 결과/JSON/repr를 만든다. condition을 공유해도 불변 객체이므로 입력을 수정하지 않는다. 범용 Adapter 프레임워크나 미래 Adapter용 빈 파일은 없다.

작업 전 **401 passed in 1.90s**, 최종 전체 pytest는 **449 passed in 2.51s**. 신규 테스트는 48개다. 필수 작은 통합 사례 3개(안산 PASS, 수원 FAIL, fact 없음 UNKNOWN)와 추가 파이프라인 오류·과거 충돌·순서/중복·평가일 분리 사례가 모두 통과했다. 기존 테스트 기대값은 변경하지 않았다.

Git 저장소가 아니므로 기존 30개 파일의 SHA256 기준선을 비교했다. 기존 파일은 이 명세·ARCHITECTURE·DATA_MODEL 문서 3개만 변경했고 나머지 27개는 동일했다. adapters 패키지의 함수/공개 파일 2개와 신규 테스트 파일 1개만 추가했다. 기존 모델·Resolver·evaluator·loader·Fact·모든 기존 테스트·데이터는 변경하지 않았다.

IMPLEMENTED: ResidentRegistrationResolution → RuleEvaluation 독립 순수 Adapter.

NOT IMPLEMENTED: evaluator routing, specialized PolicyRule/로딩, 실제 정책 JSON, ApplicationWindow, 다른 Fact, API/UI/DB/금융/What-if/LLM. Resolver의 기준일 밖 충돌 오류는 기존대로 유지한다.

최종 판단: **READY_FOR_RULE_ROUTING**. 이는 독립 Adapter의 준비 상태이며 실제 정책 실행/전체 자격 판정 완성을 뜻하지 않는다.

다음 가장 작은 작업 1개: 주민등록 specialized leaf와 기존 원자/그룹을 함께 실행할 최소 routing 계약을 문서로 정한다. facts/reference context 전달, 평가일 일치 검사, 명시적 dispatch와 기존 진리표 보존을 확정하고, JSON 로딩·실제 정책 도입은 별도 단계로 둔다.
