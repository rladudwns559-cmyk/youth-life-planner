# 아키텍처

과거 CoverageReviewContext/검토 기록의 동일 bytes 복원·Acceptance baseline 대조는 **59절 M2.66**을 따른다. 개별 Review MATCHED·Historical FULL·실제 ZIP/현재 USABLE 검증은 이 loader가 실행하지 않는다. 이전 절의 미구현 표기는 당시 이력이다.

과거 PolicyEnvelope/전체 Rule Tree의 동일 bytes 복원·Acceptance binding은 **58절 M2.64**를 따른다. edition year만 비교하며 quarter 적용·FULL·현재 USABLE 검증은 별도다. 이전 절의 미구현 표기는 당시 이력이다.

과거 Coverage 입력의 동일 bytes 복원·Inventory binding은 **57절 M2.62**를 따른다. FULL 결과를 생성하지 않으며 Policy Tree/ReviewContext/Manifest 역사 준비는 별도다.

과거 혜택 원본의 동일 bytes 복원·Acceptance binding은 **56절 M2.60**을 따른다. 외부 file preparation·나머지 역사 codec·Content Validator·현재 Acceptance evaluator/Bridge는 아직 없다.

불변 Benefit Acceptance 기록 경로는 **50절 M2.46**, 이력 Context/명시 조회는 **51절 M2.48**, 내부 평가 결과 값 경로는 **52절 M2.50**을 따른다. 실제 evaluator·adapter/Bridge 연결은 아직 없다. 과거 절의 미구현 표기는 당시 이력이다.

독립 혜택 정의 값은 **48절 M2.43**, 전용 지문 경로는 **49절 M2.44**를 따른다. Snapshot 자체는 구조 검증/직렬화만 제공하고 지문은 별도 pure 함수가 계산한다. Acceptance·Bridge·Cashflow 연결은 아직 없다.

현재 독립 Cashflow 계산 경로는 23절 M2.2를 따른다. 모델 계약은 22절 M2.1이며 benefit bridge는 아직 구현하지 않았다.

정책의 독립 적용범위 값 ApplicabilityScope는 24절 M2.6을 따른다. Coverage Result 값/파생 상태는 46절 M2.38, 공개 evaluator 연결은47절 M2.39다. Envelope 연결은 아직 없다.

독립 자격조건 의미 모델 RequiredCondition은 25절 M2.7, 조건 목록 ConditionInventory는 26절 M2.8, ConditionBinding은 27절 M2.9를 따른다. root ID의 실제 tree node 조회는 39절 M2.26, 소유 ID 수집/overlap 검사는 40절 M2.28, 실행 leaf target/미매핑 사실 분석은 41절 M2.30, missing 계산과 이 helper들을 연결하는 private 매핑 구조 분석은 42절 M2.32, composition gap 사실 분석은 43절 M2.34를 따른다. composition 오류 승격·Context target·지문/Review를 연결한 findings 수집 gate는 45절 M2.36이며 Result 값/파생 상태는46절, 공개 연결은47절이다.

EligibilityCoverage 구조 모델은 28절 M2.11을 따른다. 전체 tree/review를 연결한 facts 수집은45절, Coverage Result의 상태 파생은46절, 두 경로를 연결하는 공개 evaluator는47절이다.

계산된 사실을 보존하는 두 private Integration Findings 값 모델은 44절 M2.35를 따른다. 실제 integration 계산·composition 승격은 45절 M2.36이며 EligibilityCoverageResult는46절 M2.38이다.

독립 InventoryCompletenessReview 값 모델은 29절 M2.13, ImplementationBindingReview는 30절 M2.14, CoverageReviewContext collection은 31절 M2.15, Inventory 지문은 32절 M2.17, 전체 Tree 지문은 33절 M2.18, subtree 지문은 34절 M2.19를 따른다. 제공된 Context의 private ref lookup은 36절 M2.22, Inventory 검토 대조는 37절 M2.23, Implementation 검토 대조는 38절 M2.24를 따른다. 최종 Coverage 결과의 공개 진입점은47절이다.

Review matching 결과의 Enum/불변 값 계층은 35절 M2.21을 따른다. 두 private matcher의 MATCHED/MISSING/STALE과 독립 root lookup을 구현했으며 구조 검증/지문 준비/matcher를 연결한 통합 경로는45절이다. Result 값과 private 생성 경로는46절, 공개 evaluator는47절이다.

## 1. 기획 PDF에서 확정된 요구사항

전체 제품은 frontend, backend, policy engine, financial calculator, simulation engine, explanation service, data layer로 역할을 분리한다. 정책 판정은 UI/생성형 AI와 독립적이어야 한다. 권장 스택은 React/TypeScript/Vite, FastAPI/Python, pandas와 JSON/CSV에서 시작하는 데이터 계층이다.

## 2. 이번 M1에서 승인한 결정

현재 구현은 다음뿐이다.

```text
backend/policy_engine/
  models.py       불변 도메인 모델과 타입/구조 검증
  loader.py       JSON 형식 검증 및 전체 데이터셋 로딩
  evaluator.py    명시적 연산자와 3상태 집계
  __main__.py     저장소 샘플을 실행하는 CLI
data/synthetic/   실제 자료와 분리한 테스트 정책/프로필
tests/            단위 테스트와 샘플 acceptance 테스트
```

호출 계약:

- `load_policy_set(path) -> PolicySet`: 모든 규칙 검증이 성공해야 반환. 실패는 PolicyDataError.
- `load_profile(path) -> UserProfile`: 잘못된 사용자 입력은 ProfileValidationError.
- `evaluate_policy(profile, policy, context) -> PolicyEvaluation`: 외부 I/O 없이 평가.
- `evaluate_policies(profile, policy_set, context) -> tuple[PolicyEvaluation, ...]`: 데이터 버전 일치 확인 후 평가.
- `PolicyEvaluation.to_dict() -> dict`: JSON으로 직렬화 가능한 결과. 입력 전체를 복사하지 않음.

JSON 읽기는 loader/CLI에 한정한다. evaluator는 시간 조회, 파일 접근, 네트워크, eval, DB를 사용하지 않는다. dataclass는 frozen이며 중첩 배열은 tuple로 고정한다. 평가 결과에는 평가일과 데이터/엔진 버전을 포함하며 사용자 ID나 생성 시각을 자동 생성하지 않는다.

도메인 생성자에도 검증을 적용한다. JSON을 우회한 직접 생성이 잘못된 타입을 허용해서는 안 된다. 숫자에 bool을 허용하지 않는다.

## 3. 향후 결정해야 할 사항

HTTP/API, 웹 화면, 금융, What-if, DB, LLM, 인증, 배포는 미구현이다. JSON repository를 DB로 교체할 수 있는 추상화나 미래 모듈용 빈 구현을 선제적으로 만들지 않는다. 실제 API 계약과 persistence 도입은 별도 작업이다.

## 4. M1.6B — 독립 주민등록 resolver

M1.6A의 `facts/resident_registration.py`는 입력 모델만 담당한다. 새 `resolvers/resident_registration.py`는 명시적으로 받은 사실·정책 기준일·평가일을 검토하는 독립 순수 함수를 제공한다. 미래의 다른 resolver를 위한 추상 클래스·플러그인·빈 모듈은 추가하지 않았다.

```text
RegionRef / RegistrationSource / ResidentRegistrationFact
       ↓ 명시적 인자로 전달
resolve_resident_registration(facts, *, required_region, reference_date, evaluation_date)
       ↓
ResidentRegistrationResolution
```

출력은 기존 Status를 재사용하는 status, 독립 reason_code, 기준일·평가일·요구 지역, 선택 지역·사실 날짜, missing_fields, 선택한 used_facts와 출처다. 불변 모델이며 작은 to_dict()로 표현할 수 있다. 오류는 M1.6A ResidentRegistrationValidationError를 재사용한다.

전체 입력 타입 검증 → 알려진 같은 날짜의 지역 모순 검사 → 누락/미래 기준일 검사 → 정확한 날짜 선택 → 지역 비교 순서다. 같은 사실의 중복과 순서 변경은 결과를 바꾸지 않는다. source 사전순은 결정적 출력 목적이며 신뢰도 순위가 아니다.

기존 evaluator.py / models.py / loader.py, UserProfile.region 및 EvaluationContext는 변경하지 않는다. 함수에 evaluation_date를 직접 주므로 시스템 오늘이나 암묵적인 context 변환에 의존하지 않는다.

**아직 연결하지 않음:** PolicyRule, 기존 JSON 로더, 실제 정책 JSON, API, UI, DB, 다른 사실·계산·AI 기능.

## 5. M1.6D — IMPLEMENTED: 결과 전용 값 계층

`result_types.py`는 RegionSnapshot/주민등록 Condition/Details/Evidence와 ResultValidationError를 제공한다. 원본 Fact나 Resolution을 보유하지 않고 필요한 불변 값만 표현한다. RuleEvaluation은 details=None 기본값을 추가하고 기존 값/요구조건/사유 타입을 좁게 확장한다. 공통 직렬화는 None details를 생략해 기존 atomic 출력 형태를 유지한다.

M1.6D 당시 흐름은 **수동 결과 생성 → 모델 검증 → to_dict**다. 이후 Adapter 구현 상태는 아래 6절을 따른다. 기존 evaluator.py/loader.py/resolver 및 사실 모델은 수정하지 않는다. reason Enum의 타입 참조는 정적 전방 참조, 실제 검증은 생성 시 국소 import로 하여 모듈 로딩 시 역방향 import를 피한다. API schema나 런타임 reflection은 이번에 도입하지 않는다.

신청 기준일과 fact 날짜는 detail/evidence에, 평가일은 PolicyEvaluation.context.as_of에 둔다. 사용자 정보 저장·로깅은 추가하지 않는다. 전체 collection 충돌 검증을 reference-date resolution에서 분리하는 제안은 기술부채이며 현재 Resolver는 기준일 밖 충돌도 계속 거부한다. 최신 구현 계약은 RESOLVER_RULE_ADAPTER_SPEC.md 20절이다.

## 6. M1.6E — IMPLEMENTED: 독립 Adapter

`adapters/resident_registration.py`의 `adapt_resident_registration_resolution(*, rule_id, resolution, policy_condition, evidence_refs=()) -> RuleEvaluation`을 adapters 패키지에서 공개한다.

현재 가능한 작은 연결은 **Fact → Resolver → Adapter → RuleEvaluation**이다. Adapter 자체는 Resolver를 호출하지 않고 이미 만들어진 Resolution만 받는다. 상태·사유·누락 경로·정책 근거를 그대로 보존하고 선택 fact 전부를 같은 순서의 최소 evidence snapshot으로 옮긴다. 외부 I/O·재판정·사실 선택은 없다. 변환 구조 오류는 기존 ResultValidationError로 처리한다.

기존 evaluator/loader/결과 모델/Resolver/Fact는 이번에 변경하지 않는다. 평가일의 상위 context 연결, specialized PolicyRule, routing, 실제 JSON은 **미구현**이다. 상세 필드와 오류 계약은 RESOLVER_RULE_ADAPTER_SPEC.md 21절이다. 기준일 밖 충돌의 책임 분리 제안도 보류 상태다.

## 7. M1.6G — IMPLEMENTED: 규칙/입력 모델 준비

specialized_rules/resident_registration.py에 ResidentRegistrationRule, evaluation_inputs.py에 EvaluationFacts/PolicyReferenceContext를 추가했다. 두 모듈은 models/evaluator를 역참조하지 않는다. models.py는 새 leaf를 포함한 유한 RuleNode와 children/root 검증을 제공한다. 기존 atomic PolicyRule 클래스는 그대로다.

현재 지원 범위는 **Python 객체로 혼합 트리 생성·구조 검증**까지다. evaluator.py/loader.py 및 Resolver/Adapter/result_types를 변경하지 않았다. 새 모델을 생성할 수 있다는 것이 evaluate_policy로 실행할 수 있다는 뜻은 아니다. m1.0 PolicySet은 specialized 노드를 거부하며 새 버전 허용은 Loader 검증과 같은 후속 단계로 남긴다.

입력은 불변 typed tuple/context이며 UserProfile과 별개다. 사실의 의미 판정이나 기준일 바인딩은 아직 없고 일반 region fallback도 없다. 작은 값 표현만 제공하며 API/저장소/범용 직렬화는 도입하지 않았다. 최신 구현 계약은 RULE_ROUTING_SPEC.md 21절이다.

NOT IMPLEMENTED: rule routing, Resolver/Adapter 호출 연결, loader m1.1, actual policy JSON, 다른 Fact/서비스 기능.

## 8. M1.6H — IMPLEMENTED: 단일 Policy mixed-tree routing

새 routing.py의 `evaluate_policy_tree(profile, policy, context, *, facts=None, reference_context=None) -> PolicyEvaluation`을 root 패키지에서 공개한다. 기존 evaluate_policy/evaluate_policies 시그니처는 유지한다. 7절의 모델 준비 단계를 넘어, 새 entrypoint로 단일 Python 객체 Policy의 mixed tree를 실행할 수 있다.

```text
PolicyRule → 기존 atomic evaluator ───────────────────────────┐
ResidentRegistrationRule → 기존 Resolver → 기존 Adapter ────┤
RuleGroup → 자식 재귀 평가 ─────────────────────────────────┤
                                                           ↓
                         공통 그룹/정책 결과 조립 + 기존 집계
```

evaluator.py에서 기존 그룹/정책 결과 조립만 작은 함수로 추출해 공유한다. _evaluate_atom 및 Status 기반 _aggregate의 의미/구현은 유지한다. legacy 경로의 specialized 노드는 명시적 PolicyDataError다. 새 경로의 context 부재/정책 ID 불일치도 오류이며 정상 UNKNOWN으로 숨기지 않는다.

APPLICATION_DATE는 정책별 reference context에서 가져오고 평가일은 context.as_of다. facts tuple을 필터링 없이 기존 Resolver에 넘긴다. 지역/날짜 판정·source 우선순위를 router가 재구현하지 않는다. 입력은 저장/수정하지 않으며 오류는 전파한다. leaf reason/details/정책 근거는 기존 결과 모델로 보존한다.

Loader와 PolicySet의 m1.0 제한은 변경하지 않았다. m1.1 loader, specialized 배치 실행, 실제 정책 JSON 및 전체 정책 평가는 미구현이다. 최신 계약/실제 합성 출력/검증 기록은 RULE_ROUTING_SPEC.md 22절이다.

## 9. M1.7 — IMPLEMENTED: m1.1 mixed-rule Loader

```text
JSON envelope의 schema_version 검증
  ├─ m1.0 → 기존 kind=rule/group + 공통 atomic parser
  └─ m1.1 → 명시적 leaf rule_type 분기 + 재귀 group parser
        → 전체 PolicySet 검증 성공
        → Policy 한 개 선택 + typed facts/reference context
        → 기존 evaluate_policy_tree
```

Loader는 기존 loader.py 안의 작은 버전 분기와 공통 _atomic으로 확장했다. schema framework/동적 registry/API schema를 도입하지 않았다. models.PolicySet과 같은 버전 검증을 사용하고 잘못된 버전은 노드 파싱 전에 거부한다. m1.0 fixture와 원자 의미는 유지한다.

새 합성 policies_m11.json을 추가하고 직접 만든 트리와 로드한 트리의 동등성을 확인했다. 정책 데이터 오류는 전체 로드 실패이며 사용자 fact 부족의 정상 UNKNOWN과 구별한다. 파싱/검증이 모두 성공하기 전에 PolicySet을 반환하지 않는다.

routing/evaluator/Resolver/Adapter/Fact는 이번에 변경하지 않는다. m1.1 PolicySet 지원은 specialized 배치 평가 지원을 뜻하지 않는다. 실제 정책 JSON·공식 근거 바인딩·미래 Fact·실제 정책 전체 평가는 미구현이다. 최신 계약과 테스트 변경 예외는 RULE_ROUTING_SPEC.md 23절이다.

## 10. M1.10 — IMPLEMENTED: 메모리 내 Source Registry

```text
sources/models.py     불변 SourceDocument / SourceEvidence + enum / 오류 / ref parser
sources/registry.py   불변 SourceRegistry + 여러 ref의 전체 검증
sources/__init__.py   위 최소 API 공개
```

외부 I/O 없이 typed 객체만 받는다. sources tuple을 그대로 보관하고 내부 mutable cache나 DB/네트워크 의존을 추가하지 않았다. 작은 MVP 목록에서 선형 조회로 source ID와 locator를 찾는다. 문법·중복·구조 오류 및 참조가 금지된 수명은 SourceValidationError(PolicyDataError 하위)로 거부하며 UNKNOWN을 생성하지 않는다.

`parse_evidence_ref`는 문자열을 ID/locator pair로 분해한다. `get_source`, `has_source`, `has_evidence`, `resolve`, `validate_evidence_refs`를 제공하며 refs 문자열 tuple을 새 객체로 전면 변경하지 않는다. 전체 batch 검증 성공 때만 SourceEvidence tuple을 반환한다. sources.json을 읽거나 기존 policy loader/routing과 연결하지 않는다.

Policy Evidence만 취급하고 사용자 provenance는 기존 Fact/결과 계층에 남는다. 검증 상태와 수명 상태는 분리한다. 현재 source 구조는 검증일을 보존할 뿐 시스템 시각 조회·7일 판정·STALE 변경·stale 필터링을 하지 않는다. 역사 supersedes pair는 보존하지만 manifest에 있는 과거 확인본의 존재와 release 버전 pin은 아직 검사하지 않는다.

IMPLEMENTED: SourceDocument, SourceEvidence, in-memory SourceRegistry, evidence ref validation. NOT IMPLEMENTED: sources.json loader, PolicyEnvelope, DatasetManifest, production source data, freshness enforcement. 기존 models.py/loader/routing/evaluator/Resolver/Adapter와 synthetic policy fixtures는 변경하지 않았다. 최신 상세 계약은 POLICY_DATA_ENVELOPE_SPEC.md 26절이다.

## 11. M1.11 — IMPLEMENTED: 별도 Source Registry Loader

```text
sources/loader.py load_source_registry(path)
  → UTF-8 JSON decode + 모든 object의 중복 key 검출
  → parse_source_registry(data): 버전·strict 필드/배열·Enum/날짜 경계
  → 기존 SourceEvidence / SourceDocument 생성·검증
  → 기존 SourceRegistry 생성·검증
  → 기존 get_source / resolve / validate_evidence_refs
```

parse는 pure 경계이고 load만 파일을 읽는다. SourceDocument/Registry는 여전히 I/O를 모른다. 기존 policy loader의 JSON 규칙 파서와 통합하거나 내부 helper를 재사용하지 않았으며 기존 policy loader/routing/evaluator/Resolver/Adapter는 수정하지 않았다.

source-registry-1.0 버전을 먼저 확인하고 unknown key·잘못된 타입·JSON 중복 key·미지원 Enum·strict ISO 날짜·도메인 오류를 명시적으로 거부한다. 전체 검증 실패 시 일부 자료를 반환하지 않는다. 파일 오류와 내용 오류는 기존 SourceValidationError의 code/cause로 구분한다.

새 fixture는 data/synthetic/sources.json 및 용도 설명 SOURCES_README.md뿐이다. 상태의 수명 판정은 기존 resolve, 날짜와 검증 상태는 입력 보존이다. IMPLEMENTED: strict Source Registry JSON Loader. NOT IMPLEMENTED: production sources.json·PolicyEnvelope·DatasetManifest·실제 정책 자료·production binding·freshness enforcement·웹 검증/자동 업데이트. 최신 계약은 POLICY_DATA_ENVELOPE_SPEC.md 27절이다.

## 12. M1.12 — IMPLEMENTED: 단일 edition 도메인 계층

```text
policy_data/envelope.py    PolicyEnvelope + Coverage/SourceBinding/상태 enum/오류
policy_data/validation.py  validate_envelope_sources(envelope, registry)
policy_data/__init__.py    위 최소 API 공개
```

PolicyEnvelope가 실행 Policy를 감싸고 별도 metadata를 둔다. ID·root·규칙 버전·플래그의 중복 정의 없이 같은 Policy 객체를 꺼내 기존 evaluate_policy_tree로 실행한다. 순수 cross-validator는 SourceRegistry를 명시적으로 받아 버전·근거·정책 적용 범위·파생 확인일을 검증한다. 기존 resolve의 수명 검증을 재사용하고 Registry를 수정·소유하지 않는다.

constructor는 구조·canonical source ref·coverage/binding 집합을 검증한다. Registry 존재·확인본·locator 비교는 별도 함수다. source 로딩과 정책 평가를 생성자에서 호출하지 않으며 전역 registry·시간·파일·네트워크 의존을 만들지 않는다. 오류를 UNKNOWN으로 바꾸지 않는다.

기존 합성 Policy의 True/True 제한을 유지하므로 실제 production envelope는 지원하지 않는다. DRAFT/STALE/ENDED도 구조적으로 표현할 수 있으며 별도 운영 승인·freshness·추천 대상 여부는 판단하지 않는다. 작은 합성 통합 테스트로 원본 Policy와 envelope.policy의 평가 결과 전체가 같고 loaded synthetic Registry와의 검증이 입력을 변경하지 않음을 확인한다.

IMPLEMENTED: PolicyEnvelope domain model, envelope ↔ source registry validation. NOT IMPLEMENTED: envelope JSON Loader, DatasetManifest, production policy/source/envelope, production acceptance, freshness enforcement, 배치 로딩. 기존 모든 loader·모델·routing/evaluator/Resolver/Adapter·fixtures는 수정하지 않았다. 최신 계약은 POLICY_DATA_ENVELOPE_SPEC.md 28절이다.

## 13. M1.13 — IMPLEMENTED: Envelope Loader → Registry → Engine

```text
policy_data/loader.py load_policy_envelope(path)
  → UTF-8 decode / 중복 JSON key 검출
  → parse_policy_envelope(data): envelope metadata strict parsing
  → 기존 parse_policy_set에 중첩 Policy 하나를 m1.1로 전달
  → 기존 PolicyEnvelope 생성
별도 sources/loader.py → 기존 SourceRegistry
  → 기존 validate_envelope_sources(envelope, registry)
  → envelope.policy → 기존 evaluate_policy_tree
```

기존 m1.0/m1.1/source loader 구현은 수정하지 않았다. source loader의 작은 pure JSON helper·duplicate hook만 재사용하며 rule parser는 기존 공개 parse_policy_set을 단일 Policy adapter로 호출한다. parser fallback·Rule 파싱 복제·전역 registry·암묵적 파일 참조는 없다.

외부 JSON ID/flags와 내부 Policy의 불일치는 오류다. coverage/source binding 검증은 기존 envelope, registry의 존재·수명·확인본·적용 범위는 기존 cross-validator 책임이다. loader는 자료의 production 승인·freshness·신청기간을 판단하지 않는다. 단일 파일의 도메인 구성과 전체 release 관리도 구분하며 DatasetManifest는 여전히 미구현이다.

합성 envelope JSON 1개가 기존 sources.json을 참조한다. 독립 hand-built 및 기존 m1.1 parser 경로와 객체·평가 결과 전체가 같음을 검증한다. edition은 4자리 연도이고 실제 분기별 규칙/application window를 어디에 묶을지는 미결정 기술부채다. IMPLEMENTED: strict PolicyEnvelope JSON Loader. NOT IMPLEMENTED: DatasetManifest, production acceptance, 실제 정책·공식 source, freshness automation 및 다른 서비스 기능. 최신 계약은 POLICY_DATA_ENVELOPE_SPEC.md 29절이다.

## 14. M1.14 — IMPLEMENTED: Manifest 선택과 순수 일관성 검증

```text
기존 Envelope / SourceRegistry loader → 불변 데이터 객체 (Manifest 밖에서 로드)
manifest.py → ID/edition/version/artifact 선언/객체 지문의 불변 참조 목록
validation.py validate_dataset_manifest(manifest, envelopes, registry)
  → 정확한 선택 집합·버전·객체 fingerprint
  → 기존 validate_envelope_sources
  → 기존 Policy → evaluate_policy_tree
```

Manifest는 실체 객체를 중복 보관하지 않는다. 표준 SHA256 기반 메모리 fingerprint를 계산하지만 파일 원본 SHA256과 혼동하지 않는다. 참조에 저장한 파일/엔진 artifact hash는 선언이며 이번 검증 함수가 파일·빌드를 확인하지 않는다. I/O·현재시각·production 승인·freshness·JSON Manifest 로딩은 없다.

한 정책당 edition 하나만 선택하며 제공한 envelope 전체가 manifest 선택과 일치해야 한다. registry 전체 source ID/version과 내용 지문도 고정한다. What-if는 같은 Manifest와 계산 artifact를 고정해야 하며 이번에 What-if 실행 기능을 추가하지 않았다. 기존 엔진과 모든 loader/fixtures는 변경하지 않는다.

IMPLEMENTED: DatasetManifest domain model, dataset consistency validation. NOT IMPLEMENTED: Manifest JSON Loader, production dataset, 실제 정책, release acceptance·freshness automation. 다음 작업은 첫 실제 resident slice 인코딩이다. 현재 합성 True/True 제약의 실제 자료 수용 경계를 그 작업에서 명시적으로 해결하고 추가 generic infrastructure를 자동 확장하지 않는다. 최신 계약은 POLICY_DATA_ENVELOPE_SPEC.md 30절이다.

## 15. M1.15 — IMPLEMENTED: 공식 근거와 첫 실제 leaf의 연결

```text
별도 실제 sources.json → 기존 SourceRegistry strict loader ─────┐
별도 실제 DRAFT Envelope JSON → 기존 Envelope/m1.1 strict parser ┤
  → 기존 validate_envelope_sources ─────────────────────────────┘
  → envelope.policy → 기존 evaluate_policy_tree → Resolver → Adapter
  → 주민등록 조건 leaf의 RuleEvaluation
```

models/기존 policy parser/Envelope loader의 실제 flags 수용 경계만 확장했다. 생성 시 명시적 allow_real_data=True인 경우 False/False를 허용하며, 합성 기본 진입점은 유지한다. Envelope는 일치한 실제 flags를 바꾸지 않고 그대로 전달한다. 실제 자료의 생성 허용과 운영 승인 여부는 구별한다.

기존 routing/evaluator/Resolver/Adapter/source validator/결과·사실 타입은 변경하지 않았다. 실제·합성 자료의 잘못된 연결은 기존 참조/버전/적용 정책 검증으로 거부한다. Source schema나 coverage를 새로 설계하지 않았다. 원문 조회는 수동 데이터 확인 작업에 한정되며 런타임 평가나 테스트는 네트워크를 사용하지 않는다.

Manifest는 검증된 배포 artifact가 없어 이번에 생략했다. 전체 정책 판정·production acceptance·freshness automation·API/UI 등은 추가하지 않았다. PolicyEvaluation 자체에는 coverage가 없으므로 호출자는 Envelope의 DRAFT/CONDITION_SLICE 범위를 함께 해석해야 한다. 실제 자료·7개 입력 사례·검증 한계는 REAL_POLICY_001_IMPLEMENTATION.md에 기록한다.

## 16. M1.16A — IMPLEMENTED: 평가와 분리된 BirthFact

facts/birth.py에 BirthSource/BirthFact 및 ProfileValidationError 하위 BirthFactValidationError만 추가했다. facts/__init__.py는 공개 export를 제공한다. 입력은 정확한 date/None과 별도 BirthSource이며 모델은 frozen/slots다. to_dict는 새로운 JSON 친화 값 표현만 반환한다.

UserProfile.age·정책 범위·평가 context와 연결하지 않는다. 모델은 I/O·현재시각·나이/윤년 산식·source 우선순위·상태 판정을 수행하지 않는다. 기존 주민등록 모델·엔진·결과·loader·routing·실제 자료는 변경하지 않았다.

IMPLEMENTED: BirthSource/BirthFact 입력 모델·검증·불변성·모델 단위 테스트. NOT IMPLEMENTED: BirthDateRule/evaluator/Resolver/Adapter/routing/JSON loader/actual Q3 birth data/분기 선택. 다음은 독립 BirthDateRule 모델 검증만 수행하는 작은 작업이며 상세 현재 계약은 REAL_POLICY_001_BIRTH_SLICE_SPEC.md 19절이다.

## 17. M1.16B — IMPLEMENTED: 평가와 분리된 BirthDateRule

specialized_rules/birth_date.py와 패키지 공개 export만 추가했다. 모델은 정책의 양끝 포함 날짜 구간과 근거 문자열을 보유하고 구조를 검증한다. BirthFact를 import/보관/평가하지 않으며 UserProfile·시간 context·분기 선택에도 의존하지 않는다. 기존 specialized rule에는 공유 검증 helper가 없어 같은 작은 구조 검증을 사용했다.

RuleNode/Policy/RuleGroup/RuleEvaluation/evaluator/routing/loader/SourceRegistry/실제 데이터는 변경하지 않았다. 기존 m1.1 parser와 정책 트리는 여전히 BirthDateRule을 거부한다. 패키지에서 import할 수 있다는 것이 실행 트리 등록이나 JSON 지원을 의미하지 않는다.

IMPLEMENTED: BirthDateRule structural model·필드/범위 검증·불변성·값 표현·구조 단위 테스트. NOT IMPLEMENTED: birth 평가·Resolver/Adapter·결과 타입/RuleNode/routing/loader 연결·actual Q3 birth data. 상세 계약과 다음 최소 결과 설계 작업은 REAL_POLICY_001_BIRTH_SLICE_SPEC.md 20절이다.

## 18. M1.16D — IMPLEMENTED: Birth 결과 계층만 확장

result_types.py의 BirthDateCondition/BirthDateDetails/BirthDateReasonCode와 models.py의 유한 타입/condition별 검증을 추가했다. 기존 root 공개 export도 확장했다. RuleEvaluation의 생성자 필드·순서는 유지하며 정책/프로필/Rule/Fact를 결과 객체에 보관하지 않는다.

수동 결과 → 구조 검증 → 기존 to_dict → PolicyEvaluation 중첩 표현까지 가능하다. 날짜/범위의 실제 비교는 수행하지 않는다. 결과 생성자는 상태·사유·값 유무·source·missing_fields의 정합성을 검증하고 실제 판정 함수는 다음 단계다. 기존 aggregation·직렬화 알고리즘·resident Adapter/Resolver는 변경하지 않았다.

IMPLEMENTED: Birth 결과 typed contract와 공통 결과 모델 수용, 수동 생성·직렬화 테스트. NOT IMPLEMENTED: birth evaluator/상태 계산, RuleNode/routing/loader, actual Q3 data. 기존 birth 모델·실제 resident slice·sources는 그대로다. 상세 현재 범위와 검증 한계는 REAL_POLICY_001_BIRTH_RESULT_CONTRACT.md 24절을 따른다.

## 19. M1.16E — IMPLEMENTED: 순수 birth evaluator

birth_evaluator.py에 evaluate_birth_date_rule(rule,birth_fact) 하나를 추가하고 root export로 공개했다. 기존 model → specialized_rules 의존에 역방향 evaluator import를 넣지 않도록 별도 모듈에 둔다. 새 패키지·Resolver·Adapter 없이 기존 RuleEvaluation을 직접 생성한다.

입력 객체 타입 확인 → 누락/범위 비교 → 기존 Condition/Details/결과 구성 흐름이다. 실제 방향 비교는 이 함수의 책임이다. 모델 내부 검증을 중복 구현하지 않고 기존 constructor를 사용한다. 외부 I/O·시각 조회·캐시·프로필/날짜 context 의존은 없다.

IMPLEMENTED: 독립 inclusive date range 비교, 방향별 FAIL/누락 UNKNOWN, provenance·evidence 보존, 결정적 직렬화 검증. NOT IMPLEMENTED: RuleNode/routing/정책 트리/loader/actual Q3 data. 기존 atomic/resident evaluator·집계·결과 타입·실제 자료는 변경하지 않았다. 현재 계약과 다음 routing 설계 작업은 REAL_POLICY_001_BIRTH_RESULT_CONTRACT.md 25절이다.

## 20. M1.16G — IMPLEMENTED: 기존 router의 Birth dispatch

메모리 트리의 유한 노드 목록에 BirthDateRule을 추가하고 EvaluationFacts.birth로 단일 Fact를 전달한다. router는 별도 판정 없이 기존 evaluate_birth_date_rule을 호출하여 같은 RuleEvaluation을 사용한다. 기존 atomic/resident/group 본문·public API·ALL/ANY/NOT·결과 조립·serializer는 유지했다.

입력 부재는 evaluator의 정상 UNKNOWN이며 잘못된 타입·context·미지원 노드·evaluator 예외는 기존 오류 경로로 전달한다. birth-only의 신청일 비의존성과 resident-containing 트리의 기존 context preflight를 함께 보존한다. source 조회·age 역산·분기 선택 기능은 추가하지 않았다.

IMPLEMENTED: Birth RuleNode, EvaluationFacts.birth, birth routing dispatch, mixed aggregation support. NOT IMPLEMENTED: JSON loader support·actual Q3 policy data. PolicySet birth는 schema 지원 전까지 차단한다. 실제 resident slice/sources/Envelope는 그대로이며 승인된 세 테스트 외 기존 기대값은 유지했다. 상세 현재 계약은 REAL_POLICY_001_BIRTH_ROUTING_SPEC.md 25절이다.


## 21. M1.16I — IMPLEMENTED: JSON → Birth 판정 경로

m1.1 JSON → 기존 parse_policy_set/_node의 명시적 birth_date 분기 → strict 날짜 변환 → 기존 BirthDateRule 생성자 → Policy/RuleGroup/PolicySet → 기존 evaluate_policy_tree → evaluate_birth_date_rule → RuleEvaluation 경로를 합성 데이터로 연결했다.

변경은 loader.py의 작은 필수 날짜 helper/분기, models.py의 m1.0 birth guard 한정이다. atomic/resident 파싱·평가·router·Envelope loader·집계·직렬화 책임은 유지한다. 입력 모양으로 추정하지 않고 잘못된 노드는 전체 load failure다. SourceRegistry 조회나 외부 I/O는 순수 parse 경로의 책임이 아니다.

IMPLEMENTED: m1.1 birth_date JSON parser, PolicySet m1.1 birth support, synthetic Loader → Routing 및 hand-built/loaded 의미 동등성 검증. NOT IMPLEMENTED: actual Q3 birth data/locator/actual PolicyEnvelope 통합, quarter selection, new edition syntax. 기존 실제 resident slice와 sources/data/releases는 그대로다. 합성 Envelope 전파 검증은 실제 출처·운영 승인을 의미하지 않는다. 상세 계약·검증 기록은 REAL_POLICY_001_BIRTH_LOADER_SPEC.md 29절이다.

## 22. M2.1 — IMPLEMENTED: 계산과 분리한 Cashflow 값 계층

```text
backend/cashflow/errors.py    CashflowValidationError(ValueError)
backend/cashflow/models.py    CashflowInput / CashflowResult / 작은 KRW validator
backend/cashflow/__init__.py  두 모델과 오류만 공개
```

기존 policy_engine 밖의 독립 패키지다. dataclasses와 로컬 오류만 사용하며 정책 모델·상태·Envelope·현재 시각·I/O에 의존하지 않는다. UserProfile에 지출 필드를 추가하지 않았다. 두 frozen/slots 모델은 타입·부호·nullable 계약을 검사하고 새 primitive snapshot을 반환한다.

이 단계에는 Input→Result 변환이 없다. Result는 수동으로 구성할 수 있고 타입·부호 검증이 계산 정확성을 뜻하지 않는다. 산술·저축 상한은 다음 calculate_cashflow 한 곳에서 수행해야 한다. 모델의 월 정책 현금액은 숫자 보존이며 정책 승인·지급 정의·운영 수용 gate가 아니다.

IMPLEMENTED: CashflowInput/CashflowResult/strict KRW validation/불변성/모델 테스트. NOT IMPLEMENTED: calculator, benefit bridge, 정책 연결, restricted benefit, What-if, financial products, API/UI. 실제 releases·기존 Policy Engine은 유지하며 ResidenceHistory 구현 보류도 유지한다. 상세 필드·오류·검증 기록은 CASHFLOW_ENGINE_SPEC.md 20절이다.

## 23. M2.2 — IMPLEMENTED: 독립 Cashflow 계산 함수

```text
검증된 CashflowInput
  → backend/cashflow/calculator.py: calculate_cashflow(cashflow_input)
  → CashflowResult (열 필드 / frozen / 새 to_dict snapshot)
```

함수는 기존 모델·오류만 사용하고 exact CashflowInput 객체 타입 경계만 검사한다. 필드 검증은 기존 모델 책임이며 합계·가처분액·저축 상한 산식은 calculator 한 곳에 둔다. 월세+고정지출은 필수지출, 여기에 기타지출을 더한 값은 총지출이다. 정책 전후 가처분액은 적자를 보존하고 savable_amount만 0 이상 및 명시된 capacity로 제한한다. int 외 숫자 변환·반올림·금액 상한은 없다.

공개 호출은 `from backend.cashflow.calculator import calculate_cashflow`다. 기존 최상위 models/errors API를 유지하기 위해 __init__.py는 변경하지 않았다. 모델·오류·기존 Policy Engine·데이터 파일 역시 불변이다. 현재 시각·I/O·난수·전역 가변 상태·입력 변경을 사용하지 않는다. 동일 입력의 반복 결과와 to_dict 값이 동일하다.

IMPLEMENTED: pure monthly calculation, 명시적 월 현금액 반영 산술, savings cap, 78개 계산 테스트. NOT IMPLEMENTED: benefit bridge/PolicyEvaluation 연결, restricted benefit 효과, What-if 비교, 금융상품, HTTP/UI. 양수 금액 계산은 실제 정책 승인 경로가 아니며 현재 DRAFT/CONDITION_SLICE·지역화폐 혜택을 자동 적용하지 않는다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 보류한다. 상세 산식·오류·검증 기록은 CASHFLOW_ENGINE_SPEC.md 21절을 따른다.

## 24. M2.6 — IMPLEMENTED: Coverage 전용 범위 기반 값

```text
명시적 edition_id + quarter (exact int1~4 / None)
  → policy_data/eligibility_coverage.py: ApplicabilityScope
  → 불변 값 / 새 to_dict / 파생 scope_id
```

기존 policy_data 패키지의 공개 export 하나를 추가했다. 새 모듈은 dataclasses/re/PolicyDataError만 직접 사용한다. 정책 평가 결과·Cashflow·Acceptance·시각/신청일·I/O 의존은 없다. 기존 패키지 초기화의 다른 import는 유지하며 평가 실행을 새로 추가하지 않는다.

명세에 정해진 int/None 계약을 유지하고 Quarter Enum·새 패키지·범용 validator를 만들지 않았다. 기존 edition 검증은 inline이라 같은 ASCII 네 자리 검증식을 독립 값 모델에 적용했다. PolicyEnvelope/PolicyCoverage/loader/source validator/Rule Engine/Cashflow/실제 자료는 변경하지 않았다.

IMPLEMENTED: ApplicabilityScope/strict validation/불변성/결정적 값 표현/신규84개 테스트. NOT IMPLEMENTED: Inventory/Binding/EligibilityCoverage/FULL 계산/tree 검증/Acceptance/Bridge/실제 scope 연결. ResidenceHistory의 OFFICIAL_INQUIRY_REQUIRED 보류는 유지한다. 상세 검증 기록과 다음 최소 작업은 POLICY_COVERAGE_SPEC.md 31절이다.

## 25. M2.7 — IMPLEMENTED: 구현과 분리한 조건 의미 모델

```text
명시적 condition_id / meaning / requirement / evidence_refs
  → policy_data/required_condition.py: RequiredCondition
  → 불변 조건 의미 값 / 새 primitive snapshot
```

두 분류는 별도 ConditionRequirement Enum으로 고정한다. 모델은 dataclass/Enum/re/PolicyDataError와 기존 source ref 형식 parser에만 직접 의존한다. parser는 조회 없이 문자열만 검사한다. SourceRegistry·정책 평가·사용자 fact·scope 추론·Acceptance·Cashflow를 직접 호출하지 않는다.

기존 Scope의 모듈 경계와 테스트를 보존하기 위해 같은 패키지의 별도 파일을 사용했다. public export 두 개만 추가하고 기존 PolicyEnvelope/PolicyCoverage/Scope/Rule Engine/loader·Cashflow·실제 releases는 변경하지 않았다. refs의 실제 존재/버전과 inventory/tree 연결은 후속 경계다.

IMPLEMENTED: ApplicabilityScope(기존), RequiredCondition/ConditionRequirement/strict 구조 및 ref 형식/불변성/직렬화/신규104개 테스트. NOT IMPLEMENTED: ConditionInventory/ConditionBinding/EligibilityCoverage/FULL·SLICE 계산/Acceptance/Bridge/실제 inventory. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 계속 보류한다. 현재 계약과 검증 기록은 POLICY_COVERAGE_SPEC.md 32절이다.

## 26. M2.8 — IMPLEMENTED: 의미 모델을 묶는 Inventory

```text
policy_id / ApplicabilityScope / inventory_version
  + tuple[RequiredCondition,...] / 선택적 completeness_review_ref
  → policy_data/condition_inventory.py: ConditionInventory
  → 불변 목록 / 새 중첩 to_dict snapshot
```

새 모델은 기존 두 하위 모델과 PolicyDataError만 직접 참조한다. 별도 파일과 공개 export 하나를 추가하고 기존 Scope/RequiredCondition/평가·loader·Coverage·Cashflow·실제 releases는 유지했다. 정확한 타입·빈 목록·중복 condition_id를 검사하며 하위 조건을 재검증하거나 evidence를 합치지 않는다.

review ref는 값만 보존한다. 실제 검토 기록의 조회·완결성·사용자 상태·Rule/tree 대응·FULL을 계산하지 않는다. 사용자 정보 저장·시각·난수·네트워크·파일 접근은 없다.

IMPLEMENTED: 기존 Scope/RequiredCondition, ConditionInventory의 scope/조건 소유·strict 검증·ID 유일성·불변성/결정적 값 표현·신규119개 테스트. NOT IMPLEMENTED: ConditionBinding/EligibilityCoverage/FULL·SLICE 파생/Acceptance/Bridge/실제 inventory. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED로 보류한다. 상세 현재 계약은 POLICY_COVERAGE_SPEC.md 33절이다.

## 27. M2.9 — IMPLEMENTED: 독립 Binding 값 계층

```text
명시적 condition_id / rule_root_id / implementation_review_ref
  → policy_data/condition_binding.py: ConditionBinding
  → 불변 참조 값 / 새 to_dict snapshot
```

모델은 dataclass/re/PolicyDataError만 직접 사용한다. 실제 Policy/RuleGroup/RuleNode/RequiredCondition/Inventory 객체를 import/보관하지 않고 root와 검토 기록을 조회하지 않는다. ID 검증은 기존 condition/node 계약과 동일하며 기존 helper 추출·모델 변경 없이 신규 동등성 테스트로 확인했다.

새 파일과 public export 하나를 추가했으며 기존 Scope/RequiredCondition/Inventory/PolicyEnvelope/평가·loader·Cashflow·실제 releases는 변경하지 않았다. leaf/group 한 subtree root 참조만 표현하며 collection 유일성·겹침·완전 구현 여부는 판단하지 않는다.

IMPLEMENTED: 기존 세 모델, ConditionBinding의 strict 참조/불변성/equality/snapshot·신규82개 테스트. NOT IMPLEMENTED: Inventory/tree/검토 cross-validation, EligibilityCoverage, FULL·SLICE, Acceptance/Bridge/actual mapping. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED 유지. 상세 계약과 검증 기록은 POLICY_COVERAGE_SPEC.md 34절이다.

## 28. M2.11 — IMPLEMENTED: tree 평가와 분리한 Coverage 입력

```text
ConditionInventory + tuple[ConditionBinding,...]
  → policy_data/coverage.py: EligibilityCoverage
  → 로컬 참조 정합성만 확인한 불변 구조 값 / 새 to_dict
```

새 모듈은 dataclasses/PolicyDataError/Inventory/Binding만 직접 사용한다. 기존 모델 재배치·검증 변경 없이 동일 패키지에 파일과 공개 export 하나를 추가했다. 기존 eligibility_coverage.py의 Scope/모듈 경계도 유지한다.

생성자는 exact 타입·중복 condition Binding·unknown condition 참조만 검사한다. 빈/부분 tuple·검토 미완료·같은 root는 보존하고 Policy/root 조회·subtree/ownership·ReviewContext·파생 상태를 실행하지 않는다. 범위/정책 ID/version은 Inventory를 단일 원천으로 사용하고 직접 metadata를 중복하지 않는다.

IMPLEMENTED: EligibilityCoverage structural model/로컬 참조 검증/불변성/결정적 직렬화/신규83개 테스트. NOT IMPLEMENTED: ReviewContext/CoverageResult/evaluate_eligibility_coverage/tree 검증/FULL·SLICE/Acceptance/Bridge. legacy Coverage·실제001/002와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED 보류는 유지한다. 생성자/validator 책임표는 ELIGIBILITY_COVERAGE_VALIDATION_SPEC.md 33절이다.

## 29. M2.13 — IMPLEMENTED: 검토 대상의 명시적 확인본 metadata

```text
명시적 review/policy/scope/inventory·자료 확인본 지문/date/artifact ref
  → policy_data/coverage_review.py: InventoryCompletenessReview
  → 불변 metadata / 새 scope snapshot·ISO date to_dict
```

새 모듈·public export 하나만 추가했다. 직접 의존은 dataclass/date/re/PolicyDataError/Scope다. 기존 Inventory·tree·Registry·Manifest를 import/조회하지 않고 파일/Git/네트워크·현재시간·hash 계산을 하지 않는다. 기존 coverage 모델·validator·serializer는 변경하지 않았다.

모델 생성은 metadata 타입/형식의 유효성만 뜻한다. 사람의 실제 검토·참조 artifact 존재·Inventory 내용 지문 일치·FULL을 보증하지 않는다. 이 책임은 후속 Context/validator 및 외부 검토로 분리한다.

IMPLEMENTED: InventoryCompletenessReview 구조·불변성·결정적 직렬화·신규182개 테스트. NOT IMPLEMENTED: Implementation review/Context/Result/지문 계산·매칭·stale/tree 검증/FULL·SLICE/Acceptance/Bridge. 실제 안산 자료와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED 보류는 유지한다. 상세 계약과 회귀 기록은 COVERAGE_REVIEW_CONTEXT_SPEC.md 32절이다.

## 30. M2.14 — IMPLEMENTED: 실제 tree와 분리한 Implementation review

```text
명시적 policy/scope/condition/root + inventory/rule/dataset 버전
  + inventory/tree/subtree/source/implementation 지문 + review ref/date/artifact ref
  → policy_data/implementation_review.py: ImplementationBindingReview
  → 불변15필드 metadata / 새 scope snapshot·ISO date to_dict
```

직접 의존은 dataclass/date/re/PolicyDataError/ApplicabilityScope뿐이다. 기존 coverage_review.py의 단일 클래스 경계 테스트와 Inventory review를 보존하기 위해 같은 패키지의 별도 파일과 public export 하나를 추가했다. 기존 helper 추출·공통 base·모델 재배치는 없다.

입력받은 값의 타입/형식만 확인하며 Policy/Rule/Binding 객체·tree traversal·fingerprint 계산·파일/Git/네트워크·현재시각을 사용하지 않는다. 실제 구현 정답/검토 사실/현재 snapshot 일치·FULL·verification/acceptance를 인증하지 않는다. InventoryCompletenessReview와 기존 엔진/loader/serializer/Manifest는 유지한다.

IMPLEMENTED: 두 독립 review record 모델·ImplementationBindingReview 합성 테스트216개. NOT IMPLEMENTED: fingerprint calculators, CoverageReviewContext, matching/stale, CoverageResult, Coverage validator, FULL/SLICE, Acceptance/Benefit Bridge. actual release001/002와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED 보류는 유지한다. 상세 계약·검증은 COVERAGE_REVIEW_CONTEXT_SPEC.md 33절이다.

## 31. M2.15 — IMPLEMENTED: Coverage와 분리한 ReviewContext collection

```text
명시적 policy/scope + dataset/source/implementation 확인본
  + tuple[InventoryCompletenessReview,...]
  + tuple[ImplementationBindingReview,...]
  → policy_data/coverage_review_context.py: CoverageReviewContext
  → 불변7필드 collection / 원래 순서의 새 중첩 to_dict
```

직접 의존은 dataclasses/re/PolicyDataError/Scope/두 review 타입이다. 기존 record/Scope를 재생성·재검증하지 않고 원래 객체와 tuple을 보존한다. 생성자는 collection/원소 exact 타입, policy/scope 소속, 두 종류 전체 review_ref 유일성만 확인한다. 빈 collection과 같은 소속의 역사적 확인본도 표현한다.

Coverage/Inventory/Binding/Policy/평가·Cashflow·파일/Git/네트워크·현재시각을 직접 사용하지 않는다. lookup helper·cache·지문 계산·현재 내용 대조·최신 선택·stale/missing·Coverage 상태 파생은 없다. 생성 성공은 검토 사실/현재 내용 일치/FULL을 보증하지 않는다.

IMPLEMENTED: InventoryCompletenessReview, ImplementationBindingReview(변경 없음), CoverageReviewContext collection/불변성/직렬화/합성 테스트127개. NOT IMPLEMENTED: fingerprint calculators/review matching/stale/CoverageResult/Coverage validator/FULL·SLICE/Acceptance/Benefit Bridge. actual release001/002와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 상세 계약·검증·다음 지문 명세 작업은 COVERAGE_REVIEW_CONTEXT_SPEC.md 34절이다.

## 32. M2.17 — IMPLEMENTED: 독립 Inventory 지문 경로

```text
정확한 ConditionInventory
  → coverage_fingerprint.py: _build_inventory_payload
     명시5 key / 조건ID 정렬 / 근거 순서·중복 보존 / review ref 제외
  → fingerprint_condition_inventory
     canonical JSON → strict UTF-8 → SHA256 lowercase hex64
```

새 모듈의 직접 의존은 hashlib/json/PolicyDataError/ConditionInventory뿐이다. 기존 Manifest private helper·범용 serializer에 결합하지 않고 같은 JSON recipe를 적용한다. 다른 모델·기존 source 지문·loader·평가·serializer를 변경하지 않는다.

함수는 모델 내부를 재검증하거나 tree/review/사용자 facts를 사용하지 않는다. 파일/네트워크/Git·시각·난수·환경변수·가변 전역값도 없다. 인코딩 오류는 기존 PolicyDataError로 명시하며 fallback digest는 없다. public export는 Inventory 함수 하나뿐이다.

IMPLEMENTED: Inventory 지문 함수 및 합성 테스트47개(GV01~GV06 포함). NOT IMPLEMENTED: tree/subtree utility, implementation artifact 계산, matching/stale, Result/validator, FULL/SLICE, Acceptance/Bridge. actual release와 기존 SHA 선언·ResidenceHistory OFFICIAL_INQUIRY_REQUIRED 보류는 유지한다. 상세 검증은 COVERAGE_FINGERPRINT_SPEC.md 33절이다.

## 33. M2.18 — IMPLEMENTED: 전체 Policy Tree 지문 경로

```text
정확한 Policy
  → _build_policy_tree_payload: schema/policy_id/rule_version/root
  → _build_rule_node_payload: 정확한 atomic/resident/birth/group 재귀 projection
  → _digest_payload: Inventory와 공통 canonical JSON/strict UTF-8/SHA256
  → fingerprint_policy_tree: lowercase hex64
```

기존 coverage_fingerprint.py 안에 추가했으며 새 패키지·generic serializer·public subtree API는 없다. node의 모든 명시 의미 필드·FactBasis·지역 구조·ISO 날짜·계층·순서를 보존한다. walk_nodes의 flat 목록·PolicyEvaluation·사용자 facts·review metadata를 사용하지 않는다. 미래 node/subclass는 fail closed다.

M2.17 인코딩 본문을 작은 private helper로 추출해 두 public 함수에서 공유한다. 기존 Inventory payload/고정 digest·오류는 유지한다. 이 확장과 충돌한 기존 구조 테스트1개만 명시적 사용자 승인으로 갱신했다. 모델/loader/평가/Registry·Manifest·실제 데이터는 변경하지 않는다.

IMPLEMENTED: Inventory/전체 Tree 지문, GV01~GV06 및 Tree7개 golden, 신규 Tree 테스트72개. NOT IMPLEMENTED: subtree·implementation artifact 계산, matching/stale, CoverageResult/validator, FULL/SLICE, Acceptance/Bridge. 외부 I/O·현재시각·환경 의존은 없다. ResidenceHistory OFFICIAL_INQUIRY_REQUIRED와 actual releases는 유지한다. 상세 검증은 COVERAGE_FINGERPRINT_SPEC.md 34절이다.

## 34. M2.19 — IMPLEMENTED: root-only subtree 지문 경로

```text
명시적으로 전달한 RuleNode root
  → fingerprint_rule_subtree
     schema=coverage-subtree-1.0 + root=_build_rule_node_payload(root)
  → 기존 _digest_payload
     canonical JSON / strict UTF-8 / SHA256 lowercase hex64
```

새 node serializer/encoder/package는 만들지 않았다. 현재 네 exact node·모든 descendant·순서/근거는 기존 helper가 처리하고, 미지원 객체/subclass는 fail closed다. 기존 Inventory/Tree 지문 본문과 payload/고정값은 유지한다.

Policy/ID lookup·부모 pointer·Binding/Review matching·stale·사용자 facts·상태 파생은 없다. parent/policy_id/rule_version은 입력도 payload도 아니다. 파일/네트워크/Git·시각·환경변수·평가 실행에도 의존하지 않는다.

IMPLEMENTED: Inventory/전체 Tree/subtree 세 지문 및15개 golden vectors, 신규 subtree 테스트58개. NOT IMPLEMENTED: implementation artifact 계산, root lookup, matching/stale, CoverageResult/validator, FULL/SLICE, Acceptance/Bridge. 기존 구조 제한 테스트2개만 사용자 승인으로 갱신했다. actual releases와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 상세 검증 및 다음 matching 설계 작업은 COVERAGE_FINGERPRINT_SPEC.md 35절이다.

## 35. M2.21 — IMPLEMENTED: 계산과 분리한 Review match 결과 계층

```text
명시적 status/ref + canonical stale/missing 사유 tuple
  + Implementation이면 condition/root ID
  → policy_data/coverage_review_match.py
     세 Enum + InventoryReviewMatch / ImplementationReviewMatch
  → 로컬 조합 검증한 불변 값 / 새 to_dict
```

직접 의존은 dataclasses/Enum/re/PolicyDataError뿐이다. private validation helper는 exact 타입/사유 순서·중복/상태 조합만 검사하며 기존 Binding/Review/Context를 import하거나 실제 version/지문을 비교하지 않는다. 공통 base·matcher placeholder·추가 상태는 없다.

새 모듈·공개 export만 추가하고 기존 Review/Context/Coverage·세 지문 utility·평가/loader·Cashflow는 유지했다. FULL/SLICE와 사용자 PASS/FAIL/UNKNOWN도 별개다. 시간·파일/네트워크/Git·외부 artifact 조회는 없다.

IMPLEMENTED: Review matching 결과 값 모델/합성 테스트166개. NOT IMPLEMENTED: ref resolver/matcher, stale 계산, root lookup, CoverageResult/validator, Acceptance/Bridge. actual releases와 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다. 다음은 명시 ref의 존재/종류만 확인하는 작은 resolver 작업이며 상세 책임·검증은 COVERAGE_REVIEW_MATCHING_SPEC.md 39절이다.

## 36. M2.22 — IMPLEMENTED: Context 내부의 명시 ref 조회

```text
제공된 exact CoverageReviewContext + exact 비공백 review_ref
  → coverage_review_resolution.py의 두 private resolver
  → 요청 종류 collection의 exact ref 검색
     성공: 원래 InventoryCompletenessReview / ImplementationBindingReview 객체
     반대 종류에 존재: WRONG_REVIEW_TYPE Data Error
     두 collection에 없음: REVIEW_REF_NOT_FOUND Data Error
```

입력 오류는 INVALID_MATCH_INPUT PolicyDataError다. Context=None은 이 helper 입력이 아니며 후속 matcher가 MISSING을 처리한다. ref를 정규화하지 않고 record를 재생성하지 않는다. Context 생성자의 exact record 종류와 전역 ref 유일성 불변조건을 전제로 선형 검색한다. 날짜/버전/tuple 위치에 따른 latest 선택이나 cache는 없다.

직접 의존은 Context/두 Review 타입/PolicyDataError뿐이다. 공개 export·기존 모델·지문 utility는 변경하지 않았다. 현재 policy/scope·condition/root·version·fingerprint 비교, stale, MatchResult 생성과 외부 I/O는 없다. 구조 검증이나 실제 검토 승인도 수행하지 않는다.

합성 테스트63개로 exact lookup·원본 identity·없는 ref/잘못된 종류·입력 타입·공백/대소문자·순서와100회 반복·허용 속성 외 접근 부재를 검증했다. 다음 단계는 Inventory private matcher 하나이며 별도 tree 구조 validator와 Implementation matcher는 아직 없다. 상세 오류/검증 계약은 COVERAGE_REVIEW_MATCHING_SPEC.md40절이다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 37. M2.23 — IMPLEMENTED: Inventory completeness review matching

```text
exact ConditionInventory + exact CoverageReviewContext 또는 None
  + 상위에서 미리 계산한 current_inventory_fingerprint (keyword-only)
  → private _match_inventory_review (coverage_review_matching.py)
     입력 타입/현재 지문 형식 검증
     ref 미선언 → MISSING / INVENTORY_REVIEW_NOT_DECLARED
     ref 선언 + Context 없음 → MISSING / NO_REVIEW_CONTEXT
     Context 있음 → 기존 resolver → 선택 record의 policy/scope 대조
       → Inventory version/동일 version 지문 consistency 검사
       → Dataset version/동일 version Registry consistency 검사
     모순이면 PolicyDataError, 아니면 InventoryReviewMatch의 MATCHED/STALE
```

M2.23 승인에 따라 ref=None은 Context=None이어도 미선언 사유만 반환한다. M2.20의 두 사유 반환 설계를 구체적으로 변경했으며 M2.21 결과 값 모델의 허용 조합은 유지한다. 모든 입력 검증은 정상 missing 분기보다 먼저다.

각 version이 다르면 해당 stale reason을 모으고, 같으면 그 쌍의 내용 모순을 오류로 거부한다. Inventory stale가 독립 source 모순을 숨기지 않는다. canonical 사유는 Inventory → Dataset이며 새 사유를 추가하지 않는다. Context와 record 소속 불변조건을 이용해 선택 record의 target 비교만 수행하고 중복 Context target 검사는 하지 않는다.

지문 계산은 호출자 책임이고 matcher는 공급된 문자열만 비교한다. 신뢰된 상위 준비 경로는 아직 없다. 형식이 맞는 임의 hash를 실제 현재 Inventory 내용으로 인증하지 않으며 새 snapshot 모델/public API도 만들지 않았다. 직접 의존은 re/오류/Inventory/Context/기존 결과 Enum·모델/private Inventory resolver뿐이다. cache·시간·파일/네트워크/Git·환경·입력 변경은 없다.

IMPLEMENTED: Inventory matcher, 합성 테스트142개. NOT IMPLEMENTED: Implementation matcher, Binding matching, subtree lookup, Policy/rule/tree/subtree/implementation 지문 matching, CoverageResult, 최종 Coverage validator/FULL·SLICE/Acceptance/Bridge. 기존 모델·resolver·지문 utility·공개 export·기존 테스트는 유지했다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**도 유지한다. 상세 오류 prefix·테스트·다음 단일 작업은 COVERAGE_REVIEW_MATCHING_SPEC.md41절이다.

## 38. M2.24 — IMPLEMENTED: 단일 Binding의 Implementation review matching

```text
exact Inventory + Binding + Context 또는 None
  + 상위에서 공급한 current Inventory 지문 / Policy.rule_version / Tree 지문 / subtree 지문
  → private _match_implementation_review (coverage_review_matching.py)
     입력 타입/현재값 형식 검증
     Context 없음 → Binding의 condition/root/ref 보존, MISSING / NO_REVIEW_CONTEXT
     Context 있음 → 기존 Implementation resolver
       → policy → scope → condition → root 대상 일치
       → Inventory 동일 version 지문 검사
       → rule 동일 version Tree → subtree 지문 검사
       → Dataset 동일 version Registry 지문 검사
       → 구현 artifact 지문 변경 여부
     오류면 PolicyDataError, 아니면 기존 ImplementationReviewMatch의 MATCHED/STALE
```

Policy를 인자로 받지 않고 current_rule_version을 keyword-only로 받는다. 나머지 세 현재 지문도 계산된 문자열로 받으며 실제 소속/내용의 보증은 신뢰된 상위 준비 계층 책임이다. canonical stale 사유는 Inventory → Rule → Dataset → Implementation이다. 다른 version의 stale가 독립 쌍의 동일 version 모순이나 잘못된 target 연결을 숨기지 않는다.

기존 Inventory matcher 함수 본문은 바꾸지 않았다. 추가 의존은 Binding/기존 Implementation 결과/private resolver뿐이며 모델/Enum/resolver/지문 utility·공개 export는 유지한다. 지문 계산·Policy 순회/root lookup·ownership/overlap/unbound·외부 I/O·시각·환경·입력 변경·cache는 없다. reviewed_at/artifact ref도 matching에 사용하지 않는다.

IMPLEMENTED: 두 private matcher, 신규 합성 Implementation 테스트257개.
NOT IMPLEMENTED: root lookup, Coverage structural validator, CoverageResult, FULL/SLICE 파생, 최종 Coverage validator, Acceptance/Bridge. matcher의 MATCHED만으로 실제 root/전체 구조/검토의 진실성/FULL을 인증하지 않는다.

다음 판단은 **READY_FOR_COVERAGE_STRUCTURE_VALIDATION_DESIGN**이다. 기존 구조 원칙을 유지하면서 첫 root lookup 단계의 구체적 입력·반환·오류/테스트 계약을 확정하는 작업 하나를 권장한다. 상세 검증·책임 경계는 COVERAGE_REVIEW_MATCHING_SPEC.md42절이다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 39. M2.26 — IMPLEMENTED: 명시 root ID의 원본 node 조회

```text
exact Policy + exact 비공백 rule_root_id
  → private _resolve_rule_root (policy_data/rule_root_resolution.py)
     Policy/ID 입력 검사
     → 기존 walk_nodes로 root 포함 pre-order 전체 DFS
        각 node의 exact 지원 타입 확인 → rule_id 읽기
        지역 seen ID set / target 후보 / duplicate flag
     → unsupported가 없고 순회 완료: duplicate 오류 우선
     → target 부재면 RULE_ROOT_NOT_FOUND, 있으면 원본 RuleNode 객체
```

지원 타입은 PolicyRule/ResidentRegistrationRule/BirthDateRule/RuleGroup 네 개뿐이다. ID를 정규화하지 않고 group operator에 따라 검색을 줄이지 않는다. target을 먼저 찾아도 끝까지 순회한다. Policy/walk_nodes·matcher/Review resolver·모델·지문 utility·공개 export는 변경하지 않았다.

입력 오류 INVALID_STRUCTURE_INPUT, node 타입 오류 UNSUPPORTED_RULE_NODE, 중복 DUPLICATE_RULE_NODE_ID, 부재 RULE_ROOT_NOT_FOUND 모두 기존 PolicyDataError다. unsupported는 ID 접근 전, duplicate는 순회 후, 부재는 그 다음이다. 원본 객체를 반환하며 Binding/condition·소유자·review 상태·version/정책 ID 대조는 다루지 않는다.

합성 테스트80개로 root/leaf/group/nested/정확한 ID/전체 순회/원본 identity/100회 반복·무변경·금지 의존 부재를 검증했다. 생성자가 막는 invalid tree를 훼손해 테스트하지 않고 duplicate/unsupported 방어 시나리오의 실행 한계를 명시했다.

IMPLEMENTED: 독립 private root resolver.
NOT IMPLEMENTED: ownership/overlap/unmapped·전체 결합 검사, RuleTreeIndex/ResolvedConditionBinding, 통합 지문 준비/review matching 경로, CoverageResult/FULL·SLICE/최종 Coverage validator/Acceptance/Bridge. 상세 계약과 검증은 COVERAGE_RULE_ROOT_LOOKUP_SPEC.md33절이다.

다음 판단은 **READY_FOR_COVERAGE_OWNERSHIP_DESIGN**이다. 작은 tree에서 단일 resolver로 소유 집합 설계를 진행할 수 있어 index 모델은 필수 선행이 아니다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 40. M2.28 — IMPLEMENTED: ownership 수집과 canonical overlap 검사

```text
원본 RuleNode
  → _collect_owned_rule_ids
     기존 walk_nodes → root 포함 pre-order ID tuple
     exact 지원 타입 / 중복 ID 방어

이미 resolve한 exact (ConditionBinding, RuleNode) 쌍의 exact tuple
  → _validate_binding_ownership_no_overlap
     전체 포장/타입 → 중복 condition → canonical root ID 연결 확인
     → condition_id순 각 entry의 소유 tuple 수집 / 지역 set
     → canonical pair 교집합
        첫 충돌: COVERAGE_OWNERSHIP_OVERLAP + 고정 JSON
        비겹침: None
```

M2.28 지시문의 ID tuple 후보보다 Source of Truth25절의 최종 **원본 root pair** 입력을 따른다. 임의 owned IDs 입력/병렬 API를 추가하지 않는다. JSON은 두 condition/root, 전체 교집합 수, Unicode 최소 증거 ID만 포함하며 sort_keys/ensure_ascii/compact separators를 고정한다.

새 coverage_ownership.py의 두 함수는 private이고 공개 export는 없다. 기존 root resolver·walk_nodes/모델/Review matcher·지문 utility는 변경하지 않았다. root lookup은 호출자 책임이며 Policy 소속/Binding 누락 여부를 이 helper가 새로 인증하지 않는다. 모든 수집이 끝난 뒤 overlap을 검사하고 원본 Binding/tree를 변경하지 않는다.

IMPLEMENTED: collector / no-overlap validator, 합성 테스트93개.
NOT IMPLEMENTED: unmapped/missing Binding/전체 결합·Policy identity 검사, root lookup/구조 orchestration, RuleTreeIndex/ResolvedBinding, CoverageResult/FULL·SLICE/최종 Coverage validator/Acceptance/Bridge. 지문/검토/사용자 평가·외부 I/O·cache는 없다.

다음 판단은 **READY_FOR_UNMAPPED_RULE_DESIGN**이다. 상세 입력·오류·검증 기록은 COVERAGE_OWNERSHIP_SPEC.md34절이다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 41. M2.30 — IMPLEMENTED: 실행 leaf target과 미매핑 사실 분석

```text
exact Policy
  → _collect_policy_coverage_target_rule_ids
     walk_nodes로 전체 tree pre-order 순회
     exact 네 node 타입 / 전체 ID 중복 방어
     → 세 실행 leaf ID만 원래 순서의 tuple로 반환

exact Policy + 이미 resolve한 exact (ConditionBinding, 원본 RuleNode) 쌍의 exact tuple
  → _find_unmapped_rule_ids
     전체 입력/중복 condition/Binding-root ID 연결 확인
     → target collector 한 번
     → condition_id순 각 entry의 기존 ownership collector 한 번 / 지역 set union
     → target 순서대로 소유되지 않은 leaf ID tuple 반환
```

두 함수는 새 policy_data/coverage_unmapped.py에만 두고 공개 export를 추가하지 않았다. RuleGroup은 target에서 제외하되 ALL/ANY/NOT 아래 탐색은 계속한다. ownership은 기존처럼 group을 포함하며 이 의미를 변경하지 않았다. 빈 Binding은 target 전체, 모두 소유되면 빈 tuple이다. 소유되지 않은 composition group 자체는 미매핑 항목이 아니다.

M2.29 COVERAGE_UNMAPPED_RULE_SPEC.md를 Source of Truth로 사용한다. 과거40절 및 기존 명세의 무조건 unbound 오류/모든 node target 취지는 해당 명세31절의 명시적 대체 범위를 따른다. 미매핑 사실만으로 오류나 완결성을 판단하지 않는다.

Assumption A1: 상위 caller가 동일 현재 Policy에서 모든 root를 resolve하고 no-overlap 검사를 마쳤다. finder 내부의 재조회/소속 검사/overlap 재검사는 없다. 이 준비를 연결하는 통합 경로는 아직 미구현이다. Review·지문·평가·외부 I/O·시각·환경·cache를 사용하지 않고 입력을 변경하지 않는다.

IMPLEMENTED: 두 private 분석 helper·합성 테스트112개.
NOT IMPLEMENTED: missing condition 계산·Binding completeness·미매핑 Data Error 승격/standalone validator·통합 구조 orchestration·CoverageResult/FULL·SLICE/최종 Coverage validator/Acceptance/Bridge.

상세 계약·검증 기록은 COVERAGE_UNMAPPED_RULE_SPEC.md35절이다. 다음 판단은 **READY_FOR_COVERAGE_STRUCTURE_ORCHESTRATION_DESIGN**이며, 다음 가장 작은 작업은 root resolution/no-overlap/unmapped/missing의 호출·해석 순서를 문서로 설계하는 것이다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 42. M2.32 — IMPLEMENTED: deterministic 매핑 구조 분석

```text
exact EligibilityCoverage + exact Policy
  → _analyze_coverage_structure (policy_data/coverage_structure.py)
     타입 → inventory.policy_id와 policy.policy_id 일치
     → Inventory 입력 순서의 missing condition IDs
     → condition_id순 모든 root resolution / 원본 pair tuple
     → 기존 no-overlap validator 한 번
     → 기존 unmapped finder 한 번 / Policy pre-order
     → missing empty + unmapped nonempty이면 COVERAGE_UNMAPPED_RULE
     → 나머지는 (missing, resolved_pairs, unmapped) private tuple 반환
```

missing은 정상 incomplete facts이며 root 부재/overlap 오류를 숨기지 않는다. zero Binding도 root 조회0회 뒤 no-overlap/finder를 각1회 실행하고 전체 missing/targets를 반환한다. 모든 condition이 bound인데 미매핑 leaf가 남을 때만 고정2필드 JSON의 오류로 승격한다. helper 오류는 원래 객체로 전파한다.

M2.31 COVERAGE_STRUCTURE_ORCHESTRATION_SPEC.md의 API/phase/해석 경계를 따랐다. root/ownership/unmapped helper·모델·공개 export·기존 테스트/기대값은 변경하지 않았다. resolved Binding/root는 원본이며 공개 결과 모델·serializer·persistent roots를 만들지 않는다. private 함수 하나와 합성 테스트94개를 추가했다.

입력 모델의 로컬 invariant를 신뢰하고 scope/version·Review/fingerprint/사용자 평가·시각/env/외부 I/O/cache를 사용하지 않는다. 같은 입력100회·Binding 순열·오류 우선순위/JSON·호출 횟수·원본 무변경을 검증했다. 실제 정책 Coverage/분석 결과는 생성하지 않았다.

IMPLEMENTED: missing/root/overlap/unmapped를 연결한 private 구조 분석 및 조건부 오류 승격.
NOT IMPLEMENTED: 전체 composition gate·지문/Review 통합 경로·CoverageResult/FULL·SLICE·최종 Coverage validator·Acceptance/Bridge. 정상 반환은 mapping 검사 범위에 한정한다.

상세 계약·검증 기록은 COVERAGE_STRUCTURE_ORCHESTRATION_SPEC.md32절이다. 다음 판단은 **READY_FOR_COVERAGE_INTEGRATION_GATE_DESIGN**이며, 다음 가장 작은 작업은 전체 결합 gate와 구조/지문/Review 계층의 책임·실행/오류 순서를 문서로 설계하는 것이다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 43. M2.34 — IMPLEMENTED: composition gap 사실 분석

```text
exact Policy + exact (ConditionBinding, 원본 RuleNode) 쌍의 exact tuple
  → _find_composition_gap_group_ids (policy_data/coverage_composition.py)
     전체 입력/중복 condition/Binding-root ID 연결 방어
     → 기존 walk_nodes로 전체 Policy pre-order 확인
        exact 지원 node/operator·전체 node ID 중복 방어
        ANY/NOT group 후보 IDs를 원래 순서로 수집
     → canonical condition_id순 기존 ownership collector / 지역 union
     → 소유되지 않은 ANY/NOT IDs만 pre-order tuple로 반환
```

unowned ALL은 top/nested와 무관하게 제외한다. owned ANY/NOT 또는 상위 Binding이 소유한 descendant group도 제외한다. child leaf들이 별도 Binding에 전부 포함돼도 parent ANY/NOT는 소유되지 않아 gap이다. zero Binding이면 모든 ANY/NOT group이 사실로 반환된다. gap의 존재를 이유로 오류 승격하거나 missing을 계산하지 않는다.

helper는 private이며 공개 export/새 모델을 추가하지 않았다. M2.32 구조 분석을 통과한 같은 Policy의 원본 pairs를 신뢰하고 root lookup/overlap/unmapped를 재실행하지 않는다. 기존 구조 함수·ownership/root/unmapped helper·모델·테스트/기대값은 변경하지 않았다.

합성 테스트112개로 owned/unowned·parent/nested/partial child·pre-order/원문 ID·exact 입력·선행 검증/호출 횟수·예외 원본 전파·100회/Binding 순열·입력 무변경을 검증했다. 현재 resident/birth와 미래 duration ANY의 올바른/잘못된 분해도 실제 자료 없이 합성 tree로만 확인했다. 실제 기간 Rule/산식은 없다.

IMPLEMENTED: global composition gap analysis 한 private helper.
NOT IMPLEMENTED: COVERAGE_COMPOSITION_GAP 승격·Integration Findings 모델·전체 integration gate·Context target/지문/Review 연결·CoverageResult/FULL·SLICE·최종 Coverage validator·Acceptance/Bridge. Review/fingerprint·사용자 평가·외부 I/O/시각/env/cache는 없다.

상세 계약·검증 기록은 COVERAGE_INTEGRATION_GATE_SPEC.md38절이다. 다음 판단은 **READY_FOR_COVERAGE_INTEGRATION_FINDINGS_MODEL**이며, 다음 가장 작은 작업은 두 최소 private immutable findings 값 모델과 합성 테스트다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 44. M2.35 — IMPLEMENTED: 순수 Integration Findings 값 계층

```text
이미 계산된 subtree fingerprint + 정확한 ImplementationReviewMatch
  → _ImplementationIntegrationFinding (두 필드, IDs는 match에만)

이미 계산된 M/U/G tuples + Inventory/Tree fingerprints
  + 정확한 InventoryReviewMatch + canonical Implementation findings tuple
  → _CoverageIntegrationFindings (일곱 필드)
     strict 타입/형식·중복·정렬·로컬 facts 관계 검사
     → frozen/slots 값과 새 중첩 to_dict snapshot
```

두 클래스는 새 policy_data/coverage_integration_findings.py에만 두고 공개 export에 추가하지 않았다. M2.33 최종2/7필드를 따르며 policy/scope/rule identity·runtime root·원본 Coverage/Binding/Context·최종 상태를 복제하지 않는다. 이번 지시대로 값 표현용 to_dict만 추가하고 기존 MatchResult.to_dict를 재사용한다.

M은 Inventory 입력 순서, U/G는 tree pre-order를 받은 그대로 보존한다. canonical Implementation order를 검증하고 M과 existing condition의 교집합·M empty/U 또는 G positive인 구성을 거부한다. 이 검사는 이미 계산된 facts의 로컬 정합성으로, 실제 분석·COVERAGE_COMPOSITION_GAP 승격·FULL/SLICE 계산이 아니다.

원본 MatchResult의 identity/상태/사유를 보존한다. 세 지문은 형식만 검사하며 지문 계산기/Review matcher·structure/composition helper·외부 I/O/시각/env/cache에 의존하지 않는다. 합성 테스트184개로 정상 상태·형식/관계 오류·immutability/equality·직렬화 독립성·계산 부재를 검증했다.

IMPLEMENTED: Binding 단위/Coverage 단위 private findings 값 모델.
NOT IMPLEMENTED: 실제 integration gate·Context target/지문 준비/Review 조립·gap 승격·CoverageResult/FULL·SLICE·최종 Coverage validator·Acceptance/Bridge. 상세 계약·검증은 COVERAGE_INTEGRATION_GATE_SPEC.md39절이다.

다음 판단은 **READY_TO_IMPLEMENT_COVERAGE_INTEGRATION_GATE**다. 다음 가장 작은 작업은 기존 계산/helper와 이 값 모델을 잇는 private integration 함수 및 합성 통합 테스트다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 45. M2.36 — IMPLEMENTED: Integration findings 수집 경로

```text
exact Coverage + exact Policy + 명시적 exact Context 또는 None
  → policy_data/coverage_integration.py
     _collect_coverage_integration_findings(coverage, policy, review_context)
  → 입력 타입 검사
  → 기존 structure 분석 1회: M / canonical 원본 pairs / U
  → 기존 composition 분석 1회: G
  → M empty + G positive이면 COVERAGE_COMPOSITION_GAP
  → Context target policy → scope (None이면 생략)
  → Inventory fp 1회 → Tree fp 1회 → 각 canonical subtree fp 1회
  → Inventory matcher 1회
  → canonical 각 existing Binding의 Implementation matcher
  → 모든 matcher 성공 후 기존 Binding findings tuple 생성
  → 기존 _CoverageIntegrationFindings 생성/반환
```

API 인자 3개는 모두 필수이며 위치/키워드 전달을 허용한다. 최신 M2.36 지시를 우선하여 integration 명세13절의 과거 keyword-only Context 후보를 대체했다. public export·옵션·새 모델·기존 helper/모델 변경은 없다.

원본 resolved pairs를 재정렬/재조회하지 않는다. root/소유 범위/미매핑/ANY·NOT 로직은 기존 helper만 사용한다. local row의 원본 root와 subtree 지문을 같은 Binding의 matcher에 연결하며 findings에는 root를 저장하지 않는다. 현재 지문은 matcher 전 전부 준비하고 MATCHED/MISSING/STALE을 그대로 보존한다. 정상 STALE/MISSING은 후속 slot 검사를 멈추지 않는다.

입력 → structure → composition 승격 → Context → 지문 → Inventory slot → canonical Implementation slots 오류 우선순위를 고정했다. 기존 PolicyDataError는 같은 객체로 전파한다. missing이 있으면 U/G를 정상 facts로 보존하고 missing이 없을 때 U 오류는 structure가, G 오류는 integration이 담당한다. G 오류 payload는 count/첫 pre-order ID 두 필드의 고정 JSON이다. findings의 로컬 validation에 의미 오류 승격을 떠넘기지 않는다.

Context None은 정상이고 target을 확인할 때는 explicit ref 미선언/zero Binding이어도 policy/scope를 대조한다. zero Binding이면 Implementation 지문/매칭/findings는 0개이며 Inventory/Tree 지문과 Inventory matcher는 실행한다. 누락 condition의 가짜 match를 생성하지 않는다. 명시 review_ref를 사용하며 reviewed_at/현재 시각/최신 기록 선택에 의존하지 않는다.

합성 통합 테스트107개로 phase 순서/호출 횟수·원본 pairs와 root identity·지문 대응·정상 상태·오류 우선/전파·조건부 gap 승격·all/any/not 모양·100회 결정성·Binding/Review 순열·입력 무변경을 검증했다. 실제 기간 계산/자료를 사용하지 않았다. 상세 API·오류·검증 기록은 COVERAGE_INTEGRATION_GATE_SPEC.md40절이다.

IMPLEMENTED: Integration findings collection gate·Context target 검증·조건부 composition 승격·현재 지문/Review 조립.
NOT IMPLEMENTED: CoverageResult·FULL_POLICY·CONDITION_SLICE·Policy verification·최종 Coverage validator·Acceptance/Bridge·Cashflow 연결·사용자 facts 평가·actual Integration Findings. 외부 I/O/시각/env/cache는 없다.

최종 판단은 **READY_FOR_COVERAGE_RESULT_DESIGN**이다. 다음 가장 작은 작업은 CoverageResult의 최소 값/identity와 FULL_POLICY/CONDITION_SLICE 파생 계약을 문서로 설계하는 것이다. 아직 status 코드를 구현하지 않는다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 46. M2.38 — IMPLEMENTED: 원본 대응을 검증하는 Result 값 경로

```text
원본 exact Coverage / Policy / Context 또는 None
  + 이미 계산된 exact _CoverageIntegrationFindings
  → policy_data/eligibility_coverage_result.py
     _create_eligibility_coverage_result (private)
  → 전체 exact 입력 → Coverage/Policy identity → Context policy/scope
  → Inventory 순서의 missing tuple 일치
  → canonical Binding과 finding의 condition/root/review_ref triple 일치
  → Inventory completeness review_ref 일치
  → 원본 identity/current baseline 추출 + 비공개 sentinel 전달
  → EligibilityCoverageResult의 로컬 형식/관계 검증
  → frozen/slots 8필드 값 + read-only status + 9key to_dict
```

Status/Result 두 타입은 policy_data public export에 추가했다. factory·findings·sentinel은 export하지 않는다. token은 keyword-only InitVar이며 저장 필드가 아니다. 올바른 token 없는 일반 생성·status 입력·dataclasses.replace를 거부한다. 최신 M2.38 권장안에 따라 M2.37의 init=False 후보를 이 방식으로 대체했으며 외부 caller의 수동 FULL을 허용하는 공개 생성 API는 없다.

missing/Implementation 목록은 개수만 비교하지 않고 원본 condition/root/ref 전체 tuple을 대조한다. 일부 Binding의 finding 누락·추가·다른 root/ref·잘못된 missing은 Data Error다. baseline은 모두 None 또는 모두 present이며 현재 matcher의 정상 Review 조합과 일치해야 한다. Full에는 M/U/G empty·모든 Review MATCHED·nonempty Implementation findings·present baseline을 요구한다. 별도 slice reason/status 저장값·사용자 평가·승인 상태는 없다.

**기존 Integration Gate와 이 factory는 아직 자동 연결하지 않았다.** factory/model은 gate/지문/matcher/structure/composition을 호출하지 않는다. 이미 성공한 gate findings를 같은 원본과 공급받는 전제이며 계산/외부 검토 진실성을 새로 인증하지 않는다. synthetic literal 지문과 수동 match fixture는 모델 검증에만 사용했고 실제 자료/승인 기록은 만들지 않았다.

합성 테스트226개 및 전체5620개가 통과했다. strict 입력·정확한 대응/partition·생성 제한·정상 상태·모순 오류·8fields/9keys·동결·mutation isolation·100회/Binding 순열·재계산/하위 생성자 재실행 부재를 검증했다. 현재4함수의 의존만 검사하여 같은 모듈의 미래 독립 함수/import 추가를 금지하지 않는다. 상세 계약·검증은 ELIGIBILITY_COVERAGE_RESULT_SPEC.md36절이다.

IMPLEMENTED: EligibilityCoverageStatus·EligibilityCoverageResult·internal validated creation path·derived status·deterministic serialization.
NOT IMPLEMENTED: public evaluate_eligibility_coverage·automatic Integration Gate connection·Verification·Acceptance·Benefit Bridge·Cashflow 연결·actual Ansan Result.

최종 판단은 **READY_TO_IMPLEMENT_FINAL_COVERAGE_EVALUATOR**다. 다음 가장 작은 작업은 public pure evaluator 하나에서 기존 gate1회 → private factory1회만 연결하고 합성 통합 테스트를 추가하는 것이다. actual releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**는 유지한다.

## 47. M2.39 — IMPLEMENTED: Eligibility Coverage 공식 public pure API

```text
evaluate_eligibility_coverage(coverage, policy, review_context=None)
  → 기존 _collect_coverage_integration_findings 1회
     구조 → composition → Context → 현재 지문 → Review matching
  → 원본 findings로 기존 _create_eligibility_coverage_result 1회
     원본 대응 → identity/baseline → 불변 Result
  → 원본 EligibilityCoverageResult 반환 (status는 기존 property)
```

새 eligibility_coverage_evaluator.py의 함수 하나와 public export만 추가했다. wrapper는 별도 입력/type 검사·missing/구조/지문/Review/correspondence/status 계산·직접 Result 생성·findings 변경·catch/retry를 하지 않는다. Gate 실패면 factory0회이며 양쪽 오류를 그대로 전파한다. 새 의미/옵션/모델/helper framework는 없다.

실제 합성 current 지문·Review records를 사용한 end-to-end67개 테스트로 FULL/SLICE·Context omitted/None·누락/미선언/STALE·ANY/NOT·정상 U/G·기존 구조/참조/동일 version conflict를 검증했다. 호출 횟수·원본 인자/findings/Result identity·하위 계산1회·오류 동일 객체·100회 결정성·Binding/Review 순열·입력 무변경·9key 직렬화도 확인했다. 기존 Result/gate/helpers/model/test는 변경하지 않았다. 전체5687개 통과다.

외부 caller는 policy_data.evaluate_eligibility_coverage를 사용한다. private Gate/factory/findings/sentinel을 public export하지 않으며 Result의 일반 생성 제한·파생 status도 유지한다. FULL은 자격조건 coverage만 뜻하고 user eligibility/행정 승인/VERIFIED/Acceptance와 독립이다. pure API는 시스템 시간·환경·파일·네트워크·DB·가변 전역을 사용하지 않는다.

IMPLEMENTED: 공개 evaluator·Gate1회→factory1회 공식 연결. NOT IMPLEMENTED: Policy verification·Benefit Acceptance·Benefit Bridge/Cashflow·실제 안산 FULL/정책자료 발행. 상세 검증·한계·변경 기록은 ELIGIBILITY_COVERAGE_RESULT_SPEC.md37절이다.

최종 판단은 **ELIGIBILITY_COVERAGE_CORE_COMPLETE**다. 다음 가장 작은 작업은 현재 공개 API/오류/identity/신뢰 경계와 회귀 기준을 짧게 audit해 freeze 기록 한 문서로 남기는 것이다. 실제 안산은 DRAFT/CONDITION_SLICE이며 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**는 계속 보류한다.

## 48. M2.43 — IMPLEMENTED: 혜택 정의의 불변 값 경로

```text
명시16개 keyword-only 값 + 기존 exact Scope/SourceBinding
  → policy_data/benefit_snapshot.py: BenefitSnapshot
  → 필드 순서의 exact 타입/문법·월/binding 유일/순서 검사
  → amount → restriction → cash medium 모순 → ONE_TIME 월 → evidence/source 집합 대응
  → frozen/slots 정의 값
  → to_dict: 저장16key의 새 nested primitive snapshot
```

4개 Benefit Enum과 모델만 같은 새 모듈에 두고 public export에 추가했다. 기존 policy_data의 다른 export/Coverage 구현·동결 의미는 유지했다. SourceBinding/Scope/parse_evidence_ref를 재사용하며 원본 nested 객체·입력 tuple·문자열을 보존한다. source Registry/Manifest/원문은 조회하지 않는다. 기존 ID grammar를 같은 작은 식으로 검사하고 model 오류는 INVALID_BENEFIT_SNAPSHOT PolicyDataError, ref parser 오류는 기존 객체 그대로 전달한다.

모델은 구조 유효성만 보장한다. VARIABLE/UNKNOWN·월 미정의를 허용하고 Acceptance completeness·공식 검토·Bridge support·지문을 계산하지 않는다. 동작의 직접 의존에 fingerprint/Acceptance/Bridge/Cashflow·시각·I/O를 추가하지 않았다. 일반 serializer는 지문 payload/loader가 아니며 source binding 두 필드도 새 dict로 명시한다.

합성292개 테스트로 명세 필드/Enum reflection·타입·경계/교차 규칙·정상 부분 정의·오류 우선/전파·입력 불변성·100회 결정성·직렬화 mutation isolation을 검증했다. 기존5687개를 포함해 전체5979개가 통과했다. BV 지문 실행 tests는 아직 없다.

**IMPLEMENTED:** BenefitSnapshot/4개 Enum/strict 구조 검증·16key 값 표현.

**NOT IMPLEMENTED:** Benefit fingerprint·Acceptance record/evaluator·review artifact resolution·Bridge·Cashflow 연결·실제 Ansan Benefit 정의/금액/지문. 다음 가장 작은 작업은 승인 후 별도 전용 지문 함수 하나와 BV01~BV16 literal 검증이다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, Coverage core freeze는 유지한다.

## 49. M2.44 — IMPLEMENTED: Benefit 정의의 전용 지문

```text
exact BenefitSnapshot
  → benefit_fingerprint.py: fingerprint_benefit_snapshot(snapshot)
  → private 명시15key projection
  → canonical JSON / strict UTF-8
  → SHA256 lowercase hex64
```

policy_data public export에 함수 하나만 추가했다. payload에는 definition identity/version·금액/주기/수단/제한·월·evidence·관련 source bindings를 넣는다. dataset_version과 Registry 전체 지문은 외부 provenance binding으로 남기며 일반16key serializer를 hash하지 않는다. 같은 provenance 변화가 모델 값은 바꾸지만 정의 지문은 유지할 수 있다. evidence/월/binding 순서·중복·null·원래 문자열은 보존한다.

동결 Coverage private helper를 공유하기 위해 수정/이동하지 않았다. 별도 모듈에서 동일 표준 json/hashlib recipe를 사용하고, exact 입력 오류·JSON/UTF-8 인코딩 오류는 PolicyDataError다. Snapshot의 필드/Enum/생성/serializer는 바꾸지 않았다. 함수는 입력을 재검증/재생성하거나 source/Review/시간/환경/I/O를 조회하지 않는다.

BV01~BV16 literal payload/JSON/UTF-8 byte length/digest가 모두 일치했다. 신규74개와 기존5979개를 합쳐 전체6053개 테스트가 통과했다. provenance 제외·definition 변화·Unicode/인코딩 오류·불변성·100회 결정성·serializer/Registry 미사용도 검증했다. 상세 기록은 BENEFIT_SNAPSHOT_SPEC.md37절이다.

**IMPLEMENTED:** 전용 Benefit 지문 함수와 BV 실행 golden tests.

**NOT IMPLEMENTED:** BenefitAcceptance/status/evaluator·review resolution·Benefit Bridge·Cashflow 연결·실제 안산 Benefit 자료/지문/금액. 다음 가장 작은 작업은 수용 record 최소 필드/binding/기한·철회 계약을 문서로 확정하는 것이다. 실제 정책은 slice/DRAFT, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, Coverage core freeze는 유지한다.

## 50. M2.46 — IMPLEMENTED: 과거 Acceptance 결정의 구조 값

```text
명시21개 keyword-only 값 + 기존 exact Scope/date
  → benefit_acceptance.py: PolicyBenefitAcceptance
  → 필드 순서의 exact 타입/문법 검사
  → 날짜 순서 → 같은 dataset → 같은 Registry → status/link → self-link 검사
  → frozen/slots 결정 기록
  → to_dict: 저장21key의 새 Scope dict·ISO 날짜·canonical 상태·명시 null
```

동일 모듈의 BenefitAcceptanceStatus와 PolicyBenefitAcceptance 두 타입만 public export에 추가했다. 직접 의존은 dataclasses/datetime.date/enum/re·기존 PolicyDataError/ApplicabilityScope다. 버전/ID/지문은 기존 문법과 같은 작은 구조 검사이며 기존 private validator를 추출하기 위해 frozen 코드를 수정하지 않았다.

constructor는 현재 자료/시각이나 다른 기록을 받지 않는다. Coverage evaluator·Benefit fingerprint·Policy verification·artifact lookup·Context resolution·Bridge/Cashflow를 import/호출하지 않는다. 전체 CoverageResult/BenefitSnapshot은 저장하지 않으며 supplied identity만 보존한다. 일반 constructor 성공은 외부 검토·승인 사실의 인증이 아니다.

acceptance_ref와 a revision은 별개다. REVOKED의 명시 ref는 자기 자신만 로컬 거부하고 실제 target 존재·ACCEPTED 상태·동일 target/binding·revision/검토일 관계는 다음 Context 계약으로 남긴다. valid_until의 경과로 철회가 해제되거나 과거 승인이 자동 선택되는 경로는 없다. 현재 usable/stale/expired·결과 reason/월 금액도 계산하지 않는다.

합성 모델472개 및 기존6053개를 포함해 전체6525개 테스트가 통과했다.21필드/2상태·strict 구조·local invariant·불변성·equality·21key 직렬화와100회 mutation isolation/결정성·외부 계산 부재를 확인했다. 상세 계약/검증은 BENEFIT_ACCEPTANCE_RECORD_SPEC.md37절이다.

**IMPLEMENTED:** BenefitAcceptanceStatus·PolicyBenefitAcceptance.

**NOT IMPLEMENTED:** AcceptanceContext·ref resolution·current evaluation result/evaluator·verification integration·Benefit Bridge·Cashflow 연결·actual Acceptance.

최종 판단은 **READY_FOR_ACCEPTANCE_CONTEXT_DESIGN**다. 다음 가장 작은 작업은 bounded immutable Context/명시 선택·철회 연결 계약의 문서 설계 한 개다. 자동 최신 선택/새 evaluator로 확장하지 않는다. Coverage core freeze와 BenefitSnapshot/지문 계약은 유지하며 실제 안산 DRAFT/CONDITION_SLICE·반영0원 원칙, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**도 그대로다.

## 51. M2.48 — IMPLEMENTED: 한 target의 이력과 명시 조회

```text
명시 target3값 + exact historical records tuple
  → benefit_acceptance_context.py: BenefitAcceptanceContext
  →14phase: 필드/원소 → target → ref/version 유일성
     → 모든 철회 대상 존재 → ACCEPTED 상태 →11개 binding
     → 직접 철회 유일성 → 수치 revision 순서 → 검토일 순서
  → frozen/slots 4필드 값, local index/set/edges는 저장하지 않음

exact Context + 명시 비공백 ref
  → benefit_acceptance_resolution.py: _resolve_benefit_acceptance
  → exact 원문 ref equality로 선형 조회
  → 원본 record 반환 또는 ACCEPTANCE_REF_NOT_FOUND
```

모델과 resolver는 기존 Review 모듈 패턴처럼 별도 파일에 두었다. policy_data public export에는 Context 한 타입만 추가했다. 직접 의존은 dataclasses/re·기존 PolicyDataError/ApplicabilityScope/Acceptance 타입뿐이며 private 조회는 Context/record/기존 오류만 사용한다. source/fingerprint/verification/evaluator·Bridge/Cashflow·파일/환경/네트워크/Git/시각을 조회하지 않는다.

입력 순서·객체 identity를 유지하고 B가 A 앞에 있어도 전체 ref index로 edge를 검증한다. version은 검증된 a suffix의 길이/문자열로 비교하여 a9999<a10000·매우 긴 revision을 int 변환 없이 처리한다. 전역 날짜 정렬·latest/max version 선택·기한 간 새 제약·generic graph/cache는 없다. 오류는11개 승인 prefix의 PolicyDataError이며 부분 Context나 정상 부재로 강등하지 않는다.

resolver는 Context를 재검증하지 않고 명시 ref의 과거 A/B/C를 각각 그대로 반환한다. B가 A를 철회했다고 A의 status/반환 대상을 바꾸지 않는다. **과거 A 조회 성공은 현재 사용 승인·현재 철회 효과의 판정이 아니다.** no-selection/명시 날짜 해석·이력 누락 완전성은 후속 evaluation 계약이다.

합성200개와 기존6525개를 합쳐 전체6725개 테스트가 통과했다. strict4필드·두 유일성·역사 공존·11binding·phase 복합 오류·수치 경계·원본 반환·100회/순열·4key mutation isolation·재검증/외부 계산 부재를 확인했다. AC01~AC120의 실제 구조/조회 검증과 미래 평가 범위의 구별은 BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md35절에 기록했다.

**IMPLEMENTED:** 불변 Context·철회 연결 구조 검증·명시 private resolver.

**NOT IMPLEMENTED:** current Acceptance evaluation result/evaluator·선택한 과거 승인의 현재 철회 효과·만료/stale·no-selection·verification integration·Bridge/Cashflow·실제 Context/승인.

최종 판단은 **READY_FOR_ACCEPTANCE_EVALUATION_RESULT_DESIGN**다. 다음 최소 작업은 평가 결과와 선택/철회 효과의 문서 계약 설계 한 개다. 기존21필드 record·BenefitSnapshot/지문·frozen Coverage는 그대로이며 실제 안산 DRAFT/CONDITION_SLICE·반영0원 원칙, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 52. M2.50 — IMPLEMENTED: 평가 결과의 구조 값

```text
명시9개 keyword-only 합성/이미 계산된 값
  → benefit_acceptance_evaluation_result.py의 private factory
  → private token InitVar + 원본9개 값을 생성자1회에 전달
  → 필드 → reasons 순서/중복 → 선택 metadata → 미선택/선택
     → 철회 근거/ref/사유 관계 → 배타 기한 사유 검사
  → frozen/slots BenefitAcceptanceEvaluation9필드
  → reasons empty/nonempty에서 read-only USABLE/UNUSABLE 파생
  → 저장9key + 마지막 status의10key serializer
```

새 모듈 하나에 Result/Status/Reason과 최소 로컬 helper만 두었다. 직접 의존은 dataclasses/datetime.date/enum/re·기존 PolicyDataError/ApplicabilityScope/BenefitAcceptanceStatus다. 생성 제한은 새 모듈 안의 token으로 분리했으며 frozen Coverage의 helper/토큰/코드를 수정하거나 가져오지 않았다. package public export도 바꾸지 않았다.

private factory는 Context/record/현재 자료를 받지 않고 gate를 재실행하지 않는다. 모델은9필드 간 모순을 거부하고 파생 status만 표현한다. 일반 생성/replace는 제한하되 private 접근·강제 조작 방지나 실제 평가 성공/발급 권한 인증은 아니다. 실제 evaluator가 모든 gate 성공 후 정상 factory 경로를 연결해야 한다.

이 결과는 원본과 같은 호출에서만 사용하는 내부 값이다. 실제 snapshot/Context를 복제하거나 fingerprint를 저장하지 않는다. 후속 adapter는 미리 계산된 Result/JSON을 외부 입력으로 받지 않고 같은 원본으로 새 평가와 candidate 생성을 결합해야 한다. 이 adapter·재사용 차단 기능은 아직 없다.

합성237개와 기존6725개를 포함해 전체6962개 테스트가 통과했다. strict9필드/InitVar·2상태/12사유·선택/철회/기한 로컬 관계·factory 제한/전달·오류 우선·동결/equality·10key/100회 출력 격리를 확인했다. 현재 함수의 실행 의존만 검사했으며 미래 별도 함수/모듈을 일괄 금지하지 않는다. AE 모델 사례와 후속 evaluator/adapter/운영 범위 구분은 BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md29절이다.

**IMPLEMENTED:** 내부 평가 결과9필드·Enum·로컬 검증·파생 status·표시용 serializer.

**NOT IMPLEMENTED:** 실제 evaluator·related revocation 검색/효과·기한/현재 gate·verification/Manifest/Registry/artifact·지문 비교·adapter/Bridge/Cashflow·실제 안산 결과.

최종 판단은 **READY_FOR_ACCEPTANCE_EVALUATOR_CONTRACT_DESIGN**다. 다음 최소 작업은 정확한 evaluator 입력/전체 release/근거 사용 gate·artifact 대응·동일 호출 결합 계약의 문서 설계 한 개다. 실제 안산 DRAFT/CONDITION_SLICE·반영0원 원칙, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, Coverage 동결 상태와 Benefit/record/Context 기존 계약은 유지한다.

## 53. M2.53 — IMPLEMENTED: 외부 bootstrap의 합성 verify-only

```text
명시 Python 새 subprocess: -I -S -B -X utf8
  → tools/artifacts/bootstrap.py (backend 밖의 trusted 표준 라이브러리 script)
  → flags/Windows·기대 SHA/절대 경로·backend 사전 로드 부재
  → CreateFileW: GENERIC_READ + FILE_SHARE_READ + OPEN_EXISTING, handle 유지
  → 같은 보호 ZIP 원본 bytes SHA256 대 외부 합성 기대값
  → source ZIP 구조/profile·내부 bootstrap 사본 equality
  → 명시 Python executable/base·선언 환경·허용 stdlib 경로
  → 같은 ZIP에서 inventory 전체 backend 모듈 eager import
  → 모듈/패키지/loader/archive/origin/검색 경로·함수 origin·집합 대응
  → 동일 파일/bytes·flags/출처 재대조
  → 범위/예상수/확인수/전체 확인모듈의5key JSON, 종료0
  → handle 정리, 검증 수명 종료
```

새 실행 준비 코드는 backend/policy_engine·Coverage/Acceptance/Cashflow를 import하거나 변경하지 않는다. ZIP 안 bootstrap.py를 먼저 실행하지 않으며 외부 script와 bytes equality만 확인한다. 검증된 ZIP backend는 hash/구조/환경 통과 뒤에만 import한다. 업무 evaluator나 금액 계산 entrypoint를 호출하지 않는다. 순수 API에 I/O를 추가하지 않았다.

현재 CLI는 --verify-only, --bundle, --expected-sha256, --python-executable, --python-base를 모두 명시한다. --manifest/full release·다른 artifact·verified/skip/allow-stale 우회 경로는 없다. 환경 선언6필드는 M2.52 그대로이며 actual 값으로 기대값을 교체하지 않는다. 실패는 기존 설계 prefix/field를 stderr에 출력하고 종료2다. raw traceback/payload/부분 성공 Result를 반환하지 않는다.

`tests/test_artifact_bootstrap.py`의 ZIP은 tmp의 synthetic/test-only 최소 package다. 기본 명시5개 모듈과 nested/간접 import를 사용하고 실제 backend61개를 패키징하지 않는다. 독립 unit 검사와 새 subprocess/native 검사를 구분한다. hash 실패 전 marker 부재, 오염/누락/늦은 실패/전체 inventory, 실제 Windows 공유 제한·다른 프로세스의 변경 차단 및 정상/오류/timeout/kill 종료 뒤 해제를 검증한다. 동기화는 파이프/queue로 수행한다.

M2.52 공유 artifact 규칙과 M2.51 전체 release/8개 내부 입력의 책임 경계를 유지한다. 이번 결과는 다른 프로세스/종료 뒤 사용 가능한 승인 token이 아니다. actual worker의 Manifest/source/review 준비·Coverage/Acceptance·same-call candidate·Bridge 연결은 미구현이다. 상세 CLI·오류·AR 대응·실행 검증 이력은 RELEASE_ARTIFACT_EXECUTION_BINDING_SPEC.md26절을 따른다.

최종 판단: **SYNTHETIC_ARTIFACT_VERIFY_ONLY_COMPLETE**. 다음 최소 작업은 **Acceptance 검토 artifact의 구조화된 원본 대응 계약 문서 설계 한 개**다. Generic Coverage/지문/GV·Benefit/BV·기존 도메인/테스트/fixture와 실제 release6개를 보존하며 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

검증: 사전6962개, 신규 합성106개, 최종 전체 **7068 passed in 67.01s / skipped0 / failed0**. 실제 Windows/CPython3.12.14 subprocess와 native 공유 모드를 실행했다. 기존 source/test/fixture/기대값·동결 명세·GV/BV·루트 설정4개·실제 release6개의 SHA256을 보존했고 변경은 새 bootstrap/테스트2개와 승인 문서2개뿐이다. 실제 backend 배포 artifact/엔진 hash·Manifest·승인 기록·정책 금액은 만들지 않았다.

## 54. M2.55 — IMPLEMENTED: Review Artifact 구조 계층

```text
명시된 기존 Acceptance / SourceBinding / ArtifactReference 객체
  → BenefitReviewClaim(5member)
  → ClaimEvidenceMapping2 / ReviewSourceOriginal2
  → AcceptanceReviewEntry15 (ACCEPTED/REVOKED 로컬 조합)
  → AcceptanceReviewArtifact2 (content-addressed 문법·명시 entry 유일성/외부 ref 대응)
  → 새 primitive 진단 dict/list
```

새 모듈 하나와 합성 테스트 하나를 추가하고 Enum+4개 값 타입만 package public export했다. 모든 모델은 frozen/slots/keyword-only·정확한 타입·명시 필수 인자·순서 보존·값 equality다. evidence 문법은 기존 pure parse_evidence_ref를 재사용하고 Registry는 조회하지 않는다. 기존 SourceBinding/ArtifactReference에는 serializer가 없어 명시2key 새 dict로 표현하며 기존 Acceptance serializer는 그대로 재사용한다.

ACCEPTED는 원본 참조7개·정확한5claim·source binding/원문 참조 목록과 검토 handle/이유/사례를 표현한다. REVOKED는 승인표를 복제하지 않고 기존 record의 revokes_acceptance_ref·검토 사유를 보존한다. Context resolver나 철회 target/11binding 계산은 실행하지 않는다. 원본 tuple/nested 객체를 재생성·수정하지 않는다.

구조 생성 성공은 외부 bytes 확보·hash/원본 대응·공식 내용 검토·검토자 권한·현재 USABLE을 뜻하지 않는다. 진단 serializer는 entry.acceptance21key와 root 외부 ref를 포함하며 hash 대상 raw20key projection이 아니다. 자기 hash/ref 갱신·파일 출력·raw loader를 추가하지 않았다.

**IMPLEMENTED:** Enum·4개 불변 값 모델·로컬 구조 검증·진단 serializer. **NOT IMPLEMENTED:** artifact loader/bytes integrity·external evidence resolution·source usage gate·content verification·Acceptance evaluator·same-call adapter·Benefit Bridge/Cashflow 연결. 후속 A/C와8-input B의 분리 계약은 그대로다.

실제 실행 코드 artifact는 생성하지 않았다. backend source가 늘었지만 과거 M2.52/M2.53의61개/합성5개 기록을 새 실제 release 검증이라고 바꾸지 않는다. 향후 새 실제 bundle은 그때의 전체 backend inventory로 새 bytes/hash를 만들고 재검토해야 한다. 기존 bootstrap/프로파일·frozen Coverage·지문/GV/BV·실제 release6개는 변경하지 않는다.

상세 계약/검증은 BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md30절이다. 다음 최소 작업은 **Review Artifact strict loader 계약 설계 한 개**다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, 정책 혜택 Cashflow 반영0원 원칙을 유지한다.

## 55. M2.57 — IMPLEMENTED: 순수 Review Artifact bytes loader

```text
raw_bytes + 외부 expected_acceptances 원본 tuple (필수 keyword-only)
  → exact 입력/공통 content-addressed ref/expected 유일성
  → 공급된 동일 raw bytes 전체 SHA256, 일치해야 decode
  → BOM 거부/strict UTF-8/JSON duplicate·number·Unicode scalar
  → root2/entry15/raw Acceptance20/nested exact schema 전체 검사
  → C1 canonical bytes와 원본 equality
  → 기존21필드 Acceptance + Review 모델4개 구조 복원
  → 전체 entry 집합 및20값 대응 → 각 acceptance를 공급 원본 객체로 결합
  → 불변 AcceptanceReviewArtifact
```

새 loader 모듈과 합성 테스트를 추가하고 loader 한 함수만 public export했다. 최소 private helpers는 이 계약에 한정하며 일반 Artifact DB/스토리지·새 domain/예외 모델을 추가하지 않았다. 실제 API/필드/오류 순서는 BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC.md3·18~19·28절을 따른다.

기존 constructor의 exact 타입·same-release·날짜/status·claim/순서/중복·source 목록·root invariant를 재사용한다. external ref를 임시21필드에 결합하지만 새 승인으로 발급하지 않으며 최종 entry에는 외부 원본을 is로 보존한다. raw 순서를 유지하고 first/latest selection·자동 sort/dedupe·누락 원본 합성을 하지 않는다.

진단 to_dict는 외부 raw format이 아니며 기존 serializer 의미를 변경하지 않았다. canonical 표현은 해시 대체물이 아니라 별도 bytes equality 검사다. SHA가 일치해도 source/locator·당시 Snapshot·공식 원문·검토 권한·FULL/VERIFIED/current USABLE은 확인하지 않는다. loader는 I/O/환경변수/시각/전역 mutable cache·Coverage/Benefit 계산을 사용하지 않는다.

**IMPLEMENTED:** strict bytes integrity/schema/C1·raw20 재구성·외부 원본 대응·합성 테스트. **NOT IMPLEMENTED:** 외부 파일 preparation·historical content validator·Source Gate·사람 검토 인증·Acceptance evaluator·same-call adapter·Benefit Bridge/Cashflow 연결. 기존8-input B와 동일 호출 A/C 책임은 유지한다.

기존 값 모델·동결 Coverage/GV/BV·bootstrap·Cashflow·실제 release6개는 변경하지 않는다. 실행 source ZIP/실제 Acceptance/정책 금액도 생성하지 않았다. 다음 최소 작업은 **Review Artifact content validator 계약 설계 한 개**다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

## 56. M2.60 — IMPLEMENTED: Historical BenefitSnapshot bytes loader

```text
같은 호출의 M2.57 Artifact + 외부 Acceptance 원본 R + exact raw bytes
  → ACCEPTED/root ref/명시 entry 조회/entry.acceptance is R
  → selected accepted_terms_ref.sha256 대 동일 raw bytes 전체 SHA
  → strict UTF-8/JSON·duplicate/number/Unicode scalar
  → 버전 wrapper2 + 기존 Snapshot16·nested scope2/binding2 + HB1 canonical bytes
  → 기존 Scope/Enum/SourceBinding/BenefitSnapshot constructor
  → 기존 Benefit 지문 함수1회
  → policy/scope/benefit/version·definition fp·dataset·Registry 각각 대조
  → 불변 BenefitSnapshot 반환
```

새 `policy_data/historical_benefit_snapshot_loader.py`와 합성 테스트를 추가하고 package public 함수 `load_historical_benefit_snapshot_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> BenefitSnapshot` 하나를 export했다. 입력3개는 필수 keyword-only이며 우회 옵션은 없다. 기존 모델의 저장 필드/serializer/정의15key·golden 지문은 변경하지 않았다.

실제20개 오류 prefix/P0~P8 순서·raw schema/HB1·검증 결과는 HISTORICAL_BENEFIT_SNAPSHOT_ARTIFACT_PREPARATION_SPEC.md19·26절을 따른다. Data Error는 정상 미검토/STALE/UNUSABLE로 바꾸지 않는다. 여러 Entry 중 명시 원본을 선택하며 duplicate/ref 누락은 기존 모델에서 생성 자체가 거부됨을 정상 객체 생성 테스트로 확인한다. frozen 객체 강제 변조는 없다.

구조적으로 유효한 VARIABLE/UNKNOWN/월 None·비현금 정의는 복원할 수 있으나 승인 적정성/공식 내용 검토/current USABLE/Bridge 지원은 계산하지 않는다. 후속 Content Validator의 metadata completeness 책임은 그대로다. raw SHA와 definition fp/provenance를 각각 대조하며 actual digest를 기대값으로 채택하지 않는다. 파일/Registry/환경/시각을 조회하지 않고, 외부 완성 Snapshot을 받거나 현재 Benefit으로 대체하지 않는다.

**IMPLEMENTED:** Historical BenefitSnapshot strict bytes 복원·기존 정의 fp 재계산/비교·Acceptance identity/version/provenance binding·합성 실행 테스트.

**NOT IMPLEMENTED:** 외부 file preparation·Coverage/ReviewContext/Manifest 역사 codecs·Content Validator·Source Gate·Acceptance evaluator·same-call adapter·Benefit Bridge/Cashflow 연결·실제 정책 원본/금액/승인.

same-call trusted A/C의 실제 M2.57 실행·파일 확보 책임은 외부에 남는다. root 타입/is만으로 검토 진실성·실제 loader 통과를 인증하지 않는다. 다음 최소 작업은 **Historical EligibilityCoverage Artifact Preparation Contract 문서 설계 한 개**다. 전체 validator 준비 완료로 확대하지 않는다. Coverage freeze/기존 GV·BV·bootstrap/Cashflow·실제 releases는 유지하며 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

검증: 사전 **7,673 passed in 62.77s**, 신규 합성 **294 passed in 1.52s**, 최종 전체 **7,967 passed in 70.55s / skipped0 / failed0 / timeout0**. 기존 테스트/fixture/기대값·golden·동결 core/문서·모델·기존 loader·bootstrap/Cashflow와 실제 release6개 SHA256을 보존했다. 변경은 새 코드/테스트2개와 package export·관련 문서2개뿐이다. 최종 판단은 **HISTORICAL_BENEFIT_SNAPSHOT_LOADER_COMPLETE**다.

## 57. M2.62 — IMPLEMENTED: Historical EligibilityCoverage bytes loader

```text
exact raw bytes + 같은 호출의 실제 M2.57 Artifact + 외부 Acceptance R 원본
  → ACCEPTED/root ref/명시 유일 Entry/entry.acceptance is R
  → selected coverage_snapshot_ref.sha256 대 동일 raw bytes 전체 SHA
  → strict UTF-8/JSON·duplicate/number/Unicode
  → wrapper2/coverage2/inventory5/scope2/condition4/binding3·HC1 canonical bytes
  → 기존 Scope/Requirement/Condition/Inventory/Binding/Coverage 생성자
  → 기존 Inventory 지문 함수1회
  → policy/scope/inventory_version/실제 Inventory fp 각각 대조
  → 불변 EligibilityCoverage 입력 반환 (Result/status 없음)
```

새 `policy_data/historical_eligibility_coverage_loader.py`와 합성 테스트를 추가하고 `load_historical_eligibility_coverage_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> EligibilityCoverage` 하나를 public export했다.3개 인자는 필수 keyword-only이고 옵션은 없다. 기존 Benefit historical loader의 공통화/refactor나 domain 저장 필드/serializer/지문 변경은 없다.

19개 오류 prefix/P0~P9·raw schema/HC1·합성 검증 기록은 HISTORICAL_ELIGIBILITY_COVERAGE_ARTIFACT_PREPARATION_SPEC.md20·30절을 따른다. raw SHA는 Binding/completeness ref까지 고정하고 기존 Inventory 지문은 계속 그 값들을 제외한다. 정상 Binding 누락/빈 tuple·completeness ref None은 허용하며 구조 모순을 정상 상태로 낮추지 않는다. 모든 배열의 원순서·evidence 중복을 보존한다.

**IMPLEMENTED:** Historical Coverage strict bytes 복원·기존 Inventory 지문 재계산/비교·Acceptance Inventory identity/version/fp binding·합성 실행 테스트.

**NOT IMPLEMENTED:** 당시 Policy Tree/ReviewContext/Manifest loader·Historical FULL replay·외부 파일 준비·Content Validator·Source Gate·Acceptance evaluator·Bridge/Cashflow·실제 안산 Coverage/Acceptance/FULL Result.

Tree/Review/Manifest/implementation provenance는 입력에 없어 검증 완료로 보고하지 않는다. FULL/VERIFIED/현재 USABLE은 만들지 않으며 Coverage evaluator/Result factory/Review matching/Tree 지문/ZIP을 실행하지 않는다. 다음 최소 작업은 **Historical PolicyEnvelope / Rule Tree Artifact Preparation Contract 문서 설계 한 개**다. 기존 parse_policy_envelope의 동일 bytes 준비 경계부터 확정한다.

Generic Coverage freeze/GV·BV·기존 모델/loader·bootstrap/Cashflow·실제 releases는 유지한다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

검증: 사전 **7,967 passed in 66.41s**, 신규 합성 **267 passed in 1.33s**, 최종 전체 **8,234 passed in 74.89s / skipped0 / failed0 / timeout0**. 기존 테스트/fixture/기대값·GV/BV·동결 Coverage 코드/문서·모델·기존 Historical Benefit/Review loaders·bootstrap/Cashflow와 실제 release6개 SHA256을 보존했다. 변경은 새 코드/테스트2개와 package export·관련 문서2개뿐이다. 최종 판단은 **HISTORICAL_ELIGIBILITY_COVERAGE_LOADER_COMPLETE**다.

## 58. M2.64 — IMPLEMENTED: Historical PolicyEnvelope Strict Bytes Loader

```text
exact raw bytes + 같은 호출의 실제 M2.57 Artifact + 외부 Acceptance R 원본
  → ACCEPTED/root ref/명시 유일 Entry/entry.acceptance is R
  → selected policy_envelope_ref.sha256 대 같은 raw bytes 전체 SHA
  → strict UTF-8/JSON·duplicate/number/Unicode
  → 기존 policy-data-1.0/m1.1 raw A shape·HP1 canonical bytes
  → 기존 parse_policy_envelope에 같은 parsed root를1회 전달
  → 반환 E.policy의 기존 Tree fingerprint를1회 계산
  → policy/edition year/rule version/actual Tree fp/dataset 독립 대조
  → 기존 불변 PolicyEnvelope 그대로 반환
```

새 `policy_data/historical_policy_envelope_loader.py`와 합성 테스트를 추가하고 `load_historical_policy_envelope_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> PolicyEnvelope` 하나를 export했다. 필수 keyword-only3개/exact 타입이며 추가 옵션은 없다. 기존 PolicyEnvelope15/Policy6/Rule 모델·parser·Tree 지문·Coverage Core·다른 historical loader를 변경하지 않았다.

기존 네 Rule 타입/FactBasis/전체 계층·자식 순서·비교값·근거·metadata와 optional 생략/null 의미를 보존한다. P5는 raw shape만 확인하고 모델 의미는 기존 parser가 검사한다.21개 prefix/P0~P9와 M2.63 계약/실제747개 합성 테스트는 HISTORICAL_POLICY_ENVELOPE_ARTIFACT_PREPARATION_SPEC.md20~21·28절을 따른다. parser/지문을 각각1회 호출하며 기존 parser 결과 객체를 그대로 반환한다.

**IMPLEMENTED:** Historical PolicyEnvelope strict bytes 복원·기존 전체 Tree parser 재사용·actual Tree 지문 비교·당시 Acceptance Policy/edition year/rule/dataset binding.

**NOT IMPLEMENTED:** Historical ReviewContext/Manifest loader·quarter scope verification·외부 파일 준비·Source Gate·Review Content Validator·Acceptance evaluator·Benefit Bridge/Cashflow·implementation ZIP 실행 대응·실제 안산 원본/Acceptance/FULL Result 생성.

Envelope의 edition에는 quarter가 없으므로2026/Q3 일치를 증명하지 않는다. DRAFT/VERIFIED/STALE 선언은 그대로 복원하고 현재 검토 gate를 통과시켰다고 주장하지 않는다. Inventory/Binding/Review/Manifest/SourceRegistry/implementation을 검증하거나 FULL/MATCHED/USABLE/PASS를 만들지 않는다. 기존 pretty-print releases는 H가 같더라도 HP1 실패이며 원본을 재작성하지 않는다.

다음 최소 작업은 **Historical CoverageReviewContext Artifact Preparation Contract 설계 한 개**다. 기존 Coverage freeze/GV·BV·모델/loader·bootstrap/Cashflow·실제 releases를 유지하며 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 최종 회귀·SHA 보존 결과는 아래 검증 종료 기록을 따른다.

검증: 사전 **8,234 passed in 73.76s**, 신규 합성 **747 passed in 2.97s**, 최종 전체 **8,981 passed in 64.76s / skipped0 / failed0 / timeout0**. 기존8,234개 테스트·fixture·기대값·GV/BV·동결 코드/문서와 기존 모델/parser/지문·Historical Benefit/Coverage/Review loader·bootstrap/Cashflow를 보존했다. SHA 기준선182개 중179개는 동일하고 export/관련 문서2개만 변경, 새 loader/합성 테스트2개를 추가했다. 실제 release6개의 SHA256·경로·크기·수정시각도 동일하다. 최종 판단은 **HISTORICAL_POLICY_ENVELOPE_LOADER_COMPLETE**다.

## 59. M2.66 — IMPLEMENTED: Historical CoverageReviewContext Strict Bytes Loader

```text
exact bytes + 같은 호출의 실제 M2.57 Artifact + 외부 R 원본
  → ACCEPTED/root ref/명시 유일 Entry/entry.acceptance is R
  → selected coverage_reviews_ref의 독립 SHA256 대 동일 raw bytes
  → strict UTF-8/JSON·duplicate/number/Unicode
  → wrapper2 / Context7 / Inventory review9 / Implementation review15 / Scope2 / HRC1
  → 기존 Scope/date/Review/Context 생성자로 원순서 복원
  → policy / scope / dataset / Registry / implementation baseline 순 대조
  → 기존 frozen/slots CoverageReviewContext 반환
```

새 모듈 `policy_data/historical_coverage_review_context_loader.py`와 합성 테스트를 추가하고 `load_historical_coverage_review_context_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> CoverageReviewContext` 하나만 export했다. 필수 keyword-only3개/exact 타입이며 옵션은 없다. 기존 Review/Context/Scope 모델·다른 historical loader·core/지문을 변경하거나 새 generic framework로 공통화하지 않았다.

HRC1과20개 prefix/P0~P8·기존 constructor 검증·역사 기록 공존은 HISTORICAL_COVERAGE_REVIEW_CONTEXT_ARTIFACT_PREPARATION_SPEC.md7~12·18~23·30절을 따른다. Context baseline과 R만 대조하며, 개별 Review의 inventory/rule/dataset/fp/date 차이를 자동 제거하거나 baseline 모순으로 일괄 거부하지 않는다. duplicate ref/다른 소속은 기존 Context가 거부한다. SHA/parse/constructor 순서·100회 결정성/불변성·원문 순서와 전체 저장 필드를 합성440개로 검증했다.

**IMPLEMENTED:** Historical ReviewContext strict bytes 복원·Inventory/Implementation Review 복원·Acceptance target/baseline 대조·합성 검증.

**이 loader에서 구현/실행하지 않음:** 기존 Review matcher/Review MATCHED 계산·Historical FULL·Inventory/Tree/subtree fp 재계산·실제 implementation ZIP·Historical Manifest/Registry Loader·Source Gate·Content Validator·Acceptance evaluator·same-call adapter·Bridge/Cashflow·실제 안산 검토/Acceptance/FULL 생성.

Context baseline 일치는 metadata 대응이며 사람 검토/실제 Registry/ZIP/전체 Manifest/Policy VERIFIED/현재 USABLE/사용자 PASS를 증명하지 않는다. 다음 최소 작업은 **Historical DatasetManifest Artifact Preparation Contract 설계 한 개**다. Coverage freeze/GV·BV·기존 loader/bootstrap/Cashflow/실제 releases를 보존하며 ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다.

검증: 사전 **8,981 passed in 68.62s**, 임시 사본 신규 합성 **440 passed in 1.99s**, 최종 전체 **9,421 passed in 51.77s / skipped0 / failed0 / timeout0**. 최초 전체 실행이 전후 모두 통과했고 실패/timeout/재실행은 없었다. 기존8,981개 tests/fixture/기대값·GV/BV·동결 Coverage 코드/문서·모델·기존 Historical Benefit/Coverage/PolicyEnvelope/Review loaders·bootstrap/Cashflow는 보존했다. 보호 기준선189개(루트4개 포함) 중186개는 SHA까지 동일, export/관련 문서2개만 수정하고 새 loader/합성 테스트2개를 추가했다. 실제 release6개 SHA256·경로·크기·수정시각도 모두 같다. 최종 판단은 **HISTORICAL_COVERAGE_REVIEW_CONTEXT_LOADER_COMPLETE**다.

## 60. M2.68 — IMPLEMENTED: Historical DatasetManifest Strict Bytes Loader

공개 API는 `load_historical_dataset_manifest_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> DatasetManifest`다. 세 입력 exact type/필수 keyword-only이며 실제 M2.57 반환 Artifact와 원본 Acceptance를 같은 호출 흐름에서 공급한다.

같은 Entry의 acceptance_ref/객체 is → dataset_manifest_ref → 독립 raw SHA → strict UTF-8/JSON/HM1 wrapper/canonical → UTC snapshot/기존 constructor → dataset/선택 policy membership/edition/rule → Registry fp 및 같은 Entry Policy/Registry artifact의 path+sha 대응을 검사한다.22개 오류와 P0~P9 순서를 유지한다. Manifest11필드/nested 객체/원본 collection 순서를 보존하며 보정·dedupe하지 않는다.

원래 timezone 이름/offset 표기/fold를 추정하지 않는다. 현재 engine_version/implementation SHA equality도 무조건 강제하지 않는다. R에 없는 dataset_id 비교값/Manifest quarter/engine 경로를 만들지 않는다. 같은 ZIP profile/실제 bytes/실행 대응은 외부 책임이다.

**IMPLEMENTED:** HM1 strict bytes loader, immutable DatasetManifest 복원, selected PolicyEditionReference membership, 직접 가능한 Acceptance dataset/Registry/reference binding, 신규 합성543개.

**NOT IMPLEMENTED:** Historical SourceRegistry Loader, 전체 release contents validation, production engine ZIP 실행 검증, quarter applicability verification, Content Validator, Source Gate, Acceptance evaluator, Benefit Bridge/Cashflow 연결, FastAPI/React 연결. 전체 validate_dataset_manifest/Registry 조회/다른 historical loader/Review matching/Coverage FULL은 실행하지 않는다.

검증 이력: 사전 actual 전체 **9,421 passed in 71.24s**. 신규 첫 두 실행은 각각 **1 failed, 538 passed in 2.25s / 2.36s**로 같은 recursion 사례의 fixture 깊이 가정이 틀렸다. 실제 JSON C decoder 한도를 확인해 신규 입력만 수정한 후 **539 passed in 2.08s**, 경계4개 추가 후 **543 passed in 2.66s**다. 기존9,421개 테스트·fixture·기대값은 변경하지 않았다. 사후 actual 전체 및 최종 보존: **9964 passed in 48.93s, 사후 전체 최초 실행 통과/skipped0/failed0/timeout0/재실행0. 기존192개 중189개 SHA256 동일, 수정3개는 export/관련 문서2개뿐. 신규 loader/합성 테스트2개를 추가해 최종194개, 삭제0개. 기존9,421개 tests/fixture/기대값·GV/BV·동결 Coverage·모델·기존 loader4종/Review Artifact Strict Loader/bootstrap/Acceptance/Benefit/Cashflow는 보존. 실제 release6개 SHA256·경로·크기·수정시각 모두 동일**.

최종 판단은 **HISTORICAL_DATASET_MANIFEST_LOADER_COMPLETE**이며 상세 계약/실행 대응/실패·수정 이력은 HISTORICAL_DATASET_MANIFEST_ARTIFACT_PREPARATION_SPEC.md32절이다. 다음 최소 작업은 **Historical SourceRegistry Artifact Preparation Contract 설계 한 개**다. Coverage freeze/GV01~GV15/BV01~BV16/기존 loader4종·Review Artifact Strict Loader/Acceptance/Benefit/bootstrap/Cashflow/실제 releases를 보존하고 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 61. M2.70 — IMPLEMENTED: Historical SourceRegistry Strict Bytes Loader

공개 API는 `load_historical_source_registry_bytes(*, raw_bytes: bytes, artifact: AcceptanceReviewArtifact, expected_acceptance: PolicyBenefitAcceptance) -> SourceRegistry`다. exact type/필수 keyword-only3입력만 받고 외부 Registry/Manifest/skip 옵션으로 복원하지 않는다.

정확한 Entry acceptance_ref/원본 is → source_registry_ref → 전체 raw SHA → strict UTF-8/JSON/HSR1 → raw shape/canonical → 기존 parse_source_registry1회 → 기존 fingerprint_source_registry1회 → Coverage/Benefit Registry fp 각각 비교 → parser의 동일 불변 객체 반환을 구현했다.16개 prefix/P0~P9를 유지하며 parser/지문 semantics를 수정하지 않았다.

SourceRegistry1/Document18/Evidence9필드·optional 생략·nullable·원본 tuple 순서를 보존한다. previous_urls를 정렬하지 않으며 domain helper의 기존 정렬만 사용한다. ACTIVE/SUPERSEDED/WITHDRAWN 및 DRAFT/VERIFIED/STALE을 현재 사용 적격성으로 바꾸지 않고, 오래된/미래 확인일도 내부 날짜 관계에 맞으면 그대로 복원한다.

**IMPLEMENTED:** Historical SourceRegistry strict bytes, 공개 pure parser 재사용, 실제 Registry domain fp/Acceptance binding, 신규 합성741개·helper 호출 횟수/객체 identity·오류 순서·100회 결정성·불변성/외부 호출 부재 검증.

**NOT IMPLEMENTED:** 공식 Source 원문 bytes/locator 의미/날짜별 사용 승인/Source Gate, Historical Manifest 전체 집합 비교, 전체 release validation, production ZIP 실행, Review Content Validator, Acceptance evaluator, same-call adapter, Benefit Bridge/Cashflow·FastAPI/React 연결.

검증: 사전 actual 전체 **9,964 passed in 83.16s**. 신규 최초 **739 passed in 3.03s**, HS90 날짜 경계2개 추가 후 **741 passed in 3.30s**. 최초 실패/timeout0회이며 기존9,964개 테스트·fixture·기대값은 변경하지 않았다. 사후 actual 전체 및 보존: **10705 passed in 48.52s; 사후 전체 최초 실행 통과/skipped0/failed0/timeout0/재실행0. 기존195개 중192개 SHA256 동일, 수정3개는 export와 관련 문서2개뿐. 신규 loader/테스트2개를 추가해 최종197개, 삭제0개. 기존9,964개 tests/fixture/기대값·GV/BV·Coverage freeze·Source 모델/parser/fingerprint·기존 Historical loader5종·Review Artifact Strict Loader·Acceptance/Benefit/bootstrap/Cashflow를 보존. 실제 release6개 SHA256·경로·크기·수정시각 모두 동일**.

최종 판단은 **HISTORICAL_SOURCE_REGISTRY_LOADER_COMPLETE**다. 이제 복원6종의 합성 연결 검증으로 전환할 수 있으며 추가 History 모델은 필요하지 않다. 다음 최소 작업은 **M2.71 — 6종 Historical Artifact 합성 연결 검증** 한 개로, 같은 A/R와 raw6종의 실제 loader 결과/참조·지문 관계를 통합 테스트로 확인하는 것이다. 이것이 전체 release/원문/실제 실행/FULL/USABLE의 완료를 뜻하지 않는다. 상세 실행 대응/보존 기록은 HISTORICAL_SOURCE_REGISTRY_ARTIFACT_PREPARATION_SPEC.md31절이다. Coverage freeze/GV01~GV15/BV01~BV16/기존 loader5종/Review Artifact Loader/Acceptance/Benefit/bootstrap/Cashflow/실제 releases와 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다.

## 62. M2.73 — IMPLEMENTED: Historical Cross-Artifact Validator

M2.71의 여섯 원본 합성 연결 검증과 M2.72의 확정 계약을 내부 순수 함수로 구현했다. 실제 모듈은 `backend/policy_engine/policy_data/historical_cross_artifact_validator.py`, 함수는 `_validate_historical_artifact_relationships`다. 명시 원본 Acceptance/Review Artifact와 BenefitSnapshot/EligibilityCoverage/PolicyEnvelope/CoverageReviewContext/DatasetManifest/SourceRegistry의 **필수 keyword-only8개**, exact type, 성공 None/모순 PolicyDataError만 제공한다. 공개 export·endpoint·새 모델·새 Loader는 없다.

P0 기존 Entry helper의 is/root/ref → P1 policy/scope/edition → P2 dataset → P3 기존 Manifest bind와 선택 Envelope domain → P4 실제 Registry fp/문서 집합/version → P5 같은 Coverage 구현 참조/알려진 원문 H 선언 → P6 기존 Coverage 구조 → P7 기존 지문/Inventory→canonical Implementation matcher → P8 None이다. 새 prefix8개 및 기존 helper의 예외 객체·내부 우선순위를 유지한다. 원본 Binding/root를 그대로 사용하며 정상 MISSING/STALE/partial Coverage를 새 오류로 승격하지 않는다.

Manifest 전체 정책을 선택 정책 하나로 대체해 validate_dataset_manifest를 실행하지 않는다. Source Gate/현재 시각/I/O/ZIP/bootstrap/공식 Coverage evaluator/Acceptance evaluator를 호출하지 않는다. Manifest 엔진 H와 Coverage 구현 H의 전역 equality는 없고, 공유 profile/실제 bytes·실행 대응은 외부 준비 책임이다. optional content_sha256=None을 fake H로 채우지 않는다.

**IMPLEMENTED:** 내부 관계 검증 함수, 직접 비교 가능한6종 원본 관계, 기존 selector/Manifest bind/지문/구조/matcher/get_source 재사용, 실제 여섯 loader 성공 뒤 교차 모순 차단·helper 원본 인자/횟수/예외·정상/오류100회·불변성·순수성 신규157개 테스트. M2.72의36개 분류/56개 수동 시나리오 대응은 HISTORICAL_CROSS_ARTIFACT_VALIDATOR_CONTRACT24절에 기록한다.

**NOT IMPLEMENTED:** Production same-call orchestration, 전체 release contents verification, Official Source 원문 검증, Source Gate, Review Content Validator 전체 구현, production ZIP 실행 검증, Historical FULL_POLICY, Acceptance evaluator 연결, Benefit Bridge/Cashflow·API/UI 연결.

typed 객체만으로 실제 raw 복원 이력을 재증명하지 못한다. 테스트의 같은 A/R·실제 loader6→함수 연결은 합성 시험이며 운영 adapter가 아니다. 외부 API가 임의 객체/이전 None 성공을 승인 증거로 받지 않도록 하는 진입 계약은 다음 작업이다.

검증: 사전 actual 전체 **10,786 passed in 76.36s**. 신규 최초 **147 passed in 2.40s**, 비교 순서/정상 Registry 경계10개 추가 후 최종 **157 passed in 2.29s**, 실패/timeout0회. 사후 actual 전체: **10943 passed in 64.04s (0:01:04)**. 사후 전체 최초 실행 통과. failed/skipped/timeout 0회, 재실행 0회 기존 보호 파일200개 중 **198개 SHA256 동일**, 수정2개는 승인된 계약/Architecture 문서뿐이다. 신규 운영 모듈/테스트2개를 추가해 최종 **202개**, 삭제0개다. 기존 코드·테스트·fixture·기대값·export·설정은 모두 보존했다. 기존 **10,786개 + 신규 157개 = 10,943개**가 전체 회귀에서 모두 통과했다. GV01~GV15/BV01~BV16·Coverage freeze·기존 Loader6/M2.71 통합/Review Artifact Loader/bootstrap/Acceptance/Benefit/Cashflow는 **기존 파일 SHA·기대값 보존, 기존 10,786개 전체 회귀 통과**. 실제 release6개는 **6개 전부 SHA256·경로·크기·mtime_ns 동일**.

최종 판단: **HISTORICAL_CROSS_ARTIFACT_VALIDATOR_COMPLETE**. 다음 최소 작업은 **실제 same-call orchestration 선행 조건 계약 설계 한 개**다. ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, 실제 Ansan **DRAFT / CONDITION_SLICE**, Generic Coverage freeze를 유지한다. 실제 정책·공식 원문·검토/수용 기록·금액·운영 ZIP 실행 결과를 새로 생성하지 않는다.

## 63. M2.75 — IMPLEMENTED: Historical Same-Call Orchestrator

M2.74 계약의 B 진입점을 `backend/policy_engine/policy_data/historical_artifact_orchestration.py`의 private `_orchestrate_historical_artifact_validation` 한 함수로 구현했다. 계약상 파일명이 이번 지시의 권장 파일명보다 우선하므로 alias는 만들지 않았다. 원본 A·전체 expected tuple·Review raw·역할별 raw6의 **필수 keyword-only9개**, exact type, default/option/공개 export·새 모델 없음이다.

P0a A exact type → P0b 실제 기존 Review strict loader1회(전체 expected 원본 tuple 보존) → P0c 기존 Entry selector 직접1회(status/root/ref/원본 is) → P0d raw6 exact bytes 전부 → P1~P6 기존 Benefit/Coverage/Envelope/ReviewContext/Manifest/Registry 로더 각1회 → P7 기존 Cross-Artifact Validator1회 → P8 `(R, tuple6)` 순서다. 같은 A/R/해당 raw bytes와 각 로더 반환 원본을 그대로 연결한다. SHA/strict/domain/교차 로직은 재구현하지 않는다.

정상 반환은 원본 R과 BenefitSnapshot/EligibilityCoverage/PolicyEnvelope/CoverageReviewContext/DatasetManifest/SourceRegistry의 고정 tuple6다. 첫 예외 즉시 종료·후속0회·부분 반환 없음이며 PolicyDataError/RuntimeError 원본 객체와 기존 prefix/내부 우선순위를 유지한다. 신규 입력 prefix는 INVALID_HISTORICAL_ORCHESTRATION_INPUT 한 개다. try/catch·fallback·cache·I/O·추가 평가·동적 선택은 없다.

실제 raw 통합 시험과 별도 단위 spy/예외 전파 시험을 구별했다. 신규 tests는 `tests/test_historical_same_call_orchestrator.py`이며 M2.71 저작 helper/M2.73 교차 부정 사례20개를 시험에서만 재사용한다. 다중 Entry/전체 expected/원본 is·각 raw SHA/strict/domain·로더6 성공 후 교차 모순·Manifest 선행 오류·9경계 예외 객체/후속0회·정상/오류100회·불변성·순수성·재호출·우회 인자 부재를 검증한다. 수동64개 실행 대응과 외부 미확인 분리는 HISTORICAL_SAME_CALL_ORCHESTRATION_CONTRACT23절이다.

**IMPLEMENTED:** 내부 순수 same-call 연결·B안 Review 복원 강제·raw6/교차 강제·완전 원본 tuple·신규 합성201개. 반환 tuple은 FULL/VERIFIED/USABLE이나 영구 provenance 인증이 아니다. 기존 교차의 정상 partial/MISSING/STALE·Source 상태·optional content H·역사 engine을 그대로 유지한다.

**NOT IMPLEMENTED:** 실제 원본7종 파일 preparation/허용 경로·handle/reparse/TOCTOU, production ZIP/profile/환경/import 실행 검증, 공식 Source 원문/locator·claim 의미/검토 진실성/Source Gate, 전체 Manifest release validation·Historical FULL_POLICY·현재 Acceptance evaluator·Benefit Bridge/Cashflow·API/UI 연결. 새 공유 ZIP profile의 H 관계를 역사 자료 전역 equality로 강제하지 않는다.

검증: 사전 actual 전체 **10943 passed in 90.21s (0:01:30)**. 신규 최초 **199 passed in 4.64s**, 뒤 Entry 모순/SUPERSEDED2개 추가 및 오류 반복 호출 관찰 보강 후 최종 **201 passed in 4.32s**, 최초 실패/timeout0회. 사후 actual 전체 **11144 passed in 64.49s (0:01:04)**. 사전/사후 전체는 각각 최초 실행 통과, failed/skipped/timeout0회. 신규 시험은 최초 통과 후 경계2개 추가에 따른 재실행1회이며 실패 수정 재실행0회다. 기존 보호 파일203개 중 **201개 SHA256·크기·mtime_ns 동일**, 변경2개는 승인된 이 계약/Architecture 문서뿐이다. 신규 운영/테스트2개를 추가해 최종 보호 파일205개, 삭제0개다. 기존 운영 코드/테스트/fixture/기대값/export/설정은 전부 보존했다. 실제 release6개는 **SHA256·경로·크기·mtime_ns 전부 동일**. 기존 tests/fixture/기대값·GV01~15/BV01~16·Coverage freeze·로더6/M2.71/M2.73/Review loader/bootstrap/Acceptance/Benefit/Cashflow·export·설정은 **기존10,943개 + 신규201개 = 11,144개 전체 회귀 통과, 기존 파일/기대값 보존**.

최종 판단: **HISTORICAL_SAME_CALL_ORCHESTRATOR_COMPLETE**. 다음 최소 작업은 **Review+Historical 원본7종 Raw Bytes Preparation 계약 설계**다. 실제 파일 취득의 공통 선행 책임부터 좁게 닫되, production은 backend import 전 별도 실행 artifact 검증까지 필요하다. 전체 Content/Source/release를 함께 구현하지 않고 새 History 모델/연결 함수를 자동 추가하지 않는다. ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, 실제 Ansan **DRAFT / CONDITION_SLICE**, Generic Coverage freeze와 정책 혜택 반영0원 원칙을 유지한다.

## 64. M2.77 — Historical Raw Bytes Preparation 구현·제한 검증

`backend/policy_engine/policy_data/historical_raw_bytes_preparation.py`의 private `_prepare_and_validate_historical_artifacts`와 `historical_windows_file_io.py`의 최소 Win32/handle/read helper를 추가했다. A·전체 expected tuple·trusted_root의 필수 keyword-only3개·exact 타입이며 public export/새 도메인 모델·Historical 로더·검증 알고리즘/범용 framework를 추가하지 않는다.

Q0 입력/지원환경·기존 expected ref/원본 membership → Q1 trusted directory chain → Q2 Review same-handle bytes → Q3 기존 Review strict/selector·참조6 전부 lexical 검사 → Q4 원본6 확보 → Q5 handle 재검사 → Q6 기존 M2.75를 동일 A/tuple/raw7로1회 → Q7 최종 검사/역순 정리 → Q8 `(same_call_result, raw7)` 반환이다. Review는 경로 선택 전1회·M2.75 내부1회이며 R_pre를 C에 주입하지 않는다. M2.75/기존 로더6/교차/모델을 수정하지 않았다.

Windows10/11 x64·local fixed NTFS로 제한한다. CreateFileW는 READ 공유만·OPEN_EXISTING·OPEN_REPARSE_POINT/BACKUP_SEMANTICS, 파일은 GENERIC_READ·directory는 READ_ATTRIBUTES다. 실제 volume/index/path·속성/종류/link count·길이를 검사하고 같은 handle ReadFile을 사용한다.4MiB/file·16MiB/raw7·64KiB read와 path/handle 예산을 적용하며 일반 open fallback/cache·부분 결과가 없다. 신규6prefix와 기존 예외 객체/Q0~Q8을 유지한다. 소유권 목록 할당 실패와 후속 오류에도 close를 시도하고 primary를 보존한다.

신규 `tests/test_historical_raw_bytes_preparation.py` 합성 최종 **157 passed in1.97s**, 실제 `tests/test_historical_raw_bytes_preparation_ntfs.py` 최종 **16 passed, 1 skipped in2.25s**다. 정상 native pipeline/metadata·52byte layout, 공유 writer/delete 충돌·자식 process file write/rename/delete 거부, 보호 해제 후 write/directory rename 성공, root/mid junction·hard link 거부,4/16MiB·case alias·empty·SetFileTime 변화 탐지·반복 성공/실패 handle count 불변을 확인했다. 실제 file symlink는 생성1314 권한 부족으로 미실행이며 PASS가 아니다.

신규 최초 합성147통과/2실패는 잘못된 JSON/REVOKED를 읽는 새 테스트 setup 문제로 수정했다. native 확장8통과/4실패/1skip 중3건은 sandbox 링크 생성 거부,1건은 directory rename code 기대32 대비 관찰5였다. 추가 승인 시험에서 junction/hard link가 통과했고, directory rename은 보호 중5/32 거부 및 보호 해제 후 동일 rename 성공을 함께 확인하도록 새 시험을 수정했다. 기존 테스트/fixture·보안 요구를 완화하지 않았다. 자동 승인 검토 timeout1건은 pytest timeout과 구분한다. 상세 HBP80 추적·전체 이력은 HISTORICAL_RAW_BYTES_PREPARATION_CONTRACT26절이다.

**판단: HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY.** 합성과 실제 NTFS16개가 통과했지만 필수 실제 file symlink1개 미실행이므로 전체 COMPLETE를 보류한다. 이 판단은 OS 시험을 전혀 하지 않았다는 뜻이 아니다. 다음 최소 작업은 **file symlink 생성을 허용한 별도 Windows 환경에서 기존 실제 거부 시험1건을 완료**하는 것이다. 현재 시스템 Developer Mode/권한 설정은 변경하지 않았다.

**남은 경계:** T1 보관소 ACL/발행·독립 expected 발급/정상 호스트, production ZIP/profile/import-before-trust, 공식 원문/locator/claim·Content 전체/Source Gate·전체 release/Historical FULL·현재 Acceptance evaluator·Benefit Bridge/Cashflow·API/UI는 미완료다. 동일 handle/공유 모드가 모든 metadata 변경이나 악성 관리자·filesystem 원자성을 보장한다고 주장하지 않는다. 현재 Review 로더가 raw20을 포함한 전체 canonical Review bytes SHA를 비교한다는 실제 계약을 재사용했으며 preparation은 hash를 재작성하지 않았다.

검증: 사전 actual 전체 **11144 passed in81.30s (0:01:21)**. 사후 actual 전체 **11317 passed, 1 skipped in 61.84s (0:01:01)**. 사전/사후 전체는 각각 최초 실행 성공이다. 사후 건너뜀1개는 신규 실제 file symlink 생성 WinError1314이며 PASS로 계산하지 않는다. 신규 실패·수정·재실행 이력은26.4~26.5절에 모두 기록했다. pytest timeout0회, 별도 자동 승인 검토 timeout1회다. 사후 자동 보고 단계에서 skip 설명에 숫자1314가 포함된다고 잘못 가정한 보조 스크립트 assertion1건을 수정했다. 기존 실행 로그와 정확한 skip 사례/설명·시험 코드의1314 분기를 대조해 마무리했으며 전체 pytest는 재실행하지 않았다. 기존 보호 파일206개 중 **204개 SHA256·크기·mtime_ns 동일**, 변경2개는 승인된 계약/Architecture 문서뿐이다. 신규 운영2/테스트2를 추가해 최종 보호 파일210개, 삭제0개다. 기존 운영 코드·테스트·fixture·기대값·export·설정은 모두 보존했다. 실제 release6개는 **6개 전부 SHA256·경로·크기·mtime_ns 동일**. 기존 tests/fixture/기대값·GV01~15/BV01~16·freeze·M2.75/Review/로더6/교차·Source/Manifest·bootstrap/Acceptance/Benefit/Cashflow·export/설정은 **기존11,144개 전부 + 신규173개 = 11,317개 통과. 신규 실제 file symlink1개만 건너뜀이며 기존 테스트의 건너뜀/실패0개, 기존 파일·fixture·기대값 보존**. ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, 실제 Ansan **DRAFT / CONDITION_SLICE**·정책 혜택 반영0원과 Generic Coverage freeze를 유지한다.


## 65. M2.77 보충 검증 — file symlink 필수 증거 보류·M3 전환 방향

2026-10-24 보충 검증에서 기존 운영/테스트 코드를 변경하지 않았다. 제공·확인된 별도 Windows NTFS 환경은 없다. 현재 로컬 PC는 Windows version major10/build26300·AMD64/64bit·CPython3.12.14이며, 열린 임시 시험 root handle에서 NTFS를 확인했고 현재 실행 토큰 IsUserAnAdmin=False였다. Developer Mode/보안 설정/토큰 권한 변경·관리자 상승/UAC 실행은 없었다.

기존 단독 file symlink 시험 **1 skipped in 0.69s**, 실제 NTFS 전체 **16 passed, 1 skipped in 2.17s**, 전체 회귀 **11317 passed, 1 skipped in 66.89s (0:01:06)**다. CreateSymbolicLinkW 오류1314 분기로 링크 생성 전에 중단했다. 실제 링크는 생성되지 않았고, 계획한 대상은 임시 합성 Review 파일임을 bytes까지 확인했다. 준비 함수의 실제 symlink 거부/error prefix·거부 이후 후속 차단/handle 정리는 **미관찰**이다. skip 전 미진입으로 함수/C 호출0회인 사실을 거부 후 차단 성공으로 확대하지 않는다. 다른 실제 NTFS16개 통과는 해당 증거를 대체하지 않는다.

**HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY 유지**. 보충 단독/NTFS/전체 각1회·실패0·수정/실패 수정 재실행/pytest timeout0이며, 상세15항목과 이전 이력은 HISTORICAL_RAW_BYTES_PREPARATION_CONTRACT27절에 기록한다. 실제 release6개의 SHA256·경로·크기·mtime_ns 불변, GV01~15/BV01~16·기존 코드/테스트/fixture/기대값/export 불변이다. 검증 전후 문서 기록 전 보호210개+release6개 동일, 기록 후 보호208개+release6개 동일이며 변경은 계약/Architecture 문서2개뿐이다.

사용자가 지정한 후속 방향은 **M3: 합성 사용자 입력→기존 Policy Engine→자격·불확실성→기존 Cashflow Core→결과 API→최소 React**다. 이번 보충 검증에서 M3를 구현하지 않았으며, M2.77의 실제 file symlink 필수 증거1건은 남겨 둔다. 실제 Ansan **DRAFT / CONDITION_SLICE**, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, 검증되지 않은 실제 정책 혜택0원, Generic Coverage freeze를 유지한다. production ZIP/import 신뢰·Content/Source Gate/전체 release 승인으로 확대하지 않는다.


## M3.0 — 합성 사용자 기능의 실제 웹 연결

이 절은 현재 사용자 기능 상태다. 과거 절의 UI/API 미구현 표기는 각 milestone 당시 이력이다.

React/TypeScript/Vite `frontend/` → same-origin `/api` proxy → FastAPI `backend/web/app.py` →
`SimulationInput` → `service.simulate` → 기존 `evaluate_policies` 및 `calculate_cashflow` → JSON → 결과 화면.

새 API는 `GET /api/health`, `POST /api/synthetic/simulate`다. 서버는 127.0.0.1:8100, 화면은 127.0.0.1:5173이다.
별도의 정책 엔진/집계/금액 계산식을 만들지 않았다. 기존 합성 fixture와 CLI 평가일 2026-10-20을 재사용한다.
도메인 입력에는 독립적인 나이·지역·재학·취업과 생활비 소득만 전달하고 `policy_facts=()`를 유지한다.
현금흐름에는 검증된 원 단위 정수만 전달하며 정책 지원금은 서버에서 항상 0원으로 설정한다.

응답은 synthetic/test_only, 입력 요약, 원본 조건별 판정·reason·missing·evidence, context/version,
Cashflow Core 원본 결과를 포함한다. UI의 한국어 조건 표시는 원본 결과를 설명할 뿐 새로 판정하지 않는다.
현재 결과는 입력 수정 시 폐기한다. 처리 중 중복 제출 방지, 10초 요청 제한, 오류와 재시도를 제공한다.
요청 또는 결과 캐시는 없다. 오직 불변 합성 정책 fixture만 메모리에 캐시한다.
입력/결과 영구 저장, 외부 LLM 전송, 분석 추적은 도입하지 않았다. API no-store, access-log 비활성 실행을 사용한다.

Coverage 동결 코어, 과거 6 loader, CrossValidator, Same-call Orchestrator, Raw Bytes Preparation,
Acceptance, 기존 fingerprint golden, 실제 release 6개는 이 경로에서 수정/호출하지 않는다.
실제 안산 정책 DRAFT / CONDITION_SLICE 및 ResidenceHistory OFFICIAL_INQUIRY_REQUIRED는 유지한다.
M2.77 SYNTHETIC_ONLY는 웹 연결 완료로 승격하지 않는다.

실행·검증·범위 기록은 `M3_0_SYNTHETIC_WEB.md`를 참조한다.


## M3.1 — 합성 What-if Before/After 비교 구현

현재 비교 경로는 React `WhatIf` → `POST /api/synthetic/compare` → `compare_scenarios`
→ 기존 `service.simulate(before)` / `service.simulate(after)` → 기존 Policy/Cashflow2회 → 서버 차이/근거 → 화면이다.
기존 `/api/synthetic/simulate` 및 SimulationInput/Response 계약은 유지한다.

비교 DTO는 기존 입력2개와 각 원본 결과, 정수 금액 차이, 바뀐 입력, 정책/조건별 전이,
원본 reason/missing/evidence, 정형 설명과 facts를 보존한다. 정책 집계나 예산 공식을 복제하지 않는다.
저축 상한 None/0을 구분하며 지정 상한의 숫자 차이는 양쪽 정수인 경우에만 계산한다.
개인 생활비 소득은 household_income 사실이 되지 않으며 정책 지원금은 전후0원이다.

현재 결과에서 비교를 열면 입력을 복사한다. After 수정/초기화/재요청 시 이전 비교를 버리고
AbortController/요청 번호로 오래된 성공/실패를 차단한다. 현재 입력 변경은 비교를 닫는다.
서버/네트워크/입력/시간 초과 오류는 UNKNOWN/FAIL/정상 적자와 분리한다.
외부 LLM·DB·개인정보 저장·금융상품·공개 배포는 도입하지 않았다.

최종 검증: 기존11,359+신규48 =11,407 passed, 기존1 skipped/1 warning 유지.
Frontend 기존16+신규24 =40 passed, TypeScript/Vite build 성공, 실제 HTTP/브라우저/390px 확인.
Coverage freeze, GV/BV, 도메인 코어, Historical6/Orchestrator/RawBytes, Acceptance/Benefit,
release6개를 보존한다. 실제 정책 DRAFT/CONDITION_SLICE, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED,
M2.77 HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY는 유지한다.

상세31개 보고 항목·실행·실패/수정 이력은 `M3_1_WHAT_IF_COMPARISON.md`를 참조한다.

## M3.2 — 가상 정액적금 계산

React SavingsPanel → POST /api/synthetic/savings/recurring → 기존 service.simulate(profile)
→ 기존 Cashflow 상한 + 순수 backend.finance.recurring.calculate_recurring_savings → 세전 예상 결과.
클라이언트가 보낸 계산된 상한·정책 지원금은 받지 않는다. 기존 Policy/Cashflow 공식을 복제하지 않는다.
금융 계산은 UI/정책 엔진과 분리된 frozen DTO와 Decimal(정밀도50) 순수 함수다.
매월 초 동일 납입·고정 연 기본금리·단리·정수 개월·세전만 지원한다.
원금=P*n, 총이자=P*(연금리%/100)*n*(n+1)/24. 총이자만 마지막에 ROUND_HALF_UP으로 원 단위 반올림한다.
상한 초과/적자는 경고이며 납입액을 변경하거나 정책 3상태로 판정하지 않는다.
실제 상품 수집·추천·예금·What-if 상품 비교·외부 LLM·지원금 반영은 이번 범위에 없다.
상세 계약·검증·보존·Obsidian 기록은 M3_2_SYNTHETIC_SAVINGS.md를 참조한다.

## M3.3 — 공식 상품 스냅샷 조건 비교

React05단계 → GET /api/financial-products → 검증된 로컬 JSON/XLSX 출처 → 공식 과거 정보3개.
선택/월 납입/기간/기존 현재·What-if 프로필 → POST /api/financial-products/compare
→ 공식 조건/기간/한도/최신성/가입상태/계산가정 대응 검사 → 대응 시에만 기존 M3.2 순수 함수.
현재3개는 자유적립식·계산 근거 미확인·오래된 기준일로 실제 계산0개/금액null이다.
우대금리는 표시만 하고 기본금리 계산과 분리한다. 미계산을0원으로 바꾸거나 순위를 만들지 않는다.
예산은 기존 service.simulate를 현재/변경 각각 재사용한다. WhatIf의 선택적 결과 콜백 외 기존 비교 계산은 변경하지 않았다.
스냅샷 수집은 개발 중 수행하고 서비스 요청 중 외부 통신/수집/경제 입력 저장은 없다.
실제 신규가입/사용자 자격/정책 PASS를 구분한다. 전체 마일스톤은 계산 호환성 보류이며 COMPLETE 아님.
출처·범위·30개 보고 항목은 M3_3_OFFICIAL_PRODUCT_COMPARISON.md를 참조한다.


## M3.4 — IBK 정액적금 계약 검증 결과

제품 실행 경로는 변경하지 않았다. 공식 상품설명서2쪽의 실일수/365 및 합산 후 원 미만 절사를 확인해 M3.2의 정수개월/ROUND_HALF_UP과 계약 불일치(C)로 판정했다.
공식50만원/12개월/2.40% 예시의78,000원 수치 재현은 별도 시험이며 실제 상품 계산 승인이 아니다.
data/financial-products/research/ibk-fixed-review-v1.json은 연구용 근거/판정 기록이며 서비스 catalog가 읽지 않는다.
현재 서비스는 공식 과거 정보3개/실제계산0개를 유지한다. API/React/새 날짜 계산기·범용 프레임워크를 추가하지 않았다.
24개 보고 항목과25조건 대조표는 M3_4_OFFICIAL_FIXED_SAVINGS_VERIFICATION.md를 참조한다.

## M3.6 — 엔진 결과 설명 서비스

WhatIf 비교 결과 아래 ExplanationPanel → POST /api/synthetic/explain → 기존 strict Before/After 입력 검증
→ 기존 compare_scenarios/Policy/Cashflow2회 → allowlist ExplanationFacts → 정형 문서
→ 선택한 로컬 provider1회 → JSON/전체 숫자·상태·사유·UNKNOWN·출처 대조 → 한국어 설명 또는 정형 fallback.
클라이언트가 보낸 계산 결과/facts는 받지 않으며 원본 지역 문자열·나이·평가값·프로필 전체는 모델 payload에서 제외한다.
금액/정책 상태/근거/확인 행동은 대조 후에도 서버 값만 사용한다. 모델 자유문장은 요약/정책 text 두 영역이며
숫자·상태 단정·기한/추천 표현 등을 제한한다. 자연어의 모든 의미를 검증했다는 보장은 아니다.
기본 provider는 미설정이다. 외부 API는 미지원, 새 모델 설치/다운로드 없음. 실제 LLM 실행0건.
선택 로컬 Ollama 어댑터의 고정 루프백 주소/프록시·리다이렉트 차단/1회 요청/timeout/출력 상한만 구현했다.
실제 모델·라이선스·로컬 서버의 외부 통신 정책은 연결 전 별도 확인해야 한다.
기존 M3.1 정형 문장을 fallback에 재사용하며 기존 simulate/compare와 금융 계산 계약은 변경하지 않는다.
상세 계약/보호 범위는 M3_6_AI_EXPLANATION_CONTRACT.md, 검증 결과는 M3_6_AI_EXPLANATION_SERVICE.md를 따른다.

## M3.8A — 합성 경량 설명 코어

`backend/explanation/narrative_contract.py`는 기존 ExplanationFacts를 최소 입력으로 투영하고,
합성 fixture의 summary/policy_texts를 엄격히 검사해 canonical 문서의 허용 텍스트만 교체한다.
project_facts → prepare_narrative → parse_narrative → assemble_narrative → 기존 validate_output 순서이며,
evaluate_synthetic_narrative는 예상한 계약 실패만 전체 정형 문서로 대체한다.
기존 validator/Facts/정형 생성기/Policy/Cashflow/Provider/API/React는 수정하지 않는다.

입력은 기존 delta의 방향·변경 필드명·정책/조건 상태·누락 정보·상한None/0 분류만 포함한다.
금액·정형 문장·실제policy_id·reason원문·출처경로는 모델용 JSON에서 제외한다.
슬롯은 정형 문서 순서의p01~p03이며 서버 전용 immutable tuple과 요청 전용 객체로 묶는다.
동일 Facts 투영은 결정적이고 서로 다른 준비 요청의 검사 결과는 혼합하지 않는다.
원시 JSON 자체의 요청 출처를 증명하는 프로토콜은 아니므로 향후 제공자가 요청별 응답을 연결해야 한다.
V1은0~3개 정책을 지원하고4개 이상은 정형 대체한다. 기존 정책 엔진의 지원 범위는 바꾸지 않는다.

입력4KiB/작은JSON4KiB,요약60·정책40 Unicode code point 제한을 사용한다.
중복키/비정상 상수/타입/미완성·추가필드/슬롯오류·제어문자/금지어와 알려진 불확실성 부정 문구를 거부한다.
NFKC는 검사에만 사용하고 본문을 trim/수정하지 않는다. 조립 뒤32KiB·핵심값/문장 검사는 기존 검증기 책임이다.
예상치 못한 내부 RuntimeError나 canonical 문서 손상은 정상 모델 품질 실패로 숨기지 않는다.
문자열 검사는 자연어 전체 의미를 보장하지 않으며 서버 원본 일치를 모델의 숫자 정확도 성과로 쓰지 않는다.

현재는 합성 fixture만 사용하며 실제Provider·/api/chat·공개endpoint·화면을 연결하지 않았다.
M3.7 실행 판단은 QUALITY_REVISION_REQUIRED, 현재 정형 기본값을 유지한다.
실제 상품 계산0개/지원금0원·정책DRAFT/CONDITION_SLICE·ResidenceHistory문의보류·M2.77SYNTHETIC_ONLY를 보존한다.
범위·테스트·한계·Obsidian 기록은 M3_8A_LIGHTWEIGHT_LLM_CORE.md,
고정30 합성 산출물은 evidence/m3_8a_narrative_core_evaluation.json을 참조한다.


## M3.8B 실제 경량 Provider 연결

기존server opt-in에`AIX_EXPLANATION_CONTRACT=narrative_v1`을추가하면`OllamaNarrativeProvider`가고정loopback`/api/chat`으로최소투영+슬롯schema만전송합니다. 요청별prepared→strict envelope→M3.8A parse/assemble→기존validator→기존service응답이며실패는전체정형대체입니다. 6초/8초/12초·32KiB/4KiB·256토큰유지,자동재시도없음. 미설정기본값/legacy경로·기존검증기·엔진·API·React는보존했습니다.

실제고정30은25채택/5표현거부대체,Python원본불변30/30이지만채택문장에도월세↔소득/생활비소득↔정책통과/비사용조건↔입력불변혼동이있어**M3_LIGHTWEIGHT_LOCAL_LLM_INTEGRATED_QUALITY_REVISION_REQUIRED**입니다. 기본서비스는NoProvider정형,실제모델운영승인아님. [실행보고](M3_8B_LOCAL_NARRATIVE_INTEGRATION.md) · [합성실측/원문](evidence/m3_8b_actual_evaluation.json).

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
