# M3.1 — What-if Before/After 구현 완료 보고

검증일: 2026-10-24. 대상: 기존 TEAM복학생 AI+X 저장소의 합성 웹서비스. 이 문서가 M3.1의 현재 구현 상태이며 M3.0 문서는 당시 이력으로 보존한다.

## 1. 기존 M3.0 재사용 구조

기존 React/TypeScript/Vite 페이지와 FastAPI, `SimulationInput`/`SimulationResponse`, `service.simulate`, 기존 SAMPLE-001~003, Policy Engine, Cashflow Core를 재사용했다. 새 프로젝트나 판정·예산 계산 코어를 만들지 않았다.

경로: 현재 입력 → 기존 단일 simulation → 현재 결과에서 비교 시작 → 현재 값을 복사한 After 수정 → 비교 HTTP → 기존 simulation adapter 두 번 → Python 차이/설명 → 비교 화면.

## 2. 생성·수정 파일

신규9개:

```text
backend/web/comparison_schemas.py
backend/web/comparison.py
frontend/src/comparison-api.ts
frontend/src/WhatIf.tsx
frontend/src/WhatIf.test.tsx
frontend/src/testing/comparison-fixture.json
frontend/tests/comparison-live-http.mts
tests/test_synthetic_comparison.py
docs/M3_1_WHAT_IF_COMPARISON.md
```

수정4개: `backend/web/app.py`(새 경로만 연결), `frontend/src/App.tsx`(비교 영역 연결), `frontend/src/styles.css`(비교 스타일 추가), `docs/ARCHITECTURE.md`(M3.1 추가).

기존 `service.py`, `schemas.py`, 모든 기존 Backend/Frontend 테스트, fixture, dependency/lockfile, README, 도메인 코어는 변경하지 않았다. 새 JSON은 실제 합성 adapter 응답에서 추출한 **컴포넌트 테스트 전용 snapshot**이다. 실제 화면은 이 파일을 import하지 않으며 API 응답을 표시한다.

## 3. 비교 API

`POST /api/synthetic/compare`를 추가했다. `GET /api/health`와 기존 `POST /api/synthetic/simulate`의 동작을 보존했다. 같은 no-store/입력 오류 처리 middleware를 사용한다. 비교 router에는 판정·예산 공식이 없다.

## 4. Before/After DTO

요청 `ComparisonInput`은 필수 `before`, `after`에 기존 `SimulationInput`을 그대로 사용한다. 필수 금액·nullable 정책 정보·엄격한 타입/범위·추가 필드 거부를 두 입력에 동일 적용한다. 각 모델은 frozen이며 입력을 수정하지 않는다.

응답:

| 필드 | 의미 |
|---|---|
| synthetic / test_only | 항상 true |
| before / after | 각 기존 SimulationResponse 전체 |
| numeric_deltas | After - Before, Python 정수 원 차이 |
| changed_input_fields | 바뀐 field와 Before/After 값 |
| policy_transitions | 정책별 전후 상태와 조건별 원본 판정/이유/근거 |
| explanation_facts | 실제 Cashflow 결과·차이·정책 rule 참조 |
| explanations | 위 사실의 정형 한국어 설명 |
| unknown_information | 전후 missing_fields와 실제 정책 상태 |
| benefit_applied_krw | 항상0 |
| disclaimer | 합성 시연·실제 승인/금융수익 보장 없음 |

numeric_deltas는 월소득·월세·고정/기타지출·총수입·총지출·정책 전후 여유자금·저축 투입 상한·혜택 차이를 포함한다. 사용자 지정 상한 차이는 **양쪽이 정수일 때만** 숫자 차이를 내며 어느 한쪽이 null이면 null이다. 미지정을0으로 바꾸지 않는다. UI는 바뀐 입력 목록에 ‘별도 상한 없음 ↔ 0원’을 그대로 표시한다.

## 5. 정책 엔진 실제 호출

`compare_scenarios`가 `service.simulate(data.before)`와 `service.simulate(data.after)`를 순차 호출한다. 각 adapter가 기존 `evaluate_policies`를 호출한다. 신규 테스트의 spy가 adapter→policy→cash를 서로 다른 입력으로2회 실행하는 것을 확인하며 spy 내부에서도 실제 기존 함수를 실행한다.

정책 집합은 policy_id로 대응하고 조건은 rule_id로 대응한다. 그룹의 전체 상태는 기존 엔진 결과를 사용하고 새로 집계하지 않는다.

## 6. Cashflow Core 실제 호출

같은 두 adapter가 기존 `calculate_cashflow`를 각각 실행한다. 비교 계층은 완성된 결과의 차이만 계산하며 수입-지출/저축 가능액 산식을 재작성하지 않는다. 기존 Core 직접 호출 결과 및 기존 단일 API 결과와 전후 응답 전체가 일치하는 테스트를 통과했다.

## 7. 동시에 변경 가능한 변수

주요 입력: 월 생활비 소득·월세·사용자 저축 상한·취업상태4개. 추가 입력 펼침: 만 나이·지역·재학·고정지출·기타지출5개. 모든9개를 독립 수정할 수 있다. 변경 최소 개수 제한이 없으며0개/1개/4개 변경을 검증했다. 재학과 취업은 독립이고 Before는 After 수정/초기화의 영향을 받지 않는다.

## 8. 정책 상태 변화

기존 합성 fixture와 엔진에서 발생하는 다음6개 전이를 SAMPLE-002의 미취업/취업/미입력으로 검증했다.

PASS→PASS, PASS→FAIL, FAIL→PASS, UNKNOWN→UNKNOWN, PASS→UNKNOWN, UNKNOWN→PASS.

Before/After 각각의 원본 reason_code, missing_fields, expected_condition, evaluated_value, evidence_refs를 보존한다. 화면은 전후 상태/한국어 표시와 조건별 근거를 보여준다. 전체 FAIL이어도 다른 누락 조건은 삭제하지 않는다.

## 9. 월 예산 차이

UI는 현재/변경/변화량4열 표로 월소득·월세·고정지출·기타지출·총지출·여유자금·저축 투입 상한·정책 혜택을 표시한다. 모든 변화량은 API가 계산한다. React에서는 숫자 표기와 부호만 붙인다. 서버가 전달한 특정 delta를 그대로 표시하는 테스트로 화면의 중복 계산을 방지한다.

## 10. 설명 생성 방식

외부 LLM 없이 Python 정형 문장을 생성한다. 월소득/월세/기타지출의 실제 차이와 기존 결과의 차이를 설명한다. 정책 설명은 **실제로 바뀐 입력 필드와 대응하는 조건**만 원인으로 제시하고 전후 조건 상태를 함께 보여준다. 생활비 소득 변경을 미취업 조건 변경 원인으로 설명하지 않는다.

가구소득은 계속 미확인이라고 표시한다. 조건 변경이 없으면 없다고 설명하고 지원하지 않는 원인을 추측하지 않는다. explanation_facts에 계산값과 rule 참조가 있어 향후 별도 설명 계층에 전달할 수 있다. 이번에 LLM을 연결하지 않았다.

## 11. React 비교 화면

기존 계산 결과 아래 ‘상황이 바뀐다면?’을 추가했다. ‘현재 상황으로 비교 시작’이 서버 응답의 입력 요약을 복사한다. After만 수정하고 비교 버튼을 누른다. 현재/변경/차이 표, 정책별 상태 전이 카드, 바뀐 입력, 이유와 미확인 정보를 보여준다.

‘현재 값으로 다시 설정’은 After를 Before로 되돌리고 비교를 비운다. 기존 현재 입력을 바꾸면 단일 결과와 비교 영역이 함께 사라지고 현재 상황을 다시 계산하도록 한다. 기존 M3.0 입력/결과 화면과 스타일을 유지했다.

## 12. 실제 HTTP 확인

기존 저장소에서 FastAPI127.0.0.1:8100, Vite127.0.0.1:5173을 실행했다. `/api` proxy를 재사용한다.

`frontend/tests/comparison-live-http.mts`가 실제 화면의 `compare` 함수를 import해 실제 fetch로 네 변수 변경·동일 입력·적자/상한 null·422를 검증했다. 기존 `tests/live-http.mts`도 통과했다. 두 HTTP 시험 모두 mock 응답이 없다.

실행: frontend 폴더에서 `node --experimental-strip-types tests/comparison-live-http.mts`. 서버 실행 명령은 기존 README와 같고 추가 의존성은 없다.

## 13. 실제 브라우저 확인

브라우저에서 현재 상황 입력→현재 계산→After 복사→네 변수 수정→실제 API 비교를 실행했다. 변경0개 비교, 음수 Cashflow, 취업 미입력 PASS→UNKNOWN, 상한 null/0, 초기화도 확인했다. API 중단 시 서버 오류, Vite 중단 시 실제 네트워크 오류가 각각 표시되고 비교 결과가 비워지는 것을 확인했다. 중단한 로컬 서버를 복구하고 새 비교를 정상 실행했다.

390×844에서 viewport/문서 scrollWidth 일치와 수평 넘침 없음을 확인했다. 스크롤바가 표시되는 관찰에서는 clientWidth/scrollWidth가 모두375, 전체 페이지 캡처에서는 모두390이었다. 입력 글자는16px이다. 표와 주요 정책 전이를 육안 확인했다. 임시 viewport는 원래대로 복구했다. **실물 휴대폰·모바일 Safari·가상 키보드 시험은 미실행**이다.

사진과 최종 브라우저 상태는 작업 채팅 폴더 `output/m3.1/`에 저장했다. localhost 서버는 검증 후 실행 상태로 남겼다.

## 14. 제안서 4쪽 수치 재현

공통: 안산시, 만24세, 재학 중, 고정지출200,000원, 기타지출350,000원.

| 항목 | Before | After | 변화 |
|---|---:|---:|---:|
| 취업상태 | 미취업 | 취업 | 변경 |
| 월소득 | 1,500,000 | 1,800,000 | +300,000 |
| 월세 | 450,000 | 550,000 | +100,000 |
| 월 여유자금 | **500,000** | **700,000** | **+200,000** |
| 저축 투입 상한 | **300,000** | **500,000** | **+200,000** |
| SAMPLE-001 | PASS | PASS | 유지 |
| SAMPLE-002 | PASS | FAIL | 변경 |
| SAMPLE-003 | UNKNOWN | UNKNOWN | 유지 |
| 정책 혜택 반영 | **0** | **0** | **0** |

Backend 테스트·실제 HTTP·실제 브라우저에서 재현했다. UI에 이 표의 결과를 하드코딩하지 않았다.

## 15. UNKNOWN 유지

두 adapter 모두 `policy_facts=()`를 유지한다. 월 생활비 소득을 높여도 가구소득 사실이 생성되지 않는다. SAMPLE-003은 안산시에서 UNKNOWN→UNKNOWN이며 가구소득 정보 부족을 계속 표시한다. 다른 지역으로 변경하면 전체 FAIL이어도 가구소득 누락을 보존한다.

## 16. 적자·미입력 상한

소득100,000원/지출1,000,000원은 After 여유자금 **-900,000원**, Before 대비 **-1,400,000원**이며 오류로 처리하지 않는다. 저축 투입 상한은0원이다.

여유자금500,000원에서 사용자 상한 null은 저축 투입500,000원, 상한0원은 저축 투입0원이다. null/0을 전후 양 방향으로 검증했고 브라우저에서도 다른 결과를 확인했다.

## 17. API/네트워크 오류 처리

입력 오류(로컬 또는422), 정책UNKNOWN, 정책FAIL, 정상 적자, 서버 오류, 네트워크 오류,10초 시간 초과, 요청 중 상태를 구분한다. 비교는 하나의 응답에서만 표시하므로 서로 다른 요청의 Before/After를 섞지 않는다. After 평가 실패 시 부분 응답을 반환하지 않는500 시험을 통과했다.

수정/초기화/새 요청/컴포넌트 해제 시 AbortController와 증가하는 요청 번호로 오래된 응답을 차단한다. 취소를 무시하고 늦게 성공/실패하는 fetch를 사용한 신규 테스트도 통과했다. 입력 수정 시 이전 비교를 지우며 요청 중에도 After를 수정하거나 초기화할 수 있다.

## 18. 신규 Backend 테스트

`tests/test_synthetic_comparison.py`: **48 passed**.

동일/개별/네 변수 변경,6개 상태 전이, UNKNOWN·소득 분리, 음수/음수 차이, 상한 null/0, 원본 Core/adapter 결과 전체 일치, 실제 함수2회 호출, 사용자 입력 불변성/요청 독립성, 두 nested 입력 검증/지원금 우회 차단, 두 입력 선검증, After 실패 시 부분 반환 차단, 혜택0원·disclaimer·facts·기존 endpoint 보존을 검증했다.

## 19. 신규 Frontend 테스트

기존 **16개 그대로 + 신규24개 = 40 passed**. 복사/여러 변수/0·1개 변경, 요청 payload, 상태 전이/서버 변화량/설명/UNKNOWN, 초기화, 상한 null/0·재학 독립, 입력 오류, 적자,422/500/네트워크 오류/재시도, 늦은 응답/실패,10초 timeout, 기존 페이지 연결과 현재 입력 수정 시 폐기, semantic table을 검증했다.

컴포넌트 테스트는 fetch mock을 사용한다. 실제 HTTP 및390px 레이아웃은 별도 실서버/브라우저 증거다. jsdom으로 실제 폭을 검증했다고 주장하지 않는다. TypeScript 검사와 최종 Vite 빌드가 성공했고 빌드 경고는 없다.

## 20. 전체 pytest 결과

작업 전: **11,359 passed, 1 skipped, 1 warning** (88.64초).

최종 작업 후: **11,407 passed, 1 skipped, 1 warning**. 최종 실행 요약: `11407 passed, 1 skipped, 1 warning in 95.05s (0:01:35)`. 신규48개만 증가했다. Windows/NTFS 시험은 보안 설정 변경 없이 허용된 실행 도구를 사용했다.

## 21. 기존11,359개 회귀

기존 테스트의 제거·기대값 변경·건너뜀 추가가 없다. 기존 Backend 테스트 파일 전부와 Frontend `App.test.tsx`의 SHA256·크기·수정시각을 보존했다. 기존42개 웹 테스트와16개 화면 테스트도 포함해 통과했다.

## 22. 기존 skipped/warning

skipped1: `tests/test_historical_raw_bytes_preparation_ntfs.py:202`, 실제 파일 symlink 생성 권한 부족. M2.77은 **HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY** 유지.

warning1: 기존 Starlette TestClient의 httpx 사용 deprecation 안내. 숨기거나 제거하지 않았고 새 경고를 추가하지 않았다.

## 23. GV/BV

GV01~GV15와 BV01~BV16을 포함한 기존 golden/test/fixture를 수정하지 않았다. 해당 기존 시험은 전체 pytest에서 통과했다.

## 24. Coverage freeze

기준 파일238개 중 승인된 수정4개를 제외한 **234개**의 SHA256/크기/mtime_ns가 동일함을 최종 감사로 확인했다. Policy/Cashflow/Coverage, Historical6 loader, CrossValidator, Same-call Orchestrator, RawBytesPreparation, Acceptance/Benefit을 수정하지 않았다. 정책·예산 코어를 비교 계층에서 복제하지 않았다.

## 25. 실제 release SHA256

실제 release6개 모두 SHA256/크기/mtime_ns 불변이다. 아래 digest는 기준과 현재를 대조한 값이다.

| 파일 | SHA256 |
|---|---|
| `data/releases/ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025` |
| `data/releases/ansan-youth-2026-10-20-001/README.md` | `4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f` |
| `data/releases/ansan-youth-2026-10-20-001/sources.json` | `a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b` |
| `data/releases/ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92` |
| `data/releases/ansan-youth-2026-10-20-002/README.md` | `8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99` |
| `data/releases/ansan-youth-2026-10-20-002/sources.json` | `711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620` |

두 release를 별개의 실제 정책2개로 세지 않는다.

## 26. ResidenceHistory

**OFFICIAL_INQUIRY_REQUIRED**를 유지한다. 거주기간 사실/판정/추정 로직을 추가하지 않았다.

## 27. 실제 정책·지원금 보호

안산 실제 정책은 **DRAFT / CONDITION_SLICE**를 유지한다. 실제 release는 비교 API에서 로드하지 않는다. 합성PASS를 실제 지원금 수령/정책 승인으로 표시하지 않는다. 전후 실제 혜택 반영액과 차이는 **0원**이다. 제품은 모든 청년을 대상으로 하고 안산은 초기 검증 지역이다.

## 28. 개인정보 저장

Before/After 입력과 결과는 화면 메모리 및 요청 처리에만 사용한다. DB·파일·브라우저 저장소·쿠키·사용자 이력·외부 LLM/분석 서비스 전송이 없다. access log 비활성/응답 no-store/입력 원문 없는422를 유지한다. 시험은 합성 입력으로 수행했다. 공개 배포하지 않았다.

## 29. 미구현 기능

금융상품 추천·금리/이자/만기 계산, 외부 LLM 설명, 실제 정책의 서비스 판정/지원금 반영, 공개 배포, 로그인·DB는 구현하지 않았다.

## 30. 최종 판단

**M3_WHAT_IF_COMPARISON_COMPLETE**

실제 브라우저에서 사용자가 조건을 바꾸고, 실제 서버의 기존 엔진 두 번 실행 결과·차이·근거를 확인했다. 합성 비교 범위의 완료이며 정책 데이터 승인과 M2.77 Windows 보안 증거의 완료를 뜻하지 않는다.

### 최초 실패·수정·재실행 기록

- 신규 화면 테스트 최초:38 passed/1 failed. 같은 설명이 요약과 펼침 상세에 모두 있어 단일 요소 검색이 중복 매칭됐다. 신규 테스트의 선택자를 요약 문단으로 좁혔고 시간 초과 시험1개를 추가해 최종40개 통과. 기존 테스트/기대값은 수정하지 않았다.
- 브라우저에서 ‘월세이’ 조사 오류 발견: 새 비교 설명을 ‘월세가’로 고치고 신규 Backend 기대값에 검증을 추가했다. 출력의 내부 구현 용어도 사용자에게 필요한 금액 설명으로 바꾸고 snapshot/테스트/빌드를 재확인했다.
- 기존 탭이 없어 새 검증 탭을 만들었다. 첫 binding 변수 실패는 도구 연결 문제이며 새 탭을 식별해 정상 검증했다.
- 전체 페이지와 clip을 함께 준 첫 캡처가 잘못된 영역을 보여 전체 페이지 캡처로 교체했다. 최종 증거는 교체한 정상 이미지다.
- 기존 서버 탐색 명령1회가 실패해 실제 실행 프로세스가 없음을 별도 확인하고 서버를 시작했다. 타 프로젝트 프로세스를 종료하지 않았다.
- 서버/Vite 중단 오류는 의도한 실패 시험이다. 실행 중인 이번 로컬 프로세스만 중단/복구했다. OS 보안 설정·관리자 권한을 변경하지 않았다.

## 31. 다음 최소 작업 한 개

**M3.2 — 합성 적금1개의 예상 만기금액 계산 기능**을 제안한다. 기존 저축 투입 상한을 납입 예산으로 사용하고 기간·납입한도·적용 금리·세금 기준을 먼저 명시한 뒤 Python 계산/테스트/화면으로 연결한다. 실제 상품 추천·최고금리 보장·미검증 정책 지원금은 포함하지 않는다. 이번 단계에서 구현하지 않았다.
