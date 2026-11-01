# 정책 데이터 Envelope·공식 출처 계약

작성일: 2026-10-20, Asia/Seoul. 1~25절은 **M1.9 설계 기록**, source 모델/loader는 **26~27절**, envelope 모델/loader는 **28~29절**, 최신 **M1.14 DatasetManifest 모델은 30절**을 우선한다.

최종 판단: **READY_TO_IMPLEMENT_POLICY_DATA_ENVELOPE**. 아래는 후속 구현의 계약이며 현재 지원되는 파일 형식이나 운영 데이터가 아니다. 이번 산출물은 이 문서 하나다.

위 판단과 ‘이번 산출물’은 M1.9 당시 기록이다. M1.10은 source 도메인·메모리 참조 검증만 구현했으며 production 수용 gate나 전체 envelope는 구현하지 않았다.

## 1. 목적

실제 정책의 단일 조건을 어떤 정책·공식 원문·확인본·검토 기록에 연결해 저장하고 재현할지 정한다. 정책 자격 비교와 3상태 논리는 기존 Python 엔진의 책임이다. 출처 검증 실패를 PASS/FAIL/UNKNOWN으로 변환하지 않는다.

다음 자료를 다시 확인했다.

- [M1.8 주민등록 slice](REAL_POLICY_001_RESIDENT_SLICE.md): 실제 조건 의미의 우선 근거
- [M1.5 전체 정책 분석](REAL_POLICY_001_ANALYSIS.md): 전체 조건·회차·미해결 행정 쟁점
- [정책 규칙 명세](POLICY_RULE_SPEC.md), [데이터 모델](DATA_MODEL.md), [라우팅 명세](RULE_ROUTING_SPEC.md), [아키텍처](ARCHITECTURE.md)
- 기존 `backend/policy_engine/loader.py`, `models.py`, `specialized_rules/resident_registration.py`, `adapters/resident_registration.py`: strict 키·버전·tuple·실제 데이터 차단·근거 전달 계약

기존 문서의 초기 설계 기록보다 최신 구현 절과 실제 코드를 우선했다. 이번에는 공식 행정조건을 새로 조사하거나 변경하지 않는다. M1.8의 출처 확인일을 M1.9 작성일로 재검증한 것처럼 갱신하지 않는다.

## 2. 왜 envelope가 필요한가

현재 m1.1 leaf는 요구지역·기준일 종류·근거 문자열을 표현하지만, 원문 버전과 검토 이력을 해석하지 못한다. 현재 `Policy/PolicySet`은 `synthetic=True`, `test_only=True`만 허용한다. 실제 자료를 합성 자료로 표시해서 기존 loader에 통과시키면 안 된다.

**선택:** 실제 자료에는 별도 `schema_version="policy-data-1.0"` envelope를 제안하고, 내부 트리 문법은 `rule_schema_version="m1.1"`로 명시한다. 기존 m1.0/m1.1 envelope에 키를 추가하거나 그 버전의 의미를 변경하지 않는다. 기존 loader가 이 새 형식을 거부하는 것은 정상이다.

후속 책임 경계:

```text
명시적으로 선택한 dataset release
  → manifest 및 파일 해시 검증
  → envelope / source registry / review 기록 구조 검증
  → 버전 고정·참조 무결성·freshness·사용 범위 검증
  → 검증된 단일 조건 데이터
  → 기존 의미의 Rule → Resolver → Adapter → 결과
```

앞부분은 향후 데이터 계층의 책임이며 Resolver 안에 파일·네트워크·시스템 시각 조회를 넣지 않는다. 실제 데이터를 기존 `Policy`로 투영하는 구현 방식은 별도 승인 대상이다. 플래그를 True로 바꾸어 우회하는 변환은 금지한다.

## 3. Policy metadata

정책당 한 개 envelope, 배포당 정책 ID 한 개에 선택된 edition 한 개를 둔다. 아래 필수 키는 값이 nullable인 경우에도 명시한다. 미등록 키·중복 JSON 키·문자열 숫자·날짜 자동 보정은 허용하지 않는 후속 strict 계약이다.

| 필드 | 타입 / 계약 |
|---|---|
| schema_version | 정확한 str `policy-data-1.0`. 아직 구현되지 않은 새 형식 |
| rule_schema_version | 정확한 str `m1.1`. 현재 leaf/group 문법을 그대로 사용 |
| policy_id | 내부 canonical ID. 4절 |
| policy_name | 공백뿐이지 않은 표시 이름. 명칭 변경이 ID 변경을 뜻하지 않음 |
| edition_id | 공백 없는 str. 첫 사례 `2026`. 정책 동일성과 연도별 자료를 분리 |
| jurisdiction | 완전한 내부 `RegionRef` 표현. 담당 범위이며 사용자 주민등록 사실이 아님 |
| category | 첫 계약은 `YOUTH_SUPPORT` 하나. 확인되지 않은 정책 조건을 추가하지 않는 탐색용 분류 |
| dataset_version | 이 파일이 포함된 정확한 manifest 배포 버전과 같아야 함 |
| rule_version | `r0001`부터 증가하는 정책별 규칙 버전. 10절 |
| evaluation_scope | 첫 계약은 `CONDITION_SLICE`만 허용. 전체 정책 평가는 지원하지 않음 |
| coverage | `{included_rule_ids: 비어 있지 않은 str 배열, excluded_conditions: 비어 있지 않은 str 배열}`. 첫 목록은 root의 모든 leaf ID와 집합이 같고 중복 없음. 제외 사유는 검토자용 범위 설명이며 실행 조건 아님 |
| source_bindings | `{source_document_id, document_version}`의 비어 있지 않은 배열. 같은 문서 ID 중복 금지. 8절 |
| last_verified_at | `YYYY-MM-DD` 또는 null. 사용한 모든 근거 locator가 의미 검증된 날짜의 최솟값. null 포함 시 null. 수기 최신 날짜로 덮어쓰기 금지 |
| verification_status | `DRAFT / VERIFIED / STALE`. 13절 |
| effective_from / effective_to | 각각 ISO date 또는 null. 14절. 신청기간이 아님 |
| lifecycle_status | `ACTIVE / ENDED`. 서비스 운영자의 공식 근거 기반 기록. 오래된 자료라는 이유로 ENDED를 추정하지 않음 |
| synthetic / test_only | 정확한 bool `false / false`. 데이터의 출처·사용 의도이며 gate 통과나 서비스 노출을 보장하지 않음 |
| root | m1.1 RuleNode 하나. 기존 필드명 유지. 별도 `rules` 배열을 중복 도입하지 않음 |

`source_document_ids`는 `source_bindings`에서 계산하므로 중복 저장하지 않는다. `rule_version`은 현재처럼 정책 트리 수준이고 leaf에 추가하지 않는다. 사용자 facts·신청일 실제 값·평가 결과를 envelope에 저장하지 않는다.

같은 배포 안에서 `policy_id`는 유일하고 원자·전문 leaf·group의 모든 `rule_id`도 기존 데이터셋 전역 유일성 계약을 유지한다. 여러 연도·회차 동시 실행은 이번 형식의 지원 범위가 아니다. 연도·회차 모델이 필요할 때 별도로 확장한다.

## 4. policy_id 계약

선택: **`KR-GG-ANSAN-YOUTH-BASIC-INCOME`**. 대문자 영문·숫자를 단일 하이픈으로 연결하는 내부 canonical ID이며 공식 정부 정책 ID가 아니다. 일반 ID 문법은 `[A-Z0-9]+(?:-[A-Z0-9]+)*`로 제한한다.

- 명칭·URL·공고번호·연도만 바뀌면 유지한다. `edition_id=2026`으로 해당 자료를 구분한다.
- 정책이 종료되면 같은 ID의 상태를 기록한다. 별개 사업으로 신설·분리된 것이 확인될 때만 새 ID를 발급한다.
- 공식 정책 ID는 이번에 확인되지 않았다. 내부 ID를 공식 코드로 노출하지 않는다. 추후 확인되면 별도 외부 식별자 매핑을 검토한다.
- M1.8의 `ANSAN_YOUTH_BASIC_INCOME_2026`은 문서상 후보였다. 이번 canonical ID로 정리하며 과거 문서를 수정하거나 두 ID의 실제 데이터가 이미 존재한다고 간주하지 않는다.
- `PolicyReferenceContext.policy_id`도 선택된 envelope ID와 정확히 같아야 한다.

## 5. SourceDocument

공식 문서 하나의 안정된 정체성과 특정 확인본을 표현한다. release의 registry에는 문서 ID당 정확히 한 개의 선택된 확인본만 넣는다. 같은 ID의 이전 확인본은 과거 immutable release에 보존한다.

| 필드 | 타입 / 계약 |
|---|---|
| source_document_id | 내부 안정 ID. URL이 아님. 기존 M1.8의 `ANSAN-2026-399-HWP`, `ANSAN-C0001545`, `ANSAN-B0238-1681390` 유지 |
| document_version | 문서 ID별 `d0001`부터 증가. 의미가 같아도 URL·검증일 등 저장 metadata가 변경되면 새 확인본으로 발행. 같은 쌍의 내용 덮어쓰기 금지 |
| source_type | `OFFICIAL_NOTICE / OFFICIAL_POLICY_PAGE / OFFICIAL_QUARTER_GUIDE`의 유한 enum |
| issuer | 공식 발행 기관·담당 부서를 식별하는 공백뿐이지 않은 문자열 |
| title | 공백뿐이지 않은 공식 문서 제목 |
| notice_number | str 또는 null. S1은 `안산시 공고 제2026-399호` |
| official_url | 공식 게시물·페이지의 절대 HTTPS URL |
| attachment_url | 사용한 공식 원문 첨부 URL 또는 null |
| previous_urls | 과거 게시물·첨부 URL의 중복 없는 배열. 없으면 빈 배열. 변경일은 release/review 기록으로 추적 |
| publication_date | ISO date 또는 null. 공고·게시일이며 source_date의 canonical 이름 |
| effective_from / effective_to | ISO date 또는 null. 원문 자체가 명시하는 효력 범위. 정책 규칙 범위와 같다고 자동 복사하지 않음 |
| verified_at | ISO date 또는 null. 문서 접근·식별·아래 사용 locator 의미를 확인한 날짜. HTTP 200만 확인한 날짜가 아님 |
| verification_status | `DRAFT / VERIFIED / STALE` |
| status | `ACTIVE / SUPERSEDED / WITHDRAWN`. 확인된 근거의 사용 수명 상태. 11절 |
| supersedes | 이전 `{source_document_id, document_version}` 배열. 전체 문서 대체가 공식적으로 확인된 때만 사용 |
| content_sha256 | 원문 bytes의 소문자 64자리 SHA256 또는 null. 원본 확인본의 보조 식별값. 의미 검증을 대체하지 않음 |
| locators | 6절 SourceEvidence의 비어 있지 않은 배열. ID 중복 금지 |

`source_date` 별칭과 `last_verified_at` 별칭을 SourceDocument 안에 중복 저장하지 않는다. 공고일·확인일·효력일은 서로 대체하지 않는다. 원문 날짜가 없으면 null이며 확인일로 채우지 않는다.

URL은 형식뿐 아니라 검토자가 공식 기관의 자료인지 확인한다. 현재 slice는 `www.ansan.go.kr` 및 `ansan.go.kr` 공식 사이트를 사용한다. 향후 다른 기관을 추가할 때 공식 도메인을 검토 기록에 명시한다. 로딩 시 네트워크 접속·URL 임의 추적·원문 자동 크롤링은 요구하지 않는다.

## 6. SourceEvidence / locator

| 방식 | 장점 | 한계 | 선택 |
|---|---|---|---|
| 쪽번호만 사용 | 사람이 인쇄본에서 찾기 쉬움 | 재편집·웹 페이지·다른 렌더러에서 달라질 수 있음 | 보조 metadata |
| semantic locator + 절/표/쪽 정보 | 의미 단위의 참조 유지, 문서 종류에 덜 의존 | 사람이 최초 대응 위치를 검토해야 함 | **채택** |

SourceEvidence는 SourceDocument.locators 안의 항목이다.

| 필드 | 계약 |
|---|---|
| locator_id | `[a-z][a-z0-9]*(?:-[a-z0-9]+)*`. 예: `eligibility-resident-registration`. 한 문서 안에서 유일 |
| section | 사람이 다시 찾을 항목·문단 설명. 필수 비어 있지 않은 str |
| page | 확인한 경우에만 양의 int, 아니면 null. bool 거부 |
| table_position | 확인한 표 행·열 설명 또는 null |
| meaning_summary | 근거가 지원하는 조건의 짧은 요약. 필수 str. 긴 원문 복제 금지 |
| applicable_policy_ids | 해당 근거가 실제로 적용되는 내부 정책 ID의 비어 있지 않은 중복 없는 배열 |
| verified_at | 해당 위치와 조건 의미를 확인한 ISO date 또는 null. 문서 verified_at보다 이후일 수 없음 |
| verification_status | `DRAFT / VERIFIED / STALE`. 문서 전체 접근 성공만으로 이 위치를 VERIFIED로 만들지 않음 |
| status | `ACTIVE / SUPERSEDED / WITHDRAWN` |

locator는 원격 HTML anchor나 DOM selector가 아니다. 쪽 배치가 바뀌어도 의미가 같으면 ID를 유지하고 section/page를 새 document_version에 기록한다. 같은 locator 이름 아래 조건이 바뀌면 새 확인본·검토가 필요하다. 규칙은 참조 문자열만 같다는 이유로 이전 의미를 재사용하지 않는다.

공유 문서도 허용하지만 `applicable_policy_ids`에 대상 정책이 명시되어야 한다. 다른 정책의 근거를 단지 존재한다는 이유로 참조할 수 없다. 시 공고가 특정 조건의 일부 의미만 뒷받침하면 여러 locator를 함께 연결하고 검토 기록에 각 역할을 남긴다.

## 7. Source Registry

| 방식 | 장점 | 비용 | 판단 |
|---|---|---|---|
| A. 정책 JSON 안 sources 포함 | 단일 파일로 확인 | 여러 정책의 공유 출처 중복·버전 불일치 | 미채택 |
| B. 별도 sources.json | 중앙 ID·locator 검증, 공유 출처 추적 | manifest가 정책·registry를 함께 고정해야 함 | **MVP 채택** |
| C. 정책별 source manifest | 수집 담당별 편집 분리 | 전역 중복 검증과 여러 manifest 결합 비용 | 초기 보류 |

release당 registry 한 개: `{schema_version: "source-registry-1.0", sources: SourceDocument[]}`. sources는 비어 있지 않으며 문서 ID는 유일하다. schema_version은 이 registry 파일 문법이며 규칙 문법 m1.1이 아니다.

중앙 DB·동적 플러그인·범용 registry framework를 만들지 않는다. 향후 단순 불변 tuple과 읽기 전용 ID lookup으로 구현할 수 있다. 현재 자료는 `data/synthetic/`의 4개 파일뿐이며 이 registry는 아직 존재하지 않는다.

## 8. evidence_refs 계약

`source_document_id#locator_id` 형식을 사용한다. `#`는 정확히 하나이고 양쪽은 비어 있지 않아야 한다. document ID는 4절 ID 문법, locator는 6절 문법을 따른다. URL·자유문장·임시 DOM selector를 참조 대신 넣지 않는다.

resolve 순서:

1. envelope의 source_bindings에서 해당 문서 ID와 **고정 document_version**을 찾는다.
2. manifest의 source_versions와 registry의 같은 ID/version이 모두 일치하는지 확인한다.
3. registry에서 locator를 찾고 target policy 적용 범위·status·검증일을 확인한다.
4. review 기록의 해당 rule_version과 정확한 source binding이 일치하는지 확인한다.

이후에만 공식 URL과 사람이 읽을 위치로 연결한다. 최신 문서 버전을 자동 선택하는 fallback은 없다. 전체 root의 leaf evidence_refs 합집합에서 문서 ID를 추출한 집합과 source_bindings의 ID 집합은 같아야 한다. 사용하지 않는 자료는 이 policy binding에 넣지 않는다. registry 자체에는 다른 정책에서 사용하는 자료가 있을 수 있다.

모든 leaf는 최소 하나의 참조를 가져야 하며 한 leaf 안의 동일 참조 중복은 production gate에서 거부한다. group은 현재처럼 children 근거의 합집합을 결과에 만들며 JSON group에 evidence_refs를 추가하지 않는다.

## 9. Policy/User evidence 분리

| 구분 | 보관 위치 / 역할 |
|---|---|
| Policy Evidence | Source Registry. 공식 정책 문서와 규칙 요구의 근거 |
| User Evidence | 요청의 ResidentRegistrationFact.source 및 결과 details.evidence. 해당 사용자 사실의 provenance |

SELF_REPORTED / MANUALLY_VERIFIED / OFFICIAL_DATA는 SourceDocument 종류가 아니다. OFFICIAL_DATA enum을 지정해도 공식문서 registry에 사용자 기록을 추가하거나 진위를 인증하지 않는다. 같은 사실이라면 source 때문에 판정 상태를 바꾸지 않는다.

registry·manifest·review에는 사용자 소득·주소·주민등록번호·fact·시나리오 입력을 넣지 않는다. 초기 MVP의 요청 단위 계산·사용자 경제정보 비영구 저장 원칙을 유지한다.

## 10. schema/dataset/rule version

| 버전 | 의미 / 변경 기준 |
|---|---|
| schema_version | envelope 파일 문법. 제안 `policy-data-1.0`. registry/manifest/review도 각자의 명시적 형식 버전을 가짐 |
| rule_schema_version | root 트리 문법. 현재 m1.1을 재사용. 불명 버전 추정·fallback 금지 |
| dataset_version | 한 배포의 정책·출처·검토·freshness 설정을 모두 고정하는 유일 문자열. 재사용·덮어쓰기 금지 |
| rule_version | 정책별 정규화된 계산 정의 버전 `r0001`…; 연산·요구값·날짜 바인딩·트리 구조·edition 또는 조건 커버리지 변경 시 증가 |
| document_version | 문서 ID별 확인본 metadata/locator 버전 `d0001`…; URL·오타·검증일 등만 달라도 새 확인본 |

dataset_version은 dataset_id를 포함한 전역 구별 가능한 값으로 권장한다. 예: `ansan-youth-2026-10-20-001`. 같은 문자열을 다른 release에 재사용하지 않는다. r/d 버전은 정책/문서 ID와 함께 비교하며 숫자 순서를 사용한다.

rule_version의 계산 정의에는 evidence_refs 문자열·URL·검증일 같은 비계산 metadata는 포함하지 않는다. 근거만 갱신해 같은 rule_version을 유지하더라도 새 dataset_version·정확한 파일 해시·review binding으로 변경을 재현한다. 같은 policy_id/rule_version에 서로 다른 계산 정의를 발행하면 거부한다.

버전 재사용 검사는 발행 단계에서 보관 중인 승인 release의 동일 ID/버전과 대조한다. 처음 보는 파일만으로 과거 덮어쓰기를 탐지할 수 있다고 주장하지 않는다. 런타임은 선택된 immutable manifest의 hash·binding 정합성을 확인하고, 발행 검토는 기존 이력과의 동일성을 확인한다. 계산 정의 비교는 구조와 값·타입·순서를 기준으로 하며 의미가 같을 것이라는 자동 추정을 하지 않는다.

현재 `EvaluationContext.dataset_version`에는 선택한 manifest의 정확한 버전을 전달해야 한다. 단일 `evaluate_policy_tree`가 이를 envelope와 대조한다고 가정하지 않고 향후 데이터 경계가 확인한다. ENGINE_VERSION은 기존 호환 표식이며 빌드 전체 지문이 아니다. manifest에 별도 engine_artifact_sha256을 둔다.

## 11. 변경·supersede 계약

| 변경 | source 확인본 | rule_version | dataset_version | policy_id / 수명 처리 |
|---|---|---|---|---|
| A. URL만 변경, 조건 동일 | 같은 ID, 새 d버전, previous_urls와 재확인 기록 | 유지 | 새 배포면 증가 | 유지 |
| B. 오타 수정, 의미 동일 | 같은 문서 수정이면 새 d버전. 별도 공식 정정공고면 새 문서 ID | 유지, 의미 동일 검토 필수 | 증가 | 유지 |
| C. 신청기간 변경 | 해당 source 새 확인본/정정문 등록 | **현재 주민등록 slice는 유지**. 향후 ApplicationWindow 버전은 그 계약에서 변경 | 증가 | 유지. 신청창을 주민등록 root에 섞지 않음 |
| D. 자격조건 변경 | 변경된 근거와 적용 범위 확인 | 해당 계산 정의·커버리지가 바뀌면 증가. slice 밖 변경이면 slice r버전 유지 | 증가 | 같은 사업이면 유지 |
| E. 정책 종료 | 공식 종료 근거 등록·review | 계산 정의가 같으면 유지 | 증가 | ID 유지, lifecycle_status=ENDED. 현재 추천 제외 |

출처 수명(status)과 검증 상태(verification_status)는 독립이다. SUPERSEDED는 오래되었다는 뜻이 아니라 공식 대체 관계가 확인되었다는 뜻이다. 종료된 정책의 과거 공고는 역사 근거로 ACTIVE일 수 있다.

전체 대체는 새 SourceDocument.supersedes에 이전 ID/version을 기록하고 현재 release에서 이전 문서를 SUPERSEDED로 표시한다. 참조 대상은 현재 또는 이전 manifest의 정확한 확인본으로 해석 가능해야 한다. 자기 참조·순환·존재하지 않는 대체 대상은 거부한다.

부분 정정이면 전체 문서를 일괄 SUPERSEDED로 만들지 않는다. 영향을 받은 기존 locator를 새 확인본에서 SUPERSEDED로 표시하고, 정정문 locator에 새 active binding을 연결해 review에 대체 범위를 기록한다. 다른 유효 locator는 유지할 수 있다. S3이 게시됐다는 이유만으로 S1 전체를 대체했다고 간주하지 않는다.

과거 release는 수정하지 않는다. 이미 대체된 과거 확인본을 예전 manifest로 재현하는 것은 명시적 감사용 replay만 허용한다. 현재 서비스용 load에서 역사 모드를 암묵적으로 선택하지 않는다.

## 12. freshness

canonical 날짜는 **publication_date(출처 발행일), verified_at(출처·locator 확인일), last_verified_at(정책 근거 확인일의 최솟값)**이다. source_date는 publication_date에 대응하는 기존 문서 용어이며 새 JSON 별칭을 만들지 않는다.

최소 판정 입력은 명시적인 `data_use_date`, source/locator verified_at, verification_status, manifest의 `freshness_max_age_days`다. data_use_date는 현재 자료를 사용할 날짜이며 사용자 신청일이나 과거 `EvaluationContext.as_of`를 대신 넣어 최신성 제한을 우회하지 않는다.

**MVP 설계 기본값:** `freshness_max_age_days=7`을 manifest에 명시한다. 이는 행정 규정이 아닌 팀의 재검토 주기 결정이며, 정책 10~15개를 수동 검토하는 초기 운영 기준이다. 문서 작성만으로 주기 작업이나 자동화를 생성하지 않는다.

사용 가능 기간은 `verified_at <= data_use_date <= verified_at + 7일`처럼 양끝 포함이다. 최대 나이는 manifest의 양의 정수만 허용하고 bool은 거부한다. 확인일 누락·미래 확인일·derived 날짜 불일치는 VERIFIED 수용 불가다. publication_date=null 자체는 거부 사유가 아니다.

새 분기 안내, 정정공고, 조건 문구·첨부 변경, URL 변경·접근 실패를 검토 과정에서 발견하면 기간 내라도 STALE로 돌리고 재검토한다. 일시적 접근 실패만으로 정책 종료·조건 FAIL을 만들지 않는다. 날짜 계산만으로 변경을 탐지할 수 없으므로 팀 검토자가 상태 변경을 기록해야 한다. 런타임은 저장 상태가 VERIFIED여도 나이 제한 초과를 다시 검사한다.

## 13. verification status

MVP는 **DRAFT / VERIFIED / STALE** 세 개를 채택한다.

| 상태 | 의미 / 전이 |
|---|---|
| DRAFT | 수집 중이거나 검토 미완료. VERIFIED로 가려면 16절 gate 전부 충족 |
| VERIFIED | 지정 확인본과 적용 locator를 대조하고 검토 승인 완료. 법적 자격 확정은 아님 |
| STALE | 확인 기한 경과 또는 새 변경·접근·해석 문제로 재검토 필요. VERIFIED 복귀는 새 확인본·검토·배포 필요 |

REVIEWED는 review 기록으로 표현하므로 별도 상태를 두지 않는다. SUPERSEDED는 11절의 출처 수명 상태에 두고 이 enum과 섞지 않는다. 정책 VERIFIED는 모든 사용 source/locator가 VERIFIED·ACTIVE이며 review와 freshness 검증까지 완료된 경우에만 인정한다.

stale 처리 선택:

| 옵션 | 비교 | 결정 |
|---|---|---|
| A. 평가 차단 | 잘못된 최신 정책 결과 노출 방지, 안내는 별도 필요 | 현재 서비스용 데이터 load/preflight에 적용 |
| B. 평가 + warning | 사용자가 경고를 놓치거나 LLM이 과장할 수 있음 | 현재 추천 경로에 미채택 |
| C. production 추천 제외 | 오래된 자료를 현재 후보로 사용하지 않음 | **MVP 기본 정책** |

C를 A로 집행한다. STALE 자료가 있는 release는 현재 서비스용 load/preflight를 **전체 REJECT**한다. 조용히 해당 정책만 건너뛰어 manifest와 실행 집합이 달라지게 하지 않는다. 필요하면 검토자가 제외한 정책 목록을 명시한 새 release를 발행한다. 사용자는 ‘정책정보 재확인 필요’ 안내를 받을 수 있지만 엔진 상태를 FAIL/PASS/UNKNOWN으로 새로 만들지 않는다.

감사용 replay는 과거 자료를 재현할 수 있으나 WARN을 기록하고 현재 추천·자격 안내에 사용하지 않는다. replay 허용이 일반 loader의 우회 옵션이 되어서는 안 된다. 역사 실행 모드 자체 구현은 후속 범위다.

## 14. effective date

publication_date는 발행일, verified_at은 확인일, effective_from/to는 규칙 또는 문서의 효력 범위다. 서로 독립이다. 명시적인 공식 근거가 없으면 null이며 공고일·연도 첫날·신청기간으로 채우지 않는다.

알려진 날짜 범위는 날짜 정밀도의 양끝 포함으로 저장한다. 공식 문서가 이 의미를 지원하지 않거나 시각 단위 해석이 필요하면 날짜로 절삭하지 않고 미해결로 기록한다. 양끝이 모두 있으면 from <= to여야 한다.

null은 그 방향으로 무제한 유효하다는 뜻이 아니라 **UNKNOWN**이다. 첫 CONDITION_SLICE는 호출자가 edition과 명시적 신청일을 선택하고 이 한계를 확인하는 범위에서 저장·조건 평가를 허용할 수 있다. 효력일 미확인에 WARN을 기록하며 전체 정책의 현재 효력을 보증하지 않는다. 날짜에 따라 자동으로 전체 정책 버전을 선택하는 기능은 미지원이다.

## 15. application period와 차이

effective period는 규칙 효력이고 application period는 사용자가 접수할 수 있는 회차·시각 범위다. 신청기간 종료가 주민등록 조건 미충족을 뜻하지 않으며, 규칙 효력이 있다고 현재 접수 중이라는 뜻도 아니다.

ApplicationWindow 필드·타입·OPEN/CLOSED 판정은 이번에 추가하지 않는다. 초본 발급일, 분기 연령 기준일, 자동·소급신청 효력일도 APPLICATION_DATE의 자동 대체값이 아니다. 근거 registry에 해당 위치를 기록하는 것과 그 조건을 실행 엔진에 구현하는 것은 별개다.

## 16. production acceptance gate

이 gate는 **실제 데이터의 저장·조건 범위 수용** 계약이다. 검증된 단일 leaf를 전체 정책 추천에 사용할 수 있게 하는 gate가 아니다.

| 순서 | 최소 통과 조건 |
|---|---|
| G1 문법 | 명시적 지원 schema/rule_schema, 필수 키·정확한 타입·unknown key·JSON 중복 키 검증 |
| G2 ID·범위 | 정책/전역 rule ID 유일, edition·CONDITION_SLICE·coverage 정확, root 구조 검증 |
| G3 플래그 | 실제 envelope의 synthetic/test_only 모두 정확한 false. m1.1 합성 경로와 분리 |
| G4 공식성 | 공식 출처 1개 이상, 기관·제목·공식 URL·사람용 locator 존재. 발행일 미확인은 명시적 null 허용 |
| G5 참조 | 모든 leaf evidence_refs resolve, binding/manifest/document_version 정확히 일치, target policy 적용 범위 일치 |
| G6 검증·수명 | 사용 source/locator ACTIVE·VERIFIED·verified_at 존재, 정책 derived last_verified_at 일치, 새 대체·철회 문제 없음 |
| G7 freshness | 명시적 data_use_date와 manifest 재검토 기준 통과. 날짜만 바꿔 재검증한 것으로 표시 금지 |
| G8 review | 준비자·별도 검토자·검토일·대상 rule/source 버전·수동 사례 검토·APPROVED 기록 존재 |
| G9 release | 정확한 정책·registry·review 파일 해시 및 버전 목록 manifest와 일치. 부분 수용 없이 전체 검증 성공 |

통과하면 **ACCEPT(CONDITION_SLICE)**다. 이 scope의 전체 정책 추천·신청가능 표시 요청은 **REJECT**한다. 앞으로 FULL_POLICY 수용은 모든 필수 조건 커버리지와 효력·회차 모델 설계 후 별도 버전/승인으로 다룬다. 이번 모델에 허위 FULL_POLICY 값을 넣지 않는다.

데이터 계층의 ACCEPT / REJECT / WARN은 엔진의 PASS / FAIL / UNKNOWN과 다른 축이다. WARN은 수용 가능한 한계를 명시한 부가 결과이며 REJECT 사유를 덮지 못한다. 판정 우선순위는 REJECT > WARN > ACCEPT다.

## 17. review 기록

| 방식 | 비교 | 선택 |
|---|---|---|
| rule마다 개인 이름 저장 | 반복·변경 노이즈, leaf의 계산 책임과 무관 | 미채택 |
| release review manifest | 3명 팀의 준비·교차검토 추적, 내용 hash에 연결 가능 | **채택** |

release의 `reviews.json`을 `{schema_version: "policy-review-1.0", dataset_version, records: [...]}`로 제안한다. record 필수 필드:

```text
policy_id, edition_id, rule_version,
prepared_by, reviewed_by, reviewed_at,
source_bindings, manual_scenario_ids, decision, review_note
```

prepared_by/reviewed_by는 실명 대신 팀 내부 handle이며 서로 달라야 한다. reviewed_at은 ISO date, decision은 `APPROVED / CHANGES_REQUESTED`. manual_scenario_ids는 중복 없는 비어 있지 않은 목록이다. release에 포함된 정책마다 정확히 하나의 APPROVED record가 있어야 한다. source_bindings는 envelope의 고정 확인본 목록과 같아야 한다. 검토일은 모든 근거 verified_at 이상이어야 하며 data_use_date 이후일 수 없다.

팀원 3명이 수집하더라도 준비자 1명·별도 검토자 1명의 교차검토면 충분하다. 플랫폼 인증이나 전자서명까지 도입하지 않는다. 가상의 팀원 승인이나 실제로 하지 않은 재검증 기록을 생성하지 않는다. M1.8 사용자 승인은 조건 의미에 대한 승인이고 실제 release 검토 완료를 뜻하지 않는다.

## 18. DatasetManifest

release 단위의 immutable 선택 목록이다.

| 필드 | 계약 |
|---|---|
| schema_version | `dataset-manifest-1.0` |
| dataset_id | 예: `ansan-youth`. 여러 배포를 묶는 내부 ID |
| dataset_version | 한 release의 유일 버전. 디렉터리명·정책·reviews와 같아야 함 |
| created_at | 실제 발행 시 기록하는 timezone 포함 ISO datetime. 지금 임의 발행시각을 만들지 않음 |
| freshness_max_age_days | 명시적 양의 int. MVP 기본값 7 |
| engine_version | 실행 호환 버전. 기존 상수 의미 유지 |
| engine_artifact_sha256 | 재현에 사용한 엔진 소스 배포물/빌드의 정확한 SHA256. 단순 상수를 지문으로 대체하지 않음 |
| policy_versions | `{policy_id, edition_id, rule_version, path, sha256}` 배열. 한 정책당 한 항목 |
| source_registry | `{path, sha256}` |
| source_versions | `{source_document_id, document_version}` 배열. registry 항목과 집합이 같고 ID 중복 없음 |
| review_manifest | `{path, sha256}` |

해시는 파일의 실제 UTF-8 bytes 기준 SHA256이다. 순서나 공백만 바뀌어도 새 release다. manifest 자신을 파일 해시 목록에 넣는 자기참조를 만들지 않는다. path는 release 내부 상대 경로만 허용하며 절대 경로·`..`·release 밖으로 벗어나는 경로는 거부한다.

manifest 안에 사용자 입력이나 사용자 결과를 저장하지 않는다. What-if Before/After는 **같은 manifest bytes, dataset_version, 규칙/근거 확인본, engine artifact, freshness 판단 기준**을 고정하고 입력만 바꾼다. 비교 도중 최신 release를 재조회하지 않는다. 입력을 영구 저장하지 않아도 한 요청 내 같은 입력·자료·엔진으로 재실행 가능해야 한다는 기획의 재현성을 보존한다. 장기 재현을 위해 경제정보를 서버에 저장하는 기능을 추가하지 않는다.

배포 중 파일 교체 없이 완성된 release 전체를 선택한다. 임시 ‘latest’에 기대지 않고 명시적 manifest를 사용한다. 현재 artifact hash나 release 파일을 이번에 발행하지 않는다.

## 19. resident slice 적용 예시

**문서상 대입이며 생성된 JSON이 아니다.** 아래 version은 첫 발행 시의 후보 이름이다. 현재 VERIFIED production 자료가 존재한다는 뜻이 아니다.

| 관계 | 대입 |
|---|---|
| Policy | policy_id=`KR-GG-ANSAN-YOUTH-BASIC-INCOME`, policy_name=`2026년 안산시 청년기본소득`, edition_id=`2026` |
| 형식 | schema_version=`policy-data-1.0`, rule_schema_version=`m1.1` |
| 범위 | evaluation_scope=`CONDITION_SLICE`; included=`ANSAN_YBI_2026_RESIDENT_AT_APPLICATION`; excluded=연령·거주기간·국적/등록분류·신청창/절차·지급 조건 |
| 지역·분류 | jurisdiction=`GYEONGGI/ANSAN`, category=`YOUTH_SUPPORT` |
| 트리 | root는 M1.8 candidate leaf 그대로. kind=rule, rule_type=resident_registration, required_region=GYEONGGI/ANSAN, reference_date_source=APPLICATION_DATE |
| 근거 1 | `ANSAN-2026-399-HWP#eligibility-resident-registration` → 공고 제2026-399호 / 신청개요·신청대상·거주요건 산정 주석 |
| 근거 2 | `ANSAN-C0001545#eligibility-resident-registration` → 정책 페이지 / 사업개요·지급조건 첫 항목 |
| 근거 3 | `ANSAN-B0238-1681390#eligibility-resident-registration` → 3분기 안내 / 지급 대상 설명 문장 |
| 버전 후보 | rule_version=`r0001`, 세 source의 document_version=`d0001`을 각각 binding. dataset_version=`ansan-youth-2026-10-20-001`은 설명용 미발행 후보 |
| 발행일 | publication_date: S1=2026-02-19, S2=null, S3=2026-08-31. M1.8 확인 기록에서 가져옴 |
| 확인일 | verified_at 후보=2026-10-20. 새 계약의 locator별 대조·review가 완료된 이후에만 VERIFIED로 수용. derived last_verified_at은 그때 최솟값으로 계산 |
| 효력 | effective_from/to=null. 전체 규칙의 효력일이 공식적으로 확정됐다고 추정하지 않음 |
| 상태 | 현재 대입은 DRAFT, lifecycle_status 후보 ACTIVE. 실제 release review·공식 상태 확인을 완료했다고 주장하지 않음 |
| 플래그 | 실제 데이터 envelope의 목표는 synthetic=false, test_only=false. 현재 코드로는 로드 불가 |

세 SourceDocument의 official_url·attachment_url·기관·제목·locator는 M1.8 3~4절을 그대로 대응시킨다. S1 content_sha256은 M1.8의 `b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106`, S2/S3의 원문 bytes hash는 이번에 확인하지 않았으므로 null이다. release JSON 파일 해시는 실제 발행 시 별도로 계산한다.

M1.8의 `m1.8-resident-slice-draft.1`은 미발행 문서 후보였으며 이번 `r0001` 후보의 선행 설계 기록이다. 과거 실행 버전을 덮어쓴 이관으로 취급하지 않는다. 처음 source_binding·수동 사례 21개·review를 묶어 저장할 때 기존 확인본과 조건 일치를 다시 대조한다.

**적용 결과:** 정책 → root → stable evidence_refs → 문서 확인본 → locator로 자연스럽게 연결된다. 주민등록 PASS는 전체 정책 신청 가능을 뜻하지 않는다. 이번 예시는 새 gate에서 아직 DRAFT이므로 **현재 release 수용 결과는 REJECT**이고, 계약의 표현 가능성은 충족한다.

## 20. broken reference 처리

| 상황 | 현재 서비스용 데이터 load |
|---|---|
| 없는 source_document_id, 누락 metadata, 없는 locator | REJECT |
| envelope binding / manifest / registry의 document_version 불일치 | REJECT. 최신판 자동 대체 금지 |
| APPROVED review가 다른 rule_version 또는 다른 source 확인본을 검토 | REJECT |
| ACTIVE rule이 SUPERSEDED/WITHDRAWN 문서·locator를 참조 | REJECT. rule의 조건 충족 여부와 별개 |
| 다른 정책 전용 locator 참조 | REJECT. 해당 target policy가 적용 목록에 없으면 연결 불가 |
| stale·미검증 source 또는 locator, 확인일 누락 | REJECT. 정상 UNKNOWN으로 치환하지 않음 |
| URL 변경이 등록됐고 동일 의미·새 확인본·review·manifest가 모두 일치 | ACCEPT. previous_urls로 추적 |

rule_version과 document_version은 서로 다른 이름 공간이므로 문자열이 같아야 한다는 규칙이 아니다. **review가 승인한 조합과 manifest에 고정된 조합이 같은지** 검사한다. 내부 ref resolve 실패와 외부 URL 일시 접근 불가는 다르며, 런타임 URL 접속을 resolve의 필수 단계로 삼지 않는다. 검토 중 접근 실패를 확인한 경우에는 freshness 절차로 STALE 처리한다.

## 21. 파일/디렉터리 구조

현재 존재: `data/synthetic/README.md`, `profile.json`, `policies.json`, `policies_m11.json`. 아래는 **향후 배치 제안**이며 디렉터리·파일을 이번에 만들지 않는다.

```text
data/
  synthetic/                         기존 파일 유지
  releases/
    ansan-youth-2026-10-20-001/        미발행 예시
      manifest.json
      policies/
        KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json
      sources.json
      reviews.json
```

정책 파일은 이미 정규화된 envelope이므로 별도 `normalized/`와 복제하지 않는다. 고정 파일명은 manifest/sources/reviews의 각 역할을 나타내고 policy 파일명은 `{policy_id}__{edition_id}.json`이다. 첫 edition 문법은 4자리 연도 str로 제한한다. 다른 edition 체계는 별도 확장한다.

원문 전체를 저장소에 복제하는 raw 폴더는 지금 요구하지 않는다. 링크·짧은 의미 요약·확인본 hash를 사용한다. 원문 확인본 장기 보존이 필요해지면 저작물 보관과 저장 위치를 별도로 결정한다. URL이 사라졌을 때 원문 자체를 복원할 수 있다는 보장은 하지 않는다. 재현은 구조화 데이터와 당시 연결 기록 기준이다.

## 22. 수동 검증 시나리오

**28개 설계 검증 사례**다. 실행된 신규 테스트가 아니다. 기본 전제는 지원 형식, 무결한 파일/manifest, 올바른 공식 근거, 승인된 별도 검토, 7일 이내 확인, CONDITION_SLICE 사용이다. REJECT가 있으면 부가 WARN보다 우선한다.

| ID | 변경 상황 | 기대 | 근거 |
|---|---|---|---|
| E01 | 유효 source·locator·버전 고정·review 일치 | ACCEPT | 조건 범위 자료로 수용 |
| E02 | evidence_ref의 문서 ID 없음 | REJECT | broken ref |
| E03 | 문서는 있으나 locator 없음 | REJECT | 위치 손실 |
| E04 | URL만 변경, 새 d버전·previous_urls·재검토·새 release | ACCEPT | r버전 유지, dataset 변경 |
| E05 | 규칙 불변, 출처 재확인일만 변경, 새 d버전·review·release | ACCEPT | r버전 유지, 같은 배포 덮어쓰기 금지 |
| E06 | 요구지역 변경했으나 같은 rule_version | REJECT | 계산 정의 버전 재사용 |
| E07 | 공식 정정공고의 새 ID와 locator로 binding 전환, 영향 규칙 새 r버전·review | ACCEPT | 새 근거와 정의 일치 |
| E08 | source.status=SUPERSEDED인데 현행 rule이 참조 | REJECT | 대체된 근거로 현재 판정 금지 |
| E09 | source VERIFIED지만 verified_at=null | REJECT | 검증 기록 불완전 |
| E10 | source 또는 locator가 STALE | REJECT | 현재 서비스 release 부적격 |
| E11 | 미지원 schema_version 또는 rule_schema_version | REJECT | 형식 추정 금지 |
| E12 | 동일 release에 duplicate policy_id | REJECT | edition이 달라도 첫 계약은 중복 불허 |
| E13 | registry에 duplicate source_document_id | REJECT | 선택 확인본 모호 |
| E14 | 새 dataset_version으로 전 파일·목록·hash 일치 | ACCEPT | 새 immutable release |
| E15 | 다른 정책 전용 locator를 참조 | REJECT | applicable_policy_ids 불일치 |
| E16 | 발행일 null, 확인일·공식성·검토는 정상 | ACCEPT | 발행일 추정 불필요 |
| E17 | effective_from/to=null인 승인된 CONDITION_SLICE | WARN | 조건 범위 저장·평가만 허용, 전체 효력 보증 없음 |
| E18 | valid slice를 전체 정책 추천·신청가능 표시로 요청 | REJECT | 범위 위반 |
| E19 | verification_status=DRAFT 또는 review 미승인 | REJECT | 수집 중 자료 |
| E20 | manifest source version과 registry version 다름 | REJECT | 버전 pin 위반 |
| E21 | source는 일치하지만 review의 rule_version 다름 | REJECT | 검토 대상 불일치 |
| E22 | 검토일=10/20, data_use_date=10/27, 최대 나이7일 | ACCEPT | 기한 끝날 포함. 다른 WARN 없는 전제 |
| E23 | 위 조건에서 data_use_date=10/28, 저장 상태 VERIFIED | REJECT | 기한 초과를 runtime preflight에서 탐지 |
| E24 | 역사 replay로 오래된 immutable release 확인 | WARN | 감사 전용. 현재 추천 사용 금지 |
| E25 | 동일 dataset_version 아래 policy bytes 교체 | REJECT | manifest hash 또는 기존 release 불변성 위반 |
| E26 | 신청기간만 변경, resident r버전 유지·source/release 갱신·review | ACCEPT | application period와 resident 조건 분리 |
| E27 | 정책 종료가 확인된 release를 현재 추천용으로 요청 | REJECT | lifecycle_status=ENDED. 보관·감사와 분리 |
| E28 | manifest path가 `../`로 release 밖을 가리킴 | REJECT | 고정 자료 범위 이탈 |

E01 등의 ACCEPT 전제에는 이미 명시적으로 허용된 효력 범위가 있거나 해당 한계가 별도 검토된 경우를 둔다. 실제 resident 예시는 E17의 null 효력일 외에도 현재 DRAFT이므로 REJECT가 우선한다.

## 23. 결정사항

1. 실제 정책 envelope는 별도 `policy-data-1.0`, 내부 leaf 문법은 기존 m1.1이다. 현재 합성 제한을 임의 해제하지 않는다.
2. 연도 없는 내부 canonical policy_id와 별도 edition을 사용하고 첫 지원은 CONDITION_SLICE다.
3. release별 sources.json과 stable 문서 ID·semantic locator를 채택한다. 기존 M1.8 출처 ID는 유지한다.
4. refs 자체는 짧게 유지하고 source_bindings + manifest로 정확한 document_version을 고정한다.
5. 실제 데이터는 broken ref를 허용하지 않으며 검증 실패를 정책 UNKNOWN으로 감추지 않는다.
6. 3개 검증 상태와 별도 수명 상태를 사용한다. 확인일·발행일·효력일·신청기간을 분리한다.
7. 명시적 7일 재검토 기한과 stale 추천 제외를 채택하고 release 전체 preflight 차단으로 집행한다.
8. 별도 리뷰 파일에 팀 handle·교차검토·대상 버전·사례를 기록한다. manifest와 SHA256으로 고정한다.
9. What-if는 같은 release·엔진을 고정하며 사용자 경제정보 영구 저장을 추가하지 않는다.

이 결정은 이번 설계안의 권고 계약이며 코드·운영 배포 승인이 아니다. 선택 가능한 내부 설계는 위와 같이 정리했고 행정적 미확정 사실은 추정하지 않았다.

## 24. 미결정사항

- 후속 구현에서 실제 envelope를 담을 불변 도메인 타입과 기존 Policy의 공통 규칙 검증을 공유하는 정확한 방법. 기존 모델의 합성 제한을 제거하거나 실제 데이터를 True로 바꾸는 우회는 허용하지 않는다.
- 첫 release의 실제 준비자·검토자 handle, 검토일·발행시각·배포버전·artifact hash. 작업하지 않은 승인 기록을 만들지 않는다.
- source registry의 웹 변경 자동 탐지·장기 원문 보존. MVP 계약은 수동 재검토이며 자동 크롤러는 필요하지 않다.
- 전체 정책의 필수조건 커버리지, 분기·자동·소급 신청일, 거주기간 산법, ApplicationWindow. M1.5/M1.8의 미해결 행정 쟁점은 그대로 남는다.
- 여러 edition 동시 평가·역사 replay 서비스·FULL_POLICY gate·API/UI 노출. 첫 데이터 계약의 지원 범위가 아니다.

ID·필수 버전·출처 pin·freshness 판정·참조 실패 처리에는 남은 선택지가 없다. 위 후속 사항은 이 계약의 최소 타입·검증 구현을 막지 않지만 실제 production 정책 발행·전체 정책 서비스 활성화 전에는 필요한 항목을 완료해야 한다.

## 25. 최종 판단

**READY_TO_IMPLEMENT_POLICY_DATA_ENVELOPE**

정책·확인본·locator·규칙 버전·검토·배포를 연결하는 계약을 정했고, 실제 주민등록 slice를 대입해 표현 가능성을 확인했다. 현재 m1.1 코드가 실제 데이터를 로드하지 못한다는 제한도 명시했다. 이번 판단은 새 데이터 계약의 최소 구현 준비 완료이며 실제 데이터 발행 준비 완료가 아니다.

**다음 가장 작은 작업 1개:** 공식 자료를 담지 않는 합성 입력으로 `SourceDocument / SourceEvidence / SourceRegistry`의 불변 타입과 ID·locator·document_version 무결성 검증만 구현·테스트한다. 기존 loader·Policy의 합성 제한, routing·Resolver·Adapter는 유지하고 실제 정책 JSON·production envelope 로딩은 시작하지 않는다.

검증 기록: 기존 전체 pytest **702 passed in 2.32s**. 이번 설계 사례 28개는 실행 테스트가 아니다. 기존 backend/tests/data/docs 43개 파일의 SHA256이 작업 전 기준선과 모두 같음을 확인했다. 추가 파일은 이 문서 하나이며 실제 정책 JSON은 생성하지 않았다. 문서의 필수 25절·중복 없는 수동 사례 28개도 확인했다.

## 26. M1.10 — IMPLEMENTED: 정책 근거 도메인·메모리 참조 검증

### 구현과 배치

`backend/policy_engine/sources/`의 `models.py`, `registry.py`, `__init__.py`에 분리했다. 기존 root 패키지 exports나 Policy 모델은 수정하지 않았다. 공개 import 경로는 `backend.policy_engine.sources`다. SourceValidationError 하나만 추가했고 기존 PolicyDataError → EngineValidationError 계층을 상속한다. 오류는 code/field를 제공하며 원문 URL·제목·참조 입력값을 메시지에 복사하지 않는다.

| 구현 | 실제 계약 |
|---|---|
| SourceType | OFFICIAL_NOTICE / OFFICIAL_POLICY_PAGE / OFFICIAL_QUARTER_GUIDE |
| SourceStatus | ACTIVE / SUPERSEDED / WITHDRAWN. 문서·locator 수명 상태 |
| VerificationStatus | DRAFT / VERIFIED / STALE. 수명 상태와 별개 |
| SourceEvidence | locator_id, section, meaning_summary, applicable_policy_ids tuple, verified_at, verification_status, status, page=None, table_position=None |
| SourceDocument | source_document_id, document_version, source_type, issuer, title, official_url, publication_date, verified_at, verification_status, status, locators tuple. 선택값은 notice_number, attachment_url, previous_urls tuple, effective_from/to, supersedes tuple, content_sha256 |
| SourceRegistry | sources: 비어 있지 않은 SourceDocument tuple. 문서 ID당 확인본 한 개 |

SourceEvidence/Document는 frozen/slots, keyword-only dataclass다. Evidence의 소속 문서는 포함 관계로 결정하고 source_document_id를 중복 저장하지 않는다. SourceDocument.status라는 확정 필드명을 사용하며 lifecycle_status alias를 추가하지 않는다. SourceDocument의 synthetic/test_only 필드는 M1.9에 정의되지 않았으므로 임의 추가하지 않았다. 실제 정책 수용 여부를 이 모델로 승인하지 않는다.

supersedes는 불변 `(source_document_id, document_version)` pair의 tuple이며 to_dict에서는 기존 설계의 object 배열로 표현한다. 타입·중복·정확한 자기 참조를 거부한다. registry 안에 정확한 확인본이 함께 있는 대체 관계는 순환을 거부한다. 과거 release에 대한 pair는 보존하며, 그 대상의 존재·공식 대체 관계·상태 동기화 검증은 manifest/review 계층이 없는 이번에 완료했다고 주장하지 않는다.

### 공개 API

```text
parse_evidence_ref(ref: str) -> tuple[source_document_id, locator_id]
registry.has_source(source_document_id) -> bool
registry.get_source(source_document_id) -> SourceDocument
registry.has_evidence(ref: str) -> bool
registry.resolve(ref: str) -> SourceEvidence
validate_evidence_refs(refs: tuple[str, ...], registry) -> tuple[SourceEvidence, ...]
```

canonical 형식은 `SYNTH-SOURCE-001#eligibility-residence`다. 정확한 str, # 한 개, M1.9 ID·locator 문법을 검증하며 strip/대소문자/별칭 보정이 없다. batch refs는 비어 있지 않은 tuple이며 같은 leaf의 중복 참조를 오류로 처리한다. 입력 순서대로 전부 resolve하며 하나라도 잘못되면 부분 결과를 반환하지 않는다.

has_source/has_evidence는 존재 조회다. 유효한 ID나 ref가 없으면 False, 문법·타입 오류면 SourceValidationError다. get_source는 수명에 관계없이 metadata 조회가 가능하며 없는 ID면 SOURCE_NOT_FOUND다. resolve는 SOURCE_NOT_FOUND / LOCATOR_NOT_FOUND와 문법 오류를 구분하고, 문서 또는 locator가 SUPERSEDED/WITHDRAWN이면 SOURCE_NOT_REFERENCEABLE / EVIDENCE_NOT_REFERENCEABLE로 거부한다. 동일한 객체가 중복되어도 ID·locator 중복을 조용히 제거하지 않는다.

### 날짜·URL·직렬화·불변성

- 날짜는 정확한 Python date 또는 None이다. datetime·ISO 문자열·bool을 자동 변환하지 않는다. VERIFIED 표기의 verified_at 누락, locator 확인일이 문서 확인일보다 늦거나 문서 확인일이 없는 모순, 역전된 effective 범위는 metadata 오류다. publication_date가 None인 것은 허용한다.
- Enum은 정확한 각 enum 타입만 허용한다. 문자열·RegistrationSource를 자동 변환하지 않는다. 내부 ID 역시 정확한 str이어야 한다.
- URL은 최소 절대 HTTPS 형태·host·포트·공백/제어문자·userinfo를 검사한다. 실제 공식 도메인인지, 문서 존재·redirect·접속 가능 여부는 확인하지 않는다. 원문 SHA256은 값의 소문자 64자리 형식만 확인하고 실제 내용 hash를 계산하지 않는다.
- tuple 외 list/dict/generator를 컬렉션 필드에 그대로 받지 않는다. 호출 경계에서 명시적으로 tuple 스냅샷을 만들 수 있다. 가변 lookup mapping이나 원본 list를 보관하지 않는다.
- 모델별 to_dict는 Enum.value, date ISO/None, 새 dict/list를 만든다. 출력 변경이 원본에 영향을 주지 않는다. registry의 schema_version 표기는 값 표현이며 sources.json loader를 구현한 것이 아니다.

### 좁힌 구현 경계

**IMPLEMENTED:** SourceDocument, SourceEvidence, in-memory SourceRegistry, canonical ref parsing, 중복/타입/구조 검증, broken ref detection, 수명상 참조 금지, 명시적 직렬화.

**NOT IMPLEMENTED:** sources.json loader, PolicyEnvelope, DatasetManifest, production source data, 기존 정책 loader/routing 연결, source binding 버전 pin 대조, policy 적용 범위 확인, review gate, 전체 대체 이력 검증, freshness enforcement, stale 정책 필터링.

특히 이번 M1.10 직접 지시에 따라 **7일 freshness는 운영 정책 후보로 남기며 실행하지 않는다.** registry는 현재 시각을 읽지 않고 date를 보존한다. DRAFT/STALE 또는 오래되거나 미래인 확인일 때문에 resolve를 자동 차단하지 않는다. 이는 source ref가 존재하고 수명상 참조 가능하다는 뜻이며 production 사용 승인과 다르다. 12~13절의 현재 서비스 preflight는 향후 설계이지 이번 모델의 동작이 아니다.

Policy Evidence만 관리하며 RegistrationSource와 통합하지 않는다. 기존 rule.evidence_refs는 계속 문자열 tuple, RuleEvaluation.details.evidence는 사용자 사실 snapshot이다. 기존 합성 ref에 이번 canonical 문법을 소급 강제하지 않는다.

### 합성 테스트와 검증

신규 `tests/test_source_registry.py`의 Python builder만 사용한다. 모듈에 SYNTHETIC=True / TEST_ONLY=True를 명시하고 ID는 SYNTH-*, issuer/title은 명시적 합성, URL은 example.invalid를 사용한다. 실제 기관 URL·실제 공고 제목·실제 source JSON은 추가하지 않았다. Policy/User evidence의 분리와 기존 rule의 문자열 tuple 유지도 검증한다.

작업 전 전체 **702 passed in 2.39s**, 신규 **252 passed in 0.52s**, 최종 전체 **954 passed in 2.74s**다. 정상 조회·여러 문서/locator·반복성·중복·잘못된 ref·수명 상태·검증 상태 보존·날짜 경계·Enum/URL 타입·직렬화·깊은 불변성·I/O 부재·부분 결과 금지를 포함한다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 44개 파일의 SHA256 기준선을 비교했다. 기존 파일 중 이 문서·DATA_MODEL.md·ARCHITECTURE.md만 수정했고 나머지 41개는 동일하다. 신규 source 패키지 3개 파일과 신규 테스트 1개를 추가했다. 기존 모든 테스트·m1.0/m1.1 fixtures·loader/models/routing/evaluator/Resolver/Adapter는 변경하지 않았고 기존 702개 기대값을 유지했다. 신규 코드·테스트에는 실제 정책 URL·공고명·공고번호가 없음을 확인했다.

최종 판단: **READY_FOR_SOURCE_REGISTRY_LOADER**.

다음 가장 작은 작업 1개: 합성/test_only sources JSON만 받는 strict loader를 별도 구현하고 정확한 schema_version·unknown/duplicate JSON keys·타입 변환·전체 성공 원칙을 검증한다. 실제 공식 자료·정책 envelope·기존 policy loader 연결·freshness는 포함하지 않는다.

## 27. M1.11 — IMPLEMENTED: strict Source Registry JSON Loader

### 형식과 API

새 `backend/policy_engine/sources/loader.py`에 다음 API를 추가하고 sources 패키지에서 공개한다. 기존 정책 rule loader와 parser/helper를 합치지 않았으며 기존 도메인 모델·registry는 변경하지 않았다.

```text
parse_source_registry(data: object) -> SourceRegistry
load_source_registry(path: str | Path) -> SourceRegistry
```

parse는 정확한 JSON 호환 dict/list/scalar만 받고 파일시스템·네트워크를 사용하지 않는다. load만 UTF-8 파일 읽기와 JSON decode를 수행한 뒤 parse에 넘긴다. 결과는 기존 SourceDocument/SourceEvidence를 담은 SourceRegistry다. 추가 조회·상태 판정 구현을 만들지 않았다.

top-level은 **`schema_version`과 `sources` 두 필드만** 허용한다. 버전은 정확한 문자열 `source-registry-1.0`이고, 누락·잘못된 타입·미지원 버전은 source 파싱 전에 INVALID_SOURCE_SCHEMA_VERSION으로 거부한다. 버전 추정·fallback은 없다. synthetic/test_only는 이 source schema에 정의되지 않았으므로 JSON 필드로 추가하지 않는다. 이 loader의 성공은 자료의 공식성·합성 여부·production 승인 검증이 아니다. 이번 사용·fixture는 합성/test_only에 한정한다.

### 필수·선택 필드

| 위치 | 필수 키 | 선택 키와 생략값 |
|---|---|---|
| SourceDocument | source_document_id, document_version, source_type, issuer, title, official_url, publication_date, verified_at, verification_status, status, locators | notice_number/attachment_url/effective_from/effective_to/content_sha256=None, previous_urls/supersedes=빈 배열 |
| SourceEvidence | locator_id, section, meaning_summary, applicable_policy_ids, verified_at, verification_status, status | page/table_position=None |
| supersedes 항목 | source_document_id, document_version | 없음 |

모든 object는 정확한 dict를 요구하며 unknown key를 거부한다. 필수 nullable 날짜는 null로 명시할 수 있지만 키 생략과 동일하게 취급하지 않는다. 사람용 section은 기존 모델처럼 필수이고, page/table_position은 선택이다. locator를 사람용 문장으로 대신하지 않는다.

### 명시적 JSON 경계 변환

- sources/locators/applicable_policy_ids/previous_urls/supersedes는 **정확한 JSON list를 먼저 검증한 뒤** 불변 tuple로 변환한다. 문자열·dict·tuple·generator의 범용 tuple 보정은 없다. 비어 있어도 되는지·중복 여부는 기존 모델이 검사한다.
- 날짜는 null 또는 ASCII `YYYY-MM-DD` 문자열만 허용한다. 정확한 자릿수와 실제 달력 날짜를 검증해 date로 변환한다. 축약·공백·YYYYMMDD·주차형 날짜·datetime 문자열·Python date/datetime 객체를 raw JSON 입력으로 받지 않는다. bool/숫자도 거부한다.
- Enum은 정확한 str canonical 값만 각 기존 enum으로 변환한다. str Enum 객체도 raw JSON 입력에서는 거부한다. 대소문자·오타·공백 보정, 사용자 RegistrationSource 변환은 없다.
- supersedes object는 검증한 ID/version pair tuple로 바꾼다. source/locator 중복·정확한 날짜/효력 범위·URL/해시·수명 enum의 도메인 의미는 기존 생성자에 맡긴다.

URL은 기존 SourceDocument 형식 검증만 거치고 접속하지 않는다. source_type의 OFFICIAL_* 값도 공식성 확인을 수행하지 않는다. source와 locator의 입력 순서를 보존하며 임의 정렬·누락·dedup을 하지 않는다.

### 중복·오류·전체 성공 원칙

Python JSON decoder의 기본 마지막 값 덮어쓰기 대신 `object_pairs_hook`로 **어느 계층이든 중복 JSON key를 거부**한다. 이는 array 내부의 중복 source ID·locator와 별개다. 후자는 기존 SourceDocument/SourceRegistry가 검사한다. NaN/Infinity/-Infinity 같은 비표준 JSON 상수도 거부한다.

| 실패 종류 | SourceValidationError.code |
|---|---|
| 파일 부재·접근 등 OSError | SOURCE_FILE_ERROR / field=path. 원래 예외를 cause로 보존 |
| UTF-8 decode 오류 | INVALID_SOURCE_ENCODING |
| malformed JSON·BOM·비표준 상수·decode 재귀 오류 | INVALID_SOURCE_JSON |
| 중복 JSON object key | DUPLICATE_SOURCE_JSON_KEY |
| 지원 버전 부재/불일치 | INVALID_SOURCE_SCHEMA_VERSION |
| object/array 타입 | INVALID_SOURCE_OBJECT / INVALID_SOURCE_ARRAY |
| 필수 키 누락·추가 키 | MISSING_SOURCE_FIELDS / UNKNOWN_SOURCE_FIELDS |
| 날짜·Enum 경계 파싱 | INVALID_SOURCE_DATE / INVALID_SOURCE_ENUM |
| 도메인 데이터 모순 | 기존 SourceValidationError code를 그대로 전파 |

오류는 모두 기존 PolicyDataError 계층 아래이며 정상 UNKNOWN으로 바꾸지 않는다. 파일 I/O 오류와 내용 검증 오류는 code/cause로 구분한다. 알 수 없는 필드명·원문 값·전체 JSON을 오류 메시지에 삽입하지 않는다. 일부 source가 정상이더라도 나머지 하나가 잘못되면 전체 load failure이며 부분 registry를 반환하지 않는다.

### 합성 fixture와 기존 Registry 통합

`data/synthetic/sources.json`에 SYNTH-SOURCE-001/002 두 문서와 locator 세 개를 추가했다. 첫 문서는 eligibility-residence/application-period, 두 번째 문서는 DRAFT eligibility-residence다. 첫 문서에는 선택 필드를 명시하고 두 번째에는 생략해 기본값 경계도 확인한다. 한국어 section을 포함하는 UTF-8 자료다.

기관·제목에 SYNTHETIC/test_only를 표시하고 URL은 example.invalid만 사용한다. 실제 기관명·공고번호·정책명·공식 URL은 넣지 않는다. 별도 `data/synthetic/SOURCES_README.md`에 **synthetic=True / test_only=True 용도**와 JSON에 새 플래그를 추가하지 않은 이유를 기록했다. 기존 policy fixtures와 README는 수정하지 않았다.

로드된 registry.get_source/resolve/validate_evidence_refs는 기존 API 그대로다. SUPERSEDED/WITHDRAWN은 **로드·보존 가능**하고 참조 거부는 기존 resolve에 맡긴다. DRAFT/STALE·오래된 검증일은 보존하며 7일 freshness나 stale 필터링은 이번에도 실행하지 않는다.

### 검증·남은 범위

작업 전 전체 **954 passed in 3.23s**, 신규 `tests/test_source_registry_loader.py` **248 passed in 1.11s**, 최종 전체 **1202 passed in 3.42s**다. 독립 hand-built 모델과 동일성, file/parse/직렬화 왕복, 필수·선택·추가 키, 각 계층 중복 키, strict 배열·Enum·달력 날짜, UTF-8/BOM/파일 오류, 입력 불변성·순서·기존 resolve·부분 성공 금지·I/O 책임을 검증했다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 48개 파일의 SHA256 기준선을 비교했다. 기존 source 패키지 공개 API 파일과 문서 3개만 수정했고 나머지 44개는 동일하다. 새 loader·신규 테스트·합성 sources.json·용도 설명 파일 4개를 추가했다. 기존 테스트와 기대값, source 모델/registry, policy loader/routing/evaluator/Resolver/Adapter, 기존 synthetic policy fixtures는 변경하지 않았다. 신규 코드·테스트·fixture에 실제 정책명·기관 URL·공고번호가 없음을 확인했다.

IMPLEMENTED: strict Source Registry JSON Loader와 합성 source fixture.

NOT IMPLEMENTED: production sources.json, 실제 정책 자료, PolicyEnvelope, DatasetManifest, policy/source production binding, freshness enforcement, source 웹 확인·자동 업데이트, 실제 resident rule.

최종 판단: **READY_FOR_POLICY_ENVELOPE_MODEL**.

다음 가장 작은 작업 1개: M1.9 envelope 계약의 metadata·source binding·CONDITION_SLICE 범위를 담는 최소 불변 모델을 합성 입력으로 구현·검증한다. 기존 Policy의 합성 제한, 실제 자료 생성, production binding·전체 loader·manifest·freshness는 별도 승인 단계로 둔다.

## 28. M1.12 — IMPLEMENTED: 단일 edition의 불변 PolicyEnvelope

### 관계 선택과 현재 지원 범위

| 방식 | 비교 | 판단 |
|---|---|---|
| A. Envelope가 기존 Policy를 포함 | 실행 트리·ID·버전·플래그를 한 객체에 유지, 원본 그대로 평가 가능 | **채택** |
| B. Policy 필드를 전부 복제 | 중복 ID·규칙 버전·root·플래그의 불일치와 동기화 부담 | 미채택 |
| C. 별도 metadata에서 실행 Policy로 변환 | 향후 실제 데이터에 의미가 있으나 변환·허용 범위 검토 필요 | 이번 단계 보류 |

`policy_data/envelope.py`, `validation.py`, `__init__.py`를 새로 추가했다. 공개 경로는 `backend.policy_engine.policy_data`다. 기존 Policy/PolicySet·모든 loader·source 모델/registry·routing은 수정하지 않는다.

**이번 모델은 합성/test_only Policy만 감싼다.** 기존 Policy가 두 플래그 True를 강제하므로 실제 데이터의 false/false는 아직 지원하지 않는다. M1.9의 실제 운영 데이터 목표를 True로 바꾸거나 우회하는 구현이 아니다. 실제 데이터 수용을 위해서는 별도 실행 모델 연결 설계·승인이 여전히 필요하다. READY 판단은 후속 **합성 envelope loader**에 한정한다.

### 최종 구조

모두 frozen/slots이며 PolicyEnvelope는 keyword-only다.

| 항목 | 구현 |
|---|---|
| PolicyEnvelope 저장 필드 | schema_version, rule_schema_version, policy, edition_id, jurisdiction, category, dataset_version, evaluation_scope, coverage, source_bindings, verification_status, last_verified_at, lifecycle_status, effective_from/to |
| 읽기 전용 property | policy_id, policy_name, rule_version, root, synthetic, test_only는 기존 policy에서 직접 읽음. source_document_ids는 source_bindings에서 tuple로 계산 |
| SourceBinding | source_document_id, document_version. ID와 d0001… 확인본 형식 검증 |
| PolicyCoverage | included_rule_ids tuple, excluded_conditions tuple. 두 값 모두 비어 있지 않은 str tuple. 포함 rule ID 중복 금지 |
| PolicyCategory | YOUTH_SUPPORT만 지원 |
| EvaluationScope | CONDITION_SLICE만 지원. FULL_POLICY는 미지원 |
| PolicyLifecycleStatus | ACTIVE / ENDED. SourceStatus와 별도 enum |
| PolicyVerificationStatus | DRAFT / VERIFIED / STALE. 정책 edition의 검토 상태 선언이므로 원문 VerificationStatus와 별도 타입 |

M1.9 필수 metadata인 jurisdiction/category/dataset_version/evaluation_scope/coverage/source binding을 생략하지 않았다. manifest 미구현을 이유로 dataset_version을 삭제하지 않는다. 이는 M1.9 3절의 명시적 요구다. 현재는 비어 있지 않은 str로 보존하며 manifest와 같다는 검사는 후속 단계다. 사용자 신청일·소득·fact·registry를 envelope에 보관하지 않는다.

### 생성자 검증

- schema_version은 정확한 str `policy-data-1.0`, rule_schema_version은 `m1.1`만 지원한다. 자동 추정·fallback은 없다.
- 기존 Policy의 policy_id에 canonical ID 문법을 적용한다. policy_name은 기존 Policy가 검증한다. 중복 ID·root 구조·기존 tuple·합성 플래그 검증도 기존 Policy 책임이다.
- rule_version은 기존 policy의 값이며 `r0001`부터의 canonical 증가 형식만 envelope에서 허용한다. 문서 확인본은 `d0001`부터다. 기존 Policy 자체의 자유로운 합성 버전 문자열은 변경하지 않았다.
- edition_id는 M1.9 21절대로 첫 지원은 **ASCII 4자리 연도 문자열**이다. 예: 합성 정책의 2026/2027. 프롬프트의 EDITION-A는 후보 예시이며 확정 문법으로 추가하지 않았다. 여러 회차·비연도 edition은 후속 확장이다.
- policy_id/root/rule_version/플래그를 생성자에 별도 인자로 받지 않으므로 상위·하위 값의 불일치를 구조적으로 만들 수 없다. 이런 중복 keyword는 TypeError다. 필수 인자 자체가 없을 때도 Python 생성자 TypeError이며, 전달된 타입·값 오류는 아래 data error다.
- jurisdiction은 완전한 RegionRef, status/category/scope는 정확한 각 enum만 허용한다. 문자열·다른 enum·dict를 자동 변환하지 않는다.
- source_bindings는 비어 있지 않은 SourceBinding tuple이고 같은 문서 ID는 확인본 버전이 달라도 중복 금지다. 모든 leaf의 canonical evidence_refs에 사용된 문서 ID 집합과 binding ID 집합이 **같아야** 한다. 누락된 근거와 사용하지 않는 binding을 모두 거부한다.
- coverage의 포함 ID 집합은 모든 leaf ID와 같아야 한다. group ID를 포함하면 안 된다. 입력 순서를 재정렬하지 않으며 coverage 나열 순서가 달라도 root 실행 순서는 유지된다. 제외 조건은 범위 설명이고 실행 규칙이 아니다.
- 기존 모든 leaf의 최소 근거 tuple은 기존 모델이 보장한다. envelope는 추가로 canonical ref 문법과 leaf 내 중복 참조를 거부한다. 여러 leaf가 같은 참조를 공유하는 것은 허용한다. legacy Policy를 단독으로 쓸 때 기존 ref 문법은 변경하지 않는다.
- last_verified_at/effective_from/to는 정확한 date 또는 None이다. VERIFIED 선언에는 확인일이 필요하지만, DRAFT/STALE의 날짜 미입력은 허용한다. 두 효력일이 있으면 from <= to이며 한쪽만 있거나 모두 None도 허용한다. None을 무제한 효력·신청 가능으로 해석하지 않는다.

synthetic/test_only는 두 값 모두 True인 기존 Policy에서 읽는다. True/False, False/True, False/False 및 1을 True로 대체하는 조합은 기존 Policy 생성자가 거부한다. envelope가 플래그를 별도로 변경하거나 실제 자료를 합성으로 바꾸지 않는다.

### 순수 cross-object validation

```text
validate_envelope_sources(envelope: PolicyEnvelope, registry: SourceRegistry) -> None
```

registry를 생성자에 주입·저장하거나 전역 상태에서 찾지 않는다. 두 명시적 입력을 받아 전체 검증 성공 시 None, 오류 시 예외만 반환한다.

1. 각 binding의 source가 registry에 존재하고 document_version이 정확히 같아야 한다. 최신판으로 자동 변경하지 않는다.
2. 각 leaf에 기존 validate_evidence_refs를 호출해 source/locator 존재와 수명상 참조 가능 여부를 검증한다. SUPERSEDED/WITHDRAWN 로직을 새 validator에서 복제하지 않는다.
3. 선택 locator의 applicable_policy_ids에 envelope.policy_id가 있어야 한다. ref가 존재한다는 이유로 다른 정책의 근거를 사용하지 않는다.
4. **사용한 locator들의 verified_at 최솟값**을 last_verified_at과 대조한다. 하나라도 None이면 파생값은 None이다. 더 최근인 문서 확인일이나 사용하지 않는 locator/registry 문서로 날짜를 덮어쓰지 않는다.

단일 leaf·혼합 ALL·NOT 및 여러 source binding에 적용할 수 있다. 이미 Policy가 검증한 중복 rule ID를 별도로 재검증하지 않는다. 단일 envelope의 ID/edition은 표현하지만 서로 다른 envelope 사이 조합 유일성은 배치/manifest가 없는 이번에 검사하지 않는다.

오류는 EnvelopeValidationError(기존 PolicyDataError 하위)의 code/field다. SOURCE_VERSION_MISMATCH, POLICY_EVIDENCE_MISMATCH, LAST_VERIFIED_DATE_MISMATCH 등을 제공한다. source lookup/resolve가 발생시킨 기존 SourceValidationError는 그대로 전파한다. 사용자 판정 UNKNOWN이나 부분 성공 결과로 바꾸지 않는다.

### Domain validity와 production acceptance

구조적으로 유효한 DRAFT/STALE/VERIFIED 및 ENDED edition도 보관할 수 있다. cross-validator는 **참조 무결성**만 검사하며 검증 상태에 따른 운영 차단·7일 freshness·현재 시각 조회·공식성 확인·review 승인은 수행하지 않는다. VERIFIED 값은 검토 상태의 선언이며 이번 validator가 그 workflow의 사실성을 보증하지 않는다. source가 STALE라도 구조와 참조·날짜가 맞으면 여기서는 보존한다.

따라서 constructor 성공 또는 validate_envelope_sources 성공은 production-accepted가 아니다. 특히 이번에는 synthetic/test_only=True이고 CONDITION_SLICE뿐이므로 전체 정책 추천·신청가능 표시의 근거로 사용할 수 없다. 16절 production gate의 공식 근거·review·manifest·freshness 검증은 아직 미구현이다. production acceptance validator의 인터페이스도 의존 모델이 준비되기 전 코드 stub으로 추가하지 않았다.

### 표현·통합·검증 범위

to_dict는 기존 models의 값 serializer를 재사용해 중첩 Policy·SourceBinding·Coverage·Enum·date를 새 dict/list·canonical 문자열로 표현한다. 내부 가변 컬렉션을 노출하지 않으며 **현재 출력은 policy 객체를 포함한 도메인 값 snapshot**이다. M1.9의 flat normalized JSON을 구현하거나 기존 m1.1 loader에 입력 가능한 형식을 새로 만들었다는 뜻은 아니다. JSON Loader·flat 필드 연결은 다음 단계다.

합성 Policy/Registry/Envelope는 신규 `tests/test_policy_envelope.py`에서 메모리로 생성한다. 테스트용 지역 값은 기존 RegionRef를 재사용할 뿐 실제 정책을 나타내지 않는다. 실제 기관·정책명·공고·공식 URL을 추가하지 않았다. 기존 합성 sources.json을 읽는 작은 통합 테스트도 포함한다. 기존 fixtures는 수정하지 않는다.

동일한 원본 Policy 객체와 envelope.policy를 각각 evaluate_policy_tree에 전달해 PASS/FAIL/UNKNOWN을 포함한 결과 객체·JSON 전체가 같음을 검증한다. 새 평가 함수·라우팅·집계·날짜 판정을 추가하지 않는다. 원본 Policy/Registry는 변경되지 않는다.

작업 전 전체 **1202 passed in 4.31s**, 신규 **169 passed in 0.41s**, 최종 전체 **1371 passed in 3.86s**다. ID/edition/버전·필수 metadata·coverage·binding·검증/수명/날짜·깊은 불변성·직렬화·Registry/Engine 통합·I/O 부재를 검증했다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 52개 파일의 SHA256 기준선을 비교했다. 문서 3개만 수정했고 나머지 49개는 동일하다. 신규 policy_data 패키지 3개 파일과 신규 테스트 1개를 추가했다. 기존 모든 테스트/기대값, models.py, policy/source loader, SourceRegistry, routing/evaluator/Resolver/Adapter, 기존 synthetic fixtures는 변경하지 않았다. 신규 코드·테스트에 실제 정책명·공식 URL·공고번호가 없음을 확인했다.

IMPLEMENTED: PolicyEnvelope domain model, 작은 enum/value object, envelope ↔ source registry pure validation.

NOT IMPLEMENTED: PolicyEnvelope JSON Loader, DatasetManifest, 실제 production policy/source/envelope, false/false 데이터 수용, production acceptance, freshness enforcement, 여러 edition 배치 로딩.

최종 판단: **READY_FOR_POLICY_ENVELOPE_LOADER**.

다음 가장 작은 작업 1개: **합성/test_only PolicyEnvelope JSON Loader**를 별도로 구현해 flat metadata를 이번 불변 모델에 연결하고 strict 키·버전·경계 변환·원본 Policy 의미 보존을 검증한다. 실제 데이터와 production gate는 포함하지 않는다.

## 29. M1.13 — IMPLEMENTED: strict PolicyEnvelope JSON Loader

### 입력 구조 선택

| 후보 | 비교 | 선택 |
|---|---|---|
| A. 단일 envelope에 m1.1 Policy payload 포함 | 파일 하나에 실행 트리와 metadata가 있고 기존 parser에 그대로 전달 가능 | **채택** |
| B. 외부 policy 파일 참조 | 공유·개별 교체 가능하나 파일 버전 pin·해시·원자적 배포 계약이 선행되어야 함 | DatasetManifest 미구현이므로 보류 |

M1.9의 flat 논리 필드 목록과 M1.12의 Policy 포함 모델을 연결하는 **첫 실행 JSON 계약**이다. M1.13의 단일 파일 embed 방향을 채택해 Policy 소유 필드는 `policy` object에 묶는다. domain 모델에 새 metadata를 추가하지 않는다. policy_name/rule_version/root는 중첩 Policy에만 두고, source_document_ids는 여전히 source_bindings에서 계산한다.

M1.13이 요구한 외부/내부 identity·플래그 일치 검증을 위해 JSON 외부에는 `policy_id`, `synthetic`, `test_only`를 assertion으로 명시한다. 파싱 중 정확히 대조하고 객체에는 중복 저장하지 않는다. 외부 값을 내부에 덮어쓰거나 반대로 보정하지 않는다.

| 위치 | 확정 JSON 키 |
|---|---|
| 최상위 필수 | schema_version, rule_schema_version, policy_id, policy, edition_id, jurisdiction, category, dataset_version, evaluation_scope, coverage, source_bindings, verification_status, last_verified_at, lifecycle_status, synthetic, test_only |
| 최상위 선택 | effective_from, effective_to. 생략/null은 None |
| policy | 기존 m1.1 Policy payload 그대로: policy_id, policy_name, rule_version, synthetic, test_only, root |
| jurisdiction | sido, sigungu |
| coverage | included_rule_ids, excluded_conditions |
| source_bindings 각 항목 | source_document_id, document_version |

최상위 rule_version/policy_name/root/source_document_ids 같은 중복 대체 키, 외부 file reference, 추가 embedded schema_version을 허용하지 않는다. `schema_version=policy-data-1.0`은 envelope 문법, `rule_schema_version=m1.1`은 중첩 트리 문법이다. 두 값 모두 누락·잘못된 타입·미지원 값을 payload 파싱 전에 거부하고 fallback하지 않는다.

### 구현 및 기존 parser 재사용

새 `policy_data/loader.py`와 두 공개 API를 추가했다.

```text
parse_policy_envelope(data: object) -> PolicyEnvelope
load_policy_envelope(path: str | Path) -> PolicyEnvelope
```

메모리 parse와 UTF-8 파일 읽기를 분리한다. parser는 다음 **단일 PolicySet adapter**를 만들어 기존 공개 parse_policy_set을 한 번 호출하고 policies[0]을 가져온다.

```text
schema_version ← rule_schema_version (m1.1)
dataset_version ← envelope의 값
synthetic/test_only ← True/True (현재 지원 범위인 합성 실행 컨테이너)
policies ← [중첩 policy payload 그대로]
```

rule/atomic/resident_registration/group/FactBasis 파싱과 기존 strict Policy 검증을 복제하지 않는다. 외부 assertion flags는 정확한 bool이어야 하고 생성된 Policy의 flags와 동일해야 한다. 외부 False/내부 True는 POLICY_FLAGS_MISMATCH, 내부 False나 정수 플래그는 기존 Policy 검증에서 실패한다. adapter의 True 상수가 외부 flags를 무시하거나 production 자료를 합성으로 바꿔 통과시키는 경로는 없다. 불일치하면 envelope가 반환되지 않는다.

기존 source loader의 순수 `_object/_array/_date/_enum`과 duplicate-key/비표준 상수 hook을 읽기 전용으로 재사용했다. 기존 helper 구현·source loader public 동작을 수정하거나 새 범용 parser framework로 추출하지 않았다. JSON metadata helper 오류만 code의 SOURCE를 ENVELOPE로 바꾸어 EnvelopeValidationError로 전달하며 원래 cause를 보존한다. RegionRef 생성 오류도 해당 경계의 INVALID_JURISDICTION으로 분류한다. 기존 정책 parser의 PolicyDataError 및 모델의 근거 오류는 의미를 바꾸지 않고 전파한다.

### Strict 경계와 도메인 검증

- 모든 metadata object는 정확한 dict, 배열은 정확한 list를 요구한다. 필수 키 누락·unknown key·오타를 거부한다. 배열을 검사한 뒤 tuple과 기존 value object로 명시적으로 변환한다.
- 날짜는 null 또는 실제 달력 날짜인 ASCII YYYY-MM-DD만 허용한다. datetime/timezone 문자열·슬래시·축약·timestamp·Python date/datetime 입력을 보정하지 않는다. Enum도 정확한 canonical JSON str만 허용한다.
- edition_id는 그대로 4자리 연도 문자열이다. `2026-Q1`은 미지원이다. r/d 버전·source ID·coverage·중복 binding·source 집합·효력기간은 기존 PolicyEnvelope/SourceBinding/PolicyCoverage가 검증한다.
- 외부 policy_id는 정확한 str이어야 하며 내부 Policy.policy_id와 정확히 같아야 한다. 불일치는 POLICY_ID_MISMATCH다. 두 값을 자동 덮어쓰지 않는다.
- embedded Policy는 기존 m1.1 허용 키·node discriminator·엄격한 타입·중복 rule ID·group 자식 수·합성 제한을 그대로 적용한다. m1.0 문법을 추정해 수용하지 않는다.
- JSON decode에서 모든 object의 duplicate key를 검출한다. 중복 source binding과 rule ID는 JSON key 중복과 별도의 기존 도메인 검사다. NaN/Infinity, malformed JSON, UTF-8 BOM·cp949 자동 수용은 없다.
- 파일 부재/접근 오류는 ENVELOPE_FILE_ERROR, UTF-8 decode 오류는 INVALID_ENVELOPE_ENCODING, malformed JSON은 INVALID_ENVELOPE_JSON, duplicate key는 DUPLICATE_ENVELOPE_JSON_KEY다. 파일 오류는 OSError cause를 보존한다. 파일 읽기 후의 모델 오류를 malformed JSON으로 바꾸지 않는다.
- 모든 metadata·PolicyEnvelope 생성이 성공해야 반환한다. 정상 Policy만 먼저 반환하거나 잘못된 metadata를 생략하는 부분 성공은 없다. 데이터 오류를 UNKNOWN으로 바꾸지 않는다.

### Registry와 평가의 명시적 연결

load/parse는 registry를 요구·소유·수정하지 않는다. 반환된 객체는 **domain-valid**이며 source가 실제로 존재한다는 검증 완료를 뜻하지 않는다.

```text
load_policy_envelope(synthetic envelope JSON) → envelope
load_source_registry(기존 synthetic sources.json) → registry
validate_envelope_sources(envelope, registry) → None 또는 명시적 오류
envelope.policy → 기존 evaluate_policy_tree
```

존재하지 않는 source/locator, SUPERSEDED/WITHDRAWN, source version 불일치, 다른 정책 근거, 파생 확인일 불일치는 기존 cross-validator에서 거부한다. source list 밖 evidence와 coverage 오류는 이미 envelope 생성에서 거부한다. 로직을 loader에서 재구현하지 않는다.

DRAFT/VERIFIED/STALE·ENDED는 모델 계약대로 보존한다. VERIFIED만 로드하거나 오래된 날짜를 자동 차단하지 않는다. 7일 enforcement·production 추천 여부·공식성·review workflow는 이번에도 판단하지 않는다. 한 leaf의 PASS를 실제 전체 정책 신청 가능으로 표시할 수 없다.

### 합성 fixture와 재현 검증

새 `data/synthetic/policy_envelope_m11.json` 한 개만 추가했다. SYNTH-POLICY-001과 ALL(합성 age 조건, 합성 주민등록 조건), r0001, 2026 edition, DRAFT, True/True, 명시적 합성 효력기간을 포함한다. 근거는 기존 SYNTH-SOURCE-001의 두 locator를 재사용하며 새 source fixture를 복제하지 않는다. 실제 기관·정책명·공고·공식 URL은 없다. 기존 fixtures도 변경하지 않는다.

독립 hand-built envelope와 loaded envelope의 전체 객체·도메인 snapshot이 같다. 같은 payload를 기존 m1.1 parser로 직접 읽은 Policy와도 같다. loaded/hand-built/기존 parser의 세 경로에 같은 profile/facts/context를 주어 PASS/FAIL/UNKNOWN과 결과 JSON 전체가 같음을 확인한다. parser 재사용 호출도 테스트로 확인한다.

**직렬화 경계:** 기존 PolicyEnvelope.to_dict는 도메인 값 snapshot이며 이 JSON 문법의 serializer가 아니다. JSON 입력에는 외부 ID/flags assertion 및 m1.1 kind/rule_type이 필요하다. snapshot을 loader가 임의 추정해 읽지 않는다. 저장용 serializer는 이번에 추가하지 않았다.

### Edition 기술부채·남은 범위

**미결정:** “분기별 규칙 또는 application windows가 연도 하나의 edition에 속할 것인가, 분기별 edition으로 분리될 것인가?” 실제 전체 정책 모델링 전에 재검토한다. 이번에 답을 정하거나 분기 edition 문자열을 허용하지 않는다. ApplicationWindow·생년월일·거주이력 모델도 추가하지 않는다.

작업 전 전체 **1371 passed in 3.96s**, 신규 `tests/test_policy_envelope_loader.py` **233 passed in 0.80s**, 최종 전체 **1604 passed in 4.50s**다. strict 구조·버전·ID/flags 불일치·날짜·Enum·중복·파일 오류·입력 불변성·기존 parser 재사용·근거 검증·엔진 통합을 검증했다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 56개 파일의 SHA256 기준선을 비교했다. policy_data 공개 API 파일과 문서 3개만 수정했고 나머지 52개는 동일하다. 새 envelope loader·신규 테스트·합성 envelope JSON 3개 파일을 추가했다. 기존 모든 loader·모델·validator·routing/Resolver/Adapter·기존 테스트/기대값·기존 fixtures는 변경하지 않았다. 신규 코드·테스트·fixture에 실제 정책명·공식 URL·공고번호가 없음을 확인했다.

IMPLEMENTED: strict PolicyEnvelope JSON Loader와 합성 JSON → Registry 검증 → 기존 Engine 통합.

NOT IMPLEMENTED: DatasetManifest, production acceptance, 실제 정책 envelope/source, freshness enforcement/자동화, 분기/신청창·BirthFact·ResidenceHistoryFact.

최종 판단: **READY_FOR_DATASET_MANIFEST**.

다음 가장 작은 작업 1개: 합성 배포를 대상으로 **DatasetManifest 최소 불변 모델과 버전·참조 고정 계약**을 구현·검증한다. 실제 데이터·production gate·freshness·대규모 배포 기능은 포함하지 않는다.

## 30. M1.14 — IMPLEMENTED: DatasetManifest 모델·메모리 일관성 검증

### 선택과 최소 책임

| 후보 | 비교 | 선택 |
|---|---|---|
| A. Manifest 안에 Envelope/Registry 객체 포함 | 쉽게 접근 가능하지만 실제 데이터와 선택 metadata가 중복되고 파일·객체 경계가 흐려짐 | 미채택 |
| B. ID/edition/버전·artifact 참조·내용 지문만 보관 | 실제 객체는 기존 loader로 읽고 명시적 pure validator에서 대조 가능 | **채택** |

기존 policy_data 패키지에 manifest.py를 추가하고 validation.py에 validate_dataset_manifest를 확장했다. PolicyEnvelope·SourceRegistry·기존 loader·평가 로직은 수정하지 않았다. 배포 플랫폼·DB·CI/CD·Git/build 조회를 추가하지 않는다. JSON Manifest Loader와 실제 배포 파일도 만들지 않는다.

### 최종 모델

모든 모델은 frozen/slots이며 ArtifactReference 외에는 keyword-only다. 내부 목록은 정확한 tuple이다.

| 모델 | 필드 / 의미 |
|---|---|
| ArtifactReference | path, sha256. release 상대 경로와 **파일 bytes SHA256 선언** |
| PolicyEditionReference | policy_id, edition_id, rule_version, artifact, fingerprint, schema_version=policy-data-1.0, rule_schema_version=m1.1 |
| SourceRegistryReference | artifact, fingerprint, schema_version=source-registry-1.0. 별도 registry ID/version을 원본 모델에 추가하지 않음 |
| DatasetManifest | schema_version, dataset_id, dataset_version, created_at, freshness_max_age_days, engine_version, engine_artifact_sha256, policy_versions tuple, source_registry, source_versions tuple, review_manifest=None |
| source_versions 항목 | 기존 SourceBinding 재사용. 문서 ID/document_version을 고정 |

M1.9의 path/sha256은 ArtifactReference로 묶었으며 파일 hash 의미를 바꾸지 않았다. 메모리 대조를 위해 Policy/Registry reference에 별도 **fingerprint**를 추가했다. 두 지문을 같은 값으로 취급하지 않는다. review_manifest는 선택 ArtifactReference다. **이번 domain-only 단계에서는 미검토 DRAFT 자료를 표현하도록 None을 허용**하며, M1.9의 production review gate가 충족되었다고 간주하지 않는다. review workflow나 가상의 검토 완료 기록은 생성하지 않는다.

Manifest 자체의 verification/release enum, 사용자 입력·평가 결과·계정·서비스 URL·Policy/Registry 객체는 추가하지 않았다. metadata와 참조만 보관한다.

### ID·버전·날짜·중복

- schema_version은 정확한 문자열 `dataset-manifest-1.0`만 허용한다. fallback하지 않는다.
- dataset_id는 배포 계열의 내부 이름이고 dataset_version은 선택 release 버전이다. 정확한 비어 있지 않은 str을 사용하며 날짜/semver framework·자동 생성·보정을 도입하지 않는다. 기존 합성 envelope의 `synthetic-edition-001`을 사용한다. 버전 재사용·과거 배포 덮어쓰기 탐지는 배포 이력 계층이 없는 이번에 보장하지 않는다.
- created_at은 **정확한 timezone-aware datetime**을 명시적으로 받는다. date·문자열·naive datetime을 거부하며 시스템 현재 시각을 읽지 않는다. 값 표현·지문에는 같은 순간을 UTC ISO로 표현한다. 합성 테스트 시각을 실제 발행시각으로 주장하지 않는다.
- policy reference는 canonical policy ID, 4자리 연도 edition, r0001… 규칙 버전과 두 schema를 고정한다. 문서 버전은 기존 d0001… 계약이다.
- 한 manifest에 **policy_id당 edition 하나만** 허용한다. 같은 ID/edition의 동일 참조 중복도 오류이고, 같은 정책의 다른 edition 동시 선택도 오류다.
- source_versions에는 registry의 **사용하지 않는 문서까지 포함한 전체 ID/version 집합**을 고정한다. 문서 ID당 선택 확인본 하나이며 중복은 오류다.
- Artifact path는 slash 기반 release 상대 경로만 허용한다. 절대 경로, drive/ADS colon, backslash, 빈/`.`/`..` 경로 성분, 제어문자와 앞뒤 공백을 거부한다. 파일을 resolve하거나 열지 않는다. 서로 다른 artifact 역할의 같은 path도 거부한다.
- SHA256과 fingerprint는 정확한 소문자 64자리 hex str이다. freshness_max_age_days는 양의 int이며 bool은 거부한다. 7일이라는 값은 **보존만** 하고 날짜와 비교하지 않는다.

### 두 hash 계약과 결정성

1. **artifact.sha256 / engine_artifact_sha256:** 호출자가 제공하는 원본 파일·엔진 artifact bytes hash다. 모델은 형식을 검증하고 보존한다. 이번 validator는 파일 bytes·실행 빌드를 입력받지 않으므로 해당 파일/빌드와 일치한다고 확인하지 않는다.
2. **reference.fingerprint:** 로드된 도메인 값 snapshot의 결정적 SHA256이다. `fingerprint_policy_envelope`와 `fingerprint_source_registry`가 순수하게 계산하고 validator가 대조한다. 같은 ID/version으로 내용이 달라져도 검출한다.
3. **manifest.fingerprint():** Manifest의 모든 metadata·버전·artifact 선언·객체 fingerprint를 묶은 SHA256이다. 자기 fingerprint를 다시 입력에 포함하지 않는다. 값과 입력이 변경되면 다른 선택임을 추적할 수 있다.

표준 hashlib.sha256과 UTF-8 JSON의 sort_keys=True / 고정 separators / ensure_ascii=False / allow_nan=False를 사용한다. 별도 hash algorithm·Git commit·OS 환경 지문·Docker/build 시스템은 구현하지 않았다. 원문 hash는 문서의 content_sha256과도 구분한다.

순서 계약:

- Manifest의 policy_versions/source_versions, Registry의 sources/locators/supersedes/applicable_policy_ids, Envelope의 source_bindings/coverage.included_rule_ids는 지문 계산 시 ID 기준으로 정렬한다. 객체 원본은 재정렬하지 않는다. 같은 선택을 메모리에 나열한 순서가 다르더라도 내용 지문은 같다.
- 실행 rule children와 leaf evidence_refs, 설명용 제외 조건·URL 이력의 순서는 보존한다. 출력/근거 표현의 순서까지 재현 대상으로 삼는다.
- **파일 bytes의 순서·공백이 바뀌면 artifact.sha256은 바뀐다.** 이를 반영한 Manifest 전체 지문도 달라진다. 메모리 객체의 나열 순서 불변성과 원본 파일 bytes 동일성을 혼동하지 않는다.

to_dict는 기존 값 serializer를 사용한 새 dict/list snapshot이며 created_at을 UTC ISO로 표현한다. 향후 Manifest JSON 입력 문법을 구현한 것이 아니다. 원래 객체를 변경하지 않는다.

### Dataset consistency validation

```text
validate_dataset_manifest(
    manifest: DatasetManifest,
    envelopes: tuple[PolicyEnvelope, ...],
    registry: SourceRegistry,
) -> None
```

명시적 입력만 사용하며 파일 I/O·현재시각·정책 평가·부분 성공은 없다.

1. 입력 타입·중복 envelope ID를 확인한다. 제공한 envelope ID 집합과 manifest의 집합이 **정확히 같아야** 한다. 누락·관계없는 추가 envelope를 조용히 무시하지 않는다.
2. manifest.engine_version이 현재 ENGINE_VERSION 호환 표식과 같아야 한다. engine_artifact_sha256은 별도 기록이고 현행 상수를 실제 빌드 hash라고 간주하지 않는다.
3. source_versions가 registry 전체 ID/version 집합과 같고 Registry의 메모리 내용 fingerprint가 같아야 한다.
4. 모든 Envelope의 dataset_version이 manifest와 같고, 해당 policy ref의 edition/rule/schema/rule_schema 버전이 일치해야 한다.
5. 기존 validate_envelope_sources를 호출해 binding·locator·수명·정책 적용 범위·최소 확인일을 검증한다. 기존 로직을 복제하지 않는다.
6. 해당 PolicyEnvelope 내용 fingerprint를 대조하고 기존 walk_nodes로 dataset 전체 rule ID 유일성을 확인한다. 개별 Policy 생성자의 tree 검증을 재구현하지 않는다.

새 구조 오류는 ManifestValidationError(기존 PolicyDataError 하위)의 code/field다. POLICY_REFERENCE_SET_MISMATCH, POLICY_REFERENCE_MISMATCH, DATASET_VERSION_MISMATCH, SOURCE_REFERENCE_SET_MISMATCH, REGISTRY_FINGERPRINT_MISMATCH, POLICY_FINGERPRINT_MISMATCH 등으로 구분한다. 기존 source/envelope 오류는 그대로 전파하며 UNKNOWN으로 바꾸지 않는다.

**검증 한계:** 객체는 정확히 고정하지만 실제 파일 bytes hash·artifact 경로의 파일 존재·현재 실행 빌드 hash·과거 release 불변성·review 승인은 검증하지 않는다. 파일/배포 수용 검증까지 완료했다고 보고하지 않는다. 이번에 새 로더·배포 툴링으로 확장하지 않는다.

### Domain validity·What-if 연결

DRAFT/STALE 또는 review 미완료 자료도 domain-valid Manifest에 포함할 수 있다. 실제 서비스용 release-ready/추천 가능을 뜻하지 않는다. manifest에 별도 승인 상태를 중복 저장하지 않고 production gate와 freshness enforcement는 계속 미구현이다.

향후 What-if Before/After는 같은 manifest 선택·fingerprint, dataset_version, Policy edition/rule/reference 지문, source release, engine_version 및 선언된 engine artifact를 고정해야 한다. EvaluationContext에는 manifest.dataset_version/engine_version을 명시한다. 비교 도중 자료를 최신 버전으로 다시 선택하지 않는다. 같은 계산 실행 artifact를 사용해야 하며 현행 engine_version 상수만으로 binary 동일성이 입증된다고 주장하지 않는다. What-if 엔진이나 사용자 데이터 저장은 구현하지 않는다.

### 합성 예시·검증·다음 방향

신규 tests/test_dataset_manifest.py에서 **synthetic=True / test_only=True 용도**를 명시하고 기존 합성 Envelope JSON/sources.json을 읽어 Python Manifest를 만든다. ID는 synthetic-youth-test-only이며 2026 edition과 기존 synthetic-edition-001을 고정한다. 파일 bytes hash는 테스트 호출 경계에서 계산하고 엔진 artifact는 명시적 합성 bytes hash다. 실제 엔진 배포 artifact를 만들거나 실제 발행 manifest를 기록하지 않는다. 두 번째 합성 정책은 다중 정책 검증을 위한 메모리 객체뿐이다.

작업 전 전체 **1604 passed in 4.86s**, 신규 **132 passed in 0.64s**, 최종 전체 **1736 passed in 6.31s**다. 단일/복수 정책, 중복·누락·추가 참조, edition/rule/dataset/source 버전, 잘못된 hash·경로·날짜·타입, 내용 변경·순서 결정성, 불변성, 근거 오류, 기존 엔진 통합과 I/O 부재를 검증했다.

Git 저장소가 아니므로 기존 backend/tests/data/docs 59개 파일의 SHA256 기준선을 비교했다. policy_data 공개 API·validation 확장과 문서 3개만 수정했고 나머지 54개는 동일하다. 새 manifest 모델과 테스트 파일 2개를 추가했다. 기존 모든 테스트/기대값·모델·loader·routing/evaluator/Resolver/Adapter·fixtures는 변경하지 않았다. 신규 코드·테스트에 실제 정책명·공고번호·공식 URL이 없음을 확인했다.

IMPLEMENTED: DatasetManifest domain model, stable reference·객체 fingerprint, dataset consistency validation.

NOT IMPLEMENTED: Manifest JSON Loader, production dataset/acceptance, 실제 정책/source, 파일 bytes·실행 artifact 대조, freshness automation, 배포 플랫폼·DB·CI/CD.

최종 판단: **READY_FOR_FIRST_REAL_POLICY_DATA**. 이는 실제 자료를 처음 인코딩하는 다음 작업으로 이동할 준비이며 production release 승인이라는 뜻은 아니다.

**다음 작업은 실제 정책 데이터다.** 2026년 안산시 청년기본소득의 주민등록 resident leaf를 실제 공식 SourceDocument/SourceEvidence·PolicyEnvelope에 처음 encode하는 단계로 진행한다. 추가 generic infrastructure나 Manifest JSON Loader를 자동으로 제안하지 않는다.

다음 실제 데이터 단계의 기존 제약: 현재 Policy/Envelope loader는 True/True만 수용한다. 실제 자료를 합성이라고 표시해 우회하지 않는다. 실제 공식 자료임과 아직 서비스 추천에 사용할 수 없는 condition slice임을 구분하는 **최소 수용 경계**를 해당 실제 데이터 작업 안에서 명시적으로 해결해야 한다. 이번 M1.14에서는 제한을 해제하거나 실제 자료를 생성하지 않았다. 연도/분기 edition granularity와 전체 정책의 미해결 행정조건도 자동 확정하지 않는다.

## 31. M1.15 — IMPLEMENTED: 첫 실제 주민등록 조건 slice

현재 지원 범위는 실제 공식자료 기반 **DRAFT / CONDITION_SLICE**까지 확장됐다. 앞 절들의 실제 자료 미지원 설명은 해당 단계 당시 기록이다. 실제 데이터와 운영 승인을 구분하는 원칙은 유지한다.

Policy/PolicySet 및 parse_policy_set은 keyword-only `allow_real_data=False`를 기본으로 유지한다. 정확한 bool의 True/True만 기본 허용하며, 명시적 allow_real_data=True일 때 False/False도 허용한다. 혼합 조합·잘못된 타입은 항상 Data Error다. PolicySet 안의 각 Policy flags는 컨테이너와 일치해야 한다. 도메인 허용 인자는 InitVar이므로 저장/직렬화/내용 fingerprint에 들어가지 않으며 실제 객체를 replace할 때도 명시해야 한다.

Envelope loader는 외부/내부 flags 일치를 검증하고 실제 False/False인 경우만 기존 parser에 allow_real_data=True를 전달한다. 기존 합성 호출 형태와 모든 테스트 기대값을 유지한다. load_policy_set(path)는 합성 기본 경로이고 실제 데이터의 파일 진입점은 load_policy_envelope(path)다. PolicyEnvelope 모델과 source validator는 변경하지 않았다.

21절의 releases 배치에 실제 sources.json과 단일 resident root의 정규화 PolicyEnvelope를 추가했다. 경로명은 발행 승인 상태가 아니다. 세 source는 공식 내용/locator를 2026-10-20에 확인하여 VERIFIED이며, 정책은 DRAFT다. coverage는 주민등록 rule 하나와 미구현 조건 목록을 사용한다. source schema에 synthetic/test_only 필드를 새로 추가하지 않는다. 실제·합성 잘못된 registry 결합은 기존 ID/버전/locator/적용 정책 검증으로 거부한다.

DatasetManifest는 검증된 engine artifact 없이 실제 hash를 선언할 수 없어 이번에 생략했다. JSON manifest loader·빌드 시스템·운영 승인 gate를 추가하지 않았다. SourceRegistry strict load → Envelope strict load → cross-validation → 기존 routing/Resolver/Adapter → 주민등록 RuleEvaluation을 신규 실제 데이터 통합 테스트로 검증했다. 전체 정책 자격·접수상태·수급 여부는 판정하지 않는다.

상세 공식 출처·실제 IDs·파일·사례·한계·다음 단일 작업은 REAL_POLICY_001_IMPLEMENTATION.md를 따른다. 최종 판단: **FIRST_REAL_POLICY_SLICE_COMPLETE**.
