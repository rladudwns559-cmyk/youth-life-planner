# 데이터 모델

불변 Benefit Acceptance 결정 기록/상태는 **34절 M2.46**, 한 target의 이력 Context/명시 조회는 **35절 M2.48**, 내부 평가 결과 값은 **36절 M2.50**을 따른다. 실제 현재 evaluator·adapter/Bridge 연결은 아직 없다. 과거 절의 미구현 표기는 당시 이력이다.

독립 혜택 정의 BenefitSnapshot/4개 Enum은 **33절 M2.43**을 따른다. 구조 유효성을 표현하며 지문·검토/Acceptance·Bridge·Cashflow 적용 상태는 포함하지 않는다.

현재 독립 Cashflow 도메인 모델은 21절 M2.1을 따른다. 기존 정책 모델과 분리한다.

독립 정책 적용범위 값 ApplicabilityScope는 22절 M2.6을 따른다. 기존 PolicyEnvelope의 필드는 변경하지 않았다.

독립 자격조건 의미 값 RequiredCondition은 23절 M2.7, 조건 목록 ConditionInventory는 24절 M2.8, ConditionBinding은 25절 M2.9를 따른다. 구조/지문/Review facts 수집은 ARCHITECTURE.md45절, Result 값과 파생 상태는 이 문서32절, 공개 evaluator 연결은 ARCHITECTURE.md47절 M2.39를 따른다. 새 모델 필드는 추가하지 않았다.

EligibilityCoverage의 로컬 구조 입력 모델은 26절 M2.11을 따른다. status·Policy·ReviewContext는 포함하지 않는다.

독립 InventoryCompletenessReview metadata는 27절 M2.13, ImplementationBindingReview는 28절 M2.14, CoverageReviewContext collection은 29절 M2.15, Review match 결과 값은 30절 M2.21, private Integration Findings 값은 31절 M2.35, EligibilityCoverageResult는32절 M2.38을 따른다. 세 지문 계산은 COVERAGE_FINGERPRINT_SPEC.md, 독립 review lookup·matcher는 ARCHITECTURE.md36~38절, integration gate는45절을 따른다. 공개 evaluate_eligibility_coverage는 기존 Gate1회→Result factory1회만 연결한다. 상세 현재 계약은 ELIGIBILITY_COVERAGE_RESULT_SPEC.md37절이다.

## 1. 기획 PDF에서 확정된 요구사항

정책 원문과 구조화된 조건을 분리하고 조건별 근거를 추적한다. 생활비 실수령소득은 정책 심사용 소득과 별개다. 각 결과는 PASS/FAIL/UNKNOWN과 사유를 제공한다. 사용자 정보는 초기 MVP에서 영구 저장하지 않는 방향이다.

## 2. 이번 M1에서 승인한 결정

DB 모델이 아닌 frozen dataclass를 사용한다.

| 모델 | 필드/역할 |
|---|---|
| UserProfile | age, region, student_status(bool), employment_status, monthly_income, policy_facts(tuple). 기본값 None은 미입력. |
| PolicyFact | field, value, fact_basis. M1 정책 사실은 household_income만 지원. |
| FactBasis | basis, subject, period, reference_year, unit. 소득 비교 양쪽의 동일한 의미 확인. |
| PolicyRule | rule_id, field, operator, value, fact_basis, evidence_refs. |
| RuleGroup | rule_id, operator(ALL/ANY/NOT), children(tuple). |
| Policy | policy_id, policy_name, rule_version, root, synthetic, test_only. |
| PolicySet | schema_version, dataset_version, policies, synthetic, test_only. |
| RuleEvaluation | rule_id, status, reason_code, evaluated_value, expected_condition, missing_fields, evidence_refs. |
| PolicyEvaluation | policy_id, overall_status, rule_results, missing_fields, reason_codes, context, rule_version. to_dict에 display_status 포함. |
| EvaluationContext | as_of(date), dataset_version, engine_version. 모두 명시적이거나 고정 버전 상수. |

등록한 판정 필드: age(int), region(str), student_status(bool), employment_status(str), household_income(int). monthly_income은 프로필에서 보관할 수 있지만 정책 Rule의 필드로 등록하지 않는다. 자동 환산도 없다.

- 나이·금액은 음수가 아닌 정수. bool은 정수로 취급하지 않는다.
- region은 공백뿐인 문자열을 거부하며 자동 정규화나 지역 계층 추론은 하지 않는다.
- employment_status는 M1에서 employed/unemployed/None. student_status는 True/False/None이며 취업과 독립적이다. 실제 상태 확장은 별도 결정이다.
- policy_facts와 규칙의 in 값, 자식 규칙, 근거는 tuple로 고정한다.
- FactBasis는 값이 없을 수 있지만 household_income 규칙에는 기준을 반드시 명시한다. 사용자 값이 있어도 기준이 없거나 다르면 UNKNOWN.
- expected_condition은 원자 규칙의 field/operator/value/fact_basis 또는 그룹의 operator/child_ids다.
- 모든 노드의 rule_id는 데이터셋 전체에서 유일하다. 정책 ID도 유일하다.
- 결과는 원자/그룹 모두 root-first 순서로 평탄화하며 원본 규칙 순서를 유지한다.
- 그룹과 정책의 missing_fields는 모든 하위 결과를 중복 제거하고 정렬한 목록이다. 다른 조건 때문에 전체 FAIL/PASS가 되어도 미확인 항목을 숨기지 않는다.
- evaluated_value는 해당 조건의 단일 입력값이다. reason_code에는 입력값이나 프로필을 삽입하지 않는다. 결과 자체는 경제정보를 포함할 수 있으므로 실제 사용자 결과를 로그에 남기면 안 된다.
- synthetic/test_only는 반드시 True. 공식 URL 대신 저장소의 합성 조건 위치를 evidence_refs로 사용한다.

샘플 기준: 2026년 월 단위 합성 가구 총소득, KRW, 3,000,000 이하. 이 기준은 실제 정책·중위소득·행정 기준과 무관하다.

## 3. 향후 결정해야 할 사항

실제 Policy의 공식 URL/신청기간/서류/원문 모델, 지역 코드와 나이 기준일, 소득기준표 참조, 추가 조건 필드, 개인 정보 보관, 금융상품·금융계산·ScenarioComparison은 이번 모델에 구현하지 않는다.

## 4. M1.6A — IMPLEMENTED: 주민등록 입력 모델

이번 구현 승인은 아래 세 모델과 입력 검증에 한정한다. 앞의 M1 모델과 UserProfile.region, PolicyFact, EvaluationContext는 변경하지 않았다.

위치: `backend/policy_engine/facts/resident_registration.py`. 기존 models.py를 더 키우지 않고 사실 종류별 모듈을 둘 수 있도록 작은 facts 패키지에 분리했다. 다른 사실 모델이나 resolver용 빈 모듈은 만들지 않았다.

| 모델 | 구현된 계약 |
|---|---|
| RegionRef | frozen dataclass. sido: str, sigungu: str 모두 필수. 완전하고 허용된 canonical 쌍만 허용 |
| RegistrationSource | str Enum. SELF_REPORTED, MANUALLY_VERIFIED, OFFICIAL_DATA |
| ResidentRegistrationFact | frozen dataclass. region: RegionRef 또는 None, as_of_date: 정확한 date 또는 None, source: RegistrationSource 필수 |

지역 목록은 MVP_INTERNAL_REGION_V1 내부 값이다. 공식 행정코드가 아니다. 최소 쌍은 GYEONGGI/ANSAN, GYEONGGI/SUWON이며, 서로 다른 유효 키의 잘못된 조합을 검증하기 위한 비교 지역 SEOUL/JONGNO만 추가했다. 전국 데이터셋이나 공식 코드 필드는 없다.

**승인된 변경:** M1.6 원안은 RegionRef 내부 None을 허용했지만 M1.6A 직접 지시는 완전한 구조와 필수 키를 요구한다. 따라서 부분 RegionRef는 INVALID_REGION이며, 정보 부족은 상위 Fact.region=None으로 표현한다. 이 차이는 RESIDENT_REGISTRATION_FACT_SPEC.md 17절에 기록한다.

검증 오류는 기존 EngineValidationError를 상속하는 ResidentRegistrationValidationError이며 code와 field를 제공한다. INVALID_REGION, INVALID_DATE, INVALID_SOURCE를 구분한다. 정상 판정 상태는 생성하지 않는다. 필수 생성자 인자 자체의 누락은 Python TypeError로 거부하며, source=None이나 잘못된 source 값은 INVALID_SOURCE다.

문자열 날짜, datetime, 숫자·bool 날짜를 자동 변환하지 않는다. source 문자열도 Fact 생성자가 Enum으로 변환하지 않는다. 필요하면 호출 경계에서 date.fromisoformat 및 RegistrationSource(...)를 명시적으로 사용한다. 날짜가 과거인지 미래인지는 이 모델이 판단하지 않는다.

두 모델의 작은 to_dict()는 canonical 키, ISO 날짜 문자열, Enum.value, None을 표현한다. 범용 직렬화/역직렬화 프레임워크, JSON 입력 파서나 실제 정책 로더는 추가하지 않았다.

**M1.6A 완료 시 미구현:** source의 진위 확인, 기준일 비교, 미래 추정 차단 판정, fact 간 모순·중복 처리, resolver, Rule/프로필 연결, 실제 정책 JSON. 이후 M1.6B의 구현 범위는 아래 5절을 따른다.

## 5. M1.6B — 독립 주민등록 판정 결과

RegionRef/RegistrationSource/ResidentRegistrationFact는 수정하지 않았다. 새 모델과 함수는 `backend/policy_engine/resolvers/resident_registration.py`에 분리한다.

| 모델/인터페이스 | 계약 |
|---|---|
| ResidentRegistrationResolution | frozen dataclass. status, reason_code, required_region, reference_date, evaluation_date, resolved_region, fact_as_of_date, missing_fields, used_facts |
| sources | used_facts에서 중복 제거·사전순 정렬한 RegistrationSource tuple 속성 |
| ResidentRegistrationReasonCode | 기존 명세의 활성 8개 사유. M1 ReasonCode나 Status enum을 변경하지 않음 |
| resolve_resident_registration | facts Sequence를 tuple로 스냅샷해 검토. 날짜 인자는 정확한 date이며 reference_date=None은 UNKNOWN, evaluation_date=None은 오류 |

used_facts는 정확한 날짜에 선택한 근거만 담는다. 출처가 다르지만 날짜·지역이 같은 근거는 함께 보존하며 완전히 동일한 근거는 제거한다. 지역을 가진 근거가 있다면 region=None 후보를 결과 근거에 추가하지 않는다. 일치 날짜가 없거나 기준일이 미래면 사용 근거가 없다. to_dict()는 Enum.value, 날짜 ISO 문자열, selected facts의 명시적 표현만 반환한다.

현재 함수는 알려진 같은 날짜의 다른 지역을 입력 묶음 전체에서 먼저 검사한다. 상충은 UNKNOWN이 아닌 기존 validation error다. source에 따른 우선순위, 가장 가까운 날짜 선택, 과거 연장/미래 예측은 없다. 상세 사유·오류 우선순위는 RESIDENT_REGISTRATION_FACT_SPEC.md 18절에 기록한다.

**여전히 미구현:** source의 진위 확인, 정책 원자/프로필/JSON 연결, 생년월일·거주이력·신청기간·지원금, 다른 서비스 기능.

## 6. M1.6D — IMPLEMENTED: 결과 표현 확장

`result_types.py`의 frozen/slots 모델: RegionSnapshot, ResidentRegistrationCondition, EvaluationEvidence, ResidentRegistrationDetails. 바인딩은 ReferenceDateSource.APPLICATION_DATE, fact 종류는 EvidenceFactType.RESIDENT_REGISTRATION만 허용한다. Fact/Resolution/전체 프로필 대신 지역·선택 사실 날짜·출처의 최소 값을 보존한다.

RuleEvaluation은 기존 인자 순서를 유지하고 `details=None`만 추가했다. evaluated_value는 기존 scalar/None 및 RegionSnapshot, expected_condition은 기존 원자/그룹 및 주민등록 Condition, reason_code는 기존 두 Enum을 허용한다. PolicyEvaluation.reason_codes도 동일한 유한 Enum 집합이다.

details는 정책 reference_date와 evidence tuple을 갖는다. fact_as_of_date는 각 evidence에, 평가일은 상위 context.as_of에 둔다. 근거가 없거나 날짜가 없는 정상 UNKNOWN도 표현 가능하다. 정책 evidence_refs와 사용자 사실 evidence는 분리한다. 원본 출처의 신뢰도/진위를 판정하지 않는다.

신규 구조·타입·날짜·tuple·경로·결과 사유/상태·근거의 날짜/관찰값 정합성 위반은 ResultValidationError(code/field)다. 오류를 UNKNOWN으로 바꾸지 않는다. 기존 atomic JSON/repr에는 details=None을 출력하지 않는다. asdict/fields에는 additive 필드가 보인다. 상세 최신 계약은 RESOLVER_RULE_ADAPTER_SPEC.md 20절이다.

**M1.6D 당시 미구현:** Adapter, 새 정책 Rule/기준일 context, evaluator 연결, 실제 JSON, 미래 사실 결과 타입. 이후 Adapter 상태는 아래 7절이다. 기존 UserProfile/PolicyFact/FactBasis 및 resolver 동작은 유지한다.

## 7. M1.6E — IMPLEMENTED: 결과 변환

새 도메인 타입 없이 기존 ResidentRegistrationResolution/Condition과 M1.6D 결과 타입을 사용하는 독립 Adapter를 추가했다. Resolution.resolved_region은 RegionSnapshot 관찰값으로, policy_condition은 구조화된 요구로, reference_date와 used_facts는 details 및 EvaluationEvidence tuple로 연결한다. selected fact의 region/as_of_date/source를 모두 보존한다. None 관찰값과 빈 근거는 생성하지 않고 그대로 표현한다.

정책 evidence_refs는 사용자 fact evidence와 분리한다. 평가일은 M1.6D처럼 상위 context 책임이며 Adapter에 별도 중복 인자로 받거나 leaf에 저장하지 않는다. 변환 입력 간 요구값과 중복 메타데이터의 구조 불일치는 ResultValidationError이며 정상 UNKNOWN으로 바꾸지 않는다. 상태/사유 판정은 기존 Resolver 책임이다.

Adapter는 전문 PolicyRule/RuleNode 등록이나 evaluator 연결을 의미하지 않는다. 실제 정책 JSON·다른 Fact는 계속 미구현이다. 최신 계약은 RESOLVER_RULE_ADAPTER_SPEC.md 21절이다.

## 8. M1.6G — IMPLEMENTED: 주민등록 정책 leaf·평가 입력

| 모델 | 구현 필드 |
|---|---|
| ResidentRegistrationRule | rule_id, required_region: RegionRef, reference_date_source: 기존 APPLICATION_DATE 멤버, evidence_refs: 비어 있지 않은 str tuple |
| PolicyReferenceContext | policy_id, application_date: 정확한 date 또는 None(기본값) |
| EvaluationFacts | resident_registrations: ResidentRegistrationFact tuple, 기본 빈 tuple |

모두 frozen/slots이며 작은 to_dict()만 제공한다. Rule은 정책 요구만 저장하며 사용자 facts·날짜 실제값·상태를 넣지 않는다. context는 평가일을 복제하지 않는다. facts는 입력 순서와 중복/충돌 주장을 그대로 보존하고 Resolver의 선택/정규화 책임을 가져오지 않는다. UserProfile.region fallback은 없다.

RuleNode는 기존 PolicyRule | ResidentRegistrationRule | RuleGroup이다. children/root 검증을 같은 타입 집합으로 넓히고 재귀 순회 및 트리/데이터셋 전체 ID 유일성을 유지한다. Policy의 합성 자료 제한은 그대로다. PolicySet은 m1.0만 허용하며 specialized 노드 포함을 거부한다.

Rule 오류는 PolicyDataError, context 오류는 ContextValidationError, facts 컨테이너 오류는 ProfileValidationError다. 개별 Fact/RegionRef 생성 검증은 기존 오류를 유지한다. application_date=None은 유효한 미입력 데이터이며 이 단계에서 상태를 계산하지 않는다.

NOT IMPLEMENTED: routing, context 바인딩, Resolver/Adapter 연결, loader m1.1, 실제 정책 JSON. 세부 최신 계약은 RULE_ROUTING_SPEC.md 21절이다. 기존 모델 이름·호출부·결과 표현은 바꾸지 않았다.

## 9. M1.7 — IMPLEMENTED: PolicySet 버전별 Loader

PolicySet.schema_version은 이제 정확한 문자열 m1.0/m1.1을 허용한다. 공통 validate_schema_version으로 Loader와 domain 생성자의 지원 범위를 일치시킨다. m1.0에서 ResidentRegistrationRule을 포함하는 트리는 계속 거부하며, m1.1은 기존 RuleNode union을 담을 수 있다. 버전은 JSON 문법/허용 종류의 계약이며 ENGINE_VERSION은 변경하지 않았다.

기존 frozen 모델·tuple·ID 유일성·synthetic/test_only 제한은 유지한다. Loader가 JSON list를 tuple로, 지역 object를 기존 RegionRef로, APPLICATION_DATE 문자열을 기존 Enum으로 명시적으로 변환한다. 알 수 없는 값·잘못된 타입·추가 키는 거부하며 다른 버전으로 fallback하지 않는다. 결과 타입·facts/context·Resolver/Adapter는 수정하지 않았다.

Loader 결과의 각 Policy를 M1.6H evaluate_policy_tree로 평가할 수 있다. specialized 배치 routing은 아직 없고 기존 evaluate_policies를 이를 위한 자동 경로로 확장하지 않는다. 실제 정책 JSON과 미래 Fact도 미구현이다. 상세 최신 계약 및 승인된 테스트 1개 변경은 RULE_ROUTING_SPEC.md 23절이다.

## 10. M1.10 — IMPLEMENTED: 정책 원문 근거 모델

`sources/models.py`의 SourceDocument/SourceEvidence와 `sources/registry.py`의 SourceRegistry를 추가했다. 기존 Policy/PolicySet/UserProfile/RuleEvaluation/Fact 및 evidence_refs 문자열 tuple은 변경하지 않았다.

SourceEvidence는 locator_id, section, page/table_position, meaning_summary, applicable_policy_ids tuple, verified_at, verification_status, status를 보관한다. 문서 ID는 부모 SourceDocument의 포함 관계로 결정한다. SourceDocument는 M1.9 5절 필드를 보존하며 locators/previous_urls/supersedes는 tuple이다. supersedes의 내부 값은 ID/version pair이며 dict 표현으로 직렬화한다. registry.sources는 비어 있지 않은 문서 tuple이고 문서 ID·문서 내 locator 중복은 동일 정의라도 오류다.

SourceType, SourceStatus(ACTIVE/SUPERSEDED/WITHDRAWN), VerificationStatus(DRAFT/VERIFIED/STALE)는 별도 enum이다. RegistrationSource를 재사용하지 않는다. 날짜는 정확한 date/None이고 datetime 변환이 없다. 모델은 frozen/slots, Document/Evidence는 keyword-only다. to_dict는 새 JSON 친화 값만 반환한다.

SourceValidationError는 기존 PolicyDataError의 하위 타입이고 code/field를 제공한다. canonical 문자열 ref의 문법과 존재·수명을 검사하지만 정책의 source binding/검토/최신성 gate는 수행하지 않는다. DRAFT/STALE source도 ACTIVE라면 resolve할 수 있으므로 production 승인으로 해석하면 안 된다.

IMPLEMENTED: 메모리 source 모델·lookup·ref resolve·중복/구조 검증. NOT IMPLEMENTED: sources.json loader, PolicyEnvelope/DatasetManifest, production source data, freshness enforcement, policy/User evidence 통합. 상세 필드·오류·범위는 POLICY_DATA_ENVELOPE_SPEC.md 26절이 최신 계약이다.

## 11. M1.11 — IMPLEMENTED: Source Registry JSON 경계

sources/loader.py의 parse_source_registry / load_source_registry를 sources 패키지에서 공개한다. 10절의 도메인 모델·생성자·tuple·오류·상태 의미는 변경하지 않았다. JSON은 schema_version=source-registry-1.0 및 sources만 허용하며 모델의 필수 인자는 필수 JSON 키, 기본값이 있는 인자는 선택 키로 정의했다. 모든 계층의 추가 키를 거부한다.

정확한 JSON 배열만 tuple로, canonical Enum 문자열만 기존 enum으로, null 또는 정확한 YYYY-MM-DD 문자열만 date/None으로 명시적으로 변환한다. datetime 절삭·문자열 숫자·공백·별칭 보정은 없다. JSON 중복 key는 decode 단계, source/locator ID 중복은 기존 모델이 거부한다. 전부 성공해야 기존 SourceRegistry를 반환한다.

synthetic/test_only 필드는 source 모델·JSON 계약에 없으므로 임의 추가하지 않았다. 새 합성 sources.json과 SOURCES_README.md가 용도를 명시한다. 이 loader는 공식성·production 승인·검토·최신성을 확인하지 않는다. IMPLEMENTED: strict source loader. NOT IMPLEMENTED: PolicyEnvelope/DatasetManifest, production sources.json/실제 정책 자료, policy/source binding, freshness enforcement. 상세 최신 계약은 POLICY_DATA_ENVELOPE_SPEC.md 27절이다.

## 12. M1.12 — IMPLEMENTED: PolicyEnvelope 도메인

`policy_data/envelope.py`의 frozen/slots PolicyEnvelope는 기존 Policy를 그대로 포함한다. 정책 ID·이름·rule_version·root·synthetic/test_only는 읽기 전용 property로 위임해 복제하지 않는다. source_document_ids도 source_bindings에서 계산한다. 기존 Policy/PolicySet/RuleNode·loader·Source 모델은 변경하지 않았다.

저장 metadata는 schema_version=policy-data-1.0, rule_schema_version=m1.1, edition_id(첫 지원은 ASCII 4자리 연도), jurisdiction, category, dataset_version, evaluation_scope, coverage, source_bindings, verification_status, last_verified_at, lifecycle_status, effective_from/to다. 작은 SourceBinding과 PolicyCoverage는 tuple 기반이며 각각 문서 확인본 고정과 leaf/제외 조건 범위를 표현한다. category=YOUTH_SUPPORT, scope=CONDITION_SLICE만 지원한다.

PolicyVerificationStatus(DRAFT/VERIFIED/STALE), PolicyLifecycleStatus(ACTIVE/ENDED)는 Source의 두 상태와 별도 타입이다. VERIFIED에는 확인일이 필요하나 production 승인을 의미하지 않는다. 날짜는 정확한 date/None이며 현재 시각·신청기간으로 보정하지 않는다. 기존 Policy의 True/True 제한 때문에 이 단계는 합성/test_only만 지원한다.

`validate_envelope_sources(envelope, registry)`는 문서 존재·확인본 일치·기존 resolve·적용 정책·사용 locator의 최소 확인일을 순수하게 검사한다. 객체는 registry를 보관하지 않는다. 구조 오류는 EnvelopeValidationError(PolicyDataError 하위), 기존 근거 오류는 SourceValidationError 그대로다. 전체 성공 시 None이며 사용자 상태를 만들지 않는다.

to_dict는 기존 값 serializer를 사용한 도메인 snapshot이고 JSON Loader 형식 확정·구현이 아니다. IMPLEMENTED: envelope 모델과 source registry 검증. NOT IMPLEMENTED: PolicyEnvelope JSON Loader, DatasetManifest, production envelope/false 플래그 수용, production acceptance, freshness enforcement. 최신 상세 계약은 POLICY_DATA_ENVELOPE_SPEC.md 28절이다.

## 13. M1.13 — IMPLEMENTED: PolicyEnvelope JSON 경계

policy_data/loader.py의 parse_policy_envelope / load_policy_envelope를 공개한다. policy-data-1.0 metadata와 m1.1 Policy payload를 한 파일에 포함한다. 외부 policy_id/synthetic/test_only는 내부 Policy와 일치해야 하는 JSON assertion이며 도메인에 중복 저장하지 않는다. policy_name/rule_version/root는 중첩 Policy에만 있고 source_document_ids는 binding에서 계산한다.

메모리 parser가 정확한 object/list·필수/선택 키·canonical Enum·ISO 날짜를 읽어 기존 PolicyEnvelope를 생성한다. Policy payload는 단일 PolicySet adapter를 통해 기존 parse_policy_set을 호출해 읽으며 규칙 파싱을 복제하지 않는다. 기존 PolicyEnvelope/SourceRegistry 모델·validator는 변경하지 않았다.

JSON/file parsing과 validate_envelope_sources 호출은 분리한다. DRAFT/STALE 등은 보존하고 fresh/production 여부를 판단하지 않는다. 기존 to_dict는 snapshot이므로 이번 JSON input serializer와 동일하다고 취급하지 않는다. edition_id의 분기별 granularity는 실제 전체 정책 모델링 전 재검토할 미결정 사항이다.

IMPLEMENTED: strict envelope JSON Loader와 합성 fixture. NOT IMPLEMENTED: DatasetManifest·production acceptance·실제 정책/source·freshness automation·ApplicationWindow/BirthFact/ResidenceHistoryFact. 최신 계약은 POLICY_DATA_ENVELOPE_SPEC.md 29절이다.

## 14. M1.14 — IMPLEMENTED: DatasetManifest

policy_data/manifest.py에 DatasetManifest, ArtifactReference, PolicyEditionReference, SourceRegistryReference를 추가했다. Manifest는 Policy/Registry 객체 대신 ID·edition·버전·파일 artifact 선언·메모리 내용 fingerprint를 보관한다. source_versions는 기존 SourceBinding tuple이다. 같은 정책의 여러 edition 동시 선택과 모든 중복 참조를 거부한다.

M1.9의 dataset_id/version, timezone-aware created_at, freshness_max_age_days, engine_version/artifact SHA256, 정책·source 참조를 유지한다. review_manifest=None은 domain-only 미검토 자료 표현이며 release 승인이 아니다. 별도 verification/release 상태는 추가하지 않았다. 모델은 frozen/slots·tuple이며 to_dict는 UTC 시각과 새 값 컬렉션을 반환한다.

파일 bytes SHA256 선언과 객체 fingerprint를 분리한다. 순수 fingerprint helper는 명시한 집합 순서를 정규화하고 rule children 순서는 보존한다. validate_dataset_manifest는 manifest/envelopes/registry를 명시적으로 받아 정확한 정책 집합·버전·Registry 전체·객체 지문·dataset 전역 rule ID와 기존 validate_envelope_sources를 검증한다. 파일 bytes·실행 빌드·review·freshness는 검사하지 않는다.

IMPLEMENTED: Manifest domain model과 dataset consistency validation. NOT IMPLEMENTED: Manifest JSON Loader·production dataset/acceptance·실제 정책·freshness automation·artifact 파일 검증. 다음은 추가 infrastructure가 아니라 실제 resident slice 데이터 인코딩이며, 현재 True/True 제한의 실제 데이터 수용 경계는 그 작업에서 해결한다. 최신 상세 계약은 POLICY_DATA_ENVELOPE_SPEC.md 30절이다.

## 15. M1.15 — IMPLEMENTED: 실제 데이터 flags와 첫 condition slice

Policy/PolicySet의 실제 False/False는 생성 시 keyword-only InitVar allow_real_data=True를 명시해야 한다. 기존 기본 경로는 합성 True/True만 허용한다. 혼합 flags·잘못된 타입·컨테이너와 각 Policy flags 불일치는 거부한다. InitVar는 도메인 필드나 운영 승인 속성이 아니며 직렬화되지 않는다. 실제 객체의 dataclasses.replace에도 허용 인자를 다시 명시한다.

기존 Envelope loader는 일치하는 외부/내부 False/False를 확인하고 기존 parse_policy_set의 명시적 허용 경로를 사용한다. PolicyEnvelope/SourceRegistry/coverage 모델을 다시 설계하지 않았다. 실제 공식 source 3개는 VERIFIED 확인본이고 실행 Envelope는 DRAFT/CONDITION_SLICE다. root에 주민등록 한 leaf만 있으며 제외 조건을 coverage에 보존한다.

실제 데이터는 data/releases/ansan-youth-2026-10-20-001에 별도 저장한다. 합성 fixtures와 기존 테스트는 불변이다. 실제 신청자 데이터나 원본 HWP는 저장하지 않았다. 정확한 날짜와 지역을 명시한 가상 fact로만 테스트한다. 전체 정책 판정·production 승인·freshness·Manifest 발행은 미구현이다. 상세 계약은 POLICY_DATA_ENVELOPE_SPEC.md 31절과 REAL_POLICY_001_IMPLEMENTATION.md다.

## 16. M1.16A — IMPLEMENTED: 독립 생년월일 사실

facts/birth.py의 BirthFact는 birth_date:date|None과 필수 source:BirthSource만 갖는 frozen/slots 값이다. BirthSource는 SELF_REPORTED/MANUALLY_VERIFIED/OFFICIAL_DATA로, 주민등록 전용 RegistrationSource를 재사용하지 않는다. Enum은 출처 표식이며 인증·판정 우선순위가 아니다.

정확한 date 또는 None만 허용하고 datetime·하위 타입·문자열·숫자는 거부한다. source도 정확한 BirthSource여야 한다. BirthFactValidationError는 ProfileValidationError 하위이며 code/field로 INVALID_DATE(birth.birth_date), INVALID_SOURCE(birth.source)를 제공한다. 필수 생성자 인자 누락은 Python TypeError다. None에 정상 상태를 부여하지 않으며 오류를 UNKNOWN으로 바꾸지 않는다.

to_dict는 ISO 날짜 문자열/None과 source 문자열의 새 dict다. 날짜 파싱·나이 역산·복수 Fact·자동 저장은 없다. facts 패키지 공개 export만 추가하며 기존 UserProfile/ResidentRegistrationFact/RegionRef/EvaluationFacts는 불변이다.

IMPLEMENTED: BirthSource/BirthFact/입력 검증/불변성/최소 값 표현. NOT IMPLEMENTED: BirthDateRule·판정·evaluator·Resolver/Adapter/routing·JSON loader·실제 Q3 birth data. 상세 계약과 검증 기록은 REAL_POLICY_001_BIRTH_SLICE_SPEC.md 19절이다.

## 17. M1.16B — IMPLEMENTED: 독립 출생일 구간 Rule

specialized_rules/birth_date.py의 BirthDateRule은 rule_id/min_birth_date/max_birth_date/evidence_refs만 보유하는 frozen/slots 모델이다. 정확한 날짜 두 개를 요구하고 min ≤ max를 검증한다. 양끝 포함이 고정 의미이며 동일 날짜 구간도 허용한다. 실제 Q3 값이나 age/quarter/reference_date/inclusive 옵션은 기본값·필드에 없다.

rule_id는 비어 있지 않은 정확한 str, evidence_refs는 비어 있지 않은 정확한 tuple[str,...]이다. 기존 ResidentRegistrationRule과 같이 strip/자동 변환을 하지 않고 ref 순서·중복을 보존한다. 실제 데이터의 canonical ref·중복·출처 존재 검증은 후속 연결 경계 책임이다. 구조 오류는 기존 PolicyDataError다. to_dict는 날짜 문자열과 새 근거 list의 값 표현만 반환한다.

IMPLEMENTED: 독립 BirthDateRule structural model·검증·불변성·단위 테스트. NOT IMPLEMENTED: BirthFact 비교·판정·evaluator·RuleNode/결과 타입/routing/loader 연결·actual Q3 birth data. 기존 Fact/RuleNode/PolicyEnvelope/실제 자료는 변경하지 않았다. 상세 계약은 REAL_POLICY_001_BIRTH_SLICE_SPEC.md 20절이다.

## 18. M1.16D — IMPLEMENTED: Birth 결과 값과 공통 결과 수용

result_types.py에 frozen/slots BirthDateCondition(min_birth_date,max_birth_date), BirthDateDetails(birth_source:BirthSource|None)와 네 BirthDateReasonCode를 추가했다. 조건의 날짜는 exact date이고 min ≤ max다. 관찰 출생일은 RuleEvaluation.evaluated_value, 요구 범위는 expected_condition, provenance는 details에 한 번씩만 보존한다.

RuleEvaluation은 birth condition에 한해 date/None을 허용한다. WITHIN→PASS, BEFORE/AFTER→FAIL, MISSING→UNKNOWN을 검증한다. PASS/FAIL에는 date·유효 source·빈 missing_fields, UNKNOWN에는 None 관찰값·정확한 (birth.birth_date,)를 요구한다. details는 유한 typed union이고 condition별 다른 details/reason 혼입은 거부한다. 기존 atomic/resident 값과 출력은 유지한다.

PolicyEvaluation도 같은 유한 reason 검증으로 birth leaf를 보관한다. 직렬화는 기존 _jsonable을 사용하며 새로운 필드나 serializer framework는 없다. 날짜와 reason 방향의 실제 비교는 결과 생성자가 하지 않고 후속 evaluator에 남긴다. 자세한 허용 한계와 현재 계약은 REAL_POLICY_001_BIRTH_RESULT_CONTRACT.md 24절이다.

IMPLEMENTED: Birth 결과 타입·RuleEvaluation 조합 검증·PolicyEvaluation 중첩 표현. NOT IMPLEMENTED: evaluator·BirthFact 비교·RuleNode/routing/loader·actual Q3 data. 기존 정책·사용자 사실 모델·실제 자료는 변경하지 않았다.

## 19. M1.16G — IMPLEMENTED: Birth mixed tree 입력과 노드

M1.16E의 독립 evaluator에 이어, RuleNode/Policy.root/RuleGroup.children의 exact 허용 목록에 BirthDateRule을 추가했다. 모든 노드 사이 ID 유일성은 기존 walk_nodes 기반 검증을 그대로 사용한다. EvaluationFacts.birth는 keyword-only BirthFact|None=None이며 기존 resident positional 인자는 유지한다. 잘못된 birth 타입은 생성 시 ProfileValidationError다.

birth=None이면 to_dict는 기존 resident-only 형태를 유지하고, Fact가 있으면 기존 BirthFact.to_dict 표현을 추가한다. 모델은 frozen/slots이며 age 추론·Fact collection·자동 변환은 없다. dataclasses.fields에는 실제 새 필드가 보이므로 그 기존 기대값 1개를 명시 승인하에 갱신했다.

단일 메모리 Policy는 birth를 실행할 수 있지만 schema가 붙은 PolicySet은 birth를 아직 거부한다. loader/schema와 실제 데이터는 별도 단계다. 기존 Rule/Fact/결과 타입/Envelope는 변경하지 않았다. IMPLEMENTED: Birth RuleNode/EvaluationFacts.birth/단일 mixed routing. NOT IMPLEMENTED: JSON loader support·actual Q3 policy data. 상세 승인 테스트 세 함수와 검증 기록은 REAL_POLICY_001_BIRTH_ROUTING_SPEC.md 25절이다.


## 20. M1.16I — IMPLEMENTED: Birth JSON 경계와 PolicySet 버전

기존 BirthDateRule/Fact/결과 모델 필드는 변경하지 않았다. loader에서 정확한 두 날짜 문자열을 date로 변환하고 여섯 필수 key만 받아 기존 BirthDateRule을 구성한다. min ≤ max와 evidence_refs 불변 조건은 기존 생성자가 검증한다. evidence_refs는 정확한 JSON list → tuple이며 순서·중복을 유지한다.

PolicySet birth guard는 m1.0에만 적용한다. m1.1은 기존 유한 RuleNode 목록의 birth를 수용한다. 기존 m1.0 resident guard와 ID 유일성은 유지한다. 입력 자동 추정/새 schema/새 edition 모델은 없다.

IMPLEMENTED: m1.1 birth_date JSON parser, PolicySet m1.1 birth support, synthetic Loader → Routing. NOT IMPLEMENTED: actual Q3 birth data/locator/PolicyEnvelope 통합, quarter selection. 별도 synthetic fixture의 새 birth source ref는 미등록 논리 참조이며 공식 근거 검증 완료를 뜻하지 않는다. 합성 Envelope의 embedded Policy 전파는 기존 loader 코드 변경 없이 검증했다. 현재 계약·검증 기록은 REAL_POLICY_001_BIRTH_LOADER_SPEC.md 29절이다.

## 21. M2.1 — IMPLEMENTED: 독립 Cashflow 입력·결과

backend/cashflow/models.py의 CashflowInput은 monthly_income/monthly_rent/monthly_fixed_expenses/other_monthly_expenses 필수 int와 user_savings_capacity:int|None=None, monthly_policy_cash_benefit:int=0을 보유한다. Result는 CASHFLOW_ENGINE_SPEC.md 13절의 정확한 열 필드를 모두 명시적으로 받는다. 둘 다 frozen/slots이며 새로운 int/None dict를 반환한다.

모든 금액은 정확한 int만 허용하고 bool/float/Decimal/문자열/하위 타입은 거부한다. Input은 capacity만 None을 허용한다. Result도 capacity만 None이며 두 disposable만 음수 허용, 나머지는 0 이상이다. 오류는 독립 CashflowValidationError(ValueError)의 code/field이며 타입 오류와 음수를 구별한다. 생성자 인자 누락은 TypeError다.

Result는 타입·부호만 검사하고 합계·가처분액·저축 상한 관계를 다시 계산하지 않는다. 실제 계산은 후속 함수의 책임이다. 월 소득은 정책 소득과 별개이며 모델이 혜택 승인 사실을 확인하지 않는다. Policy Engine/실제 releases는 변경하지 않았다.

IMPLEMENTED: CashflowInput/CashflowResult/strict KRW validation/불변성/to_dict/모델 테스트. NOT IMPLEMENTED: calculation/benefit bridge/What-if/financial products. ResidenceHistory는 공식 답변 전 보류한다. 상세 검증·현재 범위는 CASHFLOW_ENGINE_SPEC.md 20절이다.

## 22. M2.6 — IMPLEMENTED: 명시적 적용범위 값

policy_data/eligibility_coverage.py의 ApplicabilityScope는 edition_id:str, quarter:int|None 두 필드만 갖는 frozen/slots dataclass다. 두 인자를 모두 명시한다. quarter=None은 annual이며 Q3와 다른 값이다. quarter는 exact int1~4만 허용하고 Enum/문자열/하위 타입/bool을 자동 변환하지 않는다. M2.5 확정 타입을 따르므로 PolicyQuarter Enum은 없다.

edition_id는 기존 Envelope와 같은 정확한 ASCII 네 자리 str 검증이다. 기존 계약대로 0000도 형식상 허용하며 실제 정책 효력연도를 인증하지 않는다. 잘못된 값은 기존 PolicyDataError, 인자 누락/추가 인자는 Python TypeError다. 새로운 validation hierarchy는 없다.

to_dict는 edition_id와 원래 int/None quarter를 담은 새 dict다. scope_id는 YYYY-Qn / YYYY-ANNUAL 표시값을 파생한다. equality는 두 필드에 기반하고 ordering·contains·날짜에서 scope 추론은 없다. 현재 Envelope/PolicyCoverage/실제 release에 연결하지 않았다.

IMPLEMENTED: ApplicabilityScope/strict 타입·범위/불변성/값 표현/합성 테스트84개. NOT IMPLEMENTED: RequiredCondition/ConditionInventory/ConditionBinding/EligibilityCoverage/FULL 판정/Acceptance/Bridge. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 상세 계약은 POLICY_COVERAGE_SPEC.md 31절이다.

## 23. M2.7 — IMPLEMENTED: 자격조건의 의미·분류·근거

policy_data/required_condition.py의 RequiredCondition은 condition_id/meaning/requirement/evidence_refs 네 필드만 갖는 frozen/slots 값이다. 모두 필수이며 ConditionRequirement는 REQUIRED/CONDITIONAL 두 Enum member뿐이다. INFORMATIONAL·scope·정책/Rule 연결·구현/검증/수용 상태·혜택 정보는 넣지 않는다. Scope 코드는 그대로 유지했다.

condition_id는 정확한 str과 대문자/숫자/밑줄의 비어 있지 않은 문자 범위, meaning은 정확한 비공백 str이다. 자동 생성·보정은 없으며 의미 문장의 공백은 보존한다. refs는 정확한 비어 있지 않은 tuple이고 기존 parse_evidence_ref로 각 canonical 형식만 확인한다. 중복/순서를 보존하며 실제 출처 존재·공식성·버전·Inventory 중복 검사는 하지 않는다.

to_dict는 네 필드를 새 dict에 담고 Enum→canonical 문자열, refs→새 list로 반환한다. 오류는 기존 PolicyDataError 및 ref parser의 SourceValidationError다. 동일 ID의 metadata conflict는 향후 Inventory 책임이다.

IMPLEMENTED: ApplicabilityScope(변경 없음), RequiredCondition/ConditionRequirement/strict 검증/불변성/값 표현/신규 합성 테스트104개. NOT IMPLEMENTED: ConditionInventory/Binding/EligibilityCoverage/FULL·SLICE 파생/Acceptance/Bridge. 실제 자료는 변경하지 않고 ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 상세 계약은 POLICY_COVERAGE_SPEC.md 32절이다.

## 24. M2.8 — IMPLEMENTED: scope별 조건 목록

policy_data/condition_inventory.py의 ConditionInventory는 policy_id, scope, inventory_version, conditions 필수 네 필드와 completeness_review_ref:str|None=None을 보유하는 frozen/slots 값이다. edition은 scope에만 있다. policy_id는 기존 canonical ID 형식, inventory_version은 i0001부터의 명시적 양의 버전이며 자동 생성/보정은 없다.

scope는 정확한 ApplicabilityScope, conditions는 최소1개의 정확한 RequiredCondition tuple이다. 하위 객체를 재생성하지 않고 그대로 보존한다. 중복 condition_id는 객체/metadata 일치 여부와 무관하게 전체 오류다. 서로 다른 ID의 같은 meaning은 허용한다. 조건·근거의 순서/중복은 자동 변경하지 않는다.

completeness_review_ref는 None 또는 정확한 비공백 str이다. 유효한 문자열을 자동 strip하지 않고 외부 검토 기록은 조회하지 않는다. equality는 필드·조건 순서를 보존한다. to_dict는 기존 하위 값 표현을 사용한 새 중첩 snapshot이며 수정해도 내부 값이 바뀌지 않는다. 오류는 기존 PolicyDataError다.

IMPLEMENTED: ApplicabilityScope·RequiredCondition(변경 없음), ConditionInventory/ID 유일성/strict collection/선택적 검토 참조/불변성/직렬화/신규119개 합성 테스트. NOT IMPLEMENTED: ConditionBinding/EligibilityCoverage/FULL·SLICE/Acceptance/Bridge/실제 inventory. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 상세 계약은 POLICY_COVERAGE_SPEC.md 33절이다.

## 25. M2.9 — IMPLEMENTED: 의미 조건과 구현 root의 참조

policy_data/condition_binding.py의 ConditionBinding은 condition_id/rule_root_id/implementation_review_ref 세 필수 str을 갖는 frozen/slots 값이다. condition_id는 RequiredCondition과 같은 exact str·대문자/숫자/밑줄 형식, root ID는 기존 Rule/Group과 같은 exact 비공백 str이다. root/ref 문자열은 자동 strip하지 않으며 검토 ref는 None을 거부한다.

scope/policy_id·조건/Rule 객체·근거 복제·구현/검증/수용 flags는 없다. 같은 문자열의 두 ID도 서로 다른 역할로 보존한다. subtree의 leaf/group 종류나 실제 존재·조건 목록·검토 기록을 확인하지 않는다. 한 객체는 root 하나만 가리키며 collection 충돌 검사는 후속 책임이다.

to_dict는 세 key의 새 dict, equality는 세 필드 전체의 값 비교다. 오류는 기존 PolicyDataError다. 기존 Scope/RequiredCondition/Inventory의 계약·코드는 변경하지 않았다.

IMPLEMENTED: 기존 세 모델, ConditionBinding/구조 검증/불변성/직렬화/신규82개 합성 테스트. NOT IMPLEMENTED: tree/Inventory cross-validation/EligibilityCoverage/FULL·SLICE/Acceptance/Bridge/실제 mapping. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 상세 계약은 POLICY_COVERAGE_SPEC.md 34절이다.

## 26. M2.11 — IMPLEMENTED: EligibilityCoverage 구조 값

policy_data/coverage.py에 inventory:ConditionInventory, bindings:tuple[ConditionBinding,...] 두 필수 필드만 갖는 frozen/slots 모델을 추가했다. exact 타입만 받고 Inventory·tuple·각 Binding의 identity/순서를 보존한다. 빈/일부 Binding은 유효하고 completeness_review_ref=None도 그대로 둔다.

동일 condition의 중복 Binding과 inventory에 없는 condition 참조는 생성자가 PolicyDataError로 거부한다. 같은 root를 가리키는 서로 다른 condition은 허용하고 후속 tree ownership 검증에 맡긴다. root의 존재·검토 확인본·FULL·SLICE·파생 ID 집합은 계산하지 않는다.

policy_id/scope/inventory_version은 inventory에만 있다. Policy/ReviewContext·검증/수용/혜택 metadata는 추가하지 않았다. to_dict는 inventory/bindings 두 key만 새 중첩 dict/list로 반환한다. equality는 입력 tuple 순서까지 반영한다. 기존 네 모델·legacy Coverage/Envelope·실제 자료는 변경하지 않았다.

IMPLEMENTED: EligibilityCoverage structural model/로컬 참조 정합성/불변성/직렬화/신규83개 합성 테스트. NOT IMPLEMENTED: ReviewContext/CoverageResult/tree validator/FULL·SLICE/Acceptance/Bridge. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 상세 책임표는 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md 33절이다.

## 27. M2.13 — IMPLEMENTED: 목록 검토 대상 metadata

InventoryCompletenessReview는 review_ref/policy_id/scope/inventory_version/inventory_fingerprint/dataset_version/source_registry_fingerprint/reviewed_at/review_artifact_ref 아홉 필수 필드의 frozen/slots 값이다. 프롬프트7필드 예시보다 명세에 확정된 자료 확인본 두 필드를 더 포함한다.

scope는 원래 exact ApplicabilityScope다. 날짜는 exact date, 지문 두 개는 exact lowercase hex64 str, policy/version은 기존 Inventory 형식이다. 나머지 참조/dataset 문자열은 exact 비공백 str이며 자동 보정하지 않는다. 지문은 형식만 검사하고 실제 내용은 비교하지 않는다.

to_dict는 원래 값과 새 scope dict·ISO date를 담은 아홉 key snapshot이다. 오류는 기존 PolicyDataError다. record 간 ref 중복·실제 검토·Inventory 완결성·현재 snapshot 일치는 후속 책임이다. Inventory/조건 목록/Rule/Manifest·reviewer 이름·status는 저장하지 않는다.

IMPLEMENTED: InventoryCompletenessReview/구조 검증/불변성/직렬화/신규182개 합성 테스트. NOT IMPLEMENTED: ImplementationBindingReview/Context/Result/지문 계산/validator/FULL·SLICE. 기존 다섯 coverage 모델·실제 releases는 불변이며 ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 상세 계약은 COVERAGE_REVIEW_CONTEXT_SPEC.md 32절이다.

## 28. M2.14 — IMPLEMENTED: 구현 검토 대상 metadata

ImplementationBindingReview는 review_ref, policy_id, scope, condition_id, rule_root_id, inventory_version, inventory_fingerprint, rule_version, policy_tree_fingerprint, subtree_fingerprint, dataset_version, source_registry_fingerprint, implementation_fingerprint, reviewed_at, review_artifact_ref **15개 필수 필드**의 독립 frozen/slots 값이다. 상속/base나 실제 Binding/Inventory/Rule 객체는 없다.

Scope/date는 exact 타입, 지문5개는 exact lowercase hex64 str이다. policy/condition/inventory version은 기존 구조 계약을 따른다. rule_version은 Policy와 같은 exact 비공백 str이며 참조/root/dataset 문자열도 원래 공백을 보존한다. 자동 보정·생성·조회·내용 일치 판정은 하지 않는다.

to_dict는 원래 값과 새 scope dict·ISO date를 담은15개 key snapshot이다. equality는 모든 필드에 기반하고 같은 ref의 다른 metadata를 단독 생성할 수 있다. 전역 ref 유일성·매칭·stale·실제 검토 진실성은 이 값 모델의 보증이 아니다.

IMPLEMENTED: InventoryCompletenessReview(불변), ImplementationBindingReview/구조 검증/불변성/직렬화/합성 테스트216개. NOT IMPLEMENTED: fingerprint calculators/Context/matching/stale/Result/Coverage validator/FULL·SLICE/Acceptance/Bridge. 실제 자료와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 상세 계약·회귀 기록은 COVERAGE_REVIEW_CONTEXT_SPEC.md 33절이다.

## 29. M2.15 — IMPLEMENTED: ReviewContext collection

CoverageReviewContext의 정확한 필드는 policy_id, scope, dataset_version, source_registry_fingerprint, implementation_fingerprint, inventory_reviews, implementation_reviews 일곱 개이며 모두 필수다. 한 policy/scope를 명시적으로 소유하므로 빈 두 tuple도 identity를 잃지 않는다.

policy_id는 기존 canonical 형식, scope는 exact ApplicabilityScope, dataset_version은 exact 비공백 문자열, 두 지문은 exact lowercase hex64 문자열이다. 두 collection은 정확한 tuple이고 각 원소는 해당 정확한 review 타입만 허용한다. 모든 record의 policy/scope 값은 Context와 같고 review_ref는 두 종류 전체에서 유일해야 한다.

다른 inventory/rule/dataset version·지문·날짜의 record는 동시에 보관할 수 있다. 참조 중복은 거부하되 condition/root/version별 유일성을 추가하지 않는다. 입력 객체·순서와 기본 equality를 유지하며 새 중첩 to_dict에 상태를 추가하지 않는다. 모델은 frozen/slots이고 lookup cache는 없다.

IMPLEMENTED: 두 review 값 모델(불변), CoverageReviewContext/collection 구조·소속·전역 ref 유일성/불변성/직렬화/합성 테스트127개. NOT IMPLEMENTED: fingerprint calculators/lookup/matching/stale/Result/Coverage validator/FULL·SLICE/Acceptance/Bridge. 실제 자료와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 상세 계약·검증은 COVERAGE_REVIEW_CONTEXT_SPEC.md 34절이다.

## 30. M2.21 — IMPLEMENTED: Review matching 결과 값

policy_data/coverage_review_match.py의 ReviewMatchStatus(MATCHED/MISSING/STALE), ReviewMissingReason(2개), ReviewStaleReason(4개)와 두 독립 frozen/slots 결과를 추가했다. Data Error는 Enum 상태가 아닌 기존 PolicyDataError다.

InventoryReviewMatch는 review_ref/status/stale_reasons/missing_reasons 네 필수 필드, ImplementationReviewMatch는 condition_id/rule_root_id를 더한 여섯 필수 필드다. Inventory에서만 ref=None을 허용하며 미선언 MISSING 사유를 요구한다. 명시 ref의 MISSING은 NO_REVIEW_CONTEXT만 가능하고 Implementation은 모든 상태에서 ref가 필수다.

MATCHED는 사유가 모두 비어야 하고, STALE은 stale 사유만 하나 이상, MISSING은 missing 사유만 하나 이상이다. Inventory stale에는 inventory/dataset version 사유만 허용한다. 정확한 Enum/tuple·canonical 순서·중복 없음·ID/ref 구조를 검증하며 자동 변환/정렬/dedupe는 없다. to_dict는 Enum value와 새 사유 list를 포함하는 독립 snapshot이다.

IMPLEMENTED: Review match 결과 모델/로컬 조합 검증/불변성/직렬화/합성 테스트166개. NOT IMPLEMENTED: review resolution/matching, version/지문 비교, stale 계산, CoverageResult/validator/FULL·SLICE/Acceptance/Bridge. 기존 Review/Context/지문 utility·실제 자료는 유지하며 ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED다. 상세 계약·검증 기록은 COVERAGE_REVIEW_MATCHING_SPEC.md 39절이다.

## 31. M2.35 — IMPLEMENTED: 계산과 분리된 private Integration Findings

policy_data/coverage_integration_findings.py에 _ImplementationIntegrationFinding과 _CoverageIntegrationFindings 두 frozen/slots 값 모델을 추가했다. private 직접 import만 사용하며 package 공개 export는 없다.

Binding 단위는 subtree_fingerprint/review_match 두 필드다. condition/root/ref는 기존 ImplementationReviewMatch에만 보존하여 중복된 identity를 만들지 않는다. Coverage 단위는 missing_condition_ids/unmapped_rule_ids/composition_gap_group_ids/inventory_fingerprint/policy_tree_fingerprint/inventory_review_match/implementation_findings 일곱 필드다. 모두 필수다.

exact 타입·세 지문 lowercase hex64·세 ID tuple의 형식/중복·Implementation condition strict 오름차순·M/existing IDs 비겹침·M empty이면 U/G empty인 로컬 정합성을 검사한다. MatchResult는 원본으로 보존하고 MATCHED/MISSING/STALE 모두 허용한다. 자동 정렬/보정·하위 생성자 재실행·root 중복/ownership 재판정은 없다. 위반은 INVALID_INTEGRATION_FINDINGS PolicyDataError다.

이번 지시대로 to_dict는 저장2개/7개 key만 새 nested dict/list로 반환하고 기존 MatchResult.to_dict를 재사용한다. tuple 순서/원본 문자열과 기본 equality/hash를 유지하며 반환 snapshot의 변경은 원본에 영향이 없다. 빈 collection은 로컬 invariant 범위에서 허용하며 실제 Inventory/전체 구현 완료를 인증하지 않는다.

Policy/RuleNode/ConditionBinding/EligibilityCoverage/ReviewContext 객체·policy/scope/rule/dataset identity 복제·상태/property·사용자 facts·금액은 없다. 이 모델은 caller 입력과 함께 쓰는 private 중간값이며 독립적인 완전한 영속 audit archive는 아니다. 실제 분석/지문 계산/Review matching·시각/I/O·FULL/SLICE·Acceptance/Cashflow를 실행하지 않는다.

IMPLEMENTED: 두 값 모델·strict 로컬 검증·불변성·직렬화·합성 테스트184개.
NOT IMPLEMENTED: integration gate·gap 승격·지문/Review orchestration·CoverageResult/FULL·SLICE·최종 validator/Acceptance/Bridge. 상세 계약·검증은 COVERAGE_INTEGRATION_GATE_SPEC.md39절이다. actual 자료와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**는 유지한다.

## 32. M2.38 — IMPLEMENTED: EligibilityCoverageResult 값과 파생 상태

policy_data/eligibility_coverage_result.py에 EligibilityCoverageStatus(FULL_POLICY/CONDITION_SLICE)와 frozen/slots EligibilityCoverageResult를 추가했다. policy_data 공개 export는 두 타입만 추가하고 내부 factory/findings/sentinel은 비공개로 유지한다.

저장 필드는 정확히 policy_id, scope, inventory_version, rule_version, dataset_version, source_registry_fingerprint, implementation_fingerprint, findings **8개**다. status는 읽기 전용 property이며 저장/입력하지 않는다. 기존 scope/findings 원본을 보존하고 metadata·지문·condition IDs를 중복 저장하지 않는다. keyword-only creation token은 InitVar라서 저장 필드/slots/equality/직렬화에 포함되지 않는다. 정상 factory token 없는 일반 생성과 dataclasses.replace는 TypeError다.

private _create_eligibility_coverage_result(coverage, policy, review_context, findings)는 exact 입력을 요구한다. Coverage/Policy policy_id·Context target policy/scope·Inventory 순서의 정확한 missing tuple·canonical condition/root/ref triple·Inventory review_ref를 대조하고 원본에서 identity/current baseline을 채운다. 이 검사만으로 구조/지문/Review를 다시 계산하지 않는다.

로컬 검증은 canonical policy ID·exact Scope/문자열/지문/findings·baseline all-none/all-present·Review/baseline 조합·M empty/K nonempty를 적용한다. Context None은 모든 baseline None과 현재 matcher 의미의 MISSING을 요구한다. Context present에서는 Inventory 미선언 MISSING 또는 MATCHED/STALE, Implementation MATCHED/STALE만 정상이다. 오류는 INVALID_COVERAGE_RESULT: field: reason의 PolicyDataError이며 SLICE로 숨기지 않는다.

FULL은 M/U/G empty·Inventory MATCHED·K nonempty·Implementation 모두 MATCHED·baseline 모두 present인 검증된 Result에서만 파생한다. 그 외 정상 incomplete는 SLICE다. to_dict는 저장8개+canonical status **9개 key**의 새 중첩 값이다. Optional baseline None도 생략하지 않고 equality는8필드 기준이다. 별도 SliceReason/is_full/Verification/Acceptance/사용자 facts/금액은 없다.

합성 모델 테스트226개와 전체5620개가 통과했다. 상세 생성 정책·오류·신뢰 한계·회귀 기록은 ELIGIBILITY_COVERAGE_RESULT_SPEC.md36절이다. 이미 계산된 findings를 신뢰된 내부 경로에서 공급받는 전제이며, 실제 gate의 성공을 이 모델이 새로 인증하지 않는다.

IMPLEMENTED: Status/Result·private validated factory·derived status·9key serialization·불변성.
NOT IMPLEMENTED: 공개 evaluate_eligibility_coverage·Integration Gate 자동 연결·Verification/Acceptance/Benefit Bridge/Cashflow·actual Result. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED** 유지다.

## 33. M2.43 — IMPLEMENTED: 독립 BenefitSnapshot

`policy_data/benefit_snapshot.py`의 BenefitSnapshot은 frozen/slots/keyword-only 불변 값이다. 저장 필드는 정확히 policy_id, scope, benefit_id, benefit_version, amount_type, amount_krw, amount_description, payment_cadence, benefit_medium, restriction, restriction_details, applicable_months, benefit_evidence_refs, source_bindings, dataset_version, source_registry_fingerprint의16개이며 nullable 값도 명시적으로 필수다.

BenefitAmountType(FIXED/VARIABLE/UNKNOWN), BenefitPaymentCadence(기존7개), BenefitMedium(기존10개), BenefitRestriction(UNRESTRICTED/RESTRICTED/UNKNOWN)를 함께 공개한다. Scope/SourceBinding은 기존 exact immutable 타입을 재사용하고 원본을 보존한다. source ID 집합은 refs와 정확히 대응하며 binding은 유일·오름차순, evidence 순서/중복은 그대로다.

FIXED는 exact int≥0·description=None, VARIABLE은 amount=None·비공백 설명, UNKNOWN은 둘 다 None이다. 제한/details·두 명확한 cash medium 모순·ONE_TIME의 단일 알려진 월을 검사한다. YYYY-MM은 유효 달력 연월의 비어 있지 않은 정렬·유일 tuple 또는 None이고 임의 지급월 추론은 없다. b0001 이상 version·canonical ID·비공백 dataset·lowercase hex64도 구조 검사한다.

equality는 provenance를 포함한16필드 전체다. to_dict는 같은16key와 새 nested 값만 반환한다. benefit_fingerprint·completeness·Acceptance/Review·Bridge 지원·월 환산액은 저장/파생하지 않는다. 생성 성공은 공식 의미·검토·수용·개인 지급 확정을 뜻하지 않는다.

합성292개 및 전체5979개 테스트가 통과했다. 상세 계약·검증 기록은 BENEFIT_SNAPSHOT_SPEC.md36절을 따른다. **NOT IMPLEMENTED:** Benefit fingerprint/BV 실행 tests·Acceptance/evaluator·Bridge·실제 Snapshot/자료 연결. 기존 Coverage/Cashflow 모델과 실제 releases는 변경하지 않았으며 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 34. M2.46 — IMPLEMENTED: PolicyBenefitAcceptance

BenefitAcceptanceStatus는 ACCEPTED/REVOKED 두 문자열 Enum member만 가진다. PolicyBenefitAcceptance는 frozen/slots/keyword-only이며 다음 순서의21개 저장 필드를 모두 명시적으로 받는다.

```text
acceptance_ref, acceptance_version, status, policy_id, scope, benefit_id,
coverage_inventory_version, coverage_inventory_fingerprint, coverage_rule_version,
coverage_policy_tree_fingerprint, coverage_dataset_version,
coverage_source_registry_fingerprint, coverage_implementation_fingerprint,
benefit_version, benefit_fingerprint, benefit_dataset_version,
benefit_source_registry_fingerprint, reviewed_at, valid_until,
review_artifact_ref, revokes_acceptance_ref
```

target은 (policy_id, scope, benefit_id), 기록 identity는 opaque acceptance_ref, target 내 revision은 a version이다. scope는 기존 exact ApplicabilityScope다. Coverage의 공유 target+7개 binding과 Benefit의4개 binding/provenance를 저장하며 전체 Result/Snapshot/verification 객체는 저장하지 않는다. 타입/문법은 BENEFIT_ACCEPTANCE_RECORD_SPEC.md14~15절을 따른다.

두 exact date는 reviewed_at<=valid_until이어야 하며 Coverage/Benefit의 dataset과 Registry 지문은 각각 같아야 한다. ACCEPTED에는 revokes=None, REVOKED에는 비공백 다른 ref를 요구한다. nullable ref도 필수 인자다. 대상 존재/연결/선후 관계·유일성은 후속 Context 책임이다. REVOKED 기한을 철회 종료로 해석하지 않는다.

일반 constructor는 구조만 검증하며 실제 발급·검토·현재 usability를 인증하지 않는다. equality/hash는21필드 전체, serializer는 같은 순서의21key·Enum.value·새 Scope dict·ISO 날짜·명시 null이다. stale/expired/usable·accepted_terms·금액·파생 상태를 저장하지 않는다.

합성472개와 기존6053개를 포함해 전체6525개 테스트가 통과했다. 상세 검증은 BENEFIT_ACCEPTANCE_RECORD_SPEC.md37절이다. **IMPLEMENTED:** 두 값 타입과 로컬 검증/직렬화. **NOT IMPLEMENTED:** Context/resolution·AcceptanceEvaluation/result/evaluator·verification integration·Bridge·Cashflow 연결·실제 안산 Acceptance. BenefitSnapshot/지문·Coverage 동결 계약·실제 releases는 그대로이며 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 35. M2.48 — IMPLEMENTED: BenefitAcceptanceContext

BenefitAcceptanceContext는 policy_id, scope, benefit_id, records 순서의 정확한4필드를 모두 명시적으로 받는 frozen/slots/keyword-only 값이다. records는 빈 값도 허용하는 exact tuple[PolicyBenefitAcceptance, ...]이며 원본 tuple·Scope·records를 보존한다. 모든 record는 같은 policy/scope/benefit target이어야 한다. 동등한 별개 Scope도 정상이며 내부 index/cache·current/selected/usable 상태는 저장하지 않는다.

Context 내 acceptance_ref/version은 각각 유일해야 한다. 서로 다른 역사 version·지문·release·기한은 공존할 수 있다. REVOKED는 Context 전체에 존재하는 ACCEPTED만 지목하며11개 Coverage/Benefit snapshot binding이 같고, 직접 철회는 한 승인당 최대1개, 철회 revision은 수치상 후행·검토일은 대상 이상이어야 한다. record별 same-release 계약과14phase 오류 순서는 기존 명세 그대로다.

equality/hash는 records 순서를 포함한4개 값 전체다. to_dict는 같은 순서의4key·새 Scope dict·기존 record serializer의 새21key dict list를 반환한다. 원본 record/Context의 재생성·수정·현재 상태 계산은 없다. Context 생성 성공은 실제 검토/발급 진실성·이력 완전성을 인증하지 않는다.

Context 한 타입만 public export했다. private _resolve_benefit_acceptance는 Context와 exact 비공백 ref를 받아 원본 객체를 반환하고, 없는 ref는 오류다. 철회된 과거 A도 조회하지만 현재 사용 승인으로 해석하지 않는다. 최신 선택·None/no-selection 의미·철회 효과·평가 결과/evaluator·verification·Bridge/Cashflow는 미구현이다.

신규 합성200개 및 기존6525개를 포함해 전체6725개 테스트가 통과했다. 상세 계약/AC 대응/검증은 BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md35절이다. 기존21필드 Acceptance·BenefitSnapshot/지문·Coverage freeze·실제 releases는 변경하지 않았다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 36. M2.50 — IMPLEMENTED: BenefitAcceptanceEvaluation 내부 결과 값

BenefitAcceptanceEvaluation의 정확한9개 stored fields는 policy_id:str, scope:ApplicabilityScope, benefit_id:str, data_use_date:date, selected_acceptance_ref:str|None, selected_acceptance_version:str|None, selected_acceptance_status:BenefitAcceptanceStatus|None, revocation_acceptance_ref:str|None, reasons:tuple[BenefitAcceptanceReason,...] 순서다. frozen/slots/keyword-only이며 nullable 값도 필수다.

평가 Status는 USABLE/UNUSABLE 정확히2개다. Reason은 BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md13절의12개를 그대로 사용한다. selected record status는 기존 ACCEPTED/REVOKED Enum이다. 새 Status는 reasons 유무로 파생하고 저장/입력하지 않는다. usable bool/property도 없다.

private token/InitVar와 factory로만 구조 생성 경로를 열었다. token은 저장9필드/serializer/equality에 포함하지 않는다. 이유의 exact tuple/Enum·canonical 순서/유일성·선택 all-None/all-present·미선택3사유·철회 근거/상태·배타 기한 사유를 로컬 검사한다. 직접 REVOKED 결과의 evidence ref는 selected ref 자신이고, ACCEPTED A를 철회한 결과의 evidence B는 A와 달라야 한다.

to_dict는9개 값과 마지막 status의10key·새 Scope dict/reasons list·ISO date·명시 None을 반환한다. equality/hash는 저장9개 전체다. 원본 Scope/tuple/문자열을 보존한다. source/기한/철회 사실을 계산하지 않으며 구조적으로 유효한 USABLE이 실제 평가/발급 인증은 아니다.

이 값은 같은 호출의 원본과 함께 사용하는 내부 결과이므로 package public export를 추가하지 않았다.9개 값/JSON/equality만으로 다른 확인본에 재사용할 수 없다. 정확한 외부 재입력 금지는 후속 adapter의 구현 의무이며 지금 구현된 기능으로 보고하지 않는다.

신규 합성237개와 기존6725개를 합쳐 전체6962개가 통과했다. 검증/AE 대응은 BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md29절이다. 실제 evaluator·Context lookup/related B·기한/검증/지문 비교·adapter·Bridge/Cashflow는 미구현이다. 기존 모델/동결 계약·실제 releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**는 유지한다.

## 37. M2.55 — IMPLEMENTED: Acceptance Review Artifact 값

BenefitReviewClaim은 AMOUNT/CADENCE/MEDIUM/RESTRICTION/APPLICABLE_MONTHS 정확한5member다. 별도 모듈 benefit_acceptance_review_artifact.py에 다음4개 frozen/slots/keyword-only 모델을 구현했다. 모든 필드는 기본값 없이 필수이며 nullable 값도 명시한다.

- ClaimEvidenceMapping2: claim, evidence_refs.
- ReviewSourceOriginal2: binding, artifact.
- AcceptanceReviewEntry15: acceptance, accepted_terms_ref, coverage_snapshot_ref, policy_envelope_ref, coverage_reviews_ref, dataset_manifest_ref, source_registry_ref, implementation_artifact_ref, claim_evidence, source_bindings, source_documents, prepared_by, reviewed_by, review_note, manual_scenario_ids.
- AcceptanceReviewArtifact2: review_artifact_ref, entries.

기존 Acceptance21필드·SourceBinding·ArtifactReference를 그대로 보존한다. ACCEPTED는7개 원본 참조·정확한5claim·정렬/유일 source bindings와 대응 원문 참조를 요구한다. REVOKED는7개 참조 None·빈 검토/source 목록과 철회 사유 metadata를 표현하고 실제 target은 조회하지 않는다. 근거 행 내부 중복은 거부하나 claim 간 공유는 허용한다. tuple/근거/entry 순서를 자동 정렬·dedupe하지 않는다.

Root만 exact content-addressed ref 문법을 확인하고 entry의 외부 ref equality·명시 ref/revision key 유일성을 검사한다. 모델 생성은 bytes hash/실제 원본 확인이 아니다. readable accepted_terms는 당시 Snapshot의 ArtifactReference를 보존하며 Snapshot/FIXED completeness·지문·Registry/source 합집합·공식 내용 검증은 하지 않는다.

진단 serializer는 정확한 stored key2/2/15/2개와 새 중첩 dict/list·Enum value·기존 ISO date 표현을 반환한다. entry.acceptance는21key이며 외부 raw20key projection과 다르다. raw loader/bytes integrity·external evidence resolution·source usage gate·content verification·Acceptance evaluator·same-call adapter·Benefit Bridge는 **NOT IMPLEMENTED**다. 정확한 타입/필드/로컬 순서·합성 검증 기록은 BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md30절이다.

기존21/16/9/4필드·지문/GV/BV·Coverage freeze·bootstrap·Cashflow·실제 releases는 유지한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 2026-10-30 정부·지자체 자산형성사업 연결

사용자 후속 요청에 따라 전국 청년 대상의 정부·지자체 적금/자산형성사업 탐색과 기초 추천을 추가했다. 안산은 기존 실제 정책 전체 조건의 첫 검증 지역이다. 기존 원기획/과거 milestone 기록은 유지한다.

공식12출처·10사업 스냅샷과 GET /api/asset-programs, POST /api/asset-programs/recommendations, React 공개목록·입력 후 추천·추가정보·What-if를 연결했다. 기존 Policy/Cashflow를 재사용하며 소득인정액/건강보험료/기준일 주민등록/가구원/선발·유지조건은 UNKNOWN이다. 모두 DRAFT / CONDITION_SLICE이며 실제 지원금0원/실제 만기 계산0개를 유지한다.

신규 backend/opportunities는 catalog/matching/changes로 분리했다. 공개 변경 이벤트는 개인 입력 없이 생성하고 NOT_SENT를 유지한다. 자동 수집/구독/실제 알림 발송은 후속 범위다. 7일 freshness는 임시 운영 Assumption이다.

전체 Backend12,463 passed / 1 skipped / 1 warning, Frontend148 passed, TS/build·실제 API/브라우저 통과. 상세: [구현·근거·검증](OFFICIAL_ASSET_PROGRAM_DISCOVERY.md), [후속 알림 계약](ASSET_PROGRAM_NOTIFICATION_CONTRACT.md).

## 2026-10-30 공식 모집 자동 확인·관심 알림

사용자의 후속 요청으로 등록 공식 출처 자동 확인·관심 지역/사업 구독·사이트 알림함·브라우저 Web Push를 연결했다. 이메일은 사용자 결정으로 제외했다. 서버 실행 중6시간 확인이며 상시 운영/전국 완전 수집은 별도 단계다. 단순200·본문 동일 검증·일정 추출·푸시 서버 접수·기기 표시는 구분한다.

알림 전용 저장소는 관심 지역/사업·수신 설정·필요한 browser subscription/기기 식별자/알림 기록만 저장한다. 소득·월세·생년월일·계좌정보는 저장하지 않는다. 구독90일 만료·정기 삭제·즉시 구독 삭제를 지원한다. 원본 금융·정책 규칙은 자동 생성하지 않고 신규 공고 전체 자격 UNKNOWN을 유지한다.

실제 공식25주소 확인·일정3건 추출(모두마감), 새 API17사례, 전체 Backend12562/1skip/1warning·Frontend161·TS/build 통과. 브라우저 기기 표시는 사용자 직접 확인이며 자동 OS 검증과 구분한다. release6/GV/BV·기존 core 보존. 상세: [구현·검증](OFFICIAL_INTAKE_MONITORING_AND_ALERTS.md), [운영](ASSET_ALERTS_OPERATIONS.md).
## 2026-10-30 화면 분리·공개 정보 배포와 상시 서버 대기

새 원본 보고: `docs/PORTAL_REDESIGN_AND_DEPLOYMENT.md`, 배포 절차: `docs/CLOUD_DEPLOYMENT_RUNBOOK.md`.

https://youth-life-planner.rladudwns559.chatgpt.site 에 공식 정보 UI를 공개 배포했다. 홈 CTA 아래 내용 제거·메뉴별 화면·입체 디자인·220ms 전환 및 접근성/상태 보존을 적용했다. 공개본은10월30일 고정 사업10/은행4 정보이며 계산·개인알림은 Python 상시 서버 연결 대기다. 로컬 전체 기능은 유지한다.

전체 Backend12,586 passed/1skip/1warning, Frontend186 passed, TS/build·production-only venv·Windows production-mode HTTP 통과. Docker/Linux·유료 서버·PC-off 정기수집은 미검증. Render starter+1GB 월 기본$7.25 제안은 계정·비용 승인 전이며 신청하지 않았다. 독립 urllib 공개접속403은 미검증으로 기록하고 native 공개설정/실제 in-app 브라우저 성공과 구분한다. 실제 만기0/미승인 지원금0원, release6·핵심95해시·Coverage freeze 보존.
## 2026-10-31 유료 배포 보류·무료 상품 탐색 우선

현재 결정은 **유료 배포 보류**다. 상품 탐색 확대와 공개 기능 정리: 기존 공개 Site에서 은행8곳·20종의 무료 조건 비교를 제공한다. 실제 만기계산0·미승인 지원금0원, 정부10사업 유지. 자동 갱신/브라우저push/이메일은 공개본에서 제공하지 않는다. 유료 서버·계정·알림 요금제0건. source 검토일의 정적 비교표이며 전국 전수·실시간 자료가 아니다. 원본 `docs/FREE_PRODUCT_DISCOVERY_AND_CLEANUP.md`, 출처 `docs/PRODUCT_DISCOVERY_SOURCES.md`. 기존 Render 제안은 승인되지 않은 보류 자료다.
## 2026-11-01 상품 목록 확대와 증거 수준 분리

상품 목록 확대: 공식상세목록61개·13금융회사, 별도2026-10-23공시참고299항목·97회사. 서로겹치므로합산하지않음. 가입방법/납입방식/정렬/ID만관심저장/12·24·전체페이지, 미지원납입단위/복합조건보류. Backend12645/1skip/1warning·Frontend224·TS/build·공개v5검증. 유료0·자동갱신/알림보류·실제계산0·지원금0원·GUI미확인. [공개 상품 찾기](https://youth-life-planner.rladudwns559.chatgpt.site/#/savings).
## 2026-11-01 공시 상품 공식 검증과 조건 비교 연결

공시 상품 공식 검증: 공시299개 중 공식 자료를 추가 확인한13상품을 승격해 상세74개·18금융회사로 확대했다. 공시14항목과 연결되며9후보는 보류했다. 월30만원·12개월·목돈200만원에서 전체 금액·기간FIT36/일부금액4,신규13개는10/3. 가입자격UNKNOWN·현재금리/판매 추가확인·실제만기계산0·미승인지원금0원. Backend12666/1skip/1warning·Frontend230·TS/build·공개v6 검증. [공개 상품 찾기](https://youth-life-planner.rladudwns559.chatgpt.site/#/savings).
## 2026-11-01 지역별 청년 지원사업 탐색 확장

지역별 청년지원사업 탐색: 기존 자산형성10개에서 주거5·취업8·교육5·생활8·문화2를 포함한 고유사업38개로 확장.17개 광역지역의 확인 자료,시군구7곳 일부 자료이며 전수 수집은 아님. 지역 선택 시 전국+광역+시군구 검토 목록,안산전체13·주거2. 나이/가구소득/재산/거주기간/전체자격UNKNOWN,지원금0원. Backend12698/1skip/1warning·Frontend238·공개v7검증. [공개 지원사업 찾기](https://youth-life-planner.rladudwns559.chatgpt.site/#/programs).

## 2026-11-01 개인 조건 기반 지원 추천

개인 조건 기반 지원 추천: 지역·현재나이·취업·월세 입력에 따라 후보 자동 비교. 지원41개(신규3),근거 연결20개/연령16·고용4·월세2 부분 비교,나머지UNKNOWN. 전체자격UNKNOWN·지원금0원. Backend12740/1skip/1warning·Frontend247,공개v8. [공개 화면](https://youth-life-planner.rladudwns559.chatgpt.site/#/programs).
