# Benefit Acceptance Context·명시 참조 조회 계약 — M2.47

현재 구현 상태는 **35절 M2.48**을 따른다. Context와 private explicit resolver만 구현했고 현재 사용 평가/result·Bridge는 없다. 아래1~34절은 승인된 M2.47 설계와 당시 검증 이력이다.

작성일: **2026-10-22 / Asia/Seoul**. **문서 전용**. 최종 판단: **READY_TO_IMPLEMENT_ACCEPTANCE_CONTEXT**.

이번 산출물은 이 문서 한 개다. 아래 Context와 private resolver는 **후속 구현 계약이며 아직 구현된 API가 아니다**. 기존 Acceptance/Snapshot/지문/Coverage/Cashflow 코드·테스트·명세·실제 releases를 수정하지 않는다. 실제 Context·Acceptance·철회 기록을 생성하지 않는다.

## 1. 목적과 Source of Truth

한 Benefit target의 불변 역사 기록과 철회 연결을 검증하고, 명시 acceptance_ref 하나로 원본 결정 revision을 찾는 최소 계약을 확정한다. 과거 기록 보관·ref 조회·현재 사용 가능성 평가의 책임을 분리한다.

| 다시 확인한 문서/코드 | 적용한 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md 4~12·19~28·37절 | 구현된21필드/2상태·target/ref/revision·동일 binding 철회·후행 version/검토일·현재 사용 분리 |
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md | FULL 필요조건·명시 선택·독립 지문 모순·verification·철회 이력/진실성 한계 |
| BENEFIT_SNAPSHOT_SPEC.md 7·14·17·36~37절 |16필드/전용 지문·단일 record의 동일 release·관련 근거 보존 |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md | 불변 승인/철회·외부 현재 선택/완전성·개인/월 적용 경계 |
| CASHFLOW_BENEFIT_BRIDGE_SPEC.md | 월 자유 현금·중복/병급·무환산·합산은 별도 책임 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | 동결 의미/API/지문/GV·실제 정책별 blocker 유지 |
| DATA_MODEL.md 34절 / ARCHITECTURE.md 50절 | Acceptance 값만 구현, Context/현재 평가/Bridge는 미구현 |
| benefit_acceptance.py / eligibility_coverage.py / errors.py | exact record/Scope·a 문법·비공백 ref·기존 PolicyDataError |
| coverage_review_context.py / coverage_review_resolution.py | exact tuple·원본 보존·frozen/slots·명시 exact ref·원본 반환·코드 prefix 오류 |

우선순위는 동결 Coverage 계약 → 승인된 M2.45/M2.46 record 계약 → 이번 Context/resolution 구체화 → 과거 후보 조항이다. 기존 문서의 당시 미구현 표기를 소급 수정하지 않는다. M2.45 27절의 선택 ref를 받는 묶음 후보는 **4필드 Context와 별도 resolver 인자**로 구체화한다.21필드 record와 기존 버전/지문 의미를 바꾸지 않는다.

작업 전 전체 baseline: **6525 passed in 16.31s**. 신규 실행 테스트는 만들지 않는다.

## 2. Context의 정확한 의미

**BenefitAcceptanceContext는 정확히 하나의 (policy_id, scope, benefit_id)에 속하는0개 이상의 immutable historical PolicyBenefitAcceptance를 명시적 collection snapshot으로 묶은 값**이다.

유효한 Context는 공급된 기록의 소속·ref/revision 유일성·철회 edge가 이 계약에 맞는다는 뜻이다. 현재 Acceptance·최신 Acceptance·usable Acceptance·VERIFIED·사용자 자격·Bridge 결과·Cashflow 입력을 뜻하지 않는다. Context에는 상태 Enum/property·선택 ref·current baseline이 없다.

## 3. One-target boundary

target은 **(policy_id, scope, benefit_id)**다. policy_id/benefit_id는 exact str과 기존 `[A-Z0-9]+(?:-[A-Z0-9]+)*` 문법, scope는 exact 기존 ApplicabilityScope를 사용한다. 문자열/Scope subclass·raw dict·자동 strip/uppercase·표시명 매칭을 거부한다.

모든 record의 세 target 값이 Context와 value equality로 일치해야 한다. 동등한 별개 Scope 인스턴스는 허용하며 object identity까지 같을 필요는 없다. Context의 원래 Scope와 각 record의 원래 Scope는 각각 보존한다. Q3/Q4/annual/다른 edition은 다른 target이다. 다른 policy/benefit/회차 기록은 별도 Context에 둔다. cross-context search나 자동 승계는 없다.

## 4. 최종 stored fields — 정확히4개

후속 BenefitAcceptanceContext는 **frozen=True, slots=True, kw_only=True**로 정한다. 일반 structural constructor를 허용하며 아래4개는 모두 default 없는 필수 인자다.

| 순서 | 필드 | 정확한 타입/규칙 |
|---|---|---|
| 1 | policy_id | exact canonical str |
| 2 | scope | exact ApplicabilityScope, 원본 보존 |
| 3 | benefit_id | exact canonical str |
| 4 | records | exact tuple[PolicyBenefitAcceptance, ...], 빈 tuple 허용·원본 보존 |

dataset_version/current_version/latest_ref/current_acceptance/selected_acceptance_ref/current_acceptance_ref·인덱스·캐시·현재 상태는 저장하지 않는다. constructor의 누락/extra/positional 인자 오용은 Python TypeError이며 별도 sentinel/factory를 도입하지 않는다.

## 5. Empty Context와 부재

`records=()`는 정상이다. 의미는 **이 target에 대해 현재 supplied Context에 record가 없음**이다. 실제로 발급된 적이 전혀 없다는 전역 진실성·완전성을 인증하지 않는다.

빈 Context만으로 Data Error를 만들지 않는다. 향후 명시 no-selection과 결합하면 정상 NO_ACCEPTANCE가 될 수 있다. 그러나 빈 Context에 존재한다고 지정한 ref를 조회하면 ACCEPTANCE_REF_NOT_FOUND다. Context 객체 자체와 None은 다르며 resolver는 None을 허용하지 않는다.

## 6. records의 exact 타입과 원본

records는 exact tuple, 각 원소는 exact PolicyBenefitAcceptance다. list/generator/tuple subclass·record subclass·dict/None/유사 객체를 자동 변환하지 않는다. 모든 원소의 exact 타입 검사를 끝낸 뒤 target/중복/edge를 읽는다.

정상 생성된 immutable record의 로컬21필드 검증을 신뢰한다. Context가 record를 재생성하거나 __post_init__을 다시 호출하지 않는다. 잘못된 날짜/내부 release/self-link는 이미 M2.46 constructor가 거부한다. object.__new__/object.__setattr__ 등의 강제 훼손까지 복구·위조 방지하는 보안 경계는 아니다. 기존 model private validator를 추출/변경하지 않는다.

## 7. Target consistency

모든 record에 대해 policy_id → scope → benefit_id 순서로 대응을 확인한다. 하나라도 다르면 **ACCEPTANCE_CONTEXT_TARGET_MISMATCH**다. status·날짜·선택 여부로 소속 오류를 생략하지 않는다. 전체 type 검사가 target 검사보다 먼저다.

소속은 값 일치이고 source/actual authority 검증이 아니다. raw record에 Context target을 덮어쓰거나 다른 target 기록을 조용히 버리는 필터를 제공하지 않는다.

## 8. Historical snapshot 차이와 same-release 범위

서로 다른 acceptance_ref/version의 역사 records는 i/r/b version·각 지문·dataset/Registry·implementation 지문·검토일/기한이 달라도 공존할 수 있다. Context 전체에 한 dataset·같은 지문·동일 유효기간을 강제하지 않는다. 각 record 내부의 Coverage/Benefit dataset·Registry equality는 기존 M2.46 계약대로 유지된다.

**예외는 직접 철회 edge B→A의 동일 binding 의무**다. B는 A의 정확한 과거 확인본을 철회하므로15절의11필드가 같아야 한다. 별개 ACCEPTED revisions끼리의 차이를 이 edge 검사로 확대하지 않는다.

Context는 전체 역사 쌍에 대해 같은 i/r/b version의 지문 conflict를 검색하지 않는다. 서로 다른 a revision에서 지문이 다르다는 사실만으로 여기서 오류를 만들거나 stale로 분류하지 않는다. 이것이 정의 version 재사용의 적법성을 인증하는 것은 아니다. record 대 current의 독립 same-version guards와 외부 발행 감사는 여전히 필요하다. 이 책임을 Context 유효성으로 면제하지 않는다.

## 9. acceptance_ref 유일성

Context 내 모든 acceptance_ref는 정확한 원문 문자열 기준으로 유일해야 한다. 같은 객체 두 번·동등한 별개 객체 두 번·다른 내용이 같은 ref를 쓰는 경우 모두 **DUPLICATE_ACCEPTANCE_REF**다. dedupe/overwrite/후승 선택은 없다.

ref는 비공백 여부만 검사된 opaque 문자열이다. `ACC-A`와 ` ACC-A `는 다른 identity다. Context는 전역 ref 유일성을 이 supplied collection 안에서만 확인한다. 다른 Context/폐기된 자료/누락 기록과의 충돌까지 발견하지 못하며 전역 발급 유일성은 외부 책임이다.

## 10. acceptance_version 유일성

한 target의 명시 revision이므로 Context 안의 acceptance_version도 유일해야 한다. 같은 version/다른 ref·같은 version/내용이 같은 record·다른 내용 모두 **DUPLICATE_ACCEPTANCE_VERSION**이다. 같은 ref와 version이 동시에 중복이면 ref 중복 검사가 우선한다.

서로 다른 Context target에서 같은 a0001을 쓰는 것은 정상이다. ref와 a version은 별개이며 review_artifact_ref·Benefit/Tree 지문·dataset은 유일성 key가 아니다. 여러 revision이 같은 실제 artifact를 참조할 수 있다. version 연속성이나 모든 과거 revision의 존재는 요구하지 않는다.

## 11. Tuple ordering과 equality

입력 records tuple과 원소 object identity를 보존한다. 자동 sort·copy/reconstruction·append/remove/update·정규화·dedupe는 없다. tuple index/첫 값/마지막 값은 oldest/latest/current 의미가 아니다.

4개 stored fields 전체의 일반 dataclass equality/hash를 사용한다. records 순서도 값의 일부이므로 서로 다른 원소를 재배열한 Context는 equality/to_dict가 다를 수 있다. 반면 유효한 같은 records 집합의 순열에서 각 exact ref의 조회 결과는 같은 원본 record여야 한다. invalid 입력 순열끼리 같은 첫 오류까지 보장하지 않는다.

## 12. Explicit ref resolution과 공개 경계

후속 private 함수의 정확한 이름/계약을 다음으로 확정한다. 두 인자 모두 필수이며 기존 Review resolver처럼 positional 또는 keyword로 전달할 수 있다.

```text
_resolve_benefit_acceptance(
    context: BenefitAcceptanceContext,
    acceptance_ref: str,
) -> PolicyBenefitAcceptance
```

후속 위치는 `backend/policy_engine/policy_data/benefit_acceptance_resolution.py`다. public domain type BenefitAcceptanceContext는 별도 `benefit_acceptance_context.py`에 두고 승인된 구현 단계에서 Context 한 타입만 policy_data export에 추가하는 방향이다. resolver/private helper는 export하지 않는다. 이번에는 파일·함수·export를 만들지 않는다.

장기 public 계산 경로는 future evaluator다. 이 private lookup을 행정 승인/현재 사용 검증 API로 노출하지 않는다. resolver는 Context constructor가 보장한 구조/edge를 신뢰하고 매번 Context 전체를 재검증하지 않는다.

## 13. Resolver 입력·반환 identity

검증 순서는 exact BenefitAcceptanceContext → exact 비공백 str acceptance_ref다. None/subclass/dict/context-like/빈 문자열/공백/다른 타입은 **INVALID_ACCEPTANCE_RESOLUTION_INPUT**이다. 값 보정을 하지 않으며 전체 원문 문자열 equality로만 찾는다.

찾으면 **Context에 저장된 원본 PolicyBenefitAcceptance 객체**를 반환한다. 복사·새 constructor·dict 변환·수정 없이 `resolved is context.records[i]`가 성립한다. ACCEPTED와 REVOKED 모두 조회할 수 있다. 오래된 record·철회 대상이 된 A도 명시 ref로 그대로 조회 가능하며 이 반환이 현재 사용 승인을 뜻하지 않는다.

## 14. Missing ref와 no-record 구별

유효한 Context에서 exact 명시 ref를 못 찾으면 **ACCEPTANCE_REF_NOT_FOUND**다. 빈 Context도 동일하다. None 반환·NO_ACCEPTANCE 결과·다른 record fallback·현재 snapshot에 맞는 기록 검색은 없다.

acceptance_ref=None은 resolver의 정상 no-record 입력이 아니다. no-selection/NO_ACCEPTANCE는 future 호출 준비/평가 계약으로 남긴다. Context construction의 dangling 철회 ref는 **REVOCATION_TARGET_NOT_FOUND**로 구별한다. 외부 조회 ref 누락과 내부 이력 연결 오류는 발생 단계가 다르다.

## 15. Revocation resolution과 동일 binding

Context는 모든 REVOKED B에 대해 B.revokes_acceptance_ref가 Context 전체에 존재하는지 검사한다. 존재하지 않으면 REVOCATION_TARGET_NOT_FOUND다. Context target consistency를 먼저 검사하므로 다른 target의 A를 끌어와 해결하지 않는다. local ref 인덱스는 전체 ref 유일성 확인 뒤 만들 수 있고 stored field/cache가 아니다.

대상 A의 상태 검사 후, **B와 A의 다음11필드를 모두 exact 값으로 비교**한다. shared target3개는 이미7절에서 보장한다. 아래 순서의 첫 불일치는 **REVOCATION_SNAPSHOT_MISMATCH**다.

```text
coverage_inventory_version
coverage_inventory_fingerprint
coverage_rule_version
coverage_policy_tree_fingerprint
coverage_dataset_version
coverage_source_registry_fingerprint
coverage_implementation_fingerprint
benefit_version
benefit_fingerprint
benefit_dataset_version
benefit_source_registry_fingerprint
```

M2.45 9·19·27절의 “원래 ACCEPTED의 동일 binding”을 그대로 적용한 것이다. 정의 fp만 같아도 dataset/Registry가 다르면 같은 승인 철회가 아니다. 반대로 ref/version/status/검토일/기한/artifact/revokes 값은 결정 revision마다 달라질 수 있으므로 A와 equality를 강제하지 않는다. 지문은 저장된 문자열을 비교할 뿐 재계산하지 않는다.

## 16. Revocation target status와 cycle

REVOKED는 **ACCEPTED 하나만** 지목한다. REVOKED→REVOKED는 **INVALID_REVOCATION_TARGET_STATUS**다. ACCEPTED의 revokes=None, REVOKED의 자기 ref 금지는 M2.46에서 이미 적용된다.

따라서 모든 유효 edge는 REVOKED에서 outgoing edge 없는 ACCEPTED로 끝나며 cycle이 불가능하다. 별도 DFS·generic graph·revocation-of-revocation 상태기를 구현할 필요가 없다. 재승인은 철회를 취소하는 edge가 아니라 새 ACCEPTED revision이다.

## 17. Duplicate revocation

**하나의 ACCEPTED acceptance_ref를 직접 지목하는 REVOKED는 Context 안에서 최대 한 개**만 허용한다. 서로 다른 정상 ref/version을 가진 B와 D가 같은 A를 철회하면 DUPLICATE_REVOCATION_TARGET이다. 같은 object 중복은 그 전에 ref 중복으로 거부된다.

이는 이번 supplied 이력의 명시적 MVP 제약이다. 철회 기한 경과로 두 번째 edge를 허용하지 않는다. 새 사유/검토 자료 보존은 외부 불변 자료에서 처리하며, 이 계약에 맞지 않는 중복 철회 데이터를 몰래 dedupe하거나 일부 기록을 숨기지 않는다. 향후 반복 철회 결정을 지원하려면 별도 계약 개정이 필요하다.

## 18. Re-acceptance와 같은 snapshot 재검토

A/a0001 ACCEPTED, B/a0002 REVOKED→A, C/a0003 ACCEPTED는 정상 공존할 수 있다. C는 새 독립 승인 기록이며 A/B를 수정하거나 B를 unrevoke하지 않는다. 같은 snapshot을 새 ref/version/artifact·기한으로 다시 검토하는 것도 허용한다. 철회가 선행하지 않은 A/C 재검토도 허용한다.

C가 A와 같거나 다른 정상 과거 release를 가질 수 있다. 다만 B는 지목한 A의11필드를 그대로 보존한다. 각 ACCEPTED가 실제 검토됐는지는 외부 책임이다. Context는 C를 current로 선택하거나 A를 자동 대체하지 않는다.

## 19. Chronology/version constraints

**B→A마다 B.reviewed_at >= A.reviewed_at, B의 a revision > A의 a revision을 요구**한다. 같은 검토일은 허용한다. M2.45 7·9·19·27절이 이미 “후행 revision”을 요구하므로 새 전역 chronology를 발명하는 것이 아니다.

a 문법은 M2.46의 `a(?:[0-9]{4}|[1-9][0-9]{4,})`, a0000 금지 그대로다. 의미 비교는 접두사 뒤 ASCII 십진수의 수치 순서다. a9999 < a10000이며 전체 문자열 사전식 비교를 쓰지 않는다. 검증된 suffix의 **(길이, suffix 문자열)** 비교로 같은 순서를 얻을 수 있다.4자리 구간은 같은 길이·고정 padding,5자리 이상은 선행0 금지이므로 정확하다. 큰 suffix의 int 변환 제한이나 새 최대 자리수·새 parser grammar가 필요 없다. 후속 작은 private 비교는 기존 record/helper를 수정하지 않는다.

version 검사를 모든 edge에 먼저 적용한 뒤 날짜 검사를 모든 edge에 적용한다. 둘 다 잘못된 한 edge면 INVALID_REVOCATION_ORDER의 records.acceptance_version이 우선한다. tuple 위치는 비교하지 않는다. B가 A보다 먼저 들어 있어도 전체 ref 인덱스로 정상 검증한다.

**A/B의 valid_until끼리는 관계를 요구하지 않는다.** 각 record의 reviewed_at<=valid_until만 유지한다. A 만료 뒤 B 발급 가능·B horizon 이후 철회 지속이라는 기존 의미를 보존한다. 서로 edge로 연결되지 않은 역사 records 사이에는 version/date 전체 단조성·연속 번호·latest 선택을 강제하지 않는다.

## 20. Validation precedence·결정성·복잡도

후속 constructor는 다음 **phase 순서**를 지킨다. 각 phase에서 해당 전체 records를 검사한 뒤 다음 phase로 간다. 같은 phase에서는 입력 tuple 순서, target3필드와 binding11필드는 앞서 정한 순서다. 첫 오류에서 전체 실패하며 부분 Context/정상 unusable 결과를 반환하지 않는다.

| phase | 검사 | 오류 code |
|---|---|---|
| 1 | Context policy_id exact 타입/canonical 문법 | INVALID_ACCEPTANCE_CONTEXT_INPUT |
| 2 | Context scope exact 타입 | INVALID_ACCEPTANCE_CONTEXT_INPUT |
| 3 | Context benefit_id exact 타입/canonical 문법 | INVALID_ACCEPTANCE_CONTEXT_INPUT |
| 4 | records exact tuple | INVALID_ACCEPTANCE_CONTEXT_INPUT |
| 5 | 모든 element exact PolicyBenefitAcceptance | INVALID_ACCEPTANCE_CONTEXT_INPUT |
| 6 | 모든 record의 policy_id/scope/benefit_id 소속 | ACCEPTANCE_CONTEXT_TARGET_MISMATCH |
| 7 | 전체 acceptance_ref 유일성 | DUPLICATE_ACCEPTANCE_REF |
| 8 | 전체 acceptance_version 유일성 | DUPLICATE_ACCEPTANCE_VERSION |
| 9 | 모든 REVOKED target ref 존재 | REVOCATION_TARGET_NOT_FOUND |
| 10 | 모든 target 상태 ACCEPTED | INVALID_REVOCATION_TARGET_STATUS |
| 11 | 모든 edge의11개 snapshot binding 일치 | REVOCATION_SNAPSHOT_MISMATCH |
| 12 | 모든 직접 revocation target 유일성 | DUPLICATE_REVOCATION_TARGET |
| 13 | 모든 edge의 후행 a revision | INVALID_REVOCATION_ORDER |
| 14 | 모든 edge의 검토일 순서 | INVALID_REVOCATION_ORDER |

예: 앞 record의 target 불일치보다 뒤 원소의 wrong type이 먼저다. 앞 edge의 날짜 오류보다 뒤 edge의 target 누락이 먼저다. 선택 예정 ref가 None/다른 정상 record여도 Context 안의 오류를 숨기지 않는다. expiry/current mismatch는 이 단계에서 계산하지 않는다.

전체 ref index와 set은 constructor의 지역 값으로만 허용한다. dictionary/set 평균 복잡도 기준 고정 횟수 순회이므로 records 수 n에 O(n) 시간/공간, 긴 문자열 비교/해싱 비용은 별도다. 문자열 총처리량 L을 포함하면 O(n+L) 수준을 목표로 한다. resolver는 저장 index 없이 O(n) 선형 검색·추가 O(1) 공간이면 충분하다. 캐시·정렬·DB·index framework를 선행하지 않는다.

## 21. Data Error boundary

duplicate ref/version·wrong target·dangling edge·revoke REVOKED·다른 binding·중복 철회·역전 version/date는 정상 불가 상태가 아닌 **PolicyDataError**다. current가 SLICE·record가 과거 날짜여도 구조 오류를 정상 사유/0원/UNKNOWN으로 낮추지 않는다.

반면 정상 역사 Context의 오래된 ACCEPTED를 현재 다른 확인본과 비교하면 future evaluator의 정상 unusable 후보가 될 수 있다. 독립 same-version/current 결합 모순이 있으면 그 evaluator도 Data Error를 우선해야 한다. Context가 이 비교를 수행했다거나 모든 current mismatch가 정상이라고 주장하지 않는다.

## 22. Immutability

Context의4개 필드 assignment/deletion을 거부한다. __dict__·mutable stored index·setters·record 추가/삭제 메서드는 없다. 원본 records tuple·Scope·record 객체를 보존하며 validation/resolution/serialization 전후 입력을 바꾸지 않는다.

역사 기록을 추가/정정하려면 새 immutable record와 새 Context snapshot을 공급한다. 기존 record·옛 Context를 고치지 않는다. ordinary frozen dataclass는 Python의 강제 메모리 조작까지 막는 인증 장치가 아니다.

## 23. Serialization

to_dict를 제공한다. **정확히 policy_id, scope, benefit_id, records의4key를 같은 순서로** 새 dict에 반환한다. scope는 기존 Scope.to_dict의 새 dict, records는 입력 tuple 순서의 새 list이며 각 원소는 기존 record.to_dict의 새21key dict다. 빈 records는 빈 list다.

nested status/날짜/nullable ref는 기존 M2.46 표현을 그대로 사용한다. 반환 list/dict/각 scope를 바꿔도 원본에 영향이 없어야 한다. 순서를 자동 정렬하거나 selected/latest/current/status/usable key를 더하지 않는다. 반복 serialization은 같은 값이며 서로 독립적인 가변 반환값을 만든다. 이 계약은 loader/JSON release schema나 지문 payload가 아니다.

## 24. Current usability·verification·지문과 분리

Context/resolver에는 current CoverageResult/BenefitSnapshot/PolicyEnvelope/Manifest/Registry/data_use_date가 없다. 따라서 FULL/VERIFIED·source freshness·completeness·현재 snapshot 일치·expired/stale·usable을 계산하지 않는다. Coverage evaluator/지문 함수/verification lookup/Bridge/Cashflow를 import·호출하지 않는다.

user profile/PASS/FAIL/UNKNOWN·지급주기/수단·금액/월 환산·개인 월 적용/중복·병급도 모른다. 파일·네트워크·시스템 시각·Git·환경·난수·가변 전역 cache를 사용하지 않는다. 기록 객체의 immutable 값과 supplied collection 안의 관계만 사용한다.

## 25. No latest selection과 과거 조회

max(version)·max(reviewed_at)·records[-1]·현재 snapshot matching 검색·최근 ACCEPTED fallback·철회 뒤 옛 승인 자동 복구를 제공하지 않는다. edge 순서 검증에 version을 사용해도 선택 규칙으로 전용하지 않는다.

(A,B,C)에서 ref=A를 주면 A, ref=B면 B, ref=C면 C를 그대로 반환한다. B가 A를 철회했다고 A의 stored status를 REVOKED로 바꾸거나 lookup을 C로 바꾸지 않는다. **역사 조회 성공과 현재 서비스 선택의 적절성은 다르다.** 현재 서비스에서 이미 철회된 A만 골라 공급하지 않도록 하는 선택/이력 완전성 의무는 외부에 남는다. 누락된 실제 B는 Context만으로 탐지할 수 없다.

## 26. Future evaluator·no-record workflow 후보

Context/resolver가 있어도 ACCEPTED record≠current usable이므로 작은 immutable current evaluation result가 여전히 필요하다. 이름·필드·reason Enum·trace·exact evaluator signature는 이번에 확정/구현하지 않는다.

| no-selection 후보 | 비교/후속 판단 |
|---|---|
| Context.records=()만 부재로 사용 | 빈 공급 자료는 표현하나 nonempty history에서 의도적 미선택을 표현하기 어려움 |
| 외부 acceptance_ref=None을 명시 | history 보관과 선택을 분리함. nonempty/empty Context 모두 no-selection 표현 가능하므로 **추천 방향** |
| Context=None도 허용 | 자료 미제공과 빈 supplied collection을 구별할 수 있음. 정확한 evaluator input/사유 매핑은 다음 result 설계로 넘김 |

후속 후보에서는 exact Context+str은 private resolver로 정확히 찾고, exact Context+None은 외부 no-selection 처리 후 resolver를 호출하지 않을 수 있다. empty+str은 여전히 REF_NOT_FOUND다. None Context+str을 조용한 NO_ACCEPTANCE로 낮추지 않는다. 어떤 선택이든 invalid Context의 자료를 미선택이라는 이유로 건너뛰지 않는다. resolver 자체의 strict str 계약은 바꾸지 않는다.

M2.41의 **외부 resolve된 record 또는 None을 받는 pure evaluator** 경계는 유지 가능한 기본 방향이다. 이번 지시의 Context+ref 직접 인자 API는 비교 후보이며, evaluator 내부에서 private resolution을 맡길지 외부 준비 adapter에서 수행할지는 다음 설계에서 확정한다. 어느 쪽도 자동 과거 검색·최신 선택·I/O를 허용하지 않는다. 기존 evaluator API가 이미 구현돼 있다고 가정하거나 조용히 바꾸지 않는다.

## 27. Truthfulness·이력 완전성 boundary

타입·ref·revision·철회 edge가 모두 유효한 가짜 역사 metadata도 구조적으로 만들 수 있다. Context 유효성은 실제 사람이 검토/승인/철회했다는 사실, artifact 존재/정확성, FULL/VERIFIED, 실제 지급을 인증하지 않는다.

공식 원문·원래 Snapshot/Manifest/Registry·Review/artifact·엔진 확인본의 불변 보존과 실제 교차 검토·전역 ref 유일성·철회 누락 없는 선택은 외부 자료 준비/발행 책임이다. 기록 번호의 빈틈/연속성만으로 완전성을 증명할 수 없다. 사용자/LLM이 선언한 ACCEPTED와 선택 ref를 운영 수용 근거로 신뢰하지 않는다. 서명/권한 서버/검토 플랫폼을 이번 선행조건으로 구현하지 않는다. 개인정보/경제정보를 이력에 넣지 않는다.

## 28. Current Ansan과 보류 상태

실제 안산001/002는 **PolicyEnvelope DRAFT / CONDITION_SLICE**다. generic Coverage core는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**이며 actual FULL·검토된 BenefitSnapshot/Acceptance는 없다. DRAFT는 verification 축이고 CONDITION_SLICE는 평가범위 축이지 새 Context 상태가 아니다.

실제 AcceptanceContext·승인/철회 ref·actual 혜택 금액·지문을 생성하지 않는다. 정책 혜택 Cashflow 반영0원 원칙을 유지하며, 아직 없는 Bridge의 실행 결과라고 설명하지 않는다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 공식 거주기간 의미/다른 조건·전체 목록/자료·검토 미완료를 이번 설계가 해소하지 않는다.

## 29. Synthetic examples

**문서상 합성 예시만** 사용한다. ID는 기존 grammar에 맞는 SYNTH-POLICY/SYNTH-BENEFIT이며 개념 표기의 underscore를 실제 ID로 사용하지 않는다. runtime Context·새 dataset/fixture·실제 승인 파일은 만들지 않는다. 모든 record는 M2.46 local validation에 맞게 supplied되었다고 가정한다.

target T는 SYNTH-POLICY / ApplicabilityScope(2026,Q3) / SYNTH-BENEFIT이다. A는 M2.45 30절·M2.46 합성 기준과 같은 SYNTH-ACCEPT-A1/a0001/ACCEPTED다. Coverage i0001/Inventory fp=`1`64개/r0001/Tree fp=`2`64개/SYNTH-D1/Registry fp=`3`64개/implementation fp=`4`64개, Benefit b0001/정의 fp=`5`64개/SYNTH-D1/Registry fp=`3`64개를 형식값으로 둔다. reviewed_at=2026-01-01, valid_until=2026-12-31, artifact=SYNTH-REVIEW-A1, revokes=None이다. 모든 지문은 계산하지 않은 형식용 자리값이다.

| 기호 | 차이/관계 |
|---|---|
| B | SYNTH-ACCEPT-A2/a0002/REVOKED→A. target/11 binding은 A와 동일. reviewed_at=2026-10-22, valid_until=2026-12-31, artifact=SYNTH-REVIEW-A2 |
| C | SYNTH-ACCEPT-A3/a0003/ACCEPTED, revokes=None. 기본 binding은 A와 동일. reviewed_at=2026-10-22, valid_until=2027-01-31, artifact=SYNTH-REVIEW-A3 |
| C2 | C의 양 dataset을 SYNTH-D2·양 Registry를 `6`64개로 함께 바꾼 별도 사례. 각 record 내부 same-release 유지 |
| D | 새 ref/a0004의 REVOKED→A. B도 함께 supplied되면 중복 철회 오류 |

empty T/()·(A,)·(A,B)·(A,B,C)·(B,C,A)·(A,B,C2)는 각 관계가 맞으면 정상이다. B만 넣으면 A가 없으므로 오류다. resolve(A/B/C)는 각 원본만 반환하며 C를 current로 표시하지 않는다. 이 예시는 placeholder만으로 실제 FULL/검토/사용을 승인하지 않는다.

## 30. Stable error codes와 표시 계약

기존 **PolicyDataError**를 사용한다. 새 오류 class/Enum/framework/.code 속성을 추가하지 않는다. 기존 resolver의 `CODE: 설명` convention에 맞춰 **`CODE: field: reason`** 형식의 stable prefix를 정한다. reason은 고정 설명이고 raw ref/version/날짜/지문/payload·개인정보를 메시지에 넣지 않는다. 고정 field path까지만 표시한다.

| code | 발생 조건/대표 field |
|---|---|
| INVALID_ACCEPTANCE_CONTEXT_INPUT | Context4필드의 잘못된 타입/문법 또는 wrong element. policy_id/scope/benefit_id/records |
| ACCEPTANCE_CONTEXT_TARGET_MISMATCH | record 소속 불일치. records.policy_id/scope/benefit_id |
| DUPLICATE_ACCEPTANCE_REF | ref 중복. records.acceptance_ref |
| DUPLICATE_ACCEPTANCE_VERSION | target revision 중복. records.acceptance_version |
| REVOCATION_TARGET_NOT_FOUND | Context 내부 철회 ref 누락. records.revokes_acceptance_ref |
| INVALID_REVOCATION_TARGET_STATUS | 철회 대상이 REVOKED. records.revokes_acceptance_ref |
| REVOCATION_SNAPSHOT_MISMATCH | A/B11필드 불일치. records.해당 필드명 |
| DUPLICATE_REVOCATION_TARGET | 같은 ACCEPTED의 직접 철회가 둘 이상. records.revokes_acceptance_ref |
| INVALID_REVOCATION_ORDER | 후행 revision/검토일 관계 위반. records.acceptance_version 또는 records.reviewed_at |
| INVALID_ACCEPTANCE_RESOLUTION_INPUT | resolver context/ref 잘못된 타입/공백. context 또는 acceptance_ref |
| ACCEPTANCE_REF_NOT_FOUND | 유효 Context에서 명시 조회 ref 없음. acceptance_ref |

현재 backend/tests/docs에 이11개 이름과 충돌하는 기존 오류는 찾지 못했다. 잘못된 내부 binding을 식별하기 위한 code와 resolver 입력 code를 별도로 둔 이유는 각각 기존 record 의무와 strict 함수 boundary를 분명히 하기 위해서다. 이 code들은 이번 문서 계약이며 아직 실행 코드가 아니다. M2.46 INVALID_BENEFIT_ACCEPTANCE나 frozen Coverage의 기존 오류를 rename/catch/wrap하지 않는다.

## 31. 후속 구현 순서와 완료조건

| 순서 | 최소 작업 | 완료조건/검증 |
|---|---|---|
| 다음 승인 단계 M2.48 후보 | **BenefitAcceptanceContext와 private _resolve_benefit_acceptance만 구현** | exact4필드/required keyword-only·empty/exact tuple·one target·두 유일성·전체 edge 검증/phase 오류·원본 보존·4key serializer·명시 조회/부재 오류·100회/순열 합성 tests·기존6525개 보존 |
| 이후 별도 승인 | current Acceptance evaluation result 계약 설계 | no-selection/Context 경계·typed reasons/trace·현재 비교 guard/철회 선택 한계 확정. 이번 설계의 미래 후보를 실제 API로 오해하지 않음 |
| 이후 별도 승인 | 승인된 result 값 구현 | 작고 immutable한 결과 모델과 합성 tests |
| 이후 별도 승인 | pure evaluator 계약/구현 | FULL/verification·Benefit completeness·현재 결합/독립 same-version guards·명시 날짜·선택/철회 검증 |
| 이후 별도 승인 | Benefit Bridge | 개인/월·중복/병급·유형·무환산·합산, 그 뒤 검증된 Cashflow 연결 |

후속 Context 구현의 직접 의존은 dataclasses/re·기존 PolicyDataError/ApplicabilityScope/PolicyBenefitAcceptance/BenefitAcceptanceStatus 정도면 충분하다. resolver는 Context/record/기존 오류만 사용한다. version 비교용 작은 private helper는 검증된 a suffix만 받으며 record/Coverage 공용 helper refactor·새 loader/DB/UI·generic graph/index framework를 선행하지 않는다. 기존 테스트의 구조 제한을 새로 광범위하게 고정하지 않고 해당 constructor/resolver의 실행 책임을 검증한다.

## 32. 수동 시나리오 — AC01~AC120

**120개 문서상 계약 사례이며 실행 테스트가 아니다.** 기본은29절 T/A/B/C이고 모든 변경 record는21필드 local invariant를 만족하도록 준비한다. C는 Context 구성, R은 explicit resolver, E는 향후 current evaluator, O는 외부 발행/선택 책임을 뜻한다. E 사유/입력 이름은 방향이며 이번 API 확정이 아니다.

| ID | 사례 | 기대 |
|---|---|---|
| AC01 | T, records=() | C 정상, supplied 기록 없음 |
| AC02 | exact canonical policy_id | C 타입/문법 통과 |
| AC03 | Context T와 다른 policy record | TARGET_MISMATCH |
| AC04 | 동등한 별개 Q3 Scope 객체 | C 정상, 각 원본 보존 |
| AC05 | record scope=Q4 | TARGET_MISMATCH |
| AC06 | exact benefit_id | C 통과 |
| AC07 | 다른 benefit record | TARGET_MISMATCH |
| AC08 | records=(A,) exact tuple | C 정상 |
| AC09 | records=[A] | INVALID_CONTEXT_INPUT, 변환 없음 |
| AC10 | 원소 dict/None/record subclass | INVALID_CONTEXT_INPUT |
| AC11 | A/B 서로 다른 ref | ref 유일성 통과 |
| AC12 | 같은 A 객체 두 번 | DUPLICATE_ACCEPTANCE_REF |
| AC13 | 서로 다른 a0001/a0002 | revision 유일성 통과 |
| AC14 | 다른 ref·같은 a0001 | DUPLICATE_ACCEPTANCE_VERSION |
| AC15 | (A,) | C 정상·R(A.ref)는 A |
| AC16 | (A,B) | 같은 binding/순서 충족 시 C 정상 |
| AC17 | (A,B,C) | C 정상, 과거 A/B 보존 |
| AC18 | A/C 같은 snapshot 새 ref/version | C 정상, 기간 갱신 허용 |
| AC19 | (A,B,C2) 다른 역사 release | C 정상 |
| AC20 | B→존재하는 ACCEPTED A | edge 통과 |
| AC21 | (B,) | REVOCATION_TARGET_NOT_FOUND |
| AC22 | REVOKED가 자기 ref 지목 | M2.46 record 생성에서 이미 Data Error |
| AC23 | 새 REVOKED가 B 지목 | INVALID_REVOCATION_TARGET_STATUS |
| AC24 | (A,B,D), B/D→A | DUPLICATE_REVOCATION_TARGET |
| AC25 | (B,A) | C 정상, tuple 위치 무관 |
| AC26 | B.reviewed_at=A.reviewed_at | 날짜 edge 통과 |
| AC27 | B 검토일이 A보다 이전 | INVALID_REVOCATION_ORDER |
| AC28 | R(Context,A.ref) | 원본 A 반환 |
| AC29 | R(Context,없는 비공백 ref) | ACCEPTANCE_REF_NOT_FOUND |
| AC30 | R(empty,비공백 ref) | ACCEPTANCE_REF_NOT_FOUND, no-record 반환 아님 |
| AC31 | 저장 원문 ref와 정확히 같은 문자열 | R 일치 |
| AC32 | A.ref 앞뒤 공백을 더해 조회 | exact 일치가 없으면 REF_NOT_FOUND |
| AC33 | R 성공 결과 identity | resolved is 원본 record |
| AC34 | records=(C,B,A) 입력 | 순서와 tuple 원본 보존 |
| AC35 | 더 큰 version C 함께 존재 | A.ref 조회는 계속 A |
| AC36 | 같은 record 집합 순열 | 각 ref 조회 identity 동일, equality는 다를 수 있음 |
| AC37 | a0001의 A | 기존 grammar 유지, O의 전역 진실성 별도 |
| AC38 | a0002의 B→a0001 | 후행 version 통과 |
| AC39 | tuple에서 a0003이 a0001 앞 | chronology 위반 아님 |
| AC40 | B a0001→A a0002, ref/version은 유일 | INVALID_REVOCATION_ORDER |
| AC41 | 별개 ACCEPTED의 i version 변경 | C 공존 허용 |
| AC42 | 별개 ACCEPTED의 b version 변경 | C 공존 허용 |
| AC43 | A/D1와 C2/D2 | 각 record 내부 동일 release면 공존 |
| AC44 | 별개 ACCEPTED의 지문 변경 | 전체 역사 pair conflict 계산 없음, E/O 검사 별도 |
| AC45 | 각 record 내부 Coverage/Benefit release 동일 | 기존 local invariant 유지 |
| AC46 | 내부 dataset/Registry 혼합한 raw 값 | M2.46 record constructor가 거부, Context가 복구 안 함 |
| AC47 | empty.to_dict | 정확한4key, records=[] |
| AC48 | (A,).to_dict | records 새 list 안 A의21key dict |
| AC49 | (A,B,C).to_dict | 같은 입력 순서·각 원소 값 유지 |
| AC50 | serializer 출력 순서 | 자동 version/date 정렬 없음 |
| AC51 | Context4필드 assignment/deletion | frozen 거부 예정 |
| AC52 | records append/remove 시도 | tuple/Context API에 변경 경로 없음 |
| AC53 | validation 전후 A와 Scope | 원본 object identity 유지 |
| AC54 | 현재 상태 property 요청 | usable/stale/expired 없음 |
| AC55 | selected/current_ref 필드 요청 | stored field 없음 |
| AC56 | 현재 날짜가 바뀜 | C/R 결과 불변, clock 조회 없음 |
| AC57 | 정책 VERIFIED 여부 | C/R 입력·검사 아님 |
| AC58 | max(a version) 검색 요청 | 제공하지 않음 |
| AC59 | 최신 reviewed_at 선택 요청 | 제공하지 않음 |
| AC60 | records[-1]의 의미 | 현재/최신을 뜻하지 않음 |
| AC61 | 형식만 정상인 가짜 승인 이력 | C 가능, 실제 검토/발급 인증 아님 |
| AC62 | scope annual과Q3 혼합 | TARGET_MISMATCH |
| AC63 | 같은 ref·다른 내용 record | DUPLICATE_ACCEPTANCE_REF |
| AC64 | 같은 revision·다른 ref/content | DUPLICATE_ACCEPTANCE_VERSION |
| AC65 | dangling 철회와 과거 날짜 record 동시 | REVOCATION_TARGET_NOT_FOUND, expiry로 숨기지 않음 |
| AC66 | B→REVOKED target와 다른 정상 A | INVALID_REVOCATION_TARGET_STATUS |
| AC67 | 같은 A의 두 직접 철회, 날짜가 다름 | DUPLICATE_REVOCATION_TARGET |
| AC68 | version/검토일 모두 역전 | version field의 INVALID_REVOCATION_ORDER 우선 |
| AC69 | future caller가 B.ref 명시 | R은 B 반환, 현재 계산은 E 별도 |
| AC70 | valid history와 정상 새 current snapshot | C/R 유효, E 재검토/정상 unusable 후보 |
| AC71 | A.valid_until을 지난 사용일 | C/R은 영향 없음, E 만료 판단 별도 |
| AC72 | current Coverage SLICE | C/R은 평가 안 함, E FULL gate 별도 |
| AC73 | current Policy DRAFT | C/R은 평가 안 함, E verification 별도 |
| AC74 | 빈 Context와 no-selection 후보 | 외부/E 정상 NO_ACCEPTANCE 방향, resolver 안 부름 |
| AC75 | old A를 명시 조회 | R 정상, 현재 usability 보장 아님 |
| AC76 | broken 내부 revoke ref | C Data Error, 정상 UNUSABLE로 낮추지 않음 |
| AC77 | 파일처럼 보이는 artifact/ref | 파일 조회 없음 |
| AC78 | URL처럼 보이는 artifact/ref | 네트워크 조회 없음 |
| AC79 | 과거/미래 날짜 비교 환경 | 시스템 시각 조회 없음 |
| AC80 | Git ref처럼 보이는 artifact | Git/환경 조회 없음 |
| AC81 | 같은 입력으로100회 Context 구성 | 동일 값·원본 records 보존 예정 |
| AC82 | 같은 Context/ref100회 조회 | 같은 원본 record identity 예정 |
| AC83 | 여러 유효 역사 records | 지역 index로 edge 검증, stored cache 없음 |
| AC84 | 실제 안산 Context | 이번에 생성하지 않음 |
| AC85 | 실제001/002 | DRAFT/CONDITION_SLICE 유지 |
| AC86 | 실제 정책 현금흐름 반영 |0원 원칙 유지, Bridge 실행 주장 없음 |
| AC87 | monthly/quarterly 구별 | Context는 cadence를 모름 |
| AC88 | local currency/cash 구별 | Context는 medium을 모름 |
| AC89 | 혜택 금액 | Context가 저장/계산하지 않음 |
| AC90 | 분기액 월할 요청 | Context/R에서 수행하지 않음 |
| AC91 | 사용자 PASS/FAIL/UNKNOWN | Context/R 입력/상태 아님 |
| AC92 | 사용자 소득/profile | Context에 저장하지 않음 |
| AC93 | 철회 후 새 ACCEPTED C | 정상 공존, B unrevoke 아님 |
| AC94 | 새 scope의 Context | 별도 T, 과거 Q3 승인 자동 승계 없음 |
| AC95 | 새 benefit의 Context | 별도 target |
| AC96 | 새 policy의 Context | 별도 target |
| AC97 | Context 유효 | 현재 usable을 뜻하지 않음 |
| AC98 | stored ACCEPTED | 현재 사용 승인과 다름 |
| AC99 | 명시 ref=A, C가 더 최근 | A 그대로, latest 대체 없음 |
| AC100 | 일관된 역사 Context | 행정 승인·실제 검토 사실 증명 아님 |
| AC101 | record tuple subclass/generator | INVALID_CONTEXT_INPUT, 자동 tuple 변환 없음 |
| AC102 | wrong Context/Scope subclass 또는 raw target | 해당 strict input 오류 |
| AC103 | R의 ref=None/blank/str subclass | INVALID_ACCEPTANCE_RESOLUTION_INPUT |
| AC104 | R의 context=None/dict/subclass | INVALID_ACCEPTANCE_RESOLUTION_INPUT |
| AC105 | B의11 binding 각각의 불일치 사례 | 내부 equality가 필요한 paired 필드도 함께 변경해 local invariant를 유지하면 REVOCATION_SNAPSHOT_MISMATCH |
| AC106 | B의 양 dataset/Registry를 함께 D2/G2로 변경 | record 자체 유효, A/D1 철회 Context는 SNAPSHOT_MISMATCH |
| AC107 | B의 ref/version/artifact/기한만 정상 새 값 |11 binding이 같으면 C 허용 |
| AC108 | A 만료 뒤 B 발급, B 자체 날짜 정상 | C 허용, 두 valid_until 간 관계 없음 |
| AC109 | B horizon 경과 | 철회 자동 해제/과거 A 자동 복구 없음 |
| AC110 | A a9999, B a10000→A | 수치 순서 통과, 문자열 단순 비교 금지 |
| AC111 | 정상 grammar의 매우 긴 a suffix | 새 자리수 상한/int 변환 의존 없음 |
| AC112 | 별개 ACCEPTED의 큰 version 검토일이 더 이른 경우 | 전역 날짜 단조성 강제 안 함 |
| AC113 | 새 ref/version이 같은 review_artifact_ref 공유 | 허용, artifact 유일성 key 아님 |
| AC114 | target만 다른 두 Context에 a0001 | 정상, version 유일성은 target 내부 |
| AC115 | 앞 record target 불일치+뒤 wrong element | phase5 INVALID_CONTEXT_INPUT 우선 |
| AC116 | duplicate ref+duplicate version | DUPLICATE_ACCEPTANCE_REF 우선 |
| AC117 | 앞 edge 날짜 역전+뒤 dangling edge | phase9 REVOCATION_TARGET_NOT_FOUND 우선 |
| AC118 | 반환 records list/각 Scope dict 수정 | 원본 Context/record에 영향 없음 |
| AC119 | selected ref=None 후보+supplied invalid 이력 | Context Data Error 생략 금지 |
| AC120 | 실제 철회 B 누락, A만 supplied | 누락 완전성 탐지 못함. O의 선택/감사 책임 |

표의 INVALID_CONTEXT_INPUT은 INVALID_ACCEPTANCE_CONTEXT_INPUT, TARGET_MISMATCH는 ACCEPTANCE_CONTEXT_TARGET_MISMATCH, REF_NOT_FOUND는 ACCEPTANCE_REF_NOT_FOUND, SNAPSHOT_MISMATCH는 REVOCATION_SNAPSHOT_MISMATCH의 약칭이다. 실행 테스트는 승인 후 phase별 복합 오류·11개 binding 각각·모든4필드 수정/삭제·serializer 중첩 mutation·100회/순열을 실제 검증해야 한다. 이번 문서가 아직 없는 Context 구현을 테스트했다고 주장하지 않는다.

## 33. 미해결 사항과 Assumptions

**Context의4필드·strict 타입·유일성·철회 대상/동일 binding/중복/선후 관계·오류 순서·private 조회·직렬화 계약은 닫혔다.** Context/resolver 구현을 막는 버전 의미 미결정은 없다. 후행 revision 의미는 기존 승인 계약에서 확인했다.

| 후속 항목/한계 | 상태 |
|---|---|
| Future result의 정확한 이름/필드/reasons/trace | 다음 result 설계에서 확정, Context 선행 차단 아님 |
| no-selection/Context=None와 evaluator exact 입력/API |26절 후보 비교를 다음 result/호출 경계 설계로 넘김 |
| 선택한 A가 supplied B의 철회 대상일 때 current 사용을 어떻게 차단/보고할지 | R은 A를 역사 조회할 뿐 사용 승인하지 않음. 외부 완전 선택 의무 유지, future evaluation 설계에서 명시 |
| 실제 artifact/전역 ref 유일성·철회 이력 완전성·원본 truthfulness | 외부 준비/발행·불변 보존 책임, 이 작은 Context로 인증 불가 |
| 실제 안산 FULL/거주기간·다른 조건/검토 자료 | 계속 미완료, ResidenceHistory 공식 답변 대기 |

**Assumption A1:** 정상 생성된 immutable records와 외부에서 불변 보존한 검토 자료를 신뢰된 내부 준비 경로가 공급한다. 사용자/LLM metadata를 승인 증거로 신뢰하지 않는다.

**Assumption A2:** 한 target의 역사 records 수는 대학 MVP에서 작다. 보관 순서 보존과 고정 횟수 순회가 충분하며 대규모 영구 registry/권한/정렬·검색 인프라는 선행하지 않는다.

동일 binding·ref/revision 유일성·직접 철회 최대1개·후행 version/date는 이번에 확정한 규칙이지 Assumption이 아니다. no-selection/result 후속 후보를 Context의 저장 필드나 resolver의 None 처리로 앞당기지 않는다.

## 34. 최종 판단과 검증 기록

**READY_TO_IMPLEMENT_ACCEPTANCE_CONTEXT**

정확한4필드의 한 target 불변 이력과 explicit private resolver 계약을 확정했다. 원본 identity·전체 tuple phase 검증·철회 확인본/순서·최신 선택 금지·역사 조회/현재 평가·외부 완전성/진실성 경계를 분리했다. 기존21필드 record·BenefitSnapshot/지문·동결 Coverage 변경이 필요 없다.

다음 가장 작은 작업 한 개: **BenefitAcceptanceContext와 private _resolve_benefit_acceptance만 합성 unit tests로 구현**한다. 현재 evaluation result/evaluator·verification integration·Bridge/Cashflow·actual Context를 포함하지 않는다. 이번 단계는 그 구현 승인을 대신하지 않는다.

사전 전체 pytest: **6525 passed in 16.31s**. 문서 작성 후 전체 pytest: **6525 passed in 15.47s**. 신규 실행 테스트/fixture/기대값은 추가·변경하지 않았다. 이 회귀는 기존 기능 보존 확인이며 아직 없는 Context/resolver 구현을 실행 검증한 결과가 아니다.

문서34개 절의 연속 순서·정확한4필드 표·철회 binding11필드·AC01~AC120의120개 유일/연속 ID·표 열 수·코드 블록·한국어 표기를 확인했다. 수동 사례는 후속 합성 구현 테스트의 계약이며 신규 실행 테스트 수는0개다.

사전 actual releases/pycache 제외 backend/tests/data/docs157개 파일 SHA256 대조에서 **기존157개 전부 동일·이 문서1개만 추가·수정/삭제0개·최종158개**다. 기존 PolicyBenefitAcceptance/Status·472개 tests·Snapshot292개/fingerprint74개·frozen Coverage·GV01~GV15/BV01~BV16 literal·Cashflow·기존 모든 문서/테스트/기대값·ResidenceHistory 자료를 보존했다. 실제 release6개 파일의 경로/크기/수정시각도 모두 동일하다. 실제 Context·Acceptance·철회·새 정책 지문·혜택 금액은 만들지 않았다.

## 35. M2.48 — IMPLEMENTED: 불변 이력 Context와 명시 ref 조회

`benefit_acceptance_context.py`에 BenefitAcceptanceContext를, 기존 Review resolver 패턴에 따라 별도 `benefit_acceptance_resolution.py`에 private _resolve_benefit_acceptance를 구현했다. policy_data public export에는 **BenefitAcceptanceContext 한 타입만** 추가했다. resolver·helper·상태/result를 새로 export하지 않았다.

Context는4절의 정확한4필드·순서·타입을 유지하는 frozen/slots/keyword-only dataclass다. 모든 필드는 default 없이 필수이며 빈 tuple은 정상이다. exact tuple/record/Scope를 요구하고 원래 tuple·record·Scope를 보존한다. Scope 소속은 값으로 비교하므로 동등한 별개 Scope 객체도 허용한다.

20절의14개 phase를 그대로 구현했다. 전체 원소 타입 → 전체 target → 전체 ref 중복 → 전체 version 중복 뒤에, 전체 철회 대상 존재 → 상태 →11개 binding → 직접 철회 중복 → 수치 revision → 검토일 순서로 검사한다. phase 안에서는 tuple 순서와 명세의 필드 순서를 사용한다. local ref index·set·edge tuple만 만들며 stored cache/global mutable state는 없다.

후행 revision은 기존 모델에서 검증된 suffix의 (길이, 문자열) key로 비교한다. a9999/a10000과5000자리 이상 suffix 경계도 int 변환/새 상한 없이 통과했다. REVOKED→REVOKED·대상 누락·다른 binding·같은 A의 중복 철회·역전 version/날짜는30절 PolicyDataError prefix로 전체 실패한다. 두 valid_until 간 관계나 전체 역사 날짜 단조성을 추가하지 않았다.

resolver는 exact Context → exact 비공백 str 입력을 확인한 뒤 원문 ref equality로 원본 record만 반환한다. 없는 ref는 ACCEPTANCE_REF_NOT_FOUND이고 None/blank/subclass는 INVALID_ACCEPTANCE_RESOLUTION_INPUT이다. Context/record를 재생성·재검증하거나 최신 기록을 찾지 않는다. 이미 B가 철회한 A도 명시적으로 조회할 수 있으며 **이 반환은 현재 사용 승인이 아니다**. A/B 상태를 바꾸거나 C로 대체하지 않는다.

to_dict는 정확한4key와 입력 순서의 새 records list를 반환하고 기존 Scope/record serializer를 재사용한다. equality/hash에는4필드와 records 순서가 반영된다. stored selection/current/usable/expired/stale/date/index 필드는 없다. 검토 사실·이력 완전성은 인증하지 않는다.

### 합성 테스트와 AC 시나리오 대응

신규 `tests/test_benefit_acceptance_context.py`는 **200개**다.120개 수동 사례를120개 신규 실행 테스트로 계산하지 않는다. 관련 계약군을 파라미터화/복합 테스트로 검증했으며 미래 계산은 아래처럼 남긴다.

| AC 범위/계약군 | 이번 검증과 한계 |
|---|---|
| AC01~AC21·AC23~AC44 | empty/strict 타입·소속·두 유일성·역사 공존·재검토·철회 edge·exact ref/원본 반환·순열 검증 |
| AC22·AC45~AC46 | 정상 record 생성자를 통과한 객체만 사용. self-link/내부 release 구조 오류는 기존 M2.46의472개 회귀 책임이며 Context가 재검증하지 않음 |
| AC47~AC68·AC75~AC83 |4key/순서/중첩 변경 격리·동결·현재/선택 상태 부재·strict errors·의존 경계·100회 결정성. 외부 승인 진실성 자체를 테스트한 것은 아님 |
| AC69 | B.ref 조회의 원본 반환만 검증. future evaluator 사용 결과는 미검증 |
| AC70~AC74·AC97~AC98·AC100·AC109·AC119~AC120 | 정상 current 변경/만료/FULL/verification/no-selection·철회 효과·이력 완전성/거버넌스는 후속. 현재 계산/상태를 추가하지 않았고 resolver의 None 거부·순수 역사 조회만 확인 |
| AC84~AC86 | 실제 Context/금액을 만들지 않고 실제 release6개와 기존 파일의 SHA256 보존 확인. 실제 Bridge 실행 검증 아님 |
| AC87~AC92 |4필드 reflection·함수 의존 검사를 통해 cadence/medium/amount/월 환산/user profile·자격 평가 경계 유지. 해당 계산은 구현/테스트하지 않음 |
| AC93~AC96·AC99·AC101~AC108·AC110~AC118 | 재승인/target 구분·exact 타입·11 binding·기간 비관계·수치 경계·artifact 재사용·오류 phase·직렬화 격리 검증 |

11개 binding 불일치는 각각 정상 record의 변경으로 검증했다. dataset/Registry는 대응하는 두 provenance 필드를 함께 바꾸어 record 내부 same-release를 유지했고, 명세 순서의 첫 Coverage field 오류를 기대한다. 강제 객체 훼손은 사용하지 않았다. Context의 Scope/record 재검증 부재와 resolver의 Context 재검증 부재도 호출 차단으로 확인했다.

모든4필드 reflection/annotations/slots/필수 keyword-only·수정/삭제 거부·출력 mutation isolation·각 ref 원본 identity·A/B/C의6가지 순열/100회 반복·phase별 복합 오류·고정 오류 메시지/입력 비노출을 검증했다. 의존 검사는 해당 함수의 실행 경계에 적용하며 다른 미래 모듈/함수 추가를 일괄 금지하지 않는다.

검증: 사전 전체 **6525 passed in 13.41s**, 신규 **200 passed in 0.72s**, 전체 **6725 passed in 14.67s**. 기존6525개 테스트/fixture/기대값은 수정하지 않았다. Acceptance472개·Snapshot292개·Benefit 지문74개와 Coverage/GV/BV·Cashflow 회귀를 포함한다.

**IMPLEMENTED:** BenefitAcceptanceContext·14phase 구조/철회 연결 검사·4key serializer·private explicit resolver·합성200개 테스트.

**NOT IMPLEMENTED:** AcceptanceEvaluationResult·evaluate_benefit_acceptance·current usability/만료/stale/not-yet-valid·선택한 과거 A에 대한 현재 철회 효과·no-selection/None 의미 결정·verification/source/Manifest/artifact 조회·지문 계산·Bridge/Cashflow·actual Context/Acceptance.

최종 판단: **READY_FOR_ACCEPTANCE_EVALUATION_RESULT_DESIGN**. 다음 가장 작은 작업 한 개는 **Acceptance 평가 결과와 명시 선택·철회 효과의 계약을 문서로 설계**하는 것이다. 현재 사용일/선택 경계와 typed reasons/trace를 먼저 확정하며 evaluator/Bridge 구현으로 진행하지 않는다. Context lookup을 현재 사용 승인으로 해석하지 않는다. 실제 안산 DRAFT/CONDITION_SLICE·정책 반영0원 원칙과 ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, Coverage core freeze는 그대로다.

### M2.48 최종 변경 범위

사전 actual releases/pycache 제외 backend/tests/data/docs158개 파일의 SHA256과 실제 release6개 파일의 SHA256·metadata를 확보했다. 최종 대조에서 **기존154개 동일·수정4개·추가3개·삭제0개·총161개**를 확인했다. 수정은 public export와 이 명세·DATA_MODEL.md·ARCHITECTURE.md뿐이다. 기존 Acceptance21필드/상태·Snapshot/지문·Coverage frozen source/명세·기존 모든 tests/fixture/기대값·GV01~GV15/BV01~BV16·Cashflow·ResidenceHistory 자료는 SHA256이 동일하다.

실제 release6개 파일은 **SHA256 전부 일치**하며 경로/크기/수정시각도 동일하다. 파일 내용 보존을 metadata만으로 판단하지 않았다. 새 실제 정책 도메인 지문·Context·승인/철회 기록·혜택 금액은 만들지 않았다.

문서35개 절·DATA_MODEL35개 절·ARCHITECTURE51개 절의 연속 순서·표/코드 블록·한국어 표기를 확인했다.32절의 기존 수동 AC01~AC120은120개 유일/연속 ID를 유지한다. 신규 실행 테스트200개와 수동 사례120개, 후속 evaluator/운영 진실성 범위를 구별한다.
